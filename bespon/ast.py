# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#

'''
Abstract syntax tree (AST) elements.
'''

# pylint: disable=C0301

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

from . import erring
import sys
import collections


# pylint: disable=E0602, W0622
if sys.version_info.major == 2:
    str = unicode
    __chr__ = chr
    chr = unichr
# pylint: enable=E0602, W0622




_astobj_common_slots = ['basetype',
                        'indent', 'at_line_start',
                        'inline', 'inline_indent',
                        'first_lineno', 'first_column',
                        'last_lineno', 'last_column']

_astobj_scalar_or_collection_slots = ['tag', 'parent', 'index',
                                      'resolved', 'final_val',
                                      'extra_dependents']

_astobj_scalar_slots = ['delim', 'block', 'implicit_type']

_astobj_collection_slots = ['keypath_parent', 'keypath_traversable',
                            'open', 'unresolved_child_count',
                            'check_append_scalar_key',
                            'check_append_scalar_val',
                            'check_append_collection',
                            'check_append_keypath']

_astobj_dict_slots = ['next_key', 'awaiting_val']

_astobj_tag_slots = ['type', 'compatible_basetypes', 'label', 'newline',
                     'collection_config_type', 'collection_config_val'
                     'resolved']

_astobj_root_slots = ['source']




class SourceAstObj(object):
    '''
    The highest-level node in the AST, representing the string, file, or
    stream in which bespon data is embedded.

    In some cases, it would be possible to collapse the functionality of the
    source node and the root node into a single node.  The two are separated
    because this makes the handling of a tag for the root node more parallel
    with normal tags (the tag is external to the node).  Having a source
    node also makes it convenient to distinguish between where bespon content
    begins and ends, versus where the actual data begins and ends
    (for example, there may be comments before or after the data).
    '''
    basetype = 'source'

    def __init__(self, state):
        self.source = state.source
        self.source_depth = state.source_depth
        self.full_ast = state.full_ast

        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = state.first_lineno
        self.first_column = state.first_column
        self.last_lineno = state.last_lineno
        self.last_column = state.last_column

        self.root = None

    def check_append_root(self, root):
        if self.root is not None:
            raise erring.Bug('Only a single root-level node is allowed')
        root.parent = self
        self.root = root
        self.last_lineno = root.last_lineno
        self.last_column = root.last_column




class RootAstObj(list):
    '''
    Lowest level in the AST except for the source node.  A list subclass that
    must ultimately contain only a single element.
    '''
    basetype = 'root'

    def __init__(self, state):
        list.__init__(self)

        self.tag = state.root_tag
        self.closing_tag = None
        self.unresolved_child_count = 0

        self.indent = state.indent
        self.at_line_start = state.at_line_start
        self.inline = state.inline
        self.inline_indent = state.inline_indent
        self.first_lineno = state.first_lineno
        self.first_column = state.first_column
        self.last_lineno = state.last_lineno
        self.last_column = state.last_column

    def check_append_scalar_key(self, obj):
        raise erring.Bug('Only a single scalar or collection object is allowed at root level', obj)

    def check_append_scalar_val(self, obj, full_ast=False):
        if len(self) == 1:
            raise erring.ParseError('Only a single scalar or collection object is allowed at root level', obj)
        # May need to revise consistency checks once add full support for
        # embedded parsing
        if not obj.external_indent.startswith(self.indent):
            raise erring.IndentationError(obj)
        if obj.resolved and not full_ast:
            self.append(obj.final_val)
        else:
            obj.parent = self
            obj.index = len(self)
            self.append(obj)
            if not obj.resolved:
                self.unresolved_child_count += 1
        self.last_lineno = obj.last_lineno
        self.last_column = obj.last_column

    def check_append_collection(self, obj):
        if len(self) == 1:
            raise erring.ParseError('Only a single scalar or collection object is allowed at root level', obj)
        # May need to revise consistency checks once add full support for
        # embedded parsing
        if not obj.external_indent.startswith(self.indent):
            raise erring.IndentationError(obj)
        obj.parent = self
        obj.index = len(self)
        self.append(obj)
        self.unresolved_child_count += 1
        self.last_lineno = obj.last_lineno
        self.last_column = obj.last_column



