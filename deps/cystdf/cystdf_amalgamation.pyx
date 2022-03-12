# distutils: language = c
# cython: language_level=3
# cython: annotation_typing = True
#
# cystdf_amalgamation.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: July 12th 2020
# -----
# Last Modified: Fri Mar 11 2022
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



import logging
import platform
import numpy as np
import threading as th
import zipfile

cimport numpy as cnp
cimport cython
from cython.view cimport array as cyarray
from cython.parallel import prange

from includes.pthread cimport *
from hashmap_src.hashmap_libc cimport *
from sqlite3_src.sqlite3_libc cimport *
from stdf4_src.stdf4_libc cimport *
from tsqueue_src.tsqueue_libc cimport *
from testidmap_src.testidmap_libc cimport *

from libc.time cimport time_t, strftime, tm, gmtime, localtime
from libc.stdint cimport *
from libc.stddef cimport wchar_t
from libc.math cimport NAN, isinf
from libc.float cimport FLT_MAX, FLT_MIN
from libc.string cimport memcpy, memset, strcpy, strrchr, strcmp, strcat, strlen
from posix.stdio cimport fseeko, ftello
from posix.unistd cimport usleep
from libc.stdio cimport sprintf, printf, snprintf
from libc.stdlib cimport malloc, free, calloc, realloc

# including a str to wchar_t func that missed from cython
cdef extern from "Python.h":
    wchar_t* PyUnicode_AsWideCharString(object, Py_ssize_t *) except NULL

logger = logging.getLogger("STDF Viewer")


# check host endianness
cdef unsigned int _a  = 256
cdef char *_b = <char*>&_a
cdef bint hostIsLittleEndian = (_b[1] == 1)
# cdef bint needByteSwap = False


##############################
# *** typedefs for stdIO *** #
##############################
# operations
ctypedef enum OPT:
    SET_ENDIAN  = 0
    PARSE       = 1
    FINISH      = 2

# record header
ctypedef struct header:
    uint16_t    rec_len
    uint8_t     rec_typ
    uint8_t     rec_sub

# minimun unit represents a record
ctypedef struct recData:
    uint16_t        recHeader
    uint64_t        offset
    unsigned char*  rawData
    uint16_t        binaryLen

# queue element
ctypedef struct dataCluster:
    STDERR      error
    OPT         operation
    recData*    pData

# arg struct
ctypedef struct parse_arg:
    void*           filename
    tsQueue*        q
    bint*           p_needByteSwap
    bint*           stopFlag

# *** end of typedefs for stdIO *** #


###########################
# *** funcs for stdIO *** #
###########################
cdef STDERR check_endian(STDF* std, bint* p_needByteSwap) nogil:
    cdef header hData
    if std.fops.stdf_read(std, &hData, sizeof(hData)) == STD_OK:
        if hData.rec_typ == 0 and hData.rec_sub == 10:
            if hData.rec_len == 2:
                p_needByteSwap[0] = False
            elif hData.rec_len == 512:
                p_needByteSwap[0] = True
            else:
                # not a stdf
                return INVAILD_STDF
            return STD_OK
        else:
            # not a stdf
            return INVAILD_STDF
    else:
        # read file failed
        return OS_FAIL


cdef void get_offset(STDF* std, tsQueue* q, bint* p_needByteSwap, bint* stopFlag) nogil:
    cdef header hData
    cdef uint16_t recHeader
    cdef uint64_t offset = 0
    cdef dataCluster *ele

    while True:
        # check stop signal from main thread
        if stopFlag != NULL:
            if stopFlag[0]:
                ele = <dataCluster*>message_queue_message_alloc_blocking(q)
                ele.error = TERMINATE
                ele.operation = FINISH
                message_queue_write(q, ele)
                break
        
        if std.fops.stdf_read(std, &hData, sizeof(hData)) == STD_OK:
            recHeader = MAKE_REC(hData.rec_typ, hData.rec_sub)
            offset += sizeof(hData)  # manually advanced by sizeof header
            # swap if byte order is different
            if p_needByteSwap[0]:
                SwapBytes(&hData.rec_len, sizeof(uint16_t))

            if (recHeader == REC_MIR or recHeader == REC_WCR or recHeader == REC_WIR or recHeader == REC_WRR or
                recHeader == REC_PTR or recHeader == REC_FTR or recHeader == REC_MPR or recHeader == REC_TSR or
                recHeader == REC_PIR or recHeader == REC_PRR or recHeader == REC_HBR or recHeader == REC_SBR or 
                recHeader == REC_PCR or recHeader == REC_PMR or recHeader == REC_PGR or recHeader == REC_PLR or
                recHeader == REC_MRR or recHeader == REC_DTR or recHeader == REC_GDR or recHeader == REC_EPS or
                recHeader == REC_BPS or recHeader == REC_SDR or recHeader == REC_RDR or recHeader == REC_ATR or
                recHeader == REC_FAR):
                # get binaryLen and read rawData
                # alloc memory
                ele = <dataCluster*>message_queue_message_alloc_blocking(q)
                ele.pData = <recData*>malloc(sizeof(recData))
                if ele.pData != NULL:
                    ele.pData.rawData = <unsigned char*>malloc(hData.rec_len)
                    if ele.pData.rawData != NULL:
                        # read rawData
                        if std.fops.stdf_read(std, ele.pData.rawData, hData.rec_len) == STD_OK:
                            # send to queue
                            # ele.pData.rawData[hData.rec_len] = b'\0'  # no need for add NULL at the end, length is record
                            ele.pData.recHeader = recHeader
                            ele.pData.offset = offset
                            ele.pData.binaryLen = hData.rec_len
                            ele.operation = PARSE
                            message_queue_write(q, ele)
                            offset += hData.rec_len  # manually advanced by length of raw data
                        else:
                            # end of file
                            free(ele.pData.rawData)
                            free(ele.pData)
                            ele.pData = NULL
                            ele.error = STD_EOF
                            ele.operation = FINISH
                            message_queue_write(q, ele)
                            break
                    else:
                        free(ele.pData.rawData)
                        free(ele.pData)
                        ele.pData   = NULL
                        ele.error   = NO_MEMORY
                        ele.operation     = FINISH
                        message_queue_write(q, ele)
                        break
                else:
                    free(ele.pData)
                    ele.pData   = NULL
                    ele.error   = NO_MEMORY
                    ele.operation     = FINISH
                    message_queue_write(q, ele)
                    break
                
            else:
                # # skip current record
                # std.fops.stdf_skip(std, hData.rec_len)
                # offset += hData.rec_len  # manually advanced by length of raw data

                # since we read all record types now, in this case means unexpected record types
                ele = <dataCluster*>message_queue_message_alloc_blocking(q)
                ele.error = INVAILD_STDF
                ele.operation = FINISH
                message_queue_write(q, ele)
                break
        else:
            # end of file
            ele = <dataCluster*>message_queue_message_alloc_blocking(q)
            ele.error = STD_EOF
            ele.operation = FINISH
            message_queue_write(q, ele)
            break


cdef void* parse(void* input_args) nogil:
    cdef parse_arg* args = <parse_arg*>input_args
    if (args == NULL or args.filename == NULL or args.q == NULL or
        args.p_needByteSwap == NULL or args.stopFlag == NULL):
        return NULL

    cdef STDF *std = NULL
    cdef tsQueue *q = args.q
    cdef bint* p_needByteSwap = args.p_needByteSwap
    cdef bint* stopFlag = args.stopFlag
    cdef STDERR status, status_reopen
    cdef dataCluster *ele = <dataCluster*>message_queue_message_alloc_blocking(q)

    status = stdf_open(&std, args.filename)

    if status != STD_OK:
        ele.error   = OS_FAIL
        ele.operation     = FINISH
        message_queue_write(q, ele)
    else:
        status = check_endian(std, p_needByteSwap)
        status_reopen = stdf_reopen(std)
        if status == STD_OK and status_reopen == STD_OK:
            # set endian and start parse
            ele.operation     = SET_ENDIAN
            message_queue_write(q, ele)
            # start parsing file
            get_offset(std, q, p_needByteSwap, stopFlag)
        else:
            ele.error   = status
            ele.operation     = FINISH
            message_queue_write(q, ele)
    stdf_close(std)
    return NULL

# *** end of funcs for stdIO *** #


cdef uint64_t getFileSize(str filepath) except *:
    cdef uint64_t fsize = 0

    pyfh = open(filepath, "rb")

    if filepath.endswith(".gz"):
        # for gzip, read last 4 bytes as filesize
        pyfh.seek(-4, 2)
        fsize = <uint64_t>(int.from_bytes(pyfh.read(4), "little"))
    elif filepath.endswith(".zip"):
        with zipfile.ZipFile(filepath, "r") as zipObj:
            fsize = <uint64_t>(zipObj.filelist[0].file_size)
    else:
        # bzip file size is not known before uncompressing, return compressed file size instead
        fsize = <uint64_t>(pyfh.seek(0, 2))
    pyfh.close()
    return fsize


#########################
# *** STDF Analyzer *** #
#########################
def analyzeSTDF(str filepath, QSignal=None, QSignalPgs=None, flag=None):
    cdef wchar_t* filepath_wc
    cdef bytes filepath_byte
    cdef char* filepath_c
    cdef void* _filepath
    cdef uint64_t fileSize
    cdef bint isWin = platform.system() == "Windows"
    cdef bint isValidSignal = (QSignal is not None)
    cdef bint isValidProgressSignal = (QSignalPgs is not None)
    cdef int previousProgress = 0, currentProgress

    fileSize = getFileSize(filepath)
    if fileSize == 0:
        raise OSError("Zero byte file detected")

    if isWin:
        filepath_wc = PyUnicode_AsWideCharString(filepath, NULL)
        _filepath = <void*>filepath_wc
    else:
        filepath_byte = filepath.encode('utf-8')
        filepath_c = filepath_byte      # for parser in pthread
        _filepath = <void*>filepath_c
    
    cdef str tmpRes = ""
    cdef str resultLog = ""

    rec_name = {REC_FAR:"FAR",
                REC_ATR:"ATR",
                REC_MIR:"MIR",
                REC_MRR:"MRR",
                REC_PCR:"PCR",
                REC_HBR:"HBR",
                REC_SBR:"SBR",
                REC_PMR:"PMR",
                REC_PGR:"PGR",
                REC_PLR:"PLR",
                REC_RDR:"RDR",
                REC_SDR:"SDR",
                REC_WIR:"WIR",
                REC_WRR:"WRR",
                REC_WCR:"WCR",
                REC_PIR:"PIR",
                REC_PRR:"PRR",
                REC_TSR:"TSR",
                REC_PTR:"PTR",
                REC_MPR:"MPR",
                REC_FTR:"FTR",
                REC_BPS:"BPS",
                REC_EPS:"EPS",
                REC_GDR:"GDR",
                REC_DTR:"DTR",}

    cdef bint stopFlag = False
    cdef tsQueue    q
    cdef pthread_t  th
    cdef dataCluster* item
    cdef uint32_t totalRecord = 0
    cdef void* pRec = NULL
    cdef uint8_t HEAD_NUM, SITE_NUM
    cdef uint16_t preRecHeader = 0
    cdef int recCnt = 0, dutCnt = 0, waferCnt = 0

    # init queue
    message_queue_init(&q, sizeof(dataCluster), 1024*8)
    # args for parser
    cdef parse_arg args
    args.filename = _filepath
    args.q = &q
    args.p_needByteSwap = &needByteSwap
    args.stopFlag = &stopFlag

    pthread_create(&th, NULL, parse, <void*>&args)

    while True:
        if flag is not None and flag.stop:
            (&stopFlag)[0] = <bint>flag.stop
            break
        
        item = <dataCluster*>message_queue_read(&q)
        if item == NULL:
            break

        else:
            if item.operation == SET_ENDIAN:
                if needByteSwap:
                    tmpRes = "Byte Order: big endian"
                else:
                    tmpRes = "Byte Order: little endian"
                if isValidSignal:
                    QSignal.emit(tmpRes)
                else:
                    resultLog += tmpRes + "\n"
                    
            elif item.operation == PARSE:
                if item.pData:
                    if (item.pData.recHeader == REC_PIR or item.pData.recHeader == REC_WIR or
                        item.pData.recHeader == REC_PRR or item.pData.recHeader == REC_WRR):
                        if recCnt != 0 and preRecHeader != 0:
                            # print previous result
                            tmpRes = "%s"%rec_name.get(preRecHeader, "") + " × %d"%recCnt if recCnt else ""
                            if isValidSignal:
                                QSignal.emit(tmpRes)
                            else:
                                resultLog += tmpRes + "\n"
                            
                        # write PXR and WXR right now, since we need to print head number of site number
                        parse_record(&pRec, item.pData.recHeader, item.pData.rawData, item.pData.binaryLen)
                        if item.pData.recHeader == REC_PIR:
                            dutCnt += 1
                            HEAD_NUM = (<PIR*>pRec).HEAD_NUM
                            SITE_NUM = (<PIR*>pRec).SITE_NUM
                            tmpRes = "[%d] %s"%(dutCnt, rec_name.get(item.pData.recHeader, "")) + f" (HEAD: {HEAD_NUM}, SITE: {SITE_NUM})"
                            if isValidSignal:
                                QSignal.emit(tmpRes)
                            else:
                                resultLog += tmpRes + "\n"
                            if isValidProgressSignal:
                                currentProgress = (100 * item.pData.offset) // fileSize
                                if currentProgress > previousProgress:
                                    QSignalPgs.emit(currentProgress)
                            
                        elif item.pData.recHeader == REC_WIR:
                            waferCnt += 1
                            HEAD_NUM = (<WIR*>pRec).HEAD_NUM
                            tmpRes = "%s"%rec_name.get(item.pData.recHeader, "") + f" (HEAD: {HEAD_NUM})"
                            if isValidSignal:
                                QSignal.emit(tmpRes)
                            else:
                                resultLog += tmpRes + "\n"
                            
                        elif item.pData.recHeader == REC_PRR:
                            HEAD_NUM    = (<PRR*>pRec).HEAD_NUM
                            SITE_NUM    = (<PRR*>pRec).SITE_NUM
                            tmpRes = "%s"%rec_name.get(item.pData.recHeader, "") + f" (HEAD: {HEAD_NUM}, SITE: {SITE_NUM})"
                            if isValidSignal:
                                QSignal.emit(tmpRes)
                            else:
                                resultLog += tmpRes + "\n"
                            
                        else:
                            HEAD_NUM = (<WRR*>pRec).HEAD_NUM
                            tmpRes = "%s"%rec_name.get(item.pData.recHeader, "") + f" (HEAD: {HEAD_NUM})"
                            if isValidSignal:
                                QSignal.emit(tmpRes)
                            else:
                                resultLog += tmpRes + "\n"
                            
                        free_record(item.pData.recHeader, pRec)
                        # reset preheader to 0, in order to print every PXR WXR
                        preRecHeader = 0
                        recCnt = 0
                        
                    else:
                        if preRecHeader != item.pData.recHeader:
                            # print previous cnt
                            if preRecHeader != 0:
                                tmpRes = "%s"%rec_name.get(preRecHeader, "") + " × %d"%recCnt if recCnt else ""
                                if isValidSignal:
                                    QSignal.emit(tmpRes)
                                else:
                                    resultLog += tmpRes + "\n"
                                
                            # update new
                            preRecHeader = item.pData.recHeader
                            recCnt = 1
                        else:
                            recCnt += 1

                    totalRecord += 1
                    free(item.pData.rawData)
                free(item.pData)
            else:
                if recCnt != 0 and preRecHeader != 0:
                    # print last record
                    tmpRes = "%s"%rec_name.get(preRecHeader, "") + " × %d"%recCnt if recCnt else ""
                    if isValidSignal:
                        QSignal.emit(tmpRes)
                    else:
                        resultLog += tmpRes + "\n"
                    if isValidProgressSignal:
                        QSignalPgs.emit(100)
                        

                # check error
                if item.error:
                    if item.error == INVAILD_STDF:
                        tmpRes = "INVAILD_STDF\n"
                    elif item.error == WRONG_VERSION:
                        tmpRes = "WRONG_VERSION\n"
                    elif item.error == OS_FAIL:
                        tmpRes = "OS_FAIL\n"
                    elif item.error == NO_MEMORY:
                        tmpRes = "NO_MEMORY\n"
                    elif item.error == STD_EOF:
                        tmpRes = "STD_EOF\n"
                    elif item.error == TERMINATE:
                        tmpRes = "TERMINATE\n"
                    else:
                        tmpRes = "Unknwon error\n"

                    if isValidSignal:
                        QSignal.emit(tmpRes)
                    else:
                        resultLog += tmpRes
                break
            

        message_queue_message_free(&q, item)
    
    pthread_join(th, NULL)
    pthread_kill(th, 0)
    message_queue_destroy(&q)
    tmpRes = ""
    tmpRes += "\nTotal wafers: %d"%waferCnt
    tmpRes += "\nTotal duts/dies: %d"%dutCnt
    tmpRes += "\nTotal records: %d\n"%totalRecord
    tmpRes += "Analysis Finished"
    if isValidSignal:
        QSignal.emit(tmpRes)
    else:
        resultLog += tmpRes
    
    return resultLog

