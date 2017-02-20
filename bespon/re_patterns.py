# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


# pylint: disable=C0301, C0330

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)


from .version import __version__
import sys
import itertools
from . import coding


# pylint: disable=E0602, W0622
if sys.version_info.major == 2:
    str = unicode
    chr = unichr
    range = xrange
# pylint: enable=E0602, W0622
# pylint: disable=W0622
if sys.maxunicode == 0xFFFF:
    chr = coding.chr_surrogate
    ord = coding.ord_surrogate
# pylint: enable=W0622




# Regular expression patterns for XID_Start and XID_Continue, and for the
# ASCII subsets of these.  The Hangul fillers are excluded, because they are
# frequently rendered as normal spaces and thus can result in unintuitive
# behavior.
#
# hangul_fillers = set([0x115F, 0x1160, 0x3164, 0xFFA0])
# xid_start_less_fillers = set([cp for cp, data in unicodetools.ucd.derivedcoreproperties.items() if 'XID_Start' in data and cp not in hangul_fillers])
if sys.maxunicode == 0xFFFF:
    XID_START_LESS_FILLERS = '''
        [A-Za-z\\\u00AA\\\u00B5\\\u00BA\\\u00C0-\\\u00D6\\\u00D8-\\\u00F6\\\u00F8-\\\u02C1\\\u02C6-\\\u02D1\\\u02E0-\\\u02E4\\\u02EC\\\u02EE\\\u0370-\\\u0374
         \\\u0376-\\\u0377\\\u037B-\\\u037D\\\u037F\\\u0386\\\u0388-\\\u038A\\\u038C\\\u038E-\\\u03A1\\\u03A3-\\\u03F5\\\u03F7-\\\u0481\\\u048A-\\\u052F
         \\\u0531-\\\u0556\\\u0559\\\u0561-\\\u0587\\\u05D0-\\\u05EA\\\u05F0-\\\u05F2\\\u0620-\\\u064A\\\u066E-\\\u066F\\\u0671-\\\u06D3\\\u06D5
         \\\u06E5-\\\u06E6\\\u06EE-\\\u06EF\\\u06FA-\\\u06FC\\\u06FF\\\u0710\\\u0712-\\\u072F\\\u074D-\\\u07A5\\\u07B1\\\u07CA-\\\u07EA\\\u07F4-\\\u07F5
         \\\u07FA\\\u0800-\\\u0815\\\u081A\\\u0824\\\u0828\\\u0840-\\\u0858\\\u08A0-\\\u08B4\\\u08B6-\\\u08BD\\\u0904-\\\u0939\\\u093D\\\u0950
         \\\u0958-\\\u0961\\\u0971-\\\u0980\\\u0985-\\\u098C\\\u098F-\\\u0990\\\u0993-\\\u09A8\\\u09AA-\\\u09B0\\\u09B2\\\u09B6-\\\u09B9\\\u09BD\\\u09CE
         \\\u09DC-\\\u09DD\\\u09DF-\\\u09E1\\\u09F0-\\\u09F1\\\u0A05-\\\u0A0A\\\u0A0F-\\\u0A10\\\u0A13-\\\u0A28\\\u0A2A-\\\u0A30\\\u0A32-\\\u0A33
         \\\u0A35-\\\u0A36\\\u0A38-\\\u0A39\\\u0A59-\\\u0A5C\\\u0A5E\\\u0A72-\\\u0A74\\\u0A85-\\\u0A8D\\\u0A8F-\\\u0A91\\\u0A93-\\\u0AA8\\\u0AAA-\\\u0AB0
         \\\u0AB2-\\\u0AB3\\\u0AB5-\\\u0AB9\\\u0ABD\\\u0AD0\\\u0AE0-\\\u0AE1\\\u0AF9\\\u0B05-\\\u0B0C\\\u0B0F-\\\u0B10\\\u0B13-\\\u0B28\\\u0B2A-\\\u0B30
         \\\u0B32-\\\u0B33\\\u0B35-\\\u0B39\\\u0B3D\\\u0B5C-\\\u0B5D\\\u0B5F-\\\u0B61\\\u0B71\\\u0B83\\\u0B85-\\\u0B8A\\\u0B8E-\\\u0B90\\\u0B92-\\\u0B95
         \\\u0B99-\\\u0B9A\\\u0B9C\\\u0B9E-\\\u0B9F\\\u0BA3-\\\u0BA4\\\u0BA8-\\\u0BAA\\\u0BAE-\\\u0BB9\\\u0BD0\\\u0C05-\\\u0C0C\\\u0C0E-\\\u0C10
         \\\u0C12-\\\u0C28\\\u0C2A-\\\u0C39\\\u0C3D\\\u0C58-\\\u0C5A\\\u0C60-\\\u0C61\\\u0C80\\\u0C85-\\\u0C8C\\\u0C8E-\\\u0C90\\\u0C92-\\\u0CA8
         \\\u0CAA-\\\u0CB3\\\u0CB5-\\\u0CB9\\\u0CBD\\\u0CDE\\\u0CE0-\\\u0CE1\\\u0CF1-\\\u0CF2\\\u0D05-\\\u0D0C\\\u0D0E-\\\u0D10\\\u0D12-\\\u0D3A\\\u0D3D
         \\\u0D4E\\\u0D54-\\\u0D56\\\u0D5F-\\\u0D61\\\u0D7A-\\\u0D7F\\\u0D85-\\\u0D96\\\u0D9A-\\\u0DB1\\\u0DB3-\\\u0DBB\\\u0DBD\\\u0DC0-\\\u0DC6
         \\\u0E01-\\\u0E30\\\u0E32\\\u0E40-\\\u0E46\\\u0E81-\\\u0E82\\\u0E84\\\u0E87-\\\u0E88\\\u0E8A\\\u0E8D\\\u0E94-\\\u0E97\\\u0E99-\\\u0E9F
         \\\u0EA1-\\\u0EA3\\\u0EA5\\\u0EA7\\\u0EAA-\\\u0EAB\\\u0EAD-\\\u0EB0\\\u0EB2\\\u0EBD\\\u0EC0-\\\u0EC4\\\u0EC6\\\u0EDC-\\\u0EDF\\\u0F00
         \\\u0F40-\\\u0F47\\\u0F49-\\\u0F6C\\\u0F88-\\\u0F8C\\\u1000-\\\u102A\\\u103F\\\u1050-\\\u1055\\\u105A-\\\u105D\\\u1061\\\u1065-\\\u1066
         \\\u106E-\\\u1070\\\u1075-\\\u1081\\\u108E\\\u10A0-\\\u10C5\\\u10C7\\\u10CD\\\u10D0-\\\u10FA\\\u10FC-\\\u115E\\\u1161-\\\u1248\\\u124A-\\\u124D
         \\\u1250-\\\u1256\\\u1258\\\u125A-\\\u125D\\\u1260-\\\u1288\\\u128A-\\\u128D\\\u1290-\\\u12B0\\\u12B2-\\\u12B5\\\u12B8-\\\u12BE\\\u12C0
         \\\u12C2-\\\u12C5\\\u12C8-\\\u12D6\\\u12D8-\\\u1310\\\u1312-\\\u1315\\\u1318-\\\u135A\\\u1380-\\\u138F\\\u13A0-\\\u13F5\\\u13F8-\\\u13FD
         \\\u1401-\\\u166C\\\u166F-\\\u167F\\\u1681-\\\u169A\\\u16A0-\\\u16EA\\\u16EE-\\\u16F8\\\u1700-\\\u170C\\\u170E-\\\u1711\\\u1720-\\\u1731
         \\\u1740-\\\u1751\\\u1760-\\\u176C\\\u176E-\\\u1770\\\u1780-\\\u17B3\\\u17D7\\\u17DC\\\u1820-\\\u1877\\\u1880-\\\u18A8\\\u18AA\\\u18B0-\\\u18F5
         \\\u1900-\\\u191E\\\u1950-\\\u196D\\\u1970-\\\u1974\\\u1980-\\\u19AB\\\u19B0-\\\u19C9\\\u1A00-\\\u1A16\\\u1A20-\\\u1A54\\\u1AA7\\\u1B05-\\\u1B33
         \\\u1B45-\\\u1B4B\\\u1B83-\\\u1BA0\\\u1BAE-\\\u1BAF\\\u1BBA-\\\u1BE5\\\u1C00-\\\u1C23\\\u1C4D-\\\u1C4F\\\u1C5A-\\\u1C7D\\\u1C80-\\\u1C88
         \\\u1CE9-\\\u1CEC\\\u1CEE-\\\u1CF1\\\u1CF5-\\\u1CF6\\\u1D00-\\\u1DBF\\\u1E00-\\\u1F15\\\u1F18-\\\u1F1D\\\u1F20-\\\u1F45\\\u1F48-\\\u1F4D
         \\\u1F50-\\\u1F57\\\u1F59\\\u1F5B\\\u1F5D\\\u1F5F-\\\u1F7D\\\u1F80-\\\u1FB4\\\u1FB6-\\\u1FBC\\\u1FBE\\\u1FC2-\\\u1FC4\\\u1FC6-\\\u1FCC
         \\\u1FD0-\\\u1FD3\\\u1FD6-\\\u1FDB\\\u1FE0-\\\u1FEC\\\u1FF2-\\\u1FF4\\\u1FF6-\\\u1FFC\\\u2071\\\u207F\\\u2090-\\\u209C\\\u2102\\\u2107
         \\\u210A-\\\u2113\\\u2115\\\u2118-\\\u211D\\\u2124\\\u2126\\\u2128\\\u212A-\\\u2139\\\u213C-\\\u213F\\\u2145-\\\u2149\\\u214E\\\u2160-\\\u2188
         \\\u2C00-\\\u2C2E\\\u2C30-\\\u2C5E\\\u2C60-\\\u2CE4\\\u2CEB-\\\u2CEE\\\u2CF2-\\\u2CF3\\\u2D00-\\\u2D25\\\u2D27\\\u2D2D\\\u2D30-\\\u2D67\\\u2D6F
         \\\u2D80-\\\u2D96\\\u2DA0-\\\u2DA6\\\u2DA8-\\\u2DAE\\\u2DB0-\\\u2DB6\\\u2DB8-\\\u2DBE\\\u2DC0-\\\u2DC6\\\u2DC8-\\\u2DCE\\\u2DD0-\\\u2DD6
         \\\u2DD8-\\\u2DDE\\\u3005-\\\u3007\\\u3021-\\\u3029\\\u3031-\\\u3035\\\u3038-\\\u303C\\\u3041-\\\u3096\\\u309D-\\\u309F\\\u30A1-\\\u30FA
         \\\u30FC-\\\u30FF\\\u3105-\\\u312D\\\u3131-\\\u3163\\\u3165-\\\u318E\\\u31A0-\\\u31BA\\\u31F0-\\\u31FF\\\u3400-\\\u4DB5\\\u4E00-\\\u9FD5
         \\\uA000-\\\uA48C\\\uA4D0-\\\uA4FD\\\uA500-\\\uA60C\\\uA610-\\\uA61F\\\uA62A-\\\uA62B\\\uA640-\\\uA66E\\\uA67F-\\\uA69D\\\uA6A0-\\\uA6EF
         \\\uA717-\\\uA71F\\\uA722-\\\uA788\\\uA78B-\\\uA7AE\\\uA7B0-\\\uA7B7\\\uA7F7-\\\uA801\\\uA803-\\\uA805\\\uA807-\\\uA80A\\\uA80C-\\\uA822
         \\\uA840-\\\uA873\\\uA882-\\\uA8B3\\\uA8F2-\\\uA8F7\\\uA8FB\\\uA8FD\\\uA90A-\\\uA925\\\uA930-\\\uA946\\\uA960-\\\uA97C\\\uA984-\\\uA9B2\\\uA9CF
         \\\uA9E0-\\\uA9E4\\\uA9E6-\\\uA9EF\\\uA9FA-\\\uA9FE\\\uAA00-\\\uAA28\\\uAA40-\\\uAA42\\\uAA44-\\\uAA4B\\\uAA60-\\\uAA76\\\uAA7A\\\uAA7E-\\\uAAAF
         \\\uAAB1\\\uAAB5-\\\uAAB6\\\uAAB9-\\\uAABD\\\uAAC0\\\uAAC2\\\uAADB-\\\uAADD\\\uAAE0-\\\uAAEA\\\uAAF2-\\\uAAF4\\\uAB01-\\\uAB06\\\uAB09-\\\uAB0E
         \\\uAB11-\\\uAB16\\\uAB20-\\\uAB26\\\uAB28-\\\uAB2E\\\uAB30-\\\uAB5A\\\uAB5C-\\\uAB65\\\uAB70-\\\uABE2\\\uAC00-\\\uD7A3\\\uD7B0-\\\uD7C6
         \\\uD7CB-\\\uD7FB\\\uF900-\\\uFA6D\\\uFA70-\\\uFAD9\\\uFB00-\\\uFB06\\\uFB13-\\\uFB17\\\uFB1D\\\uFB1F-\\\uFB28\\\uFB2A-\\\uFB36\\\uFB38-\\\uFB3C
         \\\uFB3E\\\uFB40-\\\uFB41\\\uFB43-\\\uFB44\\\uFB46-\\\uFBB1\\\uFBD3-\\\uFC5D\\\uFC64-\\\uFD3D\\\uFD50-\\\uFD8F\\\uFD92-\\\uFDC7\\\uFDF0-\\\uFDF9
         \\\uFE71\\\uFE73\\\uFE77\\\uFE79\\\uFE7B\\\uFE7D\\\uFE7F-\\\uFEFC\\\uFF21-\\\uFF3A\\\uFF41-\\\uFF5A\\\uFF66-\\\uFF9D\\\uFFA1-\\\uFFBE
         \\\uFFC2-\\\uFFC7\\\uFFCA-\\\uFFCF\\\uFFD2-\\\uFFD7\\\uFFDA-\\\uFFDC]
        |
        \\\uD800[\\\uDC00-\\\uDC0B]|\\\uD800[\\\uDC0D-\\\uDC26]|\\\uD800[\\\uDC28-\\\uDC3A]|\\\uD800[\\\uDC3C-\\\uDC3D]|\\\uD800[\\\uDC3F-\\\uDC4D]|
        \\\uD800[\\\uDC50-\\\uDC5D]|\\\uD800[\\\uDC80-\\\uDCFA]|\\\uD800[\\\uDD40-\\\uDD74]|\\\uD800[\\\uDE80-\\\uDE9C]|\\\uD800[\\\uDEA0-\\\uDED0]|
        \\\uD800[\\\uDF00-\\\uDF1F]|\\\uD800[\\\uDF30-\\\uDF4A]|\\\uD800[\\\uDF50-\\\uDF75]|\\\uD800[\\\uDF80-\\\uDF9D]|\\\uD800[\\\uDFA0-\\\uDFC3]|
        \\\uD800[\\\uDFC8-\\\uDFCF]|\\\uD800[\\\uDFD1-\\\uDFD5]|\\\uD801[\\\uDC00-\\\uDC9D]|\\\uD801[\\\uDCB0-\\\uDCD3]|\\\uD801[\\\uDCD8-\\\uDCFB]|
        \\\uD801[\\\uDD00-\\\uDD27]|\\\uD801[\\\uDD30-\\\uDD63]|\\\uD801[\\\uDE00-\\\uDF36]|\\\uD801[\\\uDF40-\\\uDF55]|\\\uD801[\\\uDF60-\\\uDF67]|
        \\\uD802[\\\uDC00-\\\uDC05]|\\\uD802\\\uDC08|\\\uD802[\\\uDC0A-\\\uDC35]|\\\uD802[\\\uDC37-\\\uDC38]|\\\uD802\\\uDC3C|\\\uD802[\\\uDC3F-\\\uDC55]|
        \\\uD802[\\\uDC60-\\\uDC76]|\\\uD802[\\\uDC80-\\\uDC9E]|\\\uD802[\\\uDCE0-\\\uDCF2]|\\\uD802[\\\uDCF4-\\\uDCF5]|\\\uD802[\\\uDD00-\\\uDD15]|
        \\\uD802[\\\uDD20-\\\uDD39]|\\\uD802[\\\uDD80-\\\uDDB7]|\\\uD802[\\\uDDBE-\\\uDDBF]|\\\uD802\\\uDE00|\\\uD802[\\\uDE10-\\\uDE13]|
        \\\uD802[\\\uDE15-\\\uDE17]|\\\uD802[\\\uDE19-\\\uDE33]|\\\uD802[\\\uDE60-\\\uDE7C]|\\\uD802[\\\uDE80-\\\uDE9C]|\\\uD802[\\\uDEC0-\\\uDEC7]|
        \\\uD802[\\\uDEC9-\\\uDEE4]|\\\uD802[\\\uDF00-\\\uDF35]|\\\uD802[\\\uDF40-\\\uDF55]|\\\uD802[\\\uDF60-\\\uDF72]|\\\uD802[\\\uDF80-\\\uDF91]|
        \\\uD803[\\\uDC00-\\\uDC48]|\\\uD803[\\\uDC80-\\\uDCB2]|\\\uD803[\\\uDCC0-\\\uDCF2]|\\\uD804[\\\uDC03-\\\uDC37]|\\\uD804[\\\uDC83-\\\uDCAF]|
        \\\uD804[\\\uDCD0-\\\uDCE8]|\\\uD804[\\\uDD03-\\\uDD26]|\\\uD804[\\\uDD50-\\\uDD72]|\\\uD804\\\uDD76|\\\uD804[\\\uDD83-\\\uDDB2]|
        \\\uD804[\\\uDDC1-\\\uDDC4]|\\\uD804\\\uDDDA|\\\uD804\\\uDDDC|\\\uD804[\\\uDE00-\\\uDE11]|\\\uD804[\\\uDE13-\\\uDE2B]|\\\uD804[\\\uDE80-\\\uDE86]|
        \\\uD804\\\uDE88|\\\uD804[\\\uDE8A-\\\uDE8D]|\\\uD804[\\\uDE8F-\\\uDE9D]|\\\uD804[\\\uDE9F-\\\uDEA8]|\\\uD804[\\\uDEB0-\\\uDEDE]|
        \\\uD804[\\\uDF05-\\\uDF0C]|\\\uD804[\\\uDF0F-\\\uDF10]|\\\uD804[\\\uDF13-\\\uDF28]|\\\uD804[\\\uDF2A-\\\uDF30]|\\\uD804[\\\uDF32-\\\uDF33]|
        \\\uD804[\\\uDF35-\\\uDF39]|\\\uD804\\\uDF3D|\\\uD804\\\uDF50|\\\uD804[\\\uDF5D-\\\uDF61]|\\\uD805[\\\uDC00-\\\uDC34]|\\\uD805[\\\uDC47-\\\uDC4A]|
        \\\uD805[\\\uDC80-\\\uDCAF]|\\\uD805[\\\uDCC4-\\\uDCC5]|\\\uD805\\\uDCC7|\\\uD805[\\\uDD80-\\\uDDAE]|\\\uD805[\\\uDDD8-\\\uDDDB]|
        \\\uD805[\\\uDE00-\\\uDE2F]|\\\uD805\\\uDE44|\\\uD805[\\\uDE80-\\\uDEAA]|\\\uD805[\\\uDF00-\\\uDF19]|\\\uD806[\\\uDCA0-\\\uDCDF]|\\\uD806\\\uDCFF|
        \\\uD806[\\\uDEC0-\\\uDEF8]|\\\uD807[\\\uDC00-\\\uDC08]|\\\uD807[\\\uDC0A-\\\uDC2E]|\\\uD807\\\uDC40|\\\uD807[\\\uDC72-\\\uDC8F]|
        \\\uD808[\\\uDC00-\\\uDF99]|\\\uD809[\\\uDC00-\\\uDC6E]|\\\uD809[\\\uDC80-\\\uDD43]|\\\uD80C[\\\uDC00-\\\uDFFF]|\\\uD80D[\\\uDC00-\\\uDC2E]|
        \\\uD811[\\\uDC00-\\\uDE46]|\\\uD81A[\\\uDC00-\\\uDE38]|\\\uD81A[\\\uDE40-\\\uDE5E]|\\\uD81A[\\\uDED0-\\\uDEED]|\\\uD81A[\\\uDF00-\\\uDF2F]|
        \\\uD81A[\\\uDF40-\\\uDF43]|\\\uD81A[\\\uDF63-\\\uDF77]|\\\uD81A[\\\uDF7D-\\\uDF8F]|\\\uD81B[\\\uDF00-\\\uDF44]|\\\uD81B\\\uDF50|
        \\\uD81B[\\\uDF93-\\\uDF9F]|\\\uD81B\\\uDFE0|[\\\uD81C-\\\uD820][\\\uDC00-\\\uDFFF]|\\\uD821[\\\uDC00-\\\uDFEC]|\\\uD822[\\\uDC00-\\\uDEF2]|
        \\\uD82C[\\\uDC00-\\\uDC01]|\\\uD82F[\\\uDC00-\\\uDC6A]|\\\uD82F[\\\uDC70-\\\uDC7C]|\\\uD82F[\\\uDC80-\\\uDC88]|\\\uD82F[\\\uDC90-\\\uDC99]|
        \\\uD835[\\\uDC00-\\\uDC54]|\\\uD835[\\\uDC56-\\\uDC9C]|\\\uD835[\\\uDC9E-\\\uDC9F]|\\\uD835\\\uDCA2|\\\uD835[\\\uDCA5-\\\uDCA6]|
        \\\uD835[\\\uDCA9-\\\uDCAC]|\\\uD835[\\\uDCAE-\\\uDCB9]|\\\uD835\\\uDCBB|\\\uD835[\\\uDCBD-\\\uDCC3]|\\\uD835[\\\uDCC5-\\\uDD05]|
        \\\uD835[\\\uDD07-\\\uDD0A]|\\\uD835[\\\uDD0D-\\\uDD14]|\\\uD835[\\\uDD16-\\\uDD1C]|\\\uD835[\\\uDD1E-\\\uDD39]|\\\uD835[\\\uDD3B-\\\uDD3E]|
        \\\uD835[\\\uDD40-\\\uDD44]|\\\uD835\\\uDD46|\\\uD835[\\\uDD4A-\\\uDD50]|\\\uD835[\\\uDD52-\\\uDEA5]|\\\uD835[\\\uDEA8-\\\uDEC0]|
        \\\uD835[\\\uDEC2-\\\uDEDA]|\\\uD835[\\\uDEDC-\\\uDEFA]|\\\uD835[\\\uDEFC-\\\uDF14]|\\\uD835[\\\uDF16-\\\uDF34]|\\\uD835[\\\uDF36-\\\uDF4E]|
        \\\uD835[\\\uDF50-\\\uDF6E]|\\\uD835[\\\uDF70-\\\uDF88]|\\\uD835[\\\uDF8A-\\\uDFA8]|\\\uD835[\\\uDFAA-\\\uDFC2]|\\\uD835[\\\uDFC4-\\\uDFCB]|
        \\\uD83A[\\\uDC00-\\\uDCC4]|\\\uD83A[\\\uDD00-\\\uDD43]|\\\uD83B[\\\uDE00-\\\uDE03]|\\\uD83B[\\\uDE05-\\\uDE1F]|\\\uD83B[\\\uDE21-\\\uDE22]|
        \\\uD83B\\\uDE24|\\\uD83B\\\uDE27|\\\uD83B[\\\uDE29-\\\uDE32]|\\\uD83B[\\\uDE34-\\\uDE37]|\\\uD83B\\\uDE39|\\\uD83B\\\uDE3B|\\\uD83B\\\uDE42|
        \\\uD83B\\\uDE47|\\\uD83B\\\uDE49|\\\uD83B\\\uDE4B|\\\uD83B[\\\uDE4D-\\\uDE4F]|\\\uD83B[\\\uDE51-\\\uDE52]|\\\uD83B\\\uDE54|\\\uD83B\\\uDE57|
        \\\uD83B\\\uDE59|\\\uD83B\\\uDE5B|\\\uD83B\\\uDE5D|\\\uD83B\\\uDE5F|\\\uD83B[\\\uDE61-\\\uDE62]|\\\uD83B\\\uDE64|\\\uD83B[\\\uDE67-\\\uDE6A]|
        \\\uD83B[\\\uDE6C-\\\uDE72]|\\\uD83B[\\\uDE74-\\\uDE77]|\\\uD83B[\\\uDE79-\\\uDE7C]|\\\uD83B\\\uDE7E|\\\uD83B[\\\uDE80-\\\uDE89]|
        \\\uD83B[\\\uDE8B-\\\uDE9B]|\\\uD83B[\\\uDEA1-\\\uDEA3]|\\\uD83B[\\\uDEA5-\\\uDEA9]|\\\uD83B[\\\uDEAB-\\\uDEBB]|
        [\\\uD840-\\\uD868][\\\uDC00-\\\uDFFF]|\\\uD869[\\\uDC00-\\\uDED6]|\\\uD869[\\\uDF00-\\\uDFFF]|[\\\uD86A-\\\uD86C][\\\uDC00-\\\uDFFF]|
        \\\uD86D[\\\uDC00-\\\uDF34]|\\\uD86D[\\\uDF40-\\\uDFFF]|\\\uD86E[\\\uDC00-\\\uDC1D]|\\\uD86E[\\\uDC20-\\\uDFFF]|
        [\\\uD86F-\\\uD872][\\\uDC00-\\\uDFFF]|\\\uD873[\\\uDC00-\\\uDEA1]|\\\uD87E[\\\uDC00-\\\uDE1D]
        '''.replace('\x20', '').replace('\n', '')
