#
# DatabaseFetcher.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: May 15th 2021
# -----
# Last Modified: Wed Dec 15 2021
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


getStatus = lambda flag: "Pass" if flag & 0b00011000 == 0 else ("Failed" if flag & 0b00010000 == 0 else "Unknown")

class DatabaseFetcher:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.completeDutArray = np.array([])
    
    
    def connectDB(self, dataBasePath):
        self.closeDB()
        diskDB = sqlite3.connect(dataBasePath)
        self.connection = sqlite3.connect(":memory:")
        # move disk database to memory for faster access
        diskDB.backup(self.connection)
        diskDB.close()
        self.cursor = self.connection.cursor()
        
    
    def closeDB(self):
        if not self.connection is None:
            self.connection.close()
        
    
    def containsWafer(self):
        # return True if db contains wafer info
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        self.cursor.execute("SELECT count(*) FROM Wafer_Info")
        sqlResult = self.cursor.fetchone()
        if sqlResult:
            return sqlResult[0] > 0
        else:
            return False
    
    
    def getTestItemsList(self):
        # return test_num + testname list in db, keep original order here, do not ordered by test_num
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        self.connection.text_factory = str
        TestList = []
        for row in self.cursor.execute("SELECT TEST_NUM, TEST_NAME from Test_Info ORDER by ROWID"):
            TestList.append(f"{row[0]}\t{row[1]}")
        return TestList
    
    
    def getWaferList(self):
        # return waferIndex + waferID list in db ordered by waferIndex
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        self.connection.text_factory = str
        WaferList = ["-\tStacked Wafer Map"]
        for row in self.cursor.execute("SELECT WaferIndex, WAFER_ID from Wafer_Info ORDER by WaferIndex"):
            WaferList.append(f"#{row[0]}\t{row[1]}")
        return WaferList
    
    
    def getSiteList(self):
        # return a set of sites in db
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        SiteList = set()
        for site, in self.cursor.execute("SELECT DISTINCT SITE_NUM FROM Dut_Info"):
            SiteList.add(site)
        return SiteList

    
    def getHeadList(self):
        # return a set of heads in db
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        HeadList = set()
        for head, in self.cursor.execute("SELECT DISTINCT HEAD_NUM FROM Dut_Info"):
            HeadList.add(head)
        return HeadList
    
    
    def getPinNames(self, testNum:int, pinType:str = "RTN"):
        # return a list of dicts contains bin info
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        self.connection.text_factory = str        
        
        pinNameDict = {"PMR": [], "LOG_NAM": []}
        sql = "SELECT DISTINCT PMR_INDX, LOG_NAM FROM Pin_Map WHERE PMR_INDX in (SELECT PMR_INDX FROM TestPin_Map WHERE TEST_NUM=? AND PIN_TYPE=?)"
        sqlResult = self.cursor.execute(sql, [testNum, pinType])
        for pmr_index, logic_name in sqlResult:
            pinNameDict["PMR"].append(pmr_index)
            pinNameDict["LOG_NAM"].append("No pin name" if logic_name is None else logic_name)
            
        return pinNameDict
    
    
    def getBinInfo(self, bin="HBIN"):
        # return a list of dicts contains bin info
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        self.connection.text_factory = str
        if bin == "HBIN" or bin == "SBIN":
            BinInfoDict = {}
            for BIN_NUM, BIN_NAME, BIN_PF in self.cursor.execute('''SELECT BIN_NUM, BIN_NAME, BIN_PF FROM Bin_Info WHERE BIN_TYPE = ? ORDER by BIN_NUM''', bin[0]):
                BinInfoDict[BIN_NUM] = {"BIN_NAME": BIN_NAME, "BIN_PF": BIN_PF}
            return BinInfoDict
        else:
            raise ValueError("Bin should be 'HBIN' or 'SBIN'")
        
    
    def getBinStats(self, head, site, bin="HBIN"):
        # return (bin num, count) list
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        BinStats = {}
        sql_param = {"HEAD_NUM":head, "SITE_NUM":site}
        if bin == "HBIN" or bin == "SBIN":
            if site == -1:
                sql = f'''SELECT {bin}, count({bin}) FROM Dut_Info WHERE HEAD_NUM=:HEAD_NUM GROUP by {bin}'''
            else:
                sql = f'''SELECT {bin}, count({bin}) FROM Dut_Info WHERE HEAD_NUM=:HEAD_NUM AND SITE_NUM=:SITE_NUM GROUP by {bin}'''
                
            for bin, count in self.cursor.execute(sql, sql_param):
                BinStats[bin] = count
        else:
            raise ValueError("Bin should be 'HBIN' or 'SBIN'")
        return BinStats
    
    
    def getFileInfo(self):
        # return MIR & WCR field-value dict
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        self.connection.text_factory = str
        MIR_Info = {}
        for field, value in self.cursor.execute("SELECT * FROM File_Info"):
            MIR_Info[field] = value
        return MIR_Info
    
    
    def getTestFailCnt(self):
        if self.cursor is None: raise RuntimeError("No database is connected")
            
        TestFailCnt = {}
        for TEST_NUM, FailCount in self.cursor.execute("SELECT TEST_NUM, FailCount FROM Test_Info"):
            TestFailCnt[TEST_NUM] = FailCount
        return TestFailCnt
    
    
    def getDUT_SiteInfo(self):
        # get <dutIndex> to <site> dictionary and complete dut list for masking
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        allHeads = self.getHeadList()
        dutSiteInfo = dict( zip(allHeads, [[] for _ in range(len(allHeads))] ) )    # initalize dutSiteInfo dict, head as key, [] as value
        completeDutList = []
        
        sql = "SELECT HEAD_NUM, SITE_NUM, DUTIndex FROM Dut_Info ORDER by DUTIndex"
        sqlResult = self.cursor.execute(sql)
            
        for HEAD_NUM, SITE_NUM, DUTIndex in sqlResult:
            completeDutList.append(DUTIndex)
            for h, sl in dutSiteInfo.items():
                if h == HEAD_NUM:
                    sl.append(SITE_NUM)
                else:
                    sl.append(None)
                    
        # convert to numpy array for masking
        self.completeDutArray = np.array(completeDutList, dtype=int)
        for head, sitelist in dutSiteInfo.items():
            dutSiteInfo[head] = np.array(sitelist, dtype=float)
        
        return (self.completeDutArray, dutSiteInfo)
    
    
    def getDUT_Summary(self):
        # return a complete dut info dict where key=dutIndex and value=
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        dutInfoDict = {}
        sqlResult = None
        
        self.connection.text_factory = bytes
        sql = "SELECT * FROM Dut_Info ORDER by DUTIndex"
        sqlResult = self.cursor.execute(sql)
        
        for head, site, DUTIndex, testCount, Testtime, partID, hbin, sbin, prrFlag, waferIndex, xcoord, ycoord in sqlResult:
            # if PRR of certain DUTs is missing, testCount... will all be None
            if isinstance(prrFlag, int):
                prrStat = getStatus(prrFlag) 
                dutFlagText = f"{prrStat} - 0x{prrFlag:02x}".encode()
            else:
                dutFlagText = b"-"
                
            tmpRow = [partID if partID else b"MissingID", 
                    b"Head %d - Site %d" % (head, site),
                    b"%d" % testCount if testCount is not None else b"-",
                    b"%d ms" % Testtime if Testtime is not None else b"-",
                    b"Bin %d" % hbin if hbin is not None else b"-",
                    b"Bin %d" % sbin if sbin is not None else b"-",
                    b"%d" % waferIndex if waferIndex is not None else b"-",
                    b"(%d, %d)" % (xcoord, ycoord) if not (xcoord is None or ycoord is None) else b"-",
                    dutFlagText]
            dutInfoDict[DUTIndex] = tmpRow
            
        return dutInfoDict
    
    
    def getDUTStats(self):
        # return number of total, passed, failed 
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        statsDict = {"Total": 0, "Pass": 0, "Failed": 0, "Unknown": 0}
        for flag, count in self.cursor.execute("SELECT Flag, count(Flag) FROM Dut_Info GROUP by Flag"):
            flag = flag if isinstance(flag, int) else 0x10    # 0x10 == No pass/fail indication, force to be Unknown if flag is NAN
            dutStatus = getStatus(flag)
            statsDict[dutStatus] = statsDict[dutStatus] + count
            statsDict["Total"] = statsDict["Total"] + count
        return statsDict
    
    
    def getTestInfo_AllDUTs(self, testNum:int) -> dict:
        # return test info of all duts in the database, including offsets and length in stdf file.
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        testInfo = {}
        sqlResult = None
        # get test item's additional info
        self.connection.text_factory = str
        self.cursor.execute("SELECT * FROM Test_Info WHERE TEST_NUM=?", [testNum])
        col = [tup[0] for tup in self.cursor.description]
        val = self.cursor.fetchone()
        testInfo.update(zip(col, val))
        
        # get complete dut index first, since indexes are omitted if testNum is not tested in certain duts
        if self.completeDutArray.size == 0:
            self.getDUT_SiteInfo()
        
        # get offset & length, insert -1 if testNum is not presented in a DUT
        tmpContainer = dict(zip( self.completeDutArray, [[-1, -1]]*(self.completeDutArray.size) ))
        sql = "SELECT DUTIndex, Offset, BinaryLen FROM Test_Offsets \
            WHERE TEST_NUM=? AND DUTIndex in (SELECT DUTIndex FROM Dut_Info) \
            ORDER by DUTIndex"
        sqlResult = self.cursor.execute(sql, [testNum])
        
        # fill in the sql result in a dict where key=dutIndex, value= offset & length        
        for ind, oft, biL in sqlResult:
            tmpContainer[ind] = [oft, biL]

        totalDutCnt = self.completeDutArray.size
        tmp_oft = np.empty(totalDutCnt, dtype=np.int64)
        tmp_biL = np.empty(totalDutCnt, dtype=np.int32)
        
        for i, ind in enumerate(self.completeDutArray):
            tmp_oft[i], tmp_biL[i] = tmpContainer[ind]
        
        testInfo.update({"Offset": tmp_oft, "BinaryLen": tmp_biL})
        return testInfo
    
    
    def getTestInfo_selDUTs(self, testNum:int, selDUTs:list[int]) -> dict:
        # return test info of selected duts in the database, including offsets and length in stdf file.
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        testInfo = {}
        # get test item's additional info
        self.connection.text_factory = str
        self.cursor.execute("SELECT * FROM Test_Info WHERE TEST_NUM=?", [testNum])
        col = [tup[0] for tup in self.cursor.description]
        val = self.cursor.fetchone()
        testInfo.update(zip(col, val))
        
        # get complete dut index first, since indexes are omitted if testNum is not tested in certain duts
        if len(selDUTs) == 0:
            testInfo.update({"Offset": np.array([]), "BinaryLen": np.array([])})
            return testInfo
        
        dutCnt = len(selDUTs)
        # get offset & length, insert -1 if testNum is not presented in a DUT
        tmpContainer = dict(zip( selDUTs, [[-1, -1]] * dutCnt))
        # BUG? parameter substitution is not working, use unsafe method instead
        # sql = "SELECT DUTIndex, Offset, BinaryLen FROM Test_Offsets WHERE TEST_NUM=? AND DUTIndex in (%s) ORDER by DUTIndex" % (",".join(["?"] * dutCnt))
        # sql_param = [testNum, *selDUTs]
        
        sql = "SELECT DUTIndex, Offset, BinaryLen FROM Test_Offsets WHERE TEST_NUM=? AND DUTIndex in (%s) ORDER by DUTIndex" % (",".join([str(i) for i in selDUTs]))
        sql_param = [testNum]
        # fill in the sql result in a dict where key=dutIndex, value= offset & length        
        for ind, oft, biL in self.cursor.execute(sql, sql_param):
            tmpContainer[ind] = [oft, biL]

        tmp_oft = np.empty(dutCnt, dtype=np.int64)
        tmp_biL = np.empty(dutCnt, dtype=np.int32)
        
        for i, ind in enumerate(selDUTs):
            tmp_oft[i], tmp_biL[i] = tmpContainer[ind]
        
        testInfo.update({"Offset": tmp_oft, "BinaryLen": tmp_biL})
        return testInfo

    
    def getWaferBounds(self):
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        self.cursor.execute("SELECT max(XCOORD), min(XCOORD), max(YCOORD), min(YCOORD) FROM Dut_Info")
        sqlResult = self.cursor.fetchone()
        return dict(zip( ["xmax", "xmin", "ymax", "ymin"], sqlResult))
    
    
    def getWaferInfo(self):
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        waferDict = {}     # key: waferIndex, value: {"WAFER_ID"}
        self.connection.text_factory = str
        sqlResult = self.cursor.execute("SELECT * FROM Wafer_Info ORDER by WaferIndex")
        col = [tup[0] for tup in self.cursor.description]   # column names
        waferIndex_pos = col.index("WaferIndex")
        
        for valueList in sqlResult:
            WaferIndex = valueList[waferIndex_pos]
            valueList = ["N/A" if ele is None else ele for ele in valueList]    # Replace all None to N/A
            waferDict[WaferIndex] = dict(zip(col, valueList))
            
        return waferDict
    
    
    def getWaferCoordsDict(self, waferIndex: int, head: int, site: int) -> dict[int, list]:
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        coordsDict: dict[int, list] = {}     # key: sbin, value: coords list
        if site == -1:
            sql = "SELECT SBIN, XCOORD, YCOORD FROM Dut_Info \
                WHERE WaferIndex=? AND HEAD_NUM=? ORDER by SBIN"
            sql_param = (waferIndex, head)
        else:
            sql = "SELECT SBIN, XCOORD, YCOORD FROM Dut_Info \
                WHERE WaferIndex=? AND HEAD_NUM=? AND SITE_NUM=? ORDER by SBIN"
            sql_param = (waferIndex, head, site)
            
        for SBIN, XCOORD, YCOORD in self.cursor.execute(sql, sql_param):
            coordsDict.setdefault(SBIN, []).append((XCOORD, YCOORD))
        
        return coordsDict
    
    
    def getStackedWaferData(self, head: int, site: int) -> dict[tuple, int]:
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        failDieDistribution: dict[tuple, int] = {}     # key: coords, value: fail counts
        if site == -1:
            sql = " SELECT XCOORD, YCOORD, Flag, count(Flag) FROM Dut_Info \
                WHERE HEAD_NUM=? GROUP by XCOORD, YCOORD, Flag"
            sql_param = (head,)
        else:
            sql = "SELECT XCOORD, YCOORD, Flag, count(Flag) FROM Dut_Info \
                WHERE HEAD_NUM=? AND SITE_NUM=? GROUP by XCOORD, YCOORD, Flag"
            sql_param = (head, site)
            
        for XCOORD, YCOORD, Flag, count in self.cursor.execute(sql, sql_param):
            if isinstance(XCOORD, int) and isinstance(YCOORD, int) and isinstance(Flag, int):
                # skip invalid dut (e.g. dut without PRR)
                previousCount = failDieDistribution.setdefault((XCOORD, YCOORD), 0)
                if getStatus(Flag) == "Failed":
                    failDieDistribution[(XCOORD, YCOORD)] = previousCount + count
        
        return failDieDistribution
    
    
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
    
    
    def getDUTIndexFromXY(self, x:int, y:int, wafer_num:int) -> list:
        if self.cursor is None: raise RuntimeError("No database is connected")
        
        dutIndexList = []
        sql = "SELECT DUTIndex FROM Dut_Info WHERE XCOORD=? AND YCOORD=?" + ("" if wafer_num == -1 else " AND WaferIndex=?")
        sql_param = [x, y] + ([] if wafer_num == -1 else [wafer_num])
            
        for dutIndex, in self.cursor.execute(sql, sql_param):
            dutIndexList.append(dutIndex)
        
        return dutIndexList
    
    
    def getDynamicLimits(self, test_num:int, dutList:np.ndarray, LLimit:float, HLimit:float, limitScale:int):
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
            sql = "SELECT DUTIndex, LLimit, HLimit FROM Dynamic_Limits WHERE TEST_NUM=? AND DUTIndex in (%s) ORDER by DUTIndex" % (",".join([str(i) for i in dutList]))
            sql_param = [test_num]
                
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


if __name__ == "__main__":
    from time import time
    count = 1
    df = DatabaseFetcher()
    df.connectDB("logs/tmp.db")
    s = time()
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
    
    
    e = time()
    print((e-s)/count, "s")
    df.connection.close()