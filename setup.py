#!/usr/bin/env python
import io
from pkgutil import walk_packages

from setuptools import setup


def find_packages(path):
    # This method returns packages and subpackages as well.
    return [name for _, name, is_pkg in walk_packages([path]) if is_pkg]


def read_file(filename):
    with open(filename) as fp:
        return fp.read().strip()


def read_rst(filename):
    # Ignore unsupported directives by pypi.
    content = read_file(filename)
    return "".join(
        line for line in io.StringIO(content) if not line.startswith(".. comment::")
    )


def read_requirements(filename):
    return [
        line.strip()
        for line in read_file(filename).splitlines()
        if not line.startswith("#")
    ]


setup(
    name="scrapy-redis",
    version=read_file("VERSION"),
    description="Redis-based components for Scrapy.",
    long_description=read_rst("README.rst") + "\n\n" + read_rst("HISTORY.rst"),
    author="R Max Espinoza",
    author_email="hey@rmax.dev",
    url="https://github.com/rmax/scrapy-redis",
    packages=list(find_packages("src")),
    package_dir={"": "src"},
    install_requires=read_requirements("requirements.txt"),
    include_package_data=True,
    license="MIT",
    keywords="scrapy-redis",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
