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
                 'stringlike', 'stringlike_val', 'stringlike_indent', 'stringlike_at_line_start', 'stringlike_start_lineno', 'stringlike_end_lineno',
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
        self.stringlike = True
        self.stringlike_val = s
        if self.start_lineno == self.stringlike_effective_start_lineno:
            self.stringlike_at_line_start = self.at_line_start
            self.stringlike_effective_at_line_start = self.at_line_start
        else:
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
                    # Also, indentation of explicit type would have already
                    # been checked in `set_type()`
                    self.stringlike_effective_at_line_start = False
                    self.stringlike_effective_indent = self.inline_indent
                else:
                    if self.stringlike_at_line_start:
                        if self.type_at_line_start:
                            if not self.stringlike_indent.startswith(self.type_indent):
                                raise erring.ParseError('Indentation error in string-like object', self.traceback_stringlike)
                        elif not (self.stringlike_indent.startswith(self.type_indent) and len(self.stringlike_indent) > len(self.type_indent)):
                            raise erring.ParseError('Indentation error in string-like object', self.traceback_stringlike)
                    elif self.stringlike_start_lineno != self.type_lineno:
                            raise erring.ParseError('Indeterminate indentation for string-like object', self.traceback_stringlike)
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
            if self.at_line_start:
                if not self.type_at_line_start:
                    if not self.indent.startswith(self.type_indent) or len(self.indent) <= len(self.type_indent):
                        raise erring.ParseError('Indentation error at start of explicitly typed inline collection object', self.traceback_stringlike)
                elif not self.indent.startswith(self.type_indent):
                    raise erring.ParseError('Indentation error at start of explicitly typed inline collection object', self.traceback_stringlike)
            else:
                if self.start_lineno != self.type.lineno:
                    raise erring.ParseError('Indeterminate indentation at start of explicitly typed inline collection object', self.state.traceback)
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
        return self.traceback_namedtuple(self.source, self.ast.pos.start_lineno, self.ast.pos.end_lineno)

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
    __slots__ = ['ast', 'cat', 'check_append_astobj', 'check_append_stringlike',
                 'end_lineno', 'indent', 'inline', 'index', 'open', 'parent',
                 'start_lineno', 'state', 'type']

    def __init__(self, cat, ast, indent):
        self.cat = cat
        self.ast = ast
        state = ast.state
        self.state = state
        if cat != 'root':
            self.inline = state.inline
            self.indent = indent
            self.type = None
            if state.type:
                self.start_lineno = state.type_start_lineno
                if not state.stringlike:
                    if not self.inline and (not state.type_at_line_start or self.start_lineno == state.start_lineno):
                        raise erring.ParseError('Explicit type declaration for {0}-like object must be on a line by itself in non-inline syntax'.format(cat), state.traceback_type)
                    if not state.type_cat != self.cat:
                        raise erring.ParseError('Invalid explicit type "{0}" applied to {1}-like collection object'.format(state.type, self.cat), state.traceback_type)
                    if indent != state.type_indent:
                        raise erring.ParseError('Indentation mismatch between explicit type declaration for collection object and object contents')
                    self.type = state.type
                    state.type = None
            elif state.stringlike:
                self.start_lineno = state.stringlike_start_lineno
            else:
                self.start_lineno = state.start_lineno
            self.end_lineno = self.start_lineno
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

        # Ordered by expected frequency
        if cat == 'kvpair':
            self.check_append_astobj = self._check_append_kvpair_astobj
            self.check_append_stringlike = self._check_append_kvpair_stringlike
        elif cat == 'dict':
            self.check_append_astobj = self._check_append_dict_astobj
            self.check_append_stringlike = self._check_append_dict_stringlike
        elif cat == 'list':
            self.check_append_astobj = self._check_append_list_astobj
            self.check_append_stringlike = self._check_append_list_stringlike
        elif cat == 'root':
            self.check_append_astobj = self._check_append_root_astobj
            self.check_append_stringlike = self._check_append_root_stringlike
        # Never instantiated with any contents
        list.__init__(self)

    def _check_append_root_astobj(self, val):
        if len(self) == 1:
            raise erring.ParseError('Only a single object is allowed at root level', self.state.traceback)
        self.append(val)
        self.start_lineno = val.start_lineno
        self.end_lineno = val.end_lineno
        self.ast.pos = self.ast.pos[-1]
        self.ast._obj_to_pythonize_list.append(val)

    def _check_append_root_stringlike(self):
        if len(self) == 1:
            raise erring.ParseError('Only a single object is allowed at root level', self.state.traceback)
        state = self.state
        self.append(state.stringlike_val)
        self.start_lineno = state.stringlike_effective_start_lineno
        self.end_lineno = state.stringlike_end_lineno
        state.type = None
        state.stringlike = False

    def _check_append_dict_astobj(self, val):
        if val.cat != 'kvpair':
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

    def _check_append_dict_stringlike(self):
        raise erring.ParseError('Cannot add a non key-value pair to a dict-like object', self.state.traceback)

    def _check_append_kvpair_astobj(self, val):
        if len(self) == 2:
            raise erring.ParseError('Key-value pair can only contain two elements', self.state.traceback)
        if not self:
            raise erring.ParseError('Keys for dict-like objects cannot be collection types', self.state.traceback)
        if self.inline:
            if val.indent != self.indent:
                raise erring.ParseError('Indentation error in dict-like object', self.state.traceback)
        else:
            if not (val.indent.startswith(self.indent) and
                    (len(val.indent) > len(self.indent) or (val.inline and val.start_lineno == self.end_lineno and len(val.indent) == len(self.indent)))):
                raise erring.ParseError('Indentation error in dict-like object', self.state.traceback)
        self.append(val)
        self.end_lineno = val.end_lineno
        self.ast.pos = self.ast.pos[-1]
        self.ast._obj_to_pythonize_list.append(val)

    def _check_append_kvpair_stringlike(self):
        state = self.state
        # No need to check indentation in general case, since kvpair is
        # only ever created by a string-like object
        if not self.inline and not state.stringlike_effective_at_line_start:
            raise erring.ParseError('Indeterminate indentation when attempting to add a key to a dict-like object', state.traceback)
        self.append(state.stringlike_val)
        self.end_lineno = state.stringlike_end_lineno
        state.type = None
        state.stringlike = False
        self.check_append_stringlike = self._check_append_kvpair_stringlike_len1

    def _check_append_kvpair_stringlike_len1(self):
        state = self.state
        if self.end_lineno != state.stringlike_effective_start_lineno:
            if self.inline:
                if state.stringlike_effective_indent != self.indent:
                    raise erring.ParseError('Indentation error in dict-like object', state.traceback)
            else:
                if state.stringlike_effective_at_line_start:
                    if len(state.stringlike_effective_indent) <= len(self.indent) or not state.stringlike_effective_indent.startswith(self.indent):
                        raise erring.ParseError('Indentation error in dict-like object', state.traceback)
                else:
                    if state.stringlike_effective_start_lineno != self.end_lineno:
                        raise erring.ParseError('Indeterminate indentation when attempting to add a value to a dict-like object', state.traceback)
                    if len(state.stringlike_effective_indent) < len(self.indent) or not state.stringlike_effective_indent.startswith(self.indent):
                        raise erring.ParseError('Indentation error in dict-like object', state.traceback)
        self.append(state.stringlike_val)
        self.end_lineno = state.stringlike_end_lineno
        state.type = None
        state.stringlike = False
        self.ast.pos = self.ast.pos.parent
        self.check_append_stringlike = self._check_append_kvpair_stringlike_len2

    def _check_append_kvpair_stringlike_len2(self):
        raise erring.ParseError('Key-value pair can only contain two elements', self.state.traceback)

    def _check_append_list_astobj(self, val):
        if not self.open:
            raise erring.ParseError('Cannot append to a list-like object when the current location has already been filled', self.state.traceback)
        if self.inline:
            if val.indent != self.indent:
                raise erring.ParseError('Indentation error in list-like object', self.state.traceback)
        else:
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
        self.open = False

    def _check_append_list_stringlike(self):
        if not self.open:
            raise erring.ParseError('Cannot append to a list-like object when the current location has already been filled', self.state.traceback)
        state = self.state
        if self.inline:
            if state.stringlike_effective_indent != self.indent:
                raise erring.ParseError('Indentation error in list-like object', state.traceback)
        elif not (self.end_lineno == state.stringlike_effective_start_lineno and state.stringlike_effective_at_line_start):
            if not state.stringlike_effective_at_line_start:
                raise erring.ParseError('Indeterminate indentation when appending to list-like object', state.traceback)
            if self.indent[-1:] == '\t' and state.stringlike_effective_indent[len(self.indent):len(self.indent)+1] == '\t':
                if not (len(state.stringlike_effective_indent) >= len(self.indent) + 1 and state.stringlike_effective_indent.startswith(self.indent)):
                    raise erring.ParseError('Indentation error in list-like object', state.traceback)
            else:
                if not (len(state.stringlike_effective_indent) >= len(self.indent) + 2 and state.stringlike_effective_indent.startswith(self.indent)):
                    raise erring.ParseError('Indentation error in list-like object', state.traceback)
        self.append(state.stringlike_val)
        self.end_lineno = state.stringlike_end_lineno
        state.type = None
        state.stringlike = False
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
    __slots__ = ['decoder', 'pos', '_obj_to_pythonize_list', 'root', 'state', ]
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

    def append_collection(self, cat, indent):
        state = self.state
        # Temp variables must be used with care; otherwise, mess up tracebacks
        pos = self.pos
        root = self.root
        if pos is not root and len(indent) < len(pos.indent):
            while pos is not root and len(indent) < len(pos.indent):
                if pos.cat == 'kvpair':
                    if len(pos) < 2:
                        self.pos = pos
                        raise erring.ParseError('A key-value pair was truncated before being completed', state.traceback_ast_pos)
                elif pos.cat == 'dict':
                    if not pos and not pos.inline:
                        self.pos = pos
                        raise erring.ParseError('A non-inline dict cannot be empty', state.traceback_ast_pos)
                elif pos.cat == 'list':
                    if not pos.inline:
                        if pos.open:
                            self.pos = pos
                            raise erring.ParseError('A list-like object was truncated before an expected element was added', state.traceback_ast_pos)
                        if not pos:
                            self.pos = pos
                            raise erring.ParseError('A non-inline list cannot be empty', state.traceback_ast_pos)
                pos.parent.end_lineno = pos.end_lineno
                pos = pos.parent
                if pos.cat == 'kvpair':
                    if len(pos) < 2:
                        self.pos = pos
                        raise erring.ParseError('A key-value pair was truncated before being completed', state.traceback_ast_pos)
                    pos.parent.end_lineno = pos.end_lineno
                    pos = pos.parent
            self.pos = pos
        # Stop using temp var before doing anything that might change Ast
        if not state.inline and cat == 'kvpair' and pos.cat != 'dict':
            self.pos.check_append_astobj(AstObj('dict', self, indent))
        self.pos.check_append_astobj(AstObj(cat, self, indent))

    def append_stringlike(self):
        self.pos.check_append_stringlike()

    def open_collection_inline(self):
        if not (self.state.inline and self.pos.cat in ('dict', 'list')):
            raise erring.ParseError('Invalid object termination (semicolon)', self.state.traceback)
        if self.pos.open:
            raise erring.ParseError('Encountered ";" when there is no object to end', self.state.traceback)
        self.pos.open = True

    def open_list_non_inline(self):
        state = self.state
        if state.inline or not state.at_line_start:
            raise erring.ParseError('Invalid location to begin a non-inline list element')
        # Temp variables must be used with care; otherwise, mess up tracebacks
        pos = self.pos
        root = self.root
        if pos is not root and len(state.indent) < len(pos.indent):
            while pos is not root and len(state.indent) < len(pos.indent):
                if pos.cat == 'kvpair':
                    if len(pos) < 2:
                        self.pos = pos
                        raise erring.ParseError('A key-value pair was truncated before being completed', state.traceback_ast_pos)
                elif pos.cat == 'dict':
                    if not pos and not pos.inline:
                        self.pos = pos
                        raise erring.ParseError('A non-inline dict cannot be empty', state.traceback_ast_pos)
                elif pos.cat == 'list':
                    if not pos.inline:
                        if pos.open:
                            self.pos = pos
                            raise erring.ParseError('A list-like object was truncated before an expected element was added', state.traceback_ast_pos)
                        if not pos:
                            self.pos = pos
                            raise erring.ParseError('A non-inline list cannot be empty', state.traceback_ast_pos)
                pos.parent.end_lineno = pos.end_lineno
                pos = pos.parent
                if pos.cat == 'kvpair':
                    if len(pos) < 2:
                        self.pos = pos
                        raise erring.ParseError('A key-value pair was truncated before being completed', state.traceback_ast_pos)
                    pos.parent.end_lineno = pos.end_lineno
                    pos = pos.parent
            self.pos = pos
        if pos.cat != 'list' or len(pos.indent) < len(state.indent):
            # No need to check indentation in the event of an explicit type
            # declaraction; that's built into `AstObj`
            self.append_collection('list', state.indent)
        self.pos.open = True

    def end_dict_inline(self):
        state = self.state
        if not state.inline:
            raise erring.ParseError('Cannot end an inline dict-like object with "}" when not in inline mode', state.traceback)
        if not self.pos.cat == 'dict':
            raise erring.ParseError('Encountered "}" when there is no dict-like object to end', state.traceback)
        if not state.indent.startswith(state.inline_indent):
            raise erring.ParseError('Indentation error', state.traceback)
        self.pos = self.pos.parent
        state.inline = self.pos.inline
        if self.pos.cat == 'kvpair' and len(self.pos) == 2:
            self.pos = self.pos.parent
            state.inline = self.pos.inline

    def end_list_inline(self):
        state = self.state
        if not state.inline:
            raise erring.ParseError('Cannot end an inline list-like object with "]" when not in inline mode', state.traceback)
        if not self.pos.cat == 'list':
            raise erring.ParseError('Encountered "]" when there is no list-like object to end', self.state.traceback)
        if not state.indent.startswith(state.inline_indent):
            raise erring.ParseError('Indentation error', state.traceback)
        self.pos = self.pos.parent
        state.inline = self.pos.inline
        if self.pos.cat == 'kvpair' and len(self.pos) == 2:
            self.pos = self.pos.parent
            state.inline = self.pos.inline


    def finalize(self):
        if self.pos is not self.root:
            state = self.state
            if state.inline:
                raise erring.ParseError('Inline syntax was never closed', state.traceback_start_inline_to_end)
            if state.type:
                raise erring.ParseError('Explicit type definition was never used', state.traceback_type)
            if state.stringlike:
                raise erring.ParseError('String-like object was never used', state.traceback_stringlike)
            # Temp variables must be used with care; otherwise, mess up tracebacks
            pos = self.pos
            root = self.root
            if pos is not root:
                while pos is not root:
                    if pos.cat == 'kvpair':
                        if len(pos) < 2:
                            self.pos = pos
                            raise erring.ParseError('A key-value pair was truncated before being completed', state.traceback_ast_pos)
                    elif pos.cat == 'dict':
                        if not pos and not pos.inline:
                            self.pos = pos
                            raise erring.ParseError('A non-inline dict cannot be empty', state.traceback_ast_pos)
                    elif pos.cat == 'list':
                        if not pos.inline:
                            if pos.open:
                                self.pos = pos
                                raise erring.ParseError('A list-like object was truncated before an expected element was added', state.traceback_ast_pos)
                            if not pos:
                                self.pos = pos
                                raise erring.ParseError('A non-inline list cannot be empty', state.traceback_ast_pos)
                    pos.parent.end_lineno = pos.end_lineno
                    pos = pos.parent
                self.pos = pos

    def pythonize(self):
        parsers = self.decoder.parsers
        for obj in reversed(self._obj_to_pythonize_list):
            py_obj = parsers[obj.cat][obj.type](obj)
            obj.parent[obj.index] = py_obj




