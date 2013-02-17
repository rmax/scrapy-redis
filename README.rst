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

Usage
-----

In your settings.py:

.. code-block:: python

  # enables scheduling storing requests queue in redis
  SCHEDULER = "scrapy_redis.scheduler.Scheduler"

  # don't cleanup redis queues, allows to pause/resume crawls
  SCHEDULER_PERSIST = True

  # store scraped item in redis for post-processing
  ITEM_PIPELINES = [
      'scrapy_redis.pipelines.RedisPipeline',
  ]


Running the example project
---------------------------

You can test the funcionality following the next steps:

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

That's it.
