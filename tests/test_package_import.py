import scrapy_redis


def test_package_metadata():
    assert scrapy_redis.__author__
    assert scrapy_redis.__email__
    assert scrapy_redis.__version__
