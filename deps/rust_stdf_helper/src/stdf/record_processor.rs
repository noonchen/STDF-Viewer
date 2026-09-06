//
// stdf/record_processor.rs
//
// Record processing for DB generation
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::database::operations::{push_cold_op, push_file_info, ColdOp, DbOp};
use crate::generic::helper::u32_to_localtime;
use crate::stdf::record_tracker::{RecordTracker, TestSubCode};
use crate::StdfHelperError;
use lazy_static::lazy_static;
use rust_stdf::*;
use std::collections::HashMap;

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

pub(crate) fn scale_unit(unit: &Option<String>, scale: i32) -> String {
    if let Some(u) = unit {
        format!("{}{}", UNIT_PREFIX.get(&scale).unwrap_or(&""), u)
    } else {
        String::new()
    }
}

#[inline(always)]
pub(crate) fn scale_option_value(
    value: &Option<f32>,
    flag: &Option<[u8; 1]>,
    scale: i32,
    mask: u8,
) -> f32 {
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

#[inline(always)]
pub(crate) fn flatten_generic_values(gen_data: &[V1]) -> String {
    let mut rslt = String::with_capacity(256);
    for (i, v1_data) in gen_data.iter().enumerate() {
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
                rslt.push_str(&match v.bit_data.len() {
                    0 => format!("{} Dn: NULL\n", i),
                    _ => format!("{} Dn: (HEX){}\n", i, hex::encode_upper(&v.bit_data)),
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

pub fn process_record_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    subfile_id: usize,
    order: ByteOrder,
    rec_view: StdfRecordView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    match rec_view {
        StdfRecordView::PTR(ptr) => on_ptr_view(tracker, file_id, ptr, ops),
        StdfRecordView::MPR(mpr) => on_mpr_view(tracker, file_id, mpr, ops),
        StdfRecordView::FTR(ftr) => on_ftr_view(tracker, file_id, ftr, ops),
        StdfRecordView::PIR(pir) => on_pir_view(tracker, file_id, pir, ops),
        StdfRecordView::PRR(prr) => on_prr_view(tracker, file_id, prr, ops),
        StdfRecordView::WIR(wir) => on_wir_view(tracker, file_id, wir, ops),
        StdfRecordView::WRR(wrr) => on_wrr_view(tracker, file_id, wrr, ops),
        StdfRecordView::WCR(wcr) => on_wcr_view(file_id, subfile_id, wcr, ops),
        StdfRecordView::GDR(gdr) => on_gdr_view(tracker, file_id, gdr, ops),
        StdfRecordView::DTR(dtr) => on_dtr_view(tracker, file_id, dtr, ops),
        StdfRecordView::TSR(tsr) => on_tsr_view(tracker, file_id, tsr),
        StdfRecordView::MIR(mir) => on_mir_view(file_id, subfile_id, mir, ops),
        StdfRecordView::MRR(mrr) => on_mrr_view(file_id, subfile_id, mrr, ops),
        StdfRecordView::PCR(pcr) => on_pcr_view(file_id, pcr, ops),
        StdfRecordView::HBR(hbr) => on_hbr_view(tracker, file_id, hbr),
        StdfRecordView::SBR(sbr) => on_sbr_view(tracker, file_id, sbr),
        StdfRecordView::PMR(pmr) => on_pmr_view(file_id, pmr, ops),
        StdfRecordView::PGR(pgr) => on_pgr_view(file_id, pgr, ops),
        StdfRecordView::PLR(plr) => on_plr_view(file_id, plr, ops),
        StdfRecordView::RDR(rdr) => on_rdr_view(file_id, subfile_id, rdr, ops),
        StdfRecordView::SDR(sdr) => on_sdr_view(file_id, subfile_id, sdr, ops),
        StdfRecordView::FAR(far) => on_far_view(file_id, subfile_id, order, far, ops),
        StdfRecordView::ATR(atr) => on_atr_view(file_id, subfile_id, atr, ops),
        StdfRecordView::VUR(vur) => on_vur_view(file_id, subfile_id, vur, ops),
        StdfRecordView::BPS(bps) => on_bps_view(tracker, file_id, bps),
        StdfRecordView::EPS => on_eps_view(tracker, file_id),
        StdfRecordView::UnknownRec(header) => Err(StdfHelperError {
            msg: format!(
                "Unknown record detected, typ: {}, sub: {}, len: {}",
                header.typ,
                header.sub,
                header.raw_data.len()
            ),
        }),
        StdfRecordView::ReservedRec(_) => Ok(()),
        // Unsupported record types are intentionally ignored, as before.
        _ => Ok(()),
    }
}

// ---------------------------------------------------------------------------
// Processor functions for each record view
// ---------------------------------------------------------------------------

#[inline]
fn on_ptr_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    ptr: PTRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    let test_num = ptr.test_num();
    let head_num = ptr.head_num();
    let site_num = ptr.site_num();
    let test_flg = ptr.test_flg();
    let result = ptr.result();
    let res_scal = ptr.res_scal();
    let opt_flag = ptr.opt_flag();

    // In TestNumberOnly mode the name getter is not even called for lookup.
    let test_name_storage;
    let test_name = if tracker.uses_test_name() {
        test_name_storage = ptr.test_txt().as_str();
        Some(test_name_storage.as_ref())
    } else {
        None
    };

    let (dut_index, test_id) =
        tracker.xtr_detected_optional(file_id, head_num, site_num, test_num, test_name)?;
    let (exist, scale) = tracker.update_scale(test_id, &res_scal);
    let lim_exist = tracker.default_limits_contains_id(test_id);

    ops.push(DbOp::Ptr {
        dut_index,
        test_id,
        result: result * 10f32.powi(scale),
        flag: test_flg[0],
    });

    if !exist || !lim_exist {
        // First PTR (or a scale-map/limit-map corner case): save the fields
        // that may have been omitted by later PTRs.
        let lo_limit = scale_option_value(&ptr.lo_limit(), &opt_flag, scale, 0x50);
        let hi_limit = scale_option_value(&ptr.hi_limit(), &opt_flag, scale, 0xA0);
        let lo_spec = scale_option_value(&ptr.lo_spec(), &opt_flag, scale, 0x04);
        let hi_spec = scale_option_value(&ptr.hi_spec(), &opt_flag, scale, 0x08);
        let unit = scale_unit(&ptr.units().map(|u| u.to_owned()), scale);

        tracker.update_default_limits(test_id, lo_limit, hi_limit);
        push_cold_op(
            ops,
            ColdOp::TestInfo {
                fid: file_id,
                test_id,
                test_num,
                sub_code: TestSubCode::Ptr,
                test_name: ptr.test_txt().to_owned(),
                res_scal,
                llimit: lo_limit,
                hlimit: hi_limit,
                unit,
                opt_flag: opt_flag.map(|f| f[0]),
                fail_cnt: -1,
                rtn_icnt: None,
                rslt_pgm_cnt: None,
                lspec: lo_spec,
                hspec: hi_spec,
                vect_nam: None,
                seq_name: tracker.get_program_section(file_id),
            },
        );
    } else if let Some(opt_flag) = opt_flag {
        // Check changed limits only when PTR carried an optional flag byte.
        let lo_limit = scale_option_value(&ptr.lo_limit(), &Some(opt_flag), scale, 0x50);
        let hi_limit = scale_option_value(&ptr.hi_limit(), &Some(opt_flag), scale, 0xA0);
        let (llimit_changed, hlimit_changed) =
            tracker.is_ptr_limits_changed(test_id, lo_limit, hi_limit)?;
        let update_llimit = llimit_changed && (opt_flag[0] & 0x50 == 0);
        let update_hlimit = hlimit_changed && (opt_flag[0] & 0xA0 == 0);

        if update_llimit || update_hlimit {
            push_cold_op(
                ops,
                ColdOp::DynamicLimit {
                    dut_index,
                    test_id,
                    llimit: if update_llimit { Some(lo_limit) } else { None },
                    hlimit: if update_hlimit { Some(hi_limit) } else { None },
                },
            );
        }
    }
    Ok(())
}

#[inline]
fn on_mpr_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    mpr: MPRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    let test_num = mpr.test_num();
    let head_num = mpr.head_num();
    let site_num = mpr.site_num();
    let test_flg = mpr.test_flg();
    let res_scal = mpr.res_scal();
    let opt_flag = mpr.opt_flag();

    let test_name_storage;
    let test_name = if tracker.uses_test_name() {
        test_name_storage = mpr.test_txt().as_str();
        Some(test_name_storage.as_ref())
    } else {
        None
    };

    let (dut_index, test_id) =
        tracker.xtr_detected_optional(file_id, head_num, site_num, test_num, test_name)?;
    let (exist, scale) = tracker.update_scale(test_id, &res_scal);

    let mut rtn_rslt = mpr.rtn_rslt();
    rtn_rslt.iter_mut().for_each(|x| *x *= 10f32.powi(scale));
    let rslt_hex = hex::encode_upper(unsafe {
        let u8ptr = std::mem::transmute::<*const _, *const u8>(rtn_rslt.as_ptr());
        std::slice::from_raw_parts(u8ptr, rtn_rslt.len() * 4)
    });
    let stat_hex = hex::encode_upper(mpr.rtn_stat());

    ops.push(DbOp::Mpr {
        dut_index,
        test_id,
        rslt_hex,
        stat_hex,
        flag: test_flg[0],
    });

    if !exist {
        let rtn_icnt = mpr.rtn_icnt();
        let rslt_cnt = mpr.rslt_cnt();
        let rtn_indx = mpr.rtn_indx();
        let lo_limit = scale_option_value(&mpr.lo_limit(), &opt_flag, scale, 0x50);
        let hi_limit = scale_option_value(&mpr.hi_limit(), &opt_flag, scale, 0xA0);
        let lo_spec = scale_option_value(&mpr.lo_spec(), &opt_flag, scale, 0x04);
        let hi_spec = scale_option_value(&mpr.hi_spec(), &opt_flag, scale, 0x08);
        let unit = scale_unit(&mpr.units().map(|u| u.to_owned()), scale);

        push_cold_op(
            ops,
            ColdOp::TestInfo {
                fid: file_id,
                test_id,
                test_num,
                sub_code: TestSubCode::Mpr,
                test_name: mpr.test_txt().to_owned(),
                res_scal,
                llimit: lo_limit,
                hlimit: hi_limit,
                unit,
                opt_flag: opt_flag.map(|f| f[0]),
                fail_cnt: -1,
                rtn_icnt: Some(rtn_icnt),
                rslt_pgm_cnt: Some(rslt_cnt),
                lspec: lo_spec,
                hspec: hi_spec,
                vect_nam: None,
                seq_name: tracker.get_program_section(file_id),
            },
        );

        if rtn_icnt > 0 {
            if let Some(rtn_indx) = rtn_indx {
                for rtn_indx in rtn_indx {
                    push_cold_op(
                        ops,
                        ColdOp::TestPin {
                            test_id,
                            pmr_indx: rtn_indx,
                            pin_type: "RTN",
                        },
                    );
                }
            }
        }
    }
    Ok(())
}

#[inline]
fn on_ftr_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    ftr: FTRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    let test_num = ftr.test_num();
    let head_num = ftr.head_num();
    let site_num = ftr.site_num();
    let test_flg = ftr.test_flg();

    let test_name_storage;
    let test_name = if tracker.uses_test_name() {
        test_name_storage = ftr.test_txt().as_str();
        Some(test_name_storage.as_ref())
    } else {
        None
    };

    let (dut_index, test_id) =
        tracker.xtr_detected_optional(file_id, head_num, site_num, test_num, test_name)?;
    let (exist, _) = tracker.update_scale(test_id, &Some(0));

    ops.push(DbOp::Ftr {
        dut_index,
        test_id,
        flag: test_flg[0],
    });

    if !exist {
        let rtn_icnt = ftr.rtn_icnt();
        let pgm_icnt = ftr.pgm_icnt();
        let rtn_indx = ftr.rtn_indx();
        let pgm_indx = ftr.pgm_indx();

        push_cold_op(
            ops,
            ColdOp::TestInfo {
                fid: file_id,
                test_id,
                test_num,
                sub_code: TestSubCode::Ftr,
                test_name: ftr.test_txt().to_owned(),
                res_scal: None,
                llimit: f32::NAN,
                hlimit: f32::NAN,
                unit: String::new(),
                opt_flag: Some(ftr.opt_flag()[0]),
                fail_cnt: -1,
                rtn_icnt: Some(rtn_icnt),
                rslt_pgm_cnt: Some(pgm_icnt),
                lspec: f32::NAN,
                hspec: f32::NAN,
                vect_nam: Some(ftr.vect_nam().to_owned()),
                seq_name: tracker.get_program_section(file_id),
            },
        );

        if rtn_icnt > 0 {
            for rtn_indx in rtn_indx {
                push_cold_op(
                    ops,
                    ColdOp::TestPin {
                        test_id,
                        pmr_indx: rtn_indx,
                        pin_type: "RTN",
                    },
                );
            }
        }
        if pgm_icnt > 0 {
            for pgm_indx in pgm_indx {
                push_cold_op(
                    ops,
                    ColdOp::TestPin {
                        test_id,
                        pmr_indx: pgm_indx,
                        pin_type: "PGM",
                    },
                );
            }
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Cold records: owned values, compact ops
// ---------------------------------------------------------------------------

#[inline(always)]
fn on_far_view(
    file_id: usize,
    subfile_id: usize,
    order: ByteOrder,
    far_rec: FARView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    push_file_info(
        ops,
        file_id,
        subfile_id,
        "STDF Version",
        far_rec.stdf_ver().to_string(),
    );
    push_file_info(
        ops,
        file_id,
        subfile_id,
        "BYTE_ORD",
        if order == ByteOrder::LittleEndian {
            "Little endian"
        } else {
            "Big endian"
        },
    );
    Ok(())
}

#[inline(always)]
fn on_vur_view(
    file_id: usize,
    subfile_id: usize,
    vur_rec: VURView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    push_file_info(
        ops,
        file_id,
        subfile_id,
        "STDF Version",
        vur_rec.upd_nam().to_owned(),
    );
    Ok(())
}

#[inline(always)]
fn on_atr_view(
    file_id: usize,
    subfile_id: usize,
    atr_rec: ATRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    push_file_info(
        ops,
        file_id,
        subfile_id,
        "File Modification",
        format!(
            "Time: {}\nCMD: {}",
            u32_to_localtime(atr_rec.mod_tim()),
            atr_rec.cmd_line().as_str()
        ),
    );
    Ok(())
}

#[inline(always)]
fn on_mir_view(
    file_id: usize,
    subfile_id: usize,
    mir_rec: MIRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    push_cold_op(
        ops,
        ColdOp::UpdateFileList {
            fid: file_id,
            sub_fid: subfile_id,
            lot_id: mir_rec.lot_id().to_owned(),
            sblot_id: mir_rec.sblot_id().to_owned(),
            proc_id: mir_rec.proc_id().to_owned(),
            flow_id: mir_rec.flow_id().to_owned(),
        },
    );

    push_file_info(
        ops,
        file_id,
        subfile_id,
        "SETUP_T",
        u32_to_localtime(mir_rec.setup_t()),
    );
    push_file_info(
        ops,
        file_id,
        subfile_id,
        "START_T",
        u32_to_localtime(mir_rec.start_t()),
    );
    push_file_info(
        ops,
        file_id,
        subfile_id,
        "STAT_NUM",
        format!("{}", mir_rec.stat_num()),
    );

    if mir_rec.mode_cod() != ' ' {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "MODE_COD",
            format!("{}", mir_rec.mode_cod()),
        );
    }
    if mir_rec.rtst_cod() != ' ' {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "RTST_COD",
            format!("{}", mir_rec.rtst_cod()),
        );
    }
    if mir_rec.prot_cod() != ' ' {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "PROT_COD",
            format!("{}", mir_rec.prot_cod()),
        );
    }
    if mir_rec.burn_tim() != 65535 {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "BURN_TIM",
            format!("{}", mir_rec.burn_tim()),
        );
    }
    if mir_rec.cmod_cod() != ' ' {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "CMOD_COD",
            format!("{}", mir_rec.cmod_cod()),
        );
    }

    if !mir_rec.lot_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "LOT_ID",
            mir_rec.lot_id().to_owned(),
        );
    }
    if !mir_rec.part_typ().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "PART_TYP",
            mir_rec.part_typ().to_owned(),
        );
    }
    if !mir_rec.node_nam().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "NODE_NAM",
            mir_rec.node_nam().to_owned(),
        );
    }
    if !mir_rec.tstr_typ().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "TSTR_TYP",
            mir_rec.tstr_typ().to_owned(),
        );
    }
    if !mir_rec.job_nam().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "JOB_NAM",
            mir_rec.job_nam().to_owned(),
        );
    }
    if !mir_rec.job_rev().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "JOB_REV",
            mir_rec.job_rev().to_owned(),
        );
    }
    if !mir_rec.sblot_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "SBLOT_ID",
            mir_rec.sblot_id().to_owned(),
        );
    }
    if !mir_rec.oper_nam().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "OPER_NAM",
            mir_rec.oper_nam().to_owned(),
        );
    }
    if !mir_rec.exec_typ().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "EXEC_TYP",
            mir_rec.exec_typ().to_owned(),
        );
    }
    if !mir_rec.exec_ver().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "EXEC_VER",
            mir_rec.exec_ver().to_owned(),
        );
    }
    if !mir_rec.test_cod().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "TEST_COD",
            mir_rec.test_cod().to_owned(),
        );
    }
    if !mir_rec.tst_temp().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "TST_TEMP",
            mir_rec.tst_temp().to_owned(),
        );
    }
    if !mir_rec.user_txt().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "USER_TXT",
            mir_rec.user_txt().to_owned(),
        );
    }
    if !mir_rec.aux_file().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "AUX_FILE",
            mir_rec.aux_file().to_owned(),
        );
    }
    if !mir_rec.pkg_typ().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "PKG_TYP",
            mir_rec.pkg_typ().to_owned(),
        );
    }
    if !mir_rec.famly_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "FAMLY_ID",
            mir_rec.famly_id().to_owned(),
        );
    }
    if !mir_rec.date_cod().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "DATE_COD",
            mir_rec.date_cod().to_owned(),
        );
    }
    if !mir_rec.facil_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "FACIL_ID",
            mir_rec.facil_id().to_owned(),
        );
    }
    if !mir_rec.floor_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "FLOOR_ID",
            mir_rec.floor_id().to_owned(),
        );
    }
    if !mir_rec.proc_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "PROC_ID",
            mir_rec.proc_id().to_owned(),
        );
    }
    if !mir_rec.oper_frq().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "OPER_FRQ",
            mir_rec.oper_frq().to_owned(),
        );
    }
    if !mir_rec.spec_nam().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "SPEC_NAM",
            mir_rec.spec_nam().to_owned(),
        );
    }
    if !mir_rec.spec_ver().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "SPEC_VER",
            mir_rec.spec_ver().to_owned(),
        );
    }
    if !mir_rec.flow_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "FLOW_ID",
            mir_rec.flow_id().to_owned(),
        );
    }
    if !mir_rec.setup_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "SETUP_ID",
            mir_rec.setup_id().to_owned(),
        );
    }
    if !mir_rec.dsgn_rev().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "DSGN_REV",
            mir_rec.dsgn_rev().to_owned(),
        );
    }
    if !mir_rec.eng_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "ENG_ID",
            mir_rec.eng_id().to_owned(),
        );
    }
    if !mir_rec.rom_cod().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "ROM_COD",
            mir_rec.rom_cod().to_owned(),
        );
    }
    if !mir_rec.serl_num().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "SERL_NUM",
            mir_rec.serl_num().to_owned(),
        );
    }
    if !mir_rec.supr_nam().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "SUPR_NAM",
            mir_rec.supr_nam().to_owned(),
        );
    }

    Ok(())
}

