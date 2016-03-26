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
import base64
import binascii
import collections
import copy
import re




class State(object):
    '''
    Keep track of state:  the name of a source (file name, or <string>), the
    current location within the source (range of lines currently being parsed,
    plus indentation and whether at beginning of line), whether syntax is
    inline, explicit typing to be applied to the next object, the next
    string-like object, etc.

    An instance is created when decoding begins, and line numbers are updated
    as parsing proceeds.  The instance is passed on to any parsing errors that
    are raised, to provide informative error messages.
    '''
    __slots__ = ['ast', 'decoder', 'source', 'indent', 'at_line_start', 'start_lineno', 'end_lineno',
                 'type', 'type_indent', 'type_at_line_start', 'type_lineno', 'type_cat',
                 'stringlike', 'stringlike_indent', 'stringlike_at_line_start', 'stringlike_start_lineno', 'stringlike_end_lineno',
                     'stringlike_effective_indent', 'stringlike_effective_at_line_start', 'stringlike_effective_start_lineno',
                 'inline', 'inline_indent']

    def __init__(self, ast=None, decoder=None, source=None, indent=None, at_line_start=True, start_lineno=0, end_lineno=0):
        self.ast = ast
        self.decoder = decoder
        if source is None:
            source = '<string>'
        self.source = source
        self.indent = indent
        self.at_line_start = at_line_start
        self.start_lineno = start_lineno
        self.end_lineno = end_lineno

        self.type = None
        self.type_indent = None
        self.type_at_line_start = None
        self.type_lineno = None
        self.type_cat = None

        self.stringlike = []
        self.stringlike_indent = None
        self.stringlike_at_line_start = None
        self.stringlike_start_lineno = None
        self.stringlike_end_lineno = None
        self.stringlike_effective_indent = None
        self.stringlike_effective_at_line_start = None
        self.stringlike_effective_start_lineno = None

        self.inline = False
        self.inline_indent = None

    def register(self, ast=None, decoder=None):
        if ast is not None:
            self.ast = ast
        if decoder is not None:
            self.decoder = decoder

    traceback_namedtuple = collections.namedtuple('traceback_namedtuple', ['source', 'start_lineno', 'end_lineno'])

    def set_type(self, t):
        if self.type:
            raise erring.ParseError('A previous explicit type declaration has not yet been resolved', self.traceback_type)
        if self.inline and not self.indent.startswith(self.inline_indent):
            raise erring.ParseError('INdentation error in explicity type definition', self.traceback)
        self.type = t
        self.type_indent = self.indent
        self.type_at_line_start = self.at_line_start
        self.type_lineno = self.start_lineno
        try:
            self.type_cat = self.decoder.parser_cats[t]
        except KeyError:
            raise erring.ParseError('Unknown explicit type "{0}"'.format(t), self.traceback_type)

    def set_stringlike(self, s):
        if self.stringlike:
            raise erring.ParseError('A previous string-like object has not yet been resolved', self.traceback_stringlike)
        self.stringlike.append(s)
        self.stringlike_indent = self.indent
        self.stringlike_at_line_start = self.at_line_start
        self.stringlike_start_lineno = self.start_lineno
        self.stringlike_end_lineno = self.end_lineno

        if self.type:
            self.stringlike_effective_start_lineno = self.type_lineno
            if self.inline:
                # All lines in inline syntax, including the first, are
                # guaranteed to start with the same minimum Indentation
                if not self.stringlike_indent.startswith(self.inline_indent):
                    raise erring.ParseError('Indentation error in string', self.traceback_type)
                # `stringlike_effective_at_line_start` isn't important in
                # inline syntax, so don't actually calculate
                self.stringlike_effective_at_line_start = False
                self.stringlike_effective_indent = self.inline_indent
            else:
                if not self.stringlike_at_line_start and self.stringlike_start_lineno != self.type_lineno:
                    raise erring.ParseError('Indeterminate indentation for string-like object', self.traceback_stringlike)
                if ((self.type_at_line_start and self.stringlike_at_line_start and not self.stringlike_indent.startswith(self.type_indent)) or
                        (not self.type_at_line_start and self.stringlike_at_line_start and
                            not (self.stringlike_indent.startswith(self.type_indent) and len(self.stringlike_indent) > len(self.type_indent)) ) ):
                    # When `stringlike_at_line_start` is False, indentation
                    # would automatically be identical
                    raise erring.ParseError('Indentation error in string-like object', self.traceback_stringlike)
                self.stringlike_effective_at_line_start = self.type_at_line_start
                self.stringlike_effective_indent = self.type_indent
        else:
            self.stringlike_effective_start_lineno = self.stringlike_start_lineno
            if self.inline:
                self.stringlike_effective_at_line_start = False
                if not self.stringlike_indent.startswith(self.inline_indent):
                    raise erring.ParseError('Indentation error in string', self.traceback_type)
                self.stringlike_effective_indent = self.inline_indent
            else:
                self.stringlike_effective_at_line_start = self.stringlike_at_line_start
                self.stringlike_effective_indent = self.stringlike_indent

    def start_inline(self):
        self.inline = True
        if self.type:
            if not self.at_line_start and self.start_lineno != self.type.lineno:
                raise erring.ParseError('Indeterminate indentation at start of explicitly typed inline collection object', self.state.traceback)
            if ((self.type_at_line_start and self.at_line_start and not self.indent.startswith(self.type_indent)) or
                    (not self.type_at_line_start and self.at_line_start and
                        not (self.indent.startswith(self.type_indent) and len(self.indent) > len(self.type_indent)) ) ):
                raise erring.ParseError('Indentation error at start of explicitly typed inline collection object', self.traceback_stringlike)
            self.inline_indent = self.type_indent
        else:
            self.inline_indent = self.indent

    @property
    def traceback(self):
        if self.type:
            return self.traceback_namedtuple(self.source, self.type_start_lineno, self.end_lineno)
        else:
            if self.stringlike:
                return self.traceback_namedtuple(self.source, self.stringlike_start_lineno, self.end_lineno)
            else:
                return self.traceback_namedtuple(self.source, self.start_lineno, self.end_lineno)

    @property
    def traceback_current_start(self):
        if self.type:
            return self.traceback_namedtuple(self.source, self.type_start_lineno, self.type_start_lineno)
        else:
            if self.stringlike:
                return self.traceback_namedtuple(self.source, self.stringlike_start_lineno, self.stringlike_start_lineno)
            else:
                return self.traceback_namedtuple(self.source, self.start_lineno, self.start_lineno)

    @property
    def traceback_type(self):
        return self.traceback_namedtuple(self.source, self.type_lineno, self.type_lineno)

    @property
    def traceback_stringlike(self):
        return self.traceback_namedtuple(self.source, self.stringlike_start_lineno, self.stringlike_end_lineno)

    @property
    def traceback_start_inline_to_end(self):
        p = self.ast.pos
        while p.parent.inline:
            p = p.parent
        return self.traceback_namedtuple(self.source, p.start_lineno, self.end_lineno)

    @property
    def traceback_ast_pos(self):
        return self.traceback_namedtuple(self.source, self.ast.pos.start_lineno, selt.ast.pos.end_lineno)

    @property
    def traceback_ast_pos_end_to_end(self):
        return self.traceback_namedtuple(self.source, self.ast.pos.end_lineno, self.state.end_lineno)




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
      +  indent       = Indentation of object.
      +  inline       = Whether the object was opened in inline syntax.
      +  nodetype     = The type of the object, if the object is explicitly
                        typed via `(type)>` syntax.  Otherwise, type is
                        inherited from `cat`.
      +  parent       = Parent node in AST.
      +  start_lineno = Line number on which object started.  Used for
                        providing line error information for instances that
                        were never closed.
      +  state        = Decoder state.


    End lineno for astobj isn't actually complete end, but is kept updated.
    '''
    __slots__ = ['ast', 'cat', 'check_append', 'end_lineno', 'indent', 'inline',
                 'index', 'open', 'parent', 'start_lineno', 'state', 'type']

    def __init__(self, cat, ast, indent):
        self.cat = cat
        self.ast = ast
        self.state = ast.state
        if cat != 'root':
            self.inline = self.state.inline
            self.indent = indent
            if self.state.type:
                self.start_lineno = self.state.type_start_lineno
            elif self.state.stringlike:
                self.start_lineno = self.state.stringlike_start_lineno
            else:
                self.start_lineno = self.state.start_lineno
            self.end_lineno = self.start_lineno
            if self.state.type and not self.state.stringlike:
                if not self.inline and (not self.state.type_at_line_start or self.start_lineno == self.state.start_lineno):
                    raise erring.ParseError('Explicit type declaration for {0}-like object must be on a line by itself in non-inline syntax'.format(cat), self.state.traceback_type)
                if not self.state.type_cat != self.cat:
                    raise erring.ParseError('Invalid explicit type "{0}" applied to {1}-like collection object'.format(self.state.type, self.cat), self.state.traceback_type)
                self.type = self.state.type
                self.state.type = None
            else:
                self.type = None
            self.open = False
            self.parent = ast.pos
            self.index = len(ast.pos)
        else:
            self.type = 'root'
            self.indent = None
            self.inline = None
            self.start_lineno = None
            self.end_lineno = None
            self.parent = None
            self.index = None
            self.open = None
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
            raise erring.ParseError('Only a single object is allowed at root level', self.state.traceback)
        if isinstance(val, AstObj):
            self.append(val)
            self.start_lineno = val.start_lineno
            self.end_lineno = val.end_lineno
            self.ast.pos = self.ast.pos[-1]
            self.ast._obj_to_pythonize_list.append(val)
        else:
            self.append(val)
            if self.state.type:
                self.start_lineno = self.state.type_lineno
            else:
                self.start_lineno = self.state.stringlike_start_lineno
            self.end_lineno = self.state.stringlike_end_lineno
            self.state.type = None
            self.state.stringlike.pop()

    def _check_append_dict(self, val):
        if not (isinstance(val, AstObj) and val.cat == 'kvpair'):
            raise erring.ParseError('Cannot add a non key-value pair to a dict-like object', self.state.traceback)
        if val.indent != self.indent:
            raise erring.ParseError('Indentation error in dict-like object', self.state.traceback)
        if self.inline and not self.open:
            # Due to syntax, non-inline key-value pairs are "self-opening"
            raise erring.ParseError('Cannot add a key-value pair to a dict-like object when the previous pair has not been terminated by a semicolon', self.state.traceback)
        self.append(val)
        self.end_lineno = val.end_lineno
        self.open = False
        self.ast.pos = self.ast.pos[-1]

    def _check_append_kvpair(self, val):
        if len(self) == 2:
            raise erring.ParseError('Key-value pair can only contain two elements', self.state.traceback)
        if isinstance(val, AstObj):
            if not self:
                raise erring.ParseError('Keys for dict-like objects cannot be collection types', self.state.traceback)
            if ((self.inline and val.indent != self.indent) or
                    (not self.inline and not (val.indent.startswith(self.indent) and
                        (len(val.indent) > len(self.indent) or (val.inline and val.start_lineno == self.end_lineno and len(val.indent) == len(self.indent))) ) ) ):
                raise erring.ParseError('Indentation error in dict-like object', self.state.traceback)
            self.append(val)
            self.end_lineno = val.end_lineno
            self.ast.pos = self.ast.pos[-1]
            self.ast._obj_to_pythonize_list.append(val)
        else:
            if not self:
                if self.state.stringlike_effective_indent != self.indent:
                    raise erring.ParseError('Indentation error in dict-like object', self.state.traceback)
                if not self.inline and not self.state.stringlike_effective_at_line_start:
                    raise erring.ParseError('Indeterminate indentation when attempting to add a key to a dict-like object', self.state.traceback)
                self.append(val)
            else:
                if ((self.inline and self.state.stringlike_effective_indent != self.indent) or
                        (not self.inline and self.state.stringlike_effective_at_line_start and
                            not (len(self.state.stringlike_effective_indent) > len(self.indent) and self.state.stringlike_effective_indent.startswith(self.indent))) ):
                    raise erring.ParseError('Indentation error in dict-like object', self.state.traceback)
                elif not self.inline and not self.state.stringlike_effective_at_line_start:
                    if self.state.stringlike_effective_start_lineno != self.end_lineno:
                        raise erring.ParseError('Indeterminate indentation when attempting to add a value to a dict-like object', self.state.traceback)
                    if not (len(self.state.stringlike_effective_indent) >= len(self.indent) and self.state.stringlike_effective_indent.startswith(self.indent)):
                        raise erring.ParseError('Indentation error in dict-like object', self.state.traceback)
                self.append(val)
            self.end_lineno = self.state.stringlike_end_lineno
            self.state.type = None
            self.state.stringlike.pop()
            if len(self) == 2:
                self.ast.pos = self.ast.pos.parent

    def _check_append_list(self, val):
        if not self.open:
            raise erring.ParseError('Cannot append to a list-like object when the current location has already been filled', self.state.traceback)
        if isinstance(val, AstObj):
            if self.inline and val.indent != self.indent:
                raise erring.ParseError('Indentation error in list-like object', self.state.traceback)
            elif not self.inline:
                if self.indent[-1:] == '\t' and val.indent[len(self.indent):len(self.indent)+1] == '\t':
                    if not (len(val.indent) >= len(self.indent) + 1 and val.indent.startswith(self.indent)):
                        raise erring.ParseError('Indentation error in list-like object', self.state.traceback)
                else:
                    if not (len(val.indent) >= len(self.indent) + 2 and val.indent.startswith(self.indent)):
                        raise erring.ParseError('Indentation error in list-like object', self.state.traceback)
            self.append(val)
            self.end_lineno = val.end_lineno
            self.ast.pos = self.ast.pos[-1]
            self.ast._obj_to_pythonize_list.append(val)
        else:
            if self.inline and self.state.stringlike_effective_indent != self.indent:
                raise erring.ParseError('Indentation error in list-like object', self.state.traceback)
            elif not self.inline:
                if not self.state.stringlike_effective_at_line_start:
                    raise erring.ParseError('Indeterminate indentation when appending to list-like object', self.state.traceback)
                elif self.indent[-1:] == '\t' and self.state.stringlike_effective_indent[len(self.indent):len(self.indent)+1] == '\t':
                    if not (len(self.state.stringlike_effective_indent) >= len(self.indent) + 1 and self.state.stringlike_effective_indent.startswith(self.indent)):
                        raise erring.ParseError('Indentation error in list-like object', self.state.traceback)
                else:
                    if not (len(self.state.stringlike_effective_indent) >= len(self.indent) + 2 and self.state.stringlike_effective_indent.startswith(self.indent)):
                        raise erring.ParseError('Indentation error in list-like object', self.state.traceback)
            self.append(val)
            self.end_lineno = self.state.stringlike_end_lineno
            self.state.type = None
            self.state.stringlike.pop()
        self.open = False




class Ast(object):
    '''
    Abstract syntax tree of data, before final, full conversion into Python
    objects.  At this stage, all non-collection types are in final form,
    and all collection types are represented as `AstObj` instances, which
    are a subclass of list and can represent all collection types in a form
    that may be conveniently translated to Python objects.

    The `pythonize()` method converts all `AstObj` instances into the
    corresponding Python objects.
    '''
    def __init__(self, decoder):
        self.decoder = decoder
        self.state = decoder.state
        self.root = AstObj('root', self, None)
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

    def append_collection(self, cat):
        if self.state.inline:
            if not self.state.indent.startswith(self.state.inline_indent):
                raise erring.ParseError('Indentation error', self.state.traceback)
            indent = self.state.inline_indent
        elif self.state.stringlike:
            indent = self.state.stringlike_effective_indent
        elif self.state.type:
            indent = self.state.type_indent
        elif self.state.at_line_start:
            indent = self.state.indent
        else:
            raise erring.ParseError('Indeterminate indentation when creating {0}-like object'.format(cat), self.state.traceback)
        while self.pos is not self.root and len(indent) < len(self.pos.indent):
            if self.pos.cat == 'kvpair' and len(self.pos) < 2:
                raise erring.ParseError('A key-value pair was truncated before being completed', self.state.traceback_ast_pos)
            elif self.pos.cat == 'dict' and not self.pos and not self.pos.inline:
                raise erring.ParseError('A non-inline dict cannot be empty', self.traceback_ast_pos)
            elif self.pos.cat == 'list' and not self.pos.inline:
                if self.pos.open:
                    raise erring.ParseError('A list-like object was truncated before an expected element was added', self.state.traceback_ast_pos)
                if not self.pos:
                    raise erring.ParseError('A non-inline list cannot be empty', self.state.traceback_ast_pos)
            self.pos.parent.end_lineno = self.pos.end_lineno
            self.pos = self.pos.parent
            if self.pos.cat == 'kvpair':
                if len(self.pos) < 2:
                    raise erring.ParseError('A key-value pair was truncated before being completed', self.state.traceback_ast_pos)
                self.pos.parent.end_lineno = self.pos.end_lineno
                self.pos = self.pos.parent
        if not self.state.inline and cat == 'kvpair' and self.pos.cat != 'dict':
            self.pos.check_append(AstObj('dict', self, indent))
        self.pos.check_append(AstObj(cat, self, indent))

    def append_stringlike(self):
        self.pos.check_append(self.state.stringlike[0])

    def open_collection_inline(self):
        if not (self.state.inline and self.pos.cat in ('dict', 'list')):
            raise erring.ParseError('Invalid object termination (semicolon)', self.state.traceback)
        if self.pos.open:
            raise erring.ParseError('Encountered ";" when there is no object to end', self.state.traceback)
        self.pos.open = True

    def open_list_non_inline(self):
        if self.state.inline or not self.state.at_line_start:
            raise erring.ParseError('Invalid location to begin a non-inline list element')
        while self.pos is not self.root and len(self.state.indent) < len(self.pos.indent):
            if self.pos.cat == 'kvpair' and len(self.pos) < 2:
                raise erring.ParseError('A key-value pair was truncated before being completed', self.state.traceback_ast_pos)
            elif self.pos.cat == 'dict' and not self.pos and not self.pos.inline:
                raise erring.ParseError('A non-inline dict cannot be empty', self.traceback_ast_pos)
            elif self.pos.cat == 'list' and not self.pos.inline:
                if self.pos.open:
                    raise erring.ParseError('A list-like object was truncated before an expected element was added', self.state.traceback_ast_pos)
                if not self.pos:
                    raise erring.ParseError('A non-inline list cannot be empty', self.state.traceback_ast_pos)
            self.pos.parent.end_lineno = self.pos.end_lineno
            self.pos = self.pos.parent
            if self.pos.cat == 'kvpair':
                if len(self.pos) < 2:
                    raise erring.ParseError('A key-value pair was truncated before being completed', self.state.traceback_ast_pos)
                self.pos.parent.end_lineno = self.pos.end_lineno
                self.pos = self.pos.parent
        if self.pos.cat != 'list' or len(self.pos.indent) < len(self.state.indent):
            self.append_collection('list')
        self.pos.open = True

    def end_dict_inline(self):
        if not self.state.inline:
            raise erring.ParseError('Cannot end an inline dict-like object with "}" when not in inline mode', self.state.traceback)
        if not self.pos.cat == 'dict':
            raise erring.ParseError('Encountered "}" when there is no dict-like object to end', self.state.traceback)
        if not self.state.indent.startswith(self.state.inline_indent):
            raise erring.ParseError('Indentation error', self.state.traceback)
        self.pos = self.pos.parent
        self.state.inline = self.pos.inline
        if self.pos.cat == 'kvpair' and len(self.pos) == 2:
            self.pos = self.pos.parent
            self.state.inline = self.pos.inline

    def end_list_inline(self):
        if not self.state.inline:
            raise erring.ParseError('Cannot end an inline list-like object with "]" when not in inline mode', self.state.traceback)
        if not self.pos.cat == 'list':
            raise erring.ParseError('Encountered "]" when there is no list-like object to end', self.state.traceback)
        if not self.state.indent.startswith(self.state.inline_indent):
            raise erring.ParseError('Indentation error', self.state.traceback)
        self.pos = self.pos.parent
        self.state.inline = self.pos.inline
        if self.pos.cat == 'kvpair' and len(self.pos) == 2:
            self.pos = self.pos.parent
            self.state.inline = self.pos.inline


    def finalize(self):
        if self.pos is not self.root:
            if self.state.inline:
                raise erring.ParseError('Inline syntax was never closed', self.state.traceback_start_inline_to_end)
            if self.state.type:
                raise erring.ParseError('Explicit type definition was never used', self.state.traceback_type)
            if self.state.stringlike:
                raise erring.ParseError('String-like object was never used', self.state.traceback_stringlike)
            while self.pos is not self.root:
                if self.pos.cat == 'kvpair' and len(self.pos) < 2:
                    raise erring.ParseError('A key-value pair was truncated before being completed', self.state.traceback_ast_pos)
                elif self.pos.cat == 'dict' and not self.pos and not self.pos.inline:
                    raise erring.ParseError('A non-inline dict cannot be empty', self.traceback_ast_pos)
                elif self.pos.cat == 'list' and not self.pos.inline:
                    if self.pos.open:
                        raise erring.ParseError('A list-like object was truncated before an expected element was added', self.state.traceback_ast_pos)
                    if not self.pos:
                        raise erring.ParseError('A non-inline list cannot be empty', self.state.traceback_ast_pos)
                self.pos.parent.end_lineno = self.pos.end_lineno
                self.pos = self.pos.parent

    def pythonize(self):
        for obj in reversed(self._obj_to_pythonize_list):
            py_obj = self.decoder.parsers[obj.cat][obj.type](obj)
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
        self.state = None

        # Whether to keep raw abstract syntax tree for debugging, or go ahead
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
                                     'odict': collections.OrderedDict}

        self.default_list_parsers = {'list':  list,
                                     'set':   set,
                                     'tuple': tuple}

        self.default_string_parsers = {'int':        int,
                                       'float':      float,
                                       'str':        str,
                                       'bytes':        bytes,
                                       'bytes.base16': base64.b16decode,
                                       'bytes.base64': base64.b64decode}

        self.default_reserved_words = {'true': True, 'TRUE': True, 'True': True,
                                       'false': False, 'FALSE': False, 'False': False,
                                       'null': None, 'NULL': None, 'Null': None,
                                       'inf': float('inf'), 'INF': float('inf'), 'Inf': float('inf'),
                                       '-inf': float('-inf'), '-INF': float('-inf'), '-Inf': float('-inf'),
                                       '+inf': float('+inf'), '+INF': float('+inf'), '+Inf': float('+inf'),
                                       'nan': float('nan'), 'NAN': float('nan'), 'NaN': float('nan')}

        self.default_aliases = {'b': 'bytes', 'b16': 'bytes.base16', 'b64': 'bytes.base64'}


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

        bytes_parser_re = re.compile(r'(?:^|[^:]+:)bytes(?:$|\.[^.]+)')
        self._bytes_parsers = set([p for p in self.string_parsers if bytes_parser_re.search(p)])

        if (set(self.dict_parsers) & set(self.list_parsers) & set(self.string_parsers)):
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
        for k, v in self.aliases.items():
            found = False
            if v in self.dict_parsers:
                self.dict_parsers[k] = self.dict_parsers[v]
                found = True
            elif v in self.list_parsers:
                self.list_parsers[k] = self.list_parsers[v]
                found = True
            elif v in self.string_parsers:
                self.string_parsers[k] = self.string_parsers[v]
                if bytes_parser_re.search(v):
                    self._bytes_parsers.update(k)
                found = True
            if not found:
                raise ValueError('Alias "{0}" => "{1}" maps to unknown type'.format(k, v))

        parser_cats = {}
        for c, d in self.parsers.items():
            for k in d:
                parser_cats[k] = c
        self.parser_cats = parser_cats

        # Set default parsers in each category
        self.dict_parsers[None] = self.dict_parsers['dict']
        self.list_parsers[None] = self.list_parsers['list']
        self.string_parsers[None] = self.string_parsers['str']


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


        # Characters that can't appear in normal unquoted strings.
        # `+` is only special in non-compact syntax, at the beginning of a
        # line, when followed by an indentation character (or Unicode
        # whitespace).  `|` is only special when followed by three or more
        # quotation marks or by a space (or Unicode whitespace).  Given the
        # limited context in which `+` and `|` are special, they are generally
        # allowed within unquoted strings.  All necessary conditions for when
        # they appear at the beginning of string are imposed in the
        # corresponding parsing functions.
        self.not_unquoted_str = '%()[]{}\'"=;'
        self.not_unquoted = set(self.not_unquoted_str)

        # Dict of functions for proceding with parsing, based on the next
        # character.
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
                       '|':  self._parse_line_pipe,
                       '':  self._parse_line_goto_next
                      }
        for c in self.whitespace:
            _parse_line[c] = self._parse_line_whitespace
        self._parse_line = collections.defaultdict(lambda: self._parse_line_unquoted_string, _parse_line)

        # Regex for matching explicit type declarations.  Don't need to filter
        # out all code points not allowed in type name; will attempt type
        # lookup and raise error upon failure.
        pattern_type = r'\([^{ws}{na}]+\)>'.format(ws=re.escape(self.unicode_whitespace_str), na=re.escape(self.not_unquoted_str.replace('=', '')))
        self._explicit_type_re = re.compile(pattern_type)

        # Regexes for identifying opening delimiters that may contains
        # multiple identical characters.
        def gen_opening_delim_regex(c):
            if c == '|':
                p = r'\|(?:\'+|\"+)'
            elif c == '+':
                p = r'\+[{ws}]+'.format(ws=re.escape(self.whitespace_str))
            else:
                p = r'{c}{c}{c}+|{c}'.format(c=re.escape(c))
            return re.compile(p)
        self._opening_delim_percent_re = gen_opening_delim_regex('%')
        self._opening_delim_single_quote_re = gen_opening_delim_regex("'")
        self._opening_delim_double_quote_re = gen_opening_delim_regex('"')
        self._opening_delim_equals_re = gen_opening_delim_regex('=')
        self._opening_delim_pipe_re = gen_opening_delim_regex('|')
        self._opening_delim_plus_re = gen_opening_delim_regex('+')

        # Dict of regexes for identifying closing delimiters.  Automatically
        # generate needed regex on the fly.
        def gen_closing_delim_regex(delim):
            c = delim[0]
            if c == '"':
                if delim == '"':
                    p = r'(?:\\.|[^"])*(")'.format(c=re.escape(c), n=len(delim))
                else:
                    p = r'(?:\\.|[^"])*({c}{{{n}}}(?!{c})/*)'.format(c=re.escape(c), n=len(delim))
            elif delim == "'":
                p = "'"
            elif c == '|':
                p = r'{c}{f}{{{n}}}(?!{f})/*'.format(c=re.escape(c), f=re.escape(delim[-1]), n=len(delim)-1)
            else:
                p = r'(?<!{c}){c}{{{n}}}(?!{c})/*'.format(c=re.escape(c), n=len(delim))
            return re.compile(p)
        self._closing_delim_re_dict = tooling.keydefaultdict(gen_closing_delim_regex)

        # Regex for integers, including hex, octal, and binary.
        pattern_int = r'''
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
        pattern_float = r'''
                         [+-]? (?: (?: \. [0-9](?:_(?=[0-9])|[0-9])* (?:[eE][+-]?[0-9](?:_(?=[0-9])|[0-9])*)? |
                                       (?:[1-9](?:_(?=[0-9])|[0-9])*|0)
                                          (?: \. (?:[0-9](?:_(?=[0-9])|[0-9])*)? (?:[eE][+-]?[0-9](?:_(?=[0-9])|[0-9])*)? |
                                              [eE][+-]?[0-9](?:_(?=[0-9])|[0-9])*
                                          )
                                   ) |
                                   0x (?: \.[0-9a-fA-F](?:_(?=[0-9a-fA-F])|[0-9a-fA-F])* (:? [pP][+-]?[0-9](?:_(?=[0-9])|[0-9])*)? |
                                          [0-9a-fA-F](?:_(?=[0-9a-fA-F])|[0-9a-fA-F])*
                                             (?: \. (?:[0-9a-fA-F](?:_(?=[0-9a-fA-F])|[0-9a-fA-F])*)? (:? [pP][+-]?[0-9](?:_(?=[0-9])|[0-9])*)? |
                                                 [pP][+-]?[0-9](?:_(?=[0-9])|[0-9])*
                                             )
                                      )
                               )
                         $
                         '''
        self._float_re = re.compile(pattern_float, re.VERBOSE)

        # There are multiple regexes for unquoted keys.  Plain unquoted keys
        # need to be distinguished from keys describing key paths.
        pattern_unquoted_key = r'[^{uws}{na}]+'.format(uws=re.escape(self.unicode_whitespace_str),
                                                       na=re.escape(self.not_unquoted_str))
        self._unquoted_key_re = re.compile(pattern_unquoted_key)

        pattern_keypath_element = r'''
                                   [^\.{uws}{na}\d][^\.{uws}{na}]* |  # Identifier-style
                                   \[ (?: \+ | [+-]?[0-9]+) \] |  # Bracket-enclosed list index
                                   \{{ (?: [^{uws}{na}]+ | '[^']*' | "(?:\\.|[^"])*" ) \}}  # Brace-enclosed unquoted string, or once-quoted inline string
                                   '''
        pattern_keypath_element = pattern_keypath_element.format(uws=re.escape(self.unicode_whitespace_str),
                                                                 na=re.escape(self.not_unquoted_str))
        self._keypath_element_re = re.compile(pattern_keypath_element, re.VERBOSE)

        pattern_keypath = r'''
                           (?:{kpe})
                           (?:\. (?:{kpe}) )*
                           '''
        pattern_keypath = pattern_keypath.format(kpe=pattern_keypath_element)
        self._keypath_re = re.compile(pattern_keypath, re.VERBOSE)

        self._unquoted_string_fragment_re = re.compile(r'[^{0}]+'.format(re.escape(self.not_unquoted_str)))


    def _unwrap_inline(self, s_list):
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
        newline_chars_str = self.newline_chars_str
        unicode_whitespace = self.unicode_whitespace
        for line in s_list[:-1]:
            line_strip_nl = line.rstrip(newline_chars_str)
            if line_strip_nl[-1] in unicode_whitespace:
                s_list_inline.append(line_strip_nl)
            else:
                s_list_inline.append(line_strip_nl + '\x20')
        s_list_inline.append(s_list[-1])
        return ''.join(s_list_inline)


    def _unicode_to_bytes(self, s):
        '''
        Encode a Unicode string to bytes.
        '''
        s = self.unicodefilter.unicode_to_ascii_newlines(s)
        try:
            s_bytes = s.encode('ascii')
        except UnicodeEncodeError as e:
            raise erring.BinaryStringEncodeError(s, e, self.state.traceback)
        return s_bytes


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

        # Create a generator for lines from the source, keeping newlines
        # Then parse to AST, and convert AST to Python objects
        self._line_gen = (line for line in s.splitlines(True))
        return self._parse_lines_to_py_obj()


    def _parse_lines_to_py_obj(self):
        '''
        Process lines from source into abstract syntax tree (AST).  All
        collection types, and key-value pairs, are initially represented as
        `AstObj` instances.  At the end, these are processed into actual dicts,
        lists, etc.  All other other objects appear in the AST as literals that
        do not require final parsing (null, bool, string, binary, int, float,
        etc.)

        Note that the root node of the AST is a `RootAstObj` instance.  This
        is an `AstObj` subclass that may only contain a single object.  At
        the root level, a BespON file may only contain a single scalar, or a
        single collection type.
        '''
        self.state = State()
        self.unicodefilter.traceback = self.state

        self._ast = Ast(self)
        self.state.register(ast=self._ast, decoder=self)

        # Start by extracting the first line and stripping any BOM
        line = self._parse_line_goto_next()
        if line:
            if line[0] == '\uFEFF':
                line = line[1:]
            elif line[0] == '\uFFFE':
                raise erring.ParseError('Encountered non-character U+FFFE, indicating string decoding with incorrect endianness', self.state.traceback)

        while line is not None:
            line = self._parse_line[line[:1]](line)

        self._ast.finalize()

        if not self._ast:
            raise erring.ParseError('There was no data to load', self.state)

        self.state = None
        self.unicodefilter.traceback = None

        if self._debug_raw_ast:
            return
        else:
            self._ast.pythonize()
            return self._ast.root[0]


    def _split_line_on_indent(self, line):
        '''
        Split a line into its leading indentation and everything else.
        '''
        rest = line.lstrip(self.indents_str)
        indent = line[:len(line)-len(rest)]
        return (indent, rest)


    def _parse_line_get_next(self, line=None):
        '''
        Get next line.  For use in lookahead in string scanning, etc.
        '''
        line = next(self._line_gen, None)
        self.state.end_lineno += 1
        return line


    def _parse_line_start_next(self, line=None):
        '''
        Reset everything after `_parse_line_get_next()`, so that it's
        equivalent to using `_parse_line_goto_next()`.  Useful when
        `_parse_line_get_next()` is used for lookahead, but nothing is consumed.
        '''
        if line is not None:
            self.state.at_line_start = True
            self.state.indent, line = self._split_line_on_indent(line)
            self.state.start_lineno = self.state.end_lineno
        return line


    def _parse_line_continue_next(self, line=None):
        '''
        Reset everything after `_parse_line_get_next()`, to continue on with
        the next line after having consumed part of it.
        '''
        self.state.at_line_start = False
        self.state.start_lineno = self.state.end_lineno
        return line


    def _parse_line_goto_next(self, line=None):
        '''
        Go to next line, after current parsing is complete.
        '''
        line = next(self._line_gen, None)
        if line is not None:
            self.state.at_line_start = True
            self.state.indent, line = self._split_line_on_indent(line)
            self.state.end_lineno += 1
            self.state.start_lineno = self.state.end_lineno
        return line


    def _parse_line_percent(self, line):
        '''
        Parse comments.
        '''
        delim = self._opening_delim_percent_re.match(line).group(0)
        if len(delim) < 3:
            if line.startswith('%!bespon'):
                if self.state.start_lineno != 1:
                    raise erring.ParseError('Encountered "%!bespon", but not on first line', self.state.traceback)
                elif self.state.indent or not self.state.at_line_start:
                    raise erring.ParseError('Encountered "%!bespon", but not at beginning of line', self.state.traceback)
                elif line[len('%!bespon'):].rstrip(self.whitespace_str):
                    raise erring.ParseError('Encountered unknown parser directives: "{0}"'.format(line.rstrip(self.newline_chars_str)), self.state.traceback)
                else:
                    line = self._parse_line_goto_next()
            else:
                line = self._parse_line_goto_next()
        else:
            line = line[len(delim):]
            indent = self.state.indent
            end_delim_re = self._closing_delim_re_dict[delim]
            text_after_opening_delim = line.lstrip(self.whitespace_str)
            empty_line = False
            while True:
                if delim in line:
                    m = end_delim_re.search(line)
                    if m:
                        if (empty_line and len(m.group(0)) == len(delim)):
                            raise erring.ParseError('Incorrect closing delimiter for multi-line comment containing empty line(s)', self.state.traceback)
                        if len(m.group(0)) > len(delim) + 2:
                            raise erring.ParseError('Incorrect closing delimiter for multi-line comment', self.state.traceback)
                        if len(m.group(0)) == len(delim) + 2:
                            if self.state.start_lineno == self.state.end_lineno:
                                raise erring.ParseError('Multi-line comment may not begin and end on the same line', self.state.traceback)
                            if text_after_opening_delim or line[:m.start()].lstrip(self.indents_str):
                                raise erring.ParseError('In multi-line comments, opening delimiter may not be followed by anything and closing delimiter may not be preceded by anything', self.state.traceback)
                        line = line[m.end():].lstrip(self.whitespace_str)
                        self._parse_line_continue_next()
                        break
                line = self._parse_line_get_next()
                if line is None:
                    raise erring.ParseError('Never found end of multi-line comment', self.state.traceback)
                if not empty_line and not line.lstrip(self.unicode_whitespace_str):
                    # Important to test this after the first lookahead, since
                    # the remainder of the starting line could very well be
                    # whitespace
                    empty_line = True
                if not line.startswith(indent) and line.lstrip(self.whitespace_str):
                    raise erring.ParseError('Indentation error in multi-line comment', self.state.traceback)
        while line is not None and not line.lstrip(self.whitespace_str):
            line = self._parse_line_goto_next()
        return line


    def _parse_line_open_paren(self, line):
        '''
        Parse explicit typing.
        '''
        if self.state.type:
            raise erring.ParseError('Duplicate or unused explicit type declaration', self.state.traceback_type)
        m = self._explicit_type_re.match(line)
        if not m:
            # Due to regex, any match is guaranteed to be a type name
            # consisting of at least one code point
            raise erring.ParseError('Could not parse explicit type declaration', self.state.traceback)
        t = m.group(0)[1:-2]
        self.state.set_type(t)
        self.state.at_line_start = False
        line = line[m.end():].lstrip(self.whitespace_str)
        if not line:
            line = self._parse_line_goto_next()
        return line


    def _parse_line_close_paren(self, line):
        '''
        Parse line segment beginning with closing parenthesis.
        '''
        raise erring.ParseError('Unexpected closing parenthesis', self.state.traceback)


    def _parse_line_open_bracket(self, line):
        '''
        Parse line segment beginning with opening square bracket.
        '''
        m_keypath = self._keypath_re.match(line)
        if m_keypath:
            line = self._parse_line_keypath(line, m_keypath)
        else:
            if not self.state.inline:
                self.state.start_inline()
            self._ast.append_collection('list')
            self._ast.pos.open = True
            line = line[1:].lstrip(self.whitespace_str)
            if not line:
                line = self._parse_line_goto_next()
        return line

    def _parse_line_close_bracket(self, line):
        '''
        Parse line segment beginning with closing square bracket.
        '''
        self._ast.end_list_inline()
        line = line[1:].lstrip(self.whitespace_str)
        if not line:
            line = self._parse_line_goto_next()
        return line


    def _parse_line_open_brace(self, line):
        '''
        Parse line segment beginning with opening curly brace.
        '''
        m_keypath = self._keypath_re.match(line)
        if m_keypath:
            line = self._parse_line_keypath(line, m_keypath)
        else:
            if not self.state.inline:
                self.state.start_inline()
            self._ast.append_collection('dict')
            self._ast.pos.open = True
            line = line[1:].lstrip(self.whitespace_str)
            if not line:
                line = self._parse_line_goto_next()
        return line

    def _parse_line_close_brace(self, line):
        '''
        Parse line segment beginning with closing curly brace.
        '''
        self._ast.end_dict_inline()
        line = line[1:].lstrip(self.whitespace_str)
        if not line:
            line = self._parse_line_goto_next()
        return line


    def _parse_line_single_quote(self, line):
        '''
        Parse single-quoted string.
        '''
        delim = self._opening_delim_single_quote_re.match(line).group(0)
        line = line[len(delim):]
        end_delim_re = self._closing_delim_re_dict[delim]
        match_group_num = 0
        return self._parse_line_quoted_string(line, delim, end_delim_re, match_group_num)


    def _parse_line_double_quote(self, line):
        '''
        Parse double-quoted string.
        '''
        delim = self._opening_delim_double_quote_re.match(line).group(0)
        line = line[len(delim):]
        end_delim_re = self._closing_delim_re_dict[delim]
        match_group_num = 1
        return self._parse_line_quoted_string(line, delim, end_delim_re, match_group_num)


    def _parse_line_quoted_string(self, line, delim, end_delim_re, match_group_num):
        '''
        Parse a quoted string, once the opening delim has been determined
        and stripped, and a regex for the closing delim has been assembled.
        '''
        m = end_delim_re.search(line)
        if m:
            end_delim = m.group(match_group_num)
            if len(end_delim) > len(delim):
                raise erring.ParseError('A block string may not begin and end on the same line', self.state.traceback)
            s = line[:m.start(match_group_num)]
            if len(delim) >= 3:
                s = self._process_quoted_string([s], delim, end_delim)
            line = line[m.end(match_group_num):]
        else:
            s_lines = [line]
            # No need to check for consistent indentation here; that is done
            # during determination of `effective_indent`
            if self.state.at_line_start:
                indent = self.state.indent
            elif self.state.inline:
                indent = self.state.inline_indent
            elif self.state.type:
                indent = self.state.type_indent
            else:
                indent = self.state.indent
            while True:
                line = self._parse_line_get_next()
                if line is None:
                    raise erring.ParseError('Text ended while scanning quoted string', self.state.traceback)
                if not line.startswith(indent) and line.lstrip(self.whitespace_str):
                    raise erring.ParseError('Indentation error within quoted string', self.state.traceback)
                if delim not in line:
                    s_lines.append(line)
                else:
                    m = end_delim_re.search(line)
                    if not m:
                        s_lines.append(line)
                    else:
                        end_delim = m.group(match_group_num)
                        s_lines.append(line[:m.start(match_group_num)])
                        line = line[m.end(match_group_num):]
                        s = self._process_quoted_string(s_lines, delim, end_delim)
                        break

        if self.state.type in self._bytes_parsers:
            s = self.unicodefilter.unicode_to_ascii_newlines(s)
            s = self._unicode_to_bytes(s)
            if delim[0] == '"':
                s = self.unicodefilter.unescape_bytes(s)
        elif delim[0] == '"':
            s = self.unicodefilter.unescape(s)

        try:
            s = self.string_parsers[self.state.type](s)
        except KeyError:
            raise erring.ParseError('Unknown explicit type "{0}" applied to string'.format(self.state.type), self.state.traceback_type)
        except Exception as e:
            raise erring.ParseError('Could not convert quoted string to type "{0}":\n  {1}'.format(self.state.type, e), self.state.traceback)

        self.state.set_stringlike(s)
        if self.state.start_lineno == self.state.end_lineno:
            self.state.at_line_start = False
        else:
            self._parse_line_continue_next()

        line = line.lstrip(self.whitespace_str)
        while line is not None:
            if line[:1] == '%':
                line = self._parse_line_percent(line)
            elif not line.lstrip(self.whitespace_str):
                line = self._parse_line_goto_next()
            else:
                break
        if line is not None and line[:1] == '=' and line[1:2] != '=':
            if self.state.inline and not self.state.indent.startswith(self.state.inline_indent):
                raise erring.ParseError('Indentation error', self.state.traceback)
            if not self.state.inline and self.state.stringlike_end_lineno != self.state.start_lineno:
                raise erring.ParseError('In a key-value pair in non-inline syntax, the equals sign "=" must follow the key on the same line', self.state.traceback)
            line = line[1:].lstrip(self.whitespace_str)
            self._ast.append_collection('kvpair')
            self._ast.append_stringlike()
        else:
            self._ast.append_stringlike()
        if line is not None and not line.lstrip(self.whitespace_str):
            line = self._parse_line_goto_next()
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
                    if not line.lstrip(self.unicode_whitespace_str):
                        raise erring.ParseError('Inline strings cannot contain empty lines', self.state.traceback)
                indent = s_lines[1][:len(s_lines[1].lstrip(self.indents_str))]
                len_indent = len(indent)
                for n, line in enumerate(s_lines[1:]):
                    if not line.startswith(indent) or line[len_indent:len_indent+1] in self.unicode_whitespace:
                        raise erring.ParseError('Inconsistent indentation or leading Unicode whitespace within inline string', self.state.traceback)
                    s_lines[n+1] = line[len_indent:]
            else:
                s_lines[1] = s_lines[1].lstrip(self.indents_str)
            # Take care of any leading/trailing spaces that separate delimiter
            # characters from identical characters in string.
            if len(delim) >= 3:
                dc = delim[0]
                if s_lines[0][:1] in self.spaces and s_lines[0].lstrip(self.spaces_str)[:1] == dc:
                    s_lines[0] = s_lines[0][1:]
                if s_lines[-1][-1:] in self.spaces and s_lines[-1].rstrip(self.spaces_str)[-1:] == dc:
                    s_lines[-1] = s_lines[-1][:-1]
            # Unwrap
            s = self._unwrap_inline(s_lines)
        else:
            if len(delim) < len(end_delim) - 2:
                raise erring.ParseError('Invalid ending delimiter for block string', self.state)
            if s_lines[0].lstrip(self.whitespace_str):
                raise erring.ParseError('Characters are not allowed immediately after the opening delimiter of a block string', self.state)
            if s_lines[-1].lstrip(self.indents_str):
                raise erring.ParseError('Characters are not allowed immediately before the closing delimiter of a block string', self.state)
            indent = s_lines[-1]
            len_indent = len(indent)
            if self.state.at_line_start and self.state.indent != indent:
                raise erring.ParseError('Opening and closing delimiters for block string do not have matching indentation', self.state)
            for n, line in enumerate(s_lines[1:-1]):
                if line.startswith(indent):
                    s_lines[n+1] = line[len_indent:]
                else:
                    if line.lstrip(self.whitespace_str):
                        raise erring.ParseError('Inconsistent indent in block string', self.state)
                    s_lines[n+1] = line.lstrip(self.indents_str)
            if len(delim) == len(end_delim) - 2:
                s_lines[-2] = s_lines[-2].rstrip(self.newline_chars_str)
            s = ''.join(s_lines[1:-1])
        return s


    def _parse_line_equals(self, line):
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

    def _parse_line_plus(self, line):
        m = self._opening_delim_plus_re.match(line)
        if not m:
            line = self._parse_line_unquoted_string(line)
        else:
            self._ast.open_list_non_inline()
            indent_after_plus = line[1:m.end()]
            line = line[m.end():]
            if line[:1] == '+' and self.opening_delim_plus_re.match(line):
                raise erring.ParseError('Cannot begin a list element on a line where one has already been started in non-inline syntax')
            if line:
                if self.state.indent[-1:] == '\t' and indent_after_plus[:1] == '\t':
                    self.state.indent += indent_after_plus
                else:
                    self.state.indent += '\x20' + indent_after_plus
            else:
                line = self._parse_line_goto_next()
        return line

    def _parse_line_semicolon(self, line):
        self._ast.open_collection_inline()
        line = line[1:].lstrip(self.whitespace_str)
        if not line:
            line = self._parse_line_goto_next()
        return line

    def _parse_line_pipe(self, line):
        m = self._opening_delim_pipe_re.match(line)
        if not m:
            if line[1:2] == '\x20':
                self.state.set_stringlike(line[2:])
                line = self._parse_line_goto_next()
            elif line[1:2] in self.unicode_whitespace:
                raise erring.ParseError('Invalid whitespace character after pipe "|"')
            else:
                line = self._parse_line_unquoted_string(line)
        else:
            delim = m.group(0)
            if not self.state.at_line_start:
                raise erring.ParseError('Pipe-quoted strings ( {0} ) are only allowed at the beginning of lines'.format(delim), self.state.traceback)
            if line[len(delim):].lstrip(self.whitespace_str):
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
                                if not s_line.lstrip(self.unicode_whitespace_str):
                                    raise erring.ParseError('Wrapped pipe-quoted string cannot contain empty lines; use block pipe-quoted string instead')
                            line_indent = s_list[0][len(indent)+1:]
                            len_line_indent = len(line_indent)
                            if not line_indent.lstrip(self.indents_str):
                                raise erring.ParseError('Invalid indentation in pipe-quoted string', self.state.traceback)
                            for n, s_line in enumerate(s_list):
                                if not s_line.startswith(line_indent) or s_line[len_line_indent:len_line_indent+1] in self.unicode_whitespace:
                                    raise erring.ParseError('Invalid indentation in pipe-quoted string', self.state.traceback)
                                s_list[n] = s_line[len_line_indent:]
                            s = self._unwrap_inline(s_lines)
                        else:
                            if len(delim) == len(end_delim) - 2:
                                s_list[-1] = s_list[-1].rstrip(self.newline_chars_str)
                            for s_line in s_list:
                                if s_line.startswith(indent) and s_line[len_indent:len_indent+1] in self.indents:
                                    line_indent = s_line[:len_indent+1]
                                    break
                            len_line_indent = len(line_indent)
                            for n, s_line in enumerate(s_list):
                                if s_line.startswith(line_indent):
                                    s_list[n] = s_line[len_line_indent:]
                                else:
                                    if s_line.lstrip(self.whitespace_str):
                                        raise erring.ParseError('Invalid indentation in pipe-quoted block string', self.state.traceback)
                                    s_list[n] = s_line.lstrip(self.indents_str)
                            s = ''.join(s_list)
                    break
                else:
                    s_list.append(line)
                    line = self._parse_line_get_next()
                    if line is None:
                        raise erring.ParseError('Text ended while scanning pipe-quoted string', self.state.traceback)
            self.state.set_stringlike(s)
            line = line.lstrip(self.whitespace_str)
            if not line:
                line = self._parse_line_goto_next()
        return line

    def _parse_line_whitespace(self, line):
        '''
        Parse line segment beginning with whitespace.
        '''
        raise erring.ParseError('Unexpected whitespace; if you are seeing this message, there is a bug in the parser', self.state.traceback)

    def _parse_line_unquoted_string(self, line):
        m = self._unquoted_string_fragment_re.match(line)
        if m.end() < len(line):
            s_list = [line[:m.end()]]
            line = line[m.end():]
            next_line_action = None
        else:
            s_list = [line]
            line = self._parse_line_get_next()
            if self.state.inline:
                indent = self.state.inline_indent
                len_indent = len(indent)
            elif self.state.at_line_start:
                indent = self.state.indent
                len_indent = len(indent)
            else:
                if line is not None and line.lstrip(self.whitespace_str):
                    indent = line[:len(self.state.indent)+1]
                    len_indent = len(indent)
                    if not indent.startswith(self.state.indent) or indent[-1] not in self.indents:
                        indent = None
                else:
                    indent = None
            if indent is None:
                next_line_action = self._parse_line_start_next
            else:
                while True:
                    if line is None or not line.lstrip(self.whitespace_str) or not line.startswith(indent):
                        next_line_action = self._parse_line_start_next
                        break
                    # Match with offset, to avoid matching indentation chars
                    m = self._unquoted_string_fragment_re.match(line, len_indent)
                    if not m:
                        next_line_action = self._parse_line_start_next
                        break
                    elif m.end() < len(line):
                        s_line = line[len_indent:m.end()]
                        if s_line.lstrip(self.whitespace_str):
                            s_list.append(s_line)
                            line = line[m.end():]
                            next_line_action = self._parse_line_continue_next
                        else:
                            next_line_action = self._parse_line_start_next
                        break
                    else:
                        s_list.append(line[len_indent:])
                        line = self._parse_line_get_next()
        # Leading whitespace will have already been stripped
        s_list[-1] = s_list[-1].rstrip(self.whitespace_str)
        for s_line in s_list:
            s_line_lstrip_uws = s_line.lstrip(self.unicode_whitespace_str)
            if not s_line_lstrip_uws:
                raise erring.ParseError('Unquoted strings cannot contain lines consisting solely of Unicode whitespace characters', self.state.traceback)
            if s_line_lstrip_uws[:1] in self.unicode_whitespace:
                raise erring.ParseError('Unquoted strings cannot contain lines beginning with Unicode whitespace characters', self.state.traceback)
        s = self._unwrap_inline(s_list)
        if s[0] in self.unicode_whitespace or s[-1] in self.unicode_whitespace:
            raise erring.ParseError('Unquoted strings cannot begin or end with Unicode whitespace characters')
        s = self._type_unquoted_string(s)

        self.state.set_stringlike(s)
        if next_line_action is None:
            self.state.at_line_start = False
        else:
            line = next_line_action(line)

        while line is not None:
            if line[:1] == '%':
                line = self._parse_line_percent(line)
            elif not line.lstrip(self.whitespace_str):
                line = self._parse_line_goto_next()
            else:
                break
        if line is not None and line[:1] == '=' and line[1:2] != '=':
            if self.state.inline and not self.state.indent.startswith(self.state.inline_indent):
                raise erring.ParseError('Indentation error', self.state.traceback)
            if not self.state.inline and self.state.stringlike_end_lineno != self.state.start_lineno:
                raise erring.ParseError('In a key-value pair in non-inline syntax, the equals sign "=" must follow the key on the same line', self.state.traceback)
            line = line[1:].lstrip(self.whitespace_str)
            self._ast.append_collection('kvpair')
            self._ast.append_stringlike()
        else:
            self._ast.append_stringlike()
        if line is not None and not line.lstrip(self.whitespace_str):
            line = self._parse_line_goto_next()
        return line

    def _type_unquoted_string(self, s):
        if self.state.type:
            if self.state.type in self._bytes_parsers:
                s = self._unicode_to_bytes(s)
            try:
                s_typed = self.string_parsers[self.state.type](s)
            except KeyError:
                raise erring.ParseError('Unknown explicit type "{0}" applied to unquoted string-like object', self.state.traceback_type)
            except Exception as e:
                raise erring.ParseError('Could not convert unquoted string to type "{0}":\n  {1}'.format(self.state.type, e), self.state.traceback)
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
