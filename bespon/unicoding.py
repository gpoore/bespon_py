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




# Unicode code points/sequences that are line terminators.
# Common line endings `\r`, `\n`, and `\r\n`, plus vertical tab, form feed,
# NEL, Line Separator, and Paragraph Separator.
# http://unicode.org/standard/reports/tr13/tr13-5.html
UNICODE_NEWLINES = set(['\v', '\f', '\r', '\n', '\r\n', '\u0085', '\u2028', '\u2029'])
UNICODE_NEWLINE_CHARS = set(''.join(UNICODE_NEWLINES))


# Default allowed literal newlines
BESPON_NEWLINES = set('\n')
BESPON_NEWLINE_CHARS = set(''.join(BESPON_NEWLINES))


# Code points with Unicode General_Category Cc (Other, control)
# http://www.unicode.org/versions/Unicode9.0.0/ch23.pdf
# Ord ranges 0-31, 127-159
UNICODE_CC = set(chr(n) for n in list(range(0x0000, 0x001F+1)) + list(range(0x007F, 0x009F+1)))


# Default allowed literal CC code points
BESPON_CC_LITERALS = set(['\t', '\n'])


# Bidi override characters can be a security concern in general, and are not
# appropriate in a human-friendly, text-based format.
# Unicode Technical Report #36, UNICODE SECURITY CONSIDERATIONS
# http://unicode.org/reports/tr36/
UNICODE_BIDI_OVERRIDES = set(['\u202D', '\u202E'])


# Default code points not allowed as literals.  This does not account
# for surrogates.  Paired surrogates can appear in valid strings
# under narrow Python builds, so surrogates cannot be prohibited in 
# general except under wide builds.
BESPON_NONLITERALS_LESS_SURROGATES = (UNICODE_CC - BESPON_CC_LITERALS) | (UNICODE_NEWLINE_CHARS - BESPON_NEWLINE_CHARS) | UNICODE_BIDI_OVERRIDES


# Code points with Unicode General_Category Zs (Separator, space)
# http://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt
UNICODE_ZS = set(['\x20',   '\xA0',   '\u1680', '\u2000', '\u2001', '\u2002',
                  '\u2003', '\u2004', '\u2005', '\u2006', '\u2007', '\u2008',
                  '\u2009', '\u200a', '\u202f', '\u205f', '\u3000'])


# Unicode White_Space, equivalent to Unicode regex `\s`.  It's safer to use 
# a defined set rather than relying on Python's `re` package.  With `re`,
# `\s` also matches the separator control characters.  Also, U+180E 
# (Mongolian Vowel Separator) was temporarily whitespace in Unicode 4.0 
# up until Unicode 6.3, which affects Python 2.7's `re`.  Note that the 
# `regex` package does the right thing using the most recent Unicode version.
# http://www.unicode.org/Public/UCD/latest/ucd/PropList.txt 
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
# in some fonts.  These don't get any special handling by default, but it 
# could be convenient to treat them specially in some contexts.  Currently, 
# this is just the Hangul fillers.  They are valid in identifier names in 
# some programming languages.
UNICODE_WHITESPACE_VISUALLY_CONFUSABLE = set(['\u115F', '\u1160', '\u3164', '\uFFA0'])


# Structure for reporting the literal appearance of code points that are not
# allowed as literals.  Line numbers are reported in two ways.  `lineno` 
# uses `\r`, `\n`, and `\r\n`, while `unicode_lineno` uses all of
# UNICODE_NEWLINES.
NonliteralTrace = collections.namedtuple('NonliteralTrace', ['chars', 'lineno', 'unicode_lineno'])


# Structure for creating tracebacks.  Such an object will typically be passed
# in from the outside, but otherwise a default object is needed.
Traceback = collections.namedtuple('Traceback', ['source', 'start_lineno', 'end_lineno'])




