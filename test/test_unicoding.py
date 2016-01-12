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

import bespon.unicoding as mdl
import bespon.erring as err

import unicodedata




unicode_cc = set([chr(n) for n in range(0, 0x10FFFF+1) if unicodedata.category(chr(n)) == 'Cc'])


def test_string_constants():
    '''
    Basic testing on code point constants to ensure appropriate length,
    compliance with Unicode, etc.
    '''
    assert(len(mdl.UNICODE_NEWLINES) == 8)
    assert(len(mdl.UNICODE_NEWLINE_CHARS) == 7)
    assert(len(mdl.UNICODE_NEWLINE_CHAR_UNESCAPES) == 7)
    assert(len(mdl.UNICODE_NEWLINE_CHAR_ESCAPES) == 7)
    assert(all(c in mdl.UNICODE_NEWLINE_CHARS for c in mdl.UNICODE_NEWLINE_CHAR_ESCAPES))

    assert(len(mdl.BESPON_DEFAULT_NEWLINES) == 3)

    assert(mdl.UNICODE_CC == unicode_cc)

    assert(len(mdl.BESPON_DEFAULT_CC_LITERALS) == 3)

    assert(len(mdl.BESPON_DEFAULT_NONLITERALS) == 65-3+2)

    assert(len(mdl.BESPON_SHORT_UNESCAPES)-2 == len(mdl.BESPON_SHORT_ESCAPES))
    assert(all(k.startswith('\\') and len(k) == 2 and ord(k[1]) < 128 for k in mdl.BESPON_SHORT_UNESCAPES))
    assert(all(len(k) == 1 for k in mdl.BESPON_SHORT_ESCAPES))


def test_keydefaultdict():
    '''
    Test functioning of keydefaultdict
    '''
    d = mld.keydefaultdict(lambda x: x**2)
    d[2]
    d[4]
    d[8]
    assert(d == {2:4, 4:16, 8:64})


def test_NonliteralTrace():
    t = mdl.NonliteralTrace('chars', 1, 2)
    assert(len(t) == 3)
    print(t)
    assert(t.chars == 'chars' and t.lineno == 1 and t.unicodelineno == 2)


def test_python_splitlines():
    '''
    Make sure Python's `splitlines()` supports all linebreaks.

    Also, make sure that `splitlines()` still splits lines at the separator
    characters, since this requires either nonliteral separator characters,
    or special treatment of them.
    '''
    s = '_'.join(mdl.UNICODE_NEWLINES)+'_'
    assert(len(s.splitlines()) == len(mdl.UNICODE_NEWLINES)+1)
    assert(len('_\x1c_\x1d_\x1e_'.splitlines()) == 4)


def test_keydefaultdict():
    def factory(s):
        return s
    kd = mdl.keydefaultdict(factory)
    assert('key' not in kd)
    assert(kd['key'] == 'key')
    assert('key' in kd and len(kd) == 1)


def test_UnicodeFilter_defaults():
    uf = mdl.UnicodeFilter()
    assert(uf.newlines == mdl.BESPON_DEFAULT_NEWLINES)
    assert(uf.nonliterals == mdl.BESPON_DEFAULT_NONLITERALS)
    assert(uf.shortescapes == mdl.BESPON_SHORT_ESCAPES)
    assert(uf.shortunescapes == mdl.BESPON_SHORT_UNESCAPES)
    assert(len(uf.filternonliteralsdict) == len(mdl.BESPON_DEFAULT_NONLITERALS))
    assert(len(uf.filterliteralslessnewlinesdict) == len(mdl.BESPON_DEFAULT_NONLITERALS) + len(mdl.BESPON_DEFAULT_NEWLINES-set(['\r\n'])))
    assert(len(uf.escapedict) == len(mdl.BESPON_DEFAULT_NONLITERALS) + 1)  # All nonliterals + backlash
    assert(len(uf.inline_escapedict) == len(mdl.BESPON_DEFAULT_NONLITERALS) + len(mdl.BESPON_DEFAULT_NEWLINES-set(['\r\n'])) + 2)  # Nonliterals, slash, tab
    assert(len(uf.unescapedict) == len(mdl.BESPON_SHORT_UNESCAPES))


def test_UnicodeFilter_private_methods():
    uf = mdl.UnicodeFilter()
    assert(all(uf._escape_unicode_char(c) == e for c, e in [('\x01', '\\x01'), ('\u0101', '\\u0101'), ('\U00100101', '\\U00100101')]))
    assert(all(uf._escape_unicode_char_xuU(c) == e for c, e in [('\x01', '\\x01'), ('\u0101', '\\u0101'), ('\U00100101', '\\U00100101')]))
    assert(all(uf._escape_unicode_char_uU(c) == e for c, e in [('\x01', '\\u0001'), ('\u0101', '\\u0101'), ('\U00100101', '\\U00100101')]))
    assert(all(chr(n) == uf._unicode_to_escaped_ascii_factory(chr(n)) for n in range(0, 512) if n < 128))
    assert(all(uf._escape_unicode_char(chr(n)) == uf._unicode_to_escaped_ascii_factory(chr(n)) for n in range(0, 512) if n >= 128))
    assert(all(uf._unicode_escaped_hex_to_char_factory(e) == c for c, e in [('\x01', '\\x01'), ('\u0101', '\\u0101'), ('\U00100101', '\\U00100101')]))


def test_UnicodeFilter_public_methods():
    uf = mdl.UnicodeFilter()
    s_raw = '\\ \'\"\a\b\x1b\f\n\r\t\v/\u0101\U00100101\u2028\u2029'
    s_esc = '\\\\ \'\"\\a\\b\\x1b\\f\n\r\t\\v/\u0101\U00100101\\u2028\\u2029'
    s_esc_inline = '\\\\ \'\"\\a\\b\\x1b\\f\\n\\r\\t\\v/\u0101\U00100101\\u2028\\u2029'
    assert(uf.escape(s_raw) == s_esc)
    assert(uf.inline_escape(s_raw) == s_esc_inline)
    assert(uf.unescape(s_esc) == s_raw)
    assert(uf.unescape(s_esc_inline) == s_raw)
    assert(all(uf.hasnonliterals(chr(n)) for n in range(0, 512) if chr(n) in uf.nonliterals))
    assert(all(not uf.hasnonliterals(chr(n)) for n in range(0, 512) if chr(n) not in uf.nonliterals))

    s_with_nonliterals = '''\
    literals
    \v\f\u0085\u2028\u2029
    literals
    \x00\x01
    '''
    T = mdl.NonliteralTrace
    trace = [T('\\v', 2, 2), T('\\f', 2, 3), T('\\x85', 2, 4), T('\\u2028', 2, 5),
             T('\\u2029', 2, 6), T('\\x00\\x01', 4, 9)]
    assert(uf.tracenonliterals(s_with_nonliterals) == trace)
