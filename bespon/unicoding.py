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
    str = unicode
    __chr__ = chr
    chr = unichr

try:
    chr(0x10FFFF)
    NARROW_BUILD = False
except ValueError:
    NARROW_BUILD = True

import collections
import re
from . import erring




# Unicode code points to be treated as line terminators
# http://unicode.org/standard/reports/tr13/tr13-5.html
# Common line endings `\r`, `\n`, and `\r\n`, plus NEL, vertical tab,
# form feed, Line Separator, and Paragraph Separator
UNICODE_NEWLINES = set(['\r', '\n', '\r\n', '\u0085', '\v', '\f', '\u2028', '\u2029'])
UNICODE_NEWLINE_CHARS = set(x for x in UNICODE_NEWLINES if len(x) == 1)


# Default allowed newlines
BESPON_DEFAULT_NEWLINES = set(['\r', '\n', '\r\n'])


# Code points with Unicode category "Other, Control" (Cc)
# http://www.fileformat.info/info/unicode/category/Cc/index.htm
# Ord ranges 0-31, 127, 128-159
UNICODE_CC = set(chr(c) for c in list(range(0x0000, 0x001F+1)) + [0x007F] + list(range(0x0080, 0x009F+1)))


# Default allowed CC code points
BESPON_DEFAULT_CC_LITERALS = set(['\t', '\n', '\r'])


# Default code points not allowed as literals
BESPON_DEFAULT_NONLITERALS = (UNICODE_CC - BESPON_DEFAULT_CC_LITERALS) | (UNICODE_NEWLINES - BESPON_DEFAULT_NEWLINES)