def _init_common(self, state):
    '''
    Shared initialization for all AST nodes below root level.
    '''
    self.tag = state.tag
    state.tag = None

    self.indent = state.indent
    self.at_line_start = state.at_line_start
    self.inline = state.inline
    self.inline_indent = state.inline_indent
    self.first_lineno = state.first_lineno
    self.first_column = state.first_column
    self.last_lineno = state.last_lineno
    self.last_column = state.last_column

    if self.tag is None:
        # If there is no tag, the external appearance of the object is
        # identical to that of the object itself.  There is no need to
        # perform indentation checks, since these will be done when the
        # object is appended to the AST.
        self.external_indent = self.indent
        self.external_at_line_start = self.at_line_start
        self.external_first_lineno = self.first_lineno
    else:
        # If there is a tag, it sets the external appearance of the object.
        # The tag's indentation will be checked upon appending to the AST,
        # so it doesn't need to be checked.  But the object itself needs to
        # be checked here for consistency with the tag.
        #
        # In checking indentation, don't need to consider the case of
        # `.at_line_start = False` due to a leading inline comment.  In
        # non-inline mode, the comment parser automatically produces an error
        # for that case.
        #
        # For non-inline collections, there is no need to check for a first
        # element that is on the same line as the tag.  In a list, the `*`
        # will check for `.at_line_start = True`.  In a dict, a key will
        # perform the same check.  It is necessary to make sure that the tag
        # is at the beginning of the line, though.
        tag = self.tag
        if self.basetype not in tag.compatible_basetypes:
            raise erring.TagError(tag)
        if self.inline:
            if not self.indent.startswith(self.inline_indent):
                raise erring.IndentationError(self)
        elif tag.at_line_start:
            if not self.indent.startswith(tag.indent):
                raise erring.IndentationError(self)
        else:
            if self.at_line_start and (len(self.indent) <= len(tag.indent) or not self.indent.startswith(tag.indent)):
                raise erring.IndentationError(self)
            if self.basetype in ('dict', 'list'):
                raise erring.ParseError('The tag for a non-inline collection must be at the start of a line', tag)
        self.external_indent = tag.indent
        self.external_at_line_start = tag.at_line_start
        self.external_first_lineno = tag.first_lineno

    self.resolved = False
    self.extra_dependents = None
    # Some attributes are not given default values, to ensure that any
    # incorrect attempt to access them results in an error.  `.parent`
    # and `.index` exist for all objects except for dict keys.  `.final_val`
    # should only ever be accessed after a check of `.resolved`.




class ScalarAstObj(object):
    '''
    Scalar object, including quoted (delim, block) and unquoted strings,
    none, bool, int, and float.
    '''
    basetype = 'scalar'
    __slots__ = (_astobj_common_slots + _astobj_scalar_or_collection_slots +
                 _astobj_scalar_slots)

    def __init__(self, state, init_common=_init_common,
                 delim=None, block=None, implicit_type=None):
        init_common(self, state)
        self.delim = delim
        self.block = block
        self.implicit_type = implicit_type

    def __hash__(self):
        # The only time a scalar will need a hash is when it is used as a
        # dict key, and in that case it must already be resolved.
        return hash(self.final_val)

    def __eq__(self, other):
        return self.final_val == other.final_val


# Individual element in a keypath
KeypathElement = collections.namedtuple('KeypathElement', ['type', 'val'])


class Keypath(ScalarAstObj):
    '''
    Abstract keypath.

    Used as dict keys or in sections for assigning in nested objects; in
    tag for representing collection config; and (with a tag) to represent
    alias, copy, and deepcopy.
    '''
    basetype = 'keypath'
    __slots__ = ['keypath']




