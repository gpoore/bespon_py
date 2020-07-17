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
from . import encoding
from . import load_types
from . import decoding

if sys.version_info.major == 2:
    str = unicode


_DEFAULT_DECODER = decoding.BespONDecoder()




def load_roundtrip_ast(fp, cls=None, **kwargs):
    '''
    Load data from a file-like object into RoundtripAst.
    '''
    encoder = kwargs.pop('encoder', None)
    enforce_types = kwargs.pop('enforce_types', None)
    if 'empty_default' in kwargs:
        raise NotImplementedError('Keyword argument "empty_default" is not supported for roundtrip use')
    if cls is None:
        if not kwargs:
            ast = _DEFAULT_DECODER.decode_to_ast(fp.read())
        else:
            ast = decoding.BespONDecoder(**kwargs).decode_to_ast(fp.read())
    else:
        ast = cls(**kwargs).decode_to_ast(fp.read())
    return RoundtripAst(ast, encoder=encoder, enforce_types=enforce_types)


def loads_roundtrip_ast(s, cls=None, **kwargs):
    '''
    Load data from a Unicode string into RoundtripAst.
    '''
    encoder = kwargs.pop('encoder', None)
    enforce_types = kwargs.pop('enforce_types', None)
    if 'empty_default' in kwargs:
        raise NotImplementedError('Keyword argument "empty_default" is not supported for roundtrip use')
    if cls is None:
        if not kwargs:
            ast = _DEFAULT_DECODER.decode_to_ast(s)
        else:
            ast = decoding.BespONDecoder(**kwargs).decode_to_ast(s)
    else:
        ast = cls(**kwargs).decode_to_ast(s)
    return RoundtripAst(ast, encoder=encoder, enforce_types=enforce_types)




class AstView(object):
    '''
    Abstract view of a location in the AST.
    '''
    __slots__ = ['_ast', '_node', '_modified_value']

    def __init__(self, ast, node):
        self._ast = ast
        self._node = node
        self._modified_value = False


    @property
    def implicit_type(self):
        return self._node.implicit_type

    @property
    def type(self):
        tag = self._node.tag
        if tag is not None and tag.type is not None:
            return tag.type
        return self._node.implicit_type


    @property
    def key(self):
        if self._node.parent.implicit_type != 'dict':
            raise AttributeError('Keys only exist in dict-like objects')
        return self._node.index

    @key.setter
    def key(self, key):
        if self._node.parent.implicit_type != 'dict':
            raise AttributeError('Keys only exist in dict-like objects')
        self._ast._replace_key_at_pos(self._node.parent, self._node.index, key)


    @property
    def key_doc_comment(self):
        if self._node.parent.implicit_type != 'dict':
            raise AttributeError('Keys only exist in dict-like objects')
        doc_comment_node = self._node.parent.key_nodes[self._node.index].doc_comment
        if doc_comment_node is None:
            return None
        return doc_comment_node.final_val

    @key_doc_comment.setter
    def key_doc_comment(self, val):
        if self._node.parent.implicit_type != 'dict':
            raise AttributeError('Keys only exist in dict-like objects')
        doc_comment_node = self._node.parent.key_nodes[self._node.index].doc_comment
        if doc_comment_node is None:
            raise NotImplementedError('Adding doc comments where they do not yet exist is not currently supported')
        self._ast._replace_doc_comment_at_pos(doc_comment_node, val)


    @property
    def key_trailing_comment(self):
        if self._node.parent.implicit_type != 'dict':
            raise AttributeError('Keys only exist in dict-like objects')
        trailing_comment_node = self._node.parent.key_nodes[self._node.index].trailing_comment
        if trailing_comment_node is None:
            return None
        return trailing_comment_node.final_val

    @key_trailing_comment.setter
    def key_trailing_comment(self, val):
        if self._node.parent.implicit_type != 'dict':
            raise AttributeError('Keys only exist in dict-like objects')
        trailing_comment_node = self._node.parent.key_nodes[self._node.index].trailing_comment
        if trailing_comment_node is None:
            raise NotImplementedError('Adding trailing comments where they do not yet exist is not currently supported')
        self._ast._replace_trailing_comment_at_pos(trailing_comment_node, val)


    @property
    def value(self):
        if self._node.implicit_type == 'alias':
            if self._node.target_node.implicit_type in ('dict', 'list'):
                raise AttributeError('Values for aliased collection types are not accessible')
            return self._node.target_node.final_val
        return self._node.final_val

    @value.setter
    def value(self, val):
        if self._node.implicit_type == 'alias':
            raise AttributeError('Aliased values cannot be assigned through the alias; assign them directly')
        self._modified_value = True
        self._ast._replace_val_at_pos(self._node, val)


    @property
    def value_doc_comment(self):
        doc_comment_node = self._node.doc_comment
        if doc_comment_node is None:
            return None
        return doc_comment_node.final_val

    @value_doc_comment.setter
    def value_doc_comment(self, val):
        doc_comment_node = self._node.doc_comment
        if doc_comment_node is None:
            raise NotImplementedError('Adding doc comments where they do not yet exist is not currently supported')
        self._ast._replace_doc_comment_at_pos(doc_comment_node, val)