#[inline(always)]
fn on_pmr_view(
    file_id: usize,
    pmr_rec: PMRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    push_cold_op(
        ops,
        ColdOp::PinMap {
            fid: file_id,
            head_num: pmr_rec.head_num(),
            site_num: pmr_rec.site_num(),
            pmr_indx: pmr_rec.pmr_indx(),
            chan_typ: pmr_rec.chan_typ(),
            chan_nam: if !pmr_rec.chan_nam().as_bytes().is_empty() {
                Some(pmr_rec.chan_nam().to_owned())
            } else {
                None
            },
            phy_nam: if !pmr_rec.phy_nam().as_bytes().is_empty() {
                Some(pmr_rec.phy_nam().to_owned())
            } else {
                None
            },
            log_nam: if !pmr_rec.log_nam().as_bytes().is_empty() {
                Some(pmr_rec.log_nam().to_owned())
            } else {
                None
            },
        },
    );
    Ok(())
}

#[inline(always)]
fn on_pgr_view(
    file_id: usize,
    pgr_rec: PGRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    if !pgr_rec.grp_nam().as_bytes().is_empty() {
        push_cold_op(
            ops,
            ColdOp::GrpName {
                fid: file_id,
                grp_indx: pgr_rec.grp_indx(),
                grp_nam: pgr_rec.grp_nam().to_owned(),
            },
        );
    }
    for pmr_id in pgr_rec.pmr_indx() {
        push_cold_op(
            ops,
            ColdOp::UpdateFromGrp {
                grp_indx: pgr_rec.grp_indx(),
                fid: file_id,
                pmr_id,
            },
        );
    }
    Ok(())
}

