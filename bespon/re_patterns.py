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

import sys




# Regular expression patterns for XID_Start and XID_Continue, and for some
# subsets of these.  The ASCII and < U+0590 subsets are useful in optimizing
# when the full, slower regex can be avoided.  The Hangul fillers are
# excluded, because they are frequently rendered as normal spaces and thus can
# result in unintuitive behavior.
#
# hangul_fillers = set([0x115F, 0x1160, 0x3164, 0xFFA0])
# xid_start_less_fillers = set([cp for cp, data in unicodetools.ucd.derivedcoreproperties.items() if 'XID_Start' in data and cp not in hangul_fillers])
# xid_start_ascii = set(cp for cp in xid_start_less_fillers if cp < 128)
# xid_start_below_u0590 = set(cp for cp in xid_start_less_fillers if cp < 0x0590)
XID_START_ASCII = '[A-Za-z]'
XID_START_BELOW_U0590 = '''
    [A-Za-z\\\u00AA\\\u00B5\\\u00BA\\\u00C0-\\\u00D6\\\u00D8-\\\u00F6\\\u00F8-\\\u02C1\\\u02C6-\\\u02D1\\\u02E0-\\\u02E4\\\u02EC\\\u02EE\\\u0370-\\\u0374
     \\\u0376-\\\u0377\\\u037B-\\\u037D\\\u037F\\\u0386\\\u0388-\\\u038A\\\u038C\\\u038E-\\\u03A1\\\u03A3-\\\u03F5\\\u03F7-\\\u0481\\\u048A-\\\u052F
     \\\u0531-\\\u0556\\\u0559\\\u0561-\\\u0587]
    '''.replace('\x20', '').replace('\n', '')
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




# xid_continue_less_fillers = set([cp for cp, data in unicodetools.ucd.derivedcoreproperties.items() if 'XID_Continue' in data and cp not in hangul_fillers])
# xid_continue_ascii = set(cp for cp in xid_continue_less_fillers if cp < 128)
# xid_continue_below_u0590 = set(cp for cp in xid_continue_less_fillers if cp < 0x0590)
XID_CONTINUE_ASCII = '[0-9A-Z_a-z]'
XID_CONTINUE_BELOW_U0590 = '''
    [0-9A-Z_a-z\\\u00AA\\\u00B5\\\u00B7\\\u00BA\\\u00C0-\\\u00D6\\\u00D8-\\\u00F6\\\u00F8-\\\u02C1\\\u02C6-\\\u02D1\\\u02E0-\\\u02E4\\\u02EC
     \\\u02EE\\\u0300-\\\u0374\\\u0376-\\\u0377\\\u037B-\\\u037D\\\u037F\\\u0386-\\\u038A\\\u038C\\\u038E-\\\u03A1\\\u03A3-\\\u03F5\\\u03F7-\\\u0481
     \\\u0483-\\\u0487\\\u048A-\\\u052F\\\u0531-\\\u0556\\\u0559\\\u0561-\\\u0587]
    '''.replace('\x20', '').replace('\n', '')
