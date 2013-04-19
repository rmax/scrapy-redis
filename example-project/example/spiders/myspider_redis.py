from scrapy_redis.spiders import RedisSpider
from example.items import ExampleLoader


class MySpider(RedisSpider):
    """Spider that reads urls from redis queue (myspider:start_urls)."""
    name = 'myspider_redis'
    redis_key = 'myspider:start_urls'

    def parse(self, response):
        el = ExampleLoader(response=response)
        el.add_xpath('name', '//title[1]/text()')
        el.add_value('url', response.url)
        return el.load_item()
