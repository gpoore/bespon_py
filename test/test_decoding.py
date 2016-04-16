# -*- coding: utf-8 -*-
#
# Copyright (c) 2015, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


from __future__ import (division, print_function, absolute_import,
                        unicode_literals)


import sys
import os
import random
import collections

if sys.version_info.major == 2:
    str = unicode
    __chr__ = chr
    chr = unichr

if all(os.path.isdir(x) for x in ('bespon', 'test', 'doc')):
    sys.path.insert(0, '.')

import bespon.decoding as mdl
import bespon.erring as err

import pytest

import json
try:
    import yaml
    loaded_yaml = True
except ImportError:
    loaded_yaml = False
import textwrap


def test__unwrap_inline():
    dc = mdl.BespONDecoder()
    s = 'first\nsecond\nthird'
    assert(dc._unwrap_inline(s.splitlines(True)) == s.replace('\n', ' '))
    t = 'first \nsecond \nthird'
    assert(dc._unwrap_inline(t.splitlines(True)) == s.replace('\n', ' '))
    u = 'first  \nsecond  \nthird'
    assert(dc._unwrap_inline(u.splitlines(True)) == u.replace('\n', ''))
    v = 'first\u3000\nsecond\u3000\nthird'
    assert(dc._unwrap_inline(v.splitlines(True)) == v.replace('\n', ''))


def test_int_re():
    dc = mdl.BespONDecoder()
    assert(dc._int_re.match('0'))
    assert(dc._int_re.match('1'))
    assert(dc._int_re.match('1234567890'))
    assert(dc._int_re.match('1_23456789_0'))
    assert(not dc._int_re.match('_1234567890'))
    assert(not dc._int_re.match('1234567890_'))
    assert(not dc._int_re.match('123456__7890'))
    assert(dc._int_re.match('0xABCDEF0123456789'))
    assert(dc._int_re.match('0xabcdef0123456789'))
    assert(dc._int_re.match('0x0123456789abcdef'))
    assert(dc._int_re.match('0x0_1_23456789abcd_e_f'))
    assert(not dc._int_re.match('_0x0123456789abcdef'))
    assert(not dc._int_re.match('0_x0123456789abcdef'))
    assert(not dc._int_re.match('0x_0123456789abcdef'))
    assert(not dc._int_re.match('0x0123456789abcdef_'))
    assert(dc._int_re.match('0o01234567'))
    assert(dc._int_re.match('0o7654321'))
    assert(dc._int_re.match('0o7_65432_1'))
    assert(not dc._int_re.match('_0o7654321'))
    assert(not dc._int_re.match('0_o7654321'))
    assert(not dc._int_re.match('0o_7654321'))
    assert(not dc._int_re.match('0o7654321_'))
    assert(not dc._int_re.match('0o765__4321'))
    assert(dc._int_re.match('0b0'))
    assert(dc._int_re.match('0b01'))
    assert(dc._int_re.match('0b10'))
    assert(dc._int_re.match('0b1_1_0'))
    assert(not dc._int_re.match('_0b11011'))
    assert(not dc._int_re.match('0_b11011'))
    assert(not dc._int_re.match('0b_11011'))
    assert(not dc._int_re.match('0b11011_'))
    assert(not dc._int_re.match('0b110__11'))
    assert(all(dc._int_re.match(str(random.randint(-1000000, 1000000))) for n in range(1000)))
    assert(all(dc._int_re.match(hex(random.randint(-1000000, 1000000))) for n in range(1000)))


