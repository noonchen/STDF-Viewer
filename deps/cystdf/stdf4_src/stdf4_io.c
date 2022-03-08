/*
 * stdf4_io.c - STDF Viewer
 * 
 * Author: noonchen - chennoon233@foxmail.com
 * Created Date: May 18th 2021
 * -----
 * Last Modified: Sun Feb 06 2022
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

// #define _FILE_OFFSET_BITS   64
// #define _LFS64_LARGEFILE    1
// #define _LARGEFILE64_SOURCE 1

#include "stdf4_io.h"
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <fcntl.h>
#include <wchar.h>
#ifdef _WIN32
    #include <io.h>
    #include <share.h>
    #include <locale.h>
    #include <stdio.h>
#endif

int get_fd_with_unicode_path(const char* utf8_filename, const wchar_t* wchar_filename) {
#ifdef _WIN32
    // open file descriptor with wchar_t path in windows
    return _wsopen(wchar_filename, _O_BINARY | _O_RDONLY, _SH_DENYWR);
#else
    // linux and mac support utf8 path natively
    return open(utf8_filename, O_RDONLY);
#endif
}


/* Uncompressed */
int _stdf_open_org(void* stdf, void* filename){
    STDF* std = (STDF*)stdf;

#ifdef _WIN32
    int fd = get_fd_with_unicode_path(NULL, (wchar_t*)filename);
    std->orgF = _wfdopen(fd, L"rb");
#else
    int fd = get_fd_with_unicode_path((char*)filename, NULL);
    std->orgF = fdopen(fd, "rb");
#endif

    if (std->orgF == NULL) {
        printf("file handler is null, failed to open %s\n", (char*)filename);
        fclose(std->orgF);
        return OS_FAIL;
    }
    return STD_OK;
}

int _stdf_read_org(void* stdf, void* buf, int length){
    STDF* std = (STDF*)stdf;
    int num = fread(buf, length, 1, std->orgF);
    if (num != 1) {
        if (length == 0 && length == num) {
            // EPS, length = 0
            return STD_OK;
        }
        return STD_EOF;
    }
    return STD_OK;
}

int _stdf_skip_org(void* stdf, int num){
    STDF* std = (STDF*)stdf;
    int status = fseeko(std->orgF, num, SEEK_CUR);
    if (status !=0 ){
        return OS_FAIL;
    }
    return STD_OK;
}

int _stdf_close_org(void* stdf){
    STDF* std = (STDF*)stdf;
    int status = fclose(std->orgF);
    if (status != 0) {
        return OS_FAIL;
    }
    return STD_OK;
}

stdf_fops stdf_fops_org = {
    _stdf_open_org,
    _stdf_read_org,
    // _stdf_skip_org,
    _stdf_close_org
};


/* GZ */
int _stdf_open_gz(void* stdf, void* filename){
    STDF* std = (STDF*)stdf;
#ifdef _WIN32
    int fd = get_fd_with_unicode_path(NULL, (wchar_t*)filename);
#else
    int fd = get_fd_with_unicode_path((char*)filename, NULL);
#endif
    std->gzF = gzdopen(fd, "rb");

    if (std->gzF == NULL) {
        printf("file handler is null, failed to open %s\n", (char*)filename);
        gzclose(std->gzF);
        return OS_FAIL;
    }
    return STD_OK;
}

int _stdf_read_gz(void* stdf, void* buf, int length){
    STDF* std = (STDF*)stdf;
    int nread = gzread(std->gzF, buf, length);
    if (nread != length) {
        return STD_EOF;
    }
    return STD_OK;
}

int _stdf_skip_gz(void* stdf, int num){
    STDF* std = (STDF*)stdf;
    if (gzseek(std->gzF, num, SEEK_CUR) != 0){
        return OS_FAIL;
    }
    return STD_OK;
}

int _stdf_close_gz(void* stdf){
    STDF* std = (STDF*)stdf;
    int status = gzclose(std->gzF);
    if (status != Z_OK) {
        return OS_FAIL;
    }
    return STD_OK;
}

stdf_fops stdf_fops_gz = {
    _stdf_open_gz,
    _stdf_read_gz,
    // _stdf_skip_gz,
    _stdf_close_gz
};


/* BZ & BZ2 */
int _stdf_open_bz(void* stdf, void* filename){
    STDF* std = (STDF*)stdf;
#ifdef _WIN32
    int fd = get_fd_with_unicode_path(NULL, (wchar_t*)filename);
#else
    int fd = get_fd_with_unicode_path((char*)filename, NULL);
#endif
    std->bzF = BZ2_bzdopen(fd, "rb");

    if (std->bzF == NULL) {
        printf("file handler is null, failed to open %s\n", (char*)filename);
        BZ2_bzclose(std->bzF);
        return OS_FAIL;
    }
    return STD_OK;
}

