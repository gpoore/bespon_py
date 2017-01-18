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
import collections
import re


from .version import __version__
from . import erring
from . import tooling
from . import coding


if sys.version_info.major == 2:
    str = unicode
if sys.maxunicode == 0xFFFF:
    chr = coding.chr_surrogate
    ord = coding.ord_surrogate




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
# http://www.unicode.org/versions/Unicode9.0.0/ch02.pdf
# http://www.unicode.org/versions/Unicode9.0.0/ch23.pdf
UNICODE_CC = set(chr(n) for n in list(range(0x0000, 0x001F+1)) + list(range(0x007F, 0x009F+1)))


# Default allowed literal CC code points
BESPON_CC_LITERALS = set(['\t', '\n'])


# Characters with the Bidi_Control property
# http://www.unicode.org/reports/tr9/tr9-35.html
UNICODE_BIDI_CONTROL = set(['\u061C', '\u200E', '\u200F',
                            '\u202A', '\u202B', '\uU+202C', '\u202D', '\u202E',
                            '\u2066', '\u2067', '\u2068', '\u2069'])


# Regex patterns for identifying all code points, both assigned AND
# unassigned, that have the Unicode Bidirectional Character Types R or AL.
# Two versions are provided, because narrow Python builds require a version
# that
# http://www.unicode.org/reports/tr9/tr9-35.html
_NARROW_BIDI_R_AL_REGEX_PATTERN = r'''
                                   \u0590|\u05be|\u05c0|
                                   \u05c3|\u05c6|[\u05c8-\u05ff]|
                                   \u0608|\u060b|\u060d|
                                   [\u061b-\u064a]|[\u066d-\u066f]|[\u0671-\u06d5]|
                                   [\u06e5-\u06e6]|[\u06ee-\u06ef]|[\u06fa-\u0710]|
                                   [\u0712-\u072f]|[\u074b-\u07a5]|[\u07b1-\u07ea]|
                                   [\u07f4-\u07f5]|[\u07fa-\u0815]|\u081a|
                                   \u0824|\u0828|[\u082e-\u0858]|
                                   [\u085c-\u08d3]|\u200f|\ufb1d|
                                   [\ufb1f-\ufb28]|[\ufb2a-\ufd3d]|[\ufd40-\ufdcf]|
                                   [\ufdf0-\ufdfc]|[\ufdfe-\ufdff]|[\ufe70-\ufefe]|
                                   \ud802[\udc00-\udd1e]|\ud802[\udd20-\ude00]|\ud802\ude04|
                                   \ud802[\ude07-\ude0b]|\ud802[\ude10-\ude37]|\ud802[\ude3b-\ude3e]|
                                   \ud802[\ude40-\udee4]|\ud802[\udee7-\udf38]|\ud802[\udf40-\udfff]|
                                   \ud803[\udc00-\ude5f]|\ud803[\ude7f-\udfff]|\ud83a[\udc00-\udccf]|
                                   \ud83a[\udcd7-\udd43]|\ud83a[\udd4b-\udfff]|\ud83b[\udc00-\udeef]|
                                   \ud83b[\udef2-\udfff]
                                   '''.replace('\x20', '').replace('\t', '').replace('\n', '')

_WIDE_BIDI_R_AL_REGEX_PATTERN   = r'''
                                   [
                                   \u0590\u05be\u05c0
                                   \u05c3\u05c6\u05c8-\u05ff
                                   \u0608\u060b\u060d
                                   \u061b-\u064a\u066d-\u066f\u0671-\u06d5
                                   \u06e5-\u06e6\u06ee-\u06ef\u06fa-\u0710
                                   \u0712-\u072f\u074b-\u07a5\u07b1-\u07ea
                                   \u07f4-\u07f5\u07fa-\u0815\u081a
                                   \u0824\u0828\u082e-\u0858
                                   \u085c-\u08d3\u200f\ufb1d
                                   \ufb1f-\ufb28\ufb2a-\ufd3d\ufd40-\ufdcf
                                   \ufdf0-\ufdfc\ufdfe-\ufdff\ufe70-\ufefe
                                   \U00010800-\U0001091e\U00010920-\U00010a00\U00010a04
                                   \U00010a07-\U00010a0b\U00010a10-\U00010a37\U00010a3b-\U00010a3e
                                   \U00010a40-\U00010ae4\U00010ae7-\U00010b38\U00010b40-\U00010e5f
                                   \U00010e7f-\U00010fff\U0001e800-\U0001e8cf\U0001e8d7-\U0001e943
                                   \U0001e94b-\U0001eeef\U0001eef2-\U0001efff
                                   ]
                                   '''.replace('\x20', '').replace('\t', '').replace('\n', '')

