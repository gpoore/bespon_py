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


import sys
import re
from . import escape
from . import grammar

if sys.version_info.major == 2:
    str = unicode


NONE_TYPE = grammar.LIT_GRAMMAR['none_type']
BOOL_TRUE = grammar.LIT_GRAMMAR['bool_true']
BOOL_FALSE = grammar.LIT_GRAMMAR['bool_false']
OPEN_INDENTATION_LIST = grammar.LIT_GRAMMAR['open_indentation_list']
START_INLINE_DICT = grammar.LIT_GRAMMAR['start_inline_dict']
END_INLINE_DICT = grammar.LIT_GRAMMAR['end_inline_dict']
ASSIGN_KEY_VAL = grammar.LIT_GRAMMAR['assign_key_val']
START_INLINE_LIST = grammar.LIT_GRAMMAR['start_inline_list']
END_INLINE_LIST = grammar.LIT_GRAMMAR['end_inline_list']
ESCAPED_STRING_SINGLEQUOTE_DELIM = grammar.LIT_GRAMMAR['escaped_string_singlequote_delim']
ESCAPED_STRING_DOUBLEQUOTE_DELIM = grammar.LIT_GRAMMAR['escaped_string_doublequote_delim']
LITERAL_STRING_DELIM = grammar.LIT_GRAMMAR['literal_string_delim']
BLOCK_PREFIX = grammar.LIT_GRAMMAR['block_prefix']
BLOCK_SUFFIX = grammar.LIT_GRAMMAR['block_suffix']




