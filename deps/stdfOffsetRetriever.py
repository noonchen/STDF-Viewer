#
# stdfOffsetRetriever.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: July 12th 2020
# -----
# Last Modified: Sun Dec 20 2020
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



import os
import time, datetime
import struct
from threading import Thread
from deps.pystdf import V4
from deps.pystdf.IO_Offset_forViewer import stdIO
from deps.pystdf.RecordParser import RecordParser

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


class stdfSummarizer:
    
    def __init__(self, fileHandle, QSignal=None, flag=None):
        # Func
        self.onRec = dict((recType, lambda **kargs: None)
                 for recType in V4.records)
        self.onRec[V4.mir] = self.onMIR
        self.onRec[V4.pmr] = self.onPMR
        self.onRec[V4.pir] = self.onPIR
        self.onRec[V4.ptr] = self.onTR
        self.onRec[V4.ftr] = self.onTR
        self.onRec[V4.mpr] = self.onTR
        self.onRec[V4.prr] = self.onPRR
        self.onRec[V4.hbr] = self.onHBR
        self.onRec[V4.sbr] = self.onSBR
        self.onRec[V4.wir] = self.onWIR
        self.onRec[V4.wrr] = self.onWRR
        
        # pyqt signal
        self.flag = flag
        self.QSignal = QSignal
        # get file size in Bytes
        self.offset = 0     # current position
        self.reading = True
        # no need to update progressbar if signal is None
        if self.QSignal: 
            self.fileSize = os.stat(fileHandle.name).st_size
            self.QSignal.emit(0)
            self.pb_thread = Thread(target=self.sendProgress)
            self.pb_thread.start()

        # File info
        self.fileInfo = {}
        self.endian = "="
        self.dutIndex = -1  # get 0 as index on first +1 action
        self.dutPassed = 0
        self.dutFailed = 0
        # Pin dict
        self.pinDict = {}   # key: Pin index, value: Pin name
        
        # precompiled struct
        self.cplStruct = {}
        # site data
        # when site_num == -1, v = data of all sites
        self.data = {}   # key: site_num, v = {test_num: DefaultDict}, DefaultDict = {"TestName": "", "Offset": None, "Length": None, "DUTIndex": None}

        self.hbinSUM = {}  # key: site_num, value: {key: HBIN, value: HBIN_count}
        self.sbinSUM = {}  # key: site_num, value: {key: SBIN, value: SBIN_count}
        self.hbinDict = {}  # key: HBIN, value: [HBIN_NAM, HBIN_PF]
        self.sbinDict = {}  # key: SBIN, value: [SBIN_NAM, SBIN_PF]
        self.dutDict = {}   # key: dutIndex, value: {PART_FLG, NUM_TEST, TEST_T, PART_ID, SOFT_BIN, HARD_BIN}, note: for incomplete stdf, KeyError could be raised as the PRR might be missing
    
    
    def sendProgress(self):
        while self.reading:
            if self.flag:
                if self.flag.stop == True: return
                
            time.sleep(0.1)
            if self.QSignal: 
                self.QSignal.emit(int(10000 * self.offset / self.fileSize))     # times additional 100 to save 2 decimal
        
        
    def before_begin(self, DataSource, endian_from_parser):
        # update endian for info parse, input is a tuple
        self.endian, = endian_from_parser
        # pre compile standard format and 0s-255s
        for stdfmt, cfmt in formatMap.items():
            self.cplStruct[self.endian+cfmt] = struct.Struct(self.endian+cfmt)
        for i in range(256):
            self.cplStruct["%ds"%i] = struct.Struct("%ds"%i)
        
        
    def before_send(self, DataSource, data_from_parser):
        recType, self.offset, binaryLen, rawData = data_from_parser
        self.onRec[recType](recType=recType, dataLen=binaryLen, rawData=rawData)
        
        
    def after_complete(self, DataSource):
        self.reading = False
        if self.QSignal: 
            self.pb_thread.join()
            # update once again when finished, ensure the progress bar hits 100%
            self.QSignal.emit(10000)
        

    def onMIR(self, **kargs):
        recType = kargs.get("recType", None)
        binaryLen = kargs.get("dataLen", 0)
        rawData = kargs.get("rawData", b'')
        
        RecordParser.endian = self.endian
        valueDict = RecordParser.parse_raw(recType, binaryLen, rawData)
        
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
                
                
    def onPMR(self, **kargs):
        recType = kargs.get("recType", None)
        binaryLen = kargs.get("dataLen", 0)
        rawData = kargs.get("rawData", b'')
        
        RecordParser.endian = self.endian
        valueDict = RecordParser.parse_raw(recType, binaryLen, rawData)
                
        PMR_INDX = valueDict["PMR_INDX"]
        CHAN_NAM = valueDict["CHAN_NAM"]
        PHY_NAM = valueDict["PHY_NAM"]
        LOG_NAM = valueDict["LOG_NAM"]

        self.pinDict[PMR_INDX] = [CHAN_NAM, PHY_NAM, LOG_NAM]
    
    
    def onPIR(self, **kargs):
        # used for linking TRs with PRR
        self.dutIndex += 1
    
    
    def onTR(self, **kargs):
        # on Test Record: FTR, PTR, MPR
        recType = kargs.get("recType", None)
        binaryLen = kargs.get("dataLen", 0)
        rawData = kargs.get("rawData", b'')
        
        # read testNum and siteNum
        THS_struct = self.cplStruct.setdefault("THS", struct.Struct(self.endian + formatMap["U4"]+formatMap["U1"]+formatMap["U1"]))
        TEST_NUM, _, SITE_NUM = THS_struct.unpack(rawData[:6])
        
        tmpSite = self.data.setdefault(SITE_NUM, {})
        tmpSumm = self.data.setdefault(-1, {})

        tmp_TestItem_site = tmpSite.setdefault(TEST_NUM, {})
        tmp_TestItem_summ = tmpSumm.setdefault(TEST_NUM, {})
        
        TEST_TXT = self.getTestName(recType, rawData)
        
        tmp_TestItem_site["TestName"] = TEST_TXT
        tmp_TestItem_summ["TestName"] = TEST_TXT
        # required for on-the-fly parser
        tmp_TestItem_site["RecType"] = recType
        tmp_TestItem_summ["RecType"] = recType
        tmp_TestItem_site["Endian"] = self.endian
        tmp_TestItem_summ["Endian"] = self.endian
                
        tmp_TestItem_site.setdefault("Offset", []).append(self.offset)
        tmp_TestItem_summ.setdefault("Offset", []).append(self.offset)
        tmp_TestItem_site.setdefault("Length", []).append(binaryLen)
        tmp_TestItem_summ.setdefault("Length", []).append(binaryLen)
        tmp_TestItem_site.setdefault("DUTIndex", []).append(self.dutIndex)
        tmp_TestItem_summ.setdefault("DUTIndex", []).append(self.dutIndex)
                    
            
    def onPRR(self, **kargs):
        recType = kargs.get("recType", None)
        binaryLen = kargs.get("dataLen", 0)
        rawData = kargs.get("rawData", b'')
        
        RecordParser.endian = self.endian
        valueDict = RecordParser.parse_raw(recType, binaryLen, rawData)
                
        SITE_NUM = valueDict["SITE_NUM"]
        HARD_BIN = valueDict["HARD_BIN"]
        SOFT_BIN = valueDict["SOFT_BIN"]
        PART_FLG = valueDict["PART_FLG"]
        NUM_TEST = valueDict["NUM_TEST"]
        TEST_T = valueDict["TEST_T"]
        PART_ID = valueDict["PART_ID"]
        
        
        tmpHSite = self.hbinSUM.setdefault(SITE_NUM, {})
        tmpHSumm = self.hbinSUM.setdefault(-1, {})
        tmpSSite = self.sbinSUM.setdefault(SITE_NUM, {})
        tmpSSumm = self.sbinSUM.setdefault(-1, {})
        tmpDUT = self.dutDict.setdefault(self.dutIndex, {})
        
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
        tmpDUT["SITE_NUM"] = SITE_NUM
        
        if PART_FLG & 0b00011000 == 0:
            tmpDUT["PART_FLG"] = "Pass"
            self.dutPassed += 1
            # we can determine the type of hard/soft bin based on the part_flag
            # it is helpful if the std is incomplete and lack of HBR/SBR
            # if key is existed, do not update repeatedly
            if not HARD_BIN in self.hbinDict: self.hbinDict[HARD_BIN] = [str(HARD_BIN), "P"]
            if not SOFT_BIN in self.sbinDict: self.sbinDict[SOFT_BIN] = [str(SOFT_BIN), "P"]
            
        elif PART_FLG & 0b00010000 == 0:
            tmpDUT["PART_FLG"] = "Failed"
            self.dutFailed += 1
            if not HARD_BIN in self.hbinDict: self.hbinDict[HARD_BIN] = [str(HARD_BIN), "F"]
            if not SOFT_BIN in self.sbinDict: self.sbinDict[SOFT_BIN] = [str(SOFT_BIN), "F"]
                    
        else:
            # no pass/fail info
            tmpDUT["PART_FLG"] = ""
            if not HARD_BIN in self.hbinDict: self.hbinDict[HARD_BIN] = [str(HARD_BIN), "U"]
            if not SOFT_BIN in self.sbinDict: self.sbinDict[SOFT_BIN] = [str(SOFT_BIN), "U"]
            
        
    def onHBR(self, **kargs):
        recType = kargs.get("recType", None)
        binaryLen = kargs.get("dataLen", 0)
        rawData = kargs.get("rawData", b'')
        
        RecordParser.endian = self.endian
        valueDict = RecordParser.parse_raw(recType, binaryLen, rawData)
                
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
       
        
    def onSBR(self, **kargs):
        recType = kargs.get("recType", None)
        binaryLen = kargs.get("dataLen", 0)
        rawData = kargs.get("rawData", b'')
        
        RecordParser.endian = self.endian
        valueDict = RecordParser.parse_raw(recType, binaryLen, rawData)        
        
        # SITE_NUM = valueDict["SITE_NUM"]
        SBIN_NUM = valueDict["SBIN_NUM"]
        SBIN_PF = valueDict["SBIN_PF"]
        SBIN_NAM = "Missing Name" if valueDict["SBIN_NAM"] == None else valueDict["SBIN_NAM"]
        
        if not SBIN_NUM in self.sbinDict:
            self.sbinDict[SBIN_NUM] = [SBIN_NAM, SBIN_PF]
        else:
            self.sbinDict[SBIN_NUM][0] = SBIN_NAM
            if SBIN_PF in ["P", "F"]: self.sbinDict[SBIN_NUM][1] = SBIN_PF


    def onWIR(self, **kargs):
        # placeholder
        pass
    
    
    def onWRR(self, **kargs):
        # placeholder
        pass
    
    
    def getTestName(self, recType, rawData):
        """Read Test Name Efficiently by skipping unrelated bytes"""
        if recType == V4.ptr:
            slen, = self.cplStruct[self.endian+formatMap["U1"]].unpack(rawData[12:13])  # 4+1+1+1+1+4 = 12
            tname_binary, = self.cplStruct[str(slen)+"s"].unpack(rawData[13 : 13+slen])
            return tname_binary.decode("ascii")

        elif recType == V4.mpr:
            if len(rawData) >= 13:  # 4+1+1+1+1+2+2 = 12, +1 to ensure slen isn't omitted
                RTN_cnt, RSLT_cnt, = self.cplStruct.setdefault("U2U2", struct.Struct(self.endian + formatMap["U2"]+formatMap["U2"])).unpack(rawData[8:12])
                tname_offset = 12 + RTN_cnt*1 + RSLT_cnt*4
                slen, = self.cplStruct[self.endian+formatMap["U1"]].unpack(rawData[tname_offset : tname_offset+1])
                tname_binary, = self.cplStruct[str(slen)+"s"].unpack(rawData[tname_offset+1 : tname_offset+1+slen])
                return tname_binary.decode("ascii")
            else:
                return ""
        
        elif recType == V4.ftr:
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
                return ""
        
        else:
            return ""
 
 
    
class stdfDataRetriever:
    
    def __init__(self, fileHandle, QSignal=None, flag=None):
        self.summarizer = stdfSummarizer(fileHandle, QSignal, flag=flag)
        P = stdIO(inp=fileHandle, flag=flag)
        P.addSink(self.summarizer)
        P.parse()
            
            
    def __call__(self):
        return self.summarizer