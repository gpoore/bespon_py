# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


# pylint: disable=C0301, C0330

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import re
from . import re_patterns




# General notes:
#  * Use of "ascii" in a variable name indicates a restriction to code
#    points in 0x00-0x7F, or 0-127 (that is, 7-bit).
#  * Use of "unicode" in a variable name indicates that the full range of
#    Unicode code points in 0x00-0x10FFFF is covered.


# Assemble literal grammar
_RAW_LIT_GRAMMAR = [# Whitespace
                    ('tab', '\t'),
                    ('space', '\x20'),
                    ('indent', '{tab}{space}'),
                    ('newline', '\n'),
                    ('ascii_other_newline', '\n\v\f\r'),
                    ('unicode_other_newline', '{ascii_other_newline}\u0085\u2028\u2029'),
                    ('whitespace', '{indent}{newline}'),
                    # unicode_whitespace = set([cp for cp, data in unicodetools.ucd.proplist.items() if 'White_Space' in data])
                    ('unicode_whitespace', ('\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u00a0\u1680' +
                                            '\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a' +
                                            '\u2028\u2029\u202f\u205f\u3000'))]

_RAW_LIT_SPECIAL = [# Special code points
                    ('comment', '#'),
                    ('assign_key_val', '='),
                    ('open_noninline_list', '*'),
                    ('start_inline_dict', '{'),
                    ('end_inline_dict', '}'),
                    ('start_inline_list', '['),
                    ('end_inline_list', ']'),
                    ('start_tag', '('),
                    ('end_tag', ')'),
                    ('end_tag_suffix', '>'),
                    ('inline_element_separator', ','),
                    ('block_prefix', '|'),
                    ('block_suffix', '/'),
                    ('escaped_string_singlequote_delim', "'"),
                    ('escaped_string_doublequote_delim', '"'),
                    ('literal_string_delim', '`'),
                    ('path_separator', '.'),
                    ('alias_prefix', '$'),
                    ('home_alias', '~'),
                    ('self_alias', '_')]

_RAW_LIT_GRAMMAR.extend(_RAW_LIT_SPECIAL)

LIT_GRAMMAR = {}
for k, v in _RAW_LIT_GRAMMAR:
    if k in ('start_inline_dict', 'end_inline_dict'):
        LIT_GRAMMAR[k] = v
    else:
        LIT_GRAMMAR[k] = v.format(**LIT_GRAMMAR)
# Add a few elements that couldn't conveniently be created with the grammar
# definition format
LIT_GRAMMAR['ascii_other_newline_seq'] = ('\r\n',) + tuple(x for x in LIT_GRAMMAR['ascii_other_newline'])
LIT_GRAMMAR['unicode_other_newline_seq'] = ('\r\n',) + tuple(x for x in LIT_GRAMMAR['unicode_other_newline'])



# Assemble regex grammar
_RAW_RE_GRAMMAR = [('backslash', '\\\\'),
                   ('non_ascii', '[^\\\u0000-\\\u007f]')]

# Whitespace
_RAW_RE_WS = [('space', re.escape(LIT_GRAMMAR['space'])),
              ('indent', '[{0}]'.format(re.escape(LIT_GRAMMAR['indent']))),
              ('newline', re.escape(LIT_GRAMMAR['newline'])),
              ('ascii_other_newline', '{0}|[{1}]'.format(re.escape('\r\n'), re.escape(LIT_GRAMMAR['ascii_other_newline']))),
              ('unicode_other_newline', '{0}|[{1}]'.format(re.escape('\r\n'), re.escape(LIT_GRAMMAR['unicode_other_newline']))),
              ('whitespace', '[{0}]'.format(re.escape(LIT_GRAMMAR['whitespace'])))]
_RAW_RE_GRAMMAR.extend(_RAW_RE_WS)

# Special characters
for k, v_lit in _RAW_LIT_SPECIAL:
    _RAW_RE_GRAMMAR[k] = re.escape(v_lit)