else:
    XID_START_LESS_FILLERS = '''
        [A-Za-z\\\u00AA\\\u00B5\\\u00BA\\\u00C0-\\\u00D6\\\u00D8-\\\u00F6\\\u00F8-\\\u02C1\\\u02C6-\\\u02D1\\\u02E0-\\\u02E4\\\u02EC\\\u02EE\\\u0370-\\\u0374
         \\\u0376-\\\u0377\\\u037B-\\\u037D\\\u037F\\\u0386\\\u0388-\\\u038A\\\u038C\\\u038E-\\\u03A1\\\u03A3-\\\u03F5\\\u03F7-\\\u0481\\\u048A-\\\u052F
         \\\u0531-\\\u0556\\\u0559\\\u0561-\\\u0587\\\u05D0-\\\u05EA\\\u05F0-\\\u05F2\\\u0620-\\\u064A\\\u066E-\\\u066F\\\u0671-\\\u06D3\\\u06D5
         \\\u06E5-\\\u06E6\\\u06EE-\\\u06EF\\\u06FA-\\\u06FC\\\u06FF\\\u0710\\\u0712-\\\u072F\\\u074D-\\\u07A5\\\u07B1\\\u07CA-\\\u07EA\\\u07F4-\\\u07F5
         \\\u07FA\\\u0800-\\\u0815\\\u081A\\\u0824\\\u0828\\\u0840-\\\u0858\\\u08A0-\\\u08B4\\\u08B6-\\\u08BD\\\u0904-\\\u0939\\\u093D\\\u0950
         \\\u0958-\\\u0961\\\u0971-\\\u0980\\\u0985-\\\u098C\\\u098F-\\\u0990\\\u0993-\\\u09A8\\\u09AA-\\\u09B0\\\u09B2\\\u09B6-\\\u09B9\\\u09BD\\\u09CE
         \\\u09DC-\\\u09DD\\\u09DF-\\\u09E1\\\u09F0-\\\u09F1\\\u0A05-\\\u0A0A\\\u0A0F-\\\u0A10\\\u0A13-\\\u0A28\\\u0A2A-\\\u0A30\\\u0A32-\\\u0A33
         \\\u0A35-\\\u0A36\\\u0A38-\\\u0A39\\\u0A59-\\\u0A5C\\\u0A5E\\\u0A72-\\\u0A74\\\u0A85-\\\u0A8D\\\u0A8F-\\\u0A91\\\u0A93-\\\u0AA8\\\u0AAA-\\\u0AB0
         \\\u0AB2-\\\u0AB3\\\u0AB5-\\\u0AB9\\\u0ABD\\\u0AD0\\\u0AE0-\\\u0AE1\\\u0AF9\\\u0B05-\\\u0B0C\\\u0B0F-\\\u0B10\\\u0B13-\\\u0B28\\\u0B2A-\\\u0B30
         \\\u0B32-\\\u0B33\\\u0B35-\\\u0B39\\\u0B3D\\\u0B5C-\\\u0B5D\\\u0B5F-\\\u0B61\\\u0B71\\\u0B83\\\u0B85-\\\u0B8A\\\u0B8E-\\\u0B90\\\u0B92-\\\u0B95
         \\\u0B99-\\\u0B9A\\\u0B9C\\\u0B9E-\\\u0B9F\\\u0BA3-\\\u0BA4\\\u0BA8-\\\u0BAA\\\u0BAE-\\\u0BB9\\\u0BD0\\\u0C05-\\\u0C0C\\\u0C0E-\\\u0C10
         \\\u0C12-\\\u0C28\\\u0C2A-\\\u0C39\\\u0C3D\\\u0C58-\\\u0C5A\\\u0C60-\\\u0C61\\\u0C80\\\u0C85-\\\u0C8C\\\u0C8E-\\\u0C90\\\u0C92-\\\u0CA8
         \\\u0CAA-\\\u0CB3\\\u0CB5-\\\u0CB9\\\u0CBD\\\u0CDE\\\u0CE0-\\\u0CE1\\\u0CF1-\\\u0CF2\\\u0D05-\\\u0D0C\\\u0D0E-\\\u0D10\\\u0D12-\\\u0D3A\\\u0D3D
         \\\u0D4E\\\u0D54-\\\u0D56\\\u0D5F-\\\u0D61\\\u0D7A-\\\u0D7F\\\u0D85-\\\u0D96\\\u0D9A-\\\u0DB1\\\u0DB3-\\\u0DBB\\\u0DBD\\\u0DC0-\\\u0DC6
         \\\u0E01-\\\u0E30\\\u0E32\\\u0E40-\\\u0E46\\\u0E81-\\\u0E82\\\u0E84\\\u0E87-\\\u0E88\\\u0E8A\\\u0E8D\\\u0E94-\\\u0E97\\\u0E99-\\\u0E9F
         \\\u0EA1-\\\u0EA3\\\u0EA5\\\u0EA7\\\u0EAA-\\\u0EAB\\\u0EAD-\\\u0EB0\\\u0EB2\\\u0EBD\\\u0EC0-\\\u0EC4\\\u0EC6\\\u0EDC-\\\u0EDF\\\u0F00
         \\\u0F40-\\\u0F47\\\u0F49-\\\u0F6C\\\u0F88-\\\u0F8C\\\u1000-\\\u102A\\\u103F\\\u1050-\\\u1055\\\u105A-\\\u105D\\\u1061\\\u1065-\\\u1066
         \\\u106E-\\\u1070\\\u1075-\\\u1081\\\u108E\\\u10A0-\\\u10C5\\\u10C7\\\u10CD\\\u10D0-\\\u10FA\\\u10FC-\\\u115E\\\u1161-\\\u1248\\\u124A-\\\u124D
         \\\u1250-\\\u1256\\\u1258\\\u125A-\\\u125D\\\u1260-\\\u1288\\\u128A-\\\u128D\\\u1290-\\\u12B0\\\u12B2-\\\u12B5\\\u12B8-\\\u12BE\\\u12C0
         \\\u12C2-\\\u12C5\\\u12C8-\\\u12D6\\\u12D8-\\\u1310\\\u1312-\\\u1315\\\u1318-\\\u135A\\\u1380-\\\u138F\\\u13A0-\\\u13F5\\\u13F8-\\\u13FD
         \\\u1401-\\\u166C\\\u166F-\\\u167F\\\u1681-\\\u169A\\\u16A0-\\\u16EA\\\u16EE-\\\u16F8\\\u1700-\\\u170C\\\u170E-\\\u1711\\\u1720-\\\u1731
         \\\u1740-\\\u1751\\\u1760-\\\u176C\\\u176E-\\\u1770\\\u1780-\\\u17B3\\\u17D7\\\u17DC\\\u1820-\\\u1877\\\u1880-\\\u18A8\\\u18AA\\\u18B0-\\\u18F5
         \\\u1900-\\\u191E\\\u1950-\\\u196D\\\u1970-\\\u1974\\\u1980-\\\u19AB\\\u19B0-\\\u19C9\\\u1A00-\\\u1A16\\\u1A20-\\\u1A54\\\u1AA7\\\u1B05-\\\u1B33
         \\\u1B45-\\\u1B4B\\\u1B83-\\\u1BA0\\\u1BAE-\\\u1BAF\\\u1BBA-\\\u1BE5\\\u1C00-\\\u1C23\\\u1C4D-\\\u1C4F\\\u1C5A-\\\u1C7D\\\u1C80-\\\u1C88
         \\\u1CE9-\\\u1CEC\\\u1CEE-\\\u1CF1\\\u1CF5-\\\u1CF6\\\u1D00-\\\u1DBF\\\u1E00-\\\u1F15\\\u1F18-\\\u1F1D\\\u1F20-\\\u1F45\\\u1F48-\\\u1F4D
         \\\u1F50-\\\u1F57\\\u1F59\\\u1F5B\\\u1F5D\\\u1F5F-\\\u1F7D\\\u1F80-\\\u1FB4\\\u1FB6-\\\u1FBC\\\u1FBE\\\u1FC2-\\\u1FC4\\\u1FC6-\\\u1FCC
         \\\u1FD0-\\\u1FD3\\\u1FD6-\\\u1FDB\\\u1FE0-\\\u1FEC\\\u1FF2-\\\u1FF4\\\u1FF6-\\\u1FFC\\\u2071\\\u207F\\\u2090-\\\u209C\\\u2102\\\u2107
         \\\u210A-\\\u2113\\\u2115\\\u2118-\\\u211D\\\u2124\\\u2126\\\u2128\\\u212A-\\\u2139\\\u213C-\\\u213F\\\u2145-\\\u2149\\\u214E\\\u2160-\\\u2188
         \\\u2C00-\\\u2C2E\\\u2C30-\\\u2C5E\\\u2C60-\\\u2CE4\\\u2CEB-\\\u2CEE\\\u2CF2-\\\u2CF3\\\u2D00-\\\u2D25\\\u2D27\\\u2D2D\\\u2D30-\\\u2D67\\\u2D6F
         \\\u2D80-\\\u2D96\\\u2DA0-\\\u2DA6\\\u2DA8-\\\u2DAE\\\u2DB0-\\\u2DB6\\\u2DB8-\\\u2DBE\\\u2DC0-\\\u2DC6\\\u2DC8-\\\u2DCE\\\u2DD0-\\\u2DD6
         \\\u2DD8-\\\u2DDE\\\u3005-\\\u3007\\\u3021-\\\u3029\\\u3031-\\\u3035\\\u3038-\\\u303C\\\u3041-\\\u3096\\\u309D-\\\u309F\\\u30A1-\\\u30FA
         \\\u30FC-\\\u30FF\\\u3105-\\\u312D\\\u3131-\\\u3163\\\u3165-\\\u318E\\\u31A0-\\\u31BA\\\u31F0-\\\u31FF\\\u3400-\\\u4DB5\\\u4E00-\\\u9FD5
         \\\uA000-\\\uA48C\\\uA4D0-\\\uA4FD\\\uA500-\\\uA60C\\\uA610-\\\uA61F\\\uA62A-\\\uA62B\\\uA640-\\\uA66E\\\uA67F-\\\uA69D\\\uA6A0-\\\uA6EF
         \\\uA717-\\\uA71F\\\uA722-\\\uA788\\\uA78B-\\\uA7AE\\\uA7B0-\\\uA7B7\\\uA7F7-\\\uA801\\\uA803-\\\uA805\\\uA807-\\\uA80A\\\uA80C-\\\uA822
         \\\uA840-\\\uA873\\\uA882-\\\uA8B3\\\uA8F2-\\\uA8F7\\\uA8FB\\\uA8FD\\\uA90A-\\\uA925\\\uA930-\\\uA946\\\uA960-\\\uA97C\\\uA984-\\\uA9B2\\\uA9CF
         \\\uA9E0-\\\uA9E4\\\uA9E6-\\\uA9EF\\\uA9FA-\\\uA9FE\\\uAA00-\\\uAA28\\\uAA40-\\\uAA42\\\uAA44-\\\uAA4B\\\uAA60-\\\uAA76\\\uAA7A\\\uAA7E-\\\uAAAF
         \\\uAAB1\\\uAAB5-\\\uAAB6\\\uAAB9-\\\uAABD\\\uAAC0\\\uAAC2\\\uAADB-\\\uAADD\\\uAAE0-\\\uAAEA\\\uAAF2-\\\uAAF4\\\uAB01-\\\uAB06\\\uAB09-\\\uAB0E
         \\\uAB11-\\\uAB16\\\uAB20-\\\uAB26\\\uAB28-\\\uAB2E\\\uAB30-\\\uAB5A\\\uAB5C-\\\uAB65\\\uAB70-\\\uABE2\\\uAC00-\\\uD7A3\\\uD7B0-\\\uD7C6
         \\\uD7CB-\\\uD7FB\\\uF900-\\\uFA6D\\\uFA70-\\\uFAD9\\\uFB00-\\\uFB06\\\uFB13-\\\uFB17\\\uFB1D\\\uFB1F-\\\uFB28\\\uFB2A-\\\uFB36\\\uFB38-\\\uFB3C
         \\\uFB3E\\\uFB40-\\\uFB41\\\uFB43-\\\uFB44\\\uFB46-\\\uFBB1\\\uFBD3-\\\uFC5D\\\uFC64-\\\uFD3D\\\uFD50-\\\uFD8F\\\uFD92-\\\uFDC7\\\uFDF0-\\\uFDF9
         \\\uFE71\\\uFE73\\\uFE77\\\uFE79\\\uFE7B\\\uFE7D\\\uFE7F-\\\uFEFC\\\uFF21-\\\uFF3A\\\uFF41-\\\uFF5A\\\uFF66-\\\uFF9D\\\uFFA1-\\\uFFBE
         \\\uFFC2-\\\uFFC7\\\uFFCA-\\\uFFCF\\\uFFD2-\\\uFFD7\\\uFFDA-\\\uFFDC\\\U00010000-\\\U0001000B\\\U0001000D-\\\U00010026\\\U00010028-\\\U0001003A
         \\\U0001003C-\\\U0001003D\\\U0001003F-\\\U0001004D\\\U00010050-\\\U0001005D\\\U00010080-\\\U000100FA\\\U00010140-\\\U00010174
         \\\U00010280-\\\U0001029C\\\U000102A0-\\\U000102D0\\\U00010300-\\\U0001031F\\\U00010330-\\\U0001034A\\\U00010350-\\\U00010375
         \\\U00010380-\\\U0001039D\\\U000103A0-\\\U000103C3\\\U000103C8-\\\U000103CF\\\U000103D1-\\\U000103D5\\\U00010400-\\\U0001049D
         \\\U000104B0-\\\U000104D3\\\U000104D8-\\\U000104FB\\\U00010500-\\\U00010527\\\U00010530-\\\U00010563\\\U00010600-\\\U00010736
         \\\U00010740-\\\U00010755\\\U00010760-\\\U00010767\\\U00010800-\\\U00010805\\\U00010808\\\U0001080A-\\\U00010835\\\U00010837-\\\U00010838
         \\\U0001083C\\\U0001083F-\\\U00010855\\\U00010860-\\\U00010876\\\U00010880-\\\U0001089E\\\U000108E0-\\\U000108F2\\\U000108F4-\\\U000108F5
         \\\U00010900-\\\U00010915\\\U00010920-\\\U00010939\\\U00010980-\\\U000109B7\\\U000109BE-\\\U000109BF\\\U00010A00\\\U00010A10-\\\U00010A13
         \\\U00010A15-\\\U00010A17\\\U00010A19-\\\U00010A33\\\U00010A60-\\\U00010A7C\\\U00010A80-\\\U00010A9C\\\U00010AC0-\\\U00010AC7
         \\\U00010AC9-\\\U00010AE4\\\U00010B00-\\\U00010B35\\\U00010B40-\\\U00010B55\\\U00010B60-\\\U00010B72\\\U00010B80-\\\U00010B91
         \\\U00010C00-\\\U00010C48\\\U00010C80-\\\U00010CB2\\\U00010CC0-\\\U00010CF2\\\U00011003-\\\U00011037\\\U00011083-\\\U000110AF
         \\\U000110D0-\\\U000110E8\\\U00011103-\\\U00011126\\\U00011150-\\\U00011172\\\U00011176\\\U00011183-\\\U000111B2\\\U000111C1-\\\U000111C4
         \\\U000111DA\\\U000111DC\\\U00011200-\\\U00011211\\\U00011213-\\\U0001122B\\\U00011280-\\\U00011286\\\U00011288\\\U0001128A-\\\U0001128D
         \\\U0001128F-\\\U0001129D\\\U0001129F-\\\U000112A8\\\U000112B0-\\\U000112DE\\\U00011305-\\\U0001130C\\\U0001130F-\\\U00011310
         \\\U00011313-\\\U00011328\\\U0001132A-\\\U00011330\\\U00011332-\\\U00011333\\\U00011335-\\\U00011339\\\U0001133D\\\U00011350
         \\\U0001135D-\\\U00011361\\\U00011400-\\\U00011434\\\U00011447-\\\U0001144A\\\U00011480-\\\U000114AF\\\U000114C4-\\\U000114C5\\\U000114C7
         \\\U00011580-\\\U000115AE\\\U000115D8-\\\U000115DB\\\U00011600-\\\U0001162F\\\U00011644\\\U00011680-\\\U000116AA\\\U00011700-\\\U00011719
         \\\U000118A0-\\\U000118DF\\\U000118FF\\\U00011AC0-\\\U00011AF8\\\U00011C00-\\\U00011C08\\\U00011C0A-\\\U00011C2E\\\U00011C40
         \\\U00011C72-\\\U00011C8F\\\U00012000-\\\U00012399\\\U00012400-\\\U0001246E\\\U00012480-\\\U00012543\\\U00013000-\\\U0001342E
         \\\U00014400-\\\U00014646\\\U00016800-\\\U00016A38\\\U00016A40-\\\U00016A5E\\\U00016AD0-\\\U00016AED\\\U00016B00-\\\U00016B2F
         \\\U00016B40-\\\U00016B43\\\U00016B63-\\\U00016B77\\\U00016B7D-\\\U00016B8F\\\U00016F00-\\\U00016F44\\\U00016F50\\\U00016F93-\\\U00016F9F
         \\\U00016FE0\\\U00017000-\\\U000187EC\\\U00018800-\\\U00018AF2\\\U0001B000-\\\U0001B001\\\U0001BC00-\\\U0001BC6A\\\U0001BC70-\\\U0001BC7C
         \\\U0001BC80-\\\U0001BC88\\\U0001BC90-\\\U0001BC99\\\U0001D400-\\\U0001D454\\\U0001D456-\\\U0001D49C\\\U0001D49E-\\\U0001D49F\\\U0001D4A2
         \\\U0001D4A5-\\\U0001D4A6\\\U0001D4A9-\\\U0001D4AC\\\U0001D4AE-\\\U0001D4B9\\\U0001D4BB\\\U0001D4BD-\\\U0001D4C3\\\U0001D4C5-\\\U0001D505
         \\\U0001D507-\\\U0001D50A\\\U0001D50D-\\\U0001D514\\\U0001D516-\\\U0001D51C\\\U0001D51E-\\\U0001D539\\\U0001D53B-\\\U0001D53E
         \\\U0001D540-\\\U0001D544\\\U0001D546\\\U0001D54A-\\\U0001D550\\\U0001D552-\\\U0001D6A5\\\U0001D6A8-\\\U0001D6C0\\\U0001D6C2-\\\U0001D6DA
         \\\U0001D6DC-\\\U0001D6FA\\\U0001D6FC-\\\U0001D714\\\U0001D716-\\\U0001D734\\\U0001D736-\\\U0001D74E\\\U0001D750-\\\U0001D76E
         \\\U0001D770-\\\U0001D788\\\U0001D78A-\\\U0001D7A8\\\U0001D7AA-\\\U0001D7C2\\\U0001D7C4-\\\U0001D7CB\\\U0001E800-\\\U0001E8C4
         \\\U0001E900-\\\U0001E943\\\U0001EE00-\\\U0001EE03\\\U0001EE05-\\\U0001EE1F\\\U0001EE21-\\\U0001EE22\\\U0001EE24\\\U0001EE27
         \\\U0001EE29-\\\U0001EE32\\\U0001EE34-\\\U0001EE37\\\U0001EE39\\\U0001EE3B\\\U0001EE42\\\U0001EE47\\\U0001EE49\\\U0001EE4B\\\U0001EE4D-\\\U0001EE4F
         \\\U0001EE51-\\\U0001EE52\\\U0001EE54\\\U0001EE57\\\U0001EE59\\\U0001EE5B\\\U0001EE5D\\\U0001EE5F\\\U0001EE61-\\\U0001EE62\\\U0001EE64
         \\\U0001EE67-\\\U0001EE6A\\\U0001EE6C-\\\U0001EE72\\\U0001EE74-\\\U0001EE77\\\U0001EE79-\\\U0001EE7C\\\U0001EE7E\\\U0001EE80-\\\U0001EE89
         \\\U0001EE8B-\\\U0001EE9B\\\U0001EEA1-\\\U0001EEA3\\\U0001EEA5-\\\U0001EEA9\\\U0001EEAB-\\\U0001EEBB\\\U00020000-\\\U0002A6D6
         \\\U0002A700-\\\U0002B734\\\U0002B740-\\\U0002B81D\\\U0002B820-\\\U0002CEA1\\\U0002F800-\\\U0002FA1D]
        '''.replace('\x20', '').replace('\n', '')


# ascii_start = set(cp for cp in xid_start_less_fillers if cp < 128)
ASCII_START = '[A-Za-z]'


