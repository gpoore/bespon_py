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
import collections

if sys.version_info.major == 2:
    str = unicode
    __chr__ = chr
    chr = unichr


class keydefaultdict(collections.defaultdict):
    '''
    Default dict that passes missing keys to the factory function, rather than
    calling the factory function with no arguments.
    '''
    def __missing__(self, k):
        if self.default_factory is None:
            raise KeyError(k)
        else:
            self[k] = self.default_factory(k)
            return self[k]
