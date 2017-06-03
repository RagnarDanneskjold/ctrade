#!/usr/bin/env python

from setuptools import setup, find_packages
import sys


requires = [
    'numpy', 'pandas'
]
if sys.version_info[0] <= 2:
    py2_requires = ['contextlib2']
    requires += py2_requires

setup(
    name='ctrade',
    version='0.0',
    description="Wrapper for Poloniex API",
    author="Giovanni Doni",
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'mock'],
    install_requires=requires,
    packages=find_packages(),
    include_package_data=True
)
