//
// database_context.rs
// Author: noonchen - chennoon233@foxmail.com
// Created Date: October 29th 2022
// -----
// Last Modified: Wed Nov 23 2022
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::StdfHelperError;
use rusqlite::{Connection, Statement, ToSql};

static CREATE_TABLE_SQL: &str = "DROP TABLE IF EXISTS File_List;
                                DROP TABLE IF EXISTS File_Info;
                                DROP TABLE IF EXISTS Dut_Info;
                                DROP TABLE IF EXISTS Dut_Counts;
                                DROP TABLE IF EXISTS Test_Info;
                                DROP TABLE IF EXISTS PTR_Data;
                                DROP TABLE IF EXISTS MPR_Data;
                                DROP TABLE IF EXISTS FTR_Data;
                                DROP TABLE IF EXISTS Bin_Info;
                                DROP TABLE IF EXISTS Wafer_Info;
                                DROP TABLE IF EXISTS Pin_Map;
                                DROP TABLE IF EXISTS Pin_Info;
                                DROP TABLE IF EXISTS TestPin_Map;
                                DROP TABLE IF EXISTS Dynamic_Limits;
                                DROP TABLE IF EXISTS Datalog;
                                VACUUM;

                                BEGIN;

                                CREATE TABLE IF NOT EXISTS File_List (
                                                        Fid INTEGER,
                                                        SubFid INTEGER,
                                                        Filename TEXT,
                                                        Lot_ID TEXT, 
                                                        Sublot_ID TEXT,
                                                        Product_ID TEXT,
                                                        Flow_ID TEXT,
                                                        PRIMARY KEY (Fid, SubFid));
            
                                CREATE TABLE IF NOT EXISTS File_Info (
                                                        Fid INTEGER,
                                                        SubFid INTEGER,
                                                        Field TEXT, 
                                                        Value TEXT,
                                                        PRIMARY KEY (Fid, SubFid, Field));
                                                        
                                CREATE TABLE IF NOT EXISTS Wafer_Info (
                                                        Fid INTEGER,
                                                        HEAD_NUM INTEGER, 
                                                        WaferIndex INTEGER,
                                                        PART_CNT INTEGER,
                                                        RTST_CNT INTEGER,
                                                        ABRT_CNT INTEGER,
                                                        GOOD_CNT INTEGER,
                                                        FUNC_CNT INTEGER,
                                                        WAFER_ID TEXT,
                                                        FABWF_ID TEXT,
                                                        FRAME_ID TEXT,
                                                        MASK_ID TEXT,
                                                        USR_DESC TEXT,
                                                        EXC_DESC TEXT,
                                                        PRIMARY KEY (Fid, WaferIndex)) WITHOUT ROWID;
                                                        
                                CREATE TABLE IF NOT EXISTS Dut_Info (
                                                        Fid INTEGER,
                                                        HEAD_NUM INTEGER, 
                                                        SITE_NUM INTEGER, 
                                                        DUTIndex INTEGER,
                                                        TestCount INTEGER,
                                                        TestTime INTEGER,
                                                        PartID TEXT,
                                                        HBIN INTEGER,
                                                        SBIN INTEGER,
                                                        Flag INTEGER,
                                                        WaferIndex INTEGER,
                                                        XCOORD INTEGER,
                                                        YCOORD INTEGER,
                                                        Supersede INTEGER,
                                                        PRIMARY KEY (Fid, DUTIndex)) WITHOUT ROWID;
                                                        
                                CREATE TABLE IF NOT EXISTS Dut_Counts (
                                                        Fid INTEGER,
                                                        HEAD_NUM INTEGER, 
                                                        SITE_NUM INTEGER, 
                                                        PART_CNT INTEGER,
                                                        RTST_CNT INTEGER,
                                                        ABRT_CNT INTEGER,
                                                        GOOD_CNT INTEGER,
                                                        FUNC_CNT INTEGER);

                                CREATE TABLE IF NOT EXISTS Test_Info (
                                                        Fid INTEGER,
                                                        TEST_ID INTEGER,
                                                        TEST_NUM INTEGER,
                                                        recHeader INTEGER,
                                                        TEST_NAME TEXT,
                                                        RES_SCAL INTEGER,
                                                        LLimit REAL,
                                                        HLimit REAL,
                                                        Unit TEXT,
                                                        OPT_FLAG INTEGER,
                                                        FailCount INTEGER,
                                                        RTN_ICNT INTEGER,
                                                        RSLT_PGM_CNT INTEGER,
                                                        LSpec REAL,
                                                        HSpec REAL,
                                                        VECT_NAM TEXT,
                                                        SEQ_NAME TEXT,
                                                        PRIMARY KEY (Fid, TEST_NUM, TEST_NAME)) WITHOUT ROWID;
                                                        
                                CREATE TABLE IF NOT EXISTS PTR_Data (
                                                        DUTIndex INTEGER,
                                                        TEST_ID INTEGER, 
                                                        RESULT REAL,
                                                        TEST_FLAG INTEGER,
                                                        PRIMARY KEY (DUTIndex, TEST_ID)) WITHOUT ROWID;

                                CREATE TABLE IF NOT EXISTS MPR_Data (
                                                        DUTIndex INTEGER,
                                                        TEST_ID INTEGER, 
                                                        RTN_RSLT TEXT,
                                                        RTN_STAT TEXT,
                                                        TEST_FLAG INTEGER,
                                                        PRIMARY KEY (DUTIndex, TEST_ID)) WITHOUT ROWID;
                                                            
                                CREATE TABLE IF NOT EXISTS FTR_Data (
                                                        DUTIndex INTEGER,
                                                        TEST_ID INTEGER, 
                                                        TEST_FLAG INTEGER,
                                                        PRIMARY KEY (DUTIndex, TEST_ID)) WITHOUT ROWID;                                                            
                                                        
                                CREATE TABLE IF NOT EXISTS Bin_Info (
                                                        Fid INTEGER,
                                                        BIN_TYPE TEXT,
                                                        BIN_NUM INTEGER, 
                                                        BIN_NAME TEXT,
                                                        BIN_PF TEXT,
                                                        PRIMARY KEY (Fid, BIN_TYPE, BIN_NUM));

                                CREATE TABLE IF NOT EXISTS Pin_Map (
                                                        Fid INTEGER,
                                                        HEAD_NUM INTEGER, 
                                                        SITE_NUM INTEGER, 
                                                        PMR_INDX INTEGER,
                                                        CHAN_TYP INTEGER,
                                                        CHAN_NAM TEXT,
                                                        PHY_NAM TEXT,
                                                        LOG_NAM TEXT,
                                                        From_GRP INTEGER);

                                CREATE TABLE IF NOT EXISTS Pin_Info (
                                                        Fid INTEGER,
                                                        P_PG_INDX INTEGER, 
                                                        GRP_NAM TEXT, 
                                                        GRP_MODE INTEGER,
                                                        GRP_RADX INTEGER,
                                                        PGM_CHAR TEXT,
                                                        PGM_CHAL TEXT,
                                                        RTN_CHAR TEXT,
                                                        RTN_CHAL TEXT,
                                                        PRIMARY KEY (Fid, P_PG_INDX));

                                CREATE TABLE IF NOT EXISTS TestPin_Map (
                                                        TEST_ID INTEGER, 
                                                        PMR_INDX INTEGER,
                                                        PIN_TYPE TEXT,
                                                        PRIMARY KEY (TEST_ID, PMR_INDX, PIN_TYPE));

                                CREATE TABLE IF NOT EXISTS Dynamic_Limits (
                                                        DUTIndex INTEGER,
                                                        TEST_ID INTEGER, 
                                                        LLimit REAL,
                                                        HLimit REAL,
                                                        PRIMARY KEY (DUTIndex, TEST_ID)) WITHOUT ROWID;

                                CREATE TABLE IF NOT EXISTS Datalog (
                                                        Fid INTEGER,
                                                        RecordType TEXT,
                                                        Value TEXT, 
                                                        AfterDUTIndex INTEGER,
                                                        isBeforePRR INTEGER);
                                                        
                                DROP INDEX IF EXISTS dutKey;
                                CREATE INDEX 
                                    dutKey 
                                ON 
                                    Dut_Info (
                                        Fid         ASC,
                                        HEAD_NUM    ASC,
                                        SITE_NUM    ASC);

                                COMMIT;
                                
                                PRAGMA synchronous = OFF;
                                PRAGMA journal_mode = OFF;
                                PRAGMA locking_mode = EXCLUSIVE;

                                BEGIN;";

