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
from .astnodes import RootNode, ScalarNode, KeyPathNode

if sys.version_info.major == 2:
    str = unicode
    __chr__ = chr
    chr = unichr

# pylint:  disable=W0622
#if sys.maxunicode == 0xFFFF:
#    chr = coding.chr_surrogate
##   ord = coding.ord_surrogate
# pylint:  enable=W0622


INDENT = grammar.LIT_GRAMMAR['indent']
WHITESPACE = grammar.LIT_GRAMMAR['whitespace']
UNICODE_WHITESPACE = grammar.LIT_GRAMMAR['unicode_whitespace']
UNICODE_WHITESPACE_SET = set(UNICODE_WHITESPACE)
ESCAPED_STRING_SINGLEQUOTE_DELIM = grammar.LIT_GRAMMAR['escaped_string_singlequote_delim']
ESCAPED_STRING_DOUBLEQUOTE_DELIM = grammar.LIT_GRAMMAR['escaped_string_doublequote_delim']
LITERAL_STRING_DELIM = grammar.LIT_GRAMMAR['literal_string_delim']
COMMENT_DELIM = grammar.LIT_GRAMMAR['comment_delim']
OPEN_NONINLINE_LIST = grammar.LIT_GRAMMAR['open_noninline_list']
PATH_SEPARATOR = grammar.LIT_GRAMMAR['path_separator']
END_TAG_WITH_SUFFIX = grammar.LIT_GRAMMAR['end_tag_with_suffix']
MAX_DELIM_LENGTH = grammar.PARAMS['max_delim_length']
DOC_COMMENT_INVALID_NEXT_TOKEN_SET = set(grammar.LIT_GRAMMAR['doc_comment_invalid_next_token']) | set([''])
ASSIGN_KEY_VAL = grammar.LIT_GRAMMAR['assign_key_val']
WHITESPACE_OR_COMMENT_OR_EMPTY_SET = set(WHITESPACE) | set(COMMENT_DELIM) | set([''])
BOM = grammar.LIT_GRAMMAR['bom']
BLOCK_PREFIX = grammar.LIT_GRAMMAR['block_prefix']
BLOCK_SUFFIX = grammar.LIT_GRAMMAR['block_suffix']
BLOCK_DELIM_SET = set([LITERAL_STRING_DELIM, ESCAPED_STRING_SINGLEQUOTE_DELIM,
                       ESCAPED_STRING_DOUBLEQUOTE_DELIM, LITERAL_STRING_DELIM])
NEWLINE = grammar.LIT_GRAMMAR['newline']
NUMBER_OR_NUMBER_UNIT_START = grammar.LIT_GRAMMAR['number_or_number_unit_start']
SCALAR_VALID_NEXT_TOKEN_CURRENT_LINE_SET = set(grammar.LIT_GRAMMAR['scalar_valid_next_token_current_line'])



class State(object):
    '''
    Keep track of state.  This includes information about the source, the
    current location within the source, the current parsing context,
    a cached doc comment and tag for the next object that is parsed, etc.
    '''
    __slots__ = ['source', 'source_include_depth',
                 'source_initial_nesting_depth',
                 'indent', 'continuation_indent', 'at_line_start',
                 'inline', 'inline_indent',
                 'first_lineno', 'first_column', 'last_lineno', 'last_column',
                 'nesting_depth',
                 'next_tag', 'in_tag', 'start_root_tag', 'end_root_tag',
                 'next_doc_comment', 'line_comments',
                 'type_data', 'full_ast']
    def __init__(self, source=None, source_include_depth=0,
                 source_initial_nesting_depth=0,
                 indent=None, at_line_start=True,
                 inline=False, inline_indent=None,
                 first_lineno=1, first_column=1,
                 type_data=None, full_ast=False):
        if not all(x is None or isinstance(x, str) for x in (source, indent, inline_indent)):
            raise TypeError('Invalid keyword argument value')
        if any(x is not None and x.lstrip('\x20\t') for x in (indent, inline_indent)):
            raise ValueError('Invalid characters in "indent" or "inline_indent"; only spaces and tabs are allowed')
        if not all(isinstance(x, int) and x >= 0 for x in (source_include_depth, source_initial_nesting_depth)):
            if all(isinstance(x, int) for x in (source_include_depth, source_initial_nesting_depth)):
                raise ValueError('Invalid keyword argument value')
            else:
                raise TypeError('Invalid keyword argument value')
        if not all(isinstance(x, int) and x > 0 for x in (first_lineno, first_column)):
            if all(isinstance(x, int) for x in (first_lineno, first_column)):
                raise ValueError('Invalid keyword argument value')
            else:
                raise TypeError('Invalid keyword argument value')
        if not all(x in (True, False) for x in (at_line_start, inline, full_ast)):
            raise TypeError('Invalid keyword argument value')
        if type_data is not None and not (isinstance(type_data, dict) and all(isinstance(k, str) and hasattr(v, '__call__') for k, v in type_data)):
            raise TypeError('Invalid keyword argument value')

        self.source = source or '<data>'
        self.source_include_depth = source_include_depth
        self.source_initial_nesting_depth = source_initial_nesting_depth

        self.indent = indent
        self.continuation_indent = None
        self.at_line_start = at_line_start
        self.inline = inline
        self.inline_indent = inline_indent
        self.first_lineno = first_lineno
        self.first_column = first_column
        self.last_lineno = self.first_lineno
        self.last_column = self.first_column
        self.nesting_depth = self.source_initial_nesting_depth

        self.next_tag = None
        self.in_tag = False
        self.start_root_tag = None
        self.end_root_tag = None

        self.next_doc_comment = None
        self.line_comments = False

        self.type_data = type_data or load_types.CORE_TYPES
        self.full_ast = full_ast




