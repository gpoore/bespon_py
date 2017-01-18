# -*- coding: utf-8 -*-
#
# Copyright (c) 2016, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


from __future__ import (division, print_function, absolute_import,
                        unicode_literals)


import sys
import os
import collections

if sys.version_info.major == 2:
    str = unicode
    __chr__ = chr
    chr = unichr

if sys.maxunicode == 0x10FFFF:
    NARROW_BUILD = False
else:
    NARROW_BUILD = True
    __narrow_chr__ = chr
    __narrow_ord__ = ord
    def _generate_chr_ord():
        def chr(n):
            if n < 0x10000:
                return __narrow_chr__(n)
            return '\\U{0:08x}'.format(n).decode('unicode-escape')
        def ord(c):
            if len(c) != 2:
                return __narrow_ord__(c)
            return 0x10000 + (__narrow_ord__(c[0]) - 0xD800)*0x400 + (__narrow_ord__(c[1]) - 0xDC00)
        return (chr, ord)
    chr, ord = _generate_chr_ord()


if all(os.path.isdir(x) for x in ('bespon', 'test', 'doc')):
    sys.path.insert(0, '.')

import bespon.unicoding as mdl
import bespon.erring as err

import pytest
import unicodedata
import re


EXTRA_TEST = False

MAX_CODE_POINT = 0x10FFFF+1


# Python's `re` package matches `\s` to the separator control characters; 
# `regex` doesn't.  U+180E (Mongolian Vowel Separator) isn't whitespace in
# current Unicode, but was in Unicode 4.0-6.3, which applies to Python 2.7's
# `re` implementation.
unicode_whitespace_re = re.compile('\s', re.UNICODE)
unicode_cc = set([chr(n) for n in range(MAX_CODE_POINT) if unicodedata.category(chr(n)) == 'Cc'])
unicode_zs = set([chr(n) for n in range(MAX_CODE_POINT) if unicodedata.category(chr(n)) == 'Zs' and n != 0x180e])
unicode_whitespace = set([chr(n) for n in range(MAX_CODE_POINT) if unicode_whitespace_re.match(chr(n)) and n not in range(0x1C, 0x1F+1) and n != 0x180e])


class State(object):
    def __init__(self, source, start_lineno, start_column, end_lineno=None, end_column=None, indent=None):
        self.source = source
        self.start_lineno = int(start_lineno)
        self.start_column = int(start_column)
        self.end_lineno = int(end_lineno) if end_lineno is not None else start_lineno
        self.end_column = int(end_column) if end_column is not None else start_column
        self.indent = indent or ''




def test_constants_and_defaults():
    '''
    Basic testing on code point constants to ensure appropriate length,
    compliance with Unicode, etc.
    '''
    assert(len(mdl.UNICODE_NEWLINES) == 8)
    assert(len(mdl.UNICODE_NEWLINE_CHARS) == 7)

    assert(len(mdl.BESPON_NEWLINES) == 1)
    assert(len(mdl.BESPON_NEWLINE_CHARS) == 1)

    assert(mdl.UNICODE_CC == unicode_cc)

    assert(len(mdl.BESPON_CC_LITERALS) == 2)

    assert(len(mdl.UNICODE_BIDI_OVERRIDES) == 2)

    assert(len(mdl.UNICODE_BOM) == 1)

    assert(len(mdl.UNICODE_NONCHARACTERS) == 66)

    # Cc minus `\t` and `\n`, plus newlines and bidi overrides
    assert(len(mdl.BESPON_NONLITERALS_LESS_SURROGATES) == (65-2) + (7-1-4) + 2)

    assert(mdl.UNICODE_ZS == unicode_zs)

    assert(len(mdl.UNICODE_WHITESPACE) == 17 + 7 + 1)  # Zs + newlines + \t
    assert(mdl.UNICODE_WHITESPACE == unicode_whitespace)

    assert(len(mdl.BESPON_INDENTS) == 2)
    assert(len(mdl.BESPON_SPACES) == 1)

    assert(len(mdl.BESPON_SHORT_UNESCAPES)-2 == len(mdl.BESPON_SHORT_ESCAPES))
    assert(all(k.startswith('\\') and len(k) == 2 and 0x21 <= ord(k[1]) <= 0x7E and len(v) == 1 and ord(v) < 128 for k, v in mdl.BESPON_SHORT_UNESCAPES.items()))




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
    assert(len(s.splitlines()) == len(mdl.UNICODE_NEWLINES)+1) # +1 for `\r\n`
    assert(len('_\x1c_\x1d_\x1e_'.splitlines()) == 4)




