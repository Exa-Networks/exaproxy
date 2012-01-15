#!/usr/bin/env python
# encoding: utf-8
"""
process.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

from threading import Thread
import subprocess
import errno

import os
import time
import socket

from Queue import Queue, Empty
import fcntl

from exaproxy.http.header import Header

from exaproxy.util.logger import logger
from exaproxy.configuration import configuration



def resolve_host(host):
	# Do the hostname resolution before the backend check
	# We may block the page but filling the OS DNS cache can not harm :)
	# XXX: we really need an async dns .. sigh, another thread ?? 
	try:
		ip = socket.gethostbyname(host)
	except socket.error, e:
		ip = None

	return ip



class WorkerManager(object):
	min_worker_count = 4
	max_worker_count = 10

	def __init__(self, low=None, high=None):
		self.workers = {}
		self.queue = Queue()
		self._nextid = 0

		self.low = low or self.min_worker_count
		self.high = max(high or self.max_worker_count, self.low)
		self.running = True

	@property
	def nextid(self):
		self._nextid += 1
		return self._nextid

	def provision(self, program, count=None):
		if self.running is True:
			required = count or max(self.low - len(self.workers), 0)
		else:
			required = 0

		for _ in xrange(required):
			worker = Worker(self.nextid, self.queue, program)
			self.workers[worker.response_box_read] = worker
			worker.start()

		return self.running is True
			
	def putRequest(self, client_id, peer, request):
		return self.queue.put((client_id, peer, request))

	def getDecision(self, box):
		response = box.readline().strip()

		if response == 'shutdown':
			worker = self.workers.get(box, None)
			if worker is not None:
				worker.shutdown()

		try:
			client_id, decision = response.split('\0', 1)
		except (ValueError, TypeError), e:
			client_id = None
			decision = None

		return client_id, decision

	def stop(self):
		# XXX: need to check that the workers do not get stuck
		for worker in self.workers:
			self.queue.put('shutdown')

	#def reprovision(self, program, count=None):
	#	queue = self.queue
	#
	#	# XXX: need to check that the workers do not get stuck
	#
	#	# any new requests will be directed away from the old workers
	#	self.queue = Queue()
	#
	#	for worker in self.workers:
	#		queue.put('shutdown')


class Worker (Thread):
	# TODO : if the program is a function, fork and run :)
	
	def __init__ (self, name, request_box, program):
		# XXX: all this could raise things
		r, w = os.pipe()                              # pipe for communication with the main thread
		self.response_box_write = os.fdopen(w,'w')    # results are written here
		self.response_box_read = os.fdopen(r,'r')     # read from the main thread

		# XXX: Not setting non blocking because it's incompatible with readline()
		# XXX: If responses are not properly terminated then the main process can block
		# XXX: http://bugs.python.org/issue1175#msg56041
		#fl = fcntl.fcntl(self.response_box_read.fileno(), fcntl.F_GETFL)
		#fcntl.fcntl(self.response_box_read.fileno(), fcntl.F_SETFL, fl | os.O_NONBLOCK)

		self.wid = name                               # a unique name
		self.creation = time.time()                   # when the thread was created
	#	self.last_worked = self.creation              # when the thread last picked a task
		self.request_box = request_box                # queue with HTTP headers to process

		self.program = program                        # the squid redirector program to fork 
		self.running = True                           # the thread is active

		self.process = self._createProcess()          # the forked program to handle classification
		Thread.__init__(self)

	def _createProcess (self):
		try:
			process = subprocess.Popen([self.program,],
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				universal_newlines=True,
			)
			logger.debug('worker %d' % self.wid,'spawn process %s' % self.program)
		except KeyboardInterrupt:
			process = None
		except (subprocess.CalledProcessError,OSError,ValueError):
			logger.error('worker %d' % self.wid,'could not spawn process %s' % self.program)
			process = None

		return process

	def _shutdown (self):
		# XXX: can raise
		self.response_box_read.close()
		self.response_box_write.close()

		if self.process:
			logger.info('worker %d' % self.wid, 'Shutting down but the child process is still running. Stopping it')
			self._stop()
			
	def _stop(self):
		logger.info('worker %d' % self.wid,'terminating process')

		try:
			if self.process:
				self.process.terminate()
				self.process.wait()
		except OSError, e:
			# No such processs
			if e[0] != errno.ESRCH:
				logger.error('worker %d' % self.wid,'PID %s died' % pid)

	def _classify (self, client_ip, method, url):
		squid = '%s %s - %s -' % (url, client_ip, method)
		#logger.info('worker %d' % self.wid, 'sending to classifier: [%s]' % squid)
		try:
			self.process.stdin.write(squid + os.linesep)

			response = self.process.stdout.readline().strip()
			#logger.info('worker %d' % self.wid, 'received from classifier: [%s]' % response)
			return response
		except IOError, e:
			logger.error('worker %d' % self.wid, 'IO/Error when sending to process: %s' % str(e))
			return 'file://internal_error.html'

	def respond(self, response):
		self.response_box_write.write(response + os.linesep)
		self.response_box_write.flush()

	def respond_proxy(self, client_id, ip, port, request):
		if 'proxy-connection' in request:
			request['proxy-connection'] = 'Connection: close'
		# We NEED Connection: close
		request['connection'] = 'Connection: close'
		# We NEED to add a Via field http://tools.ietf.org/html/rfc2616#section-14.45
		via = 'Via: %s %s, %s %s' % (request.version, 'ExaProxy-%s-%d' % (configuration.VERSION,os.getpid()), '1.1', request.host)
		if 'via' in request:
			request['via'] = '%s\0%s' % (request['via'],via)
		else:
			request['via'] = via
		#request['via'] = 'Via: %s %s, %s %s' % (request.version, 'ExaProxy-%s-%d' % ('test',os.getpid()), '1.1', request.host)
		header = request.toString(linesep='\0')
		self.respond('\0'.join((client_id, 'download', ip, str(port), header)))
	
	def respond_connect(self, client_id, ip, port, request):
		header = request.toString(linesep='\0')
		self.respond('\0'.join((client_id, 'connect', ip, str(port), header)))

	def respond_file(self, client_id, code, reason):
		self.respond('\0'.join((client_id, 'file', str(code), reason)))

	def respond_html(self, client_id, code, *data):
		self.respond('\0'.join((client_id, 'html', str(code))+data))

	def respond_shutdown(self):
		self.respond('shutdown')


	def run(self):
		while self.running:
			try:
				logger.debug('worker %d' % self.wid,'waiting for some work')
				# XXX: pypy ignores the timeout
				data = self.request_box.get(3)

				# check if we were told to stop
				if data == 'shutdown':
					logger.debug('worker %d' % self.wid, 'Received command to stop')
					break

				client_id, peer, header = data
			except Empty:
				continue
			except (ValueError, TypeError), e:
				logger.debug('worker %d' % self.wid, 'Received invalid message: %s' % data)

			if not self.running:
				logger.debug('worker %d' % self.wid, 'Consumed a message before we knew we should stop. Handling it before hangup')

			request = Header(header)
			if not request.isValid():
				self.respond_html(client_id, 400, ('This request does not conform to HTTP/1.1 specifications <!--\n<![CDATA[%s]]>\n-->\n' % str(header)).replace(os.linesep, '\0'))
				continue

			ipaddr = resolve_host(request.host)
			if not ipaddr:
				logger.warning('worker %d' % self.wid,'Could not resolve %s' % request.host)
				self.respond_html(client_id, 503, 'file://dns.html')
				continue

			# classify and return the filtered page
			if request.method in ('GET', 'PUT', 'POST'):
				redirected = self._classify(ipaddr, request.method, request.url)

				if redirected.startswith('file://'):
					self.respond_html(client_id, '250', redirected)
					continue
				elif redirected.startswith('http://'):
					request.redirect(host, path)
					self.respond_proxy(client_id, ipaddr, request.port, request)
					continue
				else:
					self.respond_proxy(client_id, ipaddr, request.port, request)
					continue

			# someone want to use us as https proxy
			if request.method == 'CONNECT':
				# we do allow connect
				if configuration.CONNECT:
					self.respond_connect(client_id, ipaddr, request.port, request)
					continue
				else:
					self.respond_html(client_id, 501, 'CONNECT NOT ALLOWED', 'We are an HTTP only proxy')
					continue

			if method in ('TRACE',):
				self.respond_html(client_id, 501, 'TRACE NOT IMPLEMENTED', 'This is bad .. we are sorry.')
				continue

			self.respond_html(client_id, 405, 'METHOD NOT ALLOWED', 'Method Not Allowed')
			continue

		# stop the child process
		self._stop()

		# tell the reactor that we've stopped
		self.respond_shutdown()

			# prevent persistence : http://tools.ietf.org/html/rfc2616#section-8.1.2.1
			# XXX: We may have more than one Connection header : http://tools.ietf.org/html/rfc2616#section-14.10
			# XXX: We may need to remove every step-by-step http://tools.ietf.org/html/rfc2616#section-13.5.1
			# XXX: We NEED to respect Keep-Alive rules http://tools.ietf.org/html/rfc2068#section-19.7.1
			# XXX: We may look at Max-Forwards
			# XXX: We need to reply to "Proxy-Connection: keep-alive", with "Proxy-Connection: close"
			# http://homepage.ntlworld.com./jonathan.deboynepollard/FGA/web-proxy-connection-header.html