static INSERT_FILE_NAME: &str = "INSERT INTO 
                                    File_List (Fid, SubFid, Filename)
                                VALUES 
                                    (?,?,?)";

static UPDATE_FILE_LIST: &str = "UPDATE File_List SET 
                                    Lot_ID=:Lot_ID, Sublot_ID=:Sublot_ID, 
                                    Product_ID=:Product_ID, Flow_ID=:Flow_ID
                                WHERE 
                                    Fid=:Fid AND SubFid=:SubFid";

static INSERT_FILE_INFO: &str = "INSERT OR REPLACE INTO 
                                    File_Info 
                                VALUES 
                                    (?,?,?,?)";

static INSERT_DUT: &str = "INSERT INTO 
                                Dut_Info (Fid, HEAD_NUM, SITE_NUM, DUTIndex) 
                            VALUES 
                                (?,?,?,?);";

static UPDATE_DUT: &str = "UPDATE Dut_Info SET 
                                TestCount=:TestCount, TestTime=:TestTime, PartID=:PartID, 
                                HBIN=:HBIN_NUM, SBIN=:SBIN_NUM, Flag=:Flag, 
                                WaferIndex=:WaferIndex, XCOORD=:XCOORD, YCOORD=:YCOORD,
                                Supersede=:Supersede
                            WHERE 
                                Fid=:Fid AND DUTIndex=:DUTIndex;";

