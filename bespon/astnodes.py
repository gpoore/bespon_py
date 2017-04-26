# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#

'''
Abstract syntax tree (AST) nodes.
'''


# pylint: disable=C0301

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import collections
import itertools
from . import grammar
from . import erring


OPEN_INDENTATION_LIST = grammar.LIT_GRAMMAR['open_indentation_list']
INLINE_ELEMENT_SEPARATOR = grammar.LIT_GRAMMAR['inline_element_separator']
PATH_SEPARATOR = grammar.LIT_GRAMMAR['path_separator']


# Key path nodes need to process their raw content into individual scalars.
# This involves checking scalar values for reserved words.  All permutations
# of reserved words are generated and put in a set for this purpose.  This
# avoids the overhead of using a regex.  The float reserved words are excluded
# from valid values, to be consistent with numeric float values being
# excluded from key paths.
_reserved_words = [grammar.LIT_GRAMMAR[k] for k in ('none_type', 'bool_true', 'bool_false', 'infinity_word', 'not_a_number_word')]
_reserved_word_patterns = set([''.join(perm) for word in _reserved_words for perm in itertools.product(*zip(word.lower(), word.upper()))])
_key_path_reserved_word_vals = {grammar.LIT_GRAMMAR['none_type']: None,
                                grammar.LIT_GRAMMAR['bool_true']: True,
                                grammar.LIT_GRAMMAR['bool_false']: False}
_reserved_word_types = {grammar.LIT_GRAMMAR['none_type']: 'none',
                        grammar.LIT_GRAMMAR['bool_true']: 'bool',
                        grammar.LIT_GRAMMAR['bool_false']: 'bool'}




_node_common_slots = ['_state',
                      'indent', 'at_line_start',
                      'inline', 'inline_indent',
                      'first_lineno', 'first_colno',
                      'last_lineno', 'last_colno',
                      'external_indent',
                      'external_at_line_start',
                      'external_first_lineno',
                      'doc_comment', 'tag', 'extra_dependents',
                      '_resolved', 'final_val']

_node_collection_slots = ['nesting_depth', 'parent', 'index',
                          'key_path_parent', '_key_path_traversable',
                          '_key_path_scope',
                          '_open',
                          '_unresolved_dependency_count']




class SourceNode(object):
    '''
    The highest-level node in the AST, representing the string, file, or
    stream in which data is embedded.

    In some cases, it would be possible to collapse the functionality of the
    source node and the root node into a single node.  The two are separated
    because this makes the handling of a tag for the root node more parallel
    with normal tags (the tag is external to the node).  Having a source
    node also makes it convenient to distinguish between where bespon content
    begins and ends (source), versus where the actual data begins and ends
    (root).  For example, there may be comments before or after the data.
    '''
    basetype = 'source'

    __slots__ = ['source_name', 'source_include_depth',
                 'source_initial_nesting_depth', 'nesting_depth',
                 'full_ast',
                 'indent', 'at_line_start', 'inline', 'inline_indent',
                 'first_lineno', 'first_colno', 'last_lineno', 'last_colno',
                 'root']

    def __init__(self, state):
        self.source_name = state.source_name
        self.source_include_depth = state.source_include_depth
        self.source_initial_nesting_depth = state.source_initial_nesting_depth
        self.nesting_depth = state.source_initial_nesting_depth
        self.full_ast = state.full_ast

        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = state.first_lineno
        self.first_colno = state.first_colno
        self.last_lineno = state.last_lineno
        self.last_colno = state.last_colno

        self.root = RootNode(self)




