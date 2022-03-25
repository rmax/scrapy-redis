#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
from pkgutil import walk_packages
from os.path import dirname, join
from pkg_resources import parse_version
from setuptools import setup, find_packages, __version__ as setuptools_version


with open(join(dirname(__file__), 'VERSION'), 'rb') as f:
    version = f.read().decode('ascii').strip()

def has_environment_marker_platform_impl_support():
    """Code extracted from 'pytest/setup.py'
    https://github.com/pytest-dev/pytest/blob/7538680c/setup.py#L31
    The first known release to support environment marker with range operators
    it is 18.5, see:
    https://setuptools.readthedocs.io/en/latest/history.html#id235
    """
    return parse_version(setuptools_version) >= parse_version('18.5')
    
install_requires = [
    'Scrapy>=1.0',
    'redis>=3.0',
    'six>=1.5.2'
]
tests_require = [
    'coverage',
    'flake8',
    'mock',
    'pytest',
    'tox'
]
extras_require = {}
cpython_dependencies = [
    'lxml>=3.5.0',
    'PyDispatcher>=2.0.5',
]

if has_environment_marker_platform_impl_support():
    extras_require[':platform_python_implementation == "CPython"'] = cpython_dependencies
    extras_require[':platform_python_implementation == "PyPy"'] = [
        # Earlier lxml versions are affected by
        # https://foss.heptapod.net/pypy/pypy/-/issues/2498,
        # which was fixed in Cython 0.26, released on 2017-06-19, and used to
        # generate the C headers of lxml release tarballs published since then, the
        # first of which was:
        'lxml>=4.0.0',
        'PyPyDispatcher>=2.1.0',
    ]
else:
    install_requires.extend(cpython_dependencies)

setup(
    name='scrapy-redis',
    version=version,
    description="Redis-based components for Scrapy.",
    long_description=open('README.rst').read() + '\n\n' + open('HISTORY.rst').read(),
    author="Rolando Espinoza",
    author_email='rolando@rmax.io',
    url='https://github.com/rolando/scrapy-redis',
    packages=find_packages(exclude=('tests', 'tests.*')),
    include_package_data=True,
    zip_safe=False,
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
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
)
