/*
 * stdf4_Types.h - STDF Viewer
 * 
 * Author: noonchen - chennoon233@foxmail.com
 * Created Date: April 27th 2021
 * -----
 * Last Modified: Mon May 16 2022
 * Modified By: noonchen
 * -----
 * Copyright (c) 2021 noonchen
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */



#include <stdint.h>

#ifndef __STDF_REC_TYPES__
#define __STDF_REC_TYPES__

//REC_TYPE Code
typedef enum {
	REC_TYP_INFO        = 0,   // Information about the STDF file
	REC_TYP_PER_LOT     = 1,   // Data collected on a per lot basis
	REC_TYP_PER_WAFER   = 2,   // Data collected per wafer
	REC_TYP_PER_PART    = 5,   // Data collected on a per part basis
	REC_TYP_PER_TEST    = 10,  // Data collected per test in the test program
	REC_TYP_PER_EXEC    = 15,  // Data collected per test execution
	REC_TYP_PER_PROG    = 20,  // Data collected per program segment
	REC_TYP_GENERIC     = 50,  // Generic Data
	REC_TYP_RESV_IMAGE  = 180, // Reserved for use by Image Software
	REC_TYP_RESV_IG900  = 181, // Reserved for use by IG900 Software
} REC_TYP;

// REC_SUB Code
typedef enum {
	REC_SUB_FAR   = 10, // File Attributes Record
	REC_SUB_ATR   = 20, // Audit Trail Record
    REC_SUB_VUR   = 30, // Version Update Record
	REC_SUB_MIR   = 10, // Master Information Record
	REC_SUB_MRR   = 20, // Master Result Record
	REC_SUB_PCR   = 30, // Part Count Record
	REC_SUB_HBR   = 40, // Hardware Bin Record
	REC_SUB_SBR   = 50, // Software Bin Record
	REC_SUB_PMR   = 60, // Pin Map Record
	REC_SUB_PGR   = 62, // Pin Group Record
	REC_SUB_PLR   = 63, // Pin List Record
	REC_SUB_RDR   = 70, // Reset Data Record
	REC_SUB_SDR   = 80, // Site Description Record
    REC_SUB_PSR   = 90, // Pattern Sequence Record
    REC_SUB_NMR   = 91, // Name Map Record
    REC_SUB_CNR   = 92, // Cell Name Record
    REC_SUB_SSR   = 93, // Scan Structure Record
    REC_SUB_CDR   = 94, // Chain Description Record
	REC_SUB_WIR   = 10, // Wafer Information Record
	REC_SUB_WRR   = 20, // Wafer Result Record
	REC_SUB_WCR   = 30, // Wafer Configuration Record
	REC_SUB_PIR   = 10, // Part Information Record
	REC_SUB_PRR   = 20, // Part Result Record
	REC_SUB_TSR   = 30, // Test Synopsis Record
	REC_SUB_PTR   = 10, // Parametric Test Record
	REC_SUB_MPR   = 15, // Multiple-Result Parametric Record
	REC_SUB_FTR   = 20, // Functional Test Record
    REC_SUB_STR   = 30, // Scan Test Record
	REC_SUB_BPS   = 10, // Begin Program Section Record
	REC_SUB_EPS   = 20, // End Program Section Record
	REC_SUB_GDR   = 10, // Generic Data Record
	REC_SUB_DTR   = 30, // Datalog Text Record
} REC_SUB;


