# distutils: language = c
# cython: language_level=3
#
# cstdflib.pxd - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: April 19th 2021
# -----
# Last Modified: Tue Jan 25 2022
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



from libc.stddef cimport size_t
from libc.stdint cimport *


cdef extern from "stdf4_func.h" nogil:

    bint needByteSwap

    void parse_record(void** pRec, uint16_t recHeader, const unsigned char* rawData, uint16_t binaryLen)

    void free_record(uint16_t recHeader, void* record)


cdef extern from "stdf4_func.c" nogil:
    cdef enum:
        REC_FAR
        REC_ATR
        REC_MIR
        REC_MRR
        REC_PCR
        REC_HBR
        REC_SBR
        REC_PMR
        REC_PGR
        REC_PLR
        REC_RDR
        REC_SDR
        REC_WIR
        REC_WRR
        REC_WCR
        REC_PIR
        REC_PRR
        REC_TSR
        REC_PTR
        REC_MPR
        REC_FTR
        REC_BPS
        REC_EPS
        REC_GDR
        REC_DTR

    ctypedef	unsigned char	B1
    ctypedef	char			C1
    ctypedef	uint8_t			U1
    ctypedef	uint16_t		U2
    ctypedef	uint32_t		U4
    ctypedef	int8_t			I1
    ctypedef	int16_t			I2
    ctypedef	int32_t			I4
    ctypedef	float			R4
    ctypedef	double			R8
    ctypedef    char*           Cn

    ctypedef U1              Bn[255]
    ctypedef U1              Dn[8192]

    ctypedef	Cn*				kxCn
    ctypedef	U1*				kxU1
    ctypedef	U2*				kxU2
    ctypedef	R4*				kxR4
    ctypedef	U1*				kxN1

    ctypedef enum V1_type:
        GDR_B0
        GDR_U1
        GDR_U2
        GDR_U4
        GDR_I1
        GDR_I2
        GDR_I4
        GDR_R4
        GDR_R8
        GDR_Cn
        GDR_Bn
        GDR_Dn
        GDR_N1
    
    ctypedef struct V1:
        V1_type		dataType
        U2          byteCnt
        void*		data

    ctypedef    V1*             Vn

    ctypedef struct _FAR:
        U1   CPU_TYPE
        U1   STDF_VER

    ctypedef struct ATR:
        U4   MOD_TIM
        Cn   CMD_LINE

    ctypedef struct MIR:
        U4  SETUP_T
        U4  START_T
        U1  STAT_NUM
        C1  MODE_COD
        C1  RTST_COD
        C1  PROT_COD
        U2  BURN_TIM
        C1  CMOD_COD
        Cn  LOT_ID
        Cn  PART_TYP
        Cn  NODE_NAM
        Cn  TSTR_TYP
        Cn  JOB_NAM
        Cn  JOB_REV
        Cn  SBLOT_ID
        Cn  OPER_NAM
        Cn  EXEC_TYP
        Cn  EXEC_VER
        Cn  TEST_COD
        Cn  TST_TEMP
        Cn  USER_TXT
        Cn  AUX_FILE
        Cn  PKG_TYP
        Cn  FAMLY_ID
        Cn  DATE_COD
        Cn  FACIL_ID
        Cn  FLOOR_ID
        Cn  PROC_ID
        Cn  OPER_FRQ
        Cn  SPEC_NAM
        Cn  SPEC_VER
        Cn  FLOW_ID
        Cn  SETUP_ID
        Cn  DSGN_REV
        Cn  ENG_ID
        Cn  ROM_COD
        Cn  SERL_NUM
        Cn  SUPR_NAM
    
    ctypedef struct MRR:
        U4  FINISH_T
        C1  DISP_COD
        Cn  USR_DESC
        Cn  EXC_DESC
        
    ctypedef struct PCR:
        U1  HEAD_NUM
        U1  SITE_NUM
        U4  PART_CNT
        U4  RTST_CNT
        U4  ABRT_CNT
        U4  GOOD_CNT
        U4  FUNC_CNT

    ctypedef struct HBR:
        U1  HEAD_NUM
        U1  SITE_NUM
        U2  HBIN_NUM
        U4  HBIN_CNT
        C1  HBIN_PF
        Cn  HBIN_NAM
    
    ctypedef struct SBR:
        U1  HEAD_NUM
        U1  SITE_NUM
        U2  SBIN_NUM
        U4  SBIN_CNT
        C1  SBIN_PF
        Cn  SBIN_NAM
    
    ctypedef struct PMR:
        U2  PMR_INDX
        U2  CHAN_TYP
        Cn  CHAN_NAM
        Cn  PHY_NAM
        Cn  LOG_NAM
        U1  HEAD_NUM
        U1  SITE_NUM
    
    ctypedef struct PGR:
        U2      GRP_INDX
        Cn      GRP_NAM
        U2      INDX_CNT
        kxU2    PMR_INDX

    ctypedef struct PLR:
        U2      GRP_CNT
        kxU2    GRP_INDX
        kxU2    GRP_MODE
        kxU1    GRP_RADX
        kxCn    PGM_CHAR
        kxCn    RTN_CHAR
        kxCn    PGM_CHAL
        kxCn    RTN_CHAL

    ctypedef struct RDR:
        U2    NUM_BINS
        kxU2  RTST_BIN

    ctypedef struct SDR:
        U1    HEAD_NUM
        U1    SITE_GRP
        U1    SITE_CNT
        kxU1  SITE_NUM
        Cn    HAND_TYP
        Cn    HAND_ID
        Cn    CARD_TYP
        Cn    CARD_ID
        Cn    LOAD_TYP
        Cn    LOAD_ID
        Cn    DIB_TYP
        Cn    DIB_ID
        Cn    CABL_TYP
        Cn    CABL_ID
        Cn    CONT_TYP
        Cn    CONT_ID
        Cn    LASR_TYP
        Cn    LASR_ID
        Cn    EXTR_TYP
        Cn    EXTR_ID

    ctypedef struct WIR:
        U1  HEAD_NUM
        U1  SITE_GRP
        U4  START_T
        Cn  WAFER_ID
    
    ctypedef struct WRR:
        U1  HEAD_NUM
        U1  SITE_GRP
        U4  FINISH_T
        U4  PART_CNT
        U4  RTST_CNT
        U4  ABRT_CNT
        U4  GOOD_CNT
        U4  FUNC_CNT
        Cn  WAFER_ID
        Cn  FABWF_ID
        Cn  FRAME_ID
        Cn  MASK_ID
        Cn  USR_DESC
        Cn  EXC_DESC
    
    ctypedef struct WCR:
        R4  WAFR_SIZ
        R4  DIE_HT
        R4  DIE_WID
        U1  WF_UNITS
        C1  WF_FLAT
        I2  CENTER_X
        I2  CENTER_Y
        C1  POS_X
        C1  POS_Y
    
    ctypedef struct PIR:
        U1  HEAD_NUM
        U1  SITE_NUM
    
    ctypedef struct PRR:
        U1  HEAD_NUM
        U1  SITE_NUM
        B1  PART_FLG
        U2  NUM_TEST
        U2  HARD_BIN
        U2  SOFT_BIN
        I2  X_COORD
        I2  Y_COORD
        U4  TEST_T
        Cn  PART_ID
        Cn  PART_TXT
        Bn  PART_FIX
    
    ctypedef struct TSR:
        U1  HEAD_NUM
        U1  SITE_NUM
        C1  TEST_TYP
        U4  TEST_NUM
        U4  EXEC_CNT
        U4  FAIL_CNT
        U4  ALRM_CNT
        Cn  TEST_NAM
        Cn  SEQ_NAME
        Cn  TEST_LBL
        B1  OPT_FLAG
        R4  TEST_TIM
        R4  TEST_MIN
        R4  TEST_MAX
        R4  TST_SUMS
        R4  TST_SQRS
    
    ctypedef struct PTR:
        U4 TEST_NUM
        U1 HEAD_NUM
        U1 SITE_NUM
        B1 TEST_FLG
        B1 PARM_FLG
        R4 RESULT
        Cn TEST_TXT
        Cn ALARM_ID
        B1 OPT_FLAG
        I1 RES_SCAL
        I1 LLM_SCAL
        I1 HLM_SCAL
        R4 LO_LIMIT
        R4 HI_LIMIT
        Cn UNITS
        Cn C_RESFMT
        Cn C_LLMFMT
        Cn C_HLMFMT
        R4 LO_SPEC
        R4 HI_SPEC
    
    ctypedef struct MPR:
        U4    TEST_NUM
        U1    HEAD_NUM
        U1    SITE_NUM
        B1    TEST_FLG
        B1    PARM_FLG
        U2    RTN_ICNT
        U2    RSLT_CNT
        kxN1   RTN_STAT
        kxR4   RTN_RSLT
        Cn    TEST_TXT
        Cn    ALARM_ID
        B1    OPT_FLAG
        I1    RES_SCAL
        I1    LLM_SCAL
        I1    HLM_SCAL
        R4    LO_LIMIT
        R4    HI_LIMIT
        R4    START_IN
        R4    INCR_IN
        kxU2   RTN_INDX
        Cn    UNITS
        Cn    UNITS_IN
        Cn    C_RESFMT
        Cn    C_LLMFMT
        Cn    C_HLMFMT
        R4    LO_SPEC
        R4    HI_SPEC
    
    ctypedef struct FTR:
        U4      TEST_NUM
        U1      HEAD_NUM
        U1      SITE_NUM
        B1      TEST_FLG
        B1      OPT_FLAG
        U4      CYCL_CNT
        U4      REL_VADR
        U4      REPT_CNT
        U4      NUM_FAIL
        I4      XFAIL_AD
        I4      YFAIL_AD
        I2      VECT_OFF
        U2      RTN_ICNT
        U2      PGM_ICNT
        kxU2    RTN_INDX
        kxN1    RTN_STAT
        kxU2    PGM_INDX
        kxN1    PGM_STAT
        Dn      FAIL_PIN
        Cn      VECT_NAM
        Cn      TIME_SET
        Cn      OP_CODE
        Cn      TEST_TXT
        Cn      ALARM_ID
        Cn      PROG_TXT
        Cn      RSLT_TXT
        U1      PATG_NUM
        Dn      SPIN_MAP
    
    ctypedef struct BPS:
        Cn  SEQ_NAME

    ctypedef struct EPS
    ctypedef struct GDR:
        U2  FLD_CNT
        Vn  GEN_DATA

    ctypedef struct DTR:
        Cn  TEXT_DAT


