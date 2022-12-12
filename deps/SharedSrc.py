#
# SharedSrc.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: November 5th 2022
# -----
# Last Modified: Mon Dec 12 2022
# Modified By: noonchen
# -----
# Copyright (c) 2022 noonchen
# <<licensetext>>
#

import io, os, sys, logging, datetime
import toml, subprocess, platform, sqlite3
import rust_stdf_helper
import numpy as np
from enum import IntEnum
from random import choice
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QWidget, QMessageBox
from PyQt5.QtCore import QObject, QThread, pyqtSignal as Signal
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter



class SettingParams:
    def __init__(self):
        # trend
        self.showHL_trend = True
        self.showLL_trend = True
        self.showHSpec_trend = True
        self.showLSpec_trend = True
        self.showMed_trend = True
        self.showMean_trend = True
        # histo
        self.showHL_histo = True
        self.showLL_histo = True
        self.showHSpec_histo = True
        self.showLSpec_histo = True
        self.showMed_histo = True
        self.showMean_histo = True
        self.showBoxp_histo = True
        self.showBoxpOl_histo = True
        self.showBars_histo = True
        self.binCount = 30
        self.showSigma = "3, 6, 9"
        # PPQQ
        self.x_ppqq = "Normal Quantiles"
        self.y_ppqq = "Data Quantiles"
        # General
        self.language = "English"
        self.font = "JetBrains Mono"
        self.recentFolder = ""
        self.dataNotation = "G"  # F E G stand for float, Scientific, automatic
        self.dataPrecision = 3
        self.checkCpk = False
        self.cpkThreshold = 1.33
        self.sortTestList = "Original"
        self.fileSymbol = {0: "o"}
        # colors
        self.siteColor = {-1: "#00CC00", 0: "#00B3FF", 1: "#FF9300", 2: "#EC4EFF", 
                          3: "#00FFFF", 4: "#AA8D00", 5: "#FFB1FF", 6: "#929292", 7: "#FFFB00"}
        self.sbinColor = {}
        self.hbinColor = {}
        
    def getFloatFormat(self) -> str:
        return "%%.%d%s" % (self.dataPrecision, self.dataNotation)


# setting attr to human string
settingNamePair = [("showHL_trend", "Show Upper Limit (Trend)"), ("showLL_trend", "Show Lower Limit (Trend)"), 
                   ("showHSpec_trend", "Show High Specification (Trend)"), ("showLSpec_trend", "Show Low Specification (Trend)"), 
                   ("showMed_trend", "Show Median Line (Trend)"), ("showMean_trend", "Show Mean Line (Trend)"),
                   # histo
                   ("showHL_histo", "Show Upper Limit (Histo)"), ("showLL_histo", "Show Lower Limit (Histo)"), 
                   ("showHSpec_histo", "Show High Specification (Histo)"), ("showLSpec_histo", "Show Low Specification (Histo)"), 
                   ("showMed_histo", "Show Median Line (Histo)"), ("showMean_histo", "Show Mean Line (Histo)"), 
                   ("showBoxp_histo", "Show Boxplot"), ("showBoxpOl_histo", "Show Boxplot Outlier"), 
                   ("showBars_histo", "Show Histogram Bars"), ("binCount", "Bin Count"), ("showSigma", "δ Lines"),
                   # PPQQ
                   ("x_ppqq", "X of Normal Plot"), ("y_ppqq", "Y of Normal Plot"), 
                   # general
                   ("language", "Language"), ("font", "Font"), ("recentFolder", "Recent Folder"), 
                   ("dataNotation", "Data Notation"), ("dataPrecision", "Data Precison"), 
                   ("cpkThreshold", "Cpk Warning Threshold"), ("checkCpk", "Search Low Cpk"), ("sortTestList", "Sort TestList"),
                   ("fileSymbol", "File Symbols (Scatter Points)"), 
                   # color
                   ("siteColor", "Site Colors"), ("sbinColor", "Software Bin Colors"), ("hbinColor", "Hardware Bin Colors")]


# This is the setting that will
# be used across all files
GlobalSetting = SettingParams()


def getSetting() -> SettingParams:
    return GlobalSetting


def updateSetting(**kwargs):
    global GlobalSetting
    for key, value in kwargs.items():
        if key in GlobalSetting.__dict__:
            setattr(GlobalSetting, key, value)


