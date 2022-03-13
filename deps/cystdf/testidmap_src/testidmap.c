/*
 * testidmap.c - STDF Viewer
 * 
 * Author: noonchen - chennoon233@foxmail.com
 * Created Date: March 10th 2022
 * -----
 * Last Modified: Fri Mar 11 2022
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



#include "testidmap.h"
#include <stdlib.h>
#include <string.h>


testIDMap* createTestIDMap() 
{
    testIDMap* map = (testIDMap*)malloc(sizeof(testIDMap));
    if (map == NULL)
    {
        return NULL;
    }

    map->capacity = INIT_SIZE;
    map->mapSize = 0;
    map->tests = (testItem*)malloc(map->capacity * sizeof(testItem));
    map->id = (int*)malloc(map->capacity * sizeof(int));
    if (map->tests == NULL || map->id == NULL)
    {
        free(map->tests);
        free(map->id);
        free(map);
        return NULL;
    }

    return map;
}


void destoryTestIDMap(testIDMap* map)
{
    if (map == NULL)
    {
        return;
    }

    for (int i = 0; i < map->mapSize; i++)
    {
        // free test name in test items
        free((map->tests)[i].TEST_NAME);
    }
    free(map->tests);
    free(map->id);
    free(map);
    return;
}


int getTestID(testIDMap* map, uint32_t TEST_NUM, const char* TEST_NAME)
{
    if (map == NULL)
    {
        return TESTIDMAP_INVALID;
    }

    for (int i = 0; i < map->mapSize; i++)
    {
        testItem tmp = (map->tests)[i];
        if (tmp.TEST_NUM == TEST_NUM && strcmp(tmp.TEST_NAME, TEST_NAME) == 0)
        {
            return map->id[i];
        }
    }
    return TESTIDMAP_MISSING;
}


int insertTestItem(testIDMap* map, uint32_t TEST_NUM, const char* TEST_NAME)
{
    if (map == NULL)
    {
        return TESTIDMAP_INVALID;
    }

    if (map->capacity <= map->mapSize)
    {
        // expand capacity
        int newCapacity = map->capacity + (map->capacity / 2);

        testItem* tmp_tests = (testItem*)realloc(map->tests, newCapacity * sizeof(testItem));
        int* tmp_id = (int*)realloc(map->id, newCapacity * sizeof(int));

        if (tmp_tests != NULL && tmp_id != NULL)
        {
            map->tests = tmp_tests;
            map->id = tmp_id;
            map->capacity = newCapacity;
        }
        else
        {
            free(tmp_tests);
            free(tmp_id);
            return TESTIDMAP_OMEM;
        }
    }

    // insert new test to last
    // current mapSize is the index and id of the new test
    (map->tests)[map->mapSize].TEST_NAME = (char*)calloc( strlen(TEST_NAME)+1, sizeof(char));
    if ((map->tests)[map->mapSize].TEST_NAME == NULL)
    {
        return TESTIDMAP_OMEM;
    }
    strcpy((map->tests)[map->mapSize].TEST_NAME, TEST_NAME);
    (map->tests)[map->mapSize].TEST_NUM = TEST_NUM;
    (map->id)[map->mapSize] = map->mapSize;
    // cnt +1
    map->mapSize += 1;

    // return the id of inserted test item
    return (map->mapSize) - 1;
}