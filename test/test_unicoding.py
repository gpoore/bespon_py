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

'''
# It's possible to patch `chr()` and `ord()` on a narrow Python 2.7
# build so that it will pass tests with any code points.  This introduces
# a slowdown of about 8x in test timing compared to Python 3.5, and
# a slowdown of around 40x compared to tests that don't involve points
# 0x10000 and above.  This patching approach is not being used, because
# it could easily introduce bugs (for example, patched `ord()` must accept
# arguments of length 2).  Instead, the tests are written to use whatever
# range of code points works with the current build.  The patching code
# is retained below for future reference.
#
# http://stackoverflow.com/questions/9934752/platform-specific-unicode-semantics-in-python-2-7
# http://stackoverflow.com/questions/7105874/valueerror-unichr-arg-not-in-range0x10000-narrow-python-build-please-hel
#
# Patched `chr()` and `ord()` for narrow builds
try:
    unichr(0x10000)
except ValueError:
    import struct
    def chr(n):
        try:
            return unichr(n)
        except ValueError:
            return struct.pack('i', n).decode('utf-32')
    __ord__ = ord
    def ord(s):
        try:
            return __ord__(s)
        except TypeError:
            if len(s) == 2:
                b = s.encode('UTF-32LE')
                n = struct.unpack('<{}I'.format(len(b) // 4), b)[0]
                if n <= 0x10FFFF:
                    return n
                else:
                    raise
            else:
                raise
'''

try:
    chr(0x10FFFF)
    NARROW_BUILD = False
except ValueError:
    NARROW_BUILD = True


if all(os.path.isdir(x) for x in ('bespon', 'test', 'doc')):
    sys.path.insert(0, '.')

import bespon.unicoding as mdl
import bespon.erring as err

import pytest
import unicodedata
import re


if not NARROW_BUILD:
    MAX_CODE_POINT = 0x10FFFF+1
else:
    MAX_CODE_POINT = 0x10000
unicode_whitespace_re = re.compile('\s', re.UNICODE)
unicode_cc = set([chr(n) for n in range(MAX_CODE_POINT) if unicodedata.category(chr(n)) == 'Cc'])
# Python's `re` package matches `\s` to the separator control characters; `regex` doesn't
# U+180E (Mongolian Vowel Separator) isn't whitespace in Unicode 8.0, but was in Unicode in 4.0-6.3 apparently, which applies to Python 2.7's `re`
unicode_whitespace = set([chr(n) for n in range(MAX_CODE_POINT) if unicode_whitespace_re.match(chr(n)) and n not in range(0x1C, 0x1F+1) and n != 0x180e])


def test_string_constants():
    '''
    Basic testing on code point constants to ensure appropriate length,
    compliance with Unicode, etc.
    '''
    assert(len(mdl.UNICODE_NEWLINES) == 8)
    assert(len(mdl.UNICODE_NEWLINE_CHARS) == 7)

    assert(len(mdl.BESPON_NEWLINES) == 3)

    assert(mdl.UNICODE_CC == unicode_cc)

    assert(len(mdl.BESPON_CC_LITERALS) == 3)

    # Cc minus `\t`, `\r`, `\n`; plus newlines `\u2028` and `\u2029` (other
    # newlines covered in Cc); plus bidi overrides
    assert(len(mdl.BESPON_NONLITERALS) == (65-3) + (7-3-2) + 2)

    assert(len(mdl.UNICODE_ZS) == 17)
    assert(len(mdl.UNICODE_WHITESPACE) == 17 + 7 + 1)
    assert(len(mdl.UNICODE_WHITESPACE) == 25)  # Unicode 8.0
    assert(mdl.UNICODE_WHITESPACE == unicode_whitespace)

    assert(len(mdl.BESPON_INDENTS) == 2)
    assert(len(mdl.BESPON_SPACES) == 1)

    assert(len(mdl.BESPON_SHORT_UNESCAPES)-2 == len(mdl.BESPON_SHORT_ESCAPES))
    assert(all(k.startswith('\\') and len(k) == 2 and ord(k[1]) < 128 for k in mdl.BESPON_SHORT_UNESCAPES))
    assert(all(len(k) == 1 for k in mdl.BESPON_SHORT_ESCAPES))


def test_NonliteralTrace():
    t = mdl.NonliteralTrace('chars', 1, 2)
    assert(len(t) == 3)
    assert(t.chars == 'chars' and t.lineno == 1 and t.unicode_lineno == 2)