class BespONEncoder(object):
    '''
    Encode BespON.  This is a very basic encoder using indentation-style
    syntax.
    '''
    def __init__(self):
        self.dict_indent_per_level = '\x20\x20\x20\x20'
        self.list_indent_per_level = '\x20\x20'

        self._escape = escape.Escape()
        self._escape_unicode = self._escape.escape_unicode
        self._invalid_literal_unicode_re = self._escape.invalid_literal_unicode_re
        self._invalid_literal_bytes_re = self._escape.invalid_literal_bytes_re

        # Unquoted strings containing single spaces are currently not used.
        unquoted_string_pattern = r'(?!{reserved_word}$)(?:(?P<key>{unquoted_key})|(?P<number_unit>{number_unit}))\Z'
        self._unquoted_str_re = re.compile(unquoted_string_pattern.format(reserved_word=grammar.RE_GRAMMAR['reserved_word'],
                                                                          unquoted_key=grammar.RE_GRAMMAR['unquoted_key_ascii'],
                                                                          number_unit=grammar.RE_GRAMMAR['unquoted_dec_number_unit_ascii']))

        self._line_terminator_re = re.compile(grammar.RE_GRAMMAR['line_terminator_unicode'])

        self.bidi_rtl_re = re.compile(grammar.RE_GRAMMAR['bidi_rtl'])
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


    def _encode_none(self, obj, indent, key=False, key_path=False, val=False,
                     none_type=NONE_TYPE):
        self._last_scalar_bidi_rtl = False
        return none_type


    def _encode_bool(self, obj, indent, key=False, key_path=False, val=False,
                     bool_true=BOOL_TRUE, bool_false=BOOL_FALSE):
        self._last_scalar_bidi_rtl = False
        return bool_true if obj else bool_false


    def _encode_int(self, obj, indent, key=False, key_path=False, val=False, num_base=None):
        if key_path:
            raise TypeError('Ints are not supported in key paths')
        self._last_scalar_bidi_rtl = False
        if num_base is not None and num_base != 10:
            if num_base == 16:
                return '0x{0:0x}'.format(obj)
            if num_base == 8:
                return '0o{0:0o}'.format(obj)
            if num_base == 2:
                return '0b{0:0b}'.format(obj)
            raise ValueError('Unknown base {0}'.format(num_base))
        return str(obj)


    def _encode_float(self, obj, indent, key=False, key_path=False, val=False, num_base=None):
        if key:
            raise TypeError('Floats are not supported as dict keys')
        self._last_scalar_bidi_rtl = False
        if num_base is not None and num_base != 10:
            if num_base == 16:
                hex_str = obj.hex()
                num, exp = hex_str.split('p')
                num = num.rstrip('0')
                if num[-1] == '.':
                    num += '0'
                return num + 'p' + exp
            raise ValueError('Unknown base {0}'.format(num_base))
        return str(obj)


    def _encode_str(self, obj, indent, key=False, key_path=False, val=False, delim=None, block=None):
        # Not using grammar here for the sake of concise clarity over
        # consistency.  Might be worth revising in future.
        # There is a lot of logic here to cover round tripping.  In that
        # scenario, delimiter style should be preserved whenever reasonable.
        if self.bidi_rtl_re.search(obj) is None:
            self._last_scalar_bidi_rtl = False
        else:
            self._last_scalar_bidi_rtl = True
        if delim is None:
            m = self._unquoted_str_re.match(obj)
        if delim is None and m is not None:
            if key_path and m.lastgroup != 'key':
                raise ValueError('String does not match the required pattern for a key path element')
            return obj
        if key_path:
            if delim is None:
                raise ValueError('String does not match the required pattern for a key path element')
            raise ValueError('Key path elements cannot be quoted')
        if self._line_terminator_re.search(obj) is None:
            if delim is None:
                if '"' not in obj:
                    return '"{0}"'.format(self._escape_unicode(obj, '"'))
                return '"""{0}"""'.format(self._escape_unicode(obj, '"'))
            if delim not in obj:
                return delim + obj + delim
            if delim[0] == '"':
                return '"""{0}"""'.format(self._escape_unicode(obj, '"'))
            if delim[0] == "'":
                return "'''{0}'''".format(self._escape_unicode(obj, "'"))
            if delim[0] == '`':
                if self._invalid_literal_unicode_re.search(obj) is not None:
                    if '"' not in obj:
                        return '"{0}"'.format(self._escape_unicode(obj, '"'))
                    return '"""{0}"""'.format(self._escape_unicode(obj, '"'))
                if '```' not in obj:
                    return '```' + obj + '```'
                if '``````' not in obj:
                    return '``````' + obj + '``````'
                if '"' not in obj:
                    return '"{0}"'.format(self._escape_unicode(obj, '"'))
                return '"""{0}"""'.format(self._escape_unicode(obj, '"'))
            raise ValueError('Unknown string delimiting character "{0}"'.format(delim[0]))
        if delim is not None and len(delim) % 3 != 0:
            delim = delim[0]*3
        if delim is None or obj[-1] != '\n' or self._invalid_literal_unicode_re.search(obj) is not None:
            if delim is None or delim[0] == '`':
                delim_char = '"'
            elif delim[0] in ('"', "'"):
                delim_char = delim[0]
            else:
                raise ValueError('Unknown string delimiting character "{0}"'.format(delim[0]))
            obj_encoded = self._escape_unicode(obj, delim_char, multidelim=True)
            obj_encoded_lines = obj_encoded.splitlines(True)
            if obj_encoded_lines[-1][-1:] != '\n':
                obj_encoded_lines[-1] += '\\\n'
            obj_encoded_indented = ''.join([indent + line for line in obj_encoded_lines])
            return '|{0}\n{1}{2}|{0}/'.format(delim_char*3, obj_encoded_indented, indent)
        if delim not in obj:
            obj_lines = obj.splitlines(True)
            obj_indented = ''.join([indent + line for line in obj_lines])
            return '|{0}\n{1}{2}|{0}/'.format(delim, obj_indented, indent)
        if delim[0]*3 not in obj:
            obj_lines = obj.splitlines(True)
            obj_indented = ''.join([indent + line for line in obj_lines])
            return '|{0}\n{1}{2}|{0}/'.format(delim[0]*3, obj_indented, indent)
        if delim[0]*6 not in obj:
            obj_lines = obj.splitlines(True)
            obj_indented = ''.join([indent + line for line in obj_lines])
            return '|{0}\n{1}{2}|{0}/'.format(delim[0]*6, obj_indented, indent)
        obj_encoded = self._escape_unicode(obj, '"', multidelim=True)
        obj_encoded_lines = obj_encoded.splitlines(True)
        return '|{0}\n{1}{2}|{0}/'.format('"""', obj_encoded_indented, indent)


    def _encode_list(self, obj, indent, key=False, key_path=False, val=False,
                     open_indentation_list=OPEN_INDENTATION_LIST,
                     start_inline_list=START_INLINE_LIST,
                     end_inline_list=END_INLINE_LIST):
        if key:
            raise TypeError('Lists are not supported as dict keys')
        if not obj:
            yield start_inline_list + end_inline_list + '\n'
        else:
            first = True
            for n, elem in enumerate(obj):
                type_elem = type(elem)
                if type_elem in self._list_types and elem:
                    if first:
                        yield open_indentation_list + '\n' + indent + '\x20\x20'
                        first = False
                    else:
                        yield indent + open_indentation_list + '\n' + indent + '\x20\x20'
                    for x in self._encode_funcs[type_elem](elem, indent + '\x20\x20'):
                        yield x
                else:
                    if first:
                        yield open_indentation_list + '\x20'
                        first = False
                    else:
                        yield indent + open_indentation_list + '\x20'
                    if type_elem in self._scalar_types:
                        yield self._encode_funcs[type_elem](elem, indent + '\x20\x20')
                        yield '\n'
                    else:
                        for x in self._encode_funcs[type_elem](elem, indent + '\x20\x20'):
                            yield x

    def _encode_dict(self, obj, indent, key=False, key_path=False, val=False,
                     start_inline_dict=START_INLINE_DICT,
                     end_inline_dict=END_INLINE_DICT,
                     assign_key_val=ASSIGN_KEY_VAL):
        if key:
            raise TypeError('Dicts are not supported as dict keys')
        if not obj:
            yield start_inline_dict + end_inline_dict + '\n'
        else:
            first = True
            for k, v in obj.items():
                if first:
                    yield self._encode_funcs[type(k)](k, indent, key=True)
                    first = False
                else:
                    yield indent + self._encode_funcs[type(k)](k, indent, key=True)
                yield '\x20' + assign_key_val
                type_v = type(v)
                if type_v in self._scalar_types:
                    if self._last_scalar_bidi_rtl:
                        yield '\n' + indent + self.dict_indent_per_level
                    else:
                        yield '\x20'
                    yield self._encode_funcs[type_v](v, indent + self.dict_indent_per_level, val=True)
                    yield '\n'
                elif not v:
                    yield '\x20'
                    yield self._encode_funcs[type_v](v, indent + self.dict_indent_per_level, val=True)
                elif type_v in self._dict_types:
                    yield '\n' + indent + self.dict_indent_per_level
                    for x in self._encode_funcs[type_v](v, indent + self.dict_indent_per_level, val=True):
                        yield x
                elif type_v in self._list_types:
                    yield '\n' + indent + self.list_indent_per_level
                    for x in self._encode_funcs[type_v](v, indent + self.list_indent_per_level, val=True):
                        yield x
                else:
                    raise TypeError('Unsupported object of type {0}'.format(type_v))


    def iterencode(self, obj):
        '''
        Encode an object iteratively as a sequence of strings.
        '''
        self._last_scalar_bidi_rtl = False
        if type(obj) in self._encode_funcs:
            if type(obj) in self._collection_types:
                return self._encode_funcs[type(obj)](obj, '')
            return self._encode_funcs[type(obj)](obj, '') + '\n'
        raise TypeError('Encoding type {0} is not supported'.format(type(obj)))


    def encode(self, obj):
        '''
        Encode an object as a string.
        '''
        return ''.join(x for x in self.iterencode(obj))


    def encode_scalar(self, obj, indent='', key=False, key_path=False,
                      delim=None, block=False, num_base=None):
        '''
        Encode a scalar.

        This is used in RoundtripAst.
        '''
        self._last_scalar_bidi_rtl = False
        if (block and delim is None) or (delim is not None and num_base is not None) or (key_path and not key):
            raise TypeError('Invalid argument combination')
        if delim is not None:
            return self._encode_funcs[type(obj)](obj, indent, key=key, key_path=key_path, delim=delim, block=block)
        if num_base is not None:
            return self._encode_funcs[type(obj)](obj, indent, key=key, key_path=key_path, num_base=num_base)
        return self._encode_funcs[type(obj)](obj, indent, key=key, key_path=key_path)