# xid_continue_less_fillers = set([cp for cp, data in unicodetools.ucd.derivedcoreproperties.items() if 'XID_Continue' in data and cp not in hangul_fillers])
if sys.maxunicode == 0xFFFF:
    XID_CONTINUE_LESS_FILLERS = '''
        [0-9A-Z\\\u005Fa-z\\\u00AA\\\u00B5\\\u00B7\\\u00BA\\\u00C0-\\\u00D6\\\u00D8-\\\u00F6\\\u00F8-\\\u02C1\\\u02C6-\\\u02D1\\\u02E0-\\\u02E4\\\u02EC
         \\\u02EE\\\u0300-\\\u0374\\\u0376-\\\u0377\\\u037B-\\\u037D\\\u037F\\\u0386-\\\u038A\\\u038C\\\u038E-\\\u03A1\\\u03A3-\\\u03F5\\\u03F7-\\\u0481
         \\\u0483-\\\u0487\\\u048A-\\\u052F\\\u0531-\\\u0556\\\u0559\\\u0561-\\\u0587\\\u0591-\\\u05BD\\\u05BF\\\u05C1-\\\u05C2\\\u05C4-\\\u05C5\\\u05C7
         \\\u05D0-\\\u05EA\\\u05F0-\\\u05F2\\\u0610-\\\u061A\\\u0620-\\\u0669\\\u066E-\\\u06D3\\\u06D5-\\\u06DC\\\u06DF-\\\u06E8\\\u06EA-\\\u06FC\\\u06FF
         \\\u0710-\\\u074A\\\u074D-\\\u07B1\\\u07C0-\\\u07F5\\\u07FA\\\u0800-\\\u082D\\\u0840-\\\u085B\\\u08A0-\\\u08B4\\\u08B6-\\\u08BD\\\u08D4-\\\u08E1
         \\\u08E3-\\\u0963\\\u0966-\\\u096F\\\u0971-\\\u0983\\\u0985-\\\u098C\\\u098F-\\\u0990\\\u0993-\\\u09A8\\\u09AA-\\\u09B0\\\u09B2\\\u09B6-\\\u09B9
         \\\u09BC-\\\u09C4\\\u09C7-\\\u09C8\\\u09CB-\\\u09CE\\\u09D7\\\u09DC-\\\u09DD\\\u09DF-\\\u09E3\\\u09E6-\\\u09F1\\\u0A01-\\\u0A03\\\u0A05-\\\u0A0A
         \\\u0A0F-\\\u0A10\\\u0A13-\\\u0A28\\\u0A2A-\\\u0A30\\\u0A32-\\\u0A33\\\u0A35-\\\u0A36\\\u0A38-\\\u0A39\\\u0A3C\\\u0A3E-\\\u0A42\\\u0A47-\\\u0A48
         \\\u0A4B-\\\u0A4D\\\u0A51\\\u0A59-\\\u0A5C\\\u0A5E\\\u0A66-\\\u0A75\\\u0A81-\\\u0A83\\\u0A85-\\\u0A8D\\\u0A8F-\\\u0A91\\\u0A93-\\\u0AA8
         \\\u0AAA-\\\u0AB0\\\u0AB2-\\\u0AB3\\\u0AB5-\\\u0AB9\\\u0ABC-\\\u0AC5\\\u0AC7-\\\u0AC9\\\u0ACB-\\\u0ACD\\\u0AD0\\\u0AE0-\\\u0AE3\\\u0AE6-\\\u0AEF
         \\\u0AF9\\\u0B01-\\\u0B03\\\u0B05-\\\u0B0C\\\u0B0F-\\\u0B10\\\u0B13-\\\u0B28\\\u0B2A-\\\u0B30\\\u0B32-\\\u0B33\\\u0B35-\\\u0B39\\\u0B3C-\\\u0B44
         \\\u0B47-\\\u0B48\\\u0B4B-\\\u0B4D\\\u0B56-\\\u0B57\\\u0B5C-\\\u0B5D\\\u0B5F-\\\u0B63\\\u0B66-\\\u0B6F\\\u0B71\\\u0B82-\\\u0B83\\\u0B85-\\\u0B8A
         \\\u0B8E-\\\u0B90\\\u0B92-\\\u0B95\\\u0B99-\\\u0B9A\\\u0B9C\\\u0B9E-\\\u0B9F\\\u0BA3-\\\u0BA4\\\u0BA8-\\\u0BAA\\\u0BAE-\\\u0BB9\\\u0BBE-\\\u0BC2
         \\\u0BC6-\\\u0BC8\\\u0BCA-\\\u0BCD\\\u0BD0\\\u0BD7\\\u0BE6-\\\u0BEF\\\u0C00-\\\u0C03\\\u0C05-\\\u0C0C\\\u0C0E-\\\u0C10\\\u0C12-\\\u0C28
         \\\u0C2A-\\\u0C39\\\u0C3D-\\\u0C44\\\u0C46-\\\u0C48\\\u0C4A-\\\u0C4D\\\u0C55-\\\u0C56\\\u0C58-\\\u0C5A\\\u0C60-\\\u0C63\\\u0C66-\\\u0C6F
         \\\u0C80-\\\u0C83\\\u0C85-\\\u0C8C\\\u0C8E-\\\u0C90\\\u0C92-\\\u0CA8\\\u0CAA-\\\u0CB3\\\u0CB5-\\\u0CB9\\\u0CBC-\\\u0CC4\\\u0CC6-\\\u0CC8
         \\\u0CCA-\\\u0CCD\\\u0CD5-\\\u0CD6\\\u0CDE\\\u0CE0-\\\u0CE3\\\u0CE6-\\\u0CEF\\\u0CF1-\\\u0CF2\\\u0D01-\\\u0D03\\\u0D05-\\\u0D0C\\\u0D0E-\\\u0D10
         \\\u0D12-\\\u0D3A\\\u0D3D-\\\u0D44\\\u0D46-\\\u0D48\\\u0D4A-\\\u0D4E\\\u0D54-\\\u0D57\\\u0D5F-\\\u0D63\\\u0D66-\\\u0D6F\\\u0D7A-\\\u0D7F
         \\\u0D82-\\\u0D83\\\u0D85-\\\u0D96\\\u0D9A-\\\u0DB1\\\u0DB3-\\\u0DBB\\\u0DBD\\\u0DC0-\\\u0DC6\\\u0DCA\\\u0DCF-\\\u0DD4\\\u0DD6\\\u0DD8-\\\u0DDF
         \\\u0DE6-\\\u0DEF\\\u0DF2-\\\u0DF3\\\u0E01-\\\u0E3A\\\u0E40-\\\u0E4E\\\u0E50-\\\u0E59\\\u0E81-\\\u0E82\\\u0E84\\\u0E87-\\\u0E88\\\u0E8A\\\u0E8D
         \\\u0E94-\\\u0E97\\\u0E99-\\\u0E9F\\\u0EA1-\\\u0EA3\\\u0EA5\\\u0EA7\\\u0EAA-\\\u0EAB\\\u0EAD-\\\u0EB9\\\u0EBB-\\\u0EBD\\\u0EC0-\\\u0EC4\\\u0EC6
         \\\u0EC8-\\\u0ECD\\\u0ED0-\\\u0ED9\\\u0EDC-\\\u0EDF\\\u0F00\\\u0F18-\\\u0F19\\\u0F20-\\\u0F29\\\u0F35\\\u0F37\\\u0F39\\\u0F3E-\\\u0F47
         \\\u0F49-\\\u0F6C\\\u0F71-\\\u0F84\\\u0F86-\\\u0F97\\\u0F99-\\\u0FBC\\\u0FC6\\\u1000-\\\u1049\\\u1050-\\\u109D\\\u10A0-\\\u10C5\\\u10C7\\\u10CD
         \\\u10D0-\\\u10FA\\\u10FC-\\\u115E\\\u1161-\\\u1248\\\u124A-\\\u124D\\\u1250-\\\u1256\\\u1258\\\u125A-\\\u125D\\\u1260-\\\u1288\\\u128A-\\\u128D
         \\\u1290-\\\u12B0\\\u12B2-\\\u12B5\\\u12B8-\\\u12BE\\\u12C0\\\u12C2-\\\u12C5\\\u12C8-\\\u12D6\\\u12D8-\\\u1310\\\u1312-\\\u1315\\\u1318-\\\u135A
         \\\u135D-\\\u135F\\\u1369-\\\u1371\\\u1380-\\\u138F\\\u13A0-\\\u13F5\\\u13F8-\\\u13FD\\\u1401-\\\u166C\\\u166F-\\\u167F\\\u1681-\\\u169A
         \\\u16A0-\\\u16EA\\\u16EE-\\\u16F8\\\u1700-\\\u170C\\\u170E-\\\u1714\\\u1720-\\\u1734\\\u1740-\\\u1753\\\u1760-\\\u176C\\\u176E-\\\u1770
         \\\u1772-\\\u1773\\\u1780-\\\u17D3\\\u17D7\\\u17DC-\\\u17DD\\\u17E0-\\\u17E9\\\u180B-\\\u180D\\\u1810-\\\u1819\\\u1820-\\\u1877\\\u1880-\\\u18AA
         \\\u18B0-\\\u18F5\\\u1900-\\\u191E\\\u1920-\\\u192B\\\u1930-\\\u193B\\\u1946-\\\u196D\\\u1970-\\\u1974\\\u1980-\\\u19AB\\\u19B0-\\\u19C9
         \\\u19D0-\\\u19DA\\\u1A00-\\\u1A1B\\\u1A20-\\\u1A5E\\\u1A60-\\\u1A7C\\\u1A7F-\\\u1A89\\\u1A90-\\\u1A99\\\u1AA7\\\u1AB0-\\\u1ABD\\\u1B00-\\\u1B4B
         \\\u1B50-\\\u1B59\\\u1B6B-\\\u1B73\\\u1B80-\\\u1BF3\\\u1C00-\\\u1C37\\\u1C40-\\\u1C49\\\u1C4D-\\\u1C7D\\\u1C80-\\\u1C88\\\u1CD0-\\\u1CD2
         \\\u1CD4-\\\u1CF6\\\u1CF8-\\\u1CF9\\\u1D00-\\\u1DF5\\\u1DFB-\\\u1F15\\\u1F18-\\\u1F1D\\\u1F20-\\\u1F45\\\u1F48-\\\u1F4D\\\u1F50-\\\u1F57\\\u1F59
         \\\u1F5B\\\u1F5D\\\u1F5F-\\\u1F7D\\\u1F80-\\\u1FB4\\\u1FB6-\\\u1FBC\\\u1FBE\\\u1FC2-\\\u1FC4\\\u1FC6-\\\u1FCC\\\u1FD0-\\\u1FD3\\\u1FD6-\\\u1FDB
         \\\u1FE0-\\\u1FEC\\\u1FF2-\\\u1FF4\\\u1FF6-\\\u1FFC\\\u203F-\\\u2040\\\u2054\\\u2071\\\u207F\\\u2090-\\\u209C\\\u20D0-\\\u20DC\\\u20E1
         \\\u20E5-\\\u20F0\\\u2102\\\u2107\\\u210A-\\\u2113\\\u2115\\\u2118-\\\u211D\\\u2124\\\u2126\\\u2128\\\u212A-\\\u2139\\\u213C-\\\u213F
         \\\u2145-\\\u2149\\\u214E\\\u2160-\\\u2188\\\u2C00-\\\u2C2E\\\u2C30-\\\u2C5E\\\u2C60-\\\u2CE4\\\u2CEB-\\\u2CF3\\\u2D00-\\\u2D25\\\u2D27\\\u2D2D
         \\\u2D30-\\\u2D67\\\u2D6F\\\u2D7F-\\\u2D96\\\u2DA0-\\\u2DA6\\\u2DA8-\\\u2DAE\\\u2DB0-\\\u2DB6\\\u2DB8-\\\u2DBE\\\u2DC0-\\\u2DC6\\\u2DC8-\\\u2DCE
         \\\u2DD0-\\\u2DD6\\\u2DD8-\\\u2DDE\\\u2DE0-\\\u2DFF\\\u3005-\\\u3007\\\u3021-\\\u302F\\\u3031-\\\u3035\\\u3038-\\\u303C\\\u3041-\\\u3096
         \\\u3099-\\\u309A\\\u309D-\\\u309F\\\u30A1-\\\u30FA\\\u30FC-\\\u30FF\\\u3105-\\\u312D\\\u3131-\\\u3163\\\u3165-\\\u318E\\\u31A0-\\\u31BA
         \\\u31F0-\\\u31FF\\\u3400-\\\u4DB5\\\u4E00-\\\u9FD5\\\uA000-\\\uA48C\\\uA4D0-\\\uA4FD\\\uA500-\\\uA60C\\\uA610-\\\uA62B\\\uA640-\\\uA66F
         \\\uA674-\\\uA67D\\\uA67F-\\\uA6F1\\\uA717-\\\uA71F\\\uA722-\\\uA788\\\uA78B-\\\uA7AE\\\uA7B0-\\\uA7B7\\\uA7F7-\\\uA827\\\uA840-\\\uA873
         \\\uA880-\\\uA8C5\\\uA8D0-\\\uA8D9\\\uA8E0-\\\uA8F7\\\uA8FB\\\uA8FD\\\uA900-\\\uA92D\\\uA930-\\\uA953\\\uA960-\\\uA97C\\\uA980-\\\uA9C0
         \\\uA9CF-\\\uA9D9\\\uA9E0-\\\uA9FE\\\uAA00-\\\uAA36\\\uAA40-\\\uAA4D\\\uAA50-\\\uAA59\\\uAA60-\\\uAA76\\\uAA7A-\\\uAAC2\\\uAADB-\\\uAADD
         \\\uAAE0-\\\uAAEF\\\uAAF2-\\\uAAF6\\\uAB01-\\\uAB06\\\uAB09-\\\uAB0E\\\uAB11-\\\uAB16\\\uAB20-\\\uAB26\\\uAB28-\\\uAB2E\\\uAB30-\\\uAB5A
         \\\uAB5C-\\\uAB65\\\uAB70-\\\uABEA\\\uABEC-\\\uABED\\\uABF0-\\\uABF9\\\uAC00-\\\uD7A3\\\uD7B0-\\\uD7C6\\\uD7CB-\\\uD7FB\\\uF900-\\\uFA6D
         \\\uFA70-\\\uFAD9\\\uFB00-\\\uFB06\\\uFB13-\\\uFB17\\\uFB1D-\\\uFB28\\\uFB2A-\\\uFB36\\\uFB38-\\\uFB3C\\\uFB3E\\\uFB40-\\\uFB41\\\uFB43-\\\uFB44
         \\\uFB46-\\\uFBB1\\\uFBD3-\\\uFC5D\\\uFC64-\\\uFD3D\\\uFD50-\\\uFD8F\\\uFD92-\\\uFDC7\\\uFDF0-\\\uFDF9\\\uFE00-\\\uFE0F\\\uFE20-\\\uFE2F
         \\\uFE33-\\\uFE34\\\uFE4D-\\\uFE4F\\\uFE71\\\uFE73\\\uFE77\\\uFE79\\\uFE7B\\\uFE7D\\\uFE7F-\\\uFEFC\\\uFF10-\\\uFF19\\\uFF21-\\\uFF3A\\\uFF3F
         \\\uFF41-\\\uFF5A\\\uFF66-\\\uFF9F\\\uFFA1-\\\uFFBE\\\uFFC2-\\\uFFC7\\\uFFCA-\\\uFFCF\\\uFFD2-\\\uFFD7\\\uFFDA-\\\uFFDC]
        |
        \\\uD800[\\\uDC00-\\\uDC0B]|\\\uD800[\\\uDC0D-\\\uDC26]|\\\uD800[\\\uDC28-\\\uDC3A]|\\\uD800[\\\uDC3C-\\\uDC3D]|\\\uD800[\\\uDC3F-\\\uDC4D]|
        \\\uD800[\\\uDC50-\\\uDC5D]|\\\uD800[\\\uDC80-\\\uDCFA]|\\\uD800[\\\uDD40-\\\uDD74]|\\\uD800\\\uDDFD|\\\uD800[\\\uDE80-\\\uDE9C]|
        \\\uD800[\\\uDEA0-\\\uDED0]|\\\uD800\\\uDEE0|\\\uD800[\\\uDF00-\\\uDF1F]|\\\uD800[\\\uDF30-\\\uDF4A]|\\\uD800[\\\uDF50-\\\uDF7A]|
        \\\uD800[\\\uDF80-\\\uDF9D]|\\\uD800[\\\uDFA0-\\\uDFC3]|\\\uD800[\\\uDFC8-\\\uDFCF]|\\\uD800[\\\uDFD1-\\\uDFD5]|\\\uD801[\\\uDC00-\\\uDC9D]|
        \\\uD801[\\\uDCA0-\\\uDCA9]|\\\uD801[\\\uDCB0-\\\uDCD3]|\\\uD801[\\\uDCD8-\\\uDCFB]|\\\uD801[\\\uDD00-\\\uDD27]|\\\uD801[\\\uDD30-\\\uDD63]|
        \\\uD801[\\\uDE00-\\\uDF36]|\\\uD801[\\\uDF40-\\\uDF55]|\\\uD801[\\\uDF60-\\\uDF67]|\\\uD802[\\\uDC00-\\\uDC05]|\\\uD802\\\uDC08|
        \\\uD802[\\\uDC0A-\\\uDC35]|\\\uD802[\\\uDC37-\\\uDC38]|\\\uD802\\\uDC3C|\\\uD802[\\\uDC3F-\\\uDC55]|\\\uD802[\\\uDC60-\\\uDC76]|
        \\\uD802[\\\uDC80-\\\uDC9E]|\\\uD802[\\\uDCE0-\\\uDCF2]|\\\uD802[\\\uDCF4-\\\uDCF5]|\\\uD802[\\\uDD00-\\\uDD15]|\\\uD802[\\\uDD20-\\\uDD39]|
        \\\uD802[\\\uDD80-\\\uDDB7]|\\\uD802[\\\uDDBE-\\\uDDBF]|\\\uD802[\\\uDE00-\\\uDE03]|\\\uD802[\\\uDE05-\\\uDE06]|\\\uD802[\\\uDE0C-\\\uDE13]|
        \\\uD802[\\\uDE15-\\\uDE17]|\\\uD802[\\\uDE19-\\\uDE33]|\\\uD802[\\\uDE38-\\\uDE3A]|\\\uD802\\\uDE3F|\\\uD802[\\\uDE60-\\\uDE7C]|
        \\\uD802[\\\uDE80-\\\uDE9C]|\\\uD802[\\\uDEC0-\\\uDEC7]|\\\uD802[\\\uDEC9-\\\uDEE6]|\\\uD802[\\\uDF00-\\\uDF35]|\\\uD802[\\\uDF40-\\\uDF55]|
        \\\uD802[\\\uDF60-\\\uDF72]|\\\uD802[\\\uDF80-\\\uDF91]|\\\uD803[\\\uDC00-\\\uDC48]|\\\uD803[\\\uDC80-\\\uDCB2]|\\\uD803[\\\uDCC0-\\\uDCF2]|
        \\\uD804[\\\uDC00-\\\uDC46]|\\\uD804[\\\uDC66-\\\uDC6F]|\\\uD804[\\\uDC7F-\\\uDCBA]|\\\uD804[\\\uDCD0-\\\uDCE8]|\\\uD804[\\\uDCF0-\\\uDCF9]|
        \\\uD804[\\\uDD00-\\\uDD34]|\\\uD804[\\\uDD36-\\\uDD3F]|\\\uD804[\\\uDD50-\\\uDD73]|\\\uD804\\\uDD76|\\\uD804[\\\uDD80-\\\uDDC4]|
        \\\uD804[\\\uDDCA-\\\uDDCC]|\\\uD804[\\\uDDD0-\\\uDDDA]|\\\uD804\\\uDDDC|\\\uD804[\\\uDE00-\\\uDE11]|\\\uD804[\\\uDE13-\\\uDE37]|\\\uD804\\\uDE3E|
        \\\uD804[\\\uDE80-\\\uDE86]|\\\uD804\\\uDE88|\\\uD804[\\\uDE8A-\\\uDE8D]|\\\uD804[\\\uDE8F-\\\uDE9D]|\\\uD804[\\\uDE9F-\\\uDEA8]|
        \\\uD804[\\\uDEB0-\\\uDEEA]|\\\uD804[\\\uDEF0-\\\uDEF9]|\\\uD804[\\\uDF00-\\\uDF03]|\\\uD804[\\\uDF05-\\\uDF0C]|\\\uD804[\\\uDF0F-\\\uDF10]|
        \\\uD804[\\\uDF13-\\\uDF28]|\\\uD804[\\\uDF2A-\\\uDF30]|\\\uD804[\\\uDF32-\\\uDF33]|\\\uD804[\\\uDF35-\\\uDF39]|\\\uD804[\\\uDF3C-\\\uDF44]|
        \\\uD804[\\\uDF47-\\\uDF48]|\\\uD804[\\\uDF4B-\\\uDF4D]|\\\uD804\\\uDF50|\\\uD804\\\uDF57|\\\uD804[\\\uDF5D-\\\uDF63]|\\\uD804[\\\uDF66-\\\uDF6C]|
        \\\uD804[\\\uDF70-\\\uDF74]|\\\uD805[\\\uDC00-\\\uDC4A]|\\\uD805[\\\uDC50-\\\uDC59]|\\\uD805[\\\uDC80-\\\uDCC5]|\\\uD805\\\uDCC7|
        \\\uD805[\\\uDCD0-\\\uDCD9]|\\\uD805[\\\uDD80-\\\uDDB5]|\\\uD805[\\\uDDB8-\\\uDDC0]|\\\uD805[\\\uDDD8-\\\uDDDD]|\\\uD805[\\\uDE00-\\\uDE40]|
        \\\uD805\\\uDE44|\\\uD805[\\\uDE50-\\\uDE59]|\\\uD805[\\\uDE80-\\\uDEB7]|\\\uD805[\\\uDEC0-\\\uDEC9]|\\\uD805[\\\uDF00-\\\uDF19]|
        \\\uD805[\\\uDF1D-\\\uDF2B]|\\\uD805[\\\uDF30-\\\uDF39]|\\\uD806[\\\uDCA0-\\\uDCE9]|\\\uD806\\\uDCFF|\\\uD806[\\\uDEC0-\\\uDEF8]|
        \\\uD807[\\\uDC00-\\\uDC08]|\\\uD807[\\\uDC0A-\\\uDC36]|\\\uD807[\\\uDC38-\\\uDC40]|\\\uD807[\\\uDC50-\\\uDC59]|\\\uD807[\\\uDC72-\\\uDC8F]|
        \\\uD807[\\\uDC92-\\\uDCA7]|\\\uD807[\\\uDCA9-\\\uDCB6]|\\\uD808[\\\uDC00-\\\uDF99]|\\\uD809[\\\uDC00-\\\uDC6E]|\\\uD809[\\\uDC80-\\\uDD43]|
        \\\uD80C[\\\uDC00-\\\uDFFF]|\\\uD80D[\\\uDC00-\\\uDC2E]|\\\uD811[\\\uDC00-\\\uDE46]|\\\uD81A[\\\uDC00-\\\uDE38]|\\\uD81A[\\\uDE40-\\\uDE5E]|
        \\\uD81A[\\\uDE60-\\\uDE69]|\\\uD81A[\\\uDED0-\\\uDEED]|\\\uD81A[\\\uDEF0-\\\uDEF4]|\\\uD81A[\\\uDF00-\\\uDF36]|\\\uD81A[\\\uDF40-\\\uDF43]|
        \\\uD81A[\\\uDF50-\\\uDF59]|\\\uD81A[\\\uDF63-\\\uDF77]|\\\uD81A[\\\uDF7D-\\\uDF8F]|\\\uD81B[\\\uDF00-\\\uDF44]|\\\uD81B[\\\uDF50-\\\uDF7E]|
        \\\uD81B[\\\uDF8F-\\\uDF9F]|\\\uD81B\\\uDFE0|[\\\uD81C-\\\uD820][\\\uDC00-\\\uDFFF]|\\\uD821[\\\uDC00-\\\uDFEC]|\\\uD822[\\\uDC00-\\\uDEF2]|
        \\\uD82C[\\\uDC00-\\\uDC01]|\\\uD82F[\\\uDC00-\\\uDC6A]|\\\uD82F[\\\uDC70-\\\uDC7C]|\\\uD82F[\\\uDC80-\\\uDC88]|\\\uD82F[\\\uDC90-\\\uDC99]|
        \\\uD82F[\\\uDC9D-\\\uDC9E]|\\\uD834[\\\uDD65-\\\uDD69]|\\\uD834[\\\uDD6D-\\\uDD72]|\\\uD834[\\\uDD7B-\\\uDD82]|\\\uD834[\\\uDD85-\\\uDD8B]|
        \\\uD834[\\\uDDAA-\\\uDDAD]|\\\uD834[\\\uDE42-\\\uDE44]|\\\uD835[\\\uDC00-\\\uDC54]|\\\uD835[\\\uDC56-\\\uDC9C]|\\\uD835[\\\uDC9E-\\\uDC9F]|
        \\\uD835\\\uDCA2|\\\uD835[\\\uDCA5-\\\uDCA6]|\\\uD835[\\\uDCA9-\\\uDCAC]|\\\uD835[\\\uDCAE-\\\uDCB9]|\\\uD835\\\uDCBB|\\\uD835[\\\uDCBD-\\\uDCC3]|
        \\\uD835[\\\uDCC5-\\\uDD05]|\\\uD835[\\\uDD07-\\\uDD0A]|\\\uD835[\\\uDD0D-\\\uDD14]|\\\uD835[\\\uDD16-\\\uDD1C]|\\\uD835[\\\uDD1E-\\\uDD39]|
        \\\uD835[\\\uDD3B-\\\uDD3E]|\\\uD835[\\\uDD40-\\\uDD44]|\\\uD835\\\uDD46|\\\uD835[\\\uDD4A-\\\uDD50]|\\\uD835[\\\uDD52-\\\uDEA5]|
        \\\uD835[\\\uDEA8-\\\uDEC0]|\\\uD835[\\\uDEC2-\\\uDEDA]|\\\uD835[\\\uDEDC-\\\uDEFA]|\\\uD835[\\\uDEFC-\\\uDF14]|\\\uD835[\\\uDF16-\\\uDF34]|
        \\\uD835[\\\uDF36-\\\uDF4E]|\\\uD835[\\\uDF50-\\\uDF6E]|\\\uD835[\\\uDF70-\\\uDF88]|\\\uD835[\\\uDF8A-\\\uDFA8]|\\\uD835[\\\uDFAA-\\\uDFC2]|
        \\\uD835[\\\uDFC4-\\\uDFCB]|\\\uD835[\\\uDFCE-\\\uDFFF]|\\\uD836[\\\uDE00-\\\uDE36]|\\\uD836[\\\uDE3B-\\\uDE6C]|\\\uD836\\\uDE75|\\\uD836\\\uDE84|
        \\\uD836[\\\uDE9B-\\\uDE9F]|\\\uD836[\\\uDEA1-\\\uDEAF]|\\\uD838[\\\uDC00-\\\uDC06]|\\\uD838[\\\uDC08-\\\uDC18]|\\\uD838[\\\uDC1B-\\\uDC21]|
        \\\uD838[\\\uDC23-\\\uDC24]|\\\uD838[\\\uDC26-\\\uDC2A]|\\\uD83A[\\\uDC00-\\\uDCC4]|\\\uD83A[\\\uDCD0-\\\uDCD6]|\\\uD83A[\\\uDD00-\\\uDD4A]|
        \\\uD83A[\\\uDD50-\\\uDD59]|\\\uD83B[\\\uDE00-\\\uDE03]|\\\uD83B[\\\uDE05-\\\uDE1F]|\\\uD83B[\\\uDE21-\\\uDE22]|\\\uD83B\\\uDE24|\\\uD83B\\\uDE27|
        \\\uD83B[\\\uDE29-\\\uDE32]|\\\uD83B[\\\uDE34-\\\uDE37]|\\\uD83B\\\uDE39|\\\uD83B\\\uDE3B|\\\uD83B\\\uDE42|\\\uD83B\\\uDE47|\\\uD83B\\\uDE49|
        \\\uD83B\\\uDE4B|\\\uD83B[\\\uDE4D-\\\uDE4F]|\\\uD83B[\\\uDE51-\\\uDE52]|\\\uD83B\\\uDE54|\\\uD83B\\\uDE57|\\\uD83B\\\uDE59|\\\uD83B\\\uDE5B|
        \\\uD83B\\\uDE5D|\\\uD83B\\\uDE5F|\\\uD83B[\\\uDE61-\\\uDE62]|\\\uD83B\\\uDE64|\\\uD83B[\\\uDE67-\\\uDE6A]|\\\uD83B[\\\uDE6C-\\\uDE72]|
        \\\uD83B[\\\uDE74-\\\uDE77]|\\\uD83B[\\\uDE79-\\\uDE7C]|\\\uD83B\\\uDE7E|\\\uD83B[\\\uDE80-\\\uDE89]|\\\uD83B[\\\uDE8B-\\\uDE9B]|
        \\\uD83B[\\\uDEA1-\\\uDEA3]|\\\uD83B[\\\uDEA5-\\\uDEA9]|\\\uD83B[\\\uDEAB-\\\uDEBB]|[\\\uD840-\\\uD868][\\\uDC00-\\\uDFFF]|
        \\\uD869[\\\uDC00-\\\uDED6]|\\\uD869[\\\uDF00-\\\uDFFF]|[\\\uD86A-\\\uD86C][\\\uDC00-\\\uDFFF]|\\\uD86D[\\\uDC00-\\\uDF34]|
        \\\uD86D[\\\uDF40-\\\uDFFF]|\\\uD86E[\\\uDC00-\\\uDC1D]|\\\uD86E[\\\uDC20-\\\uDFFF]|[\\\uD86F-\\\uD872][\\\uDC00-\\\uDFFF]|
        \\\uD873[\\\uDC00-\\\uDEA1]|\\\uD87E[\\\uDC00-\\\uDE1D]|\\\uDB40[\\\uDD00-\\\uDDEF]
        '''.replace('\x20', '').replace('\n', '')
