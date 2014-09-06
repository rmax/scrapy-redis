from scrapy.selector import Selector
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.contrib.spiders import CrawlSpider, Rule
from example.items import ExampleLoader

class DmozSpider(CrawlSpider):
    name = 'dmoz'
    allowed_domains = ['dmoz.org']
    start_urls = ['http://www.dmoz.org/']

    rules = (
        Rule(SgmlLinkExtractor(restrict_xpaths='//div[@id="catalogs"]')),
        Rule(SgmlLinkExtractor(restrict_xpaths='//ul[@class="directory dir-col"]'),
             callback='parse_directory', follow=True)
    )

    def parse_directory(self, response):
        hxs = Selector(response)
        for li in hxs.xpath('//ul[@class="directory-url"]/li'):
            el = ExampleLoader(selector=li)
            el.add_xpath('name', 'a/text()')
            el.add_xpath('description', 'text()')
            el.add_xpath('link', 'a/@href')
            el.add_value('url', response.url)
            yield el.load_item()
