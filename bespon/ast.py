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


END_INLINE_DICT = grammar.LIT_GRAMMAR['end_inline_dict']
END_INLINE_LIST = grammar.LIT_GRAMMAR['end_inline_list']
START_TAG = grammar.LIT_GRAMMAR['start_tag']
END_TAG_WITH_SUFFIX = grammar.LIT_GRAMMAR['end_tag_with_suffix']
INLINE_ELEMENT_SEPARATOR = grammar.LIT_GRAMMAR['inline_element_separator']
OPEN_NONINLINE_LIST = grammar.LIT_GRAMMAR['open_noninline_list']
PATH_SEPARATOR = grammar.LIT_GRAMMAR['path_separator']
ASSIGN_KEY_VAL = grammar.LIT_GRAMMAR['assign_key_val']




class Ast(object):
    '''
    Abstract representation of data during parsing, before final, full
    conversion into standard Python objects.
    '''
    __slots__ = ['state', 'full_ast', 'max_nesting_depth',
                 'source', 'root', 'pos', 'section_pos',
                 '_unresolved_nodes', '_in_tag_cached_pos',
                 '_first_section', '_last_section']

    def __init__(self, state, max_nesting_depth=100):
        self.state = state
        self.full_ast = state.full_ast
        if not isinstance(max_nesting_depth, int):
            raise TypeError
        if max_nesting_depth < 1:
            raise ValueError
        self.max_nesting_depth = max_nesting_depth
        self.source = astnodes.SourceNode(state)
        self.root = self.source.root
        self.pos = self.root
        self.section_pos = None
        self._unresolved_nodes = [self.root]
        self._in_tag_cached_pos = None
        self._first_section = None
        self._last_section = None

    def __bool__(self):
        if len(self.root) > 0:
            return True
        return False

    if sys.version_info.major == 2:
        __nonzero__ = __bool__


    def _noninline_climb_to_indent(self, state_or_scalar_obj, pos):
        '''
        Starting at `pos`, climb to a higher level in that AST with less
        indentation that is potentially compatible with `state_or_scalar_obj`.
        For use in non-inline mode.
        '''
        try:
            len_indent = len(state_or_scalar_obj.external_indent)
        except AttributeError:
            len_indent = len(state_or_scalar_obj.indent)
        section_pos = self.section_pos
        while (len_indent < len(pos.indent) or pos.key_path_parent is not None) and pos is not section_pos:
            if pos.basetype == 'dict':
                if not pos:
                    raise erring.ParseError('A non-inline dict-like object cannot be empty', pos)
                if pos._awaiting_val:
                    raise erring.ParseError('A dict-like object ended before a key-value pair was completed', pos)
            elif pos.basetype == 'list':
                # No need to check for an empty list, since an empty
                # non-inline list would necessarily be open
                if pos._open:
                    raise erring.ParseError('A list-like object ended before an expected value was added', pos)
            elif pos.basetype == 'root':
                break
            else:  # other invalid location
                raise erring.IndentationError(state_or_scalar_obj)
            parent = pos.parent
            parent.last_lineno = pos.last_lineno
            parent.last_colno = pos.last_colno
            if pos._key_path_scope is not None:
                for kp_elem in pos._key_path_scope:
                    kp_elem._key_path_traversable = False
                pos._key_path_scope = None
            pos = parent
        self.pos = pos
        return pos


    def _section_climb(self, pos):
        '''
        Starting at `pos`, climb to the highest level in the AST below root,
        which is where sections may be created.
        '''
        self.section_pos = None
        root = self.root
        while pos.parent is not root:
            if pos.basetype == 'dict':
                if not pos:
                    raise erring.ParseError('A non-inline dict-like object cannot be empty', pos)
                if pos._awaiting_val:
                    raise erring.ParseError('A dict-like object ended before a key-value pair was completed', pos)
            elif pos.basetype == 'list':
                # No need to check for an empty list, since an empty
                # non-inline list would necessarily be open
                if pos._open:
                    raise erring.ParseError('A list-like object ended before an expected value was added', pos)
            else:  # other invalid location
                raise erring.IndentationError(scalar_obj)
            parent = pos.parent
            parent.last_lineno = pos.last_lineno
            parent.last_colno = pos.last_colno
            if pos._key_path_scope is not None:
                for kp_elem in pos._key_path_scope:
                    kp_elem._key_path_traversable = False
                pos._key_path_scope = None
            pos = parent
        self.pos = pos
        return pos


    def _key_path_climb(self, pos):
        '''
        Starting at `pos`, which was created by a key path, climb to the
        higher level in that AST corresponding to the top of the key path.
        '''
        key_path_parent = pos.key_path_parent
        last_lineno = pos.last_lineno
        last_colno = pos.last_colno
        if pos.basetype == 'dict':
            if pos._awaiting_val:
                raise erring.ParseError('A dict-like object ended before a key-value pair was completed', pos)
        elif pos.basetype == 'list':
            if pos._open:
                raise erring.ParseError('A list-like object ended before an expected value was added', pos)
        else:  # other invalid location
            raise erring.Bug('Unexpected key path element', pos)
        while pos is not key_path_parent:
            parent = pos.parent
            parent.last_lineno = last_lineno
            parent.last_colno = last_colno
            pos = parent
        self.pos = pos
        return pos


    def append_scalar_key(self, assign_key_val=ASSIGN_KEY_VAL,
                          DictlikeNode=astnodes.DictlikeNode):
        '''
        Append a scalar key.

        In inline mode, append at the current position.  In non-inline mode,
        if the key's indentation does not match that of the current position,
        try to find an appropriate pre-existing dict or attempt to create one.
        '''
        # Checks could be avoided by treating any scalar that isn't a valid
        # key as a value as soon as it is parsed, rather than caching it like
        # a potentially valid key.  The current approach gives more
        # informative error messages than would be possible with that
        # approach.
        state = self.state
        scalar_obj = state.next_scalar
        if state.first_lineno != scalar_obj.last_lineno:
            if not (state.inline and state.first_lineno == scalar_obj.last_lineno + 1):
                raise erring.ParseError('Key-value assignment "{0}" must be on the same line as the key in non-inline mode, and no later than the following line in inline mode'.format(assign_key_val), state)
            if state.last_line_comment_lineno == scalar_obj.last_lineno:
                raise erring.ParseError('Key-value assignment "{0}" cannot be separated from its key by a line comment'.format(assign_key_val), state)
        state.next_scalar = None
        state.next_cache = False
        scalar_obj.assign_key_val_lineno = state.first_lineno
        scalar_obj.assign_key_val_colno = state.first_colno
        if scalar_obj.basetype == 'key_path':
            self._append_key_path(scalar_obj)
            return
        if scalar_obj.basetype != 'scalar' or scalar_obj.implicit_type == 'unquoted_string':
            raise erring.ParseError('Unquoted strings and alias types are not valid keys for dict-like objects', scalar_obj)
        # Temp variables must be used with care; otherwise, don't update self
        pos = self.pos
        if scalar_obj.inline:
            pos.check_append_scalar_key(scalar_obj)
        elif pos is self.section_pos:
            # If in a section, need to create a dict immediately
            # below it.  If section content is indented, there is no
            # danger of accidentally creating an extra dict due to
            # improper key indentation, because in that case the section
            # dict wouldn't be open.
            dict_obj = DictlikeNode(scalar_obj)
            self._append_key_path_collection(dict_obj)
            dict_obj.check_append_scalar_key(scalar_obj)
        elif scalar_obj.external_indent == pos.indent and pos.basetype == 'dict':
            if pos.key_path_parent is not None:
                pos = self._key_path_climb(pos)
            pos.check_append_scalar_key(scalar_obj)
        elif len(scalar_obj.external_indent) >= len(pos.indent):
            if not ((pos.basetype == 'dict' and pos._awaiting_val) or pos._open):
                raise erring.ParseError('Cannot start a new dict-like object here; check for incorrect indentation or unintended values', scalar_obj)
            dict_obj = DictlikeNode(scalar_obj)
            # No need to set `._open=True`; irrelevant in non-inline mode.
            self._append_collection(dict_obj)
            dict_obj.check_append_scalar_key(scalar_obj)
        else:
            pos = self._noninline_climb_to_indent(scalar_obj, pos)
            if not pos.basetype == 'dict':
                raise erring.IndentationError(scalar_obj)
            pos.check_append_scalar_key(scalar_obj)


    def append_scalar_val(self):
        '''
        Append a scalar value.
        '''
        # Unlike the key case, there is never a need to climb up the AST.
        # If the value is inline, it should be added.  Otherwise, if it is a
        # dict value, the key would have taken care of the AST, and if it is
        # a list element, the list opener `*` would have done the same thing.
        state = self.state
        scalar_obj = state.next_scalar
        state.next_scalar = None
        state.next_cache = False
        if scalar_obj.implicit_type == 'key_path':
            raise erring.ParseError('Key paths are only allowed as dict keys, not as values', scalar_obj)
        if not scalar_obj._resolved:
            self._unresolved_nodes.append(scalar_obj)
        if self.section_pos is not self.pos:
            self.pos.check_append_scalar_val(scalar_obj)
        else:
            self.pos.check_append_key_path_scalar_val(scalar_obj)


    def _append_collection(self, collection_obj):
        '''
        Append a collection.
        '''
        # There is never a need to climb to a higher level in the AST.  In
        # inline mode, that would be taken care of by closing delimiters.
        # In non-inline mode, keys and list element openers `*` can trigger
        # climbing the AST based on indentation.
        self._unresolved_nodes.append(collection_obj)
        if self.section_pos is not self.pos:
            self.pos.check_append_collection(collection_obj)
        else:
            self.pos.check_append_key_path_collection(collection_obj)
        # Wait to check nesting depth until after appending, because nesting
        # depth is inherited from parent, and parent is set during appending.
        if collection_obj.nesting_depth > self.max_nesting_depth:
            raise erring.ParseError('Max nesting depth for collections was exceeded; max depth = {0}'.format(self.max_nesting_depth), collection_obj)
        self.pos = collection_obj


    def _append_key_path_collection(self, collection_obj):
        '''
        Append a collection created within a key path.
        '''
        # There is never a need to climb to a higher level in the AST.  In
        # inline mode, that would be taken care of by closing delimiters.
        # In non-inline mode, keys and list element openers `*` can trigger
        # climbing the AST based on indentation.
        self._unresolved_nodes.append(collection_obj)
        self.pos.check_append_key_path_collection(collection_obj)
        if collection_obj.nesting_depth > self.max_nesting_depth:
            raise erring.ParseError('Max nesting depth for collections was exceeded; max depth = {0}'.format(self.max_nesting_depth), collection_obj)
        self.pos = collection_obj



    def start_inline_dict(self, DictlikeNode=astnodes.DictlikeNode):
        '''
        Start an inline dict-like object at "{".
        '''
        state = self.state
        if not state.inline:
            state.inline = True
            state.inline_indent = state.indent
        dict_obj = DictlikeNode(state)
        dict_obj._open = True
        self._append_collection(dict_obj)


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
        if pos.basetype != 'dict':
            raise erring.ParseError('Encountered "{0}" when there is no dict-like object to end'.format(END_INLINE_DICT), state)
        if pos._awaiting_val:
            raise erring.ParseError('Missing value; a dict-like object cannot end with an incomplete key-value pair', state)
        if pos.key_path_parent is None:
            pos.last_lineno = state.last_lineno
            pos.last_colno = state.last_colno
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


    def start_inline_list(self, ListlikeNode=astnodes.ListlikeNode):
        '''
        Start an inline list-like object at "[".
        '''
        state = self.state
        if not state.inline:
            state.inline = True
            state.inline_indent = state.indent
        list_obj = ListlikeNode(state)
        list_obj._open = True
        self.append_collection(list_obj)


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
        if pos.basetype != 'list':
            raise erring.ParseError('Encountered "{0}" when there is no list-like object to end'.format(END_INLINE_LIST), state)
        if pos.key_path_parent is None:
            pos.last_lineno = state.last_lineno
            pos.last_colno = state.last_colno
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
        external_inline = state.inline
        if not external_inline:
            state.inline = True
            state.inline_indent = state.indent
        tag_node = TagNode(state, external_inline)
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
        if pos.basetype != 'tag':
            raise erring.ParseError('Encountered "{0}" when there is no tag to end'.format(END_TAG_WITH_SUFFIX), state)
        if pos._awaiting_val:
            raise erring.ParseError('Missing value; a tag cannot end with an incomplete key-value pair', state)
        state.inline = pos.external_inline
        state.next_tag = pos
        self.pos = self._in_tag_cached_pos
        state.in_tag = False


    def open_inline_collection(self):
        '''
        Open a collection object in inline syntax after ",".
        '''
        pos = self.pos
        state = self.state
        if state.inline and state.indent.startswith(state.inline_indent) and not pos._open and (pos.basetype == 'list' or not pos._awaiting_val):
            if pos.key_path_parent is not None:
                key_path_parent = pos.key_path_parent
                last_lineno = state.last_lineno
                last_colno = state.last_colno
                while pos is not key_path_parent:
                    pos.last_lineno = last_lineno
                    pos.last_colno = last_colno
                    pos = pos.parent
                self.pos = pos
            pos.last_lineno = state.last_lineno
            pos.last_colno = state.last_colno
            pos._open = True
        else:
            if not state.inline:
                raise erring.ParseError('Object separator "{0}" is not allowed outside tags and inline collections'.format(INLINE_ELEMENT_SEPARATOR), state)
            if not state.indent.startswith(state.inline_indent):
                raise erring.IndentationError(state)
            raise erring.ParseError('Misplaced object separator "{0}" or missing object/key-value pair'.format(INLINE_ELEMENT_SEPARATOR), state)


    def open_noninline_list(self, ListlikeNode=astnodes.ListlikeNode):
        '''
        Open a list-like object in non-inline syntax at `*`.
        '''
        state = self.state
        if state.inline or not state.at_line_start:
            # The `*` doesn't change `.at_line_start` status, unlike other
            # tokens.
            raise erring.ParseError('Invalid location to begin a non-inline list element', state)
        # Temp variables must be used with care; otherwise, don't update self
        pos = self.pos
        if pos is self.section_pos:
            list_obj = ListlikeNode(state)
            list_obj._open = True
            self._append_key_path_collection(list_obj)
        elif state.indent == pos.indent and pos.basetype == 'list':
            if pos._open:
                raise erring.ParseError('Cannot start a new list element while a previous element is missing', state)
            pos._open = True
            pos.last_lineno = state.last_lineno
            pos.last_colno = state.last_colno
        elif len(state.indent) >= len(pos.indent):
            list_obj = ListlikeNode(state)
            list_obj._open = True
            self._append_collection(list_obj)
        else:
            pos = self._noninline_climb_to_indent(state, pos)
            if state.indent == pos.indent and pos.basetype == 'list':
                # Don't need to check for a list that is already open.
                # If the list were already open, would still be at the level
                # of the list in the AST, and never would have ended up here,
                # needing to climb up the AST.
                pos._open = True
                pos.last_lineno = state.last_lineno
                pos.last_colno = state.last_colno
            else:
                raise erring.ParseError('Misplaced "{0}"; cannot start a list element here'.format(OPEN_NONINLINE_LIST), state)


    def _append_key_path(self, kp_obj,
                         open_noninline_list=OPEN_NONINLINE_LIST,
                         DictlikeNode=astnodes.DictlikeNode,
                         ListlikeNode=astnodes.ListlikeNode):
        '''
        Create the AST node corresponding to the elements in a key path.
        '''
        state = self.state
        if state.in_tag:
            raise erring.ParseError('Key paths are not valid in tags')
        pos = self.pos
        if kp_obj.inline:
            initial_pos = pos
        elif pos is self.section_pos:
            dict_obj = DictlikeNode(kp_obj)
            self._append_collection(dict_obj)
            initial_pos = dict_obj
        elif kp_obj.external_indent == pos.indent and pos.basetype == 'dict':
            if pos.key_path_parent is not None:
                pos = self._key_path_climb(pos)
            initial_pos = pos
        elif len(kp_obj.external_indent) >= len(pos.indent):
            if not ((pos.basetype == 'dict' and pos._awaiting_val) or pos._open):
                raise erring.ParseError('Cannot start a new dict-like object here; check for incorrect indentation or unintended values', kp_obj)
            dict_obj = DictlikeNode(kp_obj)
            self._append_collection(dict_obj)
            initial_pos = dict_obj
        else:
            pos = self._noninline_climb_to_indent(kp_obj, pos)
            if not pos.basetype == 'dict':
                raise erring.IndentationError(kp_obj)
            initial_pos = pos
        pos = initial_pos
        for kp_elem, next_kp_elem in zip(kp_obj[:-1], kp_obj[1:]):
            if pos.basetype == 'dict' and kp_elem in pos:
                pos = pos[kp_elem]
                key_obj = pos.index
                if key_obj.key_path_occurances is None:
                    key_obj.key_path_occurances = [kp_elem]
                else:
                    key_obj.key_path_occurances.append(kp_elem)
                if not pos._key_path_traversable:
                    raise erring.ParseError('Key path cannot pass through a pre-existing node that was created outside of the current scope and is now locked', kp_elem, pos)
            else:
                pos.check_append_key_path_scalar_key(kp_elem)
                if next_kp_elem == open_noninline_list:
                    collection_obj = ListlikeNode(kp_obj, key_path_parent=initial_pos, _key_path_traversable=True)
                else:
                    collection_obj = DictlikeNode(kp_obj, key_path_parent=initial_pos, _key_path_traversable=True)
                self._append_key_path_collection(collection_obj)
                pos = collection_obj
                if initial_pos._key_path_scope is None:
                    initial_pos._key_path_scope = [collection_obj]
                else:
                    initial_pos._key_path_scope.append(collection_obj)
        if kp_obj[-1] == open_noninline_list:
            pos._open = True
        else:
            pos.check_append_key_path_scalar_key(kp_obj[-1])
        self.pos = pos


    def start_section(self, section_obj,
                      open_noninline_list=OPEN_NONINLINE_LIST,
                      ListlikeNode=astnodes.ListlikeNode,
                      DictlikeNode=astnodes.DictlikeNode):
        '''
        Start a section.
        '''
        state = self.state
        if state.inline:
            # This covers the case of being in a tag
            raise erring.ParseError('Sections are not allowed in inline mode', section_obj)
        if not section_obj.at_line_start or section_obj.indent != '':
            raise erring.ParseError('Sections must begin at the start of a line, with no indentation', section_obj)
        pos = self.pos
        root = self.root
        if self._first_section is None:
            self._first_section = section_obj
        elif self._first_section._end_delim != self._last_section._end_delim:
            if self._first_section._end_delim:
                raise erring.ParseError('Cannot start a section when a previous section is missing an end delimiter; section end delimiters must be used for all sections, or not at all', section_obj, self._last_section)
            else:
                raise erring.ParseError('Cannot start a section when a previous section has an end delimiter, unlike preceding sections; section end delimiters must be used for all sections, or not at all', section_obj, self._last_section)
        self._last_section = section_obj
        if pos is root:
            if section_obj.scalar is not None and section_obj.scalar.final_val == open_noninline_list:
                obj = ListlikeNode(section_obj)
            else:
                obj = DictlikeNode(section_obj)
            self._append_collection(obj)
            initial_pos = obj
        elif pos.parent is root:
            initial_pos = pos
            if initial_pos.external_indent != '':
                raise erring.ParseError('Sections must begin at the start of a line, with no indentation, but this is inconsistent with an existing top-level object', section_obj, initial_pos)
        else:
            pos = self._section_climb(pos)
            initial_pos = pos
            if initial_pos.external_indent != '':
                raise erring.ParseError('Sections must begin at the start of a line, with no indentation, but this is inconsistent with an existing top-level object', section_obj, initial_pos)
        pos = initial_pos
        if section_obj.key_path is not None:
            kp_obj = section_obj.key_path
            for kp_elem, next_kp_elem in zip(kp_obj[:-1], kp_obj[1:]):
                if pos.basetype != 'dict':
                    raise erring.ParseError('Key path is incompatible with previously created object', kp_elem, pos)
                if kp_elem in pos:
                    pos = pos[kp_elem]
                    key_obj = pos.index
                    if key_obj.key_path_occurances is None:
                        key_obj.key_path_occurances = [kp_elem]
                    else:
                        key_obj.key_path_occurances.append(kp_elem)
                    if not pos._key_path_traversable:
                        raise erring.ParseError('Key path cannot pass through a pre-existing node that was created outside of the current scope and is now locked', kp_elem, pos)
                else:
                    pos.check_append_key_path_scalar_key(kp_elem)
                    if next_kp_elem == open_noninline_list:
                        collection_obj = ListlikeNode(kp_obj, key_path_parent=initial_pos, _key_path_traversable=True)
                    else:
                        collection_obj = DictlikeNode(kp_obj, key_path_parent=initial_pos, _key_path_traversable=True)
                    self._append_key_path_collection(collection_obj)
                    pos = collection_obj
            if kp_obj[-1] == open_noninline_list:
                pos._open = True
            else:
                pos.check_append_key_path_scalar_key(kp_obj[-1])
            self.pos = pos
        elif section_obj.scalar.final_val != open_noninline_list:
            pos.check_append_key_path_scalar_key(section_obj.scalar)
        else:
            if pos.basetype != 'list':
                raise erring.ParseError('Key path is incompatible with previously created object', section_obj.scalar, pos)
            pos._open = True
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
        self._section_climb(self.pos)


    def finalize(self):
        '''
        Check AST for errors and return to root node.
        '''
        if self._first_section is not None and self._first_section is not self._last_section:
            if self._first_section._end_delim != self._last_section._end_delim:
                if self._first_section._end_delim:
                    raise erring.ParseError('The last section is missing an end delimiter; section end delimiters must be used for all sections, or not at all', self._last_section)
                else:
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
                if pos.basetype == 'dict':
                    raise erring.ParseError('An inline dict-like object never ended; missing "{0}"'.format(END_INLINE_DICT), pos)
                if pos.basetype == 'list':
                    raise erring.ParseError('An inline list-like object never ended; missing "{0}"'.format(END_INLINE_LIST), pos)
                if pos.basetype == 'tag':
                    raise erring.ParseError('A tag never ended; missing "{0}" and any necessary following object'.format(END_TAG_WITH_SUFFIX), pos)
                raise erring.ParseError('An inline object with unexpected basetype {0} never ended'.format(pos.basetype), pos)
            if not state.source_inline:
                raise erring.Bug('Data that started in non-inline mode ended in inline mode', state)
        elif pos is not root:
            while pos is not root:
                if pos.basetype == 'dict':
                    if not pos:
                        raise erring.ParseError('A non-inline dict-like object cannot be empty', pos)
                    if pos._awaiting_val:
                        raise erring.ParseError('A dict-like object ended before a key-value pair was completed', pos)
                elif pos.basetype == 'list':
                    # No need to check for an empty list, since an empty
                    # non-inline list would necessarily be open
                    if pos._open:
                        raise erring.ParseError('A list-like object ended before an expected value was added', pos)
                else:  # other invalid location
                    raise erring.Bug('Object with unexpected basetype {0} never ended'.format(pos.basetype), pos)
                parent = pos.parent
                parent.last_lineno = pos.last_lineno
                parent.last_colno = pos.last_colno
                if pos._key_path_scope is not None:
                    for kp_elem in pos._key_path_scope:
                        kp_elem._key_path_traversable = False
                    pos._key_path_scope = None
                pos = parent
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
                if node._unresolved_dependency_count > 0:
                    remaining_nodes.append(node)
                elif node.basetype == 'tag':
                    # #### Check
                    node._resolved = True
                elif node.tag is None or node.tag._resolved:
                    # #### Fix for other types
                    if node.basetype == 'dict':
                        node.final_val = type_data[node.basetype].parser((k.final_val, v.final_val) for k, v in node.items())
                        node.parent._unresolved_dependency_count -= 1
                    elif node.basetype == 'list':
                        node.final_val = type_data[node.basetype].parser(x.final_val for x in node)
                        node.parent._unresolved_dependency_count -= 1
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
