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
INDENT = grammar.LIT_GRAMMAR['indent']
LINE_TERMINATOR_ASCII_OR_EMPTY_SET = set(grammar.LIT_GRAMMAR['line_terminator_ascii_seq'] + ('',))
LINE_TERMINATOR_UNICODE_OR_EMPTY_SET = set(grammar.LIT_GRAMMAR['line_terminator_unicode_seq'] + ('',))


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
                      '_resolved', 'final_val']

_node_data_slots = ['doc_comment', 'tag', 'extra_dependents',
                    'external_indent',
                    'external_at_line_start',
                    'external_first_lineno',
                    'external_first_colno']

_node_scalar_slots = ['implicit_type', 'delim', 'block']

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

    __slots__ = (_node_common_slots + ['source_name', 'source_include_depth',
                                       'source_initial_nesting_depth', 'nesting_depth',
                                       'root', 'full_ast'])

    def __init__(self, state):
        self.source_name = state.source_name
        self.source_include_depth = state.source_include_depth
        self.source_initial_nesting_depth = state.source_initial_nesting_depth
        self.nesting_depth = state.source_initial_nesting_depth
        self.full_ast = state.full_ast

        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = self.last_lineno = state.lineno
        self.first_colno = self.last_colno = state.colno

        self.root = RootNode(self)

        self._resolved = False




class RootNode(list):
    '''
    Lowest level in the AST except for the source node.  A list subclass that
    must ultimately contain only a single element.
    '''
    basetype = 'root'

    __slots__ = (_node_common_slots + _node_collection_slots +
                 ['source_name', 'doc_comment', 'tag', 'end_tag'])

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

        self._state = source._state
        self.indent = source.indent
        self.at_line_start = source.at_line_start
        self.inline = source.inline
        self.inline_indent = source.inline_indent
        self.first_lineno = source.first_lineno
        self.first_colno = source.first_colno
        self.last_lineno = source.last_lineno
        self.last_colno = source.last_colno


    def check_append_scalar_val(self, node, len=len):
        if len(self) == 1:
            raise erring.ParseError('Only a single scalar or collection object is allowed at root level', node)
        if not node.external_indent.startswith(self.indent):
            raise erring.IndentationError(node)
        if node._resolved:
            self.append(node)
            self._resolved = True
        else:
            node.parent = self
            node.index = len(self)
            self.append(node)
            self._unresolved_dependency_count += 1
        self.indent = node.external_indent
        self.at_line_start = node.external_at_line_start
        self.first_lineno = node.external_first_lineno
        self.first_colno = node.external_first_colno
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._open = False


    def check_append_collection(self, node, len=len):
        if len(self) == 1:
            raise erring.ParseError('Only a single scalar or collection object is allowed at root level', node)
        if not node.external_indent.startswith(self.indent):
            raise erring.IndentationError(node)
        self.append(node)
        node.parent = self
        node.index = len(self)
        node.nesting_depth = self.nesting_depth + 1
        self._unresolved_dependency_count += 1
        self.indent = node.external_indent
        self.at_line_start = node.external_at_line_start
        self.first_lineno = node.external_first_lineno
        self.first_colno = node.external_first_colno
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._open = False




