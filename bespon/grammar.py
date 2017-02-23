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
from .version import __version__
from . import re_patterns




# Assemble literal grammar
_RAW_LIT_GRAMMAR = [# Whitespace
                    ('tab', '\t'),
                    ('space', '\x20'),
                    ('indent', '{tab}{space}'),
                    ('newline', '\n'),
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
                    ('escaped_string_single_delim', "'"),
                    ('escaped_string_double_delim', '"'),
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




# Assemble regex grammar
_RAW_RE_GRAMMAR = []

# Whitespace
_RAW_RE_WS = [('space', re.escape(LIT_GRAMMAR['space'])),
              ('indent', '[{0}]'.format(re.escape(LIT_GRAMMAR['indent']))),
              ('newline', re.escape(LIT_GRAMMAR['newline'])),
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

RE_GRAMMAR = {}
for k, v in _RAW_RE_GRAMMAR:
    if k in ('start_inline_dict', 'end_inline_dict'):
        RE_GRAMMAR[k] = v
    else:
        RE_GRAMMAR[k] = v.format(**RE_GRAMMAR)
