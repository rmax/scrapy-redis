import os
from setuptools import setup


LONG_DESC = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()


setup(name='scrapy-redis',
      version='0.6.0',
      description='Redis-based components for Scrapy',
      long_description=LONG_DESC,
      author='Rolando Espinoza La fuente',
      author_email='darkrho@gmail.com',
      url='http://github.com/darkrho/scrapy-redis',
      packages=['scrapy_redis'],
      license='BSD',
      install_requires=['Scrapy>=1.0.0', 'redis>=2.10.0'],
      classifiers=[
          'Programming Language :: Python',
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
      ],
     )
