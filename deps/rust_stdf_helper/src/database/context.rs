//
// context.rs
//
// Database context for STDF DB generation.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::database::operations::TestId;
use crate::database::schema::*;
use crate::StdfHelperError;
use rusqlite::{Connection, Statement, ToSql};

// number of data rows per multi-row INSERT
const ROWS_PER_BATCH: usize = 128;

struct PtrRow {
    dut: u64,
    tid: TestId,
    result: f32,
    flag: u8,
}

struct FtrRow {
    dut: u64,
    tid: TestId,
    flag: u8,
}

struct MprRow {
    dut: u64,
    tid: TestId,
    rslt: String,
    stat: String,
    flag: u8,
}

struct DatalogRow {
    fid: usize,
    rec_type: &'static str,
    value: String,
    dut_index: u64,
    is_before_prr: bool,
}

pub struct DatabaseCtx<'con> {
    db: &'con Connection,
    insert_file_name_stmt: Statement<'con>,
    update_file_list_stmt: Statement<'con>,
    insert_file_info_stmt: Statement<'con>,
    insert_dut_stmt: Statement<'con>,
    update_dut_stmt: Statement<'con>,
    update_supersede_dut_stmt: Statement<'con>,
    update_supersede_die_stmt: Statement<'con>,
    insert_ptr_data_stmt: Statement<'con>,
    insert_mpr_data_stmt: Statement<'con>,
    insert_ftr_data_stmt: Statement<'con>,
    insert_test_info_stmt: Statement<'con>,
    update_fail_count_stmt: Statement<'con>,
    insert_hbin_stmt: Statement<'con>,
    insert_sbin_stmt: Statement<'con>,
    insert_dut_cnt_stmt: Statement<'con>,
    insert_wafer_stmt: Statement<'con>,
    insert_pin_map_stmt: Statement<'con>,
    update_from_grp_stmt: Statement<'con>,
    insert_grp_name_stmt: Statement<'con>,
    insert_pin_info_stmt: Statement<'con>,
    insert_test_pin_stmt: Statement<'con>,
    insert_dynamic_limit_stmt: Statement<'con>,
    insert_datalog_rec_stmt: Statement<'con>,
    insert_ptr_batch_stmt: Statement<'con>,
    insert_ftr_batch_stmt: Statement<'con>,
    insert_mpr_batch_stmt: Statement<'con>,
    insert_datalog_batch_stmt: Statement<'con>,
    ptr_batch: Vec<PtrRow>,
    ftr_batch: Vec<FtrRow>,
    mpr_batch: Vec<MprRow>,
    datalog_batch: Vec<DatalogRow>,
}