class BespONDecoder(object):
    '''
    Decode BespON in a string or stream.
    '''
    def __init__(self, *args, **kwargs):
        # Process args
        if args:
            raise TypeError('Explicit keyword arguments are required')
        only_ascii = kwargs.pop('only_ascii', False)
        unquoted_strings = kwargs.pop('unquoted_strings', True)
        unquoted_unicode = kwargs.pop('unquoted_unicode', False)
        ints = kwargs.pop('ints', True)
        if any(x not in (True, False) for x in (only_ascii, unquoted_strings, unquoted_unicode, ints)):
            raise TypeError
        if only_ascii and unquoted_unicode:
            raise ValueError('Setting "only_ascii"=True is incompatible with "unquoted_unicode"=True')
        self.only_ascii = only_ascii
        self.unquoted_strings = unquoted_strings
        self.unquoted_unicode = unquoted_unicode
        self.ints = ints

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
        self.escape_unicode = escape.basic_unicode_escape
        self.unescape = escape.Unescape()
        self.unescape_unicode = self.unescape.unescape_unicode
        self.unescape_bytes = self.unescape.unescape_bytes


        # Create dict of token-based parsing functions
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
        token_functions = {'comment_delim': self._parse_token_comment_delim,
                           'assign_key_val': self._parse_token_assign_key_val_invalid,
                           'open_noninline_list': self._parse_token_open_noninline_list,
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
        for c in NUMBER_OR_NUMBER_UNIT_START:
            parse_token[c] = self._parse_token_number_or_number_unit
        parse_token[''] = self._parse_line_goto_next
        self._parse_token = parse_token


        # Assemble regular expressions
        self.not_valid_ascii_re = re.compile(grammar.RE_GRAMMAR['not_valid_ascii'])
        self._not_valid_below_u0590_re = re.compile(grammar.RE_GRAMMAR['not_valid_below_u0590'])
        not_valid_unicode = grammar.RE_GRAMMAR['not_valid_unicode']
        self._not_valid_unicode_re = re.compile(not_valid_unicode)
        bidi_rtl = grammar.RE_GRAMMAR['bidi_rtl']
        self._bidi_rtl_re = re.compile(bidi_rtl)
        self._bidi_rtl_or_not_valid_unicode_re = '(?P<bidi_rtl>{0})|(?P<not_valid>{1})'.format(bidi_rtl, not_valid_unicode)
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

        # Number and number-unit types.  The order in the regex is important.
        # Hex, octal, and binary must come first, so that the `0` in the
        # `0<letter>` prefix doesn't trigger a premature match.  Number-units
        # must come before floats, which must come before ints, so that the
        # match doesn't end prematurely.  It would be possible to use
        # `{unquoted_dec_number_unit_ascii}` to optimize slightly when
        # applicable.  It would probably also be possible to avoid some
        # backtracking with decimal number by splitting number-units and
        # floats into a sequence of groups, with the first group being int.
        number_or_number_unit_pattern = '''
            (?P<float_16>{hex_float}) | (?P<int_16>{hex_integer}) |
            (?P<int_8>{oct_integer}) | (?P<int_2>{bin_integer}) |
            (?P<number_unit_10>{unquoted_dec_number_unit_unicode}) |
            (?P<float_10>{dec_float}|{infinity}|{not_a_number}) |
            (?P<int_10>{dec_integer})
            '''.replace('\x20', '').replace('\n', '').format(**grammar.RE_GRAMMAR)
        self._number_or_number_unit_re = re.compile(number_or_number_unit_pattern)

        # Unquoted strings and key paths.  As with the number regex, it would
        # probably be possible to optimize to reduce backtracking.
        unquoted_string_or_key_path_pattern = '''
            (?P<key_path>{key_path}) |
            (?P<unquoted_string>{unquoted_string})(?P<unquoted_string_unfinished>{indent}*$)?
            '''.replace('\x20', '').replace('\n', '')
        unquoted_string_pattern = '(?P<unquoted_string>{unquoted_string})(?P<unquoted_string_unfinished>{indent}*$)?'
        self._unquoted_string_or_key_path_ascii_re = re.compile(unquoted_string_or_key_path_pattern.format(indent=grammar.RE_GRAMMAR['indent'],
                                                                                                           key_path=grammar.RE_GRAMMAR['key_path_ascii'],
                                                                                                           unquoted_string=grammar.RE_GRAMMAR['unquoted_string_ascii']))
        self._unquoted_string_ascii_re = re.compile(unquoted_string_pattern.format(indent=grammar.RE_GRAMMAR['indent'],
                                                                                   key_path=grammar.RE_GRAMMAR['key_path_ascii'],
                                                                                   unquoted_string=grammar.RE_GRAMMAR['unquoted_string_ascii']))
        self._unquoted_string_or_key_path_below_u0590_re = re.compile(unquoted_string_or_key_path_pattern.format(indent=grammar.RE_GRAMMAR['indent'],
                                                                                                                 key_path=grammar.RE_GRAMMAR['key_path_below_u0590'],
                                                                                                                 unquoted_string=grammar.RE_GRAMMAR['unquoted_string_below_u0590']))
        self._unquoted_string_below_u0590_re = re.compile(unquoted_string_pattern.format(indent=grammar.RE_GRAMMAR['indent'],
                                                                                         key_path=grammar.RE_GRAMMAR['key_path_below_u0590'],
                                                                                         unquoted_string=grammar.RE_GRAMMAR['unquoted_string_below_u0590']))
        self._unquoted_string_or_key_path_unicode_re = re.compile(unquoted_string_or_key_path_pattern.format(indent=grammar.RE_GRAMMAR['indent'],
                                                                                                             key_path=grammar.RE_GRAMMAR['key_path_unicode'],
                                                                                                             unquoted_string=grammar.RE_GRAMMAR['unquoted_string_unicode']))
        self._unquoted_string_unicode_re = re.compile(unquoted_string_pattern.format(indent=grammar.RE_GRAMMAR['indent'],
                                                                                     key_path=grammar.RE_GRAMMAR['key_path_unicode'],
                                                                                     unquoted_string=grammar.RE_GRAMMAR['unquoted_string_unicode']))


    @staticmethod
    def _unwrap_inline_string(s_list, unicode_whitespace_set=UNICODE_WHITESPACE_SET):
        '''
        Unwrap an inline string.

        Any line that ends with a newline preceded by Unicode whitespace has
        the newline stripped.  Otherwise, a trailing newline is replace by a
        space.  The last line will not have a newline, and any trailing
        whitespace it has will already have been dealt with during parsing, so
        it is passed through unmodified.

        Note that in escaped strings, a single backslash before a newline is
        not treated as an escape in unwrapping.  Escaping newlines is only
        allowed in block strings.
        '''
        s_list_inline = []
        for line in s_list[:-1]:
            if line[-1:] in unicode_whitespace_set:
                s_list_inline.append(line)
            else:
                s_list_inline.append(line + '\x20')
        s_list_inline.append(s_list[-1])
        return ''.join(s_list_inline)


    def _traceback_not_valid_literal(self, normalize_string, index):
        '''
        Locate an invalid literal code point using an re match object,
        and raise an error.
        '''
        state = self._state
        newline_count = 0
        newline_index = 0
        for m in self._newline_re.finditer(normalize_string, 0, index):
            newline_count += 1
            newline_index = m.start()
        state.last_lineno += lineno
        state.last_column = index - newline_index
        code_point = normalize_string[index]
        code_point_esc = self._escape(code_point)
        raise erring.InvalidLiteralError(self._state, code_point, code_point_esc)


    def _check_code_point_ranges_and_not_valid_literal(self, normalized_string, bom=BOM):
        '''
        Check the decoded, newline-normalized source for right-to-left code
        point and invalid literal code points.
        '''
        self._pure_ascii = True
        self._only_below_u0590 = True
        self._bidi_rtl = False
        self._bidi_rtl_last_scalar_last_lineno = 0
        self._bidi_rtl_last_scalar_last_line = ''
        self._unquoted_string_or_key_path_re = self._unquoted_string_or_key_path_ascii_re
        self._unquoted_string_re = self._unquoted_string_ascii_re

        if normalized_string[:1] == bom:
            bom_offset = 1
        else:
            bom_offset = 0

        m_not_valid_ascii = self.not_valid_ascii_re.search(normalized_string, bom_offset)
        if m_not_valid_ascii is None:
            return
        elif self.only_ascii:
            self._traceback_not_valid_literal(normalized_string, m_not_valid_ascii.start())
        else:
            self._pure_ascii = False
            self._unquoted_string_or_key_path_re = self._unquoted_string_or_key_path_below_u0590_re
            self._unquoted_string_re = self._unquoted_string_below_u0590_re
            m_not_valid_below_u0590 = self._not_valid_below_u0590_re.search(normalized_string, m_not_valid_ascii.start())
            if m_not_valid_below_u0590 is None:
                return
            else:
                self._only_below_u0590 = False
                self._unquoted_string_or_key_path_re = self._unquoted_string_or_key_path_unicode_re
                self._unquoted_string_re = self._unquoted_string_unicode_re
                m_bidi_rtl_or_not_valid_unicode = self._bidi_rtl_or_not_valid_unicode_re.search(normalized_string, m_not_valid_below_u0590.start())
                if m_bidi_rtl_or_not_valid_unicode is None:
                    return
                elif m_bidi_rtl_or_not_valid_unicode.lastgroup == 'not_valid':
                    self._traceback_not_valid_literal(normalized_string, m_bidi_rtl_or_not_valid_unicode.start())
                else:  # .lastgroup == 'bidi_rtl'
                    self._bidi_rtl = True
                    m_not_valid_unicode = self._not_valid_unicode_re.search(normalized_string, m_bidi_rtl_or_not_valid_unicode.start())
                    if m_not_valid_unicode is None:
                        return
                    else:
                        self._traceback_not_valid_literal(normalized_string, m_not_valid_unicode.start())


    def decode(self, string_or_bytes):
        '''
        Decode a Unicode string or byte string into Python objects.
        '''
        state = State()
        self._state = state
        # Decode if necessary
        if isinstance(string_or_bytes, str):
            raw_string = string_or_bytes
        else:
            try:
                raw_string = string_or_bytes.decode('utf8')
            except Exception as e:
                raise erring.SourceDecodeError(state, e)

        self._check_code_point_ranges_and_not_valid_literal(raw_string)

        line_iter = iter(raw_string.splitlines())
        del raw_string

        ast, data = self._parse_lines(line_iter)

        self._state = None

        return data


    def _parse_lines(self, line_iter, full_ast=False):
        '''
        Process lines from source into abstract syntax tree (AST).  Then
        process the AST into standard Python objects.
        '''
        state = self._state
        ast = Ast(state)

        self._full_ast = full_ast
        self._ast = ast
        self._line_iter = line_iter

        # Start by extracting the first line and stripping any BOM
        line = next(line_iter, '')
        if line[:1] == BOM:
            # Don't increment column, because that would throw off indentation
            # for subsequent lines
            line = line[1:]
        line = self._parse_line_start_last(line)
        line = self._parse_line_continue_last_to_next_significant_token(line, at_line_start=True)
        ast.set_root()

        parse_token = self._parse_token
        while line is not None:
            line = parse_token[line[:1]](line)

        # Don't keep references to object that are no longer needed.  This
        # only really matters for things like the ast, which can consume
        # significant memory.
        self._full_ast = None
        self._ast = None
        self._line_iter = None

        ast.finalize()
        if not ast.root:
            raise erring.ParseError('There was no data to load', state)

        data = ast.root.final_val

        return (ast, data)


    def _parse_line_goto_next(self, line, next=next, whitespace=INDENT):
        '''
        Go to next line.  Used when parsing completes on a line, and no
        additional parsing is needed for that line.

        The `line` argument is needed so that this can be used in the
        `_parse_lines` dict of functions as the value for the empty string
        key.  When the function is used directly as part of other parsing
        functions, this argument isn't actually needed.  However, it is kept
        mandatory to maintain parallelism between all of the `_parse_line_*()`
        functions, since some of these do require a `line` argument.

        In the event of `line == None`, use sensible values.  The primary
        concern is the line numbers, because some lookahead relies on
        state.first_lineno being incremented if nothing is found on the
        current line.  If the last line ends with `\n`, then incrementing
        the line number when `line == None` is correct.  If the last line
        does not end with `\n`, then incrementing is technically incorrect
        in a sense, but could be interpreted as automatically inserting the
        missing `\n`.
        '''
        line = next(self._line_iter, None)
        state = self._state
        lineno = state.last_lineno + 1
        state.first_lineno = lineno
        state.last_lineno = lineno
        if line is None:
            state.indent = ''
            state.continuation_indent = ''
            state.at_line_start = True
            state.first_column = 1
            state.last_column = 1
            return line
        line_lstrip_ws = line.lstrip(whitespace)
        indent_len = len(line) - len(line_lstrip_ws)
        indent = line[:indent_len]
        state.indent = indent
        state.continuation_indent = indent
        state.at_line_start = True
        column = indent_len + 1
        state.first_column = column
        state.last_column = column
        return line_lstrip_ws


    def _parse_line_get_next(self, line, next=next):
        '''
        Get next line.  For use in lookahead in string scanning, etc.
        '''
        state = self._state
        line = next(self._line_iter, None)
        state.last_lineno += 1
        state.last_column = 1
        return line


    def _parse_line_start_last(self, line, whitespace=INDENT):
        '''
        Reset everything after `_parse_line_get_next()`, so that it's
        equivalent to using `_parse_line_goto_next()`.  Useful when
        `_parse_token_get_next_line()` is used for lookahead, but nothing is
        consumed.

        As with `_parse_line_goto_next()`, sensible defaults are needed for
        the `line == None` case.
        '''
        state = self._state
        state.first_lineno = state.last_lineno
        if line is None:
            state.indent = ''
            state.continuation_indent = ''
            state.at_line_start = True
            state.first_column = 1
            state.last_column = 1
            return line
        line_lstrip_ws = line.lstrip(whitespace)
        indent_len = len(line) - len(line_lstrip_ws)
        indent = line[:indent_len]
        state.indent = indent
        state.continuation_indent = indent
        state.at_line_start = True
        column = indent_len + 1
        state.first_column = column
        state.last_column = column
        return line_lstrip_ws


    def _parse_line_continue_last(self, line, at_line_start=False,
                                  whitespace=INDENT,
                                  whitespace_or_comment_or_empty_set=WHITESPACE_OR_COMMENT_OR_EMPTY_SET):
        '''
        Reset everything after `_parse_line_get_next()`, to continue on
        with the next line after having consumed part of it.
        '''
        if line == '':
            return self._parse_line_goto_next(line)
        state = self._state
        if line[:1] not in whitespace_or_comment_or_empty_set:
            state.first_column += 1
            state.last_column += 1
            return line
        line_lstrip_ws = line.lstrip(whitespace)
        if line_lstrip_ws == '':
            return self._parse_line_goto_next(line)
        state.first_lineno = state.last_lineno
        state.indent = state.continuation_indent
        state.at_line_start = at_line_start
        column = state.last_column + 1 + len(line) - len(line_lstrip_ws)
        state.first_column = column
        state.last_column = column
        return line_lstrip_ws


    def _parse_line_continue_last_to_next_significant_token(self, line, at_line_start=False,
                                                            comment_delim=COMMENT_DELIM,
                                                            whitespace=INDENT,
                                                            whitespace_or_comment_or_empty_set=WHITESPACE_OR_COMMENT_OR_EMPTY_SET):
        '''
        Skip ahead to the next significant token (token other than whitespace
        and line comments).  Used in checking ahead after doc comments, tags,
        possible keys, etc. to see whether what follows is potentially valid
        or should trigger an immediate error.
        '''
        state = self._state
        if line[:1] not in whitespace_or_comment_or_empty_set:
            column = state.last_column + 1
            state.first_column = column
            state.last_column = column
            return line
        line_lstrip_ws = line.lstrip(whitespace)
        if line_lstrip_ws == '':
            line = self._parse_line_goto_next(line_lstrip_ws)
            if line is not None and (line == '' or (line[:1] == comment_delim and line[1:2] != comment_delim)):
                while line is not None and (line == '' or (line[:1] == comment_delim and line[1:2] != comment_delim)):
                    if line == '':
                        line = self._parse_line_goto_next(line)
                    else:
                        line = self._parse_token_line_comment(line)
            return line
        state.first_lineno = state.last_lineno
        state.indent = state.continuation_indent
        state.at_line_start = at_line_start
        column = state.last_column + 1 + len(line) - len(line_lstrip_ws)
        state.first_column = column
        state.last_column = column
        if line_lstrip_ws[:1] == comment_delim and line_lstrip_ws[1:2] != comment_delim:
            line = self._parse_token_line_comment(line_lstrip_ws)
            if line is not None and (line == '' or (line[:1] == comment_delim and line[1:2] != comment_delim)):
                while line is not None and (line == '' or (line[:1] == comment_delim and line[1:2] != comment_delim)):
                    if line == '':
                        line = self._parse_line_goto_next(line)
                    else:
                        line = self._parse_token_line_comment(line)
            return line
        return line_lstrip_ws


    def _check_bidi_rtl(self):
        if self._bidi_rtl_last_scalar_last_lineno == self._state.first_lineno and self._bidi_rtl_re.search(self._bidi_rtl_last_scalar_last_line):
            raise erring.ParseError('Cannot start a scalar object or comment on a line with a preceding object whose last line contains right-to-left code points', self._state)


    def _parse_token_assign_key_val_invalid(self, line,
                                            assign_key_val=ASSIGN_KEY_VAL):
        '''
        Raise an informative error for a misplaced "=".
        '''
        raise erring.ParseError('Misplaced "{0}"; in non-inline syntax, it must follow a key on the same line, while in inline syntax, it cannot be further than the start of the next line'.format(assign_key_val), self._state)


    def _parse_token_open_noninline_list(self, line,
                                         open_noninline_list=OPEN_NONINLINE_LIST,
                                         path_separator=PATH_SEPARATOR):
        '''
        Open a non-inline list, or start a key path that has a list as its
        first element.
        '''
        next_code_point = line[1:2]
        if next_code_point == open_noninline_list:
            raise erring.ParseError('Invalid double list opening "{0}"'.format(line[:2]), self._state)
        if next_code_point == path_separator:
            return self._parse_token_unquoted_string_or_key_path(line)
        self._ast.open_noninline_list()
        return self._parse_line_start_last(self._state.indent + '\x20' + line[1:])


    def _parse_token_start_inline_dict(self, line):
        '''
        Start an inline dict.
        '''
        self._ast.start_inline_dict()
        return self._parse_line_continue_last(line[1:])


    def _parse_token_end_inline_dict(self, line):
        '''
        End an inline dict.
        '''
        self._ast.end_inline_dict()
        return self._parse_line_continue_last(line[1:])


    def _parse_token_start_inline_list(self, line):
        '''
        Start an inline list.
        '''
        self._ast.start_inline_list()
        return self._parse_line_continue_last(line[1:])


    def _parse_token_end_inline_list(self, line):
        '''
        End an inline list.
        '''
        self._ast.end_inline_list()
        return self._parse_line_continue_last(line[1:])


    def _parse_token_start_tag(self, line):
        '''
        Start a tag.
        '''
        self._ast.start_tag()
        return self._parse_line_continue_last(line[1:])


    def _parse_token_end_tag(self, line, end_tag_with_suffix=END_TAG_WITH_SUFFIX):
        '''
        End a tag.
        '''
        if line[:2] != end_tag_with_suffix:
            raise erring.ParseError('Invalid end tag delimiter', self._state)
        # Account for end tag suffix
        self._state.last_column += 1
        self._ast.end_tag()
        # Account for end tag suffix with `[2:]`
        return self._parse_line_continue_last(line[2:])


    def _parse_token_inline_element_separator(self, line):
        '''
        Parse an element separator in a dict or list.
        '''
        self._ast.open_inline_collection()
        return self._parse_line_continue_last(line[1:])


    def _parse_delim_inline(self, name, delim, line, whitespace=INDENT,
                            unicode_whitespace_set=UNICODE_WHITESPACE_SET):
        '''
        Find the closing delimiter for an inline quoted string or doc comment.
        '''
        state = self._state
        closing_delim_re, group = self._closing_delim_re_dict[delim]
        m = closing_delim_re.search(line)
        if m is not None:
            content = line[:m.start(group)]
            line = line[m.end(group):]
            state.last_column += 2*len(delim) - 1 + len(content)
            return ([content], content, line)
        content_lines = []
        content_lines.append(line)
        indent = state.indent
        line = self._parse_line_get_next(line)
        if line is None:
            raise erring.ParseError('Unterminated {0}'.format(name), state)
        line_lstrip_ws = line.lstrip(whitespace)
        continuation_indent = line[:len(line)-len(line_lstrip_ws)]
        state.continuation_indent = continuation_indent
        if not continuation_indent.startswith(indent):
            raise erring.IndentationError(state)
        line = line_lstrip_ws
        while True:
            if line == '':
                raise erring.ParseError('Unterminated {0}'.format(name), state)
            elif line[0] in unicode_whitespace_set:
                state.last_column += len(continuation_indent)
                if line[0] in whitespace:
                    raise erring.IndentationError(state)
                else:
                    raise erring.ParseError('A Unicode whitespace code point was found where a wrapped line was expected to start', state)
            if delim in line:
                m = closing_delim_re.search(line)
                if m is not None:
                    line_content = line[:m.start(group)]
                    line = line[m.end(group):]
                    content_lines.append(line_content)
                    state.last_column += len(continuation_indent) + m.end(group) - 1
                    break
            content_lines.append(line)
            line = self._parse_line_get_next(line)
            if line is None:
                raise erring.ParseError('Unterminated {0}'.format(name), state)
            if not line.startswith(continuation_indent):
                if line.lstrip(whitespace) == '':
                    raise erring.ParseError('Unterminated {0}'.format(name), state)
                else:
                    raise erring.IndentationError(state)
            line = line[len(continuation_indent):]
        return (content_lines, self._unwrap_inline_string(content_lines), line)


    def _parse_token_line_comment(self, line, comment_delim=COMMENT_DELIM):
        '''
        Parse a line comment.  This is used in `_parse_token_comment()` and
        `_parse_line_continue_last_to_next_significant_token()` to ensure
        uniform handling.  No checking is done for `#` followed by `#`, since
        this function is only ever called with valid line comments.  This
        function receives the line with the leading `#` still intact.
        '''
        self._state.line_comments = True
        return self._parse_line_goto_next('')


    def _parse_token_comment_delim(self, line, comment_delim=COMMENT_DELIM,
                                   max_delim_length=MAX_DELIM_LENGTH,
                                   ScalarNode=ScalarNode,
                                   invalid_next_token_set=DOC_COMMENT_INVALID_NEXT_TOKEN_SET,
                                   block_prefix=BLOCK_PREFIX):
        '''
        Parse inline comments.
        '''
        if self._bidi_rtl:
            self._check_bidi_rtl()
        line_strip_delim = line.lstrip(comment_delim)
        len_delim = len(line) - len(line_strip_delim)
        if len_delim == 1:
            return self._parse_token_line_comment(line)
        if len_delim == 2:
            raise erring.ParseError('Invalid comment start "{0}"; use "{1}" for a line comment, or "{3}<comment>{3}" for a doc comment'.format(comment_delim*2, comment_delim, comment_delim*3), state)
        state = self._state
        if state.in_tag:
            raise erring.ParseError('Doc comments are not allowed in tags', state)
        if len_delim % 3 != 0 or len_delim > max_delim_length:
            raise erring.ParseError('Doc comment delims must have lengths that are multiples of 3 and are no longer than {0} characters'.format(max_delim_length), state)
        delim = line[:len_delim]
        content_lines, content, line = self._parse_delim_inline('doc comment', delim, line_strip_delim)
        node = ScalarNode(state, delim=delim, block=False, implicit_type = 'doc_comment')
        if self._full_ast:
            node.raw_val = content_lines
        node.final_val = content
        node.resolved = True
        state.next_doc_comment = node
        if self._bidi_rtl:
            self._bidi_rtl_last_scalar_last_line = content_lines[-1]
            self._bidi_rtl_last_scalar_last_lineno = node.last_lineno
        line = self._parse_line_continue_last_to_next_significant_token(line)
        if not node.inline and node.at_line_start and node.last_lineno == state.first_lineno:
            raise erring.ParseError('In non-inline mode, doc comments that start a line cannot be followed immediately by data', node)
        if line is not None and line[:1] in invalid_next_token_set and not (line[:1] == block_prefix and line[1:2] != comment_delim):
            raise erring.ParseError('Doc comment was never applied to an object', node, state)
        return line


    def _scalar_node_lookahead_append(self, node, line,
                                      whitespace=INDENT,
                                      assign_key_val=ASSIGN_KEY_VAL,
                                      scalar_valid_next_token_current_line_set=SCALAR_VALID_NEXT_TOKEN_CURRENT_LINE_SET):
        '''
        Look ahead after a scalar node for a following "=" that would cause
        it to be treated as a key.  Also check for invalid following tokens
        on the line where the scalar ends, to provide more informative error
        messages than would be possible otherwise.  Append the node to the
        AST based on what the lookahead reveals.
        '''
        state = self._state
        line_lstrip_ws = line.lstrip(whitespace)
        if line_lstrip_ws == '':
            if not state.inline:
                self._ast.append_scalar_val(node)
                return self._parse_line_goto_next(line)
            line = self._parse_line_goto_next(line)
            if line is None:
                self._ast.append_scalar_val(node)
                return line
            if line[:1] == assign_key_val:
                if not state.indent.startswith(state.inline_indent):
                    raise erring.IndentationError(state)
                self._ast.append_scalar_key(node)
                state.last_column += 1
                return self._parse_line_continue_last(line[1:])
            self._ast.append_scalar_val(node)
            return line
        if line_lstrip_ws[:1] == assign_key_val:
            self._ast.append_scalar_key(node)
            state.last_column += 1 + len(line) - len(line_lstrip_ws)
            return self._parse_line_continue_last(line_lstrip_ws[1:])
        if line_lstrip_ws[:1] not in scalar_valid_next_token_current_line_set:
            raise erring.ParseError('Unexpected token after end of scalar object', state)
        self._ast.append_scalar_val(node)
        state.last_column += len(line) - len(line_lstrip_ws)
        return self._parse_line_continue_last(line_lstrip_ws)


    def _parse_token_literal_string_delim(self, line,
                                          max_delim_length=MAX_DELIM_LENGTH,
                                          ScalarNode=ScalarNode):
        '''
        Parse inline literal string.
        '''
        if self._bidi_rtl:
            self._check_bidi_rtl()
        state = self._state
        line_strip_delim = line.lstrip(line[0])
        len_delim = len(line) - len(line_strip_delim)
        if len_delim > 3 and (len_delim % 3 != 0 or len_delim > max_delim_length):
            raise erring.ParseError('Literal string delims must have lengths of 1 or 2, or multiples of 3 that are no longer than {0} characters'.format(max_delim_length), state)
        delim = line[:len_delim]
        content_lines, content, line = self._parse_delim_inline('literal string', delim, line_strip_delim)
        node = ScalarNode(state, delim=delim, block=False, implicit_type = 'literal_string')
        if self._full_ast:
            node.raw_val = content_lines
        node.final_val = content
        node.resolved = True
        if self._bidi_rtl:
            self._bidi_rtl_last_scalar_last_line = content_lines[-1]
            self._bidi_rtl_last_scalar_last_lineno = node.last_lineno
        return self._scalar_node_lookahead_append(node, line)


    def _parse_token_escaped_string(self, line,
                                    max_delim_length=MAX_DELIM_LENGTH,
                                    ScalarNode=ScalarNode):
        '''
        Parse inline escaped string (single or double quote).
        '''
        if self._bidi_rtl:
            self._check_bidi_rtl()
        state = self._state
        line_strip_delim = line.lstrip(line[0])
        len_delim = len(line) - len(line_strip_delim)
        if len_delim == 2:
            delim = line[0]
            content_lines = ['']
            content = ''
            line = line[2:]
            state.last_column += 1
        else:
            if len_delim > 3 and (len_delim % 3 != 0 or len_delim > max_delim_length):
                raise erring.ParseError('Escaped string delims must have lengths of 1 or 2, or multiples of 3 that are no longer than {0} characters'.format(max_delim_length), state)
            delim = line[:len_delim]
            content_lines, content, line = self._parse_delim_inline('escaped string', delim, line_strip_delim)
        node = ScalarNode(state, delim=delim, block=False, implicit_type = 'escaped_string')
        if self._full_ast:
            node.raw_val = content_lines
        if '\\' not in content:
            content_esc = content
        else:
            try:
                content_esc = self.unescape_unicode(content)
            except Exception as e:
                raise erring.ParseError('Failed to unescape escaped string:\n  {0}'.format(e), node)
        node.final_val = content_esc
        node.resolved = True
        if self._bidi_rtl:
            self._bidi_rtl_last_scalar_last_line = content_lines[-1]
            self._bidi_rtl_last_scalar_last_lineno = node.last_lineno
        return self._scalar_node_lookahead_append(node, line)


    def _parse_token_block_prefix(self, line,
                                  max_delim_length=MAX_DELIM_LENGTH,
                                  ScalarNode=ScalarNode,
                                  whitespace=INDENT,
                                  unicode_whitespace_set=UNICODE_WHITESPACE_SET,
                                  block_prefix=BLOCK_PREFIX,
                                  block_suffix=BLOCK_SUFFIX,
                                  block_delim_set=BLOCK_DELIM_SET,
                                  comment_delim=COMMENT_DELIM,
                                  escaped_string_doublequote_delim=ESCAPED_STRING_DOUBLEQUOTE_DELIM,
                                  escaped_string_singlequote_delim=ESCAPED_STRING_SINGLEQUOTE_DELIM,
                                  literal_string_delim=LITERAL_STRING_DELIM,
                                  newline=NEWLINE):
        '''
        Parse a block quoted string or doc comment.
        '''
        if self._bidi_rtl:
            self._check_bidi_rtl()
        state = self._state
        delim_code_point = line[1:2]
        if delim_code_point not in block_delim_set:
            raise erring.ParseError('Invalid block delimiter', state)
        line_strip_delim = line[1:].lstrip(delim_code_point)
        # -1 for `|`
        len_delim = len(line) - len(line_strip_delim) - 1
        if len_delim < 3 or len_delim % 3 != 0 or len_delim > max_delim_length:
            raise erring.ParseError('Block delims must have lengths that are multiples of 3 that are no longer than {0} characters'.format(max_delim_length), state)
        if line_strip_delim.lstrip(whitespace) != '':
            state.last_column += len_delim
            raise erring.ParseError('An opening block delim must not be followed by anything; block content does not start until the next line', state)
        delim = delim_code_point*len_delim
        closing_delim_re, group = self._closing_delim_re_dict[delim]
        end_block_delim = block_prefix + delim + block_suffix
        content_lines = []
        indent = state.indent
        while True:
            line = self._parse_line_get_next(line)
            if line is None:
                raise erring.ParseError('Unterminated block', state)
            if not line.startswith(indent) and line.lstrip(whitespace) != '':
                raise erring.IndentationError(state)
            if delim in line:
                m = closing_delim_re.search(line)
                if m is not None:
                    line_lstrip_ws = line.lstrip(whitespace)
                    if not line_lstrip_ws.startswith(end_block_delim):
                        raise erring.ParseError('Invalid delim sequence in body of block')
                    continuation_indent = line[:len(line)-len(line_lstrip_ws)]
                    len_continuation_indent = len(continuation_indent)
                    state.continuation_indent = continuation_indent
                    line = line_lstrip_ws[len(end_block_delim):]
                    state.last_column += len_continuation_indent + len(end_block_delim) - 1
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
                                content_lines.append('')
                            else:
                                raise erring.ParseError('Incorrect indentation relative to block delim indentation on line {0}'.format(state.first_lineno+lineno+1), state)
                    break
            content_lines.append(line)
        # Note that there's no need to reset the bidi_rtl state, given the
        # contents of the final delimiter.
        # Modify last line by adding `\n`, then join lines with `\n`, then
        # put last line back to original value, to avoid having to modify the
        # final string by adding an `\n` at the end
        content_lines_dedent[-1] = content_lines_dedent[-1] + newline
        content = newline.join(content_lines_dedent)
        content_lines_dedent[-1] = content_lines_dedent[-1][:-1]
        if delim_code_point == literal_string_delim:
            node = ScalarNode(state, delim=delim, block=True, implicit_type = 'literal_string')
            if self._full_ast:
                node.raw_val = content_lines_dedent
            node.final_val = content
            node.resolved = True
            return self._scalar_node_lookahead_append(node, line)
        if delim_code_point == escaped_string_singlequote_delim or delim_code_point == escaped_string_singlequote_delim:
            node = ScalarNode(state, delim=delim, block=True, implicit_type='escaped_string')
            if self._full_ast:
                node.raw_val = content_lines_dedent
            if '\\' not in content:
                content_esc = content
            else:
                try:
                    content_esc = self.unescape_unicode(content)
                except Exception as e:
                    raise erring.ParseError('Failed to unescape escaped string:\n  {0}'.format(e), node)
            node.final_val = content_esc
            node.resolved = True
            return self._scalar_node_lookahead_append(node, line)
        node = ScalarNode(state, delim=delim, block=True, implicit_type = 'doc_comment')
        if self._full_ast:
            node.raw_val = content_lines_dedent
        node.final_val = content
        node.resolved = True
        state.next_doc_comment = node
        line = self._parse_line_continue_last_to_next_significant_token(line)
        if not node.inline and node.at_line_start and node.last_lineno == state.first_lineno:
            raise erring.ParseError('In non-inline mode, the end of a block doc comment cannot be followed immediately by data', node)
        if line is not None and line[:1] in invalid_next_token_set and not (line[:1] == block_prefix and line[1:2] != comment_delim):
            raise erring.ParseError('Doc comment was never applied to an object', node, state)
        return line


    def _parse_token_number_or_number_unit(self, line, int=int):
        '''
        Parse a number (float, int, etc.) or a number-unit string.
        '''
        # No need to update bidi_rtl, since state cannot be modified by
        # numbers or number-units
        if self._bidi_rtl:
            self._check_bidi_rtl()
        state = self._state
        m = self._number_or_number_unit_re.match(line)
        if m is None:
            raise erring.ParseError('Invalid literal with number-style start')
        group_name =  m.lastgroup
        group_type, group_base = group_name.rsplit('_', 1)
        raw_val = m.group(group_name)
        state.last_column += m.end(group_name) - 1
        line = line[m.end():]
        if group_type == 'number_unit':
            final_val = raw_val
            node = ScalarNode(state, implicit_type='number_unit')
        elif group_type == 'int':
            cleaned_val = raw_val.replace('\x20', '').replace('\t', '').replace('_', '')
            parser = self._type_data['int'].parser
            if group_base == '10':
                final_val = parser(cleaned_val)
            else:
                final_val = parser(cleaned_val, int(group_base))
            node = ScalarNode(state, implicit_type='int', base=group_base)
        elif group_type == 'float':
            cleaned_val = raw_val.replace('\x20', '').replace('\t', '').replace('_', '')
            parser = self._type_data['float'].parser
            if group_base == '10':
                final_val = parser(cleaned_val)
            else:
                final_val = parser.fromhex(cleaned_val)
            node = ScalarNode(state, implicit_type='int', base=int(group_base))
        else:
            raise ValueError
        if self._full_ast:
            node.raw_val = raw_val
        node.final_val = final_val
        node.resolved = True
        return self._scalar_node_lookahead_append(node, line)


    def _parse_token_unquoted_string_or_key_path(self, line,
                                                 whitespace=INDENT,
                                                 ScalarNode=ScalarNode,
                                                 KeyPathNode=KeyPathNode):
        '''
        Parse an unquoted key, a key path, or an unquoted multi-word string.
        '''
        # #### Parts of this may need to lookahead with
        # #### `scalar_valid_next_token_current_line_set` to give better error
        # #### messages
        if self._bidi_rtl:
            self._check_bidi_rtl()
        state = self._state
        m = self._unquoted_string_or_key_path_re.match(line)
        if m is None:
            raise erring.ParseError('Invalid unquoted key, key path, or unquoted string', state)
        if m.lastgroup == 'unquoted_string':
            raw_val = m.group('unquoted_string')
            if '\x20' in raw_val:
                implicit_type = 'unquoted_string'
            else:
                implicit_type = 'unquoted_key'
            state.last_column += len(raw_val) - 1
            line = line[len(raw_val):]
            node = ScalarNode(state, implicit_type=implicit_type)
            if self._full_ast:
                node.raw_val = raw_val
            node.final_val = raw_val
            node.resolved = True
            if self._bidi_rtl:
                self._bidi_rtl_last_scalar_last_line = raw_val
                self._bidi_rtl_last_scalar_last_lineno = node.last_lineno
            if implicit_type == 'unquoted_key':
                return self._scalar_node_lookahead_append(node, line)
            self._ast.append_scalar_val(node)
            return self._parse_line_continue_last(line)
        if m.lastgroup == 'key_path':
            state.last_column += m.end() - 1
            if state.in_tag:
                raise erring.ParseError('Key paths are not allowed in tags', state)
            node = KeyPathNode(state, m.group('key_path'))
            node.resolved = True
            self._ast.append_key_path(node)
            return self._parse_line_continue_last(line[m.end()+2:])
        content_lines = []
        line_rstrip_ws = line.rstrip(whitespace)
        state.last_column += len(line_rstrip_ws) - 1
        # Create the node here to capture current state, then update the
        # node's state later if it wraps over multiple lines
        node = ScalarNode(state, implicit_type='unquoted_string')
        content_lines.append(line_rstrip_ws)
        indent = state.indent
        line = self._parse_line_get_next(line)
        if line is not None:
            line_lstrip_ws = line.lstrip(whitespace)
            continuation_indent = line[:len(line)-len(line_lstrip_ws)]
            if continuation_indent.startswith(indent) and (state.at_line_start or len(continuation_indent) > len(indent)):
                state.continuation_indent = continuation_indent
                while True:
                    m = self._unquoted_string_re.match(line, len(continuation_indent))
                    if m is None:
                        line = self._parse_line_start_last(line)
                        break
                    if m.lastgroup == 'unquoted_string':
                        content_lines.append(line[m.start():m.end()])
                        column = m.end() - 1
                        state.last_column = column
                        node.last_lineno = state.last_lineno
                        node.last_column = column
                        node.continuation_indent = continuation_indent
                        line = self._parse_line_continue_last(line[m.end():])
                        break
                    line_strip_ws = line.strip(whitespace)
                    content_lines.append(line_strip_ws)
                    line = self._parse_line_get_next(line)
                    if line is None:
                        line = self._parse_line_start_last(line)
                        break
                    if not line.startswith(continuation_indent):
                        line = self._parse_line_start_last(line)
                        break
        if self._full_ast:
            node.raw_val = content_lines
        node.final_val = '\x20'.join(content_lines)
        node.resolved = True
        self._ast.append_scalar_val(node)
        return line


    def _parse_token_alias_prefix(self, line):
        raise NotImplementedError


