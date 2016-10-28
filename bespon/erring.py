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
    str = unicode
    __chr__ = chr
    chr = unichr

try:
    chr(0x10FFFF)
    NARROW_BUILD = False
except ValueError:
    NARROW_BUILD = True




# Structure for creating tracebacks.
class Traceback(object):
    '''
    Collection of data needed to provide a traceback.
    '''
    def __init__(self, source, start_lineno, start_column, end_lineno=None, end_column=None):
        self.source = source
        self.start_lineno = start_lineno
        self.start_column = start_column
        self.end_lineno = end_lineno or start_lineno
        self.end_column = end_column or start_column




class BespONException(Exception):
    '''
    Base BespON exception.
    '''
    def fmt_msg_with_traceback(self, msg, traceback):
        if traceback is None:
            return '\n  ' + msg
        else:
            if traceback.start_lineno >= traceback.end_lineno:
                if traceback.start_column >= traceback.end_column:
                    t = 'In "{0}" on line {1}:{2}: '.format(traceback.source, traceback.start_lineno, traceback.start_column)
                else:
                    t = 'In "{0}" on line {1}:{2}-{3}: '.format(traceback.source, traceback.start_lineno, traceback.start_column, traceback.end_column)
            else:
                t = 'In "{0}" on lines {1}:{2} - {3}:{4}: '.format(traceback.source, traceback.start_lineno, traceback.start_column, traceback.end_lineno, traceback.end_column)
            return '\n  ' + t + '\n  ' + msg


class InvalidLiteralCharacterError(BespONException):
    '''
    Character that is not allowed to appear literally has appeared.
    '''


class ConfigError(BespONException):
    '''
    Error in configuration or settings.
    '''


class UnknownEscapeError(BespONException):
    '''
    Unknown backslash escape.  Typically raise for short escapes of the form
    `\\<char>`, when the escape has not been registered.
    '''
    def __init__(self, escape_raw, escape_esc, traceback=None):
        self.escape_raw = escape_raw
        self.escape_esc = escape_esc
        self.traceback = traceback
    def __str__(self):
        msg = 'Unknown escape sequence: "{0}"'.format(self.escape_esc)
        return self.fmt_msg_with_traceback(msg, self.traceback)


class UnicodeSurrogateError(BespONException):
    '''
    Unicode surrogate code point.
    '''
    def __init__(self, codepoint_raw, codepoint_esc, traceback=None):
        self.codepoint_raw = codepoint_raw
        self.codepoint_esc = codepoint_esc
        self.traceback = traceback
    def __str__(self):
        if NARROW_BUILD:
            msg = 'Unpaired Unicode surrogate code points are not allowed: "{0}"'.format(self.codepoint_esc)
        else:
            msg = 'Unicode surrogate code points are not allowed: "{0}"'.format(self.codepoint_esc)
        return self.fmt_msg_with_traceback(msg, self.traceback)


class EscapedUnicodeSurrogateError(BespONException):
    '''
    Escaped Unicode surrogate code point.
    '''
    def __init__(self, escape_raw, escape_esc, traceback=None):
        self.escape_raw = escape_raw
        self.escape_esc = escape_esc
        self.traceback = traceback
    def __str__(self):
        msg = 'Escaped Unicode surrogate code points are not allowed: "{0}"'.format(self.escape_esc)
        return self.fmt_msg_with_traceback(msg, self.traceback)


class BinaryError(BespONException):
    '''
    Base class for binary exceptions.
    '''
    def __init__(self, unicode_string, error, traceback=None):
        self.unicode_string = unicode_string
        self.error = error
        self.traceback = traceback


class BinaryStringEncodeError(BinaryError):
    '''
    Error in converting from Unicode string to binary ASCII string.
    '''
    def __str__(self):
        msg = 'Failed to encode to ASCII binary string:\n  {0}'.format(self.error)
        return self.fmt_msg_with_traceback(msg, self.traceback)


class BinaryBase64DecodeError(BinaryError):
    '''
    Error in converting Unicode string to base64 string.
    '''
    def __str__(self):
        msg = 'Failed to decode base64:\n  {0}'.format(self.error)
        return self.fmt_msg_with_traceback(msg, self.traceback)


class BinaryBase16DecodeError(BinaryError):
    '''
    Error in converting Unicode string to base16 string.
    '''
    def __str__(self):
        msg = 'Failed to decode base16 (hex):\n  {0}'.format(self.error)
        return self.fmt_msg_with_traceback(msg, self.traceback)


class ParseError(BespONException):
    '''
    Error during parsing
    '''
    def __init__(self, msg, traceback):
        self.msg = msg
        self.traceback = traceback
    def __str__(self):
        return self.fmt_msg_with_traceback(self.msg, self.traceback)
