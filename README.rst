==============
    BespON
==============

--------------------------------
    Bespoken Object Notation    
--------------------------------

BespON is a multi-paradigm, extensible configuration language.  Data may be represented in a compact inline form, an indentation-based form, or a section- and keypath-based form. Working with additional data types beyond those in the base specification is simple.


----

::

   % Comments are allowed

   unquoted_key = unquoted_value

   inline_dict = {key1=value1, key2=value2,}  % Trailing commas are valid

   inline_ordered_dict = (odict)> {key1=value1, key2=value2}  % Explicit typing

   list_of_ints_and_floats =  % Several forms of int and float literals
    * 1
    * 0x12
    * 0o755
    * 0b1010
    * 1.2e3
    * -inf
    * 0x4.3p2

   inline_list_of_ints_and_floats = [1, 0x12, 0o755, 0b1010, 1.2e3, -inf, 0x4.3p2]

   'literal string containing whitespace' = "string with escapes!\u{21}\x21"

   empty_strings = ['', ""]

   wrapped_string = """string containing no whitespace lines in which line breaks
       are replaced with spaces, and "quotes" are possible by via delimiters"""

   multiline_literal_string = '''
         A literal string in which linebreaks are kept (as '\n')
           and leading indentation (relative to delimiters) is preserved,
         with special delimiters always on lines by themselves.
       '''/
   
   multiline_literal_string_with_final_newline_stripped = '''
       A multiline literal string with a special closing delimiter.
       '''//

   multiline_escaped_string = """
       The same pattern as multiline literal strings, but different delimiters.
       """/
  
   %%%
   Multiline comments
   use the same syntax
   %%%/

   key1.key2 = true  % Same as "key1 = {key2=true}"

   === section.subsection
   k = v  % Same as "section = {subsection = {k=v} }"
   
   ===/  % Back to root level from most recent "=== <section>..."

   non_ascii = """àáâãäåæ... requires quoting by default for increased clarity 
       and security, but unquoted Unicode can be turned on in the parser"""
  
   quoted_strings_have_flexible_indentation = '''so a string can wrap
   like this if you really don't want to indent'''

   unquoted_values_can_contain_whitespace = but if they wrap onto another
       line in non-inline syntax, relative indentation is required, and no 
       lines consisting only of whitespace are allowed
   
   dict_with_overwritable_values = (overwrite=true)> {toggle=false}
   dict_with_overwritable_values.toggle = true  % No duplicate key error

----


Why?
====

Requisite XKCD reference for new formats:

.. image:: http://imgs.xkcd.com/comics/standards.png
   :target: http://imgs.xkcd.com/comics/standards.png 

What does BespON bring that is lacking in some other formats?

* Comments
* Trailing commas
* Unquoted strings
* Multiline strings, with easy control of leading whitespace and trailing newlines
* Both integers (decimal, hex, octal, binary) and floats (decimal, hex)
* Explicit typing for special or user-defined types
* Control over when dict keys and list elements may be overwritten
* Context-independent special characters that make a list short enough to remember: ``%=,*'"{}[]()``
* Labels, references, and copying
* Sections and keypaths for deeply nested data structures
* Decent performance even when completely implemented in an interpreted language


Getting started
===============

Want to start using BespON now?  A reference implementation is available in Python.  Versions in additional languages may be created as there is interest and time allows.

Want more details, or want to create an implementation in your favorite language?  See the detailed specification.