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
from . import defaults
import collections
import re




class State(object):
    '''
    Keep track of state:  the name of a source (file name, or <string>), the
    current location within the source (range of lines currently being parsed,
    plus indentation and whether at beginning of line), whether syntax is
    inline, explicit typing to be applied to the next object, the next
    string-like object, etc.  Several properties are available for providing
    tracebacks in the event of errors.

    The state serves as a one-element stack for explicit typing and for
    string-like objects.  This allows type information to be held until it is
    needed, and allows lookahead after string-like objects so that it may be
    determined whether they are dict keys.
    '''
    # Use __slots__ to optimize attribute access
    __slots__ = ['ast', 'decoder', 'source',
                 'indent', 'at_line_start', 'start_lineno', 'end_lineno',
                 'inline', 'inline_indent',
                 'type', 'type_obj', 'type_indent', 'type_at_line_start', 'type_start_lineno', 'type_end_lineno', 'type_cat',
                 'stringlike', 'stringlike_obj', 'stringlike_indent', 'stringlike_at_line_start', 'stringlike_start_lineno', 'stringlike_end_lineno',
                 'stringlike_effective_indent', 'stringlike_effective_at_line_start', 'stringlike_effective_start_lineno']

    def __init__(self, source=None,
                 indent=None, at_line_start=None, start_lineno=0, end_lineno=0,
                 inline=False, inline_indent=None):
        # These are set later, since they don't typically exist when a
        # `State()` is created
        self.ast = None
        self.decoder = None

        # Current state information
        self.source = source or '<string>'
        self.indent = indent
        self.at_line_start = at_line_start
        self.start_lineno = start_lineno
        self.end_lineno = end_lineno
        self.inline = inline
        self.inline_indent = inline_indent

        # Information for last explicit type declaration
        self.type = False
        self.type_obj = None
        self.type_indent = None
        self.type_at_line_start = None
        self.type_start_lineno = 0
        self.type_end_lineno = 0
        self.type_cat = None

        # Information for last string-like object
        self.stringlike = False
        self.stringlike_obj = None
        self.stringlike_indent = None
        self.stringlike_at_line_start = None
        self.stringlike_start_lineno = 0
        self.stringlike_end_lineno = 0
        # Information for resolving string-like object that accounts for the
        # possibility of explicit type declaration, which might be on an
        # earlier line
        self.stringlike_effective_indent = None
        self.stringlike_effective_at_line_start = None
        self.stringlike_effective_start_lineno = 0

    def register(self, ast=None, decoder=None):
        '''
        Set `ast` and `decoder`.

        This isn't done in `__init__()` because `ast` and `state` have a
        circular dependency.  The solution is to create `state` first, then
        create `ast` and allow it to register itself and its `decoder`.
        '''
        self.ast = ast
        self.decoder = decoder

    traceback_namedtuple = collections.namedtuple('traceback_namedtuple', ['source', 'start_lineno', 'end_lineno'])

    def set_type(self, kvarg_list):
        '''
        Store explicit type definition and relevant current state for later use.

        Indentation is checked when used, rather than when stored.
        '''
        if self.type:
            if self.inline:
                raise erring.ParseError('Encountered explicit type declaration before a previous declaration was resolved', self.traceback_type)
            if self.type_cat == 'string':
                raise erring.ParseError('Explicit type declaration "{0}" for string-like object was never used'.format(self.type_obj), self.traceback_type)
            # Use current indentation, in case collection contents are indented
            # relative to type declaration.  If indentations aren't compatible,
            # it will be caught in the creation of the `*AstObj`.
            self.ast.append_collection(self.type_cat, self.indent)
        if not kvarg_list:
            raise erring.ParseError('Encountered empty explicit type declaration', self.state.traceback)
        t, v = kvarg_list[0]
        if t in self.decoder._parser_cats and v is True and len(kvarg_list) == 1:
            self.type_obj = t
            self.type_indent = self.indent
            self.type_at_line_start = self.at_line_start
            self.at_line_start = False
            self.type_start_lineno = self.start_lineno
            self.type_end_lineno = self.end_lineno
            self.type_cat = self.decoder._parser_cats[t]
            self.type = True
        elif t == self.decoder.dialect and v is True:
            if self.decoder._ast:
                raise erring.ParseError('Parser directives can only be used before the beginning of data', self.traceback)
            if len(kvarg_list) > 1:
                d = dict(kvarg_list[1:])
                if len(d) < len(kvarg_list[1:]):
                    raise erring.ParseError('Explicit type declaration contains duplicate keys', self.traceback)
                self.decoder._parser_directives(d)
        else:
            raise erring.ParseError('Could not parse explicit type declaration; invalid or unsupported settings', self.traceback)


    def set_stringlike(self, s):
        '''
        Store string-like object and relevant current state so that lookahead
        is possible to determine whether the object is a dict key.

        The `effective*` attributes are used in determining whether the object
        may be inserted into the AST without errors.  They take into account
        the possibility that the string-like object might have an explicit type
        declaration on a previous line with less indentation.
        '''
        if self.stringlike:
            # This shouldn't ever happen, since stringlike objects are resolved
            # immediately, rather than being stored for future use like
            # explicit type declarations
            raise erring.ParseError('A string-like object was not resolved before the next string-like object', self.traceback_stringlike)
        if self.start_lineno == self.stringlike_effective_start_lineno:
            # If another, complete string-like object has already occurred on
            # the current line, then only a few settings need to be updated.
            # Don't need to check for an intervening explicit type declaration
            # for a collection object, since it wouldn't be valid in non-inline
            # syntax and should have been resolved in inline syntax; in either
            # case, an unused non-string explicit type declaration will trigger
            # an error when applied to a string-like object.
            self.stringlike_at_line_start = False
            self.stringlike_effective_at_line_start = False
            self.stringlike_end_lineno = self.end_lineno
        elif not self.type:
            self.stringlike_indent = self.indent
            self.stringlike_at_line_start = self.stringlike_effective_at_line_start = self.at_line_start
            self.stringlike_start_lineno = self.stringlike_effective_start_lineno = self.start_lineno
            self.stringlike_end_lineno = self.end_lineno
            if self.inline:
                if not self.stringlike_indent.startswith(self.inline_indent):
                    raise erring.ParseError('Indentation error in string-like object', self.traceback_stringlike)
                self.stringlike_effective_indent = self.inline_indent
            else:
                self.stringlike_effective_indent = self.stringlike_indent
        elif self.type_cat != 'string':
            if self.inline:
                raise erring.ParseError('Explicit type declaration for collection type "{0}" was never used'.format(self.type), self.traceback_type)
            # Don't need to check that current indentation is compatible with
            # `type_indent`, since that's checked in `DictlikeAstObj`.  Use
            # the current indentation, rather than `type_indent`, in case the
            # content is indented relative to the type declaration.
            self.ast.append_collection(self.type_cat, self.indent)
            self.stringlike_indent = self.indent
            self.stringlike_at_line_start = self.stringlike_effective_at_line_start = self.at_line_start
            self.stringlike_start_lineno = self.stringlike_effective_start_lineno = self.start_lineno
            self.stringlike_end_lineno = self.end_lineno
            self.stringlike_effective_indent = self.stringlike_indent
        else:
            self.stringlike_indent = self.indent
            self.stringlike_at_line_start = self.at_line_start
            self.stringlike_start_lineno = self.start_lineno
            self.stringlike_end_lineno = self.end_lineno
            self.stringlike_effective_start_lineno = self.type_start_lineno
            if self.inline:
                if not self.type_indent.startswith(self.inline_indent):
                    raise erring.ParseError('Indentation error in explicit type declaration for string-like object', self.traceback_type)
                if not self.stringlike_indent.startswith(self.inline_indent):
                    raise erring.ParseError('Indentation error in string-like object', self.traceback_stringlike)
                self.stringlike_effective_at_line_start = False
                self.stringlike_effective_indent = self.inline_indent
            else:
                if self.stringlike_at_line_start:
                    if self.type_at_line_start:
                        if not self.stringlike_indent.startswith(self.type_indent):
                            raise erring.ParseError('Indentation error in string-like object', self.traceback_stringlike)
                    elif len(self.stringlike_indent) <= len(self.type_indent) or not self.stringlike_indent.startswith(self.type_indent):
                        raise erring.ParseError('Indentation error in string-like object', self.traceback_stringlike)
                self.stringlike_effective_at_line_start = self.type_at_line_start
                self.stringlike_effective_indent = self.type_indent
        # Actually set things last, so that it's possible to do a correct
        # boolean check on `stringlike` during the process if that is ever
        # desirable (for example, in `ast.append_collection()`)
        self.stringlike = True
        self.stringlike_obj = s

    def start_inline(self):
        '''
        Transition to inline syntax.
        '''
        if self.type:
            if self.at_line_start:
                if self.type_at_line_start:
                    if not self.indent.startswith(self.type_indent):
                        raise erring.ParseError('Indentation error at transition to inline syntax', self.traceback)
                elif len(self.indent) <= len(self.type_indent) or not self.indent.startswith(self.type_indent):
                    raise erring.ParseError('Indentation error at transition to inline syntax', self.traceback)
                self.inline_indent = self.indent
            else:
                self.inline_indent = self.type_indent
        else:
            self.inline_indent = self.indent
        self.inline = True

    @property
    def traceback(self):
        '''
        Traceback from the earliest stored position to the end.
        '''
        if self.type:
            return self.traceback_namedtuple(self.source, self.type_start_lineno, self.end_lineno)
        else:
            if self.stringlike:
                return self.traceback_namedtuple(self.source, self.stringlike_start_lineno, self.end_lineno)
            else:
                return self.traceback_namedtuple(self.source, self.start_lineno, self.end_lineno)

    @property
    def traceback_current_start(self):
        '''
        Traceback to the start of the region currently being parsed.
        '''
        if self.type:
            return self.traceback_namedtuple(self.source, self.type_start_lineno, self.type_start_lineno)
        else:
            if self.stringlike:
                return self.traceback_namedtuple(self.source, self.stringlike_start_lineno, self.stringlike_start_lineno)
            else:
                return self.traceback_namedtuple(self.source, self.start_lineno, self.start_lineno)

    @property
    def traceback_type(self):
        '''
        Traceback to explicit type declaration.
        '''
        return self.traceback_namedtuple(self.source, self.type_start_lineno, self.type_end_lineno)

    @property
    def traceback_stringlike(self):
        '''
        Traceback to string-like object.
        '''
        return self.traceback_namedtuple(self.source, self.stringlike_start_lineno, self.stringlike_end_lineno)

    @property
    def traceback_start_inline_to_end(self):
        '''
        Traceback from beginning of current inline syntax to the end
        (that is, to current parsing location).
        '''
        p = self.ast.pos
        while p.parent.inline:
            p = p.parent
        return self.traceback_namedtuple(self.source, p.start_lineno, self.end_lineno)

    @property
    def traceback_ast_pos(self):
        '''
        Traceback to a particular position in the AST.
        '''
        return self.traceback_namedtuple(self.source, self.ast.pos.start_lineno, self.ast.pos.end_lineno)

    @property
    def traceback_ast_pos_end_to_end(self):
        '''
        Traceback from the end of a particular position in the AST to the end
        (that is, to current parsing location).
        '''
        return self.traceback_namedtuple(self.source, self.ast.pos.end_lineno, self.state.end_lineno)




