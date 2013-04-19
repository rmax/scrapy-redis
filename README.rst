Redis-based components for Scrapy
=================================

This is a initial work on Scrapy-Redis integration, not production-tested.
Use it at your own risk!

Features:

* Distributed crawling/scraping
* Distributed post-processing

Requirements:

* Scrapy >= 0.13 (development version)
* redis-py (tested on 2.4.9)
* redis server (tested on 2.2-2.4)

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

  # enables scheduling storing requests queue in redis
  SCHEDULER = "scrapy_redis.scheduler.Scheduler"

  # don't cleanup redis queues, allows to pause/resume crawls
  SCHEDULER_PERSIST = True

  # Schedule requests using a priority queue. (default)
  SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.SpiderPriorityQueue'

  # Schedule requests using a queue (FIFO).
  SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.SpiderQueue'

  # Schedule requests using a stack (LIFO).
  SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.SpiderStack'

  # store scraped item in redis for post-processing
  ITEM_PIPELINES = [
      'scrapy_redis.pipelines.RedisPipeline',
  ]

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



.. image:: https://d2weczhvl823v0.cloudfront.net/darkrho/scrapy-redis/trend.png
   :alt: Bitdeli badge
   :target: https://bitdeli.com/free

