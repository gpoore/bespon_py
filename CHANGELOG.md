# `bespon` Change Log


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
