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




# Unicode code points that are line terminators
# http://unicode.org/standard/reports/tr13/tr13-5.html
# Common line endings `\r`, `\n`, and `\r\n`, plus vertical tab, form feed,
# NEL, Line Separator, and Paragraph Separator
UNICODE_NEWLINES = set(['\v', '\f', '\r', '\n', '\r\n', '\u0085', '\u2028', '\u2029'])
UNICODE_NEWLINE_CHARS = set(''.join(UNICODE_NEWLINES))


# Default allowed literal newlines
BESPON_NEWLINES = set('\n')
BESPON_NEWLINE_CHARS = set(''.join(BESPON_NEWLINES))


# Code points with Unicode Category_Category Cc (Other, control)
# http://www.unicode.org/versions/Unicode9.0.0/ch23.pdf
# Ord ranges 0-31, 127-159
UNICODE_CC = set(chr(n) for n in list(range(0x0000, 0x001F+1)) + list(range(0x007F, 0x009F+1)))


# Default allowed CC code points
BESPON_CC_LITERALS = set(['\t', '\n'])


# Bidi override characters can be a security concern in general, and are not
# appropriate in a human-friendly, text-based format.
# Unicode Technical Report #36, UNICODE SECURITY CONSIDERATIONS
# http://unicode.org/reports/tr36/
UNICODE_BIDI_OVERRIDES = set(['\u202D', '\u202E'])


# Unicode surrogates.  By default these are not allowed, except when 
# properly paired under narrow Python builds.
# http://www.unicode.org/versions/Unicode9.0.0/ch23.pdf
UNICODE_HIGH_SURROGATES = set(chr(n) for n in range(0xD800, 0xDBFF+1))
UNICODE_LOW_SURROGATES = set(chr(n) for n in range(0xDC00, 0xDFFF+1))
UNICODE_SURROGATES = UNICODE_HIGH_SURROGATES | UNICODE_LOW_SURROGATES


# Default code points not allowed as literals.  This does not account
# for surrogates.  Paired surrogates can appear in valid strings
# under narrow Python builds, so surrogates cannot be prohibited in 
# general except under wide builds.
BESPON_NONLITERALS_LESS_SURROGATES = (UNICODE_CC - BESPON_CC_LITERALS) | (UNICODE_NEWLINE_CHARS - BESPON_NEWLINE_CHARS) | UNICODE_BIDI_OVERRIDES


# Code points with Unicode General_Category Zs (Separator, space)
# http://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt
UNICODE_ZS = set(['\x20',   '\xa0',   '\u1680', '\u2000', '\u2001', '\u2002',
                  '\u2003', '\u2004', '\u2005', '\u2006', '\u2007', '\u2008',
                  '\u2009', '\u200a', '\u202f', '\u205f', '\u3000'])


# Unicode whitespace, equivalent to Unicode regex `\s`.  It's safer to use 
# a defined set rather than relying on Python's `re` package.  With `re`,
# `\s` also matches the separator control characters.  Also, U+180E 
# (Mongolian Vowel Separator) was temporarily whitespace in Unicode 4.0 
# up until Unicode 6.3, which affects Python 2.7's `re`.  Note that the 
# `regex` package does the right thing using the most recent Unicode version.
UNICODE_WHITESPACE = UNICODE_ZS | UNICODE_NEWLINE_CHARS | set('\t')


# Default characters that count as indentation and spaces
BESPON_INDENTS = set(['\x20', '\t'])
BESPON_SPACES = set(['\x20'])


# Default short backslash escapes.  Two are less common:  `\e` is from GCC, 
# clang, etc., and `\/` is from JSON.  By default, these two are only used 
# in reading escapes, not in creating them.
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

BESPON_SHORT_ESCAPES = {v:k for k, v in BESPON_SHORT_UNESCAPES.items() if v not in ('/', '\x1B')}


# A few extra characters that are not in Zs, but that can look like spaces 
# in many fonts.  These don't get any special handling by default, but it 
# could be convenient to treat them specially in some contexts.  Currently, 
# this is just the Hangul fillers.  They are valid in identifier names in 
# some programming languages.
UNICODE_WHITESPACE_VISUALLY_CONFUSABLE = set(['\u115F', '\u1160', '\u3164', '\uFFA0'])


