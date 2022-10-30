//
// database_context.rs
// Author: noonchen - chennoon233@foxmail.com
// Created Date: October 29th 2022
// -----
// Last Modified: Sun Oct 30 2022
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::StdfHelperError;
use rusqlite::{Connection, Statement, ToSql};

static CREATE_TABLE_SQL: &str = "DROP TABLE IF EXISTS File_Info;
                                DROP TABLE IF EXISTS Dut_Info;
                                DROP TABLE IF EXISTS Dut_Counts;
                                DROP TABLE IF EXISTS Test_Info;
                                DROP TABLE IF EXISTS Test_Offsets;
                                DROP TABLE IF EXISTS Bin_Info;
                                DROP TABLE IF EXISTS Wafer_Info;
                                DROP TABLE IF EXISTS Pin_Map;
                                DROP TABLE IF EXISTS Pin_Info;
                                DROP TABLE IF EXISTS TestPin_Map;
                                DROP TABLE IF EXISTS Dynamic_Limits;
                                DROP TABLE IF EXISTS Datalog;
                                VACUUM;

                                BEGIN;
                                CREATE TABLE IF NOT EXISTS File_Info (
                                                        Fid INTEGER,
                                                        Field TEXT, 
                                                        Value TEXT);
                                                        
                                CREATE TABLE IF NOT EXISTS Wafer_Info (
                                                        HEAD_NUM INTEGER, 
                                                        WaferIndex INTEGER PRIMARY KEY,
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
                                                        EXC_DESC TEXT);
                                                        
                                CREATE TABLE IF NOT EXISTS Dut_Info (
                                                        HEAD_NUM INTEGER, 
                                                        SITE_NUM INTEGER, 
                                                        DUTIndex INTEGER PRIMARY KEY,
                                                        TestCount INTEGER,
                                                        TestTime INTEGER,
                                                        PartID TEXT,
                                                        HBIN INTEGER,
                                                        SBIN INTEGER,
                                                        Flag INTEGER,
                                                        WaferIndex INTEGER,
                                                        XCOORD INTEGER,
                                                        YCOORD INTEGER) WITHOUT ROWID;
                                                        
                                CREATE TABLE IF NOT EXISTS Dut_Counts (
                                                        HEAD_NUM INTEGER, 
                                                        SITE_NUM INTEGER, 
                                                        PART_CNT INTEGER,
                                                        RTST_CNT INTEGER,
                                                        ABRT_CNT INTEGER,
                                                        GOOD_CNT INTEGER,
                                                        FUNC_CNT INTEGER);

                                CREATE TABLE IF NOT EXISTS Test_Info (
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
                                                        PRIMARY KEY (TEST_NUM, TEST_NAME)) WITHOUT ROWID;
                                                        
                                CREATE TABLE IF NOT EXISTS Test_Offsets (
                                                        DUTIndex INTEGER,
                                                        TEST_ID INTEGER, 
                                                        Offset INTEGER,
                                                        BinaryLen INTEGER,
                                                        PRIMARY KEY (DUTIndex, TEST_ID)) WITHOUT ROWID;
                                                        
                                CREATE TABLE IF NOT EXISTS Bin_Info (
                                                        BIN_TYPE TEXT,
                                                        BIN_NUM INTEGER, 
                                                        BIN_NAME TEXT,
                                                        BIN_PF TEXT,
                                                        PRIMARY KEY (BIN_TYPE, BIN_NUM));

                                CREATE TABLE IF NOT EXISTS Pin_Map (
                                                        HEAD_NUM INTEGER, 
                                                        SITE_NUM INTEGER, 
                                                        PMR_INDX INTEGER,
                                                        CHAN_TYP INTEGER,
                                                        CHAN_NAM TEXT,
                                                        PHY_NAM TEXT,
                                                        LOG_NAM TEXT,
                                                        From_GRP INTEGER);

                                CREATE TABLE IF NOT EXISTS Pin_Info (
                                                        P_PG_INDX INTEGER PRIMARY KEY, 
                                                        GRP_NAM TEXT, 
                                                        GRP_MODE INTEGER,
                                                        GRP_RADX INTEGER,
                                                        PGM_CHAR TEXT,
                                                        PGM_CHAL TEXT,
                                                        RTN_CHAR TEXT,
                                                        RTN_CHAL TEXT);

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
                                                        PRIMARY KEY (DUTIndex, TEST_ID));

                                CREATE TABLE IF NOT EXISTS Datalog (
                                                        RecordType TEXT,
                                                        Value TEXT, 
                                                        AfterDUTIndex INTEGER,
                                                        isBeforePRR INTEGER);
                                                        
                                DROP INDEX IF EXISTS dutKey;
                                COMMIT;
                                
                                PRAGMA synchronous = OFF;
                                PRAGMA journal_mode = WAL;

                                BEGIN;";

