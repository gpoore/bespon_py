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
    as parsing proceeds.  The source instance is passed on to any parsing
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
      +  ast          = Abstract Syntax Tree in which object is placed.
      +  cat          = General type category of the object.  Possibilities
                        include `root`, `list` (list-like; list, set, etc.),
                        `dict` (dict-like; dict, ordered dict, or other
                        mapping), or `kvpair` (key-value pair; what an object
                        with category `dict` must contain).
      +  compact      = Whether the object was opened in compact syntax.
      +  indent       = Indentation of object.
      +  nodetype     = The type of the object, if the object is explicitly
                        typed via `(type)>` syntax.  Otherwise, type is
                        inherited from `cat`.
      +  parent       = Parent node in AST.
      +  start_lineno = Line number on which object started.  Used for
                        providing line error information for instances that
                        were never closed.
    '''
    __slots__ = ['ast', 'cat', 'check_append', 'compact', 'indent', 'index', 'nodetype', 'open', 'parent', 'start_lineno']

    def __init__(self, cat, decoder, ast=None):
        # `decoder._ast` doesn't exist yet when creating root
        if ast is None:
            self.ast = decoder._ast
        else:
            self.ast = ast
        self.cat = cat
        if cat != 'root':
            self.compact = decoder._compact
            self.indent = decoder._indent
            self.index = len(self.ast.pos)
            self.nodetype = decoder._next_type
            self.open = False
            self.parent = self.ast.pos
            self.start_lineno = decoder.source.start_lineno
        else:
            self.compact = None
            self.indent = None
            self.index = None
            self.nodetype = 'root'
            self.open = None
            self.parent = None
            self.start_lineno = None
        if cat == 'root':
            self.check_append = self._check_append_root
        elif cat == 'dict':
            self.check_append = self._check_append_dict
        elif cat == 'kvpair':
            self.check_append = self._check_append_kvpair
        elif cat == 'list':
            self.check_append = self._check_append_list
        # Never instantiated with any contents
        list.__init__(self)

    def _check_append_root(self, val):
        if len(self) == 1:
            raise erring.ParseError('Only a single object is allowed at root level', self.ast.source)
        if isinstance(val, AstObj):
            self.append(val)
            self.ast.pos = self.ast.pos[-1]
            # Can only have `dict` or `list`, so no need to check
            self.ast._obj_to_pythonize_list.append(val)
        else:
            self.append(val)

    def _check_append_dict(self, val):
        if not (isinstance(val, AstObj) and val.cat == 'kvpair'):
            raise erring.ParseError('Cannot add a non-key-value pair to a dict-like object', self.ast.source)
        if val.indent != self.indent:
            raise erring.ParseError('Key indentation error in dict-like object', self.ast.source)
        self.append(val)
        self.ast.pos = self.ast.pos[-1]

    def _check_append_kvpair(self, val):
        if len(self) == 2:
            raise erring.ParseError('Key-value pair can only contain two elements', self.ast.source)
        if isinstance(val, AstObj):
            if not self:
                raise erring.ParseError('Keys for dict-like objects cannot be collection types', self.ast.source)
            if not (len(val.indent) > len(self.indent) and val.indent.startswith(self.indent)):
                raise erring.ParseError('Indentation error', self.ast.source)
            self.append(val)
            self.ast.pos = self.ast.pos[-1]
            self.ast._obj_to_pythonize_list.append(val)
        else:
            # Don't need to check indentation of key; already checked when
            # kvpair AstObj is created
            if self and not (self.ast.decoder._indent.startswith(self.indent) and ((self.ast.decoder._at_line_start and self.ast.decoder._indent > self.indent) or
                             (not self.ast.decoder._at_line_start and self.ast.decoder._indent >= self.indent)) ):
                raise erring.ParseError('Value indentation error in dict-like object', self.ast.source)
            self.append(val)
            if len(self) == 2:
                self.ast.pos = self.ast.pos.parent

    def _check_append_list(self, val):
        if not self.open:
            raise erring.ParseError('Cannot append to a list element that already exists', self.ast.source)
        if not (len(self.ast.decoder._indent) >= len(self.indent) + 2 and self.ast.decoder._indent.startswith(self.indent)):
            raise erring.ParseError('Indentation error in list-like object', self.ast.source)
        if isinstance(val, AstObj):
            self.append(val)
            self.ast.pos = self.ast.pos[-1]
            self.ast._obj_to_pythonize_list.append(val)
        else:
            self.append(val)
        self.open = False


class Ast(object):
    '''
    Abstract syntax tree of data, before final, full conversion into Python
    objects.  At this stage, all non-collection types are in final form,
    and all collection types are represented as `AstObj` instances, which
    are a subclass of list and can represent all collection types in a form
    that may be conveniently translated to Python objects.
    '''
    def __init__(self, decoder):
        self.decoder = decoder
        self.source = decoder.source
        self.root = AstObj('root', self.decoder, self)
        self.pos = self.root
        self._obj_to_pythonize_list = []

    def __eq__(self, other):
        return self.root == other

    def __str__(self):
        return '<Ast: {0}>'.format(str(self.root))

    def __repr__(self):
        return '<Ast: {0}>'.format(repr(self.root))

    def __bool__(self):
        return bool(self.root)

    def append(self, val):
        while self.pos is not self.root and len(self.decoder._indent) < len(self.pos.indent):
            if self.pos.cat == 'kvpair' and len(self.pos) == 1:
                self.pos.append('')
            elif self.pos.cat == 'list' and self.pos.open:
                self.pos.append('')
            self.pos = self.pos.parent
        if isinstance(val, AstObj) and val.cat == 'kvpair':
            if self.pos.cat == 'kvpair' and self.pos.indent == val.indent:
                # Current `decoder._indent` is for the current `kvpair`
                # being appended, so we can't use `check_append()`
                if len(self.pos) == 1:
                    self.pos.append('')
                self.pos = self.pos.parent
            elif not self.pos.cat == 'dict':
                self.pos.check_append(AstObj('dict', self.decoder))
            val = AstObj('kvpair', self.decoder)
        self.pos.check_append(val)

    def finalize(self):
        while self.pos is not self.root:
            if self.pos.cat == 'kvpair' and len(self.pos) == 1:
                self.pos.append('')
            elif self.pos.cat == 'list' and self.pos.open:
                self.pos.append('')
            self.pos = self.pos.parent

    def pythonize(self):
        for obj in reversed(self._obj_to_pythonize_list):
            py_obj = self.decoder.parsers[obj.cat][obj.nodetype](obj)
            obj.parent[obj.index] = py_obj




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

        # Whether to keep raw Abstract Syntax Tree for debugging, or go ahead
        # and convert it into full Python objects
        self._debug_raw_ast = False

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

        if (set(self.dict_parsers) & set(self.list_parsers) & set(self.string_parsers)) - set([None]):
            raise erring.ConfigError('Overlap between dict, list, and string parsers is not supported')

        self.parsers = {'dict': self.dict_parsers,
                        'list': self.list_parsers,
                        'string': self.string_parsers}

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
        self.unicode_whitespace = self.unicodefilter.unicode_whitespace
        self.unicode_whitespace_str = self.unicodefilter.unicode_whitespace_str

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
        r = self._parse_lines_to_py_obj()

        # Clean up Source() instance.  Don't want it hanging around in case
        # the decoder instance or its methods are used again.
        self.source = None
        self.unicodefilter.source = None

        return r


    def _parse_lines_to_py_obj(self):
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
        self._ast = Ast(self)
        self._next_type = None
        self._next_type_indent = None
        self._indent = None
        self._compact = None

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
            line = self._parse_line[line[:1]](line)

        self._ast.finalize()

        if not self._ast:
            raise erring.ParseError('There was no data to load', self.source)

        if not self._debug_raw_ast:
            self._ast.pythonize()
            return self._ast.root[0]



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
        # Characters that can't appear in normal unquoted strings.
        # `+` is only special in non-compact syntax, at the beginning of a
        # line, when followed by an indentation character (or Unicode
        # whitespace).  `|` is only special when followed by three or more
        # quotation marks or by a space (or Unicode whitespace).  Given the
        # limited context in which `+` and `|` are special, they are generally
        # allowed within unquoted strings.  All necessary conditions for when
        # they appear at the beginning of string are imposed in the
        # corresponding parsing functions.
        self._not_unquoted_ascii_str = '%()[]{}\'"=;'
        self._not_unquoted_ascii = set(self._not_unquoted_ascii_str)
        self._not_unquoted_str = self.unicodefilter.to_ascii_and_fullwidth(self._not_unquoted_ascii_str)
        self._not_unquoted = set(self._not_unquoted_str)

        self._equals = set([c for c in self.unicodefilter.to_ascii_and_fullwidth('=')])
        self._semicolons = set([c for c in self.unicodefilter.to_ascii_and_fullwidth(';')])
        self._ending_delims = set([c for c in self.unicodefilter.to_ascii_and_fullwidth(')]}')])
        self._open_brackets = set([c for c in self.unicodefilter.to_ascii_and_fullwidth('[')])
        self._open_braces = set([c for c in self.unicodefilter.to_ascii_and_fullwidth('{')])
        self._quotes = set([c for c in self.unicodefilter.to_ascii_and_fullwidth('"\'')])

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
                       ';':  self._parse_line_semicolon,
                       '+':  self._parse_line_plus,
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
        not_allowed_type = self.unicodefilter.to_ascii_and_fullwidth(self._not_unquoted_ascii_str.replace('=', ''))
        pattern_type = r'''[\(\uFF08]  # Opening parenthesis
                           [^{ws}{na}]+?  # Contents
                           [\)\uFF09]  # Closing parenthesis
                           [>\uFF1E]  # Greater-than sign
                        '''
        pattern_type = pattern_type.format(ws=re.escape(self.unicode_whitespace_str), na=re.escape(not_allowed_type))
        self._explicit_type_re = re.compile(pattern_type, re.VERBOSE)

        # Regexes for identifying opening delimiters that may contains
        # multiple identical characters.  Treat ASCII and fullwidth
        # equivalents as identical.
        def gen_opening_delim_regex(c, fullwidth_to_ascii=self.unicodefilter.fullwidth_to_ascii, ascii_to_fullwidth=self.unicodefilter.ascii_to_fullwidth):
            c = fullwidth_to_ascii(c)
            cw = ascii_to_fullwidth(c)
            if c == '|':
                p = '[{0}{1}](?:[{2}{3}]+|[{4}{5}]+)'.format(c, cw, "'", ascii_to_fullwidth("'"), '"', ascii_to_fullwidth('"'))
            else:
                p = '[{0}{1}]+'.format(c, cw)
            return re.compile(p)
        self._opening_delim_percent_re = gen_opening_delim_regex('%')
        self._opening_delim_single_quote_re = gen_opening_delim_regex("'")
        self._opening_delim_double_quote_re = gen_opening_delim_regex('"')
        self._opening_delim_equals_re = gen_opening_delim_regex('=')
        self._opening_delim_pipe_re = gen_opening_delim_regex('|')
        self._opening_delim_plus_re = gen_opening_delim_regex('+')

        # Dict of regexes for identifying closing delimiters.  Automatically
        # generate needed regex on the fly.
        def gen_closing_delim_regex(delim, fullwidth_to_ascii=self.unicodefilter.fullwidth_to_ascii, ascii_to_fullwidth=self.unicodefilter.ascii_to_fullwidth):
            c = fullwidth_to_ascii(delim[0])
            cw = ascii_to_fullwidth(c)
            if c == '%':
                p = '(?<![{0}{1}])[{0}{1}]{{{2}}}(?![{0}{1}])[/\uFF0F]'.format(c, cw, len(delim))
            elif c == '|':
                c_follow = fullwidth_to_ascii(delim[1])
                cw_follow = ascii_to_fullwidth(c_follow)
                p = '(?<![{0}{1}])[{0}{1}][{2}{3}]{{{4}}}[/\uFF0F]{{1,2}}'.format(c, cw, c_follow, cw_follow, len(delim)-1)
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

        # There are multiple regexes for unquoted keys.  Plain unquoted keys
        # need to be distinguished from keys describing key paths.
        pattern_unquoted_key = r'[^{0}{1}]+'.format(re.escape(self.unicode_whitespace_str), re.escape(self._not_unquoted_str))
        self._unquoted_key_re = re.compile(pattern_unquoted_key)

        pattern_unquoted_keypath = r'''
                                    (?:  # First element
                                       (?:[^{ws}{na}\d][^{ws}{na}]*) |  # Identifier-style
                                       (?:[\[\uFF3B] (?:[+\uFF0B]|[+\uFF0B-\uFF0D]?[0-9\uFF10-\uFF19]+) [\]\uFF3D]) |  # Bracket-enclosed list index
                                       (?:[\{{\uFF5B] (?:[{numberish}] | ['\uFF07][{numberish}]['\uFF07] | ["\uFF02][{numberish}]["\uFF02]) [\}}\uFF5D])  # Brace-enclosed number
                                    )
                                    (?:[.\uFF0E]  # Separating period, then subsequent element
                                       (?:
                                          (?:[^{ws}{na}\d][^{ws}{na}]*) |  # Identifier-style
                                          (?:[\[\uFF3B] (?:[+\uFF0B]|[+\uFF0B-\uFF0D]?[0-9\uFF10-\uFF19]+) [\]\uFF3D]) |  # Bracket-enclosed list index
                                          (?:[\{{\uFF5B] (?:[{numberish}] | ['\uFF07][{numberish}]['\uFF07] | ["\uFF02][{numberish}]["\uFF02]) [\}}\uFF5D])  # Brace-enclosed number
                                       )
                                    )*
                                    '''
        not_allowed_unquoted_keypath = self.unicodefilter.to_ascii_and_fullwidth(self._not_unquoted_ascii_str + '.')
        pattern_numberish = r'[0-9\uFF10-\uFF19a-z\uFF41-\uFF5AA-Z\uFF21-\uFF3A]'
        pattern_unquoted_keypath = pattern_unquoted_keypath.format(ws=re.escape(self.unicode_whitespace_str), na=re.escape(not_allowed_unquoted_keypath), numberish=pattern_numberish)
        self._unquoted_keypath_re = re.compile(pattern_unquoted_keypath, re.VERBOSE)

        self._unquoted_string_piece_re = re.compile(r'[^{0}]'.format(re.escape(self._not_unquoted_str)))


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


    def _parse_line_start_next(self, line=None):
        '''
        Reset everything after `_parse_line_get_next()`, so that it's
        equivalent to using `_parse_line_goto_next()`.  Useful when
        `_parse_line_get_next()` is used for lookahead, but nothing is consumed.
        '''
        self.source.start_lineno = self.source.end_lineno
        self._at_line_start = True
        return line


    def _parse_line_continue_next(self, line=None):
        '''
        Reset everything after `_parse_line_get_next()`, to continue on with
        the next line after having consumed part of it.
        '''
        self.source.start_lineno = self.source.end_lineno
        self._at_line_start = False
        return line


    def _parse_line_goto_next(self, line=None):
        '''
        Go to next line, after current parsing is complete.
        '''
        line = next(self._line_gen, None)
        if line is not None:
            self._indent, line = self._split_line_on_indent(line)
        if self.source.end_lineno <= self.source.start_lineno:
            self.source.start_lineno += 1
        else:
            self.source.start_lineno = self.source.end_lineno + 1
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
            if m is not None:
                line = line[m.end():]
            else:
                while m is None:
                    line = self._parse_line_get_next()
                    if line is None:
                        raise erring.ParseError('Never found end of multi-line comment', self.source)
                    m = end_delim_re.match(line)
                line = line[m.end():]
                self._parse_line_continue_next()
            if not line.lstrip(self.whitespace_str):
                line = self._parse_line_goto_next()
        return line


    def _parse_line_open_paren(self, line):
        '''
        Parse explicit typing.
        '''
        if self._next_type is not None:
            raise erring.ParseError('Duplicate or unused explicit type declarations', self.source)
        m = self._explicit_type_re.match(line)
        if not m:
            raise erring.ParseError('Could not parse explicit type declaration', self.source)
        self._next_type = m.group(0)[1:-2]
        line = line[m.end():].lstrip(self.whitespace_str)
        if self._next_type and not self._compact:
            if self._next_type in ('str.empty', 'bin.empty'):
                # Go ahead and deal with empty strings and binary strings
                # These must be on the same line as the type declaration
                if not line:
                    self._ast.append(self.string_parsers[self._next_type](''))
                    self._next_type = None
                    self._at_line_start = False
                else:
                    m = self._opening_delim_equals_re.match(line)
                    if self._at_line_start and m and len(m.group(0)):
                        line = line[1:]
                        self._ast.append(AstObj('kvpair', self))
                        self._ast.append(self.string_parsers[self._next_type](''))
                        self._next_type = None
                        self._at_line_start = False
                    else:
                        raise erring.ParseError('Could not resolve empty type "{0}"'.format(self._next_type), self.source)
            elif self._at_line_start:
                if not line and self._next_type in self.dict_parsers:
                    self._ast.append(AstObj('dict', self))
                    self._next_type = None
                    line = self._parse_line_goto_next()
                elif not line and self._next_type in self.list_parsers:
                    self._ast.append(AstObj('list', self))
                    self._next_type = None
                    line = self._parse_line_goto_next()
                else:
                    self._next_type_indent = self._indent
        return line


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
            line = line[m.end():]
        else:
            s_lines = [line]
            if self._at_line_start:
                indent = self._indent
            else:
                indent = self._ast.indent
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
                    line = line[m.end():]
                    s = self._process_quoted_string(s_lines, delim, end_delim)
                    break
        try:
            s = self.string_parsers[self._next_type](s)
        except KeyError:
            raise erring.ParseError('Invalid explicit type "{0}" applied to string'.format(self._next_type), self.source)
        except Exception as e:
            raise erring.ParseError('Could not convert quoted string to type "{0}":\n  {1}'.format(self._next_type, e), self.source)
        if self._next_type_indent:
            self._indent = self._next_type_indent
        if self._at_line_start and not self._compact:
            line = line.lstrip(self.whitespace_str)
            m = self._opening_delim_equals_re.match(line)
            if m:
                if len(m.group(0)) != 1:
                    raise erring.ParseError('Unexpected equals signs', self.source)
                line = line[1:]
                self._ast.append(AstObj('kvpair', self))
                self._ast.append(s)
            else:
                self._ast.append(s)
        elif not self._compact:
            self._ast.append(s)
        else:
            raise erring.ParseError('Unfinished parsing path')
        self._next_type = None
        self._next_type_indent = None
        self._at_line_start = False
        return line


    def _process_quoted_string(self, s_lines, delim, end_delim):
        '''
        Process list of raw text lines that make up a quoted string.  The
        string wraps over multiple lines if it is an inline string.
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
                        raise erring.ParseError('Inconsistent indentation within inline string', self.source)
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
            if self._at_line_start and self._indent != indent:
                raise erring.ParseError('Opening and closing delimiters for block string do not have matching indentation', self.source)
            for n, line in enumerate(s_lines[1:-1]):
                if line.startswith(indent):
                    s_lines[n+1] = line[len_indent:]
                else:
                    if not line.lstrip(self.whitespace_str):
                        s_lines[n+1] = line.lstrip(self.indents_str)
                    else:
                        raise erring.ParseError('Inconsistent indent in block string', self.source)
            if len(delim) == len(end_delim) - 2:
                s_lines[-2] = s_lines[-2].rstrip(self.newline_chars_str)
            s = ''.join(s_lines[1:-1])
        return s


    def _parse_line_equals(self, line):
        '''
        Parse line segment beginning with equals sign.
        '''
        if not self._at_line_start:
            raise erring.ParseError('Unexpected equals sign', self.source)
        m = self._opening_delim_equals_re.match(line)
        if len(m.group(0)) == 1:
            line = line[1:]
            s = self.string_parsers[self._next_type]('')
            self._ast.append(AstObj('kvpair', self))
            self._ast.append(s)
            # Type must be `None`; when parsing explicit type declaractions,
            # empty types are immediately resolved to ensure that the type
            # declaration and object are on the same line.  So no need to
            # reset `_next_type` and `_next_type_indent`.
            self._at_line_start = False
        else:
            raise erring.ParseError('Unsupported branch')
        return line

    def _parse_line_plus(self, line):
        m = self._opening_delim_plus_re.match(line)
        if len(m.group(0)) == 1:
            if line[1:2] == '' or line[1:2] in self.whitespace:
                if not self._at_line_start:
                    raise erring.ParseError('Unexpected plus sign', self.source)
                if not (self._ast.pos.cat == 'list' and self._ast.pos.indent == self._indent):
                    self._ast.append(AstObj('list', self))
                if self._ast.pos.open:
                    self._ast.pos.append('')
                self._ast.pos.open = True
                plus = line[0]
                line = line[1:]
                extra_indent = line[:len(line)-len(line.lstrip(self.indents_str))]
                if not (self._indent[-2:-1] == '\t' and extra_indent[:1] == '\t'):
                    if plus == '+':
                        extra_indent = '\x20' + extra_indent
                    else:
                        extra_indent = '\u3000' + extra_indent
                self._indent += extra_indent
                line = line.lstrip(self.whitespace_str)
        return line

    def _parse_line_semicolon(self, line):
        pass

    def _parse_line_pipe(self, line):
        pass

    def _parse_line_whitespace(self, line):
        '''
        Parse line segment beginning with whitespace.
        '''
        if self._at_line_start and line.lstrip(self.whitespace_str):
            self._indent, line = self._split_line_on_indent(line)
        elif line.lstrip(self.whitespace_str):
            line = line.lstrip(self.whitespace_str)
        else:
            while True:
                line = self._parse_line_goto_next()
                if line is None:
                    if self._ast.pos == self._ast.root and not self._ast.root:
                        try:
                            self._ast.append(self.string_parsers[self._next_type](''))
                        except KeyError:
                            raise erring.ParseError('Invalid explicit type "{0}" applied to string'.format(self._next_type), self.source)
                    break
                elif line.lstrip(self.whitespace_str):
                    break
        return line

    def _parse_line_unquoted_string(self, line):
        m_keypath = self._unquoted_keypath_re.match(line)
        if m_keypath and line[m_keypath.end():].lstrip(self.whitespace_str)[:1] in self._equals:
            if not self._at_line_start:
                raise erring.ParseError('Cannot start a key in a dict-like object here')
            k = m_keypath.group(0).replace('\uFF0E', '.')
            line = line[m_keypath.end():].lstrip(self.whitespace_str)[1:]
            path = k.split('.')
            if len(path) == 1:
                self._ast.append(AstObj('kvpair', self))
                self._ast.append(self._type_unquoted_string(path[0]))
                self._next_type = None
                self._next_type_indent = None
                self._at_line_start = False
            else:
                raise erring.ParseError('Unsupported branch', self.source)
        else:
            m = self._unquoted_string_piece_re.match(line)
            if not m:
                raise erring.ParseError('Invalid unquoted string', self.source)
            s = m.group(0)
            if len(s) < len(line):
                rest = line[m.end():]  # Regex matches whitespace, so no need to strip
                if rest[:1] in self._equals:
                    if not self._at_line_start:
                        raise erring.ParseError('Cannot start a key in a dict-like object here')
                    m_key = self._unquoted_key_re.match(s)
                    if not (m and len(m.group(0)) == len(s)):
                        raise erring.ParseError('An unquoted key in a dict-like object cannot contain Unicode whitespace')
                    line = rest[1:]
                    self._ast.append(AstObj('kvpair', self))
                    self._ast.append(self._type_unquoted_string(s))
                    self._next_type = None
                    self._next_type_indent = None
                    self._at_line_start = False
                else:
                    self._ast.append(self._type_unquoted_string(s))
                    self._next_type = None
                    self._next_type_indent = None
                    self._at_line_start = False
            else:
                pass

        return line




    def _type_unquoted_string(self, s):
        s = s.strip(self.whitespace_str)
        if s[:1] in self.unicode_whitespace or s[-2:-1] in self.unicode_whitespace:
            raise erring.ParseError('An unquoted string must not begin or end with Unicode whitespace characters besides space, tab, and ideographic space', self.source)
        if self._next_type:
            s_typed = self.string_parsers[self._next_type](s)
        elif s in self.reserved_words:
            s_typed = self.reserved_words[s]
        else:
            m_int = self._int_re.match(s)
            if m_int:
                s_typed = int(s.replace('_', ''))
            else:
                m_float = self._float_re.match(s)
                if m_float:
                    s_typed = float(s.replace('_', ''))
                else:
                    s_typed = s
        return s_typed



# Fix _next_type_indent