#define REC_FAR (REC_TYP_INFO      <<8 | REC_SUB_FAR)    // FAR
#define REC_ATR (REC_TYP_INFO      <<8 | REC_SUB_ATR)    // ATR
#define REC_ATR (REC_TYP_INFO      <<8 | REC_SUB_VUR)    // VUR
#define REC_MIR (REC_TYP_PER_LOT   <<8 | REC_SUB_MIR)    // MIR
#define REC_MRR (REC_TYP_PER_LOT   <<8 | REC_SUB_MRR)    // MRR
#define REC_PCR (REC_TYP_PER_LOT   <<8 | REC_SUB_PCR)    // PCR
#define REC_HBR (REC_TYP_PER_LOT   <<8 | REC_SUB_HBR)    // HBR
#define REC_SBR (REC_TYP_PER_LOT   <<8 | REC_SUB_SBR)    // SBR
#define REC_PMR (REC_TYP_PER_LOT   <<8 | REC_SUB_PMR)    // PMR
#define REC_PGR (REC_TYP_PER_LOT   <<8 | REC_SUB_PGR)    // PGR
#define REC_PLR (REC_TYP_PER_LOT   <<8 | REC_SUB_PLR)    // PLR
#define REC_RDR (REC_TYP_PER_LOT   <<8 | REC_SUB_RDR)    // RDR
#define REC_SDR (REC_TYP_PER_LOT   <<8 | REC_SUB_SDR)    // SDR
#define REC_SDR (REC_TYP_PER_LOT   <<8 | REC_SUB_PSR)    // PSR
#define REC_SDR (REC_TYP_PER_LOT   <<8 | REC_SUB_NMR)    // NMR
#define REC_SDR (REC_TYP_PER_LOT   <<8 | REC_SUB_CNR)    // CNR
#define REC_SDR (REC_TYP_PER_LOT   <<8 | REC_SUB_SSR)    // SSR
#define REC_SDR (REC_TYP_PER_LOT   <<8 | REC_SUB_CDR)    // CDR
#define REC_WIR (REC_TYP_PER_WAFER <<8 | REC_SUB_WIR)    // WIR
#define REC_WRR (REC_TYP_PER_WAFER <<8 | REC_SUB_WRR)    // WRR
#define REC_WCR (REC_TYP_PER_WAFER <<8 | REC_SUB_WCR)    // WCR
#define REC_PIR (REC_TYP_PER_PART  <<8 | REC_SUB_PIR)    // PIR
#define REC_PRR (REC_TYP_PER_PART  <<8 | REC_SUB_PRR)    // PRR
#define REC_TSR (REC_TYP_PER_TEST  <<8 | REC_SUB_TSR)    // TSR
#define REC_PTR (REC_TYP_PER_EXEC  <<8 | REC_SUB_PTR)    // PTR
#define REC_MPR (REC_TYP_PER_EXEC  <<8 | REC_SUB_MPR)    // MPR
#define REC_FTR (REC_TYP_PER_EXEC  <<8 | REC_SUB_FTR)    // FTR
#define REC_FTR (REC_TYP_PER_EXEC  <<8 | REC_SUB_STR)    // STR
#define REC_BPS (REC_TYP_PER_PROG  <<8 | REC_SUB_BPS)    // BPS
#define REC_EPS (REC_TYP_PER_PROG  <<8 | REC_SUB_EPS)    // EPS
#define REC_GDR (REC_TYP_GENERIC   <<8 | REC_SUB_GDR)    // GDR
#define REC_DTR (REC_TYP_GENERIC   <<8 | REC_SUB_DTR)    // DTR


// Data Types
typedef	unsigned char	B1;
typedef	char			C1;
typedef	uint8_t			U1;
typedef	uint16_t		U2;
typedef	uint32_t		U4;
typedef uint64_t        U8;
typedef	int8_t			I1; 
typedef	int16_t			I2;
typedef	int32_t			I4;
typedef	float			R4;
typedef	double			R8;
// typedef	struct {
// 	U1 	count;
// 	C1 	data[255U];
// } Cn;	//first byte = unsigned count of bytes to follow (maximum of 255 bytes)
typedef char*           Cn;

// Variable length character string, string length is stored in another field
typedef char*           Cf;

// first two bytes = unsigned count of bytes to follow (maximum of 65535 bytes)
typedef char*           Sn;

// typedef	struct {
// 	U1 	count;
// 	U1 	data[255U];
// } Bn;	//First byte = unsigned count of bytes to follow (maximum of 255 bytes)
typedef U1              Bn[255U];

// typedef	struct {
// 	U2 	count;
// 	U1	data[8192];     // 65535 can be stored in 8192 bytes
// } Dn;	//First two bytes = unsigned count of bits to follow (maximum of 65,535 bits)
typedef U1              Dn[8192U];

