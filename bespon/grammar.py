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




# General notes on suffixes in variable names.  Note that these suffixes only
# have the meanings described below when used as suffixes.
#  * Use of "ascii" suffix in a variable name indicates a restriction to code
#    points in 0x00-0x7F, or 0-127 (that is, 7-bit).
#  * Use of "below_u0590" suffix in a variable name indicates a restriction
#    to code points below 0x590, which is a convenient range because it
#    contains very few invalid code points (only those in Unicode Cc) and
#    does not contain any right-to-left code points.  Thus, regex patterns
#    are only marginally more complex and slower than for the ASCII range,
#    while rtl checks may be omitted.
#  * Use of "unicode" suffix in a variable name indicates that the full range
#    of Unicode code points in 0x00-0x10FFFF is covered.
#  * Use of "bytes" suffix in a variable name indicates that it is an ASCII
#    representation of a byte string.  Such variables are manipulated as
#    Unicode strings so that things like the `.format()` method are available,
#    but must always be encoded with ASCII before being used.


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


# Non-textual general parameters
PARAMS = {'max_nesting_depth': 100,
          'max_delim_length': 3*30}




# Assemble literal grammar
_RAW_LIT_GRAMMAR = [# Whitespace
                    ('tab', '\t'),
                    ('space', '\x20'),
                    ('indent', '{tab}{space}'),
                    ('newline', '\n'),
                    ('line_terminator_ascii', '\n\v\f\r'),
                    ('line_terminator_unicode', '{line_terminator_ascii}\u0085\u2028\u2029'),
                    ('whitespace', '{indent}{newline}'),
                    # unicode_whitespace = set([cp for cp, data in unicodetools.ucd.proplist.items() if 'White_Space' in data])
                    ('unicode_whitespace', ('\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u00a0\u1680' +
                                            '\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a' +
                                            '\u2028\u2029\u202f\u205f\u3000')),
                    # Keywords
                    ('none_type', 'none'),
                    ('bool_true', 'true'),
                    ('bool_false', 'false'),
                    ('infinity_word', 'inf'),
                    ('not_a_number_word', 'nan'),
                    # Math
                    ('sign', '+-'),
                    ('dec_exponent_letter', 'eE'),
                    ('hex_exponent_letter', 'pP'),
                    ('quaternion_unit', 'ijk'),
                    ('imaginary_unit', 'i'),
                    # Other
                    ('bom', '\uFEFF'),
                    # Need to be able to add a sentinel to the end of a string
                    # during backslash-escape processing with custom `indent`.
                    # A code point that is invalid as a literal is needed,
                    # ideally in the ASCII range.  Almost anything could be
                    # used.  The end-of-text character (ETX) was chosen
                    # because it has the right meaning and is safer than null
                    # in the event of a bug that allows a sentinel to escape
                    # into data (which shouldn't happen for an implementation
                    # that passes the test suite).
                    ('terminal_sentinel', '\u0003')]

_RAW_LIT_SPECIAL = [# Special code points
                    ('comment_delim', '#'),
                    ('assign_key_val', '='),
                    ('open_indentation_list', '*'),
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
                    ('self_alias', '_'),
                    # Combinations
                    ('end_tag_with_suffix', '{end_tag}{end_tag_suffix}'),
                    # Numbers
                    ('number_start', '0123456789+-')]
_RAW_LIT_GRAMMAR.extend(_RAW_LIT_SPECIAL)

LIT_GRAMMAR = {}
for k, v in _RAW_LIT_GRAMMAR:
    if k in ('start_inline_dict', 'end_inline_dict'):
        LIT_GRAMMAR[k] = v
    else:
        LIT_GRAMMAR[k] = v.format(**LIT_GRAMMAR)
# Add a few elements that couldn't conveniently be created with the grammar
# definition format
LIT_GRAMMAR['line_terminator_ascii_seq'] = ('\r\n',) + tuple(x for x in LIT_GRAMMAR['line_terminator_ascii'])
LIT_GRAMMAR['line_terminator_unicode_seq'] = ('\r\n',) + tuple(x for x in LIT_GRAMMAR['line_terminator_unicode'])




