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

* In this forked version: added `json` supported data in Redis

    data contains `url`, `meta` and other optional parameters. `meta` is a nested json which contains sub-data.
    this function extract this data and send another FormRequest with `url`, `meta` and addition `formdata`.

    For example:
    .. code-block:: json::
        {"url": "https://exaple.com", "meta": {'job-id':'123xsd', 'start-date':'dd/mm/yy'}, "url_cookie_key":"fertxsas" }

    this data can be accessed in `scrapy spider` through response.
    like: `request.url`, `request.meta`, `request.cookies`
    
.. note:: This features cover the basic case of distributing the workload across multiple workers. If you need more features like URL expiration, advanced URL prioritization, etc., we suggest you to take a look at the `Frontera`_ project.

Requirements
------------

* Python 2.7, 3.4 or 3.5
* Redis >= 2.8
* ``Scrapy`` >= 1.1
* ``redis-py`` >= 3.0

Installation
------------

From `github`::

  $ git clone https://github.com/darkrho/scrapy-redis.git
  $ cd scrapy-redis
  $ python setup.py install

.. note:: For using this json supported data feature, please make sure you have not installed the scrapy-redis through pip. If you already did it, you first uninstall that one.
    .. code::
        pip uninstall scrapy-redis


Usage
-----

Use the following settings in your project:

.. code-block:: python

  # Enables scheduling storing requests queue in redis.
  SCHEDULER = "scrapy_redis.scheduler.Scheduler"

  # Ensure all spiders share same duplicates filter through redis.
  DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"

  # Enables stats shared based on Redis
  STATS_CLASS = "scrapy_redis.stats.RedisStatsCollector"

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

  # Maximum idle time before close spider.
  # When the number of idle seconds is greater than MAX_IDLE_TIME_BEFORE_CLOSE, the crawler will close.
  # If 0, the crawler will DontClose forever to wait for the next request.
  # If negative number, the crawler will immediately close when the queue is empty, just like Scrapy.
  #MAX_IDLE_TIME_BEFORE_CLOSE = 0

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

  # If True, it uses redis ``zrevrange`` and ``zremrangebyrank`` operation. You have to use the ``zadd``
  # command to add URLS and Scores to redis queue. This could be useful if you
  # want to use priority and avoid duplicates in your start urls list.
  #REDIS_START_URLS_AS_ZSET = False

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

1. Check scrapy_redis package in your PYTHONPATH

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

2. push json data to redis::

    redis-cli lpush myspider '{"url": "https://exaple.com", "meta": {"job-id":"123xsd", "start-date":"dd/mm/yy"}, "url_cookie_key":"fertxsas" }'


.. note::

    * These spiders rely on the spider idle signal to fetch start urls, hence it
    may have a few seconds of delay between the time you push a new url and the
    spider starts crawling it.

    * Also please pay attention to json formatting.

Alternative Choice
---------------------------

Frontera_  is a web crawling framework consisting of `crawl frontier`_, and distribution/scaling primitives, allowing to build a large scale online web crawler.

.. _Frontera: https://github.com/scrapinghub/frontera
.. _crawl frontier: http://nlp.stanford.edu/IR-book/html/htmledition/the-url-frontier-1.html
