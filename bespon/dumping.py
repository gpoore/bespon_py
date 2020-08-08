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

from .encoding import BespONEncoder


_DEFAULT_ENCODER = BespONEncoder()



def dump(obj, fp, cls=None, **kwargs):
    '''
    Dump data to a file-like object.
    '''
    if cls is None:
        if not kwargs:
            fp.write(_DEFAULT_ENCODER.encode(obj))
        else:
            fp.write(BespONEncoder(**kwargs).encode(obj))
    else:
        fp.write(cls(**kwargs).encode(obj))


def dumps(obj, cls=None, **kwargs):
    '''
    Dump data to a Unicode string.
    '''
    if cls is None:
        if not kwargs:
            return _DEFAULT_ENCODER.encode(obj)
        return BespONEncoder(**kwargs).encode(obj)
    return cls(**kwargs).encode(obj)
