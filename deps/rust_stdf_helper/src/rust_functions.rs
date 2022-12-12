//
// rust_functions.rs
// Author: noonchen - chennoon233@foxmail.com
// Created Date: October 29th 2022
// -----
// Last Modified: Mon Dec 12 2022
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::{database_context::DataBaseCtx, StdfHelperError};
use chrono::{DateTime, Local, NaiveDateTime, TimeZone, Utc};
use lazy_static::lazy_static;
use rust_stdf::*;
use rust_xlsxwriter::{Worksheet, XlsxError};
use std::collections::HashMap;
use std::io::{Read, Seek, SeekFrom};
use std::{fs, io};
use zip::ZipArchive;

lazy_static! {
    static ref UNIT_PREFIX: HashMap<i32, &'static str> = HashMap::from([
        (15, "f"),
        (12, "p"),
        (9, "n"),
        (6, "u"),
        (3, "m"),
        (2, "%"),
        (0, ""),
        (-3, "K"),
        (-6, "M"),
        (-9, "G"),
        (-12, "T"),
    ]);
}

#[inline(always)]
fn scale_unit(unit: &Option<String>, scale: i32) -> String {
    if let Some(u) = unit {
        format!("{}{}", UNIT_PREFIX.get(&scale).unwrap_or(&""), u)
    } else {
        String::new()
    }
}

#[inline(always)]
fn scale_option_value(value: &Option<f32>, flag: &Option<[u8; 1]>, scale: i32, mask: u8) -> f32 {
    if let Some(f32_num) = value {
        if let Some(valid) = flag.map(|f| f[0] & mask == 0) {
            if valid {
                f32_num * 10f32.powi(scale)
            } else {
                f32::NAN
            }
        } else {
            f32::NAN
        }
    } else {
        f32::NAN
    }
}

pub struct RecordTracker {
    // file id, test num, test name -> unique test id (map size)
    id_map: HashMap<(usize, u32, String), usize>,

    // unique test id -> result scale
    scale_map: HashMap<usize, i32>,

    // unique test id -> low limit in 1st PTR
    default_llimit: HashMap<usize, f32>,
    // unique test id -> high limit in 1st PTR
    default_hlimit: HashMap<usize, f32>,

    // unique test id -> fail count
    test_fail_count: HashMap<usize, u32>,

    // file id, head, site -> dut index
    dut_index_tracker: HashMap<(usize, u8, u8), u64>,

    // file id, head -> wafer index
    wafer_index_tracker: HashMap<(usize, u8), u64>,

    // (file id, HBIN) -> (bin name, bin type)
    hbin_tracker: HashMap<(usize, u16), (String, char)>,
    // (file id, SBIN) -> (bin name, bin type)
    sbin_tracker: HashMap<(usize, u16), (String, char)>,

    // DTR/GDR location tracker, file id -> is_before_PRR?
    datalog_pos_tracker: HashMap<usize, bool>,

    // program section tracker
    program_sections: HashMap<usize, Vec<String>>,

    // for counting
    // file id -> dut count
    dut_total: HashMap<usize, u64>,
    // file id -> wafer count
    wafer_total: HashMap<usize, u64>,
}

impl RecordTracker {
    pub fn new() -> Self {
        RecordTracker {
            id_map: HashMap::with_capacity(1024),
            scale_map: HashMap::with_capacity(1024),
            default_llimit: HashMap::with_capacity(1024),
            default_hlimit: HashMap::with_capacity(1024),
            test_fail_count: HashMap::with_capacity(1024),
            dut_index_tracker: HashMap::with_capacity(128),
            wafer_index_tracker: HashMap::with_capacity(128),
            hbin_tracker: HashMap::with_capacity(128),
            sbin_tracker: HashMap::with_capacity(1024),
            datalog_pos_tracker: HashMap::with_capacity(32),
            program_sections: HashMap::with_capacity(32),
            dut_total: HashMap::with_capacity(32),
            wafer_total: HashMap::with_capacity(32),
        }
    }

    #[inline(always)]
    pub fn pir_detected(&mut self, file_id: usize, head_num: u8, site_num: u8) -> u64 {
        // indicating any DTR or GDR is before PRR
        self.datalog_pos_tracker.insert(file_id, true);
        let dut_index;

        if let Some(dut_total) = self.dut_total.get_mut(&file_id) {
            // increment dut_index by 1
            *dut_total += 1;
            // update dut index tracker
            self.dut_index_tracker
                .insert((file_id, head_num, site_num), *dut_total);
            dut_index = *dut_total;
        } else {
            // no dut_index was saved for file id, set dut_index to default 1
            dut_index = 1;
            // insert dut_index=1 to hashmap
            self.dut_total.insert(file_id, dut_index);
            self.dut_index_tracker
                .insert((file_id, head_num, site_num), dut_index);
        };
        dut_index
    }

    #[inline(always)]
    pub fn prr_detected(
        &mut self,
        file_id: usize,
        prr_rec: &PRR,
    ) -> Result<(u64, Option<u64>), StdfHelperError> {
        // in PRR, all BPS should be closed by EPS
        if let Some(pg_sec_list) = self.program_sections.get_mut(&file_id) {
            pg_sec_list.clear();
        };
        // set is_before_PRR to false
        self.datalog_pos_tracker.insert(file_id, false);
        // infer HBIN/SBIN types, it is helpful
        // when file missing HBR/SBR
        // HBIN
        self.hbin_tracker
            .entry((file_id, prr_rec.hard_bin))
            .or_insert_with(|| {
                let hbin_type = if prr_rec.part_flg[0] & 0b00011000 == 0 {
                    'P'
                } else if prr_rec.part_flg[0] & 0b00010000 == 0 {
                    'F'
                } else {
                    'U'
                };
                (String::new(), hbin_type)
            });
        // SBIN
        self.sbin_tracker
            .entry((file_id, prr_rec.soft_bin))
            .or_insert_with(|| {
                let sbin_type = if prr_rec.part_flg[0] & 0b00011000 == 0 {
                    'P'
                } else if prr_rec.part_flg[0] & 0b00010000 == 0 {
                    'F'
                } else {
                    'U'
                };
                (String::new(), sbin_type)
            });
        // get dut_index
        let dut_index = match self.dut_index_tracker.get( &(file_id, prr_rec.head_num, prr_rec.site_num) ) {
            Some(stored_ind) => Ok(*stored_ind),
            // if dut_index is None, returns Err
            None => Err(StdfHelperError { msg: format!("STDF file structure error in File[{}]: PRR Head[{}] Site[{}] showed up before PIR", file_id, prr_rec.head_num, prr_rec.site_num) }),
        }?;
        // get wafer_index if WIR is detected
        let wafer_index = self
            .wafer_index_tracker
            .get(&(file_id, prr_rec.head_num))
            .copied();
        Ok((dut_index, wafer_index))
    }

    #[inline(always)]
    pub fn hbr_detected(&mut self, file_id: usize, hbr_rec: &HBR) {
        let bin_pf = if hbr_rec.hbin_pf == 'P' || hbr_rec.hbin_pf == 'F' {
            hbr_rec.hbin_pf
        } else {
            'U'
        };
        // since HBR is valid, we can drop the inferred info from PRR
        if let Some((name, pf)) = self.hbin_tracker.get_mut(&(file_id, hbr_rec.hbin_num)) {
            // update name & Pass/Fail if exist
            if !hbr_rec.hbin_nam.is_empty() {
                *name = hbr_rec.hbin_nam.clone();
            };
            *pf = bin_pf;
        } else {
            // insert if not exist
            self.hbin_tracker.insert(
                (file_id, hbr_rec.hbin_num),
                (hbr_rec.hbin_nam.clone(), bin_pf),
            );
        }
    }

