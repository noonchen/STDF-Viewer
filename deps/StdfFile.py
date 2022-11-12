#
# StdfFile.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: November 3rd 2022
# -----
# Last Modified: Sat Nov 12 2022
# Modified By: noonchen
# -----
# Copyright (c) 2022 noonchen
# <<licensetext>>
#


import os, zipfile, itertools
import numpy as np
from indexed_gzip import IndexedGzipFile
from indexed_bzip2 import IndexedBzip2File

from deps.DatabaseFetcher import DatabaseFetcher
from deps.SharedSrc import *
import rust_stdf_helper


class StdfFiles:
    def __init__(self, paths: list[str]):
        self.file_paths = paths
        self.file_type = []
        self.file_handles = []
        # save zip object in case of being gc
        self.zip_handles = []
        
    def open(self):
        # open files and store types and pointers
        for path in self.file_paths:
            if (path.lower()).endswith("gz"):
                self.file_type.append("gz")
                self.file_handles.append(IndexedGzipFile(filename=path, mode='rb'))
            elif (path.lower()).endswith("bz2"):
                self.file_type.append("bzip")
                self.file_handles.append(IndexedBzip2File(path, parallelization = 4))
            elif (path.lower()).endswith("zip"):
                zipObj = zipfile.ZipFile(path, "r")
                # zip checks
                if len(zipObj.namelist()) == 0:
                    raise OSError("Empty zip file detected")
                fileNameOf1st = zipObj.namelist()[0]
                if zipObj.filelist[0].file_size == 0:
                    raise OSError(f"The first item in the zip is not a file: \n{fileNameOf1st}")
                # open the 1st file in zip, ignore the rest
                self.file_type.append("zip")
                self.file_handles.append(zipObj.open(fileNameOf1st, "r", force_zip64=True))
                self.zip_handles.append(zipObj)
            else:
                self.file_type.append("orig")
                self.file_handles.append(open(path, 'rb'))
        
    def seek(self, fid: int, offset: int, whence: int = 0):
        self.file_handles[fid].seek(offset, whence)
        
    def read(self, fid: int, numBytes: int):
        return self.file_handles[fid].read(numBytes)
    
    def close(self):
        [fp.close() for fp in self.file_handles]
        [zipfp.close() for zipfp in self.zip_handles]