def test_python_splitlines():
    '''
    Make sure Python's `splitlines()` supports all linebreaks.

    Also, make sure that `splitlines()` still splits lines at the separator
    characters, since this requires either nonliteral separator characters,
    or special treatment of them.
    '''
    s = '_'.join(mdl.UNICODE_NEWLINES) + '_'
    assert(len(s.splitlines()) == len(mdl.UNICODE_NEWLINES)+1)
    assert(len('_\x1c_\x1d_\x1e_'.splitlines()) == 4)


def test_UnicodeFilter_defaults():
    # Note that many of the translation dicts are defaultdicts, or
    # keydefaultdicts, so any assertions about their lengths must be made
    # before they are ever used; using the dicts will add elements
    uf = mdl.UnicodeFilter()
    assert(uf.nonliterals == mdl.BESPON_NONLITERALS)
    assert('\r\n' not in uf.nonliterals)

    assert(uf.newlines == mdl.BESPON_NEWLINES)
    assert(uf.newline_chars == set(''.join(mdl.BESPON_NEWLINES)))
    assert(len(uf.newline_chars) == len(mdl.BESPON_NEWLINES) - 1)
    assert(len(uf.newline_chars_str) == len(uf.newline_chars) and all(x in uf.newline_chars for x in uf.newline_chars_str))

    assert(len(uf.filter_nonliterals_dict) == len(mdl.BESPON_NONLITERALS))
    assert(len(uf.filter_literalslessnewlines_dict) == len(mdl.BESPON_NONLITERALS) + len(mdl.BESPON_NEWLINES-set(['\r\n'])))
    assert(set(''.join(unicode_cc).translate(uf.filter_nonliterals_dict)) == mdl.BESPON_CC_LITERALS)
    assert(set(''.join(unicode_cc).translate(uf.filter_literalslessnewlines_dict)) == unicode_cc - set('\t'))

    assert(uf.shortescapes == mdl.BESPON_SHORT_ESCAPES)
    assert(uf.shortunescapes == mdl.BESPON_SHORT_UNESCAPES)
    # make sure defaults don't trigger any errors during sanity checks for escapes
    uf_custom = mdl.UnicodeFilter(shortescapes=mdl.BESPON_SHORT_ESCAPES, shortunescapes=mdl.BESPON_SHORT_UNESCAPES)

    assert(len(uf.escape_dict) == len(mdl.BESPON_NONLITERALS) + 1)  # All nonliterals + backlash
    assert(len(uf.escape_to_inline_dict) == len(mdl.BESPON_NONLITERALS) + len(mdl.BESPON_NEWLINES-set(['\r\n'])) + 2)  # Nonliterals, slash, tab
    assert(len(uf.unescape_dict) == len(mdl.BESPON_SHORT_UNESCAPES))


def test_UnicodeFilter_private_methods():
    uf = mdl.UnicodeFilter()
    xtest_sequence = [('\x01', '\\x01'), ('\u0101', '\\u0101'), ('\U00100101', '\\U00100101')]
    utest_sequence = [('\u0001', '\\u0001'), ('\u0101', '\\u0101'), ('\U00100101', '\\U00100101')]
    if NARROW_BUILD:
        xtest_sequence = xtest_sequence[:-1]
        utest_sequence = utest_sequence[:-1]
    assert(all(uf._escape_unicode_char(c) == e for c, e in xtest_sequence))
    assert(all(uf._escape_unicode_char_xuU(c) == e for c, e in xtest_sequence))
    assert(all(uf._escape_unicode_char_uU(c) == e for c, e in utest_sequence))
    assert(all(chr(n) == uf._unicode_ord_to_escaped_ascii_factory(n) for n in range(0, 512) if n < 128))
    assert(all(uf._escape_unicode_char(chr(n)) == uf._unicode_ord_to_escaped_ascii_factory(n) for n in range(0, 512) if n >= 128))
    assert(all(uf._unicode_escaped_hex_to_char_factory(e) == c for c, e in xtest_sequence))
    assert(all(uf._bin_escaped_hex_to_bytes_factory(e) == c for c, e in [(b'\x01', b'\\x01'), (b'\xaf', b'\\xaf'), (b'\x13', b'\\x13')]))