def _set_tag_doc_comment_externals(self, state, block=False, len=len):
    '''
    When there are doc comments or tags, set them and determine external
    attributes.  This is shared by all AST nodes below root level.
    Incorporating it into individual node `__init__()` would be possible,
    but would risk logic not staying in sync.
    '''
    doc_comment_node = state.next_doc_comment
    state.next_doc_comment = None
    tag_node = state.next_tag
    state.next_tag = None
    state.next_cache = False
    self.doc_comment = doc_comment_node
    self.tag = tag_node

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
    if tag_node is None:
        if doc_comment_node.inline:
            if not self.indent.startswith(doc_comment_node.inline_indent):
                raise erring.IndentationError(self)
        elif doc_comment_node.at_line_start:
            if not self.at_line_start:
                raise erring.ParseError('In non-inline mode, a doc comment that starts at the beginning of a line cannot be followed immediately by the start of another object; a doc comment cannot set the indentation level', doc_comment_node, self)
            if doc_comment_node.indent != self.indent:
                raise erring.ParseError('Inconsistent indentation between doc comment and object', doc_comment_node, self)
        elif self.at_line_start and (len(self.indent) <= len(doc_comment_node.indent) or not self.indent.startswith(doc_comment_node.indent)):
            raise erring.IndentationError(self)
        self.external_indent = doc_comment_node.indent
        self.external_at_line_start = doc_comment_node.at_line_start
        self.external_first_lineno = doc_comment_node.first_lineno
        self.external_first_colno = doc_comment_node.first_colno
    else:
        if self.basetype not in tag_node.compatible_basetypes:
            if not self.inline and 'dict' in tag_node.compatible_basetypes:
                erring.ParseError('Tag is incompatible with object; tags for dict-like objects in indentation-style syntax require an explicit type', tag_node, self)
            raise erring.ParseError('Tag is incompatible with object', tag_node, self)
        if tag_node.block_scalar and not self.block:
            raise erring.ParseError('Tag has a "newline" or "indent" argument, but is applied to a scalar with no literal line breaks', tag_node, self)
        tag_node.parent = self
        if not tag_node._resolved:
            self._unresolved_dependency_count += 1
        if tag_node.label is not None:
            state.ast.register_label(self)
        if doc_comment_node is None:
            if tag_node.external_inline:
                if not self.indent.startswith(tag_node.inline_indent):
                    raise erring.IndentationError(self)
            elif tag_node.at_line_start:
                if not self.indent.startswith(tag_node.indent):
                    raise erring.IndentationError(self)
            else:
                if self.at_line_start and (len(self.indent) <= len(tag_node.indent) or not self.indent.startswith(tag_node.indent)):
                    raise erring.IndentationError(self)
                if self.basetype in ('dict', 'list') and not self.inline:
                    raise erring.ParseError('The tag for a non-inline collection must be at the start of a line', tag_node)
            self.external_indent = tag_node.indent
            self.external_at_line_start = tag_node.at_line_start
            self.external_first_lineno = tag_node.first_lineno
            self.external_first_colno = tag_node.first_colno
        else:
            if doc_comment_node.inline:
                if not tag_node.indent.startswith(doc_comment_node.inline_indent):
                    raise erring.IndentationError(tag_node)
                if not self.indent.startswith(doc_comment_node.inline_indent):
                    raise erring.IndentationError(self)
            elif doc_comment_node.at_line_start:
                if not tag_node.at_line_start:
                    raise erring.ParseError('In non-inline mode, a doc comment that starts at the beginning of a line cannot be followed immediately by the start of another object; a doc comment cannot set the indentation level', doc_comment_node, tag_node)
                if doc_comment_node.indent != tag_node.indent:
                    raise erring.ParseError('Inconsistent indentation between doc comment and tag', doc_comment_node, tag_node)
                if not self.indent.startswith(tag_node.indent):
                    raise erring.IndentationError(self)
            elif tag_node.at_line_start:
                if len(tag_node.indent) <= len(doc_comment_node.indent) or not tag_node.indent.startswith(doc_comment_node.indent):
                    raise erring.IndentationError(tag_node)
                if not self.indent.startswith(tag_node.indent):
                    raise erring.IndentationError(self)
            else:
                if self.at_line_start and (len(self.indent) <= len(tag_node.indent) or not self.indent.startswith(tag_node.indent)):
                    raise erring.IndentationError(self)
                if self.basetype in ('dict', 'list') and not self.inline:
                    raise erring.ParseError('The tag for a non-inline collection must be at the start of a line', tag_node)
            self.external_indent = doc_comment_node.indent
            self.external_at_line_start = doc_comment_node.at_line_start
            self.external_first_lineno = doc_comment_node.first_lineno
            self.external_first_colno = doc_comment_node.first_colno




class ScalarNode(object):
    '''
    Scalar object, including quoted (inline, block) and unquoted strings,
    none, bool, int, and float.  Also used to represent doc comments.
    '''
    basetype = 'scalar'
    __slots__ = _node_common_slots + _node_data_slots + _node_scalar_slots
    def __init__(self, state, first_lineno, first_colno, last_lineno, last_colno,
                 implicit_type, delim=None, block=False,
                 set_tag_doc_comment_externals=_set_tag_doc_comment_externals):
        self.implicit_type = implicit_type
        self.delim = delim
        self.block = block

        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = first_lineno
        self.first_colno = first_colno
        self.last_lineno = last_lineno
        self.last_colno = last_colno
        self._resolved = True
        self.extra_dependents = None
        if not state.next_cache:
            self.doc_comment = None
            self.tag = None
            self.external_indent = self.indent
            self.external_at_line_start = self.at_line_start
            self.external_first_lineno = self.first_lineno
            self.external_first_colno = self.first_colno
        else:
            set_tag_doc_comment_externals(self, state, block)