    #[inline(always)]
    pub fn sbr_detected(&mut self, file_id: usize, sbr_rec: &SBR) {
        let bin_pf = if sbr_rec.sbin_pf == 'P' || sbr_rec.sbin_pf == 'F' {
            sbr_rec.sbin_pf
        } else {
            'U'
        };
        // since HBR is valid, we can drop the inferred info from PRR
        if let Some((name, pf)) = self.sbin_tracker.get_mut(&(file_id, sbr_rec.sbin_num)) {
            // update name & Pass/Fail if exist
            if !sbr_rec.sbin_nam.is_empty() {
                *name = sbr_rec.sbin_nam.clone();
            };
            *pf = bin_pf;
        } else {
            // insert if not exist
            self.sbin_tracker.insert(
                (file_id, sbr_rec.sbin_num),
                (sbr_rec.sbin_nam.clone(), bin_pf),
            );
        }
    }

    #[inline(always)]
    pub fn wir_detected(&mut self, file_id: usize, head_num: u8) -> u64 {
        let wafer_index;

        if let Some(wafer_total) = self.wafer_total.get_mut(&file_id) {
            // increment by 1
            *wafer_total += 1;
            // update wafer index tracker
            self.wafer_index_tracker
                .insert((file_id, head_num), *wafer_total);
            wafer_index = *wafer_total;
        } else {
            // set default 1 if not exists
            wafer_index = 1;
            self.wafer_total.insert(file_id, wafer_index);
            self.wafer_index_tracker
                .insert((file_id, head_num), wafer_index);
        };
        wafer_index
    }

    /// return (exist, scale) for [PTR], [MPR]
    #[inline(always)]
    pub fn update_scale(&mut self, test_id: usize, scale: &Option<i8>) -> (bool, i32) {
        match self.scale_map.get(&test_id) {
            Some(s) => (true, *s),
            None => {
                // new test_id, insert into map
                // if scale is None, use 0 instead, for
                // it have no effect on the result
                let s = scale.unwrap_or(0) as i32;
                self.scale_map.insert(test_id, s);
                (false, s)
            }
        }
    }

    /// return (dut_index, test_id) for [PTR], [FTR], [MPR] or maybe [STR] in the future
    ///
    /// ## Error
    /// if request dut_index from (file_id, head, site) that never stored in `dut_index_tracker`
    #[inline(always)]
    pub fn xtr_detected(
        &mut self,
        file_id: usize,
        head_num: u8,
        site_num: u8,
        test_num: u32,
        test_txt: &str,
    ) -> Result<(u64, usize), StdfHelperError> {
        // get dut_index
        let dut_index = match self.dut_index_tracker.get( &(file_id, head_num, site_num) ) {
            Some(stored_ind) => Ok(*stored_ind),
            // if dut_index is None, returns Err
            None => Err(StdfHelperError { msg: format!("STDF file structure error in File[{}]: TestNumber[{}] Head[{}] Site[{}] showed up before PIR", file_id, test_num, head_num, site_num) }),
        }?;
        // get test_id
        let key = (file_id, test_num, test_txt.to_string());
        let test_id = match self.id_map.get(&key) {
            Some(id) => *id,
            None => {
                let unique_id = self.id_map.len();
                self.id_map.insert(key, unique_id);
                unique_id
            }
        };
        Ok((dut_index, test_id))
    }

    /// return `true` if test_id is already in hashmap, no update
    #[inline(always)]
    pub fn update_default_limits(&mut self, test_id: usize, llimit: f32, hlimit: f32) -> bool {
        let llimit_exist = self.default_llimit.contains_key(&test_id);
        let hlimit_exist = self.default_hlimit.contains_key(&test_id);

        if !llimit_exist {
            // update llimit
            self.default_llimit.insert(test_id, llimit);
        }
        if !hlimit_exist {
            // update hlimit
            self.default_hlimit.insert(test_id, hlimit);
        }
        llimit_exist && hlimit_exist
    }

    /// return (llimit_changed, hlimit_changed) if [PTR] limits is differ from that of 1st PTR
    ///
    /// ## Error
    /// if no default limit can be found for test_id
    #[inline(always)]
    pub fn is_ptr_limits_changed(
        &self,
        test_id: usize,
        llimit: f32,
        hlimit: f32,
    ) -> Result<(bool, bool), StdfHelperError> {
        // llimit
        let llimit_changed = match self.default_llimit.get(&test_id) {
            Some(dft_ll) => {
                // NAN - NAN > EPSILON is `false`
                // meaning if limit is NAN, it will return false
                Ok((llimit - *dft_ll).abs() > f32::EPSILON)
            }
            None => Err(StdfHelperError {
                msg: "Default low limit can not be read...this should never happen".to_string(),
            }),
        }?;
        // hlimit
        let hlimit_changed = match self.default_hlimit.get(&test_id) {
            Some(dft_hl) => Ok((hlimit - *dft_hl).abs() > f32::EPSILON),
            None => Err(StdfHelperError {
                msg: "Default high limit can not be read...this should never happen".to_string(),
            }),
        }?;
        Ok((llimit_changed, hlimit_changed))
    }

    #[inline(always)]
    pub fn get_program_section(&self, file_id: usize) -> Option<String> {
        // use `;` to join all sections
        self.program_sections
            .get(&file_id)
            .map(|pg_sec_list| pg_sec_list.join(";"))
    }

    #[inline(always)]
    pub fn get_wafer_index(&self, file_id: usize, head_num: u8) -> Result<u64, StdfHelperError> {
        match self.wafer_index_tracker.get(&(file_id, head_num)) {
            Some(ind) => Ok(*ind),
            None => Err(StdfHelperError {
                msg: format!(
                    "STDF file structure error in File[{}]: WRR Head[{}] showed up before WIR",
                    file_id, head_num
                ),
            }),
        }
    }

    #[inline(always)]
    pub fn tsr_detected(&mut self, file_id: usize, tsr_rec: &TSR) -> Result<(), StdfHelperError> {
        // get test_id
        let test_id = match self.id_map.get(&(
            file_id,
            tsr_rec.test_num,
            tsr_rec.test_nam.to_string(),
        )) {
            Some(id) => Ok(*id),
            None => {
                // in some stdf files, the test name in TSR might be different
                // in PTR/MPR/FTR, in this case, we should find the test id that
                // file id and test number matched
                match self
                    .id_map
                    .keys()
                    .find(|&key| key.0 == file_id && key.1 == tsr_rec.test_num)
                {
                    Some(key) => {
                        println!("TSR: [{}\t{}] matches no records in File[{}], use test name [{}] instead", 
                        tsr_rec.test_num, tsr_rec.test_nam, file_id, &key.2);
                        // this unwrap is infallible
                        Ok(*self.id_map.get(key).unwrap())
                    }
                    None => {
                        // if fild id and test number cannot match any key,
                        // report this error
                        Err(StdfHelperError {
                            msg: format!(
                                "Test number [{}] in TSR matches no records in File[{}]",
                                tsr_rec.test_num, file_id
                            ),
                        })
                    }
                }
            }
        }?;
        // update fail cnt hashmap, only when fail cnt is valid
        if tsr_rec.fail_cnt != u32::MAX {
            if let Some(cnt) = self.test_fail_count.get_mut(&test_id) {
                *cnt += tsr_rec.fail_cnt;
            } else {
                // if test id is not exist, insert
                self.test_fail_count.insert(test_id, tsr_rec.fail_cnt);
            }
        }
        Ok(())
    }

    #[inline(always)]
    pub fn get_datalog_relative_pos(&self, file_id: usize) -> (u64, bool) {
        let dut_index = match self.dut_total.get(&file_id) {
            Some(ind) => *ind,
            // DTR/GDR can appear any where in the file,
            // if it's before the 1st PIR, `None` is matched.
            None => 0,
        };
        let is_before_prr = match self.datalog_pos_tracker.get(&file_id) {
            Some(b) => *b,
            // same as above
            None => true,
        };
        (dut_index, is_before_prr)
    }