else:
    XID_CONTINUE_LESS_FILLERS = '''
        [0-9A-Z\\\u005Fa-z\\\u00AA\\\u00B5\\\u00B7\\\u00BA\\\u00C0-\\\u00D6\\\u00D8-\\\u00F6\\\u00F8-\\\u02C1\\\u02C6-\\\u02D1\\\u02E0-\\\u02E4\\\u02EC
         \\\u02EE\\\u0300-\\\u0374\\\u0376-\\\u0377\\\u037B-\\\u037D\\\u037F\\\u0386-\\\u038A\\\u038C\\\u038E-\\\u03A1\\\u03A3-\\\u03F5\\\u03F7-\\\u0481
         \\\u0483-\\\u0487\\\u048A-\\\u052F\\\u0531-\\\u0556\\\u0559\\\u0561-\\\u0587\\\u0591-\\\u05BD\\\u05BF\\\u05C1-\\\u05C2\\\u05C4-\\\u05C5\\\u05C7
         \\\u05D0-\\\u05EA\\\u05F0-\\\u05F2\\\u0610-\\\u061A\\\u0620-\\\u0669\\\u066E-\\\u06D3\\\u06D5-\\\u06DC\\\u06DF-\\\u06E8\\\u06EA-\\\u06FC\\\u06FF
         \\\u0710-\\\u074A\\\u074D-\\\u07B1\\\u07C0-\\\u07F5\\\u07FA\\\u0800-\\\u082D\\\u0840-\\\u085B\\\u08A0-\\\u08B4\\\u08B6-\\\u08BD\\\u08D4-\\\u08E1
         \\\u08E3-\\\u0963\\\u0966-\\\u096F\\\u0971-\\\u0983\\\u0985-\\\u098C\\\u098F-\\\u0990\\\u0993-\\\u09A8\\\u09AA-\\\u09B0\\\u09B2\\\u09B6-\\\u09B9
         \\\u09BC-\\\u09C4\\\u09C7-\\\u09C8\\\u09CB-\\\u09CE\\\u09D7\\\u09DC-\\\u09DD\\\u09DF-\\\u09E3\\\u09E6-\\\u09F1\\\u0A01-\\\u0A03\\\u0A05-\\\u0A0A
         \\\u0A0F-\\\u0A10\\\u0A13-\\\u0A28\\\u0A2A-\\\u0A30\\\u0A32-\\\u0A33\\\u0A35-\\\u0A36\\\u0A38-\\\u0A39\\\u0A3C\\\u0A3E-\\\u0A42\\\u0A47-\\\u0A48
         \\\u0A4B-\\\u0A4D\\\u0A51\\\u0A59-\\\u0A5C\\\u0A5E\\\u0A66-\\\u0A75\\\u0A81-\\\u0A83\\\u0A85-\\\u0A8D\\\u0A8F-\\\u0A91\\\u0A93-\\\u0AA8
         \\\u0AAA-\\\u0AB0\\\u0AB2-\\\u0AB3\\\u0AB5-\\\u0AB9\\\u0ABC-\\\u0AC5\\\u0AC7-\\\u0AC9\\\u0ACB-\\\u0ACD\\\u0AD0\\\u0AE0-\\\u0AE3\\\u0AE6-\\\u0AEF
         \\\u0AF9\\\u0B01-\\\u0B03\\\u0B05-\\\u0B0C\\\u0B0F-\\\u0B10\\\u0B13-\\\u0B28\\\u0B2A-\\\u0B30\\\u0B32-\\\u0B33\\\u0B35-\\\u0B39\\\u0B3C-\\\u0B44
         \\\u0B47-\\\u0B48\\\u0B4B-\\\u0B4D\\\u0B56-\\\u0B57\\\u0B5C-\\\u0B5D\\\u0B5F-\\\u0B63\\\u0B66-\\\u0B6F\\\u0B71\\\u0B82-\\\u0B83\\\u0B85-\\\u0B8A
         \\\u0B8E-\\\u0B90\\\u0B92-\\\u0B95\\\u0B99-\\\u0B9A\\\u0B9C\\\u0B9E-\\\u0B9F\\\u0BA3-\\\u0BA4\\\u0BA8-\\\u0BAA\\\u0BAE-\\\u0BB9\\\u0BBE-\\\u0BC2
         \\\u0BC6-\\\u0BC8\\\u0BCA-\\\u0BCD\\\u0BD0\\\u0BD7\\\u0BE6-\\\u0BEF\\\u0C00-\\\u0C03\\\u0C05-\\\u0C0C\\\u0C0E-\\\u0C10\\\u0C12-\\\u0C28
         \\\u0C2A-\\\u0C39\\\u0C3D-\\\u0C44\\\u0C46-\\\u0C48\\\u0C4A-\\\u0C4D\\\u0C55-\\\u0C56\\\u0C58-\\\u0C5A\\\u0C60-\\\u0C63\\\u0C66-\\\u0C6F
         \\\u0C80-\\\u0C83\\\u0C85-\\\u0C8C\\\u0C8E-\\\u0C90\\\u0C92-\\\u0CA8\\\u0CAA-\\\u0CB3\\\u0CB5-\\\u0CB9\\\u0CBC-\\\u0CC4\\\u0CC6-\\\u0CC8
         \\\u0CCA-\\\u0CCD\\\u0CD5-\\\u0CD6\\\u0CDE\\\u0CE0-\\\u0CE3\\\u0CE6-\\\u0CEF\\\u0CF1-\\\u0CF2\\\u0D01-\\\u0D03\\\u0D05-\\\u0D0C\\\u0D0E-\\\u0D10
         \\\u0D12-\\\u0D3A\\\u0D3D-\\\u0D44\\\u0D46-\\\u0D48\\\u0D4A-\\\u0D4E\\\u0D54-\\\u0D57\\\u0D5F-\\\u0D63\\\u0D66-\\\u0D6F\\\u0D7A-\\\u0D7F
         \\\u0D82-\\\u0D83\\\u0D85-\\\u0D96\\\u0D9A-\\\u0DB1\\\u0DB3-\\\u0DBB\\\u0DBD\\\u0DC0-\\\u0DC6\\\u0DCA\\\u0DCF-\\\u0DD4\\\u0DD6\\\u0DD8-\\\u0DDF
         \\\u0DE6-\\\u0DEF\\\u0DF2-\\\u0DF3\\\u0E01-\\\u0E3A\\\u0E40-\\\u0E4E\\\u0E50-\\\u0E59\\\u0E81-\\\u0E82\\\u0E84\\\u0E87-\\\u0E88\\\u0E8A\\\u0E8D
         \\\u0E94-\\\u0E97\\\u0E99-\\\u0E9F\\\u0EA1-\\\u0EA3\\\u0EA5\\\u0EA7\\\u0EAA-\\\u0EAB\\\u0EAD-\\\u0EB9\\\u0EBB-\\\u0EBD\\\u0EC0-\\\u0EC4\\\u0EC6
         \\\u0EC8-\\\u0ECD\\\u0ED0-\\\u0ED9\\\u0EDC-\\\u0EDF\\\u0F00\\\u0F18-\\\u0F19\\\u0F20-\\\u0F29\\\u0F35\\\u0F37\\\u0F39\\\u0F3E-\\\u0F47
         \\\u0F49-\\\u0F6C\\\u0F71-\\\u0F84\\\u0F86-\\\u0F97\\\u0F99-\\\u0FBC\\\u0FC6\\\u1000-\\\u1049\\\u1050-\\\u109D\\\u10A0-\\\u10C5\\\u10C7\\\u10CD
         \\\u10D0-\\\u10FA\\\u10FC-\\\u115E\\\u1161-\\\u1248\\\u124A-\\\u124D\\\u1250-\\\u1256\\\u1258\\\u125A-\\\u125D\\\u1260-\\\u1288\\\u128A-\\\u128D
         \\\u1290-\\\u12B0\\\u12B2-\\\u12B5\\\u12B8-\\\u12BE\\\u12C0\\\u12C2-\\\u12C5\\\u12C8-\\\u12D6\\\u12D8-\\\u1310\\\u1312-\\\u1315\\\u1318-\\\u135A
         \\\u135D-\\\u135F\\\u1369-\\\u1371\\\u1380-\\\u138F\\\u13A0-\\\u13F5\\\u13F8-\\\u13FD\\\u1401-\\\u166C\\\u166F-\\\u167F\\\u1681-\\\u169A
         \\\u16A0-\\\u16EA\\\u16EE-\\\u16F8\\\u1700-\\\u170C\\\u170E-\\\u1714\\\u1720-\\\u1734\\\u1740-\\\u1753\\\u1760-\\\u176C\\\u176E-\\\u1770
         \\\u1772-\\\u1773\\\u1780-\\\u17D3\\\u17D7\\\u17DC-\\\u17DD\\\u17E0-\\\u17E9\\\u180B-\\\u180D\\\u1810-\\\u1819\\\u1820-\\\u1877\\\u1880-\\\u18AA
         \\\u18B0-\\\u18F5\\\u1900-\\\u191E\\\u1920-\\\u192B\\\u1930-\\\u193B\\\u1946-\\\u196D\\\u1970-\\\u1974\\\u1980-\\\u19AB\\\u19B0-\\\u19C9
         \\\u19D0-\\\u19DA\\\u1A00-\\\u1A1B\\\u1A20-\\\u1A5E\\\u1A60-\\\u1A7C\\\u1A7F-\\\u1A89\\\u1A90-\\\u1A99\\\u1AA7\\\u1AB0-\\\u1ABD\\\u1B00-\\\u1B4B
         \\\u1B50-\\\u1B59\\\u1B6B-\\\u1B73\\\u1B80-\\\u1BF3\\\u1C00-\\\u1C37\\\u1C40-\\\u1C49\\\u1C4D-\\\u1C7D\\\u1C80-\\\u1C88\\\u1CD0-\\\u1CD2
         \\\u1CD4-\\\u1CF6\\\u1CF8-\\\u1CF9\\\u1D00-\\\u1DF5\\\u1DFB-\\\u1F15\\\u1F18-\\\u1F1D\\\u1F20-\\\u1F45\\\u1F48-\\\u1F4D\\\u1F50-\\\u1F57\\\u1F59
         \\\u1F5B\\\u1F5D\\\u1F5F-\\\u1F7D\\\u1F80-\\\u1FB4\\\u1FB6-\\\u1FBC\\\u1FBE\\\u1FC2-\\\u1FC4\\\u1FC6-\\\u1FCC\\\u1FD0-\\\u1FD3\\\u1FD6-\\\u1FDB
         \\\u1FE0-\\\u1FEC\\\u1FF2-\\\u1FF4\\\u1FF6-\\\u1FFC\\\u203F-\\\u2040\\\u2054\\\u2071\\\u207F\\\u2090-\\\u209C\\\u20D0-\\\u20DC\\\u20E1
         \\\u20E5-\\\u20F0\\\u2102\\\u2107\\\u210A-\\\u2113\\\u2115\\\u2118-\\\u211D\\\u2124\\\u2126\\\u2128\\\u212A-\\\u2139\\\u213C-\\\u213F
         \\\u2145-\\\u2149\\\u214E\\\u2160-\\\u2188\\\u2C00-\\\u2C2E\\\u2C30-\\\u2C5E\\\u2C60-\\\u2CE4\\\u2CEB-\\\u2CF3\\\u2D00-\\\u2D25\\\u2D27\\\u2D2D
         \\\u2D30-\\\u2D67\\\u2D6F\\\u2D7F-\\\u2D96\\\u2DA0-\\\u2DA6\\\u2DA8-\\\u2DAE\\\u2DB0-\\\u2DB6\\\u2DB8-\\\u2DBE\\\u2DC0-\\\u2DC6\\\u2DC8-\\\u2DCE
         \\\u2DD0-\\\u2DD6\\\u2DD8-\\\u2DDE\\\u2DE0-\\\u2DFF\\\u3005-\\\u3007\\\u3021-\\\u302F\\\u3031-\\\u3035\\\u3038-\\\u303C\\\u3041-\\\u3096
         \\\u3099-\\\u309A\\\u309D-\\\u309F\\\u30A1-\\\u30FA\\\u30FC-\\\u30FF\\\u3105-\\\u312D\\\u3131-\\\u3163\\\u3165-\\\u318E\\\u31A0-\\\u31BA
         \\\u31F0-\\\u31FF\\\u3400-\\\u4DB5\\\u4E00-\\\u9FD5\\\uA000-\\\uA48C\\\uA4D0-\\\uA4FD\\\uA500-\\\uA60C\\\uA610-\\\uA62B\\\uA640-\\\uA66F
         \\\uA674-\\\uA67D\\\uA67F-\\\uA6F1\\\uA717-\\\uA71F\\\uA722-\\\uA788\\\uA78B-\\\uA7AE\\\uA7B0-\\\uA7B7\\\uA7F7-\\\uA827\\\uA840-\\\uA873
         \\\uA880-\\\uA8C5\\\uA8D0-\\\uA8D9\\\uA8E0-\\\uA8F7\\\uA8FB\\\uA8FD\\\uA900-\\\uA92D\\\uA930-\\\uA953\\\uA960-\\\uA97C\\\uA980-\\\uA9C0
         \\\uA9CF-\\\uA9D9\\\uA9E0-\\\uA9FE\\\uAA00-\\\uAA36\\\uAA40-\\\uAA4D\\\uAA50-\\\uAA59\\\uAA60-\\\uAA76\\\uAA7A-\\\uAAC2\\\uAADB-\\\uAADD
         \\\uAAE0-\\\uAAEF\\\uAAF2-\\\uAAF6\\\uAB01-\\\uAB06\\\uAB09-\\\uAB0E\\\uAB11-\\\uAB16\\\uAB20-\\\uAB26\\\uAB28-\\\uAB2E\\\uAB30-\\\uAB5A
         \\\uAB5C-\\\uAB65\\\uAB70-\\\uABEA\\\uABEC-\\\uABED\\\uABF0-\\\uABF9\\\uAC00-\\\uD7A3\\\uD7B0-\\\uD7C6\\\uD7CB-\\\uD7FB\\\uF900-\\\uFA6D
         \\\uFA70-\\\uFAD9\\\uFB00-\\\uFB06\\\uFB13-\\\uFB17\\\uFB1D-\\\uFB28\\\uFB2A-\\\uFB36\\\uFB38-\\\uFB3C\\\uFB3E\\\uFB40-\\\uFB41\\\uFB43-\\\uFB44
         \\\uFB46-\\\uFBB1\\\uFBD3-\\\uFC5D\\\uFC64-\\\uFD3D\\\uFD50-\\\uFD8F\\\uFD92-\\\uFDC7\\\uFDF0-\\\uFDF9\\\uFE00-\\\uFE0F\\\uFE20-\\\uFE2F
         \\\uFE33-\\\uFE34\\\uFE4D-\\\uFE4F\\\uFE71\\\uFE73\\\uFE77\\\uFE79\\\uFE7B\\\uFE7D\\\uFE7F-\\\uFEFC\\\uFF10-\\\uFF19\\\uFF21-\\\uFF3A\\\uFF3F
         \\\uFF41-\\\uFF5A\\\uFF66-\\\uFF9F\\\uFFA1-\\\uFFBE\\\uFFC2-\\\uFFC7\\\uFFCA-\\\uFFCF\\\uFFD2-\\\uFFD7\\\uFFDA-\\\uFFDC\\\U00010000-\\\U0001000B
         \\\U0001000D-\\\U00010026\\\U00010028-\\\U0001003A\\\U0001003C-\\\U0001003D\\\U0001003F-\\\U0001004D\\\U00010050-\\\U0001005D
         \\\U00010080-\\\U000100FA\\\U00010140-\\\U00010174\\\U000101FD\\\U00010280-\\\U0001029C\\\U000102A0-\\\U000102D0\\\U000102E0
         \\\U00010300-\\\U0001031F\\\U00010330-\\\U0001034A\\\U00010350-\\\U0001037A\\\U00010380-\\\U0001039D\\\U000103A0-\\\U000103C3
         \\\U000103C8-\\\U000103CF\\\U000103D1-\\\U000103D5\\\U00010400-\\\U0001049D\\\U000104A0-\\\U000104A9\\\U000104B0-\\\U000104D3
         \\\U000104D8-\\\U000104FB\\\U00010500-\\\U00010527\\\U00010530-\\\U00010563\\\U00010600-\\\U00010736\\\U00010740-\\\U00010755
         \\\U00010760-\\\U00010767\\\U00010800-\\\U00010805\\\U00010808\\\U0001080A-\\\U00010835\\\U00010837-\\\U00010838\\\U0001083C
         \\\U0001083F-\\\U00010855\\\U00010860-\\\U00010876\\\U00010880-\\\U0001089E\\\U000108E0-\\\U000108F2\\\U000108F4-\\\U000108F5
         \\\U00010900-\\\U00010915\\\U00010920-\\\U00010939\\\U00010980-\\\U000109B7\\\U000109BE-\\\U000109BF\\\U00010A00-\\\U00010A03
         \\\U00010A05-\\\U00010A06\\\U00010A0C-\\\U00010A13\\\U00010A15-\\\U00010A17\\\U00010A19-\\\U00010A33\\\U00010A38-\\\U00010A3A\\\U00010A3F
         \\\U00010A60-\\\U00010A7C\\\U00010A80-\\\U00010A9C\\\U00010AC0-\\\U00010AC7\\\U00010AC9-\\\U00010AE6\\\U00010B00-\\\U00010B35
         \\\U00010B40-\\\U00010B55\\\U00010B60-\\\U00010B72\\\U00010B80-\\\U00010B91\\\U00010C00-\\\U00010C48\\\U00010C80-\\\U00010CB2
         \\\U00010CC0-\\\U00010CF2\\\U00011000-\\\U00011046\\\U00011066-\\\U0001106F\\\U0001107F-\\\U000110BA\\\U000110D0-\\\U000110E8
         \\\U000110F0-\\\U000110F9\\\U00011100-\\\U00011134\\\U00011136-\\\U0001113F\\\U00011150-\\\U00011173\\\U00011176\\\U00011180-\\\U000111C4
         \\\U000111CA-\\\U000111CC\\\U000111D0-\\\U000111DA\\\U000111DC\\\U00011200-\\\U00011211\\\U00011213-\\\U00011237\\\U0001123E
         \\\U00011280-\\\U00011286\\\U00011288\\\U0001128A-\\\U0001128D\\\U0001128F-\\\U0001129D\\\U0001129F-\\\U000112A8\\\U000112B0-\\\U000112EA
         \\\U000112F0-\\\U000112F9\\\U00011300-\\\U00011303\\\U00011305-\\\U0001130C\\\U0001130F-\\\U00011310\\\U00011313-\\\U00011328
         \\\U0001132A-\\\U00011330\\\U00011332-\\\U00011333\\\U00011335-\\\U00011339\\\U0001133C-\\\U00011344\\\U00011347-\\\U00011348
         \\\U0001134B-\\\U0001134D\\\U00011350\\\U00011357\\\U0001135D-\\\U00011363\\\U00011366-\\\U0001136C\\\U00011370-\\\U00011374
         \\\U00011400-\\\U0001144A\\\U00011450-\\\U00011459\\\U00011480-\\\U000114C5\\\U000114C7\\\U000114D0-\\\U000114D9\\\U00011580-\\\U000115B5
         \\\U000115B8-\\\U000115C0\\\U000115D8-\\\U000115DD\\\U00011600-\\\U00011640\\\U00011644\\\U00011650-\\\U00011659\\\U00011680-\\\U000116B7
         \\\U000116C0-\\\U000116C9\\\U00011700-\\\U00011719\\\U0001171D-\\\U0001172B\\\U00011730-\\\U00011739\\\U000118A0-\\\U000118E9\\\U000118FF
         \\\U00011AC0-\\\U00011AF8\\\U00011C00-\\\U00011C08\\\U00011C0A-\\\U00011C36\\\U00011C38-\\\U00011C40\\\U00011C50-\\\U00011C59
         \\\U00011C72-\\\U00011C8F\\\U00011C92-\\\U00011CA7\\\U00011CA9-\\\U00011CB6\\\U00012000-\\\U00012399\\\U00012400-\\\U0001246E
         \\\U00012480-\\\U00012543\\\U00013000-\\\U0001342E\\\U00014400-\\\U00014646\\\U00016800-\\\U00016A38\\\U00016A40-\\\U00016A5E
         \\\U00016A60-\\\U00016A69\\\U00016AD0-\\\U00016AED\\\U00016AF0-\\\U00016AF4\\\U00016B00-\\\U00016B36\\\U00016B40-\\\U00016B43
         \\\U00016B50-\\\U00016B59\\\U00016B63-\\\U00016B77\\\U00016B7D-\\\U00016B8F\\\U00016F00-\\\U00016F44\\\U00016F50-\\\U00016F7E
         \\\U00016F8F-\\\U00016F9F\\\U00016FE0\\\U00017000-\\\U000187EC\\\U00018800-\\\U00018AF2\\\U0001B000-\\\U0001B001\\\U0001BC00-\\\U0001BC6A
         \\\U0001BC70-\\\U0001BC7C\\\U0001BC80-\\\U0001BC88\\\U0001BC90-\\\U0001BC99\\\U0001BC9D-\\\U0001BC9E\\\U0001D165-\\\U0001D169
         \\\U0001D16D-\\\U0001D172\\\U0001D17B-\\\U0001D182\\\U0001D185-\\\U0001D18B\\\U0001D1AA-\\\U0001D1AD\\\U0001D242-\\\U0001D244
         \\\U0001D400-\\\U0001D454\\\U0001D456-\\\U0001D49C\\\U0001D49E-\\\U0001D49F\\\U0001D4A2\\\U0001D4A5-\\\U0001D4A6\\\U0001D4A9-\\\U0001D4AC
         \\\U0001D4AE-\\\U0001D4B9\\\U0001D4BB\\\U0001D4BD-\\\U0001D4C3\\\U0001D4C5-\\\U0001D505\\\U0001D507-\\\U0001D50A\\\U0001D50D-\\\U0001D514
         \\\U0001D516-\\\U0001D51C\\\U0001D51E-\\\U0001D539\\\U0001D53B-\\\U0001D53E\\\U0001D540-\\\U0001D544\\\U0001D546\\\U0001D54A-\\\U0001D550
         \\\U0001D552-\\\U0001D6A5\\\U0001D6A8-\\\U0001D6C0\\\U0001D6C2-\\\U0001D6DA\\\U0001D6DC-\\\U0001D6FA\\\U0001D6FC-\\\U0001D714
         \\\U0001D716-\\\U0001D734\\\U0001D736-\\\U0001D74E\\\U0001D750-\\\U0001D76E\\\U0001D770-\\\U0001D788\\\U0001D78A-\\\U0001D7A8
         \\\U0001D7AA-\\\U0001D7C2\\\U0001D7C4-\\\U0001D7CB\\\U0001D7CE-\\\U0001D7FF\\\U0001DA00-\\\U0001DA36\\\U0001DA3B-\\\U0001DA6C\\\U0001DA75
         \\\U0001DA84\\\U0001DA9B-\\\U0001DA9F\\\U0001DAA1-\\\U0001DAAF\\\U0001E000-\\\U0001E006\\\U0001E008-\\\U0001E018\\\U0001E01B-\\\U0001E021
         \\\U0001E023-\\\U0001E024\\\U0001E026-\\\U0001E02A\\\U0001E800-\\\U0001E8C4\\\U0001E8D0-\\\U0001E8D6\\\U0001E900-\\\U0001E94A
         \\\U0001E950-\\\U0001E959\\\U0001EE00-\\\U0001EE03\\\U0001EE05-\\\U0001EE1F\\\U0001EE21-\\\U0001EE22\\\U0001EE24\\\U0001EE27
         \\\U0001EE29-\\\U0001EE32\\\U0001EE34-\\\U0001EE37\\\U0001EE39\\\U0001EE3B\\\U0001EE42\\\U0001EE47\\\U0001EE49\\\U0001EE4B\\\U0001EE4D-\\\U0001EE4F
         \\\U0001EE51-\\\U0001EE52\\\U0001EE54\\\U0001EE57\\\U0001EE59\\\U0001EE5B\\\U0001EE5D\\\U0001EE5F\\\U0001EE61-\\\U0001EE62\\\U0001EE64
         \\\U0001EE67-\\\U0001EE6A\\\U0001EE6C-\\\U0001EE72\\\U0001EE74-\\\U0001EE77\\\U0001EE79-\\\U0001EE7C\\\U0001EE7E\\\U0001EE80-\\\U0001EE89
         \\\U0001EE8B-\\\U0001EE9B\\\U0001EEA1-\\\U0001EEA3\\\U0001EEA5-\\\U0001EEA9\\\U0001EEAB-\\\U0001EEBB\\\U00020000-\\\U0002A6D6
         \\\U0002A700-\\\U0002B734\\\U0002B740-\\\U0002B81D\\\U0002B820-\\\U0002CEA1\\\U0002F800-\\\U0002FA1D\\\U000E0100-\\\U000E01EF]
        '''.replace('\x20', '').replace('\n', '')


# ascii_continue = set(cp for cp in xid_continue_less_fillers if cp < 128)
ASCII_CONTINUE = '[0-9A-Z\\\u005Fa-z]'




# Right-to-left code points (Bidi_Class R or AL).  Unassigned code points are
# included, so this can still be used if those are enabled as literals.  The
# pattern is also much more compact when unassigned code points are included.
#
# bidi_r_al = set([cp for cp, data in unicodetools.ucd.derivedbidiclass.items() if data['Bidi_Class'] in ('R', 'AL')])
if sys.maxunicode == 0xFFFF:
    BIDI_R_AL = '''
        [\\\u0590\\\u05BE\\\u05C0\\\u05C3\\\u05C6\\\u05C8-\\\u05FF\\\u0608\\\u060B\\\u060D\\\u061B-\\\u064A\\\u066D-\\\u066F\\\u0671-\\\u06D5
            \\\u06E5-\\\u06E6\\\u06EE-\\\u06EF\\\u06FA-\\\u0710\\\u0712-\\\u072F\\\u074B-\\\u07A5\\\u07B1-\\\u07EA\\\u07F4-\\\u07F5\\\u07FA-\\\u0815\\\u081A
            \\\u0824\\\u0828\\\u082E-\\\u0858\\\u085C-\\\u08D3\\\u200F\\\uFB1D\\\uFB1F-\\\uFB28\\\uFB2A-\\\uFD3D\\\uFD40-\\\uFDCF\\\uFDF0-\\\uFDFC
            \\\uFDFE-\\\uFDFF\\\uFE70-\\\uFEFE]
        |
        \\\uD802[\\\uDC00-\\\uDD1E]|\\\uD802[\\\uDD20-\\\uDE00]|\\\uD802\\\uDE04|\\\uD802[\\\uDE07-\\\uDE0B]|\\\uD802[\\\uDE10-\\\uDE37]|
        \\\uD802[\\\uDE3B-\\\uDE3E]|\\\uD802[\\\uDE40-\\\uDEE4]|\\\uD802[\\\uDEE7-\\\uDF38]|\\\uD802[\\\uDF40-\\\uDFFF]|\\\uD803[\\\uDC00-\\\uDE5F]|
        \\\uD803[\\\uDE7F-\\\uDFFF]|\\\uD83A[\\\uDC00-\\\uDCCF]|\\\uD83A[\\\uDCD7-\\\uDD43]|\\\uD83A[\\\uDD4B-\\\uDFFF]|\\\uD83B[\\\uDC00-\\\uDEEF]|
        \\\uD83B[\\\uDEF2-\\\uDFFF]
        '''.replace('\x20', '').replace('\n', '')
else:
    BIDI_R_AL = '''
        [\\\u0590\\\u05BE\\\u05C0\\\u05C3\\\u05C6\\\u05C8-\\\u05FF\\\u0608\\\u060B\\\u060D\\\u061B-\\\u064A\\\u066D-\\\u066F\\\u0671-\\\u06D5
         \\\u06E5-\\\u06E6\\\u06EE-\\\u06EF\\\u06FA-\\\u0710\\\u0712-\\\u072F\\\u074B-\\\u07A5\\\u07B1-\\\u07EA\\\u07F4-\\\u07F5\\\u07FA-\\\u0815\\\u081A
         \\\u0824\\\u0828\\\u082E-\\\u0858\\\u085C-\\\u08D3\\\u200F\\\uFB1D\\\uFB1F-\\\uFB28\\\uFB2A-\\\uFD3D\\\uFD40-\\\uFDCF\\\uFDF0-\\\uFDFC
         \\\uFDFE-\\\uFDFF\\\uFE70-\\\uFEFE\\\U00010800-\\\U0001091E\\\U00010920-\\\U00010A00\\\U00010A04\\\U00010A07-\\\U00010A0B\\\U00010A10-\\\U00010A37
         \\\U00010A3B-\\\U00010A3E\\\U00010A40-\\\U00010AE4\\\U00010AE7-\\\U00010B38\\\U00010B40-\\\U00010E5F\\\U00010E7F-\\\U00010FFF
         \\\U0001E800-\\\U0001E8CF\\\U0001E8D7-\\\U0001E943\\\U0001E94B-\\\U0001EEEF\\\U0001EEF2-\\\U0001EFFF]
        '''.replace('\x20', '').replace('\n', '')

BIDI_R_AL_SET = set([chr(cp) for cp in itertools.chain([range(0x00ad, 0x00ad),
                                                        range(0x034f, 0x034f),
                                                        range(0x061c, 0x061c),
                                                        range(0x115f, 0x1160),
                                                        range(0x17b4, 0x17b5),
                                                        range(0x180b, 0x180e),
                                                        range(0x200b, 0x200f),
                                                        range(0x202a, 0x202e),
                                                        range(0x2060, 0x206f),
                                                        range(0x3164, 0x3164),
                                                        range(0xfe00, 0xfe0f),
                                                        range(0xfeff, 0xfeff),
                                                        range(0xffa0, 0xffa0),
                                                        range(0xfff0, 0xfff8),
                                                        range(0x1bca0, 0x1bca3),
                                                        range(0x1d173, 0x1d17a),
                                                        range(0xe0000, 0xe0fff)])])




# Default ignorable.  A quoted string cannot consist of these alone.
#
# default_ignorable = set([cp for cp, data in unicodetools.ucd.derivedcoreproperties.items() if 'Default_Ignorable_Code_Point' in data])
if sys.maxunicode == 0xFFFF:
    DEFAULT_IGNORABLE = '''
        [\\\u00AD\\\u034F\\\u061C\\\u115F-\\\u1160\\\u17B4-\\\u17B5\\\u180B-\\\u180E\\\u200B-\\\u200F\\\u202A-\\\u202E\\\u2060-\\\u206F\\\u3164
            \\\uFE00-\\\uFE0F\\\uFEFF\\\uFFA0\\\uFFF0-\\\uFFF8]
        |
        \\\uD82F[\\\uDCA0-\\\uDCA3]|\\\uD834[\\\uDD73-\\\uDD7A]|[\\\uDB40-\\\uDB43][\\\uDC00-\\\uDFFF]
        '''.replace('\x20', '').replace('\n', '')
else:
    DEFAULT_IGNORABLE = '''
        [\\\u00AD\\\u034F\\\u061C\\\u115F-\\\u1160\\\u17B4-\\\u17B5\\\u180B-\\\u180E\\\u200B-\\\u200F\\\u202A-\\\u202E\\\u2060-\\\u206F\\\u3164
         \\\uFE00-\\\uFE0F\\\uFEFF\\\uFFA0\\\uFFF0-\\\uFFF8\\\U0001BCA0-\\\U0001BCA3\\\U0001D173-\\\U0001D17A\\\U000E0000-\\\U000E0FFF]
        '''.replace('\x20', '').replace('\n', '')








