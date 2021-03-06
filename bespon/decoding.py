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
from .astnodes import ScalarNode, FullScalarNode, CommentNode, FullCommentNode, AliasNode, KeyPathNode, SectionNode

if sys.version_info.major == 2:
    str = unicode




class SourceRange(object):
    '''
    Create tracebacks to a range within a source.
    '''
    def __init__(self, state, first_lineno, first_colno, last_lineno, last_colno):
        self._state = state
        self.first_lineno = first_lineno
        self.first_colno = first_colno
        self.last_lineno = last_lineno
        self.last_colno = last_colno




_context_core_attr = ['_state', 'indent', 'at_line_start', 'inline', 'inline_indent']

_context_node_attr = _context_core_attr + ['external_indent', 'external_at_line_start']

_context_full_core_attr = _context_core_attr + ['first_lineno', 'first_colno', 'last_lineno', 'last_colno']

_context_full_node_attr = _context_full_core_attr + ['external_first_lineno', 'external_first_colno']


class Context(object):
    '''
    Store state of an object for future use.
    '''
    pass


class CommentContext(Context):
    __slots__ = _context_core_attr
    def __init__(self, state):
        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent

    def update(self):
        state = self._state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        return self


class FullCommentContext(Context):
    __slots__ = _context_core_attr
    def __init__(self, state):
        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = state.lineno
        self.first_colno = state.colno
        self.last_lineno = state.last_lineno
        self.last_colno = state.last_colno


class NodeContext(Context):
    __slots__ = _context_node_attr
    def __init__(self, state):
        self._state = state
        self.indent = self.external_indent = state.indent
        self.at_line_start = self.external_at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent

    def update(self):
        state = self._state
        self.indent = self.external_indent = state.indent
        self.at_line_start = self.external_at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        return self

    def copy(self):
        cls = self.__class__
        context = cls.__new__(cls)
        context._state = self._state
        context.indent = context.external_indent = self.indent
        context.at_line_start = context.external_at_line_start = self.at_line_start
        context.inline = self.inline
        context.inline_indent = self.inline_indent
        return context


class FullNodeContext(Context):
    __slots__ = _context_node_attr
    def __init__(self, state):
        self._state = state
        self.indent = self.external_indent = state.indent
        self.at_line_start = self.external_at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = self.external_first_lineno = state.lineno
        self.first_colno = self.external_first_colno = state.colno
        self.last_lineno = state.last_lineno
        self.last_colno = state.last_colno

    @classmethod
    def from_context_and_range(cls, context, first_lineno, first_colno, last_lineno, last_colno):
        obj = cls.__new__(cls)
        obj._state = context._state
        obj.indent = obj.external_indent = context.indent
        obj.at_line_start = obj.external_at_line_start = context.at_line_start
        obj.inline = context.inline
        obj.inline_indent = context.inline_indent
        obj.first_lineno = obj.external_first_lineno = first_lineno
        obj.first_colno = obj.external_first_colno = first_colno
        obj.last_lineno = last_lineno
        obj.last_colno = last_colno
        return obj


class TagContext(Context):
    __slots__ = _context_core_attr + ['external_indent']
    def __init__(self, state):
        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.external_indent = state.external_indent

    def update(self):
        state = self._state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.external_indent = state.external_indent
        return self


class FullTagContext(Context):
    __slots__ = _context_full_core_attr + ['external_indent']
    def __init__(self, state):
        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = state.lineno
        self.first_colno = state.colno
        self.last_lineno = state.last_lineno
        self.last_colno = state.last_colno
        self.external_indent = state.external_indent




class State(object):
    '''
    Keep track of a data source and all associated state.  This includes
    general information about the source, the current location within the
    source, the current parsing context, cached values, and regular
    expressions appropriate for analyzing the source.
    '''
    __slots__ = ['_state',
                 'source_name', 'source_include_depth',
                 'source_initial_nesting_depth', 'source_inline',
                 'source_embedded',
                 'source_lines', 'source_lines_iter',
                 'bom_offset',
                 'source_only_ascii', 'source_only_below_u0590',
                 'indent', 'at_line_start',
                 'inline', 'inline_indent',
                 'lineno', 'colno', 'len_full_line_plus_one',
                 'last_line_comment_lineno',
                 'nesting_depth',
                 'next_cache',
                 'next_tag', 'in_tag', 'start_root_tag', 'end_root_tag',
                 'next_doc_comment', 'next_doc_comment_context',
                 'next_scalar', 'next_scalar_context', 'next_scalar_is_keyable',
                 'data_types',
                 'core_data_types', 'extended_data_types', 'python_data_types',
                 'ast', 'full_ast',
                 'bidi_rtl', 'bidi_rtl_re',
                 'bidi_rtl_last_scalar_last_lineno',
                 'bidi_rtl_last_scalar_last_line',
                 'newline_re', 'unquoted_string_or_key_path_re',
                 'alias_path_re', 'number_re',
                 'escape_unicode', 'unescape_unicode', 'unescape_bytes',
                 'circular_references']
    def __init__(self, decoder, source_raw_string,
                 source_name=None, source_include_depth=0,
                 source_initial_nesting_depth=0,
                 source_embedded=False,
                 indent='', at_line_start=True,
                 inline=False, inline_indent=None,
                 lineno=1, colno=1,
                 full_ast=False,
                 indent_chars=grammar.LIT_GRAMMAR['indent']):
        if not all(x is None or isinstance(x, str) for x in (source_name, inline_indent)):
            raise TypeError
        if not all(isinstance(x, str) for x in (indent,)):
            raise TypeError
        if any(x is not None and x != '' and x.lstrip(indent_chars) for x in (indent, inline_indent)):
            raise ValueError('Invalid indentation characters')
        if not all(isinstance(x, int) and x >= 0 for x in (source_include_depth, source_initial_nesting_depth)):
            if not all(isinstance(x, int) for x in (source_include_depth, source_initial_nesting_depth)):
                raise TypeError
            raise ValueError
        if not all(isinstance(x, int) and x > 0 for x in (lineno, colno)):
            if not all(isinstance(x, int) for x in (lineno, colno)):
                raise TypeError
            raise ValueError
        if not all(x in (True, False) for x in (at_line_start, inline, full_ast, source_embedded)):
            raise TypeError

        # In some cases, data may be derived either from a `State` instance or
        # from an AST node instance.  `_state` provides an attribute common to
        # all of these that allows `state` access.
        self._state = self

        self.source_name = source_name or '<data>'
        self.source_include_depth = source_include_depth
        self.source_initial_nesting_depth = source_initial_nesting_depth
        self.source_inline = inline
        self.source_embedded = source_embedded

        self.indent = indent
        self.at_line_start = at_line_start
        self.inline = inline
        self.inline_indent = inline_indent
        self.lineno = lineno
        self.colno = colno
        self.len_full_line_plus_one = None
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

        self.data_types = decoder._data_types
        self.core_data_types = load_types.CORE_TYPES
        self.extended_data_types = load_types.EXTENDED_TYPES
        self.full_ast = full_ast

        self.newline_re = decoder._newline_re
        self.escape_unicode = decoder._escape_unicode
        self.unescape_unicode = decoder._unescape_unicode
        self.unescape_bytes = decoder._unescape_bytes

        self.circular_references = decoder.circular_references

        self._check_literals_set_code_point_attrs(source_raw_string, decoder)
        self.source_lines = source_raw_string.splitlines()
        self.source_lines_iter = iter(self.source_lines)

        self.ast = Ast(self, decoder.max_nesting_depth, decoder.empty_default)
        if self.full_ast:
            self.ast.source_lines = self.source_lines


    def _traceback_not_valid_literal(self, source_raw_string, index, decoder):
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
            self.colno += index - self.bom_offset
        else:
            self.lineno += newline_count
            self.colno = index - newline_index
        code_point = source_raw_string[index]
        code_point_esc = self.escape_unicode(code_point)
        if decoder.only_ascii_source and not decoder._not_valid_unicode_re.search(source_raw_string):
            raise erring.InvalidLiteralError(self, code_point, code_point_esc, comment='only_ascii_source=True')
        raise erring.InvalidLiteralError(self, code_point, code_point_esc)


    def _check_literals_set_code_point_attrs(self, source_raw_string, decoder,
                                             bom=grammar.LIT_GRAMMAR['bom']):
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
        self.alias_path_re = decoder._alias_path_ascii_re
        self.number_re = decoder._number_re

        if source_raw_string[:1] == bom:
            bom_offset = 1
        else:
            bom_offset = 0
        self.bom_offset = bom_offset

        m_not_valid_ascii = decoder._not_valid_ascii_re.search(source_raw_string, bom_offset)
        if m_not_valid_ascii is None:
            return
        if decoder.only_ascii_source:
            self._traceback_not_valid_literal(source_raw_string, m_not_valid_ascii.start(), decoder)
        self.source_only_ascii = False
        if not decoder.only_ascii_unquoted:
            self.unquoted_string_or_key_path_re = decoder._unquoted_string_or_key_path_below_u0590_re
            self.alias_path_re = decoder._alias_path_below_u0590_re
        m_not_valid_below_u0590 = decoder._not_valid_below_u0590_re.search(source_raw_string, m_not_valid_ascii.start())
        if m_not_valid_below_u0590 is None:
            return
        self.source_only_below_u0590 = False
        if not decoder.only_ascii_unquoted:
            self.unquoted_string_or_key_path_re = decoder._unquoted_string_or_key_path_unicode_re
            self.alias_path_re = decoder._alias_path_unicode_re
        m_bidi_rtl_or_not_valid_unicode = decoder._bidi_rtl_or_not_valid_unicode_re.search(source_raw_string, m_not_valid_below_u0590.start())
        if m_bidi_rtl_or_not_valid_unicode is None:
            return
        if m_bidi_rtl_or_not_valid_unicode.lastgroup == 'not_valid':
            self._traceback_not_valid_literal(source_raw_string, m_bidi_rtl_or_not_valid_unicode.start(), decoder)
        self.bidi_rtl = True
        m_not_valid_unicode = decoder._not_valid_unicode_re.search(source_raw_string, m_bidi_rtl_or_not_valid_unicode.start())
        if m_not_valid_unicode is None:
            return
        self._traceback_not_valid_literal(source_raw_string, m_not_valid_unicode.start(), decoder)


    def source_range_to_loc(self, lineno, colno):
        '''
        Return an object that may be used for creating a traceback to a range
        in the source, starting at the current state location and continuing
        to the designated location.
        '''
        return SourceRange(self, self.lineno, self.colno, lineno, colno)




