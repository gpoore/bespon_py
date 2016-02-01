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
from . import tooling
import collections
import binascii
import base64
import re




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


class AstObj(list):
    '''
    Abstract representation of collection types in AST.

    Attributes:
      +  cat          = General type category of the object.  Possibilities
                        include `list` (list-like; list, set, etc.), `dict`
                        (dict-like; dict, ordered dict, or other mapping),
                        or `kvpair` (key-value pair; what an object with
                        category `dict` must contain)
      +  compact      = Whether the object was opened in compact syntax.
      +  indent       = Indentation of object.
      +  nodetype     = The type of the object, if the object is explicitly
                        typed via `(type)>` syntax.  Otherwise, type is
                        inherited from `cat`.
      +  source       = A `Source` instance, used for providing line numbers in
                        any error messages generated by attempting to append
                        invalid types.
      +  start_lineno = Line number on which object started.  Used for
                        providing line error information for instances that
                        were never closed.
    '''
    __slots__ = ['cat', 'compact', 'indent', 'nodetype', 'source', 'start_lineno']
    def __init__(self, cat, obj):
        self.cat = cat
        self.compact = obj.compact
        self.indent = obj.indent
        self.nodetype = obj.next_type
        self.source = obj.source
        if self.source is None:
            self.start_lineno = None
        else:
            self.start_lineno = self.source.start_lineno
        # Never instantiated with any contents
        list.__init__(self)
    def check_append(self, val):
        '''
        Append a value, making sure that the value is consistent with the type
        of the instance.
        '''
        if isinstance(val, AstObj):
            if not (self.cat == 'list' or (self.cat == 'dict' and val.cat == 'kvpair') or (self.cat == 'kvpair' and len(self) == 1)):
                raise erring.ParseError('Attempting to add a collection object where one is not allowed', self.source)
        self.append(val)


class RootAstObj(AstObj):
    '''
    Root of AST.  May only contain a single object.
    '''
    __slots__ = ['cat', 'compact', 'indent', 'nodetype', 'source', 'start_lineno']
    def __init__(self, obj):
        self.cat = '(root)'
        self.compact = None
        self.indent = None
        self.nodetype = '(root)'
        self.source = obj.source
        if self.source is None:
            self.start_lineno = None
        else:
            self.start_lineno = self.source.start_lineno
        # Never instantiated with any contents
        list.__init__(self)
    def check_append(self, val):
        if len(self) == 1:
            raise erring.ParseError('Only a single scalar or collection object is allowed at root level', self.source)
        self.append(val)




