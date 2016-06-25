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


Processing items
----------------

The ``process_items.py`` provides an example of consuming the items queue::

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
