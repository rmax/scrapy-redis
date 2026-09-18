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
* ``redis-py`` >= 4.2

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

Settings
--------

Idle Redis queue polling can be reduced with opt-in, deadline-gated exponential
backoff:

* ``REDIS_IDLE_BACKOFF_ENABLED`` (default ``False``) enables idle-poll backoff.
* ``REDIS_IDLE_BACKOFF_MIN`` (default ``1.0``) is the initial delay in seconds.
* ``REDIS_IDLE_BACKOFF_MAX`` (default ``30.0``) caps the delay in seconds.
* ``REDIS_IDLE_BACKOFF_FACTOR`` (default ``2.0``) multiplies the delay after
  each empty poll.

When enabled, the spider never blocks the reactor: while waiting for the next
poll deadline it skips all Redis calls. The close deadline is still checked on
every idle callback. The tradeoff is that new work may take up to the
backoff cap to be picked up, while idle Redis load is reduced when many
workers share a queue.

Connection pooling
~~~~~~~~~~~~~~~~~~

Components of one crawler share a single Redis connection pool when using the
default client class and plain connection parameters. Pools are scoped per
``Settings`` object (crawler). Configurations with custom client classes or
client-only parameters (``ssl``, ``unix_socket_path``,
``single_connection_client``) keep the previous per-component behavior.

* ``REDIS_MAX_CONNECTIONS``: Maximum connections in the shared pool (default:
  no override is applied — redis-py's own pool default, effectively unlimited
  on redis-py 4.x/5.x). It raises ``ConnectionError`` when exhausted; supply a
  ``BlockingConnectionPool`` via ``REDIS_PARAMS.connection_pool``
  (``REDIS_PARAMS["connection_pool"]``) for waiting semantics.

Connection setup, protocols, and timeouts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

redis-py 8 changed its default connection protocol to RESP3. Selecting a
protocol changes connection setup only; it does not remove timeout risk from
warm operations on already-established connections.
The ``REDIS_PROTOCOL`` setting defaults to ``None``, leaving redis-py's
installed-version default unchanged.

On redis-py >= 5, the recommended, discoverable form for opting into RESP2 is:

.. code-block:: python

    REDIS_PROTOCOL = 2

The existing equivalent form remains supported:

.. code-block:: python

    REDIS_PARAMS = {"protocol": 2}

Both forms require redis-py >= 5. ``REDIS_PROTOCOL`` takes precedence when
both settings specify a protocol. As optional advanced tuning on redis-py >=
5, you can also omit redis-py's connection identification metadata:

.. code-block:: python

    REDIS_PARAMS = {"driver_info": None}

This can reduce connection-setup work, but loses useful client-identification
metadata in exchange.

The library's historical ``retry_on_timeout=True`` default is deprecated and
has no effect on redis-py >= 6. On those versions, the effective retry policy
comes from redis-py's ``retry`` object and its defaults. Measure the resulting
behavior before lowering retries, especially under connection churn or
saturation.

In testing with Redis 8.0.2, ``CLIENT MAINT_NOTIFICATIONS`` was rejected during
RESP3 connection setup. This observation is scoped to the tested Redis 8.0.2
version. The rejection is not shown by ``MONITOR`` or commandstats; inspect
client logs and Redis's ``total_error_replies`` counter for diagnostics.

The connection-related behavior by redis-py version is summarized below:

.. list-table::
   :header-rows: 1

   * - redis-py
     - Connection setup notes
   * - 4.2–4.x
     - No ``protocol`` or ``driver_info`` knobs.
   * - 5.x
     - Both knobs are available; RESP2 is the default.
   * - 6.x–7.x
     - RESP2 is the default; retry semantics changed in 6.x, and
       ``CLIENT MAINT_NOTIFICATIONS`` is used on explicit RESP3 from 7.x.
   * - 8.x
     - RESP3 is the default.

Alternative Choice
---------------------------

Frontera_  is a web crawling framework consisting of `crawl frontier`_, and distribution/scaling primitives, allowing to build a large scale online web crawler.

.. _Frontera: https://github.com/scrapinghub/frontera
.. _crawl frontier: http://nlp.stanford.edu/IR-book/html/htmledition/the-url-frontier-1.html
