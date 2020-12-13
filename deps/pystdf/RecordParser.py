#
# RecordParser.py - STDF Viewer
# Created based on IO.py from PySTDF
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: July 10th 2020
# -----
# Last Modified: Sun Dec 13 2020
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



import struct
import re

from deps.pystdf.Types import *
from deps.pystdf import V4


# pre-compile struct format, key: endian+fmt, value: struct object
structFMT = dict([(endian+cfmt, struct.Struct(endian+cfmt)) for endian in ["=", "<", ">"] for cfmt in packFormatMap.values()])
# pre-compile format of Cn, length of Cn ≤ 255
structFMT.update( dict([(str(i)+"s", struct.Struct(str(i)+"s")) for i in range(256)]) )
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


"""*** Functions group of parse_raw() ***"""
def appendFieldParser(fn, action):
    """Append a field parsing function to a record parsing function.
    This is used to build record parsing functions based on the record type specification."""
    def newRecordParser(*args):
        # get the current parserFunction list
        fields = fn(*args)
        try:
            # created a nested function callbacks
            # when call the final function, the fields is propogated with 
            # the result of action().
            fields.append(action(*args))
        except EndOfRecordException: pass
        return fields
    # output a list
    return newRecordParser


def createRecordParser(recType):
    fn = lambda rawInfo, fields: fields
    for stdfType in recType.fieldStdfTypes:
        # fieldStdfTypes is defined in StdfRecordMeta class, are strictly-ordered stdf types list in a record
        # ["CI", "U1", ...]
        fn = appendFieldParser(fn, getFieldParser(stdfType))
    return fn


def getFieldParser(fieldType):
    if (fieldType.startswith("k")):
        # "kCn" -> "k", "Cn"
        fieldIndex, arrayFmt = re.match('k(\d+)([A-Z][a-z0-9]+)', fieldType).groups()
        return lambda rawInfo, fields: readArray(rawInfo, fields[int(fieldIndex)], arrayFmt)
    else:
        parseFn = unpackMap[fieldType]
        return lambda rawInfo, fields: parseFn(rawInfo, fieldType)  


def readField(rawInfo, stdfFmt):
    return readAndUnpack(rawInfo, packFormatMap[stdfFmt])
 
         
def readAndUnpack(rawInfo, fmt):
    # get the length of value format, e.g. fmt="I", size=4
    size = struct.calcsize(fmt)
    if (size > rawInfo.len):
        # if the value size exceeds the remaining length of the current record, raise error
        # this exception is handled in appendFieldParser()
        raise EndOfRecordException()
    
    buf = rawInfo.raw[:size]
    # update the remaining length of the record
    rawInfo.len -= len(buf)
    rawInfo.raw = rawInfo.raw[size:]
    val,=structFMT[RecordParser.endian + fmt].unpack(buf)
    
    if isinstance(val, bytes):
        return val.decode("ascii")
    else:
        return val


def readCn(rawInfo):
    if rawInfo.len == 0: raise EndOfRecordException()
    
    slen = readField(rawInfo, "U1")
    if slen > rawInfo.len: raise EndOfRecordException()
    if slen == 0: return ""
    
    buf = rawInfo.raw[:slen]
    rawInfo.len -= len(buf)
    rawInfo.raw = rawInfo.raw[slen:]

    val,=structFMT[str(slen) + "s"].unpack(buf)
    return val.decode("ascii")


def readBn(rawInfo):
    blen = readField(rawInfo, "U1")
    bn = []
    for i in range(0, blen):
        bn.append(readField(rawInfo, "B1"))
    return bn


def readDn(rawInfo):
    dbitlen = readField(rawInfo, "U2")
    dlen = dbitlen / 8
    if dbitlen % 8 > 0:
        dlen+=1
    dn = []
    for i in range(0, int(dlen)):
        dn.append(readField(rawInfo, "B1"))
    return dn


def readVn(rawInfo):
    vlen = readField(rawInfo, "U2")
    vn = []
    for i in range(0, vlen):
        fldtype = readField(rawInfo, "B1")
        if fldtype in vnMap:
            vn.append(vnMap[fldtype](rawInfo))
    return vn


def readArray(rawInfo, indexValue, stdfFmt):
    if (stdfFmt == 'N1'):
        readArray(rawInfo, indexValue/2+indexValue%2, 'U1')
        return
    arr = []
    for i in range(int(indexValue)):
        arr.append(unpackMap[stdfFmt](rawInfo, stdfFmt))
    return arr


vnMap = {
    0: lambda rawInfo: rawInfo.shift(1),
    1: lambda rawInfo: readField(rawInfo, "U1"),
    2: lambda rawInfo: readField(rawInfo, "U2"),
    3: lambda rawInfo: readField(rawInfo, "U4"),
    4: lambda rawInfo: readField(rawInfo, "I1"),
    5: lambda rawInfo: readField(rawInfo, "I2"),
    6: lambda rawInfo: readField(rawInfo, "I4"),
    7: lambda rawInfo: readField(rawInfo, "R4"),
    8: lambda rawInfo: readField(rawInfo, "R8"),
    10: lambda rawInfo: readCn(rawInfo),
    11: lambda rawInfo: readBn(rawInfo),
    12: lambda rawInfo: readDn(rawInfo),
    13: lambda rawInfo: readField(rawInfo, "U1")}