class FullScalarNode(object):
    '''
    ScalarNode with extra data for full AST.
    '''
    basetype = 'scalar'
    __slots__ = (_node_common_slots + _node_data_slots + _node_scalar_slots +
                 ['continuation_indent', 'raw_val', 'num_base',
                  'key_path', 'key_path_occurrences',
                  'assign_key_val_lineno', 'assign_key_val_colno'])

    def __init__(self, state, first_lineno, first_colno, last_lineno, last_colno,
                 implicit_type, delim=None, block=False, num_base=None,
                 continuation_indent=None,
                 set_tag_doc_comment_externals=_set_tag_doc_comment_externals):
        self.implicit_type = implicit_type
        self.delim = delim
        self.block = block
        self.num_base = num_base
        self.continuation_indent = continuation_indent
        self.key_path = None
        self.key_path_occurrences = None

        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = first_lineno
        self.first_colno = first_colno
        self.last_lineno = last_lineno
        self.last_colno = last_colno
        self._resolved = True
        self.extra_dependents = None
        if not state.next_cache:
            self.doc_comment = None
            self.tag = None
            self.external_indent = self.indent
            self.external_at_line_start = self.at_line_start
            self.external_first_lineno = self.first_lineno
            self.external_first_colno = self.first_colno
        else:
            set_tag_doc_comment_externals(self, state)




class CommentNode(object):
    '''
    Line comment or doc comment.
    '''
    basetype = 'comment'
    __slots__ = _node_common_slots + _node_scalar_slots

    def __init__(self, state, first_lineno, first_colno, last_lineno, last_colno,
                 implicit_type, delim=None, block=False):
        self.implicit_type = implicit_type
        self.delim = delim
        self.block = block

        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = first_lineno
        self.first_colno = first_colno
        self.last_lineno = last_lineno
        self.last_colno = last_colno
        self._resolved = True


class FullCommentNode(object):
    '''
    CommentNode with extra data for full AST.
    '''
    basetype = 'comment'
    __slots__ = (_node_common_slots +
                 ['delim', 'block', 'implicit_type', 'continuation_indent',
                  'raw_val'])

    def __init__(self, state, first_lineno, first_colno, last_lineno, last_colno,
                 implicit_type, delim=None, block=None, continuation_indent=None):
        self.implicit_type = implicit_type
        self.delim = delim
        self.block = block
        self.continuation_indent = continuation_indent

        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = first_lineno
        self.first_colno = first_colno
        self.last_lineno = last_lineno
        self.last_colno = last_colno
        self._resolved = True




