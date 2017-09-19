# -*- coding: utf-8 -*-
#
# Copyright (c) 2016-2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


# pylint:  disable=C0301

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import sys
import collections
import base64
import re
import fractions
from . import grammar

# pylint:  disable=C0103, W0622, E0602
if sys.version_info.major == 2:
    str = unicode
# pylint:  enable=C0103, W0622, E0602




IMPLICIT_CORE_SCALAR_TYPES = set(['none', 'bool', 'int', 'float', 'str'])
IMPLICIT_EXTENDED_SCALAR_TYPES = set(['complex', 'rational'])
IMPLICIT_SCALAR_TYPES = IMPLICIT_CORE_SCALAR_TYPES | IMPLICIT_EXTENDED_SCALAR_TYPES
IMPLICIT_COLLECTION_TYPES = set(['dict', 'list'])
IMPLICIT_TYPES = IMPLICIT_SCALAR_TYPES | IMPLICIT_COLLECTION_TYPES


class LoadType(object):
    '''
    Data type for loading.

    ascii_bytes:  The typed string represents binary data using ASCII. If
                  escapes are used, only bytes-compatible escapes are allowed.
                  The string is encoded to binary with the ASCII codec before
                  being passed to the parser.

    mutable:      Whether a collection is mutable.  Mutable collections are
                  more convenient to work with when resolving aliases.
    '''
    __slots__ = ['name', 'compatible_implicit_types', 'parser',
                 'ascii_bytes', 'mutable']
    def __init__(self, name=None, compatible_implicit_types=None, parser=None,
                 ascii_bytes=False, mutable=False):
        if not isinstance(name, str):
            raise TypeError
        if not isinstance(compatible_implicit_types, set):
            if isinstance(compatible_implicit_types, str):
                compatible_implicit_types = [compatible_implicit_types]
            elif not (isinstance(compatible_implicit_types, list) or isinstance(compatible_implicit_types, tuple)):
                raise TypeError
            compatible_implicit_types = set(compatible_implicit_types)
        if compatible_implicit_types - IMPLICIT_TYPES:
            raise ValueError
        if not hasattr(parser, '__call__'):
            raise TypeError
        if not all(x in (True, False) for x in (ascii_bytes, mutable)):
            raise TypeError
        if ascii_bytes and ('str' not in compatible_implicit_types or len(compatible_implicit_types) > 1):
            raise ValueError
        if mutable and compatible_implicit_types - IMPLICIT_COLLECTION_TYPES:
            raise ValueError
        self.name = name
        self.compatible_implicit_types = compatible_implicit_types
        self.parser = parser
        self.ascii_bytes = ascii_bytes
        self.mutable = mutable

    def copy(self):
        return LoadType(name=self.name,
                        compatible_implicit_types=self.compatible_implicit_types,
                        parser=self.parser, ascii_bytes=self.ascii_bytes,
                        mutable=self.mutable)




WHITESPACE_BYTES_RE = re.compile('{0}+'.format(grammar.RE_GRAMMAR['whitespace']).encode('ascii'))
BASE16_RE = re.compile(grammar.RE_GRAMMAR['base16'].encode('ascii'))
BASE64_RE = re.compile(grammar.RE_GRAMMAR['base64'].encode('ascii'))


# https://tools.ietf.org/html/rfc3548
# https://tools.ietf.org/html/rfc4648

def _base16_parser(b, whitespace_bytes_re=WHITESPACE_BYTES_RE,
                   base16_re=BASE16_RE, b16decode=base64.b16decode):
    if not base16_re.match(b):
        raise ValueError('Invalid character(s) in Base16-encoded data; mixed-case characters are not permitted, spaces are only allowed if a single space separates each byte on a line, and trailing empty lines are not permitted')
    b_processed = whitespace_bytes_re.sub(b'', b)
    # Optional second argument is casefold
    return b16decode(b_processed, True)


def _base64_parser(b, whitespace_bytes_re=WHITESPACE_BYTES_RE,
                   base64_re=BASE64_RE, b64decode=base64.b64decode):
    if not base64_re.match(b):
        raise ValueError('Invalid character(s) in Base64-encoded data; whitespace is only permitted at the end of lines, and trailing empty lines are not permitted')
    b_processed = whitespace_bytes_re.sub(b'', b)
    return base64.b64decode(b_processed)




# There is no explicit validation of parser function arguments here.  Parser
# functions for scalar types that are always unquoted (none, bool, numbers)
# are only ever called on arguments that have already been validated.  That
# leaves parser functions operating on quoted or unquoted strings.  These are
# given the parsed strings, and are responsible for their own validation
# internally.  The Base16 and Base64 parsers are an example.
CORE_TYPES = {x.name: x for x in [
    LoadType(name='none', compatible_implicit_types='none', parser=lambda x: None),
    LoadType(name='bool', compatible_implicit_types='bool', parser=lambda x: x == 'true'),
    LoadType(name='int', compatible_implicit_types='int', parser=int),
    LoadType(name='float', compatible_implicit_types='float', parser=float),
    LoadType(name='str', compatible_implicit_types='str', parser=str),
    LoadType(name='bytes', compatible_implicit_types='str', ascii_bytes=True, parser=lambda x: x),
    LoadType(name='base16', compatible_implicit_types='str', ascii_bytes=True, parser=_base16_parser),
    LoadType(name='base64', compatible_implicit_types='str', ascii_bytes=True, parser=_base64_parser),
    LoadType(name='dict', compatible_implicit_types='dict', mutable=True, parser=dict),
    LoadType(name='list', compatible_implicit_types='list', mutable=True, parser=list)
]}

EXTENDED_TYPES = {x.name: x for x in [
    LoadType(name='complex', compatible_implicit_types='complex', parser=complex),
    LoadType(name='rational', compatible_implicit_types='rational', parser=fractions.Fraction),
    LoadType(name='odict', compatible_implicit_types='dict', mutable=True, parser=collections.OrderedDict),
    LoadType(name='set', compatible_implicit_types='list', mutable=True, parser=set)
]}

PYTHON_TYPES = {x.name: x for x in [
    LoadType(name='tuple', compatible_implicit_types='list', parser=tuple)
]}

STANDARD_TYPES = {}
STANDARD_TYPES.update(CORE_TYPES)
STANDARD_TYPES.update(EXTENDED_TYPES)

ALL_TYPES = {}
ALL_TYPES.update(STANDARD_TYPES)
ALL_TYPES.update(PYTHON_TYPES)