# The remaining patterns relate to code points that are not allowed as
# literals.


# Unpaired Unicode surrogates
UNPAIRED_SURROGATE = '[\\\uD800-\\\uDBFF](?=[^\\\uDC00-\\\uDFFF]|$)|(?<![\\\uD800-\\\uDBFF])[\\\uDC00-\\\uDFFF]'


# Default invalid literal code points.  These are assembled as single massive
# patterns to yield the simplest possible regex and thus increase efficiency
# somewhat.
#
# For narrow builds, a pattern without surrogates is used, and is extended
# at the beginning with an appropriate pattern for unpaired surrogates.
# For all other cases, surrogates are incorporated in the pattern generation,
# because the surrogate range ends up falling within a larger range, and thus
# incorporating it results in a simpler pattern.
#
# Note that noncharacter code points are not listed in UnicodeData.txt,
# so generating a list of unassigned code points that are not noncharacters
# must be done with care.
#
# unicode_cc_less_tab_line_feed = set([cp for cp, data in unicodetools.ucd.unicodedata.items() if data['General_Category'] == 'Cc']) - set([ord(c) for c in ('\t', '\n')])
# non_unicode_cc_newlines = set([ord(c) for c in ('\u2028', '\u2029')])
# bidi_control = set([cp for cp, data in unicodetools.ucd.proplist.items() if 'Bidi_Control' in data])
# bom = set([ord('\uFEFF')])
# noncharacters = set([cp for cp, data in unicodetools.ucd.proplist.items() if 'Noncharacter_Code_Point' in data])
# private_use = set([cp for cp, data in unicodetools.ucd.blocks.items() if 'Private' in data['Block'] and (cp < 0xD800 or cp > 0xDFFF) and cp in unicodetools.ucd.unicodedata])
# unassigned_reserved = set([cp for cp in range(0, 0x10FFFF+1) if cp not in unicodetools.ucd.unicodedata and cp not in noncharacters])
# surrogates = set([cp for cp, data in unicodetools.ucd.blocks.items() if 'Surrogate' in data['Block']])
# default_invalid_literal_less_surrogates = unicode_cc_less_tab_line_feed | non_unicode_cc_newlines | bidi_control | bom | noncharacters | private_use | unassigned_reserved
# default_invalid_literal = default_invalid_literal_less_surrogates | surrogates
# default_invalid_literal_less_private_use_unassigned_reserved_surrogates = default_invalid_literal - private_use - unassigned_reserved - surrogates
# default_invalid_literal_less_private_use_unassigned_reserved = default_invalid_literal_less_private_use_unassigned_reserved_surrogates | surrogates
if sys.maxunicode == 0xFFFF:
    DEFAULT_INVALID_LITERAL = '''
        {UNPAIRED_SURROGATE}
        |
        [\\\u0000-\\\u0008\\\u000B-\\\u001F\\\u007F-\\\u009F\\\u0378-\\\u0379\\\u0380-\\\u0383\\\u038B\\\u038D\\\u03A2\\\u0530\\\u0557-\\\u0558\\\u0560
         \\\u0588\\\u058B-\\\u058C\\\u0590\\\u05C8-\\\u05CF\\\u05EB-\\\u05EF\\\u05F5-\\\u05FF\\\u061C-\\\u061D\\\u070E\\\u074B-\\\u074C\\\u07B2-\\\u07BF
         \\\u07FB-\\\u07FF\\\u082E-\\\u082F\\\u083F\\\u085C-\\\u085D\\\u085F-\\\u089F\\\u08B5\\\u08BE-\\\u08D3\\\u0984\\\u098D-\\\u098E\\\u0991-\\\u0992
         \\\u09A9\\\u09B1\\\u09B3-\\\u09B5\\\u09BA-\\\u09BB\\\u09C5-\\\u09C6\\\u09C9-\\\u09CA\\\u09CF-\\\u09D6\\\u09D8-\\\u09DB\\\u09DE\\\u09E4-\\\u09E5
         \\\u09FC-\\\u0A00\\\u0A04\\\u0A0B-\\\u0A0E\\\u0A11-\\\u0A12\\\u0A29\\\u0A31\\\u0A34\\\u0A37\\\u0A3A-\\\u0A3B\\\u0A3D\\\u0A43-\\\u0A46
         \\\u0A49-\\\u0A4A\\\u0A4E-\\\u0A50\\\u0A52-\\\u0A58\\\u0A5D\\\u0A5F-\\\u0A65\\\u0A76-\\\u0A80\\\u0A84\\\u0A8E\\\u0A92\\\u0AA9\\\u0AB1\\\u0AB4
         \\\u0ABA-\\\u0ABB\\\u0AC6\\\u0ACA\\\u0ACE-\\\u0ACF\\\u0AD1-\\\u0ADF\\\u0AE4-\\\u0AE5\\\u0AF2-\\\u0AF8\\\u0AFA-\\\u0B00\\\u0B04\\\u0B0D-\\\u0B0E
         \\\u0B11-\\\u0B12\\\u0B29\\\u0B31\\\u0B34\\\u0B3A-\\\u0B3B\\\u0B45-\\\u0B46\\\u0B49-\\\u0B4A\\\u0B4E-\\\u0B55\\\u0B58-\\\u0B5B\\\u0B5E
         \\\u0B64-\\\u0B65\\\u0B78-\\\u0B81\\\u0B84\\\u0B8B-\\\u0B8D\\\u0B91\\\u0B96-\\\u0B98\\\u0B9B\\\u0B9D\\\u0BA0-\\\u0BA2\\\u0BA5-\\\u0BA7
         \\\u0BAB-\\\u0BAD\\\u0BBA-\\\u0BBD\\\u0BC3-\\\u0BC5\\\u0BC9\\\u0BCE-\\\u0BCF\\\u0BD1-\\\u0BD6\\\u0BD8-\\\u0BE5\\\u0BFB-\\\u0BFF\\\u0C04\\\u0C0D
         \\\u0C11\\\u0C29\\\u0C3A-\\\u0C3C\\\u0C45\\\u0C49\\\u0C4E-\\\u0C54\\\u0C57\\\u0C5B-\\\u0C5F\\\u0C64-\\\u0C65\\\u0C70-\\\u0C77\\\u0C84\\\u0C8D
         \\\u0C91\\\u0CA9\\\u0CB4\\\u0CBA-\\\u0CBB\\\u0CC5\\\u0CC9\\\u0CCE-\\\u0CD4\\\u0CD7-\\\u0CDD\\\u0CDF\\\u0CE4-\\\u0CE5\\\u0CF0\\\u0CF3-\\\u0D00
         \\\u0D04\\\u0D0D\\\u0D11\\\u0D3B-\\\u0D3C\\\u0D45\\\u0D49\\\u0D50-\\\u0D53\\\u0D64-\\\u0D65\\\u0D80-\\\u0D81\\\u0D84\\\u0D97-\\\u0D99\\\u0DB2
         \\\u0DBC\\\u0DBE-\\\u0DBF\\\u0DC7-\\\u0DC9\\\u0DCB-\\\u0DCE\\\u0DD5\\\u0DD7\\\u0DE0-\\\u0DE5\\\u0DF0-\\\u0DF1\\\u0DF5-\\\u0E00\\\u0E3B-\\\u0E3E
         \\\u0E5C-\\\u0E80\\\u0E83\\\u0E85-\\\u0E86\\\u0E89\\\u0E8B-\\\u0E8C\\\u0E8E-\\\u0E93\\\u0E98\\\u0EA0\\\u0EA4\\\u0EA6\\\u0EA8-\\\u0EA9\\\u0EAC
         \\\u0EBA\\\u0EBE-\\\u0EBF\\\u0EC5\\\u0EC7\\\u0ECE-\\\u0ECF\\\u0EDA-\\\u0EDB\\\u0EE0-\\\u0EFF\\\u0F48\\\u0F6D-\\\u0F70\\\u0F98\\\u0FBD\\\u0FCD
         \\\u0FDB-\\\u0FFF\\\u10C6\\\u10C8-\\\u10CC\\\u10CE-\\\u10CF\\\u1249\\\u124E-\\\u124F\\\u1257\\\u1259\\\u125E-\\\u125F\\\u1289\\\u128E-\\\u128F
         \\\u12B1\\\u12B6-\\\u12B7\\\u12BF\\\u12C1\\\u12C6-\\\u12C7\\\u12D7\\\u1311\\\u1316-\\\u1317\\\u135B-\\\u135C\\\u137D-\\\u137F\\\u139A-\\\u139F
         \\\u13F6-\\\u13F7\\\u13FE-\\\u13FF\\\u169D-\\\u169F\\\u16F9-\\\u16FF\\\u170D\\\u1715-\\\u171F\\\u1737-\\\u173F\\\u1754-\\\u175F\\\u176D\\\u1771
         \\\u1774-\\\u177F\\\u17DE-\\\u17DF\\\u17EA-\\\u17EF\\\u17FA-\\\u17FF\\\u180F\\\u181A-\\\u181F\\\u1878-\\\u187F\\\u18AB-\\\u18AF\\\u18F6-\\\u18FF
         \\\u191F\\\u192C-\\\u192F\\\u193C-\\\u193F\\\u1941-\\\u1943\\\u196E-\\\u196F\\\u1975-\\\u197F\\\u19AC-\\\u19AF\\\u19CA-\\\u19CF\\\u19DB-\\\u19DD
         \\\u1A1C-\\\u1A1D\\\u1A5F\\\u1A7D-\\\u1A7E\\\u1A8A-\\\u1A8F\\\u1A9A-\\\u1A9F\\\u1AAE-\\\u1AAF\\\u1ABF-\\\u1AFF\\\u1B4C-\\\u1B4F\\\u1B7D-\\\u1B7F
         \\\u1BF4-\\\u1BFB\\\u1C38-\\\u1C3A\\\u1C4A-\\\u1C4C\\\u1C89-\\\u1CBF\\\u1CC8-\\\u1CCF\\\u1CF7\\\u1CFA-\\\u1CFF\\\u1DF6-\\\u1DFA\\\u1F16-\\\u1F17
         \\\u1F1E-\\\u1F1F\\\u1F46-\\\u1F47\\\u1F4E-\\\u1F4F\\\u1F58\\\u1F5A\\\u1F5C\\\u1F5E\\\u1F7E-\\\u1F7F\\\u1FB5\\\u1FC5\\\u1FD4-\\\u1FD5\\\u1FDC
         \\\u1FF0-\\\u1FF1\\\u1FF5\\\u1FFF\\\u200E-\\\u200F\\\u2028-\\\u202E\\\u2065-\\\u2069\\\u2072-\\\u2073\\\u208F\\\u209D-\\\u209F\\\u20BF-\\\u20CF
         \\\u20F1-\\\u20FF\\\u218C-\\\u218F\\\u23FF\\\u2427-\\\u243F\\\u244B-\\\u245F\\\u2B74-\\\u2B75\\\u2B96-\\\u2B97\\\u2BBA-\\\u2BBC\\\u2BC9
         \\\u2BD2-\\\u2BEB\\\u2BF0-\\\u2BFF\\\u2C2F\\\u2C5F\\\u2CF4-\\\u2CF8\\\u2D26\\\u2D28-\\\u2D2C\\\u2D2E-\\\u2D2F\\\u2D68-\\\u2D6E\\\u2D71-\\\u2D7E
         \\\u2D97-\\\u2D9F\\\u2DA7\\\u2DAF\\\u2DB7\\\u2DBF\\\u2DC7\\\u2DCF\\\u2DD7\\\u2DDF\\\u2E45-\\\u2E7F\\\u2E9A\\\u2EF4-\\\u2EFF\\\u2FD6-\\\u2FEF
         \\\u2FFC-\\\u2FFF\\\u3040\\\u3097-\\\u3098\\\u3100-\\\u3104\\\u312E-\\\u3130\\\u318F\\\u31BB-\\\u31BF\\\u31E4-\\\u31EF\\\u321F\\\u32FF
         \\\u4DB6-\\\u4DBF\\\u9FD6-\\\u9FFF\\\uA48D-\\\uA48F\\\uA4C7-\\\uA4CF\\\uA62C-\\\uA63F\\\uA6F8-\\\uA6FF\\\uA7AF\\\uA7B8-\\\uA7F6\\\uA82C-\\\uA82F
         \\\uA83A-\\\uA83F\\\uA878-\\\uA87F\\\uA8C6-\\\uA8CD\\\uA8DA-\\\uA8DF\\\uA8FE-\\\uA8FF\\\uA954-\\\uA95E\\\uA97D-\\\uA97F\\\uA9CE\\\uA9DA-\\\uA9DD
         \\\uA9FF\\\uAA37-\\\uAA3F\\\uAA4E-\\\uAA4F\\\uAA5A-\\\uAA5B\\\uAAC3-\\\uAADA\\\uAAF7-\\\uAB00\\\uAB07-\\\uAB08\\\uAB0F-\\\uAB10\\\uAB17-\\\uAB1F
         \\\uAB27\\\uAB2F\\\uAB66-\\\uAB6F\\\uABEE-\\\uABEF\\\uABFA-\\\uABFF\\\uD7A4-\\\uD7AF\\\uD7C7-\\\uD7CA\\\uD7FC-\\\uD7FF\\\uE000-\\\uF8FF
         \\\uFA6E-\\\uFA6F\\\uFADA-\\\uFAFF\\\uFB07-\\\uFB12\\\uFB18-\\\uFB1C\\\uFB37\\\uFB3D\\\uFB3F\\\uFB42\\\uFB45\\\uFBC2-\\\uFBD2\\\uFD40-\\\uFD4F
         \\\uFD90-\\\uFD91\\\uFDC8-\\\uFDEF\\\uFDFE-\\\uFDFF\\\uFE1A-\\\uFE1F\\\uFE53\\\uFE67\\\uFE6C-\\\uFE6F\\\uFE75\\\uFEFD-\\\uFF00\\\uFFBF-\\\uFFC1
         \\\uFFC8-\\\uFFC9\\\uFFD0-\\\uFFD1\\\uFFD8-\\\uFFD9\\\uFFDD-\\\uFFDF\\\uFFE7\\\uFFEF-\\\uFFF8\\\uFFFE-\\\uFFFF]
        |
        \\\uD800\\\uDC0C|\\\uD800\\\uDC27|\\\uD800\\\uDC3B|\\\uD800\\\uDC3E|\\\uD800[\\\uDC4E-\\\uDC4F]|\\\uD800[\\\uDC5E-\\\uDC7F]|
        \\\uD800[\\\uDCFB-\\\uDCFF]|\\\uD800[\\\uDD03-\\\uDD06]|\\\uD800[\\\uDD34-\\\uDD36]|\\\uD800\\\uDD8F|\\\uD800[\\\uDD9C-\\\uDD9F]|
        \\\uD800[\\\uDDA1-\\\uDDCF]|\\\uD800[\\\uDDFE-\\\uDE7F]|\\\uD800[\\\uDE9D-\\\uDE9F]|\\\uD800[\\\uDED1-\\\uDEDF]|\\\uD800[\\\uDEFC-\\\uDEFF]|
        \\\uD800[\\\uDF24-\\\uDF2F]|\\\uD800[\\\uDF4B-\\\uDF4F]|\\\uD800[\\\uDF7B-\\\uDF7F]|\\\uD800\\\uDF9E|\\\uD800[\\\uDFC4-\\\uDFC7]|
        \\\uD800[\\\uDFD6-\\\uDFFF]|\\\uD801[\\\uDC9E-\\\uDC9F]|\\\uD801[\\\uDCAA-\\\uDCAF]|\\\uD801[\\\uDCD4-\\\uDCD7]|\\\uD801[\\\uDCFC-\\\uDCFF]|
        \\\uD801[\\\uDD28-\\\uDD2F]|\\\uD801[\\\uDD64-\\\uDD6E]|\\\uD801[\\\uDD70-\\\uDDFF]|\\\uD801[\\\uDF37-\\\uDF3F]|\\\uD801[\\\uDF56-\\\uDF5F]|
        \\\uD801[\\\uDF68-\\\uDFFF]|\\\uD802[\\\uDC06-\\\uDC07]|\\\uD802\\\uDC09|\\\uD802\\\uDC36|\\\uD802[\\\uDC39-\\\uDC3B]|\\\uD802[\\\uDC3D-\\\uDC3E]|
        \\\uD802\\\uDC56|\\\uD802[\\\uDC9F-\\\uDCA6]|\\\uD802[\\\uDCB0-\\\uDCDF]|\\\uD802\\\uDCF3|\\\uD802[\\\uDCF6-\\\uDCFA]|\\\uD802[\\\uDD1C-\\\uDD1E]|
        \\\uD802[\\\uDD3A-\\\uDD3E]|\\\uD802[\\\uDD40-\\\uDD7F]|\\\uD802[\\\uDDB8-\\\uDDBB]|\\\uD802[\\\uDDD0-\\\uDDD1]|\\\uD802\\\uDE04|
        \\\uD802[\\\uDE07-\\\uDE0B]|\\\uD802\\\uDE14|\\\uD802\\\uDE18|\\\uD802[\\\uDE34-\\\uDE37]|\\\uD802[\\\uDE3B-\\\uDE3E]|\\\uD802[\\\uDE48-\\\uDE4F]|
        \\\uD802[\\\uDE59-\\\uDE5F]|\\\uD802[\\\uDEA0-\\\uDEBF]|\\\uD802[\\\uDEE7-\\\uDEEA]|\\\uD802[\\\uDEF7-\\\uDEFF]|\\\uD802[\\\uDF36-\\\uDF38]|
        \\\uD802[\\\uDF56-\\\uDF57]|\\\uD802[\\\uDF73-\\\uDF77]|\\\uD802[\\\uDF92-\\\uDF98]|\\\uD802[\\\uDF9D-\\\uDFA8]|\\\uD802[\\\uDFB0-\\\uDFFF]|
        \\\uD803[\\\uDC49-\\\uDC7F]|\\\uD803[\\\uDCB3-\\\uDCBF]|\\\uD803[\\\uDCF3-\\\uDCF9]|\\\uD803[\\\uDD00-\\\uDE5F]|\\\uD803[\\\uDE7F-\\\uDFFF]|
        \\\uD804[\\\uDC4E-\\\uDC51]|\\\uD804[\\\uDC70-\\\uDC7E]|\\\uD804[\\\uDCC2-\\\uDCCF]|\\\uD804[\\\uDCE9-\\\uDCEF]|\\\uD804[\\\uDCFA-\\\uDCFF]|
        \\\uD804\\\uDD35|\\\uD804[\\\uDD44-\\\uDD4F]|\\\uD804[\\\uDD77-\\\uDD7F]|\\\uD804[\\\uDDCE-\\\uDDCF]|\\\uD804\\\uDDE0|\\\uD804[\\\uDDF5-\\\uDDFF]|
        \\\uD804\\\uDE12|\\\uD804[\\\uDE3F-\\\uDE7F]|\\\uD804\\\uDE87|\\\uD804\\\uDE89|\\\uD804\\\uDE8E|\\\uD804\\\uDE9E|\\\uD804[\\\uDEAA-\\\uDEAF]|
        \\\uD804[\\\uDEEB-\\\uDEEF]|\\\uD804[\\\uDEFA-\\\uDEFF]|\\\uD804\\\uDF04|\\\uD804[\\\uDF0D-\\\uDF0E]|\\\uD804[\\\uDF11-\\\uDF12]|\\\uD804\\\uDF29|
        \\\uD804\\\uDF31|\\\uD804\\\uDF34|\\\uD804[\\\uDF3A-\\\uDF3B]|\\\uD804[\\\uDF45-\\\uDF46]|\\\uD804[\\\uDF49-\\\uDF4A]|\\\uD804[\\\uDF4E-\\\uDF4F]|
        \\\uD804[\\\uDF51-\\\uDF56]|\\\uD804[\\\uDF58-\\\uDF5C]|\\\uD804[\\\uDF64-\\\uDF65]|\\\uD804[\\\uDF6D-\\\uDF6F]|\\\uD804[\\\uDF75-\\\uDFFF]|
        \\\uD805\\\uDC5A|\\\uD805\\\uDC5C|\\\uD805[\\\uDC5E-\\\uDC7F]|\\\uD805[\\\uDCC8-\\\uDCCF]|\\\uD805[\\\uDCDA-\\\uDD7F]|\\\uD805[\\\uDDB6-\\\uDDB7]|
        \\\uD805[\\\uDDDE-\\\uDDFF]|\\\uD805[\\\uDE45-\\\uDE4F]|\\\uD805[\\\uDE5A-\\\uDE5F]|\\\uD805[\\\uDE6D-\\\uDE7F]|\\\uD805[\\\uDEB8-\\\uDEBF]|
        \\\uD805[\\\uDECA-\\\uDEFF]|\\\uD805[\\\uDF1A-\\\uDF1C]|\\\uD805[\\\uDF2C-\\\uDF2F]|\\\uD805[\\\uDF40-\\\uDFFF]|\\\uD806[\\\uDC00-\\\uDC9F]|
        \\\uD806[\\\uDCF3-\\\uDCFE]|\\\uD806[\\\uDD00-\\\uDEBF]|\\\uD806[\\\uDEF9-\\\uDFFF]|\\\uD807\\\uDC09|\\\uD807\\\uDC37|\\\uD807[\\\uDC46-\\\uDC4F]|
        \\\uD807[\\\uDC6D-\\\uDC6F]|\\\uD807[\\\uDC90-\\\uDC91]|\\\uD807\\\uDCA8|\\\uD807[\\\uDCB7-\\\uDFFF]|\\\uD808[\\\uDF9A-\\\uDFFF]|\\\uD809\\\uDC6F|
        \\\uD809[\\\uDC75-\\\uDC7F]|\\\uD809[\\\uDD44-\\\uDFFF]|[\\\uD80A-\\\uD80B][\\\uDC00-\\\uDFFF]|\\\uD80D[\\\uDC2F-\\\uDFFF]|
        [\\\uD80E-\\\uD810][\\\uDC00-\\\uDFFF]|\\\uD811[\\\uDE47-\\\uDFFF]|[\\\uD812-\\\uD819][\\\uDC00-\\\uDFFF]|\\\uD81A[\\\uDE39-\\\uDE3F]|
        \\\uD81A\\\uDE5F|\\\uD81A[\\\uDE6A-\\\uDE6D]|\\\uD81A[\\\uDE70-\\\uDECF]|\\\uD81A[\\\uDEEE-\\\uDEEF]|\\\uD81A[\\\uDEF6-\\\uDEFF]|
        \\\uD81A[\\\uDF46-\\\uDF4F]|\\\uD81A\\\uDF5A|\\\uD81A\\\uDF62|\\\uD81A[\\\uDF78-\\\uDF7C]|\\\uD81A[\\\uDF90-\\\uDFFF]|\\\uD81B[\\\uDC00-\\\uDEFF]|
        \\\uD81B[\\\uDF45-\\\uDF4F]|\\\uD81B[\\\uDF7F-\\\uDF8E]|\\\uD81B[\\\uDFA0-\\\uDFDF]|\\\uD81B[\\\uDFE1-\\\uDFFF]|\\\uD821[\\\uDFED-\\\uDFFF]|
        \\\uD822[\\\uDEF3-\\\uDFFF]|[\\\uD823-\\\uD82B][\\\uDC00-\\\uDFFF]|\\\uD82C[\\\uDC02-\\\uDFFF]|[\\\uD82D-\\\uD82E][\\\uDC00-\\\uDFFF]|
        \\\uD82F[\\\uDC6B-\\\uDC6F]|\\\uD82F[\\\uDC7D-\\\uDC7F]|\\\uD82F[\\\uDC89-\\\uDC8F]|\\\uD82F[\\\uDC9A-\\\uDC9B]|\\\uD82F[\\\uDCA4-\\\uDFFF]|
        [\\\uD830-\\\uD833][\\\uDC00-\\\uDFFF]|\\\uD834[\\\uDCF6-\\\uDCFF]|\\\uD834[\\\uDD27-\\\uDD28]|\\\uD834[\\\uDDE9-\\\uDDFF]|
        \\\uD834[\\\uDE46-\\\uDEFF]|\\\uD834[\\\uDF57-\\\uDF5F]|\\\uD834[\\\uDF72-\\\uDFFF]|\\\uD835\\\uDC55|\\\uD835\\\uDC9D|\\\uD835[\\\uDCA0-\\\uDCA1]|
        \\\uD835[\\\uDCA3-\\\uDCA4]|\\\uD835[\\\uDCA7-\\\uDCA8]|\\\uD835\\\uDCAD|\\\uD835\\\uDCBA|\\\uD835\\\uDCBC|\\\uD835\\\uDCC4|\\\uD835\\\uDD06|
        \\\uD835[\\\uDD0B-\\\uDD0C]|\\\uD835\\\uDD15|\\\uD835\\\uDD1D|\\\uD835\\\uDD3A|\\\uD835\\\uDD3F|\\\uD835\\\uDD45|\\\uD835[\\\uDD47-\\\uDD49]|
        \\\uD835\\\uDD51|\\\uD835[\\\uDEA6-\\\uDEA7]|\\\uD835[\\\uDFCC-\\\uDFCD]|\\\uD836[\\\uDE8C-\\\uDE9A]|\\\uD836\\\uDEA0|\\\uD836[\\\uDEB0-\\\uDFFF]|
        \\\uD837[\\\uDC00-\\\uDFFF]|\\\uD838\\\uDC07|\\\uD838[\\\uDC19-\\\uDC1A]|\\\uD838\\\uDC22|\\\uD838\\\uDC25|\\\uD838[\\\uDC2B-\\\uDFFF]|
        \\\uD839[\\\uDC00-\\\uDFFF]|\\\uD83A[\\\uDCC5-\\\uDCC6]|\\\uD83A[\\\uDCD7-\\\uDCFF]|\\\uD83A[\\\uDD4B-\\\uDD4F]|\\\uD83A[\\\uDD5A-\\\uDD5D]|
        \\\uD83A[\\\uDD60-\\\uDFFF]|\\\uD83B[\\\uDC00-\\\uDDFF]|\\\uD83B\\\uDE04|\\\uD83B\\\uDE20|\\\uD83B\\\uDE23|\\\uD83B[\\\uDE25-\\\uDE26]|
        \\\uD83B\\\uDE28|\\\uD83B\\\uDE33|\\\uD83B\\\uDE38|\\\uD83B\\\uDE3A|\\\uD83B[\\\uDE3C-\\\uDE41]|\\\uD83B[\\\uDE43-\\\uDE46]|\\\uD83B\\\uDE48|
        \\\uD83B\\\uDE4A|\\\uD83B\\\uDE4C|\\\uD83B\\\uDE50|\\\uD83B\\\uDE53|\\\uD83B[\\\uDE55-\\\uDE56]|\\\uD83B\\\uDE58|\\\uD83B\\\uDE5A|\\\uD83B\\\uDE5C|
        \\\uD83B\\\uDE5E|\\\uD83B\\\uDE60|\\\uD83B\\\uDE63|\\\uD83B[\\\uDE65-\\\uDE66]|\\\uD83B\\\uDE6B|\\\uD83B\\\uDE73|\\\uD83B\\\uDE78|\\\uD83B\\\uDE7D|
        \\\uD83B\\\uDE7F|\\\uD83B\\\uDE8A|\\\uD83B[\\\uDE9C-\\\uDEA0]|\\\uD83B\\\uDEA4|\\\uD83B\\\uDEAA|\\\uD83B[\\\uDEBC-\\\uDEEF]|
        \\\uD83B[\\\uDEF2-\\\uDFFF]|\\\uD83C[\\\uDC2C-\\\uDC2F]|\\\uD83C[\\\uDC94-\\\uDC9F]|\\\uD83C[\\\uDCAF-\\\uDCB0]|\\\uD83C\\\uDCC0|\\\uD83C\\\uDCD0|
        \\\uD83C[\\\uDCF6-\\\uDCFF]|\\\uD83C[\\\uDD0D-\\\uDD0F]|\\\uD83C\\\uDD2F|\\\uD83C[\\\uDD6C-\\\uDD6F]|\\\uD83C[\\\uDDAD-\\\uDDE5]|
        \\\uD83C[\\\uDE03-\\\uDE0F]|\\\uD83C[\\\uDE3C-\\\uDE3F]|\\\uD83C[\\\uDE49-\\\uDE4F]|\\\uD83C[\\\uDE52-\\\uDEFF]|\\\uD83D[\\\uDED3-\\\uDEDF]|
        \\\uD83D[\\\uDEED-\\\uDEEF]|\\\uD83D[\\\uDEF7-\\\uDEFF]|\\\uD83D[\\\uDF74-\\\uDF7F]|\\\uD83D[\\\uDFD5-\\\uDFFF]|\\\uD83E[\\\uDC0C-\\\uDC0F]|
        \\\uD83E[\\\uDC48-\\\uDC4F]|\\\uD83E[\\\uDC5A-\\\uDC5F]|\\\uD83E[\\\uDC88-\\\uDC8F]|\\\uD83E[\\\uDCAE-\\\uDD0F]|\\\uD83E\\\uDD1F|
        \\\uD83E[\\\uDD28-\\\uDD2F]|\\\uD83E[\\\uDD31-\\\uDD32]|\\\uD83E\\\uDD3F|\\\uD83E[\\\uDD4C-\\\uDD4F]|\\\uD83E[\\\uDD5F-\\\uDD7F]|
        \\\uD83E[\\\uDD92-\\\uDDBF]|\\\uD83E[\\\uDDC1-\\\uDFFF]|\\\uD83F[\\\uDC00-\\\uDFFF]|\\\uD869[\\\uDED7-\\\uDEFF]|\\\uD86D[\\\uDF35-\\\uDF3F]|
        \\\uD86E[\\\uDC1E-\\\uDC1F]|\\\uD873[\\\uDEA2-\\\uDFFF]|[\\\uD874-\\\uD87D][\\\uDC00-\\\uDFFF]|\\\uD87E[\\\uDE1E-\\\uDFFF]|
        [\\\uD87F-\\\uDB3F][\\\uDC00-\\\uDFFF]|\\\uDB40\\\uDC00|\\\uDB40[\\\uDC02-\\\uDC1F]|\\\uDB40[\\\uDC80-\\\uDCFF]|\\\uDB40[\\\uDDF0-\\\uDFFF]|
        [\\\uDB41-\\\uDBFF][\\\uDC00-\\\uDFFF]
        '''.replace('\x20', '').replace('\n', '').replace('{UNPAIRED_SURROGATE}', UNPAIRED_SURROGATE)
