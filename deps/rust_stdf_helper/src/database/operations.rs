//
// operations.rs
//
// Compact, owned database operations for STDF DB generation.
// For passing STDF record views information to DB gen thread.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::database::context::DatabaseCtx;
use crate::StdfHelperError;

/// Test ID represents a unique identifier for a test item in a database.
/// It is calculated by `(fid as u32) << 32 | local_id`, where
/// local_id is the test id within a single file group.
pub type TestId = i64;

/// Message sent from the per-group worker threads to the SQLite writer.
pub enum DbMessage {
    /// One batch of operations, preserving operation order within the sender.
    Batch(Vec<DbOp>),
    /// The worker hit a fatal parse/tracking error. The writer aborts with it.
    WorkerError { msg: String },
}

/// One database mutation.
pub enum DbOp {
    Ptr {
        dut_index: u64,
        test_id: TestId,
        result: f32,
        flag: u8,
    },
    Ftr {
        dut_index: u64,
        test_id: TestId,
        flag: u8,
    },
    Mpr {
        dut_index: u64,
        test_id: TestId,
        rslt_hex: String,
        stat_hex: String,
        flag: u8,
    },
    Datalog {
        fid: usize,
        rec_type: &'static str,
        value: String,
        dut_index: u64,
        is_before_prr: bool,
    },
    /// Less frequent, wider operations. Boxed to keep the hot enum stride
    /// small while still using one order-preserving operation stream.
    Cold(Box<ColdOp>),
}

/// Cold database mutations (one or a few per file, or one per unique test).
pub enum ColdOp {
    UpdateFileList {
        fid: usize,
        sub_fid: usize,
        lot_id: String,
        sblot_id: String,
        proc_id: String,
        flow_id: String,
    },
    FileInfo {
        fid: usize,
        sub_fid: usize,
        field: String,
        value: String,
    },
    InsertDut {
        fid: usize,
        head_num: u8,
        site_num: u8,
        dut_index: u64,
    },
    UpdateDut {
        fid: usize,
        dut_index: u64,
        num_test: u16,
        test_t: u32,
        part_id: String,
        part_text: String,
        hard_bin: u16,
        soft_bin: u16,
        part_flg: u8,
        wafer_index: Option<u64>,
        x_coord: Option<i16>,
        y_coord: Option<i16>,
    },
    SupersedeDut {
        fid: usize,
        head_num: u8,
        site_num: u8,
        part_id: String,
    },
    SupersedeDie {
        fid: usize,
        head_num: u8,
        site_num: u8,
        wafer_index: Option<u64>,
        x_coord: Option<i16>,
        y_coord: Option<i16>,
    },
    TestInfo {
        fid: usize,
        test_id: TestId,
        test_num: u32,
        rec_header: u8,
        test_name: String,
        res_scal: Option<i8>,
        llimit: f32,
        hlimit: f32,
        unit: String,
        opt_flag: Option<u8>,
        fail_cnt: i32,
        rtn_icnt: Option<u16>,
        rslt_pgm_cnt: Option<u16>,
        lspec: f32,
        hspec: f32,
        vect_nam: Option<String>,
        seq_name: Option<String>,
    },
    DynamicLimit {
        dut_index: u64,
        test_id: TestId,
        llimit: Option<f32>,
        hlimit: Option<f32>,
    },
    TestPin {
        test_id: TestId,
        pmr_indx: u16,
        pin_type: &'static str,
    },
    Wafer {
        fid: usize,
        head_num: u8,
        wafer_index: u64,
        part_cnt: Option<u32>,
        rtst_cnt: Option<u32>,
        abrt_cnt: Option<u32>,
        good_cnt: Option<u32>,
        func_cnt: Option<u32>,
        wafer_id: String,
        fabwf_id: Option<String>,
        frame_id: Option<String>,
        mask_id: Option<String>,
        usr_desc: Option<String>,
        exc_desc: Option<String>,
    },
    DutCounts {
        fid: usize,
        head_num: u8,
        site_num: u8,
        part_cnt: u32,
        rtst_cnt: u32,
        abrt_cnt: u32,
        good_cnt: u32,
        func_cnt: u32,
    },
    Hbin {
        fid: usize,
        bin_num: u16,
        bin_name: String,
        bin_pf: char,
    },
    Sbin {
        fid: usize,
        bin_num: u16,
        bin_name: String,
        bin_pf: char,
    },
    FailCount {
        test_id: TestId,
        count: u32,
    },
    PinMap {
        fid: usize,
        head_num: u8,
        site_num: u8,
        pmr_indx: u16,
        chan_typ: u16,
        chan_nam: Option<String>,
        phy_nam: Option<String>,
        log_nam: Option<String>,
    },
    UpdateFromGrp {
        grp_indx: u16,
        fid: usize,
        pmr_id: u16,
    },
    GrpName {
        fid: usize,
        grp_indx: u16,
        grp_nam: String,
    },
    PinInfo {
        fid: usize,
        grp_indx: u16,
        grp_mode: u16,
        grp_radx: u8,
        pgm_char: Option<String>,
        pgm_chal: Option<String>,
        rtn_char: Option<String>,
        rtn_chal: Option<String>,
    },
}

