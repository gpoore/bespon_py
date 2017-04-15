# -*- coding: utf-8 -*-
#
# Copyright (c) 2016-2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


import sys
import os
# Get a version of open() that can handle encoding
if sys.version_info.major == 2:
    from io import open
import collections


if (sys.version_info < (2, 7) or
        (sys.version_info.major == 3 and sys.version_info < (3, 3))):
    sys.exit('BespON requires Python 2.7 or 3.3+')

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


# Extract the version from version.py
# First load functions from fmtversion.py that are needed by version.py
fname = os.path.join(os.path.dirname(__file__), 'bespon', 'fmtversion.py')
with open(fname, 'rb') as f:
    c = compile(f.read(), 'bespon/fmtversion.py', 'exec')
    exec(c)
fname = os.path.join(os.path.dirname(__file__), 'bespon', 'version.py')
with open(fname, 'r', encoding='utf8') as f:
    t = ''.join([line for line in f.readlines() if line.startswith('__version__')])
    if not t:
        raise RuntimeError('Failed to extract version from "version.py"')
    c = compile(t, 'bespon/version.py', 'exec')
    exec(c)
version = __version__

fname = os.path.join(os.path.dirname(__file__), 'README.rst')
with open(fname, encoding='utf8') as f:
    long_description = f.read()


setup(name = 'BespON',
      version = version,
      py_modules = [],
      packages = ['bespon'],
      description = 'Python library for BespON',
      long_description = long_description,
      author = 'Geoffrey M. Poore',
      author_email = 'gpoore@gmail.com',
      url = 'http://github.com/gpoore/bespon_py',
      license = 'BSD',
      keywords = ['configuration', 'serialization', 'interchange'],
      # https://pypi.python.org/pypi?:action=list_classifiers
      classifiers = [
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: Information Technology',
          'Intended Audience :: Science/Research',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Topic :: Utilities',
      ]
)
