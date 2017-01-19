# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#

'''
Abstract syntax tree (AST) elements.
'''

# pylint: disable=C0103
from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

from . import erring
import sys


# pylint: disable=E0602, W0622
if sys.version_info.major == 2:
    str = unicode
    __chr__ = chr
    chr = unichr
# pylint: enable=E0602, W0622







_astobj_common_slots = ['ast',
                        'cat', 'tag',
                        'depth', 'parent', 'index',
                        'indent', 'at_line_start', 'inline', 'inline_indent',
                        'first_lineno', 'first_column',
                        'last_lineno', 'last_column',
                        'finalized', 'final_val', 'extra_dependents']

_astobj_stringlike_slots = ['delim', 'block']

_astobj_collection_slots = ['keypath_parent', 'keypath_traversable',
                            'open', 'unresolved_children',
                            'check_append_scalar_key',
                            'check_append_scalar_val',
                            'check_append_collection',
                            'check_append_keypath']

_astobj_dictlike_slots = ['next_key', 'awaiting_val']

_astobj_tag_slots = ['type', 'mutable', 'placeholder_obj',
                     'label', 'newline',
                     'collection_config_type', 'collection_config_args']