BESPON_INDENTS = set(['\x20', '\t', '\u3000'])
BESPON_SPACES = set(['\x20', '\u3000'])


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
            self[k] = self.default_factory(k)
            return self[k]




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
    def __init__(self, literals=None, nonliterals=None,
                 shortescapes=None, shortunescapes=None,
                 onlyascii=False, xescapes=True):
        # If a `Source()` instance is provided, enhanced tracebacks are
        # possible in some cases.  Start with default value.
        self.source = None


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
                if NARROW_BUILD:
                    raise erring.ConfigError('Only single code points can be specified as nonliterals, with the exception of "\\r\\n"; narrow Python build will not work with points not in range(0x10000)')
                else:
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


        self.spaces = BESPON_SPACES
        self.spaces_str = ''.join(self.spaces)
        self.indents = BESPON_INDENTS
        self.indents_str = ''.join(self.indents)
        if self.spaces & self.nonliterals or self.indents & self.nonliterals:
            raise erring.ConfigError('Space and indentation characters cannot be treated as nonliterals')
        # Overall whitespace
        self.whitespace = self.indents | self.newline_chars | self.spaces
        self.whitespace_str = ''.join(self.whitespace)
        self.remove_whitespace_dict = {ord(c): None for c in self.whitespace}


        # Dicts that map code points to their escaped versions, and vice versa
        if shortescapes is None:
            shortescapes = BESPON_SHORT_ESCAPES
        else:
            if '\\' not in shortescapes:
                raise erring.ConfigError('Short backslash escapes must define the escape of "\\"')
            if not all(len(c) == 1 and ord(c) < 128 for c in shortescapes):
                raise erring.ConfigError('Short escapes only map single code points in the ASCII range to escapes')
            if not all(len(v) == 2 and 0x21 <= ord(v[1]) <= 0x7E for k, v in shortescapes.items()):
                # 0x21 through 0x7E is `!` through `~`, all printable ASCII
                # except for space (0x20), which shouldn't be allowed since
                # it is (optionally) part of newline escapes
                raise erring.ConfigError('Short escapes only map single code points to a backslash followed by a single ASCII character in 0x21 through 0x7E')
        self.shortescapes = shortescapes

        if shortunescapes is None:
            shortunescapes = BESPON_SHORT_UNESCAPES
        else:
            if '\\\\' not in shortunescapes:
                raise erring.ConfigError('Short backslash unescapes must define the meaning of "\\\\"')
            if not all(x.startswith('\\') and len(x) == 2 and 0x21 <= ord(x[1]) <= 0x7E for x in shortunescapes):
                raise erring.ConfigError('All short backlash unescapes be a backslash followed by a single ASCII character in 0x21 through 0x7E')
            if not all(len(v) == 1 and ord(v) < 128 for k, v in shortunescapes.items()):
                raise erring.ConfigError('All short backlash unescapes be map to a single ASCII code point')
            if any(pattern in shortunescapes for pattern in ('\\x', '\\X', '\\u', '\\U', '\\o', '\\O')):
                raise erring.ConfigError('Short backlash unescapes cannot use the letters X, U, or O, in either upper or lower case')
        self.shortunescapes = shortunescapes

        # Binary variants
        self.shortescapes_bin = {k.encode('ascii'): v.encode('ascii') for k, v in self.shortescapes.items()}
        self.shortunescapes_bin = {k.encode('ascii'): v.encode('ascii') for k, v in self.shortunescapes.items()}


        # Whether `\xHH` escapes are allowed
        escape_re_pattern = r'\\x..|\\u....|\\U........|\\[{spaces}]*(?:{newlines})|\\.|\\'
        # Since `newlines` is a set that may contain a two-character sequence
        # (`\r\n`), need to ensure that any two-character sequence appears
        # first in matching, so need reversed `sorted()`
        escape_re_pattern = escape_re_pattern.format(newlines='|'.join(sorted(self.newlines, reverse=True)), spaces=self.spaces_str)
        if xescapes:
            self.escape_re = re.compile(escape_re_pattern, re.DOTALL)
            self._escape_unicode_char = self._escape_unicode_char_xuU
        else:
            self.escape_re = re.compile(escape_re_pattern.lsplit('|', 1)[1], re.DOTALL)
            self._escape_unicode_char = self._escape_unicode_char_uU

        escape_bin_re_pattern = r'\\x..|\\\x20*(?:\r\n|\r|\n)|\\.|\\'.encode('ascii')
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
        escape_dict[ord('\\')] = self.shortescapes['\\']
        if not onlyascii:
            self.escape_dict = escape_dict
        else:
            # Factory function adds characters to dict as they are requested
            # All escapes already in `escape_dict` are valid ASCII, since
            # `_escape_unicode_char()` gives hex escapes, and short escapes
            # must use printable ASCII characters
            self.escape_dict = keydefaultdict(self._unicode_ord_to_escaped_ascii_factory, escape_dict)

        # The bin dicts map ints to individual bytes or byte strings.
        # This looks the same as the Unicode case, but the usage is different
        # because `bytes.translate()` apparently only maps individual bytes to
        # individual bytes, so it can't be used.  `b''.join(...)` is used
        # instead, iterating over the byte string.  Since iterating over a
        # byte string yields ints, we still need a mapping of ints to (byte)
        # strings.  Unfortunately, for Python 2 compatibility, we actually
        # need a mapping of individual bytes to byte strings, and have to
        # use `bytes(bytearray([<int>]))` instead of Python 3's
        # `bytes([<int>])`.
        escape_bin_dict = {n: chr(n).encode('ascii') if chr(n) not in self.nonliterals else b'\\x'+hex(n)[2:].encode('ascii') for n in range(0, 127)}
        escape_bin_dict.update({n: b'\\x'+hex(n)[2:].encode('ascii') for n in range(127, 256)})
        for k, v in self.shortescapes_bin.items():
            n = ord(k)
            if n in escape_bin_dict and chr(n) in self.nonliterals:
                escape_bin_dict[n] = v
        escape_bin_dict[ord(b'\\')] = self.shortescapes_bin[b'\\']
        if sys.version_info.major == 2:
            self.escape_bin_dict = {bytes(bytearray([k])): v for k, v in escape_bin_dict.items()}
        else:
            self.escape_bin_dict = escape_bin_dict


        # Escaping with no literal line breaks
        # Inherits onlyascii settings
        # Copy over all newlines escapes and the tab short escape, if it exists
        escape_to_inline_dict = self.escape_dict.copy()
        for c in UNICODE_NEWLINE_CHARS:
            n = ord(c)
            try:
                escape_to_inline_dict[n] = self.shortescapes[c]
            except KeyError:
                escape_to_inline_dict[n] = self._escape_unicode_char(c)
        if '\t' in self.shortescapes:
            escape_to_inline_dict[ord('\t')] = self.shortescapes['\t']
        self.escape_to_inline_dict = escape_to_inline_dict

        # It is important here to use `escape_bin_dict`, and NOT
        # `self.escape_bin_dict`, since they may be different depending on
        # Python versions
        escape_to_inline_bin_dict = escape_bin_dict.copy()
        for c in UNICODE_NEWLINE_CHARS:
            n = ord(c)
            if n < 128:
                c = c.encode('ascii')
                try:
                    escape_to_inline_bin_dict[n] = self.shortescapes_bin[c]
                except KeyError:
                    escape_to_inline_bin_dict[n] = b'\\x'+hex(n)[2:].encode('ascii')
        if b'\t' in self.shortescapes_bin:
            escape_to_inline_bin_dict[ord(b'\t')] = self.shortescapes_bin[b'\t']
        if sys.version_info.major == 2:
            self.escape_to_inline_bin_dict = {bytes(bytearray([k])): v for k, v in escape_to_inline_bin_dict.items()}
        else:
            self.escape_to_inline_bin_dict = escape_to_inline_bin_dict


        # Dict for unescaping with current settings
        # Used for looking up backlash escapes found by `re.sub()`
        # Starts with all short escapes; the factory function adds additional
        # escapes as they are requested
        self.unescape_dict = keydefaultdict(self._unicode_escaped_hex_to_char_factory, self.shortunescapes)
        self.unescape_bin_dict = keydefaultdict(self._bin_escaped_hex_to_bytes_factory, self.shortunescapes_bin)


        # Dict for tranlating Unicode newlines into a bytes-compatible form
        # Useful for working with binary strings if a file uses `\u0085`,
        # `\u2028`, or `\u2029` to represent newlines
        self.unicode_to_bin_newlines_dict = {ord(c): '\n' for c in UNICODE_NEWLINE_CHARS if ord(c) >= 128}


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


    def _unicode_ord_to_escaped_ascii_factory(self, n):
        '''
        Given a code point (ord), return an escaped version in `\\xHH`,
        `\\uHHHH`, or `\\UHHHHHHHH` form for all non-ASCII code points.

        This is used in dicts for `str.translate()`, so an integer is received
        and a character or escaped sequence is returned.
        '''
        c = chr(n)
        if not n < 128:
            c = self._escape_unicode_char(c)
        return c


    def _unicode_escaped_hex_to_char_factory(self, s):
        '''
        Given a string in `\\xHH`, `\\uHHHH`, or `\\UHHHHHHHH` form, return the
        Unicode code point corresponding to the hex value of the `H`'s.  Given
        `\\<spaces or ideographic spaces><newline>`, return an empty string.
        Otherwise, raise an error for `\\<char>` or `\\`, which is the only
        other form the argument will ever take.

        Arguments to this function are prefiltered by a regex into the allowed
        hex escape forms.  Before this function is invoked, all known short
        (2-letter) escape sequences have already been filtered out.  Any
        remaining short escapes `\\<char>` at this point are unrecognized.
        '''
        # Consider special treatment of surrogates 0xd800 to 0xdfff?
        try:
            v = chr(int(s[2:], 16))
        except ValueError:
            # Need to make sure we have the pattern
            # `\\<spaces or ideographic spaces><newline>`
            # Given regex, no need to worry about multiple newlines
            if (s != '\\' and s[1:] != s[1:].rstrip(self.newline_chars_str) and
                    not s[1:].lstrip(self.spaces_str).rstrip(self.newline_chars_str)):
                v = ''
            else:
                raise erring.UnknownEscapeError(s, self.source)
        return v


    def _bin_escaped_hex_to_bytes_factory(self, b):
        '''
        Given a binary string in `\\xHH` form, return the byte corresponding
        to the hex value of the `H`'s.  Given `\\<spaces><newline>`, return an
        empty byte string.  Otherwise, raise an error for `\\<byte>` or `\\`,
        which is the only other form the argument will ever take.

        Arguments to this function are prefiltered by a regex into the allowed
        hex escape forms.  Before this function is invoked, all known short
        (2-letter) escape sequences have already been filtered out.  Any
        remaining short escapes `\\<char>` at this point are unrecognized.
        '''
        try:
            # Python 3 only would be:
            #   v = int(b[2:], 16).to_bytes(1, 'little')
            v = bytes(bytearray([int(b[2:], 16)]))
        except ValueError:
            # Make sure we have the full pattern `\\<spaces><newline>`
            if (b != b'\\' and b[1:] != b[1:].rstrip(b'\r\n') and
                     not b[1:].lstrip(b'\x20').rstrip(b'\r\n')):
                v = b''
            else:
                # Using `decode('ascii')` is safe here because any binary
                # strings will have started off as Unicode strings that were
                # then encoded to ASCII.  If the code is ever used for other
                # purposes, or the order of operations is changed, then
                # translating back to Unicode might require more care.
                raise erring.UnknownEscapeError(b.decode('ascii'), self.source)
        return v


    def escape(self, s):
        '''
        Within a string, replace all code points that are not allowed to appear
        literally with their escaped counterparts.
        '''
        return s.translate(self.escape_dict)


    def escape_bin(self, b):
        '''
        Within a binary string, replace all bytes that are not allowed to
        appear literally with their escaped counterparts.
        '''
        escape_bin_dict = self.escape_bin_dict
        return b''.join(escape_bin_dict[x] for x in b)


    def escape_to_inline(self, s):
        '''
        Within a string, replace all code points that are not allowed to appear
        literally with their escaped counterparts.  Also escape all newlines.
        '''
        return s.translate(self.escape_to_inline_dict)


    def escape_to_inline_bin(self, b):
        '''
        Within a binary string, replace all bytes that are not allowed to appear
        literally with their escaped counterparts.  Also escape all newlines.
        '''
        escape_to_inline_bin_dict = self.escape_to_inline_bin_dict
        return b''.join(escape_to_inline_bin_dict[x] for x in b)


    def unescape(self, s):
        '''
        Within a string, replace all backslash escapes of the form `\\xHH`,
        `\\uHHHH`, and `\\UHHHHHHHH`, as well as the form `\\<char>`, with the
        corresponding code points.
        '''
        # Local reference to speed things up a little
        unescape_dict = self.unescape_dict
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
        newline_chars_str = self.newline_chars_str
        trace = []
        # Keep track of how many lines didn't end with `\r`, `\n`, or `\r\n`
        offset = 0
        # Work with a copy of s in which all literals, except for newlines, are removed
        for n, line in enumerate(s.translate(self.filter_literalslessnewlines_dict).splitlines(True)):
            nonlits = line.rstrip(newline_chars_str)
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
        if self.newlines != BESPON_DEFAULT_NEWLINES:
            return s.translate(self.unicode_to_bin_newlines_dict)
        else:
            return s


    def remove_whitespace(self, s):
        '''
        Remove all whitespace (indentation plus newlines plus spaces) from a
        string.
        '''
        return s.translate(self.remove_whitespace_dict)
