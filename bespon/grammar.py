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


from .version import __version__
from . import re_patterns
import sys
import re


# Assemble regex for validating string or stream after decoding
# >>> unicode_cc = [cp for cp, data in unicodetools.ucd.unicodedata.items() if data['General_Category'] == 'Cc']
# >>> invalid_unicode_cc_set = set(unicode_cc) - set([ord('\t'), ord('\n')])
_invalid_unicode_cc = '[\\\x00-\\\x08\\\x0b-\\\x1f\\\x7f-\\\x9f]'
_invalid_non_cc_newlines = '\\\u2028|\\\u2029'
# >>> bidi_control = [cp for cp, data in unicodetools.ucd.proplist.items() if 'Bidi_Control' in data]
_invalid_bidi_control = '[\\\u061c\\\u200e-\\\u200f\\\u202a-\\\u202e\\\u2066-\\\u2069]'
# >>> unicode_surrogates = [cp for cp, data in unicodetools.ucd.blocks.items() if 'Surrogate' in data['Block']]
_invalid_surrogates = '[\\\ud800-\\\udfff]'
_invalid_bom = '\\\ufeff'
# >>> noncharacters = [cp for cp, data in unicodetools.ucd.proplist.items() if 'Noncharacter_Code_Point' in data]
if sys.maxunicode == 0xFFFF:
    _invalid_noncharacters = '''
                             [\\\ufdd0-\\\ufdef\\\ufffe-\\\uffff]|
                              \\\ud83f[\\\udffe-\\\udfff]|\\\ud87f[\\\udffe-\\\udfff]|
                              \\\ud8bf[\\\udffe-\\\udfff]|\\\ud8ff[\\\udffe-\\\udfff]|
                              \\\ud93f[\\\udffe-\\\udfff]|\\\ud97f[\\\udffe-\\\udfff]|
                              \\\ud9bf[\\\udffe-\\\udfff]|\\\ud9ff[\\\udffe-\\\udfff]|
                              \\\uda3f[\\\udffe-\\\udfff]|\\\uda7f[\\\udffe-\\\udfff]|
                              \\\udabf[\\\udffe-\\\udfff]|\\\udaff[\\\udffe-\\\udfff]|
                              \\\udb3f[\\\udffe-\\\udfff]|\\\udb7f[\\\udffe-\\\udfff]|
                              \\\udbbf[\\\udffe-\\\udfff]|\\\udbff[\\\udffe-\\\udfff]
                             '''.replace('\x20', '').replace('\n', '')
else:
    _invalid_noncharacters = '''
                             [\\\ufdd0-\\\ufdef\\\ufffe-\\\uffff\\\U0001fffe-\\\U0001ffff
                              \\\U0002fffe-\\\U0002ffff\\\U0003fffe-\\\U0003ffff\\\U0004fffe-\\\U0004ffff
                              \\\U0005fffe-\\\U0005ffff\\\U0006fffe-\\\U0006ffff\\\U0007fffe-\\\U0007ffff
                              \\\U0008fffe-\\\U0008ffff\\\U0009fffe-\\\U0009ffff\\\U000afffe-\\\U000affff
                              \\\U000bfffe-\\\U000bffff\\\U000cfffe-\\\U000cffff\\\U000dfffe-\\\U000dffff
                              \\\U000efffe-\\\U000effff\\\U000ffffe-\\\U000fffff\\\U0010fffe-\\\U0010ffff]
                             '''.replace('\x20', '').replace('\n', '')

invalid_codepoint_pattern = '|'.join(_invalid_unicode_cc, _invalid_non_cc_newlines,
                                     _invalid_bidi_control, _invalid_surrogates,
                                     _invalid_bom, _invalid_noncharacters)

invalid_codepoint_re = re.compile(invalid_codepoint_pattern)


invalid_only_ascii_codepoint_pattern = '[^\\\t\\\n\\\u0020-\\\u007e]'




# Assemble literal grammar
_RAW_LIT_GRAMMAR = [# Whitespace
                    ('tab', '\t'),
                    ('space', '\x20'),
                    ('indent', '{tab}{space}'),
                    ('newline', '\n'),
                    ('whitespace', '{indent}{newline}'),
                    ('unicode_whitespace', ('\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u00a0' + '\u1680' +
                                            '\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a' +
                                            '\u2028\u2029\u202f\u205f\u3000')),
                    # Special code points
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
                    ('inline_separator', ','),
                    ('block_prefix', '|'),
                    ('block_suffix', '/')
                    ('escaped_string', '\'"'),
                    ('literal_string', '`'),
                    ('alias_prefix', '$'),]

