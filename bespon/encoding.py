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
import collections
import fractions
from . import escape
from . import grammar
from . import tooling

if sys.version_info.major == 2:
    str = unicode




class BespONEncoder(object):
    '''
    Encode BespON.
    '''
    def __init__(self, *args, **kwargs):
        if args:
            raise TypeError('Explicit keyword arguments are required')

        only_ascii_source = kwargs.pop('only_ascii_source', False)
        only_ascii_unquoted = kwargs.pop('only_ascii_unquoted', True)
        aliases = kwargs.pop('aliases', True)
        circular_references = kwargs.pop('circular_references', False)
        integers = kwargs.pop('integers', True)
        hex_floats = kwargs.pop('hex_floats', False)
        extended_types = kwargs.pop('extended_types', False)
        python_types = kwargs.pop('python_types', False)
        baseclass = kwargs.pop('baseclass', False)
        trailing_commas = kwargs.pop('trailing_commas', False)
        compact_inline = kwargs.pop('compact_inline', False)
        if not all(x in (True, False) for x in (only_ascii_source, only_ascii_unquoted,
                                                aliases, circular_references,
                                                integers, hex_floats, extended_types, python_types,
                                                baseclass, trailing_commas, compact_inline)):
            raise TypeError
        self.only_ascii_source = only_ascii_source
        self.only_ascii_unquoted = only_ascii_unquoted
        self.aliases = aliases
        self.circular_references = circular_references
        self.integers = integers
        self.hex_floats = hex_floats
        self.extended_types = extended_types
        self.python_types = python_types
        self.baseclass = baseclass
        self.trailing_commas = trailing_commas
        self.compact_inline = compact_inline

        max_nesting_depth = kwargs.pop('max_nesting_depth', grammar.PARAMS['max_nesting_depth'])
        max_section_depth = kwargs.pop('max_section_depth', 0)
        inline_depth = kwargs.pop('inline_depth', max_nesting_depth+1)
        if not all(isinstance(x, int) for x in (max_nesting_depth, max_section_depth, inline_depth)):
            raise TypeError
        if not all(x >= 0 for x in (max_nesting_depth, max_section_depth, inline_depth)):
            raise ValueError
        self.max_nesting_depth = max_nesting_depth
        self.max_section_depth = max_section_depth
        self.inline_depth = inline_depth

        nesting_indent = kwargs.pop('nesting_indent', grammar.LIT_GRAMMAR['nesting_indent'])
        start_list_item = kwargs.pop('start_list_item', grammar.LIT_GRAMMAR['start_list_item'])
        flush_start_list_item = kwargs.pop('flush_start_list_item', grammar.LIT_GRAMMAR['flush_start_list_item'])
        if not all(isinstance(x, str) and x for x in (nesting_indent, start_list_item, flush_start_list_item)):
            raise TypeError
        if nesting_indent.lstrip(grammar.LIT_GRAMMAR['indent']):
            raise ValueError
        self.nesting_indent = nesting_indent
        if (start_list_item.count(grammar.LIT_GRAMMAR['open_indentation_list']) != 1 or
                start_list_item[0] not in grammar.LIT_GRAMMAR['indent'] or
                start_list_item.strip(grammar.LIT_GRAMMAR['indent_or_open_indentation_list'])):
            raise ValueError
        if (flush_start_list_item[0] != grammar.LIT_GRAMMAR['open_indentation_list'] or
                start_list_item.strip(grammar.LIT_GRAMMAR['indent_or_open_indentation_list'])):
            raise ValueError
        self.start_list_item = start_list_item
        self.flush_start_list_item = flush_start_list_item
        before_open, after_open = start_list_item.split(grammar.LIT_GRAMMAR['open_indentation_list'])
        self._start_list_item_indent = before_open
        self._start_list_item_open = start_list_item[:-len(after_open)]
        self._list_item_leading = after_open
        if before_open[-1:] == '\t' and after_open[:1] == '\t':
            self._list_item_indent = start_list_item.replace(grammar.LIT_GRAMMAR['open_indentation_list'], '')
        else:
            self._list_item_indent = start_list_item.replace(grammar.LIT_GRAMMAR['open_indentation_list'], '\x20')
        self._flush_start_list_item_indent = ''
        self._flush_start_list_item_open = flush_start_list_item[0]
        self._flush_list_item_leading = flush_start_list_item[1:]
        if flush_start_list_item[1:2] == '\t':
            self._flush_list_item_indent = flush_start_list_item[1:]
        else:
            self._flush_list_item_indent = '\x20' + flush_start_list_item[1:]

        if kwargs:
            raise TypeError('Unexpected keyword argument(s) {0}'.format(', '.join('"{0}"'.format(k) for k in kwargs)))


        self._escape = escape.Escape(only_ascii_source=only_ascii_source)
        self._escape_unicode = self._escape.escape_unicode
        self._escape_bytes = self._escape.escape_bytes
        self._invalid_literal_unicode_re = self._escape.invalid_literal_unicode_re
        self._invalid_literal_bytes_re = self._escape.invalid_literal_bytes_re


        if only_ascii_unquoted:
            self._unquoted_str_re = re.compile(grammar.RE_GRAMMAR['valid_terminated_unquoted_string_ascii'])
        else:
            self._unquoted_str_re = re.compile(grammar.RE_GRAMMAR['valid_terminated_unquoted_string_unicode'])
        self._unquoted_bytes_re = re.compile(grammar.RE_GRAMMAR['valid_terminated_unquoted_string_ascii'].encode('ascii'))

        self._line_terminator_unicode_re = re.compile(grammar.RE_GRAMMAR['line_terminator_unicode'])
        self._line_terminator_bytes_re = re.compile(grammar.RE_GRAMMAR['line_terminator_ascii'].encode('ascii'))

        self.bidi_rtl_re = re.compile(grammar.RE_GRAMMAR['bidi_rtl'])


        encode_funcs = {type(None): self._encode_none,
                        type(True): self._encode_bool,
                        type(1): self._encode_int if integers else self._encode_int_as_float,
                        type(1.0): self._encode_float,
                        type('a'): self._encode_str,
                        type(b'a'): self._encode_bytes,
                        type([]): self._encode_list,
                        type({}): self._encode_dict}

        extended_types_encode_funcs = {type(1j): self._encode_complex,
                                       type(fractions.Fraction()): self._encode_rational,
                                       type(collections.OrderedDict()): self._encode_odict,
                                       type(set()): self._encode_set}

        python_types_encode_funcs = {type(tuple()): self._encode_tuple}

        if self.extended_types:
            encode_funcs.update(extended_types_encode_funcs)
        if self.python_types:
            encode_funcs.update(python_types_encode_funcs)

        if not baseclass:
            def encode_func_factory(t):
                if t in extended_types_encode_funcs:
                    raise TypeError('Unsupported type {0} (extended_types=False)'.format(t))
                if t in python_types_encode_funcs:
                    raise TypeError('Unsupported type {0} (python_types=False)'.format(t))
                raise TypeError('Unsupported type {0}'.format(t))
        else:
            def encode_func_factory(t, issubclass=issubclass):
                for k, v in encode_funcs.items():
                    if issubclass(t, k):
                        return v
                if t in extended_types_encode_funcs:
                    raise TypeError('Unsupported type {0} (extended_types=False)'.format(t))
                if t in python_types_encode_funcs:
                    raise TypeError('Unsupported type {0} (python_types=False)'.format(t))
                raise TypeError('Unsupported type {0}'.format(t))
        self._encode_funcs = tooling.keydefaultdict(encode_func_factory)
        self._encode_funcs.update(encode_funcs)


    def _reset(self):
        '''
        Reset everything in preparation for the next run.
        '''
        self._buffer = []
        self._nesting_depth = 0
        self._scalar_bidi_rtl = False
        self._obj_path = collections.OrderedDict()
        self._alias_counter = 0
        self._alias_values = {}
        self._alias_def_template = {}
        self._alias_def_buffer_index = {}


    def _free(self):
        '''
        Free up memory used in last run.
        '''
        self._buffer = None
        self._obj_path = None
        self._alias_values = None
        self._alias_def_template = None
        self._alias_def_buffer_index = None


    def _encode_none(self, obj,
                     flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                     none_type=grammar.LIT_GRAMMAR['none_type']):
        self._buffer.append(leading)
        self._buffer.append(none_type)


    def _encode_bool(self, obj,
                     flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                     bool_true=grammar.LIT_GRAMMAR['bool_true'],
                     bool_false=grammar.LIT_GRAMMAR['bool_false']):
        self._buffer.append(leading)
        self._buffer.append(bool_true if obj else bool_false)


    def _encode_int(self, obj,
                    flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                    num_base=10,
                    hex_template='{0}{{0:0x}}'.format(grammar.LIT_GRAMMAR['hex_prefix']),
                    oct_template='{0}{{0:0o}}'.format(grammar.LIT_GRAMMAR['oct_prefix']),
                    bin_template='{0}{{0:0b}}'.format(grammar.LIT_GRAMMAR['bin_prefix']),
                    str=str):
        if key_path:
            raise TypeError('Ints are not valid in key paths')
        self._buffer.append(leading)
        if num_base == 10:
            self._buffer.append(str(obj))
            return
        if num_base == 16:
            self._buffer.append(hex_template.format(obj))
            return
        if num_base == 8:
            self._buffer.append(oct_template.format(obj))
            return
        if num_base == 2:
            self._buffer.append(bin_template.format(obj))
            return
        raise ValueError('Unknown base {0}'.format(num_base))


    def _encode_int_as_float(self, obj, float=float, **kwargs):
        # Extremely large ints won't be silently converted to inf, because
        # `float()` raises an OverflowError.
        self._encode_float(float(obj), **kwargs)


    def _encode_float(self, obj,
                      flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                      num_base=None,
                      hex_exponent_letter=grammar.LIT_GRAMMAR['hex_exponent_letter'][0],
                      str=str):
        if key:
            raise TypeError('Floats are not valid dict keys')
        self._buffer.append(leading)
        if self.hex_floats:
            if num_base is not None:
                if num_base != 16:
                    raise ValueError
            else:
                num_base = 16
        if num_base is None or num_base == 10:
            self._buffer.append(str(obj))
            return
        if num_base == 16:
            num, exp = obj.hex().split('p')
            num = num.rstrip('0')
            if num[-1] == '.':
                num += '0'
            self._buffer.append(num + hex_exponent_letter + exp)
            return
        raise ValueError('Unknown base {0}'.format(num_base))


    def _encode_complex(self, obj,
                        flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                        num_base=None,
                        hex_exponent_letter=grammar.LIT_GRAMMAR['hex_exponent_letter'][0],
                        dec_float_zero=grammar.LIT_GRAMMAR['dec_float_zero'],
                        hex_float_zero=grammar.LIT_GRAMMAR['hex_float_zero'],
                        imaginary_unit=grammar.LIT_GRAMMAR['imaginary_unit'],
                        str=str):
        if key:
            raise TypeError('Complex floats are not valid dict keys')
        self._buffer.append(leading)
        if self.hex_floats:
            if num_base is not None:
                if num_base != 16:
                    raise ValueError
            else:
                num_base = 16
        real = obj.real
        imag = obj.imag
        if num_base is None or num_base == 10:
            if real == 0.0:
                self._buffer.append(str(imag) + imaginary_unit)
                return
            if imag == 0.0:
                self._buffer.append(str(real) + '+' + dec_float_zero + imaginary_unit)
                return
            if imag < 0.0:
                self._buffer.append(str(real) + str(imag) + imaginary_unit)
                return
            self._buffer.append(str(real) + '+' + str(imag) + imaginary_unit)
            return
        if num_base == 16:
            if real == 0.0:
                num_imag, exp_imag = imag.hex().split('p')
                num_imag = num_imag.rstrip('0')
                if num_imag[-1] == '.':
                    num_imag += '0'
                self._buffer.append(num_imag + hex_exponent_letter + exp_imag + imaginary_unit)
                return
            if imag == 0.0:
                num_real, exp_real = real.hex().split('p')
                num_real = num_real.rstrip('0')
                if num_real[-1] == '.':
                    num_real += '0'
                self._buffer.append(num_real + hex_exponent_letter + exp_real + '+' + hex_float_zero + imaginary_unit)
                return
            num_real, exp_real = real.hex().split('p')
            num_real = num_real.rstrip('0')
            if num_real[-1] == '.':
                num_real += '0'
            num_imag, exp_imag = imag.hex().split('p')
            num_imag = num_imag.rstrip('0')
            if num_imag[-1] == '.':
                num_imag += '0'
            if imag < 0.0:
                self._buffer.append(num_real + hex_exponent_letter + exp_real + num_imag + hex_exponent_letter + exp_imag + imaginary_unit)
                return
            self._buffer.append(num_real + hex_exponent_letter + exp_real + '+' + num_imag + hex_exponent_letter + exp_imag + imaginary_unit)
            return
        raise ValueError('Unknown base {0}'.format(num_base))


    def _encode_rational(self, obj,
                         flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                         str=str):
        if key:
            raise TypeError('Rational numbers are not valid dict keys')
        self._buffer.append(leading)
        self._buffer.append(str(obj))


    def _encode_str(self, obj,
                    flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                    delim=None, block=None,
                    string_delim_seq_set=grammar.LIT_GRAMMAR['string_delim_seq_set'],
                    len=len):
        # There is a lot of logic here to cover round-tripping.  In that
        # scenario, delimiter style should be preserved whenever reasonable.
        if delim is None:
            if self._unquoted_str_re.match(obj) is not None:
                self._scalar_bidi_rtl = self.bidi_rtl_re.search(obj) is not None
                self._buffer.append(leading)
                self._buffer.append(obj)
                return
            delim_char = '"'
        elif delim in string_delim_seq_set:
            delim_char = delim[0]
        else:
            raise ValueError
        if key_path:
            if delim is None:
                raise ValueError('String does not match the required pattern for a key path element')
            raise ValueError('Key path elements cannot be quoted')
        if inline and self.compact_inline:
            self._buffer.append(leading)
            self._buffer.append('"{0}"'.format(self._escape_unicode(obj, '"', inline=True, bidi_rtl=True)))
            return
        if self._line_terminator_unicode_re.search(obj) is None:
            self._scalar_bidi_rtl = self.bidi_rtl_re.search(obj) is not None
            self._buffer.append(leading)
            if delim_char == "'":
                if "'" not in obj:
                    self._buffer.append("'{0}'".format(self._escape_unicode(obj, "'")))
                    return
                self._buffer.append("'''{0}'''".format(self._escape_unicode(obj, "'", multidelim=True)))
                return
            if delim_char == '"' or obj == '' or self._invalid_literal_unicode_re.search(obj) is not None:
                if '"' not in obj:
                    self._buffer.append('"{0}"'.format(self._escape_unicode(obj, '"')))
                    return
                self._buffer.append('"""{0}"""'.format(self._escape_unicode(obj, '"', multidelim=True)))
                return
            if '`' not in obj:
                self._buffer.append('`{0}`'.format(obj))
                return
            if '``' not in obj:
                if obj[0] == '`':
                    open_delim = '``\x20'
                else:
                    open_delim = '``'
                if obj[-1] == '`':
                    close_delim = '\x20``'
                else:
                    close_delim = '``'
                self._buffer.append(open_delim + obj + close_delim)
                return
            if '```' not in obj:
                if obj[0] == '`':
                    open_delim = '```\x20'
                else:
                    open_delim = '```'
                if obj[-1] == '`':
                    close_delim = '\x20```'
                else:
                    close_delim = '```'
                self._buffer.append(open_delim + obj + close_delim)
                return
            if '"' not in obj:
                self._buffer.append('"{0}"'.format(self._escape_unicode(obj, '"')))
                return
            self._buffer.append('"""{0}"""'.format(self._escape_unicode(obj, '"', multidelim=True)))
            return
        if at_line_start:
            self._buffer.append(leading)
        else:
            indent += self.nesting_indent
            self._buffer.append('\n' + indent)
        template = '|{0}\n{1}{2}|{0}/'
        if obj[-1] != '\n' or self._invalid_literal_unicode_re.search(obj) is not None:
            if delim_char == '`':
                delim_char = '"'
            obj_encoded = self._escape_unicode(obj, delim_char, multidelim=True)
            obj_encoded_lines = obj_encoded.splitlines(True)
            if obj_encoded_lines[-1][-1:] != '\n':
                obj_encoded_lines[-1] += '\\\n'
            obj_encoded_indented = ''.join([indent + line for line in obj_encoded_lines])
            self._buffer.append(template.format(delim_char*3, obj_encoded_indented, indent))
            return
        if delim_char*3 not in obj:
            obj_lines = obj.splitlines(True)
            obj_indented = ''.join([indent + line for line in obj_lines])
            self._buffer.append(template.format(delim_char*3, obj_indented, indent))
            return
        if delim_char*6 not in obj:
            obj_lines = obj.splitlines(True)
            obj_indented = ''.join([indent + line for line in obj_lines])
            self._buffer.append(template.format(delim_char*6, obj_indented, indent))
            return
        obj_encoded = self._escape_unicode(obj, '"', multidelim=True)
        obj_encoded_lines = obj_encoded.splitlines(True)
        obj_encoded_indented = ''.join([indent + line for line in obj_encoded_lines])
        self._buffer.append(template.format('"""', obj_encoded_indented, indent))
        return


    def _encode_bytes(self, obj,
                      flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                      delim=None, block=None,
                      string_delim_seq_set=grammar.LIT_GRAMMAR['string_delim_seq_set']):
        if key_path:
            raise TypeError('Bytes type cannot be used in key paths')
        tag = '(bytes)> '
        if delim is None:
            if self._unquoted_bytes_re.match(obj) is not None:
                self._buffer.append(leading)
                self._buffer.append(tag + obj.decode('ascii'))
                return
            delim_char = '"'
            delim_char_bytes = b'"'
        elif delim in string_delim_seq_set:
            delim_char = delim[0]
            delim_char_bytes = delim_char.encode('ascii')
        else:
            raise ValueError
        if inline and self.compact_inline:
            self._buffer.append(leading)
            self._buffer.append('"{0}"'.format(self._escape_bytes(obj, '"', inline=True).decode('ascii')))
            return
        if self._line_terminator_bytes_re.search(obj) is None:
            self._buffer.append(leading)
            if delim_char == "'":
                if b"'" not in obj:
                    self._buffer.append(tag + "'{0}'".format(self._escape_bytes(obj, "'").decode('ascii')))
                    return
                self._buffer.append(tag + "'''{0}'''".format(self._escape_bytes(obj, "'", multidelim=True).decode('ascii')))
                return
            if delim_char == '"' or obj == b'' or self._invalid_literal_bytes_re.search(obj) is not None:
                if b'"' not in obj:
                    self._buffer.append(tag + '"{0}"'.format(self._escape_bytes(obj, '"').decode('ascii')))
                    return
                self._buffer.append(tag + '"""{0}"""'.format(self._escape_bytes(obj, '"', multidelim=True).decode('ascii')))
                return
            if b'`' not in obj:
                self._buffer.append(tag + '`{0}`'.format(obj.decode('ascii')))
                return
            if b'``' not in obj:
                if obj[:1] == b'`':
                    open_delim = '``\x20'
                else:
                    open_delim = '``'
                if obj[-1:] == b'`':
                    close_delim = '\x20``'
                else:
                    close_delim = '``'
                self._buffer.append(tag + open_delim + obj.decode('ascii') + close_delim)
                return
            if '```' not in obj:
                if obj[:1] == b'`':
                    open_delim = '```\x20'
                else:
                    open_delim = '```'
                if obj[-1:] == b'`':
                    close_delim = '\x20```'
                else:
                    close_delim = '```'
                self._buffer.append(tag + open_delim + obj.decode('ascii') + close_delim)
                return
            if b'"' not in obj:
                self._buffer.append(tag +'"{0}"'.format(self._escape_bytes(obj, '"').decode('ascii')))
                return
            self._buffer.append(tag + '"""{0}"""'.format(self._escape_bytes(obj, '"', multidelim=True).decode('ascii')))
            return
        if at_line_start:
            self._buffer.append(leading)
        else:
            indent += self.nesting_indent
            self._buffer.append('\n' + indent)
        tag = '(bytes)>\n' + indent
        template = '|{0}\n{1}{2}|{0}/'
        if obj[-1] != b'\n' or self._invalid_literal_bytes_re.search(obj) is not None:
            if delim_char == '`':
                delim_char = '"'
            obj_encoded = self._escape_bytes(obj, delim_char, multidelim=True).decode('ascii')
            obj_encoded_lines = obj_encoded.splitlines(True)
            if obj_encoded_lines[-1][-1:] != '\n':
                obj_encoded_lines[-1] += '\\\n'
            obj_encoded_indented = ''.join([indent + line for line in obj_encoded_lines])
            self._buffer.append(tag + template.format(delim_char*3, obj_encoded_indented, indent))
            return
        if delim_char_bytes*3 not in obj:
            obj_lines = obj.decode('ascii').splitlines(True)
            obj_indented = ''.join([indent + line for line in obj_lines])
            self._buffer.append(tag + template.format(delim_char*3, obj_indented, indent))
            return
        if delim_char_bytes*6 not in obj:
            obj_lines = obj.decode('ascii').splitlines(True)
            obj_indented = ''.join([indent + line for line in obj_lines])
            self._buffer.append(tag + template.format(delim_char*6, obj_indented, indent))
            return
        obj_encoded = self._escape_bytes(obj, '"', multidelim=True).decode('ascii')
        obj_encoded_lines = obj_encoded.splitlines(True)
        obj_encoded_indented = ''.join([indent + line for line in obj_encoded_lines])
        self._buffer.append(tag + template.format('"""', obj_encoded_indented, indent))


    def _encode_doc_comment(self, obj,
                            flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                            delim=None, block=None,
                            doc_comment_delim_seq_set=grammar.LIT_GRAMMAR['doc_comment_delim_seq_set'],):
        if key_path:
            raise TypeError('Key paths do not take doc comments')
        if delim is None:
            delim = '###'
        elif delim in doc_comment_delim_seq_set:
            delim = '###'
        else:
            raise ValueError
        if self._invalid_literal_unicode_re.search(obj) is not None:
            raise ValueError('Invalid literal code point')
        while delim in obj:
            delim += '###'
            if delim not in doc_comment_delim_seq_set:
                raise ValueError('Cannot create comment since all valid escape sequences of "#" appear literally within the comment text')
        if not at_line_start:
            indent += self.nesting_indent
            self._buffer.append('\n' + indent)
        if self._line_terminator_unicode_re.search(obj) or self.bidi_rtl_re.search(obj):
            if obj[-1] != '\n':
                self._buffer.append('|{0}\n{1}{2}\n{1}|{0}/'.format(delim, indent, indent.join(obj.splitlines(True))))
                return
            self._buffer.append('|{0}\n{1}{2}{1}|{0}/'.format(delim, indent, indent.join(obj.splitlines(True))))
            return
        self._buffer.append('{0}{1}{0}'.format(delim, obj))


    def _encode_line_comment(self, obj,
                             flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                             delim=None, block=None):
        if self._invalid_literal_unicode_re.search(obj) is not None:
            raise ValueError('Invalid literal code point')
        if self._line_terminator_unicode_re.search(obj):
            raise ValueError('Line comments cannot contain literal newlines')
        self._buffer.append(leading)
        self._buffer.append('#' + obj)


    def _encode_alias(self, obj,
                      flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                      alias_prefix=grammar.LIT_GRAMMAR['alias_prefix'],
                      alias_basename='obj', id=id, str=str):
        id_obj = id(obj)
        if not self.aliases:
            raise ValueError('Objects appeared multiple times but aliasing is not enabled (aliases=False)')
        if id_obj in self._obj_path and not self.circular_references:
            raise ValueError('Circular references were encountered but are not enabled (circular_references=False)')
        alias_value = self._alias_values[id_obj]
        if alias_value is None:
            self._alias_counter += 1
            alias_value = alias_basename + str(self._alias_counter)
            if alias_basename != 'obj':
                self._scalar_bidi_rtl = self.bidi_rtl_re.search(alias_value) is not None
            self._alias_values[id_obj] = alias_value
            self._buffer[self._alias_def_buffer_index[id_obj]] = self._alias_def_template[id_obj].format(alias_value)
        self._buffer.append(leading)
        self._buffer.append(alias_prefix + alias_value)


    def _encode_list(self, obj,
                     flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                     explicit_type=None,
                     start_inline_list=grammar.LIT_GRAMMAR['start_inline_list'],
                     end_inline_list=grammar.LIT_GRAMMAR['end_inline_list'],
                     indent_chars=grammar.LIT_GRAMMAR['indent'],
                     id=id, len=len, type=type):
        if key:
            raise TypeError('List-like objects are not supported as dict keys')
        id_obj = id(obj)
        if id_obj in self._alias_values:
            self._encode_alias(obj)
            return

        self._obj_path[id_obj] = None
        self._alias_values[id_obj] = None

        if not inline:
            inline = self._nesting_depth >= self.inline_depth
        self._nesting_depth += 1
        if self._nesting_depth > self.max_nesting_depth:
            raise TypeError('Max nesting depth for collections was exceeded; max depth = {0}'.format(self.max_nesting_depth))

        if not obj:
            self._buffer.append(leading)
            if explicit_type is None:
                self._alias_def_buffer_index[id_obj] = len(self._buffer)
                self._buffer.append('')
                self._alias_def_template[id_obj] = '(label={0})>\x20'
            else:
                self._buffer.append('({0}'.format(explicit_type))
                self._alias_def_buffer_index[id_obj] = len(self._buffer)
                self._buffer.append('')
                self._buffer.append(')>\x20')
                self._alias_def_template[id_obj] = ', label={0}'
            self._buffer.append(start_inline_list + end_inline_list)
            self._obj_path.popitem()
            self._nesting_depth -= 1
            return

        if inline:
            self._buffer.append(leading)
            if explicit_type is None:
                self._alias_def_buffer_index[id_obj] = len(self._buffer)
                self._buffer.append('')
                self._alias_def_template[id_obj] = '(label={0})>\x20'
            else:
                self._buffer.append('({0}'.format(explicit_type))
                self._alias_def_buffer_index[id_obj] = len(self._buffer)
                self._buffer.append('')
                self._buffer.append(')>\x20')
                self._alias_def_template[id_obj] = ', label={0}'
            internal_indent = indent + self.nesting_indent
            if self.compact_inline:
                self._buffer.append(start_inline_list)
                for item in obj:
                    self._encode_funcs[type(item)](item, inline=inline, at_line_start=False, indent=internal_indent)
                    self._buffer.append(',\x20')
                if self.trailing_commas:
                    self._buffer[-1] = ','
                else:
                    self._buffer[-1] = ''
                self._buffer.append(end_inline_list)
            else:
                self._buffer.append(start_inline_list + '\n')
                for item in obj:
                    self._buffer.append(internal_indent)
                    self._encode_funcs[type(item)](item, inline=inline, indent=internal_indent)
                    self._buffer.append(',\n')
                if not self.trailing_commas:
                    self._buffer[-1] = '\n'
                self._buffer.append(indent + end_inline_list)
        else:
            if after_start_list_item or not at_line_start:
                self._buffer.append('\n')
            if flush_margin or after_start_list_item:
                start_list_item_indent = self._flush_start_list_item_indent
                start_list_item_open = self._flush_start_list_item_open
                internal_leading = self._flush_list_item_leading
                internal_indent = indent + self._flush_list_item_indent
            else:
                start_list_item_indent = self._start_list_item_indent
                start_list_item_open = self._start_list_item_open
                internal_leading = self._list_item_leading
                internal_indent = indent + self._list_item_indent
            if explicit_type is None:
                self._alias_def_buffer_index[id_obj] = len(self._buffer)
                self._buffer.append('')
                self._alias_def_template[id_obj] = indent + start_list_item_indent + '(label={0})>\n'
            else:
                self._buffer.append(indent + start_list_item_indent + '({0}'.format(explicit_type))
                self._alias_def_buffer_index[id_obj] = len(self._buffer)
                self._buffer.append('')
                self._buffer.append(')>\n')
                self._alias_def_template[id_obj] = ', label={0}'
            for item in obj:
                self._buffer.append(indent + start_list_item_open)
                self._encode_funcs[type(item)](item, inline=inline, after_start_list_item=True, indent=internal_indent, leading=internal_leading)
                self._buffer.append('\n')
            self._buffer.pop()

        self._obj_path.popitem()
        self._nesting_depth -= 1


    def _encode_dict(self, obj,
                     flush_margin=False, inline=False, at_line_start=True, indent='', leading='', after_start_list_item=False, key=False, key_path=False, value=False,
                     explicit_type=None,
                     start_inline_dict=grammar.LIT_GRAMMAR['start_inline_dict'],
                     end_inline_dict=grammar.LIT_GRAMMAR['end_inline_dict'],
                     assign_key_val=grammar.LIT_GRAMMAR['assign_key_val']):
        if key:
            raise TypeError('Dict-like objects are not supported as dict keys')
        id_obj = id(obj)
        if id_obj in self._alias_values:
            self._encode_alias(obj)
            return

        self._obj_path[id_obj] = None
        self._alias_values[id_obj] = None

        if not inline:
            inline = self._nesting_depth >= self.inline_depth
        self._nesting_depth += 1
        if self._nesting_depth > self.max_nesting_depth:
            raise TypeError('Max nesting depth for collections was exceeded; max depth = {0}'.format(self.max_nesting_depth))

        if not obj:
            self._buffer.append(leading)
            if explicit_type is None:
                self._alias_def_buffer_index[id_obj] = len(self._buffer)
                self._buffer.append('')
                self._alias_def_template[id_obj] = '(label={0})>\x20'
            else:
                self._buffer.append('({0}'.format(explicit_type))
                self._alias_def_buffer_index[id_obj] = len(self._buffer)
                self._buffer.append('')
                self._buffer.append(')>\x20')
                self._alias_def_template[id_obj] = ', label={0}'
            self._buffer.append(start_inline_dict + end_inline_dict)
            self._obj_path.popitem()
            self._nesting_depth -= 1
            return

        if inline:
            self._buffer.append(leading)
            if explicit_type is None:
                self._alias_def_buffer_index[id_obj] = len(self._buffer)
                self._buffer.append('')
                self._alias_def_template[id_obj] = '(label={0})>\x20'
            else:
                self._buffer.append('({0}'.format(explicit_type))
                self._alias_def_buffer_index[id_obj] = len(self._buffer)
                self._buffer.append('')
                self._buffer.append(')>\x20')
                self._alias_def_template[id_obj] = ', label={0}'
            internal_indent = indent + self.nesting_indent
            if self.compact_inline:
                self._buffer.append(start_inline_dict)
                for k, v in obj.items():
                    self._encode_funcs[type(k)](k, inline=inline, at_line_start=False, indent=internal_indent, key=True)
                    self._buffer.append(' =')
                    self._encode_funcs[type(v)](v, inline=inline, at_line_start=False, indent=internal_indent, leading='\x20', value=True)
                    self._buffer.append(',\x20')
                if self.trailing_commas:
                    self._buffer[-1] = ','
                else:
                    self._buffer[-1] = ''
                self._buffer.append(end_inline_dict)
            else:
                self._buffer.append(start_inline_dict + '\n')
                for k, v in obj.items():
                    self._buffer.append(internal_indent)
                    self._encode_funcs[type(k)](k, inline=inline, indent=internal_indent, key=True)
                    if self._scalar_bidi_rtl:
                        self._scalar_bidi_rtl = False
                        self._buffer.append('\x20=\n' + internal_indent)
                        self._encode_funcs[type(v)](v, inline=inline, indent=internal_indent, value=True)
                    else:
                        self._buffer.append('\x20=')
                        self._encode_funcs[type(v)](v, inline=inline, at_line_start=False, indent=internal_indent, leading='\x20', value=True)
                    self._buffer.append(',\n')
                if not self.trailing_commas:
                    self._buffer[-1] = '\n'
                self._buffer.append(indent + end_inline_dict)
        else:
            if at_line_start:
                self._buffer.append(leading)
            else:
                indent += self.nesting_indent
                self._buffer.append('\n' + indent)
            if explicit_type is None:
                self._alias_def_buffer_index[id_obj] = len(self._buffer)
                self._buffer.append('')
                self._alias_def_template[id_obj] = indent + '(dict, label={0})>\n'
            else:
                self._buffer.append(indent + '({0}'.format(explicit_type))
                self._alias_def_buffer_index[id_obj] = len(self._buffer)
                self._buffer.append('')
                self._buffer.append(')>\n')
                self._alias_def_template[id_obj] = ', label={0}'
            internal_indent = indent + self.nesting_indent
            first = True
            for k, v in obj.items():
                if first:
                    first = False
                else:
                    self._buffer.append(indent)
                self._encode_funcs[type(k)](k, inline=inline, indent=indent, key=True)
                if self._scalar_bidi_rtl:
                    self._scalar_bidi_rtl = False
                    self._buffer.append('\x20=\n' + internal_indent)
                    self._encode_funcs[type(v)](v, inline=inline, indent=internal_indent, value=True)
                else:
                    self._buffer.append('\x20=')
                    self._encode_funcs[type(v)](v, inline=inline, at_line_start=False, indent=indent, leading='\x20', value=True)
                self._buffer.append('\n')
            self._buffer.pop()

        self._obj_path.popitem()
        self._nesting_depth -= 1


    def _encode_odict(self, obj, **kwargs):
        self._encode_dict(obj, explicit_type='odict', **kwargs)


    def _encode_set(self, obj, **kwargs):
        self._encode_list(obj, explicit_type='set', **kwargs)

    def _encode_tuple(self, obj, **kwargs):
        self._encode_list(obj, explicit_type='tuple', **kwargs)


    def encode(self, obj):
        '''
        Encode an object as a string.
        '''
        self._reset()
        self._encode_funcs[type(obj)](obj, flush_margin=True)
        if self._buffer[-1][-1] != '\n':
            self._buffer.append('\n')
        encoded = ''.join(self._buffer)
        self._free()
        return encoded


    def partial_encode(self, obj, dtype=None,
                       flush_margin=False,
                       inline=False, at_line_start=True, indent='',
                       after_start_list_item=False,
                       key=False, key_path=False,
                       delim=None, block=False, num_base=None,
                       initial_nesting_depth=0):
        '''
        Encode an object within a larger object in a manner suitable for its
        context.  This is used in RoundtripAst.
        '''
        self._reset()
        self._nesting_depth = initial_nesting_depth
        if dtype is None:
            if (delim and num_base) or (key_path and not key):
                raise TypeError('Invalid argument combination')
            if delim or block:
                self._encode_funcs[type(obj)](obj, flush_margin=flush_margin, inline=inline, at_line_start=at_line_start, after_start_list_item=after_start_list_item, key=key, key_path=key_path, delim=delim, block=block)
            elif num_base:
                self._encode_funcs[type(obj)](obj, flush_margin=flush_margin, inline=inline, at_line_start=at_line_start, after_start_list_item=after_start_list_item, key=key, key_path=key_path, num_base=num_base)
            else:
                self._encode_funcs[type(obj)](obj, flush_margin=flush_margin, inline=inline, at_line_start=at_line_start, after_start_list_item=after_start_list_item, key=key, key_path=key_path)
        elif dtype == 'doc_comment':
            self._encode_doc_comment(obj, flush_margin=flush_margin, inline=inline, at_line_start=at_line_start, after_start_list_item=after_start_list_item, key=key, key_path=key_path, delim=delim, block=block)
        elif dtype == 'line_comment':
            self._encode_line_comment(obj, flush_margin=flush_margin, inline=inline, at_line_start=at_line_start, after_start_list_item=after_start_list_item, key=key, key_path=key_path, delim=delim, block=block)
        else:
            raise ValueError
        encoded = ''.join(self._buffer).replace('\n', '\n'+indent)
        self._free()
        return encoded
