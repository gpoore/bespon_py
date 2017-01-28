# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, Geoffrey M. Poore
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
from . import astnodes




class Ast(object):
    '''
    Abstract representation of data during parsing, before final, full
    conversion into standard Python objects.

    If the `full_ast` setting is not used (default), then all scalar objects
    (string, int, float, bool, None, bytes, etc.) will be represented as
    final Python objects at this stage.  Otherwise, they will be represented
    with astnodes.ScalarNode.

    The `.pythonize()` method converts the abstract representation into final
    Python objects.  By default, it overwrites the abstract representation
    in this process; this can be avoided with a keyword argument.
    '''
    __slots__ = ['state', 'source', 'root', 'pos', 'unresolved_nodes']

    def __init__(self, state, full_ast=False):
        self.state = state
        if full_ast not in (True, False):
            raise TypeError
        self.full_ast = full_ast
        self.source = astnodes.SourceNode(state)
        self.pos = self.source
        self._unresolved_nodes = []

    def __bool__(self):
        if len(self.source) > 0 and len(self.root) > 0:
            return True
        return False

    if sys.version_info.major == 2:
        __nonzero__ = __bool__


    def append_scalar_key(self, obj, DictlikeNode=astnodes.DictlikeNode):
        '''
        Append a scalar key.  In inline mode, append at the current position.
        In non-inline mode, if the key's indentation does not match that of
        the current position, try to find an appropriate pre-existing dict or
        attempt to create one.
        '''
        if not obj.resolved:
            self._unresolved_nodes.append(obj)
        # Temp variables must be used with care; otherwise, don't update self
        pos = self.pos
        if obj.inline or obj.external_indent == pos.indent or pos.basetype == 'tag':
            pos.check_append_scalar_key(obj, self.full_ast)
        elif len(obj.external_indent) > len(pos.indent):
            next_pos = DictlikeNode(obj)
            self._unresolved_nodes.append(next_pos)
            pos.check_append_collection(next_pos)
            next_pos.check_append_scalar_key(obj)
            self.pos = next_pos
        else:
            root = self.root
            while pos is not root and len(obj.external_indent) < len(pos.indent):
                if pos.basetype == 'dict':
                    if not pos:
                        raise erring.ParseError('A non-inline dict-like object cannot be empty', pos)
                    if pos.awaiting_val:
                        raise erring.ParseError('A dict-like object ended before a key-value pair was completed', pos)
                elif pos.basetype == 'list':
                    # No need to check for an empty list, since an empty
                    # non-inline list would necessarily be open
                    if pos.open:
                        raise erring.ParseError('A list-like object ended before an expected value was added', pos)
                else:  # other invalid location
                    raise erring.IndentationError(obj)
                parent = pos.parent
                parent.last_lineno = pos.last_lineno
                parent.last_column = pos.last_column
                pos = parent
            # No need to check whether final pos is a dict; if a dict should
            # exist at this level, it must have already been created before
            # the lower level of the AST was reached.
            pos.check_append_scalar_key(obj, self.full_ast)
            self.pos = pos


    def append_scalar_val(self, obj):
        '''
        Append a scalar value.
        '''
        # Unlike the key case, there is never a need to walk up the AST.
        # If the value is inline, it should be added.  Otherwise, if it is a
        # dict value, the key would have taken care of the AST, and if it is
        # a list element, the list opener `*` would have done the same thing.
        if not obj.resolved:
            self._unresolved_nodes.append(obj)
        self.pos.append_scalar_val(obj)


    def append_collection(self, obj):
        '''
        Append a collection.
        '''
        # There is never a need to climb to a higher level in the AST.  In
        # inline mode, that would be taken care of by closing delimiters.
        # In non-inline mode, keys and list element openers `*` serve an
        # analogous function.
        self._unresolved_nodes.append(obj)
        self.pos.check_append_collection(obj)
        self.pos = obj


    def start_dict_inline(self, DictlikeNode=astnodes.DictlikeNode):
        '''
        Start an inline dict-like object at "{".
        '''
        state = self.state
        if not state.inline:
            state.inline = True
            state.inline_indent = state.indent
        obj = DictlikeNode(state)
        obj.open = True
        self.append_collection(obj)


    def end_dict_inline(self):
        '''
        End an inline dict-like object at "}".
        '''
        pos = self.pos
        state = self.state
        if not state.inline:
            raise erring.ParseError('Cannot end a dict-like object with "}" when not in inline mode', state)
        if pos.basetype != 'dict':
            raise erring.ParseError('Encountered "}" when there is no dict-like object to end', state)
        if not state.indent.startswith(state.inline_indent):
            raise erring.IndentationError(state)
        if pos.awaiting_val:
            raise erring.ParseError('Missing value; a dict-like object cannot end with an incomplete key-value pair', state)
        pos = pos.parent
        state.inline = pos.inline
        self.pos = pos


    def start_list_inline(self, ListlikeNode=astnodes.ListlikeNode):
        '''
        Start an inline list-like object at "[".
        '''
        state = self.state
        if not state.inline:
            state.inline = True
            state.inline_indent = state.indent
        obj = ListlikeNode(state)
        obj.open = True
        self.append_collection(obj)


    def end_list_inline(self):
        '''
        End an inline list-like object at "]".
        '''
        pos = self.pos
        state = self.state
        if not state.inline:
            raise erring.ParseError('Cannot end a list-like object with "]" when not in inline mode', state)
        if pos.basetype != 'list':
            raise erring.ParseError('Encountered "]" when there is no list-like object to end', state)
        if not state.indent.startswith(state.inline_indent):
            raise erring.IndentationError(state)
        pos = pos.parent
        state.inline = pos.inline
        self.pos = pos


    def start_tag(self):
        '''
        Start a tag at "(".
        '''
        raise NotImplementedError


    def end_tag(self):
        '''
        End a tag at ")>".
        '''
        raise NotImplementedError


    def open_collection_inline(self):
        '''
        Open a collection object in inline syntax after ",".
        '''
        pos = self.pos
        state = self.state
        if state.inline and state.indent.startswith(state.inline_indent) and not pos.open:
            pos.open = True
            pos.last_lineno = state.last_lineno
            pos.last_column = state.last_column
        elif pos.basetype == 'tag' and state.indent.startswith(pos.indent) and not pos.open:
            pos.open = True
            pos.last_lineno = state.last_lineno
            pos.last_column = state.last_column
        else:
            if not state.inline and pos.basetype != 'tag':
                raise erring.ParseError('Object separator "," is not allowed outside tags and inline collections', state)
            if state.inline and not state.indent.startswith(state.inline_indent):
                raise erring.IndentationError(state)
            if not state.inline and pos.basetype == 'tag' and not state.indent.startswith(pos.indent):
                raise erring.IndentationError(state)
            raise erring.ParseError('Misplaced object separator "," or missing object/key-value pair', state)


    def open_list_non_inline(self, ListlikeNode=astnodes.ListlikeNode):
        '''
        Open a list-like object in non-inline syntax at `*`.
        '''
        state = self.state
        if state.inline or not state.at_line_start:
            # The `*` doesn't change `.at_line_start` status, but that
            # doesn't mean that additional checks are needed; whenever
            # an `*` is encountered, there is a check for a following,
            # invalid `*`.
            raise erring.ParseError('Invalid location to begin a non-inline list element', state)
        # Temp variables must be used with care; otherwise, don't update self
        pos = self.pos
        if state.indent == pos.indent and pos.basetype == 'list':
            if state.next_tag is not None:
                raise erring.ParseError('Unused tag', state.next_tag)
            if pos.open:
                raise erring.ParseError('Cannot start a new list element while the previous element is missing', state)
            pos.open = True
            pos.last_lineno = state.last_lineno
            pos.last_column = state.last_column
        elif len(state.indent) >= len(pos.indent):
            next_pos = ListlikeNode(state)
            self._unresolved_nodes.append(next_pos)
            next_pos.open = True
            self.append_collection(next_pos)
            self.pos = next_pos
        else:
            if state.next_tag is not None:
                raise erring.ParseError('Unused tag', state.next_tag)
            root = self.root
            while pos is not root and len(state.indent) < len(pos.indent):
                if pos.basetype == 'dict':
                    if not pos:
                        raise erring.ParseError('A non-inline dict-like object cannot be empty', pos)
                    if pos.awaiting_val:
                        raise erring.ParseError('A dict-like object ended before a key-value pair was completed', pos)
                elif pos.basetype == 'list':
                    # No need to check for an empty list, since an empty
                    # non-inline list would necessarily be open
                    if pos.open:
                        raise erring.ParseError('A list-like object ended before an expected value was added', pos)
                else:  # other invalid location
                    raise erring.ParseError('Misplaced "*"; cannot start a list element here', state)
                parent = pos.parent
                parent.last_lineno = pos.last_lineno
                parent.last_column = pos.last_column
                pos = parent
            if state.indent == pos.indent and pos.basetype == 'list':
                # Don't need to check for a list that is already open.
                # If the list were already open, would still be at the level
                # of the list in the AST, and never would have ended up here,
                # needing to climb up the AST.
                pos.open = True
                pos.last_lineno = state.last_lineno
                pos.last_column = state.last_column
            else:
                raise erring.ParseError('Misplaced "*"; cannot start a list element here', state)
            self.pos = pos




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
