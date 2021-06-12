/*
 * Copyright (c) 2012 Jeremy Pepper
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 *  * Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 *  * Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *  * Neither the name of message_queue nor the names of its contributors may
 *    be used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

#ifndef MESSAGE_QUEUE_H
#define MESSAGE_QUEUE_H

#ifndef CACHE_LINE_SIZE
#define CACHE_LINE_SIZE 64
#endif

#include <semaphore.h>

/**
 * \brief Message queue structure
 *
 * This structure is passed to all message_queue API calls
 */
typedef struct message_queue {
	unsigned int message_size;
	unsigned int max_depth;
	void *memory;
	void **freelist;
	void **queue_data;
	struct {
		sem_t unnamed_sem;
		sem_t *sem;
		unsigned int blocked_readers;
		int free_blocks;
		unsigned int allocpos __attribute__((aligned(CACHE_LINE_SIZE)));
		unsigned int freepos __attribute__((aligned(CACHE_LINE_SIZE)));
	} allocator __attribute__((aligned(CACHE_LINE_SIZE)));
	struct {
		sem_t unnamed_sem;
		sem_t *sem;
		unsigned int blocked_readers;
		int entries;
		unsigned int readpos __attribute__((aligned(CACHE_LINE_SIZE)));
		unsigned int writepos __attribute__((aligned(CACHE_LINE_SIZE)));
	} queue __attribute__((aligned(CACHE_LINE_SIZE)));
} tsQueue;

#ifdef __cplusplus
extern "C" {
#endif

/**
 * \brief Initialize a message queue structure
 *
 * This function must be called before any other message_queue API calls on a
 * message queue structure.
 *
 * \param queue pointer to the message queue structure to initialize
 * \param message_size size in bytes of the largest message that will be sent
 *        on this queue
 * \param max_depth the maximum number of message to allow in the queue at
 *        once. This will be rounded to the next highest power of two.
 *
 * \return 0 if successful, or nonzero if an error occured
 */
extern int message_queue_init(tsQueue *queue, int message_size, int max_depth);

/**
 * \brief Allocate a new message
 *
 * This allocates message_size bytes to be used with this queue. Messages
 * passed to the queue MUST be allocated with this function or with
 * message_queue_message_alloc_blocking.
 *
 * \param queue pointer to the message queue to which the message will be
 *        written
 * \return pointer to the allocated message, or NULL if no memory is available
 */
extern void *message_queue_message_alloc(tsQueue *queue);

/**
 * \brief Allocate a new message
 *
 * This allocates message_size bytes to be used with this queue. Messages
 * passed to the queue MUST be allocated with this function or with
 * message_queue_message_alloc. This function blocks until memory is
 * available.
 *
 * \param queue pointer to the message queue to which the message will be
 *        written
 * \return pointer to the allocated message
 */
extern void *message_queue_message_alloc_blocking(tsQueue *queue);

/**
 * \brief Free a message
 *
 * This returns the message to the queue's freelist to be reused to satisfy
 * future allocations. This function MUST be used to free messages--they
 * cannot be passed to free().
 *
 * \param queue pointer to the message queue from which the message was
 *        allocated
 * \param message pointer to the message to be freed
 */
extern void message_queue_message_free(tsQueue *queue, void *message);

/**
 * \brief Write a message to the queue
 *
 * Messages must have been allocated from the same queue by
 * message_queue_message_alloc to be passed to this function.
 *
 * \param queue pointer to the queue to which to write
 * \param message pointer to the message to write to the queue
 */
extern void message_queue_write(tsQueue *queue, void *message);

/**
 * \brief Read a message from the queue if one is available
 *
 * \param queue pointer to the queue from which to read
 * \return pointer to the next message on the queue, or NULL if no messages
 *         are available.
 */
extern void *message_queue_tryread(tsQueue *queue);

/**
 * \brief Read a message from the queue
 *
 * This reads a message from the queue, blocking if necessary until one is
 * available.
 *
 * \param queue pointer to the queue from which to read
 * \return pointer to the next message on the queue
 */
extern void *message_queue_read(tsQueue *queue);

/**
 * \brief Destroy a message queue structure
 *
 * This frees any resources associated with the message queue.
 *
 * \param queue pointer to the message queue to destroy
 */
extern void message_queue_destroy(tsQueue *queue);

#ifdef __cplusplus
}
#endif

#endif
