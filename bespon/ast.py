# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


# pylint: disable=C0301

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import sys
from . import erring
from . import astnodes
from . import grammar


OPEN_NONINLINE_LIST = grammar.LIT_GRAMMAR['open_noninline_list']




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
    __slots__ = ['state', 'full_ast', 'max_nesting_depth',
                 'source', 'root', 'pos',
                 '_unresolved_nodes', '_in_tag_cached_pos']

    def __init__(self, state, full_ast=False, max_nesting_depth=100):
        self.state = state
        if full_ast not in (True, False):
            raise TypeError
        self.full_ast = full_ast
        if not isinstance(max_nesting_depth, int):
            raise TypeError
        self.max_nesting_depth = max_nesting_depth
        self.source = astnodes.SourceNode(state)
        self.pos = self.source
        self._unresolved_nodes = []
        self._in_tag_cached_pos = None

    def __bool__(self):
        if len(self.source) > 0 and len(self.root) > 0:
            return True
        return False

    if sys.version_info.major == 2:
        __nonzero__ = __bool__


    def set_root(self):
        root = astnodes.RootNode(self.state)
        self.root = root
        self._unresolved_nodes.append(root)
        self.pos.check_append_root(root)
        self.pos = root


    def append_doc_comment(self, obj):
        state = self.state
        state.next_doc_comment = obj


    def append_scalar_key(self, obj, DictlikeNode=astnodes.DictlikeNode):
        '''
        Append a scalar key.

        In inline mode, append at the current position.  In non-inline mode,
        if the key's indentation does not match that of the current position,
        try to find an appropriate pre-existing dict or attempt to create one.
        '''
        if not obj.resolved:
            raise erring.ParseError('Invalid dict key; keys must be resolvable at the location where they are used', obj)
        # Temp variables must be used with care; otherwise, don't update self
        pos = self.pos
        if obj.inline or (obj.external_indent == pos.indent and pos.basetype == 'dict'):
            pos.check_append_scalar_key(obj)
        elif len(obj.external_indent) >= len(pos.indent):
            # Object will be in a dict, so its `.nesting_depth` is incorrect
            # and must be updated.  This won't be reflected in state, so
            # update that directly.
            obj.nesting_depth += 1
            self.state.nesting_depth += 1
            dict_obj = DictlikeNode(obj)
            # No need to set `.open=True`; it is irrelevant in non-inline mode
            self.append_collection(dict_obj)
            dict_obj.check_append_scalar_key(obj)
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
            pos.check_append_scalar_key(obj)
            self.state.nesting_depth = pos.nesting_depth
            self.pos = pos


    def append_scalar_val(self, obj):
        '''
        Append a scalar value.
        '''
        # Unlike the key case, there is never a need to climb up the AST.
        # If the value is inline, it should be added.  Otherwise, if it is a
        # dict value, the key would have taken care of the AST, and if it is
        # a list element, the list opener `*` would have done the same thing.
        if not obj.resolved:
            self._unresolved_nodes.append(obj)
        self.pos.check_append_scalar_val(obj)


    def append_collection(self, obj):
        '''
        Append a collection.
        '''
        # There is never a need to climb to a higher level in the AST.  In
        # inline mode, that would be taken care of by closing delimiters.
        # In non-inline mode, keys and list element openers `*` can trigger
        # climbing the AST based on indentation.
        if obj.nesting_depth > self.max_nesting_depth:
            raise erring.ParseError('Max nesting depth for collections was exceeded; max depth = {0}'.format(self.max_nesting_depth), obj)
        self._unresolved_nodes.append(obj)
        self.pos.check_append_collection(obj)
        self.pos = obj



    def start_inline_dict(self, DictlikeNode=astnodes.DictlikeNode):
        '''
        Start an inline dict-like object at "{".
        '''
        state = self.state
        if not state.inline:
            state.inline = True
            state.inline_indent = state.indent
        state.nesting_depth += 1
        dict_obj = DictlikeNode(state)
        dict_obj.open = True
        self.append_collection(dict_obj)


    def end_inline_dict(self):
        '''
        End an inline dict-like object at "}".
        '''
        pos = self.pos
        state = self.state
        if not state.inline:
            raise erring.ParseError('Cannot end a dict-like object with "}" when not in inline mode', state)
        if not state.indent.startswith(state.inline_indent):
            raise erring.IndentationError(state)
        if pos.basetype != 'dict':
            raise erring.ParseError('Encountered "}" when there is no dict-like object to end', state)
        if pos.awaiting_val:
            raise erring.ParseError('Missing value; a dict-like object cannot end with an incomplete key-value pair', state)
        pos.last_lineno = state.last_lineno
        pos.last_column = state.last_column
        pos = pos.parent
        state.inline = pos.inline
        state.nesting_depth -= 1
        self.pos = pos


    def start_inline_list(self, ListlikeNode=astnodes.ListlikeNode):
        '''
        Start an inline list-like object at "[".
        '''
        state = self.state
        if not state.inline:
            state.inline = True
            state.inline_indent = state.indent
        state.nesting_depth += 1
        list_obj = ListlikeNode(state)
        list_obj.open = True
        self.append_collection(list_obj)


    def end_inline_list(self):
        '''
        End an inline list-like object at "]".
        '''
        pos = self.pos
        state = self.state
        if not state.inline:
            raise erring.ParseError('Cannot end a list-like object with "]" when not in inline mode', state)
        if not state.indent.startswith(state.inline_indent):
            raise erring.IndentationError(state)
        if pos.basetype != 'list':
            raise erring.ParseError('Encountered "]" when there is no list-like object to end', state)
        pos.last_lineno = state.last_lineno
        pos.last_column = state.last_column
        pos = pos.parent
        state.inline = pos.inline
        state.nesting_depth -= 1
        self.pos = pos


    def start_tag(self, TagNode=astnodes.TagNode):
        '''
        Start a tag at "(".
        '''
        # Don't need to check for an existing, unused tag, because the parser
        # handles that case when the end of a tag is encountered, by looking
        # ahead.  Don't need to check indent, because that will be checked
        # when the tagged object is appended to the AST.
        state = self.state
        if state.in_tag:
            raise erring.ParseError('Cannot nest tags; encountered "(" before a previous tag was complete', state, state.next_tag)
        self._in_tag_cached_pos = self.pos
        external_inline = state.inline
        if not external_inline:
            state.inline = True
            state.inline_indent = state.indent
        # Tags aren't collections, so don't increment `.nesting_depth`
        tag_node = TagNode(state, external_inline)
        self.pos = tag_node


    def end_tag(self):
        '''
        End a tag at ")>".
        '''
        pos = self.pos
        state = self.state
        # Don't need to check state.inline, because being in a tag guarantees
        # inline mode, unlike dicts and lists.
        if not state.indent.startswith(state.inline_indent):
            raise erring.IndentationError(state)
        if pos.basetype != 'tag':
            raise erring.ParseError('Encountered ")>" when there is no tag to end', state)
        if pos.awaiting_val:
            raise erring.ParseError('Missing value; a tag cannot end with an incomplete key-value pair', state)
        state.inline = pos.external_inline
        state.next_tag = pos
        # Tags aren't collections, so don't decrement `.nesting_depth`
        self.pos = self._in_tag_cached_pos
        state.in_tag = False


    def open_inline_collection(self):
        '''
        Open a collection object in inline syntax after ",".
        '''
        pos = self.pos
        state = self.state
        if state.inline and state.indent.startswith(state.inline_indent) and not pos.open:
            pos.open = True
            pos.last_lineno = state.last_lineno
            pos.last_column = state.last_column
        else:
            if not state.inline:
                raise erring.ParseError('Object separator "," is not allowed outside tags and inline collections', state)
            if not state.indent.startswith(state.inline_indent):
                raise erring.IndentationError(state)
            raise erring.ParseError('Misplaced object separator "," or missing object/key-value pair', state)


    def open_noninline_list(self, ListlikeNode=astnodes.ListlikeNode):
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
            if pos.open:
                raise erring.ParseError('Cannot start a new list element while the previous element is missing', state)
            pos.open = True
            pos.last_lineno = state.last_lineno
            pos.last_column = state.last_column
        elif len(state.indent) >= len(pos.indent):
            state.nesting_depth += 1
            list_obj = ListlikeNode(state)
            list_obj.open = True
            self.append_collection(list_obj)
        else:
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
            state.nesting_depth = pos.nesting_depth
            self.pos = pos


    def append_key_path(self, kp_obj,
                        DictlikeNode=astnodes.DictlikeNode,
                        open_noninline_list=OPEN_NONINLINE_LIST):
        '''
        Create the AST node corresponding to the elements in a key path.
        '''
        state = self.state
        kp_obj_0 = kp_obj[0]
        if kp_obj_0 == open_noninline_list:
            raise NotImplementedError
        else:
            if kp_obj_0 in self.pos:
                pos = self.pos[kp_obj_0]
            else:
                self.append_scalar_key(kp_obj_0)
                pos = self.pos
        for kp_elem in kp_obj[1:]:
            if kp_elem in pos:
                pos = pos[kp_elem]
            else:
                dict_obj = DictlikeNode(kp_obj, keypath_traversable=True)
                dict_obj.open = True
                pos.check_append_collection(dict_obj, in_key_path_after_element1=True)
                pos = dict_obj
                pos.check_append_scalar_key(kp_elem)
        self.pos = pos









    def finalize(self):
        '''
        Check AST for errors and return to root node.
        '''
        # Don't need to check for unused `state.next_tag`, since tag parsing
        # involves lookahead to ensure a valid, following object.  A dangling
        # tag would already have triggered an error during tag parsing.
        if self.pos is not self.root:
            state = self.state
            # Temp variables must be used with care; otherwise, don't update self
            pos = self.pos
            root = self.root
            while pos is not root:
                if pos.inline:
                    if pos.basetype == 'dict':
                        raise erring.ParseError('An inline dict-like object never ended; missing "}"', pos)
                    elif pos.basetype == 'list':
                        raise erring.ParseError('An inline list-like object never ended; missing "]"', pos)
                    elif pos.basetype == 'tag':
                        raise erring.ParseError('A tag never ended; missing ")>" and any necessary following object', pos)
                    else:
                        raise erring.Bug('An inline object with unexpected basetype {0} never ended'.format(pos.basetype), pos)
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
                    raise erring.Bug('Object with unexpected basetype {0} never ended'.format(pos.basetype), pos)
                parent = pos.parent
                parent.last_lineno = pos.last_lineno
                parent.last_column = pos.last_column
                pos = parent
            state.nesting_depth = pos.nesting_depth
            self.pos = pos
        self.resolve()


    def resolve(self):
        '''
        Convert all unresolved nodes into standard Python types.
        '''
        # Unresolved nodes are visited in the opposite order from which they
        # were created.  Later nodes are lower in the AST, so under normal
        # circumstances they can and must be resolved first.
        #
        # Objects with alias or copy tags can't be resolved until the
        # targeted object has been resolved.  Similarly, collections
        # configured with init, default, or recmerge have to wait to be
        # resolved until the targeted collection(s) are resolved.  Multiple
        # passes through the remaining unresolved objects may be required.
        #
        # Circular or otherwise complex aliases can exist in or between
        # collections.  These require special care.  If a collection contains
        # a reference to itself, the collection must be created with a
        # placeholder element, which is then replaced with the alias to the
        # collection that now exists.  This can be complicated by the use
        # of immutable collections.  A truly immutable collection cannot
        # contain an alias to itself, unless that alias is inside a mutable
        # collection.  This complicates the resolving process for immutable
        # objects, and requires a check for unresolvable situations.
        type_data = self.state.type_data
        unresolved_nodes = list(reversed(self._unresolved_nodes))
        while unresolved_nodes:
            initial_unresolved_count = len(unresolved_nodes)
            remaining_nodes = []
            for node in unresolved_nodes:
                if node.unresolved_child_count > 0:
                    remaining_nodes.append(node)
                elif node.basetype == 'tag':
                    # #### Check
                    node.resolved = True
                elif node.tag is None or node.tag.resolved:
                    # #### Fix for other types
                    if node.basetype == 'dict':
                        node.final_val = type_data[node.basetype].parser((k.final_val, v.final_val) for k, v in node.items())
                        node.parent.unresolved_child_count -= 1
                    elif node.basetype == 'list':
                        node.final_val = type_data[node.basetype].parser(x.final_val for x in node)
                        node.parent.unresolved_child_count -= 1
                    elif node.basetype == 'root':
                        node.final_val = node[0].final_val
                    else:
                        raise NotImplementedError
                else:
                    remaining_nodes.append(node)
            unresolved_nodes = remaining_nodes
            if not len(unresolved_nodes) < initial_unresolved_count and unresolved_nodes:
                raise erring.ParseError('Could not resolve all nodes', self.state)
        # #### make finalize do all resolving except pythonize?
