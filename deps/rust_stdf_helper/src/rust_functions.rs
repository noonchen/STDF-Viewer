//
// rust_functions.rs
// Author: noonchen - chennoon233@foxmail.com
// Created Date: October 29th 2022
// -----
// Last Modified: Sun Oct 30 2022
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::{database_context::DataBaseCtx, StdfHelperError};
use chrono::{DateTime, Local, NaiveDateTime, TimeZone, Utc};
use rust_stdf::*;
use std::collections::HashMap;

pub struct RecordTracker {
    // file id, test num, test name -> unique test id (map size)
    id_map: HashMap<(usize, u32, String), usize>,

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

    // file id, pin index -> pin name
    // pin_name_map: HashMap<(usize, u16), String>,

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
            default_llimit: HashMap::with_capacity(1024),
            default_hlimit: HashMap::with_capacity(1024),
            test_fail_count: HashMap::with_capacity(1024),
            dut_index_tracker: HashMap::with_capacity(128),
            wafer_index_tracker: HashMap::with_capacity(128),
            hbin_tracker: HashMap::with_capacity(128),
            sbin_tracker: HashMap::with_capacity(1024),
            // pin_name_map: HashMap::with_capacity(128),
            datalog_pos_tracker: HashMap::with_capacity(32),
            program_sections: HashMap::with_capacity(32),
            dut_total: HashMap::with_capacity(32),
            wafer_total: HashMap::with_capacity(32),
        }
    }

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

    pub fn prr_detected(&mut self, file_id: usize, prr_rec: &PRR) -> Result<(u64, Option<u64>), StdfHelperError> {
        // in PRR, all BPS should be closed by EPS
        if let Some(pg_sec_list) = self.program_sections.get_mut(&file_id) {
            pg_sec_list.clear();
        };
        // set is_before_PRR to false
        self.datalog_pos_tracker.insert(file_id, false);
        // infer HBIN/SBIN types, it is helpful 
        // when file missing HBR/SBR
        // HBIN
        if !self.hbin_tracker.contains_key(&(file_id, prr_rec.hard_bin)) {
            let hbin_type = if prr_rec.part_flg[0] & 0b00011000 == 0 {
                'P'
            } else if prr_rec.part_flg[0] & 0b00010000 == 0 {
                'F'
            } else {
                'U'
            };
            self.hbin_tracker.insert(
                (file_id, prr_rec.hard_bin), 
                (String::new(), hbin_type));
        };
        // SBIN
        if !self.sbin_tracker.contains_key(&(file_id, prr_rec.soft_bin)) {
            let sbin_type = if prr_rec.part_flg[0] & 0b00011000 == 0 {
                'P'
            } else if prr_rec.part_flg[0] & 0b00010000 == 0 {
                'F'
            } else {
                'U'
            };
            self.sbin_tracker.insert(
                (file_id, prr_rec.soft_bin), 
                (String::new(), sbin_type));
        };
        // get dut_index
        let dut_index = match self.dut_index_tracker.get( &(file_id, prr_rec.head_num, prr_rec.site_num) ) {
            Some(stored_ind) => Ok(*stored_ind),
            // if dut_index is None, returns Err
            None => Err(StdfHelperError { msg: format!("STDF file structure error in File[{}]: PRR Head[{}] Site[{}] showed up before PIR", file_id, prr_rec.head_num, prr_rec.site_num) }),
        }?;
        // get wafer_index if WIR is detected
        let wafer_index = match self.wafer_index_tracker.get( &(file_id, prr_rec.head_num) ) {
            Some(ind) => Some(*ind),
            None => None
        };
        Ok((dut_index, wafer_index))
    }

    pub fn hbr_detected(&mut self, file_id: usize, hbr_rec: &HBR) {
        // since HBR is valid, we can drop the inferred info from PRR
        if let Some( (name, pf) ) = self.hbin_tracker.get_mut( &(file_id, hbr_rec.hbin_num) ) {
            // update name & Pass/Fail if exist
            if hbr_rec.hbin_nam.len() > 0 {
                *name = hbr_rec.hbin_nam.clone();
            };
            *pf = hbr_rec.hbin_pf;
        } else {
            // insert if not exist
            self.hbin_tracker.insert(
                (file_id, hbr_rec.hbin_num), 
                (hbr_rec.hbin_nam.clone(), hbr_rec.hbin_pf));
        }
    }

    pub fn sbr_detected(&mut self, file_id: usize, sbr_rec: &SBR) {
        // since HBR is valid, we can drop the inferred info from PRR
        if let Some( (name, pf) ) = self.sbin_tracker.get_mut( &(file_id, sbr_rec.sbin_num) ) {
            // update name & Pass/Fail if exist
            if sbr_rec.sbin_nam.len() > 0 {
                *name = sbr_rec.sbin_nam.clone();
            };
            *pf = sbr_rec.sbin_pf;
        } else {
            // insert if not exist
            self.sbin_tracker.insert(
                (file_id, sbr_rec.sbin_num), 
                (sbr_rec.sbin_nam.clone(), sbr_rec.sbin_pf));
        }
    }

    /// return (dut_index, test_id) for [PTR], [FTR], [MPR] or maybe [STR] in the future
    ///
    /// ## Error
    /// if request dut_index from (file_id, head, site) that never stored in `dut_index_tracker`
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
    pub fn update_default_limits(
        &mut self,
        test_id: usize,
        llimit: Option<f32>,
        hlimit: Option<f32>,
    ) -> bool {
        let llimit_exist = self.default_llimit.contains_key(&test_id);
        let hlimit_exist = self.default_hlimit.contains_key(&test_id);

        if !llimit_exist {
            // update llimit
            self.default_llimit
                .insert(test_id, llimit.unwrap_or_else(|| f32::NAN));
        }
        if !hlimit_exist {
            // update hlimit
            self.default_hlimit
                .insert(test_id, hlimit.unwrap_or_else(|| f32::NAN));
        }
        llimit_exist && hlimit_exist
    }

    /// return (llimit_changed, hlimit_changed) if [PTR] limits is differ from that of 1st PTR
    ///
    /// ## Error
    /// if no default limit can be found for test_id
    pub fn is_ptr_limits_changed(
        &self,
        test_id: usize,
        llimit: Option<f32>,
        hlimit: Option<f32>,
    ) -> Result<(bool, bool), StdfHelperError> {
        // llimit
        let llimit_changed = llimit.is_some()
            && match self.default_llimit.get(&test_id) {
                Some(dft_ll) => {
                    // unwrap is safe here, since we have a is_some() precondition
                    // when the float number difference > epsilon, means limit changed
                    Ok((llimit.unwrap() - *dft_ll).abs() > f32::EPSILON)
                }
                None => Err(StdfHelperError {
                    msg: format!("Default low limit can not be read...this should never happen"),
                }),
            }?;
        // hlimit
        let hlimit_changed = hlimit.is_some()
            && match self.default_hlimit.get(&test_id) {
                Some(dft_hl) => Ok((hlimit.unwrap() - *dft_hl).abs() > f32::EPSILON),
                None => Err(StdfHelperError {
                    msg: format!("Default high limit can not be read...this should never happen"),
                }),
            }?;
        Ok((llimit_changed, hlimit_changed))
    }

    pub fn get_program_section(&self, file_id: usize) -> Option<String> {
        if let Some(pg_sec_list) = self.program_sections.get(&file_id) {
            // use `;` to join all sections
            Some(pg_sec_list.join(";"))
        } else {
            None
        }
    }
}