    #[inline(always)]
    pub fn bps_detected(&mut self, file_id: usize, bps_rec: &BPS) -> Result<(), StdfHelperError> {
        self.program_sections
            .entry(file_id)
            .and_modify(|v| v.push(bps_rec.seq_name.clone()))
            .or_insert_with(|| vec![bps_rec.seq_name.clone()]);
        Ok(())
    }

    #[inline(always)]
    pub fn eps_detected(&mut self, file_id: usize) -> Result<(), StdfHelperError> {
        self.program_sections.entry(file_id).and_modify(|v| {
            v.pop();
        });
        Ok(())
    }
}

#[inline(always)]
pub fn process_incoming_record(
    db_ctx: &mut DataBaseCtx,
    rec_tracker: &mut RecordTracker,
    rec_info: (usize, usize, ByteOrder, u64, usize, StdfRecord),
) -> Result<(), StdfHelperError> {
    // unpack info
    let (file_id, subfile_id, order, _offset, _data_len, rec) = rec_info;
    match rec {
        // // rec type 15
        StdfRecord::PTR(ptr_rec) => on_ptr_rec(db_ctx, rec_tracker, file_id, ptr_rec)?,
        StdfRecord::MPR(mpr_rec) => on_mpr_rec(db_ctx, rec_tracker, file_id, mpr_rec)?,
        StdfRecord::FTR(ftr_rec) => on_ftr_rec(db_ctx, rec_tracker, file_id, ftr_rec)?,
        // StdfRecord::STR(str_rec) => str_rec.read_from_bytes(raw_data, order),
        // // rec type 5
        StdfRecord::PIR(pir_rec) => on_pir_rec(db_ctx, rec_tracker, file_id, pir_rec)?,
        StdfRecord::PRR(prr_rec) => on_prr_rec(db_ctx, rec_tracker, file_id, prr_rec)?,
        // // rec type 2
        StdfRecord::WIR(wir_rec) => on_wir_rec(db_ctx, rec_tracker, file_id, wir_rec)?,
        StdfRecord::WRR(wrr_rec) => on_wrr_rec(db_ctx, rec_tracker, file_id, wrr_rec)?,
        StdfRecord::WCR(wcr_rec) => on_wcr_rec(db_ctx, file_id, subfile_id, wcr_rec)?,
        // // rec type 50
        StdfRecord::GDR(gdr_rec) => on_gdr_rec(db_ctx, rec_tracker, file_id, gdr_rec)?,
        StdfRecord::DTR(dtr_rec) => on_dtr_rec(db_ctx, rec_tracker, file_id, dtr_rec)?,
        // // rec type 10
        StdfRecord::TSR(tsr_rec) => on_tsr_rec(rec_tracker, file_id, tsr_rec)?,
        // // rec type 1
        StdfRecord::MIR(mir_rec) => on_mir_rec(db_ctx, file_id, subfile_id, mir_rec)?,
        StdfRecord::MRR(mrr_rec) => on_mrr_rec(db_ctx, file_id, subfile_id, mrr_rec)?,
        StdfRecord::PCR(pcr_rec) => on_pcr_rec(db_ctx, file_id, pcr_rec)?,
        StdfRecord::HBR(hbr_rec) => on_hbr_rec(rec_tracker, file_id, hbr_rec)?,
        StdfRecord::SBR(sbr_rec) => on_sbr_rec(rec_tracker, file_id, sbr_rec)?,
        StdfRecord::PMR(pmr_rec) => on_pmr_rec(db_ctx, file_id, pmr_rec)?,
        StdfRecord::PGR(pgr_rec) => on_pgr_rec(db_ctx, file_id, pgr_rec)?,
        StdfRecord::PLR(plr_rec) => on_plr_rec(db_ctx, file_id, plr_rec)?,
        StdfRecord::RDR(rdr_rec) => on_rdr_rec(db_ctx, file_id, subfile_id, rdr_rec)?,
        StdfRecord::SDR(sdr_rec) => on_sdr_rec(db_ctx, file_id, subfile_id, sdr_rec)?,
        // // StdfRecord::PSR(psr_rec) => psr_rec,
        // // StdfRecord::NMR(nmr_rec) => nmr_rec,
        // // StdfRecord::CNR(cnr_rec) => cnr_rec,
        // // StdfRecord::SSR(ssr_rec) => ssr_rec,
        // // StdfRecord::CDR(cdr_rec) => cdr_rec,
        // // rec type 0
        StdfRecord::FAR(far_rec) => on_far_rec(db_ctx, file_id, subfile_id, order, far_rec)?,
        StdfRecord::ATR(atr_rec) => on_atr_rec(db_ctx, file_id, subfile_id, atr_rec)?,
        StdfRecord::VUR(vur_rec) => on_vur_rec(db_ctx, file_id, subfile_id, vur_rec)?,
        // // rec type 20
        StdfRecord::BPS(bps_rec) => on_bps_rec(rec_tracker, file_id, bps_rec)?,
        StdfRecord::EPS(_eps_rec) => on_eps_rec(rec_tracker, file_id)?,
        // rec type 180: Reserved
        // rec type 181: Reserved
        // invalid
        StdfRecord::InvalidRec(header) => {
            return Err(StdfHelperError {
                msg: format!(
                    "Invalid record detected, typ: {}, sub: {}, len: {}",
                    header.typ, header.sub, header.len
                ),
            })
        }
        // not matched
        _ => (),
    }
    Ok(())
}

#[inline(always)]
pub fn process_summary_data(
    db_ctx: &mut DataBaseCtx,
    rec_tracker: &mut RecordTracker,
) -> Result<(), StdfHelperError> {
    // write HBR
    for (&(file_id, bin_num), (bin_nam, bin_pf)) in rec_tracker.hbin_tracker.iter() {
        db_ctx.insert_hbin(rusqlite::params![
            file_id,
            bin_num,
            bin_nam,
            &bin_pf.to_string()
        ])?;
    }
    // write SBR
    for (&(file_id, bin_num), (bin_nam, bin_pf)) in rec_tracker.sbin_tracker.iter() {
        db_ctx.insert_sbin(rusqlite::params![
            file_id,
            bin_num,
            bin_nam,
            &bin_pf.to_string()
        ])?;
    }
    // write TSR
    for (&test_id, &fail_cnt) in rec_tracker.test_fail_count.iter() {
        if let Err(e) = db_ctx.update_fail_count(rusqlite::params![fail_cnt, test_id,]) {
            // we don't really care about errors when saving TSR's failcount
            // because it can be parsed in python
            println!("Sqlite3 error when saving TSR fail counts: {}", e.msg);
        }
    }
    Ok(())
}
// database related functions

#[inline(always)]
pub fn u32_to_localtime(timestamp: u32) -> String {
    // convert u32 timestamp to native datetime (without timezone info)
    let utc_native = NaiveDateTime::from_timestamp(timestamp as i64, 0);
    // treat the native datetime as if in UTC, converts to UTC datetime
    let utc_time = Utc.from_local_datetime(&utc_native).unwrap();
    // convert UTC datetime to Local datetime
    let local_time: DateTime<Local> = DateTime::from(utc_time);
    format!("{}", local_time.format("%Y-%m-%d %H:%M:%S"))
}

#[inline(always)]
fn on_far_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    subfile_id: usize,
    order: ByteOrder,
    far_rec: FAR,
) -> Result<(), StdfHelperError> {
    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        subfile_id,
        "STDF Version",
        far_rec.stdf_ver.to_string()
    ])?;
    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        subfile_id,
        "BYTE_ORD",
        if order == ByteOrder::LittleEndian {
            "Little endian"
        } else {
            "Big endian"
        }
    ])?;
    Ok(())
}

