#
# stdfOffsetRetriever.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: July 12th 2020
# -----
# Last Modified: Tue Mar 30 2021
# Modified By: noonchen
# -----
# Copyright (c) 2020 noonchen
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



import os, sys, logging
import time, datetime
import struct
from array import array
import threading as th
import multiprocessing as mp
from .stdfData import stdfData
from .pystdf import V4
from .pystdf.IO_Offset_forViewer import stdIO
from .pystdf.RecordParser import RecordParser
# import sqlite3

logger = logging.getLogger("STDF Viewer")

formatMap = {
  "C1": "c",
  "B1": "B",
  "U1": "B",
  "U2": "H",
  "U4": "I",
  "U8": "Q",
  "I1": "b",
  "I2": "h",
  "I4": "i",
  "I8": "q",
  "R4": "f",
  "R8": "d"}

scale_char = {15: "f",
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

def getIntType(num):
    for t in ["H", "I", "L", "Q"]:
        try:
            array(t, [num])
            return t
        except OverflowError:
            continue
    return "Q"

class Process(mp.Process):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self._pcon, self._ccon = mp.Pipe()
        self._exception = None
        
    def run(self):
        try:
            mp.Process.run(self)
            self._ccon.send(None)
        except:
            self._ccon.send(sys.exc_info()[:2])
            
    @property
    def exception(self):
        if self._pcon.poll():
            self._exception = self._pcon.recv()
        return self._exception


def getFileSize(fd):
    # assume fd has attr "name"
    path = fd.name
    if path.endswith("gz"):
        # open gzip file as a binary file, not a gz obj
        with open(path, "rb") as f:
            f.seek(-4, 2)
            fsize = struct.unpack('I', f.read(4))[0]
    else:
        # bzip file size is not known before uncompressing, return compressed file size instead
        fsize = os.stat(fd.name).st_size
    return fsize


class stdfSummarizer:
    
    def __init__(self, QSignal=None, flag=None, q=None, fileSize=1):
        # # database
        # self.dbcon = sqlite3.connect('test.db')
        # self.dbcur = self.dbcon.cursor()
        # self.dbcur.execute('''DROP TABLE IF EXISTS DataOffsets''')
        # self.dbcur.execute(
        #     '''CREATE TABLE IF NOT EXISTS DataOffsets (
        #     HEAD_NUM, 
        #     SITE_NUM, 
        #     TEST_NUM, 
        #     DUTIndex,
        #     recHeader,
        #     Endian,
        #     Offset,
        #     Length)''')
        # self.dbcur.execute('''PRAGMA synchronous = EXTRA''')
        # self.dbcur.execute('''PRAGMA journal_mode = WAL''')
        # pyqt signal
        self.flag = flag
        self.QSignal = QSignal
        self.q = q
        
        self.offset = 0     # current position
        self.reading = True
        # get file size in Bytes
        self.fileSize = fileSize
        self.offsetType = getIntType(fileSize)
        # no need to update progressbar if signal is None
        if self.QSignal: 
            self.QSignal.emit(0)
            self.pb_thread = th.Thread(target=self.sendProgress)
            self.pb_thread.start()

        # precompiled struct
        self.cplStruct = {}
        # stdf data
        self.endian = "="
        self.stdfData = stdfData()
        # used for recording PTRs, MPRs that already read possibly omitted fields
        self.readAlreadyTR = {}
        
        # File info
        self.fileInfo = {}
        self.dutIndex = 0  # get 1 as index on first +1 action, used for counting total DUT number
        self.waferIndex = 0 # used for counting total wafer number
        self.dutPassed = 0
        self.dutFailed = 0
        # Pin dict
        self.pinDict = {}   # key: Pin index, value: Pin name
        # site data
        self.testData = {}   # key: head_num, value: {key: site_num, v = {test_num: DefaultDict}}, DefaultDict = {"TestName": "", "Offset": None, "Length": None, "DUTIndex": None}

        self.hbinSUM = {}  # key: head_num, value: {key: site_num, value: {key: HBIN, value: HBIN_count}}
        self.sbinSUM = {}  # key: head_num, value: {key: site_num, value: {key: SBIN, value: SBIN_count}}
        self.hbinDict = {}  # key: HBIN, value: [HBIN_NAM, HBIN_PF]
        self.sbinDict = {}  # key: SBIN, value: [SBIN_NAM, SBIN_PF]
        
        self.head_site_dutIndex = {}    # key: head numb << 8 | site num, value: dutIndex, a tmp dict used to retrieve dut index by head/site info, required by multi head stdf files
        self.dutDict = {}   # key: dutIndex, value: {HEAD_NUM, SITE_NUM, PART_FLG, NUM_TEST, TEST_T, PART_ID, SOFT_BIN, HARD_BIN}, note: for incomplete stdf, KeyError could be raised as the PRR might be missing
        
        self.head_waferIndex = {}  # similar to head_site_dutIndex, but one head per wafer
        self.waferInfo = {} # key: center_x, center_y, diameter, size_unit
        self.waferDict = {} # key: waferIndex, value: {WAFER_ID, dutIndexList, coordList}
        
        self.globalTestFlag = {}    # key: test number, value: fail count
                
        # before analyze, backup the previous ocache in case user terminated 2nd file reading
        RecordParser.ocache_previous = RecordParser.ocache
        RecordParser.ocache = {}
        self.analyze()  # start
    
    
    def sendProgress(self):
        while self.reading:
            if getattr(self.flag, "stop", False):
                return
                
            time.sleep(0.1)
            if self.QSignal: 
                self.QSignal.emit(int(10000 * self.offset / self.fileSize))     # times additional 100 to save 2 decimal
        
        
    def set_endian(self, endian_from_parser):
        # update endian for info parse, input is a tuple
        self.endian, = endian_from_parser
        RecordParser.endian = endian_from_parser
        # pre compile standard format and 0s-255s
        for stdfmt, cfmt in formatMap.items():
            self.cplStruct[self.endian+cfmt] = struct.Struct(self.endian+cfmt)
        for i in range(256):
            self.cplStruct["%ds"%i] = struct.Struct("%ds"%i)
        
        
    def analyze(self):
        while self.q:
            queueDataList = self.q.get()
            if len(queueDataList):
                if getattr(self.flag, "stop", False):
                    return
            
                if isinstance(queueDataList[0], str):
                    # queueDataList = [endian]
                    self.set_endian(queueDataList[0])
                else:
                    # queueDataList = [dicts]
                    for d in queueDataList:
                        recHeader = d["recHeader"]
                        self.offset = d["offset"]
                        binaryLen = d["length"]
                        rawData = d["rawData"]
                        self.onRec(recHeader=recHeader, binaryLen=binaryLen, rawData=rawData)
            else:
                # queueDataList = [], finish
                break
        # join progress bar thread if finished
        self.after_complete()
        
        
    def after_complete(self):
        self.reading = False
        # copy info to stdfData obj
        self.stdfData.fileInfo = self.fileInfo
        self.stdfData.dutIndex = self.dutIndex
        self.stdfData.waferIndex = self.waferIndex
        self.stdfData.dutPassed = self.dutPassed
        self.stdfData.dutFailed = self.dutFailed
        self.stdfData.pinDict = self.pinDict
        self.stdfData.testData = self.testData
        self.stdfData.hbinSUM = self.hbinSUM
        self.stdfData.sbinSUM = self.sbinSUM
        self.stdfData.hbinDict = self.hbinDict
        self.stdfData.sbinDict = self.sbinDict
        self.stdfData.dutDict = self.dutDict
        self.stdfData.waferInfo = self.waferInfo
        self.stdfData.waferDict = self.waferDict
        self.stdfData.globalTestFlag = self.globalTestFlag
        
        # self.dbcon.commit()
        # self.dbcon.close()
        
        if self.QSignal: 
            self.pb_thread.join()
            # update once again when finished, ensure the progress bar hits 100%
            self.QSignal.emit(10000)
        
        
    def onRec(self, recHeader=0, binaryLen=0, rawData=b""):
        # most frequent records on top to reduce check times
        # in Cython it will be replaced by switch case, which will be more efficient than py_dict/if..else
        if recHeader == 3850 or recHeader == 3855 or recHeader == 3860: # PTR 3850 # MPR 3855 # FTR 3860
            self.onTR(recHeader, binaryLen, rawData)
        elif recHeader == 1290: # PIR 1290
            self.onPIR(recHeader, binaryLen, rawData)
        elif recHeader == 1300: # PRR 1300
            self.onPRR(recHeader, binaryLen, rawData)
        elif recHeader == 522: # WIR 522
            self.onWIR(recHeader, binaryLen, rawData)
        elif recHeader == 532: # WRR 532
            self.onWRR(recHeader, binaryLen, rawData)
        elif recHeader == 2590: # TSR 2590
            self.onTSR(recHeader, binaryLen, rawData)
        elif recHeader == 296: # HBR 296
            self.onHBR(recHeader, binaryLen, rawData)
        elif recHeader == 306: # SBR 306
            self.onSBR(recHeader, binaryLen, rawData)
        elif recHeader == 316: # PMR 316
            self.onPMR(recHeader, binaryLen, rawData)
        elif recHeader == 266: # MIR 266
            self.onMIR(recHeader, binaryLen, rawData)
        elif recHeader == 542: # WCR 542
            self.onWCR(recHeader, binaryLen, rawData)
            
        # FAR 10
        # ATR 20
        # MRR 276
        # PCR 286
        # PGR 318
        # PLR 319
        # RDR 326
        # SDR 336
        # BPS 5130
        # EPS 5140
        # GDR 12810
        # DTR 12830
        

    def onMIR(self, recHeader, binaryLen, rawData):
        valueDict = RecordParser.parse_raw(recHeader, binaryLen, rawData)
        unix2Time = lambda unix: str(datetime.datetime.utcfromtimestamp(unix).strftime("%Y-%m-%d %H:%M:%S (UTC)"))
        
        self.fileInfo["SETUP_T"] = unix2Time(valueDict["SETUP_T"])
        self.fileInfo["START_T"] = unix2Time(valueDict["START_T"])
        self.fileInfo["STAT_NUM"] = str(valueDict["STAT_NUM"])
        self.fileInfo["MODE_COD"] = valueDict["MODE_COD"]
        self.fileInfo["RTST_COD"] = valueDict["RTST_COD"]
        self.fileInfo["PROT_COD"] = valueDict["PROT_COD"]
        self.fileInfo["BURN_TIM"] = str(valueDict["BURN_TIM"])
        self.fileInfo["CMOD_COD"] = valueDict["CMOD_COD"]
        self.fileInfo["LOT_ID"] = valueDict["LOT_ID"]
        self.fileInfo["PART_TYP"] = valueDict["PART_TYP"]
        self.fileInfo["NODE_NAM"] = valueDict["NODE_NAM"]
        self.fileInfo["TSTR_TYP"] = valueDict["TSTR_TYP"]
        self.fileInfo["JOB_NAM"] = valueDict["JOB_NAM"]
        self.fileInfo["JOB_REV"] = valueDict["JOB_REV"]
        self.fileInfo["SBLOT_ID"] = valueDict["SBLOT_ID"]
        self.fileInfo["OPER_NAM"] = valueDict["OPER_NAM"]
        self.fileInfo["EXEC_TYP"] = valueDict["EXEC_TYP"]
        self.fileInfo["EXEC_VER"] = valueDict["EXEC_VER"]
        self.fileInfo["TEST_COD"] = valueDict["TEST_COD"]
        self.fileInfo["TST_TEMP"] = valueDict["TST_TEMP"]
        self.fileInfo["USER_TXT"] = valueDict["USER_TXT"]
        self.fileInfo["AUX_FILE"] = valueDict["AUX_FILE"]
        self.fileInfo["PKG_TYP"] = valueDict["PKG_TYP"]
        self.fileInfo["FAMLY_ID"] = valueDict["FAMLY_ID"]
        self.fileInfo["DATE_COD"] = valueDict["DATE_COD"]
        self.fileInfo["FACIL_ID"] = valueDict["FACIL_ID"]
        self.fileInfo["FLOOR_ID"] = valueDict["FLOOR_ID"]
        self.fileInfo["PROC_ID"] = valueDict["PROC_ID"]
        self.fileInfo["OPER_FRQ"] = valueDict["OPER_FRQ"]
        self.fileInfo["SPEC_NAM"] = valueDict["SPEC_NAM"]        
        self.fileInfo["SPEC_VER"] = valueDict["SPEC_VER"]
        self.fileInfo["FLOW_ID"] = valueDict["FLOW_ID"]
        self.fileInfo["SETUP_ID"] = valueDict["SETUP_ID"]
        self.fileInfo["DSGN_REV"] = valueDict["DSGN_REV"]
        self.fileInfo["ENG_ID"] = valueDict["ENG_ID"]
        self.fileInfo["ROM_COD"] = valueDict["ROM_COD"]        
        self.fileInfo["SERL_NUM"] = valueDict["SERL_NUM"]
        self.fileInfo["SUPR_NAM"] = valueDict["SUPR_NAM"]
                
                
    def onPMR(self, recHeader, binaryLen, rawData):        
        valueDict = RecordParser.parse_raw(recHeader, binaryLen, rawData)
                
        PMR_INDX = valueDict["PMR_INDX"]
        CHAN_NAM = valueDict["CHAN_NAM"]
        PHY_NAM = valueDict["PHY_NAM"]
        LOG_NAM = valueDict["LOG_NAM"]

        self.pinDict[PMR_INDX] = [CHAN_NAM, PHY_NAM, LOG_NAM]
    
    
    def onPIR(self, recHeader, binaryLen, rawData):
        # used for linking TRs with PRR
        self.dutIndex += 1
        
        valueDict = RecordParser.parse_raw(recHeader, binaryLen, rawData)
        SITE_NUM = valueDict["SITE_NUM"]
        HEAD_NUM = valueDict["HEAD_NUM"]
        
        self.head_site_dutIndex[HEAD_NUM<<8 | SITE_NUM] = self.dutIndex
    
    
    def onTR(self, recHeader, binaryLen, rawData):
        # read testNum and siteNum
        THS_struct = self.cplStruct.setdefault("THS", struct.Struct(self.endian + formatMap["U4"]+formatMap["U1"]+formatMap["U1"]))
        TEST_NUM, HEAD_NUM, SITE_NUM = THS_struct.unpack(rawData[:6])
        currentDutIndex = self.head_site_dutIndex[HEAD_NUM<<8 | SITE_NUM]
        
        tmpHead = self.testData.setdefault(HEAD_NUM, {})
        tmpSite = tmpHead.setdefault(SITE_NUM, {})
        tmp_TestItem_site = tmpSite.setdefault(TEST_NUM, {})
        
        TEST_TXT = self.getTestName(recHeader, rawData)
        
        tmp_TestItem_site["TestName"] = TEST_TXT
        # required for on-the-fly parser
        tmp_TestItem_site["recHeader"] = recHeader
        tmp_TestItem_site["Endian"] = self.endian
             
        tmp_TestItem_site.setdefault("Length", array("H")).append(binaryLen)
        tmp_TestItem_site.setdefault("DUTIndex", array("I")).append(currentDutIndex)
        try:
            # for high compression file, e.g. bz2 or gz, the offset may way larger than
            # the compressed file size, and leading to Overflow
            tmp_TestItem_site.setdefault("Offset", array(self.offsetType)).append(self.offset)
        except OverflowError:
            logger.warning(f"Overflow occurred when save file offset, type code changed from {self.offset} to 'Q'")
            # when overflowed, create a new array to store the offset
            orig_arr: array = tmp_TestItem_site["Offset"]
            self.offsetType = "Q"
            new_arr = array(self.offsetType, orig_arr.tolist())
            new_arr.append(self.offset)
            tmp_TestItem_site["Offset"] = new_arr
            
        # self.dbcur.execute('''INSERT INTO DataOffsets VALUES (?,?,?,?,?,?,?,?)''', 
        #                    (HEAD_NUM, SITE_NUM, TEST_NUM, currentDutIndex, recHeader, self.endian, self.offset, binaryLen))
            
        # cache omitted fields
        # MUST pre-read and cache OPT_FLAG, RES_SCAL, LLM_SCAL, HLM_SCAL of a test item from the first record
        # as it may be omitted in the later record, causing typeError when user directly selects sites where 
        # no such field value is available in the data preparation.
        if TEST_NUM not in self.readAlreadyTR:
            self.readAlreadyTR[TEST_NUM] = ""
            RecordParser.updateOCache(recHeader, binaryLen, rawData)
                            
            
    def onPRR(self, recHeader, binaryLen, rawData):
        valueDict = RecordParser.parse_raw(recHeader, binaryLen, rawData)
        HEAD_NUM = valueDict["HEAD_NUM"]
        SITE_NUM = valueDict["SITE_NUM"]
        HARD_BIN = valueDict["HARD_BIN"]
        SOFT_BIN = valueDict["SOFT_BIN"]
        PART_FLG = valueDict["PART_FLG"]
        NUM_TEST = valueDict["NUM_TEST"]
        X_COORD = valueDict["X_COORD"]
        Y_COORD = valueDict["Y_COORD"]
        TEST_T = valueDict["TEST_T"]
        PART_ID = valueDict["PART_ID"]
        currentDutIndex = self.head_site_dutIndex[HEAD_NUM<<8 | SITE_NUM]
        
        tmpHHead = self.hbinSUM.setdefault(HEAD_NUM, {})
        tmpHSite = tmpHHead.setdefault(SITE_NUM, {})
        tmpHSumm = tmpHHead.setdefault(-1, {})
        
        tmpSHead = self.sbinSUM.setdefault(HEAD_NUM, {})
        tmpSSite = tmpSHead.setdefault(SITE_NUM, {})
        tmpSSumm = tmpSHead.setdefault(-1, {})
        tmpDUT = self.dutDict.setdefault(currentDutIndex, {})
        
        tmpHSite[HARD_BIN] = tmpHSite.setdefault(HARD_BIN, 0) + 1
        tmpHSumm[HARD_BIN] = tmpHSumm.setdefault(HARD_BIN, 0) + 1
        tmpSSite[SOFT_BIN] = tmpSSite.setdefault(SOFT_BIN, 0) + 1
        tmpSSumm[SOFT_BIN] = tmpSSumm.setdefault(SOFT_BIN, 0) + 1
        # key: dutIndex, value: {PART_FLG, NUM_TEST, TEST_T, PART_ID, SOFT_BIN, HARD_BIN}
        tmpDUT["NUM_TEST"] = NUM_TEST
        tmpDUT["TEST_T"] = TEST_T
        tmpDUT["PART_ID"] = PART_ID
        tmpDUT["HARD_BIN"] = HARD_BIN
        tmpDUT["SOFT_BIN"] = SOFT_BIN
        tmpDUT["HEAD_NUM"] = HEAD_NUM
        tmpDUT["SITE_NUM"] = SITE_NUM
        tmpDUT["PART_FLG"] = PART_FLG
        # update wafer only if WIR is detected
        if not self.waferIndex == 0:
            currentWaferIndex = self.head_waferIndex[HEAD_NUM]
            self.waferDict[currentWaferIndex]["dutIndexList"].append(currentDutIndex)
            self.waferDict[currentWaferIndex]["coordList"].append(array("h", [X_COORD, Y_COORD]))
            if X_COORD == -32768 or Y_COORD == -32768:
                pass
            else:
                if X_COORD < self.waferInfo.get("xmin",  32767): self.waferInfo["xmin"] = X_COORD
                if Y_COORD < self.waferInfo.get("ymin",  32767): self.waferInfo["ymin"] = Y_COORD
                if X_COORD > self.waferInfo.get("xmax", -32768): self.waferInfo["xmax"] = X_COORD
                if Y_COORD > self.waferInfo.get("ymax", -32768): self.waferInfo["ymax"] = Y_COORD
        
        if PART_FLG & 0b00011000 == 0:
            tmpDUT["PART_STAT"] = "Pass"
            self.dutPassed += 1
            # we can determine the type of hard/soft bin based on the part_flag
            # it is helpful if the std is incomplete and lack of HBR/SBR
            # if key is existed, do not update repeatedly
            if not HARD_BIN in self.hbinDict: self.hbinDict[HARD_BIN] = [str(HARD_BIN), "P"]
            if not SOFT_BIN in self.sbinDict: self.sbinDict[SOFT_BIN] = [str(SOFT_BIN), "P"]
            
        elif PART_FLG & 0b00010000 == 0:
            tmpDUT["PART_STAT"] = "Failed"
            self.dutFailed += 1
            if not HARD_BIN in self.hbinDict: self.hbinDict[HARD_BIN] = [str(HARD_BIN), "F"]
            if not SOFT_BIN in self.sbinDict: self.sbinDict[SOFT_BIN] = [str(SOFT_BIN), "F"]
                    
        else:
            # no pass/fail info
            tmpDUT["PART_STAT"] = "None"
            if not HARD_BIN in self.hbinDict: self.hbinDict[HARD_BIN] = [str(HARD_BIN), "U"]
            if not SOFT_BIN in self.sbinDict: self.sbinDict[SOFT_BIN] = [str(SOFT_BIN), "U"]
            
        
    def onHBR(self, recHeader, binaryLen, rawData):
        # This method is used for getting bin num/names/PF
        valueDict = RecordParser.parse_raw(recHeader, binaryLen, rawData)
                
        # SITE_NUM = valueDict["SITE_NUM"]
        HBIN_NUM = valueDict["HBIN_NUM"]
        HBIN_PF = valueDict["HBIN_PF"]
        HBIN_NAM = "Missing Name" if valueDict["HBIN_NAM"] == None else valueDict["HBIN_NAM"]
        # use the count from PRR as default, in case the file is incomplete
        # HBIN_CNT = valueDict["HBIN_CNT"]
        if not HBIN_NUM in self.hbinDict:
            # this bin is not seen in PRR, no predicted info, use the one in file
            self.hbinDict[HBIN_NUM] = [HBIN_NAM, HBIN_PF]
        else:
            # use PF info of HBR only if it's not missing, otherwise use the predicted info
            self.hbinDict[HBIN_NUM][0] = HBIN_NAM
            if HBIN_PF in ["P", "F"]: self.hbinDict[HBIN_NUM][1] = HBIN_PF 
       
        
    def onSBR(self, recHeader, binaryLen, rawData):
        valueDict = RecordParser.parse_raw(recHeader, binaryLen, rawData)        
        
        # SITE_NUM = valueDict["SITE_NUM"]
        SBIN_NUM = valueDict["SBIN_NUM"]
        SBIN_PF = valueDict["SBIN_PF"]
        SBIN_NAM = "Missing Name" if valueDict["SBIN_NAM"] == None else valueDict["SBIN_NAM"]
        
        if not SBIN_NUM in self.sbinDict:
            self.sbinDict[SBIN_NUM] = [SBIN_NAM, SBIN_PF]
        else:
            self.sbinDict[SBIN_NUM][0] = SBIN_NAM
            if SBIN_PF in ["P", "F"]: self.sbinDict[SBIN_NUM][1] = SBIN_PF


    def onWCR(self, recHeader, binaryLen, rawData):
        valueDict = RecordParser.parse_raw(recHeader, binaryLen, rawData)
        # key: center_x, center_y, diameter, size_unit
        self.waferInfo = {"center_x": valueDict["CENTER_X"],
                        "center_y": valueDict["CENTER_Y"],
                        "diameter": valueDict["WAFR_SIZ"],
                        "size_unit": valueDict["WF_UNITS"]}
    
    
    def onWIR(self, recHeader, binaryLen, rawData):
        valueDict = RecordParser.parse_raw(recHeader, binaryLen, rawData)
        self.waferIndex += 1
        if valueDict["WAFER_ID"] == "": 
            valueDict["WAFER_ID"] = "Missing Name"        
        HEAD_NUM = valueDict["HEAD_NUM"]
        self.head_waferIndex[HEAD_NUM] = self.waferIndex
        # init key-value for wafer dict 
        self.waferDict[self.waferIndex] = {"dutIndexList": array("I"), "coordList": [], **valueDict}
    
    
    def onWRR(self, recHeader, binaryLen, rawData):
        valueDict = RecordParser.parse_raw(recHeader, binaryLen, rawData)
        if valueDict["WAFER_ID"] == "": 
            valueDict["WAFER_ID"] = "Missing Name"
        HEAD_NUM = valueDict["HEAD_NUM"]
        
        currentWaferIndex = self.head_waferIndex[HEAD_NUM]
        self.waferDict[currentWaferIndex].update(valueDict)

    
    def onTSR(self, recHeader, binaryLen, rawData):
        # for fast find failed test number globally
        # don't care about head number nor site number
        valueDict = RecordParser.parse_raw(recHeader, binaryLen, rawData)
        TEST_NUM = valueDict["TEST_NUM"]
        FAIL_CNT = valueDict["FAIL_CNT"]
        if FAIL_CNT != 2**32-1: # 2**32-1 invalid number for FAIL_CNT
            self.globalTestFlag[TEST_NUM] = self.globalTestFlag.get(TEST_NUM, 0) + FAIL_CNT
    
    
    def getTestName(self, recHeader, rawData):
        """Read Test Name Efficiently by skipping unrelated bytes"""
        if recHeader == 3850:   # PTR 3850
            slen_byte = rawData[12:13]  # 4+1+1+1+1+4 = 12
            if slen_byte == b'':
                return "Missing Name"
            else:
                slen, = self.cplStruct[self.endian+formatMap["U1"]].unpack(slen_byte)
                tname_binary, = self.cplStruct[str(slen)+"s"].unpack(rawData[13 : 13+slen])
                return tname_binary.decode("ascii")

        elif recHeader == 3855:  # MPR 3855
            if len(rawData) >= 13:  # 4+1+1+1+1+2+2 = 12, +1 to ensure slen isn't omitted
                RTN_cnt, RSLT_cnt, = self.cplStruct.setdefault("U2U2", struct.Struct(self.endian + formatMap["U2"]+formatMap["U2"])).unpack(rawData[8:12])
                tname_offset = 12 + RTN_cnt*1 + RSLT_cnt*4
                slen, = self.cplStruct[self.endian+formatMap["U1"]].unpack(rawData[tname_offset : tname_offset+1])
                tname_binary, = self.cplStruct[str(slen)+"s"].unpack(rawData[tname_offset+1 : tname_offset+1+slen])
                return tname_binary.decode("ascii")
            else:
                return "Missing Name"
        
        elif recHeader == 3860:  # FTR 3860
            if len(rawData) >= 44:  # 4+1+1+1+1+4+4+4+4+4+4+2+2+2 = 38 (before array), +6 to ensure slen isn't omitted
                RTN_cnt, PGM_cnt, = self.cplStruct.setdefault("U2U2", struct.Struct(self.endian + formatMap["U2"]+formatMap["U2"])).unpack(rawData[34:38])
                offset = 38 + RTN_cnt*2 + (RTN_cnt//2 + RTN_cnt%2) + PGM_cnt*2 + (PGM_cnt//2 + PGM_cnt%2)   # U2 + N1, N1 = 4bits
                # skip Dn
                bitL, = self.cplStruct[self.endian+formatMap["U2"]].unpack(rawData[offset : offset+2])
                offset += 2 + bitL//8 + (1 if bitL%8 > 0 else 0)
                # skip Cn*3
                for _ in range(3):
                    L, = self.cplStruct[self.endian+formatMap["U1"]].unpack(rawData[offset : offset+1])
                    offset += 1 + L
                # get Cn of test name
                slen, = self.cplStruct[self.endian+formatMap["U1"]].unpack(rawData[offset : offset+1])
                tname_binary, = self.cplStruct[str(slen)+"s"].unpack(rawData[offset+1 : offset+1+slen])
                return  tname_binary.decode("ascii")
            else:
                return "Missing Name"
        
        else:
            return ""
 
 
    
def parser(path, flag, q):
    import gzip, bz2
    if os.path.isfile(path):
        if path.endswith("gz"):
            fileHandle = gzip.open(path, 'rb')
        elif path.endswith("bz2"):
            fileHandle = bz2.BZ2File(path, 'rb')
        else:
            fileHandle = open(path, 'rb')                
    
    P = stdIO(inp=fileHandle, flag=flag, q=q)
    P.parse()
    
    
class stdfDataRetriever:
    
    def __init__(self, fileHandle, QSignal=None, flag=None):
        self.error = None
        sys.excepthook = self.onProcessException
        th.excepthook = self.onThreadException
        
        fileSize = getFileSize(fileHandle)        # read file size may need to seek position (gz), do it first in case mess with parser
        self.useThread = (fileSize <= 15*2**20)        # choose different parsing option based on the file size, for file larger than 15M+, process will be faster
        if self.useThread: 
            from queue import Queue
            self.q = Queue(0)
            # if the file is small, use thread for efficiency
            task = th.Thread(target=parser, args=(fileHandle.name, flag, self.q), daemon=False)
        else:
            from multiprocessing import Queue
            self.q = Queue(0)
            # if the file is large, use process for high parallelism
            task = Process(target=parser, args=(fileHandle.name, flag, self.q), daemon=False)
        
        try:
            task.start()
            # analyze & store data from queue
            self.summarizer = stdfSummarizer(QSignal=QSignal, flag=flag, q=self.q, fileSize=fileSize)
            
            if not self.useThread: 
                # process is used
                task.terminate()
                if getattr(flag, "stop", False):
                    # child process will encounter error if we close the queue
                    # help us to terminate the process
                    self.q.close()
                    
            task.join()
            self.checkError(task)
        except:
            raise
            
            
    def getStdfData(self):
        return self.summarizer.stdfData
    
    
    def onProcessException(self, eT, eV, tb):
        self.error = eT(eV)
        
        
    def onThreadException(self, hookArgs):
        eT = hookArgs.exc_type
        eV = hookArgs.exc_value
        self.error = eT(eV)
        
        
    def checkError(self, process_task):
        if self.useThread:
            if self.error:
                raise self.error
        else:
            if process_task.exception:
                eT, eV = process_task.exception
                raise eT(eV)