// typedef	struct {
// 	unsigned bit1:1;
// 	unsigned bit2:1;
// 	unsigned bit3:1;
// 	unsigned bit4:1;
// } N1;	//(Nibble = 4 bits of a byte).First item in low 4 bits, second item in high 4 bits.

typedef	Cn*				kxCn;
typedef Sn*             kxSn;
typedef Cf*             kxCf;
typedef	U1*				kxU1;
typedef	U2*				kxU2;
typedef U4*             kxU4;
typedef void*           kxUf;
typedef U8*             kxU8;
typedef	R4*				kxR4;
typedef	U1*				kxN1;

typedef enum {
	GDR_B0				= 0,
	GDR_U1				= 1,
	GDR_U2				= 2,
	GDR_U4				= 3,
	GDR_I1				= 4,
	GDR_I2				= 5,
	GDR_I4				= 6,
	GDR_R4				= 7,
	GDR_R8				= 8,
	GDR_Cn				= 10,
	GDR_Bn				= 11,
	GDR_Dn				= 12,
	GDR_N1				= 13
} V1_type;

typedef struct {
	V1_type		dataType;
    U2          byteCnt;
	void*		data;
} V1;

typedef	V1*			Vn;


// Record Types

typedef struct _FAR {
    U1   CPU_TYPE;  // CPU type that wrote this file
    U1   STDF_VER;  // STDF version number
} _FAR;

typedef struct ATR {
    U4   MOD_TIM ; //Date and time of STDF file modification
    Cn   CMD_LINE; //Command line of program
} ATR;

typedef struct VUR {
    Cn   UPD_NAM; //Update Version Name
} VUR;

typedef struct MIR {
    U4  SETUP_T  ; // Date and time of job setup
    U4  START_T  ; // Date and time first part tested
    U1  STAT_NUM ; // Tester station number
    C1  MODE_COD ; // Test mode code (e.g. prod, dev)
    C1  RTST_COD ; // Lot retest code
    C1  PROT_COD ; // Data protection code
    U2  BURN_TIM ; // Burn-in time (in minutes)
    C1  CMOD_COD ; // Command mode code
    Cn  LOT_ID   ; // Lot ID (customer specified)
    Cn  PART_TYP ; // Part Type (or product ID)
    Cn  NODE_NAM ; // Name of node that generated data
    Cn  TSTR_TYP ; // Tester type
    Cn  JOB_NAM  ; // Job name (test program name)
    Cn  JOB_REV  ; // Job (test program) revision number
    Cn  SBLOT_ID ; // Sublot ID
    Cn  OPER_NAM ; // Operator name or ID (at setup time)
    Cn  EXEC_TYP ; // Tester executive software type
    Cn  EXEC_VER ; // Tester exec software version number
    Cn  TEST_COD ; // Test phase or step code
    Cn  TST_TEMP ; // Test temperature
    Cn  USER_TXT ; // Generic user text
    Cn  AUX_FILE ; // Name of auxiliary data file
    Cn  PKG_TYP  ; // Package type
    Cn  FAMLY_ID ; // Product family ID
    Cn  DATE_COD ; // Date code
    Cn  FACIL_ID ; // Test facility ID
    Cn  FLOOR_ID ; // Test floor ID
    Cn  PROC_ID  ; // Fabrication process ID
    Cn  OPER_FRQ ; // Operation frequency or step
    Cn  SPEC_NAM ; // Test specification name
    Cn  SPEC_VER ; // Test specification version number
    Cn  FLOW_ID  ; // Test flow ID
    Cn  SETUP_ID ; // Test setup ID
    Cn  DSGN_REV ; // Device design revision
    Cn  ENG_ID   ; // Engineering lot ID
    Cn  ROM_COD  ; // ROM code ID
    Cn  SERL_NUM ; // Tester serial number
    Cn  SUPR_NAM ; // Supervisor name or ID
} MIR;

typedef struct MRR {
    U4  FINISH_T ; // Date and time last part tested
    C1  DISP_COD ; // Lot disposition code,default: space
    Cn  USR_DESC ; // Lot description supplied by user
    Cn  EXC_DESC ; // Lot description supplied by exec
} MRR;