class UnicodeFilter(object):
    '''
    Check strings for literal code points that are not allowed,
    backslash-escape and backslash-unescape strings, etc.
    '''
    def __init__(self, traceback=None,
                 only_ascii=False, unpaired_surrogates=False,
                 brace_escapes=True, x_escapes=True, 
                 literals=None, nonliterals=None,
                 spaces=None, indents=None,
                 short_escapes=None, short_unescapes=None,
                 escaped_string_delim_chars=None):
        # If a traceback object is provided, enhanced tracebacks are possible
        if traceback is not None:
            if not all(hasattr(traceback, attr) for attr in ('source', 'start_lineno', 'end_lineno')):
                raise erring.ConfigError('Invalid traceback object lacks appropriate attrs')
            self.traceback = traceback
        else:
            self.traceback = Traceback('<unknown>', '?', '?')

        for opt in (only_ascii, unpaired_surrogates, brace_escapes, x_escapes):
            if opt not in (True, False):
                raise erring.ConfigError('"only_ascii", "unpaired_surrogates", "brace_escapes", and "x_escapes" must be boolean')
        self.only_ascii = only_ascii
        if only_ascii:
            if literals is not None or nonliterals is not None:
                raise erring.ConfigError('Options "only_ascii", "literals", and "nonliterals" are mutually exclusive')
        self.unpaired_surrogates = unpaired_surrogates
        self.brace_escapes = brace_escapes
        self.x_escapes = x_escapes


        # Allowed literal code points may be specified either by `literals`, 
        # which must contain all code points that may appear literally, or by 
        # `nonliterals`, which must contain all code points that cannot
        # appear literally.  This is a separate issue from unpaired 
        # surrogates, which are never allowed to appear literally but may be 
        # enabled in escaped form by the option `unpaired_surrogates`.
        # Surrogates are accounted for separately in assembling regexes, to 
        # accommodate narrow Python builds.
        if literals is not None and nonliterals is not None:
            raise erring.ConfigError('Options "literals" and "nonliterals" are mutually exclusive') 
        elif literals is None and nonliterals is None:
            self._default_codepoints = True
            if only_ascii:
                self.literals = set(chr(n) for n in range(0x20, 0x7E+1)) + BESPON_CC_LITERALS
                self.nonliterals_less_surrogates = None
            else:
                self.literals = None
                self.nonliterals_less_surrogates = BESPON_NONLITERALS_LESS_SURROGATES
            self.newlines = BESPON_NEWLINES    
        else:
            for opt in (literals, nonliterals):
                if opt is not None:
                    if not isinstance(opt, str) and not all(isinstance(x, str) for x in opt):
                        raise erring.ConfigError('"literals" and "nonliterals" must be None, or a Unicode string, or a sequence of Unicode strings')
                    if len(opt) == 0 or any(len(x) != 1 for x in opt):
                        if NARROW_BUILD:
                            raise erring.ConfigError('Only single code points can be given in "literals" and "nonliterals", and code points above U+FFFF are not supported on narrow Python builds')
                        else:
                            raise erring.ConfigError('Only single code points can be given in "literals" and "nonliterals"')
                    if any(0xD800 <= ord(c) <= 0xDFFF for c in opt):
                        if NARROW_BUILD:
                            raise erring.ConfigError('Unicode surrogates are not allowed in "literals" and "nonliterals"; literal unpaired surrogates are never allowed, and escaped surrogates are controlled with "unpaired_surrogates"')
                        else:
                            raise erring.ConfigError('Unicode surrogates are not allowed in "literals" and "nonliterals"; literal surrogates are never allowed, and escaped surrogates are controlled with "unpaired_surrogates"')
                    if opt is literals and any(c in literals for c in '\x1C\x1D\x1E') and len('_\x1C_\x1D_\x1E_'.splitlines()) == 4:
                        # Python's `str.splitlines()` doesn't just split on 
                        # Unicode newlines; it also splits on separators.  
                        # As a result, these aren't supported as literals.
                        raise erring.ConfigError('The File Separator (U+001C), Group Separator (U+001D), and Record Separator (U+001E) are not allowed as literals by this implementation')  
            self._default_codepoints = False
            if literals is not None:
                self.literals = set(literals)
                self.nonliterals_less_surrogates = None
            else:
                self.literals = None
                self.nonliterals_less_surrogates = set(nonliterals)
            newlines = set()
            if literals is not None:
                for nl in UNICODE_NEWLINES:
                    # Need to account for `\r\n`, so `nl[-1]`
                    if nl[0] in literals and nl[-1] in literals:
                        newlines.update(nl)
            else:
                for nl in UNICODE_NEWLINES:
                    # Need to account for `\r\n`, so `nl[-1]` 
                    if nl[0] not in nonliterals and nl[-1] not in nonliterals:
                        newlines.update(nl)
            if not newlines:
                raise erring.ConfigError('At least one literal newline code point must be allowed')
            self.newlines = newlines

        # Order for creating newlines variables is important; need to avoid
        # duplicates due to `\r\n` in the event of custom newlines
        self.newline_chars = set(''.join(self.newlines))
        self.newline_chars_str = ''.join(sorted(self.newline_chars, key=ord))
        self.newline_chars_ascii = set(c for c in self.newline_chars if ord(c) < 128)
        self.newline_chars_ascii_str = ''.join(sorted(self.newline_chars_ascii, key=ord))
        self.newline_chars_non_ascii = set(c for c in self.newline_chars if ord(c) >= 128)
        self.newline_chars_non_ascii_str = ''.join(sorted(self.newline_chars_non_ascii, key=ord))
        # Regex for finding all Unicode newlines.
        # Reverse sort so that `\r\n` is first.
        self.unicode_newlines_re = re.compile('|'.join(re.escape(x) for x in sorted(UNICODE_NEWLINES, reverse=True)))
        # Bytes are always dealt with via a nonliterals set
        if self.literals is not None:
            self.nonliterals_bytes_str = set(chr(n) for n in range(256) if n >= 128 or chr(n) not in self.literals)
        else:
            self.nonliterals_bytes_str = set(chr(n) for n in range(256) if n >= 128 or chr(n) in self.nonliterals_less_surrogates)


        # Quoting character(s) for escaped strings
        if escaped_string_delim_chars is None:
            self.escaped_string_delim_chars = set('"')
        else:
            e = escaped_string_delim_chars
            if not isinstance(e, str) and not all(isinstance(x, str) and len(x) <= 1 for x in e):
                raise erring.ConfigError('"escaped_string_delim_chars" must be a Unicode string or a sequence of Unicode code points')
            if len(e) == 0:
                self.escaped_string_delim_chars = set([''])
            else:
                self.escaped_string_delim_chars = set(escaped_string_delim_chars)
                if self.literals is not None:
                    if self.escaped_string_delim_chars - self.literals:
                        raise erring.ConfigError('"escaped_string_delim_chars" must overlap with "literals", or with literals specified via "only_ascii"')
                else:
                    if self.escaped_string_delim_chars & self.nonliterals_less_surrogates:
                        raise erring.ConfigError('"escaped_string_delim_chars" cannot overlap with "nonliterals" (or default nonliterals, if "nonliterals" was not explicitly specified)')
        self.escaped_string_delim_chars_str = ''.join(sorted(self.escaped_string_delim_chars, key=ord))
        

        # Regexes for working with nonliterals.  Regardless of whether 
        # literals or nonliterals are specified, regexes are designed to 
        # find code points that aren't allowed in various contexts.  Either
        # `literals` or `nonliterals_less_surrogates` is guaranteed to 
        # contain one or more code points, so the regexes won't fail due to 
        # `{chars}` being replaced with the empty string. 
        if self.literals is not None: 
            lits_re_esc_str = re.escape(''.join(sorted(self.literals, key=ord)))
        else:
            nonlits_re_esc_str = re.escape(''.join(sorted(self.nonliterals_less_surrogates, key=ord)))
        newlines_re_esc_str = re.escape(self.newline_chars_str)
        if self.unpaired_surrogates:
            if self.literals is not None:
                # Regex for finding nonliterals
                self.nonliterals_re = re.compile(r'[^{chars}]'.format(chars=lits_re_esc_str))
                # Regexes for escaping nonliterals
                self.nonliterals_or_backslash_re = re.compile(r'\\|[^{chars}]'.format(chars=lits_re_esc_str))
                self.nonliterals_or_backslash_newlines_tab_re = re.compile(r'[\\{newlines}\t]|[^{chars}]'.format(chars=lits_re_esc_str, newlines=newlines_re_esc_str))
            else:
                self.nonliterals_re = re.compile(r'[{chars}]'.format(chars=nonlits_re_esc_str))
                self.nonliterals_or_backslash_re = re.compile(r'[\\{chars}]'.format(chars=nonlits_re_esc_str))
                self.nonliterals_or_backslash_newlines_tab_re = re.compile(r'[\\{newlines}\t{chars}]'.format(chars=nonlits_re_esc_str, newlines=newlines_re_esc_str))
        else:
            if NARROW_BUILD:
                surrogates_pattern = r'[\uD800-\uDBFF](?=[^\uDC00-\uDFFF]|$)|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]'
                if literals is not None:
                    self.nonliterals_re = re.compile(r'[^{chars}]|{surr}'.format(chars=lits_re_esc_str, surr=surrogates_pattern))
                    self.nonliterals_or_backslash_re = re.compile(r'\\|[^{chars}]|{surr}'.format(chars=lits_re_esc_str, surr=surrogates_pattern))
                    self.nonliterals_or_backslash_newlines_tab_re = re.compile(r'[\\{newlines}\t]|[^{chars}]|{surr}'.format(chars=lits_re_esc_str, newlines=newlines_re_esc_str, surr=surrogates_pattern))
                else:
                    self.nonliterals_re = re.compile(r'[{chars}]|{surr}'.format(chars=nonlits_re_esc_str, surr=surrogates_pattern))
                    self.nonliterals_or_backslash_re = re.compile(r'[\\{chars}]|{surr}'.format(chars=nonlits_re_esc_str, surr=surrogates_pattern))
                    self.nonliterals_or_backslash_newlines_tab_re = re.compile(r'[\\{newlines}\t{chars}]|{surr}'.format(chars=nonlits_re_esc_str, newlines=newlines_re_esc_str, surr=surrogates_pattern))
            else:
                if literals is not None:
                    self.nonliterals_re = re.compile(r'[^{chars}]|[\uD800-\uDFFF]'.format(chars=lits_re_esc_str))
                    self.nonliterals_or_backslash_re = re.compile(r'\\|[^{chars}]|[\uD800-\uDFFF]'.format(chars=lits_re_esc_str))
                    self.nonliterals_or_backslash_newlines_tab_re = re.compile(r'[\\{newlines}\t]|[^{chars}]|[\uD800-\uDFFF]'.format(chars=lits_re_esc_str, newlines=newlines_re_esc_str))
                else:
                    self.nonliterals_re = re.compile(r'[{chars}\uD800-\uDFFF]'.format(chars=nonlits_re_esc_str))
                    self.nonliterals_or_backslash_re = re.compile(r'[\\{chars}\uD800-\uDFFF]'.format(chars=nonlits_re_esc_str))
                    self.nonliterals_or_backslash_newlines_tab_re = re.compile(r'[\\{newlines}\t{chars}\uD800-\uDFFF]'.format(chars=nonlits_re_esc_str, newlines=newlines_re_esc_str))
        # Regexes for working with nonliterals in binary.  Since a set of
        # bytes nonliterals already exists, and surrogates are outside the 
        # bytes range, this is much simpler.
        nonliterals_bytes_re_esc_str = re.escape(''.join(sorted(self.nonliterals_bytes_str, key=ord)))
        self.nonliterals_or_backslash_bytes_re = re.compile(r'[\\{chars}]'.format(chars=nonliterals_bytes_re_esc_str).encode('latin1'))
        self.nonliterals_or_backslash_newlines_tab_bytes_re = re.compile(r'[\\{newlines}\t{chars}]'.format(chars=nonliterals_bytes_re_esc_str, newlines=re.escape(self.newline_chars_ascii_str)).encode('latin1'))
        nonliterals_or_non_printable_non_whitespace_bytes_re_esc_str = re.escape(''.join(chr(n) for n in range(256) if not 0x21 <= n <= 0x7E or chr(n) in self.nonliterals_bytes_str))
        # Regex for nonliterals or non-printable chars is designed to work
        # even if `escaped_string_delim_chars` is the empty string.
        esdc_re_esc = re.escape(''.join(self.escaped_string_delim_chars))
        self.nonliterals_or_non_printable_non_whitespace_backslash_delim_bytes_re = re.compile(r'[\\{chars}{esdc}]'.format(chars=nonliterals_or_non_printable_non_whitespace_bytes_re_esc_str, esdc=esdc_re_esc).encode('latin1'))


        # Regex for working with purely ASCII text (finding non-ASCII)
        self.non_ascii_re = re.compile(r'[^\u0000-\u007f]')


        # Spaces, indentation, and whitespace
        if spaces is None and indents is None:
            self.spaces = BESPON_SPACES
            self.indents = BESPON_INDENTS
        else:
            self._default_codepoints = False
            for opt in (spaces, indents):
                if opt is not None:
                    if not isinstance(opt, str) and not all(isinstance(x, str) and len(x) == 1 for x in opt):
                        raise erring.ConfigError('"spaces" and "indents" must be Unicode strings or sequences of single Unicode code points')
                    if len(opt) == 0:
                        raise erring.ConfigError('"spaces" and "indents" cannot be empty Unicode strings or sequences')
            if spaces is None:
                self.spaces = BESPON_SPACES
            else:
                self.spaces = set(spaces)
            if self.spaces - UNICODE_ZS:
                raise erring.ConfigError('"spaces" must only contain code points with Unicode General_Category Zs')
            if indents is None:
                self.indents = BESPON_INDENTS
            else:
                self.indents = set(indents)
            if self.indents - UNICODE_ZS - set('\t'):
                raise erring.ConfigError('"indents" must only contain code points with Unicode General_Category Zs, or the horizontal tab (\t)')
        if not self._default_codepoints:
            if self.literals is not None:
                if (self.spaces - self.literals) or (self.indents - self.literals):
                    raise erring.ConfigError('Space and indentation characters cannot be excluded from literals')
            else:
                if (self.spaces & self.nonliterals_less_surrogates) or (self.indents & self.nonliterals_less_surrogates):
                    raise erring.ConfigError('Space and indentation characters cannot be treated as nonliterals')
            if self.spaces - self.indents:
                raise erring.ConfigError('All space characters must also be treated as indentation characters')
        self.spaces_str = ''.join(sorted(self.spaces, key=ord))
        self.indents_str = ''.join(sorted(self.indents, key=ord))
        # Overall whitespace
        self.whitespace = self.indents | self.newline_chars
        self.whitespace_str = ''.join(sorted(self.whitespace, key=ord))
        # Unicode whitespace, used for checking the beginning and end of
        # unquoted strings for invalid characters, etc.
        self.unicode_whitespace = UNICODE_WHITESPACE
        self.unicode_whitespace_str = ''.join(sorted(self.unicode_whitespace, key=ord))


        # Dicts that map code points to their escaped versions, and vice versa
        if short_escapes is None:
            self._default_short_escapes = True
            self.short_escapes = BESPON_SHORT_ESCAPES
        else:
            self._default_short_escapes = False
            if '\\' not in short_escapes:
                raise erring.ConfigError('Short backslash escapes must define the escape of the backslash "\\"')
            if not all(isinstance(x, str) and len(x) == 1 and ord(x) < 128 for x in short_escapes):
                raise erring.ConfigError('Short escapes must only map single code points in the ASCII range to escapes')
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
            self.short_unescapes = BESPON_SHORT_UNESCAPES
        else:
            self._default_short_unescapes = False
            if '\\\\' not in short_unescapes:
                raise erring.ConfigError('Short backslash unescapes must define the escape of the backslash "\\\\"')
            if not all(isinstance(x, str) and len(x) == 2 and x[0] == '\\' and 0x21 <= ord(x[1]) <= 0x7E for x in short_unescapes):
                raise erring.ConfigError('All short backlash unescapes must be a backslash followed by a single ASCII character in U+0021 through U+007E')
            if not all(isinstance(v, str) and len(v) == 1 and ord(v) < 128 for k, v in short_unescapes.items()):
                raise erring.ConfigError('All short backlash unescapes must map to a single code point in the ASCII range')
            if any(pattern in short_unescapes for pattern in ('\\x', '\\X', '\\u', '\\U', '\\o', '\\O')):
                raise erring.ConfigError('Short backlash unescapes cannot use the letters X, U, or O, in either upper or lower case')
            self.short_unescapes = short_unescapes

        # Use ASCII encoding as an additional check for valid code points
        self.short_escapes_bytes = {k.encode('ascii'): v.encode('ascii') for k, v in self.short_escapes.items()}
        self.short_unescapes_bytes = {k.encode('ascii'): v.encode('ascii') for k, v in self.short_unescapes.items()}


        # Unescaping regexes
        # Unicode regex.  Depends on whether `\xHH` escapes are allowed and 
        # on whether `\u{HHHHHH}` escapes are in use.
        unescape_re_pattern = r'\\x[0-9a-fA-F]{{2}}|\\u\\{{[0-9a-fA-F]{{1,6}}\\}}|\\u[0-9a-fA-F]{{4}}|\\U[0-9a-fA-F]{{8}}|\\[{spaces}]*(?:{newlines})|\\.|\\'
        if not x_escapes:
            unescape_re_pattern = '|'.join(x for x in unescape_re_pattern.split('|') if not x.startswith(r'\\x'))
        if not brace_escapes:
            unescape_re_pattern = '|'.join(x for x in unescape_re_pattern.split('|') if not x.startswith(r'\\u\\{{'))
        # For typed strings with specified newlines, the default newline `\n`
        # may be replaced with any other valid Unicode newline sequence, even
        # with default nonliterals.  Thus, escaping must handle any 
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
        self._escape_dict = tooling.keydefaultdict(self._escape_unicode_char)
        # Copy over any relevant short escapes
        self._escape_dict.update(self.short_escapes)

        
        # The binary escape dicts are similar to the Unicode equivalents.
        # Only `\xHH` escapes are used.
        self._escape_bytes_dict = {chr(n).encode('latin1'): '\\x{0:02x}'.format(n).encode('ascii') for n in range(256)}
        self._escape_bytes_dict.update(self.short_escapes_bytes)


        # Dicts for unescaping with current settings.  Used for looking up
        # backlash escapes found by `re.sub()`.  Start with all short escapes;
        # the factory functions add escapes as they are requested.
        self._unescape_dict = tooling.keydefaultdict(self._unescape_unicode_char, self.short_unescapes)
        self._unescape_bytes_dict = tooling.keydefaultdict(self._unescape_byte, self.short_unescapes_bytes)


        # Regex for replacing all non-ASCII newlines in text that has already
        # been filtered so that it only contains allowed literal newlines.  
        # Only created if non-ASCII newlines are actually allowed as literals.
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


    def _unescape_unicode_char(self, s):
        '''
        Given a string in `\\xHH`, `\\u{H....H}`, `\\uHHHH`, or `\\UHHHHHHHH`
        form, return the Unicode code point corresponding to the hex value of
        the `H`'s.  Given `\\<spaces><newline>`, return an empty string.
        Otherwise, raise an error for `\\<char>` or `\\`, which is the only
        other form the argument will ever take.

        Arguments to this function are prefiltered by a regex into the 
        allowed forms.  Before this function is invoked, all known short
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


    def _unescape_byte(self, s):
        '''
        Given a binary string in `\\xHH` form, return the byte corresponding
        to the hex value of the `H`'s.  Given `\\<spaces><newline>`, return 
        an empty byte string.  Otherwise, raise an error for `\\<byte>` or 
        `\\`, which is the only other form the argument will ever take.

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
        d = self._escape_dict
        if inline:
            r = self.nonliterals_or_backslash_newlines_tab_re
        else:
            r = self.nonliterals_or_backslash_re
        return r.sub(lambda m: d[m.group(0)], s)


    def escape_bytes(self, s, inline=False, maximal=False):
        '''
        Within a binary string, replace all bytes whose corresponding Latin-1
        code points are not allowed to appear literally with their escaped
        counterparts.
        '''
        # Maximal is everything that inline is, and more
        d = self._escape_bytes_dict
        if maximal:
            r = self.nonliterals_or_non_printable_non_whitespace_backslash_delim_bytes_re
        elif inline:
            r = self.nonliterals_or_backslash_newlines_tab_bytes_re
        else:
            r = self.nonliterals_or_backslash_bytes_re
        return r.sub(lambda m: d[m.group(0)], s)


    def unescape(self, s):
        '''
        Within a string, replace all backslash escapes with the
        corresponding code points.
        '''
        d = self._unescape_dict
        return self.unescape_re.sub(lambda m: d[m.group(0)], s)


    def unescape_bytes(self, s):
        '''
        Within a binary string, replace all backslash escapes with the
        corresponding bytes.
        '''
        d = self._unescape_bytes_dict
        return self.unescape_bytes_re.sub(lambda m: d[m.group(0)], s)


    def has_nonliterals(self, s):
        '''
        See whether a string contains any code points that are not allowed as
        literals.
        '''
        return bool(self.nonliterals_re.search(s))


    def has_non_ascii(self, s):
        '''
        See whether a string contains any code points outside the ASCII range.
        '''
        return bool(self.non_ascii_re.search(s))


    def trace_nonliterals(self, s):
        '''
        Get the location of code points in a string that are not allowed as
        literals.  Return a list of named tuples that contains the line 
        numbers and code points.  Line numbers are given in two forms, one 
        calculated using standard `\\r`, `\\r\\n`, `\\n` newlines, and one 
        using all Unicode newlines.  All returned characters are escaped, so 
        that the output may be used as-is.
        '''
        trace = []
        n = 0
        ascii_lines = 1
        unicode_lines = 1
        while len(trace) < 20 and n < len(s):
            m = self.nonliterals_re.search(s, pos=n)
            if m:
                for m_nl in self.unicode_newlines_re.finditer(s, pos=n, endpos=m.start()):
                    nl = m_nl.group(0)
                    unicode_lines += 1
                    if nl.lstrip('\r\n') == '':
                         ascii_lines += 1
                c = m.group(0)
                trace.append(NonliteralTrace(self.escape(c), ascii_lines, unicode_lines))
                if c in UNICODE_NEWLINE_CHARS:
                    if c == '\r' and s[m.start()+1:m.start()+2] == '\n':
                        pass
                    elif c.lstrip('\r\n') == '':
                        ascii_lines += 1
                        unicode_lines += 1
                    else:
                        unicode_lines += 1    
                n = m.start() + 1
            else:
                break
        if len(trace) == 20 and n < len(s):
            trace.append(NonliteralTrace('...', '...', '...'))
        return trace


    def format_trace(self, trace):
        '''
        Format a nonliterals trace.  Typically used with 
        InvalidLiteralCharacterError.
        '''
        m =       ['  Line number  (Unicode)    Chars\n']
        template = '         {0}       {1}    {2}\n'
        for t in trace:
            m.append(template.format(str(t.lineno).rjust(4, ' '), str(t.unicode_lineno).rjust(4, ' '), t.chars))
        return ''.join(m)


    def non_ascii_to_ascii_newlines(self, s):
        '''
        Replace all non-ASCII newlines with `\n`.
        '''
        if self.newline_chars_non_ascii:
            return self.non_ascii_newlines_re.sub('\n', s)
        else:
            return s