impl<'con> DatabaseCtx<'con> {
    pub fn new(conn: &'con Connection) -> Result<Self, StdfHelperError> {
        conn.execute_batch(CREATE_TABLE_SQL)?;
        let insert_file_name_stmt = conn.prepare(INSERT_FILE_NAME)?;
        let update_file_list_stmt = conn.prepare(UPDATE_FILE_LIST)?;
        let insert_file_info_stmt = conn.prepare(INSERT_FILE_INFO)?;
        let insert_dut_stmt = conn.prepare(INSERT_DUT)?;
        let update_dut_stmt = conn.prepare(UPDATE_DUT)?;
        let update_supersede_dut_stmt = conn.prepare(UPDATE_SUPERSEDE_DUT)?;
        let update_supersede_die_stmt = conn.prepare(UPDATE_SUPERSEDE_DIE)?;
        let insert_ptr_data_stmt = conn.prepare(INSERT_PTR_DATA)?;
        let insert_mpr_data_stmt = conn.prepare(INSERT_MPR_DATA)?;
        let insert_ftr_data_stmt = conn.prepare(INSERT_FTR_DATA)?;
        let insert_test_info_stmt = conn.prepare(INSERT_TEST_INFO)?;
        let update_fail_count_stmt = conn.prepare(UPDATE_FAIL_COUNT)?;
        let insert_hbin_stmt = conn.prepare(INSERT_HBIN)?;
        let insert_sbin_stmt = conn.prepare(INSERT_SBIN)?;
        let insert_dut_cnt_stmt = conn.prepare(INSERT_DUT_COUNT)?;
        let insert_wafer_stmt = conn.prepare(INSERT_WAFER)?;
        let insert_pin_map_stmt = conn.prepare(INSERT_PIN_MAP)?;
        let update_from_grp_stmt = conn.prepare(UPDATE_FROM_GRP)?;
        let insert_grp_name_stmt = conn.prepare(INSERT_GRP_NAM)?;
        let insert_pin_info_stmt = conn.prepare(INSERT_PIN_INFO)?;
        let insert_test_pin_stmt = conn.prepare(INSERT_TEST_PIN)?;
        let insert_dynamic_limit_stmt = conn.prepare(INSERT_DYNAMIC_LIMIT)?;
        let insert_datalog_rec_stmt = conn.prepare(INSERT_DATALOG)?;
        // prepared multi-row INSERT for the hot PTR_Data path
        let mut ptr_batch_sql = String::from("INSERT OR REPLACE INTO PTR_Data VALUES ");
        for i in 0..ROWS_PER_BATCH {
            ptr_batch_sql.push_str(if i == 0 { "(?,?,?,?)" } else { ",(?,?,?,?)" });
        }
        // prepared multi-row INSERT for the hot FTR_Data path
        let mut ftr_batch_sql = String::from("INSERT OR REPLACE INTO FTR_Data VALUES ");
        for i in 0..ROWS_PER_BATCH {
            ftr_batch_sql.push_str(if i == 0 { "(?,?,?)" } else { ",(?,?,?)" });
        }
        // prepared multi-row INSERT for the hot MPR_Data path
        let mut mpr_batch_sql = String::from("INSERT OR REPLACE INTO MPR_Data VALUES ");
        for i in 0..ROWS_PER_BATCH {
            mpr_batch_sql.push_str(if i == 0 {
                "(?,?,?,?,?)"
            } else {
                ",(?,?,?,?,?)"
            });
        }
        // prepared multi-row INSERT for the Datalog (DTR/GDR) path
        let mut datalog_batch_sql = String::from("INSERT INTO Datalog VALUES ");
        for i in 0..ROWS_PER_BATCH {
            datalog_batch_sql.push_str(if i == 0 {
                "(?,?,?,?,?)"
            } else {
                ",(?,?,?,?,?)"
            });
        }
        let insert_ptr_batch_stmt = conn.prepare(&ptr_batch_sql)?;
        let insert_ftr_batch_stmt = conn.prepare(&ftr_batch_sql)?;
        let insert_mpr_batch_stmt = conn.prepare(&mpr_batch_sql)?;
        let insert_datalog_batch_stmt = conn.prepare(&datalog_batch_sql)?;

        Ok(DatabaseCtx {
            db: conn,
            insert_file_name_stmt,
            update_file_list_stmt,
            insert_file_info_stmt,
            insert_dut_stmt,
            update_dut_stmt,
            update_supersede_dut_stmt,
            update_supersede_die_stmt,
            insert_ptr_data_stmt,
            insert_mpr_data_stmt,
            insert_ftr_data_stmt,
            insert_test_info_stmt,
            update_fail_count_stmt,
            insert_hbin_stmt,
            insert_sbin_stmt,
            insert_dut_cnt_stmt,
            insert_wafer_stmt,
            insert_pin_map_stmt,
            update_from_grp_stmt,
            insert_grp_name_stmt,
            insert_pin_info_stmt,
            insert_test_pin_stmt,
            insert_dynamic_limit_stmt,
            insert_datalog_rec_stmt,
            insert_ptr_batch_stmt,
            insert_ftr_batch_stmt,
            insert_mpr_batch_stmt,
            insert_datalog_batch_stmt,
            ptr_batch: Vec::with_capacity(ROWS_PER_BATCH),
            ftr_batch: Vec::with_capacity(ROWS_PER_BATCH),
            mpr_batch: Vec::with_capacity(ROWS_PER_BATCH),
            datalog_batch: Vec::with_capacity(ROWS_PER_BATCH),
        })
    }