def test_UnicodeFilter_public_methods():
    uf = mdl.UnicodeFilter()
    if not NARROW_BUILD:
        s_raw = '\\ \'\"\a\b\x1b\f\n\r\t\v/\u2028\u2029\u0101\U00100101'
        s_esc = '\\\\ \'\"\\a\\b\\x1b\\f\n\r\t\\v/\\u2028\\u2029\u0101\U00100101'
        s_esc_inline = '\\\\ \'\"\\a\\b\\x1b\\f\\n\\r\\t\\v/\\u2028\\u2029\u0101\U00100101'
    else:
        s_raw = '\\ \'\"\a\b\x1b\f\n\r\t\v/\u2028\u2029\u0101'
        s_esc = '\\\\ \'\"\\a\\b\\x1b\\f\n\r\t\\v/\\u2028\\u2029\u0101'
        s_esc_inline = '\\\\ \'\"\\a\\b\\x1b\\f\\n\\r\\t\\v/\\u2028\\u2029\u0101'
    assert(uf.escape(s_raw) == s_esc)
    assert(uf.escape_to_inline(s_raw) == s_esc_inline)
    assert(uf.unescape(s_esc) == s_raw)
    assert(uf.unescape(s_esc_inline) == s_raw)
    assert(all(uf.has_nonliterals(chr(n)) for n in range(0, 512) if chr(n) in uf.nonliterals))
    assert(all(not uf.has_nonliterals(chr(n)) for n in range(0, 512) if chr(n) not in uf.nonliterals))

    assert(all(uf.unescape('\\'+eol) == '' for eol in uf.newlines))
    assert(all(uf.unescape('\\ '+eol) == '' for eol in uf.newlines))
    assert(all(uf.unescape('\\\u3000'+eol) == '' for eol in uf.newlines))
    assert(all(uf.unescape('\\ \u3000 \u3000'+eol) == '' for eol in uf.newlines))

    b_raw = b'\\ \'\"\a\b\x1b\f\n\r\t\v/\x13\xaf\xff'
    b_esc = b'\\\\ \'\"\\a\\b\\x1b\\f\n\r\t\\v/\\x13\\xaf\\xff'
    b_esc_inline = b'\\\\ \'\"\\a\\b\\x1b\\f\\n\\r\\t\\v/\\x13\\xaf\\xff'
    assert(uf.unescape_bin(b_esc) == b_raw)
    assert(uf.unescape_bin(b_esc_inline) == b_raw)
    assert(uf.escape_bin(b_raw) == b_esc)
    assert(uf.escape_to_inline_bin(b_raw) == b_esc_inline)

    s_with_nonliterals = '''\
    literals
    \v\f\u0085\u2028\u2029
    literals
    \x00\x01
    '''
    T = mdl.NonliteralTrace
    trace = [T('\\v', 2, 2), T('\\f', 2, 3), T('\\x85', 2, 4), T('\\u2028', 2, 5),
             T('\\u2029', 2, 6), T('\\x00\\x01', 4, 9)]
    assert(uf.trace_nonliterals(s_with_nonliterals) == trace)

    uf = mdl.UnicodeFilter(literals='\u0085\u2028\u2029')
    assert(uf.unicode_to_bin_newlines('\r\r\n\n\u0085\u2028\u2029\v\f') == '\r\r\n\n\n\n\n\v\f')
    assert(uf.remove_whitespace('\x20\u3000\t\r\n') == '')

    fwhw = [('！', '!'), ('～', '~'), ('ａ', 'a'), ('Ａ', 'A'), ('＊', '*'), ('１', '1'), ('\u3000', '\x20')]
    assert(all(uf.fullwidth_to_ascii(fw) == hw for fw, hw in fwhw))
    assert(all(uf.ascii_to_fullwidth(hw) == fw for fw, hw in fwhw))
    assert(all(uf.to_ascii_and_fullwidth(hw) == hw+fw for fw, hw in fwhw))
    assert(all(uf.to_ascii_and_fullwidth(fw) == hw+fw for fw, hw in fwhw))


def test_UnicodeFilter_errors():
    for c in '\x1c\x1d\x1e':
        with pytest.raises(err.ConfigError):
            uf = mdl.UnicodeFilter(literals=c)
    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(literals='abc', nonliterals='cde')

    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(nonliterals=['\r\n'])
    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(nonliterals=['ab'])

    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(nonliterals=[' '])
    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(nonliterals=['\t'])
    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(nonliterals=['\u3000'])

    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(shortescapes={'\\': '\\\\', '\\a': 'ab'})
    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(shortescapes={'\a': '\\a'})
    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(shortescapes={'\\': '\\\\', 'a': '\\\xff'})

    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(shortunescapes={'\\a': '\a'})
    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(shortunescapes={'\\\\': '\\', '\\\xff': 'a'})
    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(shortunescapes={'\\\\': '\\', '\\a': 'aa'})
    for esc in ('\\x', '\\X', '\\u', '\\U', '\\o', '\\O'):
        with pytest.raises(err.ConfigError):
            uf = mdl.UnicodeFilter(shortunescapes={'\\\\': '\\', esc: 'a'})

    for esc in mdl.BESPON_SHORT_UNESCAPES:
        with pytest.raises(err.UnknownEscapeError):
            uf = mdl.UnicodeFilter()
            uf._unicode_escaped_hex_to_char_factory(esc)