class ListlikeNode(list):
    '''
    List-like collection.
    '''
    basetype = 'list'
    __slots__ = (_node_common_slots + _node_data_slots +
                 _node_collection_slots + ['internal_indent'])

    def __init__(self, state_or_scalar_node,
                 set_tag_doc_comment_externals=_set_tag_doc_comment_externals,
                 key_path_parent=None, _key_path_traversable=False,
                 list=list):
        list.__init__(self)

        self.key_path_parent = key_path_parent
        self._key_path_traversable = _key_path_traversable
        self._unresolved_dependency_count = 0
        self._key_path_scope = None

        state = state_or_scalar_node._state
        self._state = state
        if state_or_scalar_node is state:
            self.indent = state.indent
            self.at_line_start = state.at_line_start
            self.inline = state.inline
            self.inline_indent = state.inline_indent
            self.first_lineno = self.last_lineno = state.lineno
            self.first_colno = self.last_colno = state.colno
        else:
            self.indent = state_or_scalar_node.external_indent
            self.at_line_start = state_or_scalar_node.external_at_line_start
            self.inline = state_or_scalar_node.inline
            self.inline_indent = state_or_scalar_node.inline_indent
            self.first_lineno = self.last_lineno = state_or_scalar_node.external_first_lineno
            self.first_colno = self.last_colno = state_or_scalar_node.external_first_colno
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
            self.external_first_colno = self.first_colno
        else:
            set_tag_doc_comment_externals(self, state)
        self._resolved = False
        self._open = False


    def check_append_scalar_key(self, node):
        raise erring.ParseError('Cannot append a key-value pair directly to a list-like object', node)


    def check_append_key_path_scalar_key(self, node):
        raise erring.ParseError('Key path is incompatible with previously created list-like object', node, self)


    def check_append_scalar_val(self, node, len=len):
        if not self._open:
            if self.inline:
                raise erring.ParseError('Cannot append to a closed list-like object; check for a missing "{0}"'.format(INLINE_ELEMENT_SEPARATOR), node)
            else:
                raise erring.ParseError('Cannot append to a closed list-like object; check for incorrect indentation or missing "{0}"'.format(OPEN_INDENTATION_LIST), node)
        if self.inline:
            if not node.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(node)
        elif node.external_indent != self.internal_indent:
            if self.internal_indent is None:
                if not self._key_path_traversable and (len(node.external_indent) <= len(self.indent) or not node.external_indent.startswith(self.indent)):
                    raise erring.IndentationError(node)
                self.internal_indent = node.external_indent
            else:
                raise erring.IndentationError(node)
        self.append(node)
        if not node._resolved:
            node.parent = self
            node.index = len(self)
            self._unresolved_dependency_count += 1
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._open = False


    def check_append_key_path_scalar_val(self, node, len=len):
        self.append(node)
        if not node._resolved:
            node.parent = self
            node.index = len(self)
            self._unresolved_dependency_count += 1
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._open = False


    def check_append_collection(self, node, len=len):
        if not self._open:
            if self.inline:
                raise erring.ParseError('Cannot append to a closed list-like object; check for a missing "{0}"'.format(INLINE_ELEMENT_SEPARATOR), node)
            else:
                if node.basetype == 'dict':
                    erring.ParseError('Cannot start a new dict-like object in a closed list-like object; check for incorrect indentation or missing "{0}"'.format(OPEN_INDENTATION_LIST), node)
                raise erring.ParseError('Cannot append to a closed list-like object; check for incorrect indentation or missing "{0}"'.format(OPEN_INDENTATION_LIST), node)
        if self.inline:
            if not node.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(node)
        elif node.external_indent != self.internal_indent:
            if self.internal_indent is None:
                if not self._key_path_traversable and (len(node.external_indent) <= len(self.indent) or not node.external_indent.startswith(self.indent)):
                    raise erring.IndentationError(node)
                self.internal_indent = node.external_indent
            else:
                raise erring.IndentationError(node)
        self.append(node)
        node.parent = self
        node.index = len(self)
        node.nesting_depth = self.nesting_depth + 1
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._open = False


    def check_append_key_path_collection(self, node, len=len):
        self.append(node)
        node.parent = self
        node.index = len(self)
        node.nesting_depth = self.nesting_depth + 1
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._open = False




