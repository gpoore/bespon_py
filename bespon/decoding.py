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
from .astnodes import ScalarNode

if sys.version_info.major == 2:
    str = unicode
    __chr__ = chr
    chr = unichr

# pylint:  disable=W0622
if sys.maxunicode == 0xFFFF:
    chr = coding.chr_surrogate
    ord = coding.ord_surrogate
# pylint:  enable=W0622




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
                 'next_doc_comment', 'line_comments']
    def __init__(self, source=None, source_include_depth=0,
                 source_initial_nesting_depth=0,
                 indent=None, at_line_start=True,
                 inline=False, inline_indent=None,
                 first_lineno=1, first_column=1):
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
        parse_token = collections.defaultdict(self._parse_token_unquoted_string_or_keypath)
        token_functions = {'comment': self._parse_token_comment,
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
        for token_name, func in token_functions:
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
            bidi = grammar.RE_GRAMMAR['bidi']
            ignorable = grammar.RE_GRAMMAR['default_ignorable']
            invalid_literal_or_bidi_or_ignorable = '(?P<invalid_literal>{0})|(?P<bidi>{1})|(?P<default_ignorable>{2})'.format(invalid_literal, bidi, ignorable)
            self._invalid_literal_or_bidi_or_ignorable_re = re.compile(invalid_literal_or_bidi_or_default_ignorable)
            invalid_literal_or_bidi = '(?P<invalid_literal>{0})|(?P<bidi>{1})'.format(invalid_literal, bidi)
            self._invalid_literal_or_bidi_re = re.compile(invalid_literal_or_bidi)
            invalid_literal_or_default_ignorable = '(?P<invalid_literal>{0})|(?P<default_ignorable>{1})'.format(invalid_literal, ignorable)
            self._invalid_literal_or_default_ignorable_re = re.compile(invalid_literal_or_default_ignorable)

        self._newline_re = re.compile(grammar.RE_GRAMMAR['newline'])

        # Dict of regexes for identifying closing delimiters for inline
        # escaped strings.  Needed regexes are automatically generated on the
        # fly.  Note that opening delimiters are handled by normal string
        # methods, as are closing delimiters for block strings.  Because
        # block string delimiters are enclosed within `|` and `/`, lookbehind
        # and lookahead for escapes or other delimiter characters is unneeded.
        escaped_string_singlequote_delim = grammar.LIT_GRAMMAR['escaped_string_singlequote_delim'],
        escaped_string_doublequote_delim = grammar.LIT_GRAMMAR['escaped_string_doublequote_delim'],
        literal_string_delim = grammar.LIT_GRAMMAR['literal_string_delim']
        comment_delim = grammar.LIT_GRAMMAR['comment_delim']
        def gen_closing_delim_regex(delim):
            c_0 = delim[0]
            if c_0 == escaped_string_singlequote_delim or c_0 == escaped_string_doublequote_delim:
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
            elif c_0 == literal_string_delim or c_0 == comment_delim:
                if delim == literal_string_delim or delim == comment_delim:
                    pattern = r'(?<!{delim_char}){delim_char}(?!{delim_char})'.format(delim_char=re.escape(c_0))
                else:
                    n = len(delim)
                    pattern = r'(?<!{delim_char}){delim_char}{{{n}}}(?!{delim_char})'.format(delim_char=re.escape(c_0), n=n)
            else:
                raise ValueError
            return re.compile(pattern)
        self._closing_delim_re_dict = tooling.keydefaultdict(gen_closing_delim_regex)

        # Regexes for working with default ignorables
        default_ignorable = grammar.RE_GRAMMAR['default_ignorable']
        invalid_di_pattern = '{delim}{di}+{delim}'
        self._invalid_default_ignorable_singlequote_re = re.compile(invalid_di_pattern.format(delim=re.escape(escaped_string_singlequote_delim), di=default_ignorable))
        self._invalid_default_ignorable_doublequote_re = re.compile(invalid_di_pattern.format(delim=re.escape(escaped_string_doublequote_delim), di=default_ignorable))
        self._invalid_default_ignorable_literal_re = re.compile(invalid_di_pattern.format(delim=re.escape(literal_string_delim), di=default_ignorable))
        self._invalid_default_ignorable_comment_re = re.compile(invalid_di_pattern.format(delim=re.escape(comment_delim), di=default_ignorable))




    @staticmethod
    def _unwrap_inline_string(s_list, unicode_whitespace_set=set(grammar.LIT_GRAMMAR['unicode_whitespace'])):
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
        self._default_ignorable = False
        # A single, leading BOM is allowed, but for simplicity the regex
        # doesn't account for that, so a manual check is needed.
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
            raw_source = string_or_bytes
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

        data = self._parse_lines(line_iter)

        return data


    def _parse_lines(self, line_iter):
        '''
        Process lines from source into abstract syntax tree (AST).  Then
        process the AST into standard Python objects.
        '''
        state = State()
        ast = Ast(state)

        # Start by extracting the first line and stripping any BOM
        line = next(line_iter)
        if line[:1] == '\uFEFF':
            line = line[1:]
            state.first_column += 1
            state.last_column += 1

        self._ast = ast
        self._state = state
        self._line_iter = line_iter

        parse_token = self._parse_token
        while line is not None:
            line = parse_token[line[:1]](line)

        self._ast = None
        self._state = None
        self._line_iter = None

        ast.finalize()
        if not ast.root:
            raise erring.ParseError('There was no data to load', None)

        data = ast.root.final_val

        return data


    def _parse_line_goto_next(self, line, next=next,
                              whitespace=grammar.LIT_GRAMMAR['whitespace']):
        '''
        Go to next line.  Used when parsing completes on a line, and no
        additional parsing is needed for that line.

        The `line` argument is needed so that this can be used in the
        `_parse_lines` dict of functions as the value for the empty string
        key.  When the function is used directly as part of other parsing
        functions, this argument isn't actually needed.  However, it is kept
        mandatory to maintain parallelism between all of the `_parse_line_*()`
        functions, since some of these do require a `line` argument.
        '''
        line = next(self._line_iter, None)
        if line is None:
            return line
        state = self._state
        lineno = state.last_lineno + 1
        state.first_lineno = lineno
        state.last_lineno = lineno
        line_ws_strip = line.lstrip(whitespace)
        indent_len = len(line) - len(line_ws_strip)
        indent = line[:indent_len]
        state.indent = indent
        state.continuation_indent = indent
        state.at_line_start = True
        column = indent_len + 1
        state.first_column = column
        state.last_column = column
        return line_ws_strip


    def _parse_line_get_next(self, line, next=next):
        '''
        Get next line.  For use in lookahead in string scanning, etc.
        '''
        state = self._state
        line = next(self._line_iter, None)
        state.last_lineno += 1
        state.last_column = 1
        return line


    def _parse_line_start_last(self, line, whitespace=grammar.LIT_GRAMMAR['whitespace']):
        '''
        Reset everything after `_parse_line_get_next()`, so that it's
        equivalent to using `_parse_line_goto_next()`.  Useful when
        `_parse_token_get_next_line()` is used for lookahead, but nothing is
        consumed.
        '''
        if line is None:
            return line
        state = self._state
        state.first_lineno = state.last_lineno
        line_ws_strip = line.lstrip(whitespace)
        indent_len = len(line) - len(line_ws_strip)
        indent = line[:indent_len]
        state.indent = indent
        state.continuation_indent = indent
        state.at_line_start = True
        column = indent_len + 1
        state.first_column = column
        state.last_column = column
        return line_ws_strip


    def _parse_line_continue_last(self, line, at_line_start=False,
                                  whitespace=grammar.LIT_GRAMMAR['whitespace']):
        '''
        Reset everything after `_parse_line_get_next()`, to continue on
        with the next line after having consumed part of it.
        '''
        line_ws_strip = line.lstrip(whitespace)
        if line_ws_strip == '':
            return self._parse_line_goto_next(line)
        state = self._state
        state.first_lineno = state.last_lineno
        state.indent = state.continuation_indent
        state.at_line_start = at_line_start
        column = state.last_column + 1 + len(line) - len(line_ws_strip)
        state.first_column = column
        state.last_column = column
        return line


    def _parse_line_continue_last_to_next_significant_token(self, line, at_line_start=False,
                                                            comment_delim=grammar.LIT_GRAMMAR['comment_delim'],
                                                            whitespace=grammar.LIT_GRAMMAR['whitespace']):
        '''
        Skip ahead to the next significant token (token other than whitespace
        and line comments).  Used in checking ahead after doc comments, tags,
        possible keys, etc. to see whether what follows is potentially valid
        or should trigger an immediate error.
        '''
        state = self._state
        line_ws_strip = line.lstrip(whitespace)
        if line_ws_strip == '':
            line = self._parse_line_goto_next(line_ws_strip)
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
            column = state.last_column + 1 + len(line) - len(line_ws_strip)
            state.first_column = column
            state.last_column = column
            if line_ws_strip[:1] == comment_delim and line_ws_strip[1:2] != comment_delim:
                line = self._parse_token_line_comment(line_ws_strip)
                if line is not None and (line == '' or (line[:1] == comment_delim and line[1:2] != comment_delim)):
                    while line is not None and (line == '' or (line[:1] == comment_delim and line[1:2] != comment_delim)):
                        if line == '':
                            line = self._parse_line_goto_next(line)
                        else:
                            line = self._parse_token_line_comment(line)
                return line
            else:
                return line_ws_strip


    def _parse_delim_inline_literal(self, name, delim, line,
                                    whitespace=grammar.LIT_GRAMMAR['whitespace']):
        '''
        Find the closing delimiter for an inline literal element that contains
        no escapes (inline literal string or inline doc comment).
        '''
        state = self._state
        closing_delim_re = self._closing_delim_re_dict[delim]
        found = False
        if delim in line:
            m = closing_delim_re.search(line)
            if m is not None:
                found = True
                content = line[:m.start()]
                line = line[m.end():]
                state.last_column += 2*len(delim) + len(content)
        if found:
            return (content, content, line)
        raw_content_list = []
        raw_content_list.append(line)
        indent = state.indent
        line = self._parse_line_get_next(line)
        if line is None:
            raise erring.ParseError('Unterminated {0}'.format(name), state)
        line_strip_ws = line.lstrip(whitespace)
        if line_strip_ws == '':
            raise erring.ParseError('Unterminated {0}'.format(name), state)
        continuation_indent = line[:len(line)-len(line_strip_ws)]
        len_continuation_indent = len(continuation_indent)
        state.continuation_indent = continuation_indent
        if not indent.startswith(continuation_indent):
            raise erring.IndentationError(state)
        while True:
            if delim in line:
                m = closing_delim_re.search(line)
                if m is not None:
                    line_content = line[len_continuation_indent:m.start()]
                    line = line[m.end():]
                    raw_content_list.append(line_content)
                    state.last_column += m.end()
                    break
            raw_content_list.append(line)
            line = self._parse_line_get_next(line)
            if line is None:
                raise erring.ParseError('Unterminated {0}'.format(name), state)
            if not line.startswith(continuation_indent) or line[len_continuation_indent:len_continuation_indent+1] in whitespace:
                raise erring.IndentationError(state)
        return (raw_content_list, self._unwrap_inline_string(raw_content_list), line)


    def _parse_token_line_comment(self, line,
                                  comment_delim=grammar.LIT_GRAMMAR['comment_delim']):
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
            m = self._invalid_default_ignorable_comment_re.search(line)
            if m is not None:
                # Index:  +1 for `#` at start of match
                index = m.start() + 1
                # Column:  +1 for `#` at start of match, zero indexing is fine
                column = state.first_column + m.start() + 1
                code_point = self.escape_unicode(line[index:index+1])
                erring.ParseError('Invalid pattern of comment characters "{0}" surrounding default ignorable code point "{1}" (column {2})'.format(comment_delim, code_point, column), state)
        return self._parse_line_goto_next('')



    def _parse_token_comment(self, line,
                             comment_delim=grammar.LIT_GRAMMAR['comment_delim'],
                             max_delim_length=grammar.PARAMS['max_delim_length'],
                             ScalarNode=ScalarNode,
                             invalid_next_token_set=set(grammar.LIT_GRAMMAR['doc_comment_invalid_next_token'])):
        '''
        Parse inline comments.
        '''
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
            raw_content, content, line = self._parse_delim_inline_literal('doc comment', delim, line_delim_strip)
            node = ScalarNode(state, delim=delim, block=False)
            if self._full_ast:
                node.raw_val = raw_content
            node.final_val = content
            node.implicit_type = 'doc_comment'
            state.next_doc_comment = node
            line = self._parse_line_continue_last_to_next_significant_token(line)
            if not node.inline and node.at_line_start and node.last_lineno == state.first_lineno:
                raise erring.ParseError('In non-inline mode, doc comments that start a line cannot be followed immediately by data', node)
            if line is not None and line[0] in invalid_next_token_set:
                raise erring.ParseError('Doc comment was never applied to an object', node, state)
            return line


    def _parse_token_open_noninline_list(self, line,
                                         open_noninline_list=grammar.LIT_GRAMMAR['open_noninline_list'],
                                         path_separator=grammar.LIT_GRAMMAR['path_separator']):
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
        return self._parse_line_continue_last_to_next_significant_token(line, at_line_start=True)


    def _start_inline_dict(self, line):
        '''
        Start an inline dict.
        '''
        self._ast.start_dict_inline()
        return self._parse_line_continue_last_to_next_significant_token(line)


    def _parse_line_start_dict(self, line):
        '''
        Parse line segment beginning with opening curly brace.
        '''
        m_keypath = self._keypath_re.match(line)
        if m_keypath:
            line = self._parse_line_keypath(line, m_keypath)
        else:
            state = self.state
            if state.inline and not state.indent.startswith(state.inline_indent):
                raise erring.ParseError('Indentation error', state.traceback)
            elif not state.inline:
                state.start_inline()
            self._ast.append_collection('dict', state.inline_indent)
            self._ast.pos.open = True
            line = line[1:].lstrip(self._whitespace_str)
            if not line:
                line = self._parse_line_goto_next()
        return line


    def _parse_line_start_type(self, line):
        '''
        Parse explicit typing.
        '''
        state = self.state
        if state.inline:
            indent = state.inline_indent
        else:
            indent = state.indent
        line = line[1:].lstrip(self._whitespace_str)
        kvarg_list = []
        next_key = None
        awaiting_key = True
        awaiting_val = False
        while True:
            if line == '':
                while line == '':
                    line = self._parse_line_get_next()
                    if line is None:
                        raise erring.ParseError('Text ended while looking for end of explicit type declaration', state.traceback)
                    line_lstrip_whitespace = line.lstrip(self._whitespace_str)
                    if line_lstrip_whitespace and not line.startswith(indent):
                        raise erring.ParseError('Indentation error in explicit type declaration', state.traceback)
                    line = line_lstrip_whitespace

            if line[:2] == self._reserved_chars_end_type_with_suffix:
                if awaiting_val:
                    raise erring.ParseError('Invalid explicit type declaration; missing value in key-value pair', state.traceback)
                if next_key is not None:
                    kvarg_list.append((next_key, True))
                state.set_type(kvarg_list)
                line = line[2:].lstrip(self._whitespace_str)
                self._parse_line_continue_next()
                break
            elif line[:1] == self._reserved_chars_separator:
                if awaiting_key:
                    raise erring.ParseError('Invalid explicit type declaration; extra "{0}"'.format(self._reserved_chars_separator), state.traceback)
                if awaiting_val:
                    raise erring.ParseError('Invalid explicit type declaration; missing value in key-value pair', state.traceback)
                if next_key is not None:
                    kvarg_list.append((next_key, True))
                    next_key = None
                awaiting_key = True
                line = line[1:].lstrip(self._whitespace_str)
            elif line[:1] == self._reserved_chars_assign_key_val:
                if next_key is None:
                    raise erring.ParseError('Invalid explicit type declaration; missing key in key-value pair', state.traceback)
                if awaiting_val:
                    raise erring.ParseError('Invalid explicit type declaration; missing value in key-value pair', state.traceback)
                awaiting_val = True
                line = line[1:].lstrip(self._whitespace_str)
            elif awaiting_val:
                m = self._boolean_reserved_words_re.match(line)
                if m:
                    w = m.group(0)
                    v = self._reserved_words[w]
                    awaiting_val = False
                    kvarg_list.append((next_key, v))
                    next_key = None
                    line = line[m.end():].lstrip(self._whitespace_str)
                else:
                    raise erring.ParseError('Invalid explicit type declaration, or type declaration using unsupported features', state.traceback)
            elif awaiting_key:
                m = self._type_key_re.match(line)
                if m:
                    next_key = m.group(0)
                    line = line[m.end():].lstrip(self._whitespace_str)
                    awaiting_key = False
                else:
                    raise erring.ParseError('Invalid explicit type declaration', state.traceback)
            else:
                raise erring.ParseError('Invalid explicit type declaration, or type declaration using unsupported features', state.traceback)
        return line


    def _parse_line_end_type(self, line):
        '''
        Parse line segment beginning with closing parenthesis.
        '''
        raise erring.ParseError('Unexpected closing parenthesis', self.state.traceback)


    def _parse_line_start_list(self, line):
        '''
        Parse line segment beginning with opening square bracket.
        '''
        m_keypath = self._keypath_re.match(line)
        if m_keypath:
            line = self._parse_line_keypath(line, m_keypath)
        else:
            state = self.state
            ######## Maybe move logic to Ast?
            if state.inline and not state.indent.startswith(state.inline_indent):
                raise erring.ParseError('Indentation error', state.traceback)
            elif not state.inline:
                state.start_inline()
            self._ast.append_collection('list', state.inline_indent)
            self._ast.pos.open = True
            line = line[1:].lstrip(self._whitespace_str)
            if not line:
                line = self._parse_line_goto_next()
        return line

    def _parse_line_end_list(self, line):
        '''
        Parse line segment beginning with closing square bracket.
        '''
        self._ast.end_list_inline()
        line = line[1:].lstrip(self._whitespace_str)
        if not line:
            line = self._parse_line_goto_next()
        return line




    def _parse_line_end_dict(self, line):
        '''
        Parse line segment beginning with closing curly brace.
        '''
        self._ast.end_dict_inline()
        line = line[1:].lstrip(self._whitespace_str)
        if not line:
            line = self._parse_line_goto_next()
        return line


    def _parse_line_literal_string(self, line):
        '''
        Parse single-quoted string.
        '''
        len_delim = len(line)
        line = line.lstrip("'")
        len_delim -= len(line)
        delim = "'"*len_delim
        if len(delim) == 1:
            s, line = line.split(delim, 1)
            if line[:1] == delim:
                raise erring.ParseError('Invalid quotation mark following end of quoted string', self.state.traceback)
        elif len(delim) == 2:
            s = ''
        else:
            end_delim_re = self._closing_delim_re_dict[delim]
            match_group_num = 0
            s, line = self._parse_line_get_quoted_string(line, delim, end_delim_re, match_group_num)
        return self._parse_line_resolve_quoted_string(line, s, delim)

    def _parse_line_escaped_string(self, line):
        '''
        Parse double-quoted string.
        '''
        len_delim = len(line)
        line = line.lstrip('"')
        len_delim -= len(line)
        delim = '"'*len_delim
        if delim == '""':
            s = ''
        else:
            end_delim_re = self._closing_delim_re_dict[delim]
            match_group_num = 1
            m = end_delim_re.match(line)
            if m:
                s = line[:m.start(match_group_num)]
                line = line[m.end(match_group_num):]
                if m.end(match_group_num) - m.start(match_group_num) > len(delim):
                    raise erring.ParseError('A block string may not begin and end on the same line', self.state.traceback)
            else:
                s, line = self._parse_line_get_quoted_string(line, delim, end_delim_re, match_group_num)
        return self._parse_line_resolve_quoted_string(line, s, delim)


    def _parse_line_get_quoted_string(self, line, delim, end_delim_re, match_group_num):
        '''
        Parse a quoted string, once the opening delim has been determined
        and stripped, and a regex for the closing delim has been assembled.
        '''
        s_lines = [line]
        # No need to check for consistent indentation here; that is done
        # during determination of `effective_indent`
        state = self.state
        if state.at_line_start:
            indent = state.indent
        elif state.inline:
            indent = state.inline_indent
        elif state.type:
            indent = state.type_indent
        else:
            indent = state.indent
        while True:
            line = self._parse_line_get_next()
            if line is None:
                raise erring.ParseError('Text ended while scanning quoted string', state.traceback)
            if not line.startswith(indent) and line.lstrip(self._whitespace_str):
                raise erring.ParseError('Indentation error within quoted string', state.traceback)
            if delim not in line:
                s_lines.append(line)
            else:
                m = end_delim_re.search(line)
                if not m:
                    s_lines.append(line)
                else:
                    end_delim = m.group(match_group_num)
                    s_lines.append(line[:m.start(match_group_num)])
                    line = line[m.end(match_group_num):].lstrip(self._whitespace_str)
                    break
        if len(delim) == len(end_delim):
            # Make sure indentation is consistent and there are no empty lines
            if len(s_lines) > 2:
                for s_line in s_lines[1:-1]:
                    if not s_line.lstrip(self._unicode_whitespace_str):
                        raise erring.ParseError('Inline strings cannot contain empty lines', state.traceback)
                indent = s_lines[1][:len(s_lines[1].lstrip(self._indents_str))]
                len_indent = len(indent)
                for n, s_line in enumerate(s_lines[1:]):
                    if not s_line.startswith(indent) or s_line[len_indent:len_indent+1] in self._unicode_whitespace:
                        raise erring.ParseError('Inconsistent indentation or leading Unicode whitespace within inline string', state.traceback)
                    s_lines[n+1] = s_line[len_indent:]
            else:
                s_lines[1] = s_lines[1].lstrip(self._indents_str)
            # Take care of any leading/trailing spaces that separate delimiter
            # characters from identical characters in string.
            if len(delim) >= 3:
                dc = delim[0]
                if s_lines[0][:1] in self._spaces and s_lines[0].lstrip(self._spaces_str)[:1] == dc:
                    s_lines[0] = s_lines[0][1:]
                if s_lines[-1][-1:] in self._spaces and s_lines[-1].rstrip(self._spaces_str)[-1:] == dc:
                    s_lines[-1] = s_lines[-1][:-1]
            # Unwrap
            s = self._unwrap_inline(s_lines)
        else:
            if len(delim) < len(end_delim) - 2:
                raise erring.ParseError('Invalid ending delimiter for block string', state.traceback)
            if s_lines[0].lstrip(self._whitespace_str):
                raise erring.ParseError('Characters are not allowed immediately after the opening delimiter of a block string', state.traceback)
            if s_lines[-1].lstrip(self._indents_str):
                raise erring.ParseError('Characters are not allowed immediately before the closing delimiter of a block string', state.traceback)
            indent = s_lines[-1]
            len_indent = len(indent)
            if state.at_line_start and state.indent != indent:
                raise erring.ParseError('Opening and closing delimiters for block string do not have matching indentation', state.traceback)
            for n, s_line in enumerate(s_lines[1:-1]):
                if s_line.startswith(indent):
                    s_lines[n+1] = s_line[len_indent:]
                else:
                    if s_line.lstrip(self._whitespace_str):
                        raise erring.ParseError('Inconsistent indent in block string', state.traceback)
                    s_lines[n+1] = line.lstrip(self._indents_str)
            if len(delim) == len(end_delim) - 2:
                s_lines[-2] = s_lines[-2].rstrip(self._newline_chars_str)
            s = ''.join(s_lines[1:-1])
        return (s, line)


    def _parse_line_resolve_quoted_string(self, line, s, delim):
        state = self.state
        if state.type and state.type_obj in self.__bytes_parsers:
            s = self._unicodefilter.non_ascii_to_ascii_newlines(s)
            s = self._unicode_to_bytes(s)
            if delim[0] == '"':
                s = self._unicodefilter.unescape_bytes(s)
        elif delim[0] == '"':
            s = self._unicodefilter.unescape(s)

        if state.type:
            try:
                s = self._string_parsers[self.state.type_obj](s)
            except KeyError:
                raise erring.ParseError('Unknown explicit type "{0}" applied to string'.format(state.type_obj), state.traceback_type)
            except Exception as e:
                raise erring.ParseError('Could not convert quoted string to type "{0}":\n  {1}'.format(state.type_obj, e), state.traceback)

        state.set_stringlike(s)
        if state.start_lineno == state.end_lineno:
            state.at_line_start = False
        else:
            self._parse_line_continue_next()

        line = line.lstrip(self._whitespace_str)
        if not line or line[:1] == '%':
            while line is not None:
                if line[:1] == '%':
                    line = self._parse_line_comment(line)
                else:
                    line = line.lstrip(self._whitespace_str)
                    if not line:
                        line = self._parse_line_goto_next()
                    else:
                        break
        if line is not None and line[:1] == '=' and line[1:2] != '=':
            if state.inline:
                if not state.indent.startswith(state.inline_indent):
                    raise erring.ParseError('Indentation error', self.state.traceback)
            else:
                if state.stringlike_end_lineno != self.state.start_lineno:
                    raise erring.ParseError('In a key-value pair in non-inline syntax, the equals sign "=" must follow the key on the same line', self.state.traceback)
            line = line[1:].lstrip(self._whitespace_str)
            self._ast.append_stringlike_key()
        else:
            self._ast.append_stringlike()
        return line


    def _parse_line_assign_key_val(self, line):
        '''
        Parse line segment beginning with equals sign.
        '''
        m = self._opening_delim_equals_re.match(line)
        delim_len = len(m.group(0))
        if delim_len == 1:
            raise erring.ParseError('Unexpected equals sign "="', self.state.traceback)
        elif delim_len < 3:
            raise erring.ParseError('Unexpected series of equals signs', self.state.traceback)
        else:
            if not self.state.at_line_start:
                raise erring.ParseError('Must be at beginning of line to specify a data path', self.state.traceback)
            raise erring.ParseError('Unsupported branch')
        return line

    def _parse_line_list_item(self, line):
        nc = line[1:2]
        if nc != '' and nc not in self._whitespace:
            line = self._parse_line_unquoted_string(line)
        else:
            # Opening list involves all needed checks for attempting to open
            # two lists on the same line, being in inline syntax, etc.
            self._ast.open_list_non_inline()
            line_lstrip_whitespace = line[1:].lstrip(self._whitespace_str)
            indent_after_list_item = line[1:len(line)-len(line_lstrip_whitespace)]
            line = line_lstrip_whitespace
            if line:
                if self.state.indent[-1:] == '\t' and indent_after_list_item[:1] == '\t':
                    self.state.indent += indent_after_list_item
                else:
                    self.state.indent += '\x20' + indent_after_list_item
            else:
                line = self._parse_line_goto_next()
        return line

    def _parse_line_separator(self, line):
        self._ast.open_collection_inline()
        line = line[1:].lstrip(self._whitespace_str)
        if not line:
            line = self._parse_line_goto_next()
        return line

    def _parse_line_pipe(self, line):
        m = self._opening_delim_pipe_re.match(line)
        if not m:
            if line[1:2] == '\x20':
                self.state.set_stringlike(line[2:])
                line = self._parse_line_goto_next()
            elif line[1:2] in self._unicode_whitespace:
                raise erring.ParseError('Invalid whitespace character after pipe "|"')
            else:
                line = self._parse_line_unquoted_string(line)
        else:
            delim = m.group(0)
            if not self.state.at_line_start:
                raise erring.ParseError('Pipe-quoted strings ( {0} ) are only allowed at the beginning of lines'.format(delim), self.state.traceback)
            if line[len(delim):].lstrip(self._whitespace_str):
                raise erring.ParseError('Cannot have characters after opening delimiter of pipe-quoted string')
            line = self._parse_line_get_next()
            end_delim_re = self._closing_delim_re_dict[delim]
            indent = self.state.indent
            len_indent = len(indent)
            pattern = indent + delim
            s_list = []
            while True:
                if line.startswith(pattern):
                    m = end_delim_re.find(line)
                    if not m or len(delim) < len(m.group(0)) - 2:
                        raise erring.ParseError('Invalid closing delimiter for pipe-quoted string', self.state.traceback)
                    if not s_list:
                        s = ''
                    else:
                        end_delim = m.group(0)
                        if len(delim) == len(end_delim):
                            for s_line in s_list:
                                if not s_line.lstrip(self._unicode_whitespace_str):
                                    raise erring.ParseError('Wrapped pipe-quoted string cannot contain empty lines; use block pipe-quoted string instead')
                            line_indent = s_list[0][len(indent)+1:]
                            len_line_indent = len(line_indent)
                            if not line_indent.lstrip(self._indents_str):
                                raise erring.ParseError('Invalid indentation in pipe-quoted string', self.state.traceback)
                            for n, s_line in enumerate(s_list):
                                if not s_line.startswith(line_indent) or s_line[len_line_indent:len_line_indent+1] in self._unicode_whitespace:
                                    raise erring.ParseError('Invalid indentation in pipe-quoted string', self.state.traceback)
                                s_list[n] = s_line[len_line_indent:]
                            s = self._unwrap_inline(s_list)
                        else:
                            if len(delim) == len(end_delim) - 2:
                                s_list[-1] = s_list[-1].rstrip(self._newline_chars_str)
                            for s_line in s_list:
                                if s_line.startswith(indent) and s_line[len_indent:len_indent+1] in self._indents:
                                    line_indent = s_line[:len_indent+1]
                                    break
                            len_line_indent = len(line_indent)
                            for n, s_line in enumerate(s_list):
                                if s_line.startswith(line_indent):
                                    s_list[n] = s_line[len_line_indent:]
                                else:
                                    if s_line.lstrip(self._whitespace_str):
                                        raise erring.ParseError('Invalid indentation in pipe-quoted block string', self.state.traceback)
                                    s_list[n] = s_line.lstrip(self._indents_str)
                            s = ''.join(s_list)
                    break
                else:
                    s_list.append(line)
                    line = self._parse_line_get_next()
                    if line is None:
                        raise erring.ParseError('Text ended while scanning pipe-quoted string', self.state.traceback)
            self.state.set_stringlike(s)
            line = line.lstrip(self._whitespace_str)
            if not line:
                line = self._parse_line_goto_next()
        return line


    def _parse_line_whitespace(self, line):
        '''
        Parse line segment beginning with whitespace.
        '''
        raise erring.ParseError('Unexpected whitespace; if you are seeing this message, there is a bug in the parser', self.state.traceback)


    def _parse_line_invalid_unquoted(self, line):
        '''
        Parse line segment beginning with code point >= 128 when unquoted
        Unicode is not allowed.
        '''
        raise erring.ParseError('Unquoted non-ASCII characters are not allowed by default; retry with "unquoted_unicode" = True if the source is trustworthy/appropriate security measures are in place', self.state.traceback)


    def _parse_line_unquoted_string(self, line):
        state = self.state
        check_kv = True
        m = self._end_unquoted_string_re.search(line)
        if m:
            s = line[:m.start()].rstrip(self._whitespace_str)
            if s == '':
                if not self._unquoted_unicode__current and ord(line[:1]) >= 128:
                    raise erring.ParseError('Encountered unquoted Unicode when "unquoted_unicode" = False', state.traceback)
                else:
                    raise erring.ParseError('Unquoted string of length zero; if you are seeing this message, there is a bug in the parser', state.traceback)
            line = line[m.start():]
            state.set_stringlike(s)
            state.at_line_start = False
        else:
            s = line.rstrip(self._whitespace_str)
            s_line_0 = line
            state.set_stringlike(s)
            line = self._parse_line_goto_next()
            indent = None
            if state.stringlike_at_line_start:
                indent = state.stringlike_indent
            elif line is not None and line:
                if state.indent.startswith(state.stringlike_indent) and len(state.indent) > len(state.stringlike_indent):
                    indent = state.indent
                else:
                    check_kv = False
            if indent is not None:
                s_list = [s_line_0]
                len_indent = len(indent)
                while line is not None and line and state.indent == indent:
                    m = self._end_unquoted_string_re.search(line)
                    if m:
                        if m.start() == 0:
                            break
                        s_list.append(line[:m.start()])
                        line = line[m.start():]
                        state.stringlike_end_lineno = state.start_lineno
                        line = self._parse_line_continue_next()
                        break
                    else:
                        s_list.append(line)
                        state.stringlike_end_lineno = state.start_lineno
                        line = self._parse_line_goto_next()

                # Leading whitespace will have already been stripped
                s_list[-1] = s_list[-1].rstrip(self._whitespace_str)
                for s_line in s_list:
                    if s_line[:1] in self._unicode_whitespace:
                        raise erring.ParseError('Unquoted strings cannot contain lines beginning with Unicode whitespace characters', state.traceback)
                s = self._unwrap_inline(s_list)
                state.stringlike_obj = s

        if s[0] in self._unicode_whitespace or s[-1] in self._unicode_whitespace:
            raise erring.ParseError('Unquoted strings cannot begin or end with Unicode whitespace characters', state.traceback)

        # If typed string, update `stringlike_obj`
        # Could use `set_stringlike` after this, but the current approach
        # is more efficient for multi-line unquoted strings
        if state.type:
            if not self._unquoted_strings__current and not self._reserved_words_int_float_invalid_re.match(s):
                raise erring.ParseError('Encountered unquoted string when "unquoted_strings" = False')
            if state.type_obj in self.__bytes_parsers:
                s = self._unicode_to_bytes(s)
            try:
                state.stringlike_obj = self._string_parsers[state.type_obj](s)
            except Exception as e:
                raise erring.ParseError('Could not convert unquoted string to type "{0}":\n  {1}'.format(state.type, e), state.traceback)
        elif s[0] in self._reserved_words_int_float_starting_chars and s[-1] in self._reserved_words_int_float_ending_chars:
            m = self._reserved_words_int_float_invalid_re.match(s)
            if m:
                g = m.lastgroup
                if g == 'reserved_words':
                    try:
                        s = self._reserved_words[s]
                    except KeyError:
                        raise erring.ParseError('Invalid capitalization for reserved word "{0}"'.format(s), state.traceback)
                elif g.startswith('num_int'):
                    s = self._string_parsers['int'](s, g.replace('_', '.'))
                elif g.startswith('num_float'):
                    s = self._string_parsers['float'](s, g.replace('_', '.'))
                else:
                    raise erring.ParseError('Invalid {0} literal'.format(g.split('_', 1)[1]), state.traceback)
                state.stringlike_obj = s
            elif not self._unquoted_strings__current:
                raise erring.ParseError('Encountered unquoted string when "unquoted_strings" = False', state.traceback)
        elif not self._unquoted_strings__current:
            raise erring.ParseError('Encountered unquoted string when "unquoted_strings" = False', state.traceback)

        if not check_kv:
            self._ast.append_stringlike()
        else:
            if not line or line[:1] == '%':
                while line is not None:
                    if line[:1] == '%':
                        line = self._parse_line_comment(line)
                    else:
                        line = line.lstrip(self._whitespace_str)
                        if not line:
                            line = self._parse_line_goto_next()
                        else:
                            break
            if line is not None and line[:1] == '=' and line[1:2] != '=':
                if state.inline:
                    if not state.indent.startswith(state.inline_indent):
                        raise erring.ParseError('Indentation error', self.state.traceback)
                else:
                    if state.stringlike_end_lineno != state.start_lineno:
                        raise erring.ParseError('In a key-value pair in non-inline syntax, the equals sign "=" must follow the key on the same line', self.state.traceback)
                line = line[1:].lstrip(self._whitespace_str)
                self._ast.append_stringlike_key()
            else:
                self._ast.append_stringlike()
        return line