class BespONDecoder(object):
    '''
    Decode BespON.

    Works with Unicode strings or iterables containing Unicode strings.
    '''
    def __init__(self, dict_parsers=None, list_parsers=None, string_parsers=None,
                 reserved_words=None, aliases=None, **kwargs):
        # If a `Source()` instance is provided, enhanced tracebacks are
        # possible in some cases.  Start with default value.  An actual
        # instance is created at the beginning of decoding.
        self.source = None


        # Basic type checking on arguments
        arg_dicts = (dict_parsers, list_parsers, string_parsers, reserved_words, aliases)
        if not all(x is None or isinstance(x, dict) for x in arg_dicts):
            raise TypeError('Arguments {0} must be dicts'.format(', '.join('"{0}"'.format(x) for x in arg_dicts)))
        for d in arg_dicts:
            if d:
                if not all(hasattr(v, '__call__') for k, v in d.items()):
                    raise TypeError('All parsers must be functions (callable)')


        # Defaults
        self.default_dict_parsers = {'dict':  dict,
                                     'odict': collections.OrderedDict,
                                     None:    dict}

        self.default_list_parsers = {'list':  list,
                                     'set':   set,
                                     'tuple': tuple,
                                     None:    list}

        self.default_string_parsers = {'int':        int,
                                       'float':      float,
                                       'str':        str,
                                       'str.empty':  self.parse_str_empty,
                                       'str.esc':    self.parse_str_esc,
                                       'bin':        self.parse_bin,
                                       'bin.empty':  self.parse_bin_empty,
                                       'bin.esc':    self.parse_bin_esc,
                                       'bin.base16': self.parse_bin_base16,
                                       'bin.base64': self.parse_bin_base64,
                                       None:         str}

        self.default_reserved_words = {'true': True, 'false': False, 'null': None,
                                       'inf': float('inf'), '-inf': float('-inf'), '+inf': float('+inf'),
                                       'nan': float('nan')}

        self.default_aliases = {'esc': 'str.esc', 'bin.b64': 'bin.base64',
                                'bin.b16': 'bin.base16', 'bin.hex': 'bin.base16'}


        # Create actual dicts that are used
        self.dict_parsers = self.default_dict_parsers.copy()
        if dict_parsers:
            self.dict_parsers.update(dict_parsers)

        self.list_parsers = self.default_list_parsers.copy()
        if list_parsers:
            self.list_parsers.update(list_parsers)

        self.string_parsers = self.default_string_parsers.copy()
        if string_parsers:
            self.string_parsers.update(string_parsers)

        self.parsers = {}
        self.parsers.update(self.dict_parsers)
        self.parsers.update(self.list_parsers)
        self.parsers.update(self.string_parsers)

        self.reserved_words = self.default_reserved_words.copy()
        if reserved_words:
            self.reserved_words.update(reserved_words)

        self.aliases = self.default_aliases.copy()
        if aliases:
            self.aliases.update(aliases)
            for k, v in aliases.items():
                found = False
                if v in self.dict_parsers:
                    self.dict_parsers[k] = self.dict_parsers[v]
                    found = True
                if v in self.list_parsers:
                    self.list_parsers[k] = self.list_parsers[v]
                    found = True
                if v in self.string_parsers:
                    self.string_parsers[k] = self.string_parsers[v]
                    found = True
                if not found:
                    raise ValueError('Alias "{0}" => "{1}" maps to unknown type'.format(k, v))


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

        # Create dicts used in parsing
        # It's convenient to define these next to the definition of the
        # functions they contain
        self._build_parsing_dicts_and_re()


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


    def parse_str_empty(self, s_list, inline=False):
        '''
        Return an empty string.
        '''
        s = self.parse_str(s_list, inline)
        if s:
            raise erring.ParseError('Explicitly typed empty string is not really empty', self.source)
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


    def parse_bin_empty(self, s_list, inline=False):
        '''
        Return an empty string.
        '''
        b = self.parse_bin(s_list, inline)
        if b:
            raise erring.ParseError('Explicitly typed empty binary string is not really empty', self.source)
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
        '''
        Decode a Unicode string into objects.
        '''
        if not isinstance(s, str):
            raise TypeError('BespONDecoder only decodes Unicode strings')

        # Check for characters that may not appear literally
        if self.unicodefilter.has_nonliterals(s):
            trace = self.unicodefilter.trace_nonliterals(s)
            msg = '\n' + self.unicodefilter.format_nonliterals_trace(trace)
            raise erring.InvalidLiteralCharacterError(msg)

        # Create a Source() instance for tracking parsing location and
        # providing informative error messages.  Pass it to UnicodeFilter()
        # instance so that it can use it as well.
        self.source = Source()
        self.unicodefilter.source = self.source

        # Create a generator for lines from the source, keeping newlines
        # Then parse to AST, and convert AST to Python objects
        self._line_gen = (line for line in s.splitlines(True))
        self._parse_lines_to_ast()
        #self._parse_ast_to_pyobj()

        # Clean up Source() instance.  Don't want it hanging around in case
        # the decoder instance or its methods are used again.
        self.source = None
        self.unicodefilter.source = None

        # return self._pyobj


    def _parse_lines_to_ast(self):
        '''
        Process lines from source into abstract syntax tree (AST).

        All collection types, and key-value pairs, are represented as `AstObj`
        instances.  These will later be processed into actual dicts, lists, etc.

        All other other objects appear in the AST as literals (null, bool,
        string, binary, int, float, etc.).  They are processed into final form
        during this stage of the parsing.

        Note that the root node of the AST is a `RootAstObj` instance.  This
        is an `AstObj` subclass that may only contain a single object.  At
        the root level, a BespON file may only contain a single scalar, or a
        single collection type.
        '''
        self._ast = RootAstObj(self)
        self._ast_pos = self._ast
        self._ast_pos_stack = []
        self._next_type = None
        self._indent_level = ''
        self._indent_level_stack = []
        self._current_indent = ''
        self._in_compact = False
        self._in_compact_stack = []

        # Get things started by extracting the first line (if any), stripping
        # any BOM, and setting the line to `None` if it would have been `None`
        # had the BOM been removed before this stage.  Essentially, a file
        # will be treated as empty (producing no output) unless it contains
        # at least newlines.
        line = self._parse_line_goto_next()
        if line is not None:
            line = self._drop_bom(line)
            if not line:
                line = None

        while line is not None:
            # Using line[:1] gives '' for empty string; no IndexError
            line = self._parse_line[line[:1]](line)
        #####################################
        ####################################
        #################################
        #if not self._ast:
        #    raise erring.ParseError('There was no data to load', self.source)


    def _drop_bom(self, s):
        '''
        Handle any BOMs.

        Note that at this point, after the string is already in memory, we
        can't do anything general about the possibility of UTF-32 BOMs.
        UTF-32BE is `\\U0000FEFF`, which at this point can't be distinguished
        from UTF-16BE.  `\\uFEFF` is dropped, so both cases are handled.  If
        the UTF-32BE case is read incorrectly as UTF-16BE, then there will be
        null bytes, which are not allowed as literals by default.  Python
        won't allow `\\UFFFE0000`, which is the UTF-32LE BOM, so that case
        isn't an issue either.
        '''
        BOM = {'UTF-8': '\xEF\xBB\xBF',
               'UTF-16BE/UTF-32BE': '\uFEFF',
               'UTF-16LE': '\uFFFE'}
        encs = []
        for enc, chars in BOM.items():
            if s.startswith(chars):
                s = s[len(chars):]
                encs.append(enc)
        # Check for double BOMs just for fun
        for enc, chars in BOM.items():
            if s.startswith(chars):
                s = s[len(chars):]
                encs.append(enc)
        if len(encs) > 1:
            raise ValueError('Encountered BOM for multiple encodings {0}'.format(', '.join(e for e in encs)))
        return s


    def _split_line_on_indent(self, line):
        '''
        Split a line into its leading indentation and everything else.
        '''
        rest = line.lstrip(self.indents_str)
        indent = line[:len(line)-len(rest)]
        return (indent, rest)


    def _build_parsing_dicts_and_re(self):
        '''
        Assemble dicts of functions and regular expressions that are used in
        actual parsing.

        This is done here, rather than in `__init__()`, so as to be closer to
        where it is actually used, and to keep `__init__()` more concise.
        '''
        # Dict of functions for proceding with parsing, based on the next
        # character.  Needs to handle both ASCII and fullwidth equivalents.
        _parse_line = {'%':  self._parse_line_percent,
                       '(':  self._parse_line_open_paren,
                       ')':  self._parse_line_close_paren,
                       '[':  self._parse_line_open_bracket,
                       ']':  self._parse_line_close_bracket,
                       '{':  self._parse_line_open_brace,
                       '}':  self._parse_line_close_brace,
                       "'":  self._parse_line_single_quote,
                       '"':  self._parse_line_double_quote,
                       '=':  self._parse_line_equals,
                       '+':  self._parse_line_plus,
                       ';':  self._parse_line_semicolon,
                       '|':  self._parse_line_pipe
                      }
        for k, v in list(_parse_line.items()):
            _parse_line[self.unicodefilter.ascii_to_fullwidth(k)] = v
        _parse_line[''] = self._parse_line_whitespace
        for c in self.whitespace:
            _parse_line[c] = self._parse_line_whitespace
        self._parse_line = collections.defaultdict(lambda: self._parse_line_unquoted_string, _parse_line)

        # Regex for matching explicit type declarations.  Don't need to filter
        # out all code points not allowed in type name; will attempt type
        # lookup and raise error upon failure.
        pattern_type = r'''[\(\uFF08]  # Opening parenthesis
                           \S*?  # Contents; don't worry about newlines cause can only be at end of string
                           [\)\uFF09]  # Closing parenthesis
                           [>\uFF1E]  # Greater-than sign
                        '''
        self._explicit_type_re = re.compile(pattern_type, re.VERBOSE | re.UNICODE)

        # Regexes for identifying opening delimiters that may contains
        # multiple identical characters.  Treat ASCII and fullwidth
        # equivalents as identical.
        def gen_opening_delim_regex(c, fullwidth_to_ascii=self.unicodefilter.fullwidth_to_ascii, ascii_to_fullwidth=self.unicodefilter.ascii_to_fullwidth):
            c = fullwidth_to_ascii(c)
            if c == '|':
                p = '[{0}{1}](?:[{2}{3}]+|[{4}{5}]+)'.format(c, ascii_to_fullwidth(c), "'", ascii_to_fullwidth("'"), '"', ascii_to_fullwidth('"'))
            else:
                p = '[{0}{1}]+'.format(c, ascii_to_fullwidth(c))
            return re.compile(p)
        self._opening_delim_percent_re = gen_opening_delim_regex('%')
        self._opening_delim_single_quote_re = gen_opening_delim_regex("'")
        self._opening_delim_double_quote_re = gen_opening_delim_regex('"')
        self._opening_delim_equals_re = gen_opening_delim_regex('=')
        self._opening_delim_pipe_re = gen_opening_delim_regex('|')

        # Dict of regex for identifying closing delimiters.  Automatically
        # generate needed regex on the fly.
        def gen_closing_delim_regex(delim, fullwidth_to_ascii=self.unicodefilter.fullwidth_to_ascii, ascii_to_fullwidth=self.unicodefilter.ascii_to_fullwidth):
            c = fullwidth_to_ascii(delim[0])
            cw = ascii_to_fullwidth(c)
            if c == '%':
                p = '(?<![{0}{1}])[{0}{1}]{{{2}}}(?![{0}{1}])[/\uFF0F]'.format(c, cw, len(delim))
            elif c == '|':
                c_follow = fullwidth_to_ascii(delim[1])
                cw_follow = ascii_to_fullwidth(c_follow)
                p = '(?<![{0}{1}])[{0}{1}][{2}{3}]{{{4}}}[/\uFF0F]'.format(c, ascii_to_fullwidth(c), c_follow, cw_follow, len(delim)-1)
            else:
                p = '(?<![{0}{1}])[{0}{1}]{{{2}}}(?![{0}{1}])[/\uFF0F]{{0,2}}'.format(c, cw, len(delim))
            return re.compile(p)
        self._closing_delim_re_dict = tooling.keydefaultdict(gen_closing_delim_regex)

        # Regex for integers, including hex, octal, and binary.
        # Matches only ASCII; text containing fullwidth equivalents is
        # translated before regex matching is attempted.
        pattern_int = '''
                      [+-]? (?: [1-9](?:_(?=[0-9])|[0-9])* |
                                0x [0-9a-fA-F](?:_(?=[0-9a-fA-F])|[0-9a-fA-F])* |
                                0o [0-7](?:_(?=[0-7])|[0-7])* |
                                0b [01](?:_(?=[01])|[01])* |
                                0
                            )
                      $
                      '''
        self._int_re = re.compile(pattern_int, re.VERBOSE)

        # Regex for floats, including hex.
        pattern_float = '''
                        [+-]? (?: (?: \. [0-9](?:_(?=[0-9])|[0-9])* (?:[eE][+-]?[0-9](?:_(?=[0-9])|[0-9])*)? |
                                      (?:[1-9](?:_(?=[0-9])|[0-9])*|0) (?: \. (?:[0-9](?:_(?=[0-9])|[0-9])*)? (?:[eE][+-]?[0-9](?:_(?=[0-9])|[0-9])*)? |
                                                                           [eE][+-]?[0-9](?:_(?=[0-9])|[0-9])*)
                                  ) |
                                  0x (?: \.[0-9a-fA-F](?:_(?=[0-9a-fA-F])|[0-9a-fA-F])* |
                                         [0-9a-fA-F](?:_(?=[0-9a-fA-F])|[0-9a-fA-F])* (?: \. (?:[0-9a-fA-F](?:_(?=[0-9a-fA-F])|[0-9a-fA-F])*)? )?
                                     ) [pP][+-]?[0-9](?:_(?=[0-9])|[0-9])*
                              )
                        $
                        '''
        self._float_re = re.compile(pattern_float, re.VERBOSE)


    def _parse_line_get_next(self, line=None):
        '''
        Get next line.  For use in lookahead in string scanning, etc.
        '''
        line = next(self._line_gen, None)
        if self.source.end_lineno <= self.source.start_lineno:
            self.source.end_lineno = self.source.start_lineno + 1
        else:
            self.source.end_lineno += 1
        return line


    def _parse_line_at_next(self, line=None):
        '''
        Reset everything after `_parse_line_get_next()`, so that it's
        equivalent to using `_parse_line_goto_next()`.  Useful when
        `_parse_line_get_next()` is used for lookahead, but nothing is consumed.
        '''
        self.source.start_lineno = self.source.end_lineno
        self._at_line_start = True
        return line


    def _parse_line_goto_next(self, line=None):
        '''
        Go to next line, after current parsing is complete.
        '''
        line = next(self._line_gen, None)
        self.source.start_lineno += 1
        self._at_line_start = True
        return line


    def _parse_line_percent(self, line):
        '''
        Parse comments.
        '''
        delim = self._opening_delim_percent_re.match(line).group(0)
        if len(delim) < 3:
            if len(delim) == 1 and line[1:2] in ('!', '\uFF01'):
                line_ascii = self.unicodefilter.fullwidth_to_ascii(line)
                if line_ascii.startswith('%!bespon'):
                    if self.source.start_lineno != 1:
                        raise erring.ParseError('Encountered "%!bespon", but not on first line', self.source)
                    elif not self._at_line_start:
                        raise erring.ParseError('Encountered "%!bespon", but not at beginning of line', self.source)
                    elif line_ascii[len('%!bespon'):].rstrip(self.whitespace_str):
                        raise erring.ParseError('Encountered unknown parser directives: "{0}"'.format(line_ascii.rstrip(self.newline_chars_str)), self.source)
                    else:
                        line = self._parse_line_goto_next()
                else:
                    line = self._parse_line_goto_next()
            else:
                line = self._parse_line_goto_next()
        else:
            line = line[len(delim):]
            self._at_line_start = False
            end_delim_re = self._closing_delim_re_dict[delim]
            m = end_delim_re.search(line)
            while m is None:
                line = self._parse_line_get_next()
                if line is None:
                    raise erring.ParseError('Never found end of multi-line comment', self.source)
                m = end_delim_re.match(line)
            line = line[m.end():]
            self._at_line_start = False
        return line


    def _parse_line_open_paren(self, line):
        '''
        Parse explicit typing.
        '''
        m = self._explicit_type_re.match(line)
        if not m:
            raise erring.ParseError('Could not parse explicit type declaration', self.source)
        t = m.group(0)[1:-2]
        if t not in self.parsers:
            raise erring.ParseError('Unknown type declaration "{0}"'.format(m.group(0)), self.source)
        self._next_type = t
        return line[m.end():]


    def _parse_line_close_paren(self, line):
        '''
        Parse line segment beginning with closing parenthesis.
        '''
        raise erring.ParseError('Unexpected closing parenthesis', self.source)


    def _parse_line_open_bracket(self, line):
        pass

    def _parse_line_close_bracket(self, line):
        pass

    def _parse_line_open_brace(self, line):
        pass

    def _parse_line_close_brace(self, line):
        pass

    def _parse_line_single_quote(self, line):
        '''
        Parse single-quoted string.
        '''
        delim = self._opening_delim_single_quote_re.match(line).group(0)
        line = line[len(delim):]
        end_delim_re = self._closing_delim_re_dict[delim]
        return self._parse_line_quoted_string(line, delim, end_delim_re)


    def _parse_line_double_quote(self, line):
        '''
        Parse double-quoted string.
        '''
        delim = self._opening_delim_double_quote_re.match(line).group(0)
        line = line[len(delim):]
        end_delim_re = self._closing_delim_re_dict[delim]
        return self._parse_line_quoted_string(line, delim, end_delim_re)


    def _parse_line_quoted_string(self, line, delim, end_delim_re):
        '''
        Parse a quoted string, once the opening delim has been determined
        and stripped, and a regex for the closing delim has been assembled.
        '''
        m = end_delim_re.search(line)
        if m:
            end_delim = m.group(0)
            if len(end_delim) > len(delim):
                raise erring.ParseError('A block string may not begin and end on the same line', self.source)
            s = line[:m.start()]
            line = line[m.end()+1:]
        else:
            s_lines = [line]
            if self._at_line_start:
                indent = self._current_indent
            else:
                indent = self._indent_level
            while True:
                line = self._parse_line_get_next()
                if line is None:
                    raise erring.ParseError('Text ended while scanning quoted string', self.source)
                if not line.startswith(indent) and line.lstrip(self.whitespace_str):
                    raise erring.ParseError('Indentation error within quoted string', self.source)
                m = end_delim_re.search(line)
                if not m:
                    s_lines.append(line)
                else:
                    end_delim = m.group(0)
                    s_lines.append(line[:m.start()])
                    line = line[m.end()+1:]
                    s = self._process_quoted_string(s_lines, indent, delim, end_delim)
                    break
        try:
            s = self.string_parsers[self._next_type](s)
            self._next_type = None
        except KeyError:
            raise erring.ParseError('Invalid explicit type "{0}" applied to string'.format(self._next_type), self.source)
        except Exception as e:
            raise erring.ParseError('Could not convert quoted string to type "{0}":\n  {1}'.format(self._next_type, e), self.source)
        self._ast_pos.append(s)
        return line


    def _process_quoted_string(self, s_lines, indent, delim, end_delim):
        '''
        Process list of raw text lines that make up a quoted string.  All
        delimiters have been stripped at this point.  The string wraps over
        multiple lines if it is an inline string.
        '''
        if len(delim) == len(end_delim):
            # Make sure indentation is consistent and there are no empty lines
            if len(s_lines) > 2:
                for line in s_lines[1:-1]:
                    if not line.lstrip(self.whitespace_str):
                        raise erring.ParseError('Inline strings cannot contain empty lines', self.source)
                indent = s_lines[1][:len(s_lines[1].lstrip(self.indents_str))]
                len_indent = len(indent)
                for n, line in enumerate(s_lines[1:]):
                    if not line.startswith(indent) or line[len_indent:len_indent+1] in self.whitespace:
                        raise erring.ParseError('Inconsistent Indentation within inline string', self.source)
                    s_lines[n+1] = line[len_indent:]
            else:
                s_lines[1] = s_lines[1].lstrip(self.indents_str)
            # Unwrap
            s = self._unwrap_inline(s_lines)
            # Take care of any leading/trailing spaces that separate delimiter
            # characters from identical characters in string.
            s_strip_spaces = s.strip(self.spaces_str)
            if self.unicodefilter.fullwidth_to_ascii(delim[0]) == self.unicodefilter.fullwidth_to_ascii(s_strip_spaces[0]):
                s = s[1:]
            if self.unicodefilter.fullwidth_to_ascii(end_delim[0]) == self.unicodefilter.fullwidth_to_ascii(s_strip_spaces[-1]):
                s = s[:-1]
        else:
            if s_lines[0].lstrip(self.whitespace_str):
                raise erring.ParseError('Characters are not allowed immediately after the opening delimiter of a block string', self.source)
            if s_lines[-1].lstrip(self.indents_str):
                raise erring.ParseError('Characters are not allowed immediately before the closing delimiter of a block string', self.source)
            indent = s_lines[-1]
            len_indent = len(indent)
            if self._at_line_start and self._current_indent != indent:
                raise erring.ParseError('Opening and closing delimiters for block string do not have matching indentation', self.source)
            for n, line in enumerate(s_lines[1:-1]):
                if line.startswith(indent):
                    s_lines[n+1] = line[len_indent:]
                else:
                    if not line.lstrip(self.whitespace_str):
                        s_lines[n+1] = line[len_indent:]
                    else:
                        raise erring.ParseError('Inconsistent indent in block string', self.source)
            if len(delim) == len(end_delim) - 2:
                s_lines[-2] = s_lines[-2].rstrip(self.newline_chars_str)
            s = ''.join(s_lines[1:-1])
        return s


    def _parse_line_equals(self, line):
        pass

    def _parse_line_plus(self, line):
        pass

    def _parse_line_semicolon(self, line):
        pass

    def _parse_line_pipe(self, line):
        pass

    def _parse_line_whitespace(self, line):
        '''
        Parse line segment beginning with whitespace.
        '''
        if line.lstrip(self.whitespace_str):
            self._current_indent, line = self._split_line_on_indent(line)
        else:
            while True:
                line = self._parse_line_goto_next()
                if line is None:
                    if self._ast_pos == self._ast and not self._ast:
                        try:
                            self._ast_pos.append(self.string_parsers[self._next_type](''))
                            self._next_type = None
                        except KeyError:
                            raise erring.ParseError('Invalid explicit type "{0}" applied to string'.format(self._next_type), self.source)
                    break
                elif line.lstrip(self.whitespace_str):
                    self._current_indent, line = self._split_line_on_indent(line)
                    break
        return line

    def _parse_line_unquoted_string(self, line):
        pass









