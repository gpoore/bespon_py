# -*- coding: utf-8 -*-
#
# Copyright (c) 2016, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


from __future__ import (division, print_function, absolute_import,
                        unicode_literals)


from .version import __version__


import collections
import base64


RESERVED_CHARS = {'comment': '%',
                  'start_type': '(',
                  'end_type': ')',
                  'end_type_suffix': '>',
                  'start_list': '[',
                  'end_list': ']',
                  'start_dict': '{',
                  'end_dict': '}',
                  'escaped_string': '"',
                  'literal_string': "'",
                  'separator': ',',
                  'assign_key_val': '=',
                  'list_item': '*',
                  'block_suffix': '/'}


RESERVED_WORDS = {'true': True, 'TRUE': True, 'True': True,
                  'false': False, 'FALSE': False, 'False': False,
                  'null': None, 'NULL': None, 'Null': None,
                  'inf': float('inf'), 'INF': float('inf'), 'Inf': float('inf'),
                  '-inf': float('-inf'), '-INF': float('-inf'), '-Inf': float('-inf'),
                  '+inf': float('+inf'), '+INF': float('+inf'), '+Inf': float('+inf'),
                  'nan': float('nan'), 'NAN': float('nan'), 'NaN': float('nan')}


RESERVED_TYPE_PREFIXES = ['bespon']


RESERVED_TYPES = ['schema', 'meta', 'labelref', 'pathref',
                  'copy', 'shallowcopy', 'deepcopy']


DICT_PARSERS = {'dict':  dict,
                'odict': collections.OrderedDict}

LIST_PARSERS = {'list':  list,
                'set':   set,
                'tuple': tuple}

_int_dict = {'num.int.base2':  lambda s: int(s, 2),
             'num.int.base8':  lambda s: int(s, 8),
             'num.int.base10': int,
             'num.int.base16': lambda s: int(s, 16)}

def _int(s, type_name):
    return _int_dict[type_name](s.replace('_', ''))

_float_dict = {'num.float.base10': float,
               'num.float.base16': float.fromhex}

def _float(s, type_name):
    return _float_dict[type_name](s.replace('_', ''))

STRING_PARSERS = {'num.int':         _int,
                  'num.float':       _float,
                  'str':             str,
                  'bytes':           bytes,
                  'bytes.base16':    base64.b16decode,
                  'bytes.base64':    base64.b64decode}

PARSER_ALIASES = {'int':   'num.int',
                  'float': 'num.float',
                  'b':     'bytes',
                  'b16':   'bytes.base16',
                  'b64':   'bytes.base64'}

_BYTES_PARSERS = set(['bytes', 'b', 'bytes.base16', 'b16', 'bytes.base64', 'b64'])

_NUM_PARSERS = set(['num.int', 'int', 'num.float', 'float'])