class DictlikeNode(collections.OrderedDict):
    '''
    Dict-like collection.
    '''
    basetype = 'dict'
    __slots__ = (_node_common_slots + _node_data_slots +
                 _node_collection_slots +
                 ['_next_key', '_awaiting_val', 'key_nodes'])

    def __init__(self, state_or_scalar_node,
                 set_tag_doc_comment_externals=_set_tag_doc_comment_externals,
                 key_path_parent=None, _key_path_traversable=False,
                 OrderedDict=collections.OrderedDict):
        OrderedDict.__init__(self)

        self.key_path_parent = key_path_parent
        self._key_path_traversable = _key_path_traversable
        self._unresolved_dependency_count = 0
        self._key_path_scope = None
        self._awaiting_val = False
        self.key_nodes = {}

        state = state_or_scalar_node._state
        self._state = state
        if state_or_scalar_node is state:
            self.indent = state.indent
            self.at_line_start = state.at_line_start
            self.inline = state.inline
            self.inline_indent = state.inline_indent
            self.first_lineno = self.last_lineno = state.lineno
            self.first_colno = self.last_colno = state.colno
        else:
            self.indent = state_or_scalar_node.external_indent
            self.at_line_start = state_or_scalar_node.external_at_line_start
            self.inline = state_or_scalar_node.inline
            self.inline_indent = state_or_scalar_node.inline_indent
            self.first_lineno = self.last_lineno = state_or_scalar_node.external_first_lineno
            self.first_colno = self.last_colno = state_or_scalar_node.external_first_colno
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
            self.external_first_colno = self.first_colno
        else:
            set_tag_doc_comment_externals(self, state)
        self._resolved = False
        self._open = False


    def check_append_scalar_key(self, node):
        if self.inline:
            if not self._open:
                raise erring.ParseError('Cannot add a key to a closed object; perhaps a "{0}" is missing'.format(INLINE_ELEMENT_SEPARATOR), node)
            if self._awaiting_val:
                raise erring.ParseError('Missing value; cannot add a key until the previous key has been given a value', node, self.key_nodes[self._next_key])
            if not node.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(node)
        else:
            # Indentation dict-like objects are always open, so there is no
            # test for that.  In contrast, non-inline list-like objects
            # must be explicitly opened with `*`.
            if self._awaiting_val:
                raise erring.ParseError('Missing value; cannot add a key until the previous key has been given a value', node, self.key_nodes[self._next_key])
            if not node.external_at_line_start:
                raise erring.ParseError('A key must be at the start of the line in non-inline mode', node)
            if node.external_indent != self.indent:
                raise erring.IndentationError(node)
            # Set `_open` so that dict-like and list-like objects share a
            # common test for completeness.
            self._open = True
        # No need to check for valid key type; already done at AST level
        key = node.final_val
        if key in self:
            raise erring.ParseError('Duplicate keys are prohibited', node, self.key_nodes[key])
        self.key_nodes[key] = node
        self._next_key = key
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._awaiting_val = True


    def check_append_key_path_scalar_key(self, node):
        if self._awaiting_val:
            raise erring.ParseError('Missing value; cannot add a key until the previous key has been given a value', node, self.key_nodes[self._next_key])
        key = node.final_val
        if key in self:
            raise erring.ParseError('Duplicate keys are prohibited', node, self.key_nodes[key])
        self.key_nodes[key] = node
        self._next_key = key
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._awaiting_val = True
        self._open = True


    def check_append_scalar_val(self, node, len=len):
        if not self._awaiting_val:
            raise erring.ParseError('Missing key; cannot add a value until a key has been given', node)
        if self.inline:
            if not node.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(node)
        elif node.external_at_line_start:
            # Don't need to check indentation when the value starts on the
            # same line as the key, because any value that starts on that line
            # will be consistent with the key indentation.
            if len(node.external_indent) <= len(self.indent) or not node.external_indent.startswith(self.indent):
                raise erring.IndentationError(node)
        self[self._next_key] = node
        if not node._resolved:
            node.parent = self
            node.index = self._next_key
            self._unresolved_dependency_count += 1
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._awaiting_val = False
        self._open = False


    def check_append_key_path_scalar_val(self, node):
        if not self._awaiting_val:
            raise erring.ParseError('Missing key; cannot add a value until a key has been given', node)
        self[self._next_key] = node
        if not node._resolved:
            node.parent = self
            node.index = self._next_key
            self._unresolved_dependency_count += 1
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._awaiting_val = False
        self._open = False


    def check_append_collection(self, node, len=len):
        if not self._awaiting_val:
            raise erring.ParseError('Missing key; cannot add a value until a key has been given', node)
        if self.inline:
            if not node.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(node)
        elif node.external_at_line_start:
            if len(node.external_indent) <= len(self.indent) or not node.external_indent.startswith(self.indent):
                raise erring.IndentationError(node)
        key = self._next_key
        self[key] = node
        node.parent = self
        node.index = key
        node.nesting_depth = self.nesting_depth + 1
        if not node._resolved:
            self._unresolved_dependency_count += 1
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._awaiting_val = False
        self._open = False


    def check_append_key_path_collection(self, node):
        if not self._awaiting_val:
            raise erring.ParseError('Missing key; cannot add a value until a key has been given', node)
        key = self._next_key
        self[key] = node
        node.parent = self
        node.index = key
        node.nesting_depth = self.nesting_depth + 1
        if not node._resolved:
            self._unresolved_dependency_count += 1
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._awaiting_val = False
        self._open = False