# *** end of Record Analyzer *** #


##################################
# *** funcs of Record Parser *** #
##################################
NPINT = int
NPFLOAT = float
ctypedef cnp.int_t NPINT_t
ctypedef cnp.float_t NPFLOAT_t
cdef bint* p_needByteSwap = &needByteSwap
cdef bint py_needByteSwap = False


def setByteSwap(bint ON_OFF):
    # switch byte swap on/off from python
    global py_needByteSwap
    py_needByteSwap = ON_OFF


@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
cdef int32_t max(int32_t[:] inputArray) nogil:
    cdef int i
    cdef Py_ssize_t size = inputArray.shape[0]
    cdef int32_t result = inputArray[0]

    for i in range(size):
        if inputArray[i] > result:
            result = inputArray[i]

    return result


@cython.boundscheck(False)
@cython.wraparound(False)
def parsePFTR_rawList(uint16_t recHeader, int64_t[:] offsetArray, int32_t[:] lengthArray, object file_handle):
    if recHeader != REC_PTR and recHeader != REC_FTR:
        raise TypeError("This function is for parsering PTR & FTR only")

    cdef int i, infType
    cdef void* pRec
    cdef Py_ssize_t cnt = offsetArray.shape[0]
    cdef int32_t maxL = max(lengthArray)

    # data containers & views for nogil operation
    cdef cnp.ndarray[NPFLOAT_t, ndim=1] dataList = np.full(cnt, NAN, dtype=NPFLOAT)
    cdef cnp.ndarray[NPINT_t, ndim=1] flagList = np.zeros(cnt, dtype=NPINT)
    cdef NPFLOAT_t [:] dataList_view = dataList
    cdef NPINT_t   [:] flagList_view = flagList

    if maxL < 0:
        # no valid result
        return {"dataList":dataList, "flagList":flagList}

    # memoryView to store raw bytes from file
    cdef const unsigned char[:,:] rawDataView = cyarray(shape = (cnt, maxL),
                                                        itemsize = sizeof(unsigned char),
                                                        format="B")
    # c-contiguous view for accepting bytes from read()
    cdef const unsigned char[::1] tmpData = cyarray(shape = (maxL,),
                                                    itemsize = sizeof(unsigned char),
                                                    format="B")

    # output dict
    cdef dict testDict = {}
    
    # read raw data
    for i in range(cnt):
        if offsetArray[i] < 0 or lengthArray[i] < 0:
            # rawDataView[i, :] = b'\0'    # represent invalid rawData
            lengthArray[i] = -1

        else:
            file_handle.seek(offsetArray[i])
            # we need to append extra bytes at the end of tmpData if maxL > lengthArray[i]
            # otherwise the size mismatch error would be raised by the later copy process
            tmpData = file_handle.read(lengthArray[i]) + b'\0' * (maxL - lengthArray[i])
            rawDataView[i, :] = tmpData

    # set C extern variable to the value from python side
    global p_needByteSwap, py_needByteSwap
    p_needByteSwap[0] = py_needByteSwap
    # parse raw bytes
    for i in prange(cnt, nogil=True):
        if lengthArray[i] < 0:
            dataList_view[i] = NAN
            flagList_view[i] = -1
        else:
            parse_record(&pRec, recHeader, &rawDataView[i,0], lengthArray[i])

            if recHeader == REC_PTR:
                flagList_view[i] = (<PTR*>pRec).TEST_FLG
                infType = isinf((<PTR*>pRec).RESULT)
                if infType > 0:
                    # replace +inf with max float
                    dataList_view[i] = FLT_MAX
                elif infType < 0:
                    # replace -inf with min float
                    dataList_view[i] = FLT_MIN
                else:
                    dataList_view[i] = (<PTR*>pRec).RESULT
            elif recHeader == REC_FTR:
                flagList_view[i] = (<FTR*>pRec).TEST_FLG
                dataList_view[i] = <NPFLOAT_t>flagList_view[i]
            
            free_record(recHeader, pRec)
            pRec = NULL

    return {"dataList":dataList, "flagList":flagList}


@cython.boundscheck(False)
@cython.wraparound(False)
def parseMPR_rawList(uint16_t recHeader, uint16_t pinCount, uint16_t rsltCount, int64_t[:] offsetArray, int32_t[:] lengthArray, object file_handle):
    if recHeader != REC_MPR:
        raise TypeError("This function is for parsering MPR only")

    cdef int i, j, infType
    cdef void* pRec
    cdef Py_ssize_t cnt = offsetArray.shape[0]
    cdef int32_t maxL = max(lengthArray)

    # data containers & views for nogil operation
    # Pin as row, dut as column
    cdef cnp.ndarray[NPINT_t, ndim=2] statesList = np.full([pinCount, cnt], 16, dtype=NPINT)  # use 0x10 as the invalid states
    cdef cnp.ndarray[NPFLOAT_t, ndim=2] dataList = np.full([rsltCount, cnt], NAN, dtype=NPFLOAT)
    cdef cnp.ndarray[NPINT_t, ndim=1] flagList = np.full(cnt, -1, dtype=NPINT)      # init flag with invalid -1 value
    cdef NPINT_t   [:,:] statesList_view = statesList
    cdef NPFLOAT_t [:,:] dataList_view = dataList
    cdef NPINT_t   [:] flagList_view = flagList

    if maxL < 0:
        # no valid result
        return {"dataList":dataList, "statesList":statesList, "flagList":flagList}

    # memoryView to store raw bytes from file
    cdef const unsigned char[:,:] rawDataView = cyarray(shape = (cnt, maxL),
                                                        itemsize = sizeof(unsigned char),
                                                        format="B")
    # c-contiguous view for accepting bytes from read()
    cdef const unsigned char[::1] tmpData = cyarray(shape = (maxL,),
                                                    itemsize = sizeof(unsigned char),
                                                    format="B")

    # output dict
    cdef dict testDict = {}
    
    # read raw data
    for i in range(cnt):
        if offsetArray[i] < 0 or lengthArray[i] < 0:
            # rawDataView[i, :] = b'\0'    # represent invalid rawData
            lengthArray[i] = -1

        else:
            file_handle.seek(offsetArray[i])
            # we need to append extra bytes at the end of tmpData if maxL > lengthArray[i]
            # otherwise the size mismatch error would be raised by the later copy process
            tmpData = file_handle.read(lengthArray[i]) + b'\0' * (maxL - lengthArray[i])
            rawDataView[i, :] = tmpData

    # set C extern variable to the value from python side
    global p_needByteSwap, py_needByteSwap
    p_needByteSwap[0] = py_needByteSwap
    # parse raw bytes
    for i in prange(cnt, nogil=True):
        if lengthArray[i] < 0:
            for j in range(rsltCount):
                dataList_view[j, i] = NAN
            flagList_view[i] = -1
        else:
            parse_record(&pRec, recHeader, &rawDataView[i,0], lengthArray[i])

            flagList_view[i] = (<MPR*>pRec).TEST_FLG
            if (<MPR*>pRec).RTN_STAT != NULL:
                for j in range(pinCount):
                    # write MPR states into ith column of statesList
                    statesList_view[j, i] = ((<MPR*>pRec).RTN_STAT)[j]
            
            if (<MPR*>pRec).RTN_RSLT != NULL:
                for j in range(rsltCount):
                    # write MPR data into ith column of dataList
                    infType = isinf(((<MPR*>pRec).RTN_RSLT)[j])
                    if infType > 0:
                        # replace +inf with max float
                        dataList_view[j, i] = FLT_MAX
                    elif infType < 0:
                        # replace -inf with min float
                        dataList_view[j, i] = FLT_MIN
                    else:
                        dataList_view[j, i] = ((<MPR*>pRec).RTN_RSLT)[j]
            
            free_record(recHeader, pRec)
            pRec = NULL

    return {"dataList":dataList, "statesList":statesList, "flagList":flagList}

# *** end of Record Parser *** #


################################################
# ** Wrappers of standard sqlite3 functions ** #
################################################
# close sqlite3 database
cdef void csqlite3_close(sqlite3 *db) except *:
    cdef int exitcode
    cdef const char *errMsg

    exitcode = sqlite3_close(db)
    if exitcode != SQLITE_OK:
        errMsg = sqlite3_errmsg(db)
        raise Exception(errMsg.decode('UTF-8'))


# open sqlite3 database
cdef void csqlite3_open(str dbPath, sqlite3 **db_ptr) except *:
    cdef bytes dbPath_utf8 = dbPath.encode('UTF-8')
    cdef char *fpath = dbPath_utf8
    cdef const char *errMsg
    cdef int exitcode

    exitcode = sqlite3_open(fpath, db_ptr)
    if exitcode != SQLITE_OK:
        errMsg = sqlite3_errmsg(db_ptr[0])
        raise Exception(errMsg.decode('UTF-8'))


# execute sqlite3 query
cdef void csqlite3_exec(sqlite3 *db, const char *sql) except *:
    cdef int exitcode
    cdef char *errMsg

    exitcode = sqlite3_exec(db, sql, NULL, NULL, &errMsg)
    if exitcode != SQLITE_OK:
        raise Exception(errMsg.decode('UTF-8'))

# prepare sqlite3 statement
cdef void csqlite3_prepare_v2(sqlite3 *db, const char *Sql, sqlite3_stmt **ppStmt) except *:
    cdef int exitcode
    cdef const char *errMsg

    exitcode = sqlite3_prepare_v2(db, Sql, -1, ppStmt, NULL)
    if exitcode != SQLITE_OK:
        errMsg = sqlite3_errmsg(db)
        raise Exception(errMsg.decode('UTF-8'))


# *** The following sqlite3 funcs will be called massive times, 
# *** use error code instead of python exception
# execute sqlite3 statement and reset/clear
cdef int csqlite3_step(sqlite3_stmt *stmt) nogil:
    cdef int exitcode
    # cdef const char *errMsg

    exitcode = sqlite3_step(stmt)

    if exitcode != SQLITE_DONE:
        return exitcode
    else:
        # clear bindings and reset stmt for next step if success
        sqlite3_reset(stmt)
        sqlite3_clear_bindings(stmt)
        return 0


cdef int csqlite3_finalize(sqlite3_stmt *stmt) nogil:
    cdef int exitcode
    # cdef const char *errMsg

    exitcode = sqlite3_finalize(stmt)
    if exitcode != SQLITE_OK:
        return exitcode
    else:
        return 0

# ** End of Wrappers ** #


#################################################
# ** Callback function for iterating hashmap ** #
#################################################
cdef int writeFailCount(void* sql_stmt, uint32_t TEST_NUM, uint32_t count) nogil:
    cdef sqlite3_stmt* updateFailCount_stmt = <sqlite3_stmt*>sql_stmt
    cdef int err = 0
    sqlite3_bind_int(updateFailCount_stmt, 1, count)
    sqlite3_bind_int(updateFailCount_stmt, 2, TEST_NUM)
    err = csqlite3_step(updateFailCount_stmt)
    return err

# ** End of Callback ** #