static UPDATE_SUPERSEDE_DUT: &str = "UPDATE Dut_Info SET
                                        Supersede=1
                                    WHERE
                                        Fid=:Fid AND 
                                        HEAD_NUM=:HEAD_NUM AND 
                                        SITE_NUM=:SITE_NUM AND
                                        PartID=:PartID;";

static UPDATE_SUPERSEDE_DIE: &str = "UPDATE Dut_Info SET
                                        Supersede=1
                                    WHERE
                                        Fid=:Fid AND 
                                        HEAD_NUM=:HEAD_NUM AND 
                                        SITE_NUM=:SITE_NUM AND
                                        WaferIndex=:WaferIndex AND
                                        XCOORD=:XCOORD AND
                                        YCOORD=:YCOORD;";

static INSERT_PTR_DATA: &str = "INSERT OR REPLACE INTO 
                                    PTR_Data 
                                VALUES 
                                    (:DUTIndex, :TEST_ID, :RESULT, :TEST_FLAG);";

static INSERT_MPR_DATA: &str = "INSERT OR REPLACE INTO 
                                    MPR_Data 
                                VALUES 
                                    (:DUTIndex, :TEST_ID, :RTN_RSLT, :RTN_STAT, :TEST_FLAG);";

static INSERT_FTR_DATA: &str = "INSERT OR REPLACE INTO 
                                    FTR_Data 
                                VALUES 
                                    (:DUTIndex, :TEST_ID, :TEST_FLAG);";

static INSERT_TEST_INFO: &str = "INSERT INTO 
                                    Test_Info 
                                VALUES 
                                    (:Fid, :TEST_ID, :TEST_NUM, :recHeader, :TEST_NAME, 
                                    :RES_SCAL, :LLimit, :HLimit, :Unit, :OPT_FLAG, 
                                    :FailCount, :RTN_ICNT, :RSLT_PGM_CNT, :LSpec, 
                                    :HSpec, :VECT_NAM, :SEQ_NAME);";

// test_id => (file_id, test_num, test_name)
static UPDATE_FAIL_COUNT: &str = "UPDATE 
                                    Test_Info 
                                SET 
                                    FailCount=:count 
                                WHERE 
                                    TEST_ID=:TEST_ID";

static INSERT_HBIN: &str = "INSERT OR REPLACE INTO 
                                Bin_Info 
                            VALUES 
                                (:Fid, 'H', :HBIN_NUM, :HBIN_NAME, :PF);";

