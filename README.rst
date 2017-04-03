=====================================
    ``bespon`` package for Python
=====================================


`BespON <https://bespon.github.io>`_ is a multi-paradigm, extensible configuration
language with advanced round-tripping capabilities.  Data may be represented
in a compact inline form, an indentation-based form, or a section- and
keypath-based form.

The ``bespon`` package for Python supports loading data in a manner
analogous to the ``json`` package:

* ``bespon.load(<file-like object>)``
* ``bespon.loads(<string or bytes>)``

Similarly, it supports dumping data to a file or string:

* ``bespon.dump(<obj>, <file-like object>)``
* ``bespon.dumps(<obj>)``

At the moment, only dumping in indentation-style syntax is possible.  Support
for other styles may be added in the future.  Only dicts, lists, Unicode
strings, floats, ints, bools, and None are currently supported for dumping.

----

There is also support for lossless round tripping.  Data can be loaded,
values can be modified, and then data can be saved again with minimal
impact on the data file layout.  For example,

::

    >>> ast = bespon.loads_roundtrip_ast("""
    key.subkey.first = 123   # Comment
    key.subkey.second = 0b1101
    key.subkey.third = `literal \string`
    """)
    >>> ast.replace_key(['key', 'subkey'], 'sk')
    >>> ast.replace_val(['key', 'sk', 'second'], 7)
    >>> ast.replace_val(['key', 'sk', 'third'], '\\another \\literal')
    >>> ast.replace_key(['key', 'sk', 'third'], 'fourth')
    >>> print(ast.dumps())

    key.sk.first = 123   # Comment
    key.sk.second = 0b111
    key.sk.fourth = `\another \literal`

This example illustrates several things.

* Comments and layout are preserved exactly.
* Key renaming works with key paths.  Every time a key appears in key paths,
  it is renamed.
* When a number is modified, the new value is expressed in the same base as
  the old value.
* When a quoted string is modified, the new value is quoted in the same
  style as the old value (at least to the extent that this is practical).
* As soon as a key is modified, the new key must be used for further
  modifications.  The old key is invalid.

Currently, round trip support is limited to changing the value of any
string, float, int, or bool, without changing the type.  Support for changing
data types and for more general data manipulation will be added in the future.

----

The ``bespon`` package passes the `BespON test suite <https://github.com/bespon/bespon_tests>`_.
