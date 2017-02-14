=======
History
=======

.. comment:: bumpversion marker

0.7.0-dev (unreleased)
------------------
* Unreleased.

0.6.8 (2017-02-14)
------------------
* Fixed automated release due to not matching registered email.

0.6.7 (2016-12-27)
------------------
* Fixes bad formatting in logging message.

0.6.6 (2016-12-20)
------------------
* Fixes wrong message on dupefilter duplicates.

0.6.5 (2016-12-19)
------------------
* Fixed typo in default settings.

0.6.4 (2016-12-18)
------------------
* Fixed data decoding in Python 3.x.
* Added ``REDIS_ENCODING`` setting (default ``utf-8``).
* Default to ``CONCURRENT_REQUESTS`` value for ``REDIS_START_URLS_BATCH_SIZE``.
* Renamed queue classes to a proper naming conventiong (backwards compatible).

0.6.3 (2016-07-03)
------------------
* Added ``REDIS_START_URLS_KEY`` setting.
* Fixed spider method ``from_crawler`` signature.

0.6.2 (2016-06-26)
------------------
* Support ``redis_cls`` parameter in ``REDIS_PARAMS`` setting.
* Python 3.x compatibility fixed.
* Added ``SCHEDULER_SERIALIZER`` setting.

0.6.1 (2016-06-25)
------------------
* **Backwards incompatible change:** Require explicit ``DUPEFILTER_CLASS``
  setting.
* Added ``SCHEDULER_FLUSH_ON_START`` setting.
* Added ``REDIS_START_URLS_AS_SET`` setting.
* Added ``REDIS_ITEMS_KEY`` setting.
* Added ``REDIS_ITEMS_SERIALIZER`` setting.
* Added ``REDIS_PARAMS`` setting.
* Added ``REDIS_START_URLS_BATCH_SIZE`` spider attribute to read start urls
  in batches.
* Added ``RedisCrawlSpider``.

0.6.0 (2015-07-05)
------------------
* Updated code to be compatible with Scrapy 1.0.
* Added `-a domain=...` option for example spiders.

0.5.0 (2013-09-02)
------------------
* Added `REDIS_URL` setting to support Redis connection string.
* Added `SCHEDULER_IDLE_BEFORE_CLOSE` setting to prevent the spider closing too
  quickly when the queue is empty. Default value is zero keeping the previous
  behavior.
* Schedule preemptively requests on item scraped.
* This version is the latest release compatible with Scrapy 0.24.x.

0.4.0 (2013-04-19)
------------------
* Added `RedisSpider` and `RedisMixin` classes as building blocks for spiders
  to be fed through a redis queue.
* Added redis queue stats.
* Let the encoder handle the item as it comes instead converting it to a dict.

0.3.0 (2013-02-18)
------------------
* Added support for different queue classes.
* Changed requests serialization from `marshal` to `cPickle`.

0.2.0 (2013-02-17)
------------------
* Improved backward compatibility.
* Added example project.

0.1.0 (2011-09-01)
------------------
* First release on PyPI.
