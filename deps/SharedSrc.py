#
# SharedSrc.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: November 5th 2022
# -----
# Last Modified: Sat Nov 05 2022
# Modified By: noonchen
# -----
# Copyright (c) 2022 noonchen
# <<licensetext>>
#

from glob import glob
import os, sys, logging, datetime
import numpy as np
from enum import IntEnum
from random import choice
from operator import itemgetter
from PyQt5 import QtWidgets, QtGui, QtCore

import matplotlib
matplotlib.use('QT5Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.collections import PatchCollection
from matplotlib.backends.backend_agg import RendererAgg



# setting attr to human string
settingNamePair = [("showHL_trend", "Show Upper Limit (Trend)"), ("showLL_trend", "Show Lower Limit (Trend)"), ("showHSpec_trend", "Show High Specification (Trend)"), ("showLSpec_trend", "Show Low Specification (Trend)"), ("showMed_trend", "Show Median Line (Trend)"), ("showMean_trend", "Show Mean Line (Trend)"),
                   ("showHL_histo", "Show Upper Limit (Histo)"), ("showLL_histo", "Show Lower Limit (Histo)"), ("showHSpec_histo", "Show High Specification (Histo)"), ("showLSpec_histo", "Show Low Specification (Histo)"), ("showMed_histo", "Show Median Line (Histo)"), ("showMean_histo", "Show Mean Line (Histo)"), ("showGaus_histo", "Show Gaussian Fit"), ("showBoxp_histo", "Show Boxplot"), ("binCount", "Bin Count"), ("showSigma", "δ Lines"),
                   ("language", "Language"), ("recentFolder", "Recent Folder"), ("dataNotation", "Data Notation"), ("dataPrecision", "Data Precison"), ("cpkThreshold", "Cpk Warning Threshold"), ("checkCpk", "Search Low Cpk"), ("sortTestList", "Sort TestList"),
                   ("siteColor", "Site Colors"), ("sbinColor", "Software Bin Colors"), ("hbinColor", "Hardware Bin Colors")]
setattr(sys, "CONFIG_NAME", settingNamePair)


# check if a test item passed: bit7-6: 00 pass; 10 fail; x1 none, treated as pass; treat negative flag (indicate not tested) as pass
isPass = lambda flag: True if flag < 0 or flag & 0b11000000 == 0 else (False if flag & 0b01000000 == 0 else True)


# simulate a Enum in python
# class Tab(tuple): __getattr__ = tuple.index
# tab = Tab(["Info", "Trend", "Histo", "Bin", "Wafer"])
class tab(IntEnum):
    Info = 0
    Trend = 1
    Histo = 2
    Bin = 3
    Wafer = 4
    
class REC(IntEnum):
    '''Constants of STDF Records: typ<<8 | sub'''
    PTR = 3850
    FTR = 3860
    MPR = 3855

# unit prefixes
unit_prefix = {15: "f",
              12: "p",
              9: "n",
              6: "u",
              3: "m",
              2: "%",
              0: "",
              -3: "K",
              -6: "M",
              -9: "G",
              -12: "T"}

# MIR field name to Description Dict
mirFieldNames = ["BYTE_ORD", "SETUP_T", "START_T", "FINISH_T", "STAT_NUM", "MODE_COD", "RTST_COD", "PROT_COD", "BURN_TIM", "CMOD_COD", "LOT_ID", "PART_TYP", "NODE_NAM", "TSTR_TYP",
                 "JOB_NAM", "JOB_REV", "SBLOT_ID", "OPER_NAM", "EXEC_TYP", "EXEC_VER", "TEST_COD", "TST_TEMP", "USER_TXT", "AUX_FILE", "PKG_TYP", "FAMLY_ID",
                 "DATE_COD", "FACIL_ID", "FLOOR_ID", "PROC_ID", "OPER_FRQ", "SPEC_NAM", "SPEC_VER", "FLOW_ID", "SETUP_ID", "DSGN_REV", "ENG_ID", "ROM_COD", "SERL_NUM", "SUPR_NAM", "DISP_COD", "USR_DESC", "EXC_DESC"]

mirDescriptions = ["Byte Order", "Setup Time", "Start Time", "Finish Time", "Station Number", "Test Mode Code", "Retest Code", "Protection Code", "Burn-in Time", "Command Mode Code", "Lot ID", "Product ID", 
                   "Node Name", "Tester Type", "Job Name", "Job Revision", "Sublot ID", "Operator ID", "Tester Software Type", "Tester Software Version", "Step ID", "Test Temperature", 
                   "User Text", "Auxiliary File Name", "Package Type", "Family ID", "Date Code", "Facility ID", "Floor ID", "Process ID", "Operation Frequency", "Test Spec Name", 
                   "Test Spec Version", "Flow ID", "Setup ID", "Design Revision", "Engineer Lot ID", "ROM Code ID", "Serial Number", "Supervisor ID", "Lot Disposition Code", "Lot Description From User", "Lot Description From Exec"]

mirDict = dict(zip(mirFieldNames, mirDescriptions))

rHEX = lambda: "#"+"".join([choice('0123456789ABCDEF') for j in range(6)])
# check if a hex color string
def isHexColor(color: str) -> bool:
    '''Check if a given str is a valid hex color #RRGGBB[AA]'''
    color = color.lower()
    if color.startswith("#") and len(color) in [7, 9]:
        hexNum = list(map(lambda num: f'{num:x}', range(16)))
        for hex in color[1:]:
            if not hex in hexNum:
                return False
        return True
    else:
        return False




def init_logger(rootFolder):
    logger = logging.getLogger("STDF-Viewer")
    logger.setLevel(logging.WARNING)
    logFolder = os.path.join(rootFolder, "logs")
    logPath = os.path.join(logFolder, f"STDF-Viewer-{datetime.date.today()}.log")
    setattr(sys, "LOG_PATH", logFolder)   # save the log location globally
    os.makedirs(os.path.dirname(logPath), exist_ok=True)
    logFD = logging.FileHandler(logPath, mode="a+")
    logFD.setFormatter(logging.Formatter('%(asctime)s : %(name)s : %(levelname)s : %(message)s'))
    logger.addHandler(logFD)
    # keep 5 logs only, delete old logs
    allLogFiles = sorted([os.path.join(logFolder, f) 
                        for f in os.listdir(logFolder) 
                        if f.endswith('.log') and os.path.isfile(os.path.join(logFolder, f))])
    [os.remove(allLogFiles[i]) for i in range(len(allLogFiles)-5)] if len(allLogFiles) > 5 else []



def calc_cpk(L:float, H:float, data:np.ndarray) -> tuple:
    '''return mean, sdev and Cpk of given data series, 
    discarding np.nan values'''
    if data.size == 0 or np.all(np.isnan(data)):
        return np.nan, np.nan, np.nan
    
    sdev = np.nanstd(data)
    mean = np.nanmean(data)
    
    if np.isnan(L) or np.isnan(H):
        return mean, sdev, np.nan
    
    T = H - L
    if sdev == 0:
        Cpk = np.inf
    else:
        U = (H + L)/2
        CP = T / (6 * sdev)
        # Ca = (mean - U) / (T/2)
        Cpk = CP - abs(mean - U)/(3 * sdev)
    return mean, sdev, Cpk

def deleteWidget(w2delete: QtWidgets.QWidget):
    '''delete QWidget and release its memory'''
    w2delete.setParent(None)
    w2delete.deleteLater()

def getCanvasDicts(qfigLayout: QtWidgets.QBoxLayout) -> dict:
    '''Read canvas info (tn, head, site) from the layout 
    and recording their index into a dict'''
    canvasIndexDict = {}
    for index in range(qfigLayout.count()):
        mp_widget = qfigLayout.itemAt(index).widget()
        mp_head = mp_widget.head
        mp_test_num = mp_widget.test_num
        mp_pmr = mp_widget.pmr
        mp_site = mp_widget.site
        mp_test_name = mp_widget.test_name
        canvasIndexDict[(mp_head, mp_test_num, mp_pmr, mp_site, mp_test_name)] = index
    return canvasIndexDict

def calculateCanvasIndex(_test_num: int, _head: int, _site: int, _pmr: int, _test_name: str, canvasIndexDict: dict):
    '''Given test info (tn, head, site) and calculate the proper index
    to which the new canvas should be inserted'''
    tupleList = list(canvasIndexDict.keys())
    tupleList.append( (_head, _test_num, _pmr, _site, _test_name) )
    # sort tuple by element 0 first, then 1, finally 2
    tupleList_sort = sorted(tupleList, key=itemgetter(0, 1, 2, 3, 4))
    # find the new tuple and get its index
    newTupleIndex = tupleList_sort.index( (_head, _test_num, _pmr, _site, _test_name) )
    return newTupleIndex


# stdf v4 flag description
dutFlagBitInfo = {}        # description of dut flag
testFlagBitInfo = {}       # description of test flag
returnStateInfo = {}       # description of return state
# wafer direction description
direction_symbol = {}
# this function takes a tr method, and it will be called 
# when STDF-Viewer is initializing
def translate_const_dicts(tr):
    '''retranslate bit info when language changes'''
    global dutFlagBitInfo, testFlagBitInfo, returnStateInfo, direction_symbol
    dutFlagBitInfo = \
        {7: tr("Bit7: Bit reserved"),
            6: tr("Bit6: Bit reserved"),
            5: tr("Bit5: Bit reserved"),
            4: tr("Bit4: No pass/fail indication, ignore Bit3"),
            3: tr("Bit3: DUT failed"),
            2: tr("Bit2: Abnormal end of testing"),
            1: tr("Bit1: Wafer die is retested"),
            0: tr("Bit0: DUT is retested")}
    testFlagBitInfo = \
        {7: tr("Bit7: Test failed"),
            6: tr("Bit6: Test completed with no pass/fail indication"),
            5: tr("Bit5: Test aborted"),
            4: tr("Bit4: Test not executed"),
            3: tr("Bit3: Timeout occurred"),
            2: tr("Bit2: Test result is unreliable"),
            1: tr("Bit1: The test was executed, but no dataloagged value was taken"),
            0: tr("Bit0: Alarm detected during testing")}
    returnStateInfo = \
        {0x0: tr("RTN_STAT0: 0 or low"),
            0x1: tr("RTN_STAT1: 1 or high"),
            0x2: tr("RTN_STAT2: Midband"),
            0x3: tr("RTN_STAT3: Glitch"),
            0x4: tr("RTN_STAT4: Undetermined"),
            0x5: tr("RTN_STAT5: Failed low"),
            0x6: tr("RTN_STAT6: Failed high"),
            0x7: tr("RTN_STAT7: Failed midband"),
            0x8: tr("RTN_STAT8: Failed with a glitch"),
            0x9: tr("RTN_STAT9: Open"),
            0xA: tr("RTN_STAT10: Short")}
    direction_symbol = {"U": tr("Up"), 
                        "D": tr("Down"), 
                        "L": tr("Left"), 
                        "R": tr("Right")}



def dut_flag_parser(flagHexString: str) -> str:
    '''return detailed description of a DUT flag'''
    global dutFlagBitInfo
    try:
        flag = int(flagHexString, 16)
        flagString = f"{flag:>08b}"
        infoList = []
        for pos, bit in enumerate(reversed(flagString)):
            if bit == "1":
                infoList.append(dutFlagBitInfo[pos])
        return "\n".join(reversed(infoList))
    
    except ValueError:
        return "Unknown"


def test_flag_parser(flag: int) -> str:
    '''return detailed description of a test flag'''
    global testFlagBitInfo
    # treat negative flag (indicate not tested) as pass
    flag = 0 if flag < 0 else flag
    
    flagString = f"{flag:>08b}"
    infoList = []
    for pos, bit in enumerate(reversed(flagString)):
        if bit == "1":
            infoList.append(testFlagBitInfo[pos])
    return "\n".join(reversed(infoList))


def return_state_parser(RTN_STAT: int) -> str:
    '''convert description of the given return state'''
    global returnStateInfo
    
    if RTN_STAT >= 0 and RTN_STAT <= 0xA:
        return returnStateInfo[RTN_STAT]
    else:
        # invalid range, return empty string
        return ""


# TODO
def generateDataFloatTips(testDict: dict) -> list:
    '''testDict should be return by getData()'''
    validRTNStatList = False
    # data info used in floating tips
    dataTips = []
    test_flagInfo_list = list(map(test_flag_parser, testDict["flagList"]))
    # test name of MPR test is different from orignal after getData(), must use orignal name here
    testID = (testDict["TEST_NUM"], testDict["TEST_NAME_ORIG"])
    if testRecTypeDict[testID] == REC.MPR:
        # for MPR tests, add description of RTN_STAT and flag
        statInfo_list = list(map(return_state_parser, testDict["statesList"]))
        # length of STAT should be the same as flagList, unless MPR doesn't contain any RTN_STAT
        validRTNStatList = len(statInfo_list) == len(test_flagInfo_list)
        
    if validRTNStatList:
        # don't join empty string
        dataTips = ["\n".join([text for text in statFlagTuple if text]) for statFlagTuple in zip(statInfo_list, test_flagInfo_list)]
    else:
        # for others, add flag info only (TODO FTR currently not supported, although it contains RTN..)
        dataTips = test_flagInfo_list
    return dataTips


def genQItemList(imageFont: str, fontsize: int, dutSumList: list[str]) -> list[QtGui.QStandardItem]:
    '''Convert a str list to a QStandardItem list'''
    qitemRow = []
    # fontsize = 13 if isMac else 10
    dutStatus, dutFlagString = dutSumList[-1].split("-")
    dutFail = dutStatus.startswith("Failed")
    dutUnknown = (dutStatus == "" or dutStatus.startswith("Unknown"))
    flagInfo = dut_flag_parser(dutFlagString)
    
    for item in dutSumList:
        qitem = QtGui.QStandardItem(item)
        qitem.setTextAlignment(QtCore.Qt.AlignCenter)
        qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        qitem.setData(QtGui.QFont(imageFont, fontsize), QtCore.Qt.FontRole)
        # mark red when failed
        if dutFail: 
            qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
            qitem.setData(QtGui.QColor("#CC0000"), QtCore.Qt.BackgroundRole)
        # mark orange when unknown
        if dutUnknown: 
            qitem.setData(QtGui.QColor("#000000"), QtCore.Qt.ForegroundRole)
            qitem.setData(QtGui.QColor("#FE7B00"), QtCore.Qt.BackgroundRole)
        if flagInfo != "":
            qitem.setToolTip(flagInfo)
        qitemRow.append(qitem)
    return qitemRow


# TODO
def getTestTuple(test_name_string: str, isWaferName: bool = False) -> tuple:
    tmpList = test_name_string.split("\t", 2)     # split up to 3 elements
    numString = tmpList[0].strip("#")    # wafer number begins with "#"
    nameString = tmpList[-1]
    
    if isWaferName:
        pmr = 0
        tn = -1 if numString == "-" else int(numString)
    else:
        tn = int(numString)
        if len(tmpList) > 2:
            # a possible MPR test, e.g. [test num, #PMR, test name]
            # if it's not a MPR, pmr is set to 0
            pmr = int(tmpList[1].strip("#")) if testRecTypeDict.get((tn, nameString), 0) == REC.MPR else 0
        else:
            pmr = 0
    return (tn, pmr, nameString)


def stringifyTestData(testDict: dict, valueFormat: str) -> list:
    '''Stringify data for displaying and saving to reports'''
    recHeader = testDict["recHeader"]
    test_data_list = [testDict["TEST_NAME"], 
                        "%d" % testDict["TEST_NUM"],
                        "N/A" if np.isnan(testDict["HL"]) else valueFormat % testDict["HL"],
                        "N/A" if np.isnan(testDict["LL"]) else valueFormat % testDict["LL"],
                        testDict["Unit"]]
        
    if recHeader == REC.FTR:
        # FTR only contains test flag
        test_data_list += ["-" if np.isnan(data) else "Test Flag: %d" % data for data in testDict["dataList"]]
        
    elif recHeader == REC.PTR:
        test_data_list += ["-" if np.isnan(data) else valueFormat % data for data in testDict["dataList"]]
        
    else:
        if testDict["dataList"].size == 0:
            # No PMR related and no test data in MPR, use test flag instead
            test_data_list += ["-" if flag < 0 else "Test Flag: %d" % flag for flag in testDict["flagList"]]
        else:
            # Test data exists
            test_data_list += ["-" if np.isnan(data) else valueFormat % data for data in testDict["dataList"]]
            
    return test_data_list


# TODO
def genTrendPlot(self, fig:plt.Figure, head:int, site:int, testTuple:tuple):
    test_num, _, test_name = testTuple
    selData = self.getData(testTuple, [head], [site])
    ax = fig.add_subplot(111)
    trendLines = []
    ax.set_title("%d %s - %s - %s"%(test_num, test_name, "Head%d"%head, self.tr("All Sites") if site == -1 else "Site%d"%site), fontsize=15, fontname=self.imageFont)
    y_raw = selData["dataList"]
    dutListFromSiteHead = self.dutArray[self.getMaskFromHeadsSites([head], [site])]
    dataInvalid = np.all(np.isnan(y_raw))
    testInvalid = np.all(selData["flagList"] < 0)

    if (selData["recHeader"] == REC.MPR and dataInvalid and testInvalid) or (selData["recHeader"] != REC.MPR and (dataInvalid or testInvalid)):
        # show a warning text in figure
        # For PTR and FTR, any invalid would trigger this case
        # For MPR, dataInvalid and testInvalid both meet can it enter this case
        ax.text(x=0.5, y=0.5, s=self.tr('No test data of "%s" \nis found in Head %d - %s') % (test_name, head, self.tr("All Sites") if site == -1 else "Site %d"%site), color='red', fontname=self.imageFont, fontsize=18, weight="bold", linespacing=2, ha="center", va="center", transform=ax.transAxes)
    else:
        if selData["recHeader"] == REC.MPR and dataInvalid:
            # MPR contains only test flag but no data, replace y_raw with test flags
            y_raw = selData["flagList"].astype(float)
            # replace -1 (invalid test flag) with nan
            y_raw[y_raw < 0] = np.nan
        
        # default drawing code for PTR, FTR and "MPR without data"
        # select not nan value
        x_arr = dutListFromSiteHead[~np.isnan(y_raw)]
        y_arr = y_raw[~np.isnan(y_raw)]
        # for dynamic limits
        hasDynamicLow = False
        hasDynamicHigh = False
        dyLLimits = np.array([])
        dyHLimits = np.array([])
        # default limits
        HL = selData["HL"]
        LL = selData["LL"]
        HSpec = selData["HSpec"]
        LSpec = selData["LSpec"]
        med = selData["Median"]
        avg = selData["Mean"]
        # plot            
        trendLine, = ax.plot(x_arr, y_arr, "-o", markersize=6, markeredgewidth=0.2, markeredgecolor="black", linewidth=0.5, picker=True, color=self.settingParams.siteColor.setdefault(site, rHEX()), zorder = 0, label="Data")
        trendLines.append(trendLine)
        # axes label
        ax.ticklabel_format(useOffset=False)    # prevent + sign
        ax.xaxis.get_major_locator().set_params(integer=True)   # force integer on x axis
        ax.set_xlabel("%s"%(self.tr("DUT Index")), fontsize=12, fontname=self.imageFont)
        if selData["recHeader"] == REC.FTR or (selData["recHeader"] == REC.MPR and dataInvalid):
            ax.set_ylabel(self.tr("Test Flag"), fontsize=12, fontname=self.imageFont)
        else:
            ax.set_ylabel("%s%s"%(self.tr("Test Value"), " (%s)"%selData["Unit"] if selData["Unit"] else ""), fontsize=12, fontname=self.imageFont)
        # limits
        if len(x_arr) == 1:
            ax.set_xlim((x_arr[0]-1, x_arr[0]+1))    # only one point
        else:
            headroomX = (x_arr[-1]-x_arr[0]) * 0.05
            ax.set_xlim(left = x_arr[0] - headroomX, right = x_arr[-1] + headroomX)
        
        if self.settingParams.showHL_trend or self.settingParams.showMean_trend: 
            # try to get dynamic limits only if one of limits is enabled
            hasDynamicLow, dyLLimits, hasDynamicHigh, dyHLimits = self.DatabaseFetcher.getDynamicLimits(test_num, test_name, x_arr, LL, HL, selData["Scale"])
        # when hasDynamic is true, the limit is definitely not np.nan
        limit_max = max(HL, np.max(dyHLimits)) if hasDynamicHigh else HL
        limit_min = min(LL, np.min(dyLLimits)) if hasDynamicLow else LL
        data_max = np.nanmax([selData["Max"], limit_max])
        data_min = np.nanmin([selData["Min"], limit_min])
        dataDelta = data_max - data_min
        
        headroomY = 5 if dataDelta == 0 else dataDelta * 0.15
        ax.set_ylim((data_min-headroomY, data_max+headroomY))

        # blended transformation
        transXaYd = matplotlib.transforms.blended_transform_factory(ax.transAxes, ax.transData)
        # HL/LL lines
        if self.settingParams.showHL_trend and ~np.isnan(HL): 
            ax.text(x=0, y=HL, s=" HLimit = %.3f\n"%HL, color='r', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="left", va="center", transform=transXaYd)
            if hasDynamicHigh: 
                ax.plot(x_arr, dyHLimits, "-", linewidth=3, color='r', zorder = -10, label="Upper Limit")
            else:
                ax.axhline(y = HL, linewidth=3, color='r', zorder = -10, label="Upper Limit")
        
        if self.settingParams.showLL_trend and ~np.isnan(LL):
            ax.text(x=0, y=LL, s="\n LLimit = %.3f"%LL, color='b', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="left", va="center", transform=transXaYd)
            if hasDynamicLow: 
                ax.plot(x_arr, dyLLimits, "-", linewidth=3, color='b', zorder = -10, label="Lower Limit")
            else:
                ax.axhline(y = LL, linewidth=3, color='b', zorder = -10, label="Lower Limit")
        # Spec lines
        if self.settingParams.showHSpec_trend and ~np.isnan(HSpec): 
            ax.text(x=1, y=HSpec, s="HiSpec = %.3f \n"%HSpec, color='darkred', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="right", va="center", transform=transXaYd)
            ax.axhline(y = HSpec, linewidth=3, color='darkred', zorder = -10, label="High Spec")
        if self.settingParams.showLSpec_trend and ~np.isnan(LSpec): 
            ax.text(x=1, y=LSpec, s="\nLoSpec = %.3f "%LSpec, color='navy', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="right", va="center", transform=transXaYd)
            ax.axhline(y = LSpec, linewidth=3, color='navy', zorder = -10, label="Low Spec")
        # add med and avg text at the right edge of the plot
        m_obj = None
        m_valid = False
        a_obj = None
        a_valid = False
        if self.settingParams.showMed_trend and ~np.isnan(med):
            m_valid = True
            med_text = ("$x̃ = %.3f $\n" if med > avg else "\n$x̃ = %.3f $") % med
            m_obj = ax.text(x=0.99, y=med, s=med_text, color='k', fontsize=10, weight="bold", linespacing=2, ha="right", va="center", transform=transXaYd)
            ax.axhline(y = med, linewidth=1, color='k', zorder = 1, label="Median")
        if self.settingParams.showMean_trend and ~np.isnan(avg):
            a_valid = True
            avg_text = ("\n$x̅ = %.3f $" if med > avg else "$x̅ = %.3f $\n") % avg
            a_obj = ax.text(x=0.99, y=avg, s=avg_text, color='orange', fontsize=10, weight="bold", linespacing=2, ha="right", va="center", transform=transXaYd)
            ax.axhline(y = avg, linewidth=1, color='orange', zorder = 2, label="Mean")
            
        if m_valid or a_valid:
            if len(x_arr) != 1:
                # get the length of median text in axes coords
                text_object = m_obj if m_valid else a_obj     # get the non-None text object
                if self.textRender is None:
                    self.textRender = RendererAgg(*fig.get_size_inches(), fig.dpi)
                bb_pixel = text_object.get_window_extent(renderer=self.textRender)
                text_leftEdge_Axes = ax.transAxes.inverted().transform(bb_pixel)[0][0]
                # extend x limit to avoid data point overlapped with the text
                rightLimit = (x_arr[-1] + 2) * 1 / text_leftEdge_Axes
                ax.set_xlim(right = rightLimit)
                
    # for cursor binding
    return ax, trendLines


# TODO
def genHistoPlot(self, fig:plt.Figure, head:int, site:int, testTuple:tuple):
    test_num, _, test_name = testTuple
    selData = self.getData(testTuple, [head], [site])
    ax = fig.add_subplot(111)
    recGroups = []
    ax.set_title("%d %s - %s - %s"%(test_num, test_name, "Head%d"%head, self.tr("All Sites") if site == -1 else "Site%d"%site), fontsize=15, fontname=self.imageFont)
    y_raw = selData["dataList"]
    dutListFromSiteHead = self.dutArray[self.getMaskFromHeadsSites([head], [site])]
    dataInvalid = np.all(np.isnan(selData["dataList"]))
    testInvalid = np.all(selData["flagList"] < 0)

    if (selData["recHeader"] == REC.MPR and dataInvalid and testInvalid) or (selData["recHeader"] != REC.MPR and (dataInvalid or testInvalid)):
        # show a warning text in figure
        ax.text(x=0.5, y=0.5, s=self.tr('No test data of "%s" \nis found in Head %d - %s') % (test_name, head, self.tr("All Sites") if site == -1 else "Site %d"%site), color='red', fontname=self.imageFont, fontsize=18, weight="bold", linespacing=2, ha="center", va="center", transform=ax.transAxes)
    else:
        if selData["recHeader"] == REC.MPR and dataInvalid:
            # MPR contains only test flag but no data, replace y_raw with test flags
            y_raw = selData["flagList"].astype(float)
            # replace -1 (invalid test flag) with nan
            y_raw[y_raw < 0] = np.nan
        
        dataList = y_raw[~np.isnan(y_raw)]
        dutListNoNAN = dutListFromSiteHead[~np.isnan(y_raw)]
        HL = selData["HL"]
        LL = selData["LL"]
        HSpec = selData["HSpec"]
        LSpec = selData["LSpec"]
        med = selData["Median"]
        avg = selData["Mean"]
        sd = selData["SDev"]
        bin_num = self.settingParams.binCount
        # note: len(bin_edges) = len(hist) + 1
        # we use a filter to remove the data that's beyond 9 sigma
        # otherwise we cannot to see the detailed distribution of the main data set
        #TODO filter data beyond 9σ
        if np.isnan(avg) or np.isnan(sd):
            # no filter
            dataFilter = np.full(shape=dataList.shape, fill_value=True, dtype=bool)
        else:
            dataFilter = np.logical_and(dataList>=(avg-9*sd), dataList<=(avg+9*sd))
        filteredDataList = dataList[dataFilter]
        filteredDutList = dutListNoNAN[dataFilter]
        
        hist, bin_edges = np.histogram(filteredDataList, bins = bin_num)
        bin_width = bin_edges[1]-bin_edges[0]
        # get histo bin index (start from 1) of each dut
        # np.histogram is left-close-right-open, except the last bin
        # np.digitize should be right=False, but must remove the last bin edge to force close the rightmost bin
        bin_ind = np.digitize(filteredDataList, bin_edges[:-1], right=False)
        bin_dut_dict = {}
        for ind, dut in zip(bin_ind, filteredDutList):
            if ind in bin_dut_dict:
                bin_dut_dict[ind].append(dut)
            else:
                bin_dut_dict[ind] = [dut]
        # use bar to draw histogram, only for its "align" option 
        recGroup = ax.bar(bin_edges[:len(hist)], hist, width=bin_width, align='edge', color=self.settingParams.siteColor.setdefault(site, rHEX()), edgecolor="black", zorder = 100, label="Histo Chart", picker=True)
        # save to histo group for interaction
        setattr(recGroup, "bin_dut_dict", bin_dut_dict)
        recGroups.append(recGroup)
        # draw boxplot
        if self.settingParams.showBoxp_histo:
            ax.boxplot(dataList, showfliers=False, vert=False, notch=True, widths=0.2*max(hist), patch_artist=True, zorder=200, positions=[max(hist)/2], manage_ticks=False,
                        boxprops=dict(color='b', facecolor=(1, 1, 1, 0)),
                        capprops=dict(color='b'),
                        whiskerprops=dict(color='b'))
        
        if self.settingParams.showHL_histo and ~np.isnan(HL): 
            ax.axvline(x = HL, linewidth=3, color='r', zorder = -10, label="Upper Limit")
        if self.settingParams.showLL_histo and ~np.isnan(LL): 
            ax.axvline(x = LL, linewidth=3, color='b', zorder = -10, label="Lower Limit")
        
        if self.settingParams.showHSpec_histo and ~np.isnan(HSpec): 
            ax.axvline(x = HSpec, linewidth=3, color='darkred', zorder = -10, label="Hi Spec")
        if self.settingParams.showLSpec_histo and ~np.isnan(LSpec): 
            ax.axvline(x = LSpec, linewidth=3, color='navy', zorder = -10, label="Lo Spec")

        # set xlimit and draw fitting curve only when standard deviation is not 0
        if sd != 0 and ~np.isnan(avg) and ~np.isnan(sd):
            if self.settingParams.showGaus_histo:
                # gauss fitting
                g_x = np.linspace(avg - sd * 10, avg + sd * 10, 1000)
                g_y = max(hist) * np.exp( -0.5 * (g_x - avg)**2 / sd**2 )
                ax.plot(g_x, g_y, "r--", label="Normalized Gauss Curve")
            # set x limit
            if bin_edges[0] > avg - sd * 10:
                ax.set_xlim(left=avg - sd * 10)
            if bin_edges[-1] < avg + sd * 10:
                ax.set_xlim(right=avg + sd * 10)
        ax.set_ylim(top=max(hist)*1.1)
            
        # blended transformation
        transXdYa = matplotlib.transforms.blended_transform_factory(ax.transData, ax.transAxes)
        # vertical lines for n * σ, disable if avg and sd is invalid
        sigmaList = [] if self.settingParams.showSigma == "" or np.isnan(avg) or np.isnan(sd) else [int(i) for i in self.settingParams.showSigma.split(",")]
        for n in sigmaList:
            position_pos = avg + sd * n
            position_neg = avg - sd * n
            ax.axvline(x = position_pos, ymax = 0.95, linewidth=1, ls='-.', color='gray', zorder = 2, label="%dσ"%n)
            ax.axvline(x = position_neg, ymax = 0.95, linewidth=1, ls='-.', color='gray', zorder = 2, label="-%dσ"%n)
            ax.text(x = position_pos, y = 0.99, s="%dσ"%n, c="gray", ha="center", va="top", fontname="Courier New", fontsize=10, transform=transXdYa)
            ax.text(x = position_neg, y = 0.99, s="-%dσ"%n, c="gray", ha="center", va="top", fontname="Courier New", fontsize=10, transform=transXdYa)
        # med avg text labels / lines
        med_text = ("\n $x̃ = %.3f $") % med
        avg_text = ("\n $x̅ = %.3f $") % avg
        if self.settingParams.showMed_histo and ~np.isnan(med):
            ax.text(x=med, y=1, s=med_text, color='k', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="left" if med>avg else "right", va="center", transform=transXdYa)
            ax.axvline(x = med, linewidth=1, color='black', zorder = 1, label="Median")
        if self.settingParams.showMean_histo and ~np.isnan(avg):
            ax.text(x=avg, y=1, s=avg_text, color='orange', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="right" if med>avg else "left", va="center", transform=transXdYa)
            ax.axvline(x = avg, linewidth=1, color='orange', zorder = 2, label="Mean")
        # ax.ticklabel_format(useOffset=False)    # prevent + sign
        if selData["recHeader"] == REC.FTR or (selData["recHeader"] == REC.MPR and dataInvalid):
            ax.set_xlabel(self.tr("Test Flag"), fontsize=12, fontname=self.imageFont)
        else:
            ax.set_xlabel("%s%s"%(self.tr("Test Value"), " (%s)"%selData["Unit"] if selData["Unit"] else ""), fontsize=12, fontname="Tahoma")
        ax.set_ylabel("%s"%(self.tr("DUT Counts")), fontsize=12, fontname=self.imageFont)
        
    return ax, recGroups


# TODO
def genBinPlot(self, fig:plt.Figure, head:int, site:int):
    fig.suptitle("%s - %s - %s"%(self.tr("Bin Summary"), "Head%d"%head, self.tr("All Sites") if site == -1 else "Site%d"%site), fontsize=15, fontname=self.imageFont)
    ax_l = fig.add_subplot(121)
    ax_r = fig.add_subplot(122)
    recGroup_l = []
    recGroup_r = []
    bin_width = 0.8
    Tsize = lambda barNum: 10 if barNum <= 6 else round(5 + 5 * 2 ** (0.4*(6-barNum)))  # adjust fontsize based on bar count
    # HBIN plot
    binStats = self.DatabaseFetcher.getBinStats(head, site, "HBIN")
    HList = [BIN for BIN in sorted(binStats.keys())]
    HCnt = [binStats[BIN] for BIN in HList]
    HLable = []
    HColor = []
    self.tr("MissingName")  # explicitly translation bin name, since it's always stored in the value
    for ind, i in enumerate(HList):
        HLable.append(self.tr(self.HBIN_dict[i]["BIN_NAME"]))
        HColor.append(self.settingParams.hbinColor[i])
        ax_l.text(x=ind + bin_width/2, y=HCnt[ind], s="Bin%d\n%.1f%%"%(i, 100*HCnt[ind]/sum(HCnt)), ha="center", va="bottom", fontsize=Tsize(len(HCnt)))
        
    if len(HList) > 0:
        recGroup_l = ax_l.bar(np.arange(len(HCnt)), HCnt, align='edge', width=bin_width, color=HColor, edgecolor="black", zorder = 0, label="HardwareBin Summary", picker=True)
        setattr(recGroup_l, "head", head)
        setattr(recGroup_l, "site", site)
        setattr(recGroup_l, "binType", "HBIN")
        setattr(recGroup_l, "binList", HList)
        setattr(recGroup_l, "binNames", HLable)
        ax_l.set_xticks(np.arange(len(HCnt)) + bin_width/2)
        ax_l.set_xticklabels(labels=HLable, rotation=30, ha='right', fontsize=1+Tsize(len(HCnt)), fontname=self.imageFont)    # Warning: This method should only be used after fixing the tick positions using Axes.set_xticks. Otherwise, the labels may end up in unexpected positions.
        ax_l.set_xlim(-.1, max(3, len(HCnt))-.9+bin_width)
        ax_l.set_ylim(top=max(HCnt)*1.2)
    else:
        ax_l.text(x=0.5, y=0.5, s=self.tr('No HBIN data is\nfound in Head %d - %s') % (head, self.tr("All Sites") if site == -1 else "Site %d"%site), color='red', fontname=self.imageFont, fontsize=15, weight="bold", linespacing=2, ha="center", va="center", transform=ax_l.transAxes)
    ax_l.set_xlabel(self.tr("Hardware Bin"), fontsize=12, fontname=self.imageFont)
    ax_l.set_ylabel(self.tr("Hardware Bin Counts"), fontsize=12, fontname=self.imageFont)

    # SBIN plot
    binStats = self.DatabaseFetcher.getBinStats(head, site, "SBIN")
    SList = [BIN for BIN in sorted(binStats.keys())]
    SCnt = [binStats[BIN] for BIN in SList]
    SLable = []
    SColor = []
    for ind, i in enumerate(SList):
        SLable.append(self.tr(self.SBIN_dict[i]["BIN_NAME"]))
        SColor.append(self.settingParams.sbinColor[i])
        ax_r.text(x=ind + bin_width/2, y=SCnt[ind], s="Bin%d\n%.1f%%"%(i, 100*SCnt[ind]/sum(SCnt)), ha="center", va="bottom", fontsize=Tsize(len(SCnt)))
        
    if len(SList) > 0:
        recGroup_r = ax_r.bar(np.arange(len(SCnt)), SCnt, align='edge', width=bin_width, color=SColor, edgecolor="black", zorder = 0, label="SoftwareBin Summary", picker=True)
        setattr(recGroup_r, "head", head)
        setattr(recGroup_r, "site", site)
        setattr(recGroup_r, "binType", "SBIN")
        setattr(recGroup_r, "binList", SList)
        setattr(recGroup_r, "binNames", SLable)
        ax_r.set_xticks(np.arange(len(SCnt)) + bin_width/2)
        ax_r.set_xticklabels(labels=SLable, rotation=30, ha='right', fontsize=1+Tsize(len(SCnt)), fontname=self.imageFont)
        ax_r.set_xlim(-.1, max(3, len(SCnt))-.9+bin_width)
        ax_r.set_ylim(top=max(SCnt)*1.2)
    else:
        ax_r.text(x=0.5, y=0.5, s=self.tr('No SBIN data is\nfound in Head %d - %s') % (head, self.tr("All Sites") if site == -1 else "Site %d"%site), color='red', fontname=self.imageFont, fontsize=15, weight="bold", linespacing=2, ha="center", va="center", transform=ax_r.transAxes)
    ax_r.set_xlabel(self.tr("Software Bin"), fontsize=12, fontname=self.imageFont)
    ax_r.set_ylabel(self.tr("Software Bin Counts"), fontsize=12, fontname=self.imageFont)
    
    return [ax_l, ax_r], [recGroup_l, recGroup_r]


# TODO
def genWaferPlot(self, fig:plt.Figure, head:int, site:int, wafer_num:int):
    fig.set_size_inches(7.5, 8)
    fig.set_tight_layout(False)
    ax = fig.add_subplot(111, aspect=1)
    # set limits
    waferBounds = self.DatabaseFetcher.getWaferBounds()
    xmin = waferBounds["xmin"]
    ymin = waferBounds["ymin"]
    xmax = waferBounds["xmax"]
    ymax = waferBounds["ymax"]            
    ax.set_xlim(xmin-1, xmax+1)
    ax.set_ylim(ymin-1, ymax+1)
    # scaling xy coords to be a square
    ax.set_aspect(1.0/ax.get_data_ratio(), adjustable='box')            
    # dynamic label size
    Tsize = lambda barNum: 12 if barNum <= 15 else round(7 + 5 * 2 ** (0.4*(15-barNum)))  # adjust fontsize based on bar count
    labelsize = Tsize(max(xmax-xmin, ymax-ymin))
                
    if wafer_num == -1:
        # -1 indicates stacked wafer map
        ax.set_title(self.tr("Stacked Wafer Map - %s - %s") % ("Head%d" % head, self.tr("All DUTs") if site == -1 else self.tr("DUT in Site%d") % site), fontsize=15, fontname=self.imageFont)
        failDieDistribution = self.DatabaseFetcher.getStackedWaferData(head, site)
        x_mesh = np.arange(xmin-0.5, xmax+1, 1)     # xmin-0.5, xmin+0.5, ..., xmax+0.5
        y_mesh = np.arange(ymin-0.5, ymax+1, 1)
        # initialize a full -1 2darray
        failCount_meash = np.full((len(x_mesh)-1, len(y_mesh)-1), -1)
        # fill the count into 2darray
        for (xcoord, ycoord), count in failDieDistribution.items():
            failCount_meash[xcoord-xmin, ycoord-ymin] = count
        # x is row and y is col, whereas in xycoords, x should be col and y should be row
        failCount_meash = failCount_meash.transpose()
        # get a colormap segment
        cmap_seg = matplotlib.colors.LinearSegmentedColormap.from_list("seg", plt.get_cmap("nipy_spectral")(np.linspace(0.55, 0.9, 128)))
        # draw color mesh, replace all -1 to NaN to hide rec with no value
        pcmesh = ax.pcolormesh(x_mesh, y_mesh, np.where(failCount_meash == -1, np.nan, failCount_meash), cmap=cmap_seg, picker=100)     # set picker large enough for QuadMask to fire pick event
        setattr(pcmesh, "wafer_num", wafer_num)
        # create a new axis for colorbar
        ax_colorbar = fig.add_axes([ax.get_position().x0, ax.get_position().y0-0.04, ax.get_position().width, 0.02])
        cbar = fig.colorbar(pcmesh, cax=ax_colorbar, orientation="horizontal")
        cbar.ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        cbar.set_label(self.tr("Total failed dies"), fontname=self.imageFont)
        # ax_colorbar = fig.add_axes([ax.get_position().x1+0.03, ax.get_position().y0, 0.02, ax.get_position().height])
        # cbar = fig.colorbar(pcmesh, cax=ax_colorbar)
        # cbar.ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
        # cbar.set_label("Total failed dies", rotation=270, va="bottom")
        
    else:
        waferDict = self.waferInfoDict[wafer_num]
        ax.set_title(self.tr("Wafer ID: %s - %s - %s") % (waferDict["WAFER_ID"], "Head%d"%head, self.tr("All DUTs") if site == -1 else self.tr("DUT in Site%d") % site), fontsize=15, fontname=self.imageFont)
        # group coords by soft bin
        coordsDict = self.DatabaseFetcher.getWaferCoordsDict(wafer_num, head, site)
        dutCnt = sum([len(coordList) for coordList in coordsDict.values()])
        legendHandles = []
        # draw recs for each SBIN
        for sbin in sorted(coordsDict.keys()):
            sbinName = self.SBIN_dict[sbin]["BIN_NAME"]
            sbinCnt = len(coordsDict[sbin])
            percent = 100 * sbinCnt / dutCnt
            label = "SBIN %d - %s\n[%d - %.1f%%]"%(sbin, self.tr(sbinName), sbinCnt, percent)
            rects = []
            # skip dut with invalid coords
            for (x, y) in coordsDict[sbin]:
                rects.append(matplotlib.patches.Rectangle((x-0.5, y-0.5),1,1))
            pc = PatchCollection(patches=rects, match_original=False, facecolors=self.settingParams.sbinColor[sbin], label=label, zorder=-100, picker=True)
            # for interactive plot
            setattr(pc, "SBIN", sbin)
            setattr(pc, "BIN_NAME", self.tr(sbinName))
            setattr(pc, "wafer_num", wafer_num)
            ax.add_collection(pc)
            proxyArtist = matplotlib.patches.Patch(color=self.settingParams.sbinColor[sbin], label=label)
            legendHandles.append(proxyArtist)
        # if coordsDict contains nothing, show warning text
        if len(ax.collections) == 0:
            ax.text(x=0.5, y=0.5, s=self.tr('No DUT with valid (X,Y) is\nfound in Head %d - %s') % (head, self.tr("All Sites") if site == -1 else "Site %d"%site), color='red', fontname=self.imageFont, fontsize=18, weight="bold", linespacing=2, ha="center", va="center", transform=ax.transAxes)
        # legend
        ax.legend(handles=legendHandles, loc="upper left", bbox_to_anchor=(0., -0.02, 1, -0.02), ncol=4, borderaxespad=0, mode="expand", prop={'family':self.imageFont, 'size':labelsize})
    
    # set ticks & draw coord lines
    ax.xaxis.set_major_locator(ticker.MultipleLocator(5))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(5))            
    ax.tick_params(axis='both', which='both', labeltop=True, labelright=True, length=0, labelsize=labelsize)
    # Turn spines off and create white grid.
    for edge, spine in ax.spines.items():
        spine.set_visible(False)
    ax.set_xticks(np.arange(xmin, xmax+2, 1)-0.5, minor=True)
    ax.set_yticks(np.arange(ymin, ymax+2, 1)-0.5, minor=True)
    ax.grid(which="minor", color="gray", linestyle='-', linewidth=1, zorder=0)
    # switch x, y positive direction if WCR specified the orientation.
    if self.waferOrientation[0] == self.tr("Left"):   # x towards left
        ax.invert_xaxis()
    if self.waferOrientation[1] == self.tr("Down"):   # y towards down
        ax.invert_yaxis()
        
    return ax

