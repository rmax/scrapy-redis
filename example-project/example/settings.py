# Scrapy settings for example project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

BOT_NAME = 'example'
BOT_VERSION = '1.0'

SPIDER_MODULES = ['example.spiders']
NEWSPIDER_MODULE = 'example.spiders'
USER_AGENT = '%s/%s' % (BOT_NAME, BOT_VERSION)

SCHEDULER = "scrapy_redis.scheduler.Scheduler"
SCHEDULER_PERSIST = True

ITEM_PIPELINES = [
    'example.pipelines.ExamplePipeline',
    'scrapy_redis.pipelines.RedisPipeline',
]