# Types
_RAW_RE_TYPE = [# None type
                ('none_type', 'none'),
                ('none_type_reserved_word', '[nN][oO][nN][eE]'),

                # Boolean
                ('bool_true', 'true'),
                ('bool_false', 'false'),
                ('bool_reserved_word', '[tT][rR][uU][eE]|[fF][aA][lL][sS][eE]'),

                # Basic numeric elements
                ('sign', '[+-]'),
                ('opt_sign_indent', '(?:{sign}{indent}*)?'),
                ('zero', '0'),
                ('nonzero_dec_digit', '[1-9]'),
                ('dec_digit', '[0-9]'),
                ('dec_digits_underscores', '{dec_digit}+(?:_{dec_digit}+)*'),
                ('lower_hex_digit', '[0-9a-f]'),
                ('lower_hex_digits_underscores', '{lower_hex_digit}+(?:_{lower_hex_digit}+)*'),
                ('upper_hex_digit', '[0-9A-F]'),
                ('upper_hex_digits_underscores', '{upper_hex_digit}+(?:_{upper_hex_digit}+)*'),
                ('oct_digit', '[0-7]'),
                ('oct_digits_underscores', '{oct_digit}+(?:_{oct_digit}+)*'),
                ('bin_digit', '[01]'),
                ('bin_digits_underscores', '{bin_digit}+(?:_{bin_digit}+)*'),

                # Number types
                # Integers
                ('dec_integer', '{opt_sign_indent}(?:{zero}|{nonzero_dec_digit}{dec_digit}*(?:_{dec_digit}+)*)'),
                ('hex_integer', '{opt_sign_indent}0x_?(?:{lower_hex_digits_underscores}|{upper_hex_digits_underscores})'),
                ('oct_integer', '{opt_sign_indent}0o_?{oct_digits_underscores}'),
                ('bin_integer', '{opt_sign_indent}0b_?{bin_digits_underscores}'),
                ('integer', '{dec_integer}|{hex_integer}|{oct_integer}|{bin_integer}'),
                # Floats
                ('dec_exponent', '[eE]{sign}?{dec_digits_underscores}'),
                ('decimal_point', '\\.'),
                ('dec_float', '''
                              {opt_sign_indent}(?:{zero}|{nonzero_dec_digit}{dec_digit}*(?:_{dec_digit}+)*)
                                  (?:{decimal_point}{dec_digits_underscores}(?:_?{dec_exponent})?|_?{dec_exponent})
                              '''.replace('\x20', '').replace('\n', '')),
                ('hex_exponent', '[pP]{sign}?{dec_digits_underscores}'),
                ('hex_float', '''
                              {opt_sign_indent}0x_?
                              (?:{lower_hex_digits_underscores}(?:{decimal_point}{lower_hex_digits_underscores}(?:_?{hex_exponent})? | _?{hex_exponent}) |
                                 {upper_hex_digits_underscores}(?:{decimal_point}{upper_hex_digits_underscores}(?:_?{hex_exponent})? | _?{hex_exponent})
                              )
                              '''.replace('\x20', '').replace('\n', '')),
                ('infinity', '{opt_sign_indent}inf'),
                ('not_a_number', '{opt_sign_indent}nan'),
                ('float_reserved_word', '{opt_sign_indent}(?:[iI][nN][fF]|[nN][aA][nN])'),
                ('float', '{dec_float}|{hex_float}|{infinity}|{not_a_number}'),

                # Unquoted strings
                ('ascii_start', re_patterns.ASCII_START),
                ('unicode_start', re_patterns.XID_START_LESS_FILLERS),
                ('ascii_continue', re_patterns.ASCII_CONTINUE),
                ('unicode_continue', re_patterns.XID_CONTINUE_LESS_FILLERS),
                ('unquoted_ascii_key', '_*{ascii_start}{ascii_continue}*'),
                ('unquoted_unicode_key', '_*{unicode_start}{unicode_continue}*'),
                ('unquoted_ascii_string', '{unquoted_ascii_key}(?:{space}{ascii_continue}+)+'),
                ('unquoted_unicode_string', '{unquoted_unicode_key}(?:{space}{unicode_continue}+)+'),
                ('si_mu_prefix', '\u00B5|\u03BC'),
                ('ascii_unquoted_unit', '''
                                        [AC-DF-HJ-NP-WY-Zac-df-hj-km-np-rw-z] |
                                        [Xx][G-Zg-z][A-Za-z]* |
                                        [A-NP-WY-Za-km-wy-z][A-Za-z]+ |
                                        %
                                        '''.replace('\x20', '').replace('\n', '')),
                ('unquoted_ascii_dec_number_unit', '(?:{dec_integer}|{dec_float}){ascii_unquoted_unit}'),
                ('unquoted_unicode_dec_number_unit', '(?:{dec_integer}|{dec_float}){si_mu_prefix}?{ascii_unquoted_unit}'),

                # Key path
                ('ascii_key_path_element', '(?:{unquoted_ascii_key}|{open_noninline_list})'),
                ('unicode_key_path_element', '(?:{unquoted_unicode_key}|{open_noninline_list})'),
                ('ascii_key_path', '{ascii_key_path_element}(?:{path_separator}{ascii_key_path_element})+'),
                ('unicode_key_path', '{unicode_key_path_element}(?:{path_separator}{unicode_key_path_element})+'),

                # Alias path
                ('ascii_alias_path', '{alias_prefix}(?:{home_alias}|{self_alias}|{unquoted_ascii_key})(?:{path_separator}{unquoted_ascii_key})+'),
                ('unicode_alias_path', '{alias_prefix}(?:{home_alias}|{self_alias}|{unquoted_unicode_key})(?:{path_separator}{unquoted_unicode_key})+')]