#[inline(always)]
fn on_vur_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    subfile_id: usize,
    vur_rec: VUR,
) -> Result<(), StdfHelperError> {
    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        subfile_id,
        "STDF Version",
        vur_rec.upd_nam
    ])?;
    Ok(())
}

#[inline(always)]
fn on_atr_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    subfile_id: usize,
    atr_rec: ATR,
) -> Result<(), StdfHelperError> {
    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        subfile_id,
        "File Modification",
        format!(
            "Time: {}\nCMD: {}",
            u32_to_localtime(atr_rec.mod_tim),
            atr_rec.cmd_line
        )
    ])?;
    Ok(())
}

#[inline(always)]
fn on_mir_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    subfile_id: usize,
    mir_rec: MIR,
) -> Result<(), StdfHelperError> {
    // update File_List table
    db_ctx.update_file_list(rusqlite::params![
        &mir_rec.lot_id,
        &mir_rec.sblot_id,
        &mir_rec.proc_id,
        &mir_rec.flow_id,
        file_id,
        subfile_id
    ])?;
    // update File_Info table
    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        subfile_id,
        "SETUP_T",
        u32_to_localtime(mir_rec.setup_t)
    ])?;

    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        subfile_id,
        "START_T",
        u32_to_localtime(mir_rec.start_t)
    ])?;

    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        subfile_id,
        "STAT_NUM",
        format!("{}", mir_rec.stat_num)
    ])?;

    if mir_rec.mode_cod != ' ' {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "MODE_COD",
            format!("{}", mir_rec.mode_cod)
        ])?
    };

    if mir_rec.rtst_cod != ' ' {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "RTST_COD",
            format!("{}", mir_rec.rtst_cod)
        ])?
    };

    if mir_rec.prot_cod != ' ' {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "PROT_COD",
            format!("{}", mir_rec.prot_cod)
        ])?
    };

    if mir_rec.burn_tim != 65535 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "BURN_TIM",
            format!("{}", mir_rec.burn_tim)
        ])?
    };

    if mir_rec.cmod_cod != ' ' {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "CMOD_COD",
            format!("{}", mir_rec.cmod_cod)
        ])?
    };

    if !mir_rec.lot_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "LOT_ID",
            &mir_rec.lot_id
        ])?
    };

    if !mir_rec.part_typ.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "PART_TYP",
            &mir_rec.part_typ
        ])?
    };

    if !mir_rec.node_nam.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "NODE_NAM",
            &mir_rec.node_nam,
        ])?
    };

    if !mir_rec.tstr_typ.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "TSTR_TYP",
            &mir_rec.tstr_typ
        ])?
    };

    if !mir_rec.job_nam.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "JOB_NAM",
            &mir_rec.job_nam
        ])?
    };

    if !mir_rec.job_rev.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "JOB_REV",
            &mir_rec.job_rev
        ])?
    };

    if !mir_rec.sblot_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "SBLOT_ID",
            &mir_rec.sblot_id
        ])?
    };

    if !mir_rec.oper_nam.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "OPER_NAM",
            &mir_rec.oper_nam
        ])?
    };

    if !mir_rec.exec_typ.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "EXEC_TYP",
            &mir_rec.exec_typ
        ])?
    };

    if !mir_rec.exec_ver.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "EXEC_VER",
            &mir_rec.exec_ver
        ])?
    };

    if !mir_rec.test_cod.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "TEST_COD",
            &mir_rec.test_cod
        ])?
    };

    if !mir_rec.tst_temp.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "TST_TEMP",
            &mir_rec.tst_temp
        ])?
    };

    if !mir_rec.user_txt.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "USER_TXT",
            &mir_rec.user_txt
        ])?
    };

    if !mir_rec.aux_file.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "AUX_FILE",
            &mir_rec.aux_file
        ])?
    };

    if !mir_rec.pkg_typ.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "PKG_TYP",
            &mir_rec.pkg_typ
        ])?
    };

    if !mir_rec.famly_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "FAMLY_ID",
            &mir_rec.famly_id
        ])?
    };

    if !mir_rec.date_cod.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "DATE_COD",
            &mir_rec.date_cod
        ])?
    };

    if !mir_rec.facil_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "FACIL_ID",
            &mir_rec.facil_id
        ])?
    };

    if !mir_rec.floor_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "FLOOR_ID",
            &mir_rec.floor_id
        ])?
    };

    if !mir_rec.proc_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "PROC_ID",
            &mir_rec.proc_id
        ])?
    };

    if !mir_rec.oper_frq.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "OPER_FRQ",
            &mir_rec.oper_frq
        ])?
    };

    if !mir_rec.spec_nam.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "SPEC_NAM",
            &mir_rec.spec_nam
        ])?
    };

    if !mir_rec.spec_ver.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "SPEC_VER",
            &mir_rec.spec_ver
        ])?
    };

    if !mir_rec.flow_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "FLOW_ID",
            &mir_rec.flow_id
        ])?
    };

    if !mir_rec.setup_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "SETUP_ID",
            &mir_rec.setup_id
        ])?
    };

    if !mir_rec.dsgn_rev.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "DSGN_REV",
            &mir_rec.dsgn_rev
        ])?
    };

    if !mir_rec.eng_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "ENG_ID",
            &mir_rec.eng_id
        ])?
    };

    if !mir_rec.rom_cod.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "ROM_COD",
            &mir_rec.rom_cod
        ])?
    };

    if !mir_rec.serl_num.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "SERL_NUM",
            &mir_rec.serl_num
        ])?
    };

    if !mir_rec.supr_nam.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "SUPR_NAM",
            &mir_rec.supr_nam
        ])?
    };

    Ok(())
}

#[inline(always)]
fn on_pmr_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    pmr_rec: PMR,
) -> Result<(), StdfHelperError> {
    db_ctx.insert_pin_map(rusqlite::params![
        file_id,
        pmr_rec.head_num,
        pmr_rec.site_num,
        pmr_rec.pmr_indx,
        pmr_rec.chan_typ,
        if !pmr_rec.chan_nam.is_empty() {
            Some(pmr_rec.chan_nam)
        } else {
            None
        },
        if !pmr_rec.phy_nam.is_empty() {
            Some(pmr_rec.phy_nam)
        } else {
            None
        },
        if !pmr_rec.log_nam.is_empty() {
            Some(pmr_rec.log_nam)
        } else {
            None
        },
        // #8: From_GRP is intentionally unbinded,
        // it will be updated when PGR record shows up
        None::<u16>
    ])?;
    Ok(())
}

#[inline(always)]
fn on_pgr_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    pgr_rec: PGR,
) -> Result<(), StdfHelperError> {
    // create new data in Pin_Info
    if !pgr_rec.grp_nam.is_empty() {
        db_ctx.insert_grp_name(rusqlite::params![
            file_id,
            pgr_rec.grp_indx,
            pgr_rec.grp_nam
        ])?;
    }
    // update From_GRP colume in Pin_Map
    for pmr_id in pgr_rec.pmr_indx {
        db_ctx.update_from_grp(rusqlite::params![pgr_rec.grp_indx, file_id, pmr_id])?;
    }
    Ok(())
}

