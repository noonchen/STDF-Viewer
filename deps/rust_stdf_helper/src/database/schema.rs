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
                                                        SUB_CODE INTEGER,
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
                                                        RTN_RSLT BLOB,
                                                        RTN_STAT BLOB,
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
                                    (:Fid, :TEST_ID, :TEST_NUM, :SUB_CODE, :TEST_NAME, 
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
                                            FTR_Data (TEST_ID, DUTIndex);

                                        CREATE INDEX 
                                            dynKey
                                        ON 
                                            Dynamic_Limits (TEST_ID, DUTIndex);";

pub(crate) static COMMIT_AND_SET_LOCKING: &str = "COMMIT;
                                        PRAGMA locking_mode = NORMAL";

pub(crate) static START_NEW_TRANSACTION: &str = "COMMIT; BEGIN;";

/***********************/
/*** Fetcher Queries ***/
/***********************/

pub(crate) mod fetcher_queries {

    pub(crate) static FETCH_SELECT_FILE_LIST: &str = "SELECT 
        Fid, 
        Filename 
    FROM 
        File_List 
    ORDER BY 
        Fid, SubFid";

    pub(crate) static FETCH_SELECT_MAX_DUT_INDEX: &str = "SELECT 
        MAX(DUTIndex) 
    FROM 
        Dut_Info 
    WHERE 
        Fid=?";

    pub(crate) static FETCH_SELECT_DUT_HEAD_SITE: &str = "SELECT 
        DUTIndex, 
        HEAD_NUM, 
        SITE_NUM 
    FROM 
        Dut_Info 
    WHERE 
        Fid=? AND Supersede=0 
    ORDER BY 
        DUTIndex";

    pub(crate) static FETCH_SELECT_DUT_HEAD_SITE_ALL: &str = "SELECT 
        DUTIndex, 
        HEAD_NUM, 
        SITE_NUM 
    FROM 
        Dut_Info 
    WHERE 
        Fid=? 
    ORDER BY 
        DUTIndex";

    pub(crate) static FETCH_SELECT_PTR_DATA: &str = "SELECT 
        DUTIndex, 
        RESULT, 
        TEST_FLAG 
    FROM 
        PTR_Data 
    WHERE 
        TEST_ID=? 
    ORDER BY 
        DUTIndex";

    pub(crate) static FETCH_SELECT_FTR_DATA: &str = "SELECT 
        DUTIndex, 
        TEST_FLAG 
    FROM 
        FTR_Data 
    WHERE 
        TEST_ID=? 
    ORDER BY 
        DUTIndex";

    pub(crate) static FETCH_SELECT_MPR_DATA: &str = "SELECT 
        DUTIndex, 
        RTN_RSLT, 
        RTN_STAT, 
        TEST_FLAG 
    FROM 
        MPR_Data 
    WHERE 
        TEST_ID=? 
    ORDER BY 
        DUTIndex";

    /****** Metadata / summary queries ******/

    pub(crate) static FETCH_SELECT_WAFER_COUNT: &str = "SELECT 
        A.Fid, B.wafercnt 
    FROM 
        (SELECT DISTINCT Fid FROM File_List) as A 
    LEFT JOIN 
        (SELECT Fid, count(*) as wafercnt FROM Wafer_Info GROUP by Fid) as B 
    ON 
        A.Fid = B.Fid 
    ORDER by 
        A.Fid";

    pub(crate) static FETCH_SELECT_BYTE_ORDER: &str = "SELECT 
        (CASE WHEN Value=\"Little endian\" THEN 1 ELSE 0 END) AS \"IsLB\" 
    FROM 
        File_Info 
    WHERE 
        Field=\"BYTE_ORD\" 
    ORDER BY Fid";

    pub(crate) static FETCH_SELECT_TEST_ITEMS: &str = "SELECT 
        Test_Info.TEST_NUM, Test_Info.TEST_NAME, TestPin_Map.PMR_INDX 
    FROM 
        Test_Info 
    LEFT JOIN 
        TestPin_Map 
    ON 
        Test_Info.TEST_ID = TestPin_Map.TEST_ID 
    ORDER by 
        Test_Info.TEST_ID, TestPin_Map.ROWID";

    pub(crate) static FETCH_SELECT_TEST_RECORD_TYPES: &str = "SELECT 
        TEST_NUM, TEST_NAME, SUB_CODE 
    FROM 
        Test_Info";

    pub(crate) static FETCH_SELECT_WAFER_LIST: &str = "SELECT 
        Fid, WaferIndex, WAFER_ID 
    FROM 
        Wafer_Info 
    ORDER by 
        WaferIndex";

    pub(crate) static FETCH_SELECT_TEST_FAIL_CNT: &str = "SELECT 
        TEST_NUM, TEST_NAME, Fid, FailCount 
    FROM 
        Test_Info";

    pub(crate) static FETCH_SELECT_BIN_INFO: &str = "SELECT 
        BIN_NUM, BIN_NAME, BIN_PF 
    FROM 
        Bin_Info 
    WHERE 
        BIN_TYPE = ? 
    ORDER by 
        BIN_NUM";

    pub(crate) static FETCH_SELECT_BIN_STATS_H_HEAD: &str = "SELECT 
        Fid, HBIN, count(HBIN) 
    FROM 
        Dut_Info 
    WHERE 
        HEAD_NUM=? AND Supersede=0 
    GROUP by Fid, HBIN";

    pub(crate) static FETCH_SELECT_BIN_STATS_H_HEAD_SITE: &str = "SELECT 
        Fid, HBIN, count(HBIN) 
    FROM 
        Dut_Info 
    WHERE 
        HEAD_NUM=? AND SITE_NUM=? AND Supersede=0 
    GROUP by Fid, HBIN";

    pub(crate) static FETCH_SELECT_BIN_STATS_S_HEAD: &str = "SELECT 
        Fid, SBIN, count(SBIN) 
    FROM 
        Dut_Info 
    WHERE 
        HEAD_NUM=? AND Supersede=0 
    GROUP by Fid, SBIN";

    pub(crate) static FETCH_SELECT_BIN_STATS_S_HEAD_SITE: &str = "SELECT 
        Fid, SBIN, count(SBIN) 
    FROM 
        Dut_Info 
    WHERE 
        HEAD_NUM=? AND SITE_NUM=? AND Supersede=0 
    GROUP by Fid, SBIN";

    pub(crate) static FETCH_SELECT_FILE_INFO: &str = "SELECT 
        Fid, Field, Value 
    FROM 
        File_Info 
    ORDER By 
        Fid, Field, SubFid";

    /****** DUT-level queries ******/

    /****** Queries moved out of database/fetcher.rs (fixed SQL, no appended conditions) ******/

    pub(crate) static FETCH_SELECT_DUT_SUMMARY: &str = "SELECT 
        DUTIndex, 
        Dut_Info.Fid AS \"File ID\", 
        PartID, 
        PartText, 
        'Head ' || HEAD_NUM || ' - ' || 'Site ' || SITE_NUM, 
        TestCount, 
        TestTime || ' ms', 
        'Bin ' || HBIN, 
        'Bin ' || SBIN, 
        wf.WAFER_ID, 
        '(' || XCOORD || ', ' || YCOORD || ')', 
        printf(\"%s - 0x%02X\", CASE 
                WHEN Supersede=1 THEN 'Superseded' 
                WHEN Flag & 24 = 0 THEN 'Pass' 
                WHEN Flag & 24 = 8 THEN 'Failed' 
                ELSE 'Unknown' END, Flag) 
    FROM 
        (Dut_Info 
            LEFT JOIN (SELECT Fid, WaferIndex, WAFER_ID FROM Wafer_Info) AS wf 
            ON Dut_Info.Fid = wf.Fid AND Dut_Info.WaferIndex = wf.WaferIndex)";

    pub(crate) static FETCH_SELECT_DATALOG: &str = "SELECT 
        RecordType AS \"Record Type\", 
        '\\n' || Value || '\\n' AS \"Value\", 
        printf(\"%s ··· %s ··· %s\", 
            CASE WHEN AfterDUTIndex == 0 THEN \"|\" 
                 ELSE printf(\"PIR #%d\", AfterDUTIndex) END, 
            CASE WHEN isBeforePRR == 1 THEN RecordType 
                 ELSE printf(\"PRR #%d\", AfterDUTIndex) END, 
            CASE WHEN AfterDUTIndex == 0 THEN \"PIR #1\" 
                 WHEN isBeforePRR == 1 THEN printf(\"PRR #%d\", AfterDUTIndex) 
                 ELSE RecordType END) AS \"Approx. Location\" 
    FROM 
        Datalog";

    pub(crate) static FETCH_SELECT_WAFER_INFO: &str = "SELECT 
        Fid, HEAD_NUM, WaferIndex, PART_CNT, RTST_CNT, ABRT_CNT, 
        GOOD_CNT, FUNC_CNT, WAFER_ID, FABWF_ID, FRAME_ID, MASK_ID, 
        USR_DESC, EXC_DESC 
    FROM 
        Wafer_Info 
    ORDER by 
        WaferIndex";

    pub(crate) static FETCH_SELECT_WAFER_EXT: &str = "SELECT 
        Field, Value 
    FROM 
        File_Info 
    WHERE 
        Fid=? AND SubFid=0 AND Field in 
        ('DIE_WID', 'DIE_HT', 'POS_X', 'POS_Y', 'WF_UNITS')";

    pub(crate) static FETCH_SELECT_PIN_NAMES: &str = "SELECT 
        A.PMR_INDX, PHY_NAM, LOG_NAM, HEAD_NUM, SITE_NUM, CHAN_NAM 
    FROM 
        ((SELECT ROWID, PMR_INDX FROM TestPin_Map 
            WHERE PIN_TYPE=? AND TEST_ID in 
                (SELECT TEST_ID FROM Test_Info 
                 WHERE TEST_NUM=? AND TEST_NAME=? AND Fid=?)) as A 
        INNER JOIN 
            Pin_Map 
        ON 
            A.PMR_INDX=Pin_Map.PMR_INDX AND Pin_Map.Fid=?) 
    ORDER BY A.ROWID";

    // {column} is filled in with a caller-supplied identifier (see
    // is_dut_info_column_empty); no other text is ever appended.
    pub(crate) static FETCH_EXISTS_DUT_COLUMN: &str = "SELECT EXISTS (
        SELECT 1 
        FROM Dut_Info 
        WHERE {column} IS NOT NULL 
            AND 
            (typeof({column}) != 'text' OR trim({column}) != \"\"))";

    // Single conditional-aggregation pass replacing the five grouped counts.
    pub(crate) static FETCH_SELECT_DUT_COUNTS: &str = "SELECT 
        Fid, 
        count(*), 
        sum(CASE WHEN Supersede=0 AND (Flag & 24)=0 THEN 1 ELSE 0 END), 
        sum(CASE WHEN Supersede=0 AND (Flag & 24)=8 THEN 1 ELSE 0 END), 
        sum(CASE WHEN Flag IS NULL OR (Supersede=0 AND (Flag & 16)=16) THEN 1 ELSE 0 END), 
        sum(CASE WHEN Supersede=1 THEN 1 ELSE 0 END) 
    FROM 
        Dut_Info 
    GROUP by Fid 
    ORDER by Fid";

    // Partial DUT info for the DUT Data Table: DUTIndex, PartID, PartText,
    // "Head h - Site s", "State - 0xFL". The head/site selections arrive as
    // JSON arrays so the SQL text is constant and `prepare_cached` reuses it.
    pub(crate) static FETCH_SELECT_PARTIAL_SITES: &str = "SELECT 
        DUTIndex, 
        PartID, 
        PartText, 
        'Head ' || HEAD_NUM || ' - ' || 'Site ' || SITE_NUM, 
        printf(\"%s - 0x%02X\", CASE 
                WHEN Supersede=1 THEN 'Superseded' 
                WHEN Flag & 24 = 0 THEN 'Pass' 
                WHEN Flag & 24 = 8 THEN 'Failed' 
                ELSE 'Unknown' 
                END, Flag) 
    FROM 
        Dut_Info 
    WHERE Fid=?1 
        AND HEAD_NUM IN (SELECT value FROM json_each(?2)) 
        AND SITE_NUM IN (SELECT value FROM json_each(?3)) 
    ORDER BY 
        DUTIndex";

    /// Same as above with `-1` ("all sites") in the selection: only rows with
    /// a non-negative site are kept.
    pub(crate) static FETCH_SELECT_PARTIAL_ALL_SITES: &str = "SELECT 
        DUTIndex, 
        PartID, 
        PartText, 
        'Head ' || HEAD_NUM || ' - ' || 'Site ' || SITE_NUM, 
        printf(\"%s - 0x%02X\", CASE 
                WHEN Supersede=1 THEN 'Superseded' 
                WHEN Flag & 24 = 0 THEN 'Pass' 
                WHEN Flag & 24 = 8 THEN 'Failed' 
                ELSE 'Unknown' 
                END, Flag) 
    FROM 
        Dut_Info 
    WHERE Fid=?1 
        AND HEAD_NUM IN (SELECT value FROM json_each(?2)) 
        AND SITE_NUM >= 0 
    ORDER BY 
        DUTIndex";

    // Full Test_Info row set, used to prime the eager test_info cache.
    pub(crate) static FETCH_SELECT_ALL_TEST_INFO: &str = "SELECT 
        Fid, 
        TEST_ID, 
        SUB_CODE, 
        TEST_NUM, 
        TEST_NAME, 
        RES_SCAL, 
        LLimit, 
        HLimit, 
        Unit, 
        OPT_FLAG, 
        FailCount, 
        RTN_ICNT, 
        RSLT_PGM_CNT, 
        LSpec, 
        HSpec, 
        VECT_NAM, 
        SEQ_NAME 
    FROM 
        Test_Info";

    // Per-test Dynamic_Limits rows for the lazy cache.
    pub(crate) static FETCH_SELECT_DYNAMIC_LIMITS_BY_TEST: &str = "SELECT 
        DUTIndex, LLimit, HLimit 
    FROM 
        Dynamic_Limits 
    WHERE 
        TEST_ID=? 
    ORDER BY 
        DUTIndex";

    // Single-count templates for getDUTCountOnConditions(); {extra} carries the
    // optional " AND COL=?" pieces appended by the caller.
    // One row of [Pass, Failed, Unknown, Superseded] counts.
    pub(crate) static FETCH_COUNT_ON_COND: &str = "SELECT 
        COALESCE(SUM(Supersede=0 AND Flag & 24=0), 0), 
        COALESCE(SUM(Supersede=0 AND Flag & 24=8), 0), 
        COALESCE(SUM(Flag is NULL OR (Supersede=0 AND Flag & 16 = 16)), 0), 
        COALESCE(SUM(Supersede=1), 0) 
    FROM 
        Dut_Info 
    WHERE 1=1{extra}";

    pub(crate) static FETCH_SELECT_WAFER_BOUNDS_STACKED: &str = "SELECT 
        max(XCOORD), min(XCOORD), max(YCOORD), min(YCOORD) 
    FROM 
        Dut_Info 
    WHERE Fid >= 0 AND WaferIndex > 0";

    pub(crate) static FETCH_SELECT_WAFER_BOUNDS_WAFER: &str = "SELECT 
        max(XCOORD), min(XCOORD), max(YCOORD), min(YCOORD) 
    FROM 
        Dut_Info 
    WHERE Fid = ? AND WaferIndex = ?";

    // Site selections arrive as a JSON array (`json_each`), so the SQL text is
    // constant and `prepare_cached` reuses one statement per variant.
    pub(crate) static FETCH_SELECT_WAFER_COORDS_SITES: &str = "SELECT 
        SBIN, XCOORD, YCOORD 
    FROM 
        Dut_Info 
    WHERE WaferIndex=?1 AND Fid=?2 AND Supersede=0 AND XCOORD IS NOT NULL 
        AND YCOORD IS NOT NULL AND SITE_NUM IN (SELECT value FROM json_each(?3))";

    pub(crate) static FETCH_SELECT_WAFER_COORDS_ALL_SITES: &str = "SELECT 
        SBIN, XCOORD, YCOORD 
    FROM 
        Dut_Info 
    WHERE WaferIndex=?1 AND Fid=?2 AND Supersede=0 AND XCOORD IS NOT NULL 
        AND YCOORD IS NOT NULL AND SITE_NUM >= 0";

    pub(crate) static FETCH_SELECT_STACKED_WAFER_SITES: &str = "SELECT 
        XCOORD, YCOORD, Flag, count(Flag) 
    FROM 
        Dut_Info 
    WHERE HEAD_NUM>=0 AND Supersede=0 AND XCOORD IS NOT NULL 
        AND YCOORD IS NOT NULL AND Flag IS NOT NULL 
        AND SITE_NUM IN (SELECT value FROM json_each(?1)) 
    GROUP By XCOORD, YCOORD, Flag";

    pub(crate) static FETCH_SELECT_STACKED_WAFER_ALL_SITES: &str = "SELECT 
        XCOORD, YCOORD, Flag, count(Flag) 
    FROM 
        Dut_Info 
    WHERE HEAD_NUM>=0 AND Supersede=0 AND XCOORD IS NOT NULL 
        AND YCOORD IS NOT NULL AND Flag IS NOT NULL AND SITE_NUM >= 0 
    GROUP By XCOORD, YCOORD, Flag";

    pub(crate) static FETCH_SELECT_DUT_INDEX_BY_HBIN: &str = "SELECT Fid, DUTIndex 
    FROM Dut_Info WHERE HBIN IN (SELECT value FROM json_each(?1)) AND Fid=?2";

    pub(crate) static FETCH_SELECT_DUT_INDEX_BY_SBIN: &str = "SELECT Fid, DUTIndex 
    FROM Dut_Info WHERE SBIN IN (SELECT value FROM json_each(?1)) AND Fid=?2";

    pub(crate) static FETCH_SELECT_DUT_INDEX_BY_XY: &str = "SELECT Fid, DUTIndex 
    FROM Dut_Info WHERE XCOORD=? AND YCOORD=?";

    pub(crate) static FETCH_SELECT_DUT_INDEX_BY_XY_WAFER: &str = "SELECT Fid, DUTIndex 
    FROM Dut_Info WHERE XCOORD=? AND YCOORD=? AND WaferIndex=? AND Fid=?";
}
