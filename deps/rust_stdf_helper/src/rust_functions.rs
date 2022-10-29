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
use std::collections::{HashMap, HashSet};

pub struct RecordTracker {
    // file id, test num, test name
    id_map: HashSet<(usize, u32, String)>,

    // file id, test num, test name -> low limit in 1st PTR
    default_llimit: HashMap<(usize, u32, String), f32>,
    // file id, test num, test name -> high limit in 1st PTR
    default_hlimit: HashMap<(usize, u32, String), f32>,

    // file id, test num, test name -> fail count
    test_fail_count: HashMap<(usize, u32, String), u32>,

    // file id, head, site -> dut index
    dut_index_tracker: HashMap<(usize, u8, u8), u64>,

    // file id, head -> wafer index
    wafer_index_tracker: HashMap<(usize, u8), u64>,

    // file id, pin index -> pin name
    pin_name_map: HashMap<u16, String>,

    // DTR/GDR location tracker, file id -> is_before_PRR?
    datalog_pos_tracker: HashMap<usize, bool>,

    // for counting
    // file id -> dut count
    dut_total: HashMap<usize, u64>,
    // file id -> wafer count
    wafer_total: HashMap<usize, u64>,
}

impl RecordTracker {
    pub fn new() -> Self {
        RecordTracker {
            id_map: HashSet::with_capacity(4096),
            default_llimit: HashMap::with_capacity(4096),
            default_hlimit: HashMap::with_capacity(4096),
            test_fail_count: HashMap::with_capacity(4096),
            dut_index_tracker: HashMap::with_capacity(128),
            wafer_index_tracker: HashMap::with_capacity(128),
            pin_name_map: HashMap::with_capacity(128),
            datalog_pos_tracker: HashMap::with_capacity(32),
            dut_total: HashMap::with_capacity(32),
            wafer_total: HashMap::with_capacity(32),
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
        // StdfRecord::PTR(ptr_rec) => ptr_rec.read_from_bytes(raw_data, order),
        // StdfRecord::MPR(mpr_rec) => mpr_rec.read_from_bytes(raw_data, order),
        // StdfRecord::FTR(ftr_rec) => ftr_rec.read_from_bytes(raw_data, order),
        // StdfRecord::STR(str_rec) => str_rec.read_from_bytes(raw_data, order),
        // // rec type 5
        // StdfRecord::PIR(pir_rec) => pir_rec.read_from_bytes(raw_data, order),
        // StdfRecord::PRR(prr_rec) => prr_rec.read_from_bytes(raw_data, order),
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
        // StdfRecord::HBR(hbr_rec) => hbr_rec.read_from_bytes(raw_data, order),
        // StdfRecord::SBR(sbr_rec) => sbr_rec.read_from_bytes(raw_data, order),
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