class ScalarAstView(AstView):
    __slots__ = []

    @property
    def value_trailing_comment(self):
        trailing_comment_node = self._node.trailing_comment
        if trailing_comment_node is None:
            return None
        return trailing_comment_node.final_val

    @value_trailing_comment.setter
    def value_trailing_comment(self, val):
        trailing_comment_node = self._node.trailing_comment
        if trailing_comment_node is None:
            raise NotImplementedError('Adding trailing comments where they do not yet exist is not currently supported')
        self._ast._replace_trailing_comment_at_pos(trailing_comment_node, val)


_ast_view_by_implicit_type = {}


class DictAstView(AstView):
    __slots__ = []
    _ast_view_by_implicit_type = _ast_view_by_implicit_type

    def __getitem__(self, subscript):
        if self._modified_value:
            raise NotImplementedError('Accessing replaced dict-like objects is not currently supported')
        sub_node = self._node[subscript]
        sub_node_view = sub_node.view
        if sub_node_view is None:
            view = self._ast_view_by_implicit_type[sub_node.implicit_type](self._ast, sub_node)
            sub_node.view = view
            return view
        return sub_node_view


    def __len__(self):
        return len(self._node)


    def __iter__(self):
        return iter(self._node)


    def items(self):
        return ((key, self[key]) for key in self)


    @property
    def value_start_trailing_comment(self):
        trailing_comment_node = self._node.start_trailing_comment
        if trailing_comment_node is None:
            return None
        return trailing_comment_node.final_val

    @value_start_trailing_comment.setter
    def value_start_trailing_comment(self, val):
        trailing_comment_node = self._node.start_trailing_comment
        if trailing_comment_node is None:
            raise NotImplementedError('Adding trailing comments where they do not yet exist is not currently supported')
        self._ast._replace_trailing_comment_at_pos(trailing_comment_node, val)


    @property
    def value_end_trailing_comment(self):
        trailing_comment_node = self._node.end_trailing_comment
        if trailing_comment_node is None:
            return None
        return trailing_comment_node.final_val

    @value_end_trailing_comment.setter
    def value_end_trailing_comment(self, val):
        trailing_comment_node = self._node.end_trailing_comment
        if trailing_comment_node is None:
            raise NotImplementedError('Adding trailing comments where they do not yet exist is not currently supported')
        self._ast._replace_trailing_comment_at_pos(trailing_comment_node, val)


class ListAstView(AstView):
    __slots__ = []
    _ast_view_by_implicit_type = _ast_view_by_implicit_type

    def __getitem__(self, subscript):
        if self._modified_value:
            raise NotImplementedError('Accessing replaced list-like objects is not currently supported')
        sub_node = self._node[subscript]
        sub_node_view = sub_node.view
        if sub_node_view is None:
            view = self._ast_view_by_implicit_type[sub_node.implicit_type](self._ast, sub_node)
            sub_node.view = view
            return view
        return sub_node_view


    def __len__(self):
        return len(self._node)


    def __iter__(self):
        return (self[n] for n in range(len(self)))


    @property
    def value_start_trailing_comment(self):
        trailing_comment_node = self._node.start_trailing_comment
        if trailing_comment_node is None:
            return None
        return trailing_comment_node.final_val

    @value_start_trailing_comment.setter
    def value_start_trailing_comment(self, val):
        trailing_comment_node = self._node.start_trailing_comment
        if trailing_comment_node is None:
            raise NotImplementedError('Adding trailing comments where they do not yet exist is not currently supported')
        self._ast._replace_trailing_comment_at_pos(trailing_comment_node, val)


    @property
    def value_end_trailing_comment(self):
        trailing_comment_node = self._node.end_trailing_comment
        if trailing_comment_node is None:
            return None
        return trailing_comment_node.final_val

    @value_end_trailing_comment.setter
    def value_end_trailing_comment(self, val):
        trailing_comment_node = self._node.end_trailing_comment
        if trailing_comment_node is None:
            raise NotImplementedError('Adding trailing comments where they do not yet exist is not currently supported')
        self._ast._replace_trailing_comment_at_pos(trailing_comment_node, val)


