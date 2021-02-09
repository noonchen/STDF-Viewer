#
# IO_Offset_forViewer.py - STDF Viewer 
# Created based on IO.py from PySTDF
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: July 10th 2020
# -----
# Last Modified: Tue Feb 09 2021
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



import sys
from time import time
import struct
from deps.pystdf.Types import *
from deps.pystdf import V4


class stdIO:
    
    def __init__(self, recTypes=V4.records, inp=sys.stdin, flag=None, q=None):
        # DataSource.__init__(self)
        self.eof = 1
        # records' instances
        self.recTypes = set(recTypes)
        # python stardard input
        self.inp = inp
        self.flag = flag    # used for controlling parse actions
        self.q = q  # queue ref
        
        # {(0, 10):FAR, (50, 30):DTR, ....}
        self.recordMap = dict(
            [ ( (recType.typ, recType.sub), recType )
                for recType in recTypes ])
        
        
    def readHeader(self):
        try:
            hdr = RecordHeader()
            buffer = self.inp.read(4)
            hdr.len, hdr.typ, hdr.sub = self.StructHeader.unpack(buffer)
            return hdr
        except Exception:
            self.eof = 1
            raise EofException()


    def get_records_offset(self):

        self.eof = 0
        records_to_parse = dict([ ((recType.typ, recType.sub), recType) for recType in [V4.mir, 
                                                                                        V4.wcr, V4.wir, V4.wrr, 
                                                                                        V4.ptr, V4.ftr, V4.mpr, 
                                                                                        V4.pir, V4.prr, 
                                                                                        V4.hbr, V4.sbr] ])
        dataCluster = []    # pack 6000 items before putting into queue
        try:
            while self.eof==0:
                if self.flag: 
                    if self.flag.stop: return   # quit loop if flag set to stop
                    
                header = self.readHeader()
                if (header.typ, header.sub) in records_to_parse:    # only parse given record types
                    recType = self.recordMap[(header.typ, header.sub)]    # get record type instance
                    offset = self.inp.tell()    # position of front end of record data (without header)
                    rawData = self.inp.read(header.len)
                    
                    if len(rawData) != header.len:
                        # if the file is damaged or what, end parse
                        self.eof = 1
                        raise EofException()
                    else:
                        if self.q:
                            if len(dataCluster) < 6000:
                                dataCluster.append({"recType": (recType.typ, recType.sub), "offset": offset, "length": header.len, "rawData": rawData})
                            else:
                                self.q.put(dataCluster)
                                # don't forget to store the data from current iteration
                                dataCluster = [{"recType": (recType.typ, recType.sub), "offset": offset, "length": header.len, "rawData": rawData}]
                else:
                    self.inp.seek(header.len, 1) # skip other records
        except EofException: 
            if self.q:
                self.q.put(dataCluster)


    def detect_endian(self):
        self.inp.seek(0, 0)
        self.eof = 0
        
        # set a default endian for reading header for the 1st time
        self.endian = "="
        # precompile struct for header
        self.StructHeader = struct.Struct(self.endian + packFormatMap["U2"]+packFormatMap["U1"]+packFormatMap["U1"])
        header = self.readHeader()
        if header.typ != 0 and header.sub != 10:
            raise InitialSequenceException("It's not a valid std file")
        
        buffer = self.inp.read(1)
        cpuType, = struct.unpack(packFormatMap["U1"], buffer)
        if cpuType == 2:
            self.endian = '<'    # LSB
        else:
            self.endian = '>'    # MSB
        # restore the file offset
        self.inp.seek(0)
        # re-precompile struct for header
        self.StructHeader = struct.Struct(self.endian + packFormatMap["U2"]+packFormatMap["U1"]+packFormatMap["U1"])
        
        
    def send_endian(self):
        if self.q:
            self.q.put([self.endian])


    def parse(self):
        try:
            # start = time()
            self.detect_endian()
            self.send_endian()     # send endian before start
            self.get_records_offset()
            # end = time()
            # print("parse time %f"%(end-start))
        except Exception:
            raise
        finally:
            if self.q:
                self.q.put([])


if __name__ == "__main__":
    fd = open("", "rb")
    stdIO(inp=fd).parse()