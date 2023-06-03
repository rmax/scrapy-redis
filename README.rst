============
Scrapy-Redis
============

.. image:: https://readthedocs.org/projects/scrapy-redis/badge/?version=latest
        :alt: Documentation Status
        :target: https://readthedocs.org/projects/scrapy-redis/?badge=latest

.. image:: https://img.shields.io/pypi/v/scrapy-redis.svg
        :target: https://pypi.python.org/pypi/scrapy-redis

.. image:: https://img.shields.io/pypi/pyversions/scrapy-redis.svg
        :target: https://pypi.python.org/pypi/scrapy-redis

.. image:: https://github.com/rmax/scrapy-redis/actions/workflows/builds.yml/badge.svg
        :target: https://github.com/rmax/scrapy-redis/actions/workflows/builds.yml
        
.. image:: https://github.com/rmax/scrapy-redis/actions/workflows/checks.yml/badge.svg
        :target: https://github.com/rmax/scrapy-redis/actions/workflows/checks.yml
        
.. image:: https://github.com/rmax/scrapy-redis/actions/workflows/tests.yml/badge.svg
        :target: https://github.com/rmax/scrapy-redis/actions/workflows/tests.yml
        
.. image:: https://codecov.io/github/rmax/scrapy-redis/coverage.svg?branch=master
        :alt: Coverage Status
        :target: https://codecov.io/github/rmax/scrapy-redis

.. image:: https://img.shields.io/badge/security-bandit-green.svg
        :alt: Security Status
        :target: https://github.com/rmax/scrapy-redis
    
Redis-based components for Scrapy.

* Usage: https://github.com/rmax/scrapy-redis/wiki/Usage
* Documentation: https://github.com/rmax/scrapy-redis/wiki.
* Release: https://github.com/rmax/scrapy-redis/wiki/History
* Contribution: https://github.com/rmax/scrapy-redis/wiki/Getting-Started
* LICENSE: MIT license

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

* In this forked version: added ``json`` supported data in Redis

    data contains ``url``, ```meta``` and other optional parameters. ``meta`` is a nested json which contains sub-data.
    this function extract this data and send another FormRequest with ``url``, ``meta`` and addition ``formdata``.

    For example:

    .. code-block:: json

        { "url": "https://exaple.com", "meta": {"job-id":"123xsd", "start-date":"dd/mm/yy"}, "url_cookie_key":"fertxsas" }

    this data can be accessed in `scrapy spider` through response.
    like: `request.url`, `request.meta`, `request.cookies`
    
.. note:: This features cover the basic case of distributing the workload across multiple workers. If you need more features like URL expiration, advanced URL prioritization, etc., we suggest you to take a look at the Frontera_ project.

Requirements
------------

* Python 3.7+
* Redis >= 5.0
* ``Scrapy`` >=  2.0
* ``redis-py`` >= 4.0

Installation
------------

From pip 

.. code-block:: bash

    pip install scrapy-redis

From GitHub

.. code-block:: bash

    git clone https://github.com/darkrho/scrapy-redis.git
    cd scrapy-redis
    python setup.py install

.. note:: For using this json supported data feature, please make sure you have not installed the scrapy-redis through pip. If you already did it, you first uninstall that one.
  
.. code-block:: bash

    pip uninstall scrapy-redis

Alternative Choice
---------------------------

Frontera_  is a web crawling framework consisting of `crawl frontier`_, and distribution/scaling primitives, allowing to build a large scale online web crawler.

.. _Frontera: https://github.com/scrapinghub/frontera
.. _crawl frontier: http://nlp.stanford.edu/IR-book/html/htmledition/the-url-frontier-1.html
