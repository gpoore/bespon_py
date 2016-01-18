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


from .version import __version__
import sys

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

import collections
import re
from . import erring




# Unicode code points to be treated as line terminators
# http://unicode.org/standard/reports/tr13/tr13-5.html
# Common line endings `\r`, `\n`, and `\r\n`, plus NEL, vertical tab,
# form feed, Line Separator, and Paragraph Separator
UNICODE_NEWLINES = set(['\r', '\n', '\r\n', '\u0085', '\v', '\f', '\u2028', '\u2029'])
UNICODE_NEWLINE_CHARS = set(x for x in UNICODE_NEWLINES if len(x) == 1)
UNICODE_NEWLINE_CHARS_ORD = set(ord(c) for c in UNICODE_NEWLINE_CHARS)
UNICODE_NEWLINE_CHAR_UNESCAPES = {'\\r': '\r',
                                  '\\n': '\n',
                                  '\\u0085': '\u0085',
                                  '\\v': '\v',
                                  '\\f': '\f',
                                  '\\u2028': '\u2028',
                                  '\\u2029': '\u2029'}
UNICODE_NEWLINE_CHAR_ESCAPES = {v: k for k, v in UNICODE_NEWLINE_CHAR_UNESCAPES.items()}


# Default allowed newlines
BESPON_DEFAULT_NEWLINES = set(['\r', '\n', '\r\n'])


# Code points with Unicode category "Other, Control" (Cc)
# http://www.fileformat.info/info/unicode/category/Cc/index.htm
# Ord ranges 0-31, 127, 128-159
UNICODE_CC_ORD = set(list(range(0x0000, 0x001F+1)) + [0x007F] + list(range(0x0080, 0x009F+1)))
UNICODE_CC = set(chr(c) for c in UNICODE_CC_ORD)


# Default allowed CC code points
BESPON_DEFAULT_CC_LITERALS = set(['\t', '\n', '\r'])
BESPON_DEFAULT_CC_LITERALS_ORD = set(ord(c) for c in BESPON_DEFAULT_CC_LITERALS)


# Default code points not allowed as literals
BESPON_DEFAULT_NONLITERALS = (UNICODE_CC - BESPON_DEFAULT_CC_LITERALS) | (UNICODE_NEWLINES - BESPON_DEFAULT_NEWLINES)

# Allowed short backslash escapes
# Two are less common:  `\e` is from GCC, clang, etc., and `\/` is from JSON
# By default, these two are only used in reading escapes, not in creating them
BESPON_SHORT_UNESCAPES = {'\\\\': '\\',
                          "\\'": "'",
                          '\\"': '"',
                          '\\a': '\a',
                          '\\b': '\b',
                          '\\e': '\x1B',
                          '\\f': '\f',
                          '\\n': '\n',
                          '\\r': '\r',
                          '\\t': '\t',
                          '\\v': '\v',
                          '\\/': '/'}

BESPON_SHORT_ESCAPES = {v:k for k, v in BESPON_SHORT_UNESCAPES.items() if v != '/' and v != '\x1B'}




class keydefaultdict(collections.defaultdict):
    '''
    Default dict that passes missing keys to the factory function, rather than
    calling the factory function with no arguments.
    '''
    def __missing__(self, k):
        if self.default_factory is None:
            raise KeyError(k)
        else:
            v = self[k] = self.default_factory(k)
            return v




# Structure for keeping track of which code points that are not allowed to
# appear literally in text did in fact appear, and where
# `lineno` uses `\r`, `\n`, and `\r\n`, while `unicodelineno` uses all of
#  UNICODE_NEWLINES
NonliteralTrace = collections.namedtuple('NonliteralTrace', ['chars', 'lineno', 'unicodelineno'])




