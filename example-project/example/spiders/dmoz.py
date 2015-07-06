from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from example.items import ExampleLoader


class DmozSpider(CrawlSpider):
    name = 'dmoz'
    allowed_domains = ['dmoz.org']
    start_urls = ['http://www.dmoz.org/']

    categories_lx = LinkExtractor(restrict_xpaths='//div[@id="catalogs"]')
    directory_lx = LinkExtractor(restrict_xpaths='//ul[@class="directory dir-col"]')

    rules = (
        Rule(categories_lx),
        Rule(directory_lx, callback='parse_directory', follow=True)
    )

    def parse_directory(self, response):
        for li in response.css('ul.directory-url > li'):
            el = ExampleLoader(selector=li)
            el.add_css('name', 'a::text')
            el.add_css('description', '::text')
            el.add_css('link', 'a::attr(href)')
            el.add_value('url', response.url)
            yield el.load_item()