typedef struct PCR {
    U1  HEAD_NUM ; // Test head number
    U1  SITE_NUM ; // Test site number
    U4  PART_CNT ; // Number of parts tested
    U4  RTST_CNT ; // Number of parts retested
    U4  ABRT_CNT ; // Number of aborts during testing
    U4  GOOD_CNT ; // Number of good (passed) parts tested
    U4  FUNC_CNT ; // Number of functional parts tested
} PCR;

typedef struct HBR {
    U1  HEAD_NUM ; // Test head number
    U1  SITE_NUM ; // Test site number
    U2  HBIN_NUM ; // Hardware bin number
    U4  HBIN_CNT ; // Number of parts in bin
    C1  HBIN_PF  ; // Pass/fail indication
    Cn  HBIN_NAM ; // Name of hardware bin
} HBR;

typedef struct SBR {
    U1  HEAD_NUM ; // Test head number
    U1  SITE_NUM ; // Test site number
    U2  SBIN_NUM ; // Software bin number
    U4  SBIN_CNT ; // Number of parts in bin
    C1  SBIN_PF  ; // Pass/fail indication
    Cn  SBIN_NAM ; // Name of software bin
} SBR;

typedef struct PMR {
    U2  PMR_INDX ; // Unique index associated with pin
    U2  CHAN_TYP ; // Channel type
    Cn  CHAN_NAM ; // Channel name
    Cn  PHY_NAM  ; // Physical name of pin
    Cn  LOG_NAM  ; // Logical name of pin
    U1  HEAD_NUM ; // Head number associated with channel
    U1  SITE_NUM ; // Site number associated with channel
} PMR;

typedef struct PGR {
    U2      GRP_INDX ; // Unique index associated with pin group
    Cn      GRP_NAM  ; // Name of pin group
    U2      INDX_CNT ; // Count of PMR indexes
    kxU2    PMR_INDX ; // Array of indexes for pins in the group
} PGR;

typedef struct PLR {
    U2      GRP_CNT  ; // Count (k) of pins or pin groups
    kxU2    GRP_INDX ; // Array of pin or pin group indexes
    kxU2    GRP_MODE ; // Operating mode of pin group
    kxU1    GRP_RADX ; // Display radix of pin group
    kxCn    PGM_CHAR ; // Program state encoding characters
    kxCn    RTN_CHAR ; // Return state encoding characters
    kxCn    PGM_CHAL ; // Program state encoding characters
    kxCn    RTN_CHAL ; // Return state encoding characters
} PLR;

typedef struct RDR {
    U2    NUM_BINS ; // Number (k) of bins being retested
    kxU2 RTST_BIN ; // Array of retest bin numbers
} RDR;

typedef struct SDR {
    U1    HEAD_NUM ; // Test head number
    U1    SITE_GRP ; // Site group number
    U1    SITE_CNT ; // Number (k) of test sites in site group
    kxU1  SITE_NUM ; // Array of test site numbers
    Cn    HAND_TYP ; // Handler or prober type
    Cn    HAND_ID  ; // Handler or prober ID
    Cn    CARD_TYP ; // Probe card type
    Cn    CARD_ID  ; // Probe card ID
    Cn    LOAD_TYP ; // Load board type
    Cn    LOAD_ID  ; // Load board ID
    Cn    DIB_TYP  ; // DIB board type
    Cn    DIB_ID   ; // DIB board ID
    Cn    CABL_TYP ; // Interface cable type
    Cn    CABL_ID  ; // Interface cable ID
    Cn    CONT_TYP ; // Handler contactor type
    Cn    CONT_ID  ; // Handler contactor ID
    Cn    LASR_TYP ; // Laser type
    Cn    LASR_ID  ; // Laser ID
    Cn    EXTR_TYP ; // Extra equipment type field
    Cn    EXTR_ID  ; // Extra equipment ID
} SDR;

