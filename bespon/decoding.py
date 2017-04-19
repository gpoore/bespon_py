# -*- coding: utf-8 -*-
#
# Copyright (c) 2016-2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


# pylint: disable=C0301


from __future__ import (division, print_function, absolute_import,
                        unicode_literals)


from .version import __version__
import sys
import collections
import re

from . import erring
from . import escape
from . import tooling
from . import load_types
from . import grammar
from .ast import Ast
from .astnodes import ScalarNode, KeyPathNode, SectionNode

if sys.version_info.major == 2:
    str = unicode


BOM = grammar.LIT_GRAMMAR['bom']
MAX_DELIM_LENGTH = grammar.PARAMS['max_delim_length']

NEWLINE = grammar.LIT_GRAMMAR['newline']
INDENT = grammar.LIT_GRAMMAR['indent']
WHITESPACE_SET = set(grammar.LIT_GRAMMAR['whitespace'])
UNICODE_WHITESPACE_SET = set(grammar.LIT_GRAMMAR['unicode_whitespace'])

OPEN_INDENTATION_LIST = grammar.LIT_GRAMMAR['open_indentation_list']
PATH_SEPARATOR = grammar.LIT_GRAMMAR['path_separator']
END_TAG_WITH_SUFFIX = grammar.LIT_GRAMMAR['end_tag_with_suffix']
ASSIGN_KEY_VAL = grammar.LIT_GRAMMAR['assign_key_val']

ESCAPED_STRING_SINGLEQUOTE_DELIM = grammar.LIT_GRAMMAR['escaped_string_singlequote_delim']
ESCAPED_STRING_DOUBLEQUOTE_DELIM = grammar.LIT_GRAMMAR['escaped_string_doublequote_delim']
LITERAL_STRING_DELIM = grammar.LIT_GRAMMAR['literal_string_delim']
COMMENT_DELIM = grammar.LIT_GRAMMAR['comment_delim']
BLOCK_PREFIX = grammar.LIT_GRAMMAR['block_prefix']
BLOCK_SUFFIX = grammar.LIT_GRAMMAR['block_suffix']
BLOCK_DELIM_SET = set([LITERAL_STRING_DELIM, ESCAPED_STRING_SINGLEQUOTE_DELIM,
                       ESCAPED_STRING_DOUBLEQUOTE_DELIM, LITERAL_STRING_DELIM,
                       COMMENT_DELIM, ASSIGN_KEY_VAL])

NUMBER_START = grammar.LIT_GRAMMAR['number_start']




class State(object):
    '''
    Keep track of a data source and all associated state.  This includes
    general information about the source, the current location within the
    source, the current parsing context, cached values, and regular
    expressions appropriate for analyzing the source.
    '''
    __slots__ = ['source_name', 'source_include_depth',
                 'source_initial_nesting_depth', 'source_inline',
                 'source_embedded',
                 'source_raw_string', 'source_lines', 'source_lines_iter',
                 'source_only_ascii', 'source_only_below_u0590',
                 'indent', 'continuation_indent', 'at_line_start',
                 'inline', 'inline_indent',
                 'bom_offset',
                 'first_lineno', 'first_colno', 'last_lineno', 'last_colno',
                 'nesting_depth',
                 'next_cache',
                 'next_tag', 'in_tag', 'start_root_tag', 'end_root_tag',
                 'next_doc_comment', 'last_line_comment_lineno',
                 'next_scalar', 'next_scalar_is_keyable',
                 'type_data',
                 'ast', 'full_ast',
                 'bidi_rtl', 'bidi_rtl_re',
                 'bidi_rtl_last_scalar_last_lineno',
                 'bidi_rtl_last_scalar_last_line',
                 'newline_re', 'unquoted_string_or_key_path_re', 'number_re',
                 'escape_unicode', 'unescape_unicode', 'unescape_bytes']
    def __init__(self, decoder, source_raw_string,
                 source_name=None, source_include_depth=0,
                 source_initial_nesting_depth=0,
                 source_embedded=False,
                 indent='', at_line_start=True,
                 inline=False, inline_indent=None,
                 first_lineno=1, first_colno=1,
                 type_data=None, full_ast=False):
        if not all(x is None or isinstance(x, str) for x in (source_name, inline_indent)):
            raise TypeError
        if not all(isinstance(x, str) for x in (indent,)):
            raise TypeError
        if any(x is not None and x.lstrip('\x20\t') for x in (indent, inline_indent)):
            raise ValueError('Invalid indentation characters; only spaces and tabs are allowed')
        if not all(isinstance(x, int) and x >= 0 for x in (source_include_depth, source_initial_nesting_depth)):
            if all(isinstance(x, int) for x in (source_include_depth, source_initial_nesting_depth)):
                raise ValueError
            raise TypeError
        if not all(isinstance(x, int) and x > 0 for x in (first_lineno, first_colno)):
            if all(isinstance(x, int) for x in (first_lineno, first_colno)):
                raise ValueError
            raise TypeError
        if not all(x in (True, False) for x in (at_line_start, inline, full_ast, source_embedded)):
            raise TypeError
        if type_data is not None and not (isinstance(type_data, dict) and all(isinstance(k, str) and hasattr(v, '__call__') for k, v in type_data)):
            raise TypeError

        self.source_name = source_name or '<data>'
        self.source_include_depth = source_include_depth
        self.source_initial_nesting_depth = source_initial_nesting_depth
        self.source_inline = inline
        self.source_embedded = source_embedded

        self.indent = indent
        self.continuation_indent = None
        self.at_line_start = at_line_start
        self.inline = inline
        self.inline_indent = inline_indent
        self.first_lineno = first_lineno
        self.first_colno = first_colno
        self.last_lineno = self.first_lineno
        self.last_colno = self.first_colno
        self.nesting_depth = self.source_initial_nesting_depth

        self.next_cache = False
        self.next_tag = None
        self.in_tag = False
        self.start_root_tag = None
        self.end_root_tag = None
        self.next_doc_comment = None
        self.last_line_comment_lineno = 0
        self.next_scalar = None
        self.next_scalar_is_keyable = False

        self.type_data = type_data or load_types.CORE_TYPES
        self.full_ast = full_ast

        self.newline_re = decoder._newline_re
        self.escape_unicode = decoder._escape_unicode
        self.unescape_unicode = decoder._unescape_unicode
        self.unescape_bytes = decoder._unescape_bytes

        self._check_literals_set_code_point_attrs(source_raw_string, decoder)
        self.source_lines = source_raw_string.splitlines()
        self.source_lines_iter = iter(self.source_lines)

        self.ast = Ast(self)
        if self.full_ast:
            self.ast.source_lines = self.source_lines


    def _traceback_not_valid_literal(self, source_raw_string, index):
        '''
        Locate an invalid literal code point using an re match object,
        and raise an error.
        '''
        newline_count = 0
        newline_index = 0
        for m in self.newline_re.finditer(source_raw_string, 0, index):
            newline_count += 1
            newline_index = m.start()
        if newline_count == 0:
            self.first_colno += index - self.bom_offset
            self.last_colno = self.first_colno
        else:
            self.first_lineno += newline_count
            self.first_colno = index - newline_index
            self.last_lineno = self.first_lineno
            self.last_colno = self.first_colno
        code_point = source_raw_string[index]
        code_point_esc = self.escape_unicode(code_point)
        raise erring.InvalidLiteralError(self, code_point, code_point_esc)


    def _check_literals_set_code_point_attrs(self, source_raw_string, decoder, bom=BOM):
        '''
        Check the decoded source for right-to-left code points and invalid
        literal code points.  Set regexes for key paths and unquoted strings
        based on the range of code points present.
        '''
        self.source_only_ascii = True
        self.source_only_below_u0590 = True
        self.bidi_rtl = False
        self.bidi_rtl_re = decoder._bidi_rtl_re
        self.bidi_rtl_last_scalar_last_lineno = 0
        self.bidi_rtl_last_scalar_last_line = ''
        self.unquoted_string_or_key_path_re = decoder._unquoted_string_or_key_path_ascii_re
        self.number_re = decoder._number_re

        if source_raw_string[:1] == bom:
            bom_offset = 1
        else:
            bom_offset = 0
        self.bom_offset = bom_offset

        m_not_valid_ascii = decoder._not_valid_ascii_re.search(source_raw_string, bom_offset)
        if m_not_valid_ascii is None:
            return
        if not decoder.literal_unicode:
            self._traceback_not_valid_literal(source_raw_string, m_not_valid_ascii.start())
        self.source_only_ascii = False
        self.unquoted_string_or_key_path_re = decoder._unquoted_string_or_key_path_below_u0590_re
        m_not_valid_below_u0590 = decoder._not_valid_below_u0590_re.search(source_raw_string, m_not_valid_ascii.start())
        if m_not_valid_below_u0590 is None:
            return
        self.source_only_below_u0590 = False
        self.unquoted_string_or_key_path_re = decoder._unquoted_string_or_key_path_unicode_re
        m_bidi_rtl_or_not_valid_unicode = decoder._bidi_rtl_or_not_valid_unicode_re.search(source_raw_string, m_not_valid_below_u0590.start())
        if m_bidi_rtl_or_not_valid_unicode is None:
            return
        if m_bidi_rtl_or_not_valid_unicode.lastgroup == 'not_valid':
            self._traceback_not_valid_literal(source_raw_string, m_bidi_rtl_or_not_valid_unicode.start())
        self.bidi_rtl = True
        m_not_valid_unicode = decoder._not_valid_unicode_re.search(source_raw_string, m_bidi_rtl_or_not_valid_unicode.start())
        if m_not_valid_unicode is None:
            return
        self._traceback_not_valid_literal(source_raw_string, m_not_valid_unicode.start())