class TagNode(collections.OrderedDict):
    '''
    Tag for explicit typing, configuring collection types, defining labels,
    or setting newlines for string types.
    '''
    basetype = 'tag'
    __slots__ = (_node_common_slots +
                 ['external_inline',
                  '_open', '_unresolved_dependency_count', 'parent',
                  '_next_key', '_awaiting_val', 'key_nodes',
                  'type', 'label',
                  'compatible_basetypes',
                  'block_scalar', 'collection_config'])

    def __init__(self, state, first_lineno, first_colno, external_inline,
                 set_tag_doc_comment_externals=_set_tag_doc_comment_externals,
                 OrderedDict=collections.OrderedDict,
                 default_compatible_basetypes = set(['root', 'scalar', 'dict', 'list'])):
        OrderedDict.__init__(self)

        self.type = None
        self.compatible_basetypes = default_compatible_basetypes
        self.label = None
        self.block_scalar = False
        self.collection_config = False
        self._unresolved_dependency_count = 0
        self._open = False
        self._awaiting_val = False
        self._next_key = None
        self.key_nodes = {}

        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.external_inline = external_inline
        self.first_lineno = first_lineno
        self.first_colno = first_colno
        self.last_lineno = first_lineno
        self.last_colno = first_colno
        self._resolved = False


    _scalar_compatible_basetypes = set(['scalar'])
    _collection_compatible_basetypes = set(['dict', 'list'])
    _dict_compatible_basetypes = set(['dict'])
    _list_compatible_basetypes = set(['list'])

    _general_keywords = set(['label'])
    _block_scalar_keywords = set(['newline', 'indent'])
    _collection_keywords = set(['init'])
    _dict_keywords = set(['recmerge', 'default'])
    _list_keywords = set(['extend'])
    _any_collection_keywords = _collection_keywords | _dict_keywords | _list_keywords
    _keywords = _general_keywords | _block_scalar_keywords | _collection_keywords | _dict_keywords | _list_keywords


    def check_append_scalar_key(self, node, len=len):
        if not self._open:
            raise erring.ParseError('Cannot add a key to a closed object; perhaps a "{0}" is missing'.format(INLINE_ELEMENT_SEPARATOR), node)
        if self._awaiting_val:
            raise erring.ParseError('Missing value; cannot add a key until the previous key has been given a value', node, self.key_nodes[self._next_key])
        if not node.external_indent.startswith(self.inline_indent):
            raise erring.IndentationError(node)
        if node.delim is not None:
            raise erring.ParseError('Only unquoted keys are allowed in tags', node)
        key = node.final_val
        if key in self:
            raise erring.ParseError('Duplicate keys are prohibited', node, self.key_nodes[key])
        if key not in self._keywords:
            raise erring.ParseError('Invalid tag keyword "{0}"'.format(key), node)
        if key in self._block_scalar_keywords:
            if 'scalar' not in self.compatible_basetypes:
                raise erring.ParseError('Tag keyword argument "{0}" is incompatible with tag type'.format(key), node)
            self.compatible_basetypes = self._scalar_compatible_basetypes
            self.block_scalar = True
        elif key in self._collection_keywords:
            if 'dict' not in self.compatible_basetypes and 'list' not in self.compatible_basetypes:
                raise erring.ParseError('Tag keyword argument "{0}" is incompatible with type'.format(key), node)
            # #### If add copy or deepcopy variants
            # if key[:5] == 'deep_':
            #     other_key = key[5:]
            # else:
            #     other_key = 'deep_' + key
            # if other_key in self:
            #     raise erring.ParseError('Encountered mutually exclusive collection config settings "{0}" and "{1}'.format(key, other_key), obj, self.key_nodes[other_key])
            if len(self.compatible_basetypes) > 1:
                self.compatible_basetypes = self._collection_compatible_basetypes
            self.collection_config = True
        elif key in self._dict_keywords:
            if 'dict' not in self.compatible_basetypes:
                raise erring.ParseError('Tag keyword argument "{0}" is incompatible with type'.format(key), node)
            self.compatible_basetypes = self._dict_compatible_basetypes
            self.collection_config = True
        elif key in self._list_keywords:
            if 'list' not in self.compatible_basetypes:
                raise erring.ParseError('Tag keyword argument "{0}" is incompatible with type'.format(key), node)
            self.compatible_basetypes = self._list_compatible_basetypes
            self.collection_config = True
        self.key_nodes[key] = node
        self._next_key = key
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._awaiting_val = True


    def check_append_scalar_val(self, node, indent=INDENT,
                                line_terminator_ascii_or_empty_set=LINE_TERMINATOR_ASCII_OR_EMPTY_SET,
                                line_terminator_unicode_or_empty_set=LINE_TERMINATOR_UNICODE_OR_EMPTY_SET):
        if not node.external_indent.startswith(self.inline_indent):
            raise erring.IndentationError(node)
        if not self._awaiting_val:
            data_types = self._state.data_types
            if self._open and node.basetype == 'scalar' and node.delim is None and node.final_val in data_types and not self:
                self['type'] = node
                val = node.final_val
                data_type = data_types[val]
                if not data_type.typeable:
                    raise erring.ParseError('Type "{0}" cannot be set via tags; it is only an implicit type'.format(val), node)
                self.type = val
                self.compatible_basetypes = data_type.basetype_set
            else:
                if not self._open:
                    raise erring.ParseError('Cannot append to a closed tag; check for a missing "{0}"'.format(INLINE_ELEMENT_SEPARATOR), node)
                if node.basetype != 'scalar':
                    raise erring.ParseError('Unexpected object in tag; check for a missing key', node)
                if node.final_val in data_types or node.final_val in self._state.extended_data_types:
                    if node.final_val not in data_types:
                        raise erring.ParseError('Type "{0}" is not enabled (extended_data_types=False)'.format(node.final_val), node)
                    if node.delim is not None:
                        raise erring.ParseError('Type names must be unquoted', node)
                    if self:
                        raise erring.ParseError('Misplaced type; type must be first in a tag', node)
                    raise erring.ParseError('Missing key or unknown type; cannot add a value until a key has been given', node)
                raise erring.ParseError('Missing key or unknown type; cannot add a value until a key has been given', node)
        else:
            key = self._next_key
            if key == 'label':
                if node.basetype != 'scalar' or node.implicit_type != 'str' or node.delim is not None:
                    raise erring.ParseError('Label values must be unquoted strings', node)
                self[key] = node
                self.label = node.final_val
            elif key in self._block_scalar_keywords:
                if node.basetype != 'scalar' or node.first_lineno != node.last_lineno:
                    raise erring.ParseError('Keyword argument "{0}" only takes inline string values that are not broken over multiple lines'.format(key), node)
                val = node.final_val
                if key == 'newline':
                    if val not in line_terminator_unicode_or_empty_set:
                        raise erring.ParseError('Invalid value for "newline"; must be a Unicode line termination sequence or the empty string', node)
                    if self.type is not None and self._state.data_types[self.type].ascii_bytes and val not in line_terminator_ascii_or_empty_set:
                        raise erring.ParseError('Invalid value for "newline"; must be a Unicode line termination sequence in the ASCII range (or the empty string) for type "{0}"'.format(self.type), node)
                    self[key] = node
                elif key == 'indent':
                    if val.lstrip(indent) != '':
                        raise erring.ParseError('Invalid value for "indent"; must be a sequence of spaces and/or tabs', node)
                    self[key] = node
                else:
                    raise ValueError
            elif key in self._any_collection_keywords:
                if node.basetype != 'alias':
                    raise erring.ParseError('Collection config requires an alias or list of aliases', node)
                node.parent = self
                node.index = key
                self[key] = node
                self._unresolved_dependency_count += 1
            else:
                raise ValueError
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._awaiting_val = False
        self._open = False


    def check_append_collection(self, node):
        if node.basetype != 'alias_list':
            raise erring.ParseError('Collections are prohibited in tags, except for lists of aliases used in collection config', node)
        if not node.indent.startswith(self.inline_indent):
            raise erring.IndentationError(node)
        if not self._awaiting_val:
            raise erring.ParseError('Missing key; cannot add a value until a key has been given', node)
        key = self._next_key
        if key not in self._collection_keywords:
            raise erring.ParseError('Collections are prohibited in tags, except for lists of aliases used in collection config', node)
        self[key] = node
        node.parent = self
        node.index = key
        node.nesting_depth = 0
        self._unresolved_dependency_count += 1
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._awaiting_val = False
        self._open = False




