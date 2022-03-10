/*
 * testidmap.h - STDF Viewer
 * 
 * Author: noonchen - chennoon233@foxmail.com
 * Created Date: March 10th 2022
 * -----
 * Last Modified: Thu Mar 10 2022
 * Modified By: noonchen
 * -----
 * Copyright (c) 2022 noonchen
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

#ifndef __TESTIDMAP_H__
#define __TESTIDMAP_H__

#define INIT_SIZE 256

#define TESTIDMAP_INVALID -1003
#define TESTIDMAP_MISSING -1002  /* No such element */
#define TESTIDMAP_OMEM -1000     /* Out of Memory */
#define TESTIDMAP_OK 0    /* OK */

typedef struct testItem {
    uint32_t    TEST_NUM;
    char*       TEST_NAME;
} testItem;


typedef struct testIDMap {
    int         capacity;
    int         mapSize;
    testItem*   tests;
    int*        id;
} testIDMap;


testIDMap* createTestIDMap();

void destoryTestIDMap(testIDMap* map);

int getTestID(testIDMap* map, uint32_t TEST_NUM, const char* TEST_NAME);

int insertTestItem(testIDMap* map, uint32_t TEST_NUM, const char* TEST_NAME);


#endif  //__TESTIDMAP_H__