class BespONDecoder(object):
    '''
    Decode BespON in a string or stream.
    '''
    def __init__(self, *args, **kwargs):
        # Process args
        if args:
            raise TypeError('Explicit keyword arguments are required')
        literal_unicode = kwargs.pop('literal_unicode', True)
        unquoted_strings = kwargs.pop('unquoted_strings', True)
        unquoted_unicode = kwargs.pop('unquoted_unicode', False)
        integers = kwargs.pop('integers', True)
        if any(x not in (True, False) for x in (literal_unicode, unquoted_strings, unquoted_unicode, integers)):
            raise TypeError
        if not literal_unicode and unquoted_unicode:
            raise ValueError('Setting "literal_unicode"=False is incompatible with "unquoted_unicode"=True')
        self.literal_unicode = literal_unicode
        self.unquoted_strings = unquoted_strings
        self.unquoted_unicode = unquoted_unicode
        self.integers = integers

        custom_parsers = kwargs.pop('custom_parsers', None)
        custom_types = kwargs.pop('custom_types', None)
        if not all(x is None for x in (custom_parsers, custom_types)):
            raise NotImplementedError
        self.custom_parsers = custom_parsers
        self.custom_types = custom_types

        if kwargs:
            raise TypeError('Unexpected keyword argument(s) {0}'.format(', '.join('{0}'.format(k) for k in kwargs)))


        # Parser and type info access
        self._type_data = load_types.CORE_TYPES


        # Create escape and unescape functions
        self._escape_unicode = escape.basic_unicode_escape
        self._unescape = escape.Unescape()
        self._unescape_unicode = self._unescape.unescape_unicode
        self._unescape_bytes = self._unescape.unescape_bytes


        # Create dict of token-based parsing functions.
        #
        # Also create a dict containing only the scalar-related subset of
        # parsing functions.  This is used in sections.
        #
        # In general, having a valid starting code point for an unquoted
        # string or key path is a necessary but not sufficient condition for
        # finding a valid string or key path, due to the possibility of a
        # leading underscore.  It is simplest always to attempt a match and
        # then perform a check for success, rather than to try to
        # micro-optimize out the underscore case so that a check isn't usually
        # needed.  This also simplifies the handling of missing code points in
        # the parsing dict; since matches are checked for validity, an invalid
        # code point will automatically be caught by the standard procedure.
        # Futhermore, this approach greatly simplifies the handling of Unicode
        # surrogate pairs under narrow Python builds.  The high surrogates
        # will simply invoke an attempt at a match, which will fail for
        # invalid code points.
        parse_token = collections.defaultdict(lambda: self._parse_token_unquoted_string_or_key_path)
        parse_scalar_token = collections.defaultdict(lambda: self._parse_token_unquoted_string_or_key_path)
        token_functions = {'comment_delim': self._parse_token_comment_delim,
                           'assign_key_val': self._parse_token_assign_key_val,
                           'open_indentation_list': self._parse_token_open_indentation_list,
                           'start_inline_dict': self._parse_token_start_inline_dict,
                           'end_inline_dict': self._parse_token_end_inline_dict,
                           'start_inline_list': self._parse_token_start_inline_list,
                           'end_inline_list': self._parse_token_end_inline_list,
                           'start_tag': self._parse_token_start_tag,
                           'end_tag': self._parse_token_end_tag,
                           'inline_element_separator': self._parse_token_inline_element_separator,
                           'block_prefix': self._parse_token_block_prefix,
                           'escaped_string_singlequote_delim': self._parse_token_escaped_string,
                           'escaped_string_doublequote_delim': self._parse_token_escaped_string,
                           'literal_string_delim': self._parse_token_literal_string_delim,
                           'alias_prefix': self._parse_token_alias_prefix}
        for token_name, func in token_functions.items():
            token = grammar.LIT_GRAMMAR[token_name]
            parse_token[token] = func
            if 'string' in token_name:
                parse_scalar_token[token] = func
        for c in NUMBER_START:
            parse_token[c] = self._parse_token_number
            parse_scalar_token[c] = self._parse_token_number
        for c in INDENT:
            parse_token[c] = self._parse_token_whitespace
        parse_token[''] = self._parse_line_goto_next
        self._parse_token = parse_token
        self._parse_scalar_token = parse_scalar_token


        # Assemble regular expressions
        self._not_valid_ascii_re = re.compile(grammar.RE_GRAMMAR['not_valid_ascii'])
        self._not_valid_below_u0590_re = re.compile(grammar.RE_GRAMMAR['not_valid_below_u0590'])
        not_valid_unicode = grammar.RE_GRAMMAR['not_valid_unicode']
        self._not_valid_unicode_re = re.compile(not_valid_unicode)
        bidi_rtl = grammar.RE_GRAMMAR['bidi_rtl']
        self._bidi_rtl_re = re.compile(bidi_rtl)
        self._bidi_rtl_or_not_valid_unicode_re = re.compile(r'(?P<not_valid>{0})|(?P<bidi_rtl>{1})|'.format(not_valid_unicode, bidi_rtl))
        self._newline_re = re.compile(grammar.RE_GRAMMAR['newline'])

        # Dict of regexes for identifying closing delimiters for inline
        # escaped strings.  Needed regexes are automatically generated on the
        # fly.  Note that opening delimiters are handled by normal string
        # methods, as are closing delimiters for block strings.  Because block
        # string end delimiters are bounded by `|` and `/`, and must be at the
        # start of a line, lookbehind and lookahead for escapes or other
        # delimiter characters is unneeded.  However, the inline regexes are
        # used in processing block strings to check whether internal runs of
        # delimiters are valid.
        escaped_string_singlequote_delim = ESCAPED_STRING_SINGLEQUOTE_DELIM
        escaped_string_doublequote_delim = ESCAPED_STRING_DOUBLEQUOTE_DELIM
        literal_string_delim = LITERAL_STRING_DELIM
        comment_delim = COMMENT_DELIM
        def gen_closing_delim_regex(delim):
            c_0 = delim[0]
            if c_0 == escaped_string_singlequote_delim or c_0 == escaped_string_doublequote_delim:
                group = 1
                if delim == escaped_string_singlequote_delim or delim == escaped_string_doublequote_delim:
                    pattern = r'^(?:\\.|[^{delim_char}\\])*({delim_char})'.format(delim_char=re.escape(c_0))
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
                    n = len(delim)
                    pattern = r'''
                               ^(?: \\. | [^{delim_char}\\] | {delim_char}{{1,{n_minus}}}(?!{delim_char}) | {delim_char}{{{n_plus},}}(?!{delim_char}) )*
                                ({delim_char}{{{n}}}(?!{delim_char}))
                               '''.replace('\x20', '').replace('\n', '').format(delim_char=re.escape(c_0), n=n, n_minus=n-1, n_plus=n+1)
            elif c_0 == literal_string_delim or (c_0 == comment_delim and len(delim) >= 3):
                group = 0
                if delim == literal_string_delim:
                    pattern = r'(?<!{delim_char}){delim_char}(?!{delim_char})'.format(delim_char=re.escape(c_0))
                else:
                    n = len(delim)
                    pattern = r'(?<!{delim_char}){delim_char}{{{n}}}(?!{delim_char})'.format(delim_char=re.escape(c_0), n=n)
            else:
                raise ValueError
            return (re.compile(pattern), group)
        self._closing_delim_re_dict = tooling.keydefaultdict(gen_closing_delim_regex)

        # Number types.  The order in the regex is important.
        # Hex, octal, and binary must come first, so that the `0` in the
        # `0<letter>` prefix doesn't trigger a premature match for integer
        # zero.
        num_pattern = r'''
            {hex_prefix} (?: (?P<float_16>{hex_float_value}) | (?P<int_16>{hex_integer_value}) ) |
            (?P<int_8>{oct_integer}) | (?P<int_2>{bin_integer}) |
            (?P<int_10>{dec_integer}) (?P<float_10>{dec_fraction_and_or_exponent})? |
            (?P<float_inf_or_nan_10>{inf_or_nan})
            '''.replace('\x20', '').replace('\n', '')
        self._number_re = re.compile(num_pattern.format(**grammar.RE_GRAMMAR))

        # Unquoted strings and key paths.
        # `{unquoted_key_or_list}` will match `*`, but that won't allow `*`
        # to be used as a normal dict key, since the list parsing function is
        # called for `*` everywhere except for sections.  In sections, `*`
        # is valid by itself, or at the end of a key path.
        uqs_or_kp_pattern = r'''
            (?P<reserved_word>{reserved_word}(?!{unquoted_continue}|{path_separator})) |
            (?P<unquoted_string>{unquoted_string_or_list}) (?P<key_path>{unquoted_key_path_continue}+)?
            '''.replace('\x20', '').replace('\n', '')

        self._unquoted_string_or_key_path_ascii_re = re.compile(uqs_or_kp_pattern.format(reserved_word=grammar.RE_GRAMMAR['reserved_word'],
                                                                                         unquoted_continue=grammar.RE_GRAMMAR['unquoted_continue_ascii'],
                                                                                         path_separator=grammar.RE_GRAMMAR['path_separator'],
                                                                                         unquoted_string_or_list=grammar.RE_GRAMMAR['unquoted_string_or_list_ascii'],
                                                                                         unquoted_key_path_continue=grammar.RE_GRAMMAR['key_path_continue_ascii']))
        self._unquoted_string_or_key_path_below_u0590_re = re.compile(uqs_or_kp_pattern.format(reserved_word=grammar.RE_GRAMMAR['reserved_word'],
                                                                                               unquoted_continue=grammar.RE_GRAMMAR['unquoted_continue_below_u0590'],
                                                                                               path_separator=grammar.RE_GRAMMAR['path_separator'],
                                                                                               unquoted_string_or_list=grammar.RE_GRAMMAR['unquoted_string_or_list_below_u0590'],
                                                                                               unquoted_key_path_continue=grammar.RE_GRAMMAR['key_path_continue_below_u0590']))
        self._unquoted_string_or_key_path_unicode_re = re.compile(uqs_or_kp_pattern.format(reserved_word=grammar.RE_GRAMMAR['reserved_word'],
                                                                                           unquoted_continue=grammar.RE_GRAMMAR['unquoted_continue_unicode'],
                                                                                           path_separator=grammar.RE_GRAMMAR['path_separator'],
                                                                                           unquoted_string_or_list=grammar.RE_GRAMMAR['unquoted_string_or_list_unicode'],
                                                                                           unquoted_key_path_continue=grammar.RE_GRAMMAR['key_path_continue_unicode']))

        # Dict for looking up types of valid reserved words
        self._reserved_word_types = {grammar.LIT_GRAMMAR['none_type']: 'none',
                                     grammar.LIT_GRAMMAR['bool_true']: 'bool',
                                     grammar.LIT_GRAMMAR['bool_false']: 'bool',
                                     grammar.LIT_GRAMMAR['infinity_word']: 'float',
                                     grammar.LIT_GRAMMAR['not_a_number_word']: 'float'}


    @staticmethod
    def _unwrap_inline_string(s_list, unicode_whitespace_set=UNICODE_WHITESPACE_SET):
        '''
        Unwrap an inline string.

        Any line that ends with a newline preceded by Unicode whitespace has
        the newline stripped.  Otherwise, a trailing newline is replace by a
        space.  The last line will not have a newline due to the ending
        delimiter or alternatively the regex pattern for undelimited strings.

        Note that in escaped strings, a single backslash before a newline is
        not treated as an escape in unwrapping.  Escaping newlines is only
        allowed in block strings.  A line that ends in a backslash followed
        by a newline will not be accidentally converted into a valid escape
        by the unwrapping process, because it would be converted into a
        backslash followed by a space, which is not a valid escape.
        '''
        s_list_inline = []
        for line in s_list[:-1]:
            if line[-1:] in unicode_whitespace_set:
                s_list_inline.append(line)
            else:
                s_list_inline.append(line + '\x20')
        s_list_inline.append(s_list[-1])
        return ''.join(s_list_inline)


    def _as_unicode_string(self, unicode_string_or_bytes):
        '''
        Take an object that may be a Unicode string or bytes, and return
        a Unicode string.
        '''
        if isinstance(unicode_string_or_bytes, str):
            unicode_string = unicode_string_or_bytes
        else:
            try:
                unicode_string = unicode_string_or_bytes.decode('utf8')
            except Exception as e:
                raise erring.SourceDecodeError(e)
        return unicode_string


    def decode(self, unicode_string_or_bytes):
        '''
        Decode a Unicode string or byte string into Python objects.
        '''
        unicode_string = self._as_unicode_string(unicode_string_or_bytes)
        state = State(self, unicode_string)
        self._parse_lines(state)
        return state.ast.root.final_val


    def decode_to_ast(self, unicode_string_or_bytes):
        '''
        Decode a Unicode string or byte string into AST with full source
        information.
        '''
        unicode_string = self._as_unicode_string(unicode_string_or_bytes)
        state = State(self, unicode_string, full_ast=True)
        self._parse_lines(state)
        return state.ast


    def _parse_lines(self, state):
        '''
        Process lines from source into abstract syntax tree (AST).  Then
        process the AST into standard Python objects.
        '''
        source_lines_iter = state.source_lines_iter
        # Start by extracting the first line and stripping any BOM
        line = next(source_lines_iter, '')
        if state.bom_offset == 1:
            # Don't increment column, because that would throw off indentation
            # for subsequent lines
            line = line[1:]
        line = self._parse_line_start_last(line, state)

        parse_token = self._parse_token
        while line is not None:
            line = parse_token[line[:1]](line, state)

        state.ast.finalize()
        if not state.ast.root:
            raise erring.ParseError('There was no data to load', state)


    def _check_bidi_rtl(self, state):
        if state.bidi_rtl_last_scalar_last_lineno == state.first_lineno and state.bidi_rtl_re.search(state.bidi_rtl_last_scalar_last_line):
            raise erring.ParseError('Cannot start a scalar object or comment on a line with a preceding object whose last line contains right-to-left code points', state)


    def _parse_line_goto_next(self, line, state, next=next, whitespace=INDENT,
                              whitespace_set=WHITESPACE_SET):
        '''
        Go to next line.  Used when parsing completes on a line, and no
        additional parsing is needed for that line.

        The `line` argument is needed so that this can be used in the
        `_parse_token` dict of functions as the value for the empty string
        key.  When the function is used directly as part of other parsing
        functions, this argument isn't actually needed.  However, it is kept
        mandatory to maintain parallelism between all of the `_parse_line_*()`
        functions, since some of these do require a `line` argument.

        In the event of `line == None`, use sensible values.  The primary
        concern is the line numbers. If the last line ends with `\n`, then
        incrementing the line number when `line == None` is correct.  If the
        last line does not end with `\n`, then incrementing is technically
        incorrect in a sense, but could be interpreted as automatically
        inserting the missing `\n`.
        '''
        line = next(state.source_lines_iter, None)
        lineno = state.last_lineno + 1
        state.first_lineno = lineno
        state.last_lineno = lineno
        if line is None or line[:1] not in whitespace_set:
            state.indent = ''
            state.continuation_indent = ''
            state.at_line_start = True
            state.first_colno = 1
            state.last_colno = 1
            return line
        line_lstrip_ws = line.lstrip(whitespace)
        indent_len = len(line) - len(line_lstrip_ws)
        indent = line[:indent_len]
        state.indent = indent
        state.continuation_indent = indent
        state.at_line_start = True
        colno = indent_len + 1
        state.first_colno = colno
        state.last_colno = colno
        return line_lstrip_ws


    def _parse_line_get_next(self, line, state, next=next):
        '''
        Get next line.  For use in lookahead in string scanning, etc.
        '''
        line = next(state.source_lines_iter, None)
        state.last_lineno += 1
        state.last_colno = 1
        return line


    def _parse_line_start_last(self, line, state, whitespace=INDENT,
                               whitespace_set=WHITESPACE_SET):
        '''
        Reset everything after `_parse_line_get_next()`, so that it's
        equivalent to using `_parse_line_goto_next()`.  Useful when
        `_parse_line_get_next()` is used for lookahead, but nothing is
        consumed.

        As with `_parse_line_goto_next()`, sensible defaults are needed for
        the `line == None` case.
        '''
        state.first_lineno = state.last_lineno
        if line is None or line[:1] not in whitespace_set:
            state.indent = ''
            state.continuation_indent = ''
            state.at_line_start = True
            state.first_colno = 1
            state.last_colno = 1
            return line
        line_lstrip_ws = line.lstrip(whitespace)
        indent_len = len(line) - len(line_lstrip_ws)
        indent = line[:indent_len]
        state.indent = indent
        state.continuation_indent = indent
        state.at_line_start = True
        colno = indent_len + 1
        state.first_colno = colno
        state.last_colno = colno
        return line_lstrip_ws


    def _parse_line_continue_last(self, line, state):
        '''
        Reset everything after `_parse_line_get_next()`, to continue on
        with the next line after having consumed part of it.
        '''
        state.first_lineno = state.last_lineno
        state.continuation_indent = state.indent
        state.at_line_start = False
        state.last_colno += 1
        state.first_colno = state.last_colno
        return line


    def _parse_token_whitespace(self, line, state, whitespace=INDENT):
        '''
        Parse whitespace.
        '''
        line_lstrip_ws = line.lstrip(whitespace)
        colno = state.last_colno + len(line) - len(line_lstrip_ws)
        state.first_colno = colno
        state.last_colno = colno
        return line_lstrip_ws


    def _parse_token_assign_key_val(self, line, state):
        '''
        Assign a cached key or key path.
        '''
        if state.next_scalar is None:
            raise erring.ParseError('Missing key cannot be assigned', state)
        state.ast.append_scalar_key()
        colno = state.last_colno + 1
        state.first_colno = colno
        state.last_colno = colno
        return line[1:]


    def _parse_token_open_indentation_list(self, line, state,
                                         path_separator=PATH_SEPARATOR):
        '''
        Open a non-inline list, or start a key path that has a list as its
        first element.
        '''
        # Any tag or doc comment is handled during opening the list.
        # No need to check for `**`, because that would attempt to open a list
        # twice, which would trigger an error.
        if state.next_scalar is not None:
            if state.inline or state.next_scalar.last_lineno == state.first_lineno:
                raise erring.ParseError('Encountered a tag when a prior scalar has not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        state.ast.open_indentation_list()
        if line[1:2] == '\t' and (state.indent == '' or state.indent[-1:] == '\t'):
            return self._parse_line_start_last(state.indent + line[1:], state)
        return self._parse_line_start_last(state.indent + '\x20' + line[1:], state)


    def _parse_token_start_inline_dict(self, line, state):
        '''
        Start an inline dict.
        '''
        if state.next_scalar is not None:
            raise erring.ParseError('Cannot start a dict-like object when a prior scalar has not yet been resolved', state, unresolved_cache=True)
        state.ast.start_inline_dict()
        return self._parse_line_continue_last(line[1:], state)


    def _parse_token_end_inline_dict(self, line, state):
        '''
        End an inline dict.
        '''
        if state.next_scalar is not None:
            state.ast.append_scalar_val()
        elif state.next_cache:
            raise erring.ParseError('Cannot end a dict-like object when a prior object has not yet been resolved', state, unresolved_cache=True)
        state.ast.end_inline_dict()
        return self._parse_line_continue_last(line[1:], state)


    def _parse_token_start_inline_list(self, line, state):
        '''
        Start an inline list.
        '''
        if state.next_scalar is not None:
            raise erring.ParseError('Cannot start a list-like object when a prior scalar has not yet been resolved', state, unresolved_cache=True)
        state.ast.start_inline_list()
        return self._parse_line_continue_last(line[1:], state)


    def _parse_token_end_inline_list(self, line, state):
        '''
        End an inline list.
        '''
        if state.next_scalar is not None:
            state.ast.append_scalar_val()
        elif state.next_cache:
            raise erring.ParseError('Cannot end a list-like object when a prior object has not yet been resolved', state, unresolved_cache=True)
        state.ast.end_inline_list()
        return self._parse_line_continue_last(line[1:], state)


    def _parse_token_start_tag(self, line, state):
        '''
        Start a tag.
        '''
        raise NotImplementedError
        if state.next_scalar is not None:
            if state.inline or state.next_scalar.last_lineno == state.first_lineno:
                raise erring.ParseError('Cannot start a tag when a prior scalar has not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        elif state.next_tag is not None:
            raise erring.ParseError('Cannot start a tag when a prior tag has not yet been resolved', state, unresolved_cache=True)
        state.ast.start_tag()
        return self._parse_line_continue_last(line[1:], state)


    def _parse_token_end_tag(self, line, state,
                             end_tag_with_suffix=END_TAG_WITH_SUFFIX):
        '''
        End a tag.
        '''
        raise NotImplementedError
        if line[:2] != end_tag_with_suffix:
            raise erring.ParseError('Invalid end tag delimiter', state)
        if state.next_scalar is not None:
            state.ast.append_scalar_val()
        # No need to check `state.next_cache`, since doc comments and tags
        # aren't possible inside tags.
        # Account for end tag suffix
        state.last_colno += 1
        state.ast.end_tag()
        # Account for end tag suffix with `[2:]`
        return self._parse_line_continue_last(line[2:], state)


    def _parse_token_inline_element_separator(self, line, state):
        '''
        Parse an element separator in a dict or list.
        '''
        if state.next_scalar is not None:
            state.ast.append_scalar_val()
        elif state.next_cache:
            raise erring.ParseError('Cannot open a collection object when a prior object has not yet been resolved', state, unresolved_cache=True)
        state.ast.open_inline_collection()
        return self._parse_line_continue_last(line[1:], state)


    def _parse_delim_inline(self, name, delim, line, state, section=False,
                            whitespace=INDENT,
                            unicode_whitespace_set=UNICODE_WHITESPACE_SET):
        '''
        Find the closing delimiter for an inline quoted string or doc comment.
        '''
        closing_delim_re, group = self._closing_delim_re_dict[delim]
        m = closing_delim_re.search(line)
        if m is not None:
            content = line[:m.start(group)]
            line = line[m.end(group):]
            state.last_colno += 2*len(delim) + len(content) - 1
            return ([content], content, line)
        if section:
            raise erring.ParseError('Unterminated {0} (section strings must start and end on the same line)'.format(name), state)
        content_lines = []
        content_lines.append(line)
        indent = state.indent
        line = self._parse_line_get_next(line, state)
        if line is None:
            raise erring.ParseError('Unterminated {0} (reached end of data)'.format(name), state)
        line_lstrip_ws = line.lstrip(whitespace)
        continuation_indent = line[:len(line)-len(line_lstrip_ws)]
        state.continuation_indent = continuation_indent
        if not continuation_indent.startswith(indent):
            raise erring.IndentationError(state)
        line = line_lstrip_ws
        while True:
            if line == '':
                raise erring.ParseError('Unterminated {0} (inline delimited strings cannot contain empty lines)'.format(name), state)
            if line[0] in unicode_whitespace_set:
                state.last_colno += len(continuation_indent)
                if line[0] in whitespace:
                    raise erring.IndentationError(state)
                raise erring.ParseError('A Unicode whitespace code point "{0}" was found where a wrapped line was expected to start'.format(self._escape_unicode(line[0])), state)
            if delim in line:
                m = closing_delim_re.search(line)
                if m is not None:
                    line_content = line[:m.start(group)]
                    line = line[m.end(group):]
                    content_lines.append(line_content)
                    state.last_colno += len(continuation_indent) + m.end(group) - 1
                    break
            content_lines.append(line)
            line = self._parse_line_get_next(line, state)
            if line is None:
                raise erring.ParseError('Unterminated {0} (reached end of data)'.format(name), state)
            if not line.startswith(continuation_indent):
                if line.lstrip(whitespace) == '':
                    raise erring.ParseError('Unterminated {0} (inline delimited strings cannot contain empty lines)'.format(name), state)
                raise erring.IndentationError(state)
            line = line[len(continuation_indent):]
        return (content_lines, self._unwrap_inline_string(content_lines), line)


    def _parse_token_line_comment(self, line, state,
                                  comment_delim=COMMENT_DELIM,
                                  ScalarNode=ScalarNode):
        '''
        Parse a line comment.  This is used in `_parse_token_comment()`.
        No checking is done for `#` followed by `#`, since this function is
        only ever called with valid line comments.  This function receives
        the line with the leading `#` still intact.
        '''
        state.last_line_comment_lineno = state.last_lineno
        if state.full_ast:
            state.last_colno += len(line) - 1
            node = ScalarNode(state, delim=comment_delim, implicit_type='line_comment')
            node.raw_val = line[1:]
            node.final_val = node.raw_val
            node._resolved = True
            state.ast.scalar_nodes.append(node)
            state.ast.line_comments.append(node)
        return self._parse_line_goto_next('', state)


    def _parse_token_comment_delim(self, line, state,
                                   comment_delim=COMMENT_DELIM,
                                   max_delim_length=MAX_DELIM_LENGTH,
                                   ScalarNode=ScalarNode):
        '''
        Parse inline comments.
        '''
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        line_strip_delim = line.lstrip(comment_delim)
        len_delim = len(line) - len(line_strip_delim)
        if len_delim == 1:
            return self._parse_token_line_comment(line, state)
        if len_delim == 2:
            raise erring.ParseError('Invalid comment start "{0}"; use "{1}" for a line comment, or "{3}<comment>{3}" for an inline doc comment'.format(comment_delim*2, comment_delim, comment_delim*3), state)
        if len_delim % 3 != 0 or len_delim > max_delim_length:
            raise erring.ParseError('Doc comment delims must have lengths that are multiples of 3 and are no longer than {0} characters'.format(max_delim_length), state)
        if state.in_tag:
            raise erring.ParseError('Doc comments are not allowed in tags', state)
        if state.next_scalar is not None:
            if state.inline or state.next_scalar.last_lineno == state.first_lineno:
                raise erring.ParseError('Cannot start a doc comment when a prior scalar has not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        elif state.next_cache:
            raise erring.ParseError('Cannot start a doc comment when a prior object has not yet been resolved', state, unresolved_cache=True)
        delim = line[:len_delim]
        content_lines, content, line = self._parse_delim_inline('doc comment', delim, line_strip_delim, state)
        node = ScalarNode(state, delim=delim, block=False, implicit_type='doc_comment')
        if state.full_ast:
            node.raw_val = content_lines
            state.ast.scalar_nodes.append(node)
        node.final_val = content
        node._resolved = True
        state.next_doc_comment = node
        state.next_cache = True
        if state.bidi_rtl:
            state.bidi_rtl_last_scalar_last_line = content_lines[-1]
            state.bidi_rtl_last_scalar_last_lineno = node.last_lineno
        return self._parse_line_continue_last(line, state)


    def _parse_token_literal_string_delim(self, line, state, section=False,
                                          max_delim_length=MAX_DELIM_LENGTH,
                                          ScalarNode=ScalarNode,
                                          literal_string_delim=LITERAL_STRING_DELIM):
        '''
        Parse inline literal string.
        '''
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        if state.next_scalar is not None:
            if state.inline or state.next_scalar.last_lineno == state.first_lineno:
                raise erring.ParseError('Cannot start a string when a prior string has not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        line_strip_delim = line.lstrip(line[0])
        len_delim = len(line) - len(line_strip_delim)
        if len_delim > 3 and (len_delim % 3 != 0 or len_delim > max_delim_length):
            raise erring.ParseError('Literal string delims must have lengths of 1 or 2, or multiples of 3 that are no longer than {0} characters'.format(max_delim_length), state)
        delim = line[:len_delim]
        content_lines, content, line = self._parse_delim_inline('literal string', delim, line_strip_delim, state, section=section)
        content_strip_space = content.strip('\x20')
        if content_strip_space[:1] == literal_string_delim:
            content = content[1:]
        if content_strip_space[-1:] == literal_string_delim:
            content = content[:-1]
        node = ScalarNode(state, delim=delim, block=False, implicit_type='literal_string')
        if state.full_ast:
            node.raw_val = content_lines
            state.ast.scalar_nodes.append(node)
        node.final_val = content
        node._resolved = True
        state.next_scalar = node
        state.next_scalar_is_keyable = True
        state.next_cache = True
        if state.bidi_rtl:
            state.bidi_rtl_last_scalar_last_line = content_lines[-1]
            state.bidi_rtl_last_scalar_last_lineno = node.last_lineno
        return self._parse_line_continue_last(line, state)


    def _parse_token_escaped_string(self, line, state, section=False,
                                    max_delim_length=MAX_DELIM_LENGTH,
                                    ScalarNode=ScalarNode):
        '''
        Parse inline escaped string (single or double quote).
        '''
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        if state.next_scalar is not None:
            if state.inline or state.next_scalar.last_lineno == state.first_lineno:
                raise erring.ParseError('Encountered a string when a prior string had not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        line_strip_delim = line.lstrip(line[0])
        len_delim = len(line) - len(line_strip_delim)
        if len_delim == 2:
            delim = line[0]
            content_lines = ['']
            content = ''
            line = line[2:]
            state.last_colno += 1
        else:
            if len_delim > 3 and (len_delim % 3 != 0 or len_delim > max_delim_length):
                raise erring.ParseError('Escaped string delims must have lengths of 1 or multiples of 3 that are no longer than {0} characters'.format(max_delim_length), state)
            delim = line[:len_delim]
            content_lines, content, line = self._parse_delim_inline('escaped string', delim, line_strip_delim, state, section=section)
        node = ScalarNode(state, delim=delim, block=False, implicit_type='escaped_string')
        if state.full_ast:
            node.raw_val = content_lines
            state.ast.scalar_nodes.append(node)
        if '\\' not in content:
            content_esc = content
        else:
            try:
                content_esc = self._unescape_unicode(content)
            except Exception as e:
                raise erring.ParseError('Failed to unescape escaped string:\n  {0}'.format(e), node)
        node.final_val = content_esc
        node._resolved = True
        state.next_scalar = node
        state.next_scalar_is_keyable = True
        state.next_cache = True
        if state.bidi_rtl:
            state.bidi_rtl_last_scalar_last_line = content_lines[-1]
            state.bidi_rtl_last_scalar_last_lineno = node.last_lineno
        return self._parse_line_continue_last(line, state)


    def _parse_token_section(self, delim, line, state,
                             block_suffix=BLOCK_SUFFIX,
                             whitespace=INDENT,
                             SectionNode=SectionNode,
                             open_indentation_list=OPEN_INDENTATION_LIST,
                             ScalarNode=ScalarNode,
                             comment_delim=COMMENT_DELIM):
        '''
        Parse a section.  This is invoked by `_parse_token_block_prefix()`.
        At this point, `line` has already had the delimiter stripped.
        '''
        # No need to check for cached scalars, since that's done in
        # `_parse_token_block_prefix()`.  Can't have doc comments or tags
        # for sections in general, although that could technically be relaxed
        # for the first section if the root node were empty.
        if state.next_cache:
            if state.next_doc_comment is not None:
                raise erring.ParseError('Sections do not take doc comments', state, state.next_doc_comment)
            raise erring.ParseError('Sections do not take tags', state, state.next_tag)
        node = SectionNode(state, delim)
        if line[:1] == block_suffix:
            state.ast.end_section(delim)
            line_lstrip_ws = line[1:].lstrip(whitespace)
            if line_lstrip_ws == '':
                return self._parse_line_goto_next('', state)
            state.last_colno += 1 + len(delim) + len(line) - len(line_lstrip_ws)
            state.first_colno = state.last_colno
            if line_lstrip_ws[:1] == comment_delim and line_lstrip_ws[1:2] != comment_delim:
                return self._parse_token_line_comment(line_lstrip_ws, state)
            raise erring.ParseError('Unexpected content after end of section', state)
        line_lstrip_ws = line.lstrip(whitespace)
        state.last_colno += len(delim) + len(line) - len(line_lstrip_ws)
        state.first_colno = state.last_colno
        line = self._parse_scalar_token[line_lstrip_ws[:1]](line_lstrip_ws, state, section=True)
        next_scalar = state.next_scalar
        state.next_scalar = None
        state.next_cache = False
        node.last_colno = next_scalar.last_colno
        if next_scalar.basetype == 'scalar':
            if not state.next_scalar_is_keyable:
                raise erring.ParseError('Invalid scalar type for a key', node)
            node.scalar = next_scalar
        elif next_scalar.basetype == 'key_path':
            node.key_path = next_scalar
        else:
            raise erring.ParseError('Unexpected section type', node)
        node._resolved = True
        state.ast.start_section(node)
        line_lstrip_ws = line.lstrip(whitespace)
        if line_lstrip_ws == '':
            return self._parse_line_goto_next('', state)
        state.last_colno += len(line) - len(line_lstrip_ws)
        state.first_colno = state.last_colno
        if line_lstrip_ws[:1] == comment_delim and line_lstrip_ws[1:2] != comment_delim:
            return self._parse_token_line_comment(line_lstrip_ws, state)
        raise erring.ParseError('Unexpected content after start of section', state)


    def _parse_token_block_prefix(self, line, state,
                                  max_delim_length=MAX_DELIM_LENGTH,
                                  ScalarNode=ScalarNode,
                                  whitespace=INDENT,
                                  block_prefix=BLOCK_PREFIX,
                                  block_suffix=BLOCK_SUFFIX,
                                  block_delim_set=BLOCK_DELIM_SET,
                                  comment_delim=COMMENT_DELIM,
                                  escaped_string_doublequote_delim=ESCAPED_STRING_DOUBLEQUOTE_DELIM,
                                  escaped_string_singlequote_delim=ESCAPED_STRING_SINGLEQUOTE_DELIM,
                                  literal_string_delim=LITERAL_STRING_DELIM,
                                  assign_key_val=ASSIGN_KEY_VAL,
                                  newline=NEWLINE):
        '''
        Parse a block quoted string or doc comment.
        '''
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        delim_code_point = line[1:2]
        if delim_code_point not in block_delim_set:
            raise erring.ParseError('Invalid block delimiter', state)
        if delim_code_point == comment_delim:
            if state.next_doc_comment is not None:
                raise erring.ParseError('Encountered a doc comment when a prior doc comment had not yet been resolved', state, unresolved_cache=True)
        elif state.next_scalar is not None:
            if state.inline or state.next_scalar.last_lineno == state.first_lineno:
                raise erring.ParseError('Encountered a string when a prior string had not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        line_strip_delim = line[1:].lstrip(delim_code_point)
        # -1 for `|`
        len_delim = len(line) - len(line_strip_delim) - 1
        delim = delim_code_point*len_delim
        if len_delim < 3 or len_delim % 3 != 0 or len_delim > max_delim_length:
            raise erring.ParseError('Block delims must have lengths that are multiples of 3 that are no longer than {0} characters'.format(max_delim_length), state)
        if delim_code_point == assign_key_val:
            return self._parse_token_section(delim, line_strip_delim, state)
        if line_strip_delim.lstrip(whitespace) != '':
            raise erring.ParseError('An opening block delim must not be followed by anything; block content does not start until the next line', state)
        closing_delim_re, group = self._closing_delim_re_dict[delim]
        end_block_delim = block_prefix + delim + block_suffix
        content_lines = []
        indent = state.indent
        while True:
            line = self._parse_line_get_next(line, state)
            if line is None:
                raise erring.ParseError('Unterminated block object', state)
            if not line.startswith(indent) and line.lstrip(whitespace) != '':
                raise erring.IndentationError(state)
            if delim in line:
                m = closing_delim_re.search(line)
                if m is not None:
                    line_lstrip_ws = line.lstrip(whitespace)
                    if not line_lstrip_ws.startswith(end_block_delim):
                        raise erring.ParseError('Invalid delim sequence in body of block object')
                    continuation_indent = line[:len(line)-len(line_lstrip_ws)]
                    len_continuation_indent = len(continuation_indent)
                    state.continuation_indent = continuation_indent
                    line = line_lstrip_ws[len(end_block_delim):]
                    state.last_colno += len_continuation_indent + len(end_block_delim) - 1
                    if state.at_line_start and indent != continuation_indent:
                        raise erring.ParseError('Inconsistent block delim indentation', state)
                    if continuation_indent == '':
                        content_lines_dedent = content_lines
                    else:
                        content_lines_dedent = []
                        for lineno, c_line in enumerate(content_lines):
                            if c_line.startswith(continuation_indent):
                                content_lines_dedent.append(c_line[len_continuation_indent:])
                            elif c_line.lstrip(whitespace) == '':
                                content_lines_dedent.append('')
                            else:
                                raise erring.ParseError('Incorrect indentation relative to block delim indentation on line {0}'.format(state.first_lineno+lineno+1), state)
                    break
            content_lines.append(line)
        # Note that there's no need to reset the bidi_rtl state, given the
        # nature of the final delimiter.
        # Modify last line by adding `\n`, then join lines with `\n`, then
        # put last line back to original value, to avoid having to modify the
        # final string by adding an `\n` at the end
        content_lines_dedent_last_line = content_lines_dedent[-1]
        content_lines_dedent[-1] = content_lines_dedent_last_line + newline
        content = newline.join(content_lines_dedent)
        content_lines_dedent[-1] = content_lines_dedent_last_line
        if delim_code_point == literal_string_delim:
            node = ScalarNode(state, delim=delim, block=True, implicit_type='literal_string')
            if state.full_ast:
                node.raw_val = content_lines_dedent
                state.ast.scalar_nodes.append(node)
            node.final_val = content
            node._resolved = True
            state.next_scalar = node
            state.next_scalar_is_keyable = True
            state.next_cache = True
        elif delim_code_point == escaped_string_singlequote_delim or delim_code_point == escaped_string_doublequote_delim:
            node = ScalarNode(state, delim=delim, block=True, implicit_type='escaped_string')
            if state.full_ast:
                node.raw_val = content_lines_dedent
                state.ast.scalar_nodes.append(node)
            try:
                content_esc = self._unescape_unicode(content)
            except Exception as e:
                raise erring.ParseError('Failed to unescape escaped string:\n  {0}'.format(e), node)
            node.final_val = content_esc
            node._resolved = True
            state.next_scalar = node
            state.next_scalar_is_keyable = True
            state.next_cache = True
        elif delim_code_point == comment_delim:
            node = ScalarNode(state, delim=delim, block=True, implicit_type='doc_comment')
            if state.full_ast:
                node.raw_val = content_lines_dedent
                state.ast.scalar_nodes.append(node)
            node.final_val = content
            node._resolved = True
            state.next_doc_comment = node
            state.next_cache = True
        else:
            raise ValueError
        return self._parse_line_continue_last(line, state)


    def _parse_token_number(self, line, state, section=False, int=int):
        '''
        Parse a number (float, int, etc.).
        '''
        # No need to update bidi_rtl; state cannot be modified by numbers
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        if state.next_scalar is not None:
            if state.inline or state.next_scalar.last_lineno == state.first_lineno:
                raise erring.ParseError('Cannot start a string when a prior string has not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        m = state.number_re.match(line)
        if m is None:
            raise erring.ParseError('Invalid literal with numeric start')
        group_name =  m.lastgroup
        group_type, group_base = group_name.rsplit('_', 1)
        raw_val = line[:m.end(group_name)]
        state.last_colno += len(raw_val) - 1
        line = line[len(raw_val):]
        if group_type == 'int':
            cleaned_val = raw_val.replace('\x20', '').replace('\t', '').replace('_', '')
            parser = state.type_data['int'].parser
            try:
                if group_base == '10':
                    final_val = parser(cleaned_val)
                else:
                    final_val = parser(cleaned_val, int(group_base))
            except Exception as e:
                raise erring.ParseError('Error in typing of integer literal:\n  {0}'.format(e), state)
            node = ScalarNode(state, implicit_type='int', num_base=int(group_base))
            state.next_scalar_is_keyable = True
        elif group_type == 'float' or group_type == 'float_inf_or_nan':
            cleaned_val = raw_val.replace('\x20', '').replace('\t', '').replace('_', '')
            parser = state.type_data['float'].parser
            try:
                if group_base == '10':
                    final_val = parser(cleaned_val)
                else:
                    final_val = parser.fromhex(cleaned_val)
            except Exception as e:
                raise erring.ParseError('Error in typing of float literal:\n  {0}'.format(e), state)
            node = ScalarNode(state, implicit_type='float', num_base=int(group_base))
            state.next_scalar_is_keyable = False
        else:
            raise ValueError
        if state.full_ast:
            node.raw_val = raw_val
            state.ast.scalar_nodes.append(node)
        node.final_val = final_val
        node._resolved = True
        state.next_scalar = node
        state.next_cache = True
        return self._parse_line_continue_last(line, state)


    def _parse_token_unquoted_string_or_key_path(self, line, state,
                                                 section=False,
                                                 whitespace=INDENT,
                                                 open_indentation_list=OPEN_INDENTATION_LIST,
                                                 ScalarNode=ScalarNode,
                                                 KeyPathNode=KeyPathNode):
        '''
        Parse an unquoted string or key path.
        '''
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        if state.next_scalar is not None:
            if state.inline or state.next_scalar.last_lineno == state.first_lineno:
                raise erring.ParseError('Cannot start a string when a prior string has not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        m = state.unquoted_string_or_key_path_re.match(line)
        if m is None:
            raise erring.ParseError('Invalid unquoted string or key path', state)
        if m.lastgroup == 'unquoted_string':
            raw_val = line[:m.end()]
            line = line[len(raw_val):]
            state.last_colno += len(raw_val) - 1
            node = ScalarNode(state, implicit_type='unquoted_string')
            if state.full_ast:
                node.raw_val = raw_val
                state.ast.scalar_nodes.append(node)
            node.final_val = raw_val
            node._resolved = True
            state.next_scalar = node
            state.next_scalar_is_keyable = True
            state.next_cache = True
            if state.bidi_rtl:
                state.bidi_rtl_last_scalar_last_line = raw_val
                state.bidi_rtl_last_scalar_last_lineno = node.last_lineno
            return self._parse_line_continue_last(line, state)
        if m.lastgroup == 'reserved_word':
            raw_val = line[:m.end('reserved_word')]
            line = line[len(raw_val):]
            state.last_colno += len(raw_val) - 1
            try:
                word_type = self._reserved_word_types[raw_val]
            except KeyError:
                raise erring.ParseError('Invalid capitalization of reserved word "{0}"'.format(raw_val.lower()), state)
            try:
                final_val = state.type_data[word_type].parser(raw_val)
            except Exception as e:
                raise erring.ParseError('Error in typing of reserved word "{0}":\n  {1}'.format(raw_val, e), state)
            node = ScalarNode(state, implicit_type=word_type)
            if state.full_ast:
                node.raw_val = raw_val
                state.ast.scalar_nodes.append(node)
            node.final_val = final_val
            node._resolved = True
            state.next_scalar = node
            if word_type != 'float':
                state.next_scalar_is_keyable = True
            else:
                state.next_scalar_is_keyable = False
            state.next_cache = True
            # Reserved words don't contain rtl code points
            return self._parse_line_continue_last(line, state)
        if m.lastgroup == 'key_path':
            raw_val = line[:m.end('key_path')]
            line = line[len(raw_val):]
            state.last_colno += len(raw_val) - 1
            node = KeyPathNode(state, raw_val)
            if state.full_ast:
                node.raw_val = raw_val
                state.ast.scalar_nodes.append(node)
            node._resolved = True
            state.next_scalar = node
            state.next_scalar_is_keyable = True
            state.next_cache = True
            if state.bidi_rtl:
                state.bidi_rtl_last_scalar_last_line = raw_val
                state.bidi_rtl_last_scalar_last_lineno = node.last_lineno
            return self._parse_line_continue_last(line, state)
        raise ValueError


    def _parse_token_alias_prefix(self, line, state):
        raise NotImplementedError
