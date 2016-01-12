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




# Unicode characters to be treated as line terminators
# http://unicode.org/standard/reports/tr13/tr13-5.html
# Common line endings `\r`, `\n`, and `\r\n`, plus NEL, vertical tab,
# form feed, Line Separator, and Paragraph Separator
UNICODE_NEWLINES = set(['\r', '\n', '\r\n', '\u0085', '\v', '\f', '\u2028', '\u2029'])
UNICODE_NEWLINE_CHARS = set(x for x in UNICODE_NEWLINES if len(x) == 1)
UNICODE_NEWLINE_CHARS_ORD = set(ord(c) for c in UNICODE_NEWLINE_CHARS)
UNICODE_NEWLINE_CHAR_UNESCAPES = {'\\r': '\r',
                                  '\\n': '\n',
                                  '\\u0085', '\u0085',
                                  '\\v': '\v',
                                  '\\f': '\f',
                                  '\\u2028': '\u2028',
                                  '\\u2029': '\u2029'}
UNICODE_NEWLINE_CHAR_ESCAPES = {v, k for k, v in UNICODE_NEWLINE_CHAR_UNESCAPES}


# Default allowed newlines
BESPON_DEFAULT_NEWLINES = set(['\r', '\n', '\r\n'])


# Characters with Unicode category "Other, Control" (Cc)
# http://www.fileformat.info/info/unicode/category/Cc/index.htm
# Ord ranges 0-31, 127, 128-159
UNICODE_CC_ORD = set(list(range(0x0000, 0x001F+1)) + [0x007F] + list(range(0x0080, 0x009F+1)))
UNICODE_CC = set(chr(c) for c in UNICODE_CC_ORD)


# Default allowed CC characters
BESPON_DEFAULT_CC_LITERALS = set(['\t', '\n', '\r'])
BESPON_DEFAULT_CC_LITERALS_ORD = set(ord(c) for c in BESPON_DEFAULT_CC_LITERALS)


# Default characters not allowed as literals
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