class RootNode(list):
    '''
    Lowest level in the AST except for the source node.  A list subclass that
    must ultimately contain only a single element.
    '''
    basetype = 'root'

    __slots__ = ['source_name', 'tag', 'end_tag',
                 '_unresolved_dependency_count',
                 'nesting_depth', 'parent',
                 'key_path_parent', '_key_path_scope',
                 '_open', '_resolved', 'final_val',
                 'indent', 'at_line_start', 'inline', 'inline_indent',
                 'first_lineno', 'first_colno',
                 'last_lineno', 'last_colno']

    def __init__(self, source, list=list):
        list.__init__(self)

        self.source_name = source.source_name
        self.tag = None
        self.end_tag = None
        self._unresolved_dependency_count = 0
        self.nesting_depth = source.source_initial_nesting_depth
        self.parent = source
        self.key_path_parent = None
        self._key_path_scope = None
        self._open = True
        self._resolved = False

        self.indent = source.indent
        self.at_line_start = source.at_line_start
        self.inline = source.inline
        self.inline_indent = source.inline_indent
        self.first_lineno = source.first_lineno
        self.first_colno = source.first_colno
        self.last_lineno = source.last_lineno
        self.last_colno = source.last_colno


    def check_append_scalar_val(self, obj, len=len):
        if len(self) == 1:
            raise erring.ParseError('Only a single scalar or collection object is allowed at root level', obj)
        if not obj.external_indent.startswith(self.indent):
            raise erring.IndentationError(obj)
        if obj._resolved:
            self.append(obj)
            self._resolved = True
        else:
            obj.parent = self
            obj.index = len(self)
            self.append(obj)
            self._unresolved_dependency_count += 1
        if self.tag is None:
            self.indent = obj.indent
            self.at_line_start = obj.at_line_start
            self.first_lineno = obj.first_lineno
            self.first_colno = obj.first_colno
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno


    def check_append_collection(self, obj, len=len):
        if len(self) == 1:
            raise erring.ParseError('Only a single scalar or collection object is allowed at root level', obj)
        if not obj.external_indent.startswith(self.indent):
            raise erring.IndentationError(obj)
        obj.parent = self
        obj.index = len(self)
        obj.nesting_depth = self.nesting_depth + 1
        self.append(obj)
        self._unresolved_dependency_count += 1
        if self.tag is None:
            self.indent = obj.indent
            self.at_line_start = obj.at_line_start
            self.first_lineno = obj.first_lineno
            self.first_colno = obj.first_colno
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno




