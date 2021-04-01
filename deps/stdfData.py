#
# stdfData.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: February 25th 2021
# -----
# Last Modified: Wed Mar 03 2021
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



class stdfData:
    """
    This class is used to store the parsed stdf data
    """
    def __init__(self):
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
        self.dutDict = {}   # key: dutIndex, value: {HEAD_NUM, SITE_NUM, PART_FLG, NUM_TEST, TEST_T, PART_ID, SOFT_BIN, HARD_BIN}, note: for incomplete stdf, KeyError could be raised as the PRR might be missing
        
        self.waferInfo = {} # key: center_x, center_y, diameter, size_unit
        self.waferDict = {} # key: waferIndex, value: {WAFER_ID, dutIndexList, coordList}
        
        self.globalTestFlag = {}    # key: test number, value: fail count, if fail count is invalid, test number is not the key.
        