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
    str = unicode
    __chr__ = chr
    chr = unichr

if all(os.path.isdir(x) for x in ('bespon', 'test', 'doc')):
    sys.path.insert(0, '.')

import bespon.decoding as mdl
import bespon.erring as err

import pytest


def test__unwrap_inline():
    dc = mdl.BespONDecoder()
    s = 'first\nsecond\nthird'
    assert(dc._unwrap_inline(s.splitlines(True)) == s.replace('\n', ' '))
    t = 'first \nsecond \nthird'
    assert(dc._unwrap_inline(t.splitlines(True)) == s.replace('\n', ' '))
    u = 'first  \nsecond  \nthird'
    assert(dc._unwrap_inline(u.splitlines(True)) == u.replace('\n', ''))
    v = 'first\u3000\nsecond\u3000\nthird'
    assert(dc._unwrap_inline(v.splitlines(True)) == v.replace('\n', ''))


def test_parse_str():
    dc = mdl.BespONDecoder()
    s = 'first \nsecond \nthird'
    assert(dc.parse_str(s.splitlines(True)) == s)
    assert(dc.parse_str(s.splitlines(True), inline=True) == s.replace('\n', ''))


def test_parse_str_esc():
    dc = mdl.BespONDecoder()
    s = '\\a\\b\\v\\f\\n\\r\\t\\u1234\\x01ABCD'
    s_after = '\a\b\v\f\n\r\t\u1234\x01ABCD'
    assert(dc.parse_str_esc(s.splitlines(True)) == s_after)


def test_parse_bin():
    dc = mdl.BespONDecoder()
    s = 'ABCDEFG\a\b\f\v'
    assert(dc.parse_bin(s.splitlines(True)) == s.encode('ascii'))

    with pytest.raises(err.BinaryStringEncodeError):
        t = 'ABCDEFG\a\b\f\v\u00ff'
        dc.parse_bin(t.splitlines(True))

    with pytest.raises(err.BinaryStringEncodeError):
        t = 'ABCDEFG\a\b\f\v\xff'
        dc.parse_bin(t.splitlines(True))


def test_parse_bin_esc():
    dc = mdl.BespONDecoder()
    s = 'ABCDEFG\\a\\b\\f\\v\\x01\\xff'
    b_esc = b'ABCDEFG\a\b\f\v\x01\xff'
    assert(dc.parse_bin_esc(s.splitlines(True)) == b_esc)

    with pytest.raises(err.UnknownEscapeError):
        t = 'ABCDEFG\\a\\b\\f\\v\\x01\\xff\\uffff'
        dc.parse_bin_esc(t.splitlines(True))


def test_parse_bin_base64():
    dc = mdl.BespONDecoder()
    s = 'AQIECBav/w=='
    b = b'\x01\x02\x04\x08\x16\xaf\xff'
    assert(dc.parse_bin_base64(s.splitlines(True)) == b)

    with pytest.raises(err.BinaryBase64DecodeError):
        s = '\u2028AQIECBav/w=='
        dc.parse_bin_base64(s.splitlines(True))


def test_parse_bin_hex():
    dc = mdl.BespONDecoder()
    s = '0102040816AFFF'
    b = b'\x01\x02\x04\x08\x16\xaf\xff'
    assert(dc.parse_bin_base16(s.splitlines(True)) == b)

    with pytest.raises(err.BinaryBase16DecodeError):
        s = '\u20280102040816AFFF'
        dc.parse_bin_base16(s.splitlines(True))