static INSERT_FILE_INFO: &str = "INSERT OR REPLACE INTO 
                                    File_Info 
                                VALUES 
                                    (?,?,?)";

static INSERT_DUT: &str = "INSERT INTO 
                                Dut_Info (HEAD_NUM, SITE_NUM, DUTIndex) 
                            VALUES 
                                (?,?,?);";

static UPDATE_DUT: &str = "UPDATE Dut_Info SET 
                                TestCount=:TestCount, TestTime=:TestTime, PartID=:PartID, 
                                HBIN=:HBIN_NUM, SBIN=:SBIN_NUM, Flag=:Flag, 
                                WaferIndex=:WaferIndex, XCOORD=:XCOORD, YCOORD=:YCOORD 
                            WHERE 
                                DUTIndex=:DUTIndex; COMMIT; BEGIN;"; // commit and start another transaction in PRR

static INSERT_TEST_REC: &str = "INSERT OR REPLACE INTO 
                                Test_Offsets 
                            VALUES 
                                (:DUTIndex, :TEST_ID, :Offset ,:BinaryLen);";

static INSERT_TEST_INFO: &str = "INSERT INTO 
                                    Test_Info 
                                VALUES 
                                    (:TEST_ID, :TEST_NUM, :recHeader, :TEST_NAME, 
                                    :RES_SCAL, :LLimit, :HLimit, :Unit, :OPT_FLAG, 
                                    :FailCount, :RTN_ICNT, :RSLT_PGM_CNT, :LSpec, 
                                    :HSpec, :VECT_NAM, :SEQ_NAME);";

static INSERT_HBIN: &str = "INSERT OR REPLACE INTO 
                                Bin_Info 
                            VALUES 
                                ('H', :HBIN_NUM, :HBIN_NAME, :PF);";

static INSERT_SBIN: &str = "INSERT OR REPLACE INTO 
                                Bin_Info 
                            VALUES 
                                ('S', :SBIN_NUM, :SBIN_NAME, :PF);";

static INSERT_DUT_COUNT: &str = "INSERT INTO 
                                    Dut_Counts 
                                VALUES 
                                    (:HEAD_NUM, :SITE_NUM, :PART_CNT, :RTST_CNT, 
                                    :ABRT_CNT, :GOOD_CNT, :FUNC_CNT);";

static INSERT_WAFER: &str = "INSERT OR REPLACE INTO 
                                    Wafer_Info 
                                VALUES 
                                    (:HEAD_NUM, :WaferIndex, :PART_CNT, :RTST_CNT, 
                                    :ABRT_CNT, :GOOD_CNT, :FUNC_CNT, :WAFER_ID, 
                                    :FABWF_ID, :FRAME_ID, :MASK_ID, :USR_DESC, :EXC_DESC);";

static INSERT_PIN_MAP: &str = "INSERT INTO 
                                    Pin_Map 
                                VALUES 
                                    (:HEAD_NUM, :SITE_NUM, :PMR_INDX, :CHAN_TYP, 
                                    :CHAN_NAM, :PHY_NAM, :LOG_NAM, :From_GRP);";

