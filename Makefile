.PHONY: clean-so clean-test clean-pyc clean-build clean-docs clean
.PHONY: docs check check-manifest check-setup check-history lint
.PHONY: test test-all coverage
.PHONY: compile-reqs install-reqs
.PHONY: release dist install build-inplace
define BROWSER_PYSCRIPT
import os, webbrowser, sys
try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT
BROWSER := python -c "$$BROWSER_PYSCRIPT"

SPHINX_BUILD := html

help:
	@echo "check - check setup, code style, setup, etc"
	@echo "check-manifest - check manifest"
	@echo "check-setup - check setup"
	@echo "check-history - check history"
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-docs - remove docs artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "clean-so - remove compiled extensions"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "compile-reqs - compile requirements"
	@echo "install-reqs - install requirements"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "dist-upload - package and upload a release"
	@echo "release - bump release and push changes"
	@echo "dist - package"
	@echo "develop - install package in develop mode"
	@echo "install - install the package to the active Python's site-packages"

check: check-setup check-manifest check-history lint

check-setup:
	@echo "Checking package metadata (name, description, etc)"
	python setup.py check --strict --metadata --restructuredtext

check-manifest:
	@echo "Checking MANIFEST.in"
	check-manifest --ignore ".*"

check-history:
	@echo "Checking latest version in HISTORY"
	VERSION=`cat VERSION`; grep "^$${VERSION}\b" HISTORY.rst

clean: clean-build clean-docs clean-pyc clean-test clean-so

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-docs:
	$(MAKE) -C docs clean

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

clean-so:
	find . -name '*.so' -exec rm -f {} +

lint:
	flake8 src tests

build-inplace:
	python setup.py build_ext --inplace

develop: clean
	pip install -e .

test: develop
	py.test

test-all:
	tox -v

coverage: develop
	coverage run -m py.test
	coverage combine
	coverage report
	coverage html
	$(BROWSER) htmlcov/index.html

docs-build: develop
	rm -f docs/scrapy_redis.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ src/scrapy_redis
	$(MAKE) -C docs clean
	$(MAKE) -C docs $(SPHINX_BUILD)

docs: docs-build
	$(BROWSER) docs/_build/$(SPHINX_BUILD)/index.html

servedocs: docs
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release:
	@echo "To do a release, follow the steps:"
	@echo "- bumpversion release"
	@echo "- Review and commit"
	@echo "- git tag -a \`cat VERSION\`"
	@echo "- git push --follow-tags"

dist-upload: clean check dist
	twine upload dist/*

dist: clean
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean
	pip install .

REQUIREMENTS_IN := $(wildcard requirements*.in)
.PHONY: $(REQUIREMENTS_IN)

requirements%.txt: requirements%.in
	pip-compile -v $< -o $@

REQUIREMENTS_TXT := $(REQUIREMENTS_IN:.in=.txt)
ifndef REQUIREMENTS_TXT
REQUIREMENTS_TXT := $(wildcard requirements*.txt)
endif

compile-reqs: $(REQUIREMENTS_TXT)
	@test -z "$$REQUIREMENTS_TXT" && echo "No 'requirements*.in' files. Nothing to do"

install-reqs:
	@test -z "$$REQUIREMENTS_TXT" && echo "No 'requirements*.txt' files. Nothing to do"
	$(foreach req,$(REQUIREMENTS_TXT),pip install -r $(req);)