def test_float_re():
    dc = mdl.BespONDecoder()
    assert(dc._float_re.match('0.'))
    assert(dc._float_re.match('.0'))
    assert(dc._float_re.match('0e0'))
    assert(dc._float_re.match('+0e0'))
    assert(dc._float_re.match('-0e0'))
    assert(dc._float_re.match('0e+0'))
    assert(dc._float_re.match('0e-0'))
    assert(dc._float_re.match('1.'))
    assert(dc._float_re.match('-1.'))
    assert(dc._float_re.match('+1.'))
    assert(dc._float_re.match('1.e1'))
    assert(dc._float_re.match('-1.e1'))
    assert(dc._float_re.match('+1.e1'))
    assert(dc._float_re.match('0.12'))
    assert(dc._float_re.match('-0.12'))
    assert(dc._float_re.match('+0.12'))
    assert(dc._float_re.match('.0e0'))
    assert(dc._float_re.match('12e3'))
    assert(dc._float_re.match('12e+3'))
    assert(dc._float_re.match('12e-3'))
    assert(dc._float_re.match('3.14e5'))
    assert(dc._float_re.match('+3.14e5'))
    assert(dc._float_re.match('-3.14e5'))
    assert(dc._float_re.match('1_231_4.2_3_3e3_5_2'))
    assert(not dc._float_re.match('_12314.233e352'))
    assert(not dc._float_re.match('12314_.233e352'))
    assert(not dc._float_re.match('12314._233e352'))
    assert(not dc._float_re.match('_12314.233_e352'))
    assert(not dc._float_re.match('12314.233e_352'))
    assert(not dc._float_re.match('12314.233e352_'))
    assert(dc._float_re.match('0x3.a7p10'))
    assert(dc._float_re.match('0x3p10'))
    assert(dc._float_re.match('0x3.p10'))
    assert(dc._float_re.match('0x.a7p10'))
    assert(dc._float_re.match('0x1_d_e.a_4_f7p+1_3_0'))
    assert(not dc._float_re.match('0x1_d_e.a_4_f7p+1_3_f'))
    assert(not dc._float_re.match('_0x1de.a4f7p130'))
    assert(not dc._float_re.match('0_x1de.a4f7p130'))
    assert(not dc._float_re.match('0x_1de.a4f7p130'))
    assert(not dc._float_re.match('0x1de_.a4f7p130'))
    assert(not dc._float_re.match('0x1de._a4f7p130'))
    assert(not dc._float_re.match('0x1de.a4f7_p130'))
    assert(not dc._float_re.match('0x1de.a4f7p_130'))
    assert(not dc._float_re.match('0x1de.a4f7p130_'))
    assert(all(dc._float_re.match(str(random.uniform(-1e9, 1e9))) for n in range(1000)))
    assert(all(dc._float_re.match(float.hex(random.uniform(-1e9, 1e9))) for n in range(1000)))




def test_decode_raw_ast():
    dc = mdl.BespONDecoder()
    dc._debug_raw_ast = True

    with pytest.raises(err.ParseError):
        dc.decode('')
    with pytest.raises(err.ParseError):
        dc.decode(b'\xEF\xBB\xBF'.decode('utf-8'))
    with pytest.raises(err.ParseError):
        dc.decode('%')
    with pytest.raises(err.ParseError):
        dc.decode('%\n')
    with pytest.raises(err.ParseError):
        dc.decode(' %\n')

    dc.decode('%\n\n""')
    assert(dc._ast == [''])
    dc.decode('%\n ""')
    assert(dc._ast == [''])

    with pytest.raises(err.ParseError):
        dc.decode('%\n%%% %%%/\n')
    with pytest.raises(err.ParseError):
        dc.decode('%\n%%% %%%/')
    with pytest.raises(err.ParseError):
        dc.decode('%\n%%%\n\n%%%/\n')

    dc.decode('%\n%%%\n\n%%%/\n""\n')
    assert(dc._ast == [''])

    dc.decode('(bytes)> ""\n')
    assert(dc._ast == [b''])
    dc.decode('(b)> ""\n')
    assert(dc._ast == [b''])

    dc.decode('"a"\n')
    assert(dc._ast == ["a"])

    dc.decode('"a\nb"\n')
    assert(dc._ast == ["a b"])

    dc.decode('"""\na\nb\n"""/\n')
    assert(dc._ast == ["a\nb\n"])

    dc.decode('"""\na\nb\n"""//\n')
    assert(dc._ast == ["a\nb"])

    dc.decode(' """\n  a\n  b\n """//\n')
    assert(dc._ast == [" a\n b"])

    dc.decode('"a"="b"')
    assert(dc._ast == [collections.OrderedDict([['a', 'b']])])
    dc.decode('"a"="b"\n"c"="d"\n')
    assert(dc._ast == [collections.OrderedDict([['a', 'b'], ['c', 'd']])])
    dc.decode('"a"=\n "b"=\n  "c"="d"\n')
    assert(dc._ast == [ collections.OrderedDict([['a', collections.OrderedDict([['b', collections.OrderedDict([['c', 'd']]) ]]) ]]) ])

    dc.decode(' """\n  ab\n  cd\n """/ = "efg" ')
    assert(dc._ast == [ collections.OrderedDict([[' ab\n cd\n', 'efg']]) ])

    dc.decode('+ "a"\n+ "b"')
    assert(dc._ast == [ ['a', 'b'] ])
    dc.decode('+\n  + "a"')
    assert(dc._ast == [ [ ['a'] ] ])

    dc.decode('"a"=\n "b"="c"\n"d"="e"')
    assert(dc._ast == [ collections.OrderedDict([ ['a', collections.OrderedDict([['b', 'c']]) ], ['d', 'e'] ]) ])

    with pytest.raises(err.ParseError):
        dc.decode('"a"="b"\n "c"="d"')
    with pytest.raises(err.ParseError):
        dc.decode('+ "a"\n + "b"')




