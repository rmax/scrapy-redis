from scrapy_redis.spiders import RedisMixin

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor

from example.items import ExampleLoader


class MyCrawler(RedisMixin, CrawlSpider):
    """Spider that reads urls from redis queue (myspider:start_urls)."""
    name = 'mycrawler_redis'
    redis_key = 'mycrawler:start_urls'

    rules = (
        # follow all links
        Rule(SgmlLinkExtractor(), callback='parse_page', follow=True),
    )

    def set_crawler(self, crawler):
        CrawlSpider.set_crawler(self, crawler)
        RedisMixin.setup_redis(self)

    def parse_page(self, response):
        el = ExampleLoader(response=response)
        el.add_xpath('name', '//title[1]/text()')
        el.add_value('url', response.url)
        return el.load_item()