typedef struct PSR {
    B1      CONT_FLG ; // Continuation PSR record exist
    U2      PSR_INDX ; // PSR Record Index (used by STR records)
    Cn      PSR_NAM  ; // Symbolic name of PSR record
    B1      OPT_FLG ; // Contains PAT_LBL, FILE_UID, ATPG_DSC, and SRC_ID field missing flag bits and flag for start index for first cycle number.
    U2      TOTP_CNT ; // Count of total pattern file information sets in the complete PSR data set
    U2      LOCP_CNT ; // Count (k) of pattern file information sets in this record
    kxU8    PAT_BGN ; // Array of Cycle #’s patterns begins on
    kxU8    PAT_END ; // Array of Cycle #’s patterns stops at
    kxCn    PAT_FILE ; // Array of Pattern File Names
    kxCn    PAT_LBL ; // Optional pattern symbolic name
    kxCn    FILE_UID ; // Optional array of file identifier code
    kxCn    ATPG_DSC ; // Optional array of ATPG information
    kxCn    SRC_ID ; // Optional array of PatternInSrcFileID
} PSR;

typedef struct NMR {
    B1      CONT_FLG ; // Continuation NMR record follows if not 0
    U2      TOTM_CNT ; // Count of PMR indexes and ATPG_NAM entries
    U2      LOCM_CNT ; // Count of (k) PMR indexes and ATPG_NAM entries in this record
    kxU2    PMR_INDX ; // Array of PMR indexes
    kxCn    ATPG_NAM ; // Array of ATPG signal names
} NMR;

typedef struct CNR {
    U2  CHN_NUM ; // Chain number. Referenced by the CHN_NUM array in an STR record
    U4  BIT_POS ; // Bit position in the chain
    Sn  CELL_NAM ; // Scan Cell Name
} CNR;

typedef struct SSR {
    Cn      SSR_NAM ; // Name of the STIL Scan Structure for reference
    U2      CHN_CNT ; // Count (k) of number of Chains listed in CHN_LIST
    kxU2    CHN_LIST ; // Array of CDR Indexes
} SSR;

typedef struct CDR {
    B1      CONT_FLG ; // Continuation CDR record follows if not 0
    U2      CDR_INDX ; // SCR Index
    Cn      CHN_NAM ; // Chain Name
    U4      CHN_LEN ; // Chain Length (# of scan cells in chain)
    U2      SIN_PIN ; // PMR index of the chain's Scan In Signal
    U2      SOUT_PIN ; // PMR index of the chain's Scan Out Signal
    U1      MSTR_CNT ; // Count (m) of master clock pins specified for this scan chain
    kxU2    M_CLKS ; // Array of PMR indexes for the master clocks assigned to this chain
    U1      SLAV_CNT ; // Count (n) of slave clock pins specified for this scan chain
    kxU2    S_CLKS ; // Array of PMR indexes for the slave clocks assigned to this chain
    U1      INV_VAL ; // 0: No Inversion, 1: Inversion
    U2      LST_CNT ; // Count (k) of scan cells listed in this record
    kxSn    CELL_LST; // Array of Scan Cell Names
} CDR;

typedef struct WIR {
    U1  HEAD_NUM ; // Test head number
    U1  SITE_GRP ; // Site group number 255
    U4  START_T  ; // Date and time first part tested
    Cn  WAFER_ID ; // Wafer ID length byte = 0
} WIR;

typedef struct WRR {
    U1  HEAD_NUM ; // Test head number
    U1  SITE_GRP ; // Site group number
    U4  FINISH_T ; // Date and time last part tested
    U4  PART_CNT ; // Number of parts tested
    U4  RTST_CNT ; // Number of parts retested
    U4  ABRT_CNT ; // Number of aborts during testing
    U4  GOOD_CNT ; // Number of good (passed) parts tested
    U4  FUNC_CNT ; // Number of functional parts tested
    Cn  WAFER_ID ; // Wafer ID
    Cn  FABWF_ID ; // Fab wafer ID
    Cn  FRAME_ID ; // Wafer frame ID
    Cn  MASK_ID  ; // Wafer mask ID
    Cn  USR_DESC ; // Wafer description supplied by user
    Cn  EXC_DESC ; // Wafer description supplied by exec
} WRR;

