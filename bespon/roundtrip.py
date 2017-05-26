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
from .decoding import BespONDecoder

if sys.version_info.major == 2:
    str = unicode


_DEFAULT_DECODER = BespONDecoder()




def load_roundtrip_ast(fp, cls=None, **kwargs):
    '''
    Load data from a file-like object into RoundtripAst.
    '''
    if cls is None:
        if not kwargs:
            ast = _DEFAULT_DECODER.decode_to_ast(fp.read())
        else:
            ast = BespONDecoder(**kwargs).decode_to_ast(fp.read())
    else:
        ast = cls(**kwargs).decode_to_ast(fp.read())
    return RoundtripAst(ast)


def loads_roundtrip_ast(s, cls=None, **kwargs):
    '''
    Load data from a Unicode string into RoundtripAst.
    '''
    if cls is None:
        if not kwargs:
            ast = _DEFAULT_DECODER.decode_to_ast(s)
        else:
            ast = BespONDecoder(**kwargs).decode_to_ast(s)
    else:
        ast = cls(**kwargs).decode_to_ast(s)
    return RoundtripAst(ast)




class RoundtripAst(object):
    '''
    Abstract representation of loaded data that may be modified and then
    encoded to produce a minimal diff compared to the original source.
    '''
    def __init__(self, ast):
        self.source = ast.source
        self.source_name = self.source.source_name
        self.root = ast.root
        self.source_lines = ast.source_lines
        self.max_nesting_depth = ast.max_nesting_depth
        self.scalar_nodes = ast.scalar_nodes
        self.line_comments = ast.line_comments

        self.encoder = encoding.BespONEncoder()

        # Need a way to see what objects are on a line.  Since objects are
        # added to `scalar_nodes` as created, they are already sorted.  Since
        # line comments are always last on a line, if they are added after all
        # other objects, then sorting is preserved.
        objects_on_line = collections.defaultdict(list)
        for obj in self.scalar_nodes:
            objects_on_line[obj.first_lineno].append(obj)
        for obj in self.line_comments:
            objects_on_line[obj.first_lineno].append(obj)
        self.objects_on_line = objects_on_line

        self._replacements = {}


    def replace_val(self, path, obj):
        '''
        Replace a value in the AST.
        '''
        if isinstance(obj, dict) or isinstance(obj, list):
            raise TypeError('Replacing collections is not currently supported')
        if not isinstance(path, list) and not isinstance(path, tuple):
            raise TypeError('Path to value must be a list or tuple of dict keys/list indices')
        pos = self.root[0]
        for k in path:
            pos = pos[k]
        #if pos.tag is not None and [k for k in pos.tag if k not in ('type', 'label')]:
        #    raise TypeError('Value replacement is currently not supported for tagged objects when the tag does more than specify a type or label')
        if pos.tag is not None:
            raise TypeError('Value replacement is not currently supported for tagged objects')
        if type(pos.final_val) != type(obj):
            raise TypeError('Value replacement is only allowed for values of the same type; trying to replace {0} with {1}'.format(type(pos.final_val), type(obj)))
        continuation_indent = pos.continuation_indent
        if continuation_indent is None:
            if pos.at_line_start:
                continuation_indent = pos.indent
            else:
                continuation_indent = pos.indent + self.encoder.dict_indent_per_level
        encoded_val = self.encoder.encode_element(obj, continuation_indent,
                                                  delim=pos.delim, block=pos.block,
                                                  num_base=pos.num_base)
        if isinstance(obj, str) and self.encoder.bidi_rtl_re.search(encoded_val) is not None and self.encoder.bidi_rtl_re.search(pos.raw_val) is None:
            if pos.first_colno < self.objects_on_line[pos.first_lineno][-1].first_colno:
                raise ValueError('Replacing strings that do not contain right-to-left code points with strings that do contain them is currently not supported when this would require reformatting to avoid a following object on the same line')
        pos.final_val = obj
        pos.raw_val = encoded_val
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
        current_dict = pos
        old_key = path[-1]
        pos = pos.key_nodes[old_key]
        #if old_key.tag is not None and [k for k in pos.tag if k not in ('type', 'label')]:
        #    raise TypeError('Key replacement is currently not supported for tagged objects when the tag does more than specify a type or label')
        if pos.tag is not None:
            raise TypeError('Key replacement is not currently supported for tagged objects')
        if type(pos.final_val) != type(obj):
            raise TypeError('Key replacement is only allowed for keys of the same type; trying to replace {0} with {1}'.format(type(pos.final_val), type(obj)))
        key_path = False if pos.key_path is None else True
        continuation_indent = pos.continuation_indent
        if continuation_indent is None:
            if pos.at_line_start:
                continuation_indent = pos.indent
            else:
                continuation_indent = pos.indent + self.encoder.dict_indent_per_level
        encoded_val = self.encoder.encode_element(obj, continuation_indent,
                                                  key=True, key_path=key_path,
                                                  delim=pos.delim, block=pos.block,
                                                  num_base=pos.num_base)
        if isinstance(obj, str) and self.encoder.bidi_rtl_re.search(encoded_val) is not None and self.encoder.bidi_rtl_re.search(pos.raw_val) is None:
            if pos.first_colno < self.objects_on_line[pos.first_lineno][-1].first_colno:
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
            if k == old_key:
                if hasattr(v, 'index'):
                    v.index = obj
                current_dict[obj] = v
            else:
                current_dict[k] = v
        # The dict of key nodes isn't ordered and has no special attributes,
        # so it's simpler to update.
        del current_dict.key_nodes[old_key]
        current_dict.key_nodes[obj] = pos
        self._replacements[(pos.first_lineno, pos.first_colno, pos.last_lineno, pos.last_colno)] = encoded_val
        # The key path nodes aren't being updated, since they aren't being
        # used directly, and the relevant changes are covered (at least for
        # now) by modifying the individual key path elements.
        if pos.key_path_occurrences is not None:
            for occ in pos.key_path_occurrences:
                self._replacements[(occ.first_lineno, occ.first_colno, occ.last_lineno, occ.last_colno)] = encoded_val


    def dumps(self):
        '''
        Return the modified data as a string.
        '''
        new_source = []
        prev_last_lineno = self.source.first_lineno
        # Back up by one column, to be before start of content
        prev_last_colno = self.source.first_colno - 1
        source_lines = self.source_lines
        for (first_lineno, first_colno, last_lineno, last_colno), encoded_val in sorted(self._replacements.items(), key=lambda x: x[0]):
            # Note that all `lineno` and `colno` are 1-indexed to agree with
            # text editors, so that must be corrected in indexing operations.
            if first_lineno == prev_last_lineno:
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
