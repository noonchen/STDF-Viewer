#
# __init__.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: April 25th 2021
# -----
# Last Modified: Mon Dec 20 2021
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



import numpy as np
try:
    from . import _cystdf
except ImportError as e:
    e.msg = "cystdf module should be built before running STDF-Viewer"
    raise

__all__ = ["stdfDataRetriever", "stdfRecordAnalyzer", "stdf_PFTR_Parser", "stdf_MPR_Parser", "setByteSwap"]

class stdfDataRetriever(_cystdf.stdfDataRetriever):
    pass

def stdfRecordAnalyzer(filepath:str, QSignal:object=None, QSignalPgs:object=None, stopFlag:object=None) -> str:
    return _cystdf.analyzeSTDF(filepath, QSignal, QSignalPgs, stopFlag)

def stdf_PFTR_Parser(recHeader:int, offsetArray:np.ndarray, lengthArray:np.ndarray, file_handle) -> dict:
    '''For PTR & FTR only, keys: {dataList, flagList}'''
    return _cystdf.parsePFTR_rawList(recHeader, offsetArray, lengthArray, file_handle)

def stdf_MPR_Parser(recHeader:int, pinCount:int, rsltCount:int, offsetArray:np.ndarray, lengthArray:np.ndarray, file_handle) -> dict:
    '''For MPR only, keys: {dataList, statesList, flagList}'''
    return _cystdf.parseMPR_rawList(recHeader, pinCount, rsltCount, offsetArray, lengthArray, file_handle)

def setByteSwap(swapOn:bool):
    _cystdf.setByteSwap(swapOn)