# Assemble regex grammar
_RAW_RE_GRAMMAR = [('backslash', '\\\\'),
                   ('line_terminator_ascii', '[{0}]'.format(re.escape(LIT_GRAMMAR['line_terminator_ascii']))),
                   ('line_terminator_unicode', '[{0}]'.format(re.escape(LIT_GRAMMAR['line_terminator_unicode']))),
                   ('terminal_sentinel', re.escape(LIT_GRAMMAR['terminal_sentinel']))]

def _group_if_needed(pattern):
    if '|' in pattern:
        return '(?:{0})'.format(pattern)
    return pattern

# Regex patterns
_RE_PATTERNS = [('ascii_alpha', '[A-Za-z]'),
                ('ascii_alphanum', '[A-Za-z0-9]'),
                ('xid_start_ascii', _group_if_needed(re_patterns.XID_START_ASCII)),
                ('xid_start_below_u0590', _group_if_needed(re_patterns.XID_START_BELOW_U0590)),
                ('xid_start_less_fillers', _group_if_needed(re_patterns.XID_START_LESS_FILLERS)),
                ('xid_continue_ascii', _group_if_needed(re_patterns.XID_CONTINUE_ASCII)),
                ('xid_continue_below_u0590', _group_if_needed(re_patterns.XID_CONTINUE_BELOW_U0590)),
                ('xid_continue_less_fillers', _group_if_needed(re_patterns.XID_CONTINUE_LESS_FILLERS)),
                ('not_valid_ascii', _group_if_needed(re_patterns.NOT_VALID_LITERAL_ASCII)),
                ('not_valid_below_u0590', _group_if_needed(re_patterns.NOT_VALID_LITERAL_BELOW_U0590)),
                ('not_valid_unicode', _group_if_needed(re_patterns.NOT_VALID_LITERAL)),
                ('always_escaped_ascii', _group_if_needed(re_patterns.ALWAYS_ESCAPED_ASCII)),
                ('always_escaped_below_u0590', _group_if_needed(re_patterns.ALWAYS_ESCAPED_BELOW_U0590)),
                ('always_escaped_unicode', _group_if_needed(re_patterns.ALWAYS_ESCAPED)),
                ('bidi_rtl', _group_if_needed(re_patterns.BIDI_R_AL)),
                ('private_use', _group_if_needed(re_patterns.PRIVATE_USE))]
_RAW_RE_GRAMMAR.extend(_RE_PATTERNS)

#
_RAW_RE_CP_GROUPS = [('unquoted_start_ascii', '_*{xid_start_ascii}'),
                     ('unquoted_start_below_u0590', '_*{xid_start_below_u0590}'),
                     ('unquoted_start_unicode', '_*{xid_start_less_fillers}'),
                     ('unquoted_continue_ascii', '{xid_continue_ascii}'),
                     ('unquoted_continue_below_u0590', '{xid_continue_below_u0590}'),
                     ('unquoted_continue_unicode', '{xid_continue_less_fillers}')]
_RAW_RE_GRAMMAR.extend(_RAW_RE_CP_GROUPS)

# Whitespace
_RAW_RE_WS = [('space', re.escape(LIT_GRAMMAR['space'])),
              ('indent', '[{0}]'.format(re.escape(LIT_GRAMMAR['indent']))),
              ('newline', re.escape(LIT_GRAMMAR['newline'])),
              ('whitespace', '[{0}]'.format(re.escape(LIT_GRAMMAR['whitespace'])))]
_RAW_RE_GRAMMAR.extend(_RAW_RE_WS)

# Special characters
for k, v in _RAW_LIT_SPECIAL:
    _RAW_RE_GRAMMAR.append((k, re.escape(LIT_GRAMMAR[k])))


def _capitalization_permutations_pattern(*words):
    permutations = []
    for w in words:
        perm = ''.join('[{0}{1}]'.format(c.upper(), c.lower()) for c in w)
        permutations.append(perm)
    return '|'.join(permutations)


