# -*- coding: utf-8 -*-
#
# Copyright (c) 2016, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#

# pylint:  disable=C0301

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)


class BespONException(Exception):
    '''
    Base BespON exception.
    '''
    def fmt_msg_with_traceback(self, msg, state_or_obj, other_obj=None, unresolved_cache=False):
        if unresolved_cache:
            if state_or_obj.next_doc_comment is not None:
                cache_obj = state_or_obj.next_doc_comment
            elif state_or_obj.next_tag is not None:
                cache_obj = state_or_obj.next_tag
            elif state_or_obj.next_scalar is not None:
                cache_obj = state_or_obj.next_scalar
            else:
                return '\n  Invalid error message triggered in "{0}" at line {1}:{2}'.format(state_or_obj.source_name,
                                                                                             state_or_obj.first_lineno,
                                                                                             state_or_obj.first_colno)
            if cache_obj.first_lineno == cache_obj.last_lineno:
                traceback = 'In "{0}" on line {1}:{2}, in relation to object at {3}:{4}-{5}:'.format(state_or_obj.source_name,
                                                                                                     state_or_obj.first_lineno,
                                                                                                     state_or_obj.first_colno,
                                                                                                     cache_obj.first_lineno,
                                                                                                     cache_obj.first_colno,
                                                                                                     cache_obj.last_colno)
            else:
                traceback = 'In "{0}" line {1}:{2}, in relation to object at {3}:{4}-{5}:{6}:'.format(state_or_obj.source_name,
                                                                                                      state_or_obj.first_lineno,
                                                                                                      state_or_obj.first_colno,
                                                                                                      cache_obj.first_lineno,
                                                                                                      cache_obj.first_colno,
                                                                                                      cache_obj.last_lineno,
                                                                                                      cache_obj.last_colno)
        else:
            if other_obj is None:
                other_traceback = ''
            elif other_obj.first_lineno == other_obj.last_lineno:
                if other_obj.first_colno == other_obj.last_colno:
                    other_traceback = ', in relation to object at {0}:{1}'.format(other_obj.first_lineno, other_obj.first_colno)
                else:
                    other_traceback = ', in relation to object at {0}:{1}-{2}'.format(other_obj.first_lineno, other_obj.first_colno,
                                                                                      other_obj.last_colno)
            else:
                other_traceback = ', in relation to object at {0}:{1}-{2}:{3}'.format(other_obj.first_lineno, other_obj.first_colno,
                                                                                      other_obj.last_lineno, other_obj.last_colno)
            if state_or_obj.first_lineno == state_or_obj.last_lineno:
                if state_or_obj.first_colno == state_or_obj.last_colno:
                    traceback = 'In "{0}" on line {1}:{2}{3}:'.format(state_or_obj.source_name,
                                                                      state_or_obj.first_lineno, state_or_obj.first_colno,
                                                                      other_traceback)
                else:
                    traceback = 'In "{0}" on line {1}:{2}-{3}{4}:'.format(state_or_obj.source_name,
                                                                          state_or_obj.first_lineno, state_or_obj.first_colno,
                                                                          state_or_obj.last_colno,
                                                                          other_traceback)
            else:
                traceback = 'In "{0}" on line {1}:{2}-{3}:{4}{5}:'.format(state_or_obj.source_name,
                                                                          state_or_obj.first_lineno, state_or_obj.first_colno,
                                                                          state_or_obj.last_lineno, state_or_obj.last_colno,
                                                                          other_traceback)
        return '\n  {0}\n    {1}'.format(traceback, msg)


class Bug(BespONException):
    '''
    There is a bug in the program, as opposed to invalid user data.

    This exception is sometimes used at the end of a sequence of if/elif/else
    or in a similar context as a fallthrough result.  This ensures that if
    bugs exist or are introduced in the future, a more informative error
    message is produced, with traceback information from the data.
    '''
    def __init__(self, msg, state_or_obj):
        self.msg = msg
        self.state_or_obj = state_or_obj
    def __str__(self):
        return self.fmt_msg_with_traceback(self.msg, self.state_or_obj)


def SourceDecodeError(BespONException):
    '''
    Error during decoding of binary source.
    '''
    def __init__(self, err_msg):
        self.err_msg = err_msg
    def __str__(self):
        return 'Could not decode binary source:\n  {0}'.format(self.err_msg)


class InvalidLiteralError(BespONException):
    '''
    Code point that is not allowed to appear literally has appeared.
    '''
    def __init__(self, state_or_obj, code_point, code_point_esc):
        self.state_or_obj = state_or_obj
        self.code_point = code_point
        self.code_point_esc = code_point_esc
    def __str__(self):
        msg = 'Invalid literal code point {0}'.format(self.code_point_esc)
        return self.fmt_msg_with_traceback(msg, self.state_or_obj)


class UnknownEscapeError(BespONException):
    '''
    Unknown backslash escape.
    '''
    def __init__(self, escape_raw, escape_esc):
        self.escape_raw = escape_raw
        self.escape_esc = escape_esc
    def __str__(self):
        return 'Unknown escape sequence: "{0}"'.format(self.escape_esc)


class ParseError(BespONException):
    '''
    General error during parsing.
    '''
    def __init__(self, msg, state_or_obj, other_obj=None, unresolved_cache=False):
        self.msg = msg
        self.state_or_obj = state_or_obj
        self.other_obj = other_obj
        self.unresolved_cache = unresolved_cache
    def __str__(self):
        return self.fmt_msg_with_traceback(self.msg, self.state_or_obj, self.other_obj, self.unresolved_cache)


class IndentationError(ParseError):
    '''
    Error in relative indentation
    '''
    def __init__(self, state_or_obj):
        self.msg = 'Inconsistent relative indentation'
        self.state_or_obj = state_or_obj
    def __str__(self):
        return self.fmt_msg_with_traceback(self.msg, self.state_or_obj)
