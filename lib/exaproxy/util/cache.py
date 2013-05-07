# encoding: utf-8

from collections import OrderedDict
from time import time

class TimeCache (dict):
	def __init__ (self,timeout):
		self.timeout = timeout
		self.last = None
		self.time = OrderedDict()
		dict.__init__(self)

	def __setitem__ (self,key,value):
		dict.__setitem__(self,key,value)
		if self.timeout > 0:
			self.time[key] = time()

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
