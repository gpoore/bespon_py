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
from . import tooling




# Unicode code points to be treated as line terminators
# http://unicode.org/standard/reports/tr13/tr13-5.html
# Common line endings `\r`, `\n`, and `\r\n`, plus NEL, vertical tab,
# form feed, Line Separator, and Paragraph Separator
UNICODE_NEWLINES = set(['\r', '\n', '\r\n', '\u0085', '\v', '\f', '\u2028', '\u2029'])
UNICODE_NEWLINE_CHARS = set(x for x in UNICODE_NEWLINES if len(x) == 1)


# Default allowed literal newlines
BESPON_NEWLINES = set(['\r', '\n', '\r\n'])


# Code points with Unicode category "Other, Control" (Cc)
# http://www.fileformat.info/info/unicode/category/Cc/index.htm
# Ord ranges 0-31, 127, 128-159
UNICODE_CC = set(chr(c) for c in list(range(0x0000, 0x001F+1)) + [0x007F] + list(range(0x0080, 0x009F+1)))


# Default allowed CC code points
BESPON_CC_LITERALS = set(['\t', '\n', '\r'])


# Bidi override characters can be a security concern in general, and are not
# appropriate in a human-friendly, text-based format
# Unicode Technical Report #36, UNICODE SECURITY CONSIDERATIONS
# http://unicode.org/reports/tr36/
UNICODE_BIDI_OVERRIDES = set(['\u202D', '\u202E'])


# Default code points not allowed as literals
BESPON_NONLITERALS = (UNICODE_CC - BESPON_DEFAULT_CC_LITERALS) | (UNICODE_NEWLINES - BESPON_DEFAULT_NEWLINES) | UNICODE_BIDI_OVERRIDES


# Code points with Unicode category "Separator, Space" (Zs)
# http://www.fileformat.info/info/unicode/category/Zs/index.htm
UNICODE_ZS = set(['\x20',   '\xa0',   '\u1680', '\u2000', '\u2001', '\u2002',
                  '\u2003', '\u2004', '\u2005', '\u2006', '\u2007', '\u2008',
                  '\u2009', '\u200a', '\u202f', '\u205f', '\u3000'])


# Unicode whitespace, equivalent to Unicode regex `\s`
# Note that Python's `re` package matches `\s` to the separator control
# characters; the `regex` package doesn't.  Also, U+180E (Mongolian Vowel
# Separator) isn't whitespace in Unicode 8.0, but was in Unicode in 4.0-6.3
# apparently, which applies to Python 2.7's `re`.  So it's safer to use a
# defined set rather than relying on `re`.
UNICODE_WHITESPACE = UNICODE_ZS | UNICODE_NEWLINE_CHARS | set('\t')


# A few extra characters not in Zs, but that can look like spaces in many fonts.
# These don't get any special handling by default, but it could be convenient
# to treat them specially in some contexts.  Currently, this is just the
# Hangul fillers.  They are valid in identifier names in some programming
# languages.
UNICODE_WHITESPACE_VISUALLY_CONFUSABLE = set(['\u115F', '\u1160', '\u3164', '\uFFA0'])


# Characters that count as indentation and spaces
BESPON_INDENTS = set(['\x20', '\t'])
BESPON_SPACES = set(['\x20'])


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




# Structure for keeping track of which code points that are not allowed to
# appear literally in text did in fact appear, and where.
# `lineno` uses `\r`, `\n`, and `\r\n`, while `unicode_lineno` uses all of
#  UNICODE_NEWLINES.
NonliteralTrace = collections.namedtuple('NonliteralTrace', ['chars', 'lineno', 'unicode_lineno'])