def _set_tag_doc_comment_externals(self, state, len=len):
    '''
    When there are doc comments or tags, set them and determine external
    attributes.  This is shared by all AST nodes below root level.
    Incorporating it into individual node `__init__()` would be possible,
    but would risk logic not staying in sync.
    '''
    doc_comment_obj = state.next_doc_comment
    state.next_doc_comment = None
    tag_obj = state.next_tag
    state.next_tag = None
    state.next_cache = False
    self.doc_comment = doc_comment_obj
    self.tag = tag_obj

    # If there is no tag or doc comment, the external appearance of the object
    # is identical to that of the object itself; that case is handled in
    # individual `__init__()` since it is simple and avoids overhead.
    # Otherwise, the external appearance is based on the doc comment, or the
    # tag in its absence.  There is no need to perform indentation checks for
    # the external appearance, since these will be done during appending to
    # the AST.  The rules for cases when a doc comment or a tag is not at the
    # start of a line in indentation-style syntax will allow for things that
    # are less visually pleasing than might be desired.  However, the tradeoff
    # is that the rules are simple, relatively intuitive, and minimal while
    # still preventing ambiguity.
    if tag_obj is None:
        if doc_comment_obj.inline:
            if not self.indent.startswith(doc_comment_obj.inline_indent):
                raise erring.IndentationError(self)
        elif doc_comment_obj.at_line_start:
            if not self.at_line_start:
                raise erring.ParseError('In non-inline mode, a doc comment that starts at the beginning of a line cannot be followed immediately by the start of another object; a doc comment cannot set the indentation level', doc_comment_obj, self)
            if doc_comment_obj.indent != self.indent:
                raise erring.ParseError('Inconsistent indentation between doc comment and object', doc_comment_obj, self)
        elif self.at_line_start and (len(self.indent) <= len(doc_comment_obj.indent) or not self.indent.startswith(doc_comment_obj.indent)):
            raise erring.IndentationError(self)
        self.external_indent = doc_comment_obj.indent
        self.external_at_line_start = doc_comment_obj.at_line_start
        self.external_first_lineno = doc_comment_obj.first_lineno
    else:
        if self.basetype not in tag_obj.compatible_basetypes:
            if not self.inline and 'dict' in tag_obj.compatible_basetypes:
                erring.ParseError('Tag is incompatible with object; tags for dict-like objects in indentation-style syntax require an explicit type', tag_obj, self)
            raise erring.ParseError('Tag is incompatible with object', tag_obj, self)
        if self.basetype == 'scalar' and not self.block and (tag_obj['newline'] is not None or tag_obj['indent'] is not None):
            raise erring.ParseError('Tag has a "newline" or "indent" argument, but is applied to a scalar with no literal line breaks', tag_obj, self)
        if doc_comment_obj is None:
            if tag_obj.external_inline:
                if not self.indent.startswith(tag_obj.inline_indent):
                    raise erring.IndentationError(self)
            elif tag_obj.at_line_start:
                if not self.indent.startswith(tag_obj.indent):
                    raise erring.IndentationError(self)
            else:
                if self.at_line_start and (len(self.indent) <= len(tag_obj.indent) or not self.indent.startswith(tag_obj.indent)):
                    raise erring.IndentationError(self)
                if self.basetype in ('dict', 'list'):
                    raise erring.ParseError('The tag for a non-inline collection must be at the start of a line', tag_obj)
            self.external_indent = tag_obj.indent
            self.external_at_line_start = tag_obj.at_line_start
            self.external_first_lineno = tag_obj.first_lineno
        else:
            if doc_comment_obj.inline:
                if not tag_obj.indent.startswith(doc_comment_obj.inline_indent):
                    raise erring.IndentationError(tag_obj)
                if not self.indent.startswith(doc_comment_obj.inline_indent):
                    raise erring.IndentationError(self)
            elif doc_comment_obj.at_line_start:
                if not tag_obj.at_line_start:
                    raise erring.ParseError('In non-inline mode, a doc comment that starts at the beginning of a line cannot be followed immediately by the start of another object; a doc comment cannot set the indentation level', doc_comment_obj, tag_obj)
                if doc_comment_obj.indent != tag_obj.indent:
                    raise erring.ParseError('Inconsistent indentation between doc comment and tag', doc_comment_obj, tag_obj)
                if not self.indent.startswith(tag_obj.indent):
                    raise erring.IndentationError(self)
            elif tag_obj.at_line_start:
                if len(tag_obj.indent) <= len(doc_comment_obj.indent) or not tag_obj.indent.startswith(doc_comment_obj.indent):
                    raise erring.IndentationError(tag_obj)
                if not self.indent.startswith(tag_obj.indent):
                    raise erring.IndentationError(self)
            else:
                if self.at_line_start and (len(self.indent) <= len(tag_obj.indent) or not self.indent.startswith(tag_obj.indent)):
                    raise erring.IndentationError(self)
                if self.basetype in ('dict', 'list'):
                    raise erring.ParseError('The tag for a non-inline collection must be at the start of a line', tag_obj)
            self.external_indent = doc_comment_obj.indent
            self.external_at_line_start = doc_comment_obj.at_line_start
            self.external_first_lineno = doc_comment_obj.first_lineno
    self._resolved = False
    self.extra_dependents = None




class ScalarNode(object):
    '''
    Scalar object, including quoted (inline, block) and unquoted strings,
    none, bool, int, and float.  Also used to represent doc comments.
    '''
    basetype = 'scalar'
    __slots__ = (_node_common_slots +
                 ['delim', 'block', 'implicit_type', 'continuation_indent',
                  'raw_val', 'num_base', 'key_path', 'key_path_occurrences',
                  'assign_key_val_lineno', 'assign_key_val_colno'])

    def __init__(self, state,
                 set_tag_doc_comment_externals=_set_tag_doc_comment_externals,
                 delim=None, block=None, implicit_type=None, num_base=None):
        self.implicit_type = implicit_type
        self.block = block
        if state.full_ast:
            # Only store all details when a full AST is needed, for example,
            # for round-tripping.
            self.delim = delim
            self.num_base = num_base
            self.continuation_indent = state.continuation_indent
            self.key_path = None
            self.key_path_occurrences = None
        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = state.first_lineno
        self.first_colno = state.first_colno
        self.last_lineno = state.last_lineno
        self.last_colno = state.last_colno
        self._resolved = False
        self.extra_dependents = None
        if not state.next_cache:
            self.doc_comment = None
            self.tag = None
            self.external_indent = self.indent
            self.external_at_line_start = self.at_line_start
            self.external_first_lineno = self.first_lineno
        else:
            set_tag_doc_comment_externals(self, state)

    def __hash__(self, hash=hash):
        # The only time a scalar will need a hash is when it is used as a
        # dict key, and in that case it must already be resolved and thus
        # will have `.final_val`.
        return hash(self.final_val)

    def __eq__(self, other, hasattr=hasattr):
        # When a ScalarNode object is used as a dict key, allow access to
        # the value through the original object, another ScalarNode object
        # with the same `.final_val`, or the literal scalar value.
        return other == self.final_val or (hasattr(other, 'final_val') and other.final_val == self.final_val)




