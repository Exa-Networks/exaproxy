#!/usr/bin/env python
# encoding: utf-8
"""
monitor.py

Created by Thomas Mangin on 2012-02-05.
Copyright (c) 2012 Exa Networks. All rights reserved.
"""

class _Container (object):
	def __init__ (self,supervisor):
		self.supervisor = supervisor

class Monitor (object):
	
	def __init__(self,supervisor):
		self._container = _Container(supervisor)

	def introspection (self,objects):
		obj = self._container
		ks = [_ for _ in dir(obj) if not _.startswith('__') and not _.endswith('__')]

		for key in objects:
			if not key in ks:
				raise StopIteration()
			obj = getattr(obj,key)
			ks = [_ for _ in dir(obj) if not _.startswith('__') and not _.endswith('__')]

		for k in ks:
			value = str(getattr(obj,k))
			if value.startswith('<bound method'):
				continue
			yield k, value