else:
    DEFAULT_INVALID_LITERAL = '''
        [\\\u0000-\\\u0008\\\u000B-\\\u001F\\\u007F-\\\u009F\\\u0378-\\\u0379\\\u0380-\\\u0383\\\u038B\\\u038D\\\u03A2\\\u0530\\\u0557-\\\u0558\\\u0560
         \\\u0588\\\u058B-\\\u058C\\\u0590\\\u05C8-\\\u05CF\\\u05EB-\\\u05EF\\\u05F5-\\\u05FF\\\u061C-\\\u061D\\\u070E\\\u074B-\\\u074C\\\u07B2-\\\u07BF
         \\\u07FB-\\\u07FF\\\u082E-\\\u082F\\\u083F\\\u085C-\\\u085D\\\u085F-\\\u089F\\\u08B5\\\u08BE-\\\u08D3\\\u0984\\\u098D-\\\u098E\\\u0991-\\\u0992
         \\\u09A9\\\u09B1\\\u09B3-\\\u09B5\\\u09BA-\\\u09BB\\\u09C5-\\\u09C6\\\u09C9-\\\u09CA\\\u09CF-\\\u09D6\\\u09D8-\\\u09DB\\\u09DE\\\u09E4-\\\u09E5
         \\\u09FC-\\\u0A00\\\u0A04\\\u0A0B-\\\u0A0E\\\u0A11-\\\u0A12\\\u0A29\\\u0A31\\\u0A34\\\u0A37\\\u0A3A-\\\u0A3B\\\u0A3D\\\u0A43-\\\u0A46
         \\\u0A49-\\\u0A4A\\\u0A4E-\\\u0A50\\\u0A52-\\\u0A58\\\u0A5D\\\u0A5F-\\\u0A65\\\u0A76-\\\u0A80\\\u0A84\\\u0A8E\\\u0A92\\\u0AA9\\\u0AB1\\\u0AB4
         \\\u0ABA-\\\u0ABB\\\u0AC6\\\u0ACA\\\u0ACE-\\\u0ACF\\\u0AD1-\\\u0ADF\\\u0AE4-\\\u0AE5\\\u0AF2-\\\u0AF8\\\u0AFA-\\\u0B00\\\u0B04\\\u0B0D-\\\u0B0E
         \\\u0B11-\\\u0B12\\\u0B29\\\u0B31\\\u0B34\\\u0B3A-\\\u0B3B\\\u0B45-\\\u0B46\\\u0B49-\\\u0B4A\\\u0B4E-\\\u0B55\\\u0B58-\\\u0B5B\\\u0B5E
         \\\u0B64-\\\u0B65\\\u0B78-\\\u0B81\\\u0B84\\\u0B8B-\\\u0B8D\\\u0B91\\\u0B96-\\\u0B98\\\u0B9B\\\u0B9D\\\u0BA0-\\\u0BA2\\\u0BA5-\\\u0BA7
         \\\u0BAB-\\\u0BAD\\\u0BBA-\\\u0BBD\\\u0BC3-\\\u0BC5\\\u0BC9\\\u0BCE-\\\u0BCF\\\u0BD1-\\\u0BD6\\\u0BD8-\\\u0BE5\\\u0BFB-\\\u0BFF\\\u0C04\\\u0C0D
         \\\u0C11\\\u0C29\\\u0C3A-\\\u0C3C\\\u0C45\\\u0C49\\\u0C4E-\\\u0C54\\\u0C57\\\u0C5B-\\\u0C5F\\\u0C64-\\\u0C65\\\u0C70-\\\u0C77\\\u0C84\\\u0C8D
         \\\u0C91\\\u0CA9\\\u0CB4\\\u0CBA-\\\u0CBB\\\u0CC5\\\u0CC9\\\u0CCE-\\\u0CD4\\\u0CD7-\\\u0CDD\\\u0CDF\\\u0CE4-\\\u0CE5\\\u0CF0\\\u0CF3-\\\u0D00
         \\\u0D04\\\u0D0D\\\u0D11\\\u0D3B-\\\u0D3C\\\u0D45\\\u0D49\\\u0D50-\\\u0D53\\\u0D64-\\\u0D65\\\u0D80-\\\u0D81\\\u0D84\\\u0D97-\\\u0D99\\\u0DB2
         \\\u0DBC\\\u0DBE-\\\u0DBF\\\u0DC7-\\\u0DC9\\\u0DCB-\\\u0DCE\\\u0DD5\\\u0DD7\\\u0DE0-\\\u0DE5\\\u0DF0-\\\u0DF1\\\u0DF5-\\\u0E00\\\u0E3B-\\\u0E3E
         \\\u0E5C-\\\u0E80\\\u0E83\\\u0E85-\\\u0E86\\\u0E89\\\u0E8B-\\\u0E8C\\\u0E8E-\\\u0E93\\\u0E98\\\u0EA0\\\u0EA4\\\u0EA6\\\u0EA8-\\\u0EA9\\\u0EAC
         \\\u0EBA\\\u0EBE-\\\u0EBF\\\u0EC5\\\u0EC7\\\u0ECE-\\\u0ECF\\\u0EDA-\\\u0EDB\\\u0EE0-\\\u0EFF\\\u0F48\\\u0F6D-\\\u0F70\\\u0F98\\\u0FBD\\\u0FCD
         \\\u0FDB-\\\u0FFF\\\u10C6\\\u10C8-\\\u10CC\\\u10CE-\\\u10CF\\\u1249\\\u124E-\\\u124F\\\u1257\\\u1259\\\u125E-\\\u125F\\\u1289\\\u128E-\\\u128F
         \\\u12B1\\\u12B6-\\\u12B7\\\u12BF\\\u12C1\\\u12C6-\\\u12C7\\\u12D7\\\u1311\\\u1316-\\\u1317\\\u135B-\\\u135C\\\u137D-\\\u137F\\\u139A-\\\u139F
         \\\u13F6-\\\u13F7\\\u13FE-\\\u13FF\\\u169D-\\\u169F\\\u16F9-\\\u16FF\\\u170D\\\u1715-\\\u171F\\\u1737-\\\u173F\\\u1754-\\\u175F\\\u176D\\\u1771
         \\\u1774-\\\u177F\\\u17DE-\\\u17DF\\\u17EA-\\\u17EF\\\u17FA-\\\u17FF\\\u180F\\\u181A-\\\u181F\\\u1878-\\\u187F\\\u18AB-\\\u18AF\\\u18F6-\\\u18FF
         \\\u191F\\\u192C-\\\u192F\\\u193C-\\\u193F\\\u1941-\\\u1943\\\u196E-\\\u196F\\\u1975-\\\u197F\\\u19AC-\\\u19AF\\\u19CA-\\\u19CF\\\u19DB-\\\u19DD
         \\\u1A1C-\\\u1A1D\\\u1A5F\\\u1A7D-\\\u1A7E\\\u1A8A-\\\u1A8F\\\u1A9A-\\\u1A9F\\\u1AAE-\\\u1AAF\\\u1ABF-\\\u1AFF\\\u1B4C-\\\u1B4F\\\u1B7D-\\\u1B7F
         \\\u1BF4-\\\u1BFB\\\u1C38-\\\u1C3A\\\u1C4A-\\\u1C4C\\\u1C89-\\\u1CBF\\\u1CC8-\\\u1CCF\\\u1CF7\\\u1CFA-\\\u1CFF\\\u1DF6-\\\u1DFA\\\u1F16-\\\u1F17
         \\\u1F1E-\\\u1F1F\\\u1F46-\\\u1F47\\\u1F4E-\\\u1F4F\\\u1F58\\\u1F5A\\\u1F5C\\\u1F5E\\\u1F7E-\\\u1F7F\\\u1FB5\\\u1FC5\\\u1FD4-\\\u1FD5\\\u1FDC
         \\\u1FF0-\\\u1FF1\\\u1FF5\\\u1FFF\\\u200E-\\\u200F\\\u2028-\\\u202E\\\u2065-\\\u2069\\\u2072-\\\u2073\\\u208F\\\u209D-\\\u209F\\\u20BF-\\\u20CF
         \\\u20F1-\\\u20FF\\\u218C-\\\u218F\\\u23FF\\\u2427-\\\u243F\\\u244B-\\\u245F\\\u2B74-\\\u2B75\\\u2B96-\\\u2B97\\\u2BBA-\\\u2BBC\\\u2BC9
         \\\u2BD2-\\\u2BEB\\\u2BF0-\\\u2BFF\\\u2C2F\\\u2C5F\\\u2CF4-\\\u2CF8\\\u2D26\\\u2D28-\\\u2D2C\\\u2D2E-\\\u2D2F\\\u2D68-\\\u2D6E\\\u2D71-\\\u2D7E
         \\\u2D97-\\\u2D9F\\\u2DA7\\\u2DAF\\\u2DB7\\\u2DBF\\\u2DC7\\\u2DCF\\\u2DD7\\\u2DDF\\\u2E45-\\\u2E7F\\\u2E9A\\\u2EF4-\\\u2EFF\\\u2FD6-\\\u2FEF
         \\\u2FFC-\\\u2FFF\\\u3040\\\u3097-\\\u3098\\\u3100-\\\u3104\\\u312E-\\\u3130\\\u318F\\\u31BB-\\\u31BF\\\u31E4-\\\u31EF\\\u321F\\\u32FF
         \\\u4DB6-\\\u4DBF\\\u9FD6-\\\u9FFF\\\uA48D-\\\uA48F\\\uA4C7-\\\uA4CF\\\uA62C-\\\uA63F\\\uA6F8-\\\uA6FF\\\uA7AF\\\uA7B8-\\\uA7F6\\\uA82C-\\\uA82F
         \\\uA83A-\\\uA83F\\\uA878-\\\uA87F\\\uA8C6-\\\uA8CD\\\uA8DA-\\\uA8DF\\\uA8FE-\\\uA8FF\\\uA954-\\\uA95E\\\uA97D-\\\uA97F\\\uA9CE\\\uA9DA-\\\uA9DD
         \\\uA9FF\\\uAA37-\\\uAA3F\\\uAA4E-\\\uAA4F\\\uAA5A-\\\uAA5B\\\uAAC3-\\\uAADA\\\uAAF7-\\\uAB00\\\uAB07-\\\uAB08\\\uAB0F-\\\uAB10\\\uAB17-\\\uAB1F
         \\\uAB27\\\uAB2F\\\uAB66-\\\uAB6F\\\uABEE-\\\uABEF\\\uABFA-\\\uABFF\\\uD7A4-\\\uD7AF\\\uD7C7-\\\uD7CA\\\uD7FC-\\\uF8FF\\\uFA6E-\\\uFA6F
         \\\uFADA-\\\uFAFF\\\uFB07-\\\uFB12\\\uFB18-\\\uFB1C\\\uFB37\\\uFB3D\\\uFB3F\\\uFB42\\\uFB45\\\uFBC2-\\\uFBD2\\\uFD40-\\\uFD4F\\\uFD90-\\\uFD91
         \\\uFDC8-\\\uFDEF\\\uFDFE-\\\uFDFF\\\uFE1A-\\\uFE1F\\\uFE53\\\uFE67\\\uFE6C-\\\uFE6F\\\uFE75\\\uFEFD-\\\uFF00\\\uFFBF-\\\uFFC1\\\uFFC8-\\\uFFC9
         \\\uFFD0-\\\uFFD1\\\uFFD8-\\\uFFD9\\\uFFDD-\\\uFFDF\\\uFFE7\\\uFFEF-\\\uFFF8\\\uFFFE-\\\uFFFF\\\U0001000C\\\U00010027\\\U0001003B\\\U0001003E
         \\\U0001004E-\\\U0001004F\\\U0001005E-\\\U0001007F\\\U000100FB-\\\U000100FF\\\U00010103-\\\U00010106\\\U00010134-\\\U00010136\\\U0001018F
         \\\U0001019C-\\\U0001019F\\\U000101A1-\\\U000101CF\\\U000101FE-\\\U0001027F\\\U0001029D-\\\U0001029F\\\U000102D1-\\\U000102DF
         \\\U000102FC-\\\U000102FF\\\U00010324-\\\U0001032F\\\U0001034B-\\\U0001034F\\\U0001037B-\\\U0001037F\\\U0001039E\\\U000103C4-\\\U000103C7
         \\\U000103D6-\\\U000103FF\\\U0001049E-\\\U0001049F\\\U000104AA-\\\U000104AF\\\U000104D4-\\\U000104D7\\\U000104FC-\\\U000104FF
         \\\U00010528-\\\U0001052F\\\U00010564-\\\U0001056E\\\U00010570-\\\U000105FF\\\U00010737-\\\U0001073F\\\U00010756-\\\U0001075F
         \\\U00010768-\\\U000107FF\\\U00010806-\\\U00010807\\\U00010809\\\U00010836\\\U00010839-\\\U0001083B\\\U0001083D-\\\U0001083E\\\U00010856
         \\\U0001089F-\\\U000108A6\\\U000108B0-\\\U000108DF\\\U000108F3\\\U000108F6-\\\U000108FA\\\U0001091C-\\\U0001091E\\\U0001093A-\\\U0001093E
         \\\U00010940-\\\U0001097F\\\U000109B8-\\\U000109BB\\\U000109D0-\\\U000109D1\\\U00010A04\\\U00010A07-\\\U00010A0B\\\U00010A14\\\U00010A18
         \\\U00010A34-\\\U00010A37\\\U00010A3B-\\\U00010A3E\\\U00010A48-\\\U00010A4F\\\U00010A59-\\\U00010A5F\\\U00010AA0-\\\U00010ABF
         \\\U00010AE7-\\\U00010AEA\\\U00010AF7-\\\U00010AFF\\\U00010B36-\\\U00010B38\\\U00010B56-\\\U00010B57\\\U00010B73-\\\U00010B77
         \\\U00010B92-\\\U00010B98\\\U00010B9D-\\\U00010BA8\\\U00010BB0-\\\U00010BFF\\\U00010C49-\\\U00010C7F\\\U00010CB3-\\\U00010CBF
         \\\U00010CF3-\\\U00010CF9\\\U00010D00-\\\U00010E5F\\\U00010E7F-\\\U00010FFF\\\U0001104E-\\\U00011051\\\U00011070-\\\U0001107E
         \\\U000110C2-\\\U000110CF\\\U000110E9-\\\U000110EF\\\U000110FA-\\\U000110FF\\\U00011135\\\U00011144-\\\U0001114F\\\U00011177-\\\U0001117F
         \\\U000111CE-\\\U000111CF\\\U000111E0\\\U000111F5-\\\U000111FF\\\U00011212\\\U0001123F-\\\U0001127F\\\U00011287\\\U00011289\\\U0001128E\\\U0001129E
         \\\U000112AA-\\\U000112AF\\\U000112EB-\\\U000112EF\\\U000112FA-\\\U000112FF\\\U00011304\\\U0001130D-\\\U0001130E\\\U00011311-\\\U00011312
         \\\U00011329\\\U00011331\\\U00011334\\\U0001133A-\\\U0001133B\\\U00011345-\\\U00011346\\\U00011349-\\\U0001134A\\\U0001134E-\\\U0001134F
         \\\U00011351-\\\U00011356\\\U00011358-\\\U0001135C\\\U00011364-\\\U00011365\\\U0001136D-\\\U0001136F\\\U00011375-\\\U000113FF\\\U0001145A
         \\\U0001145C\\\U0001145E-\\\U0001147F\\\U000114C8-\\\U000114CF\\\U000114DA-\\\U0001157F\\\U000115B6-\\\U000115B7\\\U000115DE-\\\U000115FF
         \\\U00011645-\\\U0001164F\\\U0001165A-\\\U0001165F\\\U0001166D-\\\U0001167F\\\U000116B8-\\\U000116BF\\\U000116CA-\\\U000116FF
         \\\U0001171A-\\\U0001171C\\\U0001172C-\\\U0001172F\\\U00011740-\\\U0001189F\\\U000118F3-\\\U000118FE\\\U00011900-\\\U00011ABF
         \\\U00011AF9-\\\U00011BFF\\\U00011C09\\\U00011C37\\\U00011C46-\\\U00011C4F\\\U00011C6D-\\\U00011C6F\\\U00011C90-\\\U00011C91\\\U00011CA8
         \\\U00011CB7-\\\U00011FFF\\\U0001239A-\\\U000123FF\\\U0001246F\\\U00012475-\\\U0001247F\\\U00012544-\\\U00012FFF\\\U0001342F-\\\U000143FF
         \\\U00014647-\\\U000167FF\\\U00016A39-\\\U00016A3F\\\U00016A5F\\\U00016A6A-\\\U00016A6D\\\U00016A70-\\\U00016ACF\\\U00016AEE-\\\U00016AEF
         \\\U00016AF6-\\\U00016AFF\\\U00016B46-\\\U00016B4F\\\U00016B5A\\\U00016B62\\\U00016B78-\\\U00016B7C\\\U00016B90-\\\U00016EFF
         \\\U00016F45-\\\U00016F4F\\\U00016F7F-\\\U00016F8E\\\U00016FA0-\\\U00016FDF\\\U00016FE1-\\\U00016FFF\\\U000187ED-\\\U000187FF
         \\\U00018AF3-\\\U0001AFFF\\\U0001B002-\\\U0001BBFF\\\U0001BC6B-\\\U0001BC6F\\\U0001BC7D-\\\U0001BC7F\\\U0001BC89-\\\U0001BC8F
         \\\U0001BC9A-\\\U0001BC9B\\\U0001BCA4-\\\U0001CFFF\\\U0001D0F6-\\\U0001D0FF\\\U0001D127-\\\U0001D128\\\U0001D1E9-\\\U0001D1FF
         \\\U0001D246-\\\U0001D2FF\\\U0001D357-\\\U0001D35F\\\U0001D372-\\\U0001D3FF\\\U0001D455\\\U0001D49D\\\U0001D4A0-\\\U0001D4A1
         \\\U0001D4A3-\\\U0001D4A4\\\U0001D4A7-\\\U0001D4A8\\\U0001D4AD\\\U0001D4BA\\\U0001D4BC\\\U0001D4C4\\\U0001D506\\\U0001D50B-\\\U0001D50C\\\U0001D515
         \\\U0001D51D\\\U0001D53A\\\U0001D53F\\\U0001D545\\\U0001D547-\\\U0001D549\\\U0001D551\\\U0001D6A6-\\\U0001D6A7\\\U0001D7CC-\\\U0001D7CD
         \\\U0001DA8C-\\\U0001DA9A\\\U0001DAA0\\\U0001DAB0-\\\U0001DFFF\\\U0001E007\\\U0001E019-\\\U0001E01A\\\U0001E022\\\U0001E025\\\U0001E02B-\\\U0001E7FF
         \\\U0001E8C5-\\\U0001E8C6\\\U0001E8D7-\\\U0001E8FF\\\U0001E94B-\\\U0001E94F\\\U0001E95A-\\\U0001E95D\\\U0001E960-\\\U0001EDFF\\\U0001EE04
         \\\U0001EE20\\\U0001EE23\\\U0001EE25-\\\U0001EE26\\\U0001EE28\\\U0001EE33\\\U0001EE38\\\U0001EE3A\\\U0001EE3C-\\\U0001EE41\\\U0001EE43-\\\U0001EE46
         \\\U0001EE48\\\U0001EE4A\\\U0001EE4C\\\U0001EE50\\\U0001EE53\\\U0001EE55-\\\U0001EE56\\\U0001EE58\\\U0001EE5A\\\U0001EE5C\\\U0001EE5E\\\U0001EE60
         \\\U0001EE63\\\U0001EE65-\\\U0001EE66\\\U0001EE6B\\\U0001EE73\\\U0001EE78\\\U0001EE7D\\\U0001EE7F\\\U0001EE8A\\\U0001EE9C-\\\U0001EEA0\\\U0001EEA4
         \\\U0001EEAA\\\U0001EEBC-\\\U0001EEEF\\\U0001EEF2-\\\U0001EFFF\\\U0001F02C-\\\U0001F02F\\\U0001F094-\\\U0001F09F\\\U0001F0AF-\\\U0001F0B0
         \\\U0001F0C0\\\U0001F0D0\\\U0001F0F6-\\\U0001F0FF\\\U0001F10D-\\\U0001F10F\\\U0001F12F\\\U0001F16C-\\\U0001F16F\\\U0001F1AD-\\\U0001F1E5
         \\\U0001F203-\\\U0001F20F\\\U0001F23C-\\\U0001F23F\\\U0001F249-\\\U0001F24F\\\U0001F252-\\\U0001F2FF\\\U0001F6D3-\\\U0001F6DF
         \\\U0001F6ED-\\\U0001F6EF\\\U0001F6F7-\\\U0001F6FF\\\U0001F774-\\\U0001F77F\\\U0001F7D5-\\\U0001F7FF\\\U0001F80C-\\\U0001F80F
         \\\U0001F848-\\\U0001F84F\\\U0001F85A-\\\U0001F85F\\\U0001F888-\\\U0001F88F\\\U0001F8AE-\\\U0001F90F\\\U0001F91F\\\U0001F928-\\\U0001F92F
         \\\U0001F931-\\\U0001F932\\\U0001F93F\\\U0001F94C-\\\U0001F94F\\\U0001F95F-\\\U0001F97F\\\U0001F992-\\\U0001F9BF\\\U0001F9C1-\\\U0001FFFF
         \\\U0002A6D7-\\\U0002A6FF\\\U0002B735-\\\U0002B73F\\\U0002B81E-\\\U0002B81F\\\U0002CEA2-\\\U0002F7FF\\\U0002FA1E-\\\U000E0000
         \\\U000E0002-\\\U000E001F\\\U000E0080-\\\U000E00FF\\\U000E01F0-\\\U0010FFFF]
        '''.replace('\x20', '').replace('\n', '')




# Subset of default invalid literals that cannot be disabled.
if sys.maxunicode == 0xFFFF:
    INVALID_LITERALS_LESS_PRIVATE_USE_UNASSIGNED_RESERVED = '''
        {UNPAIRED_SURROGATE}
        |
        [\\\u0000-\\\u0008\\\u000B-\\\u001F\\\u007F-\\\u009F\\\u061C\\\u200E-\\\u200F\\\u2028-\\\u202E\\\u2066-\\\u2069\\\uFDD0-\\\uFDEF\\\uFEFF
         \\\uFFFE-\\\uFFFF]
        |
        \\\uD83F[\\\uDFFE-\\\uDFFF]|\\\uD87F[\\\uDFFE-\\\uDFFF]|\\\uD8BF[\\\uDFFE-\\\uDFFF]|\\\uD8FF[\\\uDFFE-\\\uDFFF]|\\\uD93F[\\\uDFFE-\\\uDFFF]|
        \\\uD97F[\\\uDFFE-\\\uDFFF]|\\\uD9BF[\\\uDFFE-\\\uDFFF]|\\\uD9FF[\\\uDFFE-\\\uDFFF]|\\\uDA3F[\\\uDFFE-\\\uDFFF]|\\\uDA7F[\\\uDFFE-\\\uDFFF]|
        \\\uDABF[\\\uDFFE-\\\uDFFF]|\\\uDAFF[\\\uDFFE-\\\uDFFF]|\\\uDB3F[\\\uDFFE-\\\uDFFF]|\\\uDB7F[\\\uDFFE-\\\uDFFF]|\\\uDBBF[\\\uDFFE-\\\uDFFF]|
        \\\uDBFF[\\\uDFFE-\\\uDFFF]
        '''.replace('\x20', '').replace('\n', '').replace('{UNPAIRED_SURROGATE}', UNPAIRED_SURROGATE)
