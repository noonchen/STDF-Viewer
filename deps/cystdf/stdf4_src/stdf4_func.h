/*
 * stdf4_func.h - STDF Viewer
 * 
 * Author: noonchen - chennoon233@foxmail.com
 * Created Date: May 11th 2021
 * -----
 * Last Modified: Mon May 17 2021
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



// #include "stdf4_types.h"
#include <stdint.h>


extern int needByteSwap;

void parse_record(void** pRec, uint16_t recHeader, const unsigned char* rawData, uint16_t binaryLen);

void free_record(uint16_t recHeader, void* record);