class BespONDecoder(object):
    '''
    Decode BespON.

    Works with Unicode strings or iterables containing Unicode strings.
    '''
    """
        __slots__ = ['state',
    '_debug_raw_ast',
    'default_dict_parsers',
    'default_list_parsers',
    'default_string_parsers',
    'default_reserved_words',
    'default_aliases',
    'dict_parsers',
    'list_parsers',
    'string_parsers',
    '_bytes_parsers',
    'parsers',
    'reserved_words',
    'aliases',
    'parser_cats',
    'dict_parsers',
    'list_parsers',
    'string_parsers',
    'unicodefilter',
    'newlines',
    'newline_chars',
    'newline_chars_str',
    'spaces',
    'spaces_str',
    'indents',
    'indents_str',
    'whitespace',
    'whitespace_str',
    'unicode_whitespace',
    'unicode_whitespace_str',
    'not_unquoted_str',
    'not_unquoted',
    '_not_unquoted_re',
    '_parse_line',
    '_explicit_type_re',
    '_opening_delim_percent_re',
    '_opening_delim_single_quote_re',
    '_opening_delim_double_quote_re',
    '_opening_delim_equals_re',
    '_opening_delim_pipe_re',
    '_opening_delim_plus_re',
    '_closing_delim_re_dict',
    '_numeric_type_starting_chars',
    '_int_re',
    '_float_re',
    '_unquoted_key_re',
    '_keypath_element_re',
    '_keypath_re',
    '_unquoted_string_fragment_re',
    '_line_iter', '_ast']
    """
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
        self._not_unquoted_re = re.compile('|'.join(re.escape(c) for c in self.not_unquoted))

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

        # Quick identification of strings for int/float checking
        self._numeric_type_starting_chars = set('+-.0123456789')

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
        self._line_iter = iter(s.splitlines(True))
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

        _parse_line = self._parse_line
        while line is not None:
            line = _parse_line[line[:1]](line)

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


    def _parse_line_get_next(self, line=None):
        '''
        Get next line.  For use in lookahead in string scanning, etc.
        '''
        line = next(self._line_iter, None)
        self.state.end_lineno += 1
        return line


    def _parse_line_start_next(self, line=None):
        '''
        Reset everything after `_parse_line_get_next()`, so that it's
        equivalent to using `_parse_line_goto_next()`.  Useful when
        `_parse_line_get_next()` is used for lookahead, but nothing is consumed.
        '''
        if line is not None:
            state = self.state
            rest = line.lstrip(self.whitespace_str)
            state.indent = line[:len(line)-len(rest)]
            state.at_line_start = True
            state.start_lineno = state.end_lineno
            return rest
        return line


    def _parse_line_continue_next(self, line=None):
        '''
        Reset everything after `_parse_line_get_next()`, to continue on with
        the next line after having consumed part of it.
        '''
        state = self.state
        state.at_line_start = False
        state.start_lineno = state.end_lineno
        return line


    def _parse_line_goto_next(self, line=None):
        '''
        Go to next line, after current parsing is complete.
        '''
        line = next(self._line_iter, None)
        if line is not None:
            state = self.state
            rest = line.lstrip(self.whitespace_str)
            state.indent = line[:len(line)-len(rest)]
            state.at_line_start = True
            state.end_lineno += 1
            state.start_lineno = state.end_lineno
            return rest
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
            state = self.state
            ######## Maybe move logic to Ast?
            if state.inline and not state.indent.startswith(state.inline_indent):
                raise erring.ParseError('Indentation error', state.traceback)
            elif not state.inline:
                state.start_inline()
            self._ast.append_collection('list', state.inline_indent)
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
            state = self.state
            if state.inline and not state.indent.startswith(state.inline_indent):
                raise erring.ParseError('Indentation error', state.traceback)
            elif not state.inline:
                state.start_inline()
            self._ast.append_collection('dict', state.inline_indent)
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
        len_delim = len(line)
        line = line.lstrip("'")
        len_delim -= len(line)
        delim = "'"*len_delim
        if delim in line:
            s, line = line.split("'", 1)
            if len(delim) > 2:
                if line[:1] == '/':
                    raise erring.ParseError('A block string may not begin and end on the same line', self.state.traceback)
                if s[:1] in self.spaces and s.lstrip(self.spaces_str) == "'":
                    s = s[1:]
                if s[-1:] in self.spaces and s.rstrip(self.spaces_str) == "'":
                    s = s[:-1]
        elif len(delim) == 2:
            s = ''
        else:
            end_delim_re = self._closing_delim_re_dict[delim]
            match_group_num = 0
            s, line = self._parse_line_get_quoted_string(line, delim, end_delim_re, match_group_num)
        return self._parse_line_resolve_quoted_string(line, s, delim)

    def _parse_line_double_quote(self, line):
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
            if not line.startswith(indent) and line.lstrip(self.whitespace_str):
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
                    line = line[m.end(match_group_num):].lstrip(self.whitespace_str)
                    break
        if len(delim) == len(end_delim):
            # Make sure indentation is consistent and there are no empty lines
            if len(s_lines) > 2:
                for s_line in s_lines[1:-1]:
                    if not s_line.lstrip(self.unicode_whitespace_str):
                        raise erring.ParseError('Inline strings cannot contain empty lines', state.traceback)
                indent = s_lines[1][:len(s_lines[1].lstrip(self.indents_str))]
                len_indent = len(indent)
                for n, s_line in enumerate(s_lines[1:]):
                    if not s_line.startswith(indent) or s_line[len_indent:len_indent+1] in self.unicode_whitespace:
                        raise erring.ParseError('Inconsistent indentation or leading Unicode whitespace within inline string', state.traceback)
                    s_lines[n+1] = s_line[len_indent:]
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
                raise erring.ParseError('Invalid ending delimiter for block string', state.traceback)
            if s_lines[0].lstrip(self.whitespace_str):
                raise erring.ParseError('Characters are not allowed immediately after the opening delimiter of a block string', state.traceback)
            if s_lines[-1].lstrip(self.indents_str):
                raise erring.ParseError('Characters are not allowed immediately before the closing delimiter of a block string', state.traceback)
            indent = s_lines[-1]
            len_indent = len(indent)
            if state.at_line_start and state.indent != indent:
                raise erring.ParseError('Opening and closing delimiters for block string do not have matching indentation', state.traceback)
            for n, s_line in enumerate(s_lines[1:-1]):
                if s_line.startswith(indent):
                    s_lines[n+1] = s_line[len_indent:]
                else:
                    if s_line.lstrip(self.whitespace_str):
                        raise erring.ParseError('Inconsistent indent in block string', state.traceback)
                    s_lines[n+1] = line.lstrip(self.indents_str)
            if len(delim) == len(end_delim) - 2:
                s_lines[-2] = s_lines[-2].rstrip(self.newline_chars_str)
            s = ''.join(s_lines[1:-1])
        return (s, line)


    def _parse_line_resolve_quoted_string(self, line, s, delim):
        state = self.state
        if state.type and state.type in self._bytes_parsers:
            s = self.unicodefilter.unicode_to_ascii_newlines(s)
            s = self._unicode_to_bytes(s)
            if delim[0] == '"':
                s = self.unicodefilter.unescape_bytes(s)
        elif delim[0] == '"':
            s = self.unicodefilter.unescape(s)

        if state.type:
            try:
                s = self.string_parsers[self.state.type](s)
            except KeyError:
                raise erring.ParseError('Unknown explicit type "{0}" applied to string'.format(self.state.type), self.state.traceback_type)
            except Exception as e:
                raise erring.ParseError('Could not convert quoted string to type "{0}":\n  {1}'.format(self.state.type, e), self.state.traceback)

        state.set_stringlike(s)
        if state.start_lineno == state.end_lineno:
            state.at_line_start = False
        else:
            self._parse_line_continue_next()

        line = line.lstrip(self.whitespace_str)
        if not line or line[:1] == '%':
            while line is not None:
                if line[:1] == '%':
                    line = self._parse_line_percent(line)
                else:
                    line = line.lstrip(self.whitespace_str)
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
            line = line[1:].lstrip(self.whitespace_str)
            self._ast.append_collection('kvpair', state.stringlike_effective_indent)
            self._ast.append_stringlike()
        else:
            self._ast.append_stringlike()
        return line


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
        state = self.state
        check_kv = True
        m = self._not_unquoted_re.search(line)
        if m:
            s = line[:m.start()].rstrip(self.whitespace_str)
            line = line[m.start():]
            state.set_stringlike(s)
            state.at_line_start = False
        else:
            s = line.rstrip(self.whitespace_str)
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
                    m = self._not_unquoted_re.search(line)
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
                s_list[-1] = s_list[-1].rstrip(self.whitespace_str)
                for s_line in s_list:
                    if s_line[:1] in self.unicode_whitespace:
                        raise erring.ParseError('Unquoted strings cannot contain lines beginning with Unicode whitespace characters', state.traceback)
                s = self._unwrap_inline(s_list)
                state.stringlike_val = s

        # If typed string, update `stringlike_val`
        # Could use `set_stringlike` after this, but the current approach
        # is more efficient for multi-line unquoted strings
        if state.type:
            if state.type in self._bytes_parsers:
                s_bytes = self._unicode_to_bytes(s)
            try:
                state.stringlike_val = self.string_parsers[state.type](s_bytes)
            except KeyError:
                raise erring.ParseError('Unknown explicit type "{0}" applied to unquoted string-like object', state.traceback_type)
            except Exception as e:
                raise erring.ParseError('Could not convert unquoted string to type "{0}":\n  {1}'.format(state.type, e), state.traceback)
        elif s in self.reserved_words:
            state.stringlike_val = self.reserved_words[s]
        elif s[0] in self._numeric_type_starting_chars:
            m_int = self._int_re.match(s)
            if m_int:
                state.stringlike_val = int(s.replace('_', ''))
            else:
                m_float = self._float_re.match(s)
                if m_float:
                    state.stringlike_val = float(s.replace('_', ''))
        elif s[0] in self.unicode_whitespace or s[-1] in self.unicode_whitespace:
            raise erring.ParseError('Unquoted strings cannot begin or end with Unicode whitespace characters', state.traceback)

        if not check_kv:
            self._ast.append_stringlike()
        else:
            if not line or line[:1] == '%':
                while line is not None:
                    if line[:1] == '%':
                        line = self._parse_line_percent(line)
                    else:
                        line = line.lstrip(self.whitespace_str)
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
                line = line[1:].lstrip(self.whitespace_str)
                self._ast.append_collection('kvpair', state.stringlike_effective_indent)
                self._ast.append_stringlike()
            else:
                self._ast.append_stringlike()
        return line


_default_decoder = BespONDecoder()
