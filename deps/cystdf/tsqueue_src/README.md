# Introduction

I've always longed for a good, _fast_ way to relay information between
threads. So, I built one!

What's a message? It's anything you want it to be: a built-in data type, a
character string, a function pointer, or a complicated data structure. The
queue won't copy or move your structure, so internal pointers remain intact. A
message is anything your application wants to send between threads.

# How does it work?

The library uses a lock-free allocator to allocate memory for messages. Then,
your application can construct whatever it needs to send in-place. When you
write the message to the queue, it's added to a lock-free structure similar to
the one used to allocate memory.

# Why should I use this?

* It's fast. Crazy fast. My three-year-old laptop can push around 6,500,000
  messages per second between threads, _including_ the overhead of allocating
  the messages.
* It's easy. There are only 8 functions to learn, and you probably only need 6
  of them. Really, there are only 3 concepts to worry about:
  * initialization/teardown,
  * allocation/deallocation, and
  * writing/reading.

  If you're a C programmer, you've dealt with all of these already.

# Why shouldn't I use this?

* It's new and so not widely tested. In fact, it's only been tested at all on
  two x86_64 machines, running Mac OS X and Linux.
* It may be overly tuned to my Core 2 Duo. Performance is tricky and often
  very hardware dependent. Hopefully wider exposure will help this work well
  on a wider variety of hardware.
* I have no clue how well it scales past two CPUs. Anyone want to try it on a
  bigger, beefier machine?
* You have to know how big the largest message you want to send on a given
  queue is in advance, and you have to decide on a maximum depth the queue can
  reach.

# How do I use this?

First, set up a message queue somewhere:

    struct message_queue queue;

Before using it, you have to initialize it:

    message_queue_init(&queue, 512, 128); /* The biggest message we'll send
                                           * with this queue is 512 bytes, and
                                           * the queue can only be 128
                                           * messages deep */

To send a message:

    struct my_message *message = message_queue_message_alloc_blocking(&queue);
    /* Construct the message here */
    message_queue_write(&queue, message);

Or, if you'd rather discard your message if there's no free memory in the
queue:

    struct my_message *message = message_queue_message_alloc(&queue);
    if(message) {
        /* Construct the message here */
        message_queue_write(&queue, message);
    }

To read a message:

	/* Blocks until a message is available */
    struct my_message *message = message_queue_read(&queue);
    /* Do something with the message here */
    message_queue_message_free(&queue, message);

If you'd rather not block to wait for a new message:

    /* Returns NULL if no message is available */
    struct my_message *message = message_queue_tryread(&queue);
    if(message) {
        /* Do something with the message here */
        message_queue_message_free(&queue, message);
    }

Whenever you're done with the queue (and no other threads are accessing it
anymore):

    message_queue_destroy(&queue);

So give it a shot and let me know what you think!