#[inline(always)]
fn on_plr_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    plr_rec: PLR,
) -> Result<(), StdfHelperError> {
    // file_id,
    for i in 0..plr_rec.grp_cnt {
        let i = i as usize;
        db_ctx.insert_pin_info(rusqlite::params![
            file_id,
            plr_rec.grp_indx[i],
            plr_rec.grp_mode[i],
            plr_rec.grp_radx[i],
            if !plr_rec.pgm_char[i].is_empty() {
                Some(plr_rec.pgm_char[i].clone())
            } else {
                None
            },
            if !plr_rec.pgm_chal[i].is_empty() {
                Some(plr_rec.pgm_chal[i].clone())
            } else {
                None
            },
            if !plr_rec.rtn_char[i].is_empty() {
                Some(plr_rec.rtn_char[i].clone())
            } else {
                None
            },
            if !plr_rec.rtn_chal[i].is_empty() {
                Some(plr_rec.rtn_chal[i].clone())
            } else {
                None
            },
        ])?;
    }
    Ok(())
}

#[inline(always)]
fn on_pir_rec(
    db_ctx: &mut DataBaseCtx,
    tracker: &mut RecordTracker,
    file_id: usize,
    pir_rec: PIR,
) -> Result<(), StdfHelperError> {
    // update tracker, get dut_index of current file_id
    let dut_index = tracker.pir_detected(file_id, pir_rec.head_num, pir_rec.site_num);
    db_ctx.insert_dut(rusqlite::params![
        file_id,
        pir_rec.head_num,
        pir_rec.site_num,
        dut_index,
    ])?;
    Ok(())
}

#[inline(always)]
fn on_ptr_rec(
    db_ctx: &mut DataBaseCtx,
    tracker: &mut RecordTracker,
    file_id: usize,
    ptr_rec: PTR,
) -> Result<(), StdfHelperError> {
    // get dut_index of (head, site)
    // get id map if existed
    let (dut_index, test_id) = tracker.xtr_detected(
        file_id,
        ptr_rec.head_num,
        ptr_rec.site_num,
        ptr_rec.test_num,
        &ptr_rec.test_txt,
    )?;
    // get or update result scale
    let (exist, scale) = tracker.update_scale(test_id, &ptr_rec.res_scal);
    // insert ptr result
    db_ctx.insert_ptr_data(rusqlite::params![
        dut_index,
        test_id,
        replace_inf(ptr_rec.result * 10f32.powi(scale)),
        ptr_rec.test_flg[0]
    ])?;

    if !exist {
        // indicates it is the 1st PTR, that we need to save the possible omitted fields
        // need to apply result scale to limits and units
        let lo_limit = scale_option_value(&ptr_rec.lo_limit, &ptr_rec.opt_flag, scale, 0x50);
        let hi_limit = scale_option_value(&ptr_rec.hi_limit, &ptr_rec.opt_flag, scale, 0xA0);
        let lo_spec = scale_option_value(&ptr_rec.lo_spec, &ptr_rec.opt_flag, scale, 0x04);
        let hi_spec = scale_option_value(&ptr_rec.hi_spec, &ptr_rec.opt_flag, scale, 0x08);
        let unit = scale_unit(&ptr_rec.units, scale);

        tracker.update_default_limits(test_id, lo_limit, hi_limit);
        db_ctx.insert_test_info(rusqlite::params![
            file_id,
            test_id,
            ptr_rec.test_num,
            10, // PTR sub code
            ptr_rec.test_txt,
            ptr_rec.res_scal,
            lo_limit,
            hi_limit,
            unit,
            ptr_rec.opt_flag.map(|f| f[0]),
            -1,          // fail cnt, default -1
            None::<u16>, // RTN_ICNT for FTR & MPR
            None::<u16>, // RSLT or PGM for MPR or FTR
            lo_spec,
            hi_spec,
            None::<String>,                       // VECT_NAM
            tracker.get_program_section(file_id), // SEQ_NAM
        ])?;
    }
    // if test id is presented in limit hashmap
    // check if the default limits have been changed
    else {
        // only when opt_flag is valid
        if let Some(opt_flag) = ptr_rec.opt_flag {
            // default limits are scaled, we need to scale current limits as well
            let lo_limit = scale_option_value(&ptr_rec.lo_limit, &ptr_rec.opt_flag, scale, 0x50);
            let hi_limit = scale_option_value(&ptr_rec.hi_limit, &ptr_rec.opt_flag, scale, 0xA0);

            let (llimit_changed, hlimit_changed) =
                tracker.is_ptr_limits_changed(test_id, lo_limit, hi_limit)?;

            let update_llimit = llimit_changed && (opt_flag[0] & 0x50 == 0);
            let update_hlimit = hlimit_changed && (opt_flag[0] & 0xA0 == 0);

            if update_llimit || update_hlimit {
                db_ctx.insert_dynamic_limit(rusqlite::params![
                    dut_index,
                    test_id,
                    if update_llimit { Some(lo_limit) } else { None },
                    if update_hlimit { Some(hi_limit) } else { None },
                ])?;
            }
        }
    }
    Ok(())
}

#[inline(always)]
fn on_mpr_rec(
    db_ctx: &mut DataBaseCtx,
    tracker: &mut RecordTracker,
    file_id: usize,
    mut mpr_rec: MPR,
) -> Result<(), StdfHelperError> {
    // get dut_index of (head, site)
    // get id map if existed
    let (dut_index, test_id) = tracker.xtr_detected(
        file_id,
        mpr_rec.head_num,
        mpr_rec.site_num,
        mpr_rec.test_num,
        &mpr_rec.test_txt,
    )?;
    let (exist, scale) = tracker.update_scale(test_id, &mpr_rec.res_scal);
    // scale MPR result array
    mpr_rec
        .rtn_rslt
        .iter_mut()
        .for_each(|x| *x = replace_inf(*x * 10f32.powi(scale)));
    // serialize result array and stat array using hex
    let rslt_hex = hex::encode_upper({
        unsafe {
            let u8ptr = std::mem::transmute::<*const _, *const u8>(mpr_rec.rtn_rslt.as_ptr());
            std::slice::from_raw_parts(u8ptr, mpr_rec.rtn_rslt.len() * 4)
        }
    });
    let stat_hex = hex::encode_upper(mpr_rec.rtn_stat);
    // insert mpr data
    db_ctx.insert_mpr_data(rusqlite::params![
        dut_index,
        test_id,
        rslt_hex,
        stat_hex,
        mpr_rec.test_flg[0]
    ])?;

    if !exist {
        // indicates it is the 1st PTR, that we need to save the possible omitted fields
        // scale limits
        let lo_limit = scale_option_value(&mpr_rec.lo_limit, &mpr_rec.opt_flag, scale, 0x50);
        let hi_limit = scale_option_value(&mpr_rec.hi_limit, &mpr_rec.opt_flag, scale, 0xA0);
        let lo_spec = scale_option_value(&mpr_rec.lo_spec, &mpr_rec.opt_flag, scale, 0x04);
        let hi_spec = scale_option_value(&mpr_rec.hi_spec, &mpr_rec.opt_flag, scale, 0x08);
        let unit = scale_unit(&mpr_rec.units, scale);

        db_ctx.insert_test_info(rusqlite::params![
            file_id,
            test_id,
            mpr_rec.test_num,
            15, // MPR sub code
            mpr_rec.test_txt,
            mpr_rec.res_scal,
            lo_limit,
            hi_limit,
            unit, // unit
            mpr_rec.opt_flag.map(|f| f[0]),
            -1,               // fail cnt, default -1
            mpr_rec.rtn_icnt, // RTN_ICNT for FTR & MPR
            mpr_rec.rslt_cnt, // RSLT for MPR, or PGM for FTR
            lo_spec,
            hi_spec,
            None::<String>,                       // VECT_NAM
            tracker.get_program_section(file_id), // SEQ_NAM
        ])?;

        // For MPR, store PMR indexes here
        if mpr_rec.rtn_icnt > 0 && mpr_rec.rtn_indx.is_some() {
            for rtn_indx in mpr_rec.rtn_indx.unwrap() {
                db_ctx.insert_test_pin(rusqlite::params![test_id, rtn_indx, "RTN"])?;
            }
        }
    }
    Ok(())
}