class RootAstObj(list):
    '''
    Abstract representation of AST root.

    The AST root is represented as a list that may only contain a single
    element.  String-like objects appear in the AST as themselves.  List-like
    objects are represented as lists.  Dict-like objects are represented as
    ordered dicts.
    '''
    __slots__ = ['ast', 'cat', 'end_lineno', 'indent', 'inline', 'index',
                 'jump', 'open', 'parent', 'start_lineno', 'state', 'type']

    def __init__(self, ast):
        self.cat = 'root'  # Collection type category
        self.ast = ast
        self.state = ast.state
        self.type = 'root'
        self.indent = None
        self.inline = None
        self.start_lineno = None
        self.end_lineno = None
        self.parent = None
        self.jump = None
        self.index = None
        self.open = None
        # Never instantiated with any contents
        list.__init__(self)

    def check_append_astobj(self, val):
        if len(self) == 1:
            raise erring.ParseError('Only a single object is allowed at root level', self.state.traceback)
        self.append(val)
        self.start_lineno = val.start_lineno
        self.end_lineno = val.end_lineno
        self.ast.pos = val
        self.ast.astobj_to_pythonize_list.append(val)

    def check_append_stringlike(self):
        if len(self) == 1:
            raise erring.ParseError('Only a single object is allowed at root level', self.state.traceback_stringlike)
        state = self.state
        self.append(state.stringlike_obj)
        self.start_lineno = state.stringlike_effective_start_lineno
        self.end_lineno = state.stringlike_end_lineno
        state.type = False
        state.stringlike = False

    def check_append_stringlike_key(self):
        raise erring.ParseError('Cannot append a key-value pair directly to AST root node', self.state.traceback_stringlike)




class ListlikeAstObj(list):
    '''
    Abstract representation of list-like collection types in AST.
    '''
    __slots__ = ['ast', 'cat', 'check_append_astobj', 'check_append_stringlike',
                 'end_lineno', 'indent', 'inline', 'index', 'jump',
                 'len_indent', 'len_indent_plus1', 'len_indent_plus2',
                 'open', 'parent', 'start_lineno', 'state', 'type']

    def __init__(self, ast, indent, jump=None):
        self.cat = 'list'  # Collection type category
        self.ast = ast
        state = ast.state
        self.state = state
        self.inline = state.inline
        self.indent = indent
        self.type = None
        if state.type and not state.stringlike:
            if state.type_cat != 'list':
                raise erring.ParseError('Invalid explicit type "{0}" applied to list-like object'.format(state.type_obj), state.traceback_type)
            if self.inline:
                # Indentations won't necessarily be equal, because `type_indent`
                # is actual indentation of type declaration, not normalized
                # indentation
                if not state.type_indent.startswith(state.inline_indent):
                    raise erring.ParseError('Indentation error in explicit type declaration for inline list-like object', state.traceback_type)
            else:
                if not state.type_at_line_start or state.type_end_lineno == state.start_lineno:
                    raise erring.ParseError('Explicit type declaration for list-like object must be on a line by itself in non-inline syntax', state.traceback_type)
                if not indent.startswith(state.type_indent):
                    # A list with an explicit type declaration may indented
                    # under the declaration.
                    raise erring.ParseError('Indentation mismatch between explicit type declaration for list-like object and object contents', state.traceback_type)
            self.start_lineno = state.type_start_lineno
            self.type = state.type_obj
            state.type = False
        elif state.stringlike:
            self.start_lineno = state.stringlike_effective_start_lineno
        else:
            self.start_lineno = state.start_lineno
        self.end_lineno = self.start_lineno
        self.open = False
        self.parent = ast.pos
        self.jump = jump
        self.index = ast.pos.next_key if ast.pos.cat == 'dict' else len(ast.pos)
        if self.inline:
            self.check_append_astobj = self._check_append_astobj_inline
            self.check_append_stringlike = self._check_append_stringlike_inline
        elif self.indent[-1:] == '\t':
            self.check_append_astobj = self._check_append_astobj_noninline_tab
            self.check_append_stringlike = self._check_append_stringlike_noninline_tab
            self.len_indent = len(self.indent)
            self.len_indent_plus1 = self.len_indent + 1
            self.len_indent_plus2 = self.len_indent + 2
        else:
            self.check_append_astobj = self._check_append_astobj_noninline
            self.check_append_stringlike = self._check_append_stringlike_noninline
            self.len_indent = len(self.indent)
            self.len_indent_plus1 = self.len_indent + 1
            self.len_indent_plus2 = self.len_indent + 2
        list.__init__(self)

    def _check_append_astobj_inline(self, val):
        if not self.open:
            raise erring.ParseError('Attempted to append to a list-like object that was not open for appending', self.state.traceback)
        if val.indent != self.indent:
            raise erring.ParseError('Indentation error in list-like object', self.state.traceback)
        self.append(val)
        self.end_lineno = val.end_lineno
        self.ast.pos = val
        self.ast.astobj_to_pythonize_list.append(val)
        self.open = False

    def _check_append_astobj_noninline_tab(self, val):
        if not self.open:
            raise erring.ParseError('Attempted to append to a list-like object that was not open for appending', self.state.traceback)
        if val.indent[self.len_indent:self.len_indent_plus1] == '\t':
            if len(val.indent) < self.len_indent_plus1 or not val.indent.startswith(self.indent):
                raise erring.ParseError('Indentation error in list-like object', self.state.traceback)
        elif len(val.indent) < self.len_indent_plus2 or not val.indent.startswith(self.indent):
            raise erring.ParseError('Indentation error in list-like object', self.state.traceback)
        self.append(val)
        self.end_lineno = val.end_lineno
        self.ast.pos = val
        self.ast.astobj_to_pythonize_list.append(val)
        self.open = False

    def _check_append_astobj_noninline(self, val):
        if not self.open:
            raise erring.ParseError('Attempted to append to a list-like object that was not open for appending', self.state.traceback)
        if len(val.indent) < self.len_indent_plus2 or not val.indent.startswith(self.indent):
            raise erring.ParseError('Indentation error in list-like object', self.state.traceback)
        self.append(val)
        self.end_lineno = val.end_lineno
        self.ast.pos = val
        self.ast.astobj_to_pythonize_list.append(val)
        self.open = False

    def _check_append_stringlike_inline(self):
        if not self.open:
            raise erring.ParseError('Attempted to append to a list-like object that was not open for appending', self.state.traceback)
        state = self.state
        if state.stringlike_effective_indent != self.indent:
            raise erring.ParseError('Indentation error in list-like object', state.traceback_stringlike)
        self.append(state.stringlike_obj)
        self.end_lineno = state.stringlike_end_lineno
        state.type = False
        state.stringlike = False
        self.open = False

    def _check_append_stringlike_noninline_tab(self):
        if not self.open:
            raise erring.ParseError('Attempted to append to a list-like object that was not open for appending', self.state.traceback)
        state = self.state
        # Don't need to check for being at line start, since if the list is
        # open, the string-like object must have been the first thing to
        # follow `+`, etc.
        if state.stringlike_effective_indent[self.len_indent:self.len_indent_plus1] == '\t':
            if len(state.stringlike_effective_indent) < self.len_indent_plus1 or not state.stringlike_effective_indent.startswith(self.indent):
                raise erring.ParseError('Indentation error in list-like object', state.traceback)
        elif len(state.stringlike_effective_indent) < self.len_indent_plus2 or not state.stringlike_effective_indent.startswith(self.indent):
            raise erring.ParseError('Indentation error in list-like object', state.traceback)
        self.append(state.stringlike_obj)
        self.end_lineno = state.stringlike_end_lineno
        state.type = False
        state.stringlike = False
        self.open = False

    def _check_append_stringlike_noninline(self):
        if not self.open:
            raise erring.ParseError('Attempted to append to a list-like object that was not open for appending', self.state.traceback)
        state = self.state
        if len(state.stringlike_effective_indent) < self.len_indent_plus2 or not state.stringlike_effective_indent.startswith(self.indent):
            raise erring.ParseError('Indentation error in list-like object', state.traceback)
        self.append(state.stringlike_obj)
        self.end_lineno = state.stringlike_end_lineno
        state.type = False
        state.stringlike = False
        self.open = False

    def check_append_stringlike_key(self):
        raise erring.ParseError('Cannot append a key-value pair directly to a list-like object', self.state.traceback_stringlike)