    #[inline(always)]
    pub fn start_new_transaction(&self) -> Result<(), StdfHelperError> {
        self.db.execute_batch(START_NEW_TRANSACTION)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_file_name(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_file_name_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn update_file_list(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.update_file_list_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_file_info(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_file_info_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_pin_map(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_pin_map_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_grp_name(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_grp_name_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn update_from_grp(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.update_from_grp_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_pin_info(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_pin_info_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_dut(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_dut_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn update_dut(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.update_dut_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn update_supersede_dut(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.update_supersede_dut_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn update_supersede_die(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.update_supersede_die_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    /// Buffer one PTR_Data row
    pub fn insert_ptr_data_batched(
        &mut self,
        dut: u64,
        tid: TestId,
        result: f32,
        flag: u8,
    ) -> Result<(), StdfHelperError> {
        self.ptr_batch.push(PtrRow {
            dut,
            tid,
            result,
            flag,
        });
        if self.ptr_batch.len() >= ROWS_PER_BATCH {
            {
                let stmt = &mut self.insert_ptr_batch_stmt;
                let mut params: Vec<&dyn ToSql> = Vec::with_capacity(ROWS_PER_BATCH * 4);
                for r in self.ptr_batch.iter() {
                    params.push(&r.dut);
                    params.push(&r.tid);
                    params.push(&r.result);
                    params.push(&r.flag);
                }
                stmt.execute(params.as_slice())?;
            }
            self.ptr_batch.clear();
        }
        Ok(())
    }

    #[inline(always)]
    /// Buffer one FTR_Data row
    pub fn insert_ftr_data_batched(
        &mut self,
        dut: u64,
        tid: TestId,
        flag: u8,
    ) -> Result<(), StdfHelperError> {
        self.ftr_batch.push(FtrRow { dut, tid, flag });
        if self.ftr_batch.len() >= ROWS_PER_BATCH {
            {
                let stmt = &mut self.insert_ftr_batch_stmt;
                let mut params: Vec<&dyn ToSql> = Vec::with_capacity(ROWS_PER_BATCH * 3);
                for r in self.ftr_batch.iter() {
                    params.push(&r.dut);
                    params.push(&r.tid);
                    params.push(&r.flag);
                }
                stmt.execute(params.as_slice())?;
            }
            self.ftr_batch.clear();
        }
        Ok(())
    }

    #[inline(always)]
    /// Buffer one MPR_Data row
    pub fn insert_mpr_data_batched(
        &mut self,
        dut: u64,
        tid: TestId,
        rslt: String,
        stat: String,
        flag: u8,
    ) -> Result<(), StdfHelperError> {
        self.mpr_batch.push(MprRow {
            dut,
            tid,
            rslt,
            stat,
            flag,
        });
        if self.mpr_batch.len() >= ROWS_PER_BATCH {
            {
                let stmt = &mut self.insert_mpr_batch_stmt;
                let mut params: Vec<&dyn ToSql> = Vec::with_capacity(ROWS_PER_BATCH * 5);
                for r in self.mpr_batch.iter() {
                    params.push(&r.dut);
                    params.push(&r.tid);
                    params.push(&r.rslt);
                    params.push(&r.stat);
                    params.push(&r.flag);
                }
                stmt.execute(params.as_slice())?;
            }
            self.mpr_batch.clear();
        }
        Ok(())
    }

    #[inline(always)]
    /// Buffer one Datalog (DTR/GDR) row
    pub fn insert_datalog_rec_batched(
        &mut self,
        fid: usize,
        rec_type: &'static str,
        value: String,
        dut_index: u64,
        is_before_prr: bool,
    ) -> Result<(), StdfHelperError> {
        self.datalog_batch.push(DatalogRow {
            fid,
            rec_type,
            value,
            dut_index,
            is_before_prr,
        });
        if self.datalog_batch.len() >= ROWS_PER_BATCH {
            {
                let stmt = &mut self.insert_datalog_batch_stmt;
                let mut params: Vec<&dyn ToSql> = Vec::with_capacity(ROWS_PER_BATCH * 5);
                for r in self.datalog_batch.iter() {
                    params.push(&r.fid);
                    params.push(&r.rec_type);
                    params.push(&r.value);
                    params.push(&r.dut_index);
                    params.push(&r.is_before_prr);
                }
                stmt.execute(params.as_slice())?;
            }
            self.datalog_batch.clear();
        }
        Ok(())
    }

    /// Flush any buffered PTR_Data rows.
    pub fn flush_ptr_batch(&mut self) -> Result<(), StdfHelperError> {
        if self.ptr_batch.is_empty() {
            return Ok(());
        }
        {
            let stmt = &mut self.insert_ptr_data_stmt;
            for r in self.ptr_batch.iter() {
                stmt.execute(rusqlite::params![r.dut, r.tid, r.result, r.flag])?;
            }
        }
        self.ptr_batch.clear();
        Ok(())
    }

    /// Flush any buffered FTR_Data rows.
    pub fn flush_ftr_batch(&mut self) -> Result<(), StdfHelperError> {
        if self.ftr_batch.is_empty() {
            return Ok(());
        }
        {
            let stmt = &mut self.insert_ftr_data_stmt;
            for r in self.ftr_batch.iter() {
                stmt.execute(rusqlite::params![r.dut, r.tid, r.flag])?;
            }
        }
        self.ftr_batch.clear();
        Ok(())
    }

    /// Flush any buffered MPR_Data rows
    pub fn flush_mpr_batch(&mut self) -> Result<(), StdfHelperError> {
        if self.mpr_batch.is_empty() {
            return Ok(());
        }
        {
            let stmt = &mut self.insert_mpr_data_stmt;
            for r in self.mpr_batch.iter() {
                stmt.execute(rusqlite::params![r.dut, r.tid, r.rslt, r.stat, r.flag])?;
            }
        }
        self.mpr_batch.clear();
        Ok(())
    }

    /// Flush any buffered Datalog rows
    pub fn flush_datalog_batch(&mut self) -> Result<(), StdfHelperError> {
        if self.datalog_batch.is_empty() {
            return Ok(());
        }
        {
            let stmt = &mut self.insert_datalog_rec_stmt;
            for r in self.datalog_batch.iter() {
                stmt.execute(rusqlite::params![
                    r.fid,
                    r.rec_type,
                    r.value,
                    r.dut_index,
                    r.is_before_prr
                ])?;
            }
        }
        self.datalog_batch.clear();
        Ok(())
    }

    #[inline(always)]
    pub fn insert_test_info(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_test_info_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_dynamic_limit(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_dynamic_limit_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_test_pin(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_test_pin_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_wafer(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_wafer_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_dut_cnt(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_dut_cnt_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_hbin(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_hbin_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_sbin(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_sbin_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn update_fail_count(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.update_fail_count_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn finalize(mut self, build_index: bool) -> Result<(), StdfHelperError> {
        // write out any data rows still buffered before committing
        self.flush_ptr_batch()?;
        self.flush_ftr_batch()?;
        self.flush_mpr_batch()?;
        self.flush_datalog_batch()?;
        if build_index {
            self.db.execute_batch(CREATE_INDEX_FOR_QUERY)?;
        }
        self.db.execute_batch(COMMIT_AND_SET_LOCKING)?;
        self.insert_file_name_stmt.finalize()?;
        self.update_file_list_stmt.finalize()?;
        self.insert_file_info_stmt.finalize()?;
        self.insert_dut_stmt.finalize()?;
        self.update_dut_stmt.finalize()?;
        self.insert_ptr_data_stmt.finalize()?;
        self.insert_mpr_data_stmt.finalize()?;
        self.insert_ftr_data_stmt.finalize()?;
        self.insert_test_info_stmt.finalize()?;
        self.update_fail_count_stmt.finalize()?;
        self.insert_hbin_stmt.finalize()?;
        self.insert_sbin_stmt.finalize()?;
        self.insert_dut_cnt_stmt.finalize()?;
        self.insert_wafer_stmt.finalize()?;
        self.insert_pin_map_stmt.finalize()?;
        self.update_from_grp_stmt.finalize()?;
        self.insert_grp_name_stmt.finalize()?;
        self.insert_pin_info_stmt.finalize()?;
        self.insert_test_pin_stmt.finalize()?;
        self.insert_dynamic_limit_stmt.finalize()?;
        self.insert_datalog_rec_stmt.finalize()?;
        self.insert_ptr_batch_stmt.finalize()?;
        self.insert_ftr_batch_stmt.finalize()?;
        self.insert_mpr_batch_stmt.finalize()?;
        self.insert_datalog_batch_stmt.finalize()?;

        Ok(())
    }
}