def test_decode_indentation_syntax():
    dc = mdl.BespONDecoder()

    assert(dc.decode('"a"="b"') == {'a': 'b'})
    assert(dc.decode(' "a" = "b" ') == {'a': 'b'})
    assert(dc.decode('"a"=\n "b"') == {'a': 'b'})
    assert(dc.decode('"a" =\n "b"') == {'a': 'b'})
    assert(dc.decode('"a"="b"\n\n\n') == {'a': 'b'})
    assert(dc.decode(' "a" = "b" \n\n\n') == {'a': 'b'})
    assert(dc.decode('"a"=\n "b"\n\n\n') == {'a': 'b'})
    assert(dc.decode('"a" =\n "b"\n\n\n') == {'a': 'b'})

    assert(dc.decode('a=b') == {'a': 'b'})
    assert(dc.decode(' a = b ') == {'a': 'b'})
    assert(dc.decode('a=\n b') == {'a': 'b'})
    assert(dc.decode('a =\n b') == {'a': 'b'})

    assert(dc.decode('"a"=\n "b"=\n  "c"="d"') == {'a': {'b': {'c': 'd'} } })
    assert(dc.decode('a=\n b=\n  c=d') == {'a': {'b': {'c': 'd'} } })

    assert(dc.decode(' "a" = 1\n "b" = \n  "c" = 3\n  "d" = 4\n\n') == {'a': 1, 'b': {'c': 3, 'd': 4}})
    assert(dc.decode(' a = 1\n b = \n  c = 3\n  d = 4\n\n') == {'a': 1, 'b': {'c': 3, 'd': 4}})

    assert(dc.decode('+ "a"\n+ "b"') == ['a', 'b'])
    assert(dc.decode('+\n  + "a"\n  + "b"') == [['a', 'b']])



def test_decode_inline_syntax():
    dc = mdl.BespONDecoder()

    assert(dc.decode('["a"]') == ['a'])
    assert(dc.decode('[a]') == ['a'])
    assert(dc.decode('{"a"="b"}') == {'a': 'b'})
    assert(dc.decode('{a=b}') == {'a': 'b'})

    assert(dc.decode('["a"; "b"]') == ['a', "b"])
    assert(dc.decode('[a; b]') == ['a', 'b'])
    assert(dc.decode('{"a"="b"; "c"="d"}') == {'a': 'b', 'c': 'd'})
    assert(dc.decode('{a=b; c=d}') == {'a': 'b', 'c': 'd'})

    assert(dc.decode('["a"; ["a"]]') == ['a', ['a']])
    assert(dc.decode('{"a"={"b"="c"}}') == {'a': {'b': 'c'}})

    assert(dc.decode('{"a"= 1; "b"= {"c"= 3; "d"= 4}}') == {'a': 1, 'b': {'c': 3, 'd': 4}})
    assert(dc.decode('{a = 1; b = {c = 3; d = 4}}') == {'a': 1, 'b': {'c': 3, 'd': 4}})