typedef struct WCR {
    R4  WAFR_SIZ ; // Diameter of wafer in WF_UNITS
    R4  DIE_HT   ; // Height of die in WF_UNITS
    R4  DIE_WID  ; // Width of die in WF_UNITS
    U1  WF_UNITS ; // Units for wafer and die dimensions
    C1  WF_FLAT  ; // Orientation of wafer flat
    I2  CENTER_X ; // X coordinate of center die on wafer
    I2  CENTER_Y ; // Y coordinate of center die on wafer
    C1  POS_X    ; // Positive X direction of wafer
    C1  POS_Y    ; // Positive Y direction of wafer
} WCR;

typedef struct PIR {
    U1  HEAD_NUM ; // Test head number
    U1  SITE_NUM ; // Test site number
} PIR;

typedef struct PRR {
    U1  HEAD_NUM ; //Test head number
    U1  SITE_NUM ; //Test site number
    B1  PART_FLG ; //Part information flag
    U2  NUM_TEST ; //Number of tests executed
    U2  HARD_BIN ; //Hardware bin number
    U2  SOFT_BIN ; //Software bin number
    I2  X_COORD  ; //(Wafer) X coordinate
    I2  Y_COORD  ; //(Wafer) Y coordinate
    U4  TEST_T   ; //Elapsed test time in milliseconds
    Cn  PART_ID  ; //Part identification
    Cn  PART_TXT ; //Part description text
    Bn  PART_FIX ; //Part repair information
} PRR;

typedef struct TSR {
    U1  HEAD_NUM ; // Test head number
    U1  SITE_NUM ; // Test site number
    C1  TEST_TYP ; // Test type
    U4  TEST_NUM ; // Test number
    U4  EXEC_CNT ; // Number of test executions
    U4  FAIL_CNT ; // Number of test failures
    U4  ALRM_CNT ; // Number of alarmed tests
    Cn  TEST_NAM ; // Test name
    Cn  SEQ_NAME ; // Sequencer (program segment/flow) name
    Cn  TEST_LBL ; // Test label or text
    B1  OPT_FLAG ; // Optional data flag
    R4  TEST_TIM ; // Average test execution time in seconds
    R4  TEST_MIN ; // Lowest test result value
    R4  TEST_MAX ; // Highest test result value
    R4  TST_SUMS ; // Sum of test result values
    R4  TST_SQRS ; // Sum of squares of test result values
} TSR;

typedef struct PTR {
    U4  TEST_NUM ; // Test number
    U1  HEAD_NUM ; // Test head number
    U1  SITE_NUM ; // Test site number
    B1  TEST_FLG ; // Test flags (fail, alarm, etc.)
    B1  PARM_FLG ; // Parametric test flags (drift, etc.)
    R4  RESULT   ; // Test result
    Cn  TEST_TXT ; // Test description text or label
    Cn  ALARM_ID ; // Name of alarm
    B1  OPT_FLAG ; // Optional data flag
    I1  RES_SCAL ; // Test results scaling exponent
    I1  LLM_SCAL ; // Low limit scaling exponent
    I1  HLM_SCAL ; // High limit scaling exponent
    R4  LO_LIMIT ; // Low test limit value
    R4  HI_LIMIT ; // High test limit value
    Cn  UNITS    ; // Test units
    Cn  C_RESFMT ; // ANSI C result format string
    Cn  C_LLMFMT ; // ANSI C low limit format string
    Cn  C_HLMFMT ; // ANSI C high limit format string
    R4  LO_SPEC  ; // Low specification limit value
    R4  HI_SPEC  ; // High specification limit value
} PTR;