if sys.maxunicode == 0xFFFF:
    UNICODE_BIDI_R_AL_REGEX_PATTERN = _NARROW_BIDI_R_AL_REGEX_PATTERN
else:
    UNICODE_BIDI_R_AL_REGEX_PATTERN = _WIDE_BIDI_R_AL_REGEX_PATTERN


# Unicode byte order marker
UNICODE_BOM = set('\uFEFF')


# Unicode noncharacters
# http://www.unicode.org/versions/Unicode9.0.0/ch23.pdf
UNICODE_NONCHARACTERS = set([chr(n) for n in range(0xFDD0, 0xFDEF+1)] +
                            ['\uFFFE', '\uFFFF',
                             '\U0001FFFE', '\U0001FFFF',
                             '\U0002FFFE', '\U0002FFFF',
                             '\U0003FFFE', '\U0003FFFF',
                             '\U0004FFFE', '\U0004FFFF',
                             '\U0005FFFE', '\U0005FFFF',
                             '\U0006FFFE', '\U0006FFFF',
                             '\U0007FFFE', '\U0007FFFF',
                             '\U0008FFFE', '\U0008FFFF',
                             '\U0009FFFE', '\U0009FFFF',
                             '\U000AFFFE', '\U000AFFFF',
                             '\U000BFFFE', '\U000BFFFF',
                             '\U000CFFFE', '\U000CFFFF',
                             '\U000DFFFE', '\U000DFFFF',
                             '\U000EFFFE', '\U000EFFFF',
                             '\U000FFFFE', '\U000FFFFF',
                             '\U0010FFFE', '\U0010FFFF'])


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