int _stdf_read_bz(void* stdf, void* buf, int length){
    STDF* std = (STDF*)stdf;
    int nread = BZ2_bzread(std->bzF, buf, length);
    if (nread != length) {
        return STD_EOF;
    }
    return STD_OK;
}

int _stdf_skip_bz(void* stdf, int num){
    char buf[num];
    STDF* std = (STDF*)stdf;
    int status = BZ2_bzread(std->bzF, buf, num);
    if (status == -1) {
        return OS_FAIL;
    }
    return STD_OK;
}

int _stdf_close_bz(void* stdf){
    STDF* std = (STDF*)stdf;
    BZ2_bzclose(std->bzF);
    return STD_OK;
}

stdf_fops stdf_fops_bz = {
    _stdf_open_bz,
    _stdf_read_bz,
    // _stdf_skip_bz,
    _stdf_close_bz
};


/* ZIP */
int _stdf_open_zip(void* stdf, void* filename){
    STDF* std = (STDF*)stdf;
    std->zipF = unzOpen64(filename);

    unzGoToFirstFile(std->zipF);
    unzOpenCurrentFile(std->zipF);

    if (std->zipF == NULL) {
        printf("file handler is null, failed to open %s\n", (char*)filename);
        unzCloseCurrentFile(std->zipF);
        unzClose(std->zipF);        
        return OS_FAIL;
    }
    return STD_OK;
}

int _stdf_read_zip(void* stdf, void* buf, int length){
    STDF* std = (STDF*)stdf;
    int nread = unzReadCurrentFile(std->zipF, buf, length);
    if (nread != length) {
        return STD_EOF;
    }
    return STD_OK;
}

int _stdf_skip_zip(void* stdf, int num){
    return STD_OK;
}

int _stdf_close_zip(void* stdf){
    STDF* std = (STDF*)stdf;
    unzCloseCurrentFile(std->zipF);
    int status = unzClose(std->zipF);
    if (status != UNZ_OK) {
        return OS_FAIL;
    }
    return STD_OK;
}

stdf_fops stdf_fops_zip = {
    _stdf_open_zip,
    _stdf_read_zip,
    // _stdf_skip_zip,
    _stdf_close_zip
};


/* API */

STDERR stdf_open(STDF** sh_ptr, void* filename) {
    *sh_ptr = (STDF*)malloc(sizeof(STDF));
    STDF* sh = *sh_ptr;
    if (sh == NULL) {
        free(sh);
        return NO_MEMORY;
    }
    sh->filepath = filename;
    
#ifdef _WIN32
    wchar_t* ext = wcsrchr((wchar_t*)filename, L'.');
    if (!_wcsnicmp(ext, L".gz", 3)){
        sh->fmt = GZ_compressed;
    } else if (!_wcsnicmp(ext, L".bz", 3)){
        sh->fmt = BZ_compressed;
    } else if (!_wcsnicmp(ext, L".bz2", 4)){
        sh->fmt = BZ_compressed;
    } else if (!_wcsnicmp(ext, L".zip", 4)){
        sh->fmt = ZIP_compressed;    
    } else {
        sh->fmt = NotCompressed;
    }
#else
    char* ext = strrchr((char*)filename, '.');
    if (!strncasecmp(ext, ".gz", 3)){
        sh->fmt = GZ_compressed;
    } else if (!strncasecmp(ext, ".bz", 3)){
        sh->fmt = BZ_compressed;
    } else if (!strncasecmp(ext, ".bz2", 4)){
        sh->fmt = BZ_compressed;
    } else if (!strncasecmp(ext, ".zip", 4)){
        sh->fmt = ZIP_compressed;
    } else {
        sh->fmt = NotCompressed;
    }
#endif

    // set file operations
    switch (sh->fmt) {
    case GZ_compressed:
        sh->gzF = NULL;
        sh->fops = &stdf_fops_gz;
        break;
    case BZ_compressed:
        sh->bzF = NULL;
        sh->fops = &stdf_fops_bz;
        break;
    case ZIP_compressed:
        sh->zipF = NULL;
        sh->fops = &stdf_fops_zip;
        break;
    
    default:
        /* treat as a uncompressed stdf */
        sh->orgF = NULL;
        sh->fops = &stdf_fops_org;
        break;
    }
    
    // open the file
    return sh->fops->stdf_open(sh, sh->filepath);
}

STDERR stdf_reopen(STDF* sh) {
    // close current file
    sh->fops->stdf_close(sh);
    return sh->fops->stdf_open(sh, sh->filepath);

}

STDERR stdf_close(STDF* sh) {
    int status = sh->fops->stdf_close(sh);
    free(sh);
    return status;
}