LIT_GRAMMAR = {}
for k, v in _RAW_LIT_GRAMMAR:
    if k in ('start_inline_dict', 'end_inline_dict'):
        LIT_GRAMMAR[k] = v
    else:
        LIT_GRAMMAR[k] = v.format(**LIT_GRAMMAR)




# Assemble regex grammar
# >>> unicode_whitespace = [cp for cp, data in unicodetools.ucd.proplist.items() if 'White_Space' in data]
_RAW_RE_GRAMMAR = []

# Whitespace
_RAW_RE_WS = [('space', re.escape(LIT_GRAMMAR['space'])),
              ('indent', '[{0}]'.format(re.escape(LIT_GRAMMAR['indent']))),
              ('newline', re.escape(LIT_GRAMMAR['newline'])),
              ('whitespace', '[{0}]'.format(re.escape(LIT_GRAMMAR['whitespace'])))]
_RAW_RE_GRAMMAR.extend(_RAW_RE_WS)

# Special characters
for k in ('comment', 'assign_key_val', 'open_noninline_list',
          'start_inline_dict', 'end_inline_dict',
          'start_inline_list', 'end_inline_list',
          'start_tag', 'end_tag', 'end_tag_suffix',
          'inline_separator', 'block_prefix', 'block_suffix',
          'escaped_string', 'literal_string', 'alias_prefix'):
    v = re.escape(LIT_GRAMMAR[k])
    if len(v) > 1:
        v = '[{0}]'.format(v)
    _RAW_RE_GRAMMAR[k] = v

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
                ('dec_float', '''
                              {opt_sign_indent}(?:{zero}|{nonzero_dec_digit}{dec_digit}*(?:_{dec_digit}+)*)
                                  (?:\\.{dec_digits_underscores}(?:_?{dec_exponent})?|_?{dec_exponent})
                              '''.replace('\x20', '').replace('\n', '')),
                ('hex_exponent', '[pP]{sign}?{dec_digits_underscores}'),
                ('hex_float', '''
                              {opt_sign_indent}0x_?
                              (?:{lower_hex_digits_underscores}(?:\\.{lower_hex_digits_underscores}(?:_?{hex_exponent})? | _?{hex_exponent}) |
                                 {upper_hex_digits_underscores}(?:\\.{upper_hex_digits_underscores}(?:_?{hex_exponent})? | _?{hex_exponent})
                              )
                              '''.replace('\x20', '').replace('\n', '')),
                ('infinity', '{opt_sign_indent}inf'),
                ('not_a_number', '{opt_sign_indent}nan'),
                ('float_reserved_word', '{opt_sign_indent}(?:[iI][nN][fF]|[nN][aA][nN])'),
                ('float', '{dec_float}|{hex_float}|{infinity}|{not_a_number}'),

                # Unquoted strings of all varieties
                ('ascii_start', '[A-Za-z]'),
                ('unicode_start', re_patterns.XID_START_LESS_FILLERS),
                ('ascii_continue', '[0-9A-Za-z_]'),
                ('unicode_continue', re_patterns.XID_CONTINUE_LESS_FILLERS),
                ('unquoted_ascii_key', '_*{ascii_start}{ascii_continue}*'),
                ('unquoted_unicode_key', '_*{unicode_start}{unicode_continue}*'),
                ('ascii_alias', '{alias_prefix}{unquoted_ascii_key}'),
                ('unicode_alias', '{alias_prefix}{unquoted_unicode_key}'),
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
                ('rtl_code_point', '{0}|{1}'.format(re_patterns.BIDI_R_AL, re_patterns.PRIVATE_USE)),

                # Keypaths
                ('ascii_key_keypath', '(?:{unquoted_ascii_key}|{open_noninline_list})(?:\\.(?:{unquoted_ascii_key}|{open_noninline_list}))+'),
                ('ascii_val_keypath', '(?:{alias_prefix}?{unquoted_ascii_key}(?:.{unquoted_ascii_key})*'),
                ('unicode_key_keypath', '(?:{unquoted_unicode_key}|{open_noninline_list})(?:\\.(?:{unquoted_unicode_key}|{open_noninline_list}))+'),
                ('unicode_val_keypath', '(?:{alias_prefix}?{unquoted_unicode_key}(?:.{unquoted_unicode_key})*')]
_RAW_RE_GRAMMAR.extend(_RAW_RE_TYPES)

RE_GRAMMAR = {}
for k, v in _RAW_RE_GRAMMAR:
    if k in ('start_inline_dict', 'end_inline_dict'):
        RE_GRAMMAR[k] = v
    else:
        RE_GRAMMAR[k] = v.format(**RE_GRAMMAR)

