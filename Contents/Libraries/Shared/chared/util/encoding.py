#!/usr/bin/env python
#
# Copyright (c) 2011 Vit Suchomel and Jan Pomikalek
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""
A module for extracting character encoding information from headers of
HTML pages.
"""

import re
import sys

def normalize_encoding(encoding):
    "Returns a normalized form of the encoding."
    import encodings
    norm = encodings.normalize_encoding(encoding).lower()
    if norm in encodings.aliases.aliases.values():
        return norm
    return encodings.aliases.aliases.get(norm)

def get_encoding(html_string):
    """
    Performs a simple RE based parsing of a HTML page (represented as a
    string) and extracts declared character encoding from the meta tags.
    If the extraction is successful, the encoding is returned. Otherwise,
    None is returned.
    """
    re_meta1 = re.compile('''<meta\s+http-equiv=['"]?content-type['"]?\s+content=['"]?[^'"]*charset=([^'"]+)''', re.I)
    re_meta2 = re.compile('''<meta\s+content=['"]?[^'"]*charset=([^'"]+)['"]?\s+http-equiv=['"]?content-type['"]?''', re.I)
    re_meta3 = re.compile('''<meta\s+http-equiv=['"]?charset['"]?\s+content=['"]?([^'"]+)''', re.I)
    re_meta4 = re.compile('''<meta\s+content=['"]?([^'"]+)['"]?\s+http-equiv=['"]?charset['"]?''', re.I)
    re_meta5 = re.compile('''<meta\s+charset=['"]?([^'"]+)''', re.I)
    for re_meta in (re_meta1, re_meta2, re_meta3, re_meta4, re_meta5):
        m = re_meta.search(html_string)
        if m:
            meta_encoding = m.group(1)
            return normalize_encoding(meta_encoding)
    return None

def main(html_file):
    html_string = open(html_file, 'r').read()
    print get_encoding(html_string)

if __name__ == "__main__":
    main(*sys.argv[1:])