class ListlikeAstObj(list):
    '''
    List-like collection.
    '''
    basetype = 'list'
    __slots__ = (_astobj_common_slots + _astobj_scalar_or_collection_slots +
                 _astobj_collection_slots +
                 ['internal_indent_immediate, internal_indent_later'])

    def __init__(self, state, init_common=_init_common,
                 keypath_parent=None, keypath_traversable=False):
        list.__init__(self)

        self.keypath_parent = keypath_parent
        self.keypath_travesable = keypath_traversable
        self.unresolved_child_count = 0
        if keypath_traversable:
            # A collection created implicitly as part of a keypath lacks most
            # standard attributes, so they are never created.  There is no
            # need to check for an unused `state.tag`, because the only way
            # to create an implicit collection is with a keypath, and a
            # keypath would resolve any existing tag.  An implicit collection
            # is always open.
            self.open = True
        else:
            init_common(self, state)
            self.open = False
            if not self.inline:
                self.internal_indent_immediate = None
                self.internal_indent_later = None

        if self.inline:
            self.check_append_scalar_val = self._check_append_scalar_val_inline
            self.check_append_collection = self._check_append_collection_inline
        else:
            self.check_append_scalar_val = self._check_append_scalar_val_noninline
            self.check_append_collection = self._check_append_collection_noninline

    def check_append_scalar_key(self, obj, full_ast=False):
        raise erring.ParseError('Cannot append a key-value pair directly to a list-like object', obj)

    def _check_append_scalar_val_inline(self, obj, full_ast=False):
        if not self.open:
            raise erring.ParseError('Cannot append to a list-like object that was not open for appending', obj)
        if not obj.external_indent.startswith(self.inline_indent):
            raise erring.IndentationError(obj)
        if obj.resolved and not full_ast:
            self.append(obj.final_val)
        else:
            obj.parent = self
            obj.index = len(self)
            self.append(obj)
            if not obj.resolved:
                self.unresolved_child_count += 1
        self.last_lineno = obj.last_lineno
        self.last_column = obj.last_column
        self.open = False

    def _check_append_collection_inline(self, obj):
        if not self.open:
            raise erring.ParseError('Cannot append to a list-like object that was not open for appending', obj)
        if not obj.external_indent.startswith(self.inline_indent):
            raise erring.IndentationError(obj)
        obj.parent = self
        obj.index = len(self)
        self.append(obj)
        self.unresolved_child_count += 1
        self.last_lineno = obj.last_lineno
        self.last_column = obj.last_column
        self.open = False

    def _set_internal_indent(self, obj):
        if len(obj.external_indent) <= len(self.indent) or not obj.external_indent.startswith(self.indent):
            raise erring.IndentationError(obj)
        extra_indent = obj.external_indent[len(self.indent):]
        if obj.external_first_lineno == self.last_lineno:
            # The non-inline list opener `*` does not affect `at_line_start`
            # and is treated as a space for the purpose of calculating the
            # overall indent of objects following it on the same line.  If
            # the `*` (which will be represented by a space in `self.indent`)
            # is adjacent to tabs on both sides, then it is not counted
            if self.indent.endswith('\t') and extra_indent[1:2] == '\t':
                self.internal_indent_immediate = obj.external_indent
                self.internal_indent_later = self.indent + extra_indent[1:]
            else:
                self.internal_indent_immediate = self.internal_indent_later = obj.external_indent
        else:
            if self.indent.endswith('\t') and extra_indent[:1] == '\t':
                self.internal_indent_immediate = self.indent + '\x20' + extra_indent
                self.internal_indent_later = obj.external_indent
            else:
                self.internal_indent_immediate = self.internal_indent_later = obj.external_indent

    def _check_append_scalar_val_noninline(self, obj, full_ast=False):
        if not self.open:
            raise erring.ParseError('Cannot append to a list-like object that was not open for appending', obj)
        if self.internal_indent_immediate is None:
            self._set_internal_indent(obj)
        if obj.first_lineno == self.last_lineno:
            if obj.external_indent != self.internal_indent_immediate:
                raise erring.IndentationError(obj)
        elif obj.external_indent != self.internal_indent_later:
            raise erring.IndentationError(obj)
        if obj.resolved and not full_ast:
            self.append(obj.final_val)
        else:
            obj.parent = self
            obj.index = len(self)
            self.append(obj)
            if not obj.resolved:
                self.unresolved_child_count += 1
        self.last_lineno = obj.last_lineno
        self.last_column = obj.last_column
        self.open = False

    def _check_append_collection_noninline(self, obj):
        if not self.open:
            raise erring.ParseError('Cannot append to a list-like object that was not open for appending', obj)
        if self.internal_indent_immediate is None:
            self._set_internal_indent(obj)
        if obj.first_lineno == self.last_lineno:
            if obj.external_indent != self.internal_indent_immediate:
                raise erring.IndentationError(obj)
        elif obj.external_indent != self.internal_indent_later:
            raise erring.IndentationError(obj)
        obj.parent = self
        obj.index = len(self)
        self.append(obj)
        self.unresolved_child_count += 1
        self.last_lineno = obj.last_lineno
        self.last_column = obj.last_column
        self.open = False