def setSettingDefaultColor(availableSites: list, SBIN_Info: dict, HBIN_Info: dict):
    """
    Update default color for hbin & sbin, needed
    when loading a new file with different bin number
    """
    global GlobalSetting
    # generate site color if not exist
    for site in availableSites:
        if site not in GlobalSetting.siteColor:
            GlobalSetting.siteColor[site] = rHEX()
    # init bin color by bin info
    for (binColorDict, bin_info) in [(GlobalSetting.sbinColor, SBIN_Info),
                                     (GlobalSetting.hbinColor, HBIN_Info)]:
        for bin_num in bin_info.keys():
            binType = bin_info[bin_num]["BIN_PF"]   # P, F or Unknown
            defaultColor = "#00CC00" if binType == "P" else ("#CC0000" if binType == "F" else "#FE7B00")
            if bin_num not in binColorDict:
                binColorDict[bin_num] = defaultColor


def setSettingDefaultSymbol(num_files: int):
    """
    Update file symbols if multiple files loaded
    """    
    global GlobalSetting
    for fid in range(num_files):
        if fid not in GlobalSetting.fileSymbol:
            GlobalSetting.fileSymbol[fid] = rSymbol()


def updateRecentFolder(filepath: str):
    dirpath = os.path.dirname(filepath)
    # update settings
    updateSetting(recentFolder = dirpath)


def loadConfigFile():
    global GlobalSetting
    try:
        configData = toml.load(sys.CONFIG_PATH)
        configString = dict([(v, k) for (k, v) in settingNamePair])
        for sec, secDict in configData.items():
            if sec == "Color Setting":
                # convert string key (site/sbin/hbin) to int
                for humanString, colorDict in secDict.items():
                    if humanString in configString:
                        attr = configString[humanString]    # e.g. siteColor
                        oldColorDict = getattr(GlobalSetting, attr)
                        for numString, hexColor in colorDict.items():
                            try:
                                num = int(numString)
                            except ValueError:
                                continue        # skip the invalid site or bin
                            if isHexColor(hexColor): 
                                oldColorDict[num] = hexColor
            else:
                for humanString, param in secDict.items():
                    if humanString in configString:
                        attr = configString[humanString]    # e.g. showHL_trend
                        # file symbol in general section is a dict
                        if attr == "fileSymbol":
                            oldSymbolDict = getattr(GlobalSetting, attr)
                            for numString, symbol in param.items():
                                try:
                                    num = int(numString)
                                except ValueError:
                                    continue
                                if isValidSymbol(symbol):
                                    oldSymbolDict[num] = symbol
                            continue
                        if type(param) == type(getattr(GlobalSetting, attr)):
                            
                            setattr(GlobalSetting, attr, param)
    except (FileNotFoundError, TypeError, toml.TomlDecodeError):
        # any error occurs in config file reading, simply ignore
        pass
    
    
def dumpConfigFile():
    # save data to toml config
    configData = {"General": {},
                  "Trend Plot": {},
                  "Histo Plot": {},
                  "PP/QQ Plot": {},
                  "Color Setting": {}}
    configName = dict(settingNamePair)
    for k, v in GlobalSetting.__dict__.items():
        if k in ["language", "font", "recentFolder", 
                 "dataNotation", "dataPrecision", 
                 "checkCpk", "cpkThreshold", "sortTestList"]:
            # General
            configData["General"][configName[k]] = v
            
        elif k in ["showHL_trend", "showLL_trend", 
                   "showHSpec_trend", "showLSpec_trend", 
                   "showMed_trend", "showMean_trend"]:
            # Trend
            configData["Trend Plot"][configName[k]] = v
            
        elif k in ["showHL_histo", "showLL_histo", 
                   "showHSpec_histo", "showLSpec_histo", 
                   "showMed_histo", "showMean_histo", 
                   "showBoxp_histo", "showBoxpOl_histo", 
                   "showBars_histo", "binCount", "showSigma"]:
            # Histo
            configData["Histo Plot"][configName[k]] = v

        elif k in ["x_ppqq", "y_ppqq"]:
            # PPQQ
            configData["PP/QQ Plot"][configName[k]] = v
        
        elif k in ["fileSymbol", "siteColor", "sbinColor", "hbinColor"]:
            # dict
            # change Int key to string, since toml only support string keys
            v = dict([(str(intKey), color) for intKey, color in v.items()])
            if k == "fileSymbol":
                section = "General"
            else:
                section = "Color Setting"
            configData[section][configName[k]] = v
            
    with open(sys.CONFIG_PATH, "w+", encoding="utf-8") as fd:
        toml.dump(configData, fd)