impl DbOp {
    /// Apply one operation to the writer-owned database context.
    pub fn apply(self, db_ctx: &mut DatabaseCtx) -> Result<(), StdfHelperError> {
        match self {
            DbOp::Ptr {
                dut_index,
                test_id,
                result,
                flag,
            } => db_ctx.insert_ptr_data_batched(dut_index, test_id, result, flag),
            DbOp::Ftr {
                dut_index,
                test_id,
                flag,
            } => db_ctx.insert_ftr_data_batched(dut_index, test_id, flag),
            DbOp::Mpr {
                dut_index,
                test_id,
                rslt_hex,
                stat_hex,
                flag,
            } => db_ctx.insert_mpr_data_batched(dut_index, test_id, rslt_hex, stat_hex, flag),
            DbOp::Datalog {
                fid,
                rec_type,
                value,
                dut_index,
                is_before_prr,
            } => db_ctx.insert_datalog_rec_batched(fid, rec_type, value, dut_index, is_before_prr),
            DbOp::Cold(op) => (*op).apply(db_ctx),
        }
    }
}

impl ColdOp {
    pub fn apply(self, db_ctx: &mut DatabaseCtx) -> Result<(), StdfHelperError> {
        match self {
            ColdOp::UpdateFileList {
                fid,
                sub_fid,
                lot_id,
                sblot_id,
                proc_id,
                flow_id,
            } => db_ctx.update_file_list(rusqlite::params![
                &lot_id, &sblot_id, &proc_id, &flow_id, fid, sub_fid
            ]),
            ColdOp::FileInfo {
                fid,
                sub_fid,
                field,
                value,
            } => db_ctx.insert_file_info(rusqlite::params![fid, sub_fid, field, value]),
            ColdOp::InsertDut {
                fid,
                head_num,
                site_num,
                dut_index,
            } => db_ctx.insert_dut(rusqlite::params![fid, head_num, site_num, dut_index]),
            ColdOp::UpdateDut {
                fid,
                dut_index,
                num_test,
                test_t,
                part_id,
                part_text,
                hard_bin,
                soft_bin,
                part_flg,
                wafer_index,
                x_coord,
                y_coord,
            } => db_ctx.update_dut(rusqlite::params![
                num_test,
                test_t,
                part_id,
                part_text,
                hard_bin,
                soft_bin,
                part_flg,
                wafer_index,
                x_coord,
                y_coord,
                0,
                fid,
                dut_index
            ]),
            ColdOp::SupersedeDut {
                fid,
                head_num,
                site_num,
                part_id,
            } => db_ctx.update_supersede_dut(rusqlite::params![fid, head_num, site_num, part_id]),
            ColdOp::SupersedeDie {
                fid,
                head_num,
                site_num,
                wafer_index,
                x_coord,
                y_coord,
            } => db_ctx.update_supersede_die(rusqlite::params![
                fid,
                head_num,
                site_num,
                wafer_index,
                x_coord,
                y_coord
            ]),
            ColdOp::TestInfo {
                fid,
                test_id,
                test_num,
                rec_header,
                test_name,
                res_scal,
                llimit,
                hlimit,
                unit,
                opt_flag,
                fail_cnt,
                rtn_icnt,
                rslt_pgm_cnt,
                lspec,
                hspec,
                vect_nam,
                seq_name,
            } => db_ctx.insert_test_info(rusqlite::params![
                fid,
                test_id,
                test_num,
                rec_header,
                test_name,
                res_scal,
                llimit,
                hlimit,
                unit,
                opt_flag,
                fail_cnt,
                rtn_icnt,
                rslt_pgm_cnt,
                lspec,
                hspec,
                vect_nam,
                seq_name
            ]),
            ColdOp::DynamicLimit {
                dut_index,
                test_id,
                llimit,
                hlimit,
            } => db_ctx.insert_dynamic_limit(rusqlite::params![dut_index, test_id, llimit, hlimit]),
            ColdOp::TestPin {
                test_id,
                pmr_indx,
                pin_type,
            } => db_ctx.insert_test_pin(rusqlite::params![test_id, pmr_indx, pin_type]),
            ColdOp::Wafer {
                fid,
                head_num,
                wafer_index,
                part_cnt,
                rtst_cnt,
                abrt_cnt,
                good_cnt,
                func_cnt,
                wafer_id,
                fabwf_id,
                frame_id,
                mask_id,
                usr_desc,
                exc_desc,
            } => db_ctx.insert_wafer(rusqlite::params![
                fid,
                head_num,
                wafer_index,
                part_cnt,
                rtst_cnt,
                abrt_cnt,
                good_cnt,
                func_cnt,
                wafer_id,
                fabwf_id,
                frame_id,
                mask_id,
                usr_desc,
                exc_desc
            ]),
            ColdOp::DutCounts {
                fid,
                head_num,
                site_num,
                part_cnt,
                rtst_cnt,
                abrt_cnt,
                good_cnt,
                func_cnt,
            } => db_ctx.insert_dut_cnt(rusqlite::params![
                fid, head_num, site_num, part_cnt, rtst_cnt, abrt_cnt, good_cnt, func_cnt
            ]),
            ColdOp::Hbin {
                fid,
                bin_num,
                bin_name,
                bin_pf,
            } => {
                let bin_pf = bin_pf.to_string();
                db_ctx.insert_hbin(rusqlite::params![fid, bin_num, bin_name, &bin_pf])
            }
            ColdOp::Sbin {
                fid,
                bin_num,
                bin_name,
                bin_pf,
            } => {
                let bin_pf = bin_pf.to_string();
                db_ctx.insert_sbin(rusqlite::params![fid, bin_num, bin_name, &bin_pf])
            }
            ColdOp::FailCount { test_id, count } => {
                // Match the legacy writer: a TSR fail-count update for a
                // missing Test_Info row is logged, not fatal.
                if let Err(e) = db_ctx.update_fail_count(rusqlite::params![count, test_id]) {
                    println!("Sqlite3 error when saving TSR fail counts: {}", e.msg);
                }
                Ok(())
            }
            ColdOp::PinMap {
                fid,
                head_num,
                site_num,
                pmr_indx,
                chan_typ,
                chan_nam,
                phy_nam,
                log_nam,
            } => db_ctx.insert_pin_map(rusqlite::params![
                fid,
                head_num,
                site_num,
                pmr_indx,
                chan_typ,
                chan_nam,
                phy_nam,
                log_nam,
                None::<u16>
            ]),
            ColdOp::UpdateFromGrp {
                grp_indx,
                fid,
                pmr_id,
            } => db_ctx.update_from_grp(rusqlite::params![grp_indx, fid, pmr_id]),
            ColdOp::GrpName {
                fid,
                grp_indx,
                grp_nam,
            } => db_ctx.insert_grp_name(rusqlite::params![fid, grp_indx, grp_nam]),
            ColdOp::PinInfo {
                fid,
                grp_indx,
                grp_mode,
                grp_radx,
                pgm_char,
                pgm_chal,
                rtn_char,
                rtn_chal,
            } => db_ctx.insert_pin_info(rusqlite::params![
                fid, grp_indx, grp_mode, grp_radx, pgm_char, pgm_chal, rtn_char, rtn_chal
            ]),
        }
    }
}