#[inline(always)]
fn on_plr_view(
    file_id: usize,
    plr_rec: PLRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    let grp_indx = plr_rec.grp_indx();
    let grp_mode = plr_rec.grp_mode();
    let grp_radx = plr_rec.grp_radx();
    let pgm_char = plr_rec.pgm_char();
    let pgm_chal = plr_rec.pgm_chal();
    let rtn_char = plr_rec.rtn_char();
    let rtn_chal = plr_rec.rtn_chal();
    for i in 0..plr_rec.grp_cnt() as usize {
        push_cold_op(
            ops,
            ColdOp::PinInfo {
                fid: file_id,
                grp_indx: grp_indx[i],
                grp_mode: grp_mode[i],
                grp_radx: grp_radx[i],
                pgm_char: if pgm_char.get_bytes(i).is_some_and(|v| !v.is_empty()) {
                    Some(pgm_char.get_str(i).unwrap().into_owned())
                } else {
                    None
                },
                pgm_chal: if pgm_chal.get_bytes(i).is_some_and(|v| !v.is_empty()) {
                    Some(pgm_chal.get_str(i).unwrap().into_owned())
                } else {
                    None
                },
                rtn_char: if rtn_char.get_bytes(i).is_some_and(|v| !v.is_empty()) {
                    Some(rtn_char.get_str(i).unwrap().into_owned())
                } else {
                    None
                },
                rtn_chal: if rtn_chal.get_bytes(i).is_some_and(|v| !v.is_empty()) {
                    Some(rtn_chal.get_str(i).unwrap().into_owned())
                } else {
                    None
                },
            },
        );
    }
    Ok(())
}

