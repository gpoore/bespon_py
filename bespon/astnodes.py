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


OPEN_NONINLINE_LIST = grammar.LIT_GRAMMAR['open_noninline_list']
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




_node_common_slots = ['source_name',
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

    def __init__(self, state):
        self.source_name = state.source_name
        self.source_include_depth = state.source_include_depth
        self.source_initial_nesting_depth = state.source_initial_nesting_depth
        self.full_ast = state.full_ast
        self.nesting_depth = state.source_initial_nesting_depth

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

    def __init__(self, source):
        list.__init__(self)

        self.source_name = source.source_name
        self.tag = None
        self.end_tag = None
        self._unresolved_dependency_count = 0
        self.nesting_depth = source.source_initial_nesting_depth
        self._key_path_scope = None
        self.key_path_parent = None
        self.section = None
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

        self.parent = source


    def check_append_scalar_val(self, obj):
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


    def check_append_collection(self, obj, in_key_path_after_element1=False):
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




def _init_common(self, state_or_scalar_obj, tagable=True):
    '''
    Shared initialization for all AST nodes below root level.

    Usually takes initialization from state, but in some cases, like
    non-inline dicts, can take values from a pre-existing scalar or other
    object.  Hence, the argument `state_or_scalar_obj`.
    '''
    try:
        doc_comment_obj = state_or_scalar_obj.next_doc_comment
        state_or_scalar_obj.next_doc_comment = None
        tag_obj = state_or_scalar_obj.next_tag
        state_or_scalar_obj.next_tag = None
        if not tagable and tag_obj is not None:
            raise erring.ParseError('A tag was applied to an untagable object', state_or_scalar_obj, tag_obj)
    except AttributeError:
        doc_comment_obj = None
        tag_obj = None
    self.doc_comment = doc_comment_obj
    self.tag = tag_obj

    self.source_name = state_or_scalar_obj.source_name
    self.indent = state_or_scalar_obj.indent
    self.at_line_start = state_or_scalar_obj.at_line_start
    self.inline = state_or_scalar_obj.inline
    self.inline_indent = state_or_scalar_obj.inline_indent
    self.first_lineno = state_or_scalar_obj.first_lineno
    self.first_colno = state_or_scalar_obj.first_colno
    self.last_lineno = state_or_scalar_obj.last_lineno
    self.last_colno = state_or_scalar_obj.last_colno

    # If there is no tag or doc comment, the external appearance of the object
    # is identical to that of the object itself.  Otherwise, the external
    # appearance is based on the doc comment, or the tag in its absence.
    # There is no need to perform indentation checks for the external
    # appearance, since these will be done during appending to the AST.
    if tag_obj is None:
        if doc_comment_obj is None:
            self.external_indent = self.indent
            self.external_at_line_start = self.at_line_start
            self.external_first_lineno = self.first_lineno
        else:
            if doc_comment_obj.inline:
                if not self.indent.startswith(doc_comment_obj.inline_indent):
                    raise erring.IndentationError(self)
            elif doc_comment_obj.at_line_start:
                if not self.at_line_start:
                    raise erring.ParseError('In non-inline mode, a doc comment that starts at the beginning of a line cannot be immediately followed by the start of another object; a doc comment cannot set the indentation level', doc_comment_obj, self)
                if doc_comment_obj.indent != self.indent:
                    raise erring.ParseError('Inconsistent indentation between doc comment and object', doc_comment_obj, self)
            elif self.at_line_start and (len(self.indent) <= len(doc_comment_obj.indent) or not self.indent.startswith(doc_comment_obj.indent)):
                raise erring.IndentationError(self)
            self.external_indent = doc_comment_obj.indent
            self.external_at_line_start = doc_comment_obj.at_line_start
            self.external_first_lineno = doc_comment_obj.first_lineno
    else:
        if self.basetype not in tag_obj.compatible_basetypes:
            raise erring.ParseError('Tag is incompatible with object', tag_obj, self)
        if self.basetype == 'scalar' and (tag_obj['newline'] is not None or tag_obj['indent'] is not None) and not self.block:
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
                    raise erring.ParseError('In non-inline mode, a doc comment that starts at the beginning of a line cannot be immediately followed by the start of another object; a doc comment cannot set the indentation level', doc_comment_obj, tag_obj)
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
    # Some attributes are not given default values, to ensure that any
    # incorrect attempt to access them results in an error.




class ScalarNode(object):
    '''
    Scalar object, including quoted (delim, block) and unquoted strings,
    none, bool, int, and float.
    '''
    basetype = 'scalar'
    __slots__ = (_node_common_slots +
                 ['delim', 'block', 'implicit_type', 'continuation_indent',
                  'raw_val', 'num_base', 'key_path', 'section',
                  'assign_key_val_lineno', 'assign_key_val_colno'])

    def __init__(self, state, init_common=_init_common,
                 delim=None, block=None, implicit_type=None, num_base=None):
        self.delim = delim
        self.block = block
        self.implicit_type = implicit_type
        self.num_base = num_base
        self.continuation_indent = state.continuation_indent
        self.key_path = None
        self.section = None
        # `init_common()` must follow assigning `.block`, because there is
        # a check for using `newline` with non-block scalars.
        init_common(self, state)

    def __hash__(self):
        # The only time a scalar will need a hash is when it is used as a
        # dict key, and in that case it must already be resolved and thus
        # will have `.final_val`.
        return hash(self.final_val)

    def __eq__(self, other):
        # When a ScalarNode object is used as a dict key, allow access to
        # the value through the original object, another ScalarNode object
        # with the save `.final_val`, or the literal scalar value.
        return other == self.final_val or (hasattr(other, 'final_val') and other.final_val == self.final_val)




class ListlikeNode(list):
    '''
    List-like collection.
    '''
    basetype = 'list'
    __slots__ = (_node_common_slots + _node_collection_slots +
                 ['section', 'internal_indent_first', 'internal_indent_subsequent'])

    def __init__(self, state_or_scalar_obj, init_common=_init_common,
                 key_path_parent=None, _key_path_traversable=False,
                 section=None):
        list.__init__(self)

        self.key_path_parent = key_path_parent
        self._key_path_traversable = _key_path_traversable
        self._unresolved_dependency_count = 0
        self._key_path_scope = None
        self.section = section
        if _key_path_traversable:
            # A collection created implicitly as part of a keypath lacks most
            # standard attributes, so they are never created. An implicit
            # collection is always open.
            self.doc_comment = None
            self.tag = None
            self.indent = state_or_scalar_obj.indent
            self.inline = state_or_scalar_obj.inline
            self.inline_indent = state_or_scalar_obj.inline_indent
            self.first_lineno = state_or_scalar_obj.first_lineno
            self.first_colno = state_or_scalar_obj.first_colno
            self.last_lineno = state_or_scalar_obj.last_lineno
            self.last_colno = state_or_scalar_obj.last_colno
            self._open = True
        else:
            init_common(self, state_or_scalar_obj)
            self._open = False
            if not self.inline:
                self.internal_indent_first = None
                self.internal_indent_subsequent = None


    def _set_internal_indent(self, obj):
        if self.section is not None:
            # This will only ever be invoked when a list is the last element
            # in a section keypath (or is the entire section).  Due to section
            # parsing rules, `obj` is guaranteed to be on a later line.  Due
            # to non-inline doc comment/tag/obj rules, consistency is already
            # enforced in this context and no special checks are needed.
            # `external_indent` may simply be used as-is.
            self.internal_indent_first = obj.external_indent
            self.internal_indent_subsequent = obj.external_indent
        else:
            if len(obj.external_indent) <= len(self.indent) or not obj.external_indent.startswith(self.indent):
                raise erring.IndentationError(obj)
            extra_indent = obj.external_indent[len(self.indent):]
            if obj.external_first_lineno == self.last_lineno:
                # The non-inline list opener `*` does not affect `at_line_start`
                # and is treated as a space for the purpose of calculating the
                # overall indent of objects following it on the same line.  If
                # the `*` (which will be represented by a space in `self.indent`)
                # is adjacent to tabs on both sides, then it is not counted
                if self.indent[-1:] == '\t' and extra_indent[1:2] == '\t':
                    self.internal_indent_first = obj.external_indent
                    self.internal_indent_subsequent = self.indent + extra_indent[1:]
                else:
                    self.internal_indent_first = self.internal_indent_subsequent = obj.external_indent
            else:
                if self.indent[-1:] == '\t' and extra_indent[:1] == '\t':
                    self.internal_indent_first = self.indent + '\x20' + extra_indent
                    self.internal_indent_subsequent = obj.external_indent
                else:
                    self.internal_indent_first = self.internal_indent_subsequent = obj.external_indent


    def check_append_scalar_key(self, obj):
        raise erring.ParseError('Cannot append a key-value pair directly to a list-like object', obj)


    def check_append_key_path_scalar_key(self, obj):
        raise erring.ParseError('Key path is incompatible with previously created list-like object', obj, self)


    def check_append_scalar_val(self, obj):
        if not self._open:
            if self.inline:
                raise erring.ParseError('Cannot append to a closed list-like object; check for incorrect indentation or missing "{0}"'.format(INLINE_ELEMENT_SEPARATOR), obj)
            else:
                raise erring.ParseError('Cannot append to a closed list-like object; check for incorrect indentation or missing "{0}"'.format(OPEN_NONINLINE_LIST), obj)
        if self.inline:
            if not obj.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(obj)
        elif obj.external_first_lineno == self.last_lineno:
            if obj.external_indent != self.internal_indent_first:
                if self.internal_indent_first is None:
                    self._set_internal_indent(obj)
                    if obj.external_indent != self.internal_indent_first:
                        raise erring.IndentationError(obj)
                else:
                    raise erring.IndentationError(obj)
        elif obj.external_indent != self.internal_indent_subsequent:
            if self.internal_indent_subsequent is None:
                self._set_internal_indent(obj)
                if obj.external_indent != self.internal_indent_subsequent:
                    raise erring.IndentationError(obj)
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


    def check_append_key_path_scalar_val(self, obj):
        if obj._resolved:
            self.append(obj)
        else:
            obj.parent = self
            obj.index = len(self)
            self.append(obj)
            self._unresolved_dependency_count += 1
        self.last_lineno = obj.last_lineno
        self.last_colno = obj.last_colno


    def check_append_collection(self, obj):
        if not self._open:
            if self.inline:
                raise erring.ParseError('Cannot append to a closed list-like object; check for incorrect indentation or missing "{0}"'.format(INLINE_ELEMENT_SEPARATOR), obj)
            else:
                raise erring.ParseError('Cannot append to a closed list-like object; check for incorrect indentation or missing "{0}"'.format(OPEN_NONINLINE_LIST), obj)
        if self.inline:
            if not obj.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(obj)
        elif obj.external_first_lineno == self.last_lineno:
            if obj.external_indent != self.internal_indent_first:
                if self.internal_indent_first is None:
                    self._set_internal_indent(obj)
                    if obj.external_indent != self.internal_indent_first:
                        raise erring.IndentationError(obj)
                else:
                    raise erring.IndentationError(obj)
        elif obj.external_indent != self.internal_indent_subsequent:
            if self.internal_indent_subsequent is None:
                self._set_internal_indent(obj)
                if obj.external_indent != self.internal_indent_subsequent:
                    raise erring.IndentationError(obj)
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


    def check_append_key_path_collection(self, obj):
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
                 ['section', '_awaiting_val', '_next_key'])

    def __init__(self, state_or_scalar_obj, init_common=_init_common,
                 key_path_parent=None, _key_path_traversable=False,
                 section=None):
        collections.OrderedDict.__init__(self)

        self.key_path_parent = key_path_parent
        self._key_path_traversable = _key_path_traversable
        self._unresolved_dependency_count = 0
        self._key_path_scope = None
        self.section = section
        if _key_path_traversable:
            # A collection created implicitly as part of a keypath lacks most
            # standard attributes, so they are never created.  An implicit
            # collection is always open.
            self.doc_comment = None
            self.tag = None
            self.indent = state_or_scalar_obj.indent
            self.inline = state_or_scalar_obj.inline
            self.inline_indent = state_or_scalar_obj.inline_indent
            self.first_lineno = state_or_scalar_obj.first_lineno
            self.first_colno = state_or_scalar_obj.first_colno
            self.last_lineno = state_or_scalar_obj.last_lineno
            self.last_colno = state_or_scalar_obj.last_colno
            self._open = True
        else:
            init_common(self, state_or_scalar_obj)
            self._open = False
        self._awaiting_val = False
        self._next_key = None


    def check_append_scalar_key(self, obj):
        if self.inline:
            if not self._open:
                raise erring.ParseError('Cannot add a key to a closed object; perhaps a "{0}" is missing'.format(INLINE_ELEMENT_SEPARATOR), obj)
            if self._awaiting_val:
                raise erring.ParseError('Missing value; cannot add a key until the previous key has been given a value', obj, self._next_key)
            if not obj.external_indent.startswith(self.inline_indent):
                raise erring.IndentationError(obj)
        else:
            # Non-inline dict-like objects are always open, so there is no
            # test for them.  In contrast, non-inline list-like objects
            # must be explicitly opened with `*`.
            if self._awaiting_val:
                raise erring.ParseError('Missing value; cannot add a key until the previous key has been given a value', obj, self._next_key)
            if not obj.external_at_line_start:
                raise erring.ParseError('A key must be at the start of the line in non-inline mode', obj)
            if obj.external_indent != self.indent:
                raise erring.IndentationError(obj)
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


    def check_append_scalar_val(self, obj):
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


    def check_append_collection(self, obj):
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




