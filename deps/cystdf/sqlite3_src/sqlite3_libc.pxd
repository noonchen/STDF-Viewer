# distutils: language = c
# cython: language_level=3
#
# csqlite.pxd - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: April 19th 2021
# -----
# Last Modified: Thu May 13 2021
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



cdef extern from "sqlite3_35_3.c" nogil:
    pass


cdef extern from "sqlite3_35_3.h" nogil:
    cdef enum:
        SQLITE_OK
        SQLITE_DONE
    ctypedef long long int sqlite3_int64
    ctypedef struct sqlite3:
        pass
    ctypedef struct Vdbe:
        # real structure of sqlite3_stmt
        pass
    ctypedef struct sqlite3_stmt:
        pass

    int sqlite3_open(const char *filename, sqlite3 **db_ptr)
    int sqlite3_close(sqlite3 *db)

    int sqlite3_exec(sqlite3 *db,                              #/* An open database */
                    const char *sql,                           #/* SQL to be evaluated */
                    int (*callback)(void*,int,char**,char**),  #/* Callback function */
                    void *,                                    #/* 1st argument to callback */
                    char **errmsg                              #/* Error msg written here */
                    )
    
    int sqlite3_prepare_v2(sqlite3 *db,         #/* Database handle */
                        const char *zSql,       #/* SQL statement, UTF-8 encoded */
                        int nByte,              #/* Maximum length of zSql in bytes. */
                        sqlite3_stmt **ppStmt,  #/* OUT: Statement handle */
                        const char **pzTail     #/* OUT: Pointer to unused portion of zSql */
                        )
    int sqlite3_step(sqlite3_stmt*)
    int sqlite3_reset(sqlite3_stmt *pStmt)
    int sqlite3_finalize(sqlite3_stmt *pStmt)

    int sqlite3_bind_parameter_index(sqlite3_stmt*, const char *zName)
    int sqlite3_bind_blob(sqlite3_stmt*, int, const void*, int n, void(*)(void*))
    int sqlite3_bind_blob64(sqlite3_stmt*, int, const void*, sqlite3_uint64,
                            void(*)(void*))
    int sqlite3_bind_double(sqlite3_stmt*, int, double)
    int sqlite3_bind_int(sqlite3_stmt*, int, int)
    int sqlite3_bind_int64(sqlite3_stmt*, int, sqlite3_int64)
    int sqlite3_bind_null(sqlite3_stmt*, int)
    int sqlite3_bind_text(sqlite3_stmt*,int,const char*,int,void(*)(void*))
    int sqlite3_bind_text16(sqlite3_stmt*, int, const void*, int, void(*)(void*))
    int sqlite3_bind_text64(sqlite3_stmt*, int, const char*, sqlite3_uint64,
                            void(*)(void*), unsigned char encoding)
    # int sqlite3_bind_value(sqlite3_stmt*, int, const sqlite3_value*)
    int sqlite3_bind_pointer(sqlite3_stmt*, int, void*, const char*,void(*)(void*))
    int sqlite3_bind_zeroblob(sqlite3_stmt*, int, int n)
    int sqlite3_bind_zeroblob64(sqlite3_stmt*, int, sqlite3_uint64)
    int sqlite3_clear_bindings(sqlite3_stmt*)

    const char *sqlite3_errmsg(sqlite3* db)
    const char *sqlite3_errstr(int)
