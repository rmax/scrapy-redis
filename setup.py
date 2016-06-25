#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pkgutil import walk_packages
from setuptools import setup


def find_packages(path):
    # This method returns packages and subpackages as well.
    for _, name, is_pkg in walk_packages([path]):
        if is_pkg:
            yield name


def read_file(filename):
    with open(filename) as fp:
        return fp.read()


requirements = [
    'Scrapy>=1.0',
    'redis>=2.10',
    'six>=1.5.2',
]

requirements_setup = [
]

setup(
    name='scrapy-redis',
    version='0.6.2',
    description="Redis-based components for Scrapy.",
    long_description=read_file('README.rst') + '\n\n' + read_file('HISTORY.rst'),
    author="Rolando Espinoza",
    author_email='rolando at rmax.io',
    url='https://github.com/rolando/scrapy-redis',
    packages=list(find_packages('src')),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=requirements,
    license="MIT",
    keywords='scrapy-redis',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    setup_requires=requirements_setup,
)