class ListlikeNode(list):
    '''
    List-like collection.
    '''
    basetype = 'list'
    __slots__ = (_node_common_slots + _node_collection_slots +
                 ['internal_indent'])

    def __init__(self, state_or_scalar_obj,
                 set_tag_doc_comment_externals=_set_tag_doc_comment_externals,
                 key_path_parent=None, _key_path_traversable=False,
                 list=list):
        list.__init__(self)

        self.key_path_parent = key_path_parent
        self._key_path_traversable = _key_path_traversable
        self._unresolved_dependency_count = 0
        self._key_path_scope = None

        state = state_or_scalar_obj._state
        self._state = state
        self.indent = state_or_scalar_obj.indent
        self.at_line_start = state_or_scalar_obj.at_line_start
        self.inline = state_or_scalar_obj.inline
        self.inline_indent = state_or_scalar_obj.inline_indent
        self.first_lineno = state_or_scalar_obj.first_lineno
        self.first_colno = state_or_scalar_obj.first_colno
        self.last_lineno = state_or_scalar_obj.last_lineno
        self.last_colno = state_or_scalar_obj.last_colno
        self._resolved = False
        self.extra_dependents = None
        self.internal_indent = None
        if _key_path_traversable:
            self.doc_comment = None
            self.tag = None
        elif not state.next_cache:
            self.doc_comment = None
            self.tag = None
            self.external_indent = self.indent
            self.external_at_line_start = self.at_line_start
            self.external_first_lineno = self.first_lineno
        else:
            set_tag_doc_comment_externals(self, state)
        self._open = False


    def check_append_scalar_key(self, obj):
        raise erring.ParseError('Cannot append a key-value pair directly to a list-like object', obj)


    def check_append_key_path_scalar_key(self, obj):
        raise erring.ParseError('Key path is incompatible with previously created list-like object', obj, self)


    def check_append_scalar_val(self, obj, len=len):
        if not self._open:
            if self.inline:
                raise erring.ParseError('Cannot append to a closed list-like object; check for a missing "{0}"'.format(INLINE_ELEMENT_SEPARATOR), obj)
            else:
                raise erring.ParseError('Cannot append to a closed list-like object; check for incorrect indentation or missing "{0}"'.format(OPEN_INDENTATION_LIST), obj)
        if self.inline:
            if not obj.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(obj)
        elif obj.external_indent != self.internal_indent:
            if self.internal_indent is None:
                if not self._key_path_traversable and (len(obj.external_indent) <= len(self.indent) or not obj.external_indent.startswith(self.indent)):
                    raise erring.IndentationError(obj)
                self.internal_indent = obj.external_indent
            else:
                raise erring.IndentationError(obj)
        if obj._resolved:
            self.append(obj)
        else:
            obj.parent = self
            obj.index = len(self)
            self.append(obj)
            self._unresolved_dependency_count += 1
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._open = False


    def check_append_key_path_scalar_val(self, obj, len=len):
        if obj._resolved:
            self.append(obj)
        else:
            obj.parent = self
            obj.index = len(self)
            self.append(obj)
            self._unresolved_dependency_count += 1
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._open = False


    def check_append_collection(self, obj, len=len):
        if not self._open:
            if self.inline:
                raise erring.ParseError('Cannot append to a closed list-like object; check for a missing "{0}"'.format(INLINE_ELEMENT_SEPARATOR), obj)
            else:
                if obj.basetype == 'dict':
                    erring.ParseError('Cannot start a new dict-like object in a closed list-like object; check for incorrect indentation or missing "{0}"'.format(OPEN_INDENTATION_LIST), scalar_obj)
                raise erring.ParseError('Cannot append to a closed list-like object; check for incorrect indentation or missing "{0}"'.format(OPEN_INDENTATION_LIST), obj)
        if self.inline:
            if not obj.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(obj)
        elif obj.external_indent != self.internal_indent:
            if self.internal_indent is None:
                if not self._key_path_traversable and (len(obj.external_indent) <= len(self.indent) or not obj.external_indent.startswith(self.indent)):
                    raise erring.IndentationError(obj)
                self.internal_indent = obj.external_indent
            else:
                raise erring.IndentationError(obj)
        obj.parent = self
        obj.index = len(self)
        obj.nesting_depth = self.nesting_depth + 1
        self.append(obj)
        self._unresolved_dependency_count += 1
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._open = False


    def check_append_key_path_collection(self, obj, len=len):
        obj.parent = self
        obj.index = len(self)
        obj.nesting_depth = self.nesting_depth + 1
        self.append(obj)
        self._unresolved_dependency_count += 1
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._open = False