def test_UnicodeFilter_defaults():
    uf = mdl.UnicodeFilter()
    assert(uf.nonliterals_less_surrogates == mdl.BESPON_NONLITERALS_LESS_SURROGATES)
    assert('\r\n' not in uf.nonliterals_less_surrogates)
    
    assert(uf.newlines == mdl.BESPON_NEWLINES)
    assert(uf.newline_chars == mdl.BESPON_NEWLINE_CHARS)
    assert(len(uf.newline_chars_str) == len(uf.newline_chars) and all(x in uf.newline_chars for x in uf.newline_chars_str))

    assert(uf.short_escapes == mdl.BESPON_SHORT_ESCAPES)
    assert(uf.short_unescapes == mdl.BESPON_SHORT_UNESCAPES)
    
    # Make sure defaults actually work when passed explicitly
    uf_custom = mdl.UnicodeFilter(nonliterals=mdl.BESPON_NONLITERALS_LESS_SURROGATES,
                                  short_escapes=mdl.BESPON_SHORT_ESCAPES,
                                  short_unescapes=mdl.BESPON_SHORT_UNESCAPES,
                                  spaces='\x20', indents='\x20\t',
                                  escaped_string_delim_chars='"')




def test_UnicodeFilter_char_and_byte_escape_unescape():
    uf = mdl.UnicodeFilter(unpaired_surrogates=True)
    ubrace_test_sequence = [('\x01', '\\u{1}'), ('\x1f', '\\u{1f}'), ('\ufeff', '\\u{feff}'), ('\u0101', '\\u{101}'), ('\U00100101', '\\u{100101}'), ('\U0010abcd', '\\u{10abcd}')]
    xubrace_test_sequence = [('\x01', '\\x01'), ('\x1f', '\\x1f'), ('\ufeff', '\\u{feff}'), ('\u0101', '\\u{101}'), ('\U00100101', '\\u{100101}'), ('\U0010abcd', '\\u{10abcd}')]
    xuU_test_sequence = [('\x01', '\\x01'), ('\x1f', '\\x1f'), ('\ufeff', '\\ufeff'), ('\u0101', '\\u0101'), ('\U00100101', '\\U00100101'), ('\U0010abcd', '\\U0010abcd')]
    uU_test_sequence = [('\u0001', '\\u0001'), ('\x1f', '\\u001f'), ('\ufeff', '\\ufeff'), ('\u0101', '\\u0101'), ('\U00100101', '\\U00100101'), ('\U0010abcd', '\\U0010abcd')]
    if NARROW_BUILD:
        ubrace_test_sequence = ubrace_test_sequence[:-1]
        xubrace_test_sequence = xubrace_test_sequence[:-1]
        xuU_test_sequence = xuU_test_sequence[:-1]
        uU_test_sequence = uU_test_sequence[:-1]
    for esc_func, unesc_func, test_seq in [(uf._escape_unicode_char, uf._unescape_unicode_char, xubrace_test_sequence),
                                            (uf._escape_unicode_char_ubrace, uf._unescape_unicode_char, ubrace_test_sequence),
                                            (uf._escape_unicode_char_xubrace, uf._unescape_unicode_char, xubrace_test_sequence),
                                            (uf._escape_unicode_char_xuU, uf._unescape_unicode_char, xuU_test_sequence),
                                            (uf._escape_unicode_char_uU, uf._unescape_unicode_char, uU_test_sequence)]:
        assert(all(esc_func(c) == e and unesc_func(e) == c for c, e in test_seq))
        if EXTRA_TEST:
            assert(all(unesc_func(esc_func(chr(n))) == chr(n) for n in range(MAX_CODE_POINT)))

    assert(all(uf._escape_bytes_dict[c] == e and uf._unescape_byte(e) == c for c, e in [(b'\x01', b'\\x01'), (b'\xaf', b'\\xaf'), (b'\x13', b'\\x13')]))




