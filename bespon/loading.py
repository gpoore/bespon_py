# -*- coding: utf-8 -*-
#
# Copyright (c) 2016-2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

from .decoding import BespONDecoder


_DEFAULT_DECODER = BespONDecoder()


def load(fp, cls=None, **kwargs):
    '''
    Load data from a file-like object.
    '''
    # Iterating over the file-like object one line at a time is tempting,
    # since that's how the parsing actually works.  However, doing that would
    # involve invoking the regex for invalid code points multiple times, which
    # would add significant overhead.  It would also mean that checks for lone
    # `\r` would be needed for each individual line.
    if cls is None:
        if not kwargs:
            return _DEFAULT_DECODER.decode(fp.read())
        return BespONDecoder(**kwargs).decode(fp.read())
    return cls(**kwargs).decode(fp.read())


def loads(s, cls=None, **kwargs):
    '''
    Load data from a Unicode or byte string.
    '''
    if cls is None:
        if not kwargs:
            return _DEFAULT_DECODER.decode(s)
        return BespONDecoder(**kwargs).decode(s)
    return cls(**kwargs).decode(s)
