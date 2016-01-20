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


from .version import __version__
import sys

if sys.version_info.major == 2:
    str = unicode
    __chr__ = chr
    chr = unichr

from . import erring
from . import unicoding
import collections
import binascii
import base64




class Source(object):
    '''
    Keep track of the name of a source (file name, or <string>), and of the
    current location within the source (range of lines currently being parsed).

    An instance is created when decoding begins, and line numbers are updated
    as parsing proceedsd.  The source instance is passed on to any parsing
    errors that are raised, to provide informative error messages.
    '''
    def __init__(self, name=None, start_lineno=0, end_lineno=0):
        if name is None:
            name = '<string>'
        self.name = name
        self.start_lineno = start_lineno
        self.end_lineno = end_lineno




class BespONDecoder(object):
    '''
    Decode BespON.

    Works with Unicode strings or iterables containing Unicode strings.
    '''
    def __init__(self, reserved_words=None, parsers=None, aliases=None, **kwargs):
        # If a `Source()` instance is provided, enhanced tracebacks are
        # possible in some cases.  Start with default value.  An actual
        # instance is created at the beginning of decoding.
        self.source = None


        # Basic type checking on arguments
        arg_dicts = (reserved_words, parsers, aliases)
        if not all(x is None or isinstance(x, dict) for x in arg_dicts):
            raise TypeError('Arguments {0} must be dicts'.format(', '.join('"{0}"'.format(x) for x in arg_dicts)))
        if parsers:
            if not all(hasattr(v, '__call__') for k, v in parsers.items()):
                raise TypeError('All parsers must be functions (callable)')
            if any(k.lower() in ('bool', 'null', 'inf', '+inf', '-inf', 'nan') for k in parsers):
                raise ValueError('Parsing of bool, null, inf, and nan is managed via "reserved_words"')


        # Defaults
        self.default_reserved_words = {'true': True, 'false': False, 'null': None,
                                       'inf': float('inf'), '-inf': float('-inf'), '+inf': float('+inf'),
                                       'nan': float('nan')}

        self.default_parsers = {#Basic types
                                'dict':        dict,
                                'list':        list,
                                'float':       float,
                                'int':         int,
                                'str':         self.parse_str,
                                #Extended types
                                'str.esc':     self.parse_str_esc,
                                'bin':         self.parse_bin,
                                'bin.esc':     self.parse_bin_esc,
                                #Optional types
                                'bin.base64':  self.parse_bin_base64,
                                'bin.hex':     self.parse_bin_base16,
                                'odict':       collections.OrderedDict,
                                'set':         set,
                                'tuple':       tuple,}

        self.default_aliases = {'esc': 'str.esc', 'bin.b64': 'bin.base64',
                                'bin.b16': 'bin.base16', 'bin.hex': 'bin.base16'}


        # Create actual dicts that are used
        self.reserved_words = self.default_reserved_words.copy()
        if reserved_words:
            self.reserved_words.update(reserved_words)

        self.parsers = self.default_parsers.copy()
        if parsers:
            self.parsers.update(parsers)

        self.aliases = self.default_aliases.copy()
        if aliases:
            for k, v in aliases.items():
                if v not in self.parsers:
                    raise ValueError('Alias "{0}" => "{1}" maps to unknown type'.format(k, v))
                self.parsers[k] = self.parsers[v]


        # Create a UnicodeFilter instance
        # Provide shortcuts to some of its attributes
        self.unicodefilter = unicoding.UnicodeFilter(**kwargs)
        self.newlines = self.unicodefilter.newlines
        self.newline_chars = self.unicodefilter.newline_chars
        self.newline_chars_str = self.unicodefilter.newline_chars_str
        self.spaces = self.unicodefilter.spaces
        self.spaces_str = self.unicodefilter.spaces_str
        self.indents = self.unicodefilter.indents
        self.indents_str = self.unicodefilter.indents_str
        self.whitespace = self.unicodefilter.whitespace
        self.whitespace_str = self.unicodefilter.whitespace_str
        ################################ TESTING
        self.unicodefilter.source = Source()
        self.source = Source()


    def _unwrap_inline(self, s_list):
        '''
        Unwrap an inline string.

        Any line that ends with a newline preceded by spaces (space or
        ideographic space) has the newline stripped.  Otherwise, a trailing
        newline is replace by a space.  The last line will not have a newline,
        and any trailing whitespace it has will already have been dealt with
        during parsing, so it is passed through unmodified.
        '''
        s_list_inline = []
        newline_chars_str = self.newline_chars_str
        spaces_str = self.spaces_str
        for line in s_list[:-1]:
            line_strip_nl = line.rstrip(newline_chars_str)
            if line_strip_nl.rstrip(spaces_str) != line_strip_nl:
                s_list_inline.append(line_strip_nl)
            else:
                s_list_inline.append(line_strip_nl + '\x20')
        s_list_inline.append(s_list[-1])
        return ''.join(s_list_inline)


    def parse_str(self, s_list, inline=False):
        '''
        Return a formatted string.

        Receives a list of strings, including newlines, and returns a string.

        Note that this function receives the raw result of parsing.  Any
        non-string indentation has already been stripped.  For unquoted
        strings, any leading/trailing indentation characters and newlines
        have also been stripped/handled.  All other newlines have not been
        handled; any unwrapping for inline strings remains to be done.
        '''
        if inline:
            s = self._unwrap_inline(s_list)
        else:
            s = ''.join(s_list)
        return s


    def parse_str_esc(self, s_list, inline=False):
        '''
        Return an unescaped version of a string.
        '''
        return self.unicodefilter.unescape(self.parse_str(s_list, inline))


    def parse_bin(self, s_list, inline=False):
        '''
        Return a binary string.
        '''
        if inline:
            s = self._unwrap_inline(s_list)
        else:
            s = ''.join(s_list)
        # If there are Unicode newline characters, convert them to `\n`
        s = self.unicodefilter.unicode_to_bin_newlines(s)
        try:
            b = s.encode('ascii')
        except UnicodeEncodeError as e:
            raise erring.BinaryStringEncodeError(s, e, self.source)
        return b


    def parse_bin_esc(self, s_list, inline=False):
        '''
        Return an unescaped version of a binary string.
        '''
        b = self.parse_bin(s_list, inline)
        return self.unicodefilter.unescape_bin(b)


    def parse_bin_base64(self, s_list, inline=False):
        '''
        Return a base64-decoded byte string.
        '''
        s = ''.join(s_list)
        s = self.unicodefilter.remove_whitespace(s)
        try:
            b = base64.b64decode(s)
        except  (ValueError, TypeError, UnicodeEncodeError, binascii.Error) as e:
            raise erring.BinaryBase64DecodeError(s, e, self.source)
        return b


    def parse_bin_base16(self, s_list, inline=False):
        '''
        Return a byte string from hex decoding.
        '''
        s = ''.join(s_list)
        s = self.unicodefilter.remove_whitespace(s)
        try:
            b = base64.b16decode(s)
        except (ValueError, TypeError, UnicodeEncodeError, binascii.Error) as e:
            raise erring.BinaryBase16DecodeError(s, e, self.source)
        return b


    def decode(self, s):
        if not isinstance(s, str):
            raise ValueError('BespONDecoder only decodes strings')

        # Create a Source() instance for tracking parsing location and
        # providing informative error messages.  Pass it to UnicodeFilter()
        # instance so that it can use it as well.
        self.source = Source()
        self.unicodefilter.source = self.source

        if self.unicodefilter.has_nonliterals(s):
            trace = self.unicodefilter.trace_nonliterals(s)
            msg = '\n' + self.unicodefilter.format_nonliterals_trace(trace)
            raise erring.InvalidLiteralCharacterError(msg)

        self._lineno_line_gen = ((n+1, line) for (n, line) in enumerate(s))
        self._parse_to_ast()

        # Clean up Source() instance.  Don't want it hanging around in case
        # the decoder instance or its methods are used again.
        self.source = None
        self.unicodefilter.source = None


    def _process_first_line(self, s):
        '''
        Handle any BOMs.  Handle any `%!bespon` in the first line.

        Note that after the string is already in memory, we can't do anything
        about the possibility of UTF-32 BOMs.  UTF-32BE is `\\U0000FEFF`, which
        at this point can't be distinguished from UTF-16BE.  And Python won't
        allow `\\UFFFE0000`, which is the UTF-32LE BOM.  This shouldn't be an
        issue, because if UTF-32 is incorrectly interpreted, it would result
        in null bytes, which aren't allowed as literals by default.
        '''
        BOM = {'UTF-8': '\xEF\xBB\xBF',
               'UTF-16BE': '\uFEFF',
               'UTF-16LE': '\uFFFE'}
        encs = []
        for enc, chars in BOM.items():
            if s.startswith(chars):
                s = s[len(chars):]
                encs.append(enc)
        for enc, chars in BOM.items():
            if s.startswith(chars):
                s = s[len(chars):]
                encs.append(enc)
        if len(encs) > 1:
            raise ValueError('Encountered BOM for multiple encodings {0}'.format(', '.join(e for e in encs)))

        magic_number = '%!bespon'
        if s.startswith(magic_number):
            s = s[len(magic_number):]
            if s.rstrip(self.whitespace_str):
                raise ValueError('Invalid first line, or unsupported parser directives:\n  {0}'.format(magic_number+s))
            s = ''
        return s


    def _split_line_on_indent(self, s):
        '''
        Split a line into its leading indentation and everything else.
        '''
        line = s.lstrip(self.indents_str)
        indent = s[:len(s)-len(line)]
        return (indent, line)


    def _parse_to_ast(self):
        self._ast = []
        self._ast_pos = self._ast
        lineno, line = next(self.lineno_line_gen, None)
        if line is None:
            self._ast_pos.append('')
            return
        line = self._process_first_line(line)
        self.source.start_lineno = lineno
        if not line:
            lineno, line = next(self.lineno_line_gen, None)
            self.source.start_lineno = lineno
            if line is None:
                self._ast_pos.append('')
                return
            indent, line = self._split_line_on_indent(line)
            self.indent = indent

        while line is not None:
            line = self._parse_line[line[0]](line)
