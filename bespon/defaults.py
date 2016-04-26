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
                  'separator': ';',
                  'assign_key_val': '=',
                  'list_item': '+',
                  'block_suffix': '/'}


RESERVED_WORDS = {'true': True, 'TRUE': True, 'True': True,
                  'false': False, 'FALSE': False, 'False': False,
                  'null': None, 'NULL': None, 'Null': None,
                  'inf': float('inf'), 'INF': float('inf'), 'Inf': float('inf'),
                  '-inf': float('-inf'), '-INF': float('-inf'), '-Inf': float('-inf'),
                  '+inf': float('+inf'), '+INF': float('+inf'), '+Inf': float('+inf'),
                  'nan': float('nan'), 'NAN': float('nan'), 'NaN': float('nan')}


DICT_PARSERS = {'dict':  dict,
                'odict': collections.OrderedDict}

LIST_PARSERS = {'list':  list,
                'set':   set,
                'tuple': tuple}

STRING_PARSERS = {'int':          int,
                  'float':        float,
                  'str':          str,
                  'bytes':        bytes,
                  'bytes.base16': base64.b16decode,
                  'bytes.base64': base64.b64decode}

PARSER_ALIASES = {'b':   'bytes',
                  'b16': 'bytes.base16',
                  'b64': 'bytes.base64'}

_BYTES_PARSERS = set(['bytes', 'b', 'bytes.base16', 'b16', 'bytes.base64', 'b64'])