class UnicodeFilter(object):
    '''
    Check strings for literal characters that are not allowed, backslash-escape
    and backslash-unescape strings, etc.
    '''
    def __init__(self, literals=None, nonliterals=None,
                 shortescapes=None, shortunescapes=None,
                 xescapes=True, sloppyescapes):
        # Special characters to be allowed as literals, beyond defaults,
        # and characters not to be allowed as literals, beyond defaults
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
            if literals & nonliterals:
                raise ValueError('Overlap between characters in "literals" and "nonliterals"')
            nonliterals = (BESPON_DEFAULT_NONLITERALS - literals) | nonliterals
            newlines = UNICODE_NEWLINES - nonliterals
            if '\r\n' in nonliterals:
                if '\r' in nonliterals and '\n' in nonliterals:
                    nonliterals = nonliterals - set(['\r\n'])
                else:
                    raise ValueError('The sequence "\\r\\n" cannot be treated as a nonliteral without also treating "\\r" and "\\n" as nonliterals')
            if not all(len(c) == 1 for c in nonliterals):
                raise ValueError('Only single characters can be specified as nonliterals, with the exception of "\\r\\n"')
        self.nonliterals = nonliterals
        self.newlines = newlines
        self.nonliteralsdict = {ord(c): None for c in self.nonliterals}


        # Dicts that map characters to their escaped versions, and vice versa
        if shortescapes is None:
            shortescapes = BESPON_SHORT_ESCAPES
        if '\\' not in shortescapes:
            raise TypeError('Short backslash escapes must define the escape of "\\"')
        if not all(len(c) == 1 for c in shortescapes):
            raise ValueError('Short escapes only map single characters/code points to escapes, not groups of code points')
        self.shortescapes = shortescapes
        if shortunescapes is None:
            shortunescapes = BESPON_SHORT_UNESCAPES
        if '\\\\' not in shortunescapes:
            raise TypeError('Short backslash unescapes must define the meaning of "\\\\"')
        if not all(x.startswith('\\') and len(x) == 2 and ord(x[1]) < 128 for x in shortunescapes):
            raise ValueError('All short backlash unescapes be a backslash followed by a single ASCII character')
        if any(pattern in shortunescapes for pattern in ('\\x', '\\X', '\\u', '\\U', '\\o', '\\O')):
            raise ValueError('Short backlash unescapes cannot use the letters X, U, or O, in either upper or lower case')
        self.shortunescapes = shortunescapes


        # Whether `\xHH` escapes are allowed
        if xescapes:
            self.escape_re = re.compile(r'(\\x..|\\u....|\\U........|\\.|\\)', re.DOTALL)
            self._escape_unicode_char = self._escape_unicode_char_xuU
        else:
            self.escape_re = re.compile(r'(\\u....|\\U........|\\.|\\)', re.DOTALL)
            self._escape_unicode_char = self._escape_unicode_char_uU


        # Whether unrecognized short (2-letter) backlash escapes raise an error
        # or are interpreted as a backlash followed by a literal character
        if sloppyescapes:
            self._unicode_escaped_hex_to_char_factory = self._unicode_escaped_hex_to_char_factory_sloppy
        else:
            self._unicode_escaped_hex_to_char_factory = self._unicode_escaped_hex_to_char_factory_strict


        # Dict for escaping characters that may not appear literally
        # This is a minimalist form of escaping, given the current literals
        escapedict = {ord(c): self._escape_unicode_char(c) for c in self.nonliterals}
        for k, v in self.shortescapes.items():
            n = ord(k)
            if n in escapedict:
                escapedict[n] = v
        # Want everything that must be escaped, plus the backslash that makes
        # escaping possible in the first place
        escapedict[ord('\\')] = shortescapes['\\']
        self.escapedict = escapedict

        self.fullescapedict = escapedict.copy().update(self.shortescapes)

        self.asciiescapedict = keydefaultdict(self._unicode_to_escaped_ascii_factory, self.escapedict)
        self.fullasciiescapedict = keydefaultdict(self._unicode_to_escaped_ascii_factory, self.fullescapedict)


        # Dict for escaping with default settings -- useful in creating
        # broadly compatible escapes when using a non-standard configuration
        if (self.nonliterals is BESPON_DEFAULT_NONLITERALS and
                self.newlines is BESPON_DEFAULT_NEWLINES):
            self.defaultescapedict = self.escapedict
            self.defaultfullescapedict = self.fullescapedict
            self.defaultasciiescapedict = self.asciiescapedict
            self.defaultfullasciiescapedict = self.fullasciiescapedict
        else:
            defaultescapedict = {ord(c): self._escape_unicode_char(c) for c in BESPON_DEFAULT_NONLITERALS}
            for k, v in BESPON_SHORT_ESCAPES.items():
                n = ord(k)
                if n in defaultescapedict:
                    defaultescapedict[n] = v
            defaultescapedict[ord('\\')] = defaultescapedict['\\']
            self.defaultescapedict = defaultescapedict

            self.defaultfullescapedict = defaultescapedict.copy().update(BESPON_SHORT_ESCAPES)

            self.defaultasciiescapedict = keydefaultdict(self._unicode_to_escaped_ascii_factory, self.defaultescapedict)
            self.defaultfullasciiescapedict = keydefaultdict(self._unicode_to_escaped_ascii_factory, self.defaultfullescapedict)


        # Dict for unescaping with current settings
        self.unescapedict = keydefaultdict(self._unicode_escaped_hex_to_char_factory, self.shortunescapes)

        if self.shortunescapes is BESPON_SHORT_UNESCAPES:
            self.defaultunescapedict = self.unescapedict
        else:
            self.defaultunescapedict = keydefaultdict(self._unicode_escaped_hex_to_char_factory, BESPON_SHORT_UNESCAPES)

        # Dict for default unescaping
        if self.shortunescapes is BESPON_SHORT_UNESCAPES:
            self.defaultunescapedict = self.unescapedict
        else:
            self.defaultunescapedict = keydefaultdict(self._unicode_escaped_hex_to_char_factory, BESPON_SHORT_UNESCAPES)


    @staticmethod
    def _escape_unicode_char_xuU(c):
        '''
        Escape a Unicode character using `\\xHH` (8-bit), `\\uHHHH` (16-bit),
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
        Escape a Unicode character using \\uHHHH` (16-bit),
        or `\\UHHHHHHHH` (32-bit) notation.
        '''
        n = ord(c)
        if n < 65536:
            e = '\\u{0:04x}'.format(n)
        else:
            e = '\\U{0:08x}'.format(n)
        return e


    @staticmethod
    def _unicode_escaped_hex_to_char_factory_strict(s):
        '''
        Given a string in `\\xHH`, `\\uHHHH`, or `\\UHHHHHHHH` form, return the
        Unicode character corresponding to the hex value of the `H`'s.  Raise
        an error for `\\<char>`, which is the only other form the argument will
        ever take.

        Arguments to this function are prefiltered by a regex into the allowed
        hex escape forms.  Before this function is invoked, all known short
        (2-letter) escape sequences have already been filtered out.  Any
        remaining short escapes `\\<char>` at this point are unrecognized.
        '''
        try:
            v = chr(int(s[2:]), 16)
        except ValueError:
            sys.stderr.write('Unsupported backslash-escape "{0}"'.format(s))
            raise
        return v


    @staticmethod
    def _unicode_escaped_hex_to_char_factory_sloppy(s):
        '''
        Given a string in `\\xHH`, `\\uHHHH`, or `\\UHHHHHHHH` form, return the
        Unicode character corresponding to the hex value of the `H`'s.  In the
        even of receiving `\\<char>`, return it unchanged.

        Arguments to this function are prefiltered by a regex into the allowed
        hex escape forms.  Before this function is invoked, all known short
        (2-letter) escape sequences have already been filtered out.  Any
        remaining short escapes `\\<char>` at this point are unrecognized.
        '''
        try:
            v = chr(int(s[2:]), 16)
        except ValueError:
            pass
        return v


    @staticmethod
    def _unicode_to_escaped_ascii_factory(c):
        '''
        Given a character, return an escaped version in `\\xHH`, `\\uHHHH`, or
        `\\UHHHHHHHH` form for all non-ASCII characters.
        '''
        if not ord(s) < 128:
            c = self._escape_unicode_char(c)
        return c


    def escape(self, s):
        '''
        Within a string, replace all characters that are not allowed to appear
        literally with their escaped counterparts.
        '''
        return s.translate(self.escapedict)


    def fullescape(self, s):
        '''
        Within a string, replace all characters that are Unicode Cc or newlines,
        or that have short escaped forms, with their escaped counterparts.
        '''
        return s.translate(self.fullescapedict)


    def asciiescape(self, s):
        '''
        Within a string, replace all non-printable or non-ASCII characters with
        their escaped counterparts.
        '''
        return s.translate(self.asciiescapedict)


    def unescape(self, s):
        '''
        Within a string, replace all backslash escapes of the form `\\xHH`,
        `\\uHHHH`, and `\\UHHHHHHHH`, as well as the form `\\<CHAR>`, with the
        corresponding characters.
        '''
        # Local reference to escapedict to speed things up a little
        unescapedict = self.unescapedict
        # For reference:  self.escape_re = re.compile(r'(\\x..|\\u....|\\U........|\\.|\\)', re.DOTALL)
        return self.escape_re.sub(lambda m: unescapedict[m.group(0)], s)


    def hasnonliterals(self, s):
        '''
        Make sure that a string does not contain any characters that are not
        allowed as literals
        '''
        sanitized_s = s.translate(self.nonliteralsdict)
        r = set()
        if len(sanitized_s) != len(s):
            r = set(s) & self.nonliterals
        return r