def loadFonts():
    for fn in os.listdir(os.path.join(sys.rootFolder, "fonts")):
        if not fn.endswith(".ttf"): continue
        fontPath = os.path.join(sys.rootFolder, "fonts", fn)
        fontIdx = QtGui.QFontDatabase.addApplicationFont(fontPath)
        if fontIdx < 0:
            print(f"Font {fn} cannot be loaded to QT")


def getLoadedFontNames() -> list:
    '''
    get top 100 font names from qt font db
    '''
    names = set()
    for i in range(100):
        # get 100 fonts at most
        ffamilies = QtGui.QFontDatabase.applicationFontFamilies(i)
        if ffamilies:
            names.add(ffamilies[0])
        else:
            break
    return sorted(names)


isMac = platform.system() == 'Darwin'


# icon related
iconDict = {}


convert2QIcon = lambda raw: \
    QtGui.QIcon(
        QtGui.QPixmap.fromImage(
            QtGui.QImage.fromData(raw, format = 'SVG')))


def getIcon(name: str) -> QtGui.QIcon:
    global iconDict
    if name not in iconDict:
        iconDict[name] = convert2QIcon(rust_stdf_helper.get_icon_src(name))
    return iconDict[name]


WHITE_COLOR = "#FFFFFF"
FAIL_DUT_COLOR = "#CC0000"
OVRD_DUT_COLOR = "#D0D0D0"
UNKN_DUT_COLOR = "#FE7B00"


FILE_FILTER = '''All Supported Files (*.std* *.std*.gz *.std*.bz2 *.std*.zip);;
                STDF (*.std *.stdf);;
                Compressed STDF (*.std*.gz *.std*.bz2 *.std*.zip);;
                All Files (*.*)'''


DUT_SUMMARY_QUERY = '''SELECT
                            DUTIndex,
                            Dut_Info.Fid AS "File ID",
                            PartID AS "Part ID",
                            'Head ' || HEAD_NUM || ' - ' || 'Site ' || SITE_NUM AS "Test Head - Site",
                            TestCount AS "Tests Executed",
                            TestTime || ' ms' AS "Test Time",
                            'Bin ' || HBIN AS "Hardware Bin",
                            'Bin ' || SBIN AS "Software Bin",
                            wf.WAFER_ID AS "Wafer ID",
                            '(' || XCOORD || ', ' || YCOORD || ')' AS "(X, Y)",
                            printf("%s - 0x%02X", CASE 
                                    WHEN Supersede=1 THEN 'Superseded' 
                                    WHEN Flag & 24 = 0 THEN 'Pass' 
                                    WHEN Flag & 24 = 8 THEN 'Failed' 
                                    ELSE 'Unknown' 
                                    END, Flag) AS "DUT Flag"
                        FROM (Dut_Info 
                            LEFT JOIN (SELECT 
                                            Fid, WaferIndex, WAFER_ID 
                                        FROM 
                                            Wafer_Info) AS "wf" 
                            ON Dut_Info.Fid = wf.Fid AND Dut_Info.WaferIndex = wf.WaferIndex)'''


# ********** python equivalent ******** #
# # generate approx location
# if AfterDUTIndex == 0:
#     leftStr = "|"
#     midStr = RecordType
#     rightStr = "PIR #1"
# elif isBeforePRR:
#     leftStr = f"PIR #{AfterDUTIndex}"
#     midStr = RecordType
#     rightStr = f"PRR #{AfterDUTIndex}"
# else:
#     leftStr = f"PIR #{AfterDUTIndex}"
#     midStr = f"PRR #{AfterDUTIndex}"
#     rightStr = RecordType
DATALOG_QUERY = '''SELECT
                        Fid as "File ID",
                        RecordType AS "Record Type",
                        '\n' || Value || '\n' AS "Value",
                        printf("%s ··· %s ··· %s",  
                                CASE 
                                    WHEN AfterDUTIndex == 0 THEN "|" 
                                    ELSE printf("PIR #%d", AfterDUTIndex) END, 
                                CASE 
                                    WHEN isBeforePRR == 1 THEN RecordType 
                                    ELSE printf("PRR #%d", AfterDUTIndex) END, 
                                CASE 
                                    WHEN AfterDUTIndex == 0 THEN "PIR #1" 
                                    WHEN isBeforePRR == 1 THEN printf("PRR #%d", AfterDUTIndex) 
                                    ELSE RecordType END) AS "Approx. Location"
                    FROM
                        Datalog'''