typedef struct MPR {
    U4    TEST_NUM ; // Test number
    U1    HEAD_NUM ; // Test head number
    U1    SITE_NUM ; // Test site number
    B1    TEST_FLG ; // Test flags (fail, alarm, etc.)
    B1    PARM_FLG ; // Parametric test flags (drift, etc.)
    U2    RTN_ICNT ; // Count of PMR indexes
    U2    RSLT_CNT ; // Count of returned results
    kxN1   RTN_STAT ; // Array of returned states
    kxR4   RTN_RSLT ; // Array of returned results
    Cn    TEST_TXT ; // Descriptive text or label
    Cn    ALARM_ID ; // Name of alarm
    B1    OPT_FLAG ; // Optional data flag
    I1    RES_SCAL ; // Test result scaling exponent
    I1    LLM_SCAL ; // Test low limit scaling exponent
    I1    HLM_SCAL ; // Test high limit scaling exponent
    R4    LO_LIMIT ; // Test low limit value
    R4    HI_LIMIT ; // Test high limit value
    R4    START_IN ; // Starting input value (condition)
    R4    INCR_IN  ; // Increment of input condition
    kxU2   RTN_INDX ; // Array of PMR indexes
    Cn    UNITS    ; // Units of returned results
    Cn    UNITS_IN ; // Input condition units
    Cn    C_RESFMT ; // ANSI C result format string
    Cn    C_LLMFMT ; // ANSI C low limit format string
    Cn    C_HLMFMT ; // ANSI C high limit format string
    R4    LO_SPEC  ; // Low specification limit value
    R4    HI_SPEC  ; // High specification limit value
} MPR;

typedef struct FTR {
    U4      TEST_NUM ; // Test number
    U1      HEAD_NUM ; // Test head number
    U1      SITE_NUM ; // Test site number
    B1      TEST_FLG ; // Test flags (fail, alarm, etc.)
    B1      OPT_FLAG ; // Optional data flag
    U4      CYCL_CNT ; // Cycle count of vector
    U4      REL_VADR ; // Relative vector address
    U4      REPT_CNT ; // Repeat count of vector
    U4      NUM_FAIL ; // Number of pins with 1 or more failures
    I4      XFAIL_AD ; // X logical device failure address
    I4      YFAIL_AD ; // Y logical device failure address
    I2      VECT_OFF ; // Offset from vector of interest
    U2      RTN_ICNT ; // Count j of return data PMR indexes
    U2      PGM_ICNT ; // Count k of programmed state indexes
    kxU2    RTN_INDX ; // Array j of return data PMR indexes
    kxN1    RTN_STAT ; // Array j of returned states
    kxU2    PGM_INDX ; // Array k of programmed state indexes
    kxN1    PGM_STAT ; // Array k of programmed states
    Dn      FAIL_PIN ; // Failing pin bitfield
    Cn      VECT_NAM ; // Vector module pattern name
    Cn      TIME_SET ; // Time set name
    Cn      OP_CODE  ; // Vector Op Code
    Cn      TEST_TXT ; // Descriptive text or label
    Cn      ALARM_ID ; // Name of alarm
    Cn      PROG_TXT ; // Additional programmed information
    Cn      RSLT_TXT ; // Additional result information
    U1      PATG_NUM ; // Pattern generator number
    Dn      SPIN_MAP ; // Bit map of enabled comparators
} FTR;

