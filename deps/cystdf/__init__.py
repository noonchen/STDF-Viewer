#
# __init__.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: April 25th 2021
# -----
# Last Modified: Sun Jun 13 2021
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



from . import _cystdf
import numpy as np

__all__ = ["stdfDataRetriever", "stdfRecordAnalyzer", "stdfParser", "setByteSwap"]

class stdfDataRetriever(_cystdf.stdfDataRetriever):
    pass

def stdfRecordAnalyzer(filepath:str) -> str:
    return _cystdf.analyzeSTDF(filepath)

def stdfParser(recHeader:int, offsetArray:np.ndarray, lengthArray:np.ndarray, file_handle) -> dict:
    return _cystdf.parse_rawList(recHeader, offsetArray, lengthArray, file_handle)

def setByteSwap(swapOn:bool):
    _cystdf.setByteSwap(swapOn)