cdef extern from "stdf4_io.c" nogil:
    STDERR stdf_open(STDF** sh, void* filename)
    STDERR stdf_close(STDF* sh)


cdef extern from "stdf4_io.h" nogil:
    ctypedef enum STDERR:
        STD_OK
        INVAILD_STDF
        WRONG_VERSION
        OS_FAIL
        NO_MEMORY
        STD_EOF
        TERMINATE

    ctypedef struct stdf_fops:
        int (*stdf_open)(void* stdf, void* filename) nogil
        int (*stdf_read)(void* stdf, void* buf, int length) nogil
        int (*stdf_skip)(void* stdf, int num) nogil
        int (*stdf_close)(void* stdf) nogil

    ctypedef struct STDF:
        stdf_fops*      fops
        pass

    STDERR stdf_open(STDF** sh, void* filename)

    STDERR stdf_reopen(STDF* sh)

    STDERR stdf_close(STDF* sh)


cdef inline uint16_t MAKE_REC(uint8_t typ, uint8_t sub) nogil:
    return typ << 8 | sub


cdef inline void SwapBytes(void* pv, size_t n) nogil:
    # https://stackoverflow.com/a/2182581
    cdef char *p = <char*>pv
    cdef size_t lo = 0, hi = n-1
    cdef char tmp

    while hi > lo:
        tmp = p[lo]
        p[lo] = p[hi]
        p[hi] = tmp
        lo += 1
        hi -= 1