class UnicodeFilter(object):
    '''
    Check strings for literal code points that are not allowed,
    backslash-escape and backslash-unescape strings, filter out newline
    characters, etc.
    '''
    def __init__(self, literals=None, nonliterals=None, onlyascii=False,
                 shortescapes=None, shortunescapes=None, xescapes=True):
        # Specified code points to be allowed as literals, beyond defaults,
        # and code points not to be allowed as literals, beyond defaults,
        # are used to create a set of code points that aren't allowed unescaped
        if literals is None and nonliterals is None:
            nonliterals = BESPON_DEFAULT_NONLITERALS
            newlines = BESPON_DEFAULT_NEWLINES
        else:
            if literals is None:
                literals = set()
            else:
                literals = set(literals)
            if nonliterals is None:
                nonliterals = set()
            else:
                nonliterals = set(nonliterals)
            if any(c in literals for c in '\x1c\x1d\x1e') and len('_\x1c_\x1d_\x1e_'.splitlines()) == 4:
                # Python's `str.splitlines()` doesn't just split on Unicode
                # newlines, it also splits on separators.  Either these
                # characters must never be allowed as literals, or
                # alternatively parsing must be adapted to account for them.
                raise erring.ConfigError('The File Separator (\\x1c), Group Separator (\\x1d), and Record Separator (\\x1e) are not allowed as literals by this implementation')
            if literals & nonliterals:
                raise erring.ConfigError('Overlap between code points in "literals" and "nonliterals"')
            nonliterals = (BESPON_DEFAULT_NONLITERALS - literals) | nonliterals
            newlines = UNICODE_NEWLINES - nonliterals
            if '\r\n' in nonliterals:
                if '\r' in nonliterals and '\n' in nonliterals:
                    nonliterals = nonliterals - set(['\r\n'])
                else:
                    raise erring.ConfigError('The sequence "\\r\\n" cannot be treated as a nonliteral without also treating "\\r" and "\\n" as nonliterals')
            if not all(len(c) == 1 for c in nonliterals):
                raise erring.ConfigError('Only single code points can be specified as nonliterals, with the exception of "\\r\\n"')
        self.nonliterals = nonliterals
        self.newlines = newlines
        self.newline_chars = set(''.join(self.newlines))
        self.newline_chars_str = ''.join(self.newline_chars)
        # Dict for filtering out all nonliterals, using `str.translate()`
        self.filter_nonliterals_dict = {ord(c): None for c in self.nonliterals}
        # Dict for filtering out all literals, except for newlines, using
        # `str.translate` --- this provides an easy way of locating all
        # nonliterals that are present on each line of the source
        self.filter_literalslessnewlines_dict = collections.defaultdict(lambda: None)
        self.filter_literalslessnewlines_dict.update({ord(c): c for c in self.nonliterals})
        self.filter_literalslessnewlines_dict.update({ord(c): c for c in UNICODE_NEWLINE_CHARS})


        # Dicts that map code points to their escaped versions, and vice versa
        if shortescapes is None:
            shortescapes = BESPON_SHORT_ESCAPES
        else:
            if '\\' not in shortescapes:
                raise erring.ConfigError('Short backslash escapes must define the escape of "\\"')
            if not all(len(c) == 1 for c in shortescapes.items()):
                raise erring.ConfigError('Short escapes only map single code points to escapes, not groups of code points to escapes')
            if not all(len(v) == 2 and ord(v[1]) < 128 for k, v in shortescapes.items()):
                raise erring.ConfigError('Short escapes only map single code points to a backslash followed by a single ASCII character')
        self.shortescapes = shortescapes

        if shortunescapes is None:
            shortunescapes = BESPON_SHORT_UNESCAPES
        else:
            if '\\\\' not in shortunescapes:
                raise erring.ConfigError('Short backslash unescapes must define the meaning of "\\\\"')
            if not all(x.startswith('\\') and len(x) == 2 and ord(x[1]) < 128 for x in shortunescapes):
                raise erring.ConfigError('All short backlash unescapes be a backslash followed by a single ASCII character')
            if not all(len(v) ==1 for k, v in shortunescapes.items()):
                raise erring.ConfigError('All short backlash unescapes be a backslash followed by a single ASCII character')
            if any(pattern in shortunescapes for pattern in ('\\x', '\\X', '\\u', '\\U', '\\o', '\\O')):
                raise erring.ConfigError('Short backlash unescapes cannot use the letters X, U, or O, in either upper or lower case')
        self.shortunescapes = shortunescapes

        self.shortescapes_bin = {k.encode('ascii'): v.encode('ascii') for k, v in self.shortescapes.items()}
        self.shortunescapes_bin = {k.encode('ascii'): v.encode('ascii') for k, v in self.shortunescapes.items()}


        # Whether `\xHH` escapes are allowed
        escape_re_pattern = r'\\x..|\\u....|\\U........|\\[\x20\u3000]*(?:{newlines})|\\.|\\'
        # Since `newlines` is a set that may contain a two-character sequence
        # (`\r\n`), need to ensure that any two-character sequence appears
        # first in matching, so need reversed `sorted()`
        escape_re_pattern = escape_re_pattern.format(newlines='|'.join(sorted(self.newlines, reverse=True)))
        if xescapes:
            self.escape_re = re.compile(escape_re_pattern, re.DOTALL)
            self._escape_unicode_char = self._escape_unicode_char_xuU
        else:
            self.escape_re = re.compile(escape_re_pattern.lsplit('|', 1)[1], re.DOTALL)
            self._escape_unicode_char = self._escape_unicode_char_uU

        escape_bin_re_pattern = rb'\\x..|\\\x20*(?:\r\n|\r|\n)|\\.|\\'
        self.escape_bin_re = re.compile(escape_bin_re_pattern, re.DOTALL)


        # Dict for escaping code points that may not appear literally
        # Use with `str.translate()`
        # This is a minimalist form of escaping, given the current literals
        escape_dict = {ord(c): self._escape_unicode_char(c) for c in self.nonliterals}
        # Copy over any relevant short escapes
        for k, v in self.shortescapes.items():
            n = ord(k)
            if n in escape_dict:
                escape_dict[n] = v
        # Want everything that must be escaped, plus the backslash that makes
        # escaping possible in the first place
        escape_dict[ord('\\')] = shortescapes['\\']
        if not onlyascii:
            self.escape_dict = escape_dict
        else:
            # Factory function adds characters to dict as they are requested
            # All escapes already in `escape_dict` are valid ASCII, since
            # `_escape_unicode_char()` gives hex escapes, and short escapes
            # must use ASCII characters
            self.escape_dict = keydefaultdict(self._unicode_to_escaped_ascii_factory, escape_dict)


        # Escaping with no literal line breaks
        # Inherits onlyascii settings
        # Copy over all newlines escapes and the tab short escape, if it exists
        inline_escape_dict = self.escape_dict.copy()
        inline_escape_dict.update({ord(k): v for k, v in UNICODE_NEWLINE_CHAR_ESCAPES.items()})
        if '\t' in self.shortescapes:
            inline_escape_dict[ord('\t')] = self.shortescapes['\t']
        self.inline_escape_dict = inline_escape_dict


        # Dict for unescaping with current settings
        # Used for looking up backlash escapes found by `re.sub()`
        # Starts with all short escapes; the factory function adds additional
        # escapes as they are requested
        self.unescape_dict = keydefaultdict(self._unicode_escaped_hex_to_char_factory, self.shortunescapes)
        self.unescape_bin_dict = keydefaultdict(self._bin_escaped_hex_to_bytes_factory, self.shortunescapes_bin)

        # Dict for removing all newlines
        self.remove_newlines_dict = {ord(c): None for c in self.newline_chars}


        # Dict for tranlating Unicode newlines into a bytes-compatible form
        self.unicode_to_bin_newlines_dict = {ord(c): '\n' for c in UNICODE_NEWLINE_CHARS if ord(c) >= 128}


        # Space characters to be treated as spaces
        self.space_chars = set(['\x20', '\u3000'])
        self.space_chars_str = ''.join(self.space_chars)


        # Indentation characters
        self.indentation_chars = set(['\x20', '\t', '\u3000'])
        self.indentation_chars_str = ''.join(self.indentation_chars)

        # Overall whitespace
        self.whitespace = self.indentation_chars | self.newline_chars | self.space_chars
        self.remove_whitespace_dict = {ord(c): None for c in self.whitespace}


    @staticmethod
    def _escape_unicode_char_xuU(c):
        '''
        Escape a Unicode code point using `\\xHH` (8-bit), `\\uHHHH` (16-bit),
        or `\\UHHHHHHHH` (32-bit) notation.
        '''
        n = ord(c)
        if n < 256:
            e = '\\x{0:02x}'.format(n)
        elif n < 65536:
            e = '\\u{0:04x}'.format(n)
        else:
            e = '\\U{0:08x}'.format(n)
        return e


    @staticmethod
    def _escape_unicode_char_uU(c):
        '''
        Escape a Unicode code point using \\uHHHH` (16-bit),
        or `\\UHHHHHHHH` (32-bit) notation.
        '''
        n = ord(c)
        if n < 65536:
            e = '\\u{0:04x}'.format(n)
        else:
            e = '\\U{0:08x}'.format(n)
        return e


    def _unicode_to_escaped_ascii_factory(self, c):
        '''
        Given a code point, return an escaped version in `\\xHH`, `\\uHHHH`, or
        `\\UHHHHHHHH` form for all non-ASCII code points.
        '''
        if not ord(c) < 128:
            c = self._escape_unicode_char(c)
        return c


    def _unicode_escaped_hex_to_char_factory(self, s):
        '''
        Given a string in `\\xHH`, `\\uHHHH`, or `\\UHHHHHHHH` form, return the
        Unicode code point corresponding to the hex value of the `H`'s.  Given
        `\\<spaces or ideographic spaces><newline>`, return an empty string.
        Otherwise, raise an error for `\\<char>`, which is the only other form
        the argument will ever take.

        Arguments to this function are prefiltered by a regex into the allowed
        hex escape forms.  Before this function is invoked, all known short
        (2-letter) escape sequences have already been filtered out.  Any
        remaining short escapes `\\<char>` at this point are unrecognized.
        '''
        try:
            v = chr(int(s[2:], 16))
        except ValueError:
            if s != '\\' and not s[1:].lstrip(self.space_chars_str).rstrip(self.newline_chars_str):
                v = ''
            else:
                raise erring.UnknownEscapeError(s)
        return v


    def _bin_escaped_hex_to_bytes_factory(self, b):
        '''
        Given a string in `\\xHH` form, return the byte corresponding to the
        hex value of the `H`'s.  Given `\\<spaces><newline>`, return an empty
        byte string.  Otherwise, raise an error for `\\<byte>`, which is the
        only other form the argument will ever take.

        Arguments to this function are prefiltered by a regex into the allowed
        hex escape forms.  Before this function is invoked, all known short
        (2-letter) escape sequences have already been filtered out.  Any
        remaining short escapes `\\<char>` at this point are unrecognized.
        '''
        try:
            v = int(b[2:], 16).to_bytes(1, 'little')
        except ValueError:
            if b != b'\\' and not b[1:].lstrip(b'\x20').rstrip(b'\r\n'):
                v = b''
            else:
                raise erring.UnknownEscapeError(b)
        return v


    def escape(self, s):
        '''
        Within a string, replace all code points that are not allowed to appear
        literally with their escaped counterparts.
        '''
        return s.translate(self.escape_dict)


    def inline_escape(self, s):
        '''
        Within a string, replace all code points that are not allowed to appear
        literally with their escaped counterparts.  Also escape all newlines.
        '''
        return s.translate(self.inline_escape_dict)


    def unescape(self, s):
        '''
        Within a string, replace all backslash escapes of the form `\\xHH`,
        `\\uHHHH`, and `\\UHHHHHHHH`, as well as the form `\\<char>`, with the
        corresponding code points.
        '''
        # Local reference to escape_dict to speed things up a little
        unescape_dict = self.unescape_dict
        # For reference, the regex with `\xHH` escapes is:
        # escape_re = re.compile(r'(\\x..|\\u....|\\U........|\\.|\\)', re.DOTALL)
        return self.escape_re.sub(lambda m: unescape_dict[m.group(0)], s)


    def unescape_bin(self, b):
        '''
        Within a binary string, replace all backslash escapes of the form
        `\\xHH`, as well as the form `\\<byte>`, with the corresponding
        byte.
        '''
        # Local reference to speed things up a little
        unescape_bin_dict = self.unescape_bin_dict
        return self.escape_bin_re.sub(lambda m: unescape_bin_dict[m.group(0)], b)


    def hasnonliterals(self, s):
        '''
        Make sure that a string does not contain any code points that are not
        allowed as literals.
        '''
        sanitized_s = s.translate(self.filter_nonliterals_dict)
        if len(sanitized_s) != len(s):
            return True
        else:
            return False


    def tracenonliterals(self, s):
        '''
        Give the location of all code points in a string that are not allowed as
        literals.  Return a list of named tuples that contains the line numbers
        and code points.  Line numbers are given in two forms, one calculated
        using standard `\r`, `\r\n`, `\n` newlines, and one using all Unicode
        newlines.  All returned characters are escaped, so that the output may
        be used as-is.
        '''
        # Create a string containing all unique, allowed newlines
        nlc = self.newline_chars_str
        trace = []
        # Keep track of how many lines didn't end with `\r`, `\n`, or `\r\n`
        offset = 0
        # Work with a copy of s in which all literals, except for newlines, are removed
        for n, line in enumerate(s.translate(self.filter_literalslessnewlines_dict).splitlines(True)):
            nonlits = line.rstrip(nlc)
            if nonlits:
                trace.append(NonliteralTrace(self.escape(nonlits), n-offset+1, n+1))
            if not len(line.rstrip('\r\n')) < len(line):
                offset += 1
        return trace


    def unicode_to_bin_newlines(self, s):
        '''
        Convert all Unicode newlines (not `\r`, `\n`, `\r\n`) into
        bytes-compatible newlines `\n`.
        '''
        return s.translate(self.unicode_to_bin_newlines_dict)


    def removenewlines(self, s):
        '''
        Remove all newlines from a string.
        '''
        return s.translate(self.remove_newlines_dict)


    def remove_whitespace(self, s):
        '''
        Remove all whitespace (indentation plus newlines plus spaces) from a
        string.
        '''
        return s.translate(self.remove_whitespace_dict)