#[inline(always)]
fn on_ftr_rec(
    db_ctx: &mut DataBaseCtx,
    tracker: &mut RecordTracker,
    file_id: usize,
    ftr_rec: FTR,
) -> Result<(), StdfHelperError> {
    // get dut_index of (head, site)
    // get id map if existed
    let (dut_index, test_id) = tracker.xtr_detected(
        file_id,
        ftr_rec.head_num,
        ftr_rec.site_num,
        ftr_rec.test_num,
        &ftr_rec.test_txt,
    )?;
    // insert ftr test flag
    db_ctx.insert_ftr_data(rusqlite::params![dut_index, test_id, ftr_rec.test_flg[0]])?;

    // FTR doesn't have result scale, but we can still use this hashmap to check
    // if this test id has been saved, to avoid duplicate rows in the sqlite3 database
    // get or update result scale
    let (exist, _) = tracker.update_scale(test_id, &Some(0));
    if !exist {
        // indicates it is the 1st PTR, that we need to save the possible omitted fields
        db_ctx.insert_test_info(rusqlite::params![
            file_id,
            test_id,
            ftr_rec.test_num,
            20, // FTR sub code
            ftr_rec.test_txt,
            None::<i8>,
            f32::NAN,
            f32::NAN,
            "", // unit
            ftr_rec.opt_flag[0],
            -1,               // fail cnt, default -1
            ftr_rec.rtn_icnt, // RTN_ICNT for FTR & MPR
            ftr_rec.pgm_icnt, // RSLT for MPR, or PGM for FTR
            f32::NAN,
            f32::NAN,
            ftr_rec.vect_nam,                     // VECT_NAM
            tracker.get_program_section(file_id), // SEQ_NAM
        ])?;

        // For FTR & MPR, store PMR indexes here
        if ftr_rec.rtn_icnt > 0 {
            for rtn_indx in ftr_rec.rtn_indx {
                db_ctx.insert_test_pin(rusqlite::params![test_id, rtn_indx, "RTN"])?;
            }
        }
        if ftr_rec.pgm_icnt > 0 {
            for pgm_indx in ftr_rec.pgm_indx {
                db_ctx.insert_test_pin(rusqlite::params![test_id, pgm_indx, "PGM"])?;
            }
        }
    }
    Ok(())
}

#[inline(always)]
fn on_prr_rec(
    db_ctx: &mut DataBaseCtx,
    tracker: &mut RecordTracker,
    file_id: usize,
    prr_rec: PRR,
) -> Result<(), StdfHelperError> {
    // in PRR, all BPS should be closed by EPS
    // set is_before_PRR to false
    // infer HBIN/SBIN types, it is helpful
    // when file missing HBR/SBR
    //
    // get dut_index
    // get wafer_index if WIR is detected
    let (dut_index, wafer_index) = tracker.prr_detected(file_id, &prr_rec)?;
    let part_flg = prr_rec.part_flg[0];
    let x_coord = match prr_rec.x_coord != -32768 {
        // use NULL to replace -32768
        true => Some(prr_rec.x_coord), // in order to reduce db size
        false => None,
    };
    let y_coord = match prr_rec.y_coord != -32768 {
        true => Some(prr_rec.y_coord),
        false => None,
    };

    // check if current dut supersedes previous duts
    // must do it before updating current PRR
    // otherwise current dut will be marked as superseded as well
    let supersede_dut = part_flg & 1u8 == 1u8;
    let supersede_die = part_flg & 2u8 == 2u8;
    if supersede_dut {
        // set previous dut with same fid, head, site and part_id as superseded
        db_ctx.update_supersede_dut(rusqlite::params![
            file_id,
            prr_rec.head_num,
            prr_rec.site_num,
            prr_rec.part_id,
        ])?;
    }
    if supersede_die {
        // set previous dut with same fid, head, site, wafer_index, x and y as superseded
        db_ctx.update_supersede_die(rusqlite::params![
            file_id,
            prr_rec.head_num,
            prr_rec.site_num,
            wafer_index,
            x_coord,
            y_coord
        ])?;
    }

    // update PRR info to database
    //
    // `supersede` status may have been
    // set to 1 by code above, we need
    // to set it back to 0
    db_ctx.update_dut(rusqlite::params![
        prr_rec.num_test,
        prr_rec.test_t,
        prr_rec.part_id,
        prr_rec.hard_bin,
        prr_rec.soft_bin,
        prr_rec.part_flg[0],
        wafer_index,
        x_coord,
        y_coord,
        0,
        file_id,
        dut_index
    ])?;
    Ok(())
}

#[inline(always)]
fn on_hbr_rec(
    tracker: &mut RecordTracker,
    file_id: usize,
    hbr_rec: HBR,
) -> Result<(), StdfHelperError> {
    // we do not update database in HBR
    // modify hashmap in memory instead
    tracker.hbr_detected(file_id, &hbr_rec);
    Ok(())
}

#[inline(always)]
fn on_sbr_rec(
    tracker: &mut RecordTracker,
    file_id: usize,
    sbr_rec: SBR,
) -> Result<(), StdfHelperError> {
    // we do not update database in SBR
    // modify hashmap in memory instead
    tracker.sbr_detected(file_id, &sbr_rec);
    Ok(())
}

#[inline(always)]
fn on_wcr_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    subfile_id: usize,
    wcr_rec: WCR,
) -> Result<(), StdfHelperError> {
    if wcr_rec.wafr_siz != 0.0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "WAFR_SIZ",
            format!("{}", wcr_rec.wafr_siz)
        ])?;
    };

    if wcr_rec.die_ht != 0.0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "DIE_HT",
            format!("{}", wcr_rec.die_ht)
        ])?;
    };

    if wcr_rec.die_wid != 0.0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "DIE_WID",
            format!("{}", wcr_rec.die_wid)
        ])?;
    };

    if wcr_rec.wf_units != 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "WF_UNITS",
            match wcr_rec.wf_units {
                1 => "inch",
                2 => "cm",
                3 => "mm",
                _ => "mil",
            }
        ])?;
    };

    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        subfile_id,
        "WF_FLAT",
        format!("{}", wcr_rec.wf_flat),
    ])?;

    if wcr_rec.center_x != -32768 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "CENTER_X",
            format!("{}", wcr_rec.center_x)
        ])?;
    };

    if wcr_rec.center_y != -32768 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "CENTER_Y",
            format!("{}", wcr_rec.center_y)
        ])?;
    };

    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        subfile_id,
        "POS_X",
        format!("{}", wcr_rec.pos_x)
    ])?;

    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        subfile_id,
        "POS_Y",
        format!("{}", wcr_rec.pos_y)
    ])?;

    Ok(())
}

#[inline(always)]
fn on_wir_rec(
    db_ctx: &mut DataBaseCtx,
    tracker: &mut RecordTracker,
    file_id: usize,
    wir_rec: WIR,
) -> Result<(), StdfHelperError> {
    // get wafer_index from tracker
    let wafer_index = tracker.wir_detected(file_id, wir_rec.head_num);

    // the following info is also available in WRR, but it still should be updated
    // in WIR in case the stdf is incomplete (no WRR).
    db_ctx.insert_wafer(rusqlite::params![
        file_id,
        wir_rec.head_num,
        wafer_index,
        None::<u32>,
        None::<u32>,
        None::<u32>,
        None::<u32>,
        None::<u32>,
        wir_rec.wafer_id,
        None::<String>,
        None::<String>,
        None::<String>,
        None::<String>,
        None::<String>,
    ])?;
    Ok(())
}

