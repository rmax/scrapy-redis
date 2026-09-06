import asyncio
import scrapy
from scrapy_redis.spiders import RedisMixin


class TestSpider(RedisMixin, scrapy.Spider):
    name = "test_spider"

    def next_requests(self):
        yield scrapy.Request("https://example.com/1")
        yield scrapy.Request("https://example.com/2")


async def collect_start_requests(spider):
    return [request async for request in spider.start()]


def test_async_start():
    spider = TestSpider()

    requests = asyncio.run(
        collect_start_requests(spider)
    )

    assert len(requests) == 2
    assert requests[0].url == "https://example.com/1"
    assert requests[1].url == "https://example.com/2"


def test_start_requests():
    spider = TestSpider()

    requests = list(spider.start_requests())

    assert len(requests) == 2
    assert requests[0].url == "https://example.com/1"
    assert requests[1].url == "https://example.com/2"