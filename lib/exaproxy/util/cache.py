# encoding: utf-8

from collections import deque
from time import time

class TimeCache (dict):
	def __init__ (self,timeout):
		self.timeout = timeout
		self.queued = deque()
		dict.__init__(self)

	def __setitem__ (self,key,value):
		dict.__setitem__(self,key,value)
		self.queued.append((time(),key))

	def expired (self,maximum):
		expire = time() - self.timeout
		while self.queued and maximum:
			t,k = self.queued.popleft()
			if self.timeout <= 0:
				continue
			if k not in self:
				continue
			maximum -= 1
			if t <= expire:
				yield k
				continue
			self.queued.appendleft((t,k))
			break
