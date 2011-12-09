#!/usr/bin/env python
# encoding: utf-8
"""
manager.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import time

from .worker import Worker

from .logger import Logger
logger = Logger()

# Do we really need to call join() on the thread as we are stoppin on our own ? 

class Manager (object):
	def __init__ (self,request_box,program,low=4,high=40):
		self.nextid = 1                   # incremental number to make the name of the next worker
		self.request_box = request_box    # queue with HTTP headers to process
		self.program = program            # what program speaks the squid redirector API
		self.low = low                    # minimum number of workers at all time
		self.high = high                  # maximum numbe of workers at all time
		self.worker = {}                  # our workers threads
		self.results = {}                 # pipes connected to each worker
		self.running = True               # we are running

	def _spawn (self):
		"""add one worker to the pool"""
		worker = Worker(self.nextid,self.request_box,self.download_pipe,self.program)
		self.worker[self.nextid] = worker
		self.results[worker.response_box] = self.worker
		logger.worker("added a worker")
		logger.worker("we have %d workers. defined range is ( %d / %d )" % (len(self.worker),self.low,self.high))
		self.worker[self.nextid].start()
		self.nextid += 1

	def _reap (self,wid):
		return # to test if a bug is related to killing (we must make sure the worker is idle)
		self.worker[wid].stop()
		del self.results[self.worker[wid].response_box]
		del self.worker[wid]
		logger.worker("removed a worker")
		logger.worker("we have %d workers. defined range is ( %d / %d )" % (len(self.worker),self.low,self.high))

	def spawn (self,number):
		"""create the set number of worker"""
		logger.worker("spawning %d more worker" % number)
		for _ in range(number):
			self._spawn()

	def respawn (self):
		"""make sure we reach the minimum number of workers"""
		number = max(min(len(self.worker),self.high),self.low)
		for wid in set(self.worker):
			self._reap(wid)
		self.spawn(number)

	def start (self):
		"""spawn our minimum number of workers"""
		logger.worker("starting workers.")
		self.spawn(max(0,self.low-len(self.worker)))

	def stop (self):
		"""tell all our worker to stop reading the queue and stop"""
		self.running = False
		if len(self.worker):
			logger.worker("stopping %d workers." % len(self.worker))
			for wid in set(self.worker):
				self._reap(wid)

	def _oldest (self):
		"""find the oldest worker"""
		oldest = None
		past = time.time()
		for wid in set(self.worker):
			creation = self.worker[wid].creation
			if creation < past:
				past = creation
				oldest = self.worker[wid]
		return oldest

	def provision (self):
		"""manage our workers to make sure we have enough to consume the queue"""
		if not self.running:
			return
		
		size = self.request_box.qsize()
		num_workers = len(self.worker)

		# we are now overprovisioned
		if size < num_workers:
			if size <= self.low:
				#logger.worker("no changes in the number of worker required")
				return
			logger.worker("we have too many workers, killing one")
			# if we have to kill one, at least stop the one who had the most chance to memory leak :)
			worker = self._oldest()
			if worker:
				self._reap(worker.wid)
		# we need more workers
		else:
			# bad we are bleeding workers !
			if num_workers < self.low:
				logger.worker("we lost some workers, respawing")
				self.respawn()
			# nothing we can do we have reach our limit
			if num_workers >= self.high:
				logger.worker("we need more workers by we reach our ceiling ! help !")
				return
			# try to figure a good number to add .. 
			# no less than one, no more than to reach self.high, lower between self.low and a quarter of the allowed growth
			nb_to_add = int(min(max(1,min(self.low,(self.high-self.low)/4)),self.high-num_workers))
			logger.worker("we are low on workers, adding a few (%d)" % nb_to_add)
			self.spawn(nb_to_add)
			
