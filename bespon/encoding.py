# -*- coding: utf-8 -*-
#
# Copyright (c) 2016-2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


# pylint:  disable = C0301

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)


import re
from . import escape
from . import grammar




class BespONEncoder(object):
    '''
    Encode BespON.  This is a very basic encoder using indentation-style
    syntax.
    '''
    def __init__(self):
        self._indent_per_level = '\x20\x20\x20\x20'

        self._escape = escape.Escape()
        self._escape_unicode = self._escape.escape_unicode

        unquoted_string_pattern = r'(?!{reserved_word}$)(?:{unquoted_key}|{number_unit})$'
        self._unquoted_str_re = re.compile(unquoted_string_pattern.format(reserved_word=grammar.RE_GRAMMAR['reserved_word'],
                                                                          unquoted_key=grammar.RE_GRAMMAR['unquoted_key_ascii'],
                                                                          number_unit=grammar.RE_GRAMMAR['unquoted_dec_number_unit_ascii']))

        self._line_terminator_re = re.compile(grammar.RE_GRAMMAR['line_terminator_unicode'])

        self._bidi_rtl_re = re.compile(grammar.RE_GRAMMAR['bidi_rtl'])
        self._last_scalar_bidi_rtl = False

        self._encode_funcs = {type(None): self._encode_none,
                              type(True): self._encode_bool,
                              type(1): self._encode_int,
                              type(1.0): self._encode_float,
                              type('a'): self._encode_str,
                              type([]): self._encode_list,
                              type({}): self._encode_dict}

        self._collection_types = set([type([]), type({})])


    def _encode_none(self, obj, indent, key=False, val=False):
        return 'none'


    def _encode_bool(self, obj, indent, key=False, val=False):
        return 'true' if obj else 'false'


    def _encode_int(self, obj, indent, key=False, val=False):
        return str(obj)


    def _encode_float(self, obj, indent, key=False, val=False):
        if key:
            raise TypeError('Floats are not supported as dict keys')
        return str(obj)


    def _encode_str(self, obj, indent, key=False, val=False):
        if self._bidi_rtl_re.search(obj):
            self._last_scalar_bidi_rtl = True
        if self._unquoted_str_re.match(obj):
            return obj
        if not self._line_terminator_re.search(obj):
            if '"' not in obj:
                return '"{0}"'.format(self._escape_unicode(obj, delim='"'))
            return '"""{0}"""'.format(self._escape_unicode(obj, delim='"', multidelim=True))
        obj_encoded = self._escape_unicode(obj, delim='"', multidelim=True)
        obj_encoded_lines = obj_encoded.splitlines(True)
        if obj_encoded_lines[-1] != '\n':
            obj_encoded_lines[-1] += '\\\n'
        if val:
            continuation_indent = indent + self._indent_per_level
            return '|"""\n{0}{1}|"""/'.format(''.join([continuation_indent + line for line in obj_encoded_lines]), continuation_indent)
        return '|"""\n{0}{1}|"""/'.format(''.join([indent + line for line in obj_encoded_lines]), indent)


    def _encode_list(self, lst, indent, key=False, val=False):
        if key:
            raise TypeError('Lists are not supported as dict keys')
        if not lst:
            yield '[]\n'
        first = True
        for elem in lst:
            if type(elem) == type(lst):
                if not elem:
                    if first:
                        first = False
                        yield '* []'
                    else:
                        yield indent + '* []'
                else:
                    yield indent + '*\n' + indent + '  '
                    for x in self._encode_funcs[type(elem)](elem, indent + '  '):
                        yield x
                    yield '\n'
            else:
                if first:
                    first = False
                    yield '* '
                else:
                    yield indent + '* '
                if type(elem) not in self._collection_types:
                    yield self._encode_funcs[type(elem)](elem, indent + '  ')
                else:
                    for x in self._encode_funcs[type(elem)](elem, indent + '  '):
                        yield x
                yield '\n'

    def _encode_dict(self, dct, indent, key=False, val=False):
        if key:
            raise TypeError('Dicts are not supported as dict keys')
        if not dct:
            yield '{}\n'
        else:
            first = True
            for k, v in dct.items():
                self._last_scalar_bidi_rtl = False
                if first:
                    first = False
                    yield self._encode_funcs[type(k)](k, indent, key=True)
                else:
                    yield indent + self._encode_funcs[type(k)](k, indent, key=True)
                yield ' ='
                if type(v) not in self._collection_types:
                    if self._last_scalar_bidi_rtl:
                        yield '\n' + indent + self._indent_per_level
                        yield self._encode_funcs[type(v)](v, indent + self._indent_per_level, val=True)
                    else:
                        yield ' '
                        yield self._encode_funcs[type(v)](v, indent + self._indent_per_level, val=True)
                else:
                    yield '\n' + indent + self._indent_per_level
                    for x in self._encode_funcs[type(v)](v, indent + self._indent_per_level, val=True):
                        yield x
                yield '\n'


    def iterencode(self, obj):
        if type(obj) in self._encode_funcs:
            if type(obj) in self._collection_types:
                return self._encode_funcs[type(obj)](obj, '')
            return self._encode_funcs[type(obj)](obj, '') + '\n'
        raise TypeError('Encoding type {0} is not supported'.format(type(obj)))


    def encode(self, obj):
        return ''.join(x for x in self.iterencode(obj))