#[inline(always)]
fn on_pir_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    pir: PIRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    let head_num = pir.head_num();
    let site_num = pir.site_num();
    let dut_index = tracker.pir_detected(file_id, &pir);
    push_cold_op(
        ops,
        ColdOp::InsertDut {
            fid: file_id,
            head_num,
            site_num,
            dut_index,
        },
    );
    Ok(())
}

#[inline(always)]
fn on_prr_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    prr_rec: PRRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    let head_num = prr_rec.head_num();
    let site_num = prr_rec.site_num();
    let hard_bin = prr_rec.hard_bin();
    let soft_bin = prr_rec.soft_bin();
    let part_flg = prr_rec.part_flg()[0];
    let (dut_index, wafer_index) = tracker.prr_detected(file_id, &prr_rec)?;
    let x_coord_value = prr_rec.x_coord();
    let x_coord = if x_coord_value != -32768 {
        Some(x_coord_value)
    } else {
        None
    };
    let y_coord_value = prr_rec.y_coord();
    let y_coord = if y_coord_value != -32768 {
        Some(y_coord_value)
    } else {
        None
    };

    let supersede_dut = part_flg & 1u8 == 1u8;
    let supersede_die = part_flg & 2u8 == 2u8;
    if supersede_dut {
        push_cold_op(
            ops,
            ColdOp::SupersedeDut {
                fid: file_id,
                head_num,
                site_num,
                part_id: prr_rec.part_id().to_owned(),
            },
        );
    }
    if supersede_die {
        push_cold_op(
            ops,
            ColdOp::SupersedeDie {
                fid: file_id,
                head_num,
                site_num,
                wafer_index,
                x_coord,
                y_coord,
            },
        );
    }

    push_cold_op(
        ops,
        ColdOp::UpdateDut {
            fid: file_id,
            dut_index,
            num_test: prr_rec.num_test(),
            test_t: prr_rec.test_t(),
            part_id: prr_rec.part_id().to_owned(),
            part_text: prr_rec.part_txt().to_owned(),
            hard_bin,
            soft_bin,
            part_flg,
            wafer_index,
            x_coord,
            y_coord,
        },
    );
    Ok(())
}

