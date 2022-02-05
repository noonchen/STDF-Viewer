/*
 * stdf4_io.h - STDF Viewer
 * 
 * Author: noonchen - chennoon233@foxmail.com
 * Created Date: May 18th 2021
 * -----
 * Last Modified: Thu Feb 03 2022
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


// #define _LARGEFILE64_SOURCE

#include <stdio.h>
#include <stdint.h>
#include "zlib_src/zlib.h"
#include "bzip2_src/bzlib.h"
#include "minizip_src/unzip.h"

#ifndef __STDF_IO_TYPES__
#define __STDF_IO_TYPES__
typedef enum {
    STD_OK          = 0,
    INVAILD_STDF    = 1000,
    WRONG_VERSION   = 1001,
    OS_FAIL         = 1002,
    NO_MEMORY       = 1003,
    STD_EOF         = 1004,
    TERMINATE       = 1005
} STDERR;


typedef enum {
    NotCompressed   = 0,
    GZ_compressed   = 1,
    BZ_compressed   = 2,
    ZIP_compressed  = 3,
} stdf_format;


typedef struct _stdf_fops {
    int (*stdf_open)(void* stdf, void* filename);
    int (*stdf_read)(void* stdf, void* buf, int length);
    // int (*stdf_skip)(void* stdf, int num);
    int (*stdf_close)(void* stdf);
} stdf_fops;


typedef struct _stdf_handler {
    void*           filepath;
    stdf_format     fmt;
    FILE*           orgF;
    gzFile          gzF;
    BZFILE*         bzF;
    unzFile         zipF;
    stdf_fops*      fops;
} STDF;

#endif //__STDF_IO_TYPES__

extern STDERR stdf_open(STDF** sh, void* filename);

extern STDERR stdf_reopen(STDF* sh);

extern STDERR stdf_close(STDF* sh);