# Types
_RAW_RE_TYPE = [# None type
                ('none_type', LIT_GRAMMAR['none_type']),
                ('none_type_reserved_word', _capitalization_permutations_pattern(LIT_GRAMMAR['none_type'])),

                # Boolean
                ('bool_true', LIT_GRAMMAR['bool_true']),
                ('bool_false', LIT_GRAMMAR['bool_false']),
                ('bool_reserved_word', _capitalization_permutations_pattern(LIT_GRAMMAR['bool_true'], LIT_GRAMMAR['bool_false'])),

                # Basic numeric elements
                ('sign', '[{0}]'.format(re.escape(LIT_GRAMMAR['sign']))),
                ('opt_sign_indent', '(?:{sign}{indent}*)?'),
                ('zero', '0'),
                ('nonzero_dec_digit', '[1-9]'),
                ('dec_digit', '[0-9]'),
                ('underscore_dec_digits', '(?:_{dec_digit}+)'),
                ('lower_hex_digit', '[0-9a-f]'),
                ('underscore_lower_hex_digits', '(?:_{lower_hex_digit}+)'),
                ('upper_hex_digit', '[0-9A-F]'),
                ('underscore_upper_hex_digits', '(?:_{upper_hex_digit}+)'),
                ('oct_digit', '[0-7]'),
                ('underscore_oct_digits', '(?:_{oct_digit}+)'),
                ('bin_digit', '[01]'),
                ('underscore_bin_digits', '(?:_{bin_digit}+)'),

                # Number types
                # Integers
                ('positive_dec_integer', '(?:{zero}|{nonzero_dec_digit}{dec_digit}*{underscore_dec_digits}*)'),
                ('hex_prefix', '0x_?'),
                ('hex_integer_value', '(?:{lower_hex_digit}+{underscore_lower_hex_digits}*|{upper_hex_digit}+{underscore_upper_hex_digits}*)'),
                ('positive_hex_integer', '{hex_prefix}{hex_integer_value}'),
                ('oct_prefix', '0o_?'),
                ('oct_integer_value', '{oct_digit}+{underscore_oct_digits}*'),
                ('positive_oct_integer', '{oct_prefix}{oct_integer_value}'),
                ('bin_prefix', '0b_?'),
                ('bin_integer_value', '{bin_digit}+{underscore_bin_digits}*'),
                ('positive_bin_integer', '{bin_prefix}{bin_integer_value}'),
                # Any integer -- order is important due to base prefixes
                ('positive_integer', '(?:{positive_hex_integer}|{positive_oct_integer}|{positive_bin_integer}|{positive_dec_integer})'),
                ('integer', '{opt_sign_indent}{positive_integer}'),
                # Floats
                ('dec_exponent_letter', '[{0}]'.format(LIT_GRAMMAR['dec_exponent_letter'])),
                ('dec_exponent', '{dec_exponent_letter}{sign}?{dec_digit}+{underscore_dec_digits}*'),
                ('decimal_point', '\\.'),
                ('dec_fraction_and_or_exponent', '(?:{decimal_point}{dec_digit}+{underscore_dec_digits}*(?:_?{dec_exponent})?|_?{dec_exponent})'),
                ('positive_dec_float', '{positive_dec_integer}{dec_fraction_and_or_exponent}'),
                ('hex_exponent_letter', '[{0}]'.format(LIT_GRAMMAR['hex_exponent_letter'])),
                ('hex_exponent', '{hex_exponent_letter}{sign}?{dec_digit}+{underscore_dec_digits}*'),
                ('hex_float_value', '''
                                    (?: {lower_hex_digit}+{underscore_lower_hex_digits}* (?:{decimal_point}{lower_hex_digit}+{underscore_lower_hex_digits}*(?:_?{hex_exponent})? | _?{hex_exponent}) |
                                        {upper_hex_digit}+{underscore_upper_hex_digits}* (?:{decimal_point}{upper_hex_digit}+{underscore_upper_hex_digits}*(?:_?{hex_exponent})? | _?{hex_exponent})
                                    )
                                    '''.replace('\x20', '').replace('\n', '')),
                ('positive_hex_float', '{hex_prefix}{hex_float_value}'),
                ('infinity_word', LIT_GRAMMAR['infinity_word']),
                ('not_a_number_word', LIT_GRAMMAR['not_a_number_word']),
                ('inf_or_nan_word', '(?:{infinity_word}|{not_a_number_word})'),
                ('float_reserved_word', _capitalization_permutations_pattern(LIT_GRAMMAR['infinity_word'], LIT_GRAMMAR['not_a_number_word'])),
                # Any float -- order is important due to base prefixes
                ('positive_float_ascii', '(?:{positive_hex_float}|{positive_dec_float}|{inf_or_nan_word}(?!{unquoted_continue_ascii}))'),
                ('positive_float_below_u0590', '(?:{positive_hex_float}|{positive_dec_float}|{inf_or_nan_word}(?!{unquoted_continue_below_u0590}))'),
                ('positive_float_unicode', '(?:{positive_hex_float}|{positive_dec_float}|{inf_or_nan_word}(?!{unquoted_continue_unicode}))'),
                ('float_ascii', '{opt_sign_indent}{positive_float_ascii}'),
                ('float_below_u0590', '{opt_sign_indent}{positive_float_below_u0590}'),
                ('float_unicode', '{opt_sign_indent}{positive_float_unicode}'),
                # General number -- order is important due to exponent parts
                ('number_ascii', '(?:{float_ascii}|{integer})'),
                ('number_below_u0590', '(?:{float_below_u0590}|{integer})'),
                ('number_unicode', '(?:{float_unicode}|{integer})'),
                # Efficient number pattern with named groups.  The order is
                # important.  Hex, octal, and binary must come first, so that
                # the `0` in the `0<letter>` prefix doesn't trigger a
                # premature match for integer zero.
                ('number_named_groups', r'''
                                         {opt_sign_indent}
                                         (?: {hex_prefix} (?: (?P<float_16>{hex_float_value}) | (?P<int_16>{hex_integer_value}) ) |
                                             (?P<int_8>{positive_oct_integer}) | (?P<int_2>{positive_bin_integer}) |
                                             (?P<int_10>{positive_dec_integer}) (?P<float_10>{dec_fraction_and_or_exponent})? |
                                             (?P<float_inf_or_nan_10>{inf_or_nan_word})
                                         )
                                         '''.replace('\x20', '').replace('\n', '')),
                # Quaternion
                # This leaves open the possibility of quaternion literals,
                # while providing what is necessary for complex literals
                # (by reserving both "i" and "j" for numeric use, it could
                # reduce accidental use of the wrong one for complex numbers)
                ('quaternion_unit', '[{0}]'.format(LIT_GRAMMAR['quaternion_unit'])),
                ('quaternion_unit_reserved_word', '[{0}{1}]'.format(LIT_GRAMMAR['quaternion_unit'], LIT_GRAMMAR['quaternion_unit'].upper())),
                # Complex
                ('imaginary_unit', LIT_GRAMMAR['imaginary_unit']),
                ('dec_complex_float_continue', r'''
                                                (?: {imaginary_unit} (?: {indent}* {opt_sign_indent} (?:{positive_dec_float}|{inf_or_nan_word}) )? |
                                                    {indent}* {opt_sign_indent} (?:{positive_dec_float}|{inf_or_nan_word}) {imaginary_unit})
                                                '''.replace('\x20', '').replace('\n', '')),
                ('hex_complex_float_continue', r'''
                                                (?: {imaginary_unit} (?: {indent}* {opt_sign_indent} (?:{positive_hex_float}|{inf_or_nan_word}) )? |
                                                    {indent}* {opt_sign_indent} (?:{positive_hex_float}|{inf_or_nan_word}) {imaginary_unit})
                                                '''.replace('\x20', '').replace('\n', '')),
                ('inf_or_nan_word_complex_float_continue', r'''
                                                (?: {imaginary_unit} (?: {indent}* {opt_sign_indent} (?:{positive_dec_float}|{positive_hex_float}|{inf_or_nan_word}) )? |
                                                    {indent}* {opt_sign_indent} (?:{positive_dec_float}|{positive_hex_float}|{inf_or_nan_word}) {imaginary_unit})
                                                '''.replace('\x20', '').replace('\n', '')),
                ('inf_or_nan_word_complex_hex_float_continue', r'''
                                                (?: {imaginary_unit} (?: {indent}* {opt_sign_indent} {positive_hex_float} )? |
                                                    {indent}* {opt_sign_indent} {positive_hex_float} {imaginary_unit})
                                                '''.replace('\x20', '').replace('\n', '')),
                ('dec_complex_float', r'''
                                       {opt_sign_indent}
                                       (?: {positive_dec_float} {dec_complex_float_continue} |
                                           {positive_hex_float} {hex_complex_float_continue} |
                                           {inf_or_nan_word} {inf_or_nan_word_complex_float_continue}
                                       )
                                       '''.replace('\x20', '').replace('\n', '')),
                # Rational
                ('rational_continue', '{indent}*/{indent}*{positive_dec_integer}'),
                ('positive_rational', '{positive_dec_integer}{rational_continue}'),
                ('rational', '{opt_sign_indent}{positive_rational}'),
                # Efficient extended number pattern with named groups.
                ('extended_number_named_groups', r'''
                                         {opt_sign_indent}
                                         (?: {hex_prefix} (?: (?P<float_16>{hex_float_value})(?P<complex_16>{hex_complex_float_continue})? | (?P<int_16>{hex_integer_value}) ) |
                                             (?P<int_8>{positive_oct_integer}) | (?P<int_2>{positive_bin_integer}) |
                                             (?P<int_10>{positive_dec_integer}) (?: (?P<rational_10>{rational_continue})|(?P<float_10>{dec_fraction_and_or_exponent})(?P<complex_10>{dec_complex_float_continue})? )? |
                                             (?P<float_inf_or_nan_10>{inf_or_nan_word}) (?: (?P<complex_inf_or_nan_10>{dec_complex_float_continue})|(?P<complex_inf_or_nan_16>{inf_or_nan_word_complex_hex_float_continue}) )?
                                         )
                                         '''.replace('\x20', '').replace('\n', '')),

                # Keywords and reserved words
                ('keyword', '(?:{none_type}|{bool_true}|{bool_false}|{infinity_word}|{not_a_number_word})'),
                ('non_number_keyword', '(?:{none_type}|{bool_true}|{bool_false})'),
                ('extended_keyword', '(?:{none_type}|{bool_true}|{bool_false}|{infinity_word}{imaginary_unit}?|{not_a_number_word}{imaginary_unit}?)'),
                ('reserved_word', '(?:{none_type_reserved_word}|{bool_reserved_word}|(?:{float_reserved_word}){quaternion_unit_reserved_word}?)'),

                # Unquoted strings
                ('unquoted_string_ascii', '{unquoted_start_ascii}{unquoted_continue_ascii}*'),
                ('unquoted_string_below_u0590', '{unquoted_start_below_u0590}{unquoted_continue_below_u0590}*'),
                ('unquoted_string_unicode', '{unquoted_start_unicode}{unquoted_continue_unicode}*'),
                ('unquoted_string_or_list_ascii', '(?:{unquoted_string_ascii}|{open_indentation_list}(?!{path_separator}))'),
                ('unquoted_string_or_list_below_u0590', '(?:{unquoted_string_below_u0590}|{open_indentation_list}(?!{path_separator}))'),
                ('unquoted_string_or_list_unicode', '(?:{unquoted_string_unicode}|{open_indentation_list}(?!{path_separator}))'),

                # Key path
                ('key_path_continue_ascii', '(?:{path_separator}{unquoted_string_or_list_ascii})'),
                ('key_path_continue_below_u0590', '(?:{path_separator}{unquoted_string_or_list_below_u0590})'),
                ('key_path_continue_unicode', '(?:{path_separator}{unquoted_string_or_list_unicode})'),
                ('key_path_ascii', '{unquoted_string_ascii}{key_path_continue_ascii}+'),
                ('key_path_below_u0590', '{unquoted_string_below_u0590}{key_path_continue_below_u0590}+'),
                ('key_path_unicode', '{unquoted_string_unicode}{key_path_continue_unicode}+'),

                # Unquoted strings and key paths
                ('unquoted_string_or_key_path_named_group_ascii', r'''
                        (?P<reserved_word>{reserved_word}(?!{unquoted_continue_ascii}|{path_separator})) |
                        (?P<unquoted_string>{unquoted_string_ascii}) (?P<key_path>{key_path_continue_ascii}+)?
                        '''.replace('\x20', '').replace('\n', '')),
                ('unquoted_string_or_key_path_named_group_below_u0590', r'''
                        (?P<reserved_word>{reserved_word}(?!{unquoted_continue_below_u0590}|{path_separator})) |
                        (?P<unquoted_string>{unquoted_string_below_u0590}) (?P<key_path>{key_path_continue_below_u0590}+)?
                        '''.replace('\x20', '').replace('\n', '')),
                ('unquoted_string_or_key_path_named_group_unicode', r'''
                        (?P<reserved_word>{reserved_word}(?!{unquoted_continue_unicode}|{path_separator})) |
                        (?P<unquoted_string>{unquoted_string_unicode}) (?P<key_path>{key_path_continue_unicode}+)?
                        '''.replace('\x20', '').replace('\n', '')),

                # Alias path
                ('alias_path_ascii', '{alias_prefix}(?:{home_alias}|{self_alias}|{unquoted_string_ascii})(?:{path_separator}{unquoted_string_ascii})*'),
                ('alias_path_below_u0590', '{alias_prefix}(?:{home_alias}|{self_alias}|{unquoted_string_below_u0590})(?:{path_separator}{unquoted_string_below_u0590})*'),
                ('alias_path_unicode', '{alias_prefix}(?:{home_alias}|{self_alias}|{unquoted_string_unicode})(?:{path_separator}{unquoted_string_unicode})*'),

                # Binary types
                ('base16', r'''
                        {lower_hex_digit}+ (?:{space}*{newline} {lower_hex_digit}+)* (?:{space}*{newline})? \Z |
                        {upper_hex_digit}+ (?:{space}*{newline} {upper_hex_digit}+)* (?:{space}*{newline})? \Z |
                        {lower_hex_digit}{{2}}(?:{space}{lower_hex_digit}{{2}})* (?:{space}*{newline} {lower_hex_digit}{{2}}(?:{space}{lower_hex_digit}{{2}})*)* (?:{space}*{newline})? \Z |
                        {upper_hex_digit}{{2}}(?:{space}{upper_hex_digit}{{2}})* (?:{space}*{newline} {upper_hex_digit}{{2}}(?:{space}{upper_hex_digit}{{2}})*)* (?:{space}*{newline})? \Z
                        '''.replace('\x20', '').replace('\n', '')),
                ('base64', r'[A-Za-z0-9+/=]+(?:{space}*{newline}[A-Za-z0-9+/=]+)*(?:{space}*{newline})?\Z')]