def test_decode_vs_json_yaml():
    dc = mdl.BespONDecoder()

    # Test against json example from https://en.wikipedia.org/wiki/JSON
    s_json = '''\
    {
      "firstName": "John",
      "lastName": "Smith",
      "isAlive": true,
      "age": 25,
      "address": {
        "streetAddress": "21 2nd Street",
        "city": "New York",
        "state": "NY",
        "postalCode": "10021-3100"
      },
      "phoneNumbers": [
        {
          "type": "home",
          "number": "212 555-1234"
        },
        {
          "type": "office",
          "number": "646 555-4567"
        }
      ],
      "children": [],
      "spouse": null
    }
    '''
    s_bespon_inline = '''\
    {
      firstName = John;
      lastName = Smith;
      isAlive = true;
      age = 25;
      address = {
        streetAddress = 21 2nd Street;
        city = New York;
        state = NY;
        postalCode = 10021-3100
      };
      phoneNumbers = [
        {
          type = home;
          number = 212 555-1234
        };
        {
          type = office;
          number = 646 555-4567
        }
      ];
      children = [];
      spouse = null
    }
    '''
    s_bespon_non_inline = '''\
    firstName = John
    lastName = Smith
    isAlive = true
    age = 25
    address =
        streetAddress = 21 2nd Street
        city = New York
        state = NY
        postalCode = 10021-3100
    phoneNumbers =
        + type = home
          number = 212 555-1234
        + type = office
          number = 646 555-4567
    children = []
    spouse = null
    '''
    assert(dc.decode(s_bespon_inline) == json.loads(s_json))
    assert(dc.decode(s_bespon_non_inline) == json.loads(s_json))

    if loaded_yaml:
        # https://en.wikipedia.org/wiki/YAML
        s_yaml = '''\
        ---
        receipt:     Oz-Ware Purchase Invoice
        date:        '2012-08-06'
        customer:
            first_name:   Dorothy
            family_name:  Gale

        items:
            - part_no:   A4786
              descrip:   Water Bucket (Filled)
              price:     1.47
              quantity:  4

            - part_no:   E1628
              descrip:   High Heeled "Ruby" Slippers
              size:      8
              price:     133.7
              quantity:  1

        bill-to:  &id001
            street: |
                    123 Tornado Alley
                    Suite 16
            city:   East Centerville
            state:  KS

        ship-to:  *id001

        specialDelivery:  >
            Follow the Yellow Brick
            Road to the Emerald City.
            Pay no attention to the
            man behind the curtain.
        ...
        '''
        s_yaml = textwrap.dedent(s_yaml)
        s_bespon = """\
        receipt =     Oz-Ware Purchase Invoice
        date =        2012-08-06
        customer =
            first_name =   Dorothy
            family_name =  Gale

        items =
            + part_no =   A4786
              descrip =   'Water Bucket (Filled)'
              price =     1.47
              quantity =  4

            + part_no =   E1628
              descrip =   'High Heeled "Ruby" Slippers'
              size =      8
              price =     133.7
              quantity =  1

        bill-to =
            street = '''
                     123 Tornado Alley
                     Suite 16
                     '''/
            city =   East Centerville
            state =  KS

        ship-to =
            street = '''
                     123 Tornado Alley
                     Suite 16
                     '''/
            city =   East Centerville
            state =  KS

        specialDelivery = '''
            Follow the Yellow Brick Road to the Emerald City. Pay no attention to the man behind the curtain.
            '''/
        """
        s_bespon = textwrap.dedent(s_bespon)
        assert(dc.decode(s_bespon) == yaml.load(s_yaml))




    def test_explicit_typing():
        dc = mdl.BespONDecoder()
        assert(dc.decode('(odict)>{a=b}') == collections.OrderedDict({'a': 'b'}))
        assert(dc.decode('(odict)> {a=b}') == collections.OrderedDict({'a': 'b'}))
        assert(dc.decode('(odict)>\na=b') == collections.OrderedDict({'a': 'b'}))
        assert(dc.decode('(odict)>\n a=b') == collections.OrderedDict({'a': 'b'}))
        assert(dc.decode('(set)>[1; 2; 3]') == set(1, 2, 3))
        assert(dc.decode('(set)> [1; 2; 3]') == set(1, 2, 3))
        assert(dc.decode('(set)>\n+ 1\n+ 2\n+ 3]') == set(1, 2, 3))
        assert(dc.decode('(set)>\n + 1\n + 2\n + 3]') == set(1, 2, 3))





"""
def test_parse_str_esc():
    dc = mdl.BespONDecoder()
    s = '\\a\\b\\v\\f\\n\\r\\t\\u1234\\x01ABCD'
    s_after = '\a\b\v\f\n\r\t\u1234\x01ABCD'
    assert(dc.parse_str_esc(s.splitlines(True)) == s_after)


def test_parse_bin():
    dc = mdl.BespONDecoder()
    s = 'ABCDEFG\a\b\f\v'
    assert(dc.parse_bin(s.splitlines(True)) == s.encode('ascii'))

    with pytest.raises(err.BinaryStringEncodeError):
        t = 'ABCDEFG\a\b\f\v\u00ff'
        dc.parse_bin(t.splitlines(True))

    with pytest.raises(err.BinaryStringEncodeError):
        t = 'ABCDEFG\a\b\f\v\xff'
        dc.parse_bin(t.splitlines(True))

def test_parse_bin_esc():
    dc = mdl.BespONDecoder()
    s = 'ABCDEFG\\a\\b\\f\\v\\x01\\xff'
    b_esc = b'ABCDEFG\a\b\f\v\x01\xff'
    assert(dc.parse_bin_esc(s.splitlines(True)) == b_esc)

    with pytest.raises(err.UnknownEscapeError):
        t = 'ABCDEFG\\a\\b\\f\\v\\x01\\xff\\uffff'
        dc.parse_bin_esc(t.splitlines(True))


def test_parse_bin_base64():
    dc = mdl.BespONDecoder()
    s = 'AQIECBav/w=='
    b = b'\x01\x02\x04\x08\x16\xaf\xff'
    assert(dc.parse_bin_base64(s.splitlines(True)) == b)

    with pytest.raises(err.BinaryBase64DecodeError):
        s = '\u2028AQIECBav/w=='
        dc.parse_bin_base64(s.splitlines(True))


def test_parse_bin_hex():
    dc = mdl.BespONDecoder()
    s = '0102040816AFFF'
    b = b'\x01\x02\x04\x08\x16\xaf\xff'
    assert(dc.parse_bin_base16(s.splitlines(True)) == b)

    with pytest.raises(err.BinaryBase16DecodeError):
        s = '\u20280102040816AFFF'
        dc.parse_bin_base16(s.splitlines(True))
"""
