============
Scrapy-Redis
============

.. image:: https://readthedocs.org/projects/scrapy-redis/badge/?version=latest
        :target: https://readthedocs.org/projects/scrapy-redis/?badge=latest
        :alt: Documentation Status

.. image:: https://img.shields.io/pypi/v/scrapy-redis.svg
        :target: https://pypi.python.org/pypi/scrapy-redis

.. image:: https://img.shields.io/pypi/pyversions/scrapy-redis.svg
        :target: https://pypi.python.org/pypi/scrapy-redis

.. image:: https://img.shields.io/travis/rolando/scrapy-redis.svg
        :target: https://travis-ci.org/rolando/scrapy-redis

.. image:: https://codecov.io/github/rolando/scrapy-redis/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/rolando/scrapy-redis

.. image:: https://landscape.io/github/rolando/scrapy-redis/master/landscape.svg?style=flat
    :target: https://landscape.io/github/rolando/scrapy-redis/master
    :alt: Code Quality Status

.. image:: https://requires.io/github/rolando/scrapy-redis/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/rolando/scrapy-redis/requirements/?branch=master

Redis-based components for Scrapy.

* Free software: MIT license
* Documentation: https://scrapy-redis.readthedocs.org.
* Python versions: 2.7, 3.4+

Features
--------

* Distributed crawling/scraping

    You can start multiple spider instances that share a single redis queue.
    Best suitable for broad multi-domain crawls.

* Distributed post-processing

    Scraped items gets pushed into a redis queued meaning that you can start as
    many as needed post-processing processes sharing the items queue.

* Scrapy plug-and-play components
  
    Scheduler + Duplication Filter, Item Pipeline, Base Spiders.
    
.. note:: This features cover the basic case of distributing the workload across multiple workers. If you need more features like URL expiration, advanced URL prioritization, etc., we suggest you to take a look at the `Frontera`_ project.

Requirements
------------

* Python 2.7, 3.4 or 3.5
* Redis >= 2.8
* ``Scrapy`` >= 1.1
* ``redis-py`` >= 2.10

Usage
-----

Use the following settings in your project:

.. code-block:: python

  # Enables scheduling storing requests queue in redis.
  SCHEDULER = "scrapy_redis.scheduler.Scheduler"

  # Ensure all spiders share same duplicates filter through redis.
  DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"

  # Default requests serializer is pickle, but it can be changed to any module
  # with loads and dumps functions. Note that pickle is not compatible between
  # python versions.
  # Caveat: In python 3.x, the serializer must return strings keys and support
  # bytes as values. Because of this reason the json or msgpack module will not
  # work by default. In python 2.x there is no such issue and you can use
  # 'json' or 'msgpack' as serializers.
  #SCHEDULER_SERIALIZER = "scrapy_redis.picklecompat"

  # Don't cleanup redis queues, allows to pause/resume crawls.
  #SCHEDULER_PERSIST = True

  # Schedule requests using a priority queue. (default)
  #SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.PriorityQueue'

  # Alternative queues.
  #SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.FifoQueue'
  #SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.LifoQueue'

  # Max idle time to prevent the spider from being closed when distributed crawling.
  # This only works if queue class is SpiderQueue or SpiderStack,
  # and may also block the same time when your spider start at the first time (because the queue is empty).
  #SCHEDULER_IDLE_BEFORE_CLOSE = 10

  # Store scraped item in redis for post-processing.
  ITEM_PIPELINES = {
      'scrapy_redis.pipelines.RedisPipeline': 300
  }

  # The item pipeline serializes and stores the items in this redis key.
  #REDIS_ITEMS_KEY = '%(spider)s:items'

  # The items serializer is by default ScrapyJSONEncoder. You can use any
  # importable path to a callable object.
  #REDIS_ITEMS_SERIALIZER = 'json.dumps'

  # Specify the host and port to use when connecting to Redis (optional).
  #REDIS_HOST = 'localhost'
  #REDIS_PORT = 6379

  # Specify the full Redis URL for connecting (optional).
  # If set, this takes precedence over the REDIS_HOST and REDIS_PORT settings.
  #REDIS_URL = 'redis://user:pass@hostname:9001'

  # Custom redis client parameters (i.e.: socket timeout, etc.)
  #REDIS_PARAMS  = {}
  # Use custom redis client class.
  #REDIS_PARAMS['redis_cls'] = 'myproject.RedisClient'

  # If True, it uses redis' ``SPOP`` operation. You have to use the ``SADD``
  # command to add URLs to the redis queue. This could be useful if you
  # want to avoid duplicates in your start urls list and the order of
  # processing does not matter.
  #REDIS_START_URLS_AS_SET = False

  # Default start urls key for RedisSpider and RedisCrawlSpider.
  #REDIS_START_URLS_KEY = '%(name)s:start_urls'

  # Use other encoding than utf-8 for redis.
  #REDIS_ENCODING = 'latin1'

.. note::

  Version 0.3 changed the requests serialization from ``marshal`` to ``cPickle``,
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

    $ python process_items.py dmoz:items -v
    ...
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


.. note::

    These spiders rely on the spider idle signal to fetch start urls, hence it
    may have a few seconds of delay between the time you push a new url and the
    spider starts crawling it.


Contributions
-------------

Donate BTC: ``13haqimDV7HbGWtz7uC6wP1zvsRWRAhPmF``

Donate BCC: ``CSogMjdfPZnKf1p5ocu3gLR54Pa8M42zZM``

Donate ETH: ``0x681d9c8a2a3ff0b612ab76564e7dca3f2ccc1c0d``

Donate LTC: ``LaPHpNS1Lns3rhZSvvkauWGDfCmDLKT8vP``


.. _Frontera: https://github.com/scrapinghub/frontera
