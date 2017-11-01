=====================================
    ``bespon`` package for Python
=====================================



The ``bespon`` package for Python encodes and decodes data in the
`BespON format <https://bespon.org>`_.



Basic usage
===========

Data is loaded in a manner analogous to Python's ``json`` module:

* ``bespon.load(<file-like object>)``
* ``bespon.loads(<string or bytes>)``

Similarly, dumping data to a file or string:

* ``bespon.dump(<obj>, <file-like object>)``
* ``bespon.dumps(<obj>)``

Only dicts, lists, Unicode strings, byte strings, floats, ints, bools, and
``None`` are supported for dumping by default.  See the ``extended_types``
and ``python_types`` keywords for optional support of additional types.



Lossless round-trip support
===========================

There is also support for lossless round-tripping.  Data can be loaded,
modified, and then saved with minimal impact on the data file layout.

Data can be loaded from a file or string into an instance of the
``RoundtripAst`` class.

* ``bespon.load_roundtrip_ast(<file-like object>)``
* ``bespon.loads_roundtrip_ast(<string or bytes>)``

This class has two methods that allow data to be modified.

* ``replace_val(<path>, <obj>)`` This replaces the object currently located
  at ``<path>`` within the data with ``<obj>``.  ``<path>`` must be a list or
  tuple consisting of dict keys and list indices.  ``<obj>`` must currently be
  a Unicode string, float, int, or bool, and must have the same type as the
  object it is replacing.  (There is also preliminary support for replacing
  lists and dicts.  Support for changing data types is coming soon.)
* ``replace_key(<path>, <obj>)`` This replaces the dict key at the end of
  ``<path>`` with the new key ``<obj>`` (which will map to the same value as
  the replaced key).  ``<obj>`` must be a Unicode string, int, or bool, and
  must have the same type as the object it is replacing.  (There is also
  preliminary support for replacing lists and dicts.  Support for changing
  data types is coming soon.)

There is also **preliminary** support for ``__getitem__``-style access
(``ast['key']``, etc.).  Data accessed in this manner has the following
attributes.

* ``key``:  Key of the current location, if in a dict.
  Allows assignment, as long as the new object is of the same type as the old
  object, and the type is supported.  (Support for changing data types is
  coming soon.)  For example, ``ast['key'].key = 'new_key'`` will rename the
  key.
* ``key_doc_comment``:  Doc comment of key, if in a dict.  ``None`` if there
  is no doc comment.  Currently only supports assignment for existing doc
  comments.
