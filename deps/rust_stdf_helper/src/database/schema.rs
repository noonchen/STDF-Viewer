//
// schema.rs
//
// SQLite schema constants.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

pub(crate) static CREATE_TABLE_SQL: &str = "DROP TABLE IF EXISTS File_List;
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
                                DROP INDEX IF EXISTS dutKey;
                                DROP INDEX IF EXISTS ptrKey;
                                DROP INDEX IF EXISTS mprKey;
                                DROP INDEX IF EXISTS ftrKey;
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
                                                        PartText TEXT,
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

pub(crate) static INSERT_FILE_NAME: &str = "INSERT INTO 
                                    File_List (Fid, SubFid, Filename)
                                VALUES 
                                    (?,?,?)";

pub(crate) static UPDATE_FILE_LIST: &str = "UPDATE File_List SET 
                                    Lot_ID=:Lot_ID, Sublot_ID=:Sublot_ID, 
                                    Product_ID=:Product_ID, Flow_ID=:Flow_ID
                                WHERE 
                                    Fid=:Fid AND SubFid=:SubFid";

pub(crate) static INSERT_FILE_INFO: &str = "INSERT OR REPLACE INTO 
                                    File_Info 
                                VALUES 
                                    (?,?,?,?)";

pub(crate) static INSERT_DUT: &str = "INSERT INTO 
                                Dut_Info (Fid, HEAD_NUM, SITE_NUM, DUTIndex) 
                            VALUES 
                                (?,?,?,?);";

pub(crate) static UPDATE_DUT: &str = "UPDATE Dut_Info SET 
                                TestCount=:TestCount, TestTime=:TestTime, PartID=:PartID, PartText=:PartText,
                                HBIN=:HBIN_NUM, SBIN=:SBIN_NUM, Flag=:Flag, 
                                WaferIndex=:WaferIndex, XCOORD=:XCOORD, YCOORD=:YCOORD,
                                Supersede=:Supersede
                            WHERE 
                                Fid=:Fid AND DUTIndex=:DUTIndex;";

pub(crate) static UPDATE_SUPERSEDE_DUT: &str = "UPDATE Dut_Info SET
                                        Supersede=1
                                    WHERE
                                        Fid=:Fid AND 
                                        HEAD_NUM=:HEAD_NUM AND 
                                        SITE_NUM=:SITE_NUM AND
                                        PartID=:PartID;";

pub(crate) static UPDATE_SUPERSEDE_DIE: &str = "UPDATE Dut_Info SET
                                        Supersede=1
                                    WHERE
                                        Fid=:Fid AND 
                                        HEAD_NUM=:HEAD_NUM AND 
                                        SITE_NUM=:SITE_NUM AND
                                        WaferIndex=:WaferIndex AND
                                        XCOORD=:XCOORD AND
                                        YCOORD=:YCOORD;";

pub(crate) static INSERT_PTR_DATA: &str = "INSERT OR REPLACE INTO 
                                    PTR_Data 
                                VALUES 
                                    (:DUTIndex, :TEST_ID, :RESULT, :TEST_FLAG);";

pub(crate) static INSERT_MPR_DATA: &str = "INSERT OR REPLACE INTO 
                                    MPR_Data 
                                VALUES 
                                    (:DUTIndex, :TEST_ID, :RTN_RSLT, :RTN_STAT, :TEST_FLAG);";

pub(crate) static INSERT_FTR_DATA: &str = "INSERT OR REPLACE INTO 
                                    FTR_Data 
                                VALUES 
                                    (:DUTIndex, :TEST_ID, :TEST_FLAG);";

pub(crate) static INSERT_TEST_INFO: &str = "INSERT OR IGNORE INTO 
                                    Test_Info 
                                VALUES 
                                    (:Fid, :TEST_ID, :TEST_NUM, :recHeader, :TEST_NAME, 
                                    :RES_SCAL, :LLimit, :HLimit, :Unit, :OPT_FLAG, 
                                    :FailCount, :RTN_ICNT, :RSLT_PGM_CNT, :LSpec, 
                                    :HSpec, :VECT_NAM, :SEQ_NAME);";