#[inline(always)]
pub fn process_incoming_record(
    db_ctx: &mut DataBaseCtx,
    rec_tracker: &mut RecordTracker,
    rec_info: (usize, ByteOrder, u64, usize, StdfRecord),
) -> Result<(), StdfHelperError> {
    // unpack info
    let (file_id, order, offset, data_len, rec) = rec_info;
    match rec {
        // // rec type 15
        StdfRecord::PTR(ptr_rec) => {
            on_ptr_rec(db_ctx, rec_tracker, file_id, offset, data_len, ptr_rec)?
        }
        StdfRecord::MPR(mpr_rec) => {
            on_mpr_rec(db_ctx, rec_tracker, file_id, offset, data_len, mpr_rec)?
        }
        StdfRecord::FTR(ftr_rec) => {
            on_ftr_rec(db_ctx, rec_tracker, file_id, offset, data_len, ftr_rec)?
        }
        // StdfRecord::STR(str_rec) => str_rec.read_from_bytes(raw_data, order),
        // // rec type 5
        StdfRecord::PIR(pir_rec) => on_pir_rec(db_ctx, rec_tracker, file_id, pir_rec)?,
        StdfRecord::PRR(prr_rec) => on_prr_rec(db_ctx, rec_tracker, file_id, prr_rec)?,
        // // rec type 2
        // StdfRecord::WIR(wir_rec) => wir_rec.read_from_bytes(raw_data, order),
        // StdfRecord::WRR(wrr_rec) => wrr_rec.read_from_bytes(raw_data, order),
        // StdfRecord::WCR(wcr_rec) => wcr_rec.read_from_bytes(raw_data, order),
        // // rec type 50
        // StdfRecord::GDR(gdr_rec) => gdr_rec.read_from_bytes(raw_data, order),
        // StdfRecord::DTR(dtr_rec) => dtr_rec.read_from_bytes(raw_data, order),
        // // rec type 10
        // StdfRecord::TSR(tsr_rec) => tsr_rec.read_from_bytes(raw_data, order),
        // // rec type 1
        StdfRecord::MIR(mir_rec) => on_mir_rec(db_ctx, file_id, mir_rec)?,
        // StdfRecord::MRR(mrr_rec) => mrr_rec.read_from_bytes(raw_data, order),
        // StdfRecord::PCR(pcr_rec) => pcr_rec.read_from_bytes(raw_data, order),
        StdfRecord::HBR(hbr_rec) => on_hbr_rec(rec_tracker, file_id, hbr_rec)?,
        StdfRecord::SBR(sbr_rec) => on_sbr_rec(rec_tracker, file_id, sbr_rec)?,
        StdfRecord::PMR(pmr_rec) => on_pmr_rec(db_ctx, file_id, pmr_rec)?,
        StdfRecord::PGR(pgr_rec) => on_pgr_rec(db_ctx, file_id, pgr_rec)?,
        StdfRecord::PLR(plr_rec) => on_plr_rec(db_ctx, file_id, plr_rec)?,
        // StdfRecord::RDR(rdr_rec) => rdr_rec.read_from_bytes(raw_data, order),
        // StdfRecord::SDR(sdr_rec) => sdr_rec.read_from_bytes(raw_data, order),
        // // StdfRecord::PSR(psr_rec) => psr_rec,
        // // StdfRecord::NMR(nmr_rec) => nmr_rec,
        // // StdfRecord::CNR(cnr_rec) => cnr_rec,
        // // StdfRecord::SSR(ssr_rec) => ssr_rec,
        // // StdfRecord::CDR(cdr_rec) => cdr_rec,
        // // rec type 0
        StdfRecord::FAR(far_rec) => on_far_rec(db_ctx, file_id, order, far_rec)?,
        StdfRecord::ATR(atr_rec) => on_atr_rec(db_ctx, file_id, atr_rec)?,
        StdfRecord::VUR(vur_rec) => on_vur_rec(db_ctx, file_id, vur_rec)?,
        // // rec type 20
        // StdfRecord::BPS(bps_rec) => bps_rec.read_from_bytes(raw_data, order),
        // StdfRecord::EPS(eps_rec) => eps_rec.read_from_bytes(raw_data, order),
        // rec type 180: Reserved
        // rec type 181: Reserved
        // not matched
        _ => (),
    }
    Ok(())
}

