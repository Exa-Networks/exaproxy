# encoding: utf-8

try:
	from collections import OrderedDict
except ImportError:
	# support installable ordereddict module in older python versions
	from ordereddict import OrderedDict

from time import time

class TimeCache (dict):
	__default = object()

	def __init__ (self,timeout):
		self.timeout = timeout
		self.last = None
		self.time = OrderedDict()
		dict.__init__(self)

	def __setitem__ (self,key,value):
		dict.__setitem__(self,key,value)
		if self.timeout > 0:
			self.time[key] = time()

	def __delitem__ (self,key):
		if key in self.time:
			del self.time[key]
		dict.__delitem__(self,key)

	# Cpython implementation of dict.pop does not call __delitem__ - sigh !
	def pop (self,key,default=__default):
		if key in self.time:
			del self.time[key]
		if default is self.__default:
			return dict.pop(self,key)
		return dict.pop(self,key,default)

	def expired (self,maximum):
		expire = time() - self.timeout

		if self.last:
			k,t = self.last
			if t > expire:
				return
			if k in self:
				maximum -= 1
				yield k
			self.last = None

		while self.time and maximum:
			k,t = self.time.popitem(False)
			if t > expire:
				self.last = k,t
				break
			if k in self:
				maximum -= 1
				yield k