class DictlikeNode(collections.OrderedDict):
    '''
    Dict-like collection.
    '''
    basetype = 'dict'
    __slots__ = (_node_common_slots + _node_collection_slots +
                 ['_awaiting_val', '_next_key'])

    def __init__(self, state_or_scalar_obj,
                 set_tag_doc_comment_externals=_set_tag_doc_comment_externals,
                 key_path_parent=None, _key_path_traversable=False,
                 OrderedDict=collections.OrderedDict):
        OrderedDict.__init__(self)

        self.key_path_parent = key_path_parent
        self._key_path_traversable = _key_path_traversable
        self._unresolved_dependency_count = 0
        self._key_path_scope = None
        self._awaiting_val = False
        self._next_key = None

        state = state_or_scalar_obj._state
        self._state = state
        self.indent = state_or_scalar_obj.indent
        self.at_line_start = state_or_scalar_obj.at_line_start
        self.inline = state_or_scalar_obj.inline
        self.inline_indent = state_or_scalar_obj.inline_indent
        self.first_lineno = state_or_scalar_obj.first_lineno
        self.first_colno = state_or_scalar_obj.first_colno
        self.last_lineno = state_or_scalar_obj.last_lineno
        self.last_colno = state_or_scalar_obj.last_colno
        self._resolved = False
        self.extra_dependents = None
        if _key_path_traversable:
            self.doc_comment = None
            self.tag = None
        elif not state.next_cache:
            self.doc_comment = None
            self.tag = None
            self.external_indent = self.indent
            self.external_at_line_start = self.at_line_start
            self.external_first_lineno = self.first_lineno
        else:
            set_tag_doc_comment_externals(self, state)
        self._open = False


    def check_append_scalar_key(self, obj):
        if self.inline:
            if not self._open:
                raise erring.ParseError('Cannot add a key to a closed object; perhaps a "{0}" is missing'.format(INLINE_ELEMENT_SEPARATOR), obj)
            if self._awaiting_val:
                raise erring.ParseError('Missing value; cannot add a key until the previous key has been given a value', obj, self._next_key)
            if not obj.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(obj)
        else:
            # Indentation dict-like objects are always open, so there is no
            # test for that.  In contrast, non-inline list-like objects
            # must be explicitly opened with `*`.
            if self._awaiting_val:
                raise erring.ParseError('Missing value; cannot add a key until the previous key has been given a value', obj, self._next_key)
            if not obj.external_at_line_start:
                raise erring.ParseError('A key must be at the start of the line in non-inline mode', obj)
            if obj.external_indent != self.indent:
                raise erring.IndentationError(obj)
            # Set `_open` so that dict-like and list-like objects share a
            # common test for completeness.
            self._open = True
        # No need to check for valid key type; already done at AST level
        if obj in self:
            raise erring.ParseError('Duplicate keys are prohibited', obj, [k for k in self if k == obj][0])
        self._next_key = obj
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._awaiting_val = True


    def check_append_key_path_scalar_key(self, obj):
        if self._awaiting_val:
            raise erring.ParseError('Missing value; cannot add a key until the previous key has been given a value', obj, self._next_key)
        if obj in self:
            raise erring.ParseError('Duplicate keys are prohibited', obj, [k for k in self if k == obj][0])
        self._next_key = obj
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._awaiting_val = True
        self._open = True


    def check_append_scalar_val(self, obj, len=len):
        if not self._awaiting_val:
            raise erring.ParseError('Missing key; cannot add a value until a key has been given', obj)
        if self.inline:
            if not obj.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(obj)
        elif obj.external_at_line_start:
            # Don't need to check indentation when the value starts on the
            # same line as the key, because any value that starts on that line
            # will be consistent with the key indentation.
            if len(obj.external_indent) <= len(self.indent) or not obj.external_indent.startswith(self.indent):
                raise erring.IndentationError(obj)
        if obj._resolved:
            self[self._next_key] = obj
        else:
            obj.parent = self
            obj.index = self._next_key
            self[self._next_key] = obj
            self._unresolved_dependency_count += 1
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._awaiting_val = False
        self._open = False


    def check_append_key_path_scalar_val(self, obj):
        if not self._awaiting_val:
            raise erring.ParseError('Missing key; cannot add a value until a key has been given', obj)
        if obj._resolved:
            self[self._next_key] = obj
        else:
            obj.parent = self
            obj.index = self._next_key
            self[self._next_key] = obj
            self._unresolved_dependency_count += 1
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._awaiting_val = False
        self._open = False


    def check_append_collection(self, obj, len=len):
        if not self._awaiting_val:
            raise erring.ParseError('Missing key; cannot add a value until a key has been given', obj)
        if self.inline:
            if not obj.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(obj)
        elif obj.external_at_line_start:
            if len(obj.external_indent) <= len(self.indent) or not obj.external_indent.startswith(self.indent):
                raise erring.IndentationError(obj)
        obj.parent = self
        obj.index = self._next_key
        obj.nesting_depth = self.nesting_depth + 1
        self[self._next_key] = obj
        self._unresolved_dependency_count += 1
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._awaiting_val = False
        self._open = False


    def check_append_key_path_collection(self, obj):
        if not self._awaiting_val:
            raise erring.ParseError('Missing key; cannot add a value until a key has been given', obj)
        obj.parent = self
        obj.index = self._next_key
        obj.nesting_depth = self.nesting_depth + 1
        self[self._next_key] = obj
        self._unresolved_dependency_count += 1
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._awaiting_val = False
        self._open = False