#[inline(always)]
fn on_wrr_rec(
    db_ctx: &mut DataBaseCtx,
    tracker: &mut RecordTracker,
    file_id: usize,
    wrr_rec: WRR,
) -> Result<(), StdfHelperError> {
    // get wafer_index from tracker
    let wafer_index = tracker.get_wafer_index(file_id, wrr_rec.head_num)?;

    // the following info is also available in WRR, but it still should be updated
    // in WIR in case the stdf is incomplete (no WRR).
    db_ctx.insert_wafer(rusqlite::params![
        file_id,
        wrr_rec.head_num,
        wafer_index,
        wrr_rec.part_cnt,
        wrr_rec.rtst_cnt,
        wrr_rec.abrt_cnt,
        wrr_rec.good_cnt,
        wrr_rec.func_cnt,
        wrr_rec.wafer_id,
        wrr_rec.fabwf_id,
        wrr_rec.frame_id,
        wrr_rec.mask_id,
        wrr_rec.usr_desc,
        wrr_rec.exc_desc,
    ])?;
    Ok(())
}

#[inline(always)]
fn on_tsr_rec(
    tracker: &mut RecordTracker,
    file_id: usize,
    tsr_rec: TSR,
) -> Result<(), StdfHelperError> {
    // we only care TSR's fail cnt,
    // don't need to write in db now

    // users mentions that some factory
    // will assign multiple test_names to a single
    // test_num, this is why I used
    // test_id (test_num, test_name) as the identifier.
    //
    // however, the spec show test_num should be unique
    // and test_name can be different from that of PTR/FTR/MPR,
    // this will lead to a test_id key error in the following
    // function.
    //
    // in this case, I have to manually consume
    // this error for compatibility.
    if let Err(e) = tracker.tsr_detected(file_id, &tsr_rec) {
        println!("TSR warning: {}", e.msg);
    }
    Ok(())
}

#[inline(always)]
fn on_pcr_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    pcr_rec: PCR,
) -> Result<(), StdfHelperError> {
    db_ctx.insert_dut_cnt(rusqlite::params![
        file_id,
        pcr_rec.head_num,
        pcr_rec.site_num,
        pcr_rec.part_cnt,
        pcr_rec.rtst_cnt,
        pcr_rec.abrt_cnt,
        pcr_rec.good_cnt,
        pcr_rec.func_cnt,
    ])?;
    Ok(())
}

#[inline(always)]
fn on_dtr_rec(
    db_ctx: &mut DataBaseCtx,
    tracker: &mut RecordTracker,
    file_id: usize,
    dtr_rec: DTR,
) -> Result<(), StdfHelperError> {
    let (dut_index, is_before_prr) = tracker.get_datalog_relative_pos(file_id);

    db_ctx.insert_datalog_rec(rusqlite::params![
        file_id,
        "DTR",
        dtr_rec.text_dat,
        dut_index,
        is_before_prr,
    ])?;
    Ok(())
}

#[inline(always)]
fn on_gdr_rec(
    db_ctx: &mut DataBaseCtx,
    tracker: &mut RecordTracker,
    file_id: usize,
    gdr_rec: GDR,
) -> Result<(), StdfHelperError> {
    let (dut_index, is_before_prr) = tracker.get_datalog_relative_pos(file_id);
    let flatten_string = flatten_generic_data(&gdr_rec);

    db_ctx.insert_datalog_rec(rusqlite::params![
        file_id,
        "GDR",
        flatten_string,
        dut_index,
        is_before_prr,
    ])?;
    Ok(())
}

#[inline(always)]
fn on_bps_rec(
    tracker: &mut RecordTracker,
    file_id: usize,
    bps_rec: BPS,
) -> Result<(), StdfHelperError> {
    tracker.bps_detected(file_id, &bps_rec)?;
    Ok(())
}

#[inline(always)]
fn on_eps_rec(tracker: &mut RecordTracker, file_id: usize) -> Result<(), StdfHelperError> {
    tracker.eps_detected(file_id)?;
    Ok(())
}

#[inline(always)]
fn on_rdr_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    subfile_id: usize,
    rdr_rec: RDR,
) -> Result<(), StdfHelperError> {
    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        subfile_id,
        "Retest Hardware Bins",
        if rdr_rec.num_bins > 0 {
            rdr_rec
                .rtst_bin
                .iter()
                .map(|b| b.to_string())
                .collect::<Vec<_>>()
                .join(", ")
        } else {
            "All hardware bins are retested".to_string()
        }
    ])?;
    Ok(())
}

#[inline(always)]
fn on_sdr_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    subfile_id: usize,
    sdr_rec: SDR,
) -> Result<(), StdfHelperError> {
    if !sdr_rec.hand_typ.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Handler Type (Group {})", sdr_rec.site_grp),
            &sdr_rec.hand_typ,
        ])?;
    }

    if !sdr_rec.hand_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Handler ID (Group {})", sdr_rec.site_grp),
            &sdr_rec.hand_id,
        ])?;
    }

    if !sdr_rec.card_typ.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Probe Card Type (Group {})", sdr_rec.site_grp),
            &sdr_rec.card_typ,
        ])?;
    }

    if !sdr_rec.card_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Probe Card ID (Group {})", sdr_rec.site_grp),
            &sdr_rec.card_id,
        ])?;
    }

    if !sdr_rec.load_typ.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Load Board Type (Group {})", sdr_rec.site_grp),
            &sdr_rec.load_typ,
        ])?;
    }

    if !sdr_rec.load_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Load Board ID (Group {})", sdr_rec.site_grp),
            &sdr_rec.load_id,
        ])?;
    }

    if !sdr_rec.dib_typ.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("DIB Board Type (Group {})", sdr_rec.site_grp),
            &sdr_rec.dib_typ,
        ])?;
    }

    if !sdr_rec.dib_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("DIB Board ID (Group {})", sdr_rec.site_grp),
            &sdr_rec.dib_id,
        ])?;
    }

    if !sdr_rec.cabl_typ.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Interface Cable Type (Group {})", sdr_rec.site_grp),
            &sdr_rec.cabl_typ,
        ])?;
    }

    if !sdr_rec.cabl_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Interface Cable ID (Group {})", sdr_rec.site_grp),
            &sdr_rec.cabl_id,
        ])?;
    }

    if !sdr_rec.cont_typ.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Handler Contactor Type (Group {})", sdr_rec.site_grp),
            &sdr_rec.cont_typ,
        ])?;
    }

    if !sdr_rec.cont_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Handler Contactor ID (Group {})", sdr_rec.site_grp),
            &sdr_rec.cont_id,
        ])?;
    }

    if !sdr_rec.lasr_typ.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Laser Type (Group {})", sdr_rec.site_grp),
            &sdr_rec.lasr_typ,
        ])?;
    }

    if !sdr_rec.lasr_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Laser ID (Group {})", sdr_rec.site_grp),
            &sdr_rec.lasr_id,
        ])?;
    }

    if !sdr_rec.extr_typ.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Extra Equipment Type (Group {})", sdr_rec.site_grp),
            &sdr_rec.extr_typ,
        ])?;
    }

    if !sdr_rec.extr_id.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            format!("Extra Equipment ID (Group {})", sdr_rec.site_grp),
            &sdr_rec.extr_id,
        ])?;
    }
    Ok(())
}

#[inline(always)]
fn on_mrr_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    subfile_id: usize,
    mrr_rec: MRR,
) -> Result<(), StdfHelperError> {
    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        subfile_id,
        "FINISH_T",
        u32_to_localtime(mrr_rec.finish_t)
    ])?;

    if mrr_rec.disp_cod != ' ' {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "DISP_COD",
            &mrr_rec.disp_cod.to_string(),
        ])?;
    }

    if !mrr_rec.usr_desc.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "USR_DESC",
            &mrr_rec.usr_desc,
        ])?;
    }

    if !mrr_rec.exc_desc.is_empty() {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            subfile_id,
            "EXC_DESC",
            &mrr_rec.exc_desc,
        ])?;
    }
    Ok(())
}

