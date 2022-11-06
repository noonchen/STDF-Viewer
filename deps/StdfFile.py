#
# StdfFile.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: November 3rd 2022
# -----
# Last Modified: Sun Nov 06 2022
# Modified By: noonchen
# -----
# Copyright (c) 2022 noonchen
# <<licensetext>>
#


import os, zipfile
import numpy as np
from indexed_gzip import IndexedGzipFile
from indexed_bzip2 import IndexedBzip2File

from deps.DatabaseFetcher import DatabaseFetcher
from deps.SharedSrc import mirFieldNames, mirDict, direction_symbol, REC, record_name_dict, unit_prefix
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
        self.DatabaseFetcher = DatabaseFetcher(len(paths))
        self.dbConnected = False
        self.containsWafer = False
        
        self.availableSites = []
        self.availableHeads = []
        self.testRecTypeDict = {}
        self.waferInfoDict = {}
        self.failCntDict = {}
        self.dutArray = np.array([])    # complete dut array in the stdf
        self.dutSiteInfo = {}           # site of each dut in self.dutArray
        self.waferOrientation = ((), ())
        # dict to store H/SBIN info
        self.HBIN_dict = {}
        self.SBIN_dict = {}
        # all test list or wafers in the database
        self.completeTestList = []
        self.completeWaferList = []
        
        
    def loadDatabase(self, dbPath: str):
        self.DatabaseFetcher.connectDB(dbPath)
        self.dbConnected = True
        self.containsWafer = any(map(lambda c: c>0, self.DatabaseFetcher.getWaferCount()))
        # TODO
        
    def close(self):
        #TODO
        if self.dbConnected:
            self.DatabaseFetcher.closeDB()
        
        
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
        metaDataList.append(["Yield: ", [f"{100*p/t :.2f}%" if t!=0 else "" for (p, t) in zip(dutCntDict["Pass"], dutCntDict["Total"])] ])
        metaDataList.append(["DUTs Tested: ", *dutCntDict["Total"] ])
        metaDataList.append(["DUTs Passed: ", *dutCntDict["Pass"] ])
        metaDataList.append(["DUTs Failed: ", *dutCntDict["Failed"] ])
        metaDataList.append(["DUTs Superseded: ", *dutCntDict["Superseded"] ])
        metaDataList.append(["DUTs Unknown: ", *dutCntDict["Unknown"] ])
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
                metaDataList.append(["Wafer Flat Direction: ", *[direction_symbol.get(d, d) if d is not None else "" for d in flat_orient_tuple] ])
            if "POS_X" in InfoDict and "POS_Y" in InfoDict:
                pos_x_tuple = InfoDict.pop("POS_X")
                pos_y_tuple = InfoDict.pop("POS_Y")
                self.waferOrientation = (pos_x_tuple, pos_y_tuple)
                metaDataList.append(["Wafer XY Direction: ", *[f"({direction_symbol.get(x_orient, x_orient)}, {direction_symbol.get(y_orient, y_orient)})" if x_orient is not None and y_orient is not None else "" for (x_orient, y_orient) in zip(pos_x_tuple, pos_y_tuple)] ])
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
        '''testID: tuple of test num and test name, for identifying tests'''
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
            
            
    # TODO
    def getData(self, testTuple:tuple, selectHeads:list = [], selectSites:list = [], selectDUTs: list = []):
        # keys in output: TEST_NAME / TEST_NUM / flagList / LL / HL / Unit / dataList / DUTIndex / Min / Max / Median / Mean / SDev / Cpk
        # pmr is only meanful in MPR, for other records, no use
        test_num, pmr, test_name = testTuple
        testID = (test_num, test_name)
        if not testID in self.selData: raise KeyError(f"{testID} is not prepared")
        
        outData = {}
        # use heads & sites to generate mask by default, if selectDUTs is available, use instead.
        if len(selectDUTs) == 0:
            selMask = self.getMaskFromHeadsSites(selectHeads, selectSites)
        else:
            # get mask from selectDUTs
            selMask = np.zeros(self.dutArray.size, dtype=bool)
            for dutIndex in selectDUTs:
                selMask |= (self.dutArray==dutIndex)
        
        recHeader = self.selData[testID]["recHeader"]
        outData["recHeader"] = recHeader
        # store original for testID-lookup, I'll append pmr to MPR test name for displaying
        outData["TEST_NAME_ORIG"] = test_name
        outData["TEST_NAME"] = test_name
        outData["TEST_NUM"] = test_num
        outData["LL"] = self.selData[testID]["LL"]
        outData["HL"] = self.selData[testID]["HL"]
        outData["LSpec"] = self.selData[testID]["LSpec"]
        outData["HSpec"] = self.selData[testID]["HSpec"]
        outData["Unit"] = self.selData[testID]["Unit"]
        outData["Scale"] = self.selData[testID]["Scale"]
        outData["DUTIndex"] = self.dutArray[selMask]
        outData["flagList"] = self.selData[testID]["flagList"][selMask]
        
        if recHeader == REC.MPR:
            # append pmr# to test name
            if pmr > 0: outData["TEST_NAME"] = f"{test_name} #{pmr}"
            try:
                # the index of test value is the same as the index of {pmr} in PMR list
                dataIndex = self.selData[testID]["PMR_INDX"].index(pmr)
                # channel name is vary from different sites, get selected (head, site) first
                channelNameDict = self.selData[testID]["CHAN_NAM"]
                pinNameKeys = set()
                if len(selectDUTs) == 0:
                    # get from heads & sites
                    [pinNameKeys.add((h, s)) for h in selectHeads for s in (selectSites if not -1 in selectSites else self.availableSites)]
                else:
                    # get from selectDUTs
                    for dutIndex in selectDUTs:
                        arrIndex = dutIndex - 1     # dutIndex starts from 1
                        for h, siteL in self.dutSiteInfo.items():
                            # get site number of dutIndex
                            s = siteL[arrIndex]
                            if not np.isnan(s):
                                # if site number is valid, means dutIndex is in (h, s)
                                pinNameKeys.add( (h, int(s)) )
                                break
                ChanNames = []
                for hskey in pinNameKeys:
                    if hskey in channelNameDict:
                        # add boundary check to prevent index error, we don't want to enter except clause just because some name cannot find.
                        ChanName = channelNameDict[hskey][dataIndex] if len(channelNameDict[hskey]) > dataIndex else ""
                        if ChanName != "":
                            ChanNames.append(ChanName)

                outData["CHAN_NAM"] = ";".join(ChanNames)
                outData["LOG_NAM"] = self.selData[testID]["LOG_NAM"][dataIndex]
                outData["PHY_NAM"] = self.selData[testID]["PHY_NAM"][dataIndex]
                outData["dataList"] = self.selData[testID]["dataList"][dataIndex][selMask]
                outData["statesList"] = self.selData[testID]["statesList"][dataIndex][selMask]
            except (ValueError, IndexError) as e:
                outData["CHAN_NAM"] = ""
                outData["LOG_NAM"] = ""
                outData["PHY_NAM"] = ""
                outData["dataList"] = np.array([])
                outData["statesList"] = np.array([])
                if isinstance(e, IndexError):
                    self.updateStatus(f"Cannot found test data for PMR {pmr} in MPR test {testID}")
                else:
                    if pmr != 0:
                        # pmr != 0 indicates a valid pmr
                        self.updateStatus(f"PMR {pmr} is not found in {testID}'s PMR list")
        else:
            outData["dataList"] = self.selData[testID]["dataList"][selMask]
            if recHeader == REC.FTR:
                outData["VECT_NAM"] = self.selData[testID]["VECT_NAM"]
        
        # get statistics
        if outData["dataList"].size > 0 and not np.all(np.isnan(outData["dataList"])):
            outData["Min"] = np.nanmin(outData["dataList"])
            outData["Max"] = np.nanmax(outData["dataList"])
            outData["Median"] = np.nanmedian(outData["dataList"])
        else:
            # these functions throw error on empty array
            outData["Min"] = np.nan
            outData["Max"] = np.nan
            outData["Median"] = np.nan
                
        outData["Mean"], outData["SDev"], outData["Cpk"] = calc_cpk(outData["LL"], outData["HL"], outData["dataList"])
        return outData
                
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