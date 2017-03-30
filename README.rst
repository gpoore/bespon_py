=====================================
    ``bespon`` package for Python
=====================================


`BespON <https://bespon.github.io>`_ is a multi-paradigm, extensible configuration
language with advanced round-tripping capabilities.  Data may be represented
in a compact inline form, an indentation-based form, or a section- and
keypath-based form.  An example of the format is shown below.

----

::

    # Line comments are allowed!  They can be round-tripped as long as data
    # elements are only modified, not added or removed.

    ### This is a doc comment.  It can always be round-tripped.###
    # Only one doc comment is allowed per object; another couldn't be here.

    "quoted key with \x5C escapes" = 'quoted value with \u{5C} escapes'

    `literal key without \ escapes` = ``literal value without `\` escapes``

    # ASCII identifier-style strings are allowed unquoted.  Keys cannot contain
    # spaces; values can contain single spaces and must be on one line.
    # Unquoted Unicode identifiers can optionally be enabled.
    unquoted_key = unquoted value

    inline_dict = {key1 = value1, key2 = value2,}  # Trailing commas are fine.

    inline_list_of_ints = [1, 0x12, 0o755, 0b1010]  # Hex, octal, and binary!

    list_of_floats =
      * 1.2e3
      * -inf  # Full IEEE 754 compatibility.  Infinity and NaN are not excluded.
      * 0x4.3p2  # Hex floats, to avoid rounding issues.

    wrapped_string = """string containing no whitespace lines in which line breaks
        are replaced with spaces, and "quotes" are possible by via delimiters"""

    multiline_literal_string = |```
            A literal string in which linebreaks are kept (as '\n')
            and leading indentation (relative to delimiters) is preserved,
            with special delimiters always on lines by themselves.
        |```/

    multiline_escaped_string = |"""
        The same idea as the literal string, but with backslash-escapes.
        |"""/

    key1.key2 = true  # Key path style; same as "key1 = {key2 = true}"

    |=== section.subsection  # Same as "section = {subsection = {key = value}}"
    key = value
    |===/  # Back to root level.  Can be omitted if sections never return to root.

----

The ``bespon`` package for Python currently supports loading data in a manner
analogous to the ``json`` package:

* ``bespon.load(<file-like object>)``
* ``bespon.loads(<string or bytes>)``

Similarly, it supports dumping data to a file or string:

* ``bespon.dump(<obj>, <file-like object>)``
* ``bespon.dumps(<obj>)``

At the moment, only dumping in indentation-style syntax is possible.  Support
for other styles may be added in the future.  Only dicts, lists, Unicode
strings, floats, ints, bools, and None are currently supported for dumping.

Support for lossless round tripping is coming very soon.  All required
functionality is already in place.  This will allow data to be loaded,
modified, and saved, with exact preservation of all data ordering and
comments, so long as data values are only modified (no data is added or
removed).

The ``bespon`` package passes the `BespON test suite <https://github.com/bespon/bespon_tests>`_.
