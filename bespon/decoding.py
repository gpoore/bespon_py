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
from .astnodes import RootNode, ScalarNode

if sys.version_info.major == 2:
    str = unicode
    __chr__ = chr
    chr = unichr

# pylint:  disable=W0622
if sys.maxunicode == 0xFFFF:
    chr = coding.chr_surrogate
    ord = coding.ord_surrogate
# pylint:  enable=W0622


WHITESPACE = grammar.LIT_GRAMMAR['whitespace']
UNICODE_WHITESPACE = grammar.LIT_GRAMMAR['unicode_whitespace']
UNICODE_WHITESPACE_SET = set(UNICODE_WHITESPACE)
ESCAPED_STRING_SINGLEQUOTE_DELIM = grammar.LIT_GRAMMAR['escaped_string_singlequote_delim'],
ESCAPED_STRING_DOUBLEQUOTE_DELIM = grammar.LIT_GRAMMAR['escaped_string_doublequote_delim'],
LITERAL_STRING_DELIM = grammar.LIT_GRAMMAR['literal_string_delim']
COMMENT_DELIM = grammar.LIT_GRAMMAR['comment_delim']
OPEN_NONINLINE_LIST = grammar.LIT_GRAMMAR['open_noninline_list']
PATH_SEPARATOR = grammar.LIT_GRAMMAR['path_separator']
END_TAG_WITH_SUFFIX = grammar.LIT_GRAMMAR['end_tag_with_suffix']
MAX_DELIM_LENGTH = grammar.PARAMS['max_delim_length']
DOC_COMMENT_INVALID_NEXT_TOKEN_SET = set(grammar.LIT_GRAMMAR['doc_comment_invalid_next_token'])
ASSIGN_KEY_VAL = grammar.LIT_GRAMMAR['assign_key_val']
WHITESPACE_OR_COMMENT_SET = set(WHITESPACE) | set(COMMENT_DELIM)