else:
    INVALID_LITERALS_LESS_PRIVATE_USE_UNASSIGNED_RESERVED = '''
        [\\\u0000-\\\u0008\\\u000B-\\\u001F\\\u007F-\\\u009F\\\u061C\\\u200E-\\\u200F\\\u2028-\\\u202E\\\u2066-\\\u2069\\\uD800-\\\uDFFF\\\uFDD0-\\\uFDEF
         \\\uFEFF\\\uFFFE-\\\uFFFF\\\U0001FFFE-\\\U0001FFFF\\\U0002FFFE-\\\U0002FFFF\\\U0003FFFE-\\\U0003FFFF\\\U0004FFFE-\\\U0004FFFF
         \\\U0005FFFE-\\\U0005FFFF\\\U0006FFFE-\\\U0006FFFF\\\U0007FFFE-\\\U0007FFFF\\\U0008FFFE-\\\U0008FFFF\\\U0009FFFE-\\\U0009FFFF
         \\\U000AFFFE-\\\U000AFFFF\\\U000BFFFE-\\\U000BFFFF\\\U000CFFFE-\\\U000CFFFF\\\U000DFFFE-\\\U000DFFFF\\\U000EFFFE-\\\U000EFFFF
         \\\U000FFFFE-\\\U000FFFFF\\\U0010FFFE-\\\U0010FFFF]
        '''.replace('\x20', '').replace('\n', '')


# Private use
if sys.maxunicode == 0xFFFF:
    PRIVATE_USE = '''
        [\\\uE000-\\\uF8FF]
        |
        [\\\uDB80-\\\uDBBE][\\\uDC00-\\\uDFFF]|\\\uDBBF[\\\uDC00-\\\uDFFD]|[\\\uDBC0-\\\uDBFE][\\\uDC00-\\\uDFFF]|\\\uDBFF[\\\uDC00-\\\uDFFD]
        '''.replace('\x20', '').replace('\n', '')
else:
    PRIVATE_USE = '''
        [\\\uE000-\\\uF8FF\\\U000F0000-\\\U000FFFFD\\\U00100000-\\\U0010FFFD]
        '''.replace('\x20', '').replace('\n', '')


# Unassigned, not noncharacters
if sys.maxunicode == 0xFFFF:
    UNASSIGNED_RESERVED = '''
        [\\\u0378-\\\u0379\\\u0380-\\\u0383\\\u038B\\\u038D\\\u03A2\\\u0530\\\u0557-\\\u0558\\\u0560\\\u0588\\\u058B-\\\u058C\\\u0590\\\u05C8-\\\u05CF
         \\\u05EB-\\\u05EF\\\u05F5-\\\u05FF\\\u061D\\\u070E\\\u074B-\\\u074C\\\u07B2-\\\u07BF\\\u07FB-\\\u07FF\\\u082E-\\\u082F\\\u083F\\\u085C-\\\u085D
         \\\u085F-\\\u089F\\\u08B5\\\u08BE-\\\u08D3\\\u0984\\\u098D-\\\u098E\\\u0991-\\\u0992\\\u09A9\\\u09B1\\\u09B3-\\\u09B5\\\u09BA-\\\u09BB
         \\\u09C5-\\\u09C6\\\u09C9-\\\u09CA\\\u09CF-\\\u09D6\\\u09D8-\\\u09DB\\\u09DE\\\u09E4-\\\u09E5\\\u09FC-\\\u0A00\\\u0A04\\\u0A0B-\\\u0A0E
         \\\u0A11-\\\u0A12\\\u0A29\\\u0A31\\\u0A34\\\u0A37\\\u0A3A-\\\u0A3B\\\u0A3D\\\u0A43-\\\u0A46\\\u0A49-\\\u0A4A\\\u0A4E-\\\u0A50\\\u0A52-\\\u0A58
         \\\u0A5D\\\u0A5F-\\\u0A65\\\u0A76-\\\u0A80\\\u0A84\\\u0A8E\\\u0A92\\\u0AA9\\\u0AB1\\\u0AB4\\\u0ABA-\\\u0ABB\\\u0AC6\\\u0ACA\\\u0ACE-\\\u0ACF
         \\\u0AD1-\\\u0ADF\\\u0AE4-\\\u0AE5\\\u0AF2-\\\u0AF8\\\u0AFA-\\\u0B00\\\u0B04\\\u0B0D-\\\u0B0E\\\u0B11-\\\u0B12\\\u0B29\\\u0B31\\\u0B34
         \\\u0B3A-\\\u0B3B\\\u0B45-\\\u0B46\\\u0B49-\\\u0B4A\\\u0B4E-\\\u0B55\\\u0B58-\\\u0B5B\\\u0B5E\\\u0B64-\\\u0B65\\\u0B78-\\\u0B81\\\u0B84
         \\\u0B8B-\\\u0B8D\\\u0B91\\\u0B96-\\\u0B98\\\u0B9B\\\u0B9D\\\u0BA0-\\\u0BA2\\\u0BA5-\\\u0BA7\\\u0BAB-\\\u0BAD\\\u0BBA-\\\u0BBD\\\u0BC3-\\\u0BC5
         \\\u0BC9\\\u0BCE-\\\u0BCF\\\u0BD1-\\\u0BD6\\\u0BD8-\\\u0BE5\\\u0BFB-\\\u0BFF\\\u0C04\\\u0C0D\\\u0C11\\\u0C29\\\u0C3A-\\\u0C3C\\\u0C45\\\u0C49
         \\\u0C4E-\\\u0C54\\\u0C57\\\u0C5B-\\\u0C5F\\\u0C64-\\\u0C65\\\u0C70-\\\u0C77\\\u0C84\\\u0C8D\\\u0C91\\\u0CA9\\\u0CB4\\\u0CBA-\\\u0CBB\\\u0CC5
         \\\u0CC9\\\u0CCE-\\\u0CD4\\\u0CD7-\\\u0CDD\\\u0CDF\\\u0CE4-\\\u0CE5\\\u0CF0\\\u0CF3-\\\u0D00\\\u0D04\\\u0D0D\\\u0D11\\\u0D3B-\\\u0D3C\\\u0D45
         \\\u0D49\\\u0D50-\\\u0D53\\\u0D64-\\\u0D65\\\u0D80-\\\u0D81\\\u0D84\\\u0D97-\\\u0D99\\\u0DB2\\\u0DBC\\\u0DBE-\\\u0DBF\\\u0DC7-\\\u0DC9
         \\\u0DCB-\\\u0DCE\\\u0DD5\\\u0DD7\\\u0DE0-\\\u0DE5\\\u0DF0-\\\u0DF1\\\u0DF5-\\\u0E00\\\u0E3B-\\\u0E3E\\\u0E5C-\\\u0E80\\\u0E83\\\u0E85-\\\u0E86
         \\\u0E89\\\u0E8B-\\\u0E8C\\\u0E8E-\\\u0E93\\\u0E98\\\u0EA0\\\u0EA4\\\u0EA6\\\u0EA8-\\\u0EA9\\\u0EAC\\\u0EBA\\\u0EBE-\\\u0EBF\\\u0EC5\\\u0EC7
         \\\u0ECE-\\\u0ECF\\\u0EDA-\\\u0EDB\\\u0EE0-\\\u0EFF\\\u0F48\\\u0F6D-\\\u0F70\\\u0F98\\\u0FBD\\\u0FCD\\\u0FDB-\\\u0FFF\\\u10C6\\\u10C8-\\\u10CC
         \\\u10CE-\\\u10CF\\\u1249\\\u124E-\\\u124F\\\u1257\\\u1259\\\u125E-\\\u125F\\\u1289\\\u128E-\\\u128F\\\u12B1\\\u12B6-\\\u12B7\\\u12BF\\\u12C1
         \\\u12C6-\\\u12C7\\\u12D7\\\u1311\\\u1316-\\\u1317\\\u135B-\\\u135C\\\u137D-\\\u137F\\\u139A-\\\u139F\\\u13F6-\\\u13F7\\\u13FE-\\\u13FF
         \\\u169D-\\\u169F\\\u16F9-\\\u16FF\\\u170D\\\u1715-\\\u171F\\\u1737-\\\u173F\\\u1754-\\\u175F\\\u176D\\\u1771\\\u1774-\\\u177F\\\u17DE-\\\u17DF
         \\\u17EA-\\\u17EF\\\u17FA-\\\u17FF\\\u180F\\\u181A-\\\u181F\\\u1878-\\\u187F\\\u18AB-\\\u18AF\\\u18F6-\\\u18FF\\\u191F\\\u192C-\\\u192F
         \\\u193C-\\\u193F\\\u1941-\\\u1943\\\u196E-\\\u196F\\\u1975-\\\u197F\\\u19AC-\\\u19AF\\\u19CA-\\\u19CF\\\u19DB-\\\u19DD\\\u1A1C-\\\u1A1D\\\u1A5F
         \\\u1A7D-\\\u1A7E\\\u1A8A-\\\u1A8F\\\u1A9A-\\\u1A9F\\\u1AAE-\\\u1AAF\\\u1ABF-\\\u1AFF\\\u1B4C-\\\u1B4F\\\u1B7D-\\\u1B7F\\\u1BF4-\\\u1BFB
         \\\u1C38-\\\u1C3A\\\u1C4A-\\\u1C4C\\\u1C89-\\\u1CBF\\\u1CC8-\\\u1CCF\\\u1CF7\\\u1CFA-\\\u1CFF\\\u1DF6-\\\u1DFA\\\u1F16-\\\u1F17\\\u1F1E-\\\u1F1F
         \\\u1F46-\\\u1F47\\\u1F4E-\\\u1F4F\\\u1F58\\\u1F5A\\\u1F5C\\\u1F5E\\\u1F7E-\\\u1F7F\\\u1FB5\\\u1FC5\\\u1FD4-\\\u1FD5\\\u1FDC\\\u1FF0-\\\u1FF1
         \\\u1FF5\\\u1FFF\\\u2065\\\u2072-\\\u2073\\\u208F\\\u209D-\\\u209F\\\u20BF-\\\u20CF\\\u20F1-\\\u20FF\\\u218C-\\\u218F\\\u23FF\\\u2427-\\\u243F
         \\\u244B-\\\u245F\\\u2B74-\\\u2B75\\\u2B96-\\\u2B97\\\u2BBA-\\\u2BBC\\\u2BC9\\\u2BD2-\\\u2BEB\\\u2BF0-\\\u2BFF\\\u2C2F\\\u2C5F\\\u2CF4-\\\u2CF8
         \\\u2D26\\\u2D28-\\\u2D2C\\\u2D2E-\\\u2D2F\\\u2D68-\\\u2D6E\\\u2D71-\\\u2D7E\\\u2D97-\\\u2D9F\\\u2DA7\\\u2DAF\\\u2DB7\\\u2DBF\\\u2DC7\\\u2DCF
         \\\u2DD7\\\u2DDF\\\u2E45-\\\u2E7F\\\u2E9A\\\u2EF4-\\\u2EFF\\\u2FD6-\\\u2FEF\\\u2FFC-\\\u2FFF\\\u3040\\\u3097-\\\u3098\\\u3100-\\\u3104
         \\\u312E-\\\u3130\\\u318F\\\u31BB-\\\u31BF\\\u31E4-\\\u31EF\\\u321F\\\u32FF\\\u4DB6-\\\u4DBF\\\u9FD6-\\\u9FFF\\\uA48D-\\\uA48F\\\uA4C7-\\\uA4CF
         \\\uA62C-\\\uA63F\\\uA6F8-\\\uA6FF\\\uA7AF\\\uA7B8-\\\uA7F6\\\uA82C-\\\uA82F\\\uA83A-\\\uA83F\\\uA878-\\\uA87F\\\uA8C6-\\\uA8CD\\\uA8DA-\\\uA8DF
         \\\uA8FE-\\\uA8FF\\\uA954-\\\uA95E\\\uA97D-\\\uA97F\\\uA9CE\\\uA9DA-\\\uA9DD\\\uA9FF\\\uAA37-\\\uAA3F\\\uAA4E-\\\uAA4F\\\uAA5A-\\\uAA5B
         \\\uAAC3-\\\uAADA\\\uAAF7-\\\uAB00\\\uAB07-\\\uAB08\\\uAB0F-\\\uAB10\\\uAB17-\\\uAB1F\\\uAB27\\\uAB2F\\\uAB66-\\\uAB6F\\\uABEE-\\\uABEF
         \\\uABFA-\\\uABFF\\\uD7A4-\\\uD7AF\\\uD7C7-\\\uD7CA\\\uD7FC-\\\uD7FF\\\uFA6E-\\\uFA6F\\\uFADA-\\\uFAFF\\\uFB07-\\\uFB12\\\uFB18-\\\uFB1C\\\uFB37
         \\\uFB3D\\\uFB3F\\\uFB42\\\uFB45\\\uFBC2-\\\uFBD2\\\uFD40-\\\uFD4F\\\uFD90-\\\uFD91\\\uFDC8-\\\uFDCF\\\uFDFE-\\\uFDFF\\\uFE1A-\\\uFE1F\\\uFE53
         \\\uFE67\\\uFE6C-\\\uFE6F\\\uFE75\\\uFEFD-\\\uFEFE\\\uFF00\\\uFFBF-\\\uFFC1\\\uFFC8-\\\uFFC9\\\uFFD0-\\\uFFD1\\\uFFD8-\\\uFFD9\\\uFFDD-\\\uFFDF
         \\\uFFE7\\\uFFEF-\\\uFFF8]
        |
        \\\uD800\\\uDC0C|\\\uD800\\\uDC27|\\\uD800\\\uDC3B|\\\uD800\\\uDC3E|\\\uD800[\\\uDC4E-\\\uDC4F]|\\\uD800[\\\uDC5E-\\\uDC7F]|
        \\\uD800[\\\uDCFB-\\\uDCFF]|\\\uD800[\\\uDD03-\\\uDD06]|\\\uD800[\\\uDD34-\\\uDD36]|\\\uD800\\\uDD8F|\\\uD800[\\\uDD9C-\\\uDD9F]|
        \\\uD800[\\\uDDA1-\\\uDDCF]|\\\uD800[\\\uDDFE-\\\uDE7F]|\\\uD800[\\\uDE9D-\\\uDE9F]|\\\uD800[\\\uDED1-\\\uDEDF]|\\\uD800[\\\uDEFC-\\\uDEFF]|
        \\\uD800[\\\uDF24-\\\uDF2F]|\\\uD800[\\\uDF4B-\\\uDF4F]|\\\uD800[\\\uDF7B-\\\uDF7F]|\\\uD800\\\uDF9E|\\\uD800[\\\uDFC4-\\\uDFC7]|
        \\\uD800[\\\uDFD6-\\\uDFFF]|\\\uD801[\\\uDC9E-\\\uDC9F]|\\\uD801[\\\uDCAA-\\\uDCAF]|\\\uD801[\\\uDCD4-\\\uDCD7]|\\\uD801[\\\uDCFC-\\\uDCFF]|
        \\\uD801[\\\uDD28-\\\uDD2F]|\\\uD801[\\\uDD64-\\\uDD6E]|\\\uD801[\\\uDD70-\\\uDDFF]|\\\uD801[\\\uDF37-\\\uDF3F]|\\\uD801[\\\uDF56-\\\uDF5F]|
        \\\uD801[\\\uDF68-\\\uDFFF]|\\\uD802[\\\uDC06-\\\uDC07]|\\\uD802\\\uDC09|\\\uD802\\\uDC36|\\\uD802[\\\uDC39-\\\uDC3B]|\\\uD802[\\\uDC3D-\\\uDC3E]|
        \\\uD802\\\uDC56|\\\uD802[\\\uDC9F-\\\uDCA6]|\\\uD802[\\\uDCB0-\\\uDCDF]|\\\uD802\\\uDCF3|\\\uD802[\\\uDCF6-\\\uDCFA]|\\\uD802[\\\uDD1C-\\\uDD1E]|
        \\\uD802[\\\uDD3A-\\\uDD3E]|\\\uD802[\\\uDD40-\\\uDD7F]|\\\uD802[\\\uDDB8-\\\uDDBB]|\\\uD802[\\\uDDD0-\\\uDDD1]|\\\uD802\\\uDE04|
        \\\uD802[\\\uDE07-\\\uDE0B]|\\\uD802\\\uDE14|\\\uD802\\\uDE18|\\\uD802[\\\uDE34-\\\uDE37]|\\\uD802[\\\uDE3B-\\\uDE3E]|\\\uD802[\\\uDE48-\\\uDE4F]|
        \\\uD802[\\\uDE59-\\\uDE5F]|\\\uD802[\\\uDEA0-\\\uDEBF]|\\\uD802[\\\uDEE7-\\\uDEEA]|\\\uD802[\\\uDEF7-\\\uDEFF]|\\\uD802[\\\uDF36-\\\uDF38]|
        \\\uD802[\\\uDF56-\\\uDF57]|\\\uD802[\\\uDF73-\\\uDF77]|\\\uD802[\\\uDF92-\\\uDF98]|\\\uD802[\\\uDF9D-\\\uDFA8]|\\\uD802[\\\uDFB0-\\\uDFFF]|
        \\\uD803[\\\uDC49-\\\uDC7F]|\\\uD803[\\\uDCB3-\\\uDCBF]|\\\uD803[\\\uDCF3-\\\uDCF9]|\\\uD803[\\\uDD00-\\\uDE5F]|\\\uD803[\\\uDE7F-\\\uDFFF]|
        \\\uD804[\\\uDC4E-\\\uDC51]|\\\uD804[\\\uDC70-\\\uDC7E]|\\\uD804[\\\uDCC2-\\\uDCCF]|\\\uD804[\\\uDCE9-\\\uDCEF]|\\\uD804[\\\uDCFA-\\\uDCFF]|
        \\\uD804\\\uDD35|\\\uD804[\\\uDD44-\\\uDD4F]|\\\uD804[\\\uDD77-\\\uDD7F]|\\\uD804[\\\uDDCE-\\\uDDCF]|\\\uD804\\\uDDE0|\\\uD804[\\\uDDF5-\\\uDDFF]|
        \\\uD804\\\uDE12|\\\uD804[\\\uDE3F-\\\uDE7F]|\\\uD804\\\uDE87|\\\uD804\\\uDE89|\\\uD804\\\uDE8E|\\\uD804\\\uDE9E|\\\uD804[\\\uDEAA-\\\uDEAF]|
        \\\uD804[\\\uDEEB-\\\uDEEF]|\\\uD804[\\\uDEFA-\\\uDEFF]|\\\uD804\\\uDF04|\\\uD804[\\\uDF0D-\\\uDF0E]|\\\uD804[\\\uDF11-\\\uDF12]|\\\uD804\\\uDF29|
        \\\uD804\\\uDF31|\\\uD804\\\uDF34|\\\uD804[\\\uDF3A-\\\uDF3B]|\\\uD804[\\\uDF45-\\\uDF46]|\\\uD804[\\\uDF49-\\\uDF4A]|\\\uD804[\\\uDF4E-\\\uDF4F]|
        \\\uD804[\\\uDF51-\\\uDF56]|\\\uD804[\\\uDF58-\\\uDF5C]|\\\uD804[\\\uDF64-\\\uDF65]|\\\uD804[\\\uDF6D-\\\uDF6F]|\\\uD804[\\\uDF75-\\\uDFFF]|
        \\\uD805\\\uDC5A|\\\uD805\\\uDC5C|\\\uD805[\\\uDC5E-\\\uDC7F]|\\\uD805[\\\uDCC8-\\\uDCCF]|\\\uD805[\\\uDCDA-\\\uDD7F]|\\\uD805[\\\uDDB6-\\\uDDB7]|
        \\\uD805[\\\uDDDE-\\\uDDFF]|\\\uD805[\\\uDE45-\\\uDE4F]|\\\uD805[\\\uDE5A-\\\uDE5F]|\\\uD805[\\\uDE6D-\\\uDE7F]|\\\uD805[\\\uDEB8-\\\uDEBF]|
        \\\uD805[\\\uDECA-\\\uDEFF]|\\\uD805[\\\uDF1A-\\\uDF1C]|\\\uD805[\\\uDF2C-\\\uDF2F]|\\\uD805[\\\uDF40-\\\uDFFF]|\\\uD806[\\\uDC00-\\\uDC9F]|
        \\\uD806[\\\uDCF3-\\\uDCFE]|\\\uD806[\\\uDD00-\\\uDEBF]|\\\uD806[\\\uDEF9-\\\uDFFF]|\\\uD807\\\uDC09|\\\uD807\\\uDC37|\\\uD807[\\\uDC46-\\\uDC4F]|
        \\\uD807[\\\uDC6D-\\\uDC6F]|\\\uD807[\\\uDC90-\\\uDC91]|\\\uD807\\\uDCA8|\\\uD807[\\\uDCB7-\\\uDFFF]|\\\uD808[\\\uDF9A-\\\uDFFF]|\\\uD809\\\uDC6F|
        \\\uD809[\\\uDC75-\\\uDC7F]|\\\uD809[\\\uDD44-\\\uDFFF]|[\\\uD80A-\\\uD80B][\\\uDC00-\\\uDFFF]|\\\uD80D[\\\uDC2F-\\\uDFFF]|
        [\\\uD80E-\\\uD810][\\\uDC00-\\\uDFFF]|\\\uD811[\\\uDE47-\\\uDFFF]|[\\\uD812-\\\uD819][\\\uDC00-\\\uDFFF]|\\\uD81A[\\\uDE39-\\\uDE3F]|
        \\\uD81A\\\uDE5F|\\\uD81A[\\\uDE6A-\\\uDE6D]|\\\uD81A[\\\uDE70-\\\uDECF]|\\\uD81A[\\\uDEEE-\\\uDEEF]|\\\uD81A[\\\uDEF6-\\\uDEFF]|
        \\\uD81A[\\\uDF46-\\\uDF4F]|\\\uD81A\\\uDF5A|\\\uD81A\\\uDF62|\\\uD81A[\\\uDF78-\\\uDF7C]|\\\uD81A[\\\uDF90-\\\uDFFF]|\\\uD81B[\\\uDC00-\\\uDEFF]|
        \\\uD81B[\\\uDF45-\\\uDF4F]|\\\uD81B[\\\uDF7F-\\\uDF8E]|\\\uD81B[\\\uDFA0-\\\uDFDF]|\\\uD81B[\\\uDFE1-\\\uDFFF]|\\\uD821[\\\uDFED-\\\uDFFF]|
        \\\uD822[\\\uDEF3-\\\uDFFF]|[\\\uD823-\\\uD82B][\\\uDC00-\\\uDFFF]|\\\uD82C[\\\uDC02-\\\uDFFF]|[\\\uD82D-\\\uD82E][\\\uDC00-\\\uDFFF]|
        \\\uD82F[\\\uDC6B-\\\uDC6F]|\\\uD82F[\\\uDC7D-\\\uDC7F]|\\\uD82F[\\\uDC89-\\\uDC8F]|\\\uD82F[\\\uDC9A-\\\uDC9B]|\\\uD82F[\\\uDCA4-\\\uDFFF]|
        [\\\uD830-\\\uD833][\\\uDC00-\\\uDFFF]|\\\uD834[\\\uDCF6-\\\uDCFF]|\\\uD834[\\\uDD27-\\\uDD28]|\\\uD834[\\\uDDE9-\\\uDDFF]|
        \\\uD834[\\\uDE46-\\\uDEFF]|\\\uD834[\\\uDF57-\\\uDF5F]|\\\uD834[\\\uDF72-\\\uDFFF]|\\\uD835\\\uDC55|\\\uD835\\\uDC9D|\\\uD835[\\\uDCA0-\\\uDCA1]|
        \\\uD835[\\\uDCA3-\\\uDCA4]|\\\uD835[\\\uDCA7-\\\uDCA8]|\\\uD835\\\uDCAD|\\\uD835\\\uDCBA|\\\uD835\\\uDCBC|\\\uD835\\\uDCC4|\\\uD835\\\uDD06|
        \\\uD835[\\\uDD0B-\\\uDD0C]|\\\uD835\\\uDD15|\\\uD835\\\uDD1D|\\\uD835\\\uDD3A|\\\uD835\\\uDD3F|\\\uD835\\\uDD45|\\\uD835[\\\uDD47-\\\uDD49]|
        \\\uD835\\\uDD51|\\\uD835[\\\uDEA6-\\\uDEA7]|\\\uD835[\\\uDFCC-\\\uDFCD]|\\\uD836[\\\uDE8C-\\\uDE9A]|\\\uD836\\\uDEA0|\\\uD836[\\\uDEB0-\\\uDFFF]|
        \\\uD837[\\\uDC00-\\\uDFFF]|\\\uD838\\\uDC07|\\\uD838[\\\uDC19-\\\uDC1A]|\\\uD838\\\uDC22|\\\uD838\\\uDC25|\\\uD838[\\\uDC2B-\\\uDFFF]|
        \\\uD839[\\\uDC00-\\\uDFFF]|\\\uD83A[\\\uDCC5-\\\uDCC6]|\\\uD83A[\\\uDCD7-\\\uDCFF]|\\\uD83A[\\\uDD4B-\\\uDD4F]|\\\uD83A[\\\uDD5A-\\\uDD5D]|
        \\\uD83A[\\\uDD60-\\\uDFFF]|\\\uD83B[\\\uDC00-\\\uDDFF]|\\\uD83B\\\uDE04|\\\uD83B\\\uDE20|\\\uD83B\\\uDE23|\\\uD83B[\\\uDE25-\\\uDE26]|
        \\\uD83B\\\uDE28|\\\uD83B\\\uDE33|\\\uD83B\\\uDE38|\\\uD83B\\\uDE3A|\\\uD83B[\\\uDE3C-\\\uDE41]|\\\uD83B[\\\uDE43-\\\uDE46]|\\\uD83B\\\uDE48|
        \\\uD83B\\\uDE4A|\\\uD83B\\\uDE4C|\\\uD83B\\\uDE50|\\\uD83B\\\uDE53|\\\uD83B[\\\uDE55-\\\uDE56]|\\\uD83B\\\uDE58|\\\uD83B\\\uDE5A|\\\uD83B\\\uDE5C|
        \\\uD83B\\\uDE5E|\\\uD83B\\\uDE60|\\\uD83B\\\uDE63|\\\uD83B[\\\uDE65-\\\uDE66]|\\\uD83B\\\uDE6B|\\\uD83B\\\uDE73|\\\uD83B\\\uDE78|\\\uD83B\\\uDE7D|
        \\\uD83B\\\uDE7F|\\\uD83B\\\uDE8A|\\\uD83B[\\\uDE9C-\\\uDEA0]|\\\uD83B\\\uDEA4|\\\uD83B\\\uDEAA|\\\uD83B[\\\uDEBC-\\\uDEEF]|
        \\\uD83B[\\\uDEF2-\\\uDFFF]|\\\uD83C[\\\uDC2C-\\\uDC2F]|\\\uD83C[\\\uDC94-\\\uDC9F]|\\\uD83C[\\\uDCAF-\\\uDCB0]|\\\uD83C\\\uDCC0|\\\uD83C\\\uDCD0|
        \\\uD83C[\\\uDCF6-\\\uDCFF]|\\\uD83C[\\\uDD0D-\\\uDD0F]|\\\uD83C\\\uDD2F|\\\uD83C[\\\uDD6C-\\\uDD6F]|\\\uD83C[\\\uDDAD-\\\uDDE5]|
        \\\uD83C[\\\uDE03-\\\uDE0F]|\\\uD83C[\\\uDE3C-\\\uDE3F]|\\\uD83C[\\\uDE49-\\\uDE4F]|\\\uD83C[\\\uDE52-\\\uDEFF]|\\\uD83D[\\\uDED3-\\\uDEDF]|
        \\\uD83D[\\\uDEED-\\\uDEEF]|\\\uD83D[\\\uDEF7-\\\uDEFF]|\\\uD83D[\\\uDF74-\\\uDF7F]|\\\uD83D[\\\uDFD5-\\\uDFFF]|\\\uD83E[\\\uDC0C-\\\uDC0F]|
        \\\uD83E[\\\uDC48-\\\uDC4F]|\\\uD83E[\\\uDC5A-\\\uDC5F]|\\\uD83E[\\\uDC88-\\\uDC8F]|\\\uD83E[\\\uDCAE-\\\uDD0F]|\\\uD83E\\\uDD1F|
        \\\uD83E[\\\uDD28-\\\uDD2F]|\\\uD83E[\\\uDD31-\\\uDD32]|\\\uD83E\\\uDD3F|\\\uD83E[\\\uDD4C-\\\uDD4F]|\\\uD83E[\\\uDD5F-\\\uDD7F]|
        \\\uD83E[\\\uDD92-\\\uDDBF]|\\\uD83E[\\\uDDC1-\\\uDFFF]|\\\uD83F[\\\uDC00-\\\uDFFD]|\\\uD869[\\\uDED7-\\\uDEFF]|\\\uD86D[\\\uDF35-\\\uDF3F]|
        \\\uD86E[\\\uDC1E-\\\uDC1F]|\\\uD873[\\\uDEA2-\\\uDFFF]|[\\\uD874-\\\uD87D][\\\uDC00-\\\uDFFF]|\\\uD87E[\\\uDE1E-\\\uDFFF]|
        \\\uD87F[\\\uDC00-\\\uDFFD]|[\\\uD880-\\\uD8BE][\\\uDC00-\\\uDFFF]|\\\uD8BF[\\\uDC00-\\\uDFFD]|[\\\uD8C0-\\\uD8FE][\\\uDC00-\\\uDFFF]|
        \\\uD8FF[\\\uDC00-\\\uDFFD]|[\\\uD900-\\\uD93E][\\\uDC00-\\\uDFFF]|\\\uD93F[\\\uDC00-\\\uDFFD]|[\\\uD940-\\\uD97E][\\\uDC00-\\\uDFFF]|
        \\\uD97F[\\\uDC00-\\\uDFFD]|[\\\uD980-\\\uD9BE][\\\uDC00-\\\uDFFF]|\\\uD9BF[\\\uDC00-\\\uDFFD]|[\\\uD9C0-\\\uD9FE][\\\uDC00-\\\uDFFF]|
        \\\uD9FF[\\\uDC00-\\\uDFFD]|[\\\uDA00-\\\uDA3E][\\\uDC00-\\\uDFFF]|\\\uDA3F[\\\uDC00-\\\uDFFD]|[\\\uDA40-\\\uDA7E][\\\uDC00-\\\uDFFF]|
        \\\uDA7F[\\\uDC00-\\\uDFFD]|[\\\uDA80-\\\uDABE][\\\uDC00-\\\uDFFF]|\\\uDABF[\\\uDC00-\\\uDFFD]|[\\\uDAC0-\\\uDAFE][\\\uDC00-\\\uDFFF]|
        \\\uDAFF[\\\uDC00-\\\uDFFD]|[\\\uDB00-\\\uDB3E][\\\uDC00-\\\uDFFF]|\\\uDB3F[\\\uDC00-\\\uDFFD]|\\\uDB40\\\uDC00|\\\uDB40[\\\uDC02-\\\uDC1F]|
        \\\uDB40[\\\uDC80-\\\uDCFF]|\\\uDB40[\\\uDDF0-\\\uDFFF]|[\\\uDB41-\\\uDB7E][\\\uDC00-\\\uDFFF]|\\\uDB7F[\\\uDC00-\\\uDFFD]
        '''.replace('\x20', '').replace('\n', '')
