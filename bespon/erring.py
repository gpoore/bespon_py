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


class BespONException(Exception):
    '''
    Base BespON exception.
    '''
    pass


class DecodingException(BespONException):
    '''
    Base decoding exception.
    '''
    def fmt_msg_with_traceback(self, msg, state_or_node, other_nodes=None, unresolved_cache=False):
        source_name = state_or_node._state.source_name
        if unresolved_cache:
            if not hasattr(state_or_node, 'next_cache'):
                raise Bug('Invalid error message', state_or_node)
            state = state_or_node
            if state.next_doc_comment is not None:
                cache_obj = state.next_doc_comment
                cache_name = 'doc comment'
            elif state.next_tag is not None:
                cache_obj = state.next_tag
                cache_name = 'tag'
            elif state.next_scalar is not None:
                cache_obj = state.next_scalar
                cache_name = 'scalar object'
            else:
                raise Bug('Invalid error message', state)
            if cache_obj.first_lineno == cache_obj.last_lineno:
                if cache_obj.first_colno == cache_obj.last_colno:
                    traceback = 'In "{0}" at line {1}:{2}, in relation to {3} at {4}:{5}:'.format(source_name,
                                                                                                  state.lineno,
                                                                                                  state.colno,
                                                                                                  cache_name,
                                                                                                  cache_obj.first_lineno,
                                                                                                  cache_obj.first_colno)
                else:
                    traceback = 'In "{0}" at line {1}:{2}, in relation to {3} at {4}:{5}-{6}:'.format(source_name,
                                                                                                      state.lineno,
                                                                                                      state.colno,
                                                                                                      cache_name,
                                                                                                      cache_obj.first_lineno,
                                                                                                      cache_obj.first_colno,
                                                                                                      cache_obj.last_colno)
            else:
                traceback = 'In "{0}" at line {1}:{2}, in relation to {3} at {4}:{5}-{6}:{7}:'.format(source_name,
                                                                                                      state.lineno,
                                                                                                      state.colno,
                                                                                                      cache_name,
                                                                                                      cache_obj.first_lineno,
                                                                                                      cache_obj.first_colno,
                                                                                                      cache_obj.last_lineno,
                                                                                                      cache_obj.last_colno)
        else:
            if other_nodes is None:
                other_traceback = ''
            else:
                if not isinstance(other_nodes, list):
                    other_nodes = [other_nodes]
                other_obj_locs = []
                for other_obj in other_nodes:
                    if other_obj.first_lineno == other_obj.last_lineno:
                        if other_obj.first_colno == other_obj.last_colno:
                            loc = '{0}:{1}'.format(other_obj.first_lineno, other_obj.first_colno)
                        else:
                            loc = '{0}:{1}-{2}'.format(other_obj.first_lineno, other_obj.first_colno,
                                                                               other_obj.last_colno)
                    else:
                        loc = '{0}:{1}-{2}:{3}'.format(other_obj.first_lineno, other_obj.first_colno,
                                                       other_obj.last_lineno, other_obj.last_colno)
                    other_obj_locs.append(loc)
                if len(other_obj_locs) == 1:
                    other_traceback = ', in relation to object at ' + other_obj_locs[0]
                elif len(other_obj_locs) == 2:
                    other_traceback = ', in relation to objects at {0} and {1}'.format(other_obj_locs[0], other_obj_locs[1])
                else:
                    other_traceback = ', in relation to objects at ' + ', '.join(other_obj_locs[:-1]) + ', and ' + other_obj_locs[-1]
            if hasattr(state_or_node, 'next_cache'):
                first_lineno = last_lineno = state_or_node.lineno
                first_colno = last_colno = state_or_node.colno
            else:
                first_lineno = state_or_node.first_lineno
                first_colno = state_or_node.first_colno
                last_lineno = state_or_node.last_lineno
                last_colno = state_or_node.last_colno
            if first_lineno == last_lineno:
                if first_colno == last_colno:
                    traceback = 'In "{0}" at line {1}:{2}{3}:'.format(source_name,
                                                                      first_lineno, first_colno,
                                                                      other_traceback)
                else:
                    traceback = 'In "{0}" at line {1}:{2}-{3}{4}:'.format(source_name,
                                                                          first_lineno, first_colno,
                                                                          last_colno,
                                                                          other_traceback)
            else:
                traceback = 'In "{0}" at line {1}:{2}-{3}:{4}{5}:'.format(source_name,
                                                                          first_lineno, first_colno,
                                                                          last_lineno, last_colno,
                                                                          other_traceback)
        return '\n  {0}\n    {1}'.format(traceback, msg)


class Bug(DecodingException):
    '''
    There is a bug in the program, as opposed to invalid user data.

    This exception is sometimes used at the end of a sequence of if/elif/else
    or in a similar context as a fallthrough.  This ensures that if bugs exist
    or are introduced in the future, a more informative error message is
    produced, with traceback information from the data.
    '''
    def __init__(self, msg, state_or_node):
        self.msg = msg
        self.state_or_node = state_or_node
    def __str__(self):
        return self.fmt_msg_with_traceback(self.msg, self.state_or_node)


class SourceDecodeError(DecodingException):
    '''
    Error during decoding of binary source.
    '''
    def __init__(self, err_msg):
        self.err_msg = err_msg
    def __str__(self):
        return 'Could not decode binary source, or received a non-Unicode, non-bytes object:\n  {0}'.format(self.err_msg)


class InvalidLiteralError(DecodingException):
    '''
    Code point that is not allowed to appear literally has appeared.
    '''
    def __init__(self, state_or_node, code_point, code_point_esc, comment=None):
        self.state_or_node = state_or_node
        self.code_point = code_point
        self.code_point_esc = code_point_esc
        self.comment = comment
    def __str__(self):
        if self.comment is None:
            msg = 'Invalid literal code point "{0}"'.format(self.code_point_esc)
        else:
            msg = 'Invalid literal code point "{0}" ({1})'.format(self.code_point_esc, self.comment)
        return self.fmt_msg_with_traceback(msg, self.state_or_node)


class UnknownEscapeError(DecodingException):
    '''
    Unknown backslash escape.
    '''
    def __init__(self, escape_raw, escape_esc):
        self.escape_raw = escape_raw
        self.escape_esc = escape_esc
    def __str__(self):
        return 'Unknown escape sequence: "{0}"'.format(self.escape_esc)


class ParseError(DecodingException):
    '''
    General error during parsing.
    '''
    def __init__(self, msg, state_or_node, other_obj=None, unresolved_cache=False):
        self.msg = msg
        self.state_or_node = state_or_node
        self.other_obj = other_obj
        self.unresolved_cache = unresolved_cache
    def __str__(self):
        return self.fmt_msg_with_traceback(self.msg, self.state_or_node, self.other_obj, self.unresolved_cache)


class IndentationError(DecodingException):
    '''
    Error in relative indentation
    '''
    def __init__(self, state_or_node):
        self.msg = 'Inconsistent relative indentation'
        self.state_or_node = state_or_node
    def __str__(self):
        return self.fmt_msg_with_traceback(self.msg, self.state_or_node)
