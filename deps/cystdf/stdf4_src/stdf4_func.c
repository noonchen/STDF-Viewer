/*
 * stdf4_func.h - STDF Viewer
 * 
 * Author: noonchen - chennoon233@foxmail.com
 * Created Date: May 11th 2021
 * -----
 * Last Modified: Wed Jan 26 2022
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
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include "stdf4_types.h"
#include <stdio.h>


int needByteSwap;

// Swap bytes when endianness mismatched
inline void SwapBytes(void *pv, size_t n)
{
    char *p = pv;
    size_t lo, hi;
    for(lo=0, hi=n-1; hi>lo; lo++, hi--)
    {
        char tmp=p[lo];
        p[lo] = p[hi];
        p[hi] = tmp;
    }
}


// Read data types
void read_B1(B1* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if (*pos < binaryLen) {
        // memcpy(desptr, &rawData[*pos], sizeof(B1));
        *desptr = rawData[*pos];
        (*pos) += sizeof(B1);

    } else {
        *desptr = 0;
        //TODO: may need to advance the position as well, preventing following fields to be parsed
    };
}

void read_C1(C1* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if (*pos < binaryLen) {
        // cannot assign directly, since C1 is signed
        memcpy(desptr, &rawData[*pos], sizeof(C1));
        (*pos) += sizeof(C1);

    } else {
        *desptr = 0;
    };
}

void read_U1(U1* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if (*pos < binaryLen) {
        // memcpy(desptr, &rawData[*pos], sizeof(U1));
        *desptr = rawData[*pos];
        (*pos) += sizeof(U1);

    } else {
        *desptr = 0;
    };
}

void read_U2(U2* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if ((*pos + sizeof(U2)) <= binaryLen) {
        // ensure there are enough bytes for convertion
        memcpy(desptr, &rawData[*pos], sizeof(U2));
        (*pos) += sizeof(U2);

        if (needByteSwap) {
            SwapBytes(desptr, sizeof(U2));
        } 

    } else {
        *desptr = 0;
    };
}

void read_U4(U4* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if ((*pos + sizeof(U4)) <= binaryLen) {
        // ensure there are enough bytes for convertion
        memcpy(desptr, &rawData[*pos], sizeof(U4));
        (*pos) += sizeof(U4);

        if (needByteSwap) {
            SwapBytes(desptr, sizeof(U4));
        } 

    } else {
        *desptr = 0;
    };
}

void read_I1(I1* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if (*pos < binaryLen) {
        memcpy(desptr, &rawData[*pos], sizeof(I1));
        (*pos) += sizeof(I1);

    } else {
        *desptr = 0;
    };
}

void read_I2(I2* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if ((*pos + sizeof(I2)) <= binaryLen) {
        // ensure there are enough bytes for convertion
        memcpy(desptr, &rawData[*pos], sizeof(I2));
        (*pos) += sizeof(I2);

        if (needByteSwap) {
            SwapBytes(desptr, sizeof(I2));
        } 

    } else {
        *desptr = 0;
    };
}

void read_I4(I4* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if ((*pos + sizeof(I4)) <= binaryLen) {
        // ensure there are enough bytes for convertion
        memcpy(desptr, &rawData[*pos], sizeof(I4));
        (*pos) += sizeof(I4);

        if (needByteSwap) {
            SwapBytes(desptr, sizeof(I4));
        } 

    } else {
        *desptr = 0;
    };
}

void read_R4(R4* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if ((*pos + sizeof(R4)) <= binaryLen) {
        // ensure there are enough bytes for convertion
        memcpy(desptr, &rawData[*pos], sizeof(R4));
        (*pos) += sizeof(R4);

        if (needByteSwap) {
            SwapBytes(desptr, sizeof(R4));
        } 

    } else {
        *desptr = 0;
    };
}

void read_R8(R8* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if ((*pos + sizeof(R8)) <= binaryLen) {
        // ensure there are enough bytes for convertion
        memcpy(desptr, &rawData[*pos], sizeof(R8));
        (*pos) += sizeof(R8);

        if (needByteSwap) {
            SwapBytes(desptr, sizeof(R8));
        } 

    } else {
        *desptr = 0;
    };
}

void read_Cn(Cn* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    U1 count = 0;
    if (*pos < binaryLen) {
        // read count
        count = rawData[*pos];
        (*pos) += sizeof(U1);

        if (count) {
            // read string if count is not 0
            *desptr = (Cn)malloc(count+1);
            memcpy(*desptr, &rawData[*pos], count);
            (*desptr)[count] = '\0';
            (*pos) += count;
        } else {
            *desptr = NULL;
        }

    } else {
        // omitted
        *desptr = NULL;
    };
}

void read_Bn(Bn* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos, uint16_t* byteCnt) {
    U1 count = 0;
    // clear contents
    memset(*desptr, 0, sizeof(*desptr));
    
    if (*pos < binaryLen) {
        // read count
        count = rawData[*pos];
        // save count to byteCnt if it's not NULL
        if (byteCnt) { *byteCnt = (uint16_t)count; }
        (*pos) += sizeof(U1);
        if (count) {
            // read string if count is not 0
            memcpy(*desptr, &rawData[*pos], count);
            (*pos) += count;
        }
    }
    else {
        if (byteCnt) { *byteCnt = 0; }
    }
}

void read_Dn(Dn* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos, uint16_t* byteCnt) {
    U2 bitcount = 0;
    U2 bytecount = 0;
    // clear contents
    memset(*desptr, 0, sizeof(*desptr));

    if (*pos + sizeof(U2) <= binaryLen) {
        // read count
        memcpy(&bitcount, &rawData[*pos], sizeof(U2));
        if (needByteSwap) {
            SwapBytes(&bitcount, sizeof(U2));
        }
        (*pos) += sizeof(U2);
        bytecount = (bitcount/8 + bitcount%8);
        // save count to byteCnt if it's not NULL
        if (byteCnt) { *byteCnt = bytecount; }
        
        if (bytecount != 0 && (*pos + bytecount <= binaryLen)) {
            // read data if bytecount is not 0 AND remaining bytes are enough
            memcpy(*desptr, &rawData[*pos], bytecount);
            (*pos) += bytecount;
        }
    }
    else {
        if (byteCnt) { *byteCnt = 0; }
    }
}


void read_kxCn(uint16_t k, kxCn* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if (k == 0) {
        *desptr = NULL;
        
    } else {
        *desptr = (kxCn)malloc(k * sizeof(Cn));   // memory for k pointers to char*
        if (*desptr == NULL) {
            free(*desptr);

        } else {
            int i;
            for (i=0; i<k; i++) {
                // *desptr points to the first char*
                read_Cn(*desptr+i, rawData, binaryLen, pos);
            }
        }
    }
}

void read_kxU1(uint16_t k, kxU1* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if (k == 0) {
        *desptr = NULL;
        
    } else {
        *desptr = (kxU1)malloc(k * sizeof(U1));
        if (*desptr == NULL) {
            free(*desptr);

        } else {
            int i;
            for (i=0; i<k; i++) {
                read_U1(*desptr+i, rawData, binaryLen, pos);
            }
        }
    }
}

void read_kxU2(uint16_t k, kxU2* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if (k == 0) {
        *desptr = NULL;
        
    } else {
        *desptr = (kxU2)malloc(k * sizeof(U2));
        if (*desptr == NULL) {
            free(*desptr);

        } else {
            int i;
            for (i=0; i<k; i++) {
                read_U2(*desptr+i, rawData, binaryLen, pos);
            }
        }
    }
}

void read_kxR4(uint16_t k, kxR4* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if (k == 0) {
        *desptr = NULL;
        
    } else {
        *desptr = (kxR4)malloc(k * sizeof(R4));
        if (*desptr == NULL) {
            free(*desptr);

        } else {
            int i;
            for (i=0; i<k; i++) {
                read_R4(*desptr+i, rawData, binaryLen, pos);
            }
        }
    }
}

void read_kxN1(uint16_t k, kxN1* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if (k == 0) {
        // omitted
        *desptr = NULL;

    } else {
        U2 bytecount = k/2 + k%2;   // k = nibble counts, 1 byte = 2 nibble
        if (*pos + bytecount <= binaryLen) {
            // we use U1 to store 4bits value
            *desptr = (kxN1)malloc(k * sizeof(U1));
            if (*desptr == NULL) {
                free(*desptr);

            } else {
                // read data if count is not 0
                int i;
                uint8_t tmp;
                for (i=0; i<bytecount; i++){
                    // read 1 byte into tmp each iteration
                    memcpy(&tmp, &rawData[*pos], 1);
                    (*pos) += 1;

                    // tmp contans data of k = 2i and k = 2i+1
                    // write lower 4bits into k = 2i
                    *(*desptr + 2*i) = tmp & 0x0F;
                    // before write higher 4bits, we should check if 2i+1 is out of bound
                    if (2*i+1 < k) {
                        *(*desptr + 2*i+1) = (tmp & 0xF0) >> 4;
                    }
                }
            }

        } else {
            // omitted
            *desptr = NULL;
        };
    }
}

void read_V1(V1** desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    if (*desptr == NULL) {
        return;
    } else {
        // read 1 byte as the type code
        if (*pos < binaryLen) {
            (*desptr)->dataType = rawData[*pos];   // force cast byte to V1 type
            (*pos) += 1;
        }
        else {
            (*desptr)->dataType = 0xF;   // 0xF is an invalid data type
        }

        void **pData = &((*desptr)->data);         // pointer to V1's data
        switch ((*desptr)->dataType)
        {   // get pointer to void* data and convert it to corresponding type*
            case GDR_B0: 
                // B0 is for padding only
                *pData = NULL;
                (*desptr)->byteCnt = 0; 
                break;
            case GDR_U1: 
                *pData = malloc(sizeof(U1));
                (*desptr)->byteCnt = 1;
                if (*pData) {read_U1((U1*)(*pData), rawData, binaryLen, pos); }
                break;
            case GDR_U2: 
                *pData = malloc(sizeof(U2));
                (*desptr)->byteCnt = 2;
                if (*pData) {read_U2((U2*)(*pData), rawData, binaryLen, pos); }
                break;
            case GDR_U4: 
                *pData = malloc(sizeof(U4));
                (*desptr)->byteCnt = 4;
                if (*pData) {read_U4((U4*)(*pData), rawData, binaryLen, pos); }
                break;
            case GDR_I1: 
                *pData = malloc(sizeof(I1));
                (*desptr)->byteCnt = 1;
                if (*pData) {read_I1((I1*)(*pData), rawData, binaryLen, pos); }
                break;
            case GDR_I2: 
                *pData = malloc(sizeof(I2));
                (*desptr)->byteCnt = 2;
                if (*pData) {read_I2((I2*)(*pData), rawData, binaryLen, pos); }
                break;
            case GDR_I4: 
                *pData = malloc(sizeof(I4));
                (*desptr)->byteCnt = 4;
                if (*pData) {read_I4((I4*)(*pData), rawData, binaryLen, pos); }
                break;
            case GDR_R4: 
                *pData = malloc(sizeof(R4));
                (*desptr)->byteCnt = 4;
                if (*pData) {read_R4((R4*)(*pData), rawData, binaryLen, pos); }
                break;
            case GDR_R8: 
                *pData = malloc(sizeof(R8));
                (*desptr)->byteCnt = 8;
                if (*pData) {read_R8((R8*)(*pData), rawData, binaryLen, pos); }
                break;
            case GDR_N1: 
                *pData = malloc(sizeof(B1));
                (*desptr)->byteCnt = 1;
                if (*pData) {read_B1((B1*)(*pData), rawData, binaryLen, pos); }
                break;
            // for Bn and Dn, read_Xn require preallocated array, use calloc for initialize memory
            case GDR_Bn: 
                *pData = calloc(255, sizeof(B1));
                if (*pData) {read_Bn((Bn*)(*pData), rawData, binaryLen, pos, &((*desptr)->byteCnt)); }
                break;
            case GDR_Dn: 
                *pData = calloc(8196, sizeof(B1));
                if (*pData) {read_Dn((Dn*)(*pData), rawData, binaryLen, pos, &((*desptr)->byteCnt)); }
                break;
            // for Cn and Dn, require preallocated memory to store the pointer to Cn
            case GDR_Cn:
                // not read byte cnt from read_Cn, for it affects so many func calls
                (*desptr)->byteCnt = 0;
                *pData = malloc(sizeof(Cn));
                if (*pData) {read_Cn((Cn*)(*pData), rawData, binaryLen, pos);} 
                break;
            default: 
                // if *pos > binaryLen, dataType is invalid
                // we must assign NULL to *pData, otherwise segfault will occur when record being freed
                *pData = NULL;
                (*desptr)->byteCnt = 0;
                break;
        }
    }
}

void read_Vn(uint16_t k, Vn* desptr, const unsigned char* rawData, uint16_t binaryLen, uint16_t* pos) {
    *desptr = (Vn)malloc(k * sizeof(V1));
    if (*desptr == NULL) {
        free(*desptr);
    } else {
        int i;
        for (i=0; i<k; i++) {
            V1* pV1 = (*desptr) + i;
            read_V1(&pV1, rawData, binaryLen, pos);
        }
    }
}


// Read records
void parse_FAR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    _FAR* record = (_FAR*)malloc(sizeof(_FAR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U1(&record->CPU_TYPE, rawData, binaryLen, &pos);
    read_U1(&record->STDF_VER, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_ATR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    ATR* record = (ATR*)malloc(sizeof(ATR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U4(&record->MOD_TIM, rawData, binaryLen, &pos);
    read_Cn(&record->CMD_LINE, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_MIR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    MIR* record = (MIR*)malloc(sizeof(MIR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U4(&record->SETUP_T, rawData, binaryLen, &pos);
    read_U4(&record->START_T, rawData, binaryLen, &pos);
    read_U1(&record->STAT_NUM, rawData, binaryLen, &pos);
    read_C1(&record->MODE_COD, rawData, binaryLen, &pos);
    read_C1(&record->RTST_COD, rawData, binaryLen, &pos);
    read_C1(&record->PROT_COD, rawData, binaryLen, &pos);
    read_U2(&record->BURN_TIM, rawData, binaryLen, &pos);
    read_C1(&record->CMOD_COD, rawData, binaryLen, &pos);
    read_Cn(&record->LOT_ID, rawData, binaryLen, &pos);
    read_Cn(&record->PART_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->NODE_NAM, rawData, binaryLen, &pos);
    read_Cn(&record->TSTR_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->JOB_NAM, rawData, binaryLen, &pos);
    read_Cn(&record->JOB_REV, rawData, binaryLen, &pos);
    read_Cn(&record->SBLOT_ID, rawData, binaryLen, &pos);
    read_Cn(&record->OPER_NAM, rawData, binaryLen, &pos);
    read_Cn(&record->EXEC_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->EXEC_VER, rawData, binaryLen, &pos);
    read_Cn(&record->TEST_COD, rawData, binaryLen, &pos);
    read_Cn(&record->TST_TEMP, rawData, binaryLen, &pos);
    read_Cn(&record->USER_TXT, rawData, binaryLen, &pos);
    read_Cn(&record->AUX_FILE, rawData, binaryLen, &pos);
    read_Cn(&record->PKG_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->FAMLY_ID, rawData, binaryLen, &pos);
    read_Cn(&record->DATE_COD, rawData, binaryLen, &pos);
    read_Cn(&record->FACIL_ID, rawData, binaryLen, &pos);
    read_Cn(&record->FLOOR_ID, rawData, binaryLen, &pos);
    read_Cn(&record->PROC_ID, rawData, binaryLen, &pos);
    read_Cn(&record->OPER_FRQ, rawData, binaryLen, &pos);
    read_Cn(&record->SPEC_NAM, rawData, binaryLen, &pos);
    read_Cn(&record->SPEC_VER, rawData, binaryLen, &pos);
    read_Cn(&record->FLOW_ID, rawData, binaryLen, &pos);
    read_Cn(&record->SETUP_ID, rawData, binaryLen, &pos);
    read_Cn(&record->DSGN_REV, rawData, binaryLen, &pos);
    read_Cn(&record->ENG_ID, rawData, binaryLen, &pos);
    read_Cn(&record->ROM_COD, rawData, binaryLen, &pos);
    read_Cn(&record->SERL_NUM, rawData, binaryLen, &pos);
    read_Cn(&record->SUPR_NAM, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_MRR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    MRR* record = (MRR*)malloc(sizeof(MRR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U4(&record->FINISH_T, rawData, binaryLen, &pos);
    read_C1(&record->DISP_COD, rawData, binaryLen, &pos);
    read_Cn(&record->USR_DESC, rawData, binaryLen, &pos);
    read_Cn(&record->EXC_DESC, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_PCR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    PCR* record = (PCR*)malloc(sizeof(PCR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    read_U1(&record->SITE_NUM, rawData, binaryLen, &pos);
    read_U4(&record->PART_CNT, rawData, binaryLen, &pos);
    read_U4(&record->RTST_CNT, rawData, binaryLen, &pos);
    read_U4(&record->ABRT_CNT, rawData, binaryLen, &pos);
    read_U4(&record->GOOD_CNT, rawData, binaryLen, &pos);
    read_U4(&record->FUNC_CNT, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_HBR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    HBR* record = (HBR*)malloc(sizeof(HBR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    read_U1(&record->SITE_NUM, rawData, binaryLen, &pos);
    read_U2(&record->HBIN_NUM, rawData, binaryLen, &pos);
    read_U4(&record->HBIN_CNT, rawData, binaryLen, &pos);
    read_C1(&record->HBIN_PF, rawData, binaryLen, &pos);
    read_Cn(&record->HBIN_NAM, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_SBR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    SBR* record = (SBR*)malloc(sizeof(SBR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    read_U1(&record->SITE_NUM, rawData, binaryLen, &pos);
    read_U2(&record->SBIN_NUM, rawData, binaryLen, &pos);
    read_U4(&record->SBIN_CNT, rawData, binaryLen, &pos);
    read_C1(&record->SBIN_PF, rawData, binaryLen, &pos);
    read_Cn(&record->SBIN_NAM, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_PMR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    PMR* record = (PMR*)malloc(sizeof(PMR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U2(&record->PMR_INDX, rawData, binaryLen, &pos);
    read_U2(&record->CHAN_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->CHAN_NAM, rawData, binaryLen, &pos);
    read_Cn(&record->PHY_NAM, rawData, binaryLen, &pos);
    read_Cn(&record->LOG_NAM, rawData, binaryLen, &pos);
    // default value for head & site is 1
    if (pos < binaryLen) {
        read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    } else {
        record->HEAD_NUM = 1;
    }
    if (pos < binaryLen) {
        read_U1(&record->SITE_NUM, rawData, binaryLen, &pos);
    } else {
        record->SITE_NUM = 1;
    }

    *pRec = record;
}

void parse_PGR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    PGR* record = (PGR*)malloc(sizeof(PGR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U2(&record->GRP_INDX, rawData, binaryLen, &pos);
    read_Cn(&record->GRP_NAM, rawData, binaryLen, &pos);
    read_U2(&record->INDX_CNT, rawData, binaryLen, &pos);
    read_kxU2(record->INDX_CNT, &record->PMR_INDX, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_PLR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    PLR* record = (PLR*)malloc(sizeof(PLR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U2(&record->GRP_CNT, rawData, binaryLen, &pos);
    read_kxU2(record->GRP_CNT, &record->GRP_INDX, rawData, binaryLen, &pos);
    read_kxU2(record->GRP_CNT, &record->GRP_MODE, rawData, binaryLen, &pos);
    read_kxU1(record->GRP_CNT, &record->GRP_RADX, rawData, binaryLen, &pos);
    read_kxCn(record->GRP_CNT, &record->PGM_CHAR, rawData, binaryLen, &pos);
    read_kxCn(record->GRP_CNT, &record->RTN_CHAR, rawData, binaryLen, &pos);
    read_kxCn(record->GRP_CNT, &record->PGM_CHAL, rawData, binaryLen, &pos);
    read_kxCn(record->GRP_CNT, &record->RTN_CHAL, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_RDR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    RDR* record = (RDR*)malloc(sizeof(RDR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U2(&record->NUM_BINS, rawData, binaryLen, &pos);
    read_kxU2(record->NUM_BINS, &record->RTST_BIN, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_SDR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    SDR* record = (SDR*)malloc(sizeof(SDR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    read_U1(&record->SITE_GRP, rawData, binaryLen, &pos);
    read_U1(&record->SITE_CNT, rawData, binaryLen, &pos);
    read_kxU1(record->SITE_CNT, &record->SITE_NUM, rawData, binaryLen, &pos);
    read_Cn(&record->HAND_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->HAND_ID, rawData, binaryLen, &pos);
    read_Cn(&record->CARD_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->CARD_ID, rawData, binaryLen, &pos);
    read_Cn(&record->LOAD_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->LOAD_ID, rawData, binaryLen, &pos);
    read_Cn(&record->DIB_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->DIB_ID, rawData, binaryLen, &pos);
    read_Cn(&record->CABL_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->CABL_ID, rawData, binaryLen, &pos);
    read_Cn(&record->CONT_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->CONT_ID, rawData, binaryLen, &pos);
    read_Cn(&record->LASR_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->LASR_ID, rawData, binaryLen, &pos);
    read_Cn(&record->EXTR_TYP, rawData, binaryLen, &pos);
    read_Cn(&record->EXTR_ID, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_WIR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    WIR* record = (WIR*)malloc(sizeof(WIR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    read_U1(&record->SITE_GRP, rawData, binaryLen, &pos);
    read_U4(&record->START_T, rawData, binaryLen, &pos);
    read_Cn(&record->WAFER_ID, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_WRR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    WRR* record = (WRR*)malloc(sizeof(WRR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    read_U1(&record->SITE_GRP, rawData, binaryLen, &pos);
    read_U4(&record->FINISH_T, rawData, binaryLen, &pos);
    read_U4(&record->PART_CNT, rawData, binaryLen, &pos);
    read_U4(&record->RTST_CNT, rawData, binaryLen, &pos);
    read_U4(&record->ABRT_CNT, rawData, binaryLen, &pos);
    read_U4(&record->GOOD_CNT, rawData, binaryLen, &pos);
    read_U4(&record->FUNC_CNT, rawData, binaryLen, &pos);
    read_Cn(&record->WAFER_ID, rawData, binaryLen, &pos);
    read_Cn(&record->FABWF_ID, rawData, binaryLen, &pos);
    read_Cn(&record->FRAME_ID, rawData, binaryLen, &pos);
    read_Cn(&record->MASK_ID, rawData, binaryLen, &pos);
    read_Cn(&record->USR_DESC, rawData, binaryLen, &pos);
    read_Cn(&record->EXC_DESC, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_WCR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    WCR* record = (WCR*)malloc(sizeof(WCR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_R4(&record->WAFR_SIZ, rawData, binaryLen, &pos);
    read_R4(&record->DIE_HT, rawData, binaryLen, &pos);
    read_R4(&record->DIE_WID, rawData, binaryLen, &pos);
    read_U1(&record->WF_UNITS, rawData, binaryLen, &pos);
    read_C1(&record->WF_FLAT, rawData, binaryLen, &pos);
    read_I2(&record->CENTER_X, rawData, binaryLen, &pos);
    read_I2(&record->CENTER_Y, rawData, binaryLen, &pos);
    read_C1(&record->POS_X, rawData, binaryLen, &pos);
    read_C1(&record->POS_Y, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_PIR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    PIR* record = (PIR*)malloc(sizeof(PIR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    read_U1(&record->SITE_NUM, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_PRR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    PRR* record = (PRR*)malloc(sizeof(PRR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    read_U1(&record->SITE_NUM, rawData, binaryLen, &pos);
    read_B1(&record->PART_FLG, rawData, binaryLen, &pos);
    read_U2(&record->NUM_TEST, rawData, binaryLen, &pos);
    read_U2(&record->HARD_BIN, rawData, binaryLen, &pos);
    read_U2(&record->SOFT_BIN, rawData, binaryLen, &pos);
    read_I2(&record->X_COORD, rawData, binaryLen, &pos);
    read_I2(&record->Y_COORD, rawData, binaryLen, &pos);
    read_U4(&record->TEST_T, rawData, binaryLen, &pos);
    read_Cn(&record->PART_ID, rawData, binaryLen, &pos);
    read_Cn(&record->PART_TXT, rawData, binaryLen, &pos);
    read_Bn(&record->PART_FIX, rawData, binaryLen, &pos, NULL);

    *pRec = record;
}

void parse_TSR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    TSR* record = (TSR*)malloc(sizeof(TSR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    read_U1(&record->SITE_NUM, rawData, binaryLen, &pos);
    read_C1(&record->TEST_TYP, rawData, binaryLen, &pos);
    read_U4(&record->TEST_NUM, rawData, binaryLen, &pos);
    read_U4(&record->EXEC_CNT, rawData, binaryLen, &pos);
    read_U4(&record->FAIL_CNT, rawData, binaryLen, &pos);
    read_U4(&record->ALRM_CNT, rawData, binaryLen, &pos);
    read_Cn(&record->TEST_NAM, rawData, binaryLen, &pos);
    read_Cn(&record->SEQ_NAME, rawData, binaryLen, &pos);
    read_Cn(&record->TEST_LBL, rawData, binaryLen, &pos);
    read_B1(&record->OPT_FLAG, rawData, binaryLen, &pos);
    read_R4(&record->TEST_TIM, rawData, binaryLen, &pos);
    read_R4(&record->TEST_MIN, rawData, binaryLen, &pos);
    read_R4(&record->TEST_MAX, rawData, binaryLen, &pos);
    read_R4(&record->TST_SUMS, rawData, binaryLen, &pos);
    read_R4(&record->TST_SQRS, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_PTR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    PTR* record = (PTR*)malloc(sizeof(PTR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U4(&record->TEST_NUM, rawData, binaryLen, &pos);
    read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    read_U1(&record->SITE_NUM, rawData, binaryLen, &pos);
    read_B1(&record->TEST_FLG, rawData, binaryLen, &pos);
    read_B1(&record->PARM_FLG, rawData, binaryLen, &pos);
    read_R4(&record->RESULT, rawData, binaryLen, &pos);
    read_Cn(&record->TEST_TXT, rawData, binaryLen, &pos);
    read_Cn(&record->ALARM_ID, rawData, binaryLen, &pos);
    read_B1(&record->OPT_FLAG, rawData, binaryLen, &pos);
    read_I1(&record->RES_SCAL, rawData, binaryLen, &pos);
    read_I1(&record->LLM_SCAL, rawData, binaryLen, &pos);
    read_I1(&record->HLM_SCAL, rawData, binaryLen, &pos);
    read_R4(&record->LO_LIMIT, rawData, binaryLen, &pos);
    read_R4(&record->HI_LIMIT, rawData, binaryLen, &pos);
    read_Cn(&record->UNITS, rawData, binaryLen, &pos);
    read_Cn(&record->C_RESFMT, rawData, binaryLen, &pos);
    read_Cn(&record->C_LLMFMT, rawData, binaryLen, &pos);
    read_Cn(&record->C_HLMFMT, rawData, binaryLen, &pos);
    read_R4(&record->LO_SPEC, rawData, binaryLen, &pos);
    read_R4(&record->HI_SPEC, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_MPR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    MPR* record = (MPR*)malloc(sizeof(MPR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U4(&record->TEST_NUM, rawData, binaryLen, &pos);
    read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    read_U1(&record->SITE_NUM, rawData, binaryLen, &pos);
    read_B1(&record->TEST_FLG, rawData, binaryLen, &pos);
    read_B1(&record->PARM_FLG, rawData, binaryLen, &pos);
    read_U2(&record->RTN_ICNT, rawData, binaryLen, &pos);
    read_U2(&record->RSLT_CNT, rawData, binaryLen, &pos);
    read_kxN1(record->RTN_ICNT, &record->RTN_STAT, rawData, binaryLen, &pos);
    read_kxR4(record->RSLT_CNT, &record->RTN_RSLT, rawData, binaryLen, &pos);
    read_Cn(&record->TEST_TXT, rawData, binaryLen, &pos);
    read_Cn(&record->ALARM_ID, rawData, binaryLen, &pos);
    read_B1(&record->OPT_FLAG, rawData, binaryLen, &pos);
    read_I1(&record->RES_SCAL, rawData, binaryLen, &pos);
    read_I1(&record->LLM_SCAL, rawData, binaryLen, &pos);
    read_I1(&record->HLM_SCAL, rawData, binaryLen, &pos);
    read_R4(&record->LO_LIMIT, rawData, binaryLen, &pos);
    read_R4(&record->HI_LIMIT, rawData, binaryLen, &pos);
    read_R4(&record->START_IN, rawData, binaryLen, &pos);
    read_R4(&record->INCR_IN, rawData, binaryLen, &pos);
    read_kxU2(record->RTN_ICNT, &record->RTN_INDX, rawData, binaryLen, &pos);
    read_Cn(&record->UNITS, rawData, binaryLen, &pos);
    read_Cn(&record->UNITS_IN, rawData, binaryLen, &pos);
    read_Cn(&record->C_RESFMT, rawData, binaryLen, &pos);
    read_Cn(&record->C_LLMFMT, rawData, binaryLen, &pos);
    read_Cn(&record->C_HLMFMT, rawData, binaryLen, &pos);
    read_R4(&record->LO_SPEC, rawData, binaryLen, &pos);
    read_R4(&record->HI_SPEC, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_FTR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    FTR* record = (FTR*)malloc(sizeof(FTR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_U4(&record->TEST_NUM, rawData, binaryLen, &pos);
    read_U1(&record->HEAD_NUM, rawData, binaryLen, &pos);
    read_U1(&record->SITE_NUM, rawData, binaryLen, &pos);
    read_B1(&record->TEST_FLG, rawData, binaryLen, &pos);
    read_B1(&record->OPT_FLAG, rawData, binaryLen, &pos);
    read_U4(&record->CYCL_CNT, rawData, binaryLen, &pos);
    read_U4(&record->REL_VADR, rawData, binaryLen, &pos);
    read_U4(&record->REPT_CNT, rawData, binaryLen, &pos);
    read_U4(&record->NUM_FAIL, rawData, binaryLen, &pos);
    read_I4(&record->XFAIL_AD, rawData, binaryLen, &pos);
    read_I4(&record->YFAIL_AD, rawData, binaryLen, &pos);
    read_I2(&record->VECT_OFF, rawData, binaryLen, &pos);
    read_U2(&record->RTN_ICNT, rawData, binaryLen, &pos);
    read_U2(&record->PGM_ICNT, rawData, binaryLen, &pos);
    read_kxU2(record->RTN_ICNT, &record->RTN_INDX, rawData, binaryLen, &pos);
    read_kxN1(record->RTN_ICNT, &record->RTN_STAT, rawData, binaryLen, &pos);
    read_kxU2(record->PGM_ICNT, &record->PGM_INDX, rawData, binaryLen, &pos);
    read_kxN1(record->PGM_ICNT, &record->PGM_STAT, rawData, binaryLen, &pos);
    read_Dn(&record->FAIL_PIN, rawData, binaryLen, &pos, NULL);
    read_Cn(&record->VECT_NAM, rawData, binaryLen, &pos);
    read_Cn(&record->TIME_SET, rawData, binaryLen, &pos);
    read_Cn(&record->OP_CODE, rawData, binaryLen, &pos);
    read_Cn(&record->TEST_TXT, rawData, binaryLen, &pos);
    read_Cn(&record->ALARM_ID, rawData, binaryLen, &pos);
    read_Cn(&record->PROG_TXT, rawData, binaryLen, &pos);
    read_Cn(&record->RSLT_TXT, rawData, binaryLen, &pos);
    read_U1(&record->PATG_NUM, rawData, binaryLen, &pos);
    read_Dn(&record->SPIN_MAP, rawData, binaryLen, &pos, NULL);

    *pRec = record;
}

void parse_BPS(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    BPS* record = (BPS*)malloc(sizeof(BPS));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_Cn(&record->SEQ_NAME, rawData, binaryLen, &pos);

    *pRec = record;
}

void parse_EPS(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {

    *pRec = NULL;
}

void parse_GDR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    GDR* record = (GDR*)malloc(sizeof(GDR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;
    read_U2(&record->FLD_CNT, rawData, binaryLen, &pos);
    read_Vn(record->FLD_CNT, &record->GEN_DATA, rawData, binaryLen, &pos);
    *pRec = record;
}

void parse_DTR(void** pRec, const unsigned char* rawData, uint16_t binaryLen) {
    DTR* record = (DTR*)malloc(sizeof(DTR));
    if (record == NULL) {
        free(record);
        *pRec = NULL;
        return;
    }
    uint16_t pos = 0;

    read_Cn(&record->TEXT_DAT, rawData, binaryLen, &pos);

    *pRec = record;
}



void parse_record(void** pRec, uint16_t recHeader, const unsigned char* rawData, uint16_t binaryLen){
    switch (recHeader) {
        case REC_FAR: parse_FAR(pRec, rawData, binaryLen); break;
        case REC_ATR: parse_ATR(pRec, rawData, binaryLen); break;
        case REC_MIR: parse_MIR(pRec, rawData, binaryLen); break;
        case REC_MRR: parse_MRR(pRec, rawData, binaryLen); break;
        case REC_PCR: parse_PCR(pRec, rawData, binaryLen); break;
        case REC_HBR: parse_HBR(pRec, rawData, binaryLen); break;
        case REC_SBR: parse_SBR(pRec, rawData, binaryLen); break;
        case REC_PMR: parse_PMR(pRec, rawData, binaryLen); break;
        case REC_PGR: parse_PGR(pRec, rawData, binaryLen); break;
        case REC_PLR: parse_PLR(pRec, rawData, binaryLen); break;
        case REC_RDR: parse_RDR(pRec, rawData, binaryLen); break;
        case REC_SDR: parse_SDR(pRec, rawData, binaryLen); break;
        case REC_WIR: parse_WIR(pRec, rawData, binaryLen); break;
        case REC_WRR: parse_WRR(pRec, rawData, binaryLen); break;
        case REC_WCR: parse_WCR(pRec, rawData, binaryLen); break;
        case REC_PIR: parse_PIR(pRec, rawData, binaryLen); break;
        case REC_PRR: parse_PRR(pRec, rawData, binaryLen); break;
        case REC_TSR: parse_TSR(pRec, rawData, binaryLen); break;
        case REC_PTR: parse_PTR(pRec, rawData, binaryLen); break;
        case REC_MPR: parse_MPR(pRec, rawData, binaryLen); break;
        case REC_FTR: parse_FTR(pRec, rawData, binaryLen); break;
        case REC_BPS: parse_BPS(pRec, rawData, binaryLen); break;
        case REC_EPS: parse_EPS(pRec, rawData, binaryLen); break;
        case REC_GDR: parse_GDR(pRec, rawData, binaryLen); break;
        case REC_DTR: parse_DTR(pRec, rawData, binaryLen); break;
        default: pRec=NULL; break;
    }
}


// Free records
void free_FAR(_FAR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->CPU_TYPE);
    // free(record->STDF_VER);
    free(record);
}

void free_ATR(ATR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->MOD_TIM);
    free(record->CMD_LINE);
    free(record);
}

void free_MIR(MIR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->SETUP_T);
    // free(record->START_T);
    // free(record->STAT_NUM);
    // free(record->MODE_COD);
    // free(record->RTST_COD);
    // free(record->PROT_COD);
    // free(record->BURN_TIM);
    // free(record->CMOD_COD);
    free(record->LOT_ID);
    free(record->PART_TYP);
    free(record->NODE_NAM);
    free(record->TSTR_TYP);
    free(record->JOB_NAM);
    free(record->JOB_REV);
    free(record->SBLOT_ID);
    free(record->OPER_NAM);
    free(record->EXEC_TYP);
    free(record->EXEC_VER);
    free(record->TEST_COD);
    free(record->TST_TEMP);
    free(record->USER_TXT);
    free(record->AUX_FILE);
    free(record->PKG_TYP);
    free(record->FAMLY_ID);
    free(record->DATE_COD);
    free(record->FACIL_ID);
    free(record->FLOOR_ID);
    free(record->PROC_ID);
    free(record->OPER_FRQ);
    free(record->SPEC_NAM);
    free(record->SPEC_VER);
    free(record->FLOW_ID);
    free(record->SETUP_ID);
    free(record->DSGN_REV);
    free(record->ENG_ID);
    free(record->ROM_COD);
    free(record->SERL_NUM);
    free(record->SUPR_NAM);
    free(record);
}

void free_MRR(MRR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->FINISH_T);
    // free(record->DISP_COD);
    free(record->USR_DESC);
    free(record->EXC_DESC);
    free(record);
}

void free_PCR(PCR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->HEAD_NUM);
    // free(record->SITE_NUM);
    // free(record->PART_CNT);
    // free(record->RTST_CNT);
    // free(record->ABRT_CNT);
    // free(record->GOOD_CNT);
    // free(record->FUNC_CNT);
    free(record);
}

void free_HBR(HBR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->HEAD_NUM);
    // free(record->SITE_NUM);
    // free(record->HBIN_NUM);
    // free(record->HBIN_CNT);
    // free(record->HBIN_PF);
    free(record->HBIN_NAM);
    free(record);
}

void free_SBR(SBR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->HEAD_NUM);
    // free(record->SITE_NUM);
    // free(record->SBIN_NUM);
    // free(record->SBIN_CNT);
    // free(record->SBIN_PF);
    free(record->SBIN_NAM);
    free(record);
}

void free_PMR(PMR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->PMR_INDX);
    // free(record->CHAN_TYP);
    free(record->CHAN_NAM);
    free(record->PHY_NAM);
    free(record->LOG_NAM);
    // free(record->HEAD_NUM);
    // free(record->SITE_NUM);
    free(record);
}

void free_PGR(PGR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->GRP_INDX);
    free(record->GRP_NAM);
    // free(record->INDX_CNT);
    free(record->PMR_INDX);
    free(record);
}

void free_PLR(PLR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->GRP_CNT);
    free(record->GRP_INDX);
    free(record->GRP_MODE);
    free(record->GRP_RADX);
    int i;
    for (i=0; i<(record->GRP_CNT); i++) {
        free(*(record->PGM_CHAR+i));    // *(record->PGM_CHAR+i) points to the ith char*
        free(*(record->RTN_CHAR+i));
        free(*(record->PGM_CHAL+i));
        free(*(record->RTN_CHAL+i));
    }
    free(record->PGM_CHAR);
    free(record->RTN_CHAR);
    free(record->PGM_CHAL);
    free(record->RTN_CHAL);
    free(record);
}

void free_RDR(RDR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->NUM_BINS);
    free(record->RTST_BIN);
    free(record);
}

void free_SDR(SDR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->HEAD_NUM);
    // free(record->SITE_GRP);
    // free(record->SITE_CNT);
    free(record->SITE_NUM);
    free(record->HAND_TYP);
    free(record->HAND_ID);
    free(record->CARD_TYP);
    free(record->CARD_ID);
    free(record->LOAD_TYP);
    free(record->LOAD_ID);
    free(record->DIB_TYP);
    free(record->DIB_ID);
    free(record->CABL_TYP);
    free(record->CABL_ID);
    free(record->CONT_TYP);
    free(record->CONT_ID);
    free(record->LASR_TYP);
    free(record->LASR_ID);
    free(record->EXTR_TYP);
    free(record->EXTR_ID);
    free(record);
}

void free_WIR(WIR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->HEAD_NUM);
    // free(record->SITE_GRP);
    // free(record->START_T);
    free(record->WAFER_ID);
    free(record);
}

void free_WRR(WRR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->HEAD_NUM);
    // free(record->SITE_GRP);
    // free(record->FINISH_T);
    // free(record->PART_CNT);
    // free(record->RTST_CNT);
    // free(record->ABRT_CNT);
    // free(record->GOOD_CNT);
    // free(record->FUNC_CNT);
    free(record->WAFER_ID);
    free(record->FABWF_ID);
    free(record->FRAME_ID);
    free(record->MASK_ID);
    free(record->USR_DESC);
    free(record->EXC_DESC);
    free(record);
}

void free_WCR(WCR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->WAFR_SIZ);
    // free(record->DIE_HT);
    // free(record->DIE_WID);
    // free(record->WF_UNITS);
    // free(record->WF_FLAT);
    // free(record->CENTER_X);
    // free(record->CENTER_Y);
    // free(record->POS_X);
    // free(record->POS_Y);
    free(record);
}

void free_PIR(PIR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->HEAD_NUM);
    // free(record->SITE_NUM);
    free(record);
}

void free_PRR(PRR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->HEAD_NUM);
    // free(record->SITE_NUM);
    // free(record->PART_FLG);
    // free(record->NUM_TEST);
    // free(record->HARD_BIN);
    // free(record->SOFT_BIN);
    // free(record->X_COORD);
    // free(record->Y_COORD);
    // free(record->TEST_T);
    free(record->PART_ID);
    free(record->PART_TXT);
    // free(record->PART_FIX);
    free(record);
}

void free_TSR(TSR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->HEAD_NUM);
    // free(record->SITE_NUM);
    // free(record->TEST_TYP);
    // free(record->TEST_NUM);
    // free(record->EXEC_CNT);
    // free(record->FAIL_CNT);
    // free(record->ALRM_CNT);
    free(record->TEST_NAM);
    free(record->SEQ_NAME);
    free(record->TEST_LBL);
    // free(record->OPT_FLAG);
    // free(record->TEST_TIM);
    // free(record->TEST_MIN);
    // free(record->TEST_MAX);
    // free(record->TST_SUMS);
    // free(record->TST_SQRS);
    free(record);
}

void free_PTR(PTR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->TEST_NUM);
    // free(record->HEAD_NUM);
    // free(record->SITE_NUM);
    // free(record->TEST_FLG);
    // free(record->PARM_FLG);
    // free(record->RESULT);
    free(record->TEST_TXT);
    free(record->ALARM_ID);
    // free(record->OPT_FLAG);
    // free(record->RES_SCAL);
    // free(record->LLM_SCAL);
    // free(record->HLM_SCAL);
    // free(record->LO_LIMIT);
    // free(record->HI_LIMIT);
    free(record->UNITS);
    free(record->C_RESFMT);
    free(record->C_LLMFMT);
    free(record->C_HLMFMT);
    // free(record->LO_SPEC);
    // free(record->HI_SPEC);
    free(record);
}

void free_MPR(MPR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->TEST_NUM);
    // free(record->HEAD_NUM);
    // free(record->SITE_NUM);
    // free(record->TEST_FLG);
    // free(record->PARM_FLG);
    // free(record->RTN_ICNT);
    // free(record->RSLT_CNT);
    free(record->RTN_STAT);
    free(record->RTN_RSLT);
    free(record->TEST_TXT);
    free(record->ALARM_ID);
    // free(record->OPT_FLAG);
    // free(record->RES_SCAL);
    // free(record->LLM_SCAL);
    // free(record->HLM_SCAL);
    // free(record->LO_LIMIT);
    // free(record->HI_LIMIT);
    // free(record->START_IN);
    // free(record->INCR_IN);
    free(record->RTN_INDX);
    free(record->UNITS);
    free(record->UNITS_IN);
    free(record->C_RESFMT);
    free(record->C_LLMFMT);
    free(record->C_HLMFMT);
    // free(record->LO_SPEC);
    // free(record->HI_SPEC);
    free(record);
}

void free_FTR(FTR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->TEST_NUM);
    // free(record->HEAD_NUM);
    // free(record->SITE_NUM);
    // free(record->TEST_FLG);
    // free(record->OPT_FLAG);
    // free(record->CYCL_CNT);
    // free(record->REL_VADR);
    // free(record->REPT_CNT);
    // free(record->NUM_FAIL);
    // free(record->XFAIL_AD);
    // free(record->YFAIL_AD);
    // free(record->VECT_OFF);
    // free(record->RTN_ICNT);
    // free(record->PGM_ICNT);
    free(record->RTN_INDX);
    free(record->RTN_STAT);
    free(record->PGM_INDX);
    free(record->PGM_STAT);
    // free(record->FAIL_PIN);
    free(record->VECT_NAM);
    free(record->TIME_SET);
    free(record->OP_CODE);
    free(record->TEST_TXT);
    free(record->ALARM_ID);
    free(record->PROG_TXT);
    free(record->RSLT_TXT);
    // free(record->PATG_NUM);
    // free(record->SPIN_MAP);
    free(record);
}

void free_BPS(BPS* record) {
    if (record == NULL) {
        return;
    }
    free(record->SEQ_NAME);
    free(record);
}

void free_EPS(EPS* record) {
    return;
}

void free_GDR(GDR* record) {
    if (record == NULL) {
        return;
    }
    // free(record->FLD_CNT);
    int i;
    if (record->GEN_DATA) {
        for (i=0; i<(record->FLD_CNT); i++) {
            // (record->GEN_DATA)+i  pointer to i-th V1
            void* pData = ((record->GEN_DATA)+i)->data;
            if ( ((record->GEN_DATA)+i)->dataType == GDR_Cn ) {
                // free Cn
                if (pData) {
                    Cn CnString = *((Cn*)pData);
                    free(CnString);
                }
                free(pData);
            }
            else {
                free(pData);
            }
        }
    }
    free(record->GEN_DATA);
    free(record);
}

void free_DTR(DTR* record) {
    if (record == NULL) {
        return;
    }
    free(record->TEXT_DAT);
    free(record);
}


void free_record(uint16_t recHeader, void* record){
    switch (recHeader) {
        case REC_FAR: free_FAR((_FAR*)record); break;
        case REC_ATR: free_ATR((ATR*)record); break;
        case REC_MIR: free_MIR((MIR*)record); break;
        case REC_MRR: free_MRR((MRR*)record); break;
        case REC_PCR: free_PCR((PCR*)record); break;
        case REC_HBR: free_HBR((HBR*)record); break;
        case REC_SBR: free_SBR((SBR*)record); break;
        case REC_PMR: free_PMR((PMR*)record); break;
        case REC_PGR: free_PGR((PGR*)record); break;
        case REC_PLR: free_PLR((PLR*)record); break;
        case REC_RDR: free_RDR((RDR*)record); break;
        case REC_SDR: free_SDR((SDR*)record); break;
        case REC_WIR: free_WIR((WIR*)record); break;
        case REC_WRR: free_WRR((WRR*)record); break;
        case REC_WCR: free_WCR((WCR*)record); break;
        case REC_PIR: free_PIR((PIR*)record); break;
        case REC_PRR: free_PRR((PRR*)record); break;
        case REC_TSR: free_TSR((TSR*)record); break;
        case REC_PTR: free_PTR((PTR*)record); break;
        case REC_MPR: free_MPR((MPR*)record); break;
        case REC_FTR: free_FTR((FTR*)record); break;
        case REC_BPS: free_BPS((BPS*)record); break;
        case REC_EPS: free_EPS((EPS*)record); break;
        case REC_GDR: free_GDR((GDR*)record); break;
        case REC_DTR: free_DTR((DTR*)record); break;
        default: return; break;
    }
}