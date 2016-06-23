#@IgnoreInspection BashAddShebang
FROM python:2.7-onbuild

RUN mkdir -p /var/app
WORKDIR /var/app

ADD example-project /var/app

RUN pip install scrapy_redis

ENTRYPOINT ["scrapy", "crawl", "dmoz"]
CMD ["-s", "LOG_LEVEL=DEBUG", "-s", "CONCURRENT_REQUESTS=8"]