def test_UnicodeFilter_public_methods():
    uf = mdl.UnicodeFilter(brace_escapes=False)
    if not NARROW_BUILD:
        s_raw = '\\ \'\"\a\b\x1b\f\n\r\t\v/\u2028\u2029\u0101\U00100101'
        s_esc = '\\\\ \'\"\\a\\b\\x1b\\f\n\\r\t\\v/\\u2028\\u2029\u0101\U00100101'
        s_esc_inline = '\\\\ \'\"\\a\\b\\x1b\\f\\n\\r\\t\\v/\\u2028\\u2029\u0101\U00100101'
    else:
        s_raw = '\\ \'\"\a\b\x1b\f\n\r\t\v/\u2028\u2029\u0101'
        s_esc = '\\\\ \'\"\\a\\b\\x1b\\f\n\\r\t\\v/\\u2028\\u2029\u0101'
        s_esc_inline = '\\\\ \'\"\\a\\b\\x1b\\f\\n\\r\\t\\v/\\u2028\\u2029\u0101'
    assert(uf.escape('\\') == '\\\\')
    assert(uf.escape(s_raw) == s_esc)
    assert(uf.escape(s_raw, inline=True) == s_esc_inline)
    assert(uf.unescape(s_esc) == s_raw)
    assert(uf.unescape(s_esc_inline) == s_raw)
    assert(all(uf.has_nonliterals(chr(n)) for n in range(0, 512) if chr(n) in uf.nonliterals_less_surrogates))
    assert(all(not uf.has_nonliterals(chr(n)) for n in range(0, 512) if chr(n) not in uf.nonliterals_less_surrogates))
    assert(all(not uf.has_non_ascii(chr(n)) for n in range(0, 128)))
    assert(all(uf.has_non_ascii(chr(n)) for n in range(128, 512)))

    uf = mdl.UnicodeFilter(literals=set('\\ \t') | mdl.UNICODE_NEWLINE_CHARS)
    assert(all(uf.unescape('\\'+eol) == '' for eol in mdl.UNICODE_NEWLINES))
    assert(all(uf.unescape('\\ '+eol) == '' for eol in mdl.UNICODE_NEWLINES))

    uf = mdl.UnicodeFilter()
    b_raw = b'\\ \'\"\a\b\x1b\f\n\r\t\v/\x13\xaf\xff'
    b_esc = b'\\\\ \'\"\\a\\b\\x1b\\f\n\\r\t\\v/\\x13\\xaf\\xff'
    b_esc_inline = b'\\\\ \'\"\\a\\b\\x1b\\f\\n\\r\\t\\v/\\x13\\xaf\\xff'
    b_esc_maximal = b'\\\\\\x20\'\\"\\a\\b\\x1b\\f\\n\\r\\t\\v/\\x13\\xaf\\xff'
    assert(uf.unescape_bytes(b_esc) == b_raw)
    assert(uf.unescape_bytes(b_esc_inline) == b_raw)
    assert(uf.escape_bytes(b_raw) == b_esc)
    assert(uf.escape_bytes(b_raw, maximal=True) == b_esc_maximal)
    assert(uf.escape_bytes(b_raw, inline=True) == b_esc_inline)

    uf = mdl.UnicodeFilter(brace_escapes=False)
    s_with_nonliterals = '''\
    literals
    \v\f\u0085\u2028\u2029
    literals
    \x00\x01
    '''
    T = mdl.NonliteralTrace
    trace = [T('\\v', 2, 2), T('\\f', 2, 3), T('\\x85', 2, 4), 
             T('\\u2028', 2, 5), T('\\u2029', 2, 6), T('\\x00', 4, 9),
             T('\\x01', 4, 9)]
    assert(uf.trace_nonliterals(s_with_nonliterals) == trace)

    uf = mdl.UnicodeFilter(literals='\\ \t\v\f\u0085\u2028\u2029')
    assert(uf.non_ascii_to_ascii_newlines('\u0085_\u2028_\u2029') == '\n_\n_\n')


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
        uf = mdl.UnicodeFilter(short_escapes={'\\': '\\\\', '\\a': 'ab'})
    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(short_escapes={'\a': '\\a'})
    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(short_escapes={'\\': '\\\\', 'a': '\\\xff'})

    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(short_unescapes={'\\a': '\a'})
    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(short_unescapes={'\\\\': '\\', '\\\xff': 'a'})
    with pytest.raises(err.ConfigError):
        uf = mdl.UnicodeFilter(short_unescapes={'\\\\': '\\', '\\a': 'aa'})
    for esc in ('\\x', '\\X', '\\u', '\\U', '\\o', '\\O'):
        with pytest.raises(err.ConfigError):
            uf = mdl.UnicodeFilter(short_unescapes={'\\\\': '\\', esc: 'a'})
        with pytest.raises(err.ConfigError):
            uf = mdl.UnicodeFilter(short_escapes={'\\': '\\\\', 'a': esc})

    uf = mdl.UnicodeFilter()
    for esc in mdl.BESPON_SHORT_UNESCAPES:
        with pytest.raises(err.UnknownEscapeError):
            uf._unescape_unicode_char(esc)

    with pytest.raises(err.ConfigError):
        mdl.UnicodeFilter(literals='\uD800')
    with pytest.raises(err.ConfigError):
        mdl.UnicodeFilter(literals='\uDFFF')

    uf = mdl.UnicodeFilter()
    for n in range(0xD800, 0xDFFF+1):
        with pytest.raises(err.UnicodeSurrogateError):
            uf._escape_unicode_char(chr(n))
        with pytest.raises(err.EscapedUnicodeSurrogateError):
            uf.unescape('\\u{0:04x}'.format(n))
    for func in (uf._escape_unicode_char_ubrace, uf._escape_unicode_char_xubrace, uf._escape_unicode_char_xuU, uf._escape_unicode_char_uU):
        with pytest.raises(err.UnicodeSurrogateError):
            func('\uD800')
        with pytest.raises(err.UnicodeSurrogateError):
            func('\uDFFF')