# check if a test item passed: bit7-6: 00 pass; 10 fail; x1 none, treated as pass; treat negative flag (indicate not tested) as pass
isPass = lambda flag: True if flag < 0 or flag & 0b11000000 == 0 else (False if flag & 0b01000000 == 0 else True)


# simulate a Enum in python
# class Tab(tuple): __getattr__ = tuple.index
# tab = Tab(["Info", "Trend", "Histo", "Bin", "Wafer"])
class tab(IntEnum):
    Info = 0
    Trend = 1
    Histo = 2
    PPQQ = 3
    Bin = 4
    Wafer = 5
    Correlate = 6
    

class REC(IntEnum):
    '''Constants of STDF Test Records: sub'''
    PTR = 10
    FTR = 20
    MPR = 15
    

record_name_dict = {
    REC.PTR: "PTR",
    REC.FTR: "FTR",
    REC.MPR: "MPR"
}

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
mirFieldNames = ["BYTE_ORD", "SETUP_T", "START_T", "FINISH_T", "STAT_NUM", 
                 "MODE_COD", "RTST_COD", "PROT_COD", "BURN_TIM", "CMOD_COD", 
                 "LOT_ID", "PART_TYP", "NODE_NAM", "TSTR_TYP", "JOB_NAM", 
                 "JOB_REV", "SBLOT_ID", "OPER_NAM", "EXEC_TYP", "EXEC_VER", 
                 "TEST_COD", "TST_TEMP", "USER_TXT", "AUX_FILE", "PKG_TYP", 
                 "FAMLY_ID", "DATE_COD", "FACIL_ID", "FLOOR_ID", "PROC_ID", 
                 "OPER_FRQ", "SPEC_NAM", "SPEC_VER", "FLOW_ID", "SETUP_ID", 
                 "DSGN_REV", "ENG_ID", "ROM_COD", "SERL_NUM", "SUPR_NAM", 
                 "DISP_COD", "USR_DESC", "EXC_DESC"]

mirDescriptions = ["Byte Order", "Setup Time", "Start Time", "Finish Time", 
                   "Station Number", "Test Mode Code", "Retest Code", 
                   "Protection Code", "Burn-in Time", "Command Mode Code", 
                   "Lot ID", "Product ID", "Node Name", "Tester Type", 
                   "Job Name", "Job Revision", "Sublot ID", "Operator ID", 
                   "Tester Software Type", "Tester Software Version", 
                   "Step ID", "Test Temperature", "User Text", 
                   "Auxiliary File Name", "Package Type", "Family ID", 
                   "Date Code", "Facility ID", "Floor ID", "Process ID", 
                   "Operation Frequency", "Test Spec Name", "Test Spec Version", 
                   "Flow ID", "Setup ID", "Design Revision", "Engineer Lot ID", 
                   "ROM Code ID", "Serial Number", "Supervisor ID", 
                   "Lot Disposition Code", "Lot Description From User", 
                   "Lot Description From Exec"]

mirDict = dict(zip(mirFieldNames, mirDescriptions))

rHEX = lambda: "#"+"".join([choice('0123456789ABCDEF') for _ in range(6)])


# check if a hex color string
def isHexColor(color: str) -> bool:
    '''Check if a given str is a valid hex color #RRGGBB[AA]'''
    color = color.lower()
    if color.startswith("#") and len(color) in [7, 9]:
        hexNum = list(map(lambda num: f'{num:x}', range(16)))
        for letter in color[1:]:
            if not letter in hexNum:
                return False
        return True
    else:
        return False


symbolName = ['o', 's', 'd', '+', 't', 't1', 't2', 't3', 'p', 'h', 'star', 'x', 'arrow_up', 'arrow_right', 'arrow_down', 'arrow_left', 'crosshair']
symbolChar = ['○', '▢', '◇', '+', '▽', '△', '▷', '◁', '⬠', '⬡', '☆', '⨯', '↑', '→', '↓', '←', '⊕']
symbolChar2Name = dict(zip(symbolChar, symbolName))

rSymbol = lambda: choice(symbolName)

def isValidSymbol(s: str) -> bool:
    '''check if `s` is in pyqtgraph symbol list'''
    return s in symbolName