#[inline(always)]
fn on_hbr_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    hbr_rec: HBRView,
) -> Result<(), StdfHelperError> {
    tracker.hbr_detected(file_id, &hbr_rec);
    Ok(())
}

#[inline(always)]
fn on_sbr_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    sbr_rec: SBRView,
) -> Result<(), StdfHelperError> {
    tracker.sbr_detected(file_id, &sbr_rec);
    Ok(())
}

#[inline(always)]
fn on_wcr_view(
    file_id: usize,
    subfile_id: usize,
    wcr_rec: WCRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    if wcr_rec.wafr_siz() != 0.0 {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "WAFR_SIZ",
            format!("{}", wcr_rec.wafr_siz()),
        );
    }
    if wcr_rec.die_ht() != 0.0 {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "DIE_HT",
            format!("{}", wcr_rec.die_ht()),
        );
    }
    if wcr_rec.die_wid() != 0.0 {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "DIE_WID",
            format!("{}", wcr_rec.die_wid()),
        );
    }
    if wcr_rec.wf_units() != 0 {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "WF_UNITS",
            match wcr_rec.wf_units() {
                1 => "inch",
                2 => "cm",
                3 => "mm",
                _ => "mil",
            },
        );
    }
    push_file_info(
        ops,
        file_id,
        subfile_id,
        "WF_FLAT",
        format!("{}", wcr_rec.wf_flat()),
    );
    if wcr_rec.center_x() != -32768 {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "CENTER_X",
            format!("{}", wcr_rec.center_x()),
        );
    }
    if wcr_rec.center_y() != -32768 {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "CENTER_Y",
            format!("{}", wcr_rec.center_y()),
        );
    }
    push_file_info(
        ops,
        file_id,
        subfile_id,
        "POS_X",
        format!("{}", wcr_rec.pos_x()),
    );
    push_file_info(
        ops,
        file_id,
        subfile_id,
        "POS_Y",
        format!("{}", wcr_rec.pos_y()),
    );
    Ok(())
}