def test_UnicodeFilter_tracebacks():
    uf = mdl.UnicodeFilter()
    
    # In escape, only `\r`, `\n`, and `\r\n` are counted as newlines in
    # traceback message.
    e_surrogate_data = [('\uD800', 'line 1:1:'), 
                        ('xx\uDFFF', 'line 1:3:'),
                        ('\r\n\v\r\f\n\u0085\u2028\u2029x\uD800', 'line 4:5:'),
                        ('a\r\nab\vabc\rabcd\fabcde\nabcdef\u0085abcdefg\u2028abcdefgh\u2029x\uD800', 'line 4:26:')]
    for s, p in e_surrogate_data:
        msg = None
        try:
            uf.escape(s)
        except err.BespONException as e:
            msg = str(e)
        assert(p in msg)
    
    uf.state = State('src', 5, 2, indent='\x20\x20\x20')
    e_surrogate_data = [('\uD800', 'line 5:2:'), 
                        ('xx\uDFFF', 'line 5:4:'),
                        ('\r\n\v\r\f\n\u0085\u2028\u2029x\uD800', 'line 8:8:'),
                        ('a\r\nab\vabc\rabcd\fabcde\nabcdef\u0085abcdefg\u2028abcdefgh\u2029x\uD800', 'line 8:29:')]
    for s, p in e_surrogate_data:
        msg = None
        try:
            uf.escape(s)
        except err.BespONException as e:
            msg = str(e)
        assert(p in msg)
    uf.state = None

    
    # In unescape, all Unicode newlines are counted as newlines, since any
    # of them may appear after a `newline` specification in explicit typing.
    u_surrogate_data = [('\\uD800', 'line 1:1:'), 
                        ('xx\\uDFFF', 'line 1:3:'),
                        ('\r\n\v\r\f\n\u0085\u2028\u2029x\\uD800', 'line 9:2:'),
                        ('a\r\nab\vabc\rabcd\fabcde\nabcdef\u0085abcdefg\u2028abcdefgh\u2029x\\uD800', 'line 9:2:')]
    u_string_data = [('\\Q', 'line 1:1:'), 
                     ('xx\\Q', 'line 1:3:'),
                     ('\r\n\v\r\f\n\u0085\u2028\u2029x\\Q', 'line 9:2:'),
                     ('a\r\nab\vabc\rabcd\fabcde\nabcdef\u0085abcdefg\u2028abcdefgh\u2029x\\Q', 'line 9:2:')]
    for s, p in u_surrogate_data + u_string_data:
        msg = None
        try:
            uf.unescape(s)
        except err.BespONException as e:
            msg = str(e)
        assert(p in msg)
    
    uf.state = State('src', 5, 2, indent='\x20\x20\x20')
    u_surrogate_data = [('\\uD800', 'line 5:2:'), 
                        ('xx\\uDFFF', 'line 5:4:'),
                        ('\r\n\v\r\f\n\u0085\u2028\u2029x\\uD800', 'line 13:5:'),
                        ('a\r\nab\vabc\rabcd\fabcde\nabcdef\u0085abcdefg\u2028abcdefgh\u2029x\\uD800', 'line 13:5:')]
    u_string_data = [('\\Q', 'line 5:2:'), 
                     ('xx\\Q', 'line 5:4:'),
                     ('\r\n\v\r\f\n\u0085\u2028\u2029x\\Q', 'line 13:5:'),
                     ('a\r\nab\vabc\rabcd\fabcde\nabcdef\u0085abcdefg\u2028abcdefgh\u2029x\\Q', 'line 13:5:')]
    for s, p in u_surrogate_data + u_string_data:
        msg = None
        try:
            uf.unescape(s)
        except err.BespONException as e:
            msg = str(e)
        assert(p in msg)
    uf.state = None


    # In bytes unescape, all newlines in Latin 1 range are counted, since any
    # of them may appear after a `newline` specification in explicit typing.
    u_bytes_data = [(b'\\Q', 'line 1:1:'), 
                    (b'xx\\Q', 'line 1:3:'),
                    (b'\r\n\v\r\f\n\x85\x28\x29x\\Q', 'line 7:4:'),
                    (b'a\r\nab\vabc\rabcd\fabcde\nabcdef\x85abcdefg\x28abcdefgh\x29x\\Q', 'line 7:19:')]
    for b, p in u_bytes_data:
        msg = None
        try:
            uf.unescape_bytes(b)
        except err.BespONException as e:
            msg = str(e)
        assert(p in msg)
    
    uf.state = State('src', 5, 2, indent='\x20\x20\x20')
    u_bytes_data = [(b'\\Q', 'line 5:2:'), 
                    (b'xx\\Q', 'line 5:4:'),
                    (b'\r\n\v\r\f\n\x85\x28\x29x\\Q', 'line 11:7:'),
                    (b'a\r\nab\vabc\rabcd\fabcde\nabcdef\x85abcdefg\x28abcdefgh\x29x\\Q', 'line 11:22:')]
    for b, p in u_bytes_data:
        msg = None
        try:
            uf.unescape_bytes(b)
        except err.BespONException as e:
            msg = str(e)
        assert(p in msg)
    uf.state = None
    
    