def getProperFontColor(background: QtGui.QColor) -> QtGui.QColor:
    # https://stackoverflow.com/questions/3942878/how-to-decide-font-color-in-white-or-black-depending-on-background-color
    if (background.red()*0.2126 + 
        background.green()*0.7152 + 
        background.blue()*0.0722) > 140:
        return QtGui.QColor("#000000")
    else:
        return QtGui.QColor("#FFFFFF")


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
    _ = [os.remove(allLogFiles[i]) for i in range(len(allLogFiles)-5)] if len(allLogFiles) > 5 else []


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


def deleteWidget(w2delete):
    '''delete QWidget(s) and release its memory'''
    if isinstance(w2delete, QWidget):
        w2delete.setParent(None)
        w2delete.deleteLater()
    elif isinstance(w2delete, list):
        for w in w2delete:
            deleteWidget(w)


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
    if RTN_STAT >= 0 and RTN_STAT <= 0xA:
        return returnStateInfo[RTN_STAT]
    else:
        # invalid range, return empty string
        return ""


def wafer_direction_name(symbol: str) -> str:
    return direction_symbol.get(symbol, symbol)


def parseTestString(test_name_string: str, isWaferName: bool = False) -> tuple:
    '''
    Parse string from 
        `TestSelection` UI into (test num, pmr index, test name)
        `WaferSelection` UI into (wafer index, file id, wafer name)
    '''
    if isWaferName:
        # split up to 2 elements
        tmpList = test_name_string.split("\t", 1)
        waferIndex = -1
        fid = -1
        wafer_name = tmpList[-1]
        
        if tmpList[0] == "-":
            # stacked wafer, use default value
            pass
        else:
            # other have a pattern "File{}-#{}"
            fileStr, waferindStr = tmpList[0].split("-")
            waferIndex = int(waferindStr.strip("#"))
            fid = int(fileStr.strip("File"))
            
        return (waferIndex, fid, wafer_name)
    
    else:
        # split up to 3 elements
        tmpList = test_name_string.split("\t", 2)
        test_num = int(tmpList[0])
        # set default PMR index to 0
        pmr = 0
        test_name = tmpList[-1]
        
        if len(tmpList) > 2:
            # a possible MPR test, e.g. [test num, #PMR, test name]
            # try to conver to int
            try:
                pmr = int(tmpList[1].strip("#"))
            except ValueError:
                # if failed, means the orignal test name
                # has the pattern of "#%s\t%s"
                test_name = f"{tmpList[1]}\t{test_name}"
                
        return (test_num, pmr, test_name)


