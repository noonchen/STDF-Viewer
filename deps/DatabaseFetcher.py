#
# DatabaseFetcher.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: May 15th 2021
# -----
# Last Modified: Sun Nov 13 2022
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
from deps.SharedSrc import record_name_dict, DUT_SUMMARY_QUERY, DATALOG_QUERY


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
    def __init__(self, num_files: int):
        self.connection = None
        self.cursor = None
        self.num_files = num_files
        # dut array from all files
        self.dutArrays = []
    
    
    def connectDB(self, dataBasePath: str):
        self.closeDB()
        self.connection = sqlite3.connect(dataBasePath)
        self.connection.text_factory = tryDecode
        self.cursor = self.connection.cursor()
        
    
    def closeDB(self):
        if not self.connection is None:
            self.connection.close()
        
    
    def getWaferCount(self) -> list[int]:
        '''return a list of int, where list[file_index] = count'''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        self.cursor.execute("SELECT A.Fid, B.wafercnt FROM \
                            (SELECT Fid FROM File_List ) as A \
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
                TestList.append(f"{TEST_NUM}\t#{PMR_INDX}\t{TEST_NAME}")
            else:
                TestList.append(f"{TEST_NUM}\t{TEST_NAME}")
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
            WaferList.append(f"File{row[0]}\t#{row[1]}\t{row[2]}")
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
        for BIN_NUM, BIN_NAME, BIN_PF in self.cursor.execute('''SELECT BIN_NUM, BIN_NAME, BIN_PF FROM Bin_Info WHERE BIN_TYPE = ? ORDER by BIN_NUM''', "H" if isHBIN else "S"):
            BinInfoDict[BIN_NUM] = {"BIN_NAME": BIN_NAME, "BIN_PF": BIN_PF}
        return BinInfoDict
        
    
    def getBinStats(self, head, site, isHBIN=True):
        '''return a dict of bin num -> [count]'''
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        BinStats = {}
        binType = "HBIN" if isHBIN else "SBIN"
        sql_param = {"HEAD_NUM":head, "SITE_NUM":site}
        if site == -1:
            sql = f'''SELECT Fid, {binType}, count({binType}) FROM Dut_Info WHERE HEAD_NUM=:HEAD_NUM AND Supersede=0 GROUP by Fid, {binType}'''
        else:
            sql = f'''SELECT Fid, {binType}, count({binType}) FROM Dut_Info WHERE HEAD_NUM=:HEAD_NUM AND SITE_NUM=:SITE_NUM AND Supersede=0 GROUP by Fid, {binType}'''
            
        for fid, bin_num, count in self.cursor.execute(sql, sql_param):
            if bin_num is None: continue
            countList = BinStats.setdefault(bin_num, [0 for _ in range(self.num_files)])
            countList[fid] = count
        return BinStats
    
    
    def getFileInfo(self):
        '''return field-value pair in File_Info table'''
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        InfoDict = {}
        # # get file count from database
        # self.cursor.execute("SELECT count(Fid) FROM File_List")
        # filecount = self.cursor.fetchone()[0]
        
        # get field data of multiple files, use `field` as key
        block1 = ", ".join([f"id{i}.Value AS File{i}" for i in range(self.num_files)])
        block2 = "\n".join([f"LEFT JOIN (SELECT * FROM File_Info WHERE Fid = {i}) as id{i} on A.Field = id{i}.Field" for i in range(self.num_files)])
        sql = f"SELECT A.Field, {block1} FROM (SELECT DISTINCT Field FROM File_Info) as A \
                {block2}"
                
        for data in self.cursor.execute(sql):
            InfoDict[data[0]] = data[1:]
        
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
    
    
    def getDUT_SiteInfo(self):
        '''return a list of dutSiteInfo dict, which 
        contains `dutIndex` to `site` information used for dut masking'''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        # clear previous dutArrays if exist, avoid duplicates
        self.dutArrays = []
        dutSiteInfoList = []
        for fid in range(self.num_files):
            headList = set()
            for head, in self.cursor.execute(f"SELECT DISTINCT HEAD_NUM FROM Dut_Info WHERE Fid={fid}"):
                headList.add(head)
            # initalize dutSiteInfo dict, head as key, [] as value
            dutSiteInfo = dict( zip(headList, [[] for _ in range(len(headList))] ) )
            completeDutList = []
            
            sql = f"SELECT HEAD_NUM, SITE_NUM, DUTIndex FROM Dut_Info WHERE Fid={fid} ORDER by DUTIndex"
            for HEAD_NUM, SITE_NUM, DUTIndex in self.cursor.execute(sql):
                completeDutList.append(DUTIndex)
                for h, sl in dutSiteInfo.items():
                    sl.append(SITE_NUM if h == HEAD_NUM else None)
                        
            # convert to numpy array for masking
            completeDutArray = np.array(completeDutList, dtype=int)
            for head, sitelist in dutSiteInfo.items():
                dutSiteInfo[head] = np.array(sitelist, dtype=float)
                
            # store dut array for other functions
            self.dutArrays.append(completeDutArray)
            dutSiteInfoList.append(dutSiteInfo)
        
        return dutSiteInfoList
    
    
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
        for fid, count in self.cursor.execute("SELECT Fid, count(*) FROM Dut_Info GROUP by Fid ORDER by Fid"):
            cntDict["Total"][fid] = count
        # pass duts from all files
        for fid, count in self.cursor.execute("SELECT Fid, count(*) FROM Dut_Info WHERE Supersede=0 AND Flag & 24 = 0 GROUP by Fid ORDER by Fid"):
            cntDict["Pass"][fid] = count
        # fail duts from all files
        for fid, count in self.cursor.execute("SELECT Fid, count(*) FROM Dut_Info WHERE Supersede=0 AND Flag & 24 = 8 GROUP by Fid ORDER by Fid"):
            cntDict["Failed"][fid] = count
        # fail duts from all files
        for fid, count in self.cursor.execute("SELECT Fid, count(*) FROM Dut_Info WHERE Flag is NULL OR (Supersede=0 AND Flag & 16 = 16) GROUP by Fid ORDER by Fid"):
            cntDict["Unknown"][fid] = count
        # superseded duts from all files
        for fid, count in self.cursor.execute("SELECT Fid, count(*) FROM Dut_Info WHERE Supersede=1 GROUP by Fid ORDER by Fid"):
            cntDict["Superseded"][fid] = count
            
        return cntDict
    
    
    def getTestInfo_AllDUTs(self, testID: tuple) -> list[dict]:
        '''return a list of test info of all duts in the database, where index is file id'''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        result = []
        for fid in range(self.num_files):
            testInfo = {}
            sqlResult = None
            # get test item's additional info
            self.cursor.execute("SELECT * FROM Test_Info WHERE Fid=? AND TEST_NUM=? AND TEST_NAME=?", [fid, *testID])
            col = [tup[0] for tup in self.cursor.description]
            val = self.cursor.fetchone()
            testInfo.update(zip(col, val))
            
            # get complete dut index first, since indexes are omitted if testNum is not tested in certain duts
            if len(self.dutArrays) == 0:
                self.getDUT_SiteInfo()
            
            # get offset & length, insert -1 if testNum is not presented in a DUT
            totalDutCnt = self.dutArrays[fid].size
            tmp_oft = np.full(totalDutCnt, -1, dtype=np.int64)
            tmp_biL = np.empty(totalDutCnt, -1, dtype=np.int32)
            
            sql = "SELECT DUTIndex, Offset, BinaryLen FROM Test_Offsets \
                WHERE TEST_ID in (SELECT TEST_ID FROM Test_Info WHERE Fid=? AND TEST_NUM=? AND TEST_NAME=?) AND \
                        DUTIndex in (SELECT DUTIndex FROM Dut_Info WHERE Fid=?) \
                ORDER by DUTIndex"
            sqlResult = self.cursor.execute(sql, [fid, *testID, fid])
            
            # dutIndex starts from 1
            for ind, oft, biL in sqlResult:
                tmp_oft[ind-1] = oft
                tmp_biL[ind-1] = biL

            testInfo.update({"Offset": tmp_oft, "BinaryLen": tmp_biL})
            result.append(testInfo)
            
        return result
    
    
    def getWaferBounds(self):
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        self.cursor.execute("SELECT max(XCOORD), min(XCOORD), max(YCOORD), min(YCOORD) FROM Dut_Info")
        sqlResult = self.cursor.fetchone()
        return dict(zip( ["xmax", "xmin", "ymax", "ymin"], sqlResult))
    
    
    def getWaferInfo(self):
        '''a dict contains wafer info extracted from WRR, use (wafer index, file id) as key '''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        waferDict = {}     # key: (waferIndex, fid), value: {"WAFER_ID"}
        sqlResult = self.cursor.execute("SELECT * FROM Wafer_Info ORDER by WaferIndex")
        col = [tup[0] for tup in self.cursor.description]   # column names
        fid_pos = col.index("Fid")
        waferIndex_pos = col.index("WaferIndex")
        
        for valueList in sqlResult:
            fid = valueList.pop(fid_pos)
            waferIndex = valueList.pop(waferIndex_pos)
            valueList = ["N/A" if ele is None else ele for ele in valueList]    # Replace all None to N/A
            waferDict[(waferIndex, fid)] = dict(zip(col, valueList))
            
        return waferDict
    
    
    def getWaferCoordsDict(self, waferIndex: int, site: int, fid: int) -> dict[int, list]:
        '''get xy of all dies in the given wafer and sites, indexed by SBIN, 
        `head` is not required since a wafer is tested on a single head'''
        
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        coordsDict: dict[int, list] = {}     # key: sbin, value: coords list
        if site == -1:
            sql = "SELECT SBIN, XCOORD, YCOORD FROM Dut_Info \
                WHERE WaferIndex=? AND Fid=? AND Supersede=0 ORDER by SBIN"
            sql_param = (waferIndex, fid)
        else:
            sql = "SELECT SBIN, XCOORD, YCOORD FROM Dut_Info \
                WHERE WaferIndex=? AND SITE_NUM=? AND Fid=? AND Supersede=0 ORDER by SBIN"
            sql_param = (waferIndex, site, fid)
            
        for SBIN, XCOORD, YCOORD in self.cursor.execute(sql, sql_param):
            coordsDict.setdefault(SBIN, []).append((XCOORD, YCOORD))
        
        return coordsDict
    
    
    def getStackedWaferData(self, head: int, site: int) -> dict[tuple, int]:
        ''' get fail count of every X,Y in the database (merge all STDF if opened multiple files) '''
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        failDieDistribution: dict[tuple, int] = {}     # key: coords, value: fail counts
        if site == -1:
            sql = " SELECT XCOORD, YCOORD, Flag, count(Flag) FROM Dut_Info \
                WHERE HEAD_NUM=? AND Supersede=0 GROUP by XCOORD, YCOORD, Flag"
            sql_param = (head,)
        else:
            sql = "SELECT XCOORD, YCOORD, Flag, count(Flag) FROM Dut_Info \
                WHERE HEAD_NUM=? AND SITE_NUM=? AND Supersede=0 GROUP by XCOORD, YCOORD, Flag"
            sql_param = (head, site)
            
        for XCOORD, YCOORD, Flag, count in self.cursor.execute(sql, sql_param):
            if isinstance(XCOORD, int) and isinstance(YCOORD, int) and isinstance(Flag, int):
                # skip invalid dut (e.g. dut without PRR)
                previousCount = failDieDistribution.setdefault((XCOORD, YCOORD), 0)
                if Flag & 24 == 8:
                    failDieDistribution[(XCOORD, YCOORD)] = previousCount + count
        
        return failDieDistribution
    
    
    #TODO
    def getDUTIndexFromBin(self, head:int, site:int, bin:int, binType:str = "HBIN") -> list:
        if self.cursor is None: raise RuntimeError("No database is connected")
        if binType != "HBIN" and binType != "SBIN": raise RuntimeError("binType should be HBIN or SBIN")
        
        dutIndexList = []
        if site == -1:
            sql = f"SELECT DUTIndex FROM Dut_Info \
                WHERE {binType}=? AND HEAD_NUM=?"
            sql_param = (bin, head)
        else:
            sql = f"SELECT DUTIndex FROM Dut_Info \
                WHERE {binType}=? AND HEAD_NUM=? AND SITE_NUM=?"
            sql_param = (bin, head, site)
            
        for dutIndex, in self.cursor.execute(sql, sql_param):
            dutIndexList.append(dutIndex)
        
        return dutIndexList
    
    
    #TODO
    def getDUTIndexFromXY(self, x:int, y:int, wafer_num:int) -> list:
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        dutIndexList = []
        sql = "SELECT DUTIndex FROM Dut_Info WHERE XCOORD=? AND YCOORD=?" + ("" if wafer_num == -1 else " AND WaferIndex=?")
        sql_param = [x, y] + ([] if wafer_num == -1 else [wafer_num])
            
        for dutIndex, in self.cursor.execute(sql, sql_param):
            dutIndexList.append(dutIndex)
        
        return dutIndexList
    
    
    #TODO
    def getDynamicLimits(self, test_num:int, test_name:str, dutList:np.ndarray, LLimit:float, HLimit:float, limitScale:int):
        if self.cursor is None: raise RuntimeError("No database is connected")
        hasValidLow = False
        hasValidHigh = False
        hasDynamicLow = False
        hasDynamicHigh = False
        if LLimit is not None: hasValidLow = True
        if HLimit is not None: hasValidHigh = True
        
        if hasValidLow or hasValidHigh:
            dut_index_dict = dict(zip(dutList, range(dutList.size)))
            if hasValidLow:
                dyLLimits = np.full(dutList.size, LLimit, np.float32)
            if hasValidHigh:
                dyHLimits = np.full(dutList.size, HLimit, np.float32)
            sql = "SELECT DUTIndex, LLimit, HLimit FROM Dynamic_Limits \
                WHERE TEST_ID in (SELECT TEST_ID FROM Test_Info WHERE TEST_NUM=? AND TEST_NAME=?) \
                    AND DUTIndex in (%s) ORDER by DUTIndex" % (",".join([str(i) for i in dutList]))
            sql_param = [test_num, test_name]
                
            for dutIndex, dyLL, dyHL in self.cursor.execute(sql, sql_param):
                # replace the limit in the list of the same index as the dutIndex in dutList
                if hasValidLow and (dyLL is not None):
                    hasDynamicLow = True
                    dyLLimits[dut_index_dict[dutIndex]] = dyLL * 10 ** limitScale
                if hasValidHigh and (dyHL is not None):
                    hasDynamicHigh = True
                    dyHLimits[dut_index_dict[dutIndex]] = dyHL * 10 ** limitScale
                    
            return hasDynamicLow, dyLLimits, hasDynamicHigh, dyHLimits
        else:
            # return empty array if all limits are None
            return hasDynamicLow, np.array([]), hasDynamicHigh, np.array([])
    
    
    def getDTR_GDRs(self) -> list[tuple]:
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        DR_List = []
            
        for RecordType, Value, ApproxLoc in self.cursor.execute(DATALOG_QUERY):
            DR_List.append((RecordType, Value, ApproxLoc))
            
        return DR_List


if __name__ == "__main__":
    from time import time
    count = 1
    df = DatabaseFetcher(3)
    df.connectDB("/Users/nochenon/Documents/GitHub/STDF-Viewer/deps/rust_stdf_helper/target/rust_test.db")
    s = time()
    # print(df.getFileInfo())
    # print(df.getDUTCountDict())
    # for _ in range(count):
    # print(df.getDUT_TestInfo(5040, HeadList=[1], SiteList=[-1]))
    
    # ** test dut site info
    # print("\n\ntest dut site info")
    # dutArray, siteInfo = df.getDUT_SiteInfo()
    # selHeads = [1]
    # selSites = [1, 22, 34]
    # mask = np.zeros(dutArray.size, dtype=bool)
    # for head in selHeads:
    #     for site in selSites:
    #         mask |= (siteInfo[head]==site)
    # print(mask)
    # print(dutArray[mask])    
    
    # ** test info selDUTs
    # print(df.getStackedWaferData(1, -1))
    
    # ** test wafer coords dict
    # print(df.getWaferCoordsDict(1, 1, 0))
    # print('\n', df.getWaferCoordsDict(1, 1, -1))
    # print('\n', df.getWaferCoordsDict(1, 255, 0))
    
    # print(df.getDUTIndexFromBin(1, -1, 2, "SBIN"))
    # print(df.getDUTIndexFromXY(40, -10, -1))
    # print(df.getDTR_GDRs())
    print(df.getPinNames(21000, "Continuty_digital_pos:passVolt_mV[1]", True))
    
    
    e = time()
    print((e-s)/count, "s")
    df.connection.close()