#[inline(always)]
fn flatten_generic_data(gdr_rec: &GDR) -> String {
    let mut rslt = String::with_capacity(256);
    for (i, v1_data) in gdr_rec.gen_data.iter().enumerate() {
        match v1_data {
            V1::B0 => {
                rslt.push_str(&format!("{} B0: NULL\n", i));
            }
            V1::U1(v) => {
                rslt.push_str(&format!("{} U1: {}\n", i, v));
            }
            V1::U2(v) => {
                rslt.push_str(&format!("{} U2: {}\n", i, v));
            }
            V1::U4(v) => {
                rslt.push_str(&format!("{} U4: {}\n", i, v));
            }
            V1::I1(v) => {
                rslt.push_str(&format!("{} I1: {}\n", i, v));
            }
            V1::I2(v) => {
                rslt.push_str(&format!("{} I2: {}\n", i, v));
            }
            V1::I4(v) => {
                rslt.push_str(&format!("{} I4: {}\n", i, v));
            }
            V1::R4(v) => {
                rslt.push_str(&format!("{} R4: {}\n", i, v));
            }
            V1::R8(v) => {
                rslt.push_str(&format!("{} R8: {}\n", i, v));
            }
            V1::Cn(v) => {
                rslt.push_str(&format!("{} Cn: {}\n", i, v));
            }
            V1::Bn(v) => {
                rslt.push_str(&match v.len() {
                    0 => format!("{} Bn: NULL\n", i),
                    _ => format!("{} Bn: (HEX){}\n", i, hex::encode_upper(v)),
                });
            }
            V1::Dn(v) => {
                rslt.push_str(&match v.len() {
                    0 => format!("{} Dn: NULL\n", i),
                    _ => format!("{} Dn: (HEX){}\n", i, hex::encode_upper(v)),
                });
            }
            V1::N1(v) => {
                rslt.push_str(&format!("{} N1: {:X}\n", i, v));
            }
            V1::Invalid => (),
        };
    }
    // if there is no V1 data, use NULL
    if rslt.is_empty() {
        rslt.push_str("NULL");
    }
    rslt
}

#[inline(always)]
pub fn get_file_size(file_path: &str) -> io::Result<u64> {
    let mut fp = fs::File::open(file_path)?;
    if file_path.ends_with(".gz") {
        // gz file, read last 4 bytes as uncompressed data size
        // although it's inaccurate for > 4GB file, are there
        // anyone really going to open that large file using
        // my app? don't think so~
        fp.seek(SeekFrom::End(-4))?;
        let mut buffer = [0u8; 4];
        fp.read_exact(&mut buffer)?;
        Ok(u32::from_le_bytes(buffer).into())
    } else if file_path.ends_with(".zip") {
        let mut za = ZipArchive::new(fp)?;
        let fst_file = za.by_index(0)?;
        Ok(fst_file.size())
    } else {
        // binary file
        Ok(fp.metadata()?.len())
    }
}

#[inline(always)]
pub fn replace_inf(num: f32) -> f32 {
    if num.is_finite() {
        num
    } else if num < 0.0 {
        f32::MIN
    } else if num > 0.0 {
        f32::MAX
    } else {
        f32::NAN
    }
}

// stdf to excel converter function
#[inline(always)]
pub fn get_fields_from_code(type_code: u64) -> &'static [&'static str] {
    use stdf_record_type::*;
    match type_code {
        // rec type 15
        REC_PTR => rust_stdf::PTR::FIELD_NAMES_AS_ARRAY,
        REC_MPR => rust_stdf::MPR::FIELD_NAMES_AS_ARRAY,
        REC_FTR => rust_stdf::FTR::FIELD_NAMES_AS_ARRAY,
        REC_STR => rust_stdf::STR::FIELD_NAMES_AS_ARRAY,
        // rec type 5
        REC_PIR => rust_stdf::PIR::FIELD_NAMES_AS_ARRAY,
        REC_PRR => rust_stdf::PRR::FIELD_NAMES_AS_ARRAY,
        // rec type 2
        REC_WIR => rust_stdf::WIR::FIELD_NAMES_AS_ARRAY,
        REC_WRR => rust_stdf::WRR::FIELD_NAMES_AS_ARRAY,
        REC_WCR => rust_stdf::WCR::FIELD_NAMES_AS_ARRAY,
        // rec type 50
        REC_GDR => rust_stdf::GDR::FIELD_NAMES_AS_ARRAY,
        REC_DTR => rust_stdf::DTR::FIELD_NAMES_AS_ARRAY,
        // rec type 0
        REC_FAR => rust_stdf::FAR::FIELD_NAMES_AS_ARRAY,
        REC_ATR => rust_stdf::ATR::FIELD_NAMES_AS_ARRAY,
        REC_VUR => rust_stdf::VUR::FIELD_NAMES_AS_ARRAY,
        // rec type 1
        REC_MIR => rust_stdf::MIR::FIELD_NAMES_AS_ARRAY,
        REC_MRR => rust_stdf::MRR::FIELD_NAMES_AS_ARRAY,
        REC_PCR => rust_stdf::PCR::FIELD_NAMES_AS_ARRAY,
        REC_HBR => rust_stdf::HBR::FIELD_NAMES_AS_ARRAY,
        REC_SBR => rust_stdf::SBR::FIELD_NAMES_AS_ARRAY,
        REC_PMR => rust_stdf::PMR::FIELD_NAMES_AS_ARRAY,
        REC_PGR => rust_stdf::PGR::FIELD_NAMES_AS_ARRAY,
        REC_PLR => rust_stdf::PLR::FIELD_NAMES_AS_ARRAY,
        REC_RDR => rust_stdf::RDR::FIELD_NAMES_AS_ARRAY,
        REC_SDR => rust_stdf::SDR::FIELD_NAMES_AS_ARRAY,
        REC_PSR => rust_stdf::PSR::FIELD_NAMES_AS_ARRAY,
        REC_NMR => rust_stdf::NMR::FIELD_NAMES_AS_ARRAY,
        REC_CNR => rust_stdf::CNR::FIELD_NAMES_AS_ARRAY,
        REC_SSR => rust_stdf::SSR::FIELD_NAMES_AS_ARRAY,
        REC_CDR => rust_stdf::CDR::FIELD_NAMES_AS_ARRAY,
        // rec type 10
        REC_TSR => rust_stdf::TSR::FIELD_NAMES_AS_ARRAY,
        // rec type 20
        REC_BPS => rust_stdf::BPS::FIELD_NAMES_AS_ARRAY,
        REC_EPS => rust_stdf::EPS::FIELD_NAMES_AS_ARRAY,
        // rec type 180: Reserved
        // rec type 181: Reserved
        REC_RESERVE => rust_stdf::ReservedRec::FIELD_NAMES_AS_ARRAY,
        // not matched
        _ => &[""; 0],
    }
}

#[inline(always)]
pub fn write_json_to_sheet(
    json: serde_json::Value,
    field_names: &[&str],
    sheet: &mut Worksheet,
    row: u32,
) -> Result<(), XlsxError> {
    for (col, &field) in field_names.iter().enumerate() {
        let col = col as u16;
        let v = &json[field];
        match v {
            serde_json::Value::Number(n) => {
                sheet.write_number_only(row, col, n.as_f64().unwrap_or(f64::NAN))?
            }
            serde_json::Value::Null => sheet.write_string_only(row, col, "N/A")?,
            serde_json::Value::String(s) => sheet.write_string_only(row, col, s)?,
            _ => sheet.write_string_only(row, col, &v.to_string())?,
        };
    }
    Ok(())
}
