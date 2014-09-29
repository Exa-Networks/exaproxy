# encoding: utf-8
"""
manager.py

Created by Thomas Mangin on 2011-11-30.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import time
from exaproxy.util.messagequeue import Queue

from .redirector import RedirectorFactory
from .response import ResponseEncoder as Respond

from exaproxy.util.log.logger import Logger

class RedirectorManager (object):
	def __init__ (self, configuration, poller):
		self.low = configuration.redirector.minimum   # minimum concurrent redirector workers
		self.high = configuration.redirector.maximum  # maximum concurrent redirector workers

		self.poller = poller
		self.configuration = configuration
		self.queue = Queue()    # store requests we do not immediately have the resources to process

		self.nextid = 1         # unique id to give to the next spawned worker
		self.worker = {}        # worker tasks for each spawned child
		self.processes = {}     # worker tasks indexed by file descriptors we can poll
		self.available = set()  # workers that are currently available to handle new requests
		self.active = {}        # workers that are currently busy waiting for a response from the spawned process
		self.stopping = set()   # workers we want to stop as soon as they stop being active

		program = configuration.redirector.program
		protocol = configuration.redirector.protocol
		self.redirector_factory = RedirectorFactory(configuration, program, protocol)

		self.log = Logger('manager', configuration.log.manager)

	def _getid(self):
		wid = str(self.nextid)
		self.nextid += 1
		return wid

	def _spawn (self):
		"""add one worker to the pool"""
		wid = self._getid()

		worker = self.redirector_factory.create(wid)
		self.worker[wid] = worker
		self.available.add(wid)

		if worker.process is not None:
			identifier = worker.process.stdout
			self.processes[identifier] = worker
			self.poller.addReadSocket('read_workers', identifier)

		self.log.info("added a worker")
		self.log.info("we have %d workers. defined range is ( %d / %d )" % (len(self.worker), self.low, self.high))

	def spawn (self, number=1):
		"""create the request number of worker processes"""
		self.log.info("spawning %d more workers" % number)
		for _ in range(number):
			self._spawn()

	def respawn (self):
		"""make sure we reach the minimum number of workers"""
		number = max(min(len(self.worker), self.high), self.low)

		for wid in set(self.worker):
			self.stopWorker(wid)

		self.spawn(number)

	def stopWorker (self, wid):
		self.log.info('want worker %s to go away' % wid)

		if wid not in self.active:
			self.reap(wid)

		else:
			self.stopping.add(wid)

	def reap (self, wid):
		self.log.info('we are killing worker %s' % wid)
		worker = self.worker[wid]

		if wid in self.active:
			self.log.error('reaping worker %s even though it is still active' % wid)
			self.active.pop(wid)

		if wid in self.stopping:
			self.stopping.remove(wid)

		if wid in self.available:
			self.available.remove(wid)

		if worker.process is not None:
			self.poller.removeReadSocket('read_workers', worker.process.stdout)
			self.processes.pop(worker.process.stdout)

		worker.shutdown()
		self.worker.pop(wid)

	def _decrease (self):
		if self.low < len(self.worker):
			wid = self._oldest()
			if wid:
				self.stopWorker(wid)

	def _increase (self):
		if len(self.worker) < self.high:
			self.spawn()

	def decrease (self, count=1):
		for _ in xrange(count):
			self._decrease()

	def increase (self, count=1):
		for _ in xrange(count):
			self._increase()

	def start (self):
		"""spawn our minimum number of workers"""
		self.log.info("starting workers.")
		self.spawn(max(0,self.low-len(self.worker)))

	def stop (self):
		"""tell all our worker to stop reading the queue and stop"""

		for wid in self.worker:
			self.reap(wid)

		self.worker = {}

	def _oldest (self):
		"""find the oldest worker"""
		oldest = None
		past = time.time()
		for wid in set(self.worker):
			creation = self.worker[wid].creation
			if creation < past and wid not in self.stopping:
				past = creation
				oldest = wid

		return oldest

	def startup (self):
		self.spawn(self.low)

	def provision (self):
		"""manage our workers to make sure we have enough to consume the queue"""
		size = self.queue.qsize()
		num_workers = len(self.worker)

		# bad we are bleeding workers !
		if num_workers < self.low:
			self.log.info("we lost some workers, respawing %d new workers" % (self.low - num_workers))
			self.spawn(self.low - num_workers)

		# we need more workers
		if size >= num_workers:
			# nothing we can do we have reach our limit
			if num_workers >= self.high:
				self.log.warning("help ! we need more workers but we reached our ceiling ! %d request are queued for %d processes" % (size,num_workers))
				return
			# try to figure a good number to add ..
			# no less than one, no more than to reach self.high, lower between self.low and a quarter of the allowed growth
			nb_to_add = int(min(max(1,min(self.low,(self.high-self.low)/4)),self.high-num_workers))
			self.log.warning("we are low on workers adding a few (%d), the queue has %d unhandled url" % (nb_to_add,size))
			self.spawn(nb_to_add)

	def deprovision (self):
		"""manage our workers to make sure we have enough to consume the queue"""
		size = self.queue.qsize()
		num_workers = len(self.worker)

		# we are now overprovisioned
		if size < 2 and num_workers > self.low:
			self.log.info("we have too many workers (%d), stopping the oldest" % num_workers)
			# if we have to kill one, at least stop the one who had the most chance to memory leak :)
			wid = self._oldest()
			if wid:
				self.stopWorker(wid)



	def acquire (self):
		identifier = None
		while self.available:
			identifier = self.available.pop()
			if identifier in self.worker:
				break
			else:
				self.log.warning("Worker %s was in available list, but it does not exist anymore" % identifier)
				identifier = None

		if identifier is not None:
			worker = self.worker[identifier]
		else:
			worker = None

		return worker

	def release (self, wid):
		if wid not in self.worker:
			return

		if wid not in self.stopping:
			self.available.add(wid)

		else:
			self.reap(wid)

	def persist (self, wid, client_id, peer, data, header, subheader, source, tainted):
		self.active[wid] = client_id, peer, data, header, subheader, source, tainted

	def progress (self, wid):
		return self.active.pop(wid)

	def doqueue (self):
		if self.available and not self.queue.isempty():
			client_id, peer, header, subheader, source, tainted = self.queue.get()
			_, command, decision = self.request(client_id, peer, header, subheader, source, tainted=tainted)

		else:
			client_id, command, decision = None, None, None

		return client_id, command, decision


	def request (self, client_id, peer, header, subheader, source, tainted=False):
		worker = self.acquire()

		if worker is not None:
			try:
				_, command, decision = worker.decide(client_id, peer, header, subheader, source)

			except:
				command, decision = None, None

			if command is None:
				self.reap(worker.wid)

				if tainted is False:
					_, command, decision = self.request(client_id, peer, header, subheader, source, tainted=True)

				else:
					_, command, decision = Respond.close(client_id)

		else:
			command, decision = None, None
			self.queue.put((client_id, peer, header, subheader, source, tainted))

		if command == 'defer':
			self.persist(worker.wid, client_id, peer, decision, header, subheader, source, tainted)
			command, decision = None, None

		elif worker is not None:
			self.release(worker.wid)

		return client_id, command, decision


	def getDecision (self, pipe_in):
		worker = self.processes.get(pipe_in, None)

		if worker is not None and worker.wid in self.active:
			client_id, peer, request, header, subheader, source, tainted = self.progress(worker.wid)
			try:
				_, command, decision = worker.progress(client_id, peer, request, header, subheader, source)

			except Exception:
				command, decision = None, None

			self.release(worker.wid)

			if command is None:
				self.reap(worker.wid)

				if tainted is False:
					_, command, decision = self.request(client_id, peer, header, subheader, source, tainted=True)

				else:
					_, command, decision = Respond.close(client_id)

		else:
			client_id, command, decision = None, None, None

		if worker is not None and client_id is None:
			self.reap(worker.wid)

		return client_id, command, decision


	def showInternalError(self):
		return 'file', ('200', 'internal_error.html')