class DictlikeAstObj(collections.OrderedDict):
    '''
    Abstract representation of dict-like collection objects in AST.
    '''
    __slots__ = ['ast', 'cat', 'check_append_astobj', 'check_append_stringlike',
                 'end_lineno', 'indent', 'inline', 'index', 'jump',
                 'len_indent', 'next_key', 'next_key_needs_val',
                 'open', 'parent', 'start_lineno', 'state', 'type']

    def __init__(self, ast, indent, jump=None):
        self.cat = 'dict'  # Collection type category
        self.ast = ast
        state = ast.state
        self.state = state
        self.inline = state.inline
        self.indent = indent
        self.type = None
        if state.type and not state.stringlike:
            if state.type_cat != 'dict':
                raise erring.ParseError('Invalid explicit type "{0}" applied to dict-like object'.format(state.type_obj), state.traceback_type)
            if self.inline:
                # Indentations won't necessarily be equal, because `type_indent`
                # is actual indentation of type declaration, not normalized
                # indentation
                if not state.type_indent.startswith(state.inline_indent):
                    raise erring.ParseError('Indentation error in explicit type declaration for inline dict-like object', state.traceback_type)
            else:
                if not state.type_at_line_start or state.type_end_lineno == state.start_lineno:
                    raise erring.ParseError('Explicit type declaration for dict-like object must be on a line by itself in non-inline syntax', state.traceback_type)
                if not indent.startswith(state.type_indent):
                    # A dict with an explicit type declaration may indented
                    # under the declaration.
                    raise erring.ParseError('Indentation mismatch between explicit type declaration for list-like object and object contents', state.traceback_type)
            self.start_lineno = state.type_start_lineno
            self.type = state.type_obj
            state.type = False
        elif state.stringlike:
            self.start_lineno = state.stringlike_effective_start_lineno
        else:
            self.start_lineno = state.start_lineno
        self.end_lineno = self.start_lineno
        self.open = False
        self.parent = ast.pos
        self.jump = jump
        self.index = ast.pos.next_key if ast.pos.cat == 'dict' else len(ast.pos)
        self.next_key = None
        self.next_key_needs_val = False
        if self.inline:
            self.check_append_astobj = self._check_append_astobj_inline_key
            self.check_append_stringlike = self._check_append_stringlike_inline_key
        else:
            self.check_append_astobj = self._check_append_astobj_noninline_key
            self.check_append_stringlike = self._check_append_stringlike_noninline_key
            self.len_indent = len(self.indent)
        # Never instantiated with any contents
        collections.OrderedDict.__init__(self)

    def _check_append_astobj_inline_key(self, val):
        raise erring.ParseError('A dict-like object cannot take a collection object as a key', self.state.traceback)

    def _check_append_astobj_inline_val(self, val):
        if val.indent != self.indent:
            raise erring.ParseError('Indentation error in dict-like object', self.state.traceback)
        self[self.next_key] = val
        self.next_key_needs_val = False
        self.end_lineno = val.end_lineno
        self.ast.pos = val
        self.ast.astobj_to_pythonize_list.append(val)
        self.check_append_astobj = self._check_append_astobj_inline_key
        self.check_append_stringlike = self._check_append_stringlike_inline_key
        self.open = False

    def _check_append_astobj_noninline_key(self, val):
        raise erring.ParseError('A dict-like object cannot take a collection object as a key', self.state.traceback)

    def _check_append_astobj_noninline_val(self, val):
        if val.inline and val.start_lineno == self.end_lineno:
            pass
        elif len(val.indent) <= self.len_indent or not val.indent.startswith(self.indent):
            raise erring.ParseError('Indentation error in dict-like object', self.state.traceback)
        self[self.next_key] = val
        self.next_key_needs_val = False
        self.end_lineno = val.end_lineno
        self.ast.pos = val
        self.ast.astobj_to_pythonize_list.append(val)
        self.check_append_astobj = self._check_append_astobj_noninline_key
        self.check_append_stringlike = self._check_append_stringlike_noninline_key
        self.open = False

    def _check_append_stringlike_inline_key(self):
        state = self.state
        if not self.open:
            raise erring.ParseError('Cannot add a key to a dict-like object when the previous pair has not been terminated by "{0}"'.format(state.decoder._reserved_chars_separator), state.traceback)
        if state.stringlike_effective_indent != self.indent:
            raise erring.ParseError('Indentation error in dict-like object', state.traceback)
        key = state.stringlike_obj
        if key in self:
            raise erring.ParseError('Duplicate keys in dict-like objects are not allowed; duplicate key = "{0}"'.format(key.replace('"', '\\"')), state.traceback_stringlike)
        self.next_key = key
        self.next_key_needs_val = True
        self.end_lineno = state.stringlike_end_lineno
        state.type = False
        state.stringlike = False
        self.check_append_astobj = self._check_append_astobj_inline_val
        self.check_append_stringlike = self._check_append_stringlike_inline_val

    def _check_append_stringlike_inline_val(self):
        state = self.state
        if state.stringlike_effective_indent != self.indent:
            raise erring.ParseError('Indentation error in dict-like object', state.traceback)
        self[self.next_key] = state.stringlike_obj
        self.next_key_needs_val = False
        self.end_lineno = state.stringlike_end_lineno
        state.type = False
        state.stringlike = False
        self.check_append_astobj = self._check_append_astobj_inline_key
        self.check_append_stringlike = self._check_append_stringlike_inline_key
        self.open = False

    def _check_append_stringlike_noninline_key(self):
        # Non-inline dict-like objects are self-opening
        state = self.state
        if not state.stringlike_effective_at_line_start:
            raise erring.ParseError('Keys for dict-like objects must be at the beginning of a line in non-inline syntax; check for leading comment, missing linebreak, or missing quotes', state.traceback)
        if state.stringlike_effective_indent != self.indent:
            if not self and self.type is not None and state.stringlike_effective_indent.startswith(self.indent):
                # Could be indented relative to explicit type declaration.
                # Don't have to worry about equivalent case in inline syntax,
                # since normalized indentations are all the same.  Don't have
                # to worry about the equivalent in the transition to inline
                # syntax, because `{`, `[`, etc. will check for explicit typing
                # and adjust `inline_indent` accordingly.  Likewise, for
                # non-inline lists, `+`, etc. performs the necessary checks.
                self.indent = state.stringlike_effective_indent
            else:
                raise erring.ParseError('Indentation error in dict-like object', state.traceback)
        key = state.stringlike_obj
        if key in self:
            raise erring.ParseError('Duplicate keys in dict-like objects are not allowed; duplicate key = "{0}"'.format(key.replace('"', '\\"')), state.traceback_stringlike)
        self.next_key = key
        self.next_key_needs_val = True
        self.end_lineno = state.stringlike_end_lineno
        state.type = False
        state.stringlike = False
        self.check_append_astobj = self._check_append_astobj_noninline_val
        self.check_append_stringlike = self._check_append_stringlike_noninline_val

    def _check_append_stringlike_noninline_val(self):
        state = self.state
        if self.end_lineno != state.stringlike_effective_start_lineno:
            if state.stringlike_effective_at_line_start:
                if len(state.stringlike_effective_indent) <= self.len_indent or not state.stringlike_effective_indent.startswith(self.indent):
                    raise erring.ParseError('Indentation error in dict-like object', state.traceback_stringlike)
        self[self.next_key] = state.stringlike_obj
        self.next_key_needs_val = False
        self.end_lineno = state.stringlike_end_lineno
        state.type = False
        state.stringlike = False
        self.check_append_astobj = self._check_append_astobj_noninline_key
        self.check_append_stringlike = self._check_append_stringlike_noninline_key
        # Non-inline dicts are self-opening, so no need to close