cdef class stdfSummarizer:
    cdef:
        object QSignal, flag, pb_thread
        uint64_t offset, fileSize
        uint32_t dutIndex, waferIndex
        int programSectionsDepth
        bint reading, isLittleEndian, stopFlag, isWindows, isBeforePRR
        dict pinDict
        bytes filepath_bt
        void* pRec
        char* endian
        char* TEST_TXT
        char** programSections
        char detailErrorMsg[512]
        const char* filepath_c
        const wchar_t*  filepath_wc
        sqlite3 *db_ptr
        sqlite3_stmt *insertFileInfo_stmt
        sqlite3_stmt *insertDut_stmt
        sqlite3_stmt *updateDut_stmt
        sqlite3_stmt *insertTR_stmt
        # sqlite3_stmt *updateTR_stmt
        sqlite3_stmt *insertTestInfo_stmt
        sqlite3_stmt *insertHBIN_stmt
        # sqlite3_stmt *updateHBIN_stmt
        sqlite3_stmt *insertSBIN_stmt
        # sqlite3_stmt *updateSBIN_stmt
        sqlite3_stmt *insertWafer_stmt
        sqlite3_stmt *insertDutCount_stmt
        sqlite3_stmt *insertPinMap_stmt
        sqlite3_stmt *updateFrom_GRP_stmt
        sqlite3_stmt *insertGRP_NAM_stmt
        sqlite3_stmt *insertPinInfo_stmt
        sqlite3_stmt *insertTestPin_stmt
        sqlite3_stmt *insertDynamicLimit_stmt
        sqlite3_stmt *insertDatalog_stmt
        testIDMap   *idMap
        map_t   defaultLLimit
        map_t   defaultHLimit
        map_t   TestFailCount
        map_t   head_site_dutIndex
        map_t   head_waferIndex


    def __cinit__(self):
        self.programSections        = NULL
        self.db_ptr                 = NULL
        self.insertFileInfo_stmt    = NULL
        self.insertDut_stmt         = NULL
        self.updateDut_stmt         = NULL
        self.insertTR_stmt          = NULL
        # self.updateTR_stmt          = NULL
        self.insertTestInfo_stmt    = NULL
        self.insertHBIN_stmt        = NULL
        # self.updateHBIN_stmt        = NULL
        self.insertSBIN_stmt        = NULL
        # self.updateSBIN_stmt        = NULL
        self.insertDutCount_stmt    = NULL
        self.insertWafer_stmt       = NULL
        self.insertPinMap_stmt      = NULL
        self.updateFrom_GRP_stmt    = NULL
        self.insertGRP_NAM_stmt     = NULL
        self.insertPinInfo_stmt     = NULL
        self.insertTestPin_stmt     = NULL
        self.insertDynamicLimit_stmt= NULL
        self.insertDatalog_stmt     = NULL
        self.pRec                   = NULL
        self.idMap                  = NULL
        self.defaultLLimit          = NULL
        self.defaultHLimit          = NULL        
        self.TestFailCount          = NULL
        self.head_site_dutIndex     = NULL
        self.head_waferIndex        = NULL


    def __init__(self, QSignal=None, flag=None, filepath=None, dbPath="test.db"):
        # init database in C
        cdef:
            const char* createTableSql = '''DROP TABLE IF EXISTS File_Info;
                                        DROP TABLE IF EXISTS Dut_Info;
                                        DROP TABLE IF EXISTS Dut_Counts;
                                        DROP TABLE IF EXISTS Test_Info;
                                        DROP TABLE IF EXISTS Test_Offsets;
                                        DROP TABLE IF EXISTS Bin_Info;
                                        DROP TABLE IF EXISTS Wafer_Info;
                                        DROP TABLE IF EXISTS Pin_Map;
                                        DROP TABLE IF EXISTS Pin_Info;
                                        DROP TABLE IF EXISTS TestPin_Map;
                                        DROP TABLE IF EXISTS Dynamic_Limits;
                                        DROP TABLE IF EXISTS Datalog;
                                        VACUUM;
                                        
                                        CREATE TABLE IF NOT EXISTS File_Info (
                                                                Field TEXT, 
                                                                Value TEXT);
                                                                
                                        CREATE TABLE IF NOT EXISTS Wafer_Info (
                                                                HEAD_NUM INTEGER, 
                                                                WaferIndex INTEGER PRIMARY KEY,
                                                                PART_CNT INTEGER,
                                                                RTST_CNT INTEGER,
                                                                ABRT_CNT INTEGER,
                                                                GOOD_CNT INTEGER,
                                                                FUNC_CNT INTEGER,
                                                                WAFER_ID TEXT,
                                                                FABWF_ID TEXT,
                                                                FRAME_ID TEXT,
                                                                MASK_ID TEXT,
                                                                USR_DESC TEXT,
                                                                EXC_DESC TEXT);
                                                                
                                        CREATE TABLE IF NOT EXISTS Dut_Info (
                                                                HEAD_NUM INTEGER, 
                                                                SITE_NUM INTEGER, 
                                                                DUTIndex INTEGER PRIMARY KEY,
                                                                TestCount INTEGER,
                                                                TestTime INTEGER,
                                                                PartID TEXT,
                                                                HBIN INTEGER,
                                                                SBIN INTEGER,
                                                                Flag INTEGER,
                                                                WaferIndex INTEGER,
                                                                XCOORD INTEGER,
                                                                YCOORD INTEGER) WITHOUT ROWID;
                                                                
                                        CREATE TABLE IF NOT EXISTS Dut_Counts (
                                                                HEAD_NUM INTEGER, 
                                                                SITE_NUM INTEGER, 
                                                                PART_CNT INTEGER,
                                                                RTST_CNT INTEGER,
                                                                ABRT_CNT INTEGER,
                                                                GOOD_CNT INTEGER,
                                                                FUNC_CNT INTEGER);

                                        CREATE TABLE IF NOT EXISTS Test_Info (
                                                                TEST_ID INTEGER,
                                                                TEST_NUM INTEGER,
                                                                recHeader INTEGER,
                                                                TEST_NAME TEXT,
                                                                RES_SCAL INTEGER,
                                                                LLimit REAL,
                                                                HLimit REAL,
                                                                Unit TEXT,
                                                                OPT_FLAG INTEGER,
                                                                FailCount INTEGER,
                                                                RTN_ICNT INTEGER,
                                                                RSLT_PGM_CNT INTEGER,
                                                                LSpec REAL,
                                                                HSpec REAL,
                                                                VECT_NAM TEXT,
                                                                SEQ_NAME TEXT,
                                                                PRIMARY KEY (TEST_NUM, TEST_NAME)) WITHOUT ROWID;
                                                                
                                        CREATE TABLE IF NOT EXISTS Test_Offsets (
                                                                DUTIndex INTEGER,
                                                                TEST_ID INTEGER, 
                                                                Offset INTEGER,
                                                                BinaryLen INTEGER,
                                                                PRIMARY KEY (DUTIndex, TEST_ID)) WITHOUT ROWID;
                                                                
                                        CREATE TABLE IF NOT EXISTS Bin_Info (
                                                                BIN_TYPE TEXT,
                                                                BIN_NUM INTEGER, 
                                                                BIN_NAME TEXT,
                                                                BIN_PF TEXT,
                                                                PRIMARY KEY (BIN_TYPE, BIN_NUM));

                                        CREATE TABLE IF NOT EXISTS Pin_Map (
                                                                HEAD_NUM INTEGER, 
                                                                SITE_NUM INTEGER, 
                                                                PMR_INDX INTEGER,
                                                                CHAN_TYP INTEGER,
                                                                CHAN_NAM TEXT,
                                                                PHY_NAM TEXT,
                                                                LOG_NAM TEXT,
                                                                From_GRP INTEGER);

                                        CREATE TABLE IF NOT EXISTS Pin_Info (
                                                                P_PG_INDX INTEGER PRIMARY KEY, 
                                                                GRP_NAM TEXT, 
                                                                GRP_MODE INTEGER,
                                                                GRP_RADX INTEGER,
                                                                PGM_CHAR TEXT,
                                                                PGM_CHAL TEXT,
                                                                RTN_CHAR TEXT,
                                                                RTN_CHAL TEXT);

                                        CREATE TABLE IF NOT EXISTS TestPin_Map (
                                                                TEST_ID INTEGER, 
                                                                PMR_INDX INTEGER,
                                                                PIN_TYPE TEXT,
                                                                PRIMARY KEY (TEST_ID, PMR_INDX, PIN_TYPE));
                                        
                                        CREATE TABLE IF NOT EXISTS Dynamic_Limits (
                                                                DUTIndex INTEGER,
                                                                TEST_ID INTEGER, 
                                                                LLimit REAL,
                                                                HLimit REAL,
                                                                PRIMARY KEY (DUTIndex, TEST_ID));
                                        
                                        CREATE TABLE IF NOT EXISTS Datalog (
                                                                RecordType TEXT,
                                                                Value TEXT, 
                                                                AfterDUTIndex INTEGER,
                                                                isBeforePRR INTEGER);
                                                                
                                        DROP INDEX IF EXISTS dutKey;
                                        PRAGMA synchronous = OFF;
                                        PRAGMA journal_mode = WAL;
                                        
                                        BEGIN;'''
            const char* insertFileInfo = '''INSERT INTO File_Info VALUES (?,?)'''
            const char* insertDut = '''INSERT INTO Dut_Info (HEAD_NUM, SITE_NUM, DUTIndex) VALUES (?,?,?);'''
            const char* updateDut = '''UPDATE Dut_Info SET TestCount=:TestCount, TestTime=:TestTime, PartID=:PartID, 
                                                            HBIN=:HBIN_NUM, SBIN=:SBIN_NUM, Flag=:Flag, 
                                                            WaferIndex=:WaferIndex, XCOORD=:XCOORD, YCOORD=:YCOORD 
                                                            WHERE DUTIndex=:DUTIndex; COMMIT; BEGIN;'''     # commit and start another transaction in PRR
            const char* insertTR = '''INSERT OR REPLACE INTO Test_Offsets VALUES (:DUTIndex, :TEST_ID, :Offset ,:BinaryLen);'''

            # I am not adding IGNORE below, since tracking seen test_nums can skip a huge amount of codes
            const char* insertTestInfo = '''INSERT INTO Test_Info VALUES (:TEST_ID, :TEST_NUM, :recHeader, :TEST_NAME, 
                                                                        :RES_SCAL, :LLimit, :HLimit, 
                                                                        :Unit, :OPT_FLAG, :FailCount, :RTN_ICNT, :RSLT_PGM_CNT, :LSpec, :HSpec, :VECT_NAM, :SEQ_NAME);'''
            const char* insertHBIN = '''INSERT OR REPLACE INTO Bin_Info VALUES ("H", :HBIN_NUM, :HBIN_NAME, :PF);'''
            # const char* updateHBIN = '''UPDATE Bin_Info SET BIN_NAME=:HBIN_NAME, BIN_PF=:BIN_PF WHERE BIN_TYPE="H" AND BIN_NUM=:HBIN_NUM'''
            const char* insertSBIN = '''INSERT OR REPLACE INTO Bin_Info VALUES ("S", :SBIN_NUM, :SBIN_NAME, :PF);'''
            # const char* updateSBIN = '''UPDATE Bin_Info SET BIN_NAME=:SBIN_NAME, BIN_PF=:BIN_PF WHERE BIN_TYPE="S" AND BIN_NUM=:SBIN_NUM'''
            const char* insertDutCount = '''INSERT INTO Dut_Counts VALUES (:HEAD_NUM, :SITE_NUM, :PART_CNT, :RTST_CNT, 
                                                                        :ABRT_CNT, :GOOD_CNT, :FUNC_CNT);'''
            const char* insertWafer = '''INSERT OR REPLACE INTO Wafer_Info VALUES (:HEAD_NUM, :WaferIndex, :PART_CNT, :RTST_CNT, :ABRT_CNT, 
                                                                                :GOOD_CNT, :FUNC_CNT, :WAFER_ID, :FABWF_ID, :FRAME_ID, 
                                                                                :MASK_ID, :USR_DESC, :EXC_DESC);'''
            const char* insertPinMap = '''INSERT INTO Pin_Map VALUES (:HEAD_NUM, :SITE_NUM, :PMR_INDX, :CHAN_TYP, 
                                                                        :CHAN_NAM, :PHY_NAM, :LOG_NAM, :From_GRP);'''
            const char* updateFrom_GRP = '''UPDATE Pin_Map SET From_GRP=:From_GRP WHERE PMR_INDX=:PMR_INDX;'''
            # create a row with GRP_NAME in Pin_Info if PGR exists, in some rare cases, PMR shows after PGR, ignore it.
            const char* insertGRP_NAM = '''INSERT OR IGNORE INTO Pin_Info (P_PG_INDX, GRP_NAM) VALUES (:P_PG_INDX, :GRP_NAM);'''
            # insert rows in Pin_Info and keep GRP_NAM
            const char* insertPinInfo = '''INSERT OR REPLACE INTO Pin_Info VALUES (:P_PG_INDX, (SELECT GRP_NAM FROM Pin_Info WHERE P_PG_INDX=:P_PG_INDX), 
                                                                        :GRP_MODE, :GRP_RADX, 
                                                                        :PGM_CHAR, :PGM_CHAL, :RTN_CHAR, :RTN_CHAL);'''
            const char* insertTestPin = '''INSERT OR IGNORE INTO TestPin_Map VALUES (:TEST_ID, :PMR_INDX, :PIN_TYPE);'''
            const char* insertDynamicLimit = '''INSERT OR REPLACE INTO Dynamic_Limits VALUES (:DUTIndex, :TEST_ID, :LLimit ,:HLimit);'''
            const char* insertDatalog = '''INSERT INTO Datalog VALUES (:RecordType, :Value, :AfterDUTIndex ,:isBeforePRR);'''

        # init sqlite3 database api
        try:
            csqlite3_open(dbPath, &self.db_ptr)
            csqlite3_exec(self.db_ptr, createTableSql)
            csqlite3_prepare_v2(self.db_ptr, insertFileInfo, &self.insertFileInfo_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertDut, &self.insertDut_stmt)
            csqlite3_prepare_v2(self.db_ptr, updateDut, &self.updateDut_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertTR, &self.insertTR_stmt)
            # csqlite3_prepare_v2(self.db_ptr, updateTR, &self.updateTR_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertTestInfo, &self.insertTestInfo_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertHBIN, &self.insertHBIN_stmt)
            # csqlite3_prepare_v2(self.db_ptr, updateHBIN, &self.updateHBIN_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertSBIN, &self.insertSBIN_stmt)
            # csqlite3_prepare_v2(self.db_ptr, updateSBIN, &self.updateSBIN_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertDutCount, &self.insertDutCount_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertWafer, &self.insertWafer_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertPinMap, &self.insertPinMap_stmt)
            csqlite3_prepare_v2(self.db_ptr, updateFrom_GRP, &self.updateFrom_GRP_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertGRP_NAM, &self.insertGRP_NAM_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertPinInfo, &self.insertPinInfo_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertTestPin, &self.insertTestPin_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertDynamicLimit, &self.insertDynamicLimit_stmt)
            csqlite3_prepare_v2(self.db_ptr, insertDatalog, &self.insertDatalog_stmt)
        except Exception:
            try:
                csqlite3_close(self.db_ptr)
            except Exception as e:
                logger.error("Error when close database: " + repr(e))
            raise

        # get file size in Bytes
        if not isinstance(filepath, str):
            raise TypeError("File path is not type <str>")
        # get wchar_t* string on Win and char* string on mac & linux
        self.isWindows = platform.system() == "Windows"
        if self.isWindows:
            self.filepath_wc = PyUnicode_AsWideCharString(filepath, NULL)
        else:
            self.filepath_bt = filepath.encode("utf-8")
            self.filepath_c = self.filepath_bt      # for parser in pthread
        self.fileSize = getFileSize(filepath)
        if self.fileSize == 0:
            raise OSError("File cannot be opened")
        # init error msg to empty
        memset(self.detailErrorMsg, 0, 512)
        # python signal
        self.flag = flag
        self.QSignal = QSignal
        # current position
        self.offset = 0
        self.reading = True
        # no need to update progressbar if signal is None
        if self.QSignal: 
            self.QSignal.emit(0)
            self.pb_thread = th.Thread(target=self.sendProgress)
            self.pb_thread.start()
        # track depth of BPS-EPS block
        self.programSectionsDepth = 0
        # default endianness & byteswap
        self.endian = "Little endian"
        self.isLittleEndian = True
        self.stopFlag = False
        # used for recording TR, TestNum, HBR, SBR that have been seen
        self.idMap                  = createTestIDMap()
        self.defaultLLimit          = hashmap_new(1024)   # key: testID, value: Low limit in first PTR
        self.defaultHLimit          = hashmap_new(1024)   # key: testID, value: high limit in first PTR
        self.TestFailCount          = hashmap_new(1024)   # key: testID, value: fail count
        self.head_site_dutIndex     = hashmap_new(8)      # key: head numb << 8 | site num, value: dutIndex, a tmp dict used to retrieve dut index by head/site info, required by multi head stdf files
        self.head_waferIndex        = hashmap_new(8)      # similar to head_site_dutIndex, but one head per wafer
        
        if self.idMap == NULL or self.defaultLLimit == NULL or self.defaultHLimit == NULL or self.TestFailCount == NULL or self.head_site_dutIndex == NULL or self.head_waferIndex == NULL:
            destoryTestIDMap(self.idMap)
            hashmap_free(self.defaultLLimit)
            hashmap_free(self.defaultHLimit)
            hashmap_free(self.TestFailCount)
            hashmap_free(self.head_site_dutIndex)
            hashmap_free(self.head_waferIndex)            
            raise MemoryError("No enough memory to start parsing")
        # for counting
        self.dutIndex = 0  # get 1 as index on first +1 action, used for counting total DUT number
        self.waferIndex = 0 # used for counting total wafer number
        self.isBeforePRR = True # used for determining location of DTR & GDR
        self.pinDict = {}   # key: Pin index, value: Pin name
        
        self.analyze()  # start
    
    
    def sendProgress(self):
        cdef int percent
        while self.reading:
            with nogil:
                percent = (10000 * self.offset) // self.fileSize     # times additional 100 to save 2 decimal
                usleep(100000)      # wait for 100 ms
            
            self.QSignal.emit(percent)        
            if self.flag.stop:
                (&self.stopFlag)[0] = <bint>self.flag.stop
                break
                
        
        
    cdef void set_endian(self) nogil:
        global hostIsLittleEndian
        if needByteSwap:
            if hostIsLittleEndian:
                self.endian = "Big endian"   # big endian
            else:
                self.endian = "Little endian"   # little endian
        else:
            # same as host
            if hostIsLittleEndian:
                self.endian = "Little endian"
            else:
                self.endian = "Big endian"
        
        
    def analyze(self):
        # global needByteSwap
        cdef int errorCode = 0
        cdef tsQueue    parseQ
        cdef pthread_t  pth
        cdef dataCluster* item
        cdef parse_arg args

        # init c queue
        if message_queue_init(&parseQ, sizeof(dataCluster), 2**22) != 0:
            raise MemoryError("Unable to start parsing queue")
        # args for parser
        args.filename = <void*>self.filepath_wc if self.isWindows else <void*>self.filepath_c
        args.q = &parseQ
        args.p_needByteSwap = &needByteSwap
        args.stopFlag = &self.stopFlag
        # start parsing thread
        if pthread_create(&pth, NULL, parse, <void*>&args) != 0:
            raise RuntimeError("Failed to start parsing thread")
        
        try:
            with nogil:
                while True:
                    item = <dataCluster*>message_queue_read(&parseQ)
                    if item == NULL:
                        break

                    else:
                        if item.operation == SET_ENDIAN:
                            self.set_endian()

                        elif item.operation == PARSE:
                            if item.pData:
                                self.offset = item.pData.offset
                                errorCode = self.onRec(recHeader=item.pData.recHeader, \
                                                        binaryLen=item.pData.binaryLen, \
                                                        rawData=item.pData.rawData)
                                free(item.pData.rawData)
                            free(item.pData)
                            if errorCode: break
                        else:
                            # save error code if finished
                            if item.error:
                                errorCode = item.error
                            break

                    message_queue_message_free(&parseQ, item)

            if errorCode:
                raise Exception

        except Exception:
            if errorCode == INVAILD_STDF:
                raise Exception("The file is not a valid STDF")
            elif errorCode == WRONG_VERSION:
                raise NotImplementedError("Only STDF version 4 is supported")
            elif errorCode == OS_FAIL:
                raise OSError("Cannot open the file")
            elif errorCode == NO_MEMORY or errorCode == MAP_OMEM:
                raise MemoryError("Not enough memory to proceed" 
                                    + ": %s" % self.detailErrorMsg.decode() if self.detailErrorMsg[0] else "")
            elif errorCode == STD_EOF:
                pass    # ignore EOF
            elif errorCode == TERMINATE:
                raise InterruptedError("Parsing is terminated by user")
            elif errorCode == MAP_MISSING:
                raise KeyError("Wrong key to get data from C dictionary" 
                                + ": %s" % self.detailErrorMsg.decode() if self.detailErrorMsg[0] else "")
            else:
                # sqlite3 error
                raise Exception(f"SQlite3 Error: {sqlite3_errstr(errorCode)}")

        finally:
            # join progress bar thread if finished
            pthread_join(pth, NULL)
            pthread_kill(pth, 0)
            message_queue_destroy(&parseQ)
            self.after_complete()
        
        
    def after_complete(self):
        cdef int errorCode = 0

        self.reading = False
        # check if all BPSs are closed
        cdef int i
        if self.programSectionsDepth > 0:
            # if not all closed, clean it now
            for i in range(self.programSectionsDepth):
                free(self.programSections[i])
            free(self.programSections)
            self.programSections = NULL
            self.programSectionsDepth = 0
        # update failcount
        cdef const char* updateFailCount = '''UPDATE Test_Info SET FailCount=:count WHERE TEST_ID=:TEST_ID'''
        cdef sqlite3_stmt* updateFailCount_stmt
        csqlite3_prepare_v2(self.db_ptr, updateFailCount, &updateFailCount_stmt)

        errorCode = hashmap_iterate(self.TestFailCount, <PFany>writeFailCount, updateFailCount_stmt)
        if errorCode:
            # log error if occurred, but do not raise it, it's not that important
            if errorCode == MAP_MISSING:
                # empty TestFailCount map
                logger.warning("No test count information detect.")
            else:
                # sqlite error
                logger.warning(f"Sqlite error when saving test count data: {sqlite3_errstr(errorCode)}")

        csqlite3_finalize(updateFailCount_stmt)
        
        cdef char* createIndex_COMMIT = '''CREATE INDEX dutKey ON Dut_Info (
                                        HEAD_NUM	ASC,
                                        SITE_NUM	ASC);
                                        
                                        COMMIT;'''
        csqlite3_exec(self.db_ptr, createIndex_COMMIT)
        csqlite3_finalize(self.insertFileInfo_stmt)
        csqlite3_finalize(self.insertDut_stmt)
        csqlite3_finalize(self.updateDut_stmt)
        csqlite3_finalize(self.insertTR_stmt)
        # csqlite3_finalize(self.updateTR_stmt)
        csqlite3_finalize(self.insertTestInfo_stmt)
        csqlite3_finalize(self.insertHBIN_stmt)
        # csqlite3_finalize(self.updateHBIN_stmt)
        csqlite3_finalize(self.insertSBIN_stmt)
        # csqlite3_finalize(self.updateSBIN_stmt)
        csqlite3_finalize(self.insertDutCount_stmt)
        csqlite3_finalize(self.insertWafer_stmt)
        csqlite3_finalize(self.insertPinMap_stmt)
        csqlite3_finalize(self.updateFrom_GRP_stmt)
        csqlite3_finalize(self.insertGRP_NAM_stmt)
        csqlite3_finalize(self.insertPinInfo_stmt)
        csqlite3_finalize(self.insertTestPin_stmt)
        csqlite3_finalize(self.insertDynamicLimit_stmt)
        csqlite3_finalize(self.insertDatalog_stmt)
        csqlite3_close(self.db_ptr)
        # clean hashmap
        hashmap_free(self.defaultLLimit)
        hashmap_free(self.defaultHLimit)
        hashmap_free(self.TestFailCount)
        hashmap_free(self.head_site_dutIndex)
        hashmap_free(self.head_waferIndex)            
        # clean testidmap
        destoryTestIDMap(self.idMap)

        if self.QSignal: 
            self.pb_thread.join()
            # update once again when finished, ensure the progress bar hits 100%
            self.QSignal.emit(10000)
        
        
    cdef int onRec(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        # most frequent records on top to reduce check times
        # in Cython it will be replaced by switch case, which will be more efficient than py_dict/if..else
        cdef int err = 0
        if recHeader == 3850 or recHeader == 3855 or recHeader == 3860: # PTR 3850 # MPR 3855 # FTR 3860
            err = self.onTR(recHeader, binaryLen, rawData)
        elif recHeader == 1290: # PIR 1290
            err = self.onPIR(recHeader, binaryLen, rawData)
        elif recHeader == 1300: # PRR 1300
            err = self.onPRR(recHeader, binaryLen, rawData)
        elif recHeader == 522: # WIR 522
            err = self.onWIR(recHeader, binaryLen, rawData)
        elif recHeader == 532: # WRR 532
            err = self.onWRR(recHeader, binaryLen, rawData)
        elif recHeader == 2590: # TSR 2590
            err = self.onTSR(recHeader, binaryLen, rawData)
        elif recHeader == 296: # HBR 296
            err = self.onHBR(recHeader, binaryLen, rawData)
        elif recHeader == 306: # SBR 306
            err = self.onSBR(recHeader, binaryLen, rawData)
        elif recHeader == 316: # PMR 316
            err = self.onPMR(recHeader, binaryLen, rawData)
        elif recHeader == 318: # PGR 318
            err = self.onPGR(recHeader, binaryLen, rawData)
        elif recHeader == 319: # PLR 319
            err = self.onPLR(recHeader, binaryLen, rawData)
        elif recHeader == 266: # MIR 266
            err = self.onMIR(recHeader, binaryLen, rawData)
        elif recHeader == 542: # WCR 542
            err = self.onWCR(recHeader, binaryLen, rawData)
        elif recHeader == 286: # PCR 286
            err = self.onPCR(recHeader, binaryLen, rawData)
        elif recHeader == 276: # MRR 276
            err = self.onMRR(recHeader, binaryLen, rawData)
        elif recHeader == 12830: # DTR 12830
            err = self.onDTR(recHeader, binaryLen, rawData)
        elif recHeader == 12810: # GDR 12810
            err = self.onGDR(recHeader, binaryLen, rawData)
        elif recHeader == 5130: # BPS 5130
            err = self.onBPS(recHeader, binaryLen, rawData)
        elif recHeader == 5140: # EPS 5140
            err = self.onEPS(recHeader, binaryLen, rawData)
        elif recHeader == 10: # FAR 10
            err = self.onFAR(recHeader, binaryLen, rawData)
        elif recHeader == 20: # ATR 20
            err = self.onATR(recHeader, binaryLen, rawData)
        elif recHeader == 326: # RDR 326
            err = self.onRDR(recHeader, binaryLen, rawData)
        elif recHeader == 336: # SDR 336
            err = self.onSDR(recHeader, binaryLen, rawData)
        return err
            

    cdef int onFAR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        return 0

    cdef int onATR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0, l = 0
            time_t timeStamp
            tm*    tmPtr
            char   stringBuffer[256]
            char*  result
        
        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        # get time string
        timeStamp = <time_t>((<ATR*>self.pRec).MOD_TIM)
        tmPtr = localtime(&timeStamp)
        strftime(stringBuffer, 26, "%Y-%m-%d %H:%M:%S (UTC)", tmPtr)
        # get size of final string
        l = snprintf(NULL, 0, "Time: %s\nCMD: %s", stringBuffer, (<ATR*>self.pRec).CMD_LINE)
        result = <char*>malloc((l+1) * sizeof(char))
        # get final string
        snprintf(result, l+1, "Time: %s\nCMD: %s", stringBuffer, (<ATR*>self.pRec).CMD_LINE)

        sqlite3_bind_text(self.insertFileInfo_stmt, 1, "File Modification", -1, NULL)
        sqlite3_bind_text(self.insertFileInfo_stmt, 2, result, -1, NULL)
        err = csqlite3_step(self.insertFileInfo_stmt)

        free(result)
        free_record(recHeader, self.pRec)
        return err


    cdef int onMIR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef int err = 0
        cdef time_t timeStamp
        cdef tm*    tmPtr
        cdef char   stringBuffer[256]
        parse_record(&self.pRec, recHeader, rawData, binaryLen)

        # Endianess
        if not err:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "BYTE_ORD", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, self.endian, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # U4  SETUP_T
        if not err:
            timeStamp = <time_t>((<MIR*>self.pRec).SETUP_T)
            tmPtr = localtime(&timeStamp)
            strftime(stringBuffer, 26, "%Y-%m-%d %H:%M:%S (UTC)", tmPtr)
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "SETUP_T", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # U4  START_T
        if not err:
            timeStamp = <time_t>((<MIR*>self.pRec).START_T)
            tmPtr = localtime(&timeStamp)
            strftime(stringBuffer, 26, "%Y-%m-%d %H:%M:%S (UTC)", tmPtr)
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "START_T", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # U1  STAT_NUM
        if not err:
            sprintf(stringBuffer, "%d", (<MIR*>self.pRec).STAT_NUM)
            stringBuffer[1] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "STAT_NUM", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # C1  MODE_COD
        if not err and (<MIR*>self.pRec).MODE_COD != 0x20:    # hex of SPACE
            sprintf(stringBuffer, "%c", (<MIR*>self.pRec).MODE_COD)
            stringBuffer[1] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "MODE_COD", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # C1  RTST_COD
        if not err and (<MIR*>self.pRec).RTST_COD != 0x20:    # hex of SPACE
            sprintf(stringBuffer, "%c", (<MIR*>self.pRec).RTST_COD)
            stringBuffer[1] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "RTST_COD", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # C1  PROT_COD
        if not err and (<MIR*>self.pRec).PROT_COD != 0x20:    # hex of SPACE
            sprintf(stringBuffer, "%c", (<MIR*>self.pRec).PROT_COD)
            stringBuffer[1] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "PROT_COD", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # U2  BURN_TIM
        if not err and (<MIR*>self.pRec).BURN_TIM != 65535:
            sprintf(stringBuffer, "%d", (<MIR*>self.pRec).BURN_TIM)
            stringBuffer[1] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "BURN_TIM", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # C1  CMOD_COD
        if not err and (<MIR*>self.pRec).CMOD_COD != 0x20:    # hex of SPACE
            sprintf(stringBuffer, "%c", (<MIR*>self.pRec).CMOD_COD)
            stringBuffer[1] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "CMOD_COD", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  LOT_ID
        if not err and (<MIR*>self.pRec).LOT_ID != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "LOT_ID", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).LOT_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  PART_TYP
        if not err and (<MIR*>self.pRec).PART_TYP != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "PART_TYP", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).PART_TYP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  NODE_NAM
        if not err and (<MIR*>self.pRec).NODE_NAM != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "NODE_NAM", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).NODE_NAM, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  TSTR_TYP
        if not err and (<MIR*>self.pRec).TSTR_TYP != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "TSTR_TYP", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).TSTR_TYP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  JOB_NAM
        if not err and (<MIR*>self.pRec).JOB_NAM != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "JOB_NAM", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).JOB_NAM, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  JOB_REV
        if not err and (<MIR*>self.pRec).JOB_REV != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "JOB_REV", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).JOB_REV, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  SBLOT_ID
        if not err and (<MIR*>self.pRec).SBLOT_ID != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "SBLOT_ID", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).SBLOT_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  OPER_NAM
        if not err and (<MIR*>self.pRec).OPER_NAM != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "OPER_NAM", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).OPER_NAM, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  EXEC_TYP
        if not err and (<MIR*>self.pRec).EXEC_TYP != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "EXEC_TYP", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).EXEC_TYP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  EXEC_VER
        if not err and (<MIR*>self.pRec).EXEC_VER != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "EXEC_VER", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).EXEC_VER, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  TEST_COD
        if not err and (<MIR*>self.pRec).TEST_COD != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "TEST_COD", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).TEST_COD, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  TST_TEMP
        if not err and (<MIR*>self.pRec).TST_TEMP != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "TST_TEMP", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).TST_TEMP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  USER_TXT
        if not err and (<MIR*>self.pRec).USER_TXT != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "USER_TXT", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).USER_TXT, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  AUX_FILE
        if not err and (<MIR*>self.pRec).AUX_FILE != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "AUX_FILE", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).AUX_FILE, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  PKG_TYP
        if not err and (<MIR*>self.pRec).PKG_TYP != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "PKG_TYP", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).PKG_TYP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  FAMLY_ID
        if not err and (<MIR*>self.pRec).FAMLY_ID != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "FAMLY_ID", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).FAMLY_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  DATE_COD
        if not err and (<MIR*>self.pRec).DATE_COD != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "DATE_COD", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).DATE_COD, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  FACIL_ID
        if not err and (<MIR*>self.pRec).FACIL_ID != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "FACIL_ID", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).FACIL_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  FLOOR_ID
        if not err and (<MIR*>self.pRec).FLOOR_ID != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "FLOOR_ID", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).FLOOR_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  PROC_ID
        if not err and (<MIR*>self.pRec).PROC_ID != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "PROC_ID", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).PROC_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  OPER_FRQ
        if not err and (<MIR*>self.pRec).OPER_FRQ != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "OPER_FRQ", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).OPER_FRQ, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  SPEC_NAM
        if not err and (<MIR*>self.pRec).SPEC_NAM != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "SPEC_NAM", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).SPEC_NAM, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  SPEC_VER
        if not err and (<MIR*>self.pRec).SPEC_VER != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "SPEC_VER", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).SPEC_VER, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  FLOW_ID
        if not err and (<MIR*>self.pRec).FLOW_ID != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "FLOW_ID", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).FLOW_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  SETUP_ID
        if not err and (<MIR*>self.pRec).SETUP_ID != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "SETUP_ID", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).SETUP_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  DSGN_REV
        if not err and (<MIR*>self.pRec).DSGN_REV != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "DSGN_REV", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).DSGN_REV, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  ENG_ID
        if not err and (<MIR*>self.pRec).ENG_ID != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "ENG_ID", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).ENG_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  ROM_COD
        if not err and (<MIR*>self.pRec).ROM_COD != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "ROM_COD", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).ROM_COD, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  SERL_NUM
        if not err and (<MIR*>self.pRec).SERL_NUM != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "SERL_NUM", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).SERL_NUM, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  SUPR_NAM
        if not err and (<MIR*>self.pRec).SUPR_NAM != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "SUPR_NAM", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MIR*>self.pRec).SUPR_NAM, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)

        free_record(recHeader, self.pRec)
        return err
                
                
    cdef int onPMR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0
            int         HEAD_NUM, SITE_NUM, CHAN_TYP
            uint16_t    PMR_INDX
            char*       CHAN_NAM
            char*       PHY_NAM
            char*       LOG_NAM
        
        parse_record(&self.pRec, recHeader, rawData, binaryLen)

        HEAD_NUM = (<PMR*>self.pRec).HEAD_NUM
        SITE_NUM = (<PMR*>self.pRec).SITE_NUM
        PMR_INDX = (<PMR*>self.pRec).PMR_INDX
        CHAN_NAM = (<PMR*>self.pRec).CHAN_NAM
        CHAN_TYP = (<PMR*>self.pRec).CHAN_TYP
        PHY_NAM = (<PMR*>self.pRec).PHY_NAM
        LOG_NAM = (<PMR*>self.pRec).LOG_NAM
        
        sqlite3_bind_int(self.insertPinMap_stmt, 1, HEAD_NUM)
        sqlite3_bind_int(self.insertPinMap_stmt, 2, SITE_NUM)
        sqlite3_bind_int(self.insertPinMap_stmt, 3, PMR_INDX)
        sqlite3_bind_int(self.insertPinMap_stmt, 4, CHAN_TYP)
        if CHAN_NAM != NULL:
            sqlite3_bind_text(self.insertPinMap_stmt, 5, CHAN_NAM, -1, NULL)
        if PHY_NAM != NULL:
            sqlite3_bind_text(self.insertPinMap_stmt, 6, PHY_NAM, -1, NULL)
        if LOG_NAM != NULL:
            sqlite3_bind_text(self.insertPinMap_stmt, 7, LOG_NAM, -1, NULL)
        # From_GRP is intentionally unbinded
        err = csqlite3_step(self.insertPinMap_stmt)
        
        free_record(recHeader, self.pRec)
        return err


    cdef int onPGR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0, i = 0
            uint16_t    GRP_INDX, INDX_CNT, PMR_INDX
            char*       GRP_NAM
            uint16_t*   pPMR_INDX
        
        parse_record(&self.pRec, recHeader, rawData, binaryLen)

        GRP_INDX = (<PGR*>self.pRec).GRP_INDX
        GRP_NAM = (<PGR*>self.pRec).GRP_NAM
        INDX_CNT = (<PGR*>self.pRec).INDX_CNT
        pPMR_INDX = (<PGR*>self.pRec).PMR_INDX

        # create new data in Pin_Info
        if GRP_NAM != NULL:
            sqlite3_bind_int(self.insertGRP_NAM_stmt, 1, GRP_INDX)
            sqlite3_bind_text(self.insertGRP_NAM_stmt, 2, GRP_NAM, -1, NULL)
            err = csqlite3_step(self.insertGRP_NAM_stmt)
        
        # update From_GRP in Pin_Map
        for i in range(INDX_CNT):
            if not err:
                PMR_INDX = pPMR_INDX[i]   # get element [i] from array pPMR_INDX
                sqlite3_bind_int(self.updateFrom_GRP_stmt, 1, GRP_INDX)
                sqlite3_bind_int(self.updateFrom_GRP_stmt, 2, PMR_INDX)
                err = csqlite3_step(self.updateFrom_GRP_stmt)
        
        free_record(recHeader, self.pRec)
        return err
    

    cdef int onPLR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0, i = 0
            uint16_t    GRP_CNT
            uint16_t*   pGRP_INDX
            uint16_t*   pGRP_MODE
            uint8_t*    pGRP_RADX
            char**      pPGM_CHAR
            char**      pRTN_CHAR
            char**      pPGM_CHAL
            char**      pRTN_CHAL
        
        parse_record(&self.pRec, recHeader, rawData, binaryLen)

        GRP_CNT = (<PLR*>self.pRec).GRP_CNT
        pGRP_INDX = (<PLR*>self.pRec).GRP_INDX      # Pin or Pin_Group
        pGRP_MODE = (<PLR*>self.pRec).GRP_MODE
        pGRP_RADX = (<PLR*>self.pRec).GRP_RADX
        pPGM_CHAR = (<PLR*>self.pRec).PGM_CHAR
        pRTN_CHAR = (<PLR*>self.pRec).RTN_CHAR
        pPGM_CHAL = (<PLR*>self.pRec).PGM_CHAL
        pRTN_CHAL = (<PLR*>self.pRec).RTN_CHAL
        
        # insert info into Pin_Info
        for i in range(GRP_CNT):
            if not err:
                sqlite3_bind_int(self.insertPinInfo_stmt, 1, (pGRP_INDX + i)[0])
                # Even there are 2 :P_PG_INDX, no need to bind the 2nd :P_PG_INDX again
                # sqlite3_bind_int(self.insertPinInfo_stmt, 2, (pGRP_INDX + i)[0])
                sqlite3_bind_int(self.insertPinInfo_stmt, 2, (pGRP_MODE + i)[0])
                sqlite3_bind_int(self.insertPinInfo_stmt, 3, (pGRP_RADX + i)[0])
                if (pPGM_CHAR + i)[0] != NULL:
                    sqlite3_bind_text(self.insertPinInfo_stmt, 4, (pPGM_CHAR + i)[0], -1, NULL)
                if (pPGM_CHAL + i)[0] != NULL:
                    sqlite3_bind_text(self.insertPinInfo_stmt, 5, (pPGM_CHAL + i)[0], -1, NULL)
                if (pRTN_CHAR + i)[0] != NULL:
                    sqlite3_bind_text(self.insertPinInfo_stmt, 6, (pRTN_CHAR + i)[0], -1, NULL)
                if (pRTN_CHAL + i)[0] != NULL:
                    sqlite3_bind_text(self.insertPinInfo_stmt, 7, (pRTN_CHAL + i)[0], -1, NULL)
                err = csqlite3_step(self.insertPinInfo_stmt)
        
        free_record(recHeader, self.pRec)
        return err
    
    
    cdef int onPIR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0
            uint8_t HEAD_NUM, SITE_NUM

        # used for linking TRs with PRR
        self.dutIndex += 1
        self.isBeforePRR = True
        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        HEAD_NUM = (<PIR*>self.pRec).HEAD_NUM
        SITE_NUM = (<PIR*>self.pRec).SITE_NUM
        
        if (MAP_OK != hashmap_put(self.head_site_dutIndex, HEAD_NUM<<8 | SITE_NUM, self.dutIndex)):
            err = MAP_OMEM
            sprintf(self.detailErrorMsg, "Error in [%d]PIR, Head:%d Site:%d", self.dutIndex, HEAD_NUM, SITE_NUM)
        
        if not err:
            sqlite3_bind_int(self.insertDut_stmt, 1, HEAD_NUM)
            sqlite3_bind_int(self.insertDut_stmt, 2, SITE_NUM)
            sqlite3_bind_int(self.insertDut_stmt, 3, self.dutIndex)
            err = csqlite3_step(self.insertDut_stmt)
    
        free_record(recHeader, self.pRec)
        return err
    
    
    cdef int onTR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int testID = 0
            uint32_t TEST_NUM, currentDutIndex, _1stLLimit, _1stHLimit
            uint8_t HEAD_NUM, SITE_NUM, OPT_FLAG
            uint16_t RTN_ICNT = 0, RSLT_PGM_CNT = 0     # For FTR & MPR
            int i, RES_SCAL, err = 0
            float LLimit = 0, HLimit = 0, LSpec = 0, HSpec = 0
            bint No_RES_SCAL = False, No_LLimit = False, No_HLimit = False, No_HSpec = False, No_LSpec = False
            bint LLimitChanged = False, HLimitChanged = False
            char* VECT_NAM = NULL
            char* TEST_TXT = NULL
            char* Unit = NULL
            char* SEQ_NAM = NULL
            int SEQ_NAM_LEN = 0
            uint16_t*   pRTN_INDX = NULL   # For FTR & MPR
            uint16_t*   pPGM_INDX = NULL   # For FTR

        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        # read testNum headNum and siteNum
        if recHeader == REC_PTR:
            TEST_NUM = (<PTR*>self.pRec).TEST_NUM
            TEST_TXT = (<PTR*>self.pRec).TEST_TXT
            HEAD_NUM = (<PTR*>self.pRec).HEAD_NUM
            SITE_NUM = (<PTR*>self.pRec).SITE_NUM
        elif recHeader == REC_FTR:
            TEST_NUM = (<FTR*>self.pRec).TEST_NUM
            TEST_TXT = (<FTR*>self.pRec).TEST_TXT
            HEAD_NUM = (<FTR*>self.pRec).HEAD_NUM
            SITE_NUM = (<FTR*>self.pRec).SITE_NUM
        else:
            TEST_NUM = (<MPR*>self.pRec).TEST_NUM
            TEST_TXT = (<MPR*>self.pRec).TEST_TXT
            HEAD_NUM = (<MPR*>self.pRec).HEAD_NUM
            SITE_NUM = (<MPR*>self.pRec).SITE_NUM

        if TEST_TXT == NULL:
            TEST_TXT = ""

        if (MAP_OK != hashmap_get(self.head_site_dutIndex, HEAD_NUM<<8 | SITE_NUM, &currentDutIndex)):
            err = MAP_MISSING
            sprintf(self.detailErrorMsg, "Error key in XTR %d, TestNumber:%d Head:%d Site:%d", recHeader, TEST_NUM, HEAD_NUM, SITE_NUM)

        testID = getTestID(self.idMap, TEST_NUM, TEST_TXT)
        if testID < 0:
            testID = insertTestItem(self.idMap, TEST_NUM, TEST_TXT)
            if testID < 0:
                err = testID
                sprintf(self.detailErrorMsg, "Error when storing testID for TestNumber:%d Head:%d Site:%d", TEST_NUM, HEAD_NUM, SITE_NUM)

        if not err:
            # insert or replace Test_Offsets
            sqlite3_bind_int(self.insertTR_stmt, 1, currentDutIndex)                # DUTIndex
            sqlite3_bind_int(self.insertTR_stmt, 2, testID)                         # TEST_ID
            sqlite3_bind_int64(self.insertTR_stmt, 3, <sqlite3_int64>self.offset)   # offset
            sqlite3_bind_int(self.insertTR_stmt, 4, binaryLen)                      # BinaryLen
            err = csqlite3_step(self.insertTR_stmt)
        
        # cache omitted fields
        # MUST pre-read and cache OPT_FLAG, RES_SCAL, LLM_SCAL, HLM_SCAL of a test item from the first record
        # as it may be omitted in the later record, causing typeError when user directly selects sites where 
        # no such field value is available in the data preparation.
        if (not err) and (not hashmap_contains(self.defaultLLimit, testID)):
            if recHeader == REC_FTR: # FTR
                No_RES_SCAL = No_LLimit = No_HLimit = No_LSpec = No_HSpec = True
                OPT_FLAG    = (<FTR*>self.pRec).OPT_FLAG
                Unit        = ""
                RTN_ICNT    = (<FTR*>self.pRec).RTN_ICNT
                RSLT_PGM_CNT= (<FTR*>self.pRec).PGM_ICNT
                pRTN_INDX   = (<FTR*>self.pRec).RTN_INDX
                pPGM_INDX   = (<FTR*>self.pRec).PGM_INDX
                VECT_NAM    = (<FTR*>self.pRec).VECT_NAM

            elif recHeader == REC_PTR:
                RES_SCAL    = (<PTR*>self.pRec).RES_SCAL
                LLimit      = (<PTR*>self.pRec).LO_LIMIT
                HLimit      = (<PTR*>self.pRec).HI_LIMIT
                LSpec       = (<PTR*>self.pRec).LO_SPEC
                HSpec       = (<PTR*>self.pRec).HI_SPEC
                Unit        = (<PTR*>self.pRec).UNITS
                OPT_FLAG    = (<PTR*>self.pRec).OPT_FLAG
                No_RES_SCAL = (OPT_FLAG & 0x01 == 0x01)
                No_LLimit   = (OPT_FLAG & 0x10 == 0x10) or (OPT_FLAG & 0x40 == 0x40)
                No_HLimit   = (OPT_FLAG & 0x20 == 0x20) or (OPT_FLAG & 0x80 == 0x80)
                No_LSpec    = (OPT_FLAG & 0x04 == 0x04)
                No_HSpec    = (OPT_FLAG & 0x08 == 0x08)

            else:
                RES_SCAL    = (<MPR*>self.pRec).RES_SCAL
                LLimit      = (<MPR*>self.pRec).LO_LIMIT
                HLimit      = (<MPR*>self.pRec).HI_LIMIT
                LSpec       = (<MPR*>self.pRec).LO_SPEC
                HSpec       = (<MPR*>self.pRec).HI_SPEC
                Unit        = (<MPR*>self.pRec).UNITS
                OPT_FLAG    = (<MPR*>self.pRec).OPT_FLAG
                RTN_ICNT    = (<MPR*>self.pRec).RTN_ICNT
                RSLT_PGM_CNT= (<MPR*>self.pRec).RSLT_CNT
                pRTN_INDX   = (<MPR*>self.pRec).RTN_INDX
                No_RES_SCAL = (OPT_FLAG & 0x01 == 0x01)
                No_LLimit   = (OPT_FLAG & 0x10 == 0x10) or (OPT_FLAG & 0x40 == 0x40)
                No_HLimit   = (OPT_FLAG & 0x20 == 0x20) or (OPT_FLAG & 0x80 == 0x80)
                No_LSpec    = (OPT_FLAG & 0x04 == 0x04)
                No_HSpec    = (OPT_FLAG & 0x08 == 0x08)

            # put the first Low Limit and High Limit in the dictionary, 
            if (MAP_OK != hashmap_put(self.defaultLLimit, testID, (<uint32_t*>&LLimit)[0]) or 
                MAP_OK != hashmap_put(self.defaultHLimit, testID, (<uint32_t*>&HLimit)[0])):  # convert float bits to uint bits
                err = MAP_OMEM
                sprintf(self.detailErrorMsg, "Error when storing limits in XTR %d, TestNumber:%d Head:%d Site:%d", recHeader, TEST_NUM, HEAD_NUM, SITE_NUM)

            if Unit == NULL: Unit = ""
            if not err:
                sqlite3_bind_int(self.insertTestInfo_stmt, 1, testID)                   # TEST_ID
                sqlite3_bind_int(self.insertTestInfo_stmt, 2, TEST_NUM)                 # TEST_NUM
                sqlite3_bind_int(self.insertTestInfo_stmt, 3, recHeader)                # recHeader
                sqlite3_bind_text(self.insertTestInfo_stmt, 4, TEST_TXT, -1, NULL)      # TEST_NAME
                if not No_RES_SCAL:
                    sqlite3_bind_int(self.insertTestInfo_stmt, 5, RES_SCAL)             # RES_SCAL
                if not No_LLimit:
                    sqlite3_bind_double(self.insertTestInfo_stmt, 6, LLimit)            # LLimit
                if not No_HLimit:
                    sqlite3_bind_double(self.insertTestInfo_stmt, 7, HLimit)            # HLimit
                sqlite3_bind_text(self.insertTestInfo_stmt, 8, Unit, -1, NULL)          # Unit
                sqlite3_bind_int(self.insertTestInfo_stmt, 9, OPT_FLAG)                 # OPT_FLAG
                sqlite3_bind_int(self.insertTestInfo_stmt, 10, -1)                      # FailCnt, default -1
                if RTN_ICNT > 0:
                    sqlite3_bind_int(self.insertTestInfo_stmt, 11, RTN_ICNT)            # RTN_ICNT for FTR & MPR
                if RSLT_PGM_CNT > 0:
                    sqlite3_bind_int(self.insertTestInfo_stmt, 12, RSLT_PGM_CNT)        # RSLT or PGM for MPR or FTR
                if not No_LSpec:
                    sqlite3_bind_double(self.insertTestInfo_stmt, 13, LSpec)            # LSpec
                if not No_HSpec:
                    sqlite3_bind_double(self.insertTestInfo_stmt, 14, HSpec)            # LSpec
                if not VECT_NAM == NULL:
                    sqlite3_bind_text(self.insertTestInfo_stmt, 15, VECT_NAM, -1, NULL) # VECT_NAM
                if self.programSectionsDepth > 0:
                    for i in range(self.programSectionsDepth):
                        SEQ_NAM_LEN += (strlen(self.programSections[i]) + 2)        # +2 get extra space to prevent crash
                    SEQ_NAM = <char*>calloc(SEQ_NAM_LEN, sizeof(char))
                    if SEQ_NAM:
                        for i in range(self.programSectionsDepth):
                            sprintf(SEQ_NAM + strlen(SEQ_NAM), "%s;", self.programSections[i])
                        SEQ_NAM[strlen(SEQ_NAM)-1] = 0x00
                        sqlite3_bind_text(self.insertTestInfo_stmt, 16, SEQ_NAM, -1, NULL) # SEQ_NAM
                    else:
                        return NO_MEMORY
                    
                err = csqlite3_step(self.insertTestInfo_stmt)
                if self.programSectionsDepth > 0:
                    free(SEQ_NAM)

            # store PMR indexes of each FTR & MPR
            if not err and recHeader != REC_PTR:
                if RTN_ICNT > 0 and pRTN_INDX != NULL:
                    for i in range(RTN_ICNT):
                        sqlite3_bind_int(self.insertTestPin_stmt, 1, testID)
                        sqlite3_bind_int(self.insertTestPin_stmt, 2, pRTN_INDX[i])
                        sqlite3_bind_text(self.insertTestPin_stmt, 3, "RTN", -1, NULL)
                        err = csqlite3_step(self.insertTestPin_stmt)

                if RSLT_PGM_CNT > 0 and pPGM_INDX != NULL:
                    for i in range(RTN_ICNT):
                        sqlite3_bind_int(self.insertTestPin_stmt, 1, testID)
                        sqlite3_bind_int(self.insertTestPin_stmt, 2, pPGM_INDX[i])
                        sqlite3_bind_text(self.insertTestPin_stmt, 3, "PGM", -1, NULL)
                        err = csqlite3_step(self.insertTestPin_stmt)

        else:
            # This case is for handling dynamic limits in PTR only, FTR is not allowed, MPR must use the same limits
            if (not err) and (recHeader == REC_PTR):
                # test_num has been seen, defaultLLimit contains test_num
                # we need to check if the limits are differ from the default one in the dictionary
                LLimit      = (<PTR*>self.pRec).LO_LIMIT
                HLimit      = (<PTR*>self.pRec).HI_LIMIT
                OPT_FLAG    = (<PTR*>self.pRec).OPT_FLAG
                # OPT_FLAG in PTR can't be 0 (bit 1 must be 1), otherwise it is omitted
                # omitted limits is the same as default
                if OPT_FLAG:
                    No_LLimit = (OPT_FLAG & 0x10 == 0x10) or (OPT_FLAG & 0x40 == 0x40)
                    No_HLimit = (OPT_FLAG & 0x20 == 0x20) or (OPT_FLAG & 0x80 == 0x80)
                    if not No_LLimit:
                        # low limit is available
                        # get default low limit from dictionary
                        if (MAP_OK != hashmap_get(self.defaultLLimit, testID, &_1stLLimit)): 
                            err = MAP_MISSING
                            sprintf(self.detailErrorMsg, "Error getting default low limit in XTR %d, TestNumber:%d Head:%d Site:%d", recHeader, TEST_NUM, HEAD_NUM, SITE_NUM)
                        # check if it's changed
                        if (_1stLLimit != (<uint32_t*>&LLimit)[0]): LLimitChanged = True
                        
                    if not No_HLimit:
                        # high limit is available
                        if (MAP_OK != hashmap_get(self.defaultHLimit, testID, &_1stHLimit)): 
                            err = MAP_MISSING
                            sprintf(self.detailErrorMsg, "Error getting default high limit in XTR %d, TestNumber:%d Head:%d Site:%d", recHeader, TEST_NUM, HEAD_NUM, SITE_NUM)
                        if (_1stHLimit != (<uint32_t*>&HLimit)[0]): HLimitChanged = True

                    if (not err) and (LLimitChanged or HLimitChanged):
                        # any limit changed, write into db
                        sqlite3_bind_int(self.insertDynamicLimit_stmt, 1, currentDutIndex)         # dutIndex 
                        sqlite3_bind_int(self.insertDynamicLimit_stmt, 2, testID)                  # TEST_ID
                        if LLimitChanged:
                            sqlite3_bind_double(self.insertDynamicLimit_stmt, 3, LLimit)            # LLimit
                        if HLimitChanged:
                            sqlite3_bind_double(self.insertDynamicLimit_stmt, 4, HLimit)            # HLimit
                        err = csqlite3_step(self.insertDynamicLimit_stmt)

        free_record(recHeader, self.pRec)
        return err
                            
            
    cdef int onPRR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            bint No_Wafer = False
            uint8_t HEAD_NUM, SITE_NUM, PART_FLG
            uint32_t currentDutIndex, currentWaferIndex
            int HARD_BIN, SOFT_BIN, NUM_TEST, X_COORD, Y_COORD, TEST_T, err = 0
            char* PART_ID
        
        self.isBeforePRR = False
        # in PRR, all BPS should be closed by EPS
        cdef int i
        if self.programSectionsDepth > 0:
            # if not all closed, clean it now
            for i in range(self.programSectionsDepth):
                free(self.programSections[i])
            free(self.programSections)
            self.programSections = NULL
            self.programSectionsDepth = 0

        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        HEAD_NUM    = (<PRR*>self.pRec).HEAD_NUM
        SITE_NUM    = (<PRR*>self.pRec).SITE_NUM
        HARD_BIN    = (<PRR*>self.pRec).HARD_BIN
        SOFT_BIN    = (<PRR*>self.pRec).SOFT_BIN
        PART_FLG    = (<PRR*>self.pRec).PART_FLG
        NUM_TEST    = (<PRR*>self.pRec).NUM_TEST
        X_COORD     = (<PRR*>self.pRec).X_COORD
        Y_COORD     = (<PRR*>self.pRec).Y_COORD
        TEST_T      = (<PRR*>self.pRec).TEST_T
        PART_ID     = (<PRR*>self.pRec).PART_ID

        if (MAP_OK != hashmap_get(self.head_site_dutIndex, HEAD_NUM<<8 | SITE_NUM, &currentDutIndex)):
            err = MAP_MISSING
            sprintf(self.detailErrorMsg, "Error dutIndex key in PRR, Head:%d Site:%d", HEAD_NUM, SITE_NUM)
        
        if hashmap_contains(self.head_waferIndex, HEAD_NUM):
            No_Wafer = False
            if (MAP_OK != hashmap_get(self.head_waferIndex, HEAD_NUM, &currentWaferIndex)):
                err = MAP_MISSING
                sprintf(self.detailErrorMsg, "Error waferIndex key in PRR, Head:%d", HEAD_NUM)
        else:
            No_Wafer = True

        if PART_ID == NULL: PART_ID = ""
        if not err:
            sqlite3_bind_int(self.updateDut_stmt, 1, NUM_TEST)                      # TestCount
            sqlite3_bind_int(self.updateDut_stmt, 2, TEST_T)                        # TestTime
            sqlite3_bind_text(self.updateDut_stmt, 3, PART_ID, -1, NULL)            # PartID
            sqlite3_bind_int(self.updateDut_stmt, 4, HARD_BIN)                      # HBIN_NUM
            sqlite3_bind_int(self.updateDut_stmt, 5, SOFT_BIN)                      # SBIN_NUM
            sqlite3_bind_int(self.updateDut_stmt, 6, PART_FLG)                      # Flag
            if not No_Wafer:
                sqlite3_bind_int(self.updateDut_stmt, 7, currentWaferIndex)         # WaferIndex
            else:
                sqlite3_bind_null(self.updateDut_stmt, 7)
            if X_COORD != -32768:
                sqlite3_bind_int(self.updateDut_stmt, 8, X_COORD)                   # XCOORD
            else:
                sqlite3_bind_null(self.updateDut_stmt, 8)
            if Y_COORD != -32768:
                sqlite3_bind_int(self.updateDut_stmt, 9, Y_COORD)                   # YCOORD
            else:
                sqlite3_bind_null(self.updateDut_stmt, 9)
            sqlite3_bind_int(self.updateDut_stmt, 10, currentDutIndex)              # DUTIndex
            err = csqlite3_step(self.updateDut_stmt)
        
        # we can determine the type of hard/soft bin based on the part_flag
        # it is helpful if the std is incomplete and lack of HBR/SBR
        # if key is existed, do not update repeatedly        
        if not err: 
            sqlite3_bind_int(self.insertHBIN_stmt, 1, HARD_BIN)                                         # HBIN_NUM
            sqlite3_bind_text(self.insertHBIN_stmt, 2, "MissingName", -1, NULL)     # HBIN_NAME
            if PART_FLG & 0b00011000 == 0:
                sqlite3_bind_text(self.insertHBIN_stmt, 3, "P", -1, NULL)  # PF
            elif PART_FLG & 0b00010000 == 0:
                sqlite3_bind_text(self.insertHBIN_stmt, 3, "F", -1, NULL)  # PF
            else:
                sqlite3_bind_text(self.insertHBIN_stmt, 3, "U", -1, NULL)  # PF
            err = csqlite3_step(self.insertHBIN_stmt)

        if not err: 
            sqlite3_bind_int(self.insertSBIN_stmt, 1, SOFT_BIN)                                         # SBIN_NUM
            sqlite3_bind_text(self.insertSBIN_stmt, 2, "MissingName", -1, NULL)     # SBIN_NAME
            if PART_FLG & 0b00011000 == 0:
                sqlite3_bind_text(self.insertSBIN_stmt, 3, "P", -1, NULL)  # PF
            elif PART_FLG & 0b00010000 == 0:
                sqlite3_bind_text(self.insertSBIN_stmt, 3, "F", -1, NULL)  # PF
            else:
                sqlite3_bind_text(self.insertSBIN_stmt, 3, "U", -1, NULL)  # PF
            err = csqlite3_step(self.insertSBIN_stmt)
        free_record(recHeader, self.pRec)
        return err
            
        
    cdef int onHBR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int HBIN_NUM, err = 0
            char* HBIN_NAM
            char  HBIN_PF[2]
        # This method is used for getting bin num/names/PF
        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        # SITE_NUM = valueDict["SITE_NUM"]
        HBIN_NUM = (<HBR*>self.pRec).HBIN_NUM
        sprintf(HBIN_PF, "%c", (<HBR*>self.pRec).HBIN_PF)
        HBIN_PF[1] = 0x00
        HBIN_NAM = (<HBR*>self.pRec).HBIN_NAM
        # use the count from PRR as default, in case the file is incomplete
        # HBIN_CNT = valueDict["HBIN_CNT"]
        if HBIN_PF[0] != 0x46 and HBIN_PF[0] != 0x50:
            # not 'F' nor 'P', write default 'U'
            HBIN_PF[0] = 0x55
        if HBIN_NAM == NULL:
            HBIN_NAM = "MissingName"

        if not err: 
            sqlite3_bind_int(self.insertHBIN_stmt, 1, HBIN_NUM)               # HBIN_NUM
            sqlite3_bind_text(self.insertHBIN_stmt, 2, HBIN_NAM, -1, NULL)    # HBIN_NAME
            sqlite3_bind_text(self.insertHBIN_stmt, 3, HBIN_PF, -1, NULL)     # PF
            err = csqlite3_step(self.insertHBIN_stmt)
        free_record(recHeader, self.pRec)
        return err
       
        
    cdef int onSBR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int SBIN_NUM, err = 0
            char* SBIN_NAM
            char  SBIN_PF[2]
        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        # SITE_NUM = valueDict["SITE_NUM"]
        SBIN_NUM = (<SBR*>self.pRec).SBIN_NUM
        sprintf(SBIN_PF, "%c", (<SBR*>self.pRec).SBIN_PF)
        SBIN_PF[1] = 0x00
        SBIN_NAM = (<SBR*>self.pRec).SBIN_NAM
        if SBIN_PF[0] != 0x46 and SBIN_PF[0] != 0x50:
            # not 'F' nor 'P', write default 'U'
            SBIN_PF[0] = 0x55
        if SBIN_NAM == NULL:
            SBIN_NAM = "MissingName"
        
        if not err: 
            sqlite3_bind_int(self.insertSBIN_stmt, 1, SBIN_NUM)               # SBIN_NUM
            sqlite3_bind_text(self.insertSBIN_stmt, 2, SBIN_NAM, -1, NULL)    # SBIN_NAME
            sqlite3_bind_text(self.insertSBIN_stmt, 3, SBIN_PF, -1, NULL)     # PF
            err = csqlite3_step(self.insertSBIN_stmt)        
        free_record(recHeader, self.pRec)
        return err


    cdef int onWCR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0
            double WAFR_SIZ, DIE_HT, DIE_WID
            uint8_t WF_UNITS, 
            int16_t CENTER_X, CENTER_Y
            char WF_FLAT[2]
            char POS_X[2]
            char POS_Y[2]
            char stringBuffer[100]
            int bufferLen

        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        WAFR_SIZ = (<WCR*>self.pRec).WAFR_SIZ
        DIE_HT = (<WCR*>self.pRec).DIE_HT
        DIE_WID = (<WCR*>self.pRec).DIE_WID
        WF_UNITS = (<WCR*>self.pRec).WF_UNITS
        sprintf(WF_FLAT, "%c", (<WCR*>self.pRec).WF_FLAT)
        CENTER_X = (<WCR*>self.pRec).CENTER_X
        CENTER_Y = (<WCR*>self.pRec).CENTER_Y
        sprintf(POS_X, "%c", (<WCR*>self.pRec).POS_X)
        sprintf(POS_Y, "%c", (<WCR*>self.pRec).POS_Y)
        WF_FLAT[1] = POS_X[1] = POS_Y[1] = 0x00

        # WAFR_SIZ
        if not err and WAFR_SIZ != 0:
            bufferLen = sprintf(stringBuffer, "%g", WAFR_SIZ)
            if bufferLen < 0: stringBuffer[0] = 0x00
            else: stringBuffer[bufferLen] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "WAFR_SIZ", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        
        # DIE_HT
        if not err and DIE_HT != 0:
            bufferLen = sprintf(stringBuffer, "%g", DIE_HT)
            if bufferLen < 0: stringBuffer[0] = 0x00
            else: stringBuffer[bufferLen] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "DIE_HT", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        # DIE_WID
        if not err and DIE_WID != 0:
            bufferLen = sprintf(stringBuffer, "%g", DIE_WID)
            if bufferLen < 0: stringBuffer[0] = 0x00
            else: stringBuffer[bufferLen] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "DIE_WID", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        # WF_UNITS
        if not err and WF_UNITS != 0:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "WF_UNITS", -1, NULL)
            if WF_UNITS == 1:   # inches
                sqlite3_bind_text(self.insertFileInfo_stmt, 2, "inch", -1, NULL)
            elif WF_UNITS == 2:   # cm
                sqlite3_bind_text(self.insertFileInfo_stmt, 2, "cm", -1, NULL)
            elif WF_UNITS == 3:   # mm
                sqlite3_bind_text(self.insertFileInfo_stmt, 2, "mm", -1, NULL)
            else:   # mil
                sqlite3_bind_text(self.insertFileInfo_stmt, 2, "mil", -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)

        # WF_FLAT
        if not err:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "WF_FLAT", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, WF_FLAT, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        # CENTER_X
        if not err and CENTER_X != -32768:
            bufferLen = sprintf(stringBuffer, "%d", CENTER_X)
            if bufferLen < 0: stringBuffer[0] = 0x00
            else: stringBuffer[bufferLen] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "CENTER_X", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        # CENTER_Y
        if not err and CENTER_Y != -32768:
            bufferLen = sprintf(stringBuffer, "%d", CENTER_Y)
            if bufferLen < 0: stringBuffer[0] = 0x00
            else: stringBuffer[bufferLen] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "CENTER_Y", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
                        
        # POS_X
        if not err:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "POS_X", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, POS_X, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)

        # POS_Y
        if not err:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "POS_Y", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, POS_Y, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)

        free_record(recHeader, self.pRec)
        return err
    
    
    cdef int onWIR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0
            uint8_t HEAD_NUM
            char* WAFER_ID

        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        HEAD_NUM = (<WIR*>self.pRec).HEAD_NUM
        WAFER_ID = (<WIR*>self.pRec).WAFER_ID
        self.waferIndex += 1
        if (MAP_OK != hashmap_put(self.head_waferIndex, HEAD_NUM, self.waferIndex)):
            err = MAP_MISSING
            sprintf(self.detailErrorMsg, "Error in [%d]WIR, Head:%d", self.waferIndex, HEAD_NUM)
        
        # the following info is also available in WRR, but it still should be updated
        # in WIR in case the stdf is incomplete (no WRR).
        if not err:
            sqlite3_bind_int(self.insertWafer_stmt, 1, HEAD_NUM)                 # HEAD_NUM
            sqlite3_bind_int(self.insertWafer_stmt, 2, self.waferIndex)          # WaferIndex
            sqlite3_bind_text(self.insertWafer_stmt, 8, WAFER_ID, -1, NULL)      # WaferID
            err = csqlite3_step(self.insertWafer_stmt)
        free_record(recHeader, self.pRec)
        return err
    
    
    cdef int onWRR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0
            uint8_t HEAD_NUM
            uint32_t currentWaferIndex, PART_CNT, RTST_CNT, ABRT_CNT, GOOD_CNT, FUNC_CNT
            char* WAFER_ID
            char* FABWF_ID
            char* FRAME_ID
            char* MASK_ID
            char* USR_DESC
            char* EXC_DESC

        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        HEAD_NUM = (<WRR*>self.pRec).HEAD_NUM
        PART_CNT = (<WRR*>self.pRec).PART_CNT
        RTST_CNT = (<WRR*>self.pRec).RTST_CNT
        ABRT_CNT = (<WRR*>self.pRec).ABRT_CNT
        GOOD_CNT = (<WRR*>self.pRec).GOOD_CNT
        FUNC_CNT = (<WRR*>self.pRec).FUNC_CNT
        WAFER_ID = (<WRR*>self.pRec).WAFER_ID
        FABWF_ID = (<WRR*>self.pRec).FABWF_ID
        FRAME_ID = (<WRR*>self.pRec).FRAME_ID
        MASK_ID = (<WRR*>self.pRec).MASK_ID
        USR_DESC = (<WRR*>self.pRec).USR_DESC
        EXC_DESC = (<WRR*>self.pRec).EXC_DESC

        if (MAP_OK != hashmap_get(self.head_waferIndex, HEAD_NUM, &currentWaferIndex)):
            err = MAP_MISSING
            sprintf(self.detailErrorMsg, "Error waferIndex key in WRR, Head:%d", HEAD_NUM)

        if not err:
            sqlite3_bind_int(self.insertWafer_stmt, 1, HEAD_NUM)                # HEAD_NUM
            sqlite3_bind_int(self.insertWafer_stmt, 2, currentWaferIndex)       # WaferIndex
            sqlite3_bind_int(self.insertWafer_stmt, 3, PART_CNT)                # PART_CNT
            if RTST_CNT != <uint32_t>0xFFFFFFFF:
                sqlite3_bind_int(self.insertWafer_stmt, 4, RTST_CNT)            # RTST_CNT
            else:
                sqlite3_bind_int(self.insertWafer_stmt, 4, -1)

            if ABRT_CNT != <uint32_t>0xFFFFFFFF:
                sqlite3_bind_int(self.insertWafer_stmt, 5, ABRT_CNT)            # ABRT_CNT
            else:
                sqlite3_bind_int(self.insertWafer_stmt, 5, -1)

            if GOOD_CNT != <uint32_t>0xFFFFFFFF:
                sqlite3_bind_int(self.insertWafer_stmt, 6, GOOD_CNT)            # GOOD_CNT
            else:
                sqlite3_bind_int(self.insertWafer_stmt, 6, -1)

            if FUNC_CNT != <uint32_t>0xFFFFFFFF:
                sqlite3_bind_int(self.insertWafer_stmt, 7, FUNC_CNT)            # FUNC_CNT
            else:
                sqlite3_bind_int(self.insertWafer_stmt, 7, -1)

            sqlite3_bind_text(self.insertWafer_stmt, 8, WAFER_ID, -1, NULL)     # WAFER_ID
            sqlite3_bind_text(self.insertWafer_stmt, 9, FABWF_ID, -1, NULL)     # FABWF_ID
            sqlite3_bind_text(self.insertWafer_stmt, 10, FRAME_ID, -1, NULL)    # FRAME_ID
            sqlite3_bind_text(self.insertWafer_stmt, 11, MASK_ID, -1, NULL)     # MASK_ID
            sqlite3_bind_text(self.insertWafer_stmt, 12, USR_DESC, -1, NULL)    # USR_DESC
            sqlite3_bind_text(self.insertWafer_stmt, 13, EXC_DESC, -1, NULL)    # EXC_DESC
            err = csqlite3_step(self.insertWafer_stmt)

        free_record(recHeader, self.pRec)
        return err

    
    cdef int onTSR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0
            uint32_t TEST_NUM, FAIL_CNT, tmpCount
            char* TEST_NAM = NULL
        # for fast find failed test number globally
        # don't care about head number nor site number
        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        TEST_NUM = (<TSR*>self.pRec).TEST_NUM
        TEST_NAM = (<TSR*>self.pRec).TEST_NAM
        FAIL_CNT = (<TSR*>self.pRec).FAIL_CNT

        if TEST_NAM == NULL:
            TEST_NAM = ""

        testID = getTestID(self.idMap, TEST_NUM, TEST_NAM)
        if testID < 0:
            # err = TESTIDMAP_MISSING
            printf("Error no testID for TEST_NUM %d, TEST_NAM %s key in TSR\n", TEST_NUM, TEST_NAM)
            sprintf(self.detailErrorMsg, "Error no testID for TEST_NUM %d, TEST_NAM %s key in TSR", TEST_NUM, TEST_NAM)

        if testID >= 0 and FAIL_CNT != <uint32_t>0xFFFFFFFF:          # 2**32-1 invalid number for FAIL_CNT
            if hashmap_contains(self.TestFailCount, testID):
                # get previous count and add up
                if (MAP_OK != hashmap_get(self.TestFailCount, testID, &tmpCount)):
                    err = MAP_MISSING
                    sprintf(self.detailErrorMsg, "Error getting count from TSR dict")
                    return err

                tmpCount += FAIL_CNT
                if (MAP_OK != hashmap_put(self.TestFailCount, testID, tmpCount)):
                    err = MAP_OMEM
                    sprintf(self.detailErrorMsg, "Error in TSR when storing count for TEST_NUM %d", TEST_NUM)
            else:
                # save current count
                if (MAP_OK != hashmap_put(self.TestFailCount, testID, FAIL_CNT)):
                    err = MAP_OMEM
                    sprintf(self.detailErrorMsg, "Error in TSR when storing count for TEST_NUM %d", TEST_NUM)
        free_record(recHeader, self.pRec)
        return err


    cdef int onPCR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0
            uint8_t HEAD_NUM, SITE_NUM
            uint32_t PART_CNT, RTST_CNT, ABRT_CNT, GOOD_CNT, FUNC_CNT

        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        HEAD_NUM = (<PCR*>self.pRec).HEAD_NUM
        SITE_NUM = (<PCR*>self.pRec).SITE_NUM
        PART_CNT = (<PCR*>self.pRec).PART_CNT
        RTST_CNT = (<PCR*>self.pRec).RTST_CNT
        ABRT_CNT = (<PCR*>self.pRec).ABRT_CNT
        GOOD_CNT = (<PCR*>self.pRec).GOOD_CNT
        FUNC_CNT = (<PCR*>self.pRec).FUNC_CNT
        
        sqlite3_bind_int(self.insertDutCount_stmt, 1, HEAD_NUM)                # HEAD_NUM
        sqlite3_bind_int(self.insertDutCount_stmt, 2, SITE_NUM)                # SITE_NUM
        sqlite3_bind_int(self.insertDutCount_stmt, 3, PART_CNT)                # PART_CNT
        if RTST_CNT != <uint32_t>0xFFFFFFFF:
            sqlite3_bind_int(self.insertDutCount_stmt, 4, RTST_CNT)            # RTST_CNT
        else:
            sqlite3_bind_int(self.insertDutCount_stmt, 4, -1)

        if ABRT_CNT != <uint32_t>0xFFFFFFFF:
            sqlite3_bind_int(self.insertDutCount_stmt, 5, ABRT_CNT)            # ABRT_CNT
        else:
            sqlite3_bind_int(self.insertDutCount_stmt, 5, -1)

        if GOOD_CNT != <uint32_t>0xFFFFFFFF:
            sqlite3_bind_int(self.insertDutCount_stmt, 6, GOOD_CNT)            # GOOD_CNT
        else:
            sqlite3_bind_int(self.insertDutCount_stmt, 6, -1)

        if FUNC_CNT != <uint32_t>0xFFFFFFFF:
            sqlite3_bind_int(self.insertDutCount_stmt, 7, FUNC_CNT)            # FUNC_CNT
        else:
            sqlite3_bind_int(self.insertDutCount_stmt, 7, -1)

        err = csqlite3_step(self.insertDutCount_stmt)
        free_record(recHeader, self.pRec)
        return err    


    cdef int onDTR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0
        
        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        
        sqlite3_bind_text(self.insertDatalog_stmt, 1, "DTR", -1, NULL)                      # RecordType
        sqlite3_bind_text(self.insertDatalog_stmt, 2, (<DTR*>self.pRec).TEXT_DAT, -1, NULL) # Value
        sqlite3_bind_int(self.insertDatalog_stmt, 3, self.dutIndex)
        sqlite3_bind_int(self.insertDatalog_stmt, 4, self.isBeforePRR)
        err = csqlite3_step(self.insertDatalog_stmt)

        free_record(recHeader, self.pRec)
        return err


    cdef int onGDR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0, result_len = 0, previous_len = 0, tmp_len = 0, i, j
            char* result = NULL
            char* tmp = NULL
            char* hexString = NULL
            uint16_t FLD_CNT
            Vn GEN_DATA
            V1 Gen_ele

        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        FLD_CNT = (<GDR*>self.pRec).FLD_CNT
        GEN_DATA = (<GDR*>self.pRec).GEN_DATA
        
        if FLD_CNT > 0 and GEN_DATA != NULL:
            # Flatten Vn to char*
            for i in range(FLD_CNT):
                Gen_ele = GEN_DATA[i]
                if Gen_ele.dataType < 0 or Gen_ele.dataType > 13:
                    # invalid type, the rest V1 is not valid
                    break
                else:
                    # valid type
                    if Gen_ele.dataType == GDR_B0:
                        # store old result_len for snprintf
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d B0: NULL\n", i)
                        result_len = tmp_len + previous_len
                        # alloc memory to store new string
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        # append string
                        snprintf(result + previous_len, tmp_len+1, "%d B0: NULL\n", i)

                    elif Gen_ele.dataType == GDR_U1:
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d U1: %d\n", i, (<U1*>(Gen_ele.data))[0])
                        result_len = tmp_len + previous_len
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        snprintf(result + previous_len, tmp_len+1, "%d U1: %d\n", i, (<U1*>(Gen_ele.data))[0])
                    
                    elif Gen_ele.dataType == GDR_U2:
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d U2: %d\n", i, (<U2*>(Gen_ele.data))[0])
                        result_len = tmp_len + previous_len
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        snprintf(result + previous_len, tmp_len+1, "%d U2: %d\n", i, (<U2*>(Gen_ele.data))[0])
                        
                    elif Gen_ele.dataType == GDR_U4:
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d U4: %d\n", i, (<U4*>(Gen_ele.data))[0])
                        result_len = tmp_len + previous_len
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        snprintf(result + previous_len, tmp_len+1, "%d U4: %d\n", i, (<U4*>(Gen_ele.data))[0])
                        
                    elif Gen_ele.dataType == GDR_I1:
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d I1: %d\n", i, (<I1*>(Gen_ele.data))[0])
                        result_len = tmp_len + previous_len
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        snprintf(result + previous_len, tmp_len+1, "%d I1: %d\n", i, (<I1*>(Gen_ele.data))[0])
                        
                    elif Gen_ele.dataType == GDR_I2:
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d I2: %d\n", i, (<I2*>(Gen_ele.data))[0])
                        result_len = tmp_len + previous_len
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        snprintf(result + previous_len, tmp_len+1, "%d I2: %d\n", i, (<I2*>(Gen_ele.data))[0])
                        
                    elif Gen_ele.dataType == GDR_I4:
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d I4: %d\n", i, (<I4*>(Gen_ele.data))[0])
                        result_len = tmp_len + previous_len
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        snprintf(result + previous_len, tmp_len+1, "%d I4: %d\n", i, (<I4*>(Gen_ele.data))[0])
                        
                    elif Gen_ele.dataType == GDR_R4:
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d R4: %f\n", i, (<R4*>(Gen_ele.data))[0])
                        result_len = tmp_len + previous_len
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        snprintf(result + previous_len, tmp_len+1, "%d R4: %f\n", i, (<R4*>(Gen_ele.data))[0])
                        
                    elif Gen_ele.dataType == GDR_R8:
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d R8: %f\n", i, (<R8*>(Gen_ele.data))[0])
                        result_len = tmp_len + previous_len
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        snprintf(result + previous_len, tmp_len+1, "%d R8: %f\n", i, (<R8*>(Gen_ele.data))[0])
                        
                    elif Gen_ele.dataType == GDR_Cn:
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d Cn: %s\n", i, (<Cn*>(Gen_ele.data))[0])
                        result_len = tmp_len + previous_len
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        snprintf(result + previous_len, tmp_len+1, "%d Cn: %s\n", i, (<Cn*>(Gen_ele.data))[0])
                    
                    # For Bn & Dn, convert the data to Hex string
                    elif Gen_ele.dataType == GDR_Bn:
                        if Gen_ele.byteCnt > 0:
                            tmp_len = 5 + 3 * Gen_ele.byteCnt + 1  # (HEX)_FF_..._FF\0
                            hexString = <char*>calloc(tmp_len, sizeof(char))
                            if hexString:
                                sprintf( hexString + strlen(hexString), "%s", <char*>"(HEX)")
                                for j in range(Gen_ele.byteCnt):
                                    sprintf( hexString + strlen(hexString), " %02X", (<Bn*>(Gen_ele.data))[0][j])
                            else:
                                return NO_MEMORY
                        else:
                            hexString = "NULL"
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d Bn: %s\n", i, hexString)
                        result_len = tmp_len + previous_len
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        snprintf(result + previous_len, tmp_len+1, "%d Bn: %s\n", i, hexString)
                        if Gen_ele.byteCnt > 0:
                            free(hexString)
                        
                    elif Gen_ele.dataType == GDR_Dn:
                        if Gen_ele.byteCnt > 0:
                            tmp_len = 5 + 3 * Gen_ele.byteCnt + 1  # (HEX)_FF_..._FF\0
                            hexString = <char*>calloc(tmp_len, sizeof(char))
                            if hexString:
                                sprintf( hexString + strlen(hexString), "%s", <char*>"(HEX)")
                                for j in range(Gen_ele.byteCnt):
                                    sprintf( hexString + strlen(hexString), " %02X", (<Dn*>(Gen_ele.data))[0][j])
                            else:
                                return NO_MEMORY
                        else:
                            hexString = "NULL"
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d Dn: %s\n", i, hexString)
                        result_len = tmp_len + previous_len
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        snprintf(result + previous_len, tmp_len+1, "%d Dn: %s\n", i, hexString)
                        if Gen_ele.byteCnt > 0:
                            free(hexString)
                    
                    elif Gen_ele.dataType == GDR_N1:
                        previous_len = result_len
                        tmp_len = snprintf(NULL, 0, "%d N1: %X\n", i, (<B1*>(Gen_ele.data))[0])
                        result_len = tmp_len + previous_len
                        tmp = <char*>realloc(result, result_len + 1)   # plus 1 for \0
                        if tmp: result = tmp
                        else: return NO_MEMORY
                        snprintf(result + previous_len, tmp_len+1, "%d N1: %X\n", i, (<B1*>(Gen_ele.data))[0])
            # replace the last \n with \0 terminator
            result[strlen(result) - 1] = 0x00
        else:
            result = "NULL"

        sqlite3_bind_text(self.insertDatalog_stmt, 1, "GDR", -1, NULL)      # RecordType
        sqlite3_bind_text(self.insertDatalog_stmt, 2, result, -1, NULL)     # Value
        sqlite3_bind_int(self.insertDatalog_stmt, 3, self.dutIndex)
        sqlite3_bind_int(self.insertDatalog_stmt, 4, self.isBeforePRR)
        err = csqlite3_step(self.insertDatalog_stmt)

        if FLD_CNT > 0 and GEN_DATA != NULL:
            free(result)
        free_record(recHeader, self.pRec)
        return err


    cdef int onBPS(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            void* tmpPtr = NULL
            char* SEQ_NAME

        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        SEQ_NAME = (<BPS*>self.pRec).SEQ_NAME

        tmpPtr = realloc(self.programSections, self.programSectionsDepth + 1)
        if tmpPtr:
            # increase depth only if successfully realloc
            self.programSectionsDepth += 1
            self.programSections = <char**>tmpPtr
            # alloc memory to store SEQ_NAME
            tmpPtr = calloc( (strlen(SEQ_NAME)+1), sizeof(char))
            if tmpPtr:
                self.programSections[self.programSectionsDepth - 1] = <char*>tmpPtr
                strcpy(self.programSections[self.programSectionsDepth - 1], SEQ_NAME)
            else:
                return NO_MEMORY
        else:
            return NO_MEMORY

        free_record(recHeader, self.pRec)
        return 0


    cdef int onEPS(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        # reduce programSectionsDepth by 1, and free memory
        if self.programSectionsDepth:
            # free the last char*
            free(self.programSections[self.programSectionsDepth - 1])
            self.programSectionsDepth -= 1
        return 0


    cdef int onRDR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0, l = 0, i
            uint16_t  NUM_BINS
            uint16_t* RTST_BIN
            char*     result
        
        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        NUM_BINS = (<RDR*>self.pRec).NUM_BINS
        RTST_BIN = (<RDR*>self.pRec).RTST_BIN
        if NUM_BINS > 0:
            for i in range(NUM_BINS):
                l += snprintf(NULL, 0, "%d, ", RTST_BIN[i])
            l += 10 # add more budget
            # convert array to string
            result = <char*>calloc(l, sizeof(char))
            for i in range(NUM_BINS-1):
                sprintf( result + strlen(result), "%d, ", RTST_BIN[i])
            sprintf( result + strlen(result), "%d", RTST_BIN[NUM_BINS-1])
        else:
            result = "All hardware bins are retested"

        sqlite3_bind_text(self.insertFileInfo_stmt, 1, "Retest Hardware Bins", -1, NULL)
        sqlite3_bind_text(self.insertFileInfo_stmt, 2, result, -1, NULL)
        err = csqlite3_step(self.insertFileInfo_stmt)

        if NUM_BINS > 0:
            free(result)
        free_record(recHeader, self.pRec)
        return err


    cdef int onSDR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0, l
            char     tmpName[100]
            uint8_t  SITE_GRP
        
        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        SITE_GRP = (<SDR*>self.pRec).SITE_GRP

        if not err and (<SDR*>self.pRec).HAND_TYP != NULL:
            l = sprintf(tmpName, "Handler Type (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).HAND_TYP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)

        if not err and (<SDR*>self.pRec).HAND_ID != NULL:
            l = sprintf(tmpName, "Handler ID (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).HAND_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)

        if not err and (<SDR*>self.pRec).CARD_TYP != NULL:
            l = sprintf(tmpName, "Probe Card Type (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).CARD_TYP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).CARD_ID != NULL:
            l = sprintf(tmpName, "Probe Card ID (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).CARD_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).LOAD_TYP != NULL:
            l = sprintf(tmpName, "Load Board Type (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).LOAD_TYP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).LOAD_ID != NULL:
            l = sprintf(tmpName, "Load Board ID (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).LOAD_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).DIB_TYP != NULL:
            l = sprintf(tmpName, "DIB Board Type (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).DIB_TYP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).DIB_ID != NULL:
            l = sprintf(tmpName, "DIB Board ID (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).DIB_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).CABL_TYP != NULL:
            l = sprintf(tmpName, "Interface Cable Type (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).CABL_TYP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).CABL_ID != NULL:
            l = sprintf(tmpName, "Interface Cable ID (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).CABL_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).CONT_TYP != NULL:
            l = sprintf(tmpName, "Handler Contactor Type (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).CONT_TYP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).CONT_ID != NULL:
            l = sprintf(tmpName, "Handler Contactor ID (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).CONT_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).LASR_TYP != NULL:
            l = sprintf(tmpName, "Laser Type (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).LASR_TYP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).LASR_ID != NULL:
            l = sprintf(tmpName, "Laser ID (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).LASR_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).EXTR_TYP != NULL:
            l = sprintf(tmpName, "Extra Equipment Type (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).EXTR_TYP, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
            
        if not err and (<SDR*>self.pRec).EXTR_ID != NULL:
            l = sprintf(tmpName, "Extra Equipment ID (Group %d)", SITE_GRP)
            tmpName[l] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, tmpName, -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<SDR*>self.pRec).EXTR_ID, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)

        free_record(recHeader, self.pRec)
        return err
    
    
    cdef int onMRR(self, uint16_t recHeader, uint16_t binaryLen, unsigned char* rawData) nogil:
        cdef:
            int err = 0
            time_t timeStamp
            tm*    tmPtr
            char   stringBuffer[256]
            char   DISP_COD
            char*  USR_DESC
            char*  EXC_DESC

        parse_record(&self.pRec, recHeader, rawData, binaryLen)
        # U4  FINISH_T
        timeStamp = <time_t>((<MRR*>self.pRec).FINISH_T)
        tmPtr = localtime(&timeStamp)
        strftime(stringBuffer, 26, "%Y-%m-%d %H:%M:%S (UTC)", tmPtr)
        sqlite3_bind_text(self.insertFileInfo_stmt, 1, "FINISH_T", -1, NULL)
        sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
        err = csqlite3_step(self.insertFileInfo_stmt)
        # C1  DISP_COD
        if not err and (<MRR*>self.pRec).DISP_COD != 0x20:    # hex of SPACE
            sprintf(stringBuffer, "%c", (<MRR*>self.pRec).DISP_COD)
            stringBuffer[1] = 0x00
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "DISP_COD", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, stringBuffer, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  USR_DESC
        if not err and (<MRR*>self.pRec).USR_DESC != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "USR_DESC", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MRR*>self.pRec).USR_DESC, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        # Cn  EXC_DESC
        if not err and (<MRR*>self.pRec).EXC_DESC != NULL:
            sqlite3_bind_text(self.insertFileInfo_stmt, 1, "EXC_DESC", -1, NULL)
            sqlite3_bind_text(self.insertFileInfo_stmt, 2, (<MRR*>self.pRec).EXC_DESC, -1, NULL)
            err = csqlite3_step(self.insertFileInfo_stmt)
        
        free_record(recHeader, self.pRec)
        return err    

    
class stdfDataRetriever:
    def __init__(self, filepath, dbPath, QSignal=None, flag=None):
        self.summarizer = stdfSummarizer(QSignal=QSignal, flag=flag, filepath=filepath, dbPath=dbPath)            