_RAW_RE_GRAMMAR.extend(_RAW_RE_TYPE)

# Escapes (no string formatting is performed on these, so braces are fine)
_RAW_RE_ESC = [('x_escape', '\\\\x(?:{lower_hex_digit}{{2}}|{upper_hex_digit}{{2}})'),
               ('u_escape', '\\\\u(?:{lower_hex_digit}{{4}}|{upper_hex_digit}{{4}})'),
               ('U_escape', '\\\\U(?:{lower_hex_digit}{{8}}|{upper_hex_digit}{{8}})'),
               ('ubrace_escape', '\\\\u\\{{(?:{lower_hex_digit}{{1,6}}|{upper_hex_digit}{{1,6}}))\\}}'),
               # The general escape patterns can include `\<spaces><newline>`,
               # but don't need to be compiled with re.DOTALL because the
               # newlines are specified explicitly and accounted for before
               # the dot in the patterns.  The last two patterns (arbitrary
               # character after backslash, or none) don't lead to errors,
               # because all such matches are filtered through a dict of
               # valid short escapes.  Invalid escapes are caught at that
               # point; the regex pattern just needs to catch everything that
               # could be a valid escape.
               ('ascii_escape', '{x_escape}|\\\\{space}*(?:{ascii_other_newline})|\\\\.|\\\\'),
               ('unicode_escape', '{x_escape}|{u_escape}|{U_escape}|{ubrace_escape}|\\\\{space}*(?:{unicode_other_newline})|\\\\.|\\\\')]

_RAW_RE_GRAMMAR.extend(_RAW_RE_ESC)

RE_GRAMMAR = {}
for k, v in _RAW_RE_GRAMMAR:
    if k in ('start_inline_dict', 'end_inline_dict'):
        RE_GRAMMAR[k] = v
    else:
        RE_GRAMMAR[k] = v.format(**RE_GRAMMAR)




# Other grammar-related elements

# Default short backslash escapes.
SHORT_BACKSLASH_UNESCAPES = {'\\\\': '\\',
                             "\\'": "'",
                             '\\"': '"',
                             '\\a': '\a',
                             '\\b': '\b',
                             '\\e': '\x1B',
                             '\\f': '\f',
                             '\\n': '\n',
                             '\\r': '\r',
                             '\\t': '\t',
                             '\\v': '\v'}

SHORT_BACKSLASH_ESCAPES = {v: k for k, v in SHORT_BACKSLASH_UNESCAPES.items()}