class TagNode(object):
    basetype = 'tag'
    __slots__ = _node_common_slots + ['type', 'mutable', 'compatible_basetypes', '_type_data'
                                      'label', 'newline',
                                      'collection_config_type', 'collection_config_val',
                                      'open', '_next_key', '_awaiting_val',
                                      '_unresolved_dependency_count', 'external_inline']
    def __init__(self, state, external_inline,
                 set_tag_doc_comment_externals=_set_tag_doc_comment_externals,
                 list=list):
        list.__init__(self)
        self.type = None
        self._type_data = state.type_data
        self.compatible_basetypes = set(['root', 'scalar', 'dict', 'list', 'keypath'])
        self.label = None
        self.newline = None
        self.collection_config_type = None
        self._unresolved_dependency_count = 0
        self._open = False
        self._awaiting_val = False
        self._next_key = None

        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.exteral_inline = external_inline
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = state.first_lineno
        self.first_colno = state.first_colno
        self.last_lineno = state.last_lineno
        self.last_colno = state.last_colno
        self._resolved = False
        self.extra_dependents = None
        if not state.next_cache:
            self.doc_comment = None
            self.tag = None
            self.external_indent = self.indent
            self.external_at_line_start = self.at_line_start
            self.external_first_lineno = self.first_lineno
        else:
            set_tag_doc_comment_externals(self, state)

    _keywords = set(['type', 'label', 'newline', 'init', 'deepinit',
                     'default', 'deepdefault', 'recmerge', 'deeprecmerge'])
    _collection_config_types = set(['init', 'deepinit', 'default',
                                    'deepdefault', 'recmerge', 'deeprecmerge'])

    def check_append_scalar_key(self, obj):
        if not self._open:
            raise erring.ParseError('Cannot add a key to a closed object; perhaps a "," is missing', obj)
        if self._awaiting_val:
            raise erring.ParseError('Missing value; cannot add a key until the previous key has been given a value', obj)
        if not obj.external_indent.startswith(self.inline_indent):
            raise erring.IndentationError(obj)
        if obj.basetype != 'scalar':
            raise erring.ParseError('Tags only take strings as keys', obj)
        # No need to check `.implicit_type`; filter for valid keys
        if obj.final_val not in self._keywords:
            raise erring.ParseError('Invalid keyword "{0}"'.format(obj.final_value), obj)
        if obj.final_val in self._collection_config_types:
            if self.collection_config_type is not None:
                raise erring.ParseError('Duplicate keys are prohibited', obj)
            if 'dict' not in self.compatible_basetypes or 'list' not in self.compatible_basetypes:
                raise erring.ParseError('Keyword argument incompatible with type')
            self.compatible_basetypes = set(['dict', 'list'])
        else:
            if getattr(self, obj.final_val) is not None:
                raise erring.ParseError('Duplicate keys are prohibited', obj)
            if obj.final_val == 'newline':
                if 'scalar' not in self.compatible_basetypes:
                    raise erring.ParseError('Incompatible argument "newline"', obj)
                self.compatible_basetypes == set(['scalar'])
        self._next_key = obj
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._awaiting_val = True

    def check_append_scalar_val(self, obj):
        if not obj.external_indent.startswith(self.inline_indent):
            raise erring.IndentationError(obj)
        if not self._awaiting_val:
            if (self._open and obj.basetype == 'scalar' and obj.final_val in self._type_data and
                    all(x is None for x in (self.type, self.label, self.newline, self.collection_config_type))):
                self.type = obj
                self.compatible_basetypes = set((self._type_data[obj.final_val].basetype,))
                self.mutable = self._type_data[obj.final_val].mutable
            else:
                if obj._resolved and obj.final_val in self._type_data:
                    raise erring.ParseError('Misplaced type; type must be first in a tag')
                else:
                    raise erring.ParseError('Missing key; cannot add a value until a key has been given', obj)
        else:
            if self._next_key in self._collection_config_types:
                self.collection_config_type = self._next_key
                if obj._resolved:
                    self.collection_config_val = obj.final_val
                else:
                    self.collection_config_val = obj
                    self._unresolved_dependency_count += 1
            else:
                if obj.basetype != 'scalar':
                    raise erring.ParseError('Only scalar values are allowed', obj)
                if obj.block:
                    raise erring.ParseError('Block strings are not allowed as tag values', obj)
                if self._next_key == 'newline':
                    if obj.final_val not in set(['\v', '\f', '\r', '\n', '\r\n', '\u0085', '\u2028', '\u2029']):
                        raise erring.ParseError('Invalid value for newline', obj)
                elif self._next_key == 'type':
                    if not all(x is None for x in (self.type, self.label, self.newline, self.collection_config_type)):
                        raise erring.ParseError('Misplaced type; type must be first in a tag')
                    try:
                        self.compatible_basetypes = set([self._type_data[obj.final_val].basetype])
                        self.mutable = self._type_data[obj.final_val].mutable
                    except KeyError:
                        raise erring.ParseError('Unknown type "{0}"'.format(obj.final_val), obj)
                setattr(self, self._next_key, obj)
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._open = False
        self._awaiting_val = False

    def check_append_collection(self, obj):
        if not obj.external_indent.startswith(self.inline_indent):
            raise erring.IndentationError(obj)
        if not self._awaiting_val:
            raise erring.ParseError('Missing key; cannot add a value until a key has been given', obj)
        if self._next_key not in self._collection_config_types:
            raise erring.ParseError('A list is only allowed in a tag as part of collection configuration', obj)
        self.collection_config_type = self._next_key
        self.collection_config_val = obj
        obj.parent = self
        self._unresolved_dependency_count += 1
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno
        self._open = False
        self._awaiting_val = False




