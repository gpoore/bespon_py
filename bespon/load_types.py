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
from . import grammar

# pylint:  disable=C0103, W0622, E0602
if sys.version_info.major == 2:
    str = unicode
# pylint:  enable=C0103, W0622, E0602




class DataType(object):
    '''
    Representation of data types.

    Overview of keyword arguments:
        binary:  The typed string represents binary data.  If it contains
                 escapes, only binary-compatible escapes are performed.  The
                 string is encoded to binary via the ascii codec before being
                 passed to the parser.
        mutable: Whether the type is mutable.  Mutable collections are more
                 convenient to work with when resolving aliases, etc.
        number:  Number types.  These are only applied to unquoted strings
                 that match the regex patterns for number literals.  Custom
                 numeric types that require quoted strings must use
                 number=False; this option is only for built-in types.
        parser:  For scalars, a function that takes a parsed string and
                 converts it to the type.  For collections, a function that
                 takes an iterable of paired objects (dict-like) or
                 an iterable of individual objects (list-like), and returns
                 the corresponding collection.  In the collection case,
                 the function must also return an empty object if no
                 arguments are provided.
        tagable: Whether the type may be used in a tag to provide explicit
                 typing.
    '''
    __slots__ = ['name', 'basetype', 'basetype_set',
                 'binary', 'mutable', 'number', 'parser', 'tagable']
    def __init__(self, name=None, basetype=None,
                 binary=False, mutable=False, number=False, parser=None,
                 tagable=True):
        if not all(isinstance(x, str) for x in (name, basetype)):
            raise TypeError
        if not all(x in (True, False) for x in (binary, mutable, number, tagable)):
            raise TypeError
        if not hasattr(parser, '__call__'):
            raise TypeError
        if basetype not in ('dict', 'list', 'scalar'):
            raise ValueError
        if basetype != 'scalar' and (binary or number or not tagable):
            raise ValueError
        self.name = name
        self.basetype = basetype
        self.basetype_set = set((basetype,))
        self.binary = binary
        self.mutable = mutable
        self.number = number
        self.parser = parser
        self.tagable = tagable




_BASE16_RE = re.compile('(?:{0})$'.format(grammar.RE_GRAMMAR['base16'].encode('ascii')).encode('ascii'))

def _base16_parser(b):
    # Need to remove any whitespace padding before decoding.  Also need to
    # validate according to Bespon's Base16 standards, which allow uppercase
    # or lowercase, but prohibit mixed-case.
    b_processed = b.replace(b'\x20', b'').replace(b'\t', b'').replace(b'\n', '')
    if not _BASE16_RE.match(b_processed):
        raise ValueError('Invalid character(s) or mixed-case in Base16-encoded data')
    return base64.b16decode(b_processed, casefold=True)


if sys.version_info.major == 2:
    _BASE64_RE = re.compile('(?:{0})$'.format(grammar.RE_GRAMMAR['base64'].encode('ascii')).encode('ascii'))

    def _base64_parser(b):
        # Need to remove any whitespace padding before decoding.  Also need to
        # validate, since `b64decode()` doesn't provide that under Python 2.7.
        b_processed = b.replace(b'\x20', b'').replace(b'\t', b'').replace(b'\n', '')
        if not _BASE64_RE.match(b_processed):
            raise ValueError('Invalid character(s) in Base64-encoded data')
        return base64.b64decode(b_processed)
else:
    def _base64_parser(b):
        b_processed = b.replace(b'\x20', b'').replace(b'\t', b'').replace(b'\n', '')
        return base64.b64decode(b_processed, validate=True)




# There is no explicit validation of parser function arguments here.  Parser
# functions for scalar types that are always unquoted (none, bool, numbers)
# are only ever called on arguments that have already been validated.  That
# leaves parser functions operating on quoted or unquoted strings.  These are
# given the parsed strings, and are responsible for their own validation
# internally.  The Base16 and Base64 parsers are an example.
CORE_TYPES = {'none': DataType(name='none', basetype='scalar', parser=lambda x: None, tagable=False),
              'bool': DataType(name='bool', basetype='scalar', parser=lambda x: x == 'true', tagable=False),
              'str': DataType(name='str', basetype='scalar', parser=str),
              'int': DataType(name='int', basetype='scalar', number=True, parser=int),
              'float': DataType(name='float', basetype='scalar', number=True, parser=float),
              'bytes': DataType(name='bytes', basetype='scalar', binary=True, parser=lambda x: x),
              'b16': DataType(name='b16', basetype='scalar', binary=True, parser=_base16_parser),
              'b64': DataType(name='b64', basetype='scalar', binary=True, parser=_base64_parser),
              'dict': DataType(name='dict', basetype='dict', mutable=True, parser=dict),
              'list': DataType(name='list', basetype='list', mutable=True, parser=list)}

EXTENDED_TYPES = {}
# #### TO DO:  Add additional standard collections, complex and rational numbers, etc.
# 'odict': DataType(name='odict', basetype='dict', mutable=True, parser=collections.OrderedDict)
# 'set': DataType(name='set', basetype='list', mutable=True, parser=set)
# 'tuple': DataType(name='tuple', basetype='list', parser=tuple)