if sys.maxunicode == 0xFFFF:
    XID_CONTINUE_LESS_FILLERS = '''
        [0-9A-Z_a-z\\\u00AA\\\u00B5\\\u00B7\\\u00BA\\\u00C0-\\\u00D6\\\u00D8-\\\u00F6\\\u00F8-\\\u02C1\\\u02C6-\\\u02D1\\\u02E0-\\\u02E4\\\u02EC
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
        [0-9A-Z_a-z\\\u00AA\\\u00B5\\\u00B7\\\u00BA\\\u00C0-\\\u00D6\\\u00D8-\\\u00F6\\\u00F8-\\\u02C1\\\u02C6-\\\u02D1\\\u02E0-\\\u02E4\\\u02EC
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




# Right-to-left code points (Bidi_Class R or AL).  Unassigned code points are
# included.
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


# Private use.  To keep the pattern as simple as possible, this includes
# noncharacters within the private use blocks, but since those are checked
# for separately, that isn't an issue.
#
# private_use = set([cp for cp, data in unicodetools.ucd.blocks.items() if 'Private' in data['Block'] and (cp < 0xD800 or cp > 0xDFFF)])
if sys.maxunicode == 0xFFFF:
    PRIVATE_USE = '''
        [\\\uE000-\\\uF8FF]
        |
        [\\\uDB80-\\\uDBFF][\\\uDC00-\\\uDFFF]
        '''.replace('\x20', '').replace('\n', '')
else:
    PRIVATE_USE = '''
        [\\\uE000-\\\uF8FF\\\U000F0000-\\\U0010FFFF]
        '''.replace('\x20', '').replace('\n', '')




# Invalid literal code points.
#
# For the most general case with narrow builds, a pattern without unpaired
# surrogates is used, and is extended at the beginning with an appropriate
# pattern for unpaired surrogates.  For all other cases, surrogates are
# incorporated in the pattern generation, since they must not appear at all.
#
# The literal `\r` is allowed, but a check for a missing following `\n` is
# inserted.
#
# Note that noncharacter code points are not listed in UnicodeData.txt,
# so generating a list of unassigned code points that are not noncharacters
# must be done with care.
#
# unicode_cc_less_t_lf_cr = set([cp for cp, data in unicodetools.ucd.unicodedata.items() if data['General_Category'] == 'Cc']) - set([ord(c) for c in ('\t', '\n', '\r')])
# non_unicode_cc_newlines = set([ord(c) for c in ('\u2028', '\u2029')])
# bidi_control = set([cp for cp, data in unicodetools.ucd.proplist.items() if 'Bidi_Control' in data])
# bom = set([ord('\uFEFF')])
# noncharacters = set([cp for cp, data in unicodetools.ucd.proplist.items() if 'Noncharacter_Code_Point' in data])
# surrogates = set([cp for cp, data in unicodetools.ucd.blocks.items() if 'Surrogate' in data['Block']])
# invalid_literal_less_surrogates = unicode_cc_less_t_lf_cr | non_unicode_cc_newlines | bidi_control | bom | noncharacters
# invalid_literal = invalid_literal_less_surrogates | surrogates
# invalid_literal_ascii = set([cp for cp in invalid_literal if cp < 128])
# valid_literal_ascii = set(range(0, 128)) - invalid_literal_ascii
# invalid_literal_below_u0590 = set([cp for cp in invalid_literal if cp < 0x0590])
# valid_literal_below_u0590 = set(range(0, 0x0590)) - invalid_literal_below_u0590
INVALID_CR = '\\\r(?!\\\n)'
UNPAIRED_SURROGATE = '[\\\uD800-\\\uDBFF](?=[^\\\uDC00-\\\uDFFF]|$)|(?<![\\\uD800-\\\uDBFF])[\\\uDC00-\\\uDFFF]'
NOT_VALID_LITERAL_ASCII = '[^\\\u0009-\\\u000A\\\u000D\\\u0020-\\\u007E]|{INVALID_CR}'.replace('{INVALID_CR}', INVALID_CR)
NOT_VALID_LITERAL_BELOW_U0590 = '[^\\\u0009-\\\u000A\\\u000D\\\u0020-\\\u007E\\\u00A0-\\\u058F]|{INVALID_CR}'.replace('{INVALID_CR}', INVALID_CR)
if sys.maxunicode == 0xFFFF:
    NOT_VALID_LITERAL = '''
        {INVALID_CR}
        |
        {UNPAIRED_SURROGATE}
        |
        [\\\u0000-\\\u0008\\\u000B-\\\u000C\\\u000E-\\\u001F\\\u007F-\\\u009F\\\u061C\\\u200E-\\\u200F\\\u2028-\\\u202E\\\u2066-\\\u2069\\\uFDD0-\\\uFDEF
         \\\uFEFF\\\uFFFE-\\\uFFFF]
        |
        \\\uD83F[\\\uDFFE-\\\uDFFF]|\\\uD87F[\\\uDFFE-\\\uDFFF]|\\\uD8BF[\\\uDFFE-\\\uDFFF]|\\\uD8FF[\\\uDFFE-\\\uDFFF]|\\\uD93F[\\\uDFFE-\\\uDFFF]|
        \\\uD97F[\\\uDFFE-\\\uDFFF]|\\\uD9BF[\\\uDFFE-\\\uDFFF]|\\\uD9FF[\\\uDFFE-\\\uDFFF]|\\\uDA3F[\\\uDFFE-\\\uDFFF]|\\\uDA7F[\\\uDFFE-\\\uDFFF]|
        \\\uDABF[\\\uDFFE-\\\uDFFF]|\\\uDAFF[\\\uDFFE-\\\uDFFF]|\\\uDB3F[\\\uDFFE-\\\uDFFF]|\\\uDB7F[\\\uDFFE-\\\uDFFF]|\\\uDBBF[\\\uDFFE-\\\uDFFF]|
        \\\uDBFF[\\\uDFFE-\\\uDFFF]
        '''.replace('\x20', '').replace('\n', '').replace('{INVALID_CR}', INVALID_CR).replace('{UNPAIRED_SURROGATE}', UNPAIRED_SURROGATE)
else:
    NOT_VALID_LITERAL = '''
        {INVALID_CR}
        |
        [\\\u0000-\\\u0008\\\u000B-\\\u000C\\\u000E-\\\u001F\\\u007F-\\\u009F\\\u061C\\\u200E-\\\u200F\\\u2028-\\\u202E\\\u2066-\\\u2069\\\uD800-\\\uDFFF
         \\\uFDD0-\\\uFDEF\\\uFEFF\\\uFFFE-\\\uFFFF\\\U0001FFFE-\\\U0001FFFF\\\U0002FFFE-\\\U0002FFFF\\\U0003FFFE-\\\U0003FFFF\\\U0004FFFE-\\\U0004FFFF
         \\\U0005FFFE-\\\U0005FFFF\\\U0006FFFE-\\\U0006FFFF\\\U0007FFFE-\\\U0007FFFF\\\U0008FFFE-\\\U0008FFFF\\\U0009FFFE-\\\U0009FFFF
         \\\U000AFFFE-\\\U000AFFFF\\\U000BFFFE-\\\U000BFFFF\\\U000CFFFE-\\\U000CFFFF\\\U000DFFFE-\\\U000DFFFF\\\U000EFFFE-\\\U000EFFFF
         \\\U000FFFFE-\\\U000FFFFF\\\U0010FFFE-\\\U0010FFFF]
        '''.replace('\x20', '').replace('\n', '').replace('{INVALID_CR}', INVALID_CR)


# Code points that must always be escaped in encoding.  This is identical to
# the invalid literal case, except that literal `\r` must be preserved.  In
# the decoding case, literal `\r` is allowed if part of `\r\n`, which is
# normalized to `\n`.
#
# unicode_cc_less_t_lf = set([cp for cp, data in unicodetools.ucd.unicodedata.items() if data['General_Category'] == 'Cc']) - set([ord(c) for c in ('\t', '\n')])
# non_unicode_cc_newlines = set([ord(c) for c in ('\u2028', '\u2029')])
# bidi_control = set([cp for cp, data in unicodetools.ucd.proplist.items() if 'Bidi_Control' in data])
# bom = set([ord('\uFEFF')])
# noncharacters = set([cp for cp, data in unicodetools.ucd.proplist.items() if 'Noncharacter_Code_Point' in data])
# surrogates = set([cp for cp, data in unicodetools.ucd.blocks.items() if 'Surrogate' in data['Block']])
# always_escaped_less_surrogates = unicode_cc_less_t_lf | non_unicode_cc_newlines | bidi_control | bom | noncharacters
# always_escaped = always_escaped_less_surrogates | surrogates
# always_not_escaped_ascii = set([cp for cp in range(128) if cp not in always_escaped])
# always_not_escaped_below_u0590 = set([cp for cp in range(0x0590) if cp not in always_escaped])
ALWAYS_ESCAPED_ASCII = '[^\\\u0009-\\\u000A\\\u0020-\\\u007E]'
ALWAYS_ESCAPED_BELOW_U0590 = '[^\\\u0009-\\\u000A\\\u0020-\\\u007E\\\u00A0-\\\u058F]'
if sys.maxunicode == 0xFFFF:
    ALWAYS_ESCAPED = '''
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
    ALWAYS_ESCAPED = '''
        [\\\u0000-\\\u0008\\\u000B-\\\u001F\\\u007F-\\\u009F\\\u061C\\\u200E-\\\u200F\\\u2028-\\\u202E\\\u2066-\\\u2069\\\uD800-\\\uDFFF\\\uFDD0-\\\uFDEF
         \\\uFEFF\\\uFFFE-\\\uFFFF\\\U0001FFFE-\\\U0001FFFF\\\U0002FFFE-\\\U0002FFFF\\\U0003FFFE-\\\U0003FFFF\\\U0004FFFE-\\\U0004FFFF
         \\\U0005FFFE-\\\U0005FFFF\\\U0006FFFE-\\\U0006FFFF\\\U0007FFFE-\\\U0007FFFF\\\U0008FFFE-\\\U0008FFFF\\\U0009FFFE-\\\U0009FFFF
         \\\U000AFFFE-\\\U000AFFFF\\\U000BFFFE-\\\U000BFFFF\\\U000CFFFE-\\\U000CFFFF\\\U000DFFFE-\\\U000DFFFF\\\U000EFFFE-\\\U000EFFFF
         \\\U000FFFFE-\\\U000FFFFF\\\U0010FFFE-\\\U0010FFFF]
        '''.replace('\x20', '').replace('\n', '')
