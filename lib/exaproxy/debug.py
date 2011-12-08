#!/usr/bin/env python
# encoding: utf-8
"""
debug.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import os
import sys

import traceback

from .logger import Logger
logger = Logger()

from .configuration import Configuration
debug = Configuration().DEBUG.PDB

def bug_report (type, value, trace):
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-'*80
	print >> sys.stderr, '-- Please provide the information below on :'
	print >> sys.stderr, '-- http://code.google.com/p/exaproxy/issues/entry'
	print >> sys.stderr, '-'*80
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-- Logging History'
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, logger.history()
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-- Traceback'
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	traceback.print_exception(type,value,trace)
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	print >> sys.stderr, '-'*80
	print >> sys.stderr, '-- Please provide the information above on :'
	print >> sys.stderr, '-- http://code.google.com/p/exaproxy/issues/entry'
	print >> sys.stderr, '-'*80
	print >> sys.stderr, ''
	print >> sys.stderr, ''
	
	#print >> sys.stderr, 'the program failed with message :', value

if debug is None:
	def intercept (type, value, trace):
		bug_report(type, value, trace)
	sys.excepthook = intercept
elif debug not in ['0','']:
	def intercept (type, value, trace):
		bug_report(type, value, trace)
		import pdb
		pdb.pm()
	sys.excepthook = intercept

del sys.argv[0]

if sys.argv:
	__file__ = os.path.abspath(sys.argv[0])
	__name__ = '__main__'
	logger.debug('%s' % sys.argv[0],'starting')
	execfile(sys.argv[0])