_RAW_RE_GRAMMAR.extend(_RAW_RE_TYPE)

# Escapes (no string formatting is performed on these, so braces are fine)
_RAW_RE_ESC = [('short_escapes_codepoint', '[{0}]'.format(re.escape(''.join(e[1] for e in SHORT_BACKSLASH_UNESCAPES)))),
               ('not_short_escapes_codepoint', '[^{0}]'.format(re.escape(''.join(e[1] for e in SHORT_BACKSLASH_UNESCAPES)))),
               ('x_escape', 'x(?:{lower_hex_digit}{{2}}|{upper_hex_digit}{{2}})'),
               ('u_escape', 'u(?:{lower_hex_digit}{{4}}|{upper_hex_digit}{{4}})'),
               ('U_escape', 'U(?:{lower_hex_digit}{{8}}|{upper_hex_digit}{{8}})'),
               ('ubrace_escape', 'u\\{{(?:{lower_hex_digit}{{1,6}}|{upper_hex_digit}{{1,6}})\\}}'),
               # The general escape patterns can include `\<spaces><newline>`,
               # but don't need to be compiled with re.DOTALL because the
               # newlines are specified explicitly and accounted for before
               # the dot in the patterns.  The last two patterns (arbitrary
               # character after backslash, or none) don't lead to errors,
               # because all such matches are filtered through a dict of
               # valid short escapes.  Invalid escapes are caught at that
               # point; the regex pattern just needs to catch everything that
               # could be a valid escape.
               ('escape_valid_or_invalid_bytes', r'\\(?:{x_escape}|{space}*{newline}|.|)'),
               ('escape_valid_bytes', r'\\(?:{x_escape}|{space}*{newline}|{short_escapes_codepoint})'),
               ('escape_valid_or_invalid_unicode', r'\\(?:{x_escape}|{u_escape}|{U_escape}|{ubrace_escape}|{space}*{newline}|.|)'),
               ('escape_valid', r'\\(?:{x_escape}|{u_escape}|{U_escape}|{ubrace_escape}|{space}*{newline}|{short_escapes_codepoint})')]