#[inline(always)]
fn on_wir_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    wir_rec: WIRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    let head_num = wir_rec.head_num();
    let wafer_index = tracker.wir_detected(file_id, &wir_rec);
    push_cold_op(
        ops,
        ColdOp::Wafer {
            fid: file_id,
            head_num,
            wafer_index,
            part_cnt: None,
            rtst_cnt: None,
            abrt_cnt: None,
            good_cnt: None,
            func_cnt: None,
            wafer_id: wir_rec.wafer_id().to_owned(),
            fabwf_id: None,
            frame_id: None,
            mask_id: None,
            usr_desc: None,
            exc_desc: None,
        },
    );
    Ok(())
}

#[inline(always)]
fn on_wrr_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    wrr_rec: WRRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    let head_num = wrr_rec.head_num();
    let wafer_index = tracker.get_wafer_index(file_id, head_num)?;
    push_cold_op(
        ops,
        ColdOp::Wafer {
            fid: file_id,
            head_num,
            wafer_index,
            part_cnt: Some(wrr_rec.part_cnt()),
            rtst_cnt: Some(wrr_rec.rtst_cnt()),
            abrt_cnt: Some(wrr_rec.abrt_cnt()),
            good_cnt: Some(wrr_rec.good_cnt()),
            func_cnt: Some(wrr_rec.func_cnt()),
            wafer_id: wrr_rec.wafer_id().to_owned(),
            fabwf_id: Some(wrr_rec.fabwf_id().to_owned()),
            frame_id: Some(wrr_rec.frame_id().to_owned()),
            mask_id: Some(wrr_rec.mask_id().to_owned()),
            usr_desc: Some(wrr_rec.usr_desc().to_owned()),
            exc_desc: Some(wrr_rec.exc_desc().to_owned()),
        },
    );
    Ok(())
}