class AliasListNode(list):
    '''
    List of alias nodes, for collection config in tags.
    '''
    basetype = 'alias_list'
    __slots__ = (_node_common_slots + ['nesting_depth', 'parent', 'index',
                                       '_open', '_unresolved_dependency_count'])

    def __init__(self, state, list=list):
        list.__init__(self)

        self._unresolved_dependency_count = 0

        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = self.last_lineno = state.lineno
        self.first_colno = self.last_colno = state.colno

        self._resolved = False
        self._open = False


    def check_append_scalar_key(self, node):
        raise erring.ParseError('Cannot append a key-value pair directly to a list-like object', node)


    def check_append_scalar_val(self, node,
                                self_alias=grammar.LIT_GRAMMAR['self_alias'],
                                len=len):
        if not self._open:
            raise erring.ParseError('Cannot append to a closed alias list; check for a missing "{0}"'.format(INLINE_ELEMENT_SEPARATOR), node)
        if not node.external_indent.startswith(self.inline_indent):
            raise erring.IndentationError(node)
        if node.basetype != 'alias':
            raise erring.ParseError('Only aliases are allowed in alias lists', node)
        self.append(node)
        node.parent = self
        node.index = len(self)
        self._unresolved_dependency_count += 1
        self.last_lineno = node.last_lineno
        self.last_colno = node.last_colno
        self._open = False


    def check_append_collection(self, node, len=len):
        raise erring.ParseError('Only aliases are allowed in alias lists; collections are not permitted', node)




