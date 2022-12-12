#
# DatabaseFetcher.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: May 15th 2021
# -----
# Last Modified: Sun Dec 11 2022
# Modified By: noonchen
# -----
# Copyright (c) 2021 noonchen
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import sqlite3
import numpy as np
from deps.SharedSrc import REC, record_name_dict, DUT_SUMMARY_QUERY, DATALOG_QUERY


commaJoin = lambda numList: ",".join(map(str, numList))


def tryDecode(b: bytes) -> str:
    '''Try to decode bytes into string using limited codesets'''
    # try decode with utf-8, compatible with ascii
    try:
        return b.decode('utf_8')
    except UnicodeDecodeError:
        pass
    # try decode with windows-1252, compatible with latin1
    try:
        return b.decode('cp1252')
    except UnicodeDecodeError:
        # decode with utf-8 and replace any unrecognized characters
        return b.decode(errors="replace")


class DatabaseFetcher:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.file_paths = []
    
    
    def connectDB(self, dataBasePath: str):
        self.closeDB()
        self.connection = sqlite3.connect(dataBasePath)
        self.connection.text_factory = tryDecode
        self.cursor = self.connection.cursor()
        self.readFilePaths()
        
    
    def closeDB(self):
        if self.connection:
            self.connection.close()
        
    
    def readFilePaths(self):
        '''read file paths stored in the database'''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        d = {}
        for fid, path in self.cursor.execute('''SELECT 
                                                    Fid, Filename 
                                                FROM 
                                                    File_List 
                                                ORDER 
                                                    By Fid, SubFid'''):
            d.setdefault(fid, []).append(path)
        
        file_paths = []
        for fid in sorted(d.keys()):
            file_paths.append(d[fid])
        self.file_paths = file_paths
        
    
    @property
    def num_files(self):
        return len(self.file_paths)
    
    
    def getWaferCount(self) -> list[int]:
        '''return a list of int, where list[file_index] = count'''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        self.cursor.execute("SELECT A.Fid, B.wafercnt FROM \
                            (SELECT DISTINCT Fid FROM File_List ) as A \
                            LEFT JOIN (SELECT Fid, count(*) as wafercnt FROM Wafer_Info GROUP by Fid) as B \
                            on A.Fid = B.Fid \
                            ORDER by A.Fid")
        result = []
        for _, wafercount in self.cursor.fetchall():
            if wafercount is None or wafercount == 0:
                result.append(0)
            else:
                result.append(wafercount)
        return result
    
    
    def getByteOrder(self) -> list[bool]:
        '''
        return a list of isLittleEndian?, indexed by file id 
        '''
        if self.cursor is None: raise RuntimeError()
        
        sql = '''SELECT 
                    (CASE WHEN Value="Little endian" 
                    THEN 1 
                    ELSE 0 END) AS "IsLB" 
                FROM 
                    File_Info 
                WHERE Field="BYTE_ORD" 
                ORDER BY Fid'''
        
        return list(map(lambda rslt: rslt[0]==1, self.cursor.execute(sql)))
    
    
    def getTestItemsList(self):
        '''return test_num + (pmr) + testname list in db in original order here'''
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        TestList = []
        for TEST_NUM, TEST_NAME, PMR_INDX in self.cursor.execute("SELECT Test_Info.TEST_NUM, Test_Info.TEST_NAME, TestPin_Map.PMR_INDX \
                                                                    FROM Test_Info \
                                                                    LEFT JOIN TestPin_Map \
                                                                    on Test_Info.TEST_ID = TestPin_Map.TEST_ID\
                                                                    ORDER by Test_Info.TEST_ID, TestPin_Map.ROWID"):
            if isinstance(PMR_INDX, int):
                # Create test items for each pin in MPR data
                item = f"{TEST_NUM}\t#{PMR_INDX}\t{TEST_NAME}"
            else:
                item = f"{TEST_NUM}\t{TEST_NAME}"
            
            # there will be duplicated items
            # if multiple files belong to a same lot/ sub lots.
            if item not in TestList:
                TestList.append(item)
            
        return TestList
    
    
    def getTestRecordTypeDict(self):
        '''return dict of (test_num, test_name) -> RecordType'''
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        recTypeDict = {}
        for TEST_NUM, TEST_NAME, recHeader in self.cursor.execute("SELECT TEST_NUM, TEST_NAME, recHeader FROM Test_Info"):
            if (TEST_NUM, TEST_NAME) in recTypeDict and recTypeDict[(TEST_NUM, TEST_NAME)] != recHeader:
                previous_rec = recTypeDict[(TEST_NUM, TEST_NAME)]
                # this test item is already registered twice with different record type, not supported
                raise ValueError(f"{TEST_NUM} {TEST_NAME} is registered as {record_name_dict[previous_rec]}, \
                    but it appears as {record_name_dict[recHeader]} again.\nIf you are opening multiple files, \
                    you should open them separately.")
            else:
                recTypeDict[(TEST_NUM, TEST_NAME)] = recHeader
        return recTypeDict
    
    
    def getWaferList(self):
        '''return waferIndex + waferID list in db ordered by waferIndex'''
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        WaferList = ["-\tStacked Wafer Map"]
        for row in self.cursor.execute("SELECT Fid, WaferIndex, WAFER_ID from Wafer_Info ORDER by WaferIndex"):
            WaferList.append(f"File{row[0]}-#{row[1]}\t{row[2]}")
        return WaferList
    
    
    def getSiteList(self):
        '''return a set of sites in db'''
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        SiteList = set()
        for site, in self.cursor.execute("SELECT DISTINCT SITE_NUM FROM Dut_Info"):
            SiteList.add(site)
        return SiteList

    
    def getHeadList(self):
        '''return a set of heads in db'''
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        HeadList = set()
        for head, in self.cursor.execute("SELECT DISTINCT HEAD_NUM FROM Dut_Info"):
            HeadList.add(head)
        return HeadList
    
    
    def getPinNames(self, testNum:int, testName:str, isRTN=True):
        '''return test pin info of a MPR or FTR, fid is used as the 
        index of the nested list.
        
        PMR -> [list]
        LOG_NAM -> [list]
        PHY_NAM -> [list]
        CHAN_NAM -> [dict]
        '''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        # must keep orignal order of PMR index, it's related to the order of values
        # Pin_Map: a table that stores all PMR records
        # TestPin_Map: a table that tracks PMR indexes that are tested in MPR or FTR
        sql = """
            SELECT 
                A.PMR_INDX, PHY_NAM, LOG_NAM, HEAD_NUM, SITE_NUM, CHAN_NAM 
            FROM 
                ((SELECT 
                    ROWID, PMR_INDX 
                FROM 
                    TestPin_Map 
                WHERE 
                    PIN_TYPE=:PIN_TYPE AND TEST_ID in 
                        (SELECT 
                            TEST_ID 
                        FROM 
                            Test_Info 
                        WHERE 
                            TEST_NUM=:TEST_NUM AND TEST_NAME=:TEST_NAME AND Fid=:Fid)) as A 
                INNER JOIN 
                    Pin_Map 
                ON 
                    A.PMR_INDX=Pin_Map.PMR_INDX AND Pin_Map.Fid=:Fid)
            ORDER BY A.ROWID"""
            
        # note: channel name is head-site dependent
        pinNameDict = {"PMR": [], "LOG_NAM": [], "PHY_NAM": [], "CHAN_NAM": []}
        pinType = "RTN" if isRTN else "PGM"
        params = {"PIN_TYPE": pinType, "TEST_NUM": testNum, "TEST_NAME": testName, "Fid": 0}
        
        for fid in range(self.num_files):
            params["Fid"] = fid
            sqlResult = self.cursor.execute(sql, params)
            tmpPMR = []
            tmpLOG = []
            tmpPHY = []
            tmpCHAN = {}
            for pmr_index, physical_name, logic_name, HEAD_NUM, SITE_NUM, channel_name in sqlResult:
                LOG_NAM = "" if logic_name is None else logic_name
                PHY_NAM = "" if physical_name is None else physical_name
                CHAN_NAM = "" if channel_name is None else channel_name
                # same pmr will loop multiple times in multi-site file, use it to detect duplicates
                if pmr_index not in tmpPMR:
                    tmpPMR.append(pmr_index)
                    tmpLOG.append(LOG_NAM)
                    tmpPHY.append(PHY_NAM)
                # channel name might be different in other sites
                tmpCHAN.setdefault( (HEAD_NUM, SITE_NUM), []).append(CHAN_NAM)
            # done with one file, append result
            pinNameDict["PMR"].append(tmpPMR)
            pinNameDict["LOG_NAM"].append(tmpLOG)
            pinNameDict["PHY_NAM"].append(tmpPHY)
            pinNameDict["CHAN_NAM"].append(tmpCHAN)
            
        return pinNameDict
    
    
    def getBinInfo(self, isHBIN=True):
        '''return a list of dicts contains bin names and pass/fail flag,
        if multiple files are opened, bin name and flag of same bin number will be merged'''
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        BinInfoDict = {}
        for BIN_NUM, BIN_NAME, BIN_PF in self.cursor.execute('''SELECT 
                                                                    BIN_NUM, BIN_NAME, BIN_PF 
                                                                FROM 
                                                                    Bin_Info 
                                                                WHERE 
                                                                    BIN_TYPE = ? 
                                                                ORDER by BIN_NUM''', "H" if isHBIN else "S"):
            BinInfoDict[BIN_NUM] = {"BIN_NAME": BIN_NAME, "BIN_PF": BIN_PF}
        return BinInfoDict
        
    
    def getBinStats(self, head, site, isHBIN=True):
        '''return a dict of bin num -> [count]'''
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        BinStats = {}
        binType = "HBIN" if isHBIN else "SBIN"
        sql_param = {"HEAD_NUM":head, "SITE_NUM":site}
        if site == -1:
            sql = f'''SELECT 
                            Fid, {binType}, count({binType}) 
                        FROM 
                            Dut_Info 
                        WHERE 
                            HEAD_NUM=:HEAD_NUM AND Supersede=0 GROUP by Fid, {binType}'''
        else:
            sql = f'''SELECT 
                            Fid, {binType}, count({binType}) 
                        FROM 
                            Dut_Info 
                        WHERE 
                            HEAD_NUM=:HEAD_NUM AND SITE_NUM=:SITE_NUM AND Supersede=0 
                        GROUP by Fid, {binType}'''
            
        for fid, bin_num, count in self.cursor.execute(sql, sql_param):
            if bin_num is None: continue
            countList = BinStats.setdefault(bin_num, [0 for _ in range(self.num_files)])
            countList[fid] = count
        return BinStats
    
    
    def getFileInfo(self):
        '''return field-value pair in File_Info table'''
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        InfoDict = {}
        sql = '''SELECT 
                    Fid, Field, Value 
                FROM 
                    File_Info 
                ORDER By 
                    Fid, Field, SubFid'''
        
        for Fid, Field, Value in self.cursor.execute(sql):
            valueList = InfoDict.setdefault(Field, [[] for _ in range(self.num_files)])
            valueList[Fid].append(Value)
            
        # convert dict value to tuple of strings
        def process(key, old_value: list) -> tuple:
            new = []
            for info_per_file in old_value:
                # info_per_file contains same field value from
                # all merged files
                # most of them are duplicated, except:
                # XX_Time and Sublot_ID
                if len(info_per_file) == 1:
                    new.append(info_per_file[0])
                elif len(info_per_file) == 0:
                    new.append(None)
                else:
                    if key in ["SETUP_T", "START_T", "FINISH_T", "SBLOT_ID"]:
                        # concat these field values by "\n"
                        new.append("\n".join([f"#{i+1} → {v}" for i, v in enumerate(info_per_file)]))
                    else:
                        # for other fields, only extract info from 1st file
                        new.append(info_per_file[0])
            return tuple(new)
        
        for key in InfoDict.keys():
            old_value = InfoDict[key]
            InfoDict[key] = process(key, old_value)
        
        return InfoDict
    
    
    def getTestFailCnt(self) -> dict:
        '''return dict of (test num, test name) -> [fail count]'''
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        TestFailCnt = {}
        for TEST_NUM, TEST_NAME, Fid, FailCount in self.cursor.execute("SELECT TEST_NUM, TEST_NAME, Fid, FailCount FROM Test_Info"):
            if not (TEST_NUM, TEST_NAME) in TestFailCnt:
                TestFailCnt[(TEST_NUM, TEST_NAME)] = [0 for _ in range(self.num_files)]
            # update nested list
            nested = TestFailCnt[(TEST_NUM, TEST_NAME)]
            nested[Fid] = FailCount
        return TestFailCnt
    
    
    def getDUTCountDict(self):
        '''return a dict of Literal[Total|Pass|Failed|Unknown|Superseded] -> [count]'''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        cntDict = {
            "Total":        [0 for _ in range(self.num_files)], 
            "Pass":         [0 for _ in range(self.num_files)], 
            "Failed":       [0 for _ in range(self.num_files)], 
            "Superseded":   [0 for _ in range(self.num_files)],
            "Unknown":      [0 for _ in range(self.num_files)], 
            }
        # total duts from all files
        for fid, count in self.cursor.execute("""SELECT 
                                                    Fid, count(*) 
                                                FROM 
                                                    Dut_Info 
                                                GROUP by Fid 
                                                ORDER by Fid"""):
            cntDict["Total"][fid] = count
        # pass duts from all files
        for fid, count in self.cursor.execute("""SELECT 
                                                    Fid, count(*) 
                                                FROM 
                                                    Dut_Info 
                                                WHERE Supersede=0 AND Flag & 24 = 0 
                                                GROUP by Fid 
                                                ORDER by Fid"""):
            cntDict["Pass"][fid] = count
        # fail duts from all files
        for fid, count in self.cursor.execute("""SELECT 
                                                    Fid, count(*) 
                                                FROM 
                                                    Dut_Info 
                                                WHERE 
                                                    Supersede=0 AND Flag & 24 = 8 
                                                GROUP by Fid 
                                                ORDER by Fid"""):
            cntDict["Failed"][fid] = count
        # fail duts from all files
        for fid, count in self.cursor.execute("""SELECT 
                                                    Fid, count(*) 
                                                FROM 
                                                    Dut_Info 
                                                WHERE 
                                                    Flag is NULL OR (Supersede=0 AND Flag & 16 = 16) 
                                                GROUP by Fid 
                                                ORDER by Fid"""):
            cntDict["Unknown"][fid] = count
        # superseded duts from all files
        for fid, count in self.cursor.execute("""SELECT 
                                                    Fid, count(*) 
                                                FROM 
                                                    Dut_Info 
                                                WHERE Supersede=1 
                                                GROUP by Fid 
                                                ORDER by Fid"""):
            cntDict["Superseded"][fid] = count
            
        return cntDict
    
    
    def getDUTCountOnConditions(self, head: int, site: int, waferid: int, fid: int):
        '''return a list of dut counts in order of [Pass|Failed|Unknown|Superseded] on the given condition'''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        head_cond = "" if head == -1 else f" AND HEAD_NUM={head}"
        site_cond = "" if site == -1 else f" AND SITE_NUM={site}"
        wfid_cond = "" if waferid == -1 else f" AND WaferIndex={waferid}"
        file_cond = "" if fid == -1 else f" AND Fid={fid}"
        
        counts = []
        # pass duts
        for count, in self.cursor.execute(f"""SELECT 
                                                count(*) 
                                            FROM 
                                                Dut_Info 
                                            WHERE 
                                                Supersede=0 AND Flag & 24=0{head_cond}{site_cond}{wfid_cond}{file_cond}"""):
            counts.append(count)
        # fail duts
        for count, in self.cursor.execute(f"""SELECT 
                                                count(*) 
                                            FROM 
                                                Dut_Info 
                                            WHERE 
                                                Supersede=0 AND Flag & 24 = 8{head_cond}{site_cond}{wfid_cond}{file_cond}"""):
            counts.append(count)
        # unknown duts
        for count, in self.cursor.execute(f"""SELECT 
                                                count(*) 
                                            FROM 
                                                Dut_Info 
                                            WHERE 
                                                Flag is NULL OR (Supersede=0 AND Flag & 16 = 16){head_cond}{site_cond}{wfid_cond}{file_cond}"""):
            counts.append(count)
        # superseded duts
        for count, in self.cursor.execute(f"""SELECT 
                                                count(*) 
                                            FROM 
                                                Dut_Info 
                                            WHERE 
                                                Supersede=1{head_cond}{site_cond}{wfid_cond}{file_cond}"""):
            counts.append(count)
            
        return counts
    
    
    def getTestInfo(self, testTup: tuple, fileId) -> dict:
        '''fetch a test info of testID from file id'''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        # get test item's additional info
        self.cursor.execute("SELECT * FROM Test_Info WHERE Fid=? AND TEST_NUM=? AND TEST_NAME=?", [fileId, *testTup])
        col = [tup[0] for tup in self.cursor.description]
        val = self.cursor.fetchone()
        if val is None:
            # when this file doesn't have
            # (test num, test name), return empty dictionary
            return {}
            
        testInfo = dict(zip(col, val))
        testInfo["LLimit"] = np.nan if testInfo["LLimit"] is None else testInfo["LLimit"]
        testInfo["HLimit"] = np.nan if testInfo["HLimit"] is None else testInfo["HLimit"]
        testInfo["LSpec"] = np.nan if testInfo["LSpec"] is None else testInfo["LSpec"]
        testInfo["HSpec"] = np.nan if testInfo["HSpec"] is None else testInfo["HSpec"]
                    
        return testInfo
    
    
    def getTestDataFromHeadSite(self, testTup: tuple, heads: list[int], sites: list[int], fileId: int) -> dict:
        '''
        return a dict contains test data, the keys are different for PTR / MPR / FTR
        PTR:    `dutList`   `dataList`  `flagList` 
        MPR:    `dutList`   `dataList`  `flagList`  `stateList`
        FTR:    `dutList`               `flagList`
        '''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        # get test ID and record type from Test_Info
        testID = None
        recHeader = None
        for tid, rh, in self.cursor.execute('''
                                            SELECT 
                                                TEST_ID, recHeader 
                                            FROM 
                                                Test_Info 
                                            WHERE Fid=? AND TEST_NUM=? AND TEST_NAME=?''', 
                                            [fileId, *testTup]):
            testID = tid
            recHeader = rh
        # if file doesn't contain this test item, return an empty dict
        if testID is None or recHeader is None:
            return {}
        
        head_condition = f" AND HEAD_NUM IN ({commaJoin(heads)})"
        if -1 in sites:
            site_condition = " AND SITE_NUM >= 0"
        else:
            site_condition = f" AND SITE_NUM IN ({commaJoin(sites)})"
        # only retrieve data from valid duts (not superseded)
        dut_condition = f''' AND DUTIndex IN (SELECT 
                                                DUTIndex 
                                            FROM 
                                                Dut_Info 
                                            WHERE Supersede=0{head_condition}{site_condition})'''
        dutList = []
        dataList = []
        flagList = []
        stateList = []
        if recHeader == REC.PTR:
            for dutIndex, rslt, flag in self.cursor.execute(f'''
                                                            SELECT
                                                                DUTIndex, RESULT, TEST_FLAG
                                                            FROM
                                                                PTR_Data
                                                            WHERE TEST_ID={testID}{dut_condition}
                                                            ORDER By DUTIndex
                                                            '''):
                dutList.append(dutIndex)
                dataList.append(rslt)
                flagList.append(flag)
            return {"dutList": np.array(dutList, dtype=np.uint32), 
                    "dataList": np.array(dataList, dtype=np.float32), 
                    "flagList": np.array(flagList, dtype=np.uint8)}
        
        elif recHeader == REC.MPR:
            for dutIndex, rslts_hex, stats_hex, flag in self.cursor.execute(f'''
                                                            SELECT
                                                                DUTIndex, RTN_RSLT, RTN_STAT, TEST_FLAG
                                                            FROM
                                                                MPR_Data
                                                            WHERE TEST_ID={testID}{dut_condition}
                                                            ORDER By DUTIndex
                                                            '''):
                dutList.append(dutIndex)
                dataList.append(np.frombuffer(bytearray.fromhex(rslts_hex), dtype=np.float32))
                stateList.append(np.frombuffer(bytearray.fromhex(stats_hex), dtype=np.uint8))
                flagList.append(flag)
            return {"dutList": np.array(dutList, dtype=np.uint32), 
                    # after transpose, row: pmr, col: dutIndex
                    "dataList": np.array(dataList).T, 
                    "stateList": np.array(stateList).T,
                    "flagList": np.array(flagList, dtype=np.uint8)}
        
        else:
            # FTR
            for dutIndex, flag in self.cursor.execute(f'''
                                                        SELECT
                                                            DUTIndex, TEST_FLAG
                                                        FROM
                                                            FTR_Data
                                                        WHERE TEST_ID={testID}{dut_condition}
                                                        ORDER By DUTIndex
                                                        '''):
                dutList.append(dutIndex)
                flagList.append(flag)
            return {"dutList": np.array(dutList, dtype=np.uint32), 
                    "flagList": np.array(flagList, dtype=np.uint8)}

    
    def getTestDataFromDutIndex(self, testTup: tuple, duts: list[int], fileId: int) -> dict:
        '''
        return a dict contains test data, the keys are different for PTR / MPR / FTR
        PTR:    `dutList`   `dataList`  `flagList` 
        MPR:    `dutList`   `dataList`  `flagList`  `stateList`
        FTR:    `dutList`               `flagList`
        
        Differs from `getTestDataFromHeadSite`, this function can get data from 
        superceded duts, and if data is not found in some duts, default data will
        be used.
        '''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        # get test ID and record type from Test_Info
        testID = None
        recHeader = None
        mprRsltCnt = 0
        for tid, rh, cnt in self.cursor.execute('''
                                            SELECT 
                                                TEST_ID, recHeader, RSLT_PGM_CNT
                                            FROM 
                                                Test_Info 
                                            WHERE Fid=? AND TEST_NUM=? AND TEST_NAME=?''', 
                                            [fileId, *testTup]):
            testID = tid
            recHeader = rh
            if cnt is not None:
                mprRsltCnt = cnt
        # if file doesn't contain this test item, return an empty dict
        if testID is None or recHeader is None:
            return {}
        
        # If the length of `duts` is too long, we will iterate all duts instead
        # and pick duts of interet during the iteration
        dutsCount = len(duts)
        if dutsCount > 128:
            # select all
            dut_condition = " AND DUTIndex > 0"
        else:
            dut_condition = f''' AND DUTIndex IN ({commaJoin(duts)})'''
        
        dutList = np.array(sorted(duts), dtype=np.uint32)
        dutMap = dict(zip(dutList, range(dutsCount)))
        maxDutIndex = np.max(dutList)
        # initiate default value, shape of dataList is related to 
        # record type, thus it is moved inside case block
        flagList = np.full(dutsCount, fill_value=-1, dtype=np.int16)
        stateList = []
        if recHeader == REC.PTR:
            dataList = np.full(dutsCount, fill_value=np.nan, dtype=np.float32)
            for dutIndex, rslt, flag in self.cursor.execute(f'''
                                                            SELECT
                                                                DUTIndex, RESULT, TEST_FLAG
                                                            FROM
                                                                PTR_Data
                                                            WHERE TEST_ID={testID}{dut_condition}
                                                            ORDER By DUTIndex
                                                            '''):
                if dutIndex > maxDutIndex: break
                elif dutIndex not in dutMap: continue
                arrayInd = dutMap[dutIndex]
                dataList[arrayInd] = rslt
                flagList[arrayInd] = flag
            return {"dutList": dutList, 
                    "dataList": dataList, 
                    "flagList": flagList}
        
        elif recHeader == REC.MPR:
            if mprRsltCnt > 0:
                dataList = np.full( (dutsCount, mprRsltCnt), fill_value=np.nan, dtype=np.float32)
                stateList = np.full( (dutsCount, mprRsltCnt), fill_value=0xF, dtype=np.uint8)
            else:
                dataList = np.array([])
                stateList = np.array([])
                
            for dutIndex, rslts_hex, stats_hex, flag in self.cursor.execute(f'''
                                                            SELECT
                                                                DUTIndex, RTN_RSLT, RTN_STAT, TEST_FLAG
                                                            FROM
                                                                MPR_Data
                                                            WHERE TEST_ID={testID}{dut_condition}
                                                            ORDER By DUTIndex
                                                            '''):
                if dutIndex > maxDutIndex: break
                elif dutIndex not in dutMap: continue
                arrayInd = dutMap[dutIndex]
                flagList[arrayInd] = flag
                if mprRsltCnt > 0:
                    dataList[arrayInd] = np.frombuffer(bytearray.fromhex(rslts_hex), dtype=np.float32)
                    stateList[arrayInd] = np.frombuffer(bytearray.fromhex(stats_hex), dtype=np.uint8)
            return {"dutList": dutList, 
                    # after transpose, row: pmr, col: dutIndex
                    "dataList": dataList.T, 
                    "stateList": stateList.T,
                    "flagList": flagList}
        
        else:
            # FTR
            for dutIndex, flag in self.cursor.execute(f'''
                                                        SELECT
                                                            DUTIndex, TEST_FLAG
                                                        FROM
                                                            FTR_Data
                                                        WHERE TEST_ID={testID}{dut_condition}
                                                        ORDER By DUTIndex
                                                        '''):
                if dutIndex > maxDutIndex: break
                elif dutIndex not in dutMap: continue
                arrayInd = dutMap[dutIndex]
                flagList[arrayInd] = flag
            return {"dutList": dutList, 
                    "flagList": flagList}
    
    
    def getWaferBounds(self, waferIndex: int, fid: int) -> tuple:
        '''
        Get min/max of xy of the given wafer
        return a tuple of
        `xmax`, `xmin`, `ymax`, `ymin`
        '''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        if waferIndex == -1:
            # -1 means stacked map, return bounds of all wafer
            condition = " Fid >= 0 AND WaferIndex > 0"
        else:
            condition = f" Fid={fid} AND WaferIndex={waferIndex}"
            
        self.cursor.execute(f'''SELECT 
                                    max(XCOORD), min(XCOORD), max(YCOORD), min(YCOORD) 
                                FROM 
                                    Dut_Info
                                WHERE
                                    {condition}''')
        return self.cursor.fetchone()
    
    
    def getWaferInfo(self):
        '''a dict contains wafer info extracted from WRR, use (wafer index, file id) as key '''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        waferDict = {}     # key: (waferIndex, fid), value: {"WAFER_ID"}
        sqlResult = self.cursor.execute("SELECT * FROM Wafer_Info ORDER by WaferIndex")
        col = [tup[0] for tup in self.cursor.description]   # column names
        fid_pos = col.index("Fid")
        waferIndex_pos = col.index("WaferIndex")
        
        for valueTuple in sqlResult:
            fid = valueTuple[fid_pos]
            waferIndex = valueTuple[waferIndex_pos]
            valueList = ["N/A" if ele is None else ele for ele in valueTuple]    # Replace all None to N/A
            waferDict[(waferIndex, fid)] = dict(zip(col, valueList))
            
        # get wafer xy direction and die ratio from File_Info
        sql = """
            SELECT
                Field, Value
            FROM
                File_Info
            WHERE
                Fid=? AND SubFid=0 AND Field in ('DIE_WID', 'DIE_HT', 'POS_X', 'POS_Y', 'WF_UNITS')
                """
        for fid in range(self.num_files):
            ext_info = {}
            for field, value in self.cursor.execute(sql, (fid,)):
                if value is None or value in ["", " "]:
                    pass
                else:
                    ext_info[field] = value
            # update all wafers of same fid
            for k, v in waferDict.items():
                if k[-1] == fid:
                    v.update(ext_info)
            
        return waferDict
    
    
    def getWaferCoordsDict(self, waferIndex: int, sites: list[int], fid: int) -> dict[int, list]:
        '''get xy of all dies in the given wafer and sites, indexed by SBIN, 
        `head` is not required since a wafer is tested on a single head'''
        
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        if -1 in sites:
            site_condition = " AND SITE_NUM >= 0"
        else:
            site_condition = f" AND SITE_NUM IN ({commaJoin(sites)})"
        
        sql = f"""
                SELECT 
                    SBIN, XCOORD, YCOORD 
                FROM 
                    Dut_Info 
                WHERE 
                    WaferIndex=? AND Fid=? AND Supersede=0 {site_condition}
                """
        sql_param = (waferIndex, fid)
        
        coordsDict = {}
        for SBIN, XCOORD, YCOORD in self.cursor.execute(sql, sql_param):
            if XCOORD is None or YCOORD is None:
                continue
            nested = coordsDict.setdefault(SBIN, {})
            nested.setdefault("x", []).append(XCOORD)
            nested.setdefault("y", []).append(YCOORD)
        
        # convert list to np.array
        for nested in coordsDict.values():
            nested["x"] = np.array(nested["x"])
            nested["y"] = np.array(nested["y"])
        
        return coordsDict
    
    
    def getStackedWaferData(self, sites: list[int]) -> dict[tuple, int]:
        '''
        get fail count of every X,Y in the database 
        (merge all STDF if opened multiple files)
        '''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        failDieDistribution: dict[tuple, int] = {}     # key: coords, value: fail counts
        
        if -1 in sites:
            site_condition = " AND SITE_NUM >= 0"
        else:
            site_condition = f" AND SITE_NUM IN ({commaJoin(sites)})"
        
        sql = f"""
            SELECT 
                XCOORD, YCOORD, Flag, count(Flag) 
            FROM 
                Dut_Info
            WHERE 
                HEAD_NUM>=0 AND Supersede=0{site_condition} 
            GROUP By 
                XCOORD, YCOORD, Flag"""
            
        for XCOORD, YCOORD, Flag, count in self.cursor.execute(sql):
            if isinstance(XCOORD, int) and isinstance(YCOORD, int) and isinstance(Flag, int):
                # skip invalid dut (e.g. dut without PRR)
                previousCount = failDieDistribution.setdefault((XCOORD, YCOORD), 0)
                if Flag & 24 == 8:
                    failDieDistribution[(XCOORD, YCOORD)] = previousCount + count
                    
        # convert to dict using fail count as key, list of xy as value
        failDict = {}
        for (x, y), count in failDieDistribution.items():
            nested = failDict.setdefault(count, {})
            nested.setdefault("x", []).append(x)
            nested.setdefault("y", []).append(y)
            
        # convert list to np.array
        for nested in failDict.values():
            nested["x"] = np.array(nested["x"])
            nested["y"] = np.array(nested["y"])
        
        return failDict
    
    
    def getDUTIndexFromBin(self, selectedBin: list) -> list:
        '''
        `selectedBin`: a list of (fid, isHBIN, [bin_num])
        
        returns list[ (File ID, DutIndex) ] that is in BIN{bin}
        '''        
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        dutIndexList = []
        
        for fid, isHBIN, binList in selectedBin:
            binType = "HBIN" if isHBIN else "SBIN"
            bin_condition = f"{binType} in ({(binList)})"
            file_condition = f" AND Fid={fid}"
            sql = f"SELECT Fid, DUTIndex FROM Dut_Info WHERE {bin_condition}{file_condition}"
            
            for fid, dutIndex, in self.cursor.execute(sql):
                d = (fid, dutIndex)
                if d not in dutIndexList:
                    dutIndexList.append(d)
        
        return dutIndexList
    
    
    def getDUTIndexFromXY(self, selectedDie: list) -> list[tuple]:
        '''
        `selectedDie`: a list of (waferInd, fid, (x, y))
        
        returns list[ (File ID, DutIndex) ] that in (X, Y)
        '''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        dutIndexList = []
        
        for waferInd, fid, (x, y) in selectedDie:
            if waferInd == -1:
                # for stacked wafermap, ignore `fid`
                # since we need to get dut index from all files
                sql = f"SELECT Fid, DUTIndex FROM Dut_Info WHERE XCOORD={x} AND YCOORD={y}"
            else:
                sql = f"SELECT Fid, DUTIndex FROM Dut_Info WHERE XCOORD={x} AND YCOORD={y} AND WaferIndex={waferInd} AND Fid={fid}"
                
            for fid, dutIndex, in self.cursor.execute(sql):
                dutIndexList.append( (fid, dutIndex) )
        
        return dutIndexList
    
    
    def getDynamicLimits(self, test_num:int, test_name:str, dutList:np.ndarray, LLimit:float, HLimit:float):
        '''
        return (dynamic llim dict, dynamic hlim dict)
        '''
        if self.cursor is None: raise RuntimeError("No database is connected")
        hasValidLow = ~np.isnan(LLimit)
        hasValidHigh = ~np.isnan(HLimit)
        hasDynamicLow = False
        hasDynamicHigh = False
        
        if hasValidLow or hasValidHigh:
            # dutIndex -> dynamic limit
            dyLLimitsDict = dict(zip(dutList, np.full(dutList.size, LLimit, np.float32)))
            dyHLimitsDict = dict(zip(dutList, np.full(dutList.size, HLimit, np.float32)))
            sql = f'''SELECT 
                        DUTIndex, LLimit, HLimit 
                    FROM 
                        Dynamic_Limits 
                    WHERE 
                        TEST_ID in (SELECT 
                                        TEST_ID 
                                    FROM 
                                        Test_Info 
                                    WHERE 
                                        TEST_NUM=? AND TEST_NAME=?) 
                        AND DUTIndex in ({commaJoin(dutList)}) 
                    ORDER by 
                        DUTIndex'''
            sql_param = [test_num, test_name]
                
            for dutIndex, dyLL, dyHL in self.cursor.execute(sql, sql_param):
                # replace the limit in the list of the same index as the dutIndex in dutList
                if hasValidLow and (dyLL is not None):
                    hasDynamicLow = True
                    dyLLimitsDict[dutIndex] = dyLL
                if hasValidHigh and (dyHL is not None):
                    hasDynamicHigh = True
                    dyHLimitsDict[dutIndex] = dyHL
                    
            # replace with empty dict if no dynamic limit
            dyLLimitsDict = dyLLimitsDict if hasDynamicLow else {}
            dyHLimitsDict = dyHLimitsDict if hasDynamicHigh else {}
            return dyLLimitsDict, dyHLimitsDict
        else:
            # return empty dict if there's no dynamic limits
            return {}, {}
    
    
    def getDTR_GDRs(self) -> list[tuple]:
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        DR_List = []
            
        for RecordType, Value, ApproxLoc in self.cursor.execute(DATALOG_QUERY):
            DR_List.append((RecordType, Value, ApproxLoc))
            
        return DR_List
    
    
    def getPartialDUTInfoOnCondition(self, heads: list[int], sites: list[int], fileId: int) -> dict:
        '''
        return a dict of dutIndex -> (part id, head-site, dut flag)
        '''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        if len(heads) == 0 or len(sites) == 0:
            return {}
        
        head_condition = f" AND HEAD_NUM in ({commaJoin(heads)})"
        site_condition = " AND SITE_NUM >= 0" if -1 in sites else f" AND SITE_NUM in ({commaJoin(sites)})"
        
        sql = f'''SELECT
                    DUTIndex,
                    PartID AS "Part ID",
                    'Head ' || HEAD_NUM || ' - ' || 'Site ' || SITE_NUM AS "Test Head - Site",
                    printf("%s - 0x%02X", CASE 
                            WHEN Supersede=1 THEN 'Superseded' 
                            WHEN Flag & 24 = 0 THEN 'Pass' 
                            WHEN Flag & 24 = 8 THEN 'Failed' 
                            ELSE 'Unknown' 
                            END, Flag) AS "DUT Flag"
                FROM Dut_Info WHERE Fid={fileId}{head_condition}{site_condition}
                ORDER By DUTIndex'''
        
        info = {}
        for dutIndex, partId, hsStr, flagStr in self.cursor.execute(sql):
            info[dutIndex] = (partId, hsStr, flagStr)
            
        return info

    
    def getFullDUTInfoFromDutArray(self, dutArray: np.ndarray, fid: int) -> dict:
        '''
        return a dict of dutIndex -> full dut info
        '''
        file_condition = f" WHERE Dut_Info.Fid={fid}"
        # dutArray might be too long to be sqlite params
        # use dict for faster filtering
        info = dict(zip(dutArray, [() for _ in range(len(dutArray))]))
        for dutIndex, *full_tup in self.cursor.execute(DUT_SUMMARY_QUERY + file_condition):
            if dutIndex in info:
                # this is the dut in `dutArray`, store
                # result in the dict
                info[dutIndex] = full_tup
        
        return info


    def getDutIndexDictFromHeadSite(self, heads: list[int], sites: list[int], fileIds: list[int]) -> dict:
        '''
        return a dict, key: File id, value: a list of DUTIndex that meets the head site condition
        '''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        dutIndexDict = {}
        if len(heads) == 0 or len(sites) == 0:
            return dutIndexDict

        file_condition = f" Fid in ({commaJoin(fileIds)})"
        head_condition = f" AND HEAD_NUM in ({commaJoin(heads)})"
        site_condition = " AND SITE_NUM >= 0" if -1 in sites else f" AND SITE_NUM in ({commaJoin(sites)})"
        
        sql = f'''SELECT 
                    Fid, DUTIndex 
                FROM 
                    Dut_Info
                WHERE {file_condition}{head_condition}{site_condition}
                ORDER By Fid, DUTIndex'''
        
        for fid, DUTIndex in self.cursor.execute(sql):
            dutIndexDict.setdefault(fid, []).append(DUTIndex)
            
        return dutIndexDict



