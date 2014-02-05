# Copyright (c) 2011 Vit Suchomel and Jan Pomikalek
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""
A module for converting HTML pages to plain text.
"""

import re

import lxml.etree
import lxml.html

def add_kw_tags(root):
    """
    Surrounds text nodes with <kw></kw> tags. To protect text nodes from
    being removed with nearby tags.
    """
    blank_text = re.compile(u'^\s*$', re.U)
    nodes_with_text = []
    nodes_with_tail = []
    for node in root.iter():
        if node.text and node.tag not in (lxml.etree.Comment, lxml.etree.ProcessingInstruction):
            nodes_with_text.append(node)
        if node.tail:
            nodes_with_tail.append(node)
    for node in nodes_with_text:
        if blank_text.match(node.text):
            node.text = None
        else:
            kw = lxml.etree.Element('kw')
            kw.text = node.text
            node.text = None
            node.insert(0, kw)
    for node in nodes_with_tail:
        if blank_text.match(node.tail):
            node.tail = None
        else:
            kw = lxml.etree.Element('kw')
            kw.text = node.tail
            node.tail = None
            parent = node.getparent()
            parent.insert(parent.index(node) + 1, kw)
    return root

def remove_comments(root):
    "Removes comment nodes."
    to_be_removed = []
    for node in root.iter():
        if node.tag == lxml.etree.Comment:
            to_be_removed.append(node)
    for node in to_be_removed:
        parent = node.getparent()
        del parent[parent.index(node)]

def html2txt(html_text, uhtml_text):
    """
    Converts HTML to DOM and removes unwanted parts.
    Returns the modified DOM transformed back into text.
    """
    if not html_text or not uhtml_text:
        return ''

    #create a root object
    try:
        root = lxml.html.fromstring(uhtml_text)
    except ValueError:
        # Unicode strings with encoding declaration are not supported.
        # for XHTML files with encoding declaration, use the declared encoding
        root = lxml.html.fromstring(html_text)

    # add <kw> tags, protect text nodes
    add_kw_tags(root)
    # remove comments
    remove_comments(root)
    # remove head, script and style
    to_be_removed = []
    for node in root.iter():
        if node.tag in ['head', 'script', 'style']:
            to_be_removed.append(node)
    for node in to_be_removed:
        parent = node.getparent()
        del parent[parent.index(node)]

    #convert root to text
    result = []
    for node in root.iter():
        if node.text:
            result.append(node.text)
    return ' '.join(result)