// database related functions

#[inline(always)]
fn u32_to_localtime(timestamp: u32) -> String {
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
    order: ByteOrder,
    far_rec: FAR,
) -> Result<(), StdfHelperError> {
    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        "STDF Version",
        far_rec.stdf_ver.to_string()
    ])?;
    db_ctx.insert_file_info(rusqlite::params![
        file_id,
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
    vur_rec: VUR,
) -> Result<(), StdfHelperError> {
    db_ctx.insert_file_info(rusqlite::params![file_id, "STDF Version", vur_rec.upd_nam])?;
    Ok(())
}

#[inline(always)]
fn on_atr_rec(
    db_ctx: &mut DataBaseCtx,
    file_id: usize,
    atr_rec: ATR,
) -> Result<(), StdfHelperError> {
    db_ctx.insert_file_info(rusqlite::params![
        file_id,
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
    mir_rec: MIR,
) -> Result<(), StdfHelperError> {
    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        "SETUP_T",
        u32_to_localtime(mir_rec.setup_t)
    ])?;

    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        "START_T",
        u32_to_localtime(mir_rec.start_t)
    ])?;

    db_ctx.insert_file_info(rusqlite::params![
        file_id,
        "STAT_NUM",
        format!("{}", mir_rec.stat_num)
    ])?;

    if mir_rec.mode_cod != ' ' {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "MODE_COD",
            format!("{}", mir_rec.mode_cod)
        ])?
    };

    if mir_rec.rtst_cod != ' ' {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "RTST_COD",
            format!("{}", mir_rec.rtst_cod)
        ])?
    };

    if mir_rec.prot_cod != ' ' {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "PROT_COD",
            format!("{}", mir_rec.prot_cod)
        ])?
    };

    if mir_rec.burn_tim != 65535 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "BURN_TIM",
            format!("{}", mir_rec.burn_tim)
        ])?
    };

    if mir_rec.cmod_cod != ' ' {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "CMOD_COD",
            format!("{}", mir_rec.cmod_cod)
        ])?
    };
    //TODO
    if mir_rec.lot_id.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "LOT_ID",
            format!("{}", mir_rec.lot_id)
        ])?
    };

    if mir_rec.part_typ.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "PART_TYP",
            format!("{}", mir_rec.part_typ)
        ])?
    };

    if mir_rec.node_nam.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "NODE_NAM",
            format!("{}", mir_rec.node_nam)
        ])?
    };

    if mir_rec.tstr_typ.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "TSTR_TYP",
            format!("{}", mir_rec.tstr_typ)
        ])?
    };

    if mir_rec.job_nam.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "JOB_NAM",
            format!("{}", mir_rec.job_nam)
        ])?
    };

    if mir_rec.job_rev.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "JOB_REV",
            format!("{}", mir_rec.job_rev)
        ])?
    };
    //TODO
    if mir_rec.sblot_id.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "SBLOT_ID",
            format!("{}", mir_rec.sblot_id)
        ])?
    };

    if mir_rec.oper_nam.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "OPER_NAM",
            format!("{}", mir_rec.oper_nam)
        ])?
    };

    if mir_rec.exec_typ.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "EXEC_TYP",
            format!("{}", mir_rec.exec_typ)
        ])?
    };

    if mir_rec.exec_ver.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "EXEC_VER",
            format!("{}", mir_rec.exec_ver)
        ])?
    };

    if mir_rec.test_cod.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "TEST_COD",
            format!("{}", mir_rec.test_cod)
        ])?
    };

    if mir_rec.tst_temp.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "TST_TEMP",
            format!("{}", mir_rec.tst_temp)
        ])?
    };

    if mir_rec.user_txt.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "USER_TXT",
            format!("{}", mir_rec.user_txt)
        ])?
    };

    if mir_rec.aux_file.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "AUX_FILE",
            format!("{}", mir_rec.aux_file)
        ])?
    };

    if mir_rec.pkg_typ.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "PKG_TYP",
            format!("{}", mir_rec.pkg_typ)
        ])?
    };

    if mir_rec.famly_id.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "FAMLY_ID",
            format!("{}", mir_rec.famly_id)
        ])?
    };

    if mir_rec.date_cod.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "DATE_COD",
            format!("{}", mir_rec.date_cod)
        ])?
    };

    if mir_rec.facil_id.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "FACIL_ID",
            format!("{}", mir_rec.facil_id)
        ])?
    };

    if mir_rec.floor_id.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "FLOOR_ID",
            format!("{}", mir_rec.floor_id)
        ])?
    };

    if mir_rec.proc_id.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "PROC_ID",
            format!("{}", mir_rec.proc_id)
        ])?
    };

    if mir_rec.oper_frq.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "OPER_FRQ",
            format!("{}", mir_rec.oper_frq)
        ])?
    };

    if mir_rec.spec_nam.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "SPEC_NAM",
            format!("{}", mir_rec.spec_nam)
        ])?
    };

    if mir_rec.spec_ver.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "SPEC_VER",
            format!("{}", mir_rec.spec_ver)
        ])?
    };
    //TODO
    if mir_rec.flow_id.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "FLOW_ID",
            format!("{}", mir_rec.flow_id)
        ])?
    };

    if mir_rec.setup_id.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "SETUP_ID",
            format!("{}", mir_rec.setup_id)
        ])?
    };

    if mir_rec.dsgn_rev.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "DSGN_REV",
            format!("{}", mir_rec.dsgn_rev)
        ])?
    };

    if mir_rec.eng_id.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "ENG_ID",
            format!("{}", mir_rec.eng_id)
        ])?
    };

    if mir_rec.rom_cod.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "ROM_COD",
            format!("{}", mir_rec.rom_cod)
        ])?
    };

    if mir_rec.serl_num.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "SERL_NUM",
            format!("{}", mir_rec.serl_num)
        ])?
    };

    if mir_rec.supr_nam.len() > 0 {
        db_ctx.insert_file_info(rusqlite::params![
            file_id,
            "SUPR_NAM",
            format!("{}", mir_rec.supr_nam)
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
        // file_id,
        pmr_rec.head_num,
        pmr_rec.site_num,
        pmr_rec.pmr_indx,
        pmr_rec.chan_typ,
        if pmr_rec.chan_nam.len() > 0 {
            Some(pmr_rec.chan_nam)
        } else {
            None
        },
        if pmr_rec.phy_nam.len() > 0 {
            Some(pmr_rec.phy_nam)
        } else {
            None
        },
        if pmr_rec.log_nam.len() > 0 {
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
    if pgr_rec.grp_nam.len() > 0 {
        db_ctx.insert_grp_name(rusqlite::params![pgr_rec.grp_indx, pgr_rec.grp_nam])?;
    }
    // update From_GRP colume in Pin_Map
    for pmr_id in pgr_rec.pmr_indx {
        db_ctx.update_from_grp(rusqlite::params![pgr_rec.grp_indx, pmr_id])?;
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
            plr_rec.grp_indx[i],
            plr_rec.grp_mode[i],
            plr_rec.grp_radx[i],
            if plr_rec.pgm_char[i].len() > 0 {
                Some(plr_rec.pgm_char[i].clone())
            } else {
                None
            },
            if plr_rec.pgm_chal[i].len() > 0 {
                Some(plr_rec.pgm_chal[i].clone())
            } else {
                None
            },
            if plr_rec.rtn_char[i].len() > 0 {
                Some(plr_rec.rtn_char[i].clone())
            } else {
                None
            },
            if plr_rec.rtn_chal[i].len() > 0 {
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
        pir_rec.head_num,
        pir_rec.site_num,
        dut_index
    ])?;
    Ok(())
}

#[inline(always)]
fn on_ptr_rec(
    db_ctx: &mut DataBaseCtx,
    tracker: &mut RecordTracker,
    file_id: usize,
    offset: u64,
    data_len: usize,
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
    // insert test offset
    db_ctx.insert_test_rec(rusqlite::params![dut_index, test_id, offset, data_len])?;

    // if test id is not presented in llimit/hlimit hashmap
    if !tracker.update_default_limits(test_id, ptr_rec.lo_limit, ptr_rec.hi_limit) {
        // indicates it is the 1st PTR, that we need to save the possible omitted fields
        db_ctx.insert_test_info(rusqlite::params![
            test_id,
            ptr_rec.test_num,
            10, // PTR sub code
            ptr_rec.test_txt,
            ptr_rec.res_scal,
            ptr_rec.lo_limit,
            ptr_rec.hi_limit,
            ptr_rec.units,
            match ptr_rec.opt_flag {
                Some(f) => Some(f[0]),
                None => None,
            },
            -1,          // fail cnt, default -1
            None::<u16>, // RTN_ICNT for FTR & MPR
            None::<u16>, // RSLT or PGM for MPR or FTR
            ptr_rec.lo_spec,
            ptr_rec.hi_spec,
            None::<String>,                       // VECT_NAM
            tracker.get_program_section(file_id), // SEQ_NAM
        ])?;
    }
    // if test id is presented in limit hashmap
    // check if the default limits have been changed
    else {
        // only when opt_flag is valid
        if let Some(opt_flag) = ptr_rec.opt_flag {
            let (llimit_changed, hlimit_changed) =
                tracker.is_ptr_limits_changed(test_id, ptr_rec.lo_limit, ptr_rec.hi_limit)?;

            let update_llimit =
                llimit_changed && (opt_flag[0] & 0x10 == 0) && (opt_flag[0] & 0x40 == 0);
            let update_hlimit =
                hlimit_changed && (opt_flag[0] & 0x20 == 0) && (opt_flag[0] & 0x80 == 0);

            if update_llimit || update_hlimit {
                db_ctx.insert_dynamic_limit(rusqlite::params![
                    dut_index,
                    test_id,
                    if update_llimit {
                        ptr_rec.lo_limit
                    } else {
                        None
                    },
                    if update_hlimit {
                        ptr_rec.hi_limit
                    } else {
                        None
                    },
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
    offset: u64,
    data_len: usize,
    mpr_rec: MPR,
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
    // insert test offset
    db_ctx.insert_test_rec(rusqlite::params![dut_index, test_id, offset, data_len])?;

    // FTR doesn't have high/low limit, but we can still use this hashmap to check
    // if this test id has been saved, to avoid duplicate rows in the sqlite3 database
    if !tracker.update_default_limits(test_id, Some(f32::NAN), Some(f32::NAN)) {
        // indicates it is the 1st PTR, that we need to save the possible omitted fields
        db_ctx.insert_test_info(rusqlite::params![
            test_id,
            mpr_rec.test_num,
            15, // MPR sub code
            mpr_rec.test_txt,
            mpr_rec.res_scal,
            mpr_rec.lo_limit,
            mpr_rec.hi_limit,
            mpr_rec.units, // unit
            match mpr_rec.opt_flag {
                Some(f) => Some(f[0]),
                None => None,
            },
            -1,               // fail cnt, default -1
            mpr_rec.rtn_icnt, // RTN_ICNT for FTR & MPR
            mpr_rec.rslt_cnt, // RSLT for MPR, or PGM for FTR
            mpr_rec.lo_spec,
            mpr_rec.hi_spec,
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
    offset: u64,
    data_len: usize,
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
    // insert test offset
    db_ctx.insert_test_rec(rusqlite::params![dut_index, test_id, offset, data_len])?;

    // FTR doesn't have high/low limit, but we can still use this hashmap to check
    // if this test id has been saved, to avoid duplicate rows in the sqlite3 database
    if !tracker.update_default_limits(test_id, Some(f32::NAN), Some(f32::NAN)) {
        // indicates it is the 1st PTR, that we need to save the possible omitted fields
        db_ctx.insert_test_info(rusqlite::params![
            test_id,
            ftr_rec.test_num,
            20, // FTR sub code
            ftr_rec.test_txt,
            None::<i8>,
            None::<f32>,
            None::<f32>,
            "", // unit
            ftr_rec.opt_flag,
            -1,               // fail cnt, default -1
            ftr_rec.rtn_icnt, // RTN_ICNT for FTR & MPR
            ftr_rec.pgm_icnt, // RSLT for MPR, or PGM for FTR
            None::<f32>,
            None::<f32>,
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
    // update PRR info to database, TODO: maybe use hashmap to avoid updating database?
    db_ctx.update_dut(rusqlite::params![
        prr_rec.num_test,
        prr_rec.test_t,
        prr_rec.part_id,
        prr_rec.hard_bin,
        prr_rec.soft_bin,
        prr_rec.part_flg[0],
        wafer_index,
        match prr_rec.x_coord != -32768 {   // use NULL to replace -32768
            true => Some(prr_rec.x_coord),  // in order to reduce db size
            false => None,
        },
        match prr_rec.y_coord != -32768 {
            true => Some(prr_rec.y_coord),
            false => None,
        },
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

