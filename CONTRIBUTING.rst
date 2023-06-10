.. highlight:: shell

============
Contribution
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

New to here
~~~~~~~~~~~

Any issue with good first issue tag on it is a great place to start! Feel free to ask any questions here.

Don't know how to start
~~~~~~~~~~~

Review codebases and PRs can give you quite a knowledge to know what's going on here!

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/rmax/scrapy-redis/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to implement it.

Implement Features & imporvments
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "feature" or "improvments"
is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

Scrapy-Redis could always use more documentation, whether as part of the
official Scrapy-Redis docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/rmax/scrapy-redis/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `scrapy-redis` for local development.

Setup environment
~~~~~~~~~~~~~~~

1. Fork the `scrapy-redis` repo on GitHub.
2. Clone your fork locally::

       git clone git@github.com:your_name_here/scrapy-redis.git

3. Install your local copy into a virtualenv. Assuming you have virtualenvwrapper installed, this is how you set up your fork for local development::

       pip install virtualenv==20.0.23
       virtualenv --python=/usr/bin/python3 ~/scrapy_redis
       source ~/scrapy_redis/bin/activate
       cd scrapy-redis/
       pip install -r requirements-install.txt
       pip install .

4. Create a branch for local development::

       git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

Setup testing environment
~~~~~~~~~~~~~~~

1. When you're done making changes, check that your changes pass flake8 and the tests, including testing other Python versions with tox::

       pip install -r requirements-tests.txt
       flake8 src/ tests/
       python -m pytest --ignore=setup.py
       tox

2. Note that if the error of `No module named scrapy_redis` shows, please check the install `scrapy-redis` of your branch by::
   
       pip install .

3. Or change the import lines::

       from scrapy_redis import xxx # from this
       from src.scrapy_redis import xxx # to this

4. Commit your changes and push your branch to GitHub::

       git add .
       git commit -m "Your detailed description of your changes."
       git push origin name-of-your-bugfix-or-feature

5. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for Python 2.6, 2.7, 3.3, 3.4 and 3.5, and for PyPy. Check
   https://travis-ci.org/rolando/scrapy-redis/pull_requests
   and make sure that the tests pass for all supported Python versions.

Tips
----

To run a subset of tests::

    pytest tests/test_scrapy_redis