class KeyPathNode(list):
    '''
    Abstract key path.

    Used as dict keys or in sections for assigning in nested objects.
    '''
    basetype = 'key_path'
    __slots__ = _node_common_slots + ['external_indent', 'external_at_line_start',
                                      'external_first_lineno', 'resolved',
                                      'extra_dependents', 'raw_val',
                                      'assign_key_val_lineno', 'assign_key_val_colno']

    def __init__(self, state, key_path_raw_val,
                 set_tag_doc_comment_externals=_set_tag_doc_comment_externals,
                 open_indentation_list=OPEN_INDENTATION_LIST,
                 path_separator=PATH_SEPARATOR,
                 reserved_word_patterns=_reserved_word_patterns,
                 key_path_reserved_word_vals=_key_path_reserved_word_vals,
                 reserved_word_types=_reserved_word_types,
                 ScalarNode=ScalarNode, list=list):
        list.__init__(self)

        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = state.first_lineno
        self.first_colno = state.first_colno
        self.last_lineno = state.last_lineno
        self.last_colno = state.last_colno
        self._resolved = False
        self.extra_dependents = None
        if not state.next_cache:
            self.doc_comment = None
            self.tag = None
            self.external_indent = self.indent
            self.external_at_line_start = self.at_line_start
            self.external_first_lineno = self.first_lineno
        else:
            set_tag_doc_comment_externals(self, state)

        first_colno = state.first_colno
        last_colno = first_colno
        for kp_elem_raw in key_path_raw_val.split(path_separator):
            if kp_elem_raw == open_indentation_list:
                self.append(kp_elem_raw)
                last_colno += 2
                first_colno = last_colno
            else:
                last_colno += len(kp_elem_raw) - 1
                if kp_elem_raw in reserved_word_patterns:
                    try:
                        kp_elem_final = key_path_reserved_word_vals[kp_elem_raw]
                    except KeyError:
                        kp_elem_node = ScalarNode(state)
                        kp_elem_node.first_colno = first_colno
                        kp_elem_node.last_colno = last_colno
                        if kp_elem_raw.lower() in _reserved_word_types:
                            raise erring.ParseError('Invalid capitalization of reserved word "{0}"'.format(kp_elem_raw.lower()), kp_elem_node)
                        elif kp_elem_raw == kp_elem_raw.lower():
                            raise erring.ParseError('Reserved word "{0}" is not allowed in key paths'.format(kp_elem_raw.lower()), kp_elem_node)
                        else:
                            raise erring.ParseError('Reserved word "{0}" is not allowed in key paths, and has invalid capitalization'.format(kp_elem_raw.lower()), kp_elem_node)
                    implicit_type = _reserved_word_types[kp_elem_raw]
                else:
                    kp_elem_final = kp_elem_raw
                    implicit_type = 'key'
                kp_elem_node = ScalarNode(state, implicit_type=implicit_type)
                kp_elem_node.first_colno = first_colno
                kp_elem_node.last_colno = last_colno
                if state.full_ast:
                    kp_elem_node.raw_val = kp_elem_raw
                    kp_elem_node.key_path = self
                kp_elem_node.final_val = kp_elem_final
                kp_elem_node._resolved = True
                self.append(kp_elem_node)
                last_colno += 2
                first_colno = last_colno




class SectionNode(object):
    '''
    Section.
    '''
    basetype = 'section'
    __slots__ = _node_common_slots + ['delim', 'key_path', 'scalar', '_end_delim']
    def __init__(self, state, delim):
        self.delim = delim
        self.key_path = None
        self.scalar = None
        self._end_delim = False

        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = state.first_lineno
        self.first_colno = state.first_colno
        self.last_lineno = state.last_lineno
        self.last_colno = state.last_colno
        self._resolved = False
        self.extra_dependents = None
        # Sections never have tags or doc comments, and don't use external
        # attributes
