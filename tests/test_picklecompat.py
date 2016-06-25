from scrapy_redis import picklecompat


def test_picklecompat():
    obj = {'_encoding': 'utf-8',
        'body': '',
        'callback': '_response_downloaded',
        'cookies': {},
        'dont_filter': False,
        'errback': None,
        'headers': {'Referer': ['http://www.dmoz.org/']},
        'meta': {'depth': 1, 'link_text': u'Fran\xe7ais', 'rule': 0},
        'method': 'GET',
        'priority': 0,
        'url': u'http://www.dmoz.org/World/Fran%C3%A7ais/',
    }
    assert obj == picklecompat.loads(picklecompat.dumps(obj))
