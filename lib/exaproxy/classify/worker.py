#!/usr/bin/env python
# encoding: utf-8
"""
process.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

from threading import Thread
from Queue import Empty
import subprocess
import errno

import os
import time
import socket

#import fcntl

from exaproxy.http.header import Header

from exaproxy.util.logger import logger

class Worker (Thread):
	# TODO : if the program is a function, fork and run :)
	
	def __init__ (self, configuration, name, request_box, program):
		self.configuration = configuration
		self.enabled = configuration.redirector.enabled
		self.transparent = configuration.http.transparent

		# XXX: all this could raise things
		r, w = os.pipe()                                # pipe for communication with the main thread
		self.response_box_write = os.fdopen(w,'w',0)    # results are written here
		self.response_box_read = os.fdopen(r,'r',0)     # read from the main thread

		self.wid = name                               # a unique name
		self.creation = time.time()                   # when the thread was created
	#	self.last_worked = self.creation              # when the thread last picked a task
		self.request_box = request_box                # queue with HTTP headers to process

		self.program = program                        # the squid redirector program to fork 
		self.running = True                           # the thread is active

		self.stats_timestamp = None			# time of the most recent outstanding request to generate stats

		# Do not move, we need the forking AFTER the setup
		self.process = self._createProcess()          # the forked program to handle classification
		Thread.__init__(self)

	def _createProcess (self):
		if not self.enabled:
			return
		try:
			process = subprocess.Popen([self.program,],
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				universal_newlines=True,
			)
			logger.debug('worker %s' % self.wid,'spawn process %s' % self.program)
		except KeyboardInterrupt:
			process = None
		except (subprocess.CalledProcessError,OSError,ValueError):
			logger.error('worker %s' % self.wid,'could not spawn process %s' % self.program)
			process = None
		return process

	def destroyProcess (self):
		if not self.enabled:
			return
		logger.debug('worker %s' % self.wid,'destroying process %s' % self.program)
		if not self.process:
			return
		try:
			if self.process:
				self.process.terminate()
				self.process.wait()
				logger.info('worker %s' % self.wid,'terminated process PID %s' % self.process.pid)
		except OSError, e:
			# No such processs
			if e[0] != errno.ESRCH:
				logger.error('worker %s' % self.wid,'PID %s died' % self.process.pid)

	def stop (self):
		logger.debug('worker %s' % self.wid,'shutdown')
		# The worker thread may be blocked reading from the queue
		# so the shutdown will not be immediate
		self.running = False


	def _classify (self, client_ip, method, url, tainted):
		squid = '%s %s - %s -' % (url, client_ip, method)
		#logger.info('worker %s' % self.wid, 'sending to classifier: [%s]' % squid)
		if not self.process:
			logger.error('worker %s' % self.wid, 'No more process to evaluate: %s' % str(e))
			classification, data = 'file', 'internal_error.html'
			return

		try:
			self.process.stdin.write(squid + os.linesep)
			response = self.process.stdout.readline().strip()

			if not response:
				classification, data = 'permit', None

			elif response.startswith('http://'):
				response = response[7:]

				if response == url:
					classification, data = 'permit', None
				elif response.startswith(url.split('/', 1)[0]+'/'):
					classification, data = 'rewrite', ('/'+response.split('/', 1)[1]) if '/' in url else ''
				else:
					classification, data = 'redirect', 'http://' + response

			elif response.startswith('file://'):
				classification, data = 'file', response[7:]

			elif response.startswith('dns://'):
				classification, data = 'dns', response[6:]

			else:
				classification, data = 'file', 'internal_error.html'

		except IOError, e:
			logger.error('worker %s' % self.wid, 'IO/Error when sending to process: %s' % str(e))
			if tainted is False:
				classification, data = 'requeue', None
			else:
				classification, data = 'file', 'internal_error.html'

		return classification, data

	def respond(self, response):
		self.response_box_write.write(str(len(response)) + ':' + response + ',')
		self.response_box_write.flush()

	def respond_proxy(self, client_id, ip, port, request):
		# We NEED Connection: close
		request['connection'] = 'Connection: close'
		# http://homepage.ntlworld.com./jonathan.deboynepollard/FGA/web-proxy-connection-header.html
		request.pop('proxy-connection',None)
		# XXX: To be RFC compliant we need to add a Via field http://tools.ietf.org/html/rfc2616#section-14.45 on the reply too
		# XXX: At the moment we only add it from the client to the server (which is what really matters)
		if not self.transparent:
			via = 'Via: %s %s, %s %s' % (request.version, 'ExaProxy-%s-%d' % (self.configuration.proxy.version,os.getpid()), '1.1', request.host)
			if 'via' in request:
				request['via'] = '%s\0%s' % (request['via'],via)
			else:
				request['via'] = via
			#request['via'] = 'Via: %s %s, %s %s' % (request.version, 'ExaProxy-%s-%d' % ('test',os.getpid()), '1.1', request.host)
		header = request.toString()
		self.respond('\0'.join((client_id, 'download', ip, str(port), header)))

	def respond_connect(self, client_id, ip, port, request):
		header = request.toString()
		self.respond('\0'.join((client_id, 'connect', ip, str(port), header)))

	def respond_file(self, client_id, code, reason):
		self.respond('\0'.join((client_id, 'file', str(code), reason)))

	def respond_rewrite(self, client_id, code, reason, protocol, url, host, client_ip):
		self.respond('\0'.join((client_id, 'rewrite', str(code), reason, protocol, url, host, str(client_ip))))

	def respond_html(self, client_id, code, *data):
		self.respond('\0'.join((client_id, 'html', str(code))+data))

	def respond_monitor(self, client_id, path):
		self.respond('\0'.join((client_id, 'monitor', path)))

	def respond_redirect(self, client_id, url):
		self.respond('\0'.join((client_id, 'redirect', url)))

	def respond_stats(self, wid, timestamp, stats):
		self.respond('\0'.join((wid, 'stats', timestamp, stats)))

	def respond_requeue(self, client_id, peer, header, source):
		# header and source are flipped to make it easier to split the values
		self.respond('\0'.join((client_id, peer, source, header)))

	def respond_hangup(self, wid):
		self.respond('\0'.join(('', 'hangup', wid)))

	def run (self):
		while self.running:
			logger.debug('worker %s' % self.wid,'waiting for some work')
			try:
				# The timeout is really caused by the SIGALARM sent on the main thread every second 
				# BUT ONLY IF the timeout is present in this call
				data = self.request_box.get(2) 
			except Empty:
				if self.enabled:
					if not self.process or self.process.poll() is not None:
						if self.running:
							logger.error('worker %s' % self.wid, 'forked process died !')
						self.running = False
						continue
			except ValueError, e:
				logger.error('worker %s' % self.wid, 'Problem reading from request_box')
				continue

			try:
				client_id, peer, header, source, tainted = data
			except TypeError, e:
				logger.alert('worker %s' % self.wid, 'Received invalid message: %s' % data)
				continue

			if self.enabled:
				if not self.process or self.process.poll() is not None:
					if self.running:
						logger.error('worker %s' % self.wid, 'forked process died !')
					self.running = False
					if source != 'nop':
						self.respond_requeue(client_id, peer, header, source)
					break

			stats_timestamp = self.stats_timestamp
			if stats_timestamp:
				# XXX: is this actually atomic as I am guessing?
				# There's a race condition here if not. We're unlikely to hit it though, unless 
				# the classifier can take a long time
				self.stats_timestamp = None if stats_timestamp == stats_timestamp else self.stats_timestamp

				# we still have work to do after this so don't continue
				stats = self._stats()
				self.respond_stats(self.wid, stats)

			if not self.running:
				logger.debug('worker %s' % self.wid, 'Consumed a message before we knew we should stop. Handling it before hangup')

			if source == 'nop':
				continue

			request = Header(self.configuration,header,peer)
			if not request.isValid():
				self.respond_html(client_id, 400, ('This request does not conform to HTTP/1.1 specifications <!--\n<![CDATA[%s]]>\n-->\n' % str(header)))
				continue

			if source == 'web':
				self.respond_monitor(client_id, request.path)
				continue

			if not self.enabled:
				self.respond_proxy(client_id, request.host, request.port, request)
				continue

			# classify and return the filtered page
			if request.method in ('GET', 'PUT', 'POST'):
				classification, data = self._classify(request.client, request.method, request.url_noport, tainted)

				if classification == 'permit':
					self.respond_proxy(client_id, request.host, request.port, request)
					continue
					
				elif classification == 'rewrite':
					request.redirect(None, data)
					self.respond_proxy(client_id, request.host, request.port, request)
					continue

				elif classification == 'file':
					#self.respond_file(client_id, '250', data)
					self.respond_rewrite(client_id, 250, data, request.protocol, request.url, request.host, request.client)
					continue

				elif classification == 'redirect':
					self.respond_redirect(client_id, data)
					continue

				elif classification == 'dns':
					self.respond_proxy(client_id, data, request.port, request)
					continue

				elif classification == 'requeue':
					self.respond_requeue(client_id, peer, header, source)

				else:
					self.respond_proxy(client_id, request.host, request.port, request)
					continue

			# someone want to use us as https proxy
			if request.method == 'CONNECT':
				# we do allow connect
				if self.configuration.http.allow_connect:
					classification, data = self._classify(request.client, request.method, request.url_noport, tainted)
					if classification == 'redirect':
						self.respond_redirect(client_id, data)

					elif classification == 'requeue':
						self.respond_requeue(client_id, peer, header, source)

					else:
						self.respond_connect(client_id, request.host, request.port, request)

					continue
				else:
					self.respond_html(client_id, 501, 'CONNECT NOT ALLOWED', 'We are an HTTP only proxy')
					continue

			if request.method in ('TRACE',):
				self.respond_html(client_id, 501, 'TRACE NOT IMPLEMENTED', 'This is bad .. we are sorry.')
				continue

			self.respond_html(client_id, 405, 'METHOD NOT ALLOWED', 'Method Not Allowed')
			continue

		self.respond_hangup(self.wid)

	def shutdown(self):
		try:
			self.response_box_read.close()
		except (IOError, ValueError):
			pass
		try:
			self.response_box_write.close()
		except (IOError, ValueError):
			pass

		self.destroyProcess()

# prevent persistence : http://tools.ietf.org/html/rfc2616#section-8.1.2.1
# XXX: We may have more than one Connection header : http://tools.ietf.org/html/rfc2616#section-14.10
# XXX: We may need to remove every step-by-step http://tools.ietf.org/html/rfc2616#section-13.5.1
# XXX: We NEED to respect Keep-Alive rules http://tools.ietf.org/html/rfc2068#section-19.7.1
# XXX: We may look at Max-Forwards
