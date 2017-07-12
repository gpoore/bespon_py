=====================================
    ``bespon`` package for Python
=====================================



The ``bespon`` package for Python encodes and decodes data in the
`BespON <https://bespon.org>`_ format.



Basic usage
===========

Data is loaded in a manner analogous to Python's ``json`` module:

* ``bespon.load(<file-like object>)``
* ``bespon.loads(<string or bytes>)``

Similarly, dumping data to a file or string:

* ``bespon.dump(<obj>, <file-like object>)``
* ``bespon.dumps(<obj>)``

At the moment, only dumping in indentation-style syntax is possible.  Support
for other styles may be added in the future.  Only dicts, lists, Unicode
strings, byte strings, floats, ints, bools, and ``None`` are currently
supported for dumping.



Lossless round-trip support
===========================

There is also support for lossless round-tripping.  Data can be loaded,
values can be modified, and then data can be saved again with minimal
impact on the data file layout.

Data can be loaded from a file or string into an instance of the
``RoundtripAst`` class.

* ``bespon.load_roundtrip_ast(<file-like object>)``
* ``bespon.loads_roundtrip_ast(<string or bytes>)``

This class has two methods that allow data to be modified.

* ``replace_val(<path>, <obj>)`` This replaces the object currently located
  at ``<path>`` within the data with ``<obj>``.  ``<path>`` must be a list
  or tuple consisting of dict keys and list indices.  ``<obj>`` must currently be a Unicode string, float, int, or bool, and must have the same
  type as the object it is replacing.
* ``replace_key(<path>, <obj>)`` This replaces the dict key at the end of
  ``<path>`` with the new key ``<obj>`` (which will map to the same value as
  the replaced key).  ``<obj>`` must be a Unicode string, int, or bool,
  and must have the same type as the object it is replacing.

After data in a ``RoundtripAst`` instance has been modified, it may be encoded
back into a string with the ``dumps()`` method.  An example is shown below.

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

This example illustrates several of BespON's round-trip capabilities.

* Comments and layout are preserved exactly.
* Key renaming works with key paths.  Every time a key appears in key paths,
  it is renamed.
* When a number is modified, the new value is expressed in the same base as
  the old value.
* When a quoted string is modified, the new value is quoted in the same
  style as the old value (at least to the extent that this is practical).
* As soon as a key is modified, the new key must be used for further
  modifications.  The old key is invalid.

Currently, round-trip support is limited to changing the value of any Unicode
string, float, int, or bool, without changing the type.  Support for changing
data types and for more general data manipulation will be added in the future.



Advanced loading and dumping
============================

The loading and dumping functions support several keyword arguments to
customize data handling.

**Loading**

* ``circular_references`` (boolean, default ``False``):  Enable aliases to
  create circular references.
* ``custom_parsers`` (dict, default ``None``):  Replace the default parser
  for a specified type with a custom parser.  For example, using
  ``custom_parsers={'int': float}`` would cause all integers to be parsed
  with the ``float()`` function.
* ``extended_types`` (boolean, default ``False``):  Enable preliminary support
  for ``set`` and ``odict`` tagged collections.  Enable
  preliminary support for complex number literals and rational number
  literals.  Complex numbers currently use the general form ``1.0+2.0i``,
  where the real part is optional, the imaginary unit is represented with
  ``i``, and numbers must be floats (either in decimal or hex form).  Rational
  numbers use the form ``1/2``, where the numerator and denominator must
  both be decimal integers, and any sign must come before the fraction.
* ``float_overflow_to_inf`` (boolean, default ``False``):  Whether
  non-``inf`` floats are permitted to overflow into ``inf`` without raising an
  error.
* ``integers`` (boolean, default ``True``):  Whether integers are permitted.
  Otherwise they are interpreted as floats.
* ``only_ascii_unquoted`` (boolean, default ``True``):  Whether non-ASCII
  identifier-style strings are allowed unquoted.
* ``only_ascii_source`` (boolean, default ``False``):  Whether non-ASCII code
  points are allowed to appear literally in the source (without being
  represented via backslash-escapes).
* ``python_types`` (boolean, default ``False``):  Enable preliminary support
  for Python-specific data types.  Currently this only supports ``tuple``.
* ``max_nesting_depth`` (int, default ``100``):  Maximum permitted nesting
  depth for collections.

**Dumping**

* ``hex_floats`` (boolean, default ``False``):  Whether floats are
  dumped in hex form.
* ``max_nesting_depth`` (int, default ``100``):  Maximum permitted nesting
  depth of collections.



Spec conformance
================

The ``bespon`` package passes the
`BespON test suite <https://github.com/bespon/bespon_tests>`_.
