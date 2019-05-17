# SPDX-License-Identifier: AGPL-3.0-or-later
import os
from setuptools import setup, find_packages
import subprocess


install_requires = [
    'bjoern>=2.2.2',
    'bsddb3',
    'falcon==1.4.1',
    'jsonschema>=2.5.0',
    'python-dateutil',
    'pytz',
    'requests',
    'setproctitle',
    'ujson>=1.35'
]


version = '0.0.0+unreleased'
here = os.path.abspath(os.path.dirname(__file__))
if os.path.exists(os.path.join(here, '.version')):
    with open(os.path.join(here, '.version'), 'r') as version_file:
        version = version_file.read().strip()
elif os.path.exists(os.path.join(here, '.git')):
    cmd = 'git describe --tags --always --dirty --match=v*'
    v = subprocess.check_output(cmd.split(' '), cwd=here).decode('utf-8').replace('-', '+', 1)
    if v.startswith('v'):
        v = v[1:]
    version = v.strip()

setup(
    name='grapi',
    version=version,

    description='',
    long_description='',

    author='Kopano',
    author_email='development@kopano.io',
    license='AGPL',

    install_requires=install_requires,

    packages=find_packages(include=['grapi', 'grapi.*']),
    zip_safe=False,

    entry_points={
        'console_scripts': [
            'kopano-grapi-mfr = grapi.mfr:main'
        ]
    }
)