class Ast(object):
    '''
    Abstract syntax tree of data, before final, full conversion into Python
    objects.  At this stage, all non-collection types are in final form,
    and all collection types are represented as `ListlikeAstObj` instances,
    which are a subclass of `list`, or `DictlikeAstObj` instances, which are a
    subclass of `collections.OrderedDict`.

    The `pythonize()` method converts `*AstObj` instances within an `Ast` into
    the corresponding Python objects.  This leaves the `Ast` as a `RootAstObj`
    that contains a single element that is the actual data.
    '''
    __slots__ = ['decoder', 'pos', 'astobj_to_pythonize_list', 'root', 'state']

    def __init__(self, decoder):
        self.decoder = decoder
        self.state = decoder.state
        self.state.register(ast=self, decoder=self.decoder)
        self.root = RootAstObj(self)
        self.pos = self.root
        self.astobj_to_pythonize_list = []

    def __eq__(self, other):
        return self.root == other

    def __str__(self):
        return '<Ast: {0}>'.format(str(self.root))

    def __repr__(self):
        return '<Ast: {0}>'.format(repr(self.root))

    def __bool__(self):
        return bool(self.root)

    def append_collection(self, cat, indent):
        '''
        Append a collection object to the AST, using its collection category
        and indentation.

        If the indentation of the object is less than that of the current
        position in the AST, walk back up the AST to find a location with
        appropriate indentation.
        '''
        state = self.state
        # Temp variables must be used with care; otherwise, mess up tracebacks
        pos = self.pos
        root = self.root
        if not state.inline and pos is not root and len(indent) < len(pos.indent):
            # Don't actually start up the `while` loop machinery unless it will
            # be used.  In inline syntax, it's impossible to go to a higher
            # level in the AST by changing indentation level, and if there's
            # an improperly indented line, it will be caught.
            while pos is not root and len(indent) < len(pos.indent):
                if pos.cat == 'dict':
                    if not pos:
                        # Could have an empty dict due to an explicit type declaration
                        self.pos = pos
                        raise erring.ParseError('A non-inline dict-like object cannot be empty', state.traceback_ast_pos)
                    if pos.next_key_needs_val:
                        self.pos = pos
                        raise erring.ParseError('A dict-like object ended before a key-value pair was completed', state.traceback_ast_pos)
                else:  # pos.cat == 'list'
                    if pos.open:
                        self.pos = pos
                        raise erring.ParseError('A list-like object ended before an expected element was added', state.traceback_ast_pos)
                    if not pos:
                        self.pos = pos
                        raise erring.ParseError('A non-inline list cannot be empty', state.traceback_ast_pos)
                pos.parent.end_lineno = pos.end_lineno
                pos = pos.parent
            self.pos = pos
        if cat == 'dict':
            self.pos.check_append_astobj(DictlikeAstObj(self, indent))
        else: # cat == 'list'
            self.pos.check_append_astobj(ListlikeAstObj(self, indent))

    def append_stringlike(self):
        '''
        Append a string-like object at the current position within the AST.
        '''
        self.pos.check_append_stringlike()

    def append_stringlike_key(self):
        '''
        Append a string-like object at the current position within the AST, as
        a key in a dict-like object.
        '''
        state = self.state
        # Temp variables must be used with care; otherwise, mess up tracebacks
        pos = self.pos
        root = self.root
        if not state.inline and not (self.pos.cat == 'dict' and state.stringlike_effective_indent == pos.indent and not self.pos.next_key_needs_val):
            if pos is not root and len(state.stringlike_effective_indent) < len(pos.indent):
                while pos is not root and len(state.stringlike_effective_indent) < len(pos.indent):
                    if pos.cat == 'dict':
                        if not pos:
                            # Could have an empty dict due to an explicit type declaration
                            self.pos = pos
                            raise erring.ParseError('A non-inline dict-like object cannot be empty', state.traceback_ast_pos)
                        if pos.next_key_needs_val:
                            self.pos = pos
                            raise erring.ParseError('A dict-like object ended before a key-value pair was completed', state.traceback_ast_pos)
                    else:  # pos.cat == 'list'
                        if pos.open:
                            self.pos = pos
                            raise erring.ParseError('A list-like object ended before an expected element was added', state.traceback_ast_pos)
                        if not pos:
                            self.pos = pos
                            raise erring.ParseError('A non-inline list cannot be empty', state.traceback_ast_pos)
                    pos.parent.end_lineno = pos.end_lineno
                    pos = pos.parent
                self.pos = pos
            if pos.cat != 'dict' or pos.indent != state.stringlike_effective_indent:
                pos.check_append_astobj(DictlikeAstObj(self, state.stringlike_effective_indent))
            elif pos.next_key_needs_val:
                raise erring.ParseError('A dict-like object was given a key before a previous key-value pair was complete', state.traceback_stringlike)
        self.pos.check_append_stringlike()

    def open_collection_inline(self):
        '''
        Open a collection object in inline syntax.
        '''
        if not self.state.inline:
            raise erring.ParseError('Invalid object termination "{0}" in non-inline syntax'.format(self.state.decoder._reserved_chars_separator), self.state.traceback)
        if self.pos.open:
            if self.pos.cat == 'dict' and self.pos.next_key_needs_val:
                raise erring.ParseError('Encountered "{0}" before a key-value pair was completed'.format(self.state.decoder._reserved_chars_separator), self.state.traceback)
            else:
                raise erring.ParseError('Encountered "{0}" when there is no object to end'.format(self.state.decoder._reserved_chars_separator), self.state.traceback)
        self.pos.open = True

    def open_list_non_inline(self):
        '''
        Open a list-like object in non-inline syntax.
        '''
        state = self.state
        if state.inline or not state.at_line_start:
            raise erring.ParseError('Invalid location to begin a non-inline list element', state.traceback)
        # Temp variables must be used with care; otherwise, mess up tracebacks
        pos = self.pos
        root = self.root
        if pos is not root and len(state.indent) < len(pos.indent):
            # If the list to be opened already exists, need to make sure we are
            # at the correct level in the AST.
            while pos is not root and len(state.indent) < len(pos.indent):
                if pos.cat == 'dict':
                    if not pos:
                        # Could have an empty dict due to an explicit type declaration
                        self.pos = pos
                        raise erring.ParseError('A non-inline dict-like object cannot be empty', state.traceback_ast_pos)
                    if pos.next_key_needs_val:
                        self.pos = pos
                        raise erring.ParseError('A dict-like object ended before a key-value pair was completed', state.traceback_ast_pos)
                else:  # pos.cat == 'list'
                    if pos.open:
                        self.pos = pos
                        raise erring.ParseError('A list-like object ended before an expected element was added', state.traceback_ast_pos)
                    if not pos:
                        self.pos = pos
                        raise erring.ParseError('A non-inline list cannot be empty', state.traceback_ast_pos)
                pos.parent.end_lineno = pos.end_lineno
                pos = pos.parent
            self.pos = pos
        if pos.cat != 'list':
            # No need to check indentation in the event of an explicit type
            # declaration; that's built into `ListlikeAstObj`.  This will give
            # list correct indentation, even if the `+`, etc. is indented
            # relative to the type declaration.
            self.append_collection('list', state.indent)
        elif len(pos.indent) < len(state.indent):
            if pos.start_lineno == state.start_lineno:
                raise erring.ParseError('Cannot begin a list element on a line where one has already been started in non-inline syntax', state.traceback)
            self.append_collection('list', state.indent)
        self.pos.open = True

    def end_dict_inline(self):
        '''
        End a dict-like object in inline syntax.
        '''
        state = self.state
        if not state.inline:
            raise erring.ParseError('Cannot end an inline dict-like object with "{0}" when not in inline mode'.format(state.decoder._reserved_chars_end_dict), state.traceback)
        if self.pos.cat != 'dict':
            raise erring.ParseError('Encountered "{0}" when there is no dict-like object to end'.format(state.decoder._reserved_chars_end_dict), state.traceback)
        if not state.indent.startswith(state.inline_indent):
            raise erring.ParseError('Indentation error', state.traceback)
        if self.pos.next_key_needs_val:
            raise erring.ParseError('A dict-like object ended before a key-value pair was completed', state.traceback)
        self.pos = self.pos.parent
        state.inline = self.pos.inline

    def end_list_inline(self):
        '''
        End a list-like object in inline syntax.
        '''
        state = self.state
        if not state.inline:
            raise erring.ParseError('Cannot end an inline list-like object with "{0}" when not in inline mode'.format(state.decoder._reserved_chars_end_list), state.traceback)
        if self.pos.cat != 'list':
            raise erring.ParseError('Encountered "{0}" when there is no list-like object to end'.format(state.decoder._reserved_chars_end_list), state.traceback)
        if not state.indent.startswith(state.inline_indent):
            raise erring.ParseError('Indentation error', state.traceback)
        self.pos = self.pos.parent
        state.inline = self.pos.inline

    def finalize(self):
        '''
        Check AST for errors and return to root node.
        '''
        if self.pos is not self.root:
            state = self.state
            if state.inline:
                raise erring.ParseError('Inline syntax was never closed', state.traceback_start_inline_to_end)
            if state.type:
                # Explicit type declarations are used as needed; they are not
                # used immediately as encountered, as are string-like objects
                raise erring.ParseError('Explicit type declaration "{0}" was never used'.format(state.type_obj), state.traceback_type)
            if state.stringlike:
                # This should never happen since string-like objects are always
                # used immediately, but just for safety purposes
                raise erring.ParseError('String-like object was never fully loaded', state.traceback_stringlike)
            # Temp variables must be used with care; otherwise, mess up tracebacks
            pos = self.pos
            root = self.root
            if pos is not root:
                while pos is not root:
                    if pos.cat == 'dict':
                        if not pos:
                            # Could have an empty dict due to an explicit type declaration
                            self.pos = pos
                            raise erring.ParseError('A non-inline dict-like object cannot be empty', state.traceback_ast_pos)
                        if pos.next_key_needs_val:
                            self.pos = pos
                            raise erring.ParseError('A dict-like object ended before a key-value pair was completed', state.traceback_ast_pos)
                    else:  # pos.cat == 'list'
                        if pos.open:
                            self.pos = pos
                            raise erring.ParseError('A list-like object ended before an expected element was added', state.traceback_ast_pos)
                        if not pos:
                            self.pos = pos
                            raise erring.ParseError('A non-inline list cannot be empty', state.traceback_ast_pos)
                    pos.parent.end_lineno = pos.end_lineno
                    pos = pos.parent
                self.pos = pos

    def pythonize(self):
        '''
        Convert all `AstObj` (except for root node) to corresponding native
        Python types.

        Go through list of objects that need to be Pythonized in reverse order,
        so that lower-level objects are Pythonized first.  This way,
        higher-level objects remain in abstract form until they themselves are
        Pythonized, so their contents are easily replaced with Pythonized
        equivalents.
        '''
        parsers = self.decoder._parsers
        for ast_obj in reversed(self.astobj_to_pythonize_list):
            py_obj = parsers[ast_obj.cat][ast_obj.type](ast_obj)
            ast_obj.parent[ast_obj.index] = py_obj




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
    'default_parser_aliases',
    'dict_parsers',
    'list_parsers',
    'string_parsers',
    '_bytes_parsers',
    'parsers',
    'reserved_words',
    'parser_aliases',
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
    '_explicit_type_name_check_re',
    '_opening_delim_percent_re',
    '_opening_delim_single_quote_re',
    '_opening_delim_double_quote_re',
    '_opening_delim_equals_re',
    '_opening_delim_pipe_re',
    '_opening_delim_plus_re',
    '_closing_delim_re_dict',
    '_numeric_types_starting_chars',
    '_int_re',
    '_float_re',
    '_unquoted_key_re',
    '_keypath_element_re',
    '_keypath_re',
    '_unquoted_string_fragment_re',
    '_line_iter', '_ast']
    """
    def __init__(self, only_ascii=False, unquoted_strings=True, unquoted_unicode=False,
                 dialect=None, reserved_chars=None, reserved_words=None,
                 dict_parsers=None, list_parsers=None, string_parsers=None, parser_aliases=None,
                 **kwargs):
        arg_bools = (only_ascii, unquoted_strings, unquoted_unicode)
        if not all(x in (True, False) for x in arg_bools):
            raise erring.ConfigError('Arguments "only_ascii", "unquoted_strings", "unquoted_unicode" must be boolean')
        # In sanity checks, it is important to keep in mind that
        # `unquoted_strings` and `unquoted_unicode` are separate and don't
        # necessarily overlap.  It would be possible to have unquoted Unicode
        # characters in a reserved word, which would not count as a string that
        # needs quoting.
        if only_ascii and unquoted_unicode:
            raise erring.ConfigError('Setting "only_ascii" = True is incompatible with "unquoted_unicode" = True')
        # Default settings for allowed characters and quoting
        self.only_ascii = only_ascii
        self.unquoted_strings = unquoted_strings
        self.unquoted_unicode = unquoted_unicode
        # Settings that are actually used; these may be changed via parser
        # directives `(bespon ...)>`.
        self._only_ascii__current = only_ascii
        self._unquoted_strings__current = unquoted_strings
        self._unquoted_unicode__current = unquoted_unicode


        if dialect is not None and not isinstance(dialect, str):
            raise erring.ConfigError('"dialect" must be None or a Unicode string')
        if reserved_chars is None and reserved_words is None:
            self.dialect = dialect or 'bespon'
        else:
            self.dialect = dialect or 'bespon.custom'


        # Create a UnicodeFilter instance
        # Provide shortcuts to some of its attributes
        self._unicodefilter = unicoding.UnicodeFilter(**kwargs)
        self._nonliterals = self._unicodefilter.nonliterals
        self._newlines = self._unicodefilter.newlines
        self._newline_chars = self._unicodefilter.newline_chars
        self._newline_chars_str = self._unicodefilter.newline_chars_str
        self._spaces = self._unicodefilter.spaces
        self._spaces_str = self._unicodefilter.spaces_str
        self._indents = self._unicodefilter.indents
        self._indents_str = self._unicodefilter.indents_str
        self._whitespace = self._unicodefilter.whitespace
        self._whitespace_str = self._unicodefilter.whitespace_str
        self._unicode_whitespace = self._unicodefilter.unicode_whitespace
        self._unicode_whitespace_str = self._unicodefilter.unicode_whitespace_str
        self._unicode_whitespace_re = re.compile('[{0}]'.format(re.escape(self._unicode_whitespace_str)))


        arg_dicts = (reserved_chars, reserved_words, dict_parsers, list_parsers, string_parsers, parser_aliases)
        if not all(x is None or isinstance(x, dict) for x in arg_dicts):
            raise TypeError('Arguments "reserved_chars", "reserved_words", "*_parsers", "parser_aliases" must be dicts')


        # Take care of reserved characters and related dict for parsing
        if reserved_chars is None:
            final_reserved_chars = defaults.RESERVED_CHARS
        else:
            # For custom reserved characters, do basic consistency checks
            for k, v in reserved_chars.items():
                if k not in defaults.RESERVED_CHARS:
                    raise erring.ConfigError('"reserved_chars" contains unknown key "{0}"'.format(k))
                if v is not None and (not isinstance(v, str) or len(v) != 1):
                    raise erring.ConfigError('"reserved_chars" must map to None or to Unicode strings of length 1 (on narrow Python builds, this limits the range of acceptable code points)')
                if v in '+-._0123456789' or ord('a') <= ord(v) <= ord('z') or ord('A') <= ord(v) <= ord('Z'):
                    # Don't allow alphanumerics, or characters used in defining digits, to be reserved chars
                    raise erring.ConfigError('"reserved_chars" cannot include the plus, hyphen, period, underscore, or 0-9, a-z, A-Z')
            if len(set(v for k, v in reserved_chars.items() if v is not None)) != len(k for k, v in reserved_chars.items() if v is not None):
                raise erring.ConfigError('"reserved_chars" contains duplicate mappings to a single code point')
            # Need a `defaultdict`, so that don't have to worry about whether
            # all elements are present
            final_reserved_chars = collections.defaultdict(lambda: None, reserved_chars)
            for o, c in (('start_type', 'end_type'), ('start_list', 'end_list'), ('start_dict', 'end_dict')):
                if not ((final_reserved_chars[o] is None and final_reserved_chars[c] is None) or (final_reserved_chars[o] is not None and final_reserved_chars[c] is not None)):
                    raise erring.ConfigError('Inconsistent "reserved_chars"; opening and closing delimiters must be defined in pairs')
            if final_reserved_chars['start_type'] is not None and final_reserved_chars['end_type_suffix'] is None:
                raise erring.ConfigError('Inconsistent "reserved_chars"; must define "end_type_suffix"')
            if any(final_reserved_chars[k] is not None for k in ('comment', 'literal_string', 'escaped_string')) and final_reserved_chars['block_suffix'] is None:
                raise erring.ConfigError('Inconsistent "reserved_chars"; cannot define comments or quoted strings without defining "block_suffix"')
            if any(final_reserved_chars[k] is not None for k in ('start_type', 'start_list', 'start_dict')) and final_reserved_chars['separator'] is None:
                raise erring.ConfigError('Inconsistent "reserved_chars"; cannot define explicit typing or collection objects without defining "separator"')
            if final_reserved_chars['assign_key_val'] is None:
                raise erring.ConfigError('Inconsistent "reserved_chars"; must define "assign_key_val"')
        self._reserved_chars = final_reserved_chars

        self._reserved_chars_literal_string = self._reserved_chars['literal_string']
        self._reserved_chars_escaped_string = self._reserved_chars['escaped_string']
        self._reserved_chars_list_item = self._reserved_chars['list_item']
        self._reserved_chars_comment = self._reserved_chars['comment']
        self._reserved_chars_separator = self._reserved_chars['separator']
        self._reserved_chars_end_list = self._reserved_chars['end_list']
        self._reserved_chars_end_dict = self._reserved_chars['end_dict']
        self._reserved_chars_end_type_with_suffix = self._reserved_chars['end_type'] + self._reserved_chars['end_type_suffix']
        self._reserved_chars_assign_key_val = self._reserved_chars['assign_key_val']
        self._reserved_chars_block_suffix = self._reserved_chars['block_suffix']

        char_functions = {'comment':         self._parse_line_comment,
                          'start_type':      self._parse_line_start_type,
                          'end_type':        self._parse_line_end_type,
                          'start_list':      self._parse_line_start_list,
                          'end_list':        self._parse_line_end_list,
                          'start_dict':      self._parse_line_start_dict,
                          'end_dict':        self._parse_line_end_dict,
                          'literal_string':  self._parse_line_literal_string,
                          'escaped_string':  self._parse_line_escaped_string,
                          'assign_key_val':  self._parse_line_assign_key_val,
                          'separator':       self._parse_line_separator,
                          'list_item':       self._parse_line_list_item}
        # Dict of functions for proceeding with parsing, based on the next
        # character.
        parse_line = collections.defaultdict(lambda: self._parse_line_unquoted_string)
        parse_line[''] = self._parse_line_goto_next
        for c in self._whitespace:
            parse_line[c] = self._parse_line_whitespace
        for k, v in final_reserved_chars.items():
            if k in char_functions and v is not None:
                # `*_suffix` characters don't need parsing functions
                parse_line[v] = char_functions[k]
        self._parse_line = parse_line


        # Characters that can't appear in normal unquoted strings.  This is
        # all reserved characters except for the suffix characters.  The
        # suffix characters are always safe, because they only have special
        # meaning when immediately following special characters.
        #
        # A case could be made for allowing some of the reserved characters
        # unquoted.  `list_item` (`*`) only has an effect in non-inline syntax,
        # at the beginning of a line, when followed by an indentation
        # character.  Likewise, `literal_string` and `escaped_string`
        # (quotation marks) only function as string escapes at the beginning
        # of text.  The comment character could be required to be at the
        # beginning of a line or be preceded by whitespace.  All of these
        # would work in principle, but they also increase cognitive load.
        # Instead of the user thinking "just quote it" when encountering a
        # reserved character, the user may instead start thinking about
        # the context and whether quoting is required.  Given that bespon
        # goes to great lengths to provide powerful and convenient quoting,
        # that would be undesirable.  The rules must be few and plain.
        #
        # The inline object delimiters and separator must always be special in
        # inline syntax, unless special context and nesting rules are used, in
        # which case cognitive load is also increased to undesirable levels.
        # It would be possible to allow them in non-inline syntax, but that
        # would make switching between inline and non-inline syntax more
        # complex.  A primary design principle is that anything valid in one
        # context must be valid in all.
        self._not_unquoted_str = ''.join(v for k, v in self._reserved_chars.items() if k not in ('end_type_suffix', 'block_suffix') and v is not None)
        self._not_unquoted = set(self._not_unquoted_str)
        self._allowed_ascii = ''.join(chr(n) for n in range(128) if chr(n) not in self._not_unquoted and chr(n) not in self._nonliterals)
        self._end_unquoted_string_re__ascii = re.compile('[^{0}]'.format(re.escape(self._allowed_ascii)))
        self._end_unquoted_string_re__unicode = re.compile('|'.join(re.escape(c) for c in self._not_unquoted))
        self._end_unquoted_string_re = self._end_unquoted_string_re__ascii


        # Regex for integers, including hex, octal, and binary.
        # It's easier to write out regex with whitespace but no comments, and
        # then replace whitespace with empty string, than to worry about using
        # `re.VERBOSE` later, when combining into a large regex.
        pattern_int = r'''
                       (?P<num_int_base10> [+-]?[1-9](?:_[0-9]|[0-9])* $ | [+-]?0 $ ) |
                       (?P<num_int_base16> [+-]?0x [0-9a-fA-F](?:_[0-9a-fA-F]|[0-9a-fA-F])* $ ) |
                       (?P<num_int_base8> [+-]?0o [0-7](?:_[0-7]|[0-7])* $ ) |
                       (?P<num_int_base2> [+-]?0b [01](?:_[01]|[01])* $ )
                       '''
        pattern_int = pattern_int.replace(' ', '').replace('\n', '')
        self._int_re = re.compile(pattern_int)

        # Catch leading zeros, uppercase X, O, B
        pattern_invalid_int = r'''
                               (?P<invalid_int>
                                  [+-]? (?: 0+(?:_[0-9]|[0-9])* |
                                            0X [0-9a-fA-F](?:_[0-9a-fA-F]|[0-9a-fA-F])* |
                                            0O [0-7](?:_[0-7]|[0-7])* |
                                            0B [01](?:_[01]|[01])*
                                        )
                                  $
                               )
                               '''
        pattern_invalid_int = pattern_invalid_int.replace(' ', '').replace('\n', '')
        self._invalid_int_re = re.compile(pattern_invalid_int)

        # Regex for floats, including hex.
        pattern_float = r'''
                         (?P<num_float_base10>
                             [+-]? (?: \. [0-9](?:_[0-9]|[0-9])* (?:[eE][+-]?[0-9](?:_[0-9]|[0-9])*)? |
                                       (?:[1-9](?:_[0-9]|[0-9])*|0)
                                          (?: \. (?:[0-9](?:_[0-9]|[0-9])*)? (?:[eE][+-]?[0-9](?:_[0-9]|[0-9])*)? |
                                              [eE][+-]?[0-9](?:_[0-9]|[0-9])*
                                          )
                                   ) $
                         ) |
                         (?P<num_float_base16>
                             [+-]? 0x (?: \.[0-9a-fA-F](?:_[0-9a-fA-F]|[0-9a-fA-F])* (?:[pP][+-]?[0-9](?:_[0-9]|[0-9])*)? |
                                          [0-9a-fA-F](?:_[0-9a-fA-F]|[0-9a-fA-F])*
                                             (?: \. (?:[0-9a-fA-F](?:_[0-9a-fA-F]|[0-9a-fA-F])*)? (?:[pP][+-]?[0-9](?:_[0-9]|[0-9])*)? |
                                                 [pP][+-]?[0-9](?:_[0-9]|[0-9])*
                                             )
                                      ) $
                         )
                         '''
        pattern_float = pattern_float.replace(' ', '').replace('\n', '')
        self._float_re = re.compile(pattern_float)

        pattern_invalid_float = r'''
                                 (?P<invalid_float>
                                    [+-]? (?: (?: 0+(?:_[0-9]|[0-9])
                                                  (?: \. (?:[0-9](?:_[0-9]|[0-9])*)? (?:[eE][+-]?[0-9](?:_[0-9]|[0-9])*)? |
                                                      [eE][+-]?[0-9](?:_[0-9]|[0-9])*
                                                  )
                                              ) |
                                              0X (?: \.[0-9a-fA-F](?:_[0-9a-fA-F]|[0-9a-fA-F])* (?:[pP][+-]?[0-9](?:_[0-9]|[0-9])*)? |
                                                     [0-9a-fA-F](?:_[0-9a-fA-F]|[0-9a-fA-F])*
                                                        (?: \. (?:[0-9a-fA-F](?:_[0-9a-fA-F]|[0-9a-fA-F])*)? (?:[pP][+-]?[0-9](?:_[0-9]|[0-9])*)? |
                                                            [pP][+-]?[0-9](?:_[0-9]|[0-9])*
                                                        )
                                                 )
                                          ) $
                                 )
                                 '''
        pattern_invalid_float = pattern_invalid_float.replace(' ', '').replace('\n', '')
        self._invalid_float_re = re.compile(pattern_invalid_float)


        # Take care of `reserved_words`
        if reserved_words is None:
            self._reserved_words = defaults.RESERVED_WORDS
        else:
            for k in reserved_words:
                if self._unicode_whitespace_re.search(k):
                    raise erring.ConfigError('"reserved_words" cannot contain words with Unicode whitespace characters')
                if self._int_re.match(k) or self._invalid_int_re.match(k) or self._float_re.match(k) or self._invalid_float_re.match(k):
                    raise erring.ConfigError('"reserved_words" cannot contain words that match the pattern for integers or floats, or the pattern for invalid integers or floats')
                if not self.unquoted_unicode:
                    m = self._unicodefilter.ascii_less_newlines_and_nonliterals_re.match(k)
                    if not m or m.group(0) != k:
                        raise erring.ConfigError('"reserved_words" cannot contain words with non-ASCII characters when "unquoted_unicode" = False')
            self._reserved_words = reserved_words

        self._boolean_reserved_words_re = re.compile('|'.join(re.escape(k) for k, v in self._reserved_words.items() if v in (True, False)))


        # Assemble a regex for matching all special unquoted values
        reserved_words_lower_set = set([w.lower() for w in self._reserved_words])
        pattern_reserved_words_case_insensitive = '(?P<reserved_words>{0})'.format('|'.join(''.join('[{0}]'.format(re.escape(c+c.upper())) for c in w) + '$' for w in reserved_words_lower_set))
        pattern_reserved_words_int_float_invalid = '{r}|{i}|{f}|{inv_i}|{inv_f}'.format(r=pattern_reserved_words_case_insensitive, i=pattern_int, f=pattern_float, inv_i=pattern_invalid_int, inv_f=pattern_invalid_float)
        # Quick identification of strings for unquoted value checking
        self._reserved_words_int_float_invalid_re = re.compile(pattern_reserved_words_int_float_invalid)
        self._reserved_words_int_float_starting_chars = set('+-.0123456789' + ''.join(w[0] + w[0].upper() for w in reserved_words_lower_set))
        self._reserved_words_int_float_ending_chars = set('.0123456789abcdefABCDEF' + ''.join(w[-1] + w[-1].upper() for w in reserved_words_lower_set))


        # Required form for all type names
        pattern_type_key = r'[a-zA-Z][0-9a-zA-Z_-]*(?:\:\:[a-zA-Z][0-9a-zA-Z_-]*|\.[a-zA-Z][0-9a-zA-Z_-]*)*$'
        self._type_name_check_re = re.compile(pattern_type_key)
        self._type_key_re = re.compile(pattern_type_key.rstrip('$'))


        # Take care of parsers and parser aliases
        for d in (dict_parsers, list_parsers, string_parsers):
            if d is not None:
                for k, v in d.items():
                    if not isinstance(k, str) or not hasattr(v, '__call__'):
                        raise TypeError('All parser dicts must map Unicode strings to functions (callable)'.format(k, v))
                    if any(k.startswith(p) for p in defaults.RESERVED_TYPE_PREFIXES) or k in defaults.RESERVED_TYPES:
                        raise erring.ConfigError('User-defined parser "{0}" has a name that is a reserved type name, or that begins with a reserved type prefix'.format(k))
                    if not self._type_name_check_re.match(k):
                        raise erring.ConfigError('User-defined parser "{0}" has a name that does not fit the required form for parser names; use a name of the form "namespace::type.sub_type", etc., using only ASCII alphanumerics plus the period, double colon, and underscore'.format(k))
        if dict_parsers is None:
            self._dict_parsers = defaults.DICT_PARSERS
        else:
            self._dict_parsers = dict_parsers
        if list_parsers is None:
            self._list_parsers = defaults.LIST_PARSERS
        else:
            self._list_parsers = list_parsers
        if string_parsers is None:
            self._string_parsers = defaults.STRING_PARSERS
        else:
            self._string_parsers = string_parsers

        if all(x is None for x in (dict_parsers, list_parsers, string_parsers)):
            self.__bytes_parsers = defaults._BYTES_PARSERS
            self.__num_parsers = defaults._NUM_PARSERS
        else:
            if set(self._dict_parsers) & set(self._list_parsers) & set(self._string_parsers):
                raise erring.ConfigError('Overlap between dict, list, and string parsers is not allowed')
            self.__bytes_parsers = set([p for p in self._string_parsers if p.split('::')[-1].split('.')[0] == 'bytes'])
            self.__num_parsers = set([p for p in self._string_parsers if p.split('::')[-1].split('.')[0] == 'num'])

        # Need a way to look up parsers by category
        self._parsers = {'dict':   self._dict_parsers,
                         'list':   self._list_parsers,
                         'string': self._string_parsers}

        if parser_aliases is None:
            self._parser_aliases = defaults.PARSER_ALIASES
            for k, v in self._parser_aliases.items():
                self._string_parsers[k] = self._string_parsers[v]
        else:
            self._parser_aliases = parser_aliases
            for k, v in self._parser_aliases.items():
                if not isinstance(k, str) or not self._type_name_check_re.match(k):
                    raise erring.ConfigError('Parser alias "{0}" should be a Unicode string of the form "namespace::type.sub_type", etc., using only ASCII alphanumerics plus the period, double colon, and underscore'.format(k))
                found = False
                if k in self._dict_parsers or k in self._list_parsers or k in self._string_parsers:
                    raise erring.ConfigError('Parse alias "{0}" is already a type name'.format(k))
                if v in self._dict_parsers:
                    self._dict_parsers[k] = self._dict_parsers[v]
                    found = True
                elif v in self._list_parsers:
                    self._list_parsers[k] = self._list_parsers[v]
                    found = True
                elif v in self._string_parsers:
                    self._string_parsers[k] = self._string_parsers[v]
                    if v in self.__bytes_parsers:
                        self.__bytes_parsers.update(k)
                    found = True
                if not found:
                    raise ValueError('Alias "{0}" => "{1}" maps to unknown type'.format(k, v))

        # Need a way to look up category for a given parser
        # Note that parsers can't overlap multiple categories
        parser_cats = {}
        for cat, dct in self._parsers.items():
            for k in dct:
                parser_cats[k] = cat
        self._parser_cats = parser_cats

        # Set default parsers in each category
        self._dict_parsers[None] = self._dict_parsers['dict']
        self._list_parsers[None] = self._list_parsers['list']
        self._string_parsers[None] = self._string_parsers['str']


        # Dict of regexes for identifying closing delimiters.  Automatically
        # generates needed regex on the fly.  Regexes for opening delimiters
        # aren't needed; performed as pure string operations.
        def gen_closing_delim_regex(delim):
            c = delim[0]
            if c == self._reserved_chars_escaped_string:
                if delim == self._reserved_chars_escaped_string:
                    p = r'(?:\\.|[^{c}])*({c})'.format(c=re.escape(c))
                else:
                    p = r'(?:\\.|[^{c}])*({c}{{{n}}}(?!{c}){s}*)'.format(c=re.escape(c), n=len(delim), s=re.escape(self._reserved_chars_block_suffix))
            elif delim == self._reserved_chars_literal_string:
                p = "'"
            else:
                p = r'(?<!{c}){c}{{{n}}}(?!{c}){s}*'.format(c=re.escape(c), n=len(delim), s=re.escape(self._reserved_chars_block_suffix))
            return re.compile(p)
        self._closing_delim_re_dict = tooling.keydefaultdict(gen_closing_delim_regex)


        # Regexes for working with unquoted keys and with keypaths
        pattern_unquoted_key = r'[^\d\.{uws}{na}][^\.{uws}{na}]*'.format(uws=re.escape(self._unicode_whitespace_str),
                                                                         na=re.escape(self._not_unquoted_str))
        pattern_keypath_element = r'''
                                   (?: {uk} |
                                       \[ \* | (?:[+-]?(?:0|[1-9][0-9]*)) \] |
                                       \{{ (?:[^\.{uws}{na}]+ | (?: ) | ) \}}
                                   )
                                   '''.format(uk=pattern_unquoted_key,
                                              uws=re.escape(self._unicode_whitespace_str),
                                              na=re.escape(self._not_unquoted_str))
        pattern_keypath = r'{ke}(?:\.{ke})*'.format(ke=pattern_keypath_element)



        # There are multiple regexes for unquoted keys.  Plain unquoted keys
        # need to be distinguished from keys describing key paths.
        pattern_unquoted_key = r'[^{uws}{na}]+'.format(uws=re.escape(self._unicode_whitespace_str),
                                                       na=re.escape(self._not_unquoted_str))
        self._unquoted_key_re = re.compile(pattern_unquoted_key)

        pattern_keypath_element = r'''
                                   [^\.{uws}{na}\d][^\.{uws}{na}]* |  # Identifier-style
                                   \[ (?: \+ | [+-]?[0-9]+) \] |  # Bracket-enclosed list index
                                   \{{ (?: [^{uws}{na}]+ | '[^']*' | "(?:\\.|[^"])*" ) \}}  # Brace-enclosed unquoted string, or once-quoted inline string
                                   '''
        pattern_keypath_element = pattern_keypath_element.format(uws=re.escape(self._unicode_whitespace_str),
                                                                 na=re.escape(self._not_unquoted_str))
        self._keypath_element_re = re.compile(pattern_keypath_element, re.VERBOSE)

        pattern_keypath = r'''
                           (?:{kpe})
                           (?:\. (?:{kpe}) )*
                           '''
        pattern_keypath = pattern_keypath.format(kpe=pattern_keypath_element)
        self._keypath_re = re.compile(pattern_keypath, re.VERBOSE)

        self._unquoted_string_fragment_re = re.compile(r'[^{0}]+'.format(re.escape(self._not_unquoted_str)))

        # Whether to keep raw abstract syntax tree for debugging, or go ahead
        # and convert it into full Python objects
        self._debug_raw_ast = False


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
        newline_chars_str = self._newline_chars_str
        unicode_whitespace = self._unicode_whitespace
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
        s = self._unicodefilter.unicode_to_ascii_newlines(s)
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
        if self._unicodefilter.has_nonliterals(s):
            trace = self._unicodefilter.trace_nonliterals(s)
            msg = '\n  Nonliterals traceback\n' + self._unicodefilter.format_trace(trace)
            raise erring.InvalidLiteralCharacterError(msg)
        if self.only_ascii and self._unicodefilter.has_unicode(s):
            trace = self._unicodefilter.trace_unicode(s)
            msg = '\n  Non-ASCII traceback ("only_ascii"=True)\n' + self._unicodefilter.format_trace(trace)
            raise erring.InvalidLiteralCharacterError(msg)

        # Store reference to string in case needed later
        self._string = s

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

        Note that the root node of the AST is a `RootAstObj` instance, which
        may only contain a single object.  At the root level, a BespON file
        may only contain a single scalar, or a single collection type.
        '''
        # Reset regex for finding end of unquoted strings, based on decoder
        # settings.  This could have been reset during any previous parsing
        # by a `(bespon ...)>`.
        if self.unquoted_unicode:
            self._end_unquoted_string_re = self._end_unquoted_string_re__unicode
        else:
            self._end_unquoted_string_re = self._end_unquoted_string_re__ascii
        # For the same reason, also reset all internal parsing to defaults
        self._only_ascii__current = self.only_ascii
        self._unquoted_strings__current = self.unquoted_strings
        self._unquoted_unicode__current = self.unquoted_unicode

        self.state = State()
        self._unicodefilter.traceback = self.state

        self._ast = Ast(self)

        # Start by extracting the first line and stripping any BOM
        line = self._parse_line_goto_next()
        if line:
            if line[0] == '\uFEFF':
                line = line[1:]
            elif line[0] == '\uFFFE':
                raise erring.ParseError('Encountered non-character U+FFFE, indicating string decoding with incorrect endianness', self.state.traceback)

        parse_line = self._parse_line
        while line is not None:
            line = parse_line[line[:1]](line)

        self._ast.finalize()

        if not self._ast:
            raise erring.ParseError('There was no data to load', self.state)

        self._string = None
        self.state = None
        self._unicodefilter.traceback = None

        if self._debug_raw_ast:
            return
        else:
            self._ast.pythonize()
            return self._ast.root[0]


    def _parser_directives(self, d):
        '''
        Process parser directives.

        This has security implications, so it is important that all
        implementations get it right.  A parser directive can never set
        `only_ascii` to False, or set `unquoted_strings` and `unquoted_unicode`
        to True, if that conflicts with the settings with which the decoder
        was created.  Elevating to non-ASCII characters could cause issues
        with some forms of data transmission.  Elevating quoting could increase
        the potential for homoglyph issues or other security issues related
        to Unicode.

        It is important to keep in mind that `unquoted_strings` and
        `unquoted_unicode` are separate and don't necessarily overlap.  It
        would be possible to have unquoted Unicode characters in a keyword,
        which would not count as a string that needs quoting.
        '''
        for k, v in d.items():
            if k == 'only_ascii' and v in (True, False):
                if v and not self.only_ascii:
                    if self._unicodefilter.has_unicode(self._string):
                        trace = self._unicodefilter.trace_unicode(self._string)
                        msg = '\n  Non-ASCII traceback ("only_ascii"=True)\n' + self._unicodefilter.format_trace(trace)
                        raise erring.InvalidLiteralCharacterError(msg)
                    self._only_ascii__current = True
                elif not v and self.only_ascii:
                    raise erring.ParseError('Parser directive has requested "only_ascii" = False, but decoder is set to use "only_ascii" = True', self.state.traceback)
            elif k == 'unquoted_strings' and v in (True, False):
                if v and not self.unquoted_strings:
                    raise erring.ParseError('Parser directive has requested "unquoted_strings" = True, but decoder is set to use "unquoted_strings" = False', self.state.traceback)
                elif not v and self.unquoted_strings:
                    self._unquoted_strings__current = False
            elif k == 'unquoted_unicode' and v in (True, False):
                if v and not self.unquoted_unicode:
                    raise erring.ParseError('Parser directive has requested "unquoted_unicode" = True, but decoder is set to use "unquoted_unicode" = False', self.state.traceback)
                elif not v and self.unquoted_unicode:
                    self._unquoted_unicode__current = False
                    self._end_unquoted_string_re = self._end_unquoted_string_re__ascii
            else:
                raise erring.ParseError('Invalid or unsupported parser directives', self.state.traceback)


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
            rest = line.lstrip(self._whitespace_str)
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
            rest = line.lstrip(self._whitespace_str)
            state.indent = line[:len(line)-len(rest)]
            state.at_line_start = True
            state.end_lineno += 1
            state.start_lineno = state.end_lineno
            return rest
        return line


    def _parse_line_comment(self, line):
        '''
        Parse comments.
        '''
        len_delim = len(line)
        line = line.lstrip(self._reserved_chars_comment)
        len_delim -= len(line)
        delim = self._reserved_chars_comment*len_delim
        if len(delim) < 3:
            if line.startswith('%!bespon'):
                if self.state.start_lineno != 1:
                    raise erring.ParseError('Encountered "%!bespon", but not on first line', self.state.traceback)
                elif self.state.indent or not self.state.at_line_start:
                    raise erring.ParseError('Encountered "%!bespon", but not at beginning of line', self.state.traceback)
                elif line[len('%!bespon'):].rstrip(self._whitespace_str):
                    raise erring.ParseError('Encountered unknown parser directives: "{0}"'.format(line.rstrip(self._newline_chars_str)), self.state.traceback)
                else:
                    line = self._parse_line_goto_next()
            else:
                line = self._parse_line_goto_next()
        else:
            line = line[len(delim):]
            indent = self.state.indent
            end_delim_re = self._closing_delim_re_dict[delim]
            text_after_opening_delim = line.lstrip(self._whitespace_str)
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
                            if text_after_opening_delim or line[:m.start()].lstrip(self._indents_str):
                                raise erring.ParseError('In multi-line comments, opening delimiter may not be followed by anything and closing delimiter may not be preceded by anything', self.state.traceback)
                        line = line[m.end():].lstrip(self._whitespace_str)
                        if not self.state.inline and len(m.group(0)) == len(delim):
                            if self.state.start_lineno == self.state.end_lineno and self.state.at_line_start:
                                if line[:1] and line[:1] != '%':
                                    raise erring.ParseError('Inline comment is causing indeterminate indenation in non-inline syntax', self.state.traceback)
                            elif self.state.start_lineno != self.state.end_lineno:
                                if line[:1] and line[:1] != '%':
                                    raise erring.ParseError('Inline comment is causing indeterminate indenation in non-inline syntax', self.state.traceback)
                                self._parse_line_continue_next()
                                if line[:1] and line[:1] == '%':
                                    self.state.at_line_start == True
                        else:
                            self._parse_line_continue_next()
                        break
                line = self._parse_line_get_next()
                if line is None:
                    raise erring.ParseError('Never found end of multi-line comment', self.state.traceback)
                if not empty_line and not line.lstrip(self._unicode_whitespace_str):
                    # Important to test this after the first lookahead, since
                    # the remainder of the starting line could very well be
                    # whitespace
                    empty_line = True
                if not line.startswith(indent) and line.lstrip(self._whitespace_str):
                    raise erring.ParseError('Indentation error in multi-line comment', self.state.traceback)
        while line is not None and not line.lstrip(self._whitespace_str):
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
            s = self._unicodefilter.unicode_to_ascii_newlines(s)
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
