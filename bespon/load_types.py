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




class DataType(object):
    '''
    Representation of data types.

    Overview of keyword arguments:
        ascii_bytes:  The typed string represents binary data using ASCII.
                      If escapes are used, only bytes-compatible escapes are
                      allowed.  The string is encoded to binary with the
                      ASCII codec before being passed to the parser.
        mutable:      Whether the type is mutable.  Mutable collections are
                      more convenient to work with when resolving aliases.
        number:       Number types.  These are only applied to unquoted
                      strings that match the regex patterns for number
                      literals.  Custom numeric types that require quoted
                      strings must use number=False; this option is only for
                      built-in types.
        parser:       For scalars, a function that takes a processed string
                      and converts it to the type.  For collections, a
                      function that takes an iterable of paired objects
                      (dict-like) or an iterable of individual objects
                      (list-like), and returns the corresponding collection.
                      In the collection case, the function must also return
                      an empty object if no arguments are provided.
        typeable:     Whether the type may be used in a tag to provide
                      explicit typing.
    '''
    __slots__ = ['name', 'basetype', 'basetype_set', 'mutable',
                 'ascii_bytes', 'escapes', 'number', 'parser', 'typeable']
    def __init__(self, name=None, basetype=None,
                 ascii_bytes=False, mutable=False, number=False, parser=None,
                 typeable=True):
        if not all(isinstance(x, str) for x in (name, basetype)):
            raise TypeError
        if not all(x in (True, False) for x in (ascii_bytes, mutable, number, typeable)):
            raise TypeError
        if not hasattr(parser, '__call__'):
            raise TypeError
        if basetype not in ('dict', 'list', 'scalar'):
            raise ValueError
        if basetype != 'scalar' and (ascii_bytes or number or not typeable):
            raise ValueError
        self.name = name
        self.basetype = basetype
        self.basetype_set = set((basetype,))
        self.ascii_bytes = ascii_bytes
        self.mutable = mutable
        self.number = number
        self.parser = parser
        self.typeable = typeable




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
CORE_TYPES = {'none': DataType(name='none', basetype='scalar', parser=lambda x: None, typeable=False),
              'bool': DataType(name='bool', basetype='scalar', parser=lambda x: x == 'true', typeable=False),
              'str': DataType(name='str', basetype='scalar', parser=str),
              'int': DataType(name='int', basetype='scalar', number=True, parser=int),
              'float': DataType(name='float', basetype='scalar', number=True, parser=float),
              'bytes': DataType(name='bytes', basetype='scalar', ascii_bytes=True, parser=lambda x: x),
              'base16': DataType(name='b16', basetype='scalar', ascii_bytes=True, parser=_base16_parser),
              'base64': DataType(name='b64', basetype='scalar', ascii_bytes=True, parser=_base64_parser),
              'dict': DataType(name='dict', basetype='dict', mutable=True, parser=dict),
              'list': DataType(name='list', basetype='list', mutable=True, parser=list)}

EXTENDED_TYPES = {'complex': DataType(name='complex', basetype='scalar', number=True, parser=complex),
                  'rational': DataType(name='rational', basetype='scalar', number=True, parser=fractions.Fraction),
                  'odict': DataType(name='odict', basetype='dict', mutable=True, parser=collections.OrderedDict),
                  'set': DataType(name='set', basetype='list', mutable=True, parser=set),
                  'tuple': DataType(name='tuple', basetype='list', parser=tuple)}
