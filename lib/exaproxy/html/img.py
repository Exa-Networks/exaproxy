# encoding: utf-8
"""
img.py

Created by Thomas Mangin on 2012-02-25.
Copyright (c) 2011-2013 Exa Networks. All rights reserved.
"""

def png (base64):
	return '<img src="data:image/png;base64,%s"/>' % base64

def jpg (base64):
	return '<img src="data:image/jpeg;base64,%s"/>' % base64