else:
    UNASSIGNED_RESERVED = '''
        [\\\u0378-\\\u0379\\\u0380-\\\u0383\\\u038B\\\u038D\\\u03A2\\\u0530\\\u0557-\\\u0558\\\u0560\\\u0588\\\u058B-\\\u058C\\\u0590\\\u05C8-\\\u05CF
         \\\u05EB-\\\u05EF\\\u05F5-\\\u05FF\\\u061D\\\u070E\\\u074B-\\\u074C\\\u07B2-\\\u07BF\\\u07FB-\\\u07FF\\\u082E-\\\u082F\\\u083F\\\u085C-\\\u085D
         \\\u085F-\\\u089F\\\u08B5\\\u08BE-\\\u08D3\\\u0984\\\u098D-\\\u098E\\\u0991-\\\u0992\\\u09A9\\\u09B1\\\u09B3-\\\u09B5\\\u09BA-\\\u09BB
         \\\u09C5-\\\u09C6\\\u09C9-\\\u09CA\\\u09CF-\\\u09D6\\\u09D8-\\\u09DB\\\u09DE\\\u09E4-\\\u09E5\\\u09FC-\\\u0A00\\\u0A04\\\u0A0B-\\\u0A0E
         \\\u0A11-\\\u0A12\\\u0A29\\\u0A31\\\u0A34\\\u0A37\\\u0A3A-\\\u0A3B\\\u0A3D\\\u0A43-\\\u0A46\\\u0A49-\\\u0A4A\\\u0A4E-\\\u0A50\\\u0A52-\\\u0A58
         \\\u0A5D\\\u0A5F-\\\u0A65\\\u0A76-\\\u0A80\\\u0A84\\\u0A8E\\\u0A92\\\u0AA9\\\u0AB1\\\u0AB4\\\u0ABA-\\\u0ABB\\\u0AC6\\\u0ACA\\\u0ACE-\\\u0ACF
         \\\u0AD1-\\\u0ADF\\\u0AE4-\\\u0AE5\\\u0AF2-\\\u0AF8\\\u0AFA-\\\u0B00\\\u0B04\\\u0B0D-\\\u0B0E\\\u0B11-\\\u0B12\\\u0B29\\\u0B31\\\u0B34
         \\\u0B3A-\\\u0B3B\\\u0B45-\\\u0B46\\\u0B49-\\\u0B4A\\\u0B4E-\\\u0B55\\\u0B58-\\\u0B5B\\\u0B5E\\\u0B64-\\\u0B65\\\u0B78-\\\u0B81\\\u0B84
         \\\u0B8B-\\\u0B8D\\\u0B91\\\u0B96-\\\u0B98\\\u0B9B\\\u0B9D\\\u0BA0-\\\u0BA2\\\u0BA5-\\\u0BA7\\\u0BAB-\\\u0BAD\\\u0BBA-\\\u0BBD\\\u0BC3-\\\u0BC5
         \\\u0BC9\\\u0BCE-\\\u0BCF\\\u0BD1-\\\u0BD6\\\u0BD8-\\\u0BE5\\\u0BFB-\\\u0BFF\\\u0C04\\\u0C0D\\\u0C11\\\u0C29\\\u0C3A-\\\u0C3C\\\u0C45\\\u0C49
         \\\u0C4E-\\\u0C54\\\u0C57\\\u0C5B-\\\u0C5F\\\u0C64-\\\u0C65\\\u0C70-\\\u0C77\\\u0C84\\\u0C8D\\\u0C91\\\u0CA9\\\u0CB4\\\u0CBA-\\\u0CBB\\\u0CC5
         \\\u0CC9\\\u0CCE-\\\u0CD4\\\u0CD7-\\\u0CDD\\\u0CDF\\\u0CE4-\\\u0CE5\\\u0CF0\\\u0CF3-\\\u0D00\\\u0D04\\\u0D0D\\\u0D11\\\u0D3B-\\\u0D3C\\\u0D45
         \\\u0D49\\\u0D50-\\\u0D53\\\u0D64-\\\u0D65\\\u0D80-\\\u0D81\\\u0D84\\\u0D97-\\\u0D99\\\u0DB2\\\u0DBC\\\u0DBE-\\\u0DBF\\\u0DC7-\\\u0DC9
         \\\u0DCB-\\\u0DCE\\\u0DD5\\\u0DD7\\\u0DE0-\\\u0DE5\\\u0DF0-\\\u0DF1\\\u0DF5-\\\u0E00\\\u0E3B-\\\u0E3E\\\u0E5C-\\\u0E80\\\u0E83\\\u0E85-\\\u0E86
         \\\u0E89\\\u0E8B-\\\u0E8C\\\u0E8E-\\\u0E93\\\u0E98\\\u0EA0\\\u0EA4\\\u0EA6\\\u0EA8-\\\u0EA9\\\u0EAC\\\u0EBA\\\u0EBE-\\\u0EBF\\\u0EC5\\\u0EC7
         \\\u0ECE-\\\u0ECF\\\u0EDA-\\\u0EDB\\\u0EE0-\\\u0EFF\\\u0F48\\\u0F6D-\\\u0F70\\\u0F98\\\u0FBD\\\u0FCD\\\u0FDB-\\\u0FFF\\\u10C6\\\u10C8-\\\u10CC
         \\\u10CE-\\\u10CF\\\u1249\\\u124E-\\\u124F\\\u1257\\\u1259\\\u125E-\\\u125F\\\u1289\\\u128E-\\\u128F\\\u12B1\\\u12B6-\\\u12B7\\\u12BF\\\u12C1
         \\\u12C6-\\\u12C7\\\u12D7\\\u1311\\\u1316-\\\u1317\\\u135B-\\\u135C\\\u137D-\\\u137F\\\u139A-\\\u139F\\\u13F6-\\\u13F7\\\u13FE-\\\u13FF
         \\\u169D-\\\u169F\\\u16F9-\\\u16FF\\\u170D\\\u1715-\\\u171F\\\u1737-\\\u173F\\\u1754-\\\u175F\\\u176D\\\u1771\\\u1774-\\\u177F\\\u17DE-\\\u17DF
         \\\u17EA-\\\u17EF\\\u17FA-\\\u17FF\\\u180F\\\u181A-\\\u181F\\\u1878-\\\u187F\\\u18AB-\\\u18AF\\\u18F6-\\\u18FF\\\u191F\\\u192C-\\\u192F
         \\\u193C-\\\u193F\\\u1941-\\\u1943\\\u196E-\\\u196F\\\u1975-\\\u197F\\\u19AC-\\\u19AF\\\u19CA-\\\u19CF\\\u19DB-\\\u19DD\\\u1A1C-\\\u1A1D\\\u1A5F
         \\\u1A7D-\\\u1A7E\\\u1A8A-\\\u1A8F\\\u1A9A-\\\u1A9F\\\u1AAE-\\\u1AAF\\\u1ABF-\\\u1AFF\\\u1B4C-\\\u1B4F\\\u1B7D-\\\u1B7F\\\u1BF4-\\\u1BFB
         \\\u1C38-\\\u1C3A\\\u1C4A-\\\u1C4C\\\u1C89-\\\u1CBF\\\u1CC8-\\\u1CCF\\\u1CF7\\\u1CFA-\\\u1CFF\\\u1DF6-\\\u1DFA\\\u1F16-\\\u1F17\\\u1F1E-\\\u1F1F
         \\\u1F46-\\\u1F47\\\u1F4E-\\\u1F4F\\\u1F58\\\u1F5A\\\u1F5C\\\u1F5E\\\u1F7E-\\\u1F7F\\\u1FB5\\\u1FC5\\\u1FD4-\\\u1FD5\\\u1FDC\\\u1FF0-\\\u1FF1
         \\\u1FF5\\\u1FFF\\\u2065\\\u2072-\\\u2073\\\u208F\\\u209D-\\\u209F\\\u20BF-\\\u20CF\\\u20F1-\\\u20FF\\\u218C-\\\u218F\\\u23FF\\\u2427-\\\u243F
         \\\u244B-\\\u245F\\\u2B74-\\\u2B75\\\u2B96-\\\u2B97\\\u2BBA-\\\u2BBC\\\u2BC9\\\u2BD2-\\\u2BEB\\\u2BF0-\\\u2BFF\\\u2C2F\\\u2C5F\\\u2CF4-\\\u2CF8
         \\\u2D26\\\u2D28-\\\u2D2C\\\u2D2E-\\\u2D2F\\\u2D68-\\\u2D6E\\\u2D71-\\\u2D7E\\\u2D97-\\\u2D9F\\\u2DA7\\\u2DAF\\\u2DB7\\\u2DBF\\\u2DC7\\\u2DCF
         \\\u2DD7\\\u2DDF\\\u2E45-\\\u2E7F\\\u2E9A\\\u2EF4-\\\u2EFF\\\u2FD6-\\\u2FEF\\\u2FFC-\\\u2FFF\\\u3040\\\u3097-\\\u3098\\\u3100-\\\u3104
         \\\u312E-\\\u3130\\\u318F\\\u31BB-\\\u31BF\\\u31E4-\\\u31EF\\\u321F\\\u32FF\\\u4DB6-\\\u4DBF\\\u9FD6-\\\u9FFF\\\uA48D-\\\uA48F\\\uA4C7-\\\uA4CF
         \\\uA62C-\\\uA63F\\\uA6F8-\\\uA6FF\\\uA7AF\\\uA7B8-\\\uA7F6\\\uA82C-\\\uA82F\\\uA83A-\\\uA83F\\\uA878-\\\uA87F\\\uA8C6-\\\uA8CD\\\uA8DA-\\\uA8DF
         \\\uA8FE-\\\uA8FF\\\uA954-\\\uA95E\\\uA97D-\\\uA97F\\\uA9CE\\\uA9DA-\\\uA9DD\\\uA9FF\\\uAA37-\\\uAA3F\\\uAA4E-\\\uAA4F\\\uAA5A-\\\uAA5B
         \\\uAAC3-\\\uAADA\\\uAAF7-\\\uAB00\\\uAB07-\\\uAB08\\\uAB0F-\\\uAB10\\\uAB17-\\\uAB1F\\\uAB27\\\uAB2F\\\uAB66-\\\uAB6F\\\uABEE-\\\uABEF
         \\\uABFA-\\\uABFF\\\uD7A4-\\\uD7AF\\\uD7C7-\\\uD7CA\\\uD7FC-\\\uD7FF\\\uFA6E-\\\uFA6F\\\uFADA-\\\uFAFF\\\uFB07-\\\uFB12\\\uFB18-\\\uFB1C\\\uFB37
         \\\uFB3D\\\uFB3F\\\uFB42\\\uFB45\\\uFBC2-\\\uFBD2\\\uFD40-\\\uFD4F\\\uFD90-\\\uFD91\\\uFDC8-\\\uFDCF\\\uFDFE-\\\uFDFF\\\uFE1A-\\\uFE1F\\\uFE53
         \\\uFE67\\\uFE6C-\\\uFE6F\\\uFE75\\\uFEFD-\\\uFEFE\\\uFF00\\\uFFBF-\\\uFFC1\\\uFFC8-\\\uFFC9\\\uFFD0-\\\uFFD1\\\uFFD8-\\\uFFD9\\\uFFDD-\\\uFFDF
         \\\uFFE7\\\uFFEF-\\\uFFF8\\\U0001000C\\\U00010027\\\U0001003B\\\U0001003E\\\U0001004E-\\\U0001004F\\\U0001005E-\\\U0001007F\\\U000100FB-\\\U000100FF
         \\\U00010103-\\\U00010106\\\U00010134-\\\U00010136\\\U0001018F\\\U0001019C-\\\U0001019F\\\U000101A1-\\\U000101CF\\\U000101FE-\\\U0001027F
         \\\U0001029D-\\\U0001029F\\\U000102D1-\\\U000102DF\\\U000102FC-\\\U000102FF\\\U00010324-\\\U0001032F\\\U0001034B-\\\U0001034F
         \\\U0001037B-\\\U0001037F\\\U0001039E\\\U000103C4-\\\U000103C7\\\U000103D6-\\\U000103FF\\\U0001049E-\\\U0001049F\\\U000104AA-\\\U000104AF
         \\\U000104D4-\\\U000104D7\\\U000104FC-\\\U000104FF\\\U00010528-\\\U0001052F\\\U00010564-\\\U0001056E\\\U00010570-\\\U000105FF
         \\\U00010737-\\\U0001073F\\\U00010756-\\\U0001075F\\\U00010768-\\\U000107FF\\\U00010806-\\\U00010807\\\U00010809\\\U00010836
         \\\U00010839-\\\U0001083B\\\U0001083D-\\\U0001083E\\\U00010856\\\U0001089F-\\\U000108A6\\\U000108B0-\\\U000108DF\\\U000108F3
         \\\U000108F6-\\\U000108FA\\\U0001091C-\\\U0001091E\\\U0001093A-\\\U0001093E\\\U00010940-\\\U0001097F\\\U000109B8-\\\U000109BB
         \\\U000109D0-\\\U000109D1\\\U00010A04\\\U00010A07-\\\U00010A0B\\\U00010A14\\\U00010A18\\\U00010A34-\\\U00010A37\\\U00010A3B-\\\U00010A3E
         \\\U00010A48-\\\U00010A4F\\\U00010A59-\\\U00010A5F\\\U00010AA0-\\\U00010ABF\\\U00010AE7-\\\U00010AEA\\\U00010AF7-\\\U00010AFF
         \\\U00010B36-\\\U00010B38\\\U00010B56-\\\U00010B57\\\U00010B73-\\\U00010B77\\\U00010B92-\\\U00010B98\\\U00010B9D-\\\U00010BA8
         \\\U00010BB0-\\\U00010BFF\\\U00010C49-\\\U00010C7F\\\U00010CB3-\\\U00010CBF\\\U00010CF3-\\\U00010CF9\\\U00010D00-\\\U00010E5F
         \\\U00010E7F-\\\U00010FFF\\\U0001104E-\\\U00011051\\\U00011070-\\\U0001107E\\\U000110C2-\\\U000110CF\\\U000110E9-\\\U000110EF
         \\\U000110FA-\\\U000110FF\\\U00011135\\\U00011144-\\\U0001114F\\\U00011177-\\\U0001117F\\\U000111CE-\\\U000111CF\\\U000111E0
         \\\U000111F5-\\\U000111FF\\\U00011212\\\U0001123F-\\\U0001127F\\\U00011287\\\U00011289\\\U0001128E\\\U0001129E\\\U000112AA-\\\U000112AF
         \\\U000112EB-\\\U000112EF\\\U000112FA-\\\U000112FF\\\U00011304\\\U0001130D-\\\U0001130E\\\U00011311-\\\U00011312\\\U00011329\\\U00011331\\\U00011334
         \\\U0001133A-\\\U0001133B\\\U00011345-\\\U00011346\\\U00011349-\\\U0001134A\\\U0001134E-\\\U0001134F\\\U00011351-\\\U00011356
         \\\U00011358-\\\U0001135C\\\U00011364-\\\U00011365\\\U0001136D-\\\U0001136F\\\U00011375-\\\U000113FF\\\U0001145A\\\U0001145C
         \\\U0001145E-\\\U0001147F\\\U000114C8-\\\U000114CF\\\U000114DA-\\\U0001157F\\\U000115B6-\\\U000115B7\\\U000115DE-\\\U000115FF
         \\\U00011645-\\\U0001164F\\\U0001165A-\\\U0001165F\\\U0001166D-\\\U0001167F\\\U000116B8-\\\U000116BF\\\U000116CA-\\\U000116FF
         \\\U0001171A-\\\U0001171C\\\U0001172C-\\\U0001172F\\\U00011740-\\\U0001189F\\\U000118F3-\\\U000118FE\\\U00011900-\\\U00011ABF
         \\\U00011AF9-\\\U00011BFF\\\U00011C09\\\U00011C37\\\U00011C46-\\\U00011C4F\\\U00011C6D-\\\U00011C6F\\\U00011C90-\\\U00011C91\\\U00011CA8
         \\\U00011CB7-\\\U00011FFF\\\U0001239A-\\\U000123FF\\\U0001246F\\\U00012475-\\\U0001247F\\\U00012544-\\\U00012FFF\\\U0001342F-\\\U000143FF
         \\\U00014647-\\\U000167FF\\\U00016A39-\\\U00016A3F\\\U00016A5F\\\U00016A6A-\\\U00016A6D\\\U00016A70-\\\U00016ACF\\\U00016AEE-\\\U00016AEF
         \\\U00016AF6-\\\U00016AFF\\\U00016B46-\\\U00016B4F\\\U00016B5A\\\U00016B62\\\U00016B78-\\\U00016B7C\\\U00016B90-\\\U00016EFF
         \\\U00016F45-\\\U00016F4F\\\U00016F7F-\\\U00016F8E\\\U00016FA0-\\\U00016FDF\\\U00016FE1-\\\U00016FFF\\\U000187ED-\\\U000187FF
         \\\U00018AF3-\\\U0001AFFF\\\U0001B002-\\\U0001BBFF\\\U0001BC6B-\\\U0001BC6F\\\U0001BC7D-\\\U0001BC7F\\\U0001BC89-\\\U0001BC8F
         \\\U0001BC9A-\\\U0001BC9B\\\U0001BCA4-\\\U0001CFFF\\\U0001D0F6-\\\U0001D0FF\\\U0001D127-\\\U0001D128\\\U0001D1E9-\\\U0001D1FF
         \\\U0001D246-\\\U0001D2FF\\\U0001D357-\\\U0001D35F\\\U0001D372-\\\U0001D3FF\\\U0001D455\\\U0001D49D\\\U0001D4A0-\\\U0001D4A1
         \\\U0001D4A3-\\\U0001D4A4\\\U0001D4A7-\\\U0001D4A8\\\U0001D4AD\\\U0001D4BA\\\U0001D4BC\\\U0001D4C4\\\U0001D506\\\U0001D50B-\\\U0001D50C\\\U0001D515
         \\\U0001D51D\\\U0001D53A\\\U0001D53F\\\U0001D545\\\U0001D547-\\\U0001D549\\\U0001D551\\\U0001D6A6-\\\U0001D6A7\\\U0001D7CC-\\\U0001D7CD
         \\\U0001DA8C-\\\U0001DA9A\\\U0001DAA0\\\U0001DAB0-\\\U0001DFFF\\\U0001E007\\\U0001E019-\\\U0001E01A\\\U0001E022\\\U0001E025\\\U0001E02B-\\\U0001E7FF
         \\\U0001E8C5-\\\U0001E8C6\\\U0001E8D7-\\\U0001E8FF\\\U0001E94B-\\\U0001E94F\\\U0001E95A-\\\U0001E95D\\\U0001E960-\\\U0001EDFF\\\U0001EE04
         \\\U0001EE20\\\U0001EE23\\\U0001EE25-\\\U0001EE26\\\U0001EE28\\\U0001EE33\\\U0001EE38\\\U0001EE3A\\\U0001EE3C-\\\U0001EE41\\\U0001EE43-\\\U0001EE46
         \\\U0001EE48\\\U0001EE4A\\\U0001EE4C\\\U0001EE50\\\U0001EE53\\\U0001EE55-\\\U0001EE56\\\U0001EE58\\\U0001EE5A\\\U0001EE5C\\\U0001EE5E\\\U0001EE60
         \\\U0001EE63\\\U0001EE65-\\\U0001EE66\\\U0001EE6B\\\U0001EE73\\\U0001EE78\\\U0001EE7D\\\U0001EE7F\\\U0001EE8A\\\U0001EE9C-\\\U0001EEA0\\\U0001EEA4
         \\\U0001EEAA\\\U0001EEBC-\\\U0001EEEF\\\U0001EEF2-\\\U0001EFFF\\\U0001F02C-\\\U0001F02F\\\U0001F094-\\\U0001F09F\\\U0001F0AF-\\\U0001F0B0
         \\\U0001F0C0\\\U0001F0D0\\\U0001F0F6-\\\U0001F0FF\\\U0001F10D-\\\U0001F10F\\\U0001F12F\\\U0001F16C-\\\U0001F16F\\\U0001F1AD-\\\U0001F1E5
         \\\U0001F203-\\\U0001F20F\\\U0001F23C-\\\U0001F23F\\\U0001F249-\\\U0001F24F\\\U0001F252-\\\U0001F2FF\\\U0001F6D3-\\\U0001F6DF
         \\\U0001F6ED-\\\U0001F6EF\\\U0001F6F7-\\\U0001F6FF\\\U0001F774-\\\U0001F77F\\\U0001F7D5-\\\U0001F7FF\\\U0001F80C-\\\U0001F80F
         \\\U0001F848-\\\U0001F84F\\\U0001F85A-\\\U0001F85F\\\U0001F888-\\\U0001F88F\\\U0001F8AE-\\\U0001F90F\\\U0001F91F\\\U0001F928-\\\U0001F92F
         \\\U0001F931-\\\U0001F932\\\U0001F93F\\\U0001F94C-\\\U0001F94F\\\U0001F95F-\\\U0001F97F\\\U0001F992-\\\U0001F9BF\\\U0001F9C1-\\\U0001FFFD
         \\\U0002A6D7-\\\U0002A6FF\\\U0002B735-\\\U0002B73F\\\U0002B81E-\\\U0002B81F\\\U0002CEA2-\\\U0002F7FF\\\U0002FA1E-\\\U0002FFFD
         \\\U00030000-\\\U0003FFFD\\\U00040000-\\\U0004FFFD\\\U00050000-\\\U0005FFFD\\\U00060000-\\\U0006FFFD\\\U00070000-\\\U0007FFFD
         \\\U00080000-\\\U0008FFFD\\\U00090000-\\\U0009FFFD\\\U000A0000-\\\U000AFFFD\\\U000B0000-\\\U000BFFFD\\\U000C0000-\\\U000CFFFD
         \\\U000D0000-\\\U000DFFFD\\\U000E0000\\\U000E0002-\\\U000E001F\\\U000E0080-\\\U000E00FF\\\U000E01F0-\\\U000EFFFD]
        '''.replace('\x20', '').replace('\n', '')