#[inline(always)]
fn on_tsr_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    tsr_rec: TSRView,
) -> Result<(), StdfHelperError> {
    if let Err(e) = tracker.tsr_detected(file_id, &tsr_rec) {
        println!("TSR warning: {}", e.msg);
    }
    Ok(())
}

#[inline(always)]
fn on_pcr_view(
    file_id: usize,
    pcr_rec: PCRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    push_cold_op(
        ops,
        ColdOp::DutCounts {
            fid: file_id,
            head_num: pcr_rec.head_num(),
            site_num: pcr_rec.site_num(),
            part_cnt: pcr_rec.part_cnt(),
            rtst_cnt: pcr_rec.rtst_cnt(),
            abrt_cnt: pcr_rec.abrt_cnt(),
            good_cnt: pcr_rec.good_cnt(),
            func_cnt: pcr_rec.func_cnt(),
        },
    );
    Ok(())
}

#[inline(always)]
fn on_dtr_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    dtr_rec: DTRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    let (dut_index, is_before_prr) = tracker.get_datalog_relative_pos(file_id);
    ops.push(DbOp::Datalog {
        fid: file_id,
        rec_type: "DTR",
        value: dtr_rec.text_dat().to_owned(),
        dut_index,
        is_before_prr,
    });
    Ok(())
}

#[inline(always)]
fn on_gdr_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    gdr_rec: GDRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    let (dut_index, is_before_prr) = tracker.get_datalog_relative_pos(file_id);
    let gen_data = gdr_rec.gen_data();
    let flatten_string = flatten_generic_values(&gen_data);
    ops.push(DbOp::Datalog {
        fid: file_id,
        rec_type: "GDR",
        value: flatten_string,
        dut_index,
        is_before_prr,
    });
    Ok(())
}

#[inline(always)]
fn on_bps_view(
    tracker: &mut RecordTracker,
    file_id: usize,
    bps_rec: BPSView,
) -> Result<(), StdfHelperError> {
    tracker.bps_detected(file_id, &bps_rec)
}