def openFileInOS(filepath: str):
    # https://stackoverflow.com/a/435669
    filepath = os.path.normpath(filepath)
    if platform.system() == 'Darwin':       # macOS
        subprocess.call(('open', filepath))
    elif platform.system() == 'Windows':    # Windows
        subprocess.call(f'cmd /c start "" "{filepath}"', creationflags = \
            subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
    else:                                   # linux variants
        subprocess.call(('xdg-open', filepath))


def revealFile(filepath: str):
    filepath = os.path.normpath(filepath)
    if platform.system() == 'Darwin':       # macOS
        subprocess.call(('open', '-R', filepath))
    elif platform.system() == 'Windows':    # Windows
        subprocess.call(f'explorer /select,"{filepath}"', creationflags = \
            subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
    else:                                   # linux variants
        subprocess.call(('xdg-open', os.path.dirname(filepath)))


def get_file_size(p: str) -> str:
    try:
        return "%.2f MB"%(os.stat(p).st_size / 2**20)
    except Exception:
        return "?? MB"
    except SystemExit:
        pass


class GeneralWorker(QObject):
    finished = Signal()
    
    def __init__(self, jobFunc, jobArgs: tuple, jobName: str, messageSignal=None):
        super().__init__()
        self.job = jobFunc
        self.jobArgs = jobArgs
        self.name = jobName
        self.msgSignal = messageSignal
        
    def run(self):
        if self.msgSignal:
            self.msgSignal.emit(f"{self.name} started", False, False, False)
        self.job(*self.jobArgs)
        if self.msgSignal:
            self.msgSignal.emit(f"{self.name} done!", False, False, False)
        self.finished.emit()


def runInQThread(jobFunc, args: tuple, jobName: str, messageSignal):
    thread = QThread()
    worker = GeneralWorker(jobFunc, args, jobName, messageSignal)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    # start
    thread.start()
    # let caller hold reference to prevent
    # being garbage collected
    return (worker, thread)
    

def get_png_size(image: io.BytesIO):
    '''http://coreygoldberg.blogspot.com/2013/01/python-verify-png-file-and-get-image.html '''
    image.seek(0)
    data = image.read(24)
    image.seek(0, 2)    # restore position
    
    if data[:8] == b'\211PNG\r\n\032\n'and (data[12:16] == b'IHDR'):
        # is png
        width = int.from_bytes(data[16:20], byteorder="big")
        height = int.from_bytes(data[20:24], byteorder="big")
        return (width, height)
    else:
        raise TypeError("Input is not a PNG image")


def pyqtGraphPlot2Bytes(chart) -> io.BytesIO:
    if isinstance(chart, pg.GraphicsView):
        exp = ImageExporter(chart.sceneObj)
        img: QtGui.QImage = exp.export(toBytes=True)
        # use bytearray to store data
        ba = QtCore.QByteArray()
        buf = QtCore.QBuffer(ba)
        buf.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        return io.BytesIO(ba.data())
            
    elif isinstance(chart, list) and len(chart) > 0:
        return pyqtGraphPlot2Bytes(chart[0])
    
    return None


def showCompleteMessage(transFunc, outPath: str, title=None, infoText=None, icon=None):
    msgbox = QMessageBox(None)
    if title:
        msgbox.setText(transFunc(title))
    else:
        msgbox.setText(transFunc("Completed"))
    
    if infoText:
        msgbox.setInformativeText(transFunc(infoText))
    else:
        msgbox.setInformativeText(transFunc("File is saved in %s") % outPath)
    
    if icon:
        msgbox.setIcon(icon)
    
    revealBtn = msgbox.addButton(transFunc(" Reveal in folder "), QMessageBox.ButtonRole.ApplyRole)
    openBtn = msgbox.addButton(transFunc("Open..."), QMessageBox.ButtonRole.ActionRole)
    okBtn = msgbox.addButton(transFunc("OK"), QMessageBox.ButtonRole.YesRole)
    msgbox.setDefaultButton(okBtn)
    msgbox.exec_()
    if msgbox.clickedButton() == revealBtn:
        revealFile(outPath)
    elif msgbox.clickedButton() == openBtn:
        openFileInOS(outPath)
    

def validateSession(dbPath: str):
    tableSet = set(["File_List", "File_Info", "Wafer_Info", "Dut_Info", "Dut_Counts", 
                    "Test_Info", "PTR_Data", "MPR_Data", "FTR_Data", "Bin_Info", 
                    "Pin_Map", "Pin_Info", "TestPin_Map", "Dynamic_Limits", "Datalog"])
    try:
        con = sqlite3.connect(dbPath)
        cur = con.cursor()
        currentTable = set([name 
                            for name,
                            in cur.execute('''SELECT 
                                                    name 
                                                FROM 
                                                    sqlite_master 
                                                WHERE 
                                                    type="table"''')])
        diff = currentTable.difference(tableSet)
        if diff:
            return False, f"Mismatched tables {','.join(diff)}"
        else:
            return True, ""
    except Exception as e:
        return False, repr(e)


__all__ = ["SettingParams", "tab", "REC", "symbolName", "symbolChar", "symbolChar2Name", 
           
           "getSetting", "updateSetting", "updateRecentFolder", 
           "setSettingDefaultColor", "setSettingDefaultSymbol", "loadConfigFile", "dumpConfigFile", 
           
           "WHITE_COLOR", "FAIL_DUT_COLOR", "OVRD_DUT_COLOR", "UNKN_DUT_COLOR", 
           "FILE_FILTER", "DUT_SUMMARY_QUERY", "DATALOG_QUERY", "mirFieldNames", "mirDict", "isMac", 
           
           "parseTestString", "isHexColor", "getProperFontColor", "init_logger", "runInQThread", 
           "loadFonts", "getLoadedFontNames", "rSymbol", "getIcon", "get_png_size", 
           "calc_cpk", "deleteWidget", "isPass", "isValidSymbol", "pyqtGraphPlot2Bytes", 
           "showCompleteMessage", "rHEX", "get_file_size", "validateSession", 
           
           "translate_const_dicts", "dut_flag_parser", "test_flag_parser", "return_state_parser", 
           "wafer_direction_name",
           ]