class AliasNode(object):
    '''
    Alias node.
    '''
    basetype = 'alias'
    __slots__ = (_node_common_slots + _node_data_slots +
                 ['parent', 'index', 'target_root', 'target_path',
                  'target_node', 'target_label'])
    def __init__(self, state, alias_raw_val, path_separator=PATH_SEPARATOR,
                 set_tag_doc_comment_externals=_set_tag_doc_comment_externals):
        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = self.last_lineno = state.lineno
        self.first_colno = state.colno
        self.last_colno = state.colno + len(alias_raw_val) - 1
        self._resolved = False
        self.extra_dependents = None
        if not state.next_cache:
            self.doc_comment = None
            self.tag = None
            self.external_indent = self.indent
            self.external_at_line_start = self.at_line_start
            self.external_first_lineno = self.first_lineno
            self.external_first_colno = self.first_colno
        else:
            set_tag_doc_comment_externals(self, state, block)

        alias_path = alias_raw_val[1:].split(path_separator)
        self.target_root = None
        self.target_node = None
        self.target_label = alias_path[0]
        if len(alias_path) == 1:
            self.target_path = None
        else:
            self.target_path = alias_path[1:]




class KeyPathNode(list):
    '''
    Abstract key path.

    Used as dict keys or in sections for assigning in nested objects.
    '''
    basetype = 'key_path'
    __slots__ = (_node_common_slots + _node_data_slots +
                 ['external_indent', 'external_at_line_start',
                  'external_first_lineno', 'resolved',
                  'extra_dependents', 'raw_val',
                  'assign_key_val_lineno', 'assign_key_val_colno'])

    def __init__(self, state, key_path_raw_val,
                 set_tag_doc_comment_externals=_set_tag_doc_comment_externals,
                 open_indentation_list=OPEN_INDENTATION_LIST,
                 path_separator=PATH_SEPARATOR,
                 reserved_word_patterns=_reserved_word_patterns,
                 key_path_reserved_word_vals=_key_path_reserved_word_vals,
                 reserved_word_types=_reserved_word_types,
                 ScalarNode=ScalarNode, FullScalarNode=FullScalarNode,
                 list=list):
        list.__init__(self)

        self._state = state
        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = self.last_lineno = state.lineno
        self.first_colno = state.colno
        self.last_colno = state.colno + len(key_path_raw_val) - 1
        self._resolved = False
        self.extra_dependents = None
        if not state.next_cache:
            self.doc_comment = None
            self.tag = None
            self.external_indent = self.indent
            self.external_at_line_start = self.at_line_start
            self.external_first_lineno = self.first_lineno
            self.external_first_colno = self.first_colno
        else:
            # Cached objects that would be invalid for a key path are filtered
            # out in decoding, so using the shared externals functions here
            # won't introduce any errors and doesn't require any checks
            set_tag_doc_comment_externals(self, state)

        first_colno = last_colno = self.first_colno
        lineno = self.first_lineno
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
                    implicit_type = 'str'
                if not self._state.full_ast:
                    kp_elem_node = ScalarNode(state, lineno, first_colno, lineno, last_colno, implicit_type)
                else:
                    kp_elem_node = FullScalarNode(state, lineno, first_colno, lineno, last_colno,
                                                  implicit_type)
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
    __slots__ = (_node_common_slots + _node_data_slots +
                 ['delim', 'key_path', 'scalar', '_end_delim'])
    def __init__(self, state, delim):
        self.delim = delim
        self.key_path = None
        self.scalar = None
        self._end_delim = False

        # Sections never have tags or doc comments, and thus technically don't
        # require external attributes.  However, external attributes are
        # created anyway so that there is a common set of attributes for
        # creating collections based on scalars, key paths, and sections.
        # There is no need for tag or doc comment checks here, because that
        # is already done during decoding.
        self._state = state
        self.indent = self.external_indent = state.indent
        self.at_line_start = self.external_at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = self.last_lineno = self.external_first_lineno = state.lineno
        self.first_colno = self.last_colno = self.external_first_colno = state.colno
        self._resolved = False
        self.extra_dependents = None