// test_id => (file_id, test_num, test_name)
pub(crate) static UPDATE_FAIL_COUNT: &str = "UPDATE 
                                    Test_Info 
                                SET 
                                    FailCount=:count 
                                WHERE 
                                    TEST_ID=:TEST_ID";

pub(crate) static INSERT_HBIN: &str = "INSERT OR REPLACE INTO 
                                Bin_Info 
                            VALUES 
                                (:Fid, 'H', :HBIN_NUM, :HBIN_NAME, :PF);";

pub(crate) static INSERT_SBIN: &str = "INSERT OR REPLACE INTO 
                                Bin_Info 
                            VALUES 
                                (:Fid, 'S', :SBIN_NUM, :SBIN_NAME, :PF);";

pub(crate) static INSERT_DUT_COUNT: &str = "INSERT INTO 
                                    Dut_Counts 
                                VALUES 
                                    (:Fid, :HEAD_NUM, :SITE_NUM, :PART_CNT, 
                                    :RTST_CNT, :ABRT_CNT, :GOOD_CNT, :FUNC_CNT);";

pub(crate) static INSERT_WAFER: &str = "INSERT OR REPLACE INTO 
                                    Wafer_Info 
                                VALUES 
                                    (:Fid, :HEAD_NUM, :WaferIndex, :PART_CNT, :RTST_CNT, 
                                    :ABRT_CNT, :GOOD_CNT, :FUNC_CNT, :WAFER_ID, 
                                    :FABWF_ID, :FRAME_ID, :MASK_ID, :USR_DESC, :EXC_DESC);";

pub(crate) static INSERT_PIN_MAP: &str = "INSERT INTO 
                                    Pin_Map 
                                VALUES 
                                    (:Fid, :HEAD_NUM, :SITE_NUM, :PMR_INDX, :CHAN_TYP, 
                                    :CHAN_NAM, :PHY_NAM, :LOG_NAM, :From_GRP);";

pub(crate) static UPDATE_FROM_GRP: &str = "UPDATE 
                                    Pin_Map 
                                SET 
                                    From_GRP=:From_GRP 
                                WHERE 
                                    Fid=:Fid AND PMR_INDX=:PMR_INDX;";

// # create a row with GRP_NAME in Pin_Info if PGR exists, in some rare cases, PMR shows after PGR, ignore it.
pub(crate) static INSERT_GRP_NAM: &str = "INSERT OR IGNORE INTO 
                                    Pin_Info (Fid, P_PG_INDX, GRP_NAM) 
                                VALUES 
                                    (:Fid, :P_PG_INDX, :GRP_NAM);";

// # insert rows in Pin_Info and keep GRP_NAM
pub(crate) static INSERT_PIN_INFO: &str = "INSERT OR REPLACE INTO 
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

pub(crate) static INSERT_TEST_PIN: &str = "INSERT OR IGNORE INTO 
                                    TestPin_Map 
                                VALUES 
                                    (:TEST_ID, :PMR_INDX, :PIN_TYPE);";

pub(crate) static INSERT_DYNAMIC_LIMIT: &str = "INSERT OR REPLACE INTO 
                                        Dynamic_Limits 
                                    VALUES 
                                        (:DUTIndex, :TEST_ID, :LLimit ,:HLimit);";

pub(crate) static INSERT_DATALOG: &str = "INSERT INTO 
                                    Datalog 
                                VALUES 
                                    (:Fid, :RecordType, :Value, :AfterDUTIndex ,:isBeforePRR);";

pub(crate) static CREATE_INDEX_FOR_QUERY: &str = "CREATE INDEX 
                                            ptrKey
                                        ON 
                                            PTR_Data (TEST_ID, DUTIndex);

                                        CREATE INDEX 
                                            mprKey
                                        ON 
                                            MPR_Data (TEST_ID, DUTIndex);

                                        CREATE INDEX 
                                            ftrKey
                                        ON 
                                            FTR_Data (TEST_ID, DUTIndex);";

pub(crate) static COMMIT_AND_SET_LOCKING: &str = "COMMIT;
                                        PRAGMA locking_mode = NORMAL";

pub(crate) static START_NEW_TRANSACTION: &str = "COMMIT; BEGIN;";