typedef struct STR {
    B1      CONT_FLG ; // Continuation STR follows if not 0
    U4      TEST_NUM ; // Test number
    U1      HEAD_NUM ; // Test head number
    U1      SITE_NUM ; // Test site number
    U2      PSR_REF ; // PSR Index (Pattern Sequence Record)
    B1      TEST_FLG ; // Test flags (fail, alarm, etc.)
    Cn      LOG_TYP ; // User defined description of datalog
    Cn      TEST_TXT ; // Descriptive text or label
    Cn      ALARM_ID ; // Name of alarm
    Cn      PROG_TXT ; // Additional Programmed information
    Cn      RSLT_TXT ; // Additional result information
    U1      Z_VAL ; // Z Handling Flag
    B1      FMU_FLG ; // MASK_MAP & FAL_MAP field status & Pattern Changed flag
    Dn      MASK_MAP ; // Bit map of Globally Masked Pins
    Dn      FAL_MAP ; // Bit map of failures after buffer full
    U8      CYC_CNT ; // Total cycles executed in test
    U4      TOTF_CNT ; // Total failures (pin x cycle) detected in test execution
    U4      TOTL_CNT ; // Total fails logged across the complete STR data set
    U8      CYC_BASE ; // Cycle offset to apply for the values in the CYCL_NUM array
    U4      BIT_BASE ; // Offset to apply for the values in the BIT_POS array
    U2      COND_CNT ; // Count (g) of Test Conditions and optional data specifications in present record
    U2      LIM_CNT ; // Count (j) of LIM Arrays in present record, 1 for global specification
    U1      CYC_SIZE ; // Size (f) of data (1,2,4, or 8 byes) in CYC_OFST field
    U1      PMR_SIZE ; // Size (f) of data (1 or 2 bytes) in PMR_INDX field
    U1      CHN_SIZE ; // Size (f) of data (1, 2 or 4 bytes) in CHN_NUM field
    U1      PAT_SIZE ; // Size (f) of data (1,2, or 4 bytes) in PAT_NUM field
    U1      BIT_SIZE ; // Size (f) of data (1,2, or 4 bytes) in BIT_POS field
    U1      U1_SIZE ; // Size (f) of data (1,2,4 or 8 bytes) in USR1 field
    U1      U2_SIZE ; // Size (f) of data (1,2,4 or 8 bytes) in USR2 field
    U1      U3_SIZE ; // Size (f) of data (1,2,4 or 8 bytes) in USR3 field
    U1      UTX_SIZE ; // Size (f) of each string entry in USER_TXT array
    U2      CAP_BGN ; // Offset added to BIT_POS value to indicate capture cycles
    kxU2    LIM_INDX ; // Array of PMR indexes that require unique limit specifications
    kxU4    LIM_SPEC ; // Array of fail datalogging limits for the PMRs listed in LIM_INDX
    kxCn    COND_LST ; // Array of test condition (Name=value) pairs
    U2      CYC_CNT ; // Count (k) of entries in CYC_OFST array
    kxUf    CYC_OFST; // Array of cycle numbers relative to CYC_BASE
    U2      PMR_CNT ; // Count (k) of entries in the PMR_INDX array
    kxUf    PMR_INDX ; // Array of PMR Indexes (All Formats)
    U2      CHN_CNT ; // Count (k) of entries in the CHN_NUM array
    kxUf    CHN_NUM ; // Array of Chain No for FF Name Mapping
    U2      EXP_CNT ; // Count (k) of EXP_DATA array entries
    kxU1    EXP_DATA ; // Array of expected vector data
    U2      CAP_CNT ; // Count (k) of CAP_DATA array entries
    kxU1    CAP_DATA ; // Array of captured data
    U2      NEW_CNT ; // Count (k) of NEW_DATA array entries
    kxU1    NEW_DATA ; // Array of new vector data
    U2      PAT_CNT ; // Count (k) of PAT_NUM array entries
    kxUf    PAT_NUM ; // Array of pattern # (Ptn/Chn/Bit format)
    U2      BPOS_CNT ; // Count (k) of BIT_POS array entries
    kxUf    BIT_POS ; // Array of chain bit positions (Ptn/Chn/Bit format)
    U2      USR1_CNT ; // Count (k) of USR1 array entries
    kxUf    USR1 ; // Array of user defined data for each logged fail
    U2      USR2_CNT ; // Count (k) of USR2 array entries
    kxUf    USR2 ; // Array of user defined data for each logged fail
    U2      USR3_CNT ; // Count (k) of USR3 array entries
    kxUf    USR3 ; // Array of user defined data for each logged fail
    U2      TXT_CNT ; // Count (k) of USER_TXT array entries
    kxCf    USER_TXT ; // Array of user defined fixed length strings for each logged fail
} STR;

typedef struct BPS {
    Cn  SEQ_NAME ; // Program section (or sequencer) name length byte = 0
} BPS;

typedef struct EPS {} EPS;

typedef struct GDR {
    U2  FLD_CNT  ; // Count of data fields in record
    Vn  GEN_DATA ; // Data type code and data for one field(Repeat GEN_DATA for each data field)
} GDR;

typedef struct DTR {
    Cn  TEXT_DAT ; // ASCII text string
} DTR;

#endif  // __STDF_REC_TYPES__