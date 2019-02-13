# SPDX-License-Identifier: AGPL-3.0-or-later
from setuptools import setup, find_packages

setup(name='grapi',
      version='1',

      description='',
      long_description='',

      author='Kopano',
      author_email='development@kopano.io',
      license='AGPL',

      packages=find_packages(include=['grapi', 'grapi.*']),
      zip_safe=False
      )