class UnicodeFilter(object):
    '''
    Check strings for literal code points that are not allowed,
    backslash-escape and backslash-unescape strings, etc.
    '''
    def __init__(self, state=None,
                 only_ascii=False, unpaired_surrogates=False,
                 brace_escapes=True, x_escapes=True,
                 literals=None, nonliterals=None,
                 spaces=None, indents=None,
                 short_escapes=None, short_unescapes=None,
                 escaped_string_delim_chars=None):
        # If a state object is provided, enhanced tracebacks are possible
        if state is not None:
            if not all(hasattr(state, attr) for attr in ('source', 'start_lineno', 'start_column', 'end_lineno', 'end_column', 'indent')):
                raise erring.ConfigError('Invalid "state" lacks appropriate attrs')
        self.state = state

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
                        if sys.maxunicode == 0xFFFF:
                            raise erring.ConfigError('Only single code points can be given in "literals" or "nonliterals", and code points above U+FFFF are not supported on narrow Python builds')
                        else:
                            raise erring.ConfigError('Only single code points can be given in "literals" or "nonliterals"')
                    if any(0xD800 <= ord(c) <= 0xDFFF for c in opt):
                        if sys.maxunicode == 0xFFFF:
                            raise erring.ConfigError('Unicode surrogates are not allowed in "literals" or "nonliterals"; literal unpaired surrogates are never allowed, and escaped surrogates are controlled with "unpaired_surrogates"')
                        else:
                            raise erring.ConfigError('Unicode surrogates are not allowed in "literals" or "nonliterals"; literal surrogates are never allowed, and escaped surrogates are controlled with "unpaired_surrogates"')
                    if any(c in UNICODE_BOM or c in UNICODE_NONCHARACTERS for c in opt):
                        raise erring.ConfigError('Unicode BOM and noncharacters are not allowed in "literals" or "nonliterals"; literal BOM and literal noncharacters are never allowed')
                    if opt is literals and any(c in literals for c in '\x1C\x1D\x1E') and len('_\x1C_\x1D_\x1E_'.splitlines()) == 4:
                        # Python's `str.splitlines()` doesn't just split on
                        # Unicode newlines; it also splits on separators.
                        # As a result, these aren't supported as literals.
                        raise erring.ConfigError('The File Separator (U+001C), Group Separator (U+001D), and Record Separator (U+001E) are not supported as literals by this implementation')
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
        # Regexes for finding and counting newlines.  Reverse sort
        # newline sets so that `\r\n` is first when present.
        self.newlines_re = re.compile('|'.join(re.escape(x) for x in sorted(self.newlines, reverse=True)))
        self.rn_newlines_re = re.compile('\r\n|\r|\n')
        self.unicode_newlines_re = re.compile('|'.join(re.escape(x) for x in sorted(UNICODE_NEWLINES, reverse=True)))
        self.latin1_newlines_bytes_re = re.compile('|'.join(re.escape(x) for x in sorted(UNICODE_NEWLINES, reverse=True) if ord(x[0]) < 256 and ord(x[-1]) < 256).encode('latin1'))

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
        if sys.maxunicode = 0xFFFF:
            bom_nonchars_pattern = '|'.join(sorted(UNICODE_NONCHARACTERS, key=ord))
        else:
            bom_nonchars_pattern = ''.join(sorted(UNICODE_NONCHARACTERS, key=ord))
        if sys.maxunicode = 0xFFFF:
            surrogates_pattern = r'[\uD800-\uDBFF](?=[^\uDC00-\uDFFF]|$)|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]'
            self.unpaired_surrogate_re = re.compile(surrogates_pattern)
            if literals is not None:
                self.nonliterals_re = re.compile(r'[^{chars}]|{surr}'.format(chars=lits_re_esc_str, surr=surrogates_pattern))
                self.nonliterals_or_backslash_re = re.compile(r'\\|[^{chars}]|{surr}'.format(chars=lits_re_esc_str, surr=surrogates_pattern))
                self.nonliterals_or_backslash_newline_chars_tab_re = re.compile(r'[\\{nl_chars}\t]|[^{chars}]|{surr}'.format(chars=lits_re_esc_str, nl_chars=newlines_re_esc_str, surr=surrogates_pattern))
            else:
                self.nonliterals_re = re.compile(r'[{chars}]|{bnc}|{surr}'.format(chars=nonlits_re_esc_str, bnc=bom_nonchars_pattern, surr=surrogates_pattern))
                self.nonliterals_or_backslash_re = re.compile(r'[\\{chars}]|{bnc}|{surr}'.format(chars=nonlits_re_esc_str, bnc=bom_nonchars_pattern, surr=surrogates_pattern))
                self.nonliterals_or_backslash_newline_chars_tab_re = re.compile(r'[\\{nl_chars}\t{chars}]|{bnc}|{surr}'.format(chars=nonlits_re_esc_str, nl_chars=newlines_re_esc_str, bnc=bom_nonchars_pattern, surr=surrogates_pattern))
        else:
            if literals is not None:
                self.nonliterals_re = re.compile(r'[^{chars}]|[\uD800-\uDFFF]'.format(chars=lits_re_esc_str))
                self.nonliterals_or_backslash_re = re.compile(r'\\|[^{chars}]|[\uD800-\uDFFF]'.format(chars=lits_re_esc_str))
                self.nonliterals_or_backslash_newline_chars_tab_re = re.compile(r'[\\{nl_chars}\t]|[^{chars}]|[\uD800-\uDFFF]'.format(chars=lits_re_esc_str, nl_chars=newlines_re_esc_str))
            else:
                self.nonliterals_re = re.compile(r'[{chars}{bnc}\uD800-\uDFFF]'.format(chars=nonlits_re_esc_str, bnc=bom_nonchars_pattern))
                self.nonliterals_or_backslash_re = re.compile(r'[\\{chars}{bnc}\uD800-\uDFFF]'.format(chars=nonlits_re_esc_str, bnc=bom_nonchars_pattern))
                self.nonliterals_or_backslash_newline_chars_tab_re = re.compile(r'[\\{nl_chars}\t{chars}{bnc}\uD800-\uDFFF]'.format(chars=nonlits_re_esc_str, nl_chars=newlines_re_esc_str, bnc=bom_nonchars_pattern))
        # Regexes for working with nonliterals in binary.  Since a set of
        # bytes nonliterals already exists, and surrogates are outside the
        # bytes range, this is much simpler.
        nonliterals_bytes_re_esc_str = re.escape(''.join(sorted(self.nonliterals_bytes_str, key=ord)))
        self.nonliterals_or_backslash_bytes_re = re.compile(r'[\\{chars}]'.format(chars=nonliterals_bytes_re_esc_str).encode('latin1'))
        self.nonliterals_or_backslash_newline_chars_tab_bytes_re = re.compile(r'[\\{nl_chars}\t{chars}]'.format(chars=nonliterals_bytes_re_esc_str, nl_chars=re.escape(self.newline_chars_ascii_str)).encode('latin1'))
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
        # Need regex for tracking down any invalid unescapes.  This is
        # assembled from the `unescape_re_pattern` before it is finalized,
        # to maintain uniformity.
        valid_long_unescape_pattern = ''.join(x[2:] for x in unescape_re_pattern.replace(r'|\\.|\\', '').split('|'))
        valid_long_unescape_pattern = valid_long_unescape_pattern.format(spaces=re.escape(self.spaces_str), newlines='|'.join(re.escape(x) for x in sorted(UNICODE_NEWLINES, reverse=True)))
        valid_short_unescape_pattern = r'[{0}]'.format(re.escape(''.join(x[1:] for x in self.short_unescapes)))
        invalid_unescape_re_pattern = r'\\(?!{vl}|{vs}).?'.format(vl=valid_long_unescape_pattern, vs=valid_short_unescape_pattern)
        self.invalid_unescape_re = re.compile(invalid_unescape_re_pattern, re.DOTALL)
        # For typed strings with specified newlines, the default newline `\n`
        # may be replaced with any other valid Unicode newline sequence, even
        # with default nonliterals.  Thus, escaping must handle any
        # Unicode newlines, not just the newlines that are allowed as
        # literals.  The same logic applies to the binary case.
        unescape_re_pattern = unescape_re_pattern.format(spaces=re.escape(self.spaces_str), newlines='|'.join(re.escape(x) for x in sorted(UNICODE_NEWLINES, reverse=True)))
        self.unescape_re = re.compile(unescape_re_pattern, re.DOTALL)

        unescape_bytes_re_pattern = r'\\x[0-9a-fA-F]{2}|\\\x20*(?:\r\n|\r|\n)|\\.|\\'.encode('ascii')
        self.unescape_bytes_re = re.compile(unescape_bytes_re_pattern, re.DOTALL)
        valid_long_unescape_bytes_pattern = r'x[0-9a-fA-F]{2}|\x20*(?:\r\n|\r|\n)'
        valid_short_unescape_bytes_pattern = valid_short_unescape_pattern
        self.invalid_unescape_bytes_re = re.compile(r'\\(?!{vl}|{vs}).?'.format(vl=valid_long_unescape_bytes_pattern, vs=valid_short_unescape_bytes_pattern).encode('ascii'), re.DOTALL)


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
            self.non_ascii_newline_chars_re = re.compile('[{0}]'.format(self.newline_chars_non_ascii_str))

    @property
    def traceback(self):
        '''
        Generate a traceback object from current state.
        '''
        state = self.state
        if state is None:
            return None
        else:
            return erring.Traceback(state.source, state.start_lineno, state.start_column, state.end_lineno, state.end_column)


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
                raise erring.UnicodeSurrogateError(c, '\\u{0:04x}'.format(n))
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
                raise erring.UnicodeSurrogateError(c, '\\u{0:04x}'.format(n))
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
            raise erring.UnicodeSurrogateError(c, '\\u{0:04x}'.format(n))
        return '\\u{{{0:0x}}}'.format(n)


    def _escape_unicode_char_uU(self, c):
        '''
        Escape a Unicode code point using \\uHHHH` (16-bit),
        or `\\UHHHHHHHH` (24-bit) notation.
        '''
        n = ord(c)
        if n < 65536:
            if 0xD800 <= n <= 0xDFFF and not self.unpaired_surrogates:
                raise erring.UnicodeSurrogateError(c, '\\u{0:04x}'.format(n))
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
                raise erring.EscapedUnicodeSurrogateError(s, s)
            v = chr(n)
        except ValueError:
            # Check for the pattern `\\<spaces><newline>`.
            # Given regex, no need to worry about multiple newlines.
            if s[-1] in self.newline_chars:
                v = ''
            else:
                if 0x21 <= ord(s[-1]) <= 0x7E:
                    s_esc = s
                else:
                    s_esc = '\<U+{0:0x}>'.format(ord(s[-1]))
                raise erring.UnknownEscapeError(s, s_esc)
        return v


    def _unescape_byte(self, b):
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
            v = chr(int(b[2:], 16)).encode('latin1')
        except ValueError:
            # Make sure we have the full pattern `\\<spaces><newline>`
            if b[-1] in (b'\r', b'\n'):
                v = b''
            else:
                b_esc = b.decode('latin1')
                if not (0x21 <= ord(b_esc[-1]) <= 0x7E):
                    b_esc = '\<0x{0:02x}>'.format(ord(b_esc[-1]))
                raise erring.UnknownEscapeError(b, b_esc)
        return v


    def escape(self, s, inline=False):
        '''
        Within a string, replace all code points that are not allowed to
        appear literally with their escaped counterparts.
        '''
        d = self._escape_dict
        if inline:
            r = self.nonliterals_or_backslash_newline_chars_tab_re
        else:
            r = self.nonliterals_or_backslash_re
        try:
            v = r.sub(lambda m: d[m.group(0)], s)
        except erring.UnicodeSurrogateError as e:
            c_raw = e.codepoint_raw
            c_esc = e.codepoint_esc
            if sys.maxunicode = 0xFFFF:
                m = self.unpaired_surrogate_re.search(s)
                n = m.start()
            else:
                n = s.find(c_raw)
            lineno = 1
            n_line_start = 0
            for m in self.rn_newlines_re.finditer(s, 0, n):
                lineno += 1
                n_line_start = m.end()
            col = n - n_line_start + 1
            state = self.state
            if state is None:
                tb = erring.Traceback('<string>', lineno, col)
            elif lineno == 1:
                tb = erring.Traceback(state.source, state.start_lineno, state.start_column+col-1)
            else:
                tb = erring.Traceback(state.source, state.start_lineno+lineno-1, col+len(state.indent))
            raise erring.UnicodeSurrogateError(c_raw, c_esc, tb)
        return v


    def escape_bytes(self, b, inline=False, maximal=False):
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
            r = self.nonliterals_or_backslash_newline_chars_tab_bytes_re
        else:
            r = self.nonliterals_or_backslash_bytes_re
        # Unlike `escape()`, there aren't any errors to be caught here.  The
        # `_escape_bytes_dict` covers all possible bytes.
        return r.sub(lambda m: d[m.group(0)], b)


    def unescape(self, s):
        '''
        Within a string, replace all backslash escapes with the
        corresponding code points.
        '''
        d = self._unescape_dict
        try:
            v = self.unescape_re.sub(lambda m: d[m.group(0)], s)
        except (erring.EscapedUnicodeSurrogateError, erring.UnknownEscapeError) as e:
            e_raw = e.escape_raw
            e_esc = e.escape_esc
            for m in self.unescape_re.finditer(s):
                if m.group(0) == e_raw:
                    n = m.start()
                    break
            lineno = 1
            n_line_start = 0
            # Use Unicode newlines for line count, since whatever literal
            # newlines are allowed can be replaced with arbitrary Unicode
            # newlines before unescaping occurs.
            for m in self.unicode_newlines_re.finditer(s, 0, n):
                lineno += 1
                n_line_start = m.end()
            col = n - n_line_start + 1
            state = self.state
            if state is None:
                tb = erring.Traceback('<string>', lineno, col)
            elif lineno == 1:
                tb = erring.Traceback(state.source, state.start_lineno, state.start_column+col-1)
            else:
                tb = erring.Traceback(state.source, state.start_lineno+lineno-1, col+len(state.indent))
            if isinstance(e, erring.EscapedUnicodeSurrogateError):
                raise erring.EscapedUnicodeSurrogateError(e_raw, e_esc, tb)
            else:
                raise erring.UnknownEscapeError(e_raw, e_esc, tb)
        return v


    def unescape_bytes(self, b):
        '''
        Within a binary string, replace all backslash escapes with the
        corresponding bytes.
        '''
        d = self._unescape_bytes_dict
        try:
            v = self.unescape_bytes_re.sub(lambda m: d[m.group(0)], b)
        except erring.UnknownEscapeError as e:
            e_raw = e.escape_raw
            e_esc = e.escape_esc
            for m in self.unescape_bytes_re.finditer(b):
                if m.group(0) == e_raw:
                    n = m.start()
                    break
            lineno = 1
            n_line_start = 0
            # Any literal byte newlines (Latin 1 range) correspond to literal
            # string newlines that appeared in the string representation
            # of the byte literal, so they should be counted in determining
            # line numbers.
            for m in self.latin1_newlines_bytes_re.finditer(b, 0, n):
                lineno += 1
                n_line_start = m.end()
            col = n - n_line_start + 1
            state = self.state
            if state is None:
                tb = erring.Traceback('<string>', lineno, col)
            elif lineno == 1:
                tb = erring.Traceback(state.source, state.start_lineno, state.start_column+col-1)
            else:
                tb = erring.Traceback(state.source, state.start_lineno+lineno-1, col+len(state.indent))
            raise erring.UnknownEscapeError(e_raw, e_esc, tb)
        return v


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
                for m_nl in self.unicode_newlines_re.finditer(s, n, m.start()):
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
            return self.non_ascii_newline_chars_re.sub('\n', s)
        else:
            return s