class TagNode(object):
    basetype = 'tag'
    __slots__ = _node_common_slots + ['type', 'mutable', 'compatible_basetypes', '_type_data'
                                      'label', 'newline',
                                      'collection_config_type', 'collection_config_val',
                                      'open', '_next_key', '_awaiting_val',
                                      '_unresolved_dependency_count']
    def __init__(self, state, init_common=_init_common):
        list.__init__(self)
        init_common(self, state)
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
                                      'assign_key_val_lineno', 'assign_key_val_colno',
                                      'section']

    def __init__(self, state, key_path_raw_val,
                 init_common=_init_common,
                 open_noninline_list=OPEN_NONINLINE_LIST,
                 path_separator=PATH_SEPARATOR,
                 reserved_word_patterns=_reserved_word_patterns,
                 key_path_reserved_word_vals=_key_path_reserved_word_vals,
                 reserved_word_types=_reserved_word_types,
                 ScalarNode=ScalarNode):
        list.__init__(self)
        init_common(self, state, tagable=False)

        self.section = None

        first_colno = state.first_colno
        last_colno = first_colno
        for kp_elem_raw in key_path_raw_val.split(path_separator):
            if kp_elem_raw == open_noninline_list:
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
                        if kp_elem_raw in _reserved_word_types:
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
                kp_elem_node.final_val = kp_elem_final
                kp_elem_node._resolved = True
                kp_elem_node.key_path = self
                self.append(kp_elem_node)
                last_colno += 2
                first_colno = last_colno




class SectionNode(object):
    '''
    Section.
    '''
    basetype = 'section'
    __slots__ = _node_common_slots + ['delim', 'key_path', 'scalar']
    def __init__(self, state, delim, init_common=_init_common):
        init_common(self, state)
        self.delim = delim
        self.key_path = None
        self.scalar = None