static UPDATE_FROM_GRP: &str = "UPDATE 
                                    Pin_Map 
                                SET 
                                    From_GRP=:From_GRP 
                                WHERE 
                                    PMR_INDX=:PMR_INDX;";

// # create a row with GRP_NAME in Pin_Info if PGR exists, in some rare cases, PMR shows after PGR, ignore it.
static INSERT_GRP_NAM: &str = "INSERT OR IGNORE INTO 
                                    Pin_Info (P_PG_INDX, GRP_NAM) 
                                VALUES 
                                    (:P_PG_INDX, :GRP_NAM);";

// # insert rows in Pin_Info and keep GRP_NAM
static INSERT_PIN_INFO: &str = "INSERT OR REPLACE INTO 
                                    Pin_Info 
                                VALUES 
                                    (:P_PG_INDX, (SELECT 
                                                    GRP_NAM 
                                                FROM 
                                                    Pin_Info 
                                                WHERE 
                                                    P_PG_INDX=:P_PG_INDX), 
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
                                    (:RecordType, :Value, :AfterDUTIndex ,:isBeforePRR);";

static CREATE_INDEX_AND_COMMIT: &str = "CREATE INDEX 
                                            dutKey 
                                        ON 
                                            Dut_Info (
                                                HEAD_NUM    ASC,
                                                SITE_NUM    ASC);
                                                
                                        COMMIT;";

pub struct DataBaseCtx<'con> {
    db: &'con Connection,
    insert_file_info_stmt: Statement<'con>,
    insert_dut_stmt: Statement<'con>,
    update_dut_stmt: Statement<'con>,
    insert_test_rec_stmt: Statement<'con>,
    insert_test_info_stmt: Statement<'con>,
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
        let insert_file_info_stmt = conn.prepare(INSERT_FILE_INFO)?;
        let insert_dut_stmt = conn.prepare(INSERT_DUT)?;
        let update_dut_stmt = conn.prepare(UPDATE_DUT)?;
        let insert_test_rec_stmt = conn.prepare(INSERT_TEST_REC)?;
        let insert_test_info_stmt = conn.prepare(INSERT_TEST_INFO)?;
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
            insert_file_info_stmt,
            insert_dut_stmt,
            update_dut_stmt,
            insert_test_rec_stmt,
            insert_test_info_stmt,
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

    pub fn insert_file_info(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_file_info_stmt.execute(p)?;
        Ok(())
    }

    pub fn insert_pin_map(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_pin_map_stmt.execute(p)?;
        Ok(())
    }

    pub fn insert_grp_name(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_grp_name_stmt.execute(p)?;
        Ok(())
    }
    pub fn update_from_grp(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.update_from_grp_stmt.execute(p)?;
        Ok(())
    }

    pub fn insert_pin_info(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_pin_info_stmt.execute(p)?;
        Ok(())
    }

    pub fn insert_dut(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_dut_stmt.execute(p)?;
        Ok(())
    }

    pub fn update_dut(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.update_dut_stmt.execute(p)?;
        Ok(())
    }

    pub fn insert_test_rec(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_test_rec_stmt.execute(p)?;
        Ok(())
    }

    pub fn insert_test_info(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_test_info_stmt.execute(p)?;
        Ok(())
    }

    pub fn insert_dynamic_limit(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_dynamic_limit_stmt.execute(p)?;
        Ok(())
    }

    pub fn insert_test_pin(&mut self, p: &[&dyn ToSql]) -> Result<(), StdfHelperError> {
        self.insert_test_pin_stmt.execute(p)?;
        Ok(())
    }

    pub fn finalize(self) -> Result<(), StdfHelperError> {
        self.db.execute_batch(CREATE_INDEX_AND_COMMIT)?;

        self.insert_file_info_stmt.finalize()?;
        self.insert_dut_stmt.finalize()?;
        self.update_dut_stmt.finalize()?;
        self.insert_test_rec_stmt.finalize()?;
        self.insert_test_info_stmt.finalize()?;
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
