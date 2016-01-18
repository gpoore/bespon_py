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
import sys

if sys.version_info.major == 2:
    # Make `str()`, `bytes()`, and related used of `isinstance()` like Python 3
    __str__ = str
    class bytes(__str__):
        '''
        Emulate Python 3's bytes type.  Only for use with Unicode strings.
        '''
        def __new__(cls, obj, encoding=None, errors='strict'):
            if not isinstance(obj, unicode):
                raise TypeError('the bytes type only supports Unicode strings')
            elif encoding is None:
                raise TypeError('string argument without an encoding')
            else:
                return __str__.__new__(cls, obj.encode(encoding, errors))
    str = unicode

from . import erring
from . import unicoding
import collections




class BespONDecoder(object):
    '''
    Decode BespON.

    Works with Unicode strings or iterables containing Unicode strings.
    '''
    def __init__(self, reservedwords=None, parsers=None, aliases=None, **kwargs):
        # Basic type checking on arguments
        arg_dicts = (reservedwords, parsers, aliases)
        if not all(x is None or isinstance(x, dict) for x in arg_dicts):
            raise TypeError('Arguments {0} must be dicts'.format(','.join('"{0}"'.format(x) for x in arg_dicts)))
        if reservedwords:
            v_s = [v for k, v in reservedwords.items()]
            if not all(x in v_s for x in (True, False, None)):
                raise TypeError('"reservedwords" must define a mapping to True, False, and None')
        if parsers:
            if not all(hasattr(v, '__call__') for k, v in parsers.items()):
                raise TypeError('All parsers must be functions (callable)')


        # Defaults
        self.default_reservedwords = {'true': True, 'false': False, 'null': None}

        self.default_parsers = {#Basic types
                                'dict':        dict,
                                'list':        list,
                                'float':       float,
                                'int':         int,
                                'str':         self.parse_str,
                                #Extended types
                                'str.esc':     self.parse_str_esc,
                                'bin':         self.parse_bin,
                                'bin.esc':     self.parse_bin_esc,
                                #Optional types
                                'bin.base64':  self.parse_bin_base64,
                                'bin.hex':     self.parse_bin_hex,
                                'odict':       collections.OrderedDict,
                                'set':         set,
                                'tuple':       tuple,}

        self.default_aliases = {'esc': 'str.esc', 'bin.b64': 'bin.base64'}


        # Create actual dicts that are used
        self.reservedwords = self.default_reservedwords.copy()
        if reservedwords:
            self.reservedwords.update()

        self.parsers = self.default_parsers.copy()
        if parsers:
            self.parsers.update(parsers)

        self.aliases = self.default_aliases.copy()
        if aliases:
            for k, v in aliases.items():
                if v not in self.parsers:
                    raise ValueError('Alias "{0}" => "{1}" maps to unknown type'.format(k, v))
                self.parsers[k] = self.parsers[v]


        # Create a UnicodeFilter instance
        # Provide shortcuts to some of its attributes
        self.unicodefilter = unicoding.UnicodeFilter(**kwargs)
        self.newlines = self.unicodefilter.newlines
        self.newline_chars = self.unicodefilter.newline_chars
        self.newline_chars_str = self.unicodefilter.newline_chars_str
        self.space_chars = self.unicodedata.space_chars
        self.space_chars_str = self.unicodedata.space_chars_str
        self.indentation_chars = self.unicodefilter.indentation_chars
        self.indentation_chars_str = self.unicodefilter.indentation_chars_str
        self.whitespace = self.unicodefilter.whitespace


    def _inline_unwrap(self, s_list):
        '''
        Unwrap an inline string.
        '''
        s_list_inline = []
        for line in s_list:
            line_strip_nl = line.rstrip(self.newline_chars_str)
            if line_strip_nl.rstrip(self.space_chars_str) != line_strip_nl:
                s_list_inline.append(line_strip_nl)
            else:
                s_list_inline.append(line_strip_nl + '\x20')
        return s_list_inline


    def parse_str(self, s_list, inline):
        '''
        Return a formatted string.

        Receives a list of strings, including newlines, and returns a string.

        Note that this function receives the raw result of parsing.  Any
        non-string indentation has already been stripped.  For unquoted
        strings, any leading/trailing indentation characters and newlines
        have also been stripped/handled.  All other newlines have not been
        handled; any unwrapping for inline strings remains to be done.
        '''
        if inline:
            s = ''.join(self._inline_unwrap(s_list))
        else:
            s = ''.join(s_list)
        return s


    def parse_str_esc(self, s_list, inline):
        '''
        Return an unescaped version of a string.
        '''
        return self.unicodefilter.unescape(self.parse_str(s_list, inline))


    def parse_bin(self, s_list, inline):
        '''
        Return a binary string.
        '''
        if inline:
            s = ''.join(self._inline_unwrap(s_list))
        else:
            s = ''.join(s_list)
        s = self.unicodefilter.unicode_to_bin_newlines(s)
        try:
            b = s.encode('ascii')
        except UnicodeEncodeError:
            raise erring.UnicodeEncodeError('')
        return b


    def parse_bin_esc(self, s_list, inline):
        '''
        Return an unescaped version of a binary string.
        '''
        b = self.parse_bin(s_list, inline)
        return self.unicodefilter.unescape_bin(b)


    def parse_bin_base64(self, s_list, inline):
        '''
        Return a base64-decoded byte string.
        '''
        from base64 import b64decode
        s = ''.join(s_list)
        s = self.unicodefilter.remove_whitespace(s)
        try:
            b = b64decode(s, validate=True)
        except binascii.Error:
            raise erring.B64('')
        return b


    def parse_bin_hex(self, s_list, inline):
        '''
        Return a byte string from hex decoding.
        '''
        import binascii
        s = ''.join(s_list)
        s = self.unicodefilter.remove_whitespace(s)
        return binascii.unhexlify(s)



    def decode(self, obj):
        if isinstance(obj, str):
            pass
        else:
            pass

# HANDLE BOM
