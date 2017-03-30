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
        self._dict_indent_per_level = '\x20\x20\x20\x20'
        self._list_indent_per_level = '\x20\x20'

        self._escape = escape.Escape()
        self._escape_unicode = self._escape.escape_unicode

        unquoted_string_pattern = r'(?!{reserved_word}$)(?:{unquoted_key}|{number_unit})\Z'
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

        self._dict_types = set([type({})])
        self._list_types = set([type([])])
        self._collection_types = self._dict_types | self._list_types
        self._scalar_types = set([k for k in self._encode_funcs if k not in self._collection_types])


    def _encode_none(self, obj, indent, key=False, val=False):
        self._last_scalar_bidi_rtl = False
        return 'none'


    def _encode_bool(self, obj, indent, key=False, val=False):
        self._last_scalar_bidi_rtl = False
        return 'true' if obj else 'false'


    def _encode_int(self, obj, indent, key=False, val=False):
        self._last_scalar_bidi_rtl = False
        return str(obj)


    def _encode_float(self, obj, indent, key=False, val=False):
        if key:
            raise TypeError('Floats are not supported as dict keys')
        self._last_scalar_bidi_rtl = False
        return str(obj)


    def _encode_str(self, obj, indent, key=False, val=False):
        if self._bidi_rtl_re.search(obj):
            self._last_scalar_bidi_rtl = True
        else:
            self._last_scalar_bidi_rtl = False
        if self._unquoted_str_re.match(obj):
            return obj
        if not self._line_terminator_re.search(obj):
            if '"' not in obj:
                return '"{0}"'.format(self._escape_unicode(obj, delim='"'))
            return '"""{0}"""'.format(self._escape_unicode(obj, delim='"', multidelim=True))
        obj_encoded = self._escape_unicode(obj, delim='"', multidelim=True)
        obj_encoded_lines = obj_encoded.splitlines(True)
        if obj_encoded_lines[-1][-1:] != '\n':
            obj_encoded_lines[-1] += '\\\n'
        return '|"""\n{0}{1}|"""/'.format(''.join([indent + line for line in obj_encoded_lines]), indent)


    def _encode_list(self, obj, indent, key=False, val=False):
        if key:
            raise TypeError('Lists are not supported as dict keys')
        if not obj:
            yield '[]\n'
        else:
            first = True
            for n, elem in enumerate(obj):
                type_elem = type(elem)
                if type_elem in self._list_types and elem:
                    if first:
                        yield '*\n' + indent + '  '
                        first = False
                    else:
                        yield indent + '*\n' + indent + '  '
                    for x in self._encode_funcs[type_elem](elem, indent + '  '):
                        yield x
                else:
                    if first:
                        yield '* '
                        first = False
                    else:
                        yield indent + '* '
                    if type_elem in self._scalar_types:
                        yield self._encode_funcs[type_elem](elem, indent + '  ')
                        yield '\n'
                    else:
                        for x in self._encode_funcs[type_elem](elem, indent + '  '):
                            yield x

    def _encode_dict(self, obj, indent, key=False, val=False):
        if key:
            raise TypeError('Dicts are not supported as dict keys')
        if not obj:
            yield '{}\n'
        else:
            first = True
            for k, v in obj.items():
                if first:
                    yield self._encode_funcs[type(k)](k, indent, key=True)
                    first = False
                else:
                    yield indent + self._encode_funcs[type(k)](k, indent, key=True)
                yield ' ='
                type_v = type(v)
                if type_v in self._scalar_types:
                    if self._last_scalar_bidi_rtl:
                        yield '\n' + indent + self._dict_indent_per_level
                    else:
                        yield ' '
                    yield self._encode_funcs[type_v](v, indent + self._dict_indent_per_level, val=True)
                    yield '\n'
                elif not v:
                    yield ' '
                    yield self._encode_funcs[type_v](v, indent + self._dict_indent_per_level, val=True)
                elif type_v in self._dict_types:
                    yield '\n' + indent + self._dict_indent_per_level
                    for x in self._encode_funcs[type_v](v, indent + self._dict_indent_per_level, val=True):
                        yield x
                elif type_v in self._list_types:
                    yield '\n' + indent + self._list_indent_per_level
                    for x in self._encode_funcs[type_v](v, indent + self._list_indent_per_level, val=True):
                        yield x
                else:
                    raise TypeError('Unsupported object of type {0}'.format(type_v))


    def iterencode(self, obj):
        if type(obj) in self._encode_funcs:
            if type(obj) in self._collection_types:
                return self._encode_funcs[type(obj)](obj, '')
            return self._encode_funcs[type(obj)](obj, '') + '\n'
        raise TypeError('Encoding type {0} is not supported'.format(type(obj)))


    def encode(self, obj):
        return ''.join(x for x in self.iterencode(obj))
