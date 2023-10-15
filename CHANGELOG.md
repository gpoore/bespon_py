# `bespon` Change Log


## v0.7.0 (2023-10-15)

* Switched packaging to `pyproject.toml`.



## v0.6.0 (2021-02-06)

* Fixed encoder bug that caused invalid output for inline strings starting
  with a quotation mark (#3).
* Encoder now uses single-character string delimiters in more cases.
* Fixed bug that prevented decoding empty block strings and empty block
  comments.
* Fixed bug that prevented lists in indentation-based syntax immediately
  under sections.



## v0.5.0 (2020-08-11)

* `.value` with roundtrip AST nodes now gives correct, updated value for
  collections that have been modified (#1).
* `dump()` now works (#2).



## v0.4.0 (2020-03-30)

* Many improvements and new features for `RoundtripAst`.
  - Improved support for replacing keys and values.  There is experimental
    support for replacing dicts and lists, and now full support for all other
    data types.
  - Added option `enforce_types`, which provides experimental support for
    replacing keys and values with objects of a different data types.
  - Added support for custom encoders.
  - Added preliminary support for `__getitem__`-style access (for example,
    `ast['key'].value`).
  - Added access to trailing comments (not doc comments) with new node
    attributes `key_trailing_comment`, `value_trailing_comment`,
    `value_start_trailing_comment`, and `value_end_trailing_comment`.  These
    also allow modification of existing trailing comments.
* New loading options:  `custom_types` allows use of custom data types.
  `empty_default` is a function that is called to produce a
  default value when there is no data to load.
* New dumping options that control output appearance, data types, and data
  structures:  `aliases`, `circular_references`, `integers`,
  `only_ascii_unquoted`, `only_ascii_source`, `extended_types`,
  `python_types`, `baseclass`, `trailing_commas`, `compact_inline`,
  `inline_depth`, `nesting_indent`, `start_list_item`, and
  `flush_start_list_item`.
* Fixed bug with round-tripping bools.
* Fixed bug in error reporting for reserved words like `inf` in key paths.


## v0.3.0 (2017-07-12)

* Added decoder options `aliases`, `circular_references`, `custom_parsers`,
  and `python_types`.
* Decoder now disables circular references by default.  They may be enabled
  with new option `circular_references`.
* More powerful alias support, particularly for alias paths passing through
  inherited keys.
* Moved decoder `tuple` support from option `extended_types` to new option
  `python_types`.
* Complex numbers starting with `inf` or `nan` now work with decoder.
* Fixed bug in doc comment-tag interaction.


## v0.2.1 (2017-06-16)

* Fixed bugs with decoder options `only_ascii_source` and
  `only_ascii_unquoted`.
* Prevent explicit typing of `none`, `true`, and `false`.
* Tag keyword `indent` no longer affects text after an escaped newline.
* Fixed bug that prevented inline collections from being tagged if not at line
  start.
* `RootNode` and `DictlikeNode` now have `_state` attribute.
* Improved grammar.


## v0.2.0 (2017-06-08)

* Significant speed improvements: around 25-30% faster on decoding benchmark
  than v0.1.1.
* Added encoder options `hex_floats` and `max_nesting_depth`.
* Added decoder options `extended_types`, `float_overflow_to_inf`,
  `integers`, `only_ascii_unquoted`, `only_ascii_source`, `max_nesting_depth`.
* Added support for tags, which enable explicit typing and object labeling
  (for later referencing via aliases).  Tags also allow `indent` and `newline`
  to be specified for multiline strings.  Added support for `bytes`, `base16`,
  and `base64` types via tagging.
* Added support for aliases.
* Encoder now detects circular references.
* Improved error handling and error messages.
* `setuptools` is used for installation if available.


## v0.1.1 (2017-04-07)

* Added `MANIFEST.in` to include `README.rst` in sdist.


## v0.1.0 (2017-04-07)

* First release with mostly complete basic feature set.