static INSERT_SBIN: &str = "INSERT OR REPLACE INTO 
                                Bin_Info 
                            VALUES 
                                (:Fid, 'S', :SBIN_NUM, :SBIN_NAME, :PF);";

static INSERT_DUT_COUNT: &str = "INSERT INTO 
                                    Dut_Counts 
                                VALUES 
                                    (:Fid, :HEAD_NUM, :SITE_NUM, :PART_CNT, 
                                    :RTST_CNT, :ABRT_CNT, :GOOD_CNT, :FUNC_CNT);";

static INSERT_WAFER: &str = "INSERT OR REPLACE INTO 
                                    Wafer_Info 
                                VALUES 
                                    (:Fid, :HEAD_NUM, :WaferIndex, :PART_CNT, :RTST_CNT, 
                                    :ABRT_CNT, :GOOD_CNT, :FUNC_CNT, :WAFER_ID, 
                                    :FABWF_ID, :FRAME_ID, :MASK_ID, :USR_DESC, :EXC_DESC);";

static INSERT_PIN_MAP: &str = "INSERT INTO 
                                    Pin_Map 
                                VALUES 
                                    (:Fid, :HEAD_NUM, :SITE_NUM, :PMR_INDX, :CHAN_TYP, 
                                    :CHAN_NAM, :PHY_NAM, :LOG_NAM, :From_GRP);";

static UPDATE_FROM_GRP: &str = "UPDATE 
                                    Pin_Map 
                                SET 
                                    From_GRP=:From_GRP 
                                WHERE 
                                    Fid=:Fid AND PMR_INDX=:PMR_INDX;";

// # create a row with GRP_NAME in Pin_Info if PGR exists, in some rare cases, PMR shows after PGR, ignore it.
static INSERT_GRP_NAM: &str = "INSERT OR IGNORE INTO 
                                    Pin_Info (Fid, P_PG_INDX, GRP_NAM) 
                                VALUES 
                                    (:Fid, :P_PG_INDX, :GRP_NAM);";

// # insert rows in Pin_Info and keep GRP_NAM
static INSERT_PIN_INFO: &str = "INSERT OR REPLACE INTO 
                                    Pin_Info 
                                VALUES 
                                    (:Fid, :P_PG_INDX, 
                                        (SELECT 
                                            GRP_NAM 
                                        FROM 
                                            Pin_Info 
                                        WHERE 
                                            Fid=:Fid AND P_PG_INDX=:P_PG_INDX), 
                                    :GRP_MODE, :GRP_RADX, 
                                    :PGM_CHAR, :PGM_CHAL, :RTN_CHAR, :RTN_CHAL);";

static INSERT_TEST_PIN: &str = "INSERT OR IGNORE INTO 
                                    TestPin_Map 
                                VALUES 
                                    (:TEST_ID, :PMR_INDX, :PIN_TYPE);";

static INSERT_DYNAMIC_LIMIT: &str = "INSERT OR REPLACE INTO 
                                        Dynamic_Limits 
                                    VALUES 
                                        (:DUTIndex, :TEST_ID, :LLimit ,:HLimit);";

static INSERT_DATALOG: &str = "INSERT INTO 
                                    Datalog 
                                VALUES 
                                    (:Fid, :RecordType, :Value, :AfterDUTIndex ,:isBeforePRR);";

static COMMIT_AND_SET_LOCKING: &str = "COMMIT;
                                        PRAGMA locking_mode = NORMAL";

static START_NEW_TRANSACTION: &str = "COMMIT; BEGIN;";

pub struct DataBaseCtx<'con> {
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
}

impl<'con> DataBaseCtx<'con> {
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

        Ok(DataBaseCtx {
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
    pub fn insert_ptr_data(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_ptr_data_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_mpr_data(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_mpr_data_stmt.execute(p)?;
        Ok(())
    }

    #[inline(always)]
    pub fn insert_ftr_data(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_ftr_data_stmt.execute(p)?;
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
    pub fn insert_datalog_rec(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_datalog_rec_stmt.execute(p)?;
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
    pub fn finalize(self) -> Result<(), StdfHelperError> {
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

        Ok(())
    }
}