for implicit_type in load_types.IMPLICIT_SCALAR_TYPES:
    _ast_view_by_implicit_type[implicit_type] = ScalarAstView
_ast_view_by_implicit_type['dict'] = DictAstView
_ast_view_by_implicit_type['list'] = ListAstView




class RoundtripAst(object):
    '''
    Abstract representation of loaded data that may be modified and then
    encoded to produce a minimal diff compared to the original source.
    '''
    def __init__(self, ast, encoder=None, enforce_types=None):
        self.source = ast.source
        self.source_name = self.source.source_name
        self.root = ast.root
        self._view = _ast_view_by_implicit_type[ast.root[0].implicit_type](self, ast.root[0])
        self.source_lines = ast.source_lines
        self.max_nesting_depth = ast.max_nesting_depth
        self.scalar_nodes = ast.scalar_nodes
        self.line_comments = ast.line_comments

        if encoder is None:
            self.encoder = encoding.BespONEncoder()
        elif isinstance(encoder, encoding.BespONEncoder):
            self.encoder = encoder
        else:
            raise TypeError
        if enforce_types is None:
            self.enforce_types = True
        elif enforce_types in (True, False):
            self.enforce_types = enforce_types
        else:
            raise TypeError

        # Need a way to see what objects are on a line.  Since objects are
        # added to `scalar_nodes` as created, they are already sorted.  Since
        # line comments are always last on a line, if they are added after all
        # other objects, then sorting is preserved.
        objects_starting_on_line = collections.defaultdict(list)
        for obj in self.scalar_nodes:
            objects_starting_on_line[obj.first_lineno].append(obj)
        for obj in self.line_comments:
            objects_starting_on_line[obj.first_lineno].append(obj)
        self._objects_starting_on_line = objects_starting_on_line

        last_node_on_line = {}
        for node in self._iter_nodes():
            if node.implicit_type not in ('dict', 'list', 'tag'):
                if node.last_lineno not in last_node_on_line:
                    last_node_on_line[node.last_lineno] = node
                else:
                    other_node = last_node_on_line[node.last_lineno]
                    if node.last_colno > other_node.last_colno:
                        last_node_on_line[node.last_lineno] = node
            elif node.inline:
                if node.last_lineno not in last_node_on_line:
                    last_node_on_line[node.last_lineno] = node
                else:
                    other_node = last_node_on_line[node.last_lineno]
                    if node.last_colno > other_node.last_colno:
                        last_node_on_line[node.last_lineno] = node
                if node.first_lineno == node.last_lineno:
                    continue
                elif node.first_lineno not in last_node_on_line:
                    last_node_on_line[node.first_lineno] = node
                else:
                    other_node = last_node_on_line[node.first_lineno]
                    if other_node.implicit_type not in ('dict', 'list', 'tag'):
                        if node.first_colno > other_node.last_colno:
                            last_node_on_line[node.first_lineno] = node
                    elif ((node.first_lineno == other_node.last_lineno and node.first_colno > other_node.last_colno) or
                            node.first_colno > other_node.first_colno):
                        last_node_on_line[node.first_lineno] = node

        for comment_node in self.line_comments:
            if comment_node.first_lineno in last_node_on_line:
                node = last_node_on_line[comment_node.first_lineno]
                if node.implicit_type in ('int', 'float', 'complex', 'rational', 'str'):
                    node.trailing_comment = comment_node
                elif node.implicit_type in ('dict', 'list'):
                    if node.last_lineno == comment_node.first_lineno:
                        node.end_trailing_comment = comment_node
                    else:
                        node.start_trailing_comment = comment_node


        self._replacements = {}


    def __getitem__(self, subscript):
        return self._view[subscript]


    def __len__(self):
        return len(self._view)


    def __iter__(self):
        return iter(self._view)


    def __getattr__(self, name):
        return getattr(self._view, name)


    def _iter_nodes(self):
        return self._iter_node(self.root[0])


    def _iter_node(self, node):
        if node.implicit_type not in ('doc_comment', 'tag'):
            if node.doc_comment is not None:
                yield node.doc_comment
            if node.tag is not None:
                yield node.tag
        yield node
        if node.implicit_type == 'dict':
            for k, v in zip(node.key_nodes.values(), node.values()):
                for x in self._iter_node(k):
                    yield x
                for x in self._iter_node(v):
                    yield x
        elif node.implicit_type == 'list':
            for v in node:
                for x in self._iter_node(v):
                    yield x


    def replace_val(self, path, obj):
        '''
        Replace a value in the AST.
        '''
        if not isinstance(path, list) and not isinstance(path, tuple):
            raise TypeError('Path to value must be a list or tuple of dict keys/list indices')
        pos = self.root[0]
        for k in path:
            pos = pos[k]
        self._replace_val_at_pos(pos, obj)


    def _replace_val_at_pos(self, pos, obj):
        if pos.tag is not None:
            raise TypeError('Value replacement is not currently supported for tagged objects')
        if self.enforce_types and type(obj) != type(pos.final_val) and not (self.encoder.baseclass and issubclass(type(obj), type(pos.final_val))):
            raise TypeError('Value replacement is only allowed for values of the same type (enforce_types=True); trying to replace {0} with {1}'.format(type(pos.final_val), type(obj)))
        if pos.implicit_type in ('dict', 'list'):
            encoded_val = self.encoder.partial_encode(obj, flush_margin=pos.parent.implicit_type == 'list',
                                                      after_start_list_item=not pos.inline and pos.parent.implicit_type == 'list',
                                                      inline=pos.inline, at_line_start=pos.at_line_start, indent=pos.indent,
                                                      initial_nesting_depth=pos.nesting_depth)
        else:
            encoded_val = self.encoder.partial_encode(obj, flush_margin=pos.parent.implicit_type == 'list',
                                                      after_start_list_item=not pos.inline and pos.parent.implicit_type == 'list',
                                                      inline=pos.inline, at_line_start=pos.at_line_start, indent=pos.indent,
                                                      delim=pos.delim, block=pos.block, num_base=pos.num_base)
            if isinstance(obj, str) and self.encoder.bidi_rtl_re.search(encoded_val) is not None and self.encoder.bidi_rtl_re.search(pos.raw_val) is None:
                if pos.first_colno < self._objects_starting_on_line[pos.first_lineno][-1].first_colno:
                    raise ValueError('Replacing strings that do not contain right-to-left code points with strings that do contain them is currently not supported when this would require reformatting to avoid a following object on the same line')
        pos.final_val = obj
        if pos.implicit_type not in ('dict', 'list'):
            pos.raw_val = encoded_val
        if hasattr(pos, 'index'):
            pos.parent.final_val[pos.index] = obj
        self._replacements[(pos.first_lineno, pos.first_colno, pos.last_lineno, pos.last_colno)] = encoded_val


    def replace_key(self, path, obj):
        '''
        Replace a key in the AST.
        '''
        if not isinstance(path, list) and not isinstance(path, tuple):
            raise TypeError('Path to key must be a list or tuple of dict keys/list indices')
        pos = self.root[0]
        for k in path[:-1]:
            pos = pos[k]
        # Must check type of collection object, given that the key extraction
        # method could also work on a list.
        if not isinstance(pos, dict):
            raise TypeError('Key replacement is only possible for dicts')
        key = path[-1]
        self._replace_key_at_pos(pos, key, obj)


    def _replace_key_at_pos(self, pos, key, obj):
        current_dict = pos
        pos = pos.key_nodes[key]
        if pos.tag is not None:
            raise TypeError('Key replacement is not currently supported for tagged objects')
        if self.enforce_types and type(obj) != type(pos.final_val) and not (self.encoder.baseclass and issubclass(type(obj), type(pos.final_val))):
            raise TypeError('Key replacement is only allowed for keys of the same type (enforce_types=True); trying to replace {0} with {1}'.format(type(pos.final_val), type(obj)))
        key_path = False if pos.key_path is None else True
        encoded_val = self.encoder.partial_encode(obj,
                                                  inline=pos.inline, at_line_start=pos.at_line_start, indent=pos.indent,
                                                  key=True, key_path=key_path,
                                                  delim=pos.delim, block=pos.block, num_base=pos.num_base)
        if isinstance(obj, str) and self.encoder.bidi_rtl_re.search(encoded_val) is not None and self.encoder.bidi_rtl_re.search(pos.raw_val) is None:
            if pos.first_colno < self._objects_starting_on_line[pos.first_lineno][-1].first_colno:
                raise ValueError('Replacing strings that do not contain right-to-left code points with strings that do contain them is currently not supported when this would require reformatting to avoid a following object on the same line')
        # Need to update the dict so that the key ordering is kept, the new
        # key is recognized as a key, and the old key is removed.  The
        # easiest way to do this while keeping all dict attributes and all
        # existing references to the dict is to remove all keys, change the
        # key object, and then add everything back again.
        current_dict_kv_pairs = [(k, v) for k, v in current_dict.items()]
        for k, v in current_dict_kv_pairs:
            del current_dict[k]
        pos.final_val = obj
        pos.raw_val = encoded_val
        for k, v in current_dict_kv_pairs:
            if k == key:
                if hasattr(v, 'index'):
                    v.index = obj
                current_dict[obj] = v
            else:
                current_dict[k] = v
        # The dict of key nodes isn't ordered and has no special attributes,
        # so it's simpler to update.
        del current_dict.key_nodes[key]
        current_dict.key_nodes[obj] = pos
        self._replacements[(pos.first_lineno, pos.first_colno, pos.last_lineno, pos.last_colno)] = encoded_val
        # The key path nodes aren't being updated, since they aren't being
        # used directly, and the relevant changes are covered (at least for
        # now) by modifying the individual key path elements.
        if pos.key_path_occurrences is not None:
            for occ in pos.key_path_occurrences:
                self._replacements[(occ.first_lineno, occ.first_colno, occ.last_lineno, occ.last_colno)] = encoded_val


    def _replace_doc_comment_at_pos(self, pos, obj):
        if not isinstance(obj, str):
            raise TypeError
        continuation_indent = pos.continuation_indent
        if continuation_indent is None:
            if pos.at_line_start:
                continuation_indent = pos.indent
            else:
                continuation_indent = pos.indent + self.encoder.nesting_indent
        encoded_val = self.encoder.partial_encode(obj, dtype='doc_comment', indent=continuation_indent, delim=pos.delim, block=pos.block)
        self._replacements[(pos.first_lineno, pos.first_colno, pos.last_lineno, pos.last_colno)] = encoded_val


    def _replace_trailing_comment_at_pos(self, pos, obj):
        if not isinstance(obj, str):
            raise TypeError
        encoded_val = self.encoder.partial_encode(obj, dtype='line_comment')
        self._replacements[(pos.first_lineno, pos.first_colno, pos.last_lineno, pos.last_colno)] = encoded_val


    def dumps(self):
        '''
        Return the modified data as a string.
        '''
        new_source = []
        prev_last_lineno = self.source.first_lineno
        # Back up by one column, to be before start of content
        prev_last_colno = self.source.first_colno - 1
        source_lines = self.source_lines
        len_source_lines = len(source_lines)
        len_source = sum(len(x) for x in source_lines)
        for (first_lineno, first_colno, last_lineno, last_colno), encoded_val in sorted(self._replacements.items(), key=lambda x: (x[0][0], x[0][1], len_source_lines-x[0][2], len_source-x[0][3])):
            # Note that all `lineno` and `colno` are 1-indexed to agree with
            # text editors, so that must be corrected in indexing operations.
            if last_lineno < prev_last_lineno or (last_lineno == prev_last_lineno and last_colno <= prev_last_colno):
                # Could have modified a value inside a collection, then
                # replaced the collection
                continue
            elif first_lineno == prev_last_lineno:
                new_source.append(source_lines[first_lineno-1][prev_last_colno:first_colno-1])
            else:
                new_source.append(source_lines[prev_last_lineno-1][prev_last_colno:] + '\n')
                for lineno in range(prev_last_lineno + 1, first_lineno):
                    new_source.append(source_lines[lineno-1] + '\n')
                new_source.append(source_lines[first_lineno-1][:first_colno-1])
            new_source.append(encoded_val)
            prev_last_lineno = last_lineno
            prev_last_colno = last_colno
        new_source.append(source_lines[prev_last_lineno-1][prev_last_colno:] + '\n')
        # Going up to, but not including, `source.last_lineno` is correct,
        # because `source.last_lineno` is always an empty line.  If a file
        # doesn't end with `\n`, it is treated as if it were, so that
        # `source.last_lineno` always refers to a line containing only an
        # empty string.
        for n in range(prev_last_lineno + 1, self.source.last_lineno):
            new_source.append(source_lines[n-1] + '\n')
        return ''.join(new_source)