#[inline(always)]
fn on_eps_view(tracker: &mut RecordTracker, file_id: usize) -> Result<(), StdfHelperError> {
    tracker.eps_detected(file_id)
}

#[inline(always)]
fn on_rdr_view(
    file_id: usize,
    subfile_id: usize,
    rdr_rec: RDRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    push_file_info(
        ops,
        file_id,
        subfile_id,
        "Retest Hardware Bins",
        if rdr_rec.num_bins() > 0 {
            rdr_rec
                .rtst_bin()
                .iter()
                .map(|b| b.to_string())
                .collect::<Vec<_>>()
                .join(", ")
        } else {
            "All hardware bins are retested".to_string()
        },
    );
    Ok(())
}

#[inline(always)]
fn on_sdr_view(
    file_id: usize,
    subfile_id: usize,
    sdr_rec: SDRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    if !sdr_rec.hand_typ().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Handler Type (Group {})", sdr_rec.site_grp()),
            sdr_rec.hand_typ().to_owned(),
        );
    }
    if !sdr_rec.hand_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Handler ID (Group {})", sdr_rec.site_grp()),
            sdr_rec.hand_id().to_owned(),
        );
    }
    if !sdr_rec.card_typ().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Probe Card Type (Group {})", sdr_rec.site_grp()),
            sdr_rec.card_typ().to_owned(),
        );
    }
    if !sdr_rec.card_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Probe Card ID (Group {})", sdr_rec.site_grp()),
            sdr_rec.card_id().to_owned(),
        );
    }
    if !sdr_rec.load_typ().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Load Board Type (Group {})", sdr_rec.site_grp()),
            sdr_rec.load_typ().to_owned(),
        );
    }
    if !sdr_rec.load_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Load Board ID (Group {})", sdr_rec.site_grp()),
            sdr_rec.load_id().to_owned(),
        );
    }
    if !sdr_rec.dib_typ().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("DIB Board Type (Group {})", sdr_rec.site_grp()),
            sdr_rec.dib_typ().to_owned(),
        );
    }
    if !sdr_rec.dib_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("DIB Board ID (Group {})", sdr_rec.site_grp()),
            sdr_rec.dib_id().to_owned(),
        );
    }
    if !sdr_rec.cabl_typ().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Interface Cable Type (Group {})", sdr_rec.site_grp()),
            sdr_rec.cabl_typ().to_owned(),
        );
    }
    if !sdr_rec.cabl_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Interface Cable ID (Group {})", sdr_rec.site_grp()),
            sdr_rec.cabl_id().to_owned(),
        );
    }
    if !sdr_rec.cont_typ().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Handler Contactor Type (Group {})", sdr_rec.site_grp()),
            sdr_rec.cont_typ().to_owned(),
        );
    }
    if !sdr_rec.cont_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Handler Contactor ID (Group {})", sdr_rec.site_grp()),
            sdr_rec.cont_id().to_owned(),
        );
    }
    if !sdr_rec.lasr_typ().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Laser Type (Group {})", sdr_rec.site_grp()),
            sdr_rec.lasr_typ().to_owned(),
        );
    }
    if !sdr_rec.lasr_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Laser ID (Group {})", sdr_rec.site_grp()),
            sdr_rec.lasr_id().to_owned(),
        );
    }
    if !sdr_rec.extr_typ().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Extra Equipment Type (Group {})", sdr_rec.site_grp()),
            sdr_rec.extr_typ().to_owned(),
        );
    }
    if !sdr_rec.extr_id().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            format!("Extra Equipment ID (Group {})", sdr_rec.site_grp()),
            sdr_rec.extr_id().to_owned(),
        );
    }
    Ok(())
}

#[inline(always)]
fn on_mrr_view(
    file_id: usize,
    subfile_id: usize,
    mrr_rec: MRRView,
    ops: &mut Vec<DbOp>,
) -> Result<(), StdfHelperError> {
    push_file_info(
        ops,
        file_id,
        subfile_id,
        "FINISH_T",
        u32_to_localtime(mrr_rec.finish_t()),
    );
    if mrr_rec.disp_cod() != ' ' {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "DISP_COD",
            mrr_rec.disp_cod().to_string(),
        );
    }
    if !mrr_rec.usr_desc().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "USR_DESC",
            mrr_rec.usr_desc().to_owned(),
        );
    }
    if !mrr_rec.exc_desc().as_bytes().is_empty() {
        push_file_info(
            ops,
            file_id,
            subfile_id,
            "EXC_DESC",
            mrr_rec.exc_desc().to_owned(),
        );
    }
    Ok(())
}
