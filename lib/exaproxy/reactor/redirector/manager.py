# encoding: utf-8
"""
manager.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import time
from Queue import Queue

from .worker import Redirector

from exaproxy.util.log.logger import Logger
# Do we really need to call join() on the thread as we are stoppin on our own ?

class RedirectorManager (object):
	def __init__ (self,configuration,poller):
		self.configuration = configuration

		self.low = configuration.redirector.minimum       # minimum number of workers at all time
		self.high = configuration.redirector.maximum      # maximum numbe of workers at all time
		self.program = configuration.redirector.program   # what program speaks the squid redirector API

		self.nbq = 0                      # number of request waiting to be filtered
		self.nextid = 1                   # incremental number to make the name of the next worker
		self.queue = Queue()              # queue with HTTP headers to process
		self.poller = poller              # poller interface that checks for events on sockets
		self.worker = {}                  # our workers threads
		self.closing = {}                 # workers that are currently closing and must be joined with when they are ready
		self.running = True               # we are running

		self.log = Logger('manager', configuration.log.manager)

	def _getid(self):
		id = str(self.nextid)
		self.nextid +=1
		return id

	def _spawn (self):
		"""add one worker to the pool"""
		wid = self._getid()

		worker = Redirector(self.configuration,wid,self.queue,self.program)
		self.poller.addReadSocket('read_workers', worker.response_box_read)
		self.worker[wid] = worker
		self.log.info("added a worker")
		self.log.info("we have %d workers. defined range is ( %d / %d )" % (len(self.worker),self.low,self.high))
		self.worker[wid].start()

	def spawn (self,number=1):
		"""create the set number of worker"""
		self.log.info("spawning %d more worker" % number)
		for _ in range(number):
			self._spawn()

	def respawn (self):
		"""make sure we reach the minimum number of workers"""
		number = max(min(len(self.worker),self.high),self.low)
		for wid in set(self.worker):
			self.reap(wid)
		self.spawn(number)

	def reap (self,wid):
		self.log.info('we are killing worker %s' % wid)
		worker = self.worker[wid]
		self.worker.pop(wid)
		self.closing[wid] = worker
		worker.stop()  # will cause the worker to stop when it can

	def start (self):
		"""spawn our minimum number of workers"""
		self.log.info("starting workers.")
		self.spawn(max(0,self.low-len(self.worker)))

	def stop (self):
		"""tell all our worker to stop reading the queue and stop"""
		self.running = False
		threads = self.worker.values() + self.closing.values()
		if len(self.worker):
			self.log.info("stopping %d workers." % len(self.worker))
			for wid in set(self.worker):
				self.reap(wid)
			for thread in threads:
				self.request(None, None, None, 'nop')
			for thread in threads:
				thread.destroyProcess()
				thread.join()

		self.worker = {}
		self.closing = {}

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

		# bad we are bleeding workers !
		if num_workers < self.low:
			self.log.info("we lost some workers, respawing")
			self.spawn(self.low-num_workers)
			return

		# we are now overprovisioned
		if size < num_workers:
			if size <= self.low:
				return
			self.log.info("we have too many workers, killing the oldest")
			# if we have to kill one, at least stop the one who had the most chance to memory leak :)
			worker = self._oldest()
			if worker:
				self.reap(worker.wid)
		# we need more workers
		else:
			# nothing we can do we have reach our limit
			if num_workers >= self.high:
				self.log.warning("we need more workers but we reached our ceiling ! help ! %d request are queued" % size)
				return
			# try to figure a good number to add ..
			# no less than one, no more than to reach self.high, lower between self.low and a quarter of the allowed growth
			nb_to_add = int(min(max(1,min(self.low,(self.high-self.low)/4)),self.high-num_workers))
			self.log.warning("we are low on workers, adding a few (%d)" % nb_to_add)
			self.spawn(nb_to_add)

	def request(self, client_id, peer, request, source):
		self.nbq += 1
		return self.queue.put((client_id,peer,request,source,False))

	def getDecision(self, box):
		# NOTE: reads may block if we send badly formatted data
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

		except ValueError:  # I/O operation on closed file
			worker = self.worker.get(box, None)
			if worker is not None:
				worker.destroyProcess()

			response = None
		except TypeError:
			response = None

		try:
			if response:
				client_id, command, decision = response.split('\0', 2)
			else:
				client_id = None
				command = None
				decision = None

		except (ValueError, TypeError):
			client_id = None
			command = None
			decision = None

		if command == 'requeue':
			_client_id, _peer, _source, _header = response.split('\0', 3)
			self.queue.put((_client_id,_peer,_header,_source,True))

			client_id = None
			command = None
			decision = None

		elif command == 'hangup':
			wid = decision
			client_id = None
			command = None
			decision = None

			worker = self.worker.pop(wid, None)

			if worker:
				self.poller.removeReadSocket('read_workers', worker.response_box_read)
			else:
				worker = self.closing.pop(wid, None)

			if worker:
				worker.shutdown()
				worker.join()

		elif command == 'stats':
			wid, timestamp, stats = decision
			self.storeStats(timestamp, wid, stats)

			client_id = None
			command = None
			decision = None

		return client_id, command, decision

	def showInternalError(self):
		return 'file', '\0'.join(('200', 'internal_error.html'))

	def requestStats(self):
		for wid, worker in self.worker.iteritems():
			worker.requestStats()

	def storeStats(self, timestamp, wid, stats):
		pairs = (d.split('=',1) for d in stats.split('?', 1).split('&'))
		d = self.cache.setdefault(timestamp, {})

		for k, v in pairs:
			d.setdefault(k, []).append(v)
