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
import random

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


def test_parse_str_empty():
    dc = mdl.BespONDecoder()
    assert(dc.parse_str_empty(['']) == '')
    assert(dc.parse_str_empty(['', '']) == '')
    with pytest.raises(err.ParseError):
        dc.parse_str_empty(['\n'])


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


def test_parse_bin_empty():
    dc = mdl.BespONDecoder()
    assert(dc.parse_bin_empty(['']) == b'')
    assert(dc.parse_bin_empty(['', '']) == b'')
    with pytest.raises(err.ParseError):
        dc.parse_bin_empty(['\n'])


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


def test__drop_bom():
    dc = mdl.BespONDecoder()
    s = '\xEF\xBB\xBF\uFEFF'
    with pytest.raises(ValueError):
        dc._drop_bom(s)

    s = '\uFFFE\xEF\xBB\xBF'
    with pytest.raises(ValueError):
        dc._drop_bom(s)

    s = '\xEF\xBB\xBF%!bespon \r\n'
    assert(dc._drop_bom(s) == '%!bespon \r\n')


def test__split_line_on_indent():
    dc = mdl.BespONDecoder()
    s = '\x20\u3000\t\x20\t\t\x20\u3000\r\n'
    assert(dc._split_line_on_indent(s) == (s[:-2], '\r\n'))


def test_int_re():
    dc = mdl.BespONDecoder()
    assert(dc._int_re.match('1'))
    assert(dc._int_re.match('1234567890'))
    assert(dc._int_re.match('1_23456789_0'))
    assert(not dc._int_re.match('_1234567890'))
    assert(not dc._int_re.match('1234567890_'))
    assert(not dc._int_re.match('123456__7890'))
    assert(dc._int_re.match('0xABCDEF0123456789'))
    assert(dc._int_re.match('0xabcdef0123456789'))
    assert(dc._int_re.match('0x0123456789abcdef'))
    assert(dc._int_re.match('0x0_1_23456789abcd_e_f'))
    assert(not dc._int_re.match('_0x0123456789abcdef'))
    assert(not dc._int_re.match('0_x0123456789abcdef'))
    assert(not dc._int_re.match('0x_0123456789abcdef'))
    assert(not dc._int_re.match('0x0123456789abcdef_'))
    assert(dc._int_re.match('0o01234567'))
    assert(dc._int_re.match('0o7654321'))
    assert(dc._int_re.match('0o7_65432_1'))
    assert(not dc._int_re.match('_0o7654321'))
    assert(not dc._int_re.match('0_o7654321'))
    assert(not dc._int_re.match('0o_7654321'))
    assert(not dc._int_re.match('0o7654321_'))
    assert(not dc._int_re.match('0o765__4321'))
    assert(dc._int_re.match('0b0'))
    assert(dc._int_re.match('0b01'))
    assert(dc._int_re.match('0b10'))
    assert(dc._int_re.match('0b1_1_0'))
    assert(not dc._int_re.match('_0b11011'))
    assert(not dc._int_re.match('0_b11011'))
    assert(not dc._int_re.match('0b_11011'))
    assert(not dc._int_re.match('0b11011_'))
    assert(not dc._int_re.match('0b110__11'))
    assert(all(dc._int_re.match(str(random.randint(-1000000, 1000000))) for n in range(1000)))
    assert(all(dc._int_re.match(hex(random.randint(-1000000, 1000000))) for n in range(1000)))


def test_float_re():
    dc = mdl.BespONDecoder()
    assert(dc._float_re.match('0e0'))
    assert(dc._float_re.match('+0e0'))
    assert(dc._float_re.match('-0e0'))
    assert(dc._float_re.match('0e+0'))
    assert(dc._float_re.match('0e-0'))
    assert(dc._float_re.match('1.'))
    assert(dc._float_re.match('-1.'))
    assert(dc._float_re.match('+1.'))
    assert(dc._float_re.match('1.e1'))
    assert(dc._float_re.match('-1.e1'))
    assert(dc._float_re.match('+1.e1'))
    assert(dc._float_re.match('0.12'))
    assert(dc._float_re.match('-0.12'))
    assert(dc._float_re.match('+0.12'))
    assert(dc._float_re.match('.0e0'))
    assert(dc._float_re.match('12e3'))
    assert(dc._float_re.match('12e+3'))
    assert(dc._float_re.match('12e-3'))
    assert(dc._float_re.match('3.14e5'))
    assert(dc._float_re.match('+3.14e5'))
    assert(dc._float_re.match('-3.14e5'))
    assert(dc._float_re.match('1_231_4.2_3_3e3_5_2'))
    assert(not dc._float_re.match('_12314.233e352'))
    assert(not dc._float_re.match('12314_.233e352'))
    assert(not dc._float_re.match('12314._233e352'))
    assert(not dc._float_re.match('_12314.233_e352'))
    assert(not dc._float_re.match('12314.233e_352'))
    assert(not dc._float_re.match('12314.233e352_'))
    assert(dc._float_re.match('0x3.a7p10'))
    assert(dc._float_re.match('0x3p10'))
    assert(dc._float_re.match('0x3.p10'))
    assert(dc._float_re.match('0x.a7p10'))
    assert(dc._float_re.match('0x1_d_e.a_4_f7p+1_3_0'))
    assert(not dc._float_re.match('0x1_d_e.a_4_f7p+1_3_f'))
    assert(not dc._float_re.match('_0x1de.a4f7p130'))
    assert(not dc._float_re.match('0_x1de.a4f7p130'))
    assert(not dc._float_re.match('0x_1de.a4f7p130'))
    assert(not dc._float_re.match('0x1de_.a4f7p130'))
    assert(not dc._float_re.match('0x1de._a4f7p130'))
    assert(not dc._float_re.match('0x1de.a4f7_p130'))
    assert(not dc._float_re.match('0x1de.a4f7p_130'))
    assert(not dc._float_re.match('0x1de.a4f7p130_'))
    assert(all(dc._float_re.match(str(random.uniform(-1e9, 1e9))) for n in range(1000)))
    assert(all(dc._float_re.match(float.hex(random.uniform(-1e9, 1e9))) for n in range(1000)))




def test_decode_basic():
    dc = mdl.BespONDecoder()

    dc.decode('')
    assert(dc._ast == [])

    dc.decode('\xEF\xBB\xBF')
    assert(dc._ast == [])