class DictlikeAstObj(collections.OrderedDict):
    '''
    Dict-like collection.
    '''
    basetype = 'dict'
    __slots__ = (_astobj_common_slots + _astobj_scalar_or_collection_slots +
                 _astobj_collection_slots + ['awaiting_val', 'next_key'])

    def __init__(self, state, init_common=_init_common,
                 keypath_parent=None, keypath_traversable=False):
        collections.OrderedDict.__init__(self)

        self.keypath_parent = keypath_parent
        self.keypath_travesable = keypath_traversable
        self.unresolved_child_count = 0
        if keypath_traversable:
            # A collection created implicitly as part of a keypath lacks most
            # standard attributes, so they are never created.  There is no
            # need to check for an unused `state.tag`, because the only way
            # to create an implicit collection is with a keypath, and a
            # keypath would resolve any existing tag.  An implicit collection
            # is always open.
            self.open = True
        else:
            init_common(self, state)
            self.open = False
        self.awaiting_key = False
        self.next_key = None

        if self.inline:
            self.check_append_scalar_key = self._check_append_scalar_key_inline
            self.check_append_scalar_val = self._check_append_scalar_val_inline
            self.check_append_collection = self._check_append_collection_inline
        else:
            self.check_append_scalar_key = self._check_append_scalar_key_noninline
            self.check_append_scalar_val = self._check_append_scalar_val_noninline
            self.check_append_collection = self._check_append_collection_noninline

    def _check_append_scalar_key_inline(self, obj, full_ast=False):
        if not obj.external_indent.startswith(self.inline_indent):
            raise erring.IndentationError(obj)
        if not self.open:
            raise erring.ParseError('Cannot add a key to a closed object; perhaps a comma is missing', obj)
        if self.awaiting_key:
            raise erring.ParseError('Cannot add a key until the previous key has been given a value', obj)
        if obj.basetype != 'scalar':
            raise erring.ParseError('Dict-like objects only take scalar types as keys', obj)
        if obj.final_val in self:
            raise erring.ParseError('Duplicate keys are prohibited', obj)
        self.awaiting_key = True
        if full_ast:
            self.next_key = obj
        else:
            self.next_key = obj.final_val













_astobj_tag_slots = ['type', 'label', 'newline',
                     'collection_config_type', 'collection_config_val'
                     'resolved']






class DictlikeAstObj(collections.OrderedDict):
    __slots__ = (_astobj_common_slots + _astobj_scalar_or_collection_slots +
                 _astobj_collection_slots + _astobj_dict_slots)
    def __init__(self, state):
        pass




class TagAstObj(object):
    __slots__ = _astobj_common_slots + _astobj_tag_slots
    def __init__(self, state):
        pass