class DataInterface:
    def __init__(self, paths: list[str]):
        self.stdf = StdfFiles(paths)
        self.num_files = len(paths)
        self.DatabaseFetcher = DatabaseFetcher(self.num_files)
        self.dbPath = ""
        self.dbConnected = False
        self.containsWafer = False
        
        self.availableSites = []
        self.availableHeads = []
        self.testRecTypeDict = {}       # used for get test record type
        # self.waferInfoDict = {}
        self.failCntDict = {}
        self.dutArrays = []             # complete dut arrays from all files
        self.dutSiteInfo = []           # site of each dut in self.dutArray
        # self.waferOrientation = ((), ())
        # dict to store H/SBIN info
        self.HBIN_dict = {}
        self.SBIN_dict = {}
        # all test list or wafers in the database
        self.completeTestList = []
        self.completeWaferList = []
        # cache for faster access
        # key: testID, (test_num, test_name)
        # value: [testDataDict], file id as index, 
        # if file id doesn't contains testID, testDataDict is an empty dict
        self.dataCache = {}
        
        
    def loadDatabase(self):
        if self.dbPath == "":
            raise ValueError("Invalid database path")
        
        self.DatabaseFetcher.connectDB(self.dbPath)
        self.dbConnected = True
        self.containsWafer = any(map(lambda c: c>0, self.DatabaseFetcher.getWaferCount()))
        # for site/head selection
        self.availableSites = self.DatabaseFetcher.getSiteList()
        self.availableHeads = self.DatabaseFetcher.getHeadList()        
        # get all MPR test numbers
        self.testRecTypeDict = self.DatabaseFetcher.getTestRecordTypeDict()
        # update fail cnt dict
        self.failCntDict = self.DatabaseFetcher.getTestFailCnt()
        # for dut masking
        self.dutSiteInfo = self.DatabaseFetcher.getDUT_SiteInfo()
        # hold a same reference to complete dut arrays
        self.dutArrays = self.DatabaseFetcher.dutArrays        
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
        # close files
        self.stdf.close()
        
        
    def getFileMetaData(self) -> list:
        metaDataList = []
        filecount = len(self.stdf.file_paths)
        # if database is not exist,
        # return a empty list instead
        if not self.dbConnected:
            return metaDataList
        # some basic os info
        get_file_size = lambda p: "%.2f MB"%(os.stat(p).st_size / 2**20)
        metaDataList.append(["File Name: ", *list(map(os.path.basename, self.stdf.file_paths)) ])
        metaDataList.append(["Directory Path: ", *list(map(os.path.dirname, self.stdf.file_paths)) ])
        metaDataList.append(["File Size: ", *list(map(get_file_size, self.stdf.file_paths)) ])
        # dut summary
        dutCntDict = self.DatabaseFetcher.getDUTCountDict()
        metaDataList.append(["Yield: ", *[f"{100*p/t :.2f}%" if t!=0 else "" for (p, t) in zip(dutCntDict["Pass"], dutCntDict["Total"])] ])
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
            wafer_unit_tuple = InfoDict.pop("WF_UNITS", ["" for _ in range(filecount)])
            if "WAFR_SIZ" in InfoDict:
                wafer_size_tuple = InfoDict.pop("WAFR_SIZ")
                metaDataList.append(["Wafer Size: ", *[f"{size} {unit}" if size is not None and unit is not None else "" for (size, unit) in zip(wafer_size_tuple, wafer_unit_tuple)] ])
            if "DIE_WID" in InfoDict and "DIE_HT" in InfoDict:
                wid_tuple = InfoDict.pop("DIE_WID")
                ht_tuple = InfoDict.pop("DIE_HT")
                metaDataList.append(["Wafer Die Width Height: ", *[f"{wid} {unit} × {ht} {unit}" if wid is not None and ht is not None and unit is not None else "" for (wid, ht, unit) in zip(wid_tuple, ht_tuple, wafer_unit_tuple)] ])
            if "CENTER_X" in InfoDict and "CENTER_Y" in InfoDict:
                cent_x_tuple = InfoDict.pop("CENTER_X")
                cent_y_tuple = InfoDict.pop("CENTER_Y")
                metaDataList.append(["Wafer Center: ", *[f"({x}, {y})" if x is not None and y is not None else "" for (x, y) in zip(cent_x_tuple, cent_y_tuple)] ])
            if "WF_FLAT" in InfoDict:
                flat_orient_tuple = InfoDict.pop("WF_FLAT")
                metaDataList.append(["Wafer Flat Direction: ", *[wafer_direction_name(d) if d is not None else "" for d in flat_orient_tuple] ])
            if "POS_X" in InfoDict and "POS_Y" in InfoDict:
                pos_x_tuple = InfoDict.pop("POS_X")
                pos_y_tuple = InfoDict.pop("POS_Y")
                self.waferOrientation = (pos_x_tuple, pos_y_tuple)
                metaDataList.append(["Wafer XY Direction: ", *[f"({wafer_direction_name(x_orient)}, {wafer_direction_name(y_orient)})" if x_orient is not None and y_orient is not None else "" for (x_orient, y_orient) in zip(pos_x_tuple, pos_y_tuple)] ])
        # append other info: ATR, RDR, SDRs, sort names for better display
        for propertyName in sorted(InfoDict.keys()):
            value: tuple = InfoDict[propertyName]
            metaDataList.append([f"{propertyName}: ", *[v if v is not None else "" for v in value]])
        
        return metaDataList
        

    # TODO
    def getDataFromOffsets(self, testInfo:dict) -> dict:
        sel_offset = testInfo.pop("Offset")
        sel_length = testInfo.pop("BinaryLen")
        recHeader = testInfo["recHeader"]
        # parse data on-the-fly
        if recHeader == REC.MPR:
            pinCount = 0 if testInfo["RTN_ICNT"] is None else testInfo["RTN_ICNT"]
            rsltCount = 0 if testInfo["RSLT_PGM_CNT"] is None else testInfo["RSLT_PGM_CNT"]
            testDict = stdf_MPR_Parser(recHeader, pinCount, rsltCount, sel_offset, sel_length, self.std_handle)
            pinInfoDict = self.DatabaseFetcher.getPinNames(testInfo["TEST_NUM"], testInfo["TEST_NAME"], "RTN")
            # if pmr in TestPin_Map is not found in Pin_Map, the following value in pinInfoDict is empty
            testDict["PMR_INDX"] = pinInfoDict["PMR"]
            testDict["LOG_NAM"] = pinInfoDict["LOG_NAM"]
            testDict["PHY_NAM"] = pinInfoDict["PHY_NAM"]
            testDict["CHAN_NAM"] = pinInfoDict["CHAN_NAM"]
            testDict["statesList"] = np.array(testDict["statesList"], dtype=int)
        else:
            testDict = stdf_PFTR_Parser(recHeader, sel_offset, sel_length, self.std_handle)
            if recHeader == REC.FTR:
                testDict["VECT_NAM"] = testInfo["VECT_NAM"] if testInfo["VECT_NAM"] is not None else "" 
        
        record_flag = testInfo["OPT_FLAG"]
        result_scale = testInfo["RES_SCAL"] if recHeader != REC.FTR and testInfo["RES_SCAL"] is not None and (record_flag & 0b00000001 == 0) else 0
        result_lolimit = testInfo["LLimit"] if recHeader != REC.FTR and testInfo["LLimit"] is not None and (record_flag & 0b01010000 == 0) else np.nan
        result_hilimit = testInfo["HLimit"] if recHeader != REC.FTR and testInfo["HLimit"] is not None and (record_flag & 0b10100000 == 0) else np.nan
        result_lospec = testInfo["LSpec"] if recHeader != REC.FTR and testInfo["LSpec"] is not None and (record_flag & 0b00000100 == 0) else np.nan
        result_hispec = testInfo["HSpec"] if recHeader != REC.FTR and testInfo["HSpec"] is not None and (record_flag & 0b00001000 == 0) else np.nan
        
        result_unit = testInfo["Unit"] if recHeader != REC.FTR else ""
        
        testDict["recHeader"] = recHeader
        testDict["TEST_NUM"] = testInfo["TEST_NUM"]
        testDict["TEST_NAME"] = testInfo["TEST_NAME"]
        testDict["dataList"] = np.array(testDict["dataList"], dtype="float")
        testDict["flagList"] = np.array(testDict["flagList"], dtype=int)
                
        testDict["dataList"] = testDict["dataList"] if recHeader == REC.FTR else testDict["dataList"] * 10 ** result_scale
        testDict["LL"] = result_lolimit * 10 ** result_scale
        testDict["HL"] = result_hilimit * 10 ** result_scale
        testDict["LSpec"] = result_lospec * 10 ** result_scale
        testDict["HSpec"] = result_hispec * 10 ** result_scale
        testDict["Unit"] = "" if recHeader == REC.FTR else unit_prefix.get(result_scale, "") + result_unit
        testDict["Scale"] = result_scale
        
        return testDict
    
    
    # TODO
    def getTestValueOfDUTs(self, selDUTs: list, testTuple:tuple) -> tuple:
        test_num, pmr, test_name = testTuple
        # read data of testID
        testID = (test_num, test_name)
        self.prepareData([testID], cacheData=True)    # must enable cache, otherwise, data of current select will be cleaned
        testDict = self.getData(testTuple, selectDUTs=selDUTs)
        valueFormat = "%%.%d%s"%(self.settingParams.dataPrecision, self.settingParams.dataNotation)
        test_data_list = self.stringifyTestData(testDict, valueFormat)
        test_passFailStat_list = [True] * 5 + list(map(isPass, testDict["flagList"]))
        # data info used in floating tips
        test_dataInfo_list = [""] * 5 + self.generateDataFloatTips(testDict=testDict)
        return (test_data_list, test_passFailStat_list, test_dataInfo_list)
    
                       
    # TODO
    def prepareData(self, testIDs: list, cacheData: bool = False):
        '''testID: tuple of test num and test name, for identifying tests
        Read testID data from ALL files
        '''
        if not cacheData:
            # remove testID that are not selected anymore
            for pre_test_num, _, pre_test_name in self.preTestSelection:
                pre_testID = (pre_test_num, pre_test_name)
                if (not pre_testID in testIDs) and (pre_testID in self.selData):
                    self.selData.pop(pre_testID)
                
        for testID in testIDs:
            # skip if testID has been read
            if testID in self.selData:
                continue
            
            # read the newly selected test num
            testInfo = self.DatabaseFetcher.getTestInfo_AllDUTs(testID)
            self.selData[testID] = self.getDataFromOffsets(testInfo)
            
            
