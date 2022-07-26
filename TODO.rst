TODO
====

* Add SCRAPY_JOB global support (jobs sharing same SCRAPY_JOB share same queues).
* Use a spider middleware instead of spider mixin. This will avoid the spider
  idle signal hack.
* Allow to use pubsub whenever appropriate.
* Move example project to its own repository. Include different crawling use
  cases (i.e.: producer/consumer).
* Add pyrebloom dupefilter.
* Warn and pass unserializable requests.
