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
	def __init__ (self,program,low=1,high=40):
		self.nbq = 0                      # number of request waiting to be filtered
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
		logger.debug('manager','we are killing worker %d' % wid)
		worker = self.worker[wid]
		self.results.pop(worker.response_box_read)
		self.worker.pop(wid)
		worker.shutdown()

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
		
		size = self.nbq
		num_workers = len(self.worker)

		# we are now overprovisioned
		if size < num_workers:
			if size <= self.low:
				return
			logger.debug('manager',"we have too many workers, killing the oldest")
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
		self.nbq += 1
		return self.queue.put((client_id, peer, request))

	def getDecision(self, box):
		# XXX: reads may block if we send badly formatted data
		self.nbq -=1
		try:
			r_buffer = box.read(3)
			while r_buffer.isdigit():
				r_buffer += box.read(1)

			if ':' in r_buffer:
				size, response = r_buffer.split(':', 1)
				if size.isdigit():
					size = int(size)
				else:
					size, response = None, None
			else:   # not a netstring
				size, response = None, None

			if size is not None:
				required = size + 1 - len(response)
				response += box.read(required)

			if response is not None:
				if response.endswith(','):
					response = response[:-1]
				else:
					response = None

		except ValueError, e: # I/O operation on closed file
			worker = self.workers.get(box, None)
			if worker is not None:
				worker.destroyProcess()

			response = None
		except TypeError, e:
			response = None

		try:
			if response:
				client_id, decision = response.split('\0', 1)
			else:
				client_id = None
				decision = None
		except (ValueError, TypeError), e:
			client_id = None
			decision = None

		return client_id, decision