"""
    def _parse_line_comment(self, line):
        '''Hangle comment (single-line or multi-line)'''
        if line[0] != line[1:2]:
            content = self.unicodefilter.fullwidth_to_halfwidth_ascii(line[1:])
            if not content.startswith('!bespon'):
                line = self._parse_line_goto_next(line)
            else:
                content = content.rstrip(self.whitespace_str)
                if ((content == '!bespon' and self.source.start_lineno == 1) or
                        (content == '!bespon.eof')):
                    line = self._parse_line_goto_next(line)
                else:
                    raise erring.ParseError('Found "%!bespon" in improper location or with unrecognized directives', self.source)
        else:
            open_delim = line[:len(line.lstrip(line[0]))]

        return line

    def _parse_line_open_paren(self, line):
        '''Handle opening parenthesis.'''
        m = self._explicit_type_re.match(line).group(0)
        if m:
            if not ((m[0] == '(' and m[-2:] == ')>') or (m[0] == '\uFF08' and m[-2:] == '\uFF09\uFF1E')):
                raise erring.ParseError('Mixing fullwidth and non-fullwidth parentheses and/or greater-than sign in type declaration', self.source)
            # All types should be defined using ASCII, but should be able to
            # invoke a type using fullwidth characters
            t = self.unicodefilter.fullwidth_to_halfwidth_ascii(m[1:-2])
            if t not in self.parsers:
                raise erring.ParseError('Unrecognized type declaration "{0}"'.format(m), self.source)
            self._next_type = t
            line = line[len(m):].lstrip(self.whitespace_str)
        else:
            self._ast_pos.check_append(AstObj(nodetype=self._next_type, cat=None, source=self.source, openchar=line[0]))
            # Reset typing
            self._next_type = None
            self._ast_pos_stack.append(self._ast_pos)
            self._ast_pos = self._ast_pos[-1]
            self._in_compact_stack.append(self._in_compact)
            self._in_compact = True
            line = line[1:].lstrip(self.whitespace_str)
        return line

    def _parse_line_close_paren(self, line):
        '''Handle closing parenthesis'''
        if self._ast_pos.closechar != line[0]:
            raise erring.ParseError('Collection closed by character "{0}" that does not pair with the character used to open it'.format(line[0]))
        try:
            self._ast_pos = self._ast_pos_stack.pop()
            self._in_compact = self._in_compact_stack.pop()
        except IndexError:
            raise erring.ParseError('Trying to close a collection that does not exist')
        return line[1:].lstrip(self.whitespace_str)

    def _parse_line_string(self, line):
        if line.startswith('"'):
            s = line.split('"', 2)
        self._ast_pos.append(s[1])
        return s[2].lstrip(self.whitespace_str)
"""








'''
magic_number = '%!bespon'
if s.startswith(magic_number):
    s = s[len(magic_number):]
    if s.rstrip(self.whitespace_str):
        raise ValueError('Invalid first line, or unsupported parser directives:\n  {0}'.format(magic_number+s))
    s = ''
'''
