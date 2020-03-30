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
import collections
from . import erring
from . import astnodes
from . import grammar


END_INLINE_DICT = grammar.LIT_GRAMMAR['end_inline_dict']
END_INLINE_LIST = grammar.LIT_GRAMMAR['end_inline_list']
START_TAG = grammar.LIT_GRAMMAR['start_tag']
END_TAG_WITH_SUFFIX = grammar.LIT_GRAMMAR['end_tag_with_suffix']
INLINE_ELEMENT_SEPARATOR = grammar.LIT_GRAMMAR['inline_element_separator']
OPEN_INDENTATION_LIST = grammar.LIT_GRAMMAR['open_indentation_list']
ASSIGN_KEY_VAL = grammar.LIT_GRAMMAR['assign_key_val']




class Ast(object):
    '''
    Abstract representation of data during parsing, before final, full
    conversion into standard Python objects.
    '''
    __slots__ = ['state', 'full_ast', 'max_nesting_depth',
                 'source', 'source_lines', 'root', 'pos', 'section_pos',
                 'scalar_nodes', 'line_comments', 'empty_default',
                 '_unresolved_collection_nodes',
                 '_unresolved_alias_nodes',
                 '_in_tag_cached_pos', '_in_tag_cached_doc_comment',
                 '_first_section', '_last_section',
                 '_labels']

    def __init__(self, state, max_nesting_depth, empty_default=None):
        self.state = state
        self.full_ast = state.full_ast
        self.max_nesting_depth = max_nesting_depth
        self.empty_default = empty_default
        self.source = astnodes.SourceNode(state)
        self.root = self.source.root
        self.pos = self.root
        self.section_pos = None
        if self.full_ast:
            self.scalar_nodes = []
            self.line_comments = []
        self._unresolved_collection_nodes = []
        self._unresolved_alias_nodes = []
        self._in_tag_cached_pos = None
        self._in_tag_cached_doc_comment = None
        self._first_section = None
        self._last_section = None
        self._labels = {}

    def __bool__(self):
        if len(self.root) > 0:
            return True
        return False

    if sys.version_info.major == 2:
        __nonzero__ = __bool__


    def _indentation_climb_to_indent(self, state_or_scalar_node, pos, len=len):
        '''
        Starting at `pos`, climb to a higher level in the AST with less
        indentation that is potentially compatible with `state_or_scalar_node`.
        For use in indentation-style syntax.
        '''
        # `state` has no `external_indent`, but most AST nodes do
        try:
            len_indent = len(state_or_scalar_node.external_indent)
        except AttributeError:
            len_indent = len(state_or_scalar_node.indent)
        root = self.root
        parent = pos.parent
        section_pos = self.section_pos
        while (len_indent < len(pos.indent) or pos.key_path_parent is not None) and pos is not section_pos and parent is not root:
            if pos._open:
                if pos.implicit_type == 'dict':
                    if not pos:
                        raise erring.ParseError('An indentation-style dict-like object cannot be empty', pos)
                    raise erring.ParseError('A dict-like object ended before a key-value pair was completed', pos)
                # pos.implicit_type == 'list'
                raise erring.ParseError('A list-like object ended before an expected value was added', pos)
            parent.last_lineno = pos.last_lineno
            parent.last_colno = pos.last_colno
            if pos._key_path_scope is not None:
                for kp_elem in pos._key_path_scope:
                    kp_elem._key_path_traversable = False
                pos._key_path_scope = None
            pos = parent
            parent = pos.parent
        self.pos = pos
        return pos


    def _section_climb_to_root(self, pos):
        '''
        Starting at `pos`, climb to the highest level in the AST below root,
        which is where sections may be created.
        '''
        self.section_pos = None
        root = self.root
        parent = pos.parent
        while parent is not root:
            if pos._open:
                if pos.implicit_type == 'dict':
                    if not pos:
                        raise erring.ParseError('An indentation-style dict-like object cannot be empty', pos)
                    raise erring.ParseError('A dict-like object ended before a key-value pair was completed', pos)
                # pos.implicit_type == 'list'
                raise erring.ParseError('A list-like object ended before an expected value was added', pos)
            parent.last_lineno = pos.last_lineno
            parent.last_colno = pos.last_colno
            if pos._key_path_scope is not None:
                for kp_elem in pos._key_path_scope:
                    kp_elem._key_path_traversable = False
                pos._key_path_scope = None
            pos = parent
            parent = pos.parent
        self.pos = pos
        return pos


    def _key_path_climb_to_start(self, pos):
        '''
        Starting at `pos`, which was created by a key path, climb to the
        higher level in that AST corresponding to the top of the key path.
        '''
        key_path_parent = pos.key_path_parent
        last_lineno = pos.last_lineno
        last_colno = pos.last_colno
        if pos._open:
            if pos.implicit_type == 'dict':
                if not pos:
                    raise erring.ParseError('An indentation-style dict-like object cannot be empty', pos)
                raise erring.ParseError('A dict-like object ended before a key-value pair was completed', pos)
            # pos.implicit_type == 'list'
            raise erring.ParseError('A list-like object ended before an expected value was added', pos)
        while pos is not key_path_parent:
            parent = pos.parent
            parent.last_lineno = last_lineno
            parent.last_colno = last_colno
            pos = parent
        self.pos = pos
        return pos


    def append_scalar_key(self, assign_key_val=ASSIGN_KEY_VAL,
                          DictlikeNode=astnodes.DictlikeNode,
                          len=len):
        '''
        Append a scalar key.

        In inline mode, append at the current position.  In indentation-style
        syntax, if the key's indentation does not match that of the current
        position, try to find an appropriate pre-existing dict or attempt to
        create one.
        '''
        state = self.state
        scalar_node = state.next_scalar
        if state.lineno != scalar_node.last_lineno:
            if not (state.inline and state.lineno == scalar_node.last_lineno + 1):
                raise erring.ParseError('Key-value assignment "{0}" must be on the same line as the key in indentation-style syntax, and no later than the following line in inline mode'.format(assign_key_val), state)
            if state.last_line_comment_lineno == scalar_node.last_lineno:
                raise erring.ParseError('Key-value assignment "{0}" cannot be separated from its key by a line comment'.format(assign_key_val), state)
            if not state.indent.startswith(state.inline_indent):
                raise erring.IndentationError(state)
        state.next_scalar = None
        state.next_cache = False
        if state.full_ast:
            scalar_node.assign_key_val_lineno = state.lineno
            scalar_node.assign_key_val_colno = state.colno
        if scalar_node.implicit_type == 'key_path':
            self._append_key_path(scalar_node)
            return
        if not state.next_scalar_is_keyable:
            raise erring.ParseError('Object is not a valid key for a dict-like object', scalar_node)
        if scalar_node.tag is not None and scalar_node.tag.label is not None:
            raise erring.ParseError('Labeling dict keys is not supported', scalar_node)
        # Temp variables must be used with care; otherwise, don't update self
        pos = self.pos
        if scalar_node.inline:
            pos.check_append_scalar_key(scalar_node)
        elif pos is self.section_pos:
            # If in a section, need to create a dict immediately
            # below it.  If section content is indented, there is no
            # danger of accidentally creating an extra dict due to
            # improper key indentation, because in that case the section
            # dict wouldn't be open.
            dict_node = DictlikeNode(scalar_node)
            self._append_key_path_collection(dict_node)
            dict_node.check_append_scalar_key(scalar_node)
        elif scalar_node.external_indent == pos.indent and pos.implicit_type == 'dict':
            if pos.key_path_parent is not None:
                pos = self._key_path_climb_to_start(pos)
            pos.check_append_scalar_key(scalar_node)
        elif len(scalar_node.external_indent) >= len(pos.indent):
            dict_node = DictlikeNode(scalar_node)
            # No need to set `._open=True`; irrelevant in indentation-style
            # syntax.
            self._append_collection(dict_node)
            dict_node.check_append_scalar_key(scalar_node)
        else:
            pos = self._indentation_climb_to_indent(scalar_node, pos)
            pos.check_append_scalar_key(scalar_node)


    def append_scalar_val(self):
        '''
        Append a scalar value.
        '''
        # Unlike the key case, there is never a need to climb up the AST.
        # If the value is inline, it should be added.  Otherwise, if it is a
        # dict value, the key would have taken care of the AST, and if it is
        # a list element, the list opener `*` would have done the same thing.
        state = self.state
        scalar_node = state.next_scalar
        state.next_scalar = None
        state.next_cache = False
        if not scalar_node._resolved:
            self._unresolved_alias_nodes.append(scalar_node)
        if self.section_pos is not self.pos:
            self.pos.check_append_scalar_val(scalar_node)
        else:
            self.pos.check_append_key_path_scalar_val(scalar_node)


    def _append_collection(self, collection_node):
        '''
        Append a collection.
        '''
        # There is never a need to climb to a higher level in the AST.  In
        # inline mode, that would be taken care of by closing delimiters.
        # In indentation mode, keys and list element openers `*` can trigger
        # climbing the AST based on indentation.
        self._unresolved_collection_nodes.append(collection_node)
        if self.section_pos is not self.pos:
            self.pos.check_append_collection(collection_node)
        else:
            self.pos.check_append_key_path_collection(collection_node)
        # Wait to check nesting depth until after appending, because nesting
        # depth is inherited from parent, and parent is set during appending.
        if collection_node.nesting_depth > self.max_nesting_depth:
            raise erring.ParseError('Max nesting depth for collections was exceeded; max depth = {0}'.format(self.max_nesting_depth), collection_node)
        self.pos = collection_node


    def _append_key_path_collection(self, collection_node):
        '''
        Append a collection created within a key path.
        '''
        # There is never a need to climb to a higher level in the AST.  In
        # inline mode, that would be taken care of by closing delimiters.
        # In indentation mode, keys and list element openers `*` can trigger
        # climbing the AST based on indentation.
        self._unresolved_collection_nodes.append(collection_node)
        self.pos.check_append_key_path_collection(collection_node)
        if collection_node.nesting_depth > self.max_nesting_depth:
            raise erring.ParseError('Max nesting depth for collections was exceeded; max depth = {0}'.format(self.max_nesting_depth), collection_node)
        self.pos = collection_node


    def start_inline_dict(self, DictlikeNode=astnodes.DictlikeNode):
        '''
        Start an inline dict-like object at "{".
        '''
        state = self.state
        if not state.inline:
            state.inline = True
            state.inline_indent = state.indent
        # No need to check indentation, since the dict-like object inherits
        # indentation, and thus indentation will be checked when it is
        # appended to the AST.
        dict_node = DictlikeNode(state)
        dict_node._open = True
        self._append_collection(dict_node)


    def end_inline_dict(self):
        '''
        End an inline dict-like object at "}".
        '''
        pos = self.pos
        state = self.state
        if not state.inline:
            raise erring.ParseError('Cannot end a dict-like object with "{0}" when not in inline mode'.format(END_INLINE_DICT), state)
        if not state.indent.startswith(state.inline_indent):
            raise erring.IndentationError(state)
        if pos.implicit_type != 'dict':
            raise erring.ParseError('Encountered "{0}" when there is no dict-like object to end'.format(END_INLINE_DICT), state)
        if pos._awaiting_val:
            raise erring.ParseError('Missing value; a dict-like object cannot end with an incomplete key-value pair', state)
        if pos.key_path_parent is None:
            pos.last_lineno = state.lineno
            pos.last_colno = state.colno
            pos = pos.parent
            state.inline = pos.inline
            self.pos = pos
        else:
            key_path_parent = pos.key_path_parent
            last_lineno = state.last_lineno
            last_colno = state.last_colno
            while pos is not key_path_parent:
                pos.last_lineno = last_lineno
                pos.last_colno = last_colno
                pos = pos.parent
            pos.last_lineno = last_lineno
            pos.last_colno = last_colno
            for kp_elem in pos._key_path_scope:
                kp_elem._key_path_traversable = False
            pos._key_path_scope = None
            self.pos = pos.parent


    def start_inline_list(self, ListlikeNode=astnodes.ListlikeNode,
                          AliasListNode=astnodes.AliasListNode):
        '''
        Start an inline list-like object at "[".
        '''
        state = self.state
        if not state.inline:
            state.inline = True
            state.inline_indent = state.indent
        if not state.in_tag:
            list_node = ListlikeNode(state)
        else:
            list_node = AliasListNode(state)
        list_node._open = True
        self._append_collection(list_node)


    def end_inline_list(self):
        '''
        End an inline list-like object at "]".
        '''
        pos = self.pos
        state = self.state
        if not state.inline:
            raise erring.ParseError('Cannot end a list-like object with "{0}" when not in inline mode'.format(END_INLINE_LIST), state)
        if not state.indent.startswith(state.inline_indent):
            raise erring.IndentationError(state)
        if pos.implicit_type == 'list':
            if pos.key_path_parent is None:
                pos.last_lineno = state.lineno
                pos.last_colno = state.colno
                pos = pos.parent
                state.inline = pos.inline
                self.pos = pos
            else:
                key_path_parent = pos.key_path_parent
                last_lineno = state.last_lineno
                last_colno = state.last_colno
                while pos is not key_path_parent:
                    pos.last_lineno = last_lineno
                    pos.last_colno = last_colno
                    pos = pos.parent
                pos.last_lineno = last_lineno
                pos.last_colno = last_colno
                for kp_elem in pos._key_path_scope:
                    kp_elem._key_path_traversable = False
                pos._key_path_scope = None
                self.pos = pos.parent
        elif pos.implicit_type == 'alias_list':
            pos.last_lineno = state.lineno
            pos.last_colno = state.colno
            # No need to reset `.inline`; tags are always inline
            self.pos = pos.parent
        else:
            raise erring.ParseError('Encountered "{0}" when there is no list-like object to end'.format(END_INLINE_LIST), state)


    def start_tag(self, TagNode=astnodes.TagNode):
        '''
        Start a tag at "(".
        '''
        # Don't need to check indent, because that will be checked when the
        # tagged object is appended to the AST.
        state = self.state
        if state.in_tag:
            raise erring.ParseError('Cannot nest tags; encountered "{0}" before a previous tag was complete'.format(START_TAG), state, state.next_tag)
        state.in_tag = True
        self._in_tag_cached_pos = self.pos
        self._in_tag_cached_doc_comment = state.next_doc_comment
        state.next_doc_comment = None
        state.next_cache = False
        external_inline = state.inline
        if not external_inline:
            state.inline = True
            state.inline_indent = state.indent
        tag_node = TagNode(state, state.lineno, state.colno, external_inline)
        tag_node._open = True
        self.state.next_tag = tag_node
        self.pos = tag_node


    def end_tag(self):
        '''
        End a tag at ")>".
        '''
        pos = self.pos
        state = self.state
        # Don't need to check state.inline, because being in a tag guarantees
        # inline mode, unlike dicts and lists.  Don't need to worry about
        # climbing key paths, because they're invalid in tags.
        if not state.indent.startswith(state.inline_indent):
            raise erring.IndentationError(state)
        if pos.implicit_type != 'tag':
            raise erring.ParseError('Encountered "{0}" when there is no tag to end'.format(END_TAG_WITH_SUFFIX), state)
        if pos._awaiting_val:
            raise erring.ParseError('Missing value; a tag cannot end with an incomplete key-value pair', state)
        pos.last_lineno = state.lineno
        pos.last_colno = state.colno + 1
        if pos._unresolved_dependency_count == 0:
            pos._resolved = True
        else:
            self._unresolved_collection_nodes.append(pos)
        state.inline = pos.external_inline
        state.next_doc_comment = self._in_tag_cached_doc_comment
        state.next_tag = pos
        state.next_cache = True
        self.pos = self._in_tag_cached_pos
        state.in_tag = False


    def open_inline_collection(self):
        '''
        Open a collection object in inline syntax after ",".
        '''
        pos = self.pos
        state = self.state
        if state.inline and state.indent.startswith(state.inline_indent) and not pos._open:
            if not state.in_tag and pos.key_path_parent is not None:
                key_path_parent = pos.key_path_parent
                last_lineno = state.lineno
                last_colno = state.colno
                while pos is not key_path_parent:
                    pos.last_lineno = last_lineno
                    pos.last_colno = last_colno
                    pos = pos.parent
                self.pos = pos
            pos.last_lineno = state.lineno
            pos.last_colno = state.colno
            pos._open = True
        else:
            if not state.inline:
                raise erring.ParseError('Object separator "{0}" is not allowed outside tags and inline collections'.format(INLINE_ELEMENT_SEPARATOR), state)
            if not state.indent.startswith(state.inline_indent):
                raise erring.IndentationError(state)
            raise erring.ParseError('Misplaced object separator "{0}" or missing object/key-value pair'.format(INLINE_ELEMENT_SEPARATOR), state)


    def open_indentation_list(self, ListlikeNode=astnodes.ListlikeNode,
                              len=len):
        '''
        Open a list-like object in indentation-style syntax at `*`.
        '''
        state = self.state
        if state.inline or not state.at_line_start:
            # The `*` doesn't change `.at_line_start` status, unlike other
            # tokens.
            raise erring.ParseError('Invalid location to begin an indentation-style list element', state)
        # Temp variables must be used with care; otherwise, don't update self
        pos = self.pos
        if pos is self.section_pos:
            ListlikeNode(state)
            list_node._open = True
            self._append_key_path_collection(list_node)
        elif pos.implicit_type == 'list' and state.indent == pos.indent:
            if pos._open:
                raise erring.ParseError('Cannot start a new list element while a previous element is missing', state)
            pos._open = True
            pos.last_lineno = state.lineno
            pos.last_colno = state.colno
        elif len(state.indent) >= len(pos.indent):
            list_node = ListlikeNode(state)
            list_node._open = True
            self._append_collection(list_node)
        else:
            pos = self._indentation_climb_to_indent(state, pos)
            if pos.implicit_type == 'list' and state.indent == pos.indent:
                # Don't need to check for a list that is already open.
                # If the list were already open, would still be at the level
                # of the list in the AST, and never would have ended up here,
                # needing to climb up the AST.
                pos._open = True
                pos.last_lineno = state.lineno
                pos.last_colno = state.colno
            else:
                raise erring.ParseError('Misplaced "{0}"; cannot start a list element here'.format(OPEN_INDENTATION_LIST), state)


    def start_explicit_indentation_dict(self, DictlikeNode=astnodes.DictlikeNode):
        '''
        Start a dict-like object in indentation-style syntax after an explicit
        type declaration.
        '''
        dict_node = DictlikeNode(self.state)
        if self.pos is self.section_pos:
            self._append_key_path_collection(dict_node)
        else:
            self._append_collection(dict_node)


    def _append_key_path(self, kp_node,
                         open_indentation_list=OPEN_INDENTATION_LIST,
                         DictlikeNode=astnodes.DictlikeNode,
                         ListlikeNode=astnodes.ListlikeNode, len=len):
        '''
        Create the AST node corresponding to the elements in a key path.
        '''
        state = self.state
        if state.in_tag:
            raise erring.ParseError('Key paths are not valid in tags', kp_node)
        pos = self.pos
        if kp_node.inline:
            initial_pos = pos
        elif pos is self.section_pos:
            dict_node = DictlikeNode(kp_node)
            self._append_collection(dict_node)
            initial_pos = dict_node
        elif kp_node.external_indent == pos.indent and (pos.implicit_type == 'dict' or pos.key_path_parent is not None):
            if pos.key_path_parent is not None:
                pos = self._key_path_climb_to_start(pos)
            initial_pos = pos
        elif len(kp_node.external_indent) >= len(pos.indent):
            if not pos._open:
                raise erring.ParseError('Cannot start a new dict-like object here; check for incorrect indentation or unintended values', kp_node)
            dict_node = DictlikeNode(kp_node)
            self._append_collection(dict_node)
            initial_pos = dict_node
        else:
            pos = self._indentation_climb_to_indent(kp_node, pos)
            if not pos.implicit_type == 'dict':
                raise erring.IndentationError(kp_node)
            initial_pos = pos
        pos = initial_pos
        for kp_elem, next_kp_elem in zip(kp_node[:-1], kp_node[1:]):
            if pos.implicit_type == 'dict' and kp_elem.final_val in pos:
                key_node = pos.key_nodes[kp_elem.final_val]
                pos = pos[kp_elem.final_val]
                if state.full_ast:
                    if key_node.key_path_occurrences is None:
                        key_node.key_path_occurrences = [kp_elem]
                    else:
                        key_node.key_path_occurrences.append(kp_elem)
                if not pos._key_path_traversable:
                    raise erring.ParseError('Key path encountered an object that already exists, or a pre-existing node that was created outside of the current scope and is now locked', kp_elem, pos)
            else:
                pos.check_append_key_path_scalar_key(kp_elem)
                if next_kp_elem == open_indentation_list:
                    collection_node = ListlikeNode(kp_node, key_path_parent=initial_pos, _key_path_traversable=True)
                else:
                    collection_node = DictlikeNode(kp_node, key_path_parent=initial_pos, _key_path_traversable=True)
                self._append_key_path_collection(collection_node)
                pos = collection_node
                if initial_pos._key_path_scope is None:
                    initial_pos._key_path_scope = [collection_node]
                else:
                    initial_pos._key_path_scope.append(collection_node)
        if kp_node[-1] == open_indentation_list:
            if pos.implicit_type != 'list':
                raise erring.ParseError('Key path cannot open list; incompatible with pre-existing object', kp_node, pos)
            pos._open = True
        else:
            pos.check_append_key_path_scalar_key(kp_node[-1])
        self.pos = pos


    def start_section(self, section_node,
                      open_indentation_list=OPEN_INDENTATION_LIST,
                      DictlikeNode=astnodes.DictlikeNode,
                      ListlikeNode=astnodes.ListlikeNode):
        '''
        Start a section.
        '''
        state = self.state
        if state.inline:
            # This covers the case of being in a tag
            raise erring.ParseError('Sections are not allowed in inline mode', section_node)
        if not section_node.at_line_start or section_node.indent != '':
            raise erring.ParseError('Sections must begin at the start of a line, with no indentation', section_node)
        pos = self.pos
        root = self.root
        if self._first_section is None:
            self._first_section = section_node
        elif self._first_section._end_delim != self._last_section._end_delim:
            if self._first_section._end_delim:
                raise erring.ParseError('Cannot start a section when a previous section is missing an end delimiter; section end delimiters must be used for all sections, or not at all', section_node, self._last_section)
            else:
                raise erring.ParseError('Cannot start a section when a previous section has an end delimiter, unlike preceding sections; section end delimiters must be used for all sections, or not at all', section_node, self._last_section)
        self._last_section = section_node
        if pos is root:
            if section_node.key_path is not None and section_node.key_path[0] == open_indentation_list:
                collection_node = ListlikeNode(section_node)
            else:
                collection_node = DictlikeNode(section_node)
            self._append_collection(collection_node)
            initial_pos = collection_node
        elif pos.parent is root:
            initial_pos = pos
            if initial_pos.external_indent != '':
                raise erring.ParseError('Sections must begin at the start of a line, with no indentation, but this is inconsistent with an existing top-level object', section_node, initial_pos)
        else:
            pos = self._section_climb_to_root(pos)
            initial_pos = pos
            if initial_pos.external_indent != '':
                raise erring.ParseError('Sections must begin at the start of a line, with no indentation, but this is inconsistent with an existing top-level object', section_node, initial_pos)
        pos = initial_pos
        if section_node.key_path is not None:
            kp_node = section_node.key_path
            if len(kp_node) == 1:
                if pos.implicit_type != 'list':
                    raise erring.ParseError('Key path is incompatible with previously created object', section_node.scalar, pos)
                pos._open = True
            else:
                for kp_elem, next_kp_elem in zip(kp_node[:-1], kp_node[1:]):
                    if pos.implicit_type != 'dict':
                        raise erring.ParseError('Key path is incompatible with previously created object', kp_elem, pos)
                    if kp_elem.final_val in pos:
                        pos = pos[kp_elem.final_val]
                        key_node = pos.index
                        if state.full_ast:
                            if key_node.key_path_occurrences is None:
                                key_node.key_path_occurrences = [kp_elem]
                            else:
                                key_node.key_path_occurrences.append(kp_elem)
                        if not pos._key_path_traversable:
                            raise erring.ParseError('Key path cannot pass through a pre-existing node that was created outside of the current scope and is now locked', kp_elem, pos)
                    else:
                        pos.check_append_key_path_scalar_key(kp_elem)
                        if next_kp_elem == open_indentation_list:
                            collection_node = ListlikeNode(kp_node, key_path_parent=initial_pos, _key_path_traversable=True)
                        else:
                            collection_node = DictlikeNode(kp_node, key_path_parent=initial_pos, _key_path_traversable=True)
                        self._append_key_path_collection(collection_node)
                        pos = collection_node
                if kp_node[-1] == open_indentation_list:
                    pos._open = True
                else:
                    pos.check_append_key_path_scalar_key(kp_node[-1])
                self.pos = pos
        else:
            pos.check_append_key_path_scalar_key(section_node.scalar)
        self.section_pos = pos


    def end_section(self, delim):
        '''
        End a section.  Section ending delimiters are optional, but if they
        are used at all, they must be used for every section.
        '''
        if self._last_section is None:
            raise erring.ParseError('There is no section to end', self.state)
        if self._last_section.delim != delim:
            raise erring.ParseError('Section start and end delims must have the same length', self.state, self._last_section)
        self._last_section._end_delim = True
        self._section_climb_to_root(self.pos)


    def register_label(self, node):
        '''
        Register a labeled object for tracking and future alias resolution.
        '''
        label = node.tag.label
        if label in self._labels:
            raise erring.ParseError('Duplicate label "{0}"'.format(label), node.tag['label'], self._labels[label].tag['label'])
        self._labels[node.tag.label] = node


    def _resolve(self, home_alias=grammar.LIT_GRAMMAR['home_alias'],
                 self_alias=grammar.LIT_GRAMMAR['self_alias'],
                 dict=dict, list=list, set=set, reversed=reversed, len=len,
                 hasattr=hasattr):
        '''
        Convert all unresolved nodes into standard Python types.
        '''
        # Unresolved nodes are visited in the opposite order from which they
        # were created.  Later nodes are lower in the AST, so typically
        # they can and must be resolved first.
        #
        # Aliases can't be resolved until the target object is resolved,
        # unless the target object is a mutable collection.  Copying types
        # can't be resolved until the target object is resolved.  Similarly,
        # collections configured with init, default, recmerge, or extend have
        # to wait to be resolved until the target collection(s) are resolved.
        # Multiple passes through the remaining unresolved objects may be
        # required.
        #
        # Circular or otherwise complex aliases can exist in or between
        # collections.  When the collections are mutable, empty collections
        # can be created, aliases to them resolved, and then the collections
        # can have their elements added later.  Immutable collections are more
        # complicated.  A truly immutable collection cannot contain an alias
        # to itself, unless that alias is inside a mutable collection.  This
        # complicates the resolving process for immutable objects, and
        # requires a check for unresolvable situations.
        state = self.state
        data_types = state.data_types
        root = self.root
        unresolved_alias_nodes = list(reversed(self._unresolved_alias_nodes))
        unresolved_collection_nodes = list(reversed(self._unresolved_collection_nodes))
        labels = self._labels

        if not unresolved_alias_nodes:
            unresolved_count = len(unresolved_collection_nodes)

            while unresolved_collection_nodes:
                remaining_unresolved_collection_nodes = []
                for node in unresolved_collection_nodes:
                    if node._unresolved_dependency_count > 0:
                        remaining_unresolved_collection_nodes.append(node)
                    else:
                        implicit_type = node.implicit_type
                        if implicit_type == 'dict':
                            if node.tag is None or node.tag.type is None:
                                node_type = implicit_type
                            else:
                                node_type = node.tag.type
                            parser = data_types[node_type].parser
                            if parser is dict:
                                node.final_val = {k: v.final_val for k, v in node.items()}
                            else:
                                node.final_val = parser((k, v.final_val) for k, v in node.items())
                            node.parent._unresolved_dependency_count -= 1
                        elif implicit_type == 'list':
                            if node.tag is None or node.tag.type is None:
                                node_type = implicit_type
                            else:
                                node_type = node.tag.type
                            parser = data_types[node_type].parser
                            if parser is list:
                                node.final_val = [v.final_val for v in node]
                            else:
                                node.final_val = parser(v.final_val for v in node)
                            node.parent._unresolved_dependency_count -= 1
                        else:
                            raise ValueError

                remaining_unresolved_count = len(remaining_unresolved_collection_nodes)
                if remaining_unresolved_count == unresolved_count:
                    sorted_nodes = list(reversed(remaining_unresolved_collection_nodes))
                    raise erring.ParseError('Could not resolve all nodes', state, sorted_nodes)
                unresolved_count = remaining_unresolved_count
                unresolved_collection_nodes = remaining_unresolved_collection_nodes

        else:
            alias_nodes = unresolved_alias_nodes
            for node in unresolved_alias_nodes:
                target_label = node.target_label
                if target_label in labels:
                    node.target_root = labels[target_label]
                elif target_label == home_alias:
                    if root[0].implicit_type not in ('dict', 'list'):
                        # This can actually happen; for example, "$~"
                        raise erring.ParseError('Cannot alias the top level of the data structure when the top level is not a dict-like or list-like object', node, root[0])
                    node.target_root = root[0]
                elif target_label == self_alias:
                    parent = node.parent
                    parent_implicit_type = parent.implicit_type
                    if parent_implicit_type in ('dict', 'list'):
                        node.target_root = parent
                    elif parent_implicit_type == 'tag':
                        node.target_root = parent.parent
                    elif parent_implicit_type == 'alias_list':
                        node.target_root = parent.parent.parent
                    else:
                        raise ValueError
                else:
                    raise erring.ParseError('Label "{0}" was never created'.format(target_label), node)
                if node.target_path is None:
                    if node.target_root is node:
                        raise erring.ParseError('Self-referential aliases are not permitted', node)
                    node.target_node = node.target_root

            for node in unresolved_collection_nodes:
                implicit_type = node.implicit_type
                if implicit_type in ('dict', 'list'):
                    if node.tag is None or node.tag.type is None:
                        node_type = implicit_type
                    else:
                        node_type = node.tag.type
                    data_type = data_types[node_type]
                    if data_type.mutable:
                        node.final_val = data_type.parser()
                    else:
                        node.final_val = None

            unresolved_count = len(unresolved_collection_nodes) + len(unresolved_alias_nodes)
            while unresolved_alias_nodes or unresolved_collection_nodes:
                remaining_unresolved_alias_nodes = []
                remaining_unresolved_collection_nodes = []

                # Resolve alias nodes
                for node in unresolved_alias_nodes:
                    if node.target_node is None:
                        pos = node.target_root
                        awaiting_resolution = False
                        for tp_elem in node.target_path:
                            if pos.implicit_type != 'dict':
                                raise erring.ParseError('An alias path cannot pass through anything but a dict-like object', node, pos)
                            # In resolving at alias, can go through nodes that
                            # have not been resolved, as long as they do not
                            # have collection config (so that all keys are
                            # known) or so long as the collection config
                            # (but not necessarily the node itself) has been
                            # resolved (again, so that all keys are known).
                            if pos.tag is None or not pos.tag.collection_config:
                                if tp_elem in pos:
                                    pos = pos[tp_elem]
                                else:
                                    raise erring.ParseError('Alias path could not be resolved; missing path element "{0}"'.format(tp_elem), node, pos)
                            elif not pos.tag._resolved:
                                awaiting_resolution = True
                                break
                            elif tp_elem in pos.tag.collection_config_nodes:
                                pos = pos.tag.collection_config_nodes[tp_elem]
                            else:
                                raise erring.ParseError('Alias path could not be resolved; missing path element "{0}"'.format(tp_elem), node, pos)
                        if not awaiting_resolution:
                            if pos is node:
                                raise erring.ParseError('Self-referential aliases are not permitted', node)
                            node.target_node = pos
                    if node.target_node is not None:
                        target_node = node.target_node
                        if target_node._resolved or (target_node.implicit_type in ('dict', 'list') and target_node.final_val is not None):
                            node.final_val = target_node.final_val
                            node.parent._unresolved_dependency_count -= 1
                            node._resolved = True
                    if not node._resolved:
                        remaining_unresolved_alias_nodes.append(node)

                # Resolve collection nodes with no remaining dependencies
                for node in unresolved_collection_nodes:
                    if node._unresolved_dependency_count > 0:
                        remaining_unresolved_collection_nodes.append(node)
                    else:
                        implicit_type = node.implicit_type
                        if implicit_type == 'dict':
                            if node.final_val is None:
                                # if `final_val` is None, must have type
                                node_type = node.tag.type
                                parser = data_types[node_type].parser
                                if not node.tag.collection_config:
                                    node.final_val = parser({k: v.final_val for k, v in node.items()})
                                else:
                                    node.final_val = parser({k: v.final_val for k, v in node.tag.collection_config_nodes.items()})
                            elif node.tag is None or not node.tag.collection_config:
                                node.final_val.update({k: v.final_val for k, v in node.items()})
                            else:
                                node.final_val.update({k: v.final_val for k, v in node.tag.collection_config_nodes.items()})
                            node.parent._unresolved_dependency_count -= 1
                        elif implicit_type == 'list':
                            if node.final_val is None:
                                node_type = node.tag.type
                                parser = data_types[node_type].parser
                                if node.tag is None or not node.tag.collection_config:
                                    node.final_val = parser([v.final_val for v in node])
                                else:
                                    node.final_val = parser([v.final_val for v in node.tag.collection_config_nodes])
                            elif node.tag is None or not node.tag.collection_config:
                                final_val = node.final_val
                                if hasattr(final_val, 'extend'):
                                    final_val.extend([v.final_val for v in node])
                                else:
                                    final_val.update([v.final_val for v in node])
                            else:
                                final_val = node.final_val
                                if hasattr(final_val, 'extend'):
                                    final_val.extend([v.final_val for v in node.tag.collection_config_nodes])
                                else:
                                    final_val.update([v.final_val for v in node.tag.collection_config_nodes])
                            node.parent._unresolved_dependency_count -= 1
                        elif implicit_type == 'tag':
                            if node.collection_config:
                                parent = node.parent
                                parent_implicit_type = parent.implicit_type
                                if parent_implicit_type == 'dict':
                                    self._resolve_dict_config(parent, node)
                                elif parent_implicit_type == 'list':
                                    self._resolve_list_config(parent, node)
                                else:
                                    raise TypeError
                            node.parent._unresolved_dependency_count -= 1
                        elif implicit_type == 'alias_list':
                            # Doesn't need a `final_val`
                            node.parent._unresolved_dependency_count -= 1
                        else:
                            raise ValueError
                        node._resolved = True

                remaining_unresolved_count = len(remaining_unresolved_alias_nodes) + len(remaining_unresolved_collection_nodes)
                if remaining_unresolved_count == unresolved_count:
                    sorted_nodes = list(reversed(remaining_unresolved_alias_nodes)) + list(reversed(remaining_unresolved_collection_nodes))
                    if remaining_unresolved_alias_nodes:
                        raise erring.ParseError('Could not resolve all aliases', state, sorted_nodes)
                    raise erring.ParseError('Could not resolve all collections', state, sorted_nodes)
                unresolved_alias_nodes = remaining_unresolved_alias_nodes
                unresolved_collection_nodes = remaining_unresolved_collection_nodes
                unresolved_count = remaining_unresolved_count

            if not state.circular_references:
                # This keeps track of which nodes have already been checked to
                # improve performance
                cleared_ids = set()
                for node in alias_nodes:
                    new_ids = set()
                    if self._circular_references_exist(node, new_ids, cleared_ids):
                        raise erring.ParseError('Circular references were encountered but are not enabled (circular_references=False)', node)
                    cleared_ids.update(new_ids)

        if root._unresolved_dependency_count == 0:
            if root:
                root.final_val = root[0].final_val
                root._resolved = True
            elif self.empty_default is not None:
                if state.full_ast:
                    raise NotImplementedError('There was no data to load; keyword argument "empty_default" is not supported for roundtrip use', state)
                try:
                    root.final_val = self.empty_default()
                except Exception as e:
                    raise erring.ParseError('Failed to use "empty_default" to create default value for empty data:\n{0}'.format(e), state)
                root._resolved = True
            else:
                if state.full_ast:
                    raise erring.ParseError('There was no data to load', state)
                raise erring.ParseError('There was no data to load; consider using "empty_default"', state)
        else:
            raise erring.ParseError('Failed to resolved root node', state)


    def _circular_references_exist(self, node, new_ids, cleared_ids,
                                   reference_check_implicit_types=set(['alias', 'dict', 'list']),
                                   id=id, any=any):
        '''
        Check for circular references as a result of aliases.
        '''
        implicit_type = node.implicit_type
        if implicit_type not in reference_check_implicit_types:
            return False
        if implicit_type == 'alias':
            return self._circular_references_exist(node.target_node, new_ids, cleared_ids)
        id_node = id(node)
        if id_node in new_ids:
            return True
        if id_node in cleared_ids:
            return False
        new_ids.update((id_node,))
        tag = node.tag
        if tag is None or not tag.collection_config:
            node_nodes = node
        else:
            node_nodes = tag.collection_config_nodes
        if implicit_type == 'dict':
            return any(self._circular_references_exist(v, new_ids, cleared_ids) for v in node_nodes.values())
        if implicit_type == 'list':
            return any(self._circular_references_exist(v, new_ids, cleared_ids) for v in node_nodes)
        raise ValueError


    def _resolve_dict_config(self, dict_node, dict_tag,
                             OrderedDict=collections.OrderedDict):
        '''
        Resolve a dict-like node with collection configuration.
        '''
        config_nodes = OrderedDict()
        if 'init' in dict_tag:
            init_aliases = dict_tag['init']
            if init_aliases.implicit_type == 'alias':
                init_aliases = (init_aliases,)
            for init_alias in init_aliases:
                target_node = init_alias.target_node
                if target_node.implicit_type != 'dict':
                    raise erring.ParseError('Alias type is incompatible with dict-like object', init_alias, target_node)
                target_tag = target_node.tag
                if target_tag is None or not target_tag.collection_config:
                    target_node_nodes = target_node
                else:
                    target_node_nodes = target_tag.collection_config_nodes
                for k, v in target_node_nodes.items():
                    if k in config_nodes:
                        for a in init_aliases:
                            if a.target_node.tag is None or not a.tag.collection_config:
                                if k in a.target_node:
                                    other_alias = a
                                    break
                            else:
                                if k in a.tag.collection_config_nodes:
                                    other_alias = a
                                    break
                        raise erring.ParseError('Duplicate keys in init are prohibited', init_alias, other_alias)
                    config_nodes[k] = v
        if 'recmerge' not in dict_tag:
            for k, v in dict_node.items():
                if k in config_nodes:
                    for a in init_aliases:
                        if a.target_node.tag is None or not a.tag.collection_config:
                            if k in a.target_node:
                                alias = a
                                break
                        else:
                            if k in a.tag.collection_config_nodes:
                                alias = a
                                break
                    raise erring.ParseError('Duplicating keys provided by init is prohibited', dict_node.key_nodes[k], alias)
                config_nodes[k] = v
        else:
            raise NotImplementedError
        if 'default' in dict_tag:
            default_aliases = dict_tag['default']
            if default_aliases.implicit_type == 'alias':
                default_aliases = (default_aliases,)
            for default_alias in default_aliases:
                target_node = default_alias.target_node
                if target_node.implicit_type != 'dict':
                    raise erring.ParseError('Alias type is incompatible with dict-like object', default_alias, target_node)
                target_tag = target_node.tag
                if target_tag is None or not target_tag.collection_config:
                    target_node_nodes = target_node
                else:
                    target_node_nodes = target_tag.collection_config_nodes
                for k, v in target_node_nodes.items():
                    if k not in config_nodes:
                        config_nodes[k] = v
        dict_tag.collection_config_nodes = config_nodes


    def _resolve_list_config(self, list_node, list_tag):
        '''
        Resolve a list-like node with collection configuration.
        '''
        config_nodes = []
        if 'init' in list_tag:
            init_aliases = list_tag['init']
            if init_aliases.implicit_type == 'alias':
                init_aliases = (init_aliases,)
            for init_alias in init_aliases:
                target_node = init_alias.target_node
                if target_node.implicit_type != 'list':
                    raise erring.ParseError('Alias type is incompatible with dict-like object', init_alias, target_node)
                target_tag = target_node.tag
                if target_tag is None or not target_tag.collection_config:
                    config_nodes.extend(target_node)
                else:
                    config_nodes.extend(target_tag.collection_config_nodes)
        config_nodes.extend(list_node)
        if 'extend' in list_tag:
            extend_aliases = list_tag['extend']
            if extend_aliases.implicit_type == 'alias':
                extend_aliases = (extend_aliases,)
            for extend_alias in extend_aliases:
                target_node = extend_alias.target_node
                if target_node.implicit_type != 'list':
                    raise erring.ParseError('Alias type is incompatible with dict-like object', extend_alias, target_node)
                target_tag = target_node.tag
                if target_tag is None or not target_tag.collection_config:
                    config_nodes.extend(target_node)
                else:
                    config_nodes.extend(target_tag.collection_config_nodes)
        list_tag.collection_config_nodes = config_nodes


    def finalize(self):
        '''
        Check AST for errors and return to root node.
        '''
        if self._first_section is not None and self._first_section is not self._last_section:
            if self._first_section._end_delim != self._last_section._end_delim:
                if self._first_section._end_delim:
                    raise erring.ParseError('The last section is missing an end delimiter; section end delimiters must be used for all sections, or not at all', self._last_section)
                raise erring.ParseError('The last section has an end delimiter, unlike preceding sections; section end delimiters must be used for all sections, or not at all', self._last_section)
        # Temp variables must be used with care; otherwise, don't update self
        state = self.state
        pos = self.pos
        root = self.root
        if state.next_scalar:
            self.append_scalar_val()
        if state.next_cache:
            raise erring.ParseError('Data ended before a tag or doc comment was resolved', state, unresolved_cache=True)
        if pos.inline:
            if pos is not root:
                if pos.implicit_type == 'dict':
                    raise erring.ParseError('An inline dict-like object never ended; missing "{0}"'.format(END_INLINE_DICT), pos)
                if pos.implicit_type == 'list':
                    raise erring.ParseError('An inline list-like object never ended; missing "{0}"'.format(END_INLINE_LIST), pos)
                if pos.implicit_type == 'tag':
                    raise erring.ParseError('A tag never ended; missing "{0}" and any necessary following object'.format(END_TAG_WITH_SUFFIX), pos)
                raise erring.ParseError('An inline object with unexpected implicit type {0} never ended'.format(pos.implicit_type), pos)
            if not state.source_inline:
                raise erring.Bug('Data that started in indentation-style syntax ended in inline mode', state)
        elif pos is not root:
            while pos is not root:
                if pos._open:
                    if pos.implicit_type == 'dict':
                        if not pos:
                            raise erring.ParseError('An indentation-style dict-like object cannot be empty', pos)
                        raise erring.ParseError('A dict-like object ended before a key-value pair was completed', pos)
                    # pos.implicit_type == 'list'
                    raise erring.ParseError('A list-like object ended before an expected value was added', pos)
                parent = pos.parent
                parent.last_lineno = pos.last_lineno
                parent.last_colno = pos.last_colno
                if pos._key_path_scope is not None:
                    for kp_elem in pos._key_path_scope:
                        kp_elem._key_path_traversable = False
                    pos._key_path_scope = None
                pos = parent
            self.pos = pos
        self._resolve()
        # Update source with final locations
        self.source.last_lineno = state.lineno
        self.source.last_colno = state.colno