# # get mask from selectDUTs
# selMask = np.zeros(self.dutArray.size, dtype=bool)
# for dutIndex in selectDUTs:
# selMask |= (self.dutArray==dutIndex)

    
    def getTestDataCore(self, testTuple:tuple, dutMask: np.ndarray, FileID: int) -> dict:
        '''
        Get parsed data of the given testTuple, test duts are constrained by dutMask and fid.
        
        ### avoid calling this function directly, as the data may not be presented in the `dataCache` yet
        
        `testTuple`: contains test number, pin index (valid for MPR) and name, e.g. (1000, 1, "name")
        `dutMask`: mask for filtering duts of interest from the complete dutArray
        `FileID`: index of loaded files
        
        return a dictionary contains:
        `TEST_NAME` / `TEST_NUM` / `flagList` / 
        `LL` / `HL` / `Unit` / `dataList` / `DUTIndex` / 
        `Min` / `Max` / `Median` / `Mean` / `SDev` / `Cpk`
        '''
        test_num, pmr, test_name = testTuple
        testID = (test_num, test_name)
        if testID not in self.dataCache: 
            # if calling this function without prepare data
            # raise exception
            raise KeyError(f"{testID} is not prepared!")
        
        testCache: dict = self.dataCache[testID][FileID]
        if len(testCache) == 0:
            # if current file doesn't contain this testID
            # return empty dict
            return {}
        
        outData = {}        
        recHeader = testCache["recHeader"]
        outData["recHeader"] = recHeader
        # store original for testID lookup
        outData["TEST_NAME_ORIG"] = test_name
        # pmr will be add to TEST_NAME for MPR
        outData["TEST_NAME"] = test_name
        outData["TEST_NUM"] = test_num
        outData["LL"] = testCache["LL"]
        outData["HL"] = testCache["HL"]
        outData["LSpec"] = testCache["LSpec"]
        outData["HSpec"] = testCache["HSpec"]
        outData["Unit"] = testCache["Unit"]
        outData["Scale"] = testCache["Scale"]
        outData["DUTIndex"] = self.dutArrays[FileID][dutMask]
        outData["flagList"] = testCache["flagList"][dutMask]
        
        if recHeader == REC.MPR:
            # append pmr# to test name
            if pmr > 0: outData["TEST_NAME"] = f"{test_name} #{pmr}"
            try:
                # the index of test value is the same as the index of {pmr} in PMR list
                dataIndex = testCache["PMR_INDX"].index(pmr)
                # channel name differs from sites, get possible (head, site) first
                channelNameDict = testCache["CHAN_NAM"]
                hsSet = set()
                for h, siteArray in self.dutSiteInfo[FileID].items():
                    dutSite = set(siteArray[dutMask])
                    # if site number is not nan, means there is a dut in (head, site) 
                    [hsSet.add( (h, s) ) for s in dutSite if not np.isnan(s)]
                # push non-empty channel names into a list
                ChanNames = []
                for hskey in hsSet:
                    if hskey in channelNameDict:
                        # add boundary check to prevent index error, we don't want to hit exception 
                        # just because some name cannot be found
                        ChanName = channelNameDict[hskey][dataIndex] if len(channelNameDict[hskey]) > dataIndex else ""
                        if ChanName != "":
                            ChanNames.append(ChanName)

                outData["CHAN_NAM"] = ";".join(ChanNames)
                outData["LOG_NAM"] = testCache["LOG_NAM"][dataIndex]
                outData["PHY_NAM"] = testCache["PHY_NAM"][dataIndex]
                outData["dataList"] = testCache["dataList"][dataIndex][dutMask]
                outData["statesList"] = testCache["statesList"][dataIndex][dutMask]
            except (ValueError, IndexError) as e:
                outData["CHAN_NAM"] = ""
                outData["LOG_NAM"] = ""
                outData["PHY_NAM"] = ""
                outData["dataList"] = np.array([])
                outData["statesList"] = np.array([])
                if isinstance(e, IndexError):
                    print(f"Cannot found test data of PMR {pmr} in MPR test {testID}")
                else:
                    if pmr != 0:
                        # pmr != 0 indicates a valid pmr
                        print(f"PMR {pmr} is not found in {testID}'s PMR list")
        else:
            outData["dataList"] = testCache["dataList"][dutMask]
            if recHeader == REC.FTR:
                outData["VECT_NAM"] = testCache["VECT_NAM"]
        
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
                
        outData["Mean"], outData["SDev"], outData["Cpk"] = calc_cpk(outData["LL"], outData["HL"], outData["dataList"])
        return outData
    
    
    def getMaskFromHeadsSites(self, selectHeads:list[int], selectSites:list[int], FileID: int) -> np.ndarray:
        '''
        Create an array mask that will work on dutArray
        and can be used for filtering duts of interest.
        '''
        mask = np.zeros(self.dutArrays[FileID], dtype=bool)
        for head in selectHeads:
            if -1 in selectSites:
                # select all sites (site is unsigned int)
                mask |= (self.dutSiteInfo[FileID][head]>=0)
                # skip current head, since we have 
                # all duts selected
                continue
            
            for site in selectSites:
                mask |= (self.dutSiteInfo[FileID][head]==site)
        
        return mask
        
    
    def getTestDataFromHeadSite(self, testTuple: tuple, selectHeads:list[int], selectSites:list[int], FileID: int) -> dict:
        '''
        Get parsed data of the given testTuple, test duts are constrained by heads & sites & fid
        
        `testTuple`: contains test number, pin index (valid for MPR) and name, e.g. (1000, 1, "name")
        `selectHeads`: list of selected STDF heads
        `selectSites`: list of selected STDF sites
        `FileID`: index of loaded files
        
        return a dictionary contains:
        see `getTestDataCore`
        '''
        # testID -> (test_num, test_name)
        testID = (testTuple[0], testTuple[-1])
        # read data from file if not cached
        if testID not in self.dataCache:
            self.prepareData([testID])
        
        dutMask = self.getMaskFromHeadsSites(selectHeads, selectSites, FileID)
        return self.getTestDataCore(testTuple, dutMask, FileID)
    
    
    def getTestStatistics(self, testTuples: list[tuple], selectHeads:list[int], selectSites:list[int], _selectFiles: list[int] = [], floatFormat: str = ""):
        '''
        Generate data of `Test Statistic` table when `Trend`/`Histo`/`Info` tab is activated
        
        `testTuples`: list of selected tests, e.g. [(1000, 1, "name"), ...] 
        `selectHeads`: list of selected STDF heads
        `selectSites`: list of selected STDF sites
        `_selectFiles`: currently not in use
        `floatFormat`: format string for float, e.g. "%.3f"
        
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
                                                                 "" if len(self.num_files) == 1 else f" / File{fid}"))
                # basic PTR stats
                CpkString = "%s" % "∞" if testDataDict["Cpk"] == np.inf else ("N/A" if np.isnan(testDataDict["Cpk"]) else floatFormat % testDataDict["Cpk"])                
                row =  [test_name,
                        testDataDict["Unit"],
                        "N/A" if np.isnan(testDataDict["LL"]) else floatFormat % testDataDict["LL"],
                        "N/A" if np.isnan(testDataDict["HL"]) else floatFormat % testDataDict["HL"],
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
                    row[1:1] = [str(pmr), testDataDict["LOG_NAM"], testDataDict["PHY_NAM"], testDataDict["CHAN_NAM"]] if testDataDict["recHeader"] == REC.MPR else ["", "", "", ""]
                    
                rowList.append(row)
            else:
                # if this file doesn't contain this
                # testTup, skip
                continue
        
        return {"VHeader": vHeaderLabels, "HHeader": hHeaderLabels, "Rows": rowList}
    
    
    # TODO
    def prepareStatTableContent(self, tabType, **kargs):
        if tabType == tab.Trend or tabType == tab.Histo or tabType == tab.Info:
            head = kargs["head"]
            site = kargs["site"]
            testTuple = kargs["testTuple"]
            testRecTypes = kargs["testRecTypes"]    # used for determining the format of output list
            valueFormat = "%%.%d%s"%(self.settingParams.dataPrecision, self.settingParams.dataNotation)

            # return data for statistic table
            testDict = self.getData(testTuple, [head], [site])
            if testDict:
                test_num, pmr, test_name = testTuple
                # basic PTR stats
                CpkString = "%s" % "∞" if testDict["Cpk"] == np.inf else ("N/A" if np.isnan(testDict["Cpk"]) else valueFormat % testDict["Cpk"])
                MeanString = valueFormat % testDict["Mean"]
                MedianString = valueFormat % testDict["Median"]
                SDevString = valueFormat % testDict["SDev"]
                MinString = valueFormat % testDict["Min"]
                MaxString = valueFormat % testDict["Max"]
                
                rowList = ["%d / %s / %s" % (test_num, f"Head {head}", "All Sites" if site == -1 else f"Site{site}"),
                        test_name,
                        testDict["Unit"],
                        "N/A" if np.isnan(testDict["LL"]) else valueFormat % testDict["LL"],
                        "N/A" if np.isnan(testDict["HL"]) else valueFormat % testDict["HL"],
                        "%d" % list(map(isPass, testDict["flagList"])).count(False),
                        CpkString,
                        MeanString,
                        MedianString,
                        SDevString,
                        MinString,
                        MaxString]
                # match the elements of table header
                if REC.FTR in testRecTypes:
                    rowList[2:2] = [testDict["VECT_NAM"]] if testDict["recHeader"] == REC.FTR else [""]
                if REC.MPR in testRecTypes:
                    rowList[2:2] = [str(pmr), testDict["LOG_NAM"], testDict["PHY_NAM"], testDict["CHAN_NAM"]] if testDict["recHeader"] == REC.MPR else ["", "", "", ""]
                
            else:
                # some weird files might in this case, in which the number of 
                # test items in different sites are not the same
                rowList = ["N/A"] * 12
            return rowList
        
        elif tabType == tab.Bin:
            bin = kargs["bin"]
            head = kargs["head"]
            site = kargs["site"]
            rowList = []
            
            if bin == "HBIN":
                fullName = self.tr("Hardware Bin")
                bin_dict = self.HBIN_dict
            elif bin == "SBIN":
                fullName = self.tr("Software Bin")
                bin_dict = self.SBIN_dict
            
            binStats = self.DatabaseFetcher.getBinStats(head, site, bin)
            # binNumList = [item[0] for item in binStats]
            total = sum([binStats[bin] for bin in binStats.keys()])
            
            rowList.append("%s / %s / %s" % (f"{fullName}", f"Head{head}", self.tr("All Sites") if site == -1 else f"Site{site}"))
            for bin_num in sorted(binStats.keys()):
                cnt = binStats[bin_num]
                if cnt == 0: continue
                item = ["Bin%d: %.1f%%"%(bin_num, 100*cnt/total), bin_num]
                if bin_num in bin_dict:
                    # add bin name
                    item[0] = self.tr(bin_dict[bin_num]["BIN_NAME"]) + "\n" + item[0]
                rowList.append(item)
                                    
            return rowList
        
        elif tabType == tab.Wafer:
            waferIndex = kargs["waferIndex"]
            head = kargs["head"]
            site = kargs["site"]
            rowList = []
            
            if waferIndex == -1:
                # -1 indicates stacked map, return empty table
                return rowList
            
            # we need sbin dict to retrieve software bin name
            bin_dict = self.SBIN_dict
            
            coordsDict = self.DatabaseFetcher.getWaferCoordsDict(waferIndex, head, site)
            total = sum([len(coordList) for coordList in coordsDict.values()])
            waferID = self.waferInfoDict[waferIndex]["WAFER_ID"]
            
            rowList.append("%s / %s / %s" % (f"{waferID}", f"Head{head}", self.tr("All Sites") if site == -1 else f"Site{site}"))
            for bin_num in sorted(coordsDict.keys()):
                cnt = len(coordsDict[bin_num])
                if cnt == 0: continue
                item = ["Bin%d: %.1f%%"%(bin_num, 100*cnt/total), bin_num]
                if bin_num in bin_dict:
                    # add bin name
                    item[0] = self.tr(bin_dict[bin_num]["BIN_NAME"]) + "\n" + item[0]
                rowList.append(item)
                                    
            return rowList
    


if __name__ == "__main__":
    stdf_paths = [
    "/Users/nochenon/Documents/STDF Files/10K_TTR-Log_NormalBinning_P020_05Sep2020_1244.std.gz",
    "/Users/nochenon/Documents/STDF Files/S5643_62_NI_Fx2_V00_22May2021_TL18B087.3_P1_0941.std.gz",
    "/Users/nochenon/Documents/STDF Files/IPD_G6S046-09C2_04Jun2022_1350.std",
    ]
    di = DataInterface(stdf_paths)
    di.loadDatabase("deps/rust_stdf_helper/target/rust_test.db")
    for i in di.getFileMetaData():
        print(i)
        
    di.close()