import scrapy
import pytest

from scrapy_redis.spiders import RedisMixin


class TestSpider(RedisMixin, scrapy.Spider):
    name = "test_spider"

    def next_requests(self):
        yield scrapy.Request("https://example.com/1")
        yield scrapy.Request("https://example.com/2")


@pytest.mark.asyncio
async def test_async_start():
    spider = TestSpider()

    requests = [request async for request in spider.start()]

    assert len(requests) == 2
    assert requests[0].url == "https://example.com/1"
    assert requests[1].url == "https://example.com/2"


def test_start_requests():
    spider = TestSpider()

    requests = list(spider.start_requests())

    assert len(requests) == 2
    assert requests[0].url == "https://example.com/1"
    assert requests[1].url == "https://example.com/2"
