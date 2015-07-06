Redis-based components for Scrapy
=================================

This project attempts to provide Redis-backed components for Scrapy.

Features:

* Distributed crawling/scraping
    You can start multiple spider instances that share a single redis queue.
    Best suitable for broad multi-domain crawls.
* Distributed post-processing
    Scraped items gets pushed into a redis queued meaning that you can start as
    many as needed post-processing processes sharing the items queue.

Requirements:

* Scrapy >= 1.0.0
* redis-py >= 2.10.0
* redis server >= 2.8.0

Available Scrapy components:

* Scheduler
* Duplication Filter
* Item Pipeline
* Base Spider


Installation
------------

From `pypi`::

  $ pip install scrapy-redis

From `github`::

  $ git clone https://github.com/darkrho/scrapy-redis.git
  $ cd scrapy-redis
  $ python setup.py install


Usage
-----

Enable the components in your `settings.py`:

.. code-block:: python

  # Enables scheduling storing requests queue in redis.
  SCHEDULER = "scrapy_redis.scheduler.Scheduler"

  # Don't cleanup redis queues, allows to pause/resume crawls.
  SCHEDULER_PERSIST = True

  # Schedule requests using a priority queue. (default)
  SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.SpiderPriorityQueue'

  # Schedule requests using a queue (FIFO).
  SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.SpiderQueue'

  # Schedule requests using a stack (LIFO).
  SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.SpiderStack'

  # Max idle time to prevent the spider from being closed when distributed crawling.
  # This only works if queue class is SpiderQueue or SpiderStack,
  # and may also block the same time when your spider start at the first time (because the queue is empty).
  SCHEDULER_IDLE_BEFORE_CLOSE = 10

  # Store scraped item in redis for post-processing.
  ITEM_PIPELINES = {
      'scrapy_redis.pipelines.RedisPipeline': 300
  }

  # Specify the host and port to use when connecting to Redis (optional).
  REDIS_HOST = 'localhost'
  REDIS_PORT = 6379

  # Specify the full Redis URL for connecting (optional).
  # If set, this takes precedence over the REDIS_HOST and REDIS_PORT settings.
  REDIS_URL = 'redis://user:pass@hostname:9001'

.. note::

  Version 0.3 changed the requests serialization from `marshal` to `cPickle`,
  therefore persisted requests using version 0.2 will not able to work on 0.3.


Running the example project
---------------------------

This example illustrates how to share a spider's requests queue
across multiple spider instances, highly suitable for broad crawls.

1. Setup scrapy_redis package in your PYTHONPATH

2. Run the crawler for first time then stop it::

    $ cd example-project
    $ scrapy crawl dmoz
    ... [dmoz] ...
    ^C

3. Run the crawler again to resume stopped crawling::

    $ scrapy crawl dmoz
    ... [dmoz] DEBUG: Resuming crawl (9019 requests scheduled)

4. Start one or more additional scrapy crawlers::

    $ scrapy crawl dmoz
    ... [dmoz] DEBUG: Resuming crawl (8712 requests scheduled)

5. Start one or more post-processing workers::

    $ python process_items.py
    Processing: Kilani Giftware (http://www.dmoz.org/Computers/Shopping/Gifts/)
    Processing: NinjaGizmos.com (http://www.dmoz.org/Computers/Shopping/Gifts/)
    ...


Feeding a Spider from Redis
---------------------------

The class `scrapy_redis.spiders.RedisSpider` enables a spider to read the
urls from redis. The urls in the redis queue will be processed one
after another, if the first request yields more requests, the spider
will process those requests before fetching another url from redis.

For example, create a file `myspider.py` with the code below:

.. code-block:: python

    from scrapy_redis.spiders import RedisSpider

    class MySpider(RedisSpider):
        name = 'myspider'

        def parse(self, response):
            # do stuff
            pass


Then:

1. run the spider::

    scrapy runspider myspider.py

2. push urls to redis::

    redis-cli lpush myspider:start_urls http://google.com


Changelog
---------

0.6
  * Updated code to be compatible with Scrapy 1.0.
  * Added `-a domain=...` option for example spiders.

0.5
  * Added `REDIS_URL` setting to support Redis connection string.
  * Added `SCHEDULER_IDLE_BEFORE_CLOSE` setting to prevent the spider closing too
    quickly when the queue is empty. Default value is zero keeping the previous
    behavior.
  * Schedule preemptively requests on item scraped.
  * This version is the latest release compatible with Scrapy 0.24.x.

0.4
  * Added `RedisSpider` and `RedisMixin` classes as building blocks for spiders
    to be fed through a redis queue.
  * Added redis queue stats.
  * Let the encoder handle the item as it comes instead converting it to a dict.

0.3
  * Added support for different queue classes.
  * Changed requests serialization from `marshal` to `cPickle`.

0.2
  * Improved backward compatibility.
  * Added example project.

0.1
  * Initial version.


.. image:: https://d2weczhvl823v0.cloudfront.net/darkrho/scrapy-redis/trend.png
   :alt: Bitdeli badge
   :target: https://bitdeli.com/free