class BespONDecoder(object):
    '''
    Decode BespON in a string or stream.

    A `Decoder` instance is intended to be static once created.  Each string
    or stream that is decoded has a `State` instance created for it, and all
    mutability is confined within that object.  This allows a single `Decoder`
    instance to be used for multiple, potentially nested, data sources without
    issues due to shared state within the `Decoder` itself.
    '''
    __slots__ = ['only_ascii_source', 'only_ascii_unquoted',
                 'aliases', 'circular_references', 'integers',
                 'custom_parsers', 'custom_types',
                 'max_nesting_depth', 'empty_default',
                 'float_overflow_to_inf',
                 'extended_types', 'python_types',
                 '_data_types',
                 '_escape_unicode',
                 '_unescape', '_unescape_unicode', '_unescape_bytes',
                 '_parse_token', '_parse_scalar_token',
                 '_not_valid_ascii_re', '_not_valid_below_u0590_re',
                 '_not_valid_unicode_re',
                 '_bidi_rtl_re', '_bidi_rtl_or_not_valid_unicode_re',
                 '_newline_re',
                 '_closing_delim_re_dict',
                 '_unquoted_string_or_key_path_ascii_re',
                 '_unquoted_string_or_key_path_below_u0590_re',
                 '_unquoted_string_or_key_path_unicode_re',
                 '_alias_path_ascii_re',
                 '_alias_path_below_u0590_re',
                 '_alias_path_unicode_re',
                 '_number_re',
                 '_reserved_word_types']
    def __init__(self, *args, **kwargs):
        # Process args
        if args:
            raise TypeError('Explicit keyword arguments are required')
        only_ascii_source = kwargs.pop('only_ascii_source', False)
        only_ascii_unquoted = kwargs.pop('only_ascii_unquoted', True)
        aliases = kwargs.pop('aliases', True)
        circular_references = kwargs.pop('circular_references', False)
        integers = kwargs.pop('integers', True)
        max_nesting_depth = kwargs.pop('max_nesting_depth', grammar.PARAMS['max_nesting_depth'])
        empty_default = kwargs.pop('empty_default', None)
        float_overflow_to_inf = kwargs.pop('float_overflow_to_inf', False)
        extended_types = kwargs.pop('extended_types', False)
        python_types = kwargs.pop('python_types', False)
        if any(x not in (True, False) for x in (only_ascii_source, only_ascii_unquoted,
                                                aliases, circular_references,
                                                integers, float_overflow_to_inf,
                                                extended_types, python_types)):
            raise TypeError
        if only_ascii_source and not only_ascii_unquoted:
            raise ValueError('Setting only_ascii_source=True is incompatible with only_ascii_unquoted=False')
        if not isinstance(max_nesting_depth, int):
            raise TypeError('max_nesting_depth must be an integer')
        if max_nesting_depth < 0:
            raise ValueError('max_nesting_depth must be >= 0')
        self.only_ascii_source = only_ascii_source
        self.only_ascii_unquoted = only_ascii_unquoted
        self.aliases = aliases
        self.circular_references = circular_references
        self.integers = integers
        self.max_nesting_depth = max_nesting_depth
        self.empty_default = empty_default
        self.float_overflow_to_inf = float_overflow_to_inf
        self.extended_types = extended_types
        self.python_types = python_types

        custom_parsers = kwargs.pop('custom_parsers', None)
        if custom_parsers is not None and not isinstance(custom_parsers, dict):
            raise TypeError('custom_parsers must be a dict mapping type names to parsing functions')
        custom_types = kwargs.pop('custom_types', None)
        if custom_types is not None:
            if isinstance(custom_types, load_types.LoadType):
                custom_types = [custom_types]
            else:
                if not (isinstance(custom_types, list) or isinstance(custom_types, tuple)):
                    raise TypeError('custom_types must be a list or tuple of LoadType objects')
                if not all(isinstance(v, load_types.LoadType) for v in custom_types):
                    raise ValueError('custom_types must be a sequence of LoadType objects')
            if any(x.name in load_types.ALL_TYPES for x in custom_types):
                raise ValueError('Cannot override built-in type definitions; use custom_parsers to override parsing for built-in types')
        self.custom_parsers = custom_parsers
        self.custom_types = custom_types

        if kwargs:
            raise TypeError('Unexpected keyword argument(s) {0}'.format(', '.join('"{0}"'.format(k) for k in kwargs)))


        # Parser and type info access
        # Copies of all LoadType objects are used, so that modification won't
        # affect other decoder instances.
        data_types = {}
        data_types.update({k: v.copy() for k, v in load_types.CORE_TYPES.items()})
        if self.extended_types:
            data_types.update({k: v.copy() for k, v in load_types.EXTENDED_TYPES.items()})
        if self.python_types:
            data_types.update({k: v.copy() for k, v in load_types.PYTHON_TYPES.items()})
        if custom_parsers is not None:
            if not all(k in data_types for k in custom_parsers):
                raise ValueError('Unknown or disabled data type(s) {0}'.format(', '.join(k for k in custom_parsers if k not in data_types)))
            for k, v in custom_parsers.items():
                data_types[k].parser = v
        if custom_types is not None:
            for x in custom_types:
                data_types[x.name] = x
        self._data_types = data_types


        # Create escape and unescape functions
        self._escape_unicode = escape.basic_unicode_escape
        self._unescape = escape.Unescape()
        self._unescape_unicode = self._unescape.unescape_unicode
        self._unescape_bytes = self._unescape.unescape_bytes


        # Create dict of token-based parsing functions.
        #
        # Also create a dict containing only the scalar-related subset of
        # parsing functions.  This is used in parsing sections.
        #
        # The default behavior is to parse for an unquoted string or key path.
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
                           'escaped_string_singlequote_delim': self._parse_token_escaped_string_delim,
                           'escaped_string_doublequote_delim': self._parse_token_escaped_string_delim,
                           'literal_string_delim': self._parse_token_literal_string_delim,
                           'alias_prefix': self._parse_token_alias_prefix}
        for token_name, func in token_functions.items():
            token = grammar.LIT_GRAMMAR[token_name]
            parse_token[token] = func
            if 'string' in token_name:
                parse_scalar_token[token] = func
        for c in grammar.LIT_GRAMMAR['number_start']:
            parse_token[c] = self._parse_token_number
            parse_scalar_token[c] = self._parse_token_number
        for c in grammar.LIT_GRAMMAR['indent']:
            parse_token[c] = self._parse_token_whitespace
        parse_token[''] = self._parse_line_goto_next
        self._parse_token = parse_token
        self._parse_scalar_token = parse_scalar_token


        # Assemble regular expressions
        self._not_valid_ascii_re = re.compile(grammar.RE_GRAMMAR['not_valid_ascii'])
        self._not_valid_below_u0590_re = re.compile(grammar.RE_GRAMMAR['not_valid_below_u0590'])
        self._not_valid_unicode_re = re.compile(grammar.RE_GRAMMAR['not_valid_unicode'])
        self._bidi_rtl_re = re.compile(grammar.RE_GRAMMAR['bidi_rtl'])
        self._bidi_rtl_or_not_valid_unicode_re = re.compile(r'(?P<not_valid>{0})|(?P<bidi_rtl>{1})|'.format(grammar.RE_GRAMMAR['not_valid_unicode'],
                                                                                                            grammar.RE_GRAMMAR['bidi_rtl']))

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
        self._closing_delim_re_dict = tooling.keydefaultdict(lambda delim: grammar.gen_closing_delim_re(delim))

        self._unquoted_string_or_key_path_ascii_re = re.compile(grammar.RE_GRAMMAR['unquoted_string_or_key_path_named_groups_ascii'])
        self._unquoted_string_or_key_path_below_u0590_re = re.compile(grammar.RE_GRAMMAR['unquoted_string_or_key_path_named_groups_below_u0590'])
        self._unquoted_string_or_key_path_unicode_re = re.compile(grammar.RE_GRAMMAR['unquoted_string_or_key_path_named_groups_unicode'])
        self._alias_path_ascii_re = re.compile(grammar.RE_GRAMMAR['alias_path_ascii'])
        self._alias_path_below_u0590_re = re.compile(grammar.RE_GRAMMAR['alias_path_below_u0590'])
        self._alias_path_unicode_re = re.compile(grammar.RE_GRAMMAR['alias_path_unicode'])

        if not self.extended_types:
            self._number_re = re.compile(grammar.RE_GRAMMAR['number_named_groups'])
        else:
            self._number_re = re.compile(grammar.RE_GRAMMAR['extended_number_named_groups'])

        # Dict for looking up types of valid reserved words
        self._reserved_word_types = {grammar.LIT_GRAMMAR['none_type']: 'none',
                                     grammar.LIT_GRAMMAR['bool_true']: 'bool',
                                     grammar.LIT_GRAMMAR['bool_false']: 'bool',
                                     grammar.LIT_GRAMMAR['infinity_word']: 'float',
                                     grammar.LIT_GRAMMAR['not_a_number_word']: 'float'}
        if self.extended_types:
            self._reserved_word_types[grammar.LIT_GRAMMAR['infinity_word']+grammar.LIT_GRAMMAR['imaginary_unit']] = 'complex'
            self._reserved_word_types[grammar.LIT_GRAMMAR['not_a_number_word']+grammar.LIT_GRAMMAR['imaginary_unit']] = 'complex'


    @staticmethod
    def _unwrap_inline_string(s_list, unicode_whitespace_set=grammar.LIT_GRAMMAR['unicode_whitespace_set']):
        '''
        Unwrap an inline string.

        Any line that ends with a newline preceded by Unicode whitespace has
        the newline stripped.  Otherwise, a trailing newline is replace by a
        space.  The last line will not have a newline due to the ending
        delimiter.  The list of lines received already has the newlines
        stripped.

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


    @staticmethod
    def _as_unicode_string(unicode_string_or_bytes):
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


    def _parse_lines(self, state,
                     whitespace=grammar.LIT_GRAMMAR['indent'], whitespace_set=grammar.LIT_GRAMMAR['whitespace_set'],
                     len=len):
        '''
        Process lines from source into abstract syntax tree (AST).  Then
        process the AST into standard Python objects.
        '''
        source_lines_iter = state.source_lines_iter
        # Extract the first line of the source, strip an optional BOM,
        # and set initial state attributes
        line = next(source_lines_iter, '')
        if state.bom_offset == 1:
            # Don't count BOM toward line length, because that would throw off
            # column calculations for subsequent lines
            line = line[1:]
        len_line = len(line)
        state.len_full_line_plus_one = len_line + 1
        if line[:1] in whitespace_set:
            line_lstrip_ws = line.lstrip(whitespace)
            state.indent = line[:len_line-len(line_lstrip_ws)]
            line = line_lstrip_ws

        parse_token = self._parse_token
        while line is not None:
            line = parse_token[line[:1]](line, state)

        state.ast.finalize()


    def _check_bidi_rtl(self, state):
        '''
        Determine if a new scalar can start on the current line, based
        on whether there is a preceding scalar on the same line that contains
        right-to-left code points on that line.
        '''
        if state.bidi_rtl_last_scalar_last_lineno == state.lineno and state.bidi_rtl_re.search(state.bidi_rtl_last_scalar_last_line):
            raise erring.ParseError('Cannot start a scalar object or comment on a line with a preceding object whose last line contains right-to-left code points', state)


    def _parse_line_goto_next(self, line, state,
                              whitespace=grammar.LIT_GRAMMAR['indent'], whitespace_set=grammar.LIT_GRAMMAR['whitespace_set'],
                              next=next, len=len):
        '''
        Go to next line.  Used when parsing completes on a line, and no
        additional parsing is needed for that line.

        The `line` argument is needed so that this can be used in the
        `_parse_token` dict of functions as the value for the empty string
        key.  When the function is used as part of other parsing
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
        state.lineno += 1
        if line is None:
            state.len_full_line_plus_one = 1
            state.indent = ''
            state.at_line_start = True
            state.colno = 1
            return line
        if line[:1] not in whitespace_set:
            state.len_full_line_plus_one = len(line) + 1
            state.indent = ''
            state.at_line_start = True
            return line
        len_line = len(line)
        line_lstrip_ws = line.lstrip(whitespace)
        len_line_lstrip_ws = len(line_lstrip_ws)
        state.len_full_line_plus_one = len_line + 1
        state.indent = line[:len_line-len_line_lstrip_ws]
        state.at_line_start = True
        return line_lstrip_ws


    def _parse_token_whitespace(self, line, state, whitespace=grammar.LIT_GRAMMAR['indent']):
        '''
        Remove non-indentation whitespace.
        '''
        return line.lstrip(whitespace)


    def _parse_token_assign_key_val(self, line, state, len=len):
        '''
        Assign a cached key or key path.
        '''
        state.colno = state.len_full_line_plus_one - len(line)
        if state.next_scalar is None:
            raise erring.ParseError('Missing key cannot be assigned', state)
        state.ast.append_scalar_key()
        state.at_line_start = False
        return line[1:]


    def _parse_token_open_indentation_list(self, line, state,
                                           whitespace=grammar.LIT_GRAMMAR['indent'],
                                           open_indentation_list=grammar.LIT_GRAMMAR['open_indentation_list'],
                                           path_separator=grammar.LIT_GRAMMAR['path_separator'],
                                           len=len):
        '''
        Open a list in indentation-style syntax.
        '''
        # Before opening the list, resolve any cached scalar.  After opening
        # the list, check for other cached values.  This must be done
        # afterward, because opening the list could involve creating a new
        # list, which would consume a doc comment and tag.
        state.colno = state.len_full_line_plus_one - len(line)
        if state.next_scalar is not None:
            state.ast.append_scalar_val()
        state.ast.open_indentation_list()
        if state.next_cache:
            raise erring.ParseError('Cannot open a list-like object when a prior object has not been resolved', state, unresolved_cache=True)
        line_less_open = line[1:]
        line_less_open_lstrip_ws = line_less_open.lstrip(whitespace)
        len_extra_ws = len(line_less_open) - len(line_less_open_lstrip_ws)
        # Prevent a following `*` from starting a new list.  A `*` in any
        # other position would trigger an error due to `_at_line_start`.
        # This check could be done elsewhere by comparing line numbers,
        # but it is simplest and most direct here.
        if line_less_open_lstrip_ws[:1] == open_indentation_list:
            state.colno += 1 + len_extra_ws
            raise erring.ParseError('Cannot open a list-like object and then create a new list-like object on the same line in indentation-style syntax', state)
        if line_less_open[:1] != '\t' or state.indent[-1:] not in ('', '\t'):
            state.indent += '\x20' + line_less_open[:len_extra_ws]
        else:
            state.indent += line_less_open[:len_extra_ws]
        return line_less_open_lstrip_ws


    def _parse_token_start_inline_dict(self, line, state, len=len):
        '''
        Start an inline dict.
        '''
        state.colno = state.len_full_line_plus_one - len(line)
        if state.next_scalar is not None:
            raise erring.ParseError('Cannot start a dict-like object when a prior scalar has not yet been resolved', state, unresolved_cache=True)
        state.ast.start_inline_dict()
        state.at_line_start = False
        return line[1:]


    def _parse_token_end_inline_dict(self, line, state, len=len):
        '''
        End an inline dict.
        '''
        state.colno = state.len_full_line_plus_one - len(line)
        if state.next_scalar is not None:
            state.ast.append_scalar_val()
        elif state.next_cache:
            raise erring.ParseError('Cannot end a dict-like object when a prior object has not yet been resolved', state, unresolved_cache=True)
        state.ast.end_inline_dict()
        state.at_line_start = False
        return line[1:]


    def _parse_token_start_inline_list(self, line, state, len=len):
        '''
        Start an inline list.
        '''
        state.colno = state.len_full_line_plus_one - len(line)
        if state.next_scalar is not None:
            raise erring.ParseError('Cannot start a list-like object when a prior scalar has not yet been resolved', state, unresolved_cache=True)
        state.ast.start_inline_list()
        state.at_line_start = False
        return line[1:]


    def _parse_token_end_inline_list(self, line, state, len=len):
        '''
        End an inline list.
        '''
        state.colno = state.len_full_line_plus_one - len(line)
        if state.next_scalar is not None:
            state.ast.append_scalar_val()
        elif state.next_cache:
            raise erring.ParseError('Cannot end a list-like object when a prior object has not yet been resolved', state, unresolved_cache=True)
        state.ast.end_inline_list()
        state.at_line_start = False
        return line[1:]


    def _parse_token_start_tag(self, line, state, len=len):
        '''
        Start a tag.
        '''
        state.colno = state.len_full_line_plus_one - len(line)
        if state.next_scalar is not None:
            state.ast.append_scalar_val()
        elif state.next_tag is not None:
            tag_node = state.next_tag
            if not state.inline and 'dict' in tag_node.compatible_implicit_types:
                if tag_node.type is None:
                    raise erring.ParseError('Cannot start a tag when a prior tag has not yet been resolved; tags for dict-like objects in indentation-style syntax require an explicit type', tag_node, self)
                state.ast.start_explicit_indentation_dict()
            else:
                raise erring.ParseError('Cannot start a tag when a prior tag has not yet been resolved', state, unresolved_cache=True)
        state.ast.start_tag()
        state.at_line_start = False
        return line[1:]


    def _parse_token_end_tag(self, line, state,
                             end_tag_with_suffix=grammar.LIT_GRAMMAR['end_tag_with_suffix'],
                             whitespace=grammar.LIT_GRAMMAR['indent'],
                             whitespace_set=grammar.LIT_GRAMMAR['whitespace_set'],
                             comment_delim=grammar.LIT_GRAMMAR['comment_delim'],
                             start_inline_dict=grammar.LIT_GRAMMAR['start_inline_dict'],
                             block_prefix=grammar.LIT_GRAMMAR['block_prefix'],
                             len=len):
        '''
        End a tag.
        '''
        state.colno = state.len_full_line_plus_one - len(line)
        if line[:2] != end_tag_with_suffix:
            raise erring.ParseError('Invalid end tag delimiter', state)
        # No need to check `state.next_cache`, since doc comments and tags
        # aren't possible inside tags.
        if state.next_scalar is not None:
            state.ast.append_scalar_val()
        state.ast.end_tag()
        # Account for end tag suffix with `[2:]`
        state.at_line_start = False
        return line[2:]


    def _parse_token_inline_element_separator(self, line, state, len=len):
        '''
        Parse an element separator in a dict or list.
        '''
        state.colno = state.len_full_line_plus_one - len(line)
        if state.next_scalar is not None:
            state.ast.append_scalar_val()
        elif state.next_cache:
            raise erring.ParseError('Cannot open a collection object when a prior object has not yet been resolved', state, unresolved_cache=True)
        state.ast.open_inline_collection()
        state.at_line_start = False
        return line[1:]


    def _parse_delim_inline(self, name, delim, line, state, section=False,
                            whitespace=grammar.LIT_GRAMMAR['indent'],
                            unicode_whitespace_set=grammar.LIT_GRAMMAR['unicode_whitespace_set'],
                            next=next, len=len):
        '''
        Find the closing delimiter for an inline quoted string or doc comment.
        '''
        closing_delim_re, group = self._closing_delim_re_dict[delim]
        m = closing_delim_re.search(line)
        if m is not None:
            content = line[:m.start(group)]
            m_end = m.end(group)
            line = line[m_end:]
            return ([content], None, content, state.lineno, state.colno + len(delim) + m_end - 1, line)
        if section:
            raise erring.ParseError('Unterminated {0} (section strings must start and end on the same line)'.format(name), state)
        content_lines = [line]
        indent = state.indent
        line = next(state.source_lines_iter, None)
        last_lineno = state.lineno + 1
        if line is None:
            raise erring.ParseError('Unterminated {0} (reached end of data)'.format(name), state)
        len_full_line = len(line)
        line_lstrip_ws = line.lstrip(whitespace)
        continuation_indent = line[:len_full_line-len(line_lstrip_ws)]
        len_continuation_indent = len(continuation_indent)
        if not continuation_indent.startswith(indent):
            raise erring.IndentationError(state.source_range_to_loc(last_lineno, len_full_line + 1 - len_continuation_indent))
        line = line_lstrip_ws
        while True:
            if line == '':
                raise erring.ParseError('Unterminated {0} (inline quoted strings cannot contain empty lines)'.format(name), state.source_range_to_loc(last_lineno, len_full_line + 1))
            if line[0] in unicode_whitespace_set:
                if line[0] in whitespace:
                    raise erring.IndentationError(state.source_range_to_loc(last_lineno, len_full_line + 1 - len(line)))
                raise erring.ParseError('A Unicode whitespace code point "{0}" was found where a wrapped line was expected to start'.format(self._escape_unicode(line[0])), state.source_range_to_loc(last_lineno, len_full_line + 1 - len(line)))
            if delim in line:
                m = closing_delim_re.search(line)
                if m is not None:
                    line_content = line[:m.start(group)]
                    m_end = m.end(group)
                    line = line[m_end:]
                    content_lines.append(line_content)
                    last_colno = len_continuation_indent + m_end
                    break
            content_lines.append(line)
            line = next(state.source_lines_iter, None)
            last_lineno += 1
            if line is None:
                raise erring.ParseError('Unterminated {0} (reached end of data)'.format(name), state.source_range_to_loc(last_lineno, 1))
            len_full_line = len(line)
            if not line.startswith(continuation_indent):
                if line.lstrip(whitespace) == '':
                    raise erring.ParseError('Unterminated {0} (inline delimited strings cannot contain empty lines)'.format(name), state.source_range_to_loc(last_lineno, len_full_line + 1))
                raise erring.IndentationError(state.source_range_to_loc(last_lineno, len_full_line + 1 - len(line.lstrip(whitespace))))
            line = line[len_continuation_indent:]
        state.len_full_line_plus_one = len_full_line + 1
        state.lineno = last_lineno
        return (content_lines, continuation_indent, self._unwrap_inline_string(content_lines), last_lineno, last_colno, line)


    def _parse_token_line_comment(self, line, state,
                                  comment_delim=grammar.LIT_GRAMMAR['comment_delim'],
                                  FullCommentNode=FullCommentNode,
                                  len=len):
        '''
        Parse a line comment.  This is used in `_parse_token_comment()`.
        No checking is done for `#` followed by `#`, since this function is
        only ever called with valid line comments.  This function receives
        the line with the leading `#` still intact.
        '''
        state.last_line_comment_lineno = state.lineno
        if state.full_ast:
            state.colno = state.len_full_line_plus_one - len(line)
            node = FullCommentNode(state, state.lineno, state.colno,
                                   state.lineno, state.len_full_line_plus_one - 1,
                                   'line_comment', delim=comment_delim)
            node.raw_val = node.final_val = line[1:]
            state.ast.scalar_nodes.append(node)
            state.ast.line_comments.append(node)
        return self._parse_line_goto_next('', state)


    def _parse_token_comment_delim(self, line, state,
                                   comment_delim=grammar.LIT_GRAMMAR['comment_delim'],
                                   max_delim_length=grammar.PARAMS['max_delim_length'],
                                   CommentNode=CommentNode,
                                   FullCommentNode=FullCommentNode,
                                   len=len):
        '''
        Parse inline comments.
        '''
        len_line = len(line)
        state.colno = first_colno = state.len_full_line_plus_one - len_line
        first_lineno = state.lineno
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        line_lstrip_delim = line.lstrip(comment_delim)
        len_delim = len_line - len(line_lstrip_delim)
        if len_delim == 1:
            return self._parse_token_line_comment(line, state)
        if len_delim % 3 != 0 or len_delim > max_delim_length:
            if len_delim == 2:
                raise erring.ParseError('Invalid comment start "{0}"; use "{1}" for a line comment, or "{2}<comment>{2}" for an inline doc comment'.format(comment_delim*2, comment_delim, comment_delim*3), state)
            raise erring.ParseError('Doc comment delims must have lengths that are multiples of 3 and are no longer than {0} characters'.format(max_delim_length), state)
        if state.in_tag:
            raise erring.ParseError('Doc comments are not allowed in tags', state)
        if state.next_scalar is not None:
            if state.inline or not state.at_line_start:
                raise erring.ParseError('Cannot start a doc comment when a prior scalar has not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        elif state.next_tag is not None:
            tag_node = state.next_tag
            if not state.inline and 'dict' in tag_node.compatible_implicit_types:
                if tag_node.type is None:
                    raise erring.ParseError('Cannot start a doc comment when a prior tag has not yet been resolved; tags for dict-like objects in indentation-style syntax require an explicit type', tag_node, self)
                state.ast.start_explicit_indentation_dict()
            else:
                raise erring.ParseError('Cannot start a doc comment when a prior tag has not yet been resolved', state, unresolved_cache=True)
        elif state.next_cache:
            raise erring.ParseError('Cannot start a doc comment when a prior object has not yet been resolved', state, unresolved_cache=True)
        delim = line[:len_delim]
        content_lines, continuation_indent, content, last_lineno, last_colno, line = self._parse_delim_inline('doc comment', delim, line_lstrip_delim, state)
        if not state.full_ast:
            node = CommentNode(state, first_lineno, first_colno, last_lineno, last_colno,
                               'doc_comment', delim=delim)
            node.final_val = content
        else:
            node = FullCommentNode(state, first_lineno, first_colno, last_lineno, last_colno,
                                   'doc_comment', delim=delim,
                                   continuation_indent=continuation_indent)
            node.raw_val = content_lines
            node.final_val = content
            state.ast.scalar_nodes.append(node)
        state.next_doc_comment = node
        state.next_cache = True
        if state.bidi_rtl:
            state.bidi_rtl_last_scalar_last_line = content_lines[-1]
            state.bidi_rtl_last_scalar_last_lineno = node.last_lineno
        if continuation_indent is not None:
            state.indent = continuation_indent
        state.at_line_start = False
        return line


    def _parse_token_literal_string_delim(self, line, state, section=False,
                                          max_delim_length=grammar.PARAMS['max_delim_length'],
                                          ScalarNode=ScalarNode,
                                          literal_string_delim=grammar.LIT_GRAMMAR['literal_string_delim'],
                                          len=len):
        '''
        Parse inline literal string.
        '''
        len_line = len(line)
        state.colno = first_colno = state.len_full_line_plus_one - len_line
        first_lineno = state.lineno
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        if state.next_scalar is not None:
            if state.inline or not state.at_line_start:
                raise erring.ParseError('Cannot start a string when a prior scalar has not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        line_lstrip_delim = line.lstrip(line[0])
        len_delim = len_line - len(line_lstrip_delim)
        if len_delim > 3 and (len_delim % 3 != 0 or len_delim > max_delim_length):
            raise erring.ParseError('Literal string delims must have lengths of 1 or 2, or multiples of 3 that are no longer than {0} characters'.format(max_delim_length), state)
        delim = line[:len_delim]
        content_lines, continuation_indent, content, last_lineno, last_colno, line = self._parse_delim_inline('literal string', delim, line_lstrip_delim, state, section=section)
        content_strip_space = content.strip('\x20')
        if content_strip_space[:1] == content_strip_space[-1:] == literal_string_delim:
            content = content[1:-1]
        elif content_strip_space[:1] == literal_string_delim:
            content = content[1:]
        elif content_strip_space[-1:] == literal_string_delim:
            content = content[:-1]
        if not state.full_ast:
            node = ScalarNode(state, first_lineno, first_colno, last_lineno, last_colno,
                              'str', delim=delim)
        else:
            node = FullScalarNode(state, first_lineno, first_colno, last_lineno, last_colno,
                                  'str', delim=delim, continuation_indent=continuation_indent)
            node.raw_val = content_lines
            state.ast.scalar_nodes.append(node)
        if node.tag is None or node.tag.type is None:
            node.final_val = content
        elif not state.data_types[node.tag.type].ascii_bytes:
            node.final_val = self._type_tagged_scalar(state, node, content)
        else:
            try:
                content_bytes = content.encode('ascii')
            except Exception as e:
                raise erring.ParseError('Failed to encode string as ASCII in preparation for tag typing:\n  {0}'.format(e), node, node.tag['type'])
            node.final_val = self._type_tagged_scalar(state, node, content_bytes)
        state.next_scalar = node
        state.next_scalar_is_keyable = True
        state.next_cache = True
        if state.bidi_rtl:
            state.bidi_rtl_last_scalar_last_line = content_lines[-1]
            state.bidi_rtl_last_scalar_last_lineno = node.last_lineno
        if continuation_indent is not None:
            state.indent = continuation_indent
        state.at_line_start = False
        return line


    def _parse_token_escaped_string_delim(self, line, state, section=False,
                                          max_delim_length=grammar.PARAMS['max_delim_length'],
                                          ScalarNode=ScalarNode,
                                          FullScalarNode=FullScalarNode,
                                          len=len):
        '''
        Parse inline escaped string (single or double quote).
        '''
        len_line = len(line)
        state.colno = first_colno = state.len_full_line_plus_one - len_line
        first_lineno = state.lineno
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        if state.next_scalar is not None:
            if state.inline or not state.at_line_start:
                raise erring.ParseError('Encountered a string when a prior scalar had not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        line_lstrip_delim = line.lstrip(line[0])
        len_delim = len_line - len(line_lstrip_delim)
        if len_delim == 2:
            delim = line[0]
            content_lines = ['']
            continuation_indent = None
            content = ''
            last_lineno = first_lineno
            last_colno = first_colno + 1
            line = line[2:]
        else:
            if len_delim > 3 and (len_delim % 3 != 0 or len_delim > max_delim_length):
                raise erring.ParseError('Escaped string delims must have lengths of 1 or multiples of 3 that are no longer than {0} characters'.format(max_delim_length), state)
            delim = line[:len_delim]
            content_lines, continuation_indent, content, last_lineno, last_colno, line = self._parse_delim_inline('escaped string', delim, line_lstrip_delim, state, section=section)
        if not state.full_ast:
            node = ScalarNode(state, first_lineno, first_colno, last_lineno, last_colno,
                              'str', delim=delim)
        else:
            node = FullScalarNode(state, first_lineno, first_colno, last_lineno, last_colno,
                                  'str', delim=delim, continuation_indent=continuation_indent)
            node.raw_val = content_lines
            state.ast.scalar_nodes.append(node)
        if node.tag is None or node.tag.type is None:
            if '\\' not in content:
                content_esc = content
            else:
                try:
                    content_esc = self._unescape_unicode(content)
                except Exception as e:
                    raise erring.ParseError('Failed to unescape escaped string:\n  {0}'.format(e), node)
            node.final_val = content_esc
        elif not state.data_types[node.tag.type].ascii_bytes:
            if '\\' not in content:
                content_esc = content
            else:
                try:
                    content_esc = self._unescape_unicode(content)
                except Exception as e:
                    raise erring.ParseError('Failed to unescape escaped string:\n  {0}'.format(e), node)
            node.final_val = self._type_tagged_scalar(state, node, content_esc)
        else:
            try:
                content_bytes = content.encode('ascii')
            except Exception as e:
                raise erring.ParseError('Failed to encode string as ASCII in preparation for tag typing:\n  {0}'.format(e), node, node.tag['type'])
            if b'\\' not in content_bytes:
                content_bytes_esc = content_bytes
            else:
                try:
                    content_bytes_esc = self._unescape_bytes(content_bytes)
                except Exception as e:
                    raise erring.ParseError('Failed to unescape escaped string that is tagged with an ASCII bytes type:\n  {0}'.format(e), node, node.tag['type'])
            node.final_val = self._type_tagged_scalar(state, node, content_bytes_esc)
        state.next_scalar = node
        state.next_scalar_is_keyable = True
        state.next_cache = True
        if state.bidi_rtl:
            state.bidi_rtl_last_scalar_last_line = content_lines[-1]
            state.bidi_rtl_last_scalar_last_lineno = node.last_lineno
        if continuation_indent is not None:
            state.indent = continuation_indent
        state.at_line_start = False
        return line


    def _parse_token_section(self, delim, line, state,
                             block_suffix=grammar.LIT_GRAMMAR['block_suffix'],
                             whitespace=grammar.LIT_GRAMMAR['indent'],
                             SectionNode=SectionNode,
                             open_indentation_list=grammar.LIT_GRAMMAR['open_indentation_list'],
                             KeyPathNode=KeyPathNode,
                             comment_delim=grammar.LIT_GRAMMAR['comment_delim'],
                             path_separator=grammar.LIT_GRAMMAR['path_separator']):
        '''
        Parse a section.  This is invoked by `_parse_token_block_prefix()`.
        At this point, `line` has already had the delimiter stripped.
        '''
        # No need to check for cached scalars, since that's done in
        # `_parse_token_block_prefix()`.  Can't have doc comments or tags
        # for sections in general, although that could technically be relaxed
        # for the first section if the root node were empty.
        if state.next_cache:
            raise erring.ParseError('Sections do not take doc comments or tags', state, unresolved_cache=True)
        if line[:1] == block_suffix:
            state.ast.end_section(delim)
            line_lstrip_ws = line[1:].lstrip(whitespace)
            if line_lstrip_ws == '':
                return self._parse_line_goto_next('', state)
            if line_lstrip_ws[:1] == comment_delim and line_lstrip_ws[1:2] != comment_delim:
                return self._parse_token_line_comment(line_lstrip_ws, state)
            state.colno = state.len_full_line_plus_one - len(line_lstrip_ws)
            raise erring.ParseError('Unexpected content after end of section', state)
        node = SectionNode(state, delim)
        line_lstrip_ws = line.lstrip(whitespace)
        if line_lstrip_ws[:1] == open_indentation_list:
            state.colno = state.len_full_line_plus_one - len(line_lstrip_ws)
            next_scalar = KeyPathNode(state, open_indentation_list)
            line = line_lstrip_ws[1:]
        else:
            line = self._parse_scalar_token[line_lstrip_ws[:1]](line_lstrip_ws, state, section=True)
            next_scalar = state.next_scalar
            state.next_scalar = None
            state.next_cache = False
        node.last_colno = next_scalar.last_colno
        if next_scalar.implicit_type == 'key_path':
            node.key_path = next_scalar
        else:
            if not state.next_scalar_is_keyable:
                raise erring.ParseError('Invalid scalar type for a key', node)
            node.scalar = next_scalar
        state.ast.start_section(node)
        line_lstrip_ws = line.lstrip(whitespace)
        if line_lstrip_ws == '':
            return self._parse_line_goto_next('', state)
        if line_lstrip_ws[:1] == comment_delim and line_lstrip_ws[1:2] != comment_delim:
            return self._parse_token_line_comment(line_lstrip_ws, state)
        if next_scalar.implicit_type == 'key_path' and len(next_scalar) == 1 and line[:1] == path_separator:
            raise erring.ParseError('When a "{0}" is used in a section, it must be the last element in a key path, or the only element'.format(open_indentation_list), state)
        raise erring.ParseError('Unexpected content after start of section', state)


    def _parse_token_block_prefix(self, line, state,
                                  max_delim_length=grammar.PARAMS['max_delim_length'],
                                  ScalarNode=ScalarNode,
                                  FullScalarNode=FullScalarNode,
                                  CommentNode=CommentNode,
                                  FullCommentNode=FullCommentNode,
                                  whitespace=grammar.LIT_GRAMMAR['indent'],
                                  block_prefix=grammar.LIT_GRAMMAR['block_prefix'],
                                  block_suffix=grammar.LIT_GRAMMAR['block_suffix'],
                                  block_delim_set=grammar.LIT_GRAMMAR['block_delim_set'],
                                  comment_delim=grammar.LIT_GRAMMAR['comment_delim'],
                                  escaped_string_doublequote_delim=grammar.LIT_GRAMMAR['escaped_string_doublequote_delim'],
                                  escaped_string_singlequote_delim=grammar.LIT_GRAMMAR['escaped_string_singlequote_delim'],
                                  literal_string_delim=grammar.LIT_GRAMMAR['literal_string_delim'],
                                  assign_key_val=grammar.LIT_GRAMMAR['assign_key_val'],
                                  newline=grammar.LIT_GRAMMAR['newline'],
                                  sentinel=grammar.LIT_GRAMMAR['terminal_sentinel'],
                                  next=next, len=len):
        '''
        Parse a block quoted string or doc comment.
        '''
        len_line = len(line)
        state.colno = first_colno = state.len_full_line_plus_one - len_line
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        delim_code_point = line[1:2]
        if delim_code_point not in block_delim_set:
            raise erring.ParseError('Invalid block delimiter', state)
        if state.next_scalar is not None:
            if state.inline or not state.at_line_start:
                raise erring.ParseError('Encountered a string when a prior scalar had not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        elif delim_code_point == comment_delim and state.next_doc_comment is not None:
            raise erring.ParseError('Encountered a doc comment when a prior doc comment had not yet been resolved', state, unresolved_cache=True)
        line_lstrip_delim = line[1:].lstrip(delim_code_point)
        # -1 for `|`
        len_delim = len_line - len(line_lstrip_delim) - 1
        delim = delim_code_point*len_delim
        if len_delim < 3 or len_delim % 3 != 0 or len_delim > max_delim_length:
            raise erring.ParseError('Block delims must have lengths that are multiples of 3 that are no longer than {0} characters'.format(max_delim_length), state)
        if delim_code_point == assign_key_val:
            return self._parse_token_section(delim, line_lstrip_delim, state)
        if line_lstrip_delim != '' and line_lstrip_delim.lstrip(whitespace) != '':
            raise erring.ParseError('An opening block delim must not be followed by anything; block content does not start until the next line', state)
        closing_delim_re, group = self._closing_delim_re_dict[delim]
        end_block_delim = block_prefix + delim + block_suffix
        len_end_block_delim = len(end_block_delim)
        content_lines = []
        indent = state.indent
        first_lineno = last_lineno = state.lineno
        while True:
            line = next(state.source_lines_iter, None)
            last_lineno += 1
            if line is None:
                raise erring.ParseError('Unterminated block object', state.source_range_to_loc(last_lineno, 1))
            len_full_line = len(line)
            if not line.startswith(indent) and line.lstrip(whitespace) != '':
                raise erring.IndentationError(state.source_range_to_loc(last_lineno, len(line.lstrip(whitespace)) + 1))
            if delim in line:
                m = closing_delim_re.search(line)
                if m is not None:
                    line_lstrip_ws = line.lstrip(whitespace)
                    if not line_lstrip_ws.startswith(end_block_delim):
                        raise erring.ParseError('Invalid delim sequence in body of block object', state.source_range_to_loc(last_lineno, line_lstrip_ws))
                    len_continuation_indent = len_full_line - len(line_lstrip_ws)
                    continuation_indent = line[:len_continuation_indent]
                    line = line_lstrip_ws[len_end_block_delim:]
                    last_colno = len_continuation_indent + len_end_block_delim
                    if state.at_line_start and indent != continuation_indent:
                        raise erring.ParseError('Inconsistent block delim indentation', state.source_range_to_loc(last_lineno, last_colno))
                    if continuation_indent == '':
                        content_lines_dedent = content_lines
                    else:
                        content_lines_dedent = []
                        for line_count, content_line in enumerate(content_lines):
                            if content_line.startswith(continuation_indent):
                                content_lines_dedent.append(content_line[len_continuation_indent:])
                            elif content_line.lstrip(whitespace) == '':
                                content_lines_dedent.append('')
                            else:
                                raise erring.ParseError('Incorrect indentation relative to block delim indentation', state.source_range_to_loc(first_lineno + line_count + 1, len(content_line.lstrip(whitespace)) + 1))
                    break
            content_lines.append(line)
        # Note that there's no need to reset the bidi_rtl state, given the
        # nature of the final delimiter.
        if delim_code_point == literal_string_delim:
            if not state.full_ast:
                node = ScalarNode(state, first_lineno, first_colno, last_lineno, last_colno,
                                  'str', delim=delim, block=True)
            else:
                node = FullScalarNode(state, first_lineno, first_colno, last_lineno, last_colno,
                                      'str', delim=delim, block=True)
                node.raw_val = content_lines_dedent
                state.ast.scalar_nodes.append(node)
            if node.tag is None:
                if content_lines:
                    content_lines_dedent_last_line = content_lines_dedent[-1]
                    content_lines_dedent[-1] = content_lines_dedent_last_line + newline
                    content = newline.join(content_lines_dedent)
                    content_lines_dedent[-1] = content_lines_dedent_last_line
                else:
                    content = ''
                node.final_val = content
            else:
                if 'newline' in node.tag:
                    tag_newline = node.tag['newline'].final_val
                else:
                    tag_newline = newline
                if 'indent' in node.tag:
                    tag_indent = node.tag['indent'].final_val
                else:
                    tag_indent = None
                if content_lines:
                    content_lines_dedent_last_line = content_lines_dedent[-1]
                    content_lines_dedent[-1] = content_lines_dedent_last_line + tag_newline
                    if tag_indent is None:
                        content = tag_newline.join(content_lines_dedent)
                    else:
                        content = tag_newline.join(tag_indent + x for x in content_lines_dedent)
                    content_lines_dedent[-1] = content_lines_dedent_last_line
                else:
                    content = ''
                if node.tag.type is None:
                    node.final_val = content
                elif not state.data_types[node.tag.type].ascii_bytes:
                    node.final_val = self._type_tagged_scalar(state, node, content)
                else:
                    try:
                        content_bytes = content.encode('ascii')
                    except Exception as e:
                        raise erring.ParseError('Failed to encode string as ASCII in preparation for tag typing:\n  {0}'.format(e), node, node.tag['type'])
                    node.final_val = self._type_tagged_scalar(state, node, content_bytes)
            state.next_scalar = node
            state.next_scalar_is_keyable = True
            state.next_cache = True
        elif delim_code_point == escaped_string_singlequote_delim or delim_code_point == escaped_string_doublequote_delim:
            if not state.full_ast:
                node = ScalarNode(state, first_lineno, first_colno, last_lineno, last_colno,
                                  'str', delim=delim, block=True)
            else:
                node = FullScalarNode(state, first_lineno, first_colno, last_lineno, last_colno,
                                      'str', delim=delim, block=True)
                node.raw_val = content_lines_dedent
                state.ast.scalar_nodes.append(node)
            if node.tag is None:
                if content_lines:
                    content_lines_dedent_last_line = content_lines_dedent[-1]
                    content_lines_dedent[-1] = content_lines_dedent_last_line + newline
                    content = newline.join(content_lines_dedent)
                    content_lines_dedent[-1] = content_lines_dedent_last_line
                else:
                    content = ''
                try:
                    content_esc = self._unescape_unicode(content)
                except Exception as e:
                    raise erring.ParseError('Failed to unescape escaped string:\n  {0}'.format(e), node)
                node.final_val = content_esc
            else:
                if 'newline' in node.tag:
                    tag_newline = node.tag['newline'].final_val
                else:
                    tag_newline = newline
                if content_lines:
                    content_lines_dedent_first_line = content_lines_dedent[0]
                    content_lines_dedent_last_line = content_lines_dedent[-1]
                    if 'indent' in node.tag:
                        tag_indent = node.tag['indent'].final_val
                        content_lines_dedent[0] = tag_indent + content_lines_dedent_first_line
                        # Don't use `content_lines_dedent_last_line`, but access
                        # by index, to account for only a single line
                        content_lines_dedent[-1] = content_lines_dedent[-1] + newline + sentinel
                    else:
                        tag_indent = ''
                        content_lines_dedent[-1] = content_lines_dedent_last_line + newline
                    content = newline.join(content_lines_dedent)
                    content_lines_dedent[0] = content_lines_dedent_first_line
                    content_lines_dedent[-1] = content_lines_dedent_last_line
                else:
                    content = ''
                if node.tag.type is None:
                    try:
                        content_esc = self._unescape_unicode(content, newline=tag_newline, indent=tag_indent)
                    except Exception as e:
                        raise erring.ParseError('Failed to unescape escaped string:\n  {0}'.format(e), node)
                    node.final_val = content_esc
                elif not state.data_types[node.tag.type].ascii_bytes:
                    try:
                        content_esc = self._unescape_unicode(content, newline=tag_newline, indent=tag_indent)
                    except Exception as e:
                        raise erring.ParseError('Failed to unescape escaped string:\n  {0}'.format(e), node)
                    node.final_val = self._type_tagged_scalar(state, node, content_esc)
                else:
                    try:
                        content_bytes = content.encode('ascii')
                    except Exception as e:
                        raise erring.ParseError('Failed to encode string as ASCII in preparation for tag typing:\n  {0}'.format(e), node, node.tag['type'])
                    # For ASCII bytes types, "newline" value is checked
                    # for compatibility in tag, so there's no need for a
                    # check here.
                    tag_newline_bytes = tag_newline.encode('ascii')
                    tag_indent_bytes = tag_indent.encode('ascii')
                    try:
                        content_bytes_esc = self._unescape_bytes(content_bytes, newline=tag_newline_bytes, indent=tag_indent_bytes)
                    except Exception as e:
                        raise erring.ParseError('Failed to unescape escaped string that is tagged with an ASCII bytes type:\n  {0}'.format(e), node, node.tag['type'])
                    node.final_val = self._type_tagged_scalar(state, node, content_bytes_esc)
            state.next_scalar = node
            state.next_scalar_is_keyable = True
            state.next_cache = True
        elif delim_code_point == comment_delim:
            if not state.full_ast:
                node = CommentNode(state, first_lineno, first_colno, last_lineno, last_colno,
                                   'doc_comment', delim=delim, block=True)
            else:
                node = FullCommentNode(state, first_lineno, first_colno, last_lineno, last_colno,
                                       'doc_comment', delim=delim, block=True)
                node.raw_val = content_lines_dedent
                state.ast.scalar_nodes.append(node)
                if content_lines:
                    # Modify last line by adding `\n`, then join lines with `\n`, then
                    # put last line back to original value, to avoid having to modify the
                    # final string by adding an `\n` at the end
                    content_lines_dedent_last_line = content_lines_dedent[-1]
                    content_lines_dedent[-1] = content_lines_dedent_last_line + newline
                    content = newline.join(content_lines_dedent)
                    content_lines_dedent[-1] = content_lines_dedent_last_line
                else:
                    content = ''
                node.final_val = content
            state.next_doc_comment = node
            state.next_cache = True
        else:
            raise ValueError
        state.len_full_line_plus_one = len_full_line + 1
        state.lineno = last_lineno
        state.indent = continuation_indent
        state.at_line_start = False
        return line


    def _parse_token_number(self, line, state, section=False,
                            len=len, int=int, infinity_word=grammar.LIT_GRAMMAR['infinity_word'],
                            infinity_set=set([float('-inf'), float('inf')]),
                            sign=grammar.LIT_GRAMMAR['sign'],
                            any_exponent_letter=grammar.LIT_GRAMMAR['dec_exponent_letter']+grammar.LIT_GRAMMAR['hex_exponent_letter'],
                            imaginary_unit=grammar.LIT_GRAMMAR['imaginary_unit']):
        '''
        Parse a number (float, int, etc.).
        '''
        state.colno = first_colno = state.len_full_line_plus_one - len(line)
        lineno = state.lineno
        # No need to reset bidi_rtl state; it cannot be modified by numbers
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        if state.next_scalar is not None:
            if state.inline or not state.at_line_start:
                raise erring.ParseError('Cannot start a number when a prior scalar has not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        m = state.number_re.match(line)
        if m is None:
            raise erring.ParseError('Invalid literal with numeric start', state)
        group_name =  m.lastgroup
        group_type, group_base = group_name.rsplit('_', 1)
        group_base = int(group_base)
        m_end = m.end()
        raw_val = line[:m_end]
        last_colno = first_colno + m_end - 1
        line = line[m_end:]
        cleaned_val = raw_val.replace('\x20', '').replace('\t', '').replace('_', '')
        if group_type == 'int' and self.integers:
            implicit_type = 'int'
            if not state.full_ast:
                node = ScalarNode(state, lineno, first_colno, lineno, last_colno, implicit_type)
            else:
                node = FullScalarNode(state, lineno, first_colno, lineno, last_colno,
                                      implicit_type, num_base=group_base)
                node.raw_val = raw_val
                state.ast.scalar_nodes.append(node)
            if node.tag is None or node.tag.type is None:
                parser = state.data_types[implicit_type].parser
                try:
                    if group_base == 10:
                        final_val = parser(cleaned_val)
                    else:
                        final_val = parser(cleaned_val, group_base)
                except Exception as e:
                    raise erring.ParseError('Error in typing of integer literal:\n  {0}'.format(e), node)
            else:
                final_val = self._type_tagged_scalar(state, node, cleaned_val, num_base=group_base)
            state.next_scalar_is_keyable = True
        elif group_type == 'float' or group_type == 'float_inf_or_nan' or (group_type == 'int' and not self.integers):
            implicit_type = 'float'
            if not state.full_ast:
                node = ScalarNode(state, lineno, first_colno, lineno, last_colno, implicit_type)
            else:
                node = FullScalarNode(state, lineno, first_colno, lineno, last_colno,
                                      implicit_type, num_base=group_base)
                node.raw_val = raw_val
                state.ast.scalar_nodes.append(node)
            if node.tag is None or node.tag.type is None:
                parser = state.data_types[implicit_type].parser
                try:
                    if group_base == 10:
                        final_val = parser(cleaned_val)
                    else:
                        final_val = parser.fromhex(cleaned_val)
                except Exception as e:
                    raise erring.ParseError('Error in typing of float literal:\n  {0}'.format(e), state)
            else:
                final_val = self._type_tagged_scalar(state, node, cleaned_val, num_base=group_base)
            if final_val in infinity_set and infinity_word not in cleaned_val and not self.float_overflow_to_inf:
                raise erring.ParseError('Non-inf float value became inf due to float precision; to allow this, set float_overflow_to_inf=True', node)
            state.next_scalar_is_keyable = False
        # Don't need to check for self.extended_types == True when working
        # with complex and rational, because the corresponding match groups
        # are only enabled (via regex pattern selection) when that is the case
        elif group_type == 'complex' or group_type == 'complex_inf_or_nan':
            implicit_type = 'complex'
            for s in sign:
                second_sign_index = cleaned_val.find(s, 1)
                if second_sign_index > 0 and cleaned_val[second_sign_index-1] in any_exponent_letter:
                    second_sign_index = cleaned_val.find(s, second_sign_index+1)
                if second_sign_index > 0:
                    break
            if second_sign_index < 0:
                cleaned_val_real = '0.0'
                cleaned_val_imag = cleaned_val
            else:
                cleaned_val_real = cleaned_val[:second_sign_index]
                cleaned_val_imag = cleaned_val[second_sign_index:]
                if cleaned_val_real[-1] == imaginary_unit:
                    cleaned_val_real, cleaned_val_imag = cleaned_val_imag, cleaned_val_real
            if not state.full_ast:
                node = ScalarNode(state, lineno, first_colno, lineno, last_colno, implicit_type)
            else:
                node = FullScalarNode(state, lineno, first_colno, lineno, last_colno,
                                      implicit_type, num_base=group_base)
                node.raw_val = raw_val
                state.ast.scalar_nodes.append(node)
            if node.tag is None or node.tag.type is None:
                parser = state.data_types[implicit_type].parser
                try:
                    float_parser = state.data_types['float'].parser
                    if group_base == 10:
                        val_real = float_parser(cleaned_val_real)
                        val_imag = float_parser(cleaned_val_imag[:-1])
                    else:
                        val_real = float_parser.fromhex(cleaned_val_real)
                        val_imag = float_parser.fromhex(cleaned_val_imag[:-1])
                    final_val = parser(val_real, val_imag)
                except Exception as e:
                    raise erring.ParseError('Error in typing of complex literal:\n  {0}'.format(e), state)
            else:
                final_val = self._type_tagged_scalar(state, node, cleaned_val.replace(imaginary_unit, 'j'), num_base=group_base)
            if ((final_val.real in infinity_set and infinity_word not in cleaned_val_real) or (final_val.imag in infinity_set and infinity_word not in cleaned_val_imag)) and not self.float_overflow_to_inf:
                raise erring.ParseError('Non-inf float value became inf due to float precision; to allow this, set float_overflow_to_inf=True', node)
            state.next_scalar_is_keyable = False
        elif group_type == 'rational':
            implicit_type = 'rational'
            if not state.full_ast:
                node = ScalarNode(state, lineno, first_colno, lineno, last_colno, implicit_type)
            else:
                node = FullScalarNode(state, lineno, first_colno, lineno, last_colno,
                                      implicit_type, num_base=group_base)
                node.raw_val = raw_val
                state.ast.scalar_nodes.append(node)
            if node.tag is None or node.tag.type is None:
                parser = state.data_types[implicit_type].parser
                try:
                    final_val = parser(cleaned_val)
                except Exception as e:
                    raise erring.ParseError('Error in typing of rational literal:\n  {0}'.format(e), state)
            else:
                final_val = self._type_tagged_scalar(state, node, cleaned_val, num_base=group_base)
            state.next_scalar_is_keyable = False
        else:
            raise ValueError
        node.final_val = final_val
        state.next_scalar = node
        state.next_cache = True
        state.at_line_start = False
        return line


    def _parse_token_unquoted_string_or_key_path(self, line, state, section=False,
                                                 whitespace=grammar.LIT_GRAMMAR['indent'],
                                                 open_indentation_list=grammar.LIT_GRAMMAR['open_indentation_list'],
                                                 assign_key_val=grammar.LIT_GRAMMAR['assign_key_val'],
                                                 ScalarNode=ScalarNode,
                                                 FullScalarNode=FullScalarNode,
                                                 KeyPathNode=KeyPathNode,
                                                 len=len):
        '''
        Parse an unquoted string or key path.
        '''
        state.colno = first_colno = state.len_full_line_plus_one - len(line)
        lineno = state.lineno
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        if state.next_scalar is not None:
            if state.inline or not state.at_line_start:
                if state.unquoted_string_or_key_path_re.match(line):
                    raise erring.ParseError('Cannot start a string when a prior scalar has not yet been resolved', state, unresolved_cache=True)
                if self.only_ascii_unquoted and self._unquoted_string_or_key_path_unicode_re.match(line):
                    raise erring.ParseError('Invalid character kept a prior scalar from being resolved (only_ascii_unquoted=True)', state, unresolved_cache=True)
                raise erring.ParseError('Invalid character kept a prior scalar from being resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        m = state.unquoted_string_or_key_path_re.match(line)
        if m is None:
            if self.only_ascii_unquoted and self._unquoted_string_or_key_path_unicode_re.match(line):
                raise erring.ParseError('Invalid unquoted string or key path (only_ascii_unquoted=True):  "{0}"'.format(line.replace('"', '\\"')), state)
            raise erring.ParseError('Invalid unquoted string or key path:  "{0}"'.format(line.replace('"', '\\"')), state)
        m_end = m.end()
        raw_val = line[:m_end]
        last_colno = first_colno + m_end - 1
        line = line[m_end:]
        group_name = m.lastgroup
        if group_name == 'unquoted_string':
            implicit_type = 'str'
            if not state.full_ast:
                node = ScalarNode(state, lineno, first_colno, lineno, last_colno, implicit_type)
            else:
                node = FullScalarNode(state, lineno, first_colno, lineno, last_colno, implicit_type)
                node.raw_val = raw_val
                state.ast.scalar_nodes.append(node)
            if node.tag is None or node.tag.type is None:
                final_val = raw_val
            elif not state.data_types[node.tag.type].ascii_bytes:
                final_val = self._type_tagged_scalar(state, node, raw_val)
            else:
                # Could get an encoding error if non-ASCII unquoted
                # string are enabled
                try:
                    raw_val_bytes = raw_val.encode('ascii')
                except Exception as e:
                    raise erring.ParseError('Failed to encode string as ASCII in preparation for tag typing:\n  {0}'.format(e), node, node.tag['type'])
                final_val = self._type_tagged_scalar(state, node, raw_val_bytes)
            node.final_val = final_val
            state.next_scalar = node
            state.next_scalar_is_keyable = True
            state.next_cache = True
            if state.bidi_rtl:
                state.bidi_rtl_last_scalar_last_line = raw_val
                state.bidi_rtl_last_scalar_last_lineno = node.last_lineno
        elif group_name == 'reserved_word':
            try:
                implicit_type = self._reserved_word_types[raw_val]
            except KeyError:
                if raw_val.lower() in self._reserved_word_types:
                    raise erring.ParseError('Invalid capitalization of reserved word "{0}"'.format(raw_val.lower()), state)
                raise erring.ParseError('Invalid use of reserved word "{0}"'.format(raw_val), state)
            if self.extended_types and (implicit_type == 'float' or implicit_type == 'complex'):
                # Handle the case of `inf...` or `nan...` when complex numbers
                # are enabled.  This could be done by creating a different
                # regex for extended types that would capture the full complex
                # number, but that would involve duplicating what already
                # exists elsewhere (underscore handling, etc.).
                return self._parse_token_number(raw_val+line, state)
            if not state.full_ast:
                node = ScalarNode(state, lineno, first_colno, lineno, last_colno, implicit_type)
            else:
                node = FullScalarNode(state, lineno, first_colno, lineno, last_colno, implicit_type)
                node.raw_val = raw_val
                state.ast.scalar_nodes.append(node)
            if node.tag is None or node.tag.type is None:
                try:
                    final_val = state.data_types[implicit_type].parser(raw_val)
                except Exception as e:
                    raise erring.ParseError('Error in typing of reserved word "{0}":\n  {1}'.format(raw_val, e), state)
            else:
                # No need to check for type with ascii_bytes=True, because
                # all reserved words either cannot be typed with tags (none,
                # bool), or must be numeric (float)
                final_val = self._type_tagged_scalar(state, node, raw_val)
            node.final_val = final_val
            state.next_scalar = node
            if implicit_type != 'float':
                state.next_scalar_is_keyable = True
            else:
                state.next_scalar_is_keyable = False
            state.next_cache = True
            # Reserved words don't contain rtl code points
        elif group_name == 'key_path':
            if state.next_cache:
                raise erring.ParseError('Key paths do not take doc comments or tags', state, unresolved_cache=True)
            node = KeyPathNode(state, raw_val)
            if state.full_ast:
                node.raw_val = raw_val
                state.ast.scalar_nodes.append(node)
            state.next_scalar = node
            state.next_scalar_is_keyable = True
            state.next_cache = True
            if state.bidi_rtl:
                state.bidi_rtl_last_scalar_last_line = raw_val
                state.bidi_rtl_last_scalar_last_lineno = node.last_lineno
            # Make sure that the key path will be used as a key, rather than
            # as a value
            if not section:
                line = line.lstrip(whitespace)
                if line == '' and state.inline:
                    line = self._parse_line_goto_next('', state)
                    if line is None:
                        raise erring.ParseError('Key path was never used', node)
                if line[:1] != assign_key_val:
                    raise erring.ParseError('Key paths must be used as keys, not values; missing or misplaced "{0}"'.format(assign_key_val), node)
        else:
            raise ValueError
        state.at_line_start = False
        return line


    def _parse_token_alias_prefix(self, line, state, AliasNode=AliasNode):
        state.colno = state.len_full_line_plus_one - len(line)
        if not self.aliases:
            raise erring.ParseError('Aliases are not enabled (aliases=False)', state)
        if state.bidi_rtl:
            self._check_bidi_rtl(state)
        if state.next_scalar is not None:
            if state.inline or not state.at_line_start:
                raise erring.ParseError('Cannot start an alias when a prior scalar has not yet been resolved', state, unresolved_cache=True)
            state.ast.append_scalar_val()
        m = state.alias_path_re.match(line)
        if m is None:
            if self.only_ascii_unquoted and self._alias_path_unicode_re.match(line):
                raise erring.ParseError('Invalid alias (only_ascii_unquoted=True):  "{0}"'.format(line.replace('"', '\\"')), state)
            raise erring.ParseError('Invalid alias:  "{0}"'.format(line.replace('"', '\\"')), state)
        m_end = m.end()
        raw_val = line[:m_end]
        line = line[m_end:]
        node = AliasNode(state, raw_val)
        state.next_scalar = node
        state.next_scalar_is_keyable = False
        state.next_cache = True
        if state.bidi_rtl:
            state.bidi_rtl_last_scalar_last_line = raw_val
            state.bidi_rtl_last_scalar_last_lineno = node.last_lineno
        state.at_line_start = False
        return line


    def _type_tagged_scalar(self, state, scalar_node, processed_val, num_base=None):
        try:
            final_val = state.data_types[scalar_node.tag.type].parser(processed_val)
        except Exception as e:
            raise erring.ParseError('Applying explicit type "{0}" to scalar object failed:\n  {1}'.format(scalar_node.tag.type, e), scalar_node, scalar_node.tag)
        return final_val