class State(object):
    '''
    Keep track of state.  This includes information about the source, the
    current location within the source, the current parsing context,
    a cached tag for the next object that is parsed, etc.
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
        if not all(x in (True, False) for x in (at_line_start, inline)):
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

        # #### need to check implementation on these
        if type_data is None:
            self.type_data = load_types.CORE_TYPES
        else:
            self.type_data = type_data
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


        # Generate parser dicts


        # Create escape and unescape functions
        self.escape_unicode = escape.basic_unicode_escape
        unescape = escape.Unescape()
        self.unescape_unicode = unescape.unescape_unicode
        self.unescape_bytes = unescape.unescape_bytes


        # Create dict of token-based parsing functions
        #
        # In general, having a valid starting code point for an unquoted
        # string or keypath is a necessary but not sufficient condition for
        # finding a valid string or keypath, due to the possibility of a
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
        parse_token = collections.defaultdict(lambda: self._parse_token_unquoted_string_or_keypath)
        token_functions = {'comment_delim': self._parse_token_comment_delim,
                           'open_noninline_list': self._parse_token_open_noninline_list,
                           'start_inline_dict': self._parse_token_start_inline_dict,
                           'end_inline_dict': self._parse_token_end_inline_dict,
                           'start_inline_list': self._parse_token_start_inline_list,
                           'end_inline_list': self._parse_token_end_inline_list,
                           'start_tag': self._parse_token_start_tag,
                           'end_tag': self._parse_token_end_tag,
                           'inline_element_separator': self._parse_token_inline_element_separator,
                           'block_prefix': self._parse_token_block_prefix,
                           'escaped_string_singlequote_delim': self._parse_token_escaped_string_singlequote_delim,
                           'escaped_string_doublequote_delim': self._parse_token_escaped_string_doublequote_delim,
                           'literal_string_delim': self._parse_token_literal_string_delim,
                           'alias_prefix': self._parse_token_alias_prefix}
        for token_name, func in token_functions.items():
            token = grammar.LIT_GRAMMAR[token_name]
            parse_token[token] = func
        for c in '1234567890-+':
            parse_token[c] = self._parse_token_number_or_number_unit
        parse_token[''] = self._parse_line_goto_next
        self._parse_token = parse_token



        # Assemble regular expressions
        if self.only_ascii:
            invalid_literal = grammar.RE_GRAMMAR['ascii_invalid_literal']
            self._invalid_literal_re = re.compile(invalid_literal)
        else:
            invalid_literal = grammar.RE_GRAMMAR['unicode_invalid_literal']
            self._invalid_literal_re = re.compile(invalid_literal)
            non_ascii = grammar.RE_GRAMMAR['non_ascii']
            ascii_invalid_literal = grammar.RE_GRAMMAR['ascii_invalid_literal']
            self._non_ascii_or_invalid_ascii_re = re.compile('(?P<non_ascii>{0})|(?P<invalid_literal>{1})'.format(non_ascii, ascii_invalid_literal))
            bidi = grammar.RE_GRAMMAR['bidi']
            ignorable = grammar.RE_GRAMMAR['default_ignorable']
            invalid_literal_or_bidi_or_ignorable = '(?P<invalid_literal>{0})|(?P<bidi>{1})|(?P<default_ignorable>{2})'.format(invalid_literal, bidi, ignorable)
            self._invalid_literal_or_bidi_or_ignorable_re = re.compile(invalid_literal_or_bidi_or_ignorable)
            invalid_literal_or_bidi = '(?P<invalid_literal>{0})|(?P<bidi>{1})'.format(invalid_literal, bidi)
            self._invalid_literal_or_bidi_re = re.compile(invalid_literal_or_bidi)
            invalid_literal_or_default_ignorable = '(?P<invalid_literal>{0})|(?P<default_ignorable>{1})'.format(invalid_literal, ignorable)
            self._invalid_literal_or_default_ignorable_re = re.compile(invalid_literal_or_default_ignorable)

        self._newline_re = re.compile(grammar.RE_GRAMMAR['newline'])

        self._bidi_re = re.compile(bidi)


        # Dict of regexes for identifying closing delimiters for inline
        # escaped strings.  Needed regexes are automatically generated on the
        # fly.  Note that opening delimiters are handled by normal string
        # methods, as are closing delimiters for block strings.  Because
        # block string delimiters are enclosed within `|` and `/`, lookbehind
        # and lookahead for escapes or other delimiter characters is unneeded.
        escaped_string_singlequote_delim = ESCAPED_STRING_SINGLEQUOTE_DELIM
        escaped_string_doublequote_delim = ESCAPED_STRING_DOUBLEQUOTE_DELIM
        literal_string_delim = LITERAL_STRING_DELIM
        comment_delim = COMMENT_DELIM
        def gen_closing_delim_regex(delim):
            c_0 = delim[0]
            if c_0 == escaped_string_singlequote_delim or c_0 == escaped_string_doublequote_delim:
                group = 1
                if delim == escaped_string_singlequote_delim or delim == escaped_string_doublequote_delim:
                    pattern = r'(?:\\.|[^{delim_char}\\]+)*({delim_char})'.format(delim_char=re.escape(c_0))
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
                               (?: \\. | [^{delim_char}\\]+ | {delim_char}{{{1,n_minus}}}(?!{delim_char}) | {delim_char}{{{n_plus},}}(?!{delim_char}) )*
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


        # Regexes for working with default ignorables
        #
        # Default ignorables mixed with inline delimiters
        singlequote = grammar.RE_GRAMMAR['escaped_string_singlequote_delim']
        doublequote = grammar.RE_GRAMMAR['escaped_string_doublequote_delim']
        literal = grammar.RE_GRAMMAR['literal_string_delim']
        comment = grammar.RE_GRAMMAR['comment_delim']
        default_ignorable = grammar.RE_GRAMMAR['default_ignorable']
        inline_invalid_di_pattern = '^{di}+{delim}|{delim}{di}+(?:{delim}|$)'
        self._invalid_ignorable_inline_singlequote_re = re.compile(inline_invalid_di_pattern.format(delim=singlequote, di=default_ignorable))
        self._invalid_ignorable_inline_doublequote_re = re.compile(inline_invalid_di_pattern.format(delim=doublequote, di=default_ignorable))
        self._invalid_ignorable_inline_literal_re = re.compile(inline_invalid_di_pattern.format(delim=literal, di=default_ignorable))
        self._invalid_ignorable_inline_doc_comment_re = re.compile(inline_invalid_di_pattern.format(delim=comment, di=default_ignorable))
        self._invalid_ignorable_line_comment_re = re.compile('{delim}{di}+{delim}'.format(delim=comment, di=default_ignorable))
        # Default ignorables at the start of continuation lines in wrapped
        # inline objects
        self._invalid_continuation_line_start_re = re.compile('{uws}|{di}'.format(uws=grammar.RE_GRAMMAR['unicode_whitespace'], di=default_ignorable))
        # Default ignorables in blocks
        block_prefix = grammar.RE_GRAMMAR['block_prefix']
        block_suffix = grammar.RE_GRAMMAR['block_suffix']
        invalid_block_di_pattern = '{delim}{di}+{delim}|{prefix}{di}+{delim}|{delim}{di}+{suffix}'
        self._invalid_ignorable_block_singlequote_re = re.compile(invalid_block_di_pattern.format(delim=singlequote, di=default_ignorable, prefix=block_prefix, suffix=block_suffix))
        self._invalid_ignorable_block_doublequote_re = re.compile(invalid_block_di_pattern.format(delim=doublequote, di=default_ignorable, prefix=block_prefix, suffix=block_suffix))
        self._invalid_ignorable_block_literal_re = re.compile(invalid_block_di_pattern.format(delim=literal, di=default_ignorable, prefix=block_prefix, suffix=block_suffix))
        self._invalid_ignorable_block_doc_comment_re = re.compile(invalid_block_di_pattern.format(delim=comment, di=default_ignorable, prefix=block_prefix, suffix=block_suffix))




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
            line_strip_nl = line[:-1]
            # Don't need to use line_strip_nl[-1:]; inline strings can't have
            # empty lines (the last line could be empty before the final
            # delimiter, but it's handled separately, so that's not an issue)
            if line_strip_nl[-1] in unicode_whitespace_set:
                s_list_inline.append(line_strip_nl)
            else:
                s_list_inline.append(line_strip_nl + '\x20')
        s_list_inline.append(s_list[-1])
        return ''.join(s_list_inline)


    def _check_invalid_literal_or_bidi_or_default_ignorable(self, normalized_string):
        '''
        Check the decoded, newline-normalized source for invalid code points
        and code points that trigger additional checking later.
        '''
        # General regex form:
        #    (?P<invalid_literal>{0})|(?P<bidi>{1})|(?P<default_ignorable>{2})
        #
        # A regex that catches everything is used at first.  If it finds
        # something other than an invalid literal, then scanning picks up
        # at the last location with a more focused regex.  This intentionally
        # involves scanning any characters that trigger a match twice
        # (using `<last_match>.start()`), so that any overlap between
        # categories will be detected.
        invalid_literal = False
        invalid_literal_index = None
        self._bidi = False
        self._bidi_last_scalar_last_lineno = 0
        self._bidi_last_scalar_last_line = ''
        self._default_ignorable = False

        # Pure ASCII may be specified as a requirement.  Even in this case,
        # a single, leading BOM is allowed, but for simplicity the regex
        # doesn't account for that, so a manual check is needed.
        if self.only_ascii:
            if normalized_string[0:1] == '\uFEFF':
                m_inv = self.invalid_literal_re.search(normalized_string, 1)
            else:
                m_inv = self.invalid_literal_re.search(normalized_string)
            if m_inv is not None:
                invalid_literal_index = m_inv.start()
                invalid_code_point = normalized_string[invalid_literal_index]
                invalid_esc = '\\U{0:08x}'.format(ord(invalid_code_point))
                invalid_lineno = len(self._newline_re.findall(normalized_string, 0, invalid_literal_index)) + 1
                raise erring.BespONException('Invalid literal code point "{0}" on line {1}'.format(invalid_esc, invalid_lineno))
            return

        # Even if pure ASCII isn't required, it is worth checking for, given
        # the comparatively much larger amount of time required to run the
        # full Unicode regexes.  This falls back to full Unicode if non-ASCII
        # code points are found.
        if normalized_string[0:1] == '\uFEFF':
            m_ascii = self._non_ascii_or_invalid_ascii_re.search(normalized_string, 1)
        else:
            m_ascii = self._non_ascii_or_invalid_ascii_re.search(normalized_string)
        if m_ascii is None:
            return
        elif m_ascii.lastgroup == 'invalid_literal':
            invalid_literal_index = m_ascii.start()
            invalid_code_point = normalized_string[invalid_literal_index]
            invalid_esc = '\\U{0:08x}'.format(ord(invalid_code_point))
            invalid_lineno = len(self._newline_re.findall(normalized_string, 0, invalid_literal_index)) + 1
            raise erring.BespONException('Invalid literal code point "{0}" on line {1}'.format(invalid_esc, invalid_lineno))

        # If the pure ASCII check fails, fall back to full Unicode.
        if normalized_string[0:1] == '\uFEFF':
            m_all = self._invalid_literal_or_bidi_or_ignorable_re.search(normalized_string, 1)
        else:
            m_all = self._invalid_literal_or_bidi_or_ignorable_re.search(normalized_string)
        if m_all is not None:
            if m_all.lastgroup == 'invalid_literal':
                invalid_literal = True
                invalid_literal_index = m_all.start()
            elif m_all.lastgroup == 'bidi':
                self._bidi = True
                m_inv_ign = self._invalid_literal_or_default_ignorable_re.search(normalized_string, m_all.start())
                if m_inv_ign is not None:
                    if m_inv_ign.lastgroup == 'invalid_literal':
                        invalid_literal = True
                        invalid_literal_index = m_inv_ign.start()
                    else:
                        self._default_ignorable = True
                        m_inv = self._invalid_literal_re.search(normalized_string, m_inv_ign.start())
                        if m_inv:
                            invalid_literal = True
                            invalid_literal_index = m_inv_ign.m_inv()
            elif m_all.lastgroup == 'default_ignorable':
                self._default_ignorable = True
                m_inv_bidi = self._invalid_literal_or_bidi_re.search(normalized_string, m_all.start())
                if m_inv_bidi is not None:
                    if m_inv_bidi.lastgroup == 'invalid_literal':
                        invalid_literal = True
                        invalid_literal_index = m_inv_bidi.start()
                    else:
                        self._bidi = True
                        m_inv = self._invalid_literal_re.search(normalized_string, m_inv_bidi.start())
                        if m_inv:
                            invalid_literal = True
                            invalid_literal_index = m_inv.start()
            else:
                raise erring.BespONException('There is a bug in the regular expression that checks for invalid code points')
        if invalid_literal:
            invalid_code_point = normalized_string[invalid_literal_index]
            if ord(invalid_code_point) <= 0xFFFF:
                invalid_esc = '\\u{0:04x}'.format(ord(invalid_code_point))
            else:
                invalid_esc = '\\U{0:08x}'.format(ord(invalid_code_point))
            invalid_lineno = len(self._newline_re.findall(normalized_string, 0, invalid_literal_index)) + 1
            raise erring.BespONException('Invalid literal code point "{0}" on line {1}'.format(invalid_esc, invalid_lineno))


    def decode(self, string_or_bytes):
        '''
        Decode a Unicode string or byte string into Python objects.
        '''
        # Decode if necessary
        if isinstance(string_or_bytes, str):
            raw_string = string_or_bytes
        else:
            try:
                raw_string = string_or_bytes.decode('utf8')
            except Exception as e:
                raise erring.BespONException('Cannot decode binary source:\n   {0}'.format(e))

        # Normalize newlines and check code points
        normalized_string = raw_string.replace('\r\n', '\n')
        del raw_string
        self._check_invalid_literal_or_bidi_or_default_ignorable(normalized_string)

        line_iter = iter(normalized_string.splitlines(True))
        del normalized_string

        ast, data = self._parse_lines(line_iter)

        return data


    def _parse_lines(self, line_iter, full_ast=False):
        '''
        Process lines from source into abstract syntax tree (AST).  Then
        process the AST into standard Python objects.
        '''
        state = State()
        ast = Ast(state)

        self._full_ast = full_ast
        self._ast = ast
        self._state = state
        self._line_iter = line_iter

        # Start by extracting the first line and stripping any BOM
        # #### deal with empty line?
        line = next(line_iter)
        if line[:1] == '\uFEFF':
            # Don't increment column, because that would throw off indentation
            # for subsequent lines
            line = line[1:]
        line = self._parse_line_start_last(line)
        if line == '':
            while line is not None and line == '':
                line = self._parse_line_goto_next(line)
        root = RootNode(state)
        ast.root = root
        ast._unresolved_nodes.append(root)
        ast.source.check_append_root(root)
        ast.pos = root

        parse_token = self._parse_token
        while line is not None:
            line = parse_token[line[:1]](line)

        # Don't keep references to object that are no longer needed.  This
        # only really matters for things like the ast, which can consume
        # significant memory.
        self._full_ast = None
        self._ast = None
        self._state = None
        self._line_iter = None

        ast.finalize()
        if not ast.root:
            raise erring.ParseError('There was no data to load', None)

        data = ast.root.final_val

        return (ast, data)


    def _parse_line_goto_next(self, line, next=next, whitespace=WHITESPACE):
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
        line_strip_ws = line.lstrip(whitespace)
        indent_len = len(line) - len(line_strip_ws)
        indent = line[:indent_len]
        state.indent = indent
        state.continuation_indent = indent
        state.at_line_start = True
        column = indent_len + 1
        state.first_column = column
        state.last_column = column
        return line_strip_ws


    def _parse_line_get_next(self, line, next=next):
        '''
        Get next line.  For use in lookahead in string scanning, etc.
        '''
        state = self._state
        line = next(self._line_iter, None)
        state.last_lineno += 1
        state.last_column = 1
        return line


    def _parse_line_start_last(self, line, whitespace=WHITESPACE):
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
        line_strip_ws = line.lstrip(whitespace)
        indent_len = len(line) - len(line_strip_ws)
        indent = line[:indent_len]
        state.indent = indent
        state.continuation_indent = indent
        state.at_line_start = True
        column = indent_len + 1
        state.first_column = column
        state.last_column = column
        return line_strip_ws


    def _parse_line_continue_last(self, line, at_line_start=False,
                                  whitespace=WHITESPACE,
                                  whitespace_or_comment_set=WHITESPACE_OR_COMMENT_SET):
        '''
        Reset everything after `_parse_line_get_next()`, to continue on
        with the next line after having consumed part of it.
        '''
        state = self._state
        if line[:1] not in whitespace_or_comment_set:
            state.first_column += 1
            state.last_column += 1
            return line
        line_strip_ws = line.lstrip(whitespace)
        if line_strip_ws == '':
            return self._parse_line_goto_next(line)
        state.first_lineno = state.last_lineno
        state.indent = state.continuation_indent
        state.at_line_start = at_line_start
        column = state.last_column + 1 + len(line) - len(line_strip_ws)
        state.first_column = column
        state.last_column = column
        return line_strip_ws


    def _parse_line_continue_last_to_next_significant_token(self, line, at_line_start=False,
                                                            comment_delim=COMMENT_DELIM,
                                                            whitespace=WHITESPACE,
                                                            whitespace_or_comment_set=WHITESPACE_OR_COMMENT_SET):
        '''
        Skip ahead to the next significant token (token other than whitespace
        and line comments).  Used in checking ahead after doc comments, tags,
        possible keys, etc. to see whether what follows is potentially valid
        or should trigger an immediate error.
        '''
        state = self._state
        if line[:1] not in whitespace_or_comment_set:
            state.first_column += 1
            state.last_column += 1
            return line
        line_strip_ws = line.lstrip(whitespace)
        if line_strip_ws == '':
            line = self._parse_line_goto_next(line_strip_ws)
            if line is not None and (line == '' or (line[:1] == comment_delim and line[1:2] != comment_delim)):
                while line is not None and (line == '' or (line[:1] == comment_delim and line[1:2] != comment_delim)):
                    if line == '':
                        line = self._parse_line_goto_next(line)
                    else:
                        line = self._parse_token_line_comment(line)
            return line
        else:
            state.first_lineno = state.last_lineno
            state.indent = state.continuation_indent
            state.at_line_start = at_line_start
            column = state.last_column + 1 + len(line) - len(line_strip_ws)
            state.first_column = column
            state.last_column = column
            if line_strip_ws[:1] == comment_delim and line_strip_ws[1:2] != comment_delim:
                line = self._parse_token_line_comment(line_strip_ws)
                if line is not None and (line == '' or (line[:1] == comment_delim and line[1:2] != comment_delim)):
                    while line is not None and (line == '' or (line[:1] == comment_delim and line[1:2] != comment_delim)):
                        if line == '':
                            line = self._parse_line_goto_next(line)
                        else:
                            line = self._parse_token_line_comment(line)
                return line
            else:
                return line_strip_ws


    def _check_bidi(self):
        if self._bidi_last_scalar_last_lineno == self._state.first_lineno and self._bidi_re.search(self._bidi_last_scalar_last_line):
            raise erring.ParseError('Cannot start a scalar object or comment on a line with a preceding object whose last line contains right-to-left code points', self._state)


    def _parse_token_open_noninline_list(self, line,
                                         open_noninline_list=OPEN_NONINLINE_LIST,
                                         path_separator=PATH_SEPARATOR):
        '''
        Open a non-inline list, or start a keypath that has a list as its
        first element.
        '''
        next_char = line[1:2]
        if next_char == open_noninline_list:
            raise erring.ParseError('Invalid double list opening "{0}"'.format(line[:2]), self._state)
        elif next_char == path_separator:
            return self._parse_token_unquoted_string_or_keypath(line)
        self._ast.open_noninline_list()
        return self._parse_line_continue_last(line, at_line_start=True)


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
        return self._parse_line_continue_last(line[1:])


    def _parse_token_inline_element_separator(self, line):
        '''
        Parse an element separator in a dict or list.
        '''
        self._ast.open_inline_collection()
        return self._parse_line_continue_last(line[1:])


    def _parse_delim_inline(self, name, delim, line, whitespace=WHITESPACE,
                            unicode_whitespace_set=UNICODE_WHITESPACE_SET):
        '''
        Find the closing delimiter for a quoted string or doc comment.
        '''
        state = self._state
        closing_delim_re, group = self._closing_delim_re_dict[delim]
        found = False
        m = closing_delim_re.search(line)
        if m is not None:
            found = True
            content = line[:m.start()]
            line = line[m.end():]
            state.last_column += 2*len(delim) + len(content)
        if found:
            return ((content,), content, line)
        content_lines = []
        content_lines.append(line)
        indent = state.indent
        line = self._parse_line_get_next(line)
        if line is None:
            raise erring.ParseError('Unterminated {0}'.format(name), state)
        line_strip_ws = line.lstrip(whitespace)
        continuation_indent = line[:len(line)-len(line_strip_ws)]
        state.continuation_indent = continuation_indent
        if not continuation_indent.startswith(indent):
            raise erring.IndentationError(state)
        line = line_strip_ws
        while True:
            if line == '':
                raise erring.ParseError('Unterminated {0}'.format(name), state)
            elif self._default_ignorable:
                if self._invalid_continuation_line_start_re.match(line):
                    state.last_column += len(continuation_indent)
                    if line[0] in whitespace:
                        raise erring.IndentationError(state)
                    else:
                        raise erring.ParseError('A Unicode whitespace or default ignorable code point was found where a wrapped line was expected to start', state)
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
                    state.last_column += len(continuation_indent) + m.end(group)
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
        uniform handling.  In many cases, line comments could actually be
        dealt with in those functions by simply calling
        `_parse_line_goto_next()`.  However, when default ignorables are
        present, additional processing is necessary.  No checking is done
        for `#` followed by `#`, since this function is only ever called with
        valid line comments.  This function receives the line with the
        leading `#` still intact.
        '''
        state = self._state
        state.line_comments = True
        if self._default_ignorable:
            m = self._invalid_ignorable_line_comment_re.search(line)
            if m is not None:
                state.last_column += len(line)
                # Index:  +1 for `#` at start of match
                index = m.start() + 1
                # Column:  +1 for `#` at start of match, zero indexing is fine
                column = state.first_column + m.start() + 1
                code_point = self.escape_unicode(line[index:index+1])
                erring.ParseError('Invalid pattern of comment characters "{0}" surrounding default ignorable code point "{1}" (column {2})'.format(comment_delim, code_point, column), state)
        return self._parse_line_goto_next('')


    def _parse_token_comment_delim(self, line, comment_delim=COMMENT_DELIM,
                                   max_delim_length=MAX_DELIM_LENGTH,
                                   ScalarNode=ScalarNode,
                                   invalid_next_token_set=DOC_COMMENT_INVALID_NEXT_TOKEN_SET):
        '''
        Parse inline comments.
        '''
        bidi = self._bidi
        if bidi:
            self._check_bidi()
        state = self._state
        line_delim_strip = line.lstrip(comment_delim)
        len_delim = len(line) - len(line_delim_strip)
        if len_delim == 1:
            return self._parse_token_line_comment(line)
        elif len_delim == 2:
            raise erring.ParseError('Invalid comment start "{0}"; use "{1}" for a line comment, or "{3}<comment>{3}" for a doc comment'.format(comment_delim*2, comment_delim, comment_delim*3), state)
        else:
            if state.in_tag:
                raise erring.ParseError('Doc comments are not allowed in tags', state)
            if len_delim % 3 != 0 or len_delim > max_delim_length:
                raise erring.ParseError('Doc comment delims must have lengths that are multiples of 3 and are no longer than {0} characters'.format(max_delim_length), state)
            delim = line[:len_delim]
            content_lines, content, line = self._parse_delim_inline('doc comment', delim, line_delim_strip)
            node = ScalarNode(state, delim=delim, block=False)
            if self._full_ast:
                node.raw_val = content_lines
            node.final_val = content
            node.resolved = True
            node.implicit_type = 'doc_comment'
            state.next_doc_comment = node
            if bidi:
                self._bidi_last_scalar_last_line = content_lines[-1]
                self._bidi_last_scalar_last_lineno = node.last_lineno
            line = self._parse_line_continue_last_to_next_significant_token(line)
            if not node.inline and node.at_line_start and node.last_lineno == state.first_lineno:
                raise erring.ParseError('In non-inline mode, doc comments that start a line cannot be followed immediately by data', node)
            if line is not None and line[0] in invalid_next_token_set:
                raise erring.ParseError('Doc comment was never applied to an object', node, state)
            return line


    def _parse_token_literal_string_delim(self, line,
                                          literal_string_delim=LITERAL_STRING_DELIM,
                                          max_delim_length=MAX_DELIM_LENGTH,
                                          ScalarNode=ScalarNode,
                                          assign_key_val=ASSIGN_KEY_VAL):
        '''
        Parse inline literal string.
        '''
        bidi = self._bidi
        if bidi:
            self._check_bidi()
        state = self._state
        line_delim_strip = line.lstrip(literal_string_delim)
        len_delim = len(line) - len(line_delim_strip)
        if len_delim > 3 and (len_delim % 3 != 0 or len_delim > max_delim_length):
            raise erring.ParseError('Literal string delims must have lengths of 1 or 2, or multiples of 3 that are no longer than {0} characters'.format(max_delim_length), state)
        delim = line[:len_delim]
        content_lines, content, line = self._parse_delim_inline('literal string', delim, line_delim_strip)
        node = ScalarNode(state, delim=delim, block=False)
        if self._full_ast:
            node.raw_val = content_lines
        node.final_val = content
        node.resolved = True
        node.implicit_type = 'literal_string'
        if bidi:
            self._bidi_last_scalar_last_line = content_lines[-1]
            self._bidi_last_scalar_last_lineno = node.last_lineno
        line = self._parse_line_continue_last_to_next_significant_token(line)
        if line is not None and line[:1] == assign_key_val:
            if not state.inline and node.last_lineno != state.first_lineno:
                raise erring.ParseError('In non-inline mode, a key and the following "{0}" must be on the same line'.format(assign_key_val), state, node)
            self._ast.append_scalar_key(node)
            line = self._parse_line_continue_last(line[1:])
        else:
            self._ast.append_scalar_val(node)
        return line
        # #### check for default ignorables by delimiters?


    def _parse_token_unquoted_string_or_keypath(self, line):
        raise NotImplementedError


    def _parse_token_block_prefix(self, line):
        raise NotImplementedError


    def _parse_token_escaped_string_singlequote_delim(self, line):
        raise NotImplementedError


    def _parse_token_escaped_string_doublequote_delim(self, line):
        raise NotImplementedError


    def _parse_token_alias_prefix(self, line):
        raise NotImplementedError


    def _parse_token_number_or_number_unit(self, line):
        raise NotImplementedError
