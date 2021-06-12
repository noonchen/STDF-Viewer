#
# hashmap_libc.pxd - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: May 17th 2021
# -----
# Last Modified: Wed May 19 2021
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

from libc.stdint cimport uint32_t

cdef extern from "hashmap.c" nogil:
    pass


cdef extern from "hashmap.h" nogil:
    ctypedef void* any_t
    ctypedef any_t map_t
    ctypedef int (*PFany)(any_t, uint32_t, uint32_t)

    cdef enum:
        MAP_MISSING
        MAP_FULL
        MAP_OMEM
        MAP_OK

    map_t hashmap_new(int size)

    int hashmap_put(map_t input_map, uint32_t key, uint32_t value)

    int hashmap_get(map_t input_map, uint32_t key, uint32_t *arg)

    int hashmap_contains(map_t input_map, uint32_t key)

    int hashmap_iterate(map_t input_map, PFany f, any_t item)

    void hashmap_free(map_t input_map)