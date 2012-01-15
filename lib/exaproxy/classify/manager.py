#!/usr/bin/env python
# encoding: utf-8
"""
manager.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

import time
from Queue import Queue, Empty

from .worker import Worker

from exaproxy.util.logger import logger

# Do we really need to call join() on the thread as we are stoppin on our own ? 

class WorkerManager (object):
	def __init__ (self,program,low=4,high=40):
		self.nextid = 1                   # incremental number to make the name of the next worker
		self.queue = Queue()              # queue with HTTP headers to process
		self.program = program            # what program speaks the squid redirector API
		self.low = low                    # minimum number of workers at all time
		self.high = high                  # maximum numbe of workers at all time
		self.worker = {}                  # our workers threads
		self.results = {}                 # pipes connected to each worker
		self.running = True               # we are running
		self.workers = set()

	def _spawn (self):
		"""add one worker to the pool"""
		worker = Worker(self.nextid,self.queue,self.program)
		self.workers.add(worker.response_box_read)
		self.worker[self.nextid] = worker
		self.results[worker.response_box_read] = self.worker
		logger.debug('manager',"added a worker")
		logger.debug('manager',"we have %d workers. defined range is ( %d / %d )" % (len(self.worker),self.low,self.high))
		self.worker[self.nextid].start()
		self.nextid += 1

		def spawn (self,number=1):
			"""create the set number of worker"""
			logger.info('manager',"spawning %d more worker" % number)
			for _ in range(number):
				self._spawn()

		def respawn (self):
			"""make sure we reach the minimum number of workers"""
			number = max(min(len(self.worker),self.high),self.low)
			for wid in set(self.worker):
				self.reap(wid)
			self.spawn(number)

	def reap (self,wid):
		worker = self.worker[wid]
		self.workers.remove(worker.response_box_read)
		del self.results[worker.response_box_read]
		del self.worker[wid]
		worker.stop()
		logger.info('manager',"removed worker %d" % wid)
		logger.debug('manager',"we have %d workers. defined range is ( %d / %d )" % (len(self.worker),self.low,self.high))

	def start (self):
		"""spawn our minimum number of workers"""
		logger.info('manager',"starting workers.")
		self.spawn(max(0,self.low-len(self.worker)))

	def stop (self):
		"""tell all our worker to stop reading the queue and stop"""
		self.running = False
		threads = [w for _,w in self.worker.iteritems()]
		if len(self.worker):
			logger.info('manager',"stopping %d workers." % len(self.worker))
			for wid in set(self.worker):
				self.reap(wid)
			for thread in threads:
				thread.join()

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
		
		size = self.queue.qsize()
		num_workers = len(self.worker)

		# we are now overprovisioned
		if size < num_workers:
			if size <= self.low:
				logger.debug('manager',"no changes in the number of worker required")
				return
			logger.info('manager',"we have too many workers, killing one")
			# if we have to kill one, at least stop the one who had the most chance to memory leak :)
			worker = self._oldest()
			if worker:
				self.reap(worker.wid)
		# we need more workers
		else:
			# bad we are bleeding workers !
			if num_workers < self.low:
				logger.info('manager',"we lost some workers, respawing")
				self.respawn()
			# nothing we can do we have reach our limit
			if num_workers >= self.high:
				logger.warning('manager',"we need more workers by we reach our ceiling ! help !")
				return
			# try to figure a good number to add .. 
			# no less than one, no more than to reach self.high, lower between self.low and a quarter of the allowed growth
			nb_to_add = int(min(max(1,min(self.low,(self.high-self.low)/4)),self.high-num_workers))
			logger.warning('manager',"we are low on workers, adding a few (%d)" % nb_to_add)
			self.spawn(nb_to_add)
			
	def request(self, client_id, peer, request):
		return self.queue.put((client_id, peer, request))

	def getDecision(self, box):
		response = box.readline().strip()

		if response == 'down':
			# XXX: AFAICS box will never have worker (and this is broken but harmless)
			worker = self.workers.get(box, None)
			if worker is not None:
				worker.shutdown()

		try:
			client_id, decision = response.split('\0', 1)
		except (ValueError, TypeError), e:
			client_id = None
			decision = None

		return client_id, decision