# Structure for reporting the literal appearance of code points that are not
# allowed as literals.  Line numbers are reported in two ways.  `lineno` 
# uses `\r`, `\n`, and `\r\n`, while `unicode_lineno` uses all of
# UNICODE_NEWLINES.
NonliteralTrace = collections.namedtuple('NonliteralTrace', ['chars', 'lineno', 'unicode_lineno'])


Traceback = collections.namedtuple('DefaultTraceback', ['source', 'start_lineno', 'end_lineno'])



class UnicodeFilter(object):
    '''
    Check strings for literal code points that are not allowed,
    backslash-escape and backslash-unescape strings, filter out newline
    characters, etc.
    '''
    def __init__(self, traceback=None, only_ascii=False,
                 literals=None, nonliterals=None,
                 short_escapes=None, short_unescapes=None,
                 x_escapes=True, brace_escapes=True,
                 unpaired_surrogates=False):
        # If a traceback object is provided that has `source`, `start_lineno`,
        # and `end_lineno`, then enhanced tracebacks are possible
        if traceback is not None:
            if not all(hasattr(traceback, x) for x in ('source', 'start_lineno', 'end_lineno')):
                raise erring.ConfigError('Invalid traceback object')
            self.traceback = traceback
        else:
            self.traceback = Traceback('<unknown>', '?', '?')

        if unpaired_surrogates not in (True, False):
            raise erring.ConfigError('"unpaired_surrogates" must be boolean')
        self.unpaired_surrogates = unpaired_surrogates


        # Assemble a set of all code points that are not allowed to appear
        # literally, taking into account any modification of this set from 
        # the defaults.  This set does not account for unpaired surrogates;
        # those are accounted for in assembling the appropriate regexes.
        # Including surrogates in the set wouldn't work with narrow builds.
        if literals is None and nonliterals is None:
            self._default_nonliterals = True
            nonliterals_less_surrogates = BESPON_NONLITERALS_LESS_SURROGATES
            newlines = BESPON_NEWLINES
        else:
            self._default_nonliterals = False
            if literals is None:
                literals = set()
            else:
                literals = set(literals)
                if not all(isinstance(x, str) for x in literals):
                    raise erring.ConfigError('"literals" must yield a set of Unicode code points')
            if nonliterals is None:
                nonliterals = set()
            else:
                nonliterals = set(nonliterals)
                if not all(isinstance(x, str) for x in nonliterals):
                    raise erring.ConfigError('"nonliterals" must yield a set of Unicode code points')
            if not (all(len(x) == 1 for x in literals) and all(len(x) == 1 for x in nonliterals)):
                if NARROW_BUILD:
                    raise erring.ConfigError('Only single code points can be given in "literals" and "nonliterals", and code points above U+FFFF cannot be used on narrow Python builds')
                else:
                    raise erring.ConfigError('Only single code points can be given in "literals" and "nonliterals"')
            if any(c in literals for c in '\x1c\x1d\x1e') and len('_\x1c_\x1d_\x1e_'.splitlines()) == 4:
                # Python's `str.splitlines()` doesn't just split on Unicode
                # newlines; it also splits on separators.  As a result, these
                # characters aren't supported as literals.
                raise erring.ConfigError('The File Separator (\\x1c), Group Separator (\\x1d), and Record Separator (\\x1e) are not allowed as literals by this implementation')
            if literals & nonliterals:
                raise erring.ConfigError('Overlap between code points in "literals" and "nonliterals"')
            if (literals & UNICODE_SURROGATES) or (nonliterals & UNICODE_SURROGATES):
                raise erring.ConfigError('"literals" and "nonliterals" are not allowed to specify surrogates (U+D800 - U+DFFF); use "unpaired_surrogates" to control these code points')
            nonliterals_less_surrogates = (BESPON_NONLITERALS_LESS_SURROGATES - literals) | nonliterals
            newlines = UNICODE_NEWLINES - nonliterals
            if '\r' in nonliterals or '\n' in nonliterals:
                newlines.remove('\r\n')
            if not newlines:
                raise erring.ConfigError('At least one literal newline code point must be allowed')
        self.nonliterals_less_surrogates = nonliterals_less_surrogates
        self.nonliterals_bytes_latin1 = set(chr(n) for n in range(256) if n >= 128 or chr(n) in self.nonliterals_less_surrogates)
        self.nonliterals_bytes = set(c.encode('latin1') for c in self.nonliterals_bytes_latin1)
        self.newlines = newlines
        # Order for creating newlines variables is important; need to avoid
        # duplicates due to `\r\n` in the event of custom newlines
        self.newline_chars = set(''.join(self.newlines))
        self.newline_chars_str = ''.join(self.newline_chars)
        self.newline_chars_ascii = set(c for c in self.newline_chars if ord(c) < 128)
        self.newline_chars_ascii_str = ''.join(self.newline_chars_ascii)
        self.newline_chars_non_ascii = set(c for c in self.newline_chars if ord(c) >= 128)
        self.newline_chars_non_ascii_str = ''.join(self.newline_chars_non_ascii)


        # Regexes for working with nonliterals.  Using `str.translate()` can 
        # be around an order of magnitude faster for pure ASCII under Python 
        # 3.5, but can be close to an order of magnitude slower otherwise.  
        # Regex performance is more reliable.
        nonlits_str = re.escape(''.join(self.nonliterals_less_surrogates))
        if self.unpaired_surrogates:
            # Regex for finding nonliterals
            self.nonliterals_re = re.compile(r'[{chars}]'.format(chars=nonlits_str))
            # Regexes for escaping nonliterals
            self.nonliterals_or_backslash_re = re.compile(r'[\\{chars}]'.format(chars=nonlits_str))
            self.nonliterals_or_backslash_newline_tab_re = re.compile(r'[\\{chars}{newlines}\t]'.format(chars=nonlits_str, newlines=re.escape(self.newline_chars_str)))
            # Regex for tracking down location of nonliterals
            self.not_nonliterals_or_newlines_re = re.compile(r'[^{chars}{newlines}]+'.format(chars=nonlits_str, newlines=re.escape(self.newline_chars_str)))
        else:
            if NARROW_BUILD:
                self.nonliterals_re = re.compile(r'[{chars}]|[\uD800-\uDBFF](?=[^\uDC00-\uDFFF]|$)|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]'.format(chars=nonlits_str))
                self.nonliterals_or_backslash_re = re.compile(r'[\\{chars}]|[\uD800-\uDBFF](?=[^\uDC00-\uDFFF]|$)|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]'.format(chars=nonlits_str))
                self.nonliterals_or_backslash_newline_tab_re = re.compile(r'[\\{chars}{newlines}\t]|[\uD800-\uDBFF](?=[^\uDC00-\uDFFF]|$)|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]'.format(chars=nonlits_str, newlines=re.escape(self.newline_chars_str)))
                self.not_nonliterals_or_newlines_re = re.compile(r'(?:[^{chars}{newlines}\uD800-\uDFFF]|[\uD800-\uDBFF][\uDC00-\uDFFF])+'.format(chars=nonlits_str, newlines=re.escape(self.newline_chars_str)))
            else:
                self.nonliterals_re = re.compile(r'[{chars}\uD800-\uDFFF]'.format(chars=nonlits_str))
                self.nonliterals_or_backslash_re = re.compile(r'[\\{chars}\uD800-\uDFFF]'.format(chars=nonlits_str))
                self.nonliterals_or_backslash_newline_tab_re = re.compile(r'[\\{chars}{newlines}\t\uD800-\uDFFF]'.format(chars=nonlits_str, newlines=re.escape(self.newline_chars_str)))
                self.not_nonliterals_or_newlines_re = re.compile(r'[^{chars}{newlines}\uD800-\uDFFF]+'.format(chars=nonlits_str, newlines=re.escape(self.newline_chars_str)))
        # Regex for working with nonliterals in binary
        self.nonliterals_or_backslash_bytes_re = re.compile(r'[\\{chars}]'.format(chars=re.escape(''.join(self.nonliterals_bytes_latin1))).encode('latin1'))
        self.nonliterals_or_backslash_newlines_tab_bytes_re = re.compile(r'[\\{chars}]'.format(chars=re.escape(''.join(chr(n) for n in range(256) if not 0x20 <= n <= 0x7E or chr(n) in self.nonliterals_bytes_latin1))).encode('latin1'))
        self.nonliterals_or_non_printable_non_whitespace_bytes_re = re.compile(r'[\\"{chars}]'.format(chars=re.escape(''.join(chr(n) for n in range(256) if not 0x21 <= n <= 0x7E or chr(n) in self.nonliterals_bytes_latin1))).encode('latin1'))


        # Regexes for working with purely ASCII text
        # Regex for finding non-ASCII
        self.unicode_re = re.compile(r'[^\u0000-\u007f]')
        # Regex for providing a trace of non-ASCII
        self.ascii_less_newlines_and_nonliterals_re = re.compile(r'[{0}]+'.format(re.escape(''.join(chr(n) for n in range(128) if chr(n) not in self.nonliterals_less_surrogates and chr(n) not in self.newline_chars))))


        # Spaces, indentation, and whitespace
        self.spaces = BESPON_SPACES
        self.spaces_str = ''.join(self.spaces)
        self.indents = BESPON_INDENTS
        self.indents_str = ''.join(self.indents)
        if not self._default_nonliterals:
            if (self.spaces & self.nonliterals_less_surrogates) or (self.indents & self.nonliterals_less_surrogates):
                raise erring.ConfigError('Space and indentation characters cannot be treated as nonliterals')
            if self.spaces - self.indents:
                raise erring.ConfigError('All space characters must also be treated as indentation characters')
        # Overall whitespace
        self.whitespace = self.indents | self.newline_chars
        self.whitespace_str = ''.join(self.whitespace)
        # Unicode whitespace, used for checking the beginning and end of
        # unquoted strings for invalid characters
        self.unicode_whitespace = UNICODE_WHITESPACE
        self.unicode_whitespace_str = ''.join(self.unicode_whitespace)


        # Dicts that map code points to their escaped versions, and vice versa
        if short_escapes is None:
            self._default_short_escapes = True
            short_escapes = BESPON_SHORT_ESCAPES
        else:
            self._default_short_escapes = False
            if '\\' not in short_escapes:
                raise erring.ConfigError('Short backslash escapes must define the escape of the backslash "\\"')
            if not all(isinstance(c, str) and len(c) == 1 and ord(c) < 128 for c in short_escapes):
                raise erring.ConfigError('Short escapes only map single code points in the ASCII range to escapes')
            if not all(isinstance(v, str) and len(v) == 2 and v[0] == '\\' and 0x21 <= ord(v[1]) <= 0x7E for k, v in short_escapes.items()):
                # 0x21 through 0x7E is `!` through `~`, all printable ASCII
                # except for space (0x20), which shouldn't be allowed since
                # it is (optionally) part of newline escapes
                raise erring.ConfigError('Short escapes only map single code points to a backslash followed by a single ASCII character in U+0021 through U+007E')
            if any(v in ('\\x', '\\X', '\\u', '\\U', '\\o', '\\O') for k, v in short_escapes.items()):
                # Prevent collision with hex or Unicode escapes, or hex escape
                # lookalike, or octal escape lookalike
                raise erring.ConfigError('Short backlash escapes cannot use the letters X, U, or O, in either upper or lower case')
        self.short_escapes = short_escapes

        if short_unescapes is None:
            self._default_short_unescapes = True
            short_unescapes = BESPON_SHORT_UNESCAPES
        else:
            self._default_short_unescapes = False
            if '\\\\' not in short_unescapes:
                raise erring.ConfigError('Short backslash unescapes must define the escape of the backslash "\\\\"')
            if not all(isinstance(x, str) and len(x) == 2 and x[0] == '\\' and 0x21 <= ord(x[1]) <= 0x7E for x in short_unescapes):
                raise erring.ConfigError('All short backlash unescapes be a backslash followed by a single ASCII character in U+0021 through U+007E')
            if not all(isinstance(v, str) and len(v) == 1 and ord(v) < 128 for k, v in short_unescapes.items()):
                raise erring.ConfigError('All short backlash unescapes be map to a single code point in the ASCII range')
            if any(pattern in short_unescapes for pattern in ('\\x', '\\X', '\\u', '\\U', '\\o', '\\O')):
                raise erring.ConfigError('Short backlash unescapes cannot use the letters X, U, or O, in either upper or lower case')
        self.short_unescapes = short_unescapes

        self.short_escapes_bytes = {k.encode('ascii'): v.encode('ascii') for k, v in self.short_escapes.items()}
        self.short_unescapes_bytes = {k.encode('ascii'): v.encode('ascii') for k, v in self.short_unescapes.items()}


        # Unescaping regexes
        # Unicode regex.  Depends on whether `\xHH` escapes are allowed and 
        # on whether `\u{HHHHHH}` escapes are in use.
        unescape_re_pattern = r'\\x[0-9a-fA-F]{{2}}|\\u\{{[0-9a-fA-F]{{1,6}}\}}|\\u[0-9a-fA-F]{{4}}|\\U[0-9a-fA-F]{{8}}|\\[{spaces}]*(?:{newlines})|\\.|\\'
        if not x_escapes:
            unescape_re_pattern = '|'.join(x for x in unescape_re_pattern.split('|') if not x.startswith(r'\\x'))
        if not brace_escapes:
            unescape_re_pattern = '|'.join(x for x in unescape_re_pattern.split('|') if not x.startswith(r'\\u\{{'))
        # For typed strings with specified newlines, the default newline `\n`
        # may be replaced with any other valid Unicode newline sequence, even
        # when nonliterals are default.  Thus, escaping must handle any 
        # Unicode newlines, not just the newlines that are allowed as 
        # literals.  The same logic applies to the binary case.
        unescape_re_pattern = unescape_re_pattern.format(spaces=re.escape(self.spaces_str), newlines='|'.join(re.escape(x) for x in sorted(UNICODE_NEWLINES, reverse=True)))
        self.unescape_re = re.compile(unescape_re_pattern, re.DOTALL)
        unescape_bytes_re_pattern = r'\\x[0-9a-fA-F]{2}|\\\x20*(?:\r\n|\r|\n)|\\.|\\'.encode('ascii')
        self.unescape_bytes_re = re.compile(unescape_bytes_re_pattern, re.DOTALL)


        # Set function for escaping Unicode characters, based on whether 
        # `\xHH` escapes are allowed and whether `\u{HHHHHH}` escapes are in 
        # use.  There are no such conditions for the binary equivalent.
        if x_escapes and brace_escapes:
            self._escape_unicode_char = self._escape_unicode_char_xubrace
        elif x_escapes:
            self._escape_unicode_char = self._escape_unicode_char_xuU
        elif brace_escapes:
            self._escape_unicode_char = self._escape_unicode_char_ubrace
        else:
            self._escape_unicode_char = self._escape_unicode_char_uU


        # Dict for escaping code points that may not appear literally.
        # For lookup in conjunction with regex.
        # This is a minimalist form of escaping, given the current literals.
        if self.unpaired_surrogates:
            minimal_escape_dict = {c: self._escape_unicode_char(c) for c in self.nonliterals}
            for c in UNICODE_SURROGATES:
                minimal_escape_dict[c] = self._escape_unicode_char(c)
        else:
            minimal_escape_dict = {c: self._escape_unicode_char(c) for c in self.nonliterals_less_surrogates}
        # Copy over any relevant short escapes
        for k, v in self.short_escapes.items():
            if k in minimal_escape_dict:
                minimal_escape_dict[k] = v
        # Want everything that must be escaped, plus the backslash that makes
        # escaping possible in the first place
        minimal_escape_dict['\\'] = self.short_escapes['\\']
        if not only_ascii:
            self.minimal_escape_dict = minimal_escape_dict
        else:
            # Factory function adds characters to dict as they are requested.
            # All escapes already in `escape_dict` are valid ASCII, since
            # `_escape_unicode_char()` gives hex escapes, and short escapes
            # must use printable ASCII characters
            self.minimal_escape_dict = tooling.keydefaultdict(self._unicode_to_escaped_ascii_factory, minimal_escape_dict)


        # Escaping with no literal line breaks.  Inherits `only_ascii`
        # settings.  Copy over all newline escapes and the tab short escape,
        # if it exists.
        inline_escape_dict = self.minimal_escape_dict.copy()
        for c in UNICODE_NEWLINE_CHARS:
            try:
                inline_escape_dict[c] = self.short_escapes[c]
            except KeyError:
                inline_escape_dict[c] = self._escape_unicode_char(c)
        try:
            inline_escape_dict['\t'] = self.short_escapes['\t']
        except KeyError:
            inline_escape_dict['\t'] = self._escape_unicode_char('\t')
        self.inline_escape_dict = inline_escape_dict

        
        # The binary escape dicts are similar to the Unicode equivalents.
        # Only `\xHH` escapes are used.  There are two variants:  (1) a 
        # minimal version based on printable ASCII plus allowed literals in 
        # the ASCII range, which is suitable for binary strings that should 
        # be treated as strings; and (2) a version in which everything but 
        # non-whitespace, printable ASCII is escaped, which is suitable for 
        # binary data in which exact byte values must be maintained (for 
        # example, `\r\n` vs. `\n`).  In practice, it will typically be 
        # better to use base64 encoding for the second case, but there may 
        # be situations in which using `\xHH` escapes is desirable due to 
        # readability.  The second approach to escaping plays the binary 
        # role of an inline escape, since it allows no literal newlines.
        minimal_escape_bytes_dict = {c.encode('latin1'): '\\x{0:02x}'.format(ord(c)).encode('ascii') for c in self.nonliterals_bytes_latin1}
        maximal_escape_bytes_dict = {chr(n).encode('latin1'): '\\x{0:02x}'.format(n).encode('ascii') for n in range(256) if not 0x21 <= n <= 0x7E or chr(n) in self.nonliterals_bytes_latin1}
        for k, v in self.short_escapes_bytes.items():
            if k in minimal_escape_bytes_dict:
                minimal_escape_bytes_dict[k] = v
            if k in maximal_escape_bytes_dict:
                maximal_escape_bytes_dict[k] = v
        # Need backslash in both cases.  
        minimal_escape_bytes_dict[b'\\'] = self.short_escapes_bytes[b'\\']
        maximal_escape_bytes_dict[b'\\'] = self.short_escapes_bytes[b'\\']
        # Escaping the escaped-string delimiter simplifies things in the 
        # maximal case.  Since any byte may appear, escaping will be required
        # in the general case, which will require the escaped-string 
        # delimiter.  If the delimiter itself is escaped when it appears
        # literally, then there is no need to search the string to find a 
        # delimiter sequence that does not appear.
        maximal_escape_bytes_dict[b'"'] = self.short_escapes_bytes[b'"']
        self.minimal_escape_bytes_dict = minimal_escape_bytes_dict
        self.maximal_escape_bytes_dict = maximal_escape_bytes_dict


        # Dicts for unescaping with current settings.  Used for looking up
        # backlash escapes found by `re.sub()`.  Start with all short escapes;
        # the factory functions add escapes as they are requested.
        self.unescape_dict = tooling.keydefaultdict(self._unicode_escaped_hex_to_char_factory, self.short_unescapes)
        self.unescape_bytes_dict = tooling.keydefaultdict(self._bytes_escaped_hex_to_bytes_factory, self.short_unescapes_bytes)


        # Regex for replacing all non-ASCII newlines
        # No need for special treatment of `\r\n`, because in ASCII range
        if self.newline_chars_non_ascii:
            self.non_ascii_newlines_re = re.compile('[{0}]'.format(self.newline_chars_non_ascii_str))


    def _escape_unicode_char_xubrace(self, c):
        '''
        Escape a Unicode code point using `\\xHH` (8-bit) or
        `\\u{H....H}` notation.
        '''
        n = ord(c)
        if n < 256:
            e = '\\x{0:02x}'.format(n)
        else:
            if 0xD800 <= n <= 0xDFFF and not self.unpaired_surrogates:
                raise erring.UnicodeSurrogateError('\\u{0:04x}'.format(n), self.traceback)
            e = '\\u{{{0:0x}}}'.format(n)
        return e


    def _escape_unicode_char_xuU(self, c):
        '''
        Escape a Unicode code point using `\\xHH` (8-bit), `\\uHHHH` (16-bit),
        or `\\UHHHHHHHH` (24-bit) notation.
        '''
        n = ord(c)
        if n < 256:
            e = '\\x{0:02x}'.format(n)
        elif n < 65536:
            if 0xD800 <= n <= 0xDFFF and not self.unpaired_surrogates:
                raise erring.UnicodeSurrogateError('\\u{0:04x}'.format(n), self.traceback)
            e = '\\u{0:04x}'.format(n)
        else:
            e = '\\U{0:08x}'.format(n)
        return e


    def _escape_unicode_char_ubrace(self, c):
        '''
        Escape a Unicode code point using `\\u{H....H}` notation.
        '''
        n = ord(c)
        if 0xD800 <= n <= 0xDFFF and not self.unpaired_surrogates:
            raise erring.UnicodeSurrogateError('\\u{0:04x}'.format(n), self.traceback)
        return '\\u{{{0:0x}}}'.format(n)


    def _escape_unicode_char_uU(self, c):
        '''
        Escape a Unicode code point using \\uHHHH` (16-bit),
        or `\\UHHHHHHHH` (24-bit) notation.
        '''
        n = ord(c)
        if n < 65536:
            if 0xD800 <= n <= 0xDFFF and not self.unpaired_surrogates:
                raise erring.UnicodeSurrogateError('\\u{0:04x}'.format(n), self.traceback)
            e = '\\u{0:04x}'.format(n)
        else:
            e = '\\U{0:08x}'.format(n)
        return e


    def _unicode_to_escaped_ascii_factory(self, c):
        '''
        Given a code point, return an escaped version for all non-ASCII code
        points.
        '''
        n = ord(c)
        if n >= 128:
            if 0xD800 <= n <= 0xDFFF and not self.unpaired_surrogates:
                raise erring.UnicodeSurrogateError('\\u{0:04x}'.format(n), self.traceback)
            c = self._escape_unicode_char(c)
        return c


    def _unicode_escaped_hex_to_char_factory(self, s):
        '''
        Given a string in `\\xHH`, `\\u{H....H}`, `\\uHHHH`, or `\\UHHHHHHHH`
        form, return the Unicode code point corresponding to the hex value of
        the `H`'s.  Given `\\<spaces><newline>`, return an empty string.
        Otherwise, raise an error for `\\<char>` or `\\`, which is the only
        other form the argument will ever take.

        Arguments to this function are prefiltered by a regex into the allowed
        forms.  Before this function is invoked, all known short
        (2-letter) escape sequences have already been filtered out.  Any
        remaining short escapes `\\<char>` at this point are unrecognized.
        '''
        try:
            n = int(s[2:].strip('{}'), 16)
            if 0xD800 <= n <= 0xDFFF and not self.unpaired_surrogates:
                raise erring.UnicodeSurrogateError(s, self.traceback)
            v = chr(n)
        except ValueError:
            # Check for the pattern `\\<spaces><newline>`.
            # Given regex, no need to worry about multiple newlines.
            if s[-1] in self.newline_chars:
                v = ''
            else:
                raise erring.UnknownEscapeError(s, self.traceback)
        return v


    def _bytes_escaped_hex_to_bytes_factory(self, s):
        '''
        Given a binary string in `\\xHH` form, return the byte corresponding
        to the hex value of the `H`'s.  Given `\\<spaces><newline>`, return an
        empty byte string.  Otherwise, raise an error for `\\<byte>` or `\\`,
        which is the only other form the argument will ever take.

        Arguments to this function are prefiltered by a regex into the allowed
        hex escape forms.  Before this function is invoked, all known short
        (2-letter) escape sequences have already been filtered out.  Any
        remaining short escapes `\\<byte>` at this point are unrecognized.
        '''
        try:
            v = chr(int(s[2:], 16)).encode('latin1')
        except ValueError:
            # Make sure we have the full pattern `\\<spaces><newline>`
            if s[-1] in (b'\r', b'\n'):
                v = b''
            else:
                raise erring.UnknownEscapeError(s.decode('latin1'), self.traceback)
        return v


    def escape(self, s, inline=False):
        '''
        Within a string, replace all code points that are not allowed to 
        appear literally with their escaped counterparts.
        '''
        if inline:
            r = self.nonliterals_or_backslash_newline_tab_re
            d = self.inline_escape_dict
        else:
            r = self.nonliterals_or_backslash_re
            d = self.minimal_escape_dict
        return r.sub(lambda m: d[m.group(0)], s)


    def escape_bytes(self, s, inline=False, maximal=False):
        '''
        Within a binary string, replace all bytes whose corresponding Latin-1
        code points are not allowed to appear literally with their escaped
        counterparts.
        '''
        # Maximal is everything that inline is, and more
        if maximal:
            d = self.maximal_escape_bytes_dict
            r = self.nonliterals_or_non_printable_non_whitespace_bytes_re
        elif inline:
            d = self.maximal_escape_bytes_dict
            r = self.nonliterals_or_backslash_newlines_tab_bytes_re
        else:
            d = self.minimal_escape_bytes_dict
            r = self.nonliterals_or_backslash_bytes_re
        return r.sub(lambda m: d[m.group(0)], s)


    def unescape(self, s):
        '''
        Within a string, replace all backslash escapes with the
        corresponding code points.
        '''
        d = self.unescape_dict
        return self.unescape_re.sub(lambda m: d[m.group(0)], s)


    def unescape_bytes(self, s):
        '''
        Within a binary string, replace all backslash escapes with the
        corresponding bytes.
        '''
        d = self.unescape_bytes_dict
        return self.unescape_bytes_re.sub(lambda m: d[m.group(0)], s)


    def has_nonliterals(self, s):
        '''
        See whether a string contains any code points that are not allowed as
        literals.
        '''
        return bool(self.nonliterals_re.search(s))


    def has_unicode(self, s):
        '''
        See whether a string contains any code points outside the ASCII range.
        '''
        return bool(self.unicode_re.search(s))


    def trace_nonliterals(self, s):
        '''
        Get the location of code points in a string that are not allowed as
        literals.  Return a list of named tuples that contains the line 
        numbers and code points.  Line numbers are given in two forms, one 
        calculated using standard `\\r`, `\\r\\n`, `\\n` newlines, and one 
        using all Unicode newlines.  All returned characters are escaped, so 
        that the output may be used as-is.
        '''
        newline_chars_str = self.newline_chars_str
        trace = []
        # Keep track of how many lines didn't end with `\r`, `\n`, or `\r\n`
        offset = 0
        # Work with a copy of s in which all literals, except for newlines, 
        # are removed
        for n, line in enumerate(self.not_nonliterals_or_newlines_re.sub('', s).splitlines(True)):
            nonlits = line.rstrip(newline_chars_str)
            if nonlits:
                trace.append(NonliteralTrace(self.escape(nonlits), n-offset+1, n+1))
            if not len(line.rstrip('\r\n')) < len(line):
                offset += 1
            if len(trace) > 20:
                trace.append(NonliteralTrace('...', '...', '...'))
                break
        return trace


    def trace_unicode(self, s):
        '''
        Get the location of code points in a string that are not ASCII, and
        return the information necessary for creating a trace.
        '''
        ascii_newline_chars_str = self.ascii_newline_chars_str
        trace = []
        # Keep track of how many lines didn't end with `\r`, `\n`, or `\r\n`
        offset = 0
        # Work with a copy of s in which all literals, except for newlines, 
        # are removed
        for n, line in enumerate(self.ascii_less_newlines_and_nonliterals_re.sub('', s).splitlines(True)):
            non_ascii = line.rstrip(ascii_newline_chars_str)
            if non_ascii:
                trace.append(NonliteralTrace(self.escape(non_ascii), n-offset+1, n+1))
            if not len(line.rstrip('\r\n')) < len(line):
                offset += 1
            if len(trace) > 20:
                trace.append(NonliteralTrace('...', '...', '...'))
                break
        return trace


    def format_trace(self, trace):
        '''
        Format a nonliterals or Unicode trace.  Used with 
        InvalidLiteralCharacterError.
        '''
        m =       ['  Line number  (Unicode)    Chars\n']
        template = '         {0}       {1}    {2}\n'
        for t in trace:
            m.append(template.format(str(t.lineno).rjust(4, ' '), str(t.unicode_lineno).rjust(4, ' '), t.chars))
        return ''.join(m)


    def unicode_to_ascii_newlines(self, s):
        '''
        Replace all non-ASCII newlines with `\n`.
        '''
        if self.newline_chars_non_ascii:
            return self.non_ascii_newlines_re.sub('\n', s)
        else:
            return s