* ``key_trailing_comment``:  Trailing line comment (``#comment``) that
  immediately follows a key on the same line.
* ``value``:  Value of the current location.  Can be assigned, as long as the
  new object is of the same type as the old object, and the type is supported.
  (Support for changing data types is coming soon.)
* ``value_doc_comment``:  Doc comment of the value at the current location.
  ``None`` if there is no doc comment.  Currently only supports assignment for
  existing doc comments.
* ``value_trailing_comment``:  Trailing line comment (``#comment``) that
  immediately follows a non-collection type on the same line.
* ``value_start_trailing_comment``:  Trailing line comment that immediately
  follows the start of a collection in inline-style syntax ("``{``" or
  "``[``").
* ``value_end_trailing_comment``:  Trailing line comment that immediately
  follows the end of a collection in inline-style syntax ("``}``" or "``]``").

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

Here is the same example using the preliminary ``__getitem__``-style syntax.

::

    >>> ast = bespon.loads_roundtrip_ast("""
    key.subkey.first = 123   # Comment
    key.subkey.second = 0b1101
    key.subkey.third = `literal \string`
    """)
    >>> ast['key']['subkey'].key = 'sk'
    >>> ast['key']['sk']['second'].value = 7
    >>> ast['key']['sk']['third'].value = '\\another \\literal'
    >>> ast['key']['sk']['third'].key = 'fourth'
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



Advanced loading and dumping
============================

The loading and dumping functions support several keyword arguments to
customize data handling.


**Loading**

* ``aliases`` (boolean, default ``True``):  Allow aliases.

* ``circular_references`` (boolean, default ``False``):  Allow aliases to
  create circular references.

* ``custom_parsers`` (dict, default ``None``):  Replace the default parser
  for a specified type with a custom parser.  For example, using
  ``custom_parsers={'int': float}`` would cause all integers to be parsed
  with the ``float()`` function.

* ``custom_types`` (``bespon.LoadType`` instance, or list or tuple of
  ``bespon.LoadType``):  Enable preliminary support for custom types.
  ``bespon.LoadType`` takes up to five named arguments (for examples, see the
  definitions of built-in types at the end of ``load_types.py``):

  * ``name`` (string):  Type name.

  * ``compatible_implicit_types`` (string, or set or list or tuple of
    strings):  Names of built-in implicit types with which the type being
    defined is compatible.  Implicit types include ``none``, ``bool``,
    ``int``, ``float``, ``str``, ``complex``, ``rational``, ``dict``, and
    ``list``.

  * ``parser`` (function):  Function that converts a string (for scalar types)
    or dict or list (collection types) into an instance of the type being
    defined.

  * ``ascii_bytes`` (boolean, default ``False``):  For types based on strings.
    Determines whether the raw string is encoded into binary as an ASCII byte
    string before being passed to the parser function.  If this is done, only
    bytes-compatible backslash escapes are allowed in the string.

  * ``mutable`` (boolean, default ``False``):  For collection types.
    Specifies whether instances are mutable after being created.  Mutable
    collections have greater flexibility in terms of circular references.

* ``extended_types`` (boolean, default ``False``):  Enable preliminary support
  for ``set`` and ``odict`` tagged collections (for example, ``(set)> [1, 2,
  3]``).  Enable preliminary support for complex number literals and rational
  number literals.  Complex numbers currently use the general form
  ``1.0+2.0i``, where the real part is optional, the imaginary unit is
  represented with ``i``, and numbers must be floats (either in decimal or hex
  form).  Rational numbers use the form ``1/2``, where the numerator and
  denominator must both be decimal integers, and any sign must come before the
  fraction.

* ``float_overflow_to_inf`` (boolean, default ``False``):  Whether
  non-``inf`` floats are permitted to overflow into ``inf`` without raising an
  error.

* ``integers`` (boolean, default ``True``):  Whether integers are permitted.
  Otherwise they are interpreted as floats.

* ``max_nesting_depth`` (int, default ``100``):  Maximum permitted nesting
  depth for collections.  When ``circular_references=True``, this is the
  maximum permitted depth before a circular reference is encountered.

* ``only_ascii_source`` (boolean, default ``False``):  Whether non-ASCII code
  points are allowed to appear literally in the source (without being
  represented via backslash-escapes).

* ``only_ascii_unquoted`` (boolean, default ``True``):  Whether non-ASCII
  identifier-style strings are allowed unquoted.

* ``python_types`` (boolean, default ``False``):  Enable preliminary support
  for Python-specific data types.  Currently this only supports ``tuple``.



**Dumping**

* ``aliases`` (boolean, default ``True``):  Allow aliases so that a
  collection may appear multiple times within data.

* ``baseclass`` (boolean, default ``False``):  Encode unknown data types as
  their baseclasses if supported.  For example, ``collections.OrderedDict``
  would be encoded as a ``dict``, and a custom integer class would be encoded
  as ``int``.

* ``circular_references`` (boolean, default ``False``):  Allow aliases to
  create circular references.

* ``compact_inline`` (boolean, default ``False``):  In inline syntax, put
  everything on one line to make it as compact as possible.

* ``extended_types`` (boolean, default ``False``):  Enable preliminary support
  for ``set`` and ``odict`` tagged collections (for example, ``(set)> [1, 2,
  3]``).  Enable preliminary support for complex number literals and rational
  number literals.  Complex numbers currently use the general form
  ``1.0+2.0i``, where the real part is optional, the imaginary unit is
  represented with ``i``, and numbers must be floats (either in decimal or hex
  form).  Rational numbers use the form ``1/2``, where the numerator and
  denominator must both be decimal integers, and any sign must come before the
  fraction.

* ``flush_start_list_item`` (string, default ``*<space>``):  How a list item
  starts in indentation-style syntax when it is at the top level, within
  another list, or otherwise in a context when the ``*`` must be aligned flush
  with a designated margin.  Must start with a single ``*`` followed by zero
  or more spaces or tabs.

* ``hex_floats`` (boolean, default ``False``):  Whether floats are
  dumped in hex form.

* ``inline_depth`` (boolean, default ``max_nesting_depth+1``):  Nesting depth
  at which to switch from indentation-style to inline-style syntax.  A value
  of ``0`` will make everything inline, ``1`` will make the top-level
  collection indentation-style but everything inside it inline-style, and
  so forth.

* ``integers`` (boolean, default ``True``):  Whether integers are permitted.
  Otherwise they are interpreted as floats.

* ``max_nesting_depth`` (int, default ``100``):  Maximum permitted nesting
  depth of collections.  When ``circular_references=True``, this is the
  maximum permitted depth before a circular reference is encountered.

* ``nesting_indent`` (string, default ``<space><space><space><space>``):
  Indentation added for each nesting level.

* ``only_ascii_source`` (boolean, default ``False``):  Whether non-ASCII code
  points are allowed to appear literally in the source (without being
  represented via backslash-escapes).

* ``only_ascii_unquoted`` (boolean, default ``True``):  Whether non-ASCII
  identifier-style strings are allowed unquoted.

* ``python_types`` (boolean, default ``False``):  Enable preliminary support
  for Python-specific data types.  Currently this only supports ``tuple``.

* ``trailing_commas`` (boolean, default ``False``):  In inline syntax, leave
  a comma after the last item in a collection.  This can minimize diffs.

* ``start_list_item`` (string, default ``<space><space>*<space>``):  How a
  list item starts in indentation-style syntax.  This must begin with one or
  more spaces or tabs and contain a single ``*``.  The leading spaces or tabs
  define the relative indentation from the previous indentation level.



Spec conformance
================

The ``bespon`` package passes the
`BespON test suite <https://github.com/bespon/bespon_tests>`_.
