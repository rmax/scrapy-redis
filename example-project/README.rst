============================
Scrapy Redis Example Project
============================


This directory contains an example Scrapy project integrated with scrapy-redis.
By default, all items are sent to redis (key ``<spider>:items``). All spiders
schedule requests through redis, so you can start additional spiders to speed
up the crawling.

Spiders
-------

* **dmoz**

  This spider simply scrapes dmoz.org.

* **myspider_redis**

  This spider uses redis as a shared requests queue and uses
  ``myspider:start_urls`` as start URLs seed. For each URL, the spider outputs
  one item.

* **mycrawler_redis**

  This spider uses redis as a shared requests queue and uses
  ``mycrawler:start_urls`` as start URLs seed. For each URL, the spider follows
  are links.


.. note::

    All requests are persisted by default. You can clear the queue by using the
    ``SCHEDULER_FLUSH_ON_START`` setting. For example: ``scrapy crawl dmoz -s
    SCHEDULER_FLUSH_ON_START=1``.


Running the example project
---------------------------

This example illustrates how to share a spider's requests queue
across multiple spider instances, highly suitable for broad crawls.

1. Check scrapy_redis package in your ``PYTHONPATH``

2. Run the crawler for first time then stop it

.. code-block:: bash

    cd example-project
    scrapy crawl dmoz
    ... [dmoz] ...
    ^C

3. Run the crawler again to resume stopped crawling

.. code-block:: bash

    scrapy crawl dmoz
    ... [dmoz] DEBUG: Resuming crawl (9019 requests scheduled)

4. Start one or more additional scrapy crawlers

.. code-block:: bash

    scrapy crawl dmoz
    ... [dmoz] DEBUG: Resuming crawl (8712 requests scheduled)

5. Start one or more post-processing workers

.. code-block:: bash

    python process_items.py dmoz:items -v
    ...
    Processing: Kilani Giftware (http://www.dmoz.org/Computers/Shopping/Gifts/)
    Processing: NinjaGizmos.com (http://www.dmoz.org/Computers/Shopping/Gifts/)
    ...


Feeding a Spider from Redis
---------------------------

The class ``scrapy_redis.spiders.RedisSpider`` enables a spider to read the
urls from redis. The urls in the redis queue will be processed one
after another, if the first request yields more requests, the spider
will process those requests before fetching another url from redis.

For example, create a file ``myspider.py`` with the code below:

.. code-block:: python

    from scrapy_redis.spiders import RedisSpider


    class MySpider(RedisSpider):
        name = "myspider"

        def parse(self, response):
            # do stuff
            pass


Then:

1. run the spider

.. code-block:: bash

    scrapy runspider myspider.py

2. push json data to redis

.. code-block:: bash

    redis-cli lpush myspider '{"url": "https://exaple.com", "meta": {"job-id":"123xsd", "start-date":"dd/mm/yy"}, "url_cookie_key":"fertxsas" }'


.. note::

    * These spiders rely on the spider idle signal to fetch start urls, hence it
    may have a few seconds of delay between the time you push a new url and the
    spider starts crawling it.

    * Also please pay attention to json formatting.


Processing items
----------------

The ``process_items.py`` provides an example of consuming the items queue::

.. code-block:: bash

    python process_items.py --help


Run via Docker
--------------

You require the following applications:

* docker (https://docs.docker.com/installation/)
* docker-compose (https://docs.docker.com/compose/install/)

For implementation details see `Dockerfile` and `docker-compose.yml` and read
official docker documentation.

1. To start sample `example-project` (`-d` for daemon)::

    docker-compose up

2. To scale `crawler` (4 instances for example)::

    docker-compose scale crawler=4
