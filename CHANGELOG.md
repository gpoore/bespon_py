# `bespon` Change Log



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

* Added MANIFEST.in to include README.rst in sdist.


## v0.1.0 (2017-04-07)

* First release with mostly complete basic feature set.
