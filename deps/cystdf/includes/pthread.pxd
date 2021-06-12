#
# pthread.pxd - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: May 4th 2021
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



cdef extern from "<pthread.h>" nogil:
    ctypedef int pthread_t

    ctypedef struct pthread_attr_t:
        pass
    ctypedef struct pthread_mutexattr_t:
        pass
    ctypedef struct pthread_mutex_t:
       pass

    enum:
        PTHREAD_CANCEL_ENABLE
        PTHREAD_CANCEL_DISABLE

    int pthread_cancel(pthread_t thread)
    int pthread_setcancelstate(int state, int *oldstate)
    pthread_t pthread_self()
    int pthread_equal(pthread_t t1, pthread_t t2)
    int pthread_create(pthread_t *thread, pthread_attr_t *attr,
                       void *(*start_routine) (void *), void *arg)
    int pthread_join(pthread_t thread, void **retval)
    int pthread_kill(pthread_t thread, int sig)

    int pthread_mutex_init(pthread_mutex_t *mutex, pthread_mutexattr_t *mutexattr)
    int pthread_mutex_lock(pthread_mutex_t *mutex)
    int pthread_mutex_unlock(pthread_mutex_t *mutex)