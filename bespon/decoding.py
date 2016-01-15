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
    def __init__(self, parse_dict=None, parse_list=None,
                 parse_int=None, parse_float=None,
                 parse_str=None, parse_bool=None, parse_null=None,
                 parse_types=None, parse_aliases=None, **kwargs):

        # Basic type checking on arguments
        kw_type_parsers = (parse_dict, parse_list, parse_int, parse_float,
                           parse_str, parse_bool, parse_null)
        if not all(x is None or hasattr(x, '__call__') for x in kw_type_parsers):
            raise TypeError('Type parsers "parse_*" must be functions (callable)')
        if parse_types is not None and not isinstance(parse_types, dict):
            raise TypeError('"parse_types" must be a dict')
        if (parse_types is not None and
                not all(isinstance(k, str) and hasattr(v, '__call__') for k, v in parse_types.items())):
            raise TypeError('"parse_types" must map strings to functions (callable)')
        if parse_aliases is not None and not isinstance(parse_aliases, dict):
            raise TypeError('"parse_aliases" must be a dict')

        # Default mapping of types to parsing functions
        self.default_parse_types = {#Basic types
                                    'dict':             parse_dict or dict,
                                    'list':             parse_list or list,
                                    'float':            parse_float or float,
                                    'int':              parse_int or int,
                                    'bool':             parse_bool or self.parse_bool,
                                    'null':             parse_null or self.parse_null,
                                    'str':              parse_str or self.parse_str,
                                    #Extended types
                                    'str.esc':          self.parse_str_esc,
                                    'str.unwrap':       self.parse_str_unwrap,
                                    'str.xunwrap':      self.parse_str_xunwrap,
                                    #Optional types
                                    'str.unwrap+esc':   self.parse_str_unwrap_esc,
                                    'str.xunwrap+esc':  self.parse_str_xunwrap_esc,
                                    'bin':              self.parse_bin,
                                    'bin.unwrap':       self.parse_bin_unwrap,
                                    'bin.xunwrap':      self.parse_bin_xunwrap,
        #                            'bin.base64':       self.parse_bin_base64,
        #                            'bin.oct':          self.parse_bin_oct,
        #                            'bin.hex':          self.parse_bin_hex,
                                    'odict':            collections.OrderedDict,
                                    'set':              set,
                                    'tuple':            tuple,}

        # Create actual dict that will be used for looking up parsing functions
        self.parse_types = self.default_parse_types.copy()
        if parse_types:
            self.parse_types.update(parse_types)

        # Create dict of aliases for parsing functions, and update the main
        # parsing dict with it
        """
        self.default_parse_aliases = {'esc': 'str.esc', 'bin.b64': 'bin.base64'}
        for k, v in self.default_parse_aliases.items():
            self.parse_types[k] = self.parse_types[v]
        self.parse_aliases = self.default_parse_aliases.copy()
        if parse_aliases:
            self.parse_aliases.update(parse_aliases)
            for k, v in parse_aliases.items():
                try:
                    self.parse_types[k] = self.parse_types[v]
                except KeyError:
                    raise ValueError('Parse type alias "{0}" maps to unknown type "{1}"'.format(k, v))
        """
        # Create a UnicodeFilter instance
        # Provide shortcuts to some of its attributes
        self.unicodefilter = unicoding.UnicodeFilter(**kwargs)
        self.newlines = self.unicodefilter.newlines
        self.newline_chars = self.unicodefilter.newline_chars
        self.newline_chars_str = self.unicodefilter.newline_chars_str

        self.indentation_chars = set(['\x20', '\t', '\u3000'])
        self.indentation_chars_str = ''.join(self.indentation_chars)
        self.space_chars = set(['\x20', '\u3000'])
        self.space_chars_str = ''.join(self.space_chars)

        self.patterns_bool_true = set(['true'])
        self.patterns_bool_false = set(['false'])
        self.patterns_null = set(['null'])


    def unwrap(self, s_list, inline=False):
        '''
        Unwrap a list of strings, returning a single string.  Remove all
        newlines preceded by a space or ideographic space, except for newlines
        only preceeded by indentation characters, which are kept with the
        preceding indentation characters stripped.  Replace all newlines
        preceded by a non-space/ideographic space with a space.

        An optimized path is provided for inline strings, which cannot contain
        lines consisting only of indentation characters plus newlines, and
        cannot end with newlines.
        '''
        newline_chars_str = self.newline_chars_str
        indentation_chars_str = self.indentation_chars_str
        s_unwrap_list = []

        if inline:
            for line in s_list[:-1]:
                line_strip_nl = line.rstrip(newline_chars_str)
                if line_strip_nl.endswith(' ') or line_strip_nl.endswith('\u3000'):
                    s_unwrap_list.append(line_strip_nl)
                else:
                    s_unwrap_list.append(line_strip_nl + ' ')
            # Last line is guaranteed not to have a newline, due to how inline
            # parsing works
            s_unwrap_list.append(s_list[-1])
        else:
            # Act as if the string were followed by an empty line
            # This allows lookahead from the last actual line
            s_list.append('')

            next_line = s_list[0]
            next_line_strip_nl = next_line.rstrip(newline_chars_str)
            next_line_strip_nl_ic = next_line_strip_nl.lstrip(indentation_chars_str)

            for line in s_list[1:]:
                current_line = next_line
                current_line_strip_nl = next_line_strip_nl
                current_line_strip_nl_ic = next_line_strip_nl_ic
                next_line = line
                next_line_strip_nl = next_line.rstrip(newline_chars_str)
                next_line_strip_nl_ic = next_line_strip_nl.lstrip(indentation_chars_str)
                # Current line is just indentation and newline -- use the newline
                if not current_line_strip_nl_ic:
                    s_unwrap_list.append(current_line.lstrip(indentation_chars_str))
                # Next line is just indentation and newline -- will get a line
                # break, so no need to do anything with current newline
                elif not next_line_strip_nl_ic:
                    s_unwrap_list.append(current_line_strip_nl)
                # If newline follows a space or ideographic space, strip it;
                # otherwise, replace it with a space
                else:
                    if (current_line_strip_nl.endswith(' ') or
                            current_line_strip_nl.endswith('\u3000')):
                        s_unwrap_list.append(current_line_strip_nl)
                    else:
                        s_unwrap_list.append(current_line_strip_nl + ' ')
            # Very last line should get a newline if it had one originally;
            # assume that if it had a newline, it was the end of a paragraph,
            # etc.  A line of indentation chracters will automatically get a
            # newline, but any other line won't, due to the empty string added
            # to the end of the string.
            if current_line_strip_nl_ic:
                s_unwrap_list[-1] += current_line[len(current_line_strip_nl):]

        return ''.join(s_unwrap_list)


    def xunwrap(self, s_list, inline=False):
        '''
        Exact variant of `unwrap()` that removes all newlines, except for
        those on lines consisting only of indentation characters, which are
        kept with the indentation characters stripped.
        '''
        newline_chars_str = self.newline_chars_str
        indentation_chars_str = self.indentation_chars_str
        s_unwrap_list = []

        for line in s_list:
            line_strip_nl = line.rstrip(newline_chars_str)
            line_strip_nl_ic = line_strip_nl.lstrip(indentation_chars_str)
            # Keep lines that contain non-indentation characters, less newline
            if line_strip_nl_ic:
                s_unwrap_list.append(line_strip_nl)
            # Keep only newlines from lines that are indentation characters
            else:
                s_unwrap_list.append(line.lstrip(indentation_chars_str))

        # For non-indentation final line, keep final newline
        if line_strip_nl_ic:
            s_unwrap_list[-1] += line[len(line_strip_nl):]

        return ''.join(s_unwrap_list)


    def parse_bool(self, s):
        '''
        Return boolean corresponding to string.
        '''
        if s in self.patterns_bool_true:
            return True
        elif s in self.patterns_bool_false:
            return False
        else:
            raise ValueError('Invalid string "{0}" for conversion to boolean'.format(s))


    def parse_null(self, s):
        '''
        Return null corresponding to string.
        '''
        if s in self.patterns_null:
            return None
        else:
            return ValueError('Invalid string "{0}" for conversion to null'.format(s))


    def parse_str(self, s_list, inline):
        '''
        Return a formatted string.

        Receives a list of strings, including newlines, and returns a string.

        Note that this function receives the raw result of parsing.  Any
        non-string indentation has already been stripped.  For unquoted
        strings, any leading/trailing indentation characters and newlines
        have also been stripped/handled.  All other newlines have not been
        handled; any unwrapping remains to be done.
        '''
        if inline:
            s = self.unwrap(s_list, inline)
        else:
            s = ''.join(s_list)
        return s


    def parse_str_esc(self, s_list, inline):
        '''
        Return an unescaped version of string.
        '''
        return self.unicodefilter.unescape(self.parse_str(s_list, inline))


    def parse_str_unwrap(self, s_list, inline):
        '''
        Return a string processed with `unwrap()`.  This is already the
        default behavior for inline strings; it only changes the output for
        block strings.
        '''
        return self.unwrap(s_list, inline)


    def parse_str_xunwrap(self, s_list, inline):
        '''
        Return a string processed with `xunwrap()`.  This changes the default
        behavior for both inline and block strings.
        '''
        return self.xunwrap(s_list, inline)


    def parse_str_unwrap_esc(self, s_list, inline):
        '''
        Return a string processed with `unwrap()` and then unescaped.
        '''
        # This could be written more efficiently as
        # `return self.unicodefilter.unescape(self.parse_str_unwrap(s_list, inline))`.
        # However, that approach wouldn't automatically adapt for custom
        # functions that parse unwrapped or escaped strings.  The current
        # approach is safer, since it has the inheritance properties that
        # might naturally be expected.  Unwrapping plus escaping should be
        # relatively rare, so there shouldn't be a need for maximum performance.
        u = self.parse_str_unwrap(s_list, inline)
        e = self.parse_str_esc(u.splitlines(True), inline)
        return e


    def parse_str_xunwrap_esc(self, s_list, inline):
        '''
        Return a string processed with `xunwrap()` and then unescaped.
        '''
        # As with `parse_str_unwrap_esc()`, the function is written to
        # inherit from the functions upon which it is based.
        x = self.parse_str_xunwrap(s_list, inline)
        e = self.parse_str_esc(x.splitlines(True), inline)
        return e


    def parse_bin(self, s_list, inline):
        '''
        Return a binary string.
        '''
        s = self.parse_str(s_list, inline)
        try:
            b = s.encode('ascii')
        except UnicodeEncodeError:
            raise erring.
        return b



    def decode(self, obj):
        if isinstance(obj, str):
            pass
        else:
            pass

# HANDLE BOM
