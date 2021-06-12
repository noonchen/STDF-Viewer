#
# tsqueue.pxd - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: April 28th 2021
# -----
# Last Modified: Tue May 04 2021
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



# Thread-Safe Queue in C
cdef extern from "tsqueue_src/message_queue.c":
    pass


cdef extern from "tsqueue_src/message_queue.h":
    ctypedef struct tsQueue:
        pass

    int message_queue_init(tsQueue *queue, int message_size, int max_depth) nogil

    void *message_queue_message_alloc(tsQueue *queue) nogil

    void *message_queue_message_alloc_blocking(tsQueue *queue) nogil

    void message_queue_message_free(tsQueue *queue, void *message) nogil

    void message_queue_write(tsQueue *queue, void *message) nogil

    void *message_queue_tryread(tsQueue *queue) nogil

    void *message_queue_read(tsQueue *queue) nogil

    void message_queue_destroy(tsQueue *queue) nogil

