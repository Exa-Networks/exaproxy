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

#import fcntl

from exaproxy.http.header import Header

from exaproxy.util.logger import logger
from exaproxy.configuration import configuration

from exaproxy.network.resolver import DNSResolver

class Worker (Thread):
	# TODO : if the program is a function, fork and run :)
	
	def __init__ (self, name, request_box, program):
		# XXX: all this could raise things
		r, w = os.pipe()                                # pipe for communication with the main thread
		self.response_box_write = os.fdopen(w,'w',0)    # results are written here
		self.response_box_read = os.fdopen(r,'r',0)     # read from the main thread

		self.resolver = DNSResolver(configuration.RESOLV)

		self.wid = name                               # a unique name
		self.creation = time.time()                   # when the thread was created
	#	self.last_worked = self.creation              # when the thread last picked a task
		self.request_box = request_box                # queue with HTTP headers to process

		self.program = program                        # the squid redirector program to fork 
		self.running = True                           # the thread is active

		# Do not move, we need the forking AFTER the setup
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

	def destroyProcess (self):
		logger.error('worker %d' % self.wid,'destroying process %s' % self.program)
		if not self.process:
			return
		try:
			if self.process:
				self.process.terminate()
				self.process.wait()
				logger.info('worker %d' % self.wid,'terminated process PID %s' % pid)
		except OSError, e:
			# No such processs
			if e[0] != errno.ESRCH:
				logger.error('worker %d' % self.wid,'PID %s died' % pid)

	def shutdown (self):
		logger.debug('worker %d' % self.wid,'shutdown')
		self.running = False
		# XXX: Queue can get stuck, make sure we send a message to unlock it
		self.stop()


	def _classify (self, client_ip, method, url):
		squid = '%s %s - %s -' % (url, client_ip, method)
		#logger.info('worker %d' % self.wid, 'sending to classifier: [%s]' % squid)
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
					classification, data = 'rewrite', ('/'+url.split('/', 1)[1]) if '/' in url else ''
				else:
					classification, data = 'redirect', 'http://' + response

			elif response.startswith('file://'):
				classification, data = 'file', response[7:]

			else:
				classification, data = 'file', 'internal_error.html'

		except IOError, e:
			logger.error('worker %d' % self.wid, 'IO/Error when sending to process: %s' % str(e))
			classification, data = 'file', 'internal_error.html'

		return classification, data

	def respond(self, response):
		self.response_box_write.write(str(len(response)) + ':' + response + ',')
		self.response_box_write.flush()

	def respond_proxy(self, client_id, ip, port, request):
		# We NEED Connection: close
		request['connection'] = 'Connection: close'
		# http://homepage.ntlworld.com./jonathan.deboynepollard/FGA/web-proxy-connection-header.html
		if 'proxy-connection' in request:
			# XXX: If the value is keep-alive, we should parse the answer and add Proxy-Connection: close
			request.pop('proxy-connection')
		# We NEED to add a Via field http://tools.ietf.org/html/rfc2616#section-14.45
		via = 'Via: %s %s, %s %s' % (request.version, 'ExaProxy-%s-%d' % (configuration.VERSION,os.getpid()), '1.1', request.host)
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

	def respond_rewrite(self, client_id, code, reason, url, host, client_ip):
		self.respond('\0'.join((client_id, 'rewrite', str(code), reason, url, host, str(client_ip))))

	def respond_html(self, client_id, code, *data):
		self.respond('\0'.join((client_id, 'html', str(code))+data))

	def respond_redirect(self, client_id, url):
		self.respond('\0'.join((client_id, 'redirect', url)))

	def stop (self):
		self.request_box.put('shutdown')

	def run (self):
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
				self.respond_html(client_id, 400, ('This request does not conform to HTTP/1.1 specifications <!--\n<![CDATA[%s]]>\n-->\n' % str(header)))
				continue

			ipaddr = self.resolver.resolveHost(request.host)
			if not ipaddr:
				logger.warning('worker %d' % self.wid,'Could not resolve %s' % request.host)


			# classify and return the filtered page
			if request.method in ('GET', 'PUT', 'POST'):
				if not ipaddr:
					self.respond_rewrite(client_id, 503, 'dns.html', request.url, request.host, request.client)
					#self.respond_file(client_id, 503, 'dns.html')
					continue

				classification, data = self._classify(request.client, request.method, request.url_noport)

				if classification == 'permit':
					self.respond_proxy(client_id, ipaddr, request.port, request)
					continue
					
				elif classification == 'rewrite':
					request.redirect(None, data)
					self.respond_proxy(client_id, ipaddr, request.port, request)
					continue

				elif classification == 'file':
					#self.respond_file(client_id, '250', data)
					self.respond_rewrite(client_id, 250, data, request.url, request.host, request.client)
					continue

				elif classification == 'redirect':
					self.respond_redirect(client_id, data)
					continue

				else:
					self.respond_proxy(client_id, ipaddr, request.port, request)
					continue

			# someone want to use us as https proxy
			if request.method == 'CONNECT':
				# we do allow connect
				if configuration.CONNECT:
					if not ipaddr:
						# XXX: the redirect url will have to be provided by the redirector
						self.respond_redirect(client_id, 'http://www.exa-networks.co.uk/business/domain/dns/panel')
						continue

					classification, data = self._classify(request.client, request.method, request.url_noport)
					if classification == 'redirect':
						self.respond_redirect(client_id, data)
					else:
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

		try:
			self.response_box_read.close()
			self.response_box_write.close()
		except (IOError, ValueError):
			pass

# prevent persistence : http://tools.ietf.org/html/rfc2616#section-8.1.2.1
# XXX: We may have more than one Connection header : http://tools.ietf.org/html/rfc2616#section-14.10
# XXX: We may need to remove every step-by-step http://tools.ietf.org/html/rfc2616#section-13.5.1
# XXX: We NEED to respect Keep-Alive rules http://tools.ietf.org/html/rfc2068#section-19.7.1
# XXX: We may look at Max-Forwards
# XXX: We need to reply to "Proxy-Connection: keep-alive", with "Proxy-Connection: close"
# http://homepage.ntlworld.com./jonathan.deboynepollard/FGA/web-proxy-connection-header.html