_RAW_RE_GRAMMAR.extend(_RAW_RE_ESC)

_raw_key_not_formatted = set(k for k, v in _RAW_LIT_SPECIAL) | set(k for k, v in _RE_PATTERNS)

RE_GRAMMAR = {}
for k, v in _RAW_RE_GRAMMAR:
    if k in _raw_key_not_formatted:
        RE_GRAMMAR[k] = v
    else:
        RE_GRAMMAR[k] = v.format(**RE_GRAMMAR)




# Functions for generating grammar-based regex patterns and compiled regexes
def gen_closing_delim_pattern(delim,
                              escaped_string_singlequote_delim=LIT_GRAMMAR['escaped_string_singlequote_delim'],
                              escaped_string_doublequote_delim=LIT_GRAMMAR['escaped_string_doublequote_delim'],
                              literal_string_delim=LIT_GRAMMAR['literal_string_delim'],
                              comment_delim=LIT_GRAMMAR['comment_delim']):
    '''
    Create a regex pattern suitable for finding the closing delimiter for
    `delim`.
    '''
    c_0 = delim[0]
    if c_0 == escaped_string_singlequote_delim or c_0 == escaped_string_doublequote_delim:
        group = 1
        n = len(delim)
        if n == 1:
            # The `(?=[\\{delim_char}])` lookahead is required to
            # avoid catastrophic backtracking.  In cases when
            # catastrophic backtracking would not occur, the
            # lookahead seems to add negligible overhead.
            pattern = r'^(?:[^{delim_char}\\]+(?=[\\{delim_char}])|\\.)*({delim_char})'.format(delim_char=re.escape(c_0))
        else:
            # The pattern here is a bit complicated to deal with the
            # possibility of escapes and of runs of the delimiter that
            # are too short or too long.  It would be possible just to
            # look for runs of the delimiter of the correct length,
            # bounded by non-delimiters or a leading `\<delim>`.  Then
            # any leading backslashes could be stripped and counted to
            # determine whether the first delim is literal or escaped.
            # Some simple benchmarks suggest that that approach would
            # typically be only a few percent faster before the
            # additional overhead of checking backslashes and possibly
            # re-invoking the regex are considered.  So alternatives
            # don't seem worthwhile.
            #
            # The `^` works, because any leading whitespace is already
            # stripped before the regex is applied.
            pattern = r'''
                        ^(?: [^{delim_char}\\]+(?=[\\{delim_char}]) | \\. | {delim_char}{{1,{n_minus}}}(?!{delim_char}) | {delim_char}{{{n_plus},}}(?!{delim_char}) )*
                        ({delim_char}{{{n}}}(?!{delim_char}))
                        '''.replace('\x20', '').replace('\n', '').format(delim_char=re.escape(c_0), n=n, n_minus=n-1, n_plus=n+1)
    elif c_0 == literal_string_delim or (c_0 == comment_delim and len(delim) >= 3):
        group = 0
        n = len(delim)
        if n == 1:
            pattern = r'(?<!{delim_char}){delim_char}(?!{delim_char})'.format(delim_char=re.escape(c_0))
        else:
            pattern = r'(?<!{delim_char}){delim_char}{{{n}}}(?!{delim_char})'.format(delim_char=re.escape(c_0), n=n)
    else:
        raise ValueError
    return (pattern, group)

def gen_closing_delim_re(delim, gen_closing_delim_pattern=gen_closing_delim_pattern):
    '''
    Generate a compiled regex suitable for finding the closing delimiter for
    `delim`.
    '''
    p, g = gen_closing_delim_pattern(delim)
    return (re.compile(p), g)
