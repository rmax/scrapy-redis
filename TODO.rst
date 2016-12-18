TODO
====

* Test on different redis versions.
* Add SCRAPY_JOB global support (jobs sharing same SCRAPY_JOB share same queues).
* Use a spider middleware instead of spider mixin. This will avoid the spider
  idle signal hack.
* Sync with latest scrapy code (i.e. scheduler, rfpdupefilter, etc).
* Allow to use pubsub whenever appropriate.
* Generalize queue clases (i.e.: LifoQueue, FifoQueue, PriorityQueue,
  PubsubQueue), allow custom serializers, use enqueue, dequeue methods.
* Move example project to its own repository. Include different crawling use
  cases (i.e.: producer/consumer).
* Add pyrebloom dupefilter.
* Warn and pass unserializable requests.
* Drop official support for Scrapy 1.0. It is enough to support current and previous
  scrapy  version.