class UnicodeFilter(object):
    '''
    Check strings for literal code points that are not allowed,
    backslash-escape and backslash-unescape strings, filter out newline
    characters, etc.
    '''
    def __init__(self, literals=None, nonliterals=None,
                 short_escapes=None, short_unescapes=None,
                 only_ascii=False, x_escapes=True, brace_escapes=True):
        # If a `Source()` instance is provided, enhanced tracebacks are
        # possible in some cases.  Start with default value.
        self.source = None


        # Specified code points to be allowed as literals, beyond defaults,
        # and code points not to be allowed as literals, beyond defaults,
        # are used to create a set of code points that aren't allowed unescaped
        if literals is None and nonliterals is None:
            nonliterals = BESPON_NONLITERALS
            newlines = BESPON_NEWLINES
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
                # newlines; it also splits on separators.  Either these
                # characters must never be allowed as literals, or
                # alternatively parsing must be adapted to account for them.
                raise erring.ConfigError('The File Separator (\\x1c), Group Separator (\\x1d), and Record Separator (\\x1e) are not allowed as literals by this implementation')
            if literals & nonliterals:
                raise erring.ConfigError('Overlap between code points in "literals" and "nonliterals"')
            nonliterals = (BESPON_NONLITERALS - literals) | nonliterals
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
        # `str.translate()` -- this provides an easy way of locating all
        # nonliterals that are present on each line of the source
        self.filter_literalslessnewlines_dict = collections.defaultdict(lambda: None)
        self.filter_literalslessnewlines_dict.update({ord(c): c for c in self.nonliterals})
        self.filter_literalslessnewlines_dict.update({ord(c): c for c in UNICODE_NEWLINE_CHARS})


        # Spaces, indentation, and whitespace
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
        self.unicode_whitespace = UNICODE_WHITESPACE
        self.unicode_whitespace_str = ''.join(self.unicode_whitespace)


        # Dicts that map code points to their escaped versions, and vice versa.
        # A separate version for binary is not needed given the current
        # approach.  Incoming data will already be in string form, so it is
        # unescaped as a string before being encoded to binary via the Latin-1
        # codec, which covers 0x00 through 0xFF.  Outgoing binary data will
        # typically start in binary form.  If the target output is a string,
        # then the binary data will ultimately have to be converted to string
        # form, and can be escaped in that form.  If the output target is a
        # file, then it would be possible to stay in binary.
        # However, `bytes.translate()` can only be used to convert a single
        # byte into a single byte, rather than into a series of bytes, so it
        # can't be used for escaping.  Also, differences in bytes handling
        # between Python 2 and Python 3 make working with binary directly a
        # little trickier.  To keep things simple and use a single approach for
        # all outgoing binary cases, binary data is decoded as Latin-1, then
        # escaped via `str.translate()`, and finally re-encoded as necessary.
        # The decoding/encoding process should have minimal overhead compared
        # to byte-at-a-time substitutions, particularly on Python 3.3+ due to
        # PEP 393.
        if short_escapes is None:
            short_escapes = BESPON_SHORT_ESCAPES
        else:
            if '\\' not in short_escapes:
                raise erring.ConfigError('Short backslash escapes must define the escape of "\\"')
            if not all(len(c) == 1 and ord(c) < 128 for c in short_escapes):
                raise erring.ConfigError('Short escapes only map single code points in the ASCII range to escapes')
            if not all(len(v) == 2 and 0x21 <= ord(v[1]) <= 0x7E for k, v in short_escapes.items()):
                # 0x21 through 0x7E is `!` through `~`, all printable ASCII
                # except for space (0x20), which shouldn't be allowed since
                # it is (optionally) part of newline escapes
                raise erring.ConfigError('Short escapes only map single code points to a backslash followed by a single ASCII character in 0x21 through 0x7E')
            if any(v in ('\\x', '\\X', '\\u', '\\U', '\\o', '\\O') for k, v in short_escapes.items()):
                raise erring.ConfigError('Short backlash escapes cannot use the letters X, U, or O, in either upper or lower case')
        self.short_escapes = short_escapes

        if short_unescapes is None:
            short_unescapes = BESPON_SHORT_UNESCAPES
        else:
            if '\\\\' not in short_unescapes:
                raise erring.ConfigError('Short backslash unescapes must define the meaning of "\\\\"')
            if not all(x.startswith('\\') and len(x) == 2 and 0x21 <= ord(x[1]) <= 0x7E for x in short_unescapes):
                raise erring.ConfigError('All short backlash unescapes be a backslash followed by a single ASCII character in 0x21 through 0x7E')
            if not all(len(v) == 1 and ord(v) < 128 for k, v in short_unescapes.items()):
                raise erring.ConfigError('All short backlash unescapes be map to a single ASCII code point')
            if any(pattern in short_unescapes for pattern in ('\\x', '\\X', '\\u', '\\U', '\\o', '\\O')):
                raise erring.ConfigError('Short backlash unescapes cannot use the letters X, U, or O, in either upper or lower case')
        self.short_unescapes = short_unescapes


        # Unescaping regex, depending on whether `\xHH` escapes are allowed and
        # whether `\u{HHHHHH}` escapes are in use.  Filtering to make sure the
        # escapes contain valid hex values is performed later.
        unescape_re_pattern = r'\\x..|\\u{{[^}}]{{1,6}}}}|\\u....|\\U........|\\[{spaces}]*(?:{newlines})|\\.|\\'
        # Since `newlines` is a set that may contain a two-character sequence
        # (`\r\n`), need to ensure that any two-character sequence appears
        # first in matching, so need reversed `sorted()`
        unescape_re_pattern = unescape_re_pattern.format(spaces=self.spaces_str, newlines='|'.join(sorted(self.newlines, reverse=True)))
        if not x_escapes:
            unescape_re_pattern = unescape_re_pattern.replace(r'\\x..|', '', 1)
        if not brace_escapes:
            unescape_re_pattern = unescape_re_pattern.replace(r'\\u{{[^}}]{{1,8}}}}|', '', 1)
        self.unescape_re = re.compile(unescape_re_pattern, re.DOTALL)
        # Again, binary tools use Unicode, because binary will be decoded with
        # Latin-1 before being operated on.
        unescape_latin1_bin_re_pattern = r'\\x..|\\\x20*(?:\r\n|\r|\n)|\\.|\\'
        self.unescape_latin1_bin_re = re.compile(unescape_latin1_bin_re_pattern, re.DOTALL)


        # Set function for escaping Unicode characters, based on whether `\xHH`
        # escapes are allowed and whether `\u{HHHHHH}` escapes are in use.
        # There are no such conditions for the binary equivalent.
        if x_escapes and brace_escapes:
            self._escape_unicode_char = self._escape_unicode_char_xubrace
        elif x_escapes:
            self._escape_unicode_char = self._escape_unicode_char_xuU
        elif brace_escapes:
            self._escape_unicode_char = self._escape_unicode_char_ubrace
        else:
            self._escape_unicode_char = self._escape_unicode_char_uU


        # Dict for escaping code points that may not appear literally.
        # Use with `str.translate()`.
        # This is a minimalist form of escaping, given the current literals
        minimal_escape_dict = {ord(c): self._escape_unicode_char(c) for c in self.nonliterals}
        # Copy over any relevant short escapes
        for k, v in self.short_escapes.items():
            n = ord(k)
            if n in minimal_escape_dict:
                minimal_escape_dict[n] = v
        # Want everything that must be escaped, plus the backslash that makes
        # escaping possible in the first place
        minimal_escape_dict[ord('\\')] = self.shortescapes['\\']
        if not only_ascii:
            self.minimal_escape_dict = minimal_escape_dict
        else:
            # Factory function adds characters to dict as they are requested
            # All escapes already in `escape_dict` are valid ASCII, since
            # `_escape_unicode_char()` gives hex escapes, and short escapes
            # must use printable ASCII characters
            self.minimal_escape_dict = tooling.keydefaultdict(self._unicode_ord_to_escaped_ascii_factory, minimal_escape_dict)

        # Escaping with no literal line breaks.  Inherits `only_ascii`
        # settings.  Copy over all newline escapes and the tab short escape,
        # if it exists.
        inline_escape_dict = self.minimal_escape_dict.copy()
        for c in UNICODE_NEWLINE_CHARS:
            n = ord(c)
            try:
                inline_escape_dict[n] = self.short_escapes[c]
            except KeyError:
                inline_escape_dict[n] = self._escape_unicode_char(c)
        try:
            inline_escape_dict[ord('\t')] = self.short_escapes['\t']
        except KeyError:
            inline_escape_dict[ord('\t')] = self._escape_unicode_char('\t')
        self.inline_escape_dict = inline_escape_dict

        # The binary escape dicts are similar to the Unicode equivalents.
        # Only `\xHH` escapes are used.  There are two variants:  (1) a minimal
        # version based on printable ASCII plus allowed literals in the ASCII
        # range, which is suitable for binary strings that should be treated
        # as strings; and (2) a version in which everything but non-whitespace,
        # printable ASCII is escaped, which is suitable for binary data in
        # which exact byte values must be maintained (for example, `\r\n` vs.
        # `\n`).  In practice, it will typically be better to use base64
        # encoding for the second case, but there may be situations in which
        # using `\xHH` escapes is desirable due to readability.  The second
        # approach to escaping play the binary role of an inline escape, since
        # it allows no literal newlines.
        minimal_escape_latin1_bin_dict = {n: '\\x'+hex(n)[2:] if chr(n) in self.nonliterals or n >= 128 for n in range(0, 256)}
        maximal_escape_latin1_bin_dict = {n: '\\x'+hex(n)[2:] if 0x20 < n <= 0x7E for n in range(0, 256)}
        for k, v in self.short_escapes.items():
            n = ord(k)
            if n in minimal_escape_latin1_bin_dict:
                minimal_escape_latin1_bin_dict[n] = v
            if n in maximal_escape_latin1_bin_dict:
                maximal_escape_latin1_bin_dict[n] = v
        # Need backslash in both cases.  Need double quotes for maximal case
        # so that there's no need to check for valid delimiters.  For the
        # maximal case, escaping must be enabled to cover all possible bytes,
        # so there's no reason not to escape double quotes to simplify things.
        minimal_escape_latin1_bin_dict[ord('\\')] = self.short_escapes['\\']
        maximal_escape_latin1_bin_dict[ord('\\')] = self.short_escapes['\\']
        maximal_escape_latin1_bin_dict[ord('"')] = self.short_escapes['"']
        self.minimal_escape_latin1_bin_dict = minimal_escape_latin1_bin_dict
        self.maximal_escape_latin1_bin_dict = maximal_escape_latin1_bin_dict


        # Dicts for unescaping with current settings.  Used for looking up
        # backlash escapes found by `re.sub()`.  Start with all short escapes;
        # the factory functions add escapes as they are requested.
        self.unescape_dict = tooling.keydefaultdict(self._unicode_escaped_hex_to_char_factory, self.short_unescapes)
        self.unescape_latin1_bin_dict = tooling.keydefaultdict(self._latin1_bin_escaped_hex_to_char_factory, self.short_unescapes)


        # Dict for tranlating Unicode newlines into a bytes-compatible form.
        # Useful for working with binary strings if a file uses `\u0085`,
        # `\u2028`, or `\u2029` to represent newlines.
        self.unicode_to_latin1_bin_newlines_dict = {ord(c): '\n' for c in UNICODE_NEWLINE_CHARS if ord(c) >= 128}


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
            if 0xD800 <= n <= 0xDFFF:
                raise erring.UnicodeSurrogateError('\\u'+hex(n)[2:], self.source)
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
            if 0xD800 <= n <= 0xDFFF:
                raise erring.UnicodeSurrogateError('\\u'+hex(n)[2:], self.source)
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
        try:
            n = int(s[2:], 16)
            if 0xD800 <= n <= 0xDFFF:
                raise erring.UnicodeSurrogateError(s, self.source)
            v = chr(n)
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


    def has_nonliterals(self, s):
        '''
        Make sure that a string does not contain any code points that are not
        allowed as literals.
        '''
        sanitized_s = s.translate(self.filter_nonliterals_dict)
        if len(sanitized_s) != len(s):
            return True
        else:
            return False


    def trace_nonliterals(self, s):
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


    def format_nonliterals_trace(self, trace):
        '''
        Format a nonliterals trace.  Used with InvalidLiteralCharacterError.
        '''
        m =       ['  Line number  (Unicode)    Chars\n']
        template = '         {0}       {1}    {2}\n'

        for t in trace:
            m.append(template.format(str(t.lineno).rjust(4, ' '), str(t.unicode_lineno).rjust(4, ' '), t.chars))

        return ''.join(m)


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


    def fullwidth_to_ascii(self, s):
        '''
        Translate all printable fullwidth ASCII equivalents (except for the
        space) into corresponding ASCII (normal, halfwidth) characters.
        '''
        return s.translate(self.fullwidth_to_ascii_dict)


    def ascii_to_fullwidth(self, s):
        '''
        Translate all printable ASCII characters (except for the space) into
        corresponding fullwidth characters.
        '''
        return s.translate(self.ascii_to_fullwidth_dict)


    def to_ascii_and_fullwidth(self, s):
        '''
        Create a string containing all characters in the original string,
        plus their corresponding fullwidth forms.
        '''
        s = s.translate(self.fullwidth_to_ascii_dict)
        return s + s.translate(self.ascii_to_fullwidth_dict)
