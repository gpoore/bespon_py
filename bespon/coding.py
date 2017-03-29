# -*- coding: utf-8 -*-
#
# Copyright (c) 2016-2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#

'''
Versions of `chr()` and `ord()` that can work with Unicode surrogate pairs.
This is important when working with narrow Python builds, and for generating
regular expressions that will be used in languages whose native string
implementation is based on UTF-16.
'''


from __future__ import (division, print_function, absolute_import,
                        unicode_literals)


import sys


# pylint: disable=E0602, W0622
if sys.version_info.major == 2:
    str = unicode
    chr = unichr
# pylint: enable=E0602, W0622


if sys.maxunicode == 0xFFFF:
    __narrow_chr__ = unichr
    __narrow_ord__ = ord
    def chr_surrogate(cp):
        '''
        Version of `chr()` that uses Unicode surrogate pairs to represent
        code points outside the Basic Multilingual Plane.
        '''
        if cp <= 0xFFFF:
            return __narrow_chr__(cp)
        # http://www.unicode.org/faq//utf_bom.html#utf16-4
        return __narrow_chr__(0xD7C0 + (cp >> 10)) + __narrow_chr__(0xDC00 + (cp & 0x3FF))
    def ord_surrogate(c):
        '''
        Version of `ord()` that can accept Unicode surrogate pairs and return
        the integer value of the code point represented by them.
        '''
        if len(c) != 2:
            return __narrow_ord__(c)
        ord_c_0 = __narrow_ord__(c[0])
        ord_c_1 = __narrow_ord__(c[1])
        if 0xD800 <= ord_c_0 <= 0xDBFF and 0xDC00 <= ord_c_1 <= 0xDFFF:
            # http://www.unicode.org/faq//utf_bom.html#utf16-4
            return -0x35FDC00 + (ord_c_0 << 10) + ord_c_1
        raise UnicodeError
else:
    def chr_surrogate(cp):
        '''
        Version of `chr()` that uses Unicode surrogate pairs to represent
        code points outside the Basic Multilingual Plane.
        '''
        if cp <= 0xFFFF:
            return chr(cp)
        # http://www.unicode.org/faq//utf_bom.html#utf16-4
        return chr(0xD7C0 + (cp >> 10)) + chr(0xDC00 + (cp & 0x3FF))
    def ord_surrogate(c):
        '''
        Version of `ord()` that can accept Unicode surrogate pairs and return
        the integer value of the code point represented by them.
        '''
        if len(c) != 2:
            return ord(c)
        ord_c_0 = ord(c[0])
        ord_c_1 = ord(c[1])
        if 0xD800 <= ord_c_0 <= 0xDBFF and 0xDC00 <= ord_c_1 <= 0xDFFF:
            # http://www.unicode.org/faq//utf_bom.html#utf16-4
            return -0x35FDC00 + (ord_c_0 << 10) + ord_c_1
        raise UnicodeError
