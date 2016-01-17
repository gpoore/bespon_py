# -*- coding: utf-8 -*-
#
# Copyright (c) 2015, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


from __future__ import (division, print_function, absolute_import,
                        unicode_literals)


import sys
import os

if sys.version_info.major == 2:
    # Make `str()`, `bytes()`, and related used of `isinstance()` like Python 3
    __str__ = str
    class bytes(__str__):
        '''
        Emulate Python 3's bytes type.  Only for use with Unicode strings.
        '''
        def __new__(cls, obj, encoding=None, errors='strict'):
            if not isinstance(obj, unicode):
                raise TypeError('the bytes type only supports Unicode strings')
            elif encoding is None:
                raise TypeError('string argument without an encoding')
            else:
                return __str__.__new__(cls, obj.encode(encoding, errors))
    str = unicode

if all(os.path.isdir(x) for x in ('bespon', 'test', 'doc')):
    sys.path.insert(0, '.')

import bespon.decoding as mdl
import bespon.erring as err

import pytest


def test__unwrap():
    decoder = mdl.BespONDecoder()
    s = '  abc\n  def\n  ghi\n'
    assert(decoder.unwrap(s.splitlines(True)) == s.replace('\n', ' ').rstrip(' ') + '\n')
    t = s.replace('\n', ' \n')
    assert(decoder.unwrap(t.splitlines(True)) == s.replace('\n', ' ') + '\n')
    u = s + '\t\nxyz\n'
    assert(decoder.unwrap(u.splitlines(True)) == s.replace('\n', ' ').rstrip(' ') + '\nxyz\n')
    v = s + '\t\nxyz\n\t\n'
    assert(decoder.unwrap(v.splitlines(True)) == s.replace('\n', ' ').rstrip(' ') + '\nxyz\n')

    inline_s = '  abc\n  def\n  ghi'
    assert(decoder.unwrap(inline_s.splitlines(True), inline=True) == inline_s.replace('\n', ' '))
    inline_t = inline_s.replace('\n', ' \n')
    assert(decoder.unwrap(inline_t.splitlines(True), inline=True) == inline_t.replace('\n', ''))


def test__xunwrap():
    decoder = mdl.BespONDecoder()
    s = '  abc\n  def\n  ghi\n'
    assert(decoder.xunwrap(s.splitlines(True)) == s.replace('\n', '') + '\n')
    t = s.replace('\n', ' \n')
    assert(decoder.xunwrap(t.splitlines(True)) == s.replace('\n', ' ') + '\n')
    u = s + '\n'
    assert(decoder.xunwrap(u.splitlines(True)) == s.replace('\n', '') + '\n')
    v = s + '\n\t \u3000\n'
    assert(decoder.xunwrap(v.splitlines(True)) == s.replace('\n', '') + '\n\n')