unpackMap = {
    "C1": readField,
    "B1": readField,
    "U1": readField,
    "U2": readField,
    "U4": readField,
    "U8": readField,
    "I1": readField,
    "I2": readField,
    "I4": readField,
    "I8": readField,
    "R4": readField,
    "R8": readField,
    "Cn": lambda rawInfo, fmt: readCn(rawInfo),
    "Bn": lambda rawInfo, fmt: readBn(rawInfo),
    "Dn": lambda rawInfo, fmt: readDn(rawInfo),
    "Vn": lambda rawInfo, fmt: readVn(rawInfo)}      

recordParsers = dict([( (recType.typ, recType.sub), createRecordParser(recType) ) for recType in V4.records ])  # parser functions dicts for recTypes

"""*** End Group ***"""


class RawData:
    def __init__(self, length, rawByte):
        self.len = length
        self.raw = rawByte
        
    def shift(self, n):
        if n <= self.len and n > 0:
            self.len -= n
            skip_raw = self.raw[:n]
            self.raw = self.raw[n:]
            return skip_raw
        else:
            return b''


class RecordParser:
    # default endian, should be changed before parse
    endian = "="
    # Parser cache
    cache = {}
    
    @staticmethod
    def parse_raw(recType, length, rawByte):
        rawInfo = RawData(length, rawByte)  # mutable object contains info of binary data
        recParser = recordParsers[(recType.typ, recType.sub)]  # get parser function of the record type
        valueList = recParser(rawInfo, [])  # get a list of data in the current record
        
        if len(valueList) < len(recType.columnNames):
            valueList += [None] * (len(recType.columnNames) - len(valueList)) # append None for the data that are not presented in the file
        
        valueDict = dict(zip(recType.fieldNames, valueList))
        return valueDict
    
    @staticmethod
    def parse_rawList(recType, offset_list, length_list, file_handle, **kargs):
        # the offsets belong to a single test item, all fields are the same except the test value
        testDict = {}
        for offset, length in zip(offset_list, length_list):
            file_handle.seek(offset, 0)
            rawByte = file_handle.read(length)
            try:
                valueDict = RecordParser.cache[(offset, length)]
            except KeyError:
                valueDict = RecordParser.parse_raw(recType, length, rawByte)
                RecordParser.cache[(offset, length)] = valueDict    # cache value dict for speed

            # bit7-6: 00 pass; 10 fail; x1 none;
            Pass = True if valueDict["TEST_FLG"] & 0b11000000 == 0 else (False if valueDict["TEST_FLG"] & 0b01000000 == 0 else None)
            testDict["StatList"] = testDict.setdefault("StatList", []) + [Pass]
            
            if "failCheck" in kargs and kargs["failCheck"] and (Pass == False):
                # only StatList is interested in failCheck mode, return immediately if a Fail is found to improve speed
                return testDict
            
            # common field for all test records
            if "TestName" not in testDict: testDict["TestName"] = valueDict["TEST_TXT"]
            if "TestNum" not in testDict: testDict["TestNum"] = valueDict["TEST_NUM"]
            
            # set default LL/HL/Unit for FTR since there's no such field
            # update the following field only once for PTR & MPR
            if "LL" not in testDict:
                if recType == V4.ftr:
                    testDict["LL"] = None
                else:
                    # bit 6 set = No Low Limit for this test 
                    testDict["LL"] = valueDict["LO_LIMIT"] * 10 ** valueDict["RES_SCAL"] if valueDict["OPT_FLAG"] & 0b01000000 == 0 else None
                    
            if "HL" not in testDict:
                if recType == V4.ftr:
                    testDict["HL"] = None
                else:
                    # bit 7 set = No High Limit for this test 
                    testDict["HL"] = valueDict["HI_LIMIT"] * 10 ** valueDict["RES_SCAL"] if valueDict["OPT_FLAG"] & 0b10000000 == 0 else None
                    
            if "Unit" not in testDict:
                if recType == V4.ftr:
                    testDict["Unit"] = ""
                else:
                    testDict["Unit"] = unit_prefix.get(valueDict["RES_SCAL"], "") + valueDict["UNITS"]
            
            if recType == V4.ptr:
                tmpResult = valueDict["RESULT"] * 10 ** valueDict["RES_SCAL"]
                # testDict.setdefault("DataList", []).append(tmpResult)     # list is immutable in python
                testDict["DataList"] = testDict.setdefault("DataList", []) + [tmpResult]
                
            elif recType == V4.ftr:
                testDict["DataList"] = testDict.setdefault("DataList", []) + [valueDict["TEST_FLG"]]

            elif recType == V4.mpr:
                # for mpr, datalist is 2d, column for different pins
                testDict["DataList"] = testDict.setdefault("DataList", []) + [valueDict["RTN_RSLT"] * 10 ** valueDict["RES_SCAL"]]
                
        return testDict



