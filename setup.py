#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import os, sys

from setuptools import setup, find_packages, Extension

if __name__ == "__main__":

    setup(
        name='taptapstats',
        author='Amber Brown',
        author_email='hawkowl@twistedmatrix.com',
        url="https://github.com/twisted/iocpreactor",
        classifiers = [
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.5",
        ],
        use_incremental=True,
        setup_requires=['incremental'],
        install_requires=['incremental', 'twisted'],
        package_dir={"": "src"},
        packages=find_packages('src') + ["twisted.plugins"],
        package_data={
            "twisted": ["plugins/taptap.py"]
        },
        license="MIT",
        zip_safe=False,
        include_package_data=True,
        description='Personal writing stats.',
        long_description=open('README.rst').read(),
    )
