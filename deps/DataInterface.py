#
# StdfFile.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: November 3rd 2022
# -----
# Last Modified: Sun Dec 11 2022
# Modified By: noonchen
# -----
# Copyright (c) 2022 noonchen
# <<licensetext>>
#


import os, itertools
import numpy as np
from deps.DatabaseFetcher import DatabaseFetcher
from deps.SharedSrc import *


class DataInterface:
    '''
    `DataInterface` provides APIs for STDF-Viewer UI to retrieve
    data from database or underlying file stream.
    
    The main purpose is to decouple IO code from GUI logic...
    '''
    
    def __init__(self):
        self.DatabaseFetcher = DatabaseFetcher()
        self.file_paths = []
        self.num_files = 0
        self.dbPath = ""
        self.dbConnected = False
        self.containsWafer = False
        
        self.availableSites = []
        self.availableHeads = []
        self.testRecTypeDict = {}       # used for get test record type
        self.waferInfoDict = {}
        self.failCntDict = {}
        # self.waferOrientation = ((), ())
        # dict to store H/SBIN info
        self.HBIN_dict = {}
        self.SBIN_dict = {}
        # all test list or wafers in the database
        self.completeTestList = []
        self.completeWaferList = []
        # cache test pin list and names for MPR
        self.pinInfoDictCache = {}
        
        
    def loadDatabase(self):
        if not os.path.isfile(self.dbPath):
            raise ValueError("Invalid database path")
        
        self.DatabaseFetcher.connectDB(self.dbPath)
        self.dbConnected = True
        self.file_paths = self.DatabaseFetcher.file_paths
        self.num_files = self.DatabaseFetcher.num_files
        self.containsWafer = any(map(lambda c: c>0, self.DatabaseFetcher.getWaferCount()))
        # for site/head selection
        self.availableSites = self.DatabaseFetcher.getSiteList()
        self.availableHeads = self.DatabaseFetcher.getHeadList()        
        # get all MPR test numbers
        self.testRecTypeDict = self.DatabaseFetcher.getTestRecordTypeDict()
        # wafer info
        self.waferInfoDict = self.DatabaseFetcher.getWaferInfo()
        # update fail cnt dict
        self.failCntDict = self.DatabaseFetcher.getTestFailCnt()
        # update Bin dict
        self.HBIN_dict = self.DatabaseFetcher.getBinInfo(isHBIN=True)
        self.SBIN_dict = self.DatabaseFetcher.getBinInfo(isHBIN=False)
        # for UI display
        self.completeTestList = self.DatabaseFetcher.getTestItemsList()
        self.completeWaferList = self.DatabaseFetcher.getWaferList()
        
        
    def close(self):
        if self.dbConnected:
            # disconnect database
            self.DatabaseFetcher.closeDB()
        
        
    def getFileMetaData(self) -> list:
        metaDataList = []
        # if database is not exist,
        # return a empty list instead
        if not self.dbConnected:
            return metaDataList
        # some basic os info
        add_i_ifmany = lambda l: l if len(l) < 2 else [f"#{i+1} → {e}" for i, e in enumerate(l)]
        metaDataList.append(["File Name: ", *list(["\n".join(add_i_ifmany(list(map(os.path.basename, fg)))) for fg in self.file_paths]) ])
        metaDataList.append(["Directory Path: ", *list([os.path.dirname(fg[0]) for fg in self.file_paths]) ])
        metaDataList.append(["File Size: ", *list(["\n".join(add_i_ifmany(list(map(get_file_size, fg)))) for fg in self.file_paths]) ])
        # dut summary
        dutCntDict = self.DatabaseFetcher.getDUTCountDict()
        metaDataList.append(["Yield: ", *[f"{100*p/(p+f) :.2f}%" if (p+f)!=0 else "?" for (p, f) in zip(dutCntDict["Pass"], dutCntDict["Failed"])] ])
        metaDataList.append(["DUTs Tested: ", *[str(n) for n in dutCntDict["Total"]] ])
        metaDataList.append(["DUTs Passed: ", *[str(n) for n in dutCntDict["Pass"]] ])
        metaDataList.append(["DUTs Failed: ", *[str(n) for n in dutCntDict["Failed"]] ])
        metaDataList.append(["DUTs Superseded: ", *[str(n) for n in dutCntDict["Superseded"]] ])
        metaDataList.append(["DUTs Unknown: ", *[str(n) for n in dutCntDict["Unknown"]] ])
        # MIR Record data
        InfoDict = self.DatabaseFetcher.getFileInfo()
        for fn in mirFieldNames:
            value: tuple = InfoDict.pop(fn, ())
            if value == (): 
                # skip non-existed MIR fields
                continue
            metaDataList.append([f"{mirDict[fn]}: ", *[v if v is not None else "" for v in value] ])
        if self.containsWafer:
            metaDataList.append(["Wafers Tested: ", *list(map(str, self.DatabaseFetcher.getWaferCount())) ])
            wafer_unit_tuple = InfoDict.pop("WF_UNITS", ["" for _ in range(self.num_files)])
            if "WAFR_SIZ" in InfoDict:
                wafer_size_tuple = InfoDict.pop("WAFR_SIZ")
                metaDataList.append(["Wafer Size: ", 
                                     *[f"{size} {unit}" 
                                       if size is not None and unit is not None 
                                       else "" 
                                       for (size, unit) in zip(wafer_size_tuple, wafer_unit_tuple)] ])
            if "DIE_WID" in InfoDict and "DIE_HT" in InfoDict:
                wid_tuple = InfoDict.pop("DIE_WID")
                ht_tuple = InfoDict.pop("DIE_HT")
                metaDataList.append(["Wafer Die Width Height: ", 
                                     *[f"{wid} {unit} × {ht} {unit}" 
                                       if wid is not None and ht is not None and unit is not None 
                                       else "" 
                                       for (wid, ht, unit) in zip(wid_tuple, ht_tuple, wafer_unit_tuple)] ])
            if "CENTER_X" in InfoDict and "CENTER_Y" in InfoDict:
                cent_x_tuple = InfoDict.pop("CENTER_X")
                cent_y_tuple = InfoDict.pop("CENTER_Y")
                metaDataList.append(["Wafer Center: ", 
                                     *[f"({x}, {y})" 
                                       if x is not None and y is not None 
                                       else "" 
                                       for (x, y) in zip(cent_x_tuple, cent_y_tuple)] ])
            if "WF_FLAT" in InfoDict:
                flat_orient_tuple = InfoDict.pop("WF_FLAT")
                metaDataList.append(["Wafer Flat Direction: ", 
                                     *[wafer_direction_name(d) 
                                       if d is not None 
                                       else "" 
                                       for d in flat_orient_tuple] ])
            if "POS_X" in InfoDict and "POS_Y" in InfoDict:
                pos_x_tuple = InfoDict.pop("POS_X")
                pos_y_tuple = InfoDict.pop("POS_Y")
                self.waferOrientation = (pos_x_tuple, pos_y_tuple)
                metaDataList.append(["Wafer XY Direction: ", 
                                     *[f"({wafer_direction_name(x_orient)}, {wafer_direction_name(y_orient)})" 
                                       if x_orient is not None and y_orient is not None 
                                       else "" 
                                       for (x_orient, y_orient) in zip(pos_x_tuple, pos_y_tuple)] ])
        # append other info: ATR, RDR, SDRs, sort names for better display
        for propertyName in sorted(InfoDict.keys()):
            value: tuple = InfoDict[propertyName]
            metaDataList.append([f"{propertyName}: ", *[v if v is not None else "" for v in value]])
        
        return metaDataList
        
    
    def checkTestPassFail(self, testTuple: tuple) -> bool:
        '''
        For fail marker
        check the failcount of testTuple in all files.
        if failcount == -1, parse flagList and update count dict
        if failcount == 0, returns True
        '''
        testID = (testTuple[0], testTuple[-1])
        failCntList = self.failCntDict[testID]
        for fid, fcnt in enumerate(failCntList):
            if fcnt == -1:
                # TSR doesn't contains
                # fail count of this test
                # parse flagList manually
                testData = self.getTestDataFromHeadSite(testTuple, 
                                                        self.availableHeads, 
                                                        self.availableSites, 
                                                        fid)
                flagList = testData.get("flagList", [])
                fcnt = sum(map(lambda f: 1 if f & 24 == 8 else 0, 
                               flagList))
                # update count
                failCntList[fid] = fcnt
        
        return all(map(lambda c: c==0, failCntList))
    
    
    def getTestCpkList(self, testTuple: tuple) -> list:
        '''
        For fail marker
        calculate Cpk of given testTuple from all heads/sites/files
        '''
        cpkList = []
        for fid, head, site in itertools.product(range(self.num_files), 
                                                 self.availableHeads, 
                                                 self.availableSites):
            testData = self.getTestDataFromHeadSite(testTuple, 
                                                    [head], 
                                                    [site], 
                                                    fid)
            cpkList.append(testData.get("Cpk", np.nan))
        return cpkList
    
    
    def testDataProcessCore(self, testTuple: tuple, testInfo: dict, testData: dict, FileID: int) -> dict:
        '''
        Merge data and calculate statistic, or index PMR result from complete MPR
        
        `testTuple`: contains test number, pin index (valid for MPR) and name, e.g. (1000, 1, "name")
        `testInfo`: info of `testTuple`, from DatabaseFetcher `getTestInfo`
        `testData`: data of `testTuple`, from DatabaseFetcher `getTestDataFromHeadSite` or `getTestDataFromDutIndex`
        `FileID`: index of loaded files
        
        return a dictionary contains:
        `TEST_NAME` / `TEST_NUM` / `flagList` / 
        `LLimit` / `HLimit` / `Unit` / `dataList` / `DUTIndex` / 
        `LSpec` / `HSpec` / `OPT_Flag` / `VECT_NAM` / `SEQ_NAME`
        `Min` / `Max` / `Median` / `Mean` / `SDev` / `Cpk`
        '''
        outData = {}
        if len(testInfo) == 0 or len(testData) == 0:
            # if current file doesn't contain this testID
            # return empty dict
            return outData
        
        test_num, pmr, test_name = testTuple
        outData.update(testInfo)
        recHeader = testInfo["recHeader"]
        # store original for testID lookup
        outData["TEST_NAME_ORIG"] = test_name
        outData["dutList"] = testData["dutList"]
        outData["flagList"] = testData["flagList"]
        
        if recHeader == REC.MPR:
            # append pmr# to test name
            if pmr > 0: 
                outData["TEST_NAME"] = f"{test_name} #{pmr}"
            # get MPR complete pin list and names
            cacheKey = (test_num, test_name, "RTN")
            if cacheKey in self.pinInfoDictCache:
                pinInfoDict = self.pinInfoDictCache[cacheKey]
            else:
                # read and cache from database if not found
                pinInfoDict = self.DatabaseFetcher.getPinNames(*cacheKey)
                self.pinInfoDictCache[cacheKey] = pinInfoDict
            # if pmr in TestPin_Map is not found in Pin_Map, 
            # the following value in pinInfoDict is empty
            PMR_list = pinInfoDict["PMR"][FileID]
            LOG_NAM_list = pinInfoDict["LOG_NAM"][FileID]
            PHY_NAM_list = pinInfoDict["PHY_NAM"][FileID]
            CHAN_NAM_dict = pinInfoDict["CHAN_NAM"][FileID]
            # get test data of current PMR
            try:
                # the index of test value is the same as the index of {pmr} in PMR list
                dataIndex = PMR_list.index(pmr)
                # channel name differs from sites, get possible (head, site) first
                ChanNames = []
                for (h, s) in testInfo["HeadSite"]:
                    if s == -1:
                        # all sites, match any sites
                        for (_h, _), cnlist in CHAN_NAM_dict.items():
                            if h == _h:
                                cn, = cnlist[dataIndex:dataIndex+1] or [""]
                                ChanNames.append(cn)
                        continue
                    if (h, s) in CHAN_NAM_dict:
                        cnlist = CHAN_NAM_dict[(h, s)]
                        cn, = cnlist[dataIndex:dataIndex+1] or [""]
                        ChanNames.append(cn)

                outData["CHAN_NAM"] = ";".join([cn for cn in ChanNames if cn != ""])
                outData["LOG_NAM"] = LOG_NAM_list[dataIndex]
                outData["PHY_NAM"] = PHY_NAM_list[dataIndex]
                outData["dataList"] = testData["dataList"][dataIndex]
                outData["stateList"] = testData["stateList"][dataIndex]
            except (ValueError, IndexError) as e:
                outData["CHAN_NAM"] = ""
                outData["LOG_NAM"] = ""
                outData["PHY_NAM"] = ""
                outData["dataList"] = np.array([])
                outData["stateList"] = np.array([])
                if isinstance(e, IndexError):
                    print(f"Cannot found test data of PMR {pmr} in MPR test {test_num}")
                else:
                    if pmr != 0:
                        # pmr != 0 indicates a valid pmr
                        print(f"PMR {pmr} is not found in {test_num}'s PMR list")
        elif recHeader == REC.PTR:
            outData["dataList"] = testData["dataList"]
        else:
            # FTR doesn't have `data`, use flag instead
            outData["dataList"] = testData["flagList"]
        
        # get statistics
        if outData["dataList"].size > 0 and not np.all(np.isnan(outData["dataList"])):
            outData["Min"] = np.nanmin(outData["dataList"])
            outData["Max"] = np.nanmax(outData["dataList"])
            outData["Median"] = np.nanmedian(outData["dataList"])
        else:
            # functions above throw error on empty array,
            # manually set to nan
            outData["Min"] = np.nan
            outData["Max"] = np.nan
            outData["Median"] = np.nan
                
        outData["Mean"], outData["SDev"], outData["Cpk"] = calc_cpk(outData["LLimit"], 
                                                                    outData["HLimit"], 
                                                                    outData["dataList"])
        return outData
    
    
    def getTestDataFromHeadSite(self, testTuple: tuple, selectHeads:list[int], selectSites:list[int], FileID: int) -> dict:
        '''
        Get parsed data of the given testTuple, test duts are constrained by heads & sites & fid
        
        `testTuple`: contains test number, pin index (valid for MPR) and name, e.g. (1000, 1, "name")
        `selectHeads`: list of selected STDF heads
        `selectSites`: list of selected STDF sites
        `FileID`: index of loaded files
        
        return a dictionary contains:
        see `testDataProcessCore`
        '''
        # testID -> (test_num, test_name)
        testID = (testTuple[0], testTuple[-1])
        testInfo = self.DatabaseFetcher.getTestInfo(testID, FileID)
        if len(testInfo) == 0:
            return {}
        # add (head, site) list to testInfo for MPR
        # it will be used for indexing channel name dict
        if testInfo["recHeader"] == REC.MPR:
            testInfo["HeadSite"] = set(itertools.product(selectHeads, 
                                                         [-1] if -1 in selectSites else selectSites))
        testData = self.DatabaseFetcher.getTestDataFromHeadSite(testID, 
                                                                selectHeads, 
                                                                selectSites, 
                                                                FileID)
        
        return self.testDataProcessCore(testTuple, testInfo, testData, FileID)
    
    
    def getTestDataFromDutIndex(self, testTuple: tuple, selectedDutIndex: list, FileID: int) -> dict:
        '''
        Get parsed data of the given testTuple, test duts are constrained by heads & sites & fid
        
        `testTuple`: contains test number, pin index (valid for MPR) and name, e.g. (1000, 1, "name")
        `dutMask`: mask for filtering duts of interest from the complete dutArray
        
        return a dictionary contains:
        see `getTestDataCore`
        '''
        # testID -> (test_num, test_name)
        testID = (testTuple[0], testTuple[-1])
        testInfo = self.DatabaseFetcher.getTestInfo(testID, FileID)
        if len(testInfo) == 0:
            return {}        
        # add (head, site) list to testInfo for MPR
        # it will be used for indexing channel name dict
        # 
        # but channel name is only displayed in statistic table
        # this function is used only in `getDutSummaryWithTestDataCore`
        # we can simply skip this logic
        if testInfo["recHeader"] == REC.MPR:
            testInfo["HeadSite"] = set()
        testData = self.DatabaseFetcher.getTestDataFromDutIndex(testID, 
                                                                selectedDutIndex,
                                                                FileID)
        
        return self.testDataProcessCore(testTuple, testInfo, testData, FileID)
    
    
    def getTestDataTableContent(self, testTuples: list[tuple], selectHeads:list[int], selectSites:list[int], _selectFiles: list[int] = None) -> dict:
        '''
        Get all required test data for TestDataTable display
        
        `testTuples`: list of selected tests, e.g. [(1000, 1, "name"), ...] 
        `selectHeads`: list of selected STDF heads
        `selectSites`: list of selected STDF sites
        `_selectFiles`: default read all files, currently not in use
        
        return a dictionary contains:
        `VHeader`: dut index as vertical header
        `TestLists`: testTuples, for ordering
        `Data`: dict, key: testTuple, value: fid -> dict from `getTestDataCore`
        `TestInfo`: dict, key: testTuple, value: list of info
        `dut2ind`: fid -> map of dutIndex to list index
        `dutInfo`: fid -> map of dutIndex to info tuple
        '''
        data = {}
        testInfo = {}
        dutIndexDict = {}
        for testTup, fid in itertools.product(testTuples, range(self.num_files)):
            test_fid = self.getTestDataFromHeadSite(testTup, selectHeads, selectSites, fid)
            if ("TEST_NAME" in test_fid) and (testTup not in testInfo):
                testInfo[testTup] = [test_fid.pop("TEST_NAME"), 
                                     test_fid.pop("TEST_NUM"),
                                     test_fid.pop("HLimit"),
                                     test_fid.pop("LLimit"),
                                     test_fid.pop("Unit")]
            if ("dutList" in test_fid) and (fid not in dutIndexDict):
                dutIndexDict[fid] = test_fid.pop("dutList")
            nest = data.setdefault(testTup, {})
            nest[fid] = test_fid
        
        vheader = []
        dutInfo = {}
        dut2ind = {}
        for fid in range(self.num_files):
            if fid in dutIndexDict:
                vheader.extend(map(lambda i: f"File{fid} #{i}", dutIndexDict[fid]))
                dut2ind[fid] = dict(zip(dutIndexDict[fid], 
                                        range(len(dutIndexDict[fid]))
                                        ))
                # add dict of dut index -> (part id, head site, dut flag)
                dutInfo[fid] = self.DatabaseFetcher.getPartialDUTInfoOnCondition(selectHeads, 
                                                                                 selectSites, 
                                                                                 fid)
            else:
                # fid doesn't contain any tests in testTuples
                dut2ind[fid] = {}
                dutInfo[fid] = {}
                
        return {"VHeader": vheader, 
                "TestLists": testTuples, 
                "Data": data, 
                "TestInfo": testInfo, 
                "dut2ind": dut2ind,
                "dutInfo": dutInfo}
    
    
    def getDutSummaryWithTestDataCore(self, testTuples: list[tuple], dutIndexDict: dict) -> dict:
        '''
        Get all required test data for Dut Data Table or Report generator. Differ
        from `getTestDataTableContent`, `dutInfo` returned by this function is "full version",
        file id and dut of interest are determined by user's selection on the GUI. 
        This function will always return dut info even if `testsTuples` is empty. 
        
        `testTuples`: list of selected tests, e.g. [(1000, 1, "name"), ...] 
        `dutMaskDict`: dict, key: file id, value: dutIndex list
        
        return a dictionary contains:
        `VHeader`: dut index as vertical header
        `TestLists`: testTuples, for ordering
        `Data`: dict, key: testTuple, value: fid -> dict from `getTestDataCore`
        `TestInfo`: dict, key: testTuple, value: list of info
        `dut2ind`: fid -> map of dutIndex to list index
        `dutInfo`: fid -> map of dutIndex to dut summary
        '''
        data = {}
        testInfo = {}
        for testTup, fid in itertools.product(testTuples, sorted(dutIndexDict.keys())):
            dutIndexList = dutIndexDict[fid]
            test_fid = self.getTestDataFromDutIndex(testTup, dutIndexList, fid)
            if ("TEST_NAME" in test_fid) and (testTup not in testInfo):
                testInfo[testTup] = [test_fid.pop("TEST_NAME"), 
                                     test_fid.pop("TEST_NUM"),
                                     test_fid.pop("HLimit"),
                                     test_fid.pop("LLimit"),
                                     test_fid.pop("Unit")]
                # already obtained the dutIndexList
                test_fid.pop("dutList")
            nest = data.setdefault(testTup, {})
            nest[fid] = test_fid
        
        vheader = []
        dutInfo = {}
        dut2ind = {}
        for fid in sorted(dutIndexDict.keys()):
            dutIndexList = sorted(dutIndexDict[fid])
            vheader.extend(map(lambda i: f"File{fid} #{i}", dutIndexList))
            dut2ind[fid] = dict(zip(dutIndexList, range(len(dutIndexList))))
            # add dict of dut index -> (part id, head site, ..., dut flag)
            dutInfo[fid] = self.DatabaseFetcher.getFullDUTInfoFromDutArray(dutIndexList, fid)
                
        return {"VHeader": vheader, 
                "TestLists": testTuples, 
                "Data": data, 
                "TestInfo": testInfo, 
                "dut2ind": dut2ind,
                "dutInfo": dutInfo}
        
        
    def getDutDataDisplayerContent(self, selectedDutIndex: list) -> dict:
        '''
        Wrapper of `getDutSummaryWithTestDataCore`, converts selectedDutIndex
        to dutMaskDict
        
        return a dict, see `getDutSummaryWithTestDataCore`
        '''
        testTuples = [parseTestString(t, False) for t in self.completeTestList]
        dutIndexDict = {}
        for fid, dutIndex in selectedDutIndex:
            dutIndexDict.setdefault(fid, []).append(dutIndex)
        
        return self.getDutSummaryWithTestDataCore(testTuples, dutIndexDict)
    
    
    def getDutSummaryReportContent(self,  testTuples: list[tuple], selectHeads:list[int], selectSites:list[int], selectFiles: list[int]) -> dict:
        '''
        For Report generation
        Wrapper of `getDutSummaryWithTestDataCore`, converts heads and sites to {fid -> [dutIndex]}
        
        return a dict, see `getDutSummaryWithTestDataCore`
        '''
        dutIndexDict = self.DatabaseFetcher.getDutIndexDictFromHeadSite(selectHeads, selectSites, selectFiles)        
        return self.getDutSummaryWithTestDataCore(testTuples, dutIndexDict)
    
    
    def getTestStatistics(self, testTuples: list[tuple], selectHeads:list[int], selectSites:list[int], _selectFiles: list[int] = None):
        '''
        Generate data of `Test Statistic` table when `Trend`/`Histo`/`Info` tab is activated
        
        `testTuples`: list of selected tests, e.g. [(1000, 1, "name"), ...] 
        `selectHeads`: list of selected STDF heads
        `selectSites`: list of selected STDF sites
        `_selectFiles`: default read all files, currently not in use
        
        return a dictionary contains:
        `VHeader`: list, vertial header
        `HHeader`: list, horizontal header
        `Rows`: list[list], statistic data
        '''
        ## HHeader
        hHeaderLabels = ["Test Name", "Unit", "Low Limit", "High Limit", 
                        "Fail Num", "Cpk", "Average", "Median", 
                        "St. Dev.", "Min", "Max"]
        # if MPR or FTR is in selected tests, add columns for them as well
        testRecTypes = set([self.testRecTypeDict[ (test_num, test_name) ] for test_num, _, test_name in testTuples])
        containsFTR = REC.FTR in testRecTypes
        containsMPR = REC.MPR in testRecTypes
        if containsFTR: hHeaderLabels[1:1] = ["Pattern Name"]
        if containsMPR: hHeaderLabels[1:1] = ["PMR Index", "Logical Name", "Physical Name", "Channel Name"]
        ## VHeader
        vHeaderLabels = []
        ## Rows
        rowList = []
        
        # TODO Configurable order of rows?
        default_order = [testTuples, selectHeads, selectSites, range(self.num_files)]
        floatFormat = getSetting().getFloatFormat()
        for testTup, head, site, fid in itertools.product(*default_order):
            testDataDict = self.getTestDataFromHeadSite(testTup, [head], [site], fid)
            # if current file doesn't have testID, 
            # `testDataDict` will be emtpy
            if testDataDict:
                test_num, pmr, test_name = testTup
                # if there is only one file, hide file index
                vHeaderLabels.append("{} / Head{} / {}{}".format(test_num, 
                                                                 head, 
                                                                 "All Sites" if site == -1 else f"Site{site}",
                                                                 "" if self.num_files == 1 else f" / File{fid}"))
                # basic PTR stats
                CpkString = "%s" % "∞" if testDataDict["Cpk"] == np.inf else ("N/A" if np.isnan(testDataDict["Cpk"]) else floatFormat % testDataDict["Cpk"])                
                row =  [test_name,
                        testDataDict["Unit"],
                        "N/A" if np.isnan(testDataDict["LLimit"]) else floatFormat % testDataDict["LLimit"],
                        "N/A" if np.isnan(testDataDict["HLimit"]) else floatFormat % testDataDict["HLimit"],
                        "%d" % list(map(isPass, testDataDict["flagList"])).count(False),
                        CpkString,
                        floatFormat % testDataDict["Mean"],
                        floatFormat % testDataDict["Median"],
                        floatFormat % testDataDict["SDev"],
                        floatFormat % testDataDict["Min"],
                        floatFormat % testDataDict["Max"]]
                # match the elements of hHeader
                if containsFTR:
                    row[1:1] = [testDataDict["VECT_NAM"]] if testDataDict["recHeader"] == REC.FTR else [""]
                if containsMPR:
                    row[1:1] = [str(pmr), 
                                testDataDict["LOG_NAM"], 
                                testDataDict["PHY_NAM"], 
                                testDataDict["CHAN_NAM"]] if testDataDict["recHeader"] == REC.MPR else ["", "", "", ""]
                    
                rowList.append(row)
            else:
                # if this file doesn't contain this
                # testTup, skip
                continue
        
        return {"VHeader": vHeaderLabels, "HHeader": hHeaderLabels, "Rows": rowList}
    
    
    def getBinStatistics(self, selectHeads:list[int], selectSites:list[int], _selectFiles: list[int] = None):
        '''
        Generate HBIN/SBIN distribution of selected heads and sites
        
        `selectHeads`: list of selected STDF heads
        `selectSites`: list of selected STDF sites
        `_selectFiles`: default read all files, currently not in use
        
        return a dictionary contains:
        `VHeader`: list, vertial header
        `Rows`: 2D list, element = (data, bin_num, isHBIN)
        `maxLen`: maximum column length
        '''
        ## VHeader
        vHeaderLabels = []
        ## Rows
        rowList = []
        ## maxLen
        maxLen = 0
        
        default_order = [["H", "S"], selectHeads, selectSites, range(self.num_files)]
        for binType, head, site, fid in itertools.product(*default_order):
            isHbin: bool = binType == "H"
            binFullName = "Hardware Bin" if isHbin else "Software Bin"
            binInfoDict = self.HBIN_dict if isHbin else self.SBIN_dict

            vHeaderLabels.append( "{}{} / Head{} / {}".format("" if self.num_files == 1 else f"File{fid} / ",
                                                              binFullName, 
                                                              head, 
                                                              "All Sites" if site == -1 else f"Site{site}"))
            # isHbinList.append(isHbin)
            # preparations for calculation
            binSummary = self.DatabaseFetcher.getBinStats(head, site, isHbin)
            totalBinCnt = sum([cntList[fid] for _, cntList in binSummary.items()])
            row = []
            # add yield and dut counts in the row
            counts = self.DatabaseFetcher.getDUTCountOnConditions(head, site, -1, fid)
            row.append((f"Yield: {100*counts[0]/(counts[0]+counts[1]):.2f}%", -1, isHbin))
            row.append((f"Total: {sum(counts)}", -1, isHbin))
            for (n, c) in zip(["Pass", "Failed", "Unknown", "Superseded"], counts):
                row.append((f"{n}: {c}", -1, isHbin))
            # iter thru binSummary, calculate percentage of each bin
            for bin_num in sorted(binSummary.keys()):
                bin_cnt = binSummary[bin_num][fid]
                if bin_cnt == 0: 
                    continue
                bin_name = binInfoDict.get(bin_num, {}).get("BIN_NAME", "NO NAME")
                item = ("{}\nBin{}: {:.1f}%".format(bin_name, 
                                                    bin_num, 
                                                    100*bin_cnt/totalBinCnt), 
                        bin_num,
                        isHbin)
                row.append(item)
            rowList.append(row)
            maxLen = max(maxLen, len(row))
            
        return {"VHeader": vHeaderLabels, "Rows": rowList, "maxLen": maxLen}
    
    
    def getWaferStatistics(self, waferTuples: list[tuple], selectSites:list[int]):
        '''
        Generate wafer statistics and SBIN distribution
        
        `waferTuples`: (wafer index, file id, wafer name)
        `selectSites`: list of selected STDF sites
        
        return a dictionary contains:
        `VHeader`: list, vertial header
        `Rows`: 2D list, element = (data, bin_num, isHBIN)
        `maxLen`: maximum column length
        '''
        ## VHeader
        vHeaderLabels = []
        ## Rows
        rowList = []
        ## maxLen
        maxLen = 0
        
        for waferTuple, site in itertools.product(waferTuples, selectSites):
            waferIndex, fid, _ = waferTuple
            if waferIndex == -1:
                # stacked wafer, only contains fail count info, skip for now...
                # TODO may be we can calculate some data for stacked wafer?
                continue
            
            vHeaderLabels.append("{}#{} / {}".format("" if self.num_files == 1 else f"File{fid} / ",
                                                     waferIndex, 
                                                     "All Sites" if site == -1 else f"Site{site}"))
            coordsDict = self.DatabaseFetcher.getWaferCoordsDict(waferIndex, [site], fid)
            totalDies = sum([len(xyDict["x"]) for xyDict in coordsDict.values()])
            row = []
            # add yield and dut counts in the row
            counts = self.DatabaseFetcher.getDUTCountOnConditions(-1, site, waferIndex, fid)
            row.append((f"Yield: {100*counts[0]/(counts[0]+counts[1]):.2f}%", -1, False))
            row.append((f"Total: {sum(counts)}", -1, False))
            for (n, c) in zip(["Pass", "Failed", "Unknown", "Superseded"], counts):
                row.append((f"{n}: {c}", -1, False))
            # add wafer infos
            for k in ["WAFER_ID", "FABWF_ID", "FRAME_ID", "MASK_ID"]:
                v = self.waferInfoDict[(waferIndex, fid)].get(k, "")
                if v != "":
                    row.append((f"{k}: {v}", -1, False))
            # soft bin only
            for sbin_num in sorted(coordsDict.keys()):
                sbin_cnt = len(coordsDict[sbin_num]["x"])
                if sbin_cnt == 0: 
                    continue
                sbin_name = self.SBIN_dict.get(sbin_num, {}).get("BIN_NAME", "NO NAME")
                item = ("{}\nBin{}: {:.1f}%".format(sbin_name, 
                                                    sbin_num, 
                                                    100*sbin_cnt/totalDies), 
                        sbin_num,
                        False)
                row.append(item)
            rowList.append(row)
            maxLen = max(maxLen, len(row))
        
        return {"VHeader": vHeaderLabels, "Rows": rowList, "maxLen": maxLen}    


    def getTrendChartData(self, testTuple: tuple, head: int, selectSites: list[int], _selectFiles: list[int] = None) -> dict:
        '''
        Get single-head, multi-site trend chart data of ONE test item
        
        `testTuple`:  selected test, e.g. (1000, 1, "name")
        `head`: a selected STDF head
        `selectSites`: list of selected STDF sites
        `_selectFiles`: default read all files, currently not in use
        
        return a dictionary contains:
        `TestInfo`: dict, key: file id, value: infoDict
        `Data`: dict[dict[dict]], e.g.
                Fid0 -> {Site0 -> testDataDict
                         Site1 -> testDataDict
                         ...}
                Fid1 -> {Site0 -> testDataDict
                         Site1 -> testDataDict
                         ...}
        '''
        data = {}
        testInfo = {}
        for fid, site in itertools.product(range(self.num_files), selectSites):
            sitesDict = data.setdefault(fid, {})
            infoDict: dict = testInfo.setdefault(fid, {})
            # retrieve single site data only
            test_site_fid = self.getTestDataFromHeadSite(testTuple, [head], [site], fid)
            if len(test_site_fid) == 0:
                # skip this site if no data
                continue
            nestSiteData = sitesDict.setdefault(site, {})
            # store all site related data to be drawn
            nestSiteData["Min"] = test_site_fid.pop("Min")
            nestSiteData["Max"] = test_site_fid.pop("Max")
            nestSiteData["Mean"] = test_site_fid.pop("Mean")
            nestSiteData["Median"] = test_site_fid.pop("Median")
            # filter out nan from dataList
            dataOrig = test_site_fid.pop("dataList")
            validMask = ~np.isnan(dataOrig)
            nestSiteData["dataList"] = dataOrig[validMask]
            nestSiteData["dutList"] = test_site_fid.pop("dutList")[validMask]
            nestSiteData["flagList"] = test_site_fid.pop("flagList")[validMask]
            if test_site_fid["recHeader"] == REC.MPR:
                nestSiteData["stateList"] = test_site_fid.pop("stateList")[validMask]
            elif test_site_fid["recHeader"] == REC.PTR:
                # dynamic limit
                dyL, dyH = self.DatabaseFetcher.getDynamicLimits(test_site_fid["TEST_NUM"],
                                                                 test_site_fid["TEST_NAME"],
                                                                 nestSiteData["dutList"],
                                                                 test_site_fid["LLimit"],
                                                                 test_site_fid["HLimit"])
                nestSiteData["dyLLimit"] = dyL
                nestSiteData["dyHLimit"] = dyH
            # info that are same for all sites 
            # will be stored in testInfo
            infoDict.update(test_site_fid)
        
        return {"TestInfo": testInfo, "Data": data}


    def getBinChartData(self, head: int, site: int) -> dict:
        '''
        Get single-head, single-site HBIN & SBIN data from all files
        
        return a dictionary contains:
        `HS`: (head, site)
        `HBIN`: {fid -> {hbin -> count}}
        `SBIN`: {fid -> {hbin -> count}}
        `HBIN_Ticks`: dict, key: all HBINs in `HBIN`, value: [(i, tick name)]
        `SBIN_Ticks`: dict, key: all SBINs in `SBIN`, value: [(i, tick name)]
        '''
        binData = {"HS": (head, site)}
        for isHBIN in [True, False]:
            # convert bin -> [count] 
            # to fid -> {bin -> count}
            orig = self.DatabaseFetcher.getBinStats(head, site, isHBIN=isHBIN)
            new = {}
            for bin_num, cntList in orig.items():
                for fid, cnt in enumerate(cntList):
                    binCntDict = new.setdefault(fid, {})
                    if cnt:
                        binCntDict[bin_num] = cnt
            keyName = "HBIN" if isHBIN else "SBIN"
            binData[keyName] = new
            # create ticks for pyqtgraph BarGraphItem
            # all files share a same tick, all bin num should
            # be included
            tickDict = {}
            binInfo = self.HBIN_dict if isHBIN else self.SBIN_dict
            for i, bin_num in enumerate(sorted(orig.keys())):
                # i is the real coordinate for Bars
                bin_name = binInfo[bin_num].get("BIN_NAME", "")
                tick_name = bin_name if bin_name else f"{keyName} {bin_num}"
                tickDict[bin_num] = (i, tick_name)
            binData[keyName+"_Ticks"] = tickDict
        return binData
    
    
    def getWaferMapData(self, testTuple: tuple, selectSites: list[int]) -> dict:
        '''
        Get single-head, multi-site trend chart data of ONE test item
        
        `testTuple`:  selected wafer (wafer index, file id, wafer name)
        `selectSites`: list of selected STDF sites
        
        return a dictionary contains:
        `Bounds`: a tuple contains wafer boundaries (`xmax`, `xmin`, `ymax`, `ymin`)
        `ID`: (waferInd, fid), waferInd == -1 means stacked wafer fail counts, otherwise it's wafer map of SBIN
        `Info`: a tuple, (`ratio`, `die_size`, `invertX`, `invertY`, `wafer ID`, `sites`)
        `Data`: a dict, key: sbin, value: {"x" -> x_array, "y" -> y_array}
        `Statistic`: for wafermap, a dict of sbin -> (sbinName, sbinCnt, percent)
        '''
        waferInd, fid, waferID = testTuple
        bounds = self.DatabaseFetcher.getWaferBounds(waferInd, fid)
        
        # bounds should all be int type, 
        # otherwise we cannot creat numpy mesh
        if any(map(lambda i: not isinstance(i, int), bounds)):
            return {}
        statistic = {}
        if waferInd == -1:
            data = self.DatabaseFetcher.getStackedWaferData(selectSites)
            for count in data.keys():
                # for bypass validation check only
                statistic[count] = count
        else:
            data = self.DatabaseFetcher.getWaferCoordsDict(waferInd, selectSites, fid)
            totalDies = sum([len(xyDict["x"]) for xyDict in data.values()])
            # key: sbin, value: {"x", "y"}
            for sbin, xyDict in data.items():
                # get statistic
                sbinName = self.SBIN_dict[sbin]["BIN_NAME"]
                sbinCnt = len(xyDict["x"])
                percent = 100 * sbinCnt / totalDies
                # legendlabel = f"SBIN {sbin} - {sbinName}\n[{sbinCnt} - {percent:.1f}%]"
                statistic[sbin] = (sbinName, sbinCnt, percent)
        # info
        try:
            wid = self.waferInfoDict[waferInd, fid].get("DIE_WID", "0")
            ht = self.waferInfoDict[waferInd, fid].get("DIE_HT", "0")
            unit = self.waferInfoDict[waferInd, fid].get("WF_UNITS", "")
            ratio = float(wid) / float(ht)
            die_size = f"{wid} {unit} × {ht} {unit}"
            # default positive direction
            invertX = "R" != self.waferInfoDict[waferInd, fid].get("POS_X", "R")
            invertY = "U" != self.waferInfoDict[waferInd, fid].get("POS_Y", "U")            
        except (ValueError, KeyError, ZeroDivisionError):
            ratio = 1
            die_size = ""
            invertX = False
            invertY = False
        
        return {"Bounds": bounds, 
                "ID": (waferInd, fid), 
                "Info": (ratio, die_size, 
                         invertX, invertY, 
                         waferID, selectSites), 
                "Data": data,
                "Statistic": statistic}