/******************************/
/**** ops helper functions ****/
/******************************/

/// Pack a file id and a local test id into a test id for the database.
///
/// Test ID must be i64, means:
///  - `fid` should be in the range of [0, `2^31 - 1`].
///  - `local_id` should be in the range of [0, `2^32 - 1`].
///
/// Although, such limitation is not likely to be hit in practice.
#[inline]
pub(crate) fn make_test_id(fid: usize, local_id: usize) -> Result<TestId, StdfHelperError> {
    if fid >= (1usize << 31) {
        return Err(StdfHelperError {
            msg: format!(
                "Too much file groups [{}]! No more than 2^31 groups per database",
                fid + 1
            ),
        });
    }
    if local_id >= (1usize << 32) {
        return Err(StdfHelperError {
            msg: format!(
                "Too much test items in a file group [{}]! No more than 2^32 tests per file group",
                local_id + 1
            ),
        });
    }
    // safe unwrap because of checks above
    let fid = u32::try_from(fid).unwrap();
    let local_id = u32::try_from(local_id).unwrap();
    let tid = (u64::from(fid) << 32) | u64::from(local_id);
    Ok(i64::try_from(tid).unwrap())
}

#[inline(always)]
pub(crate) fn push_cold_op(ops: &mut Vec<DbOp>, op: ColdOp) {
    ops.push(DbOp::Cold(Box::new(op)));
}

#[inline(always)]
pub(crate) fn push_file_info(
    ops: &mut Vec<DbOp>,
    file_id: usize,
    subfile_id: usize,
    field: impl Into<String>,
    value: impl Into<String>,
) {
    push_cold_op(
        ops,
        ColdOp::FileInfo {
            fid: file_id,
            sub_fid: subfile_id,
            field: field.into(),
            value: value.into(),
        },
    );
}

#[cfg(test)]
mod size_tests {
    use super::*;

    /// Keeps the hot `Vec<DbOp>` stride small. Measured 72 bytes on the
    /// current 64-bit target with `ColdOp` (208 bytes) boxed behind `DbOp::Cold`.
    #[test]
    fn record_db_op_size() {
        assert!(std::mem::size_of::<DbOp>() <= 96);
    }

    #[test]
    fn partitioned_test_id_bounds() {
        assert_eq!(make_test_id(0, 0).unwrap(), 0);
        assert_eq!(make_test_id(1, 2).unwrap(), (1i64 << 32) | 2);
        assert_eq!(
            make_test_id((1usize << 31) - 1, u32::MAX as usize).unwrap(),
            i64::MAX
        );
        assert!(make_test_id(1usize << 31, 0).is_err());
        assert!(make_test_id(0, 1usize << 32).is_err());
    }
}
