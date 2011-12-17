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

from Queue import Empty

from exaproxy.http.header import Header

from exaproxy.util.logger import logger
from exaproxy.configuration import configuration

class Worker (Thread):
	
	# TODO : if the program is a function, fork and run :)
	
	def __init__ (self, name, request_box, program):
		self.process = None                           # the forked program to handle classification

		# XXX: all this could raise things
		r, w = os.pipe()                              # pipe for communication with the main thread
		self.response_box_write = os.fdopen(w,'w')    # results are written here
		self.response_box_read = os.fdopen(r,'r')     # read from the main thread

		self.wid = name                               # a unique name
		self.creation = time.time()                   # when the thread was created
	#	self.last_worked = self.creation              # when the thread last picked a task
		self.request_box = request_box                # queue with HTTP headers to process

		self.program = program                        # the squid redirector program to fork 
		self.running = True                           # the thread is active
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

	def _cleanup (self):
		logger.info('worker %d' % self.wid,'terminating process')
		# XXX: can raise
		self.response_box_read.close()
		self.response_box_write.close()
		try:
			if self.process:
				self.process.terminate()
				self.process.wait()
		except OSError, e:
			# No such processs
			if e[0] != errno.ESRCH:
				logger.error('worker %d' % self.wid,'PID %s died' % pid)

	def _resolveHost(self, host):
		# Do the hostname resolution before the backend check
		# We may block the page but filling the OS DNS cache can not harm :)
		# XXX: we really need an async dns .. sigh, another thread ?? 
		try:
			#raise socket.error('UNCOMMENT TO TEST DNS RESOLUTION FAILURE')
			return socket.gethostbyname(host)
		except socket.error,e:
			return None

	def stop (self):
		self.running = False
		self.request_box.put(None)

	def _classify (self,cid,client,method,url):
		squid = '%s %s - %s -' % (url,client,method)
		logger.info('worker %d' % self.wid,'sending to classifier : [%s]' % squid)
		try:
			self.process.stdin.write('%s%s' % (squid,os.linesep))
			self.process.stdin.flush()
			response = self.process.stdout.readline()

			logger.info('worker %d' % self.wid,'received from classifier : [%s]' % response.strip())
			if response == '\n':
				response = host
			return response
		except IOError,e:
			logger.error('worker %d' % self.wid,'IO/Error when sending to process, %s' % str(e))
			self._reply(cid,500,'Interal Problem','could get a classification for %s' % url)
			# XXX: Do something
			return ''

	def _400 (self,cid,request):
		self._reply(cid,400,'INVALID REQUEST','This request does not conform to HTTP/1.1 specifications <!--\nCDATA[[%s]]\n-->' % request)

	def _request (self,cid,ip,port,req):
		req['connection'] = 'Connection: close'
		logger.debug('worker %d' % self.wid,'need to download data at %s' % str(ip))
		self.response_box_write.write('%s %s %s %d %s\n' % (cid,'request',ip,port,str(req).replace('\n','\\n').replace('\r','\\r')))
		self.response_box_write.flush()
		##logger.debug('worker %d' % self.wid,'[%s %s %s %d %s]' % (cid,'request',ip,80,request))
		#self.last_worked = time.time()
	
	def _connect (self,cid,ip,port):
		self.response_box_write.write('%s %s %s %d %s\n' % (cid,'connect',ip,port,''))
		self.response_box_write.flush()

	def _reply (self,cid,code,title,body):
		self.response_box_write.write('%s %s %s %d %s\n' % (cid,'response',title.replace(' ','_'),code,body.replace('\n','\\n').replace('\r','\\r')))
		self.response_box_write.flush()

	def run (self):
		if not self.running:
			logger.error('worker %d' % self.wid,'can not start')
			return

		logger.info('worker %d' % self.wid,'starting')
		self.process = self._createProcess()
		if not self.process:
			# LOG SOMETHING !
			self.stop()

		while True:
			try:
				logger.debug('worker %d' % self.wid,'waiting for some work')
				# XXX: For some reason, even if we have a timeout, pypy does block here
				data = self.request_box.get(1)
				if not self.running or data is None:
					break
			except (ValueError, IndexError):
				logger.error('worker %d' % self.wid,'received invalid message: %s' % data)
				if not self.running:
					break
				continue
			except Empty:
				if not self.running:
					break
				continue

			cid,peer,request = data
			logger.debug('worker %d' % self.wid,'peer %s request %s' % (str(peer),' '.join(request.split('\n',3)[:2])))

			req = Header(request)
			if not req.method:
				self._400(cid,request)
				continue

			client = req.get('x-forwarded-for',':0.0.0.0').split(':')[1].split(',')[-1].strip()
			host = req.get('host',':').split(':')[1].strip()
			method = req.method
			port = req.port

			if method != 'CONNECT' and not host:
				self._400(cid,request)
				continue

			url = req.path if req.path[:7].lower() == 'http://' else 'http://' + host + req.path

			ip = self._resolveHost(host)
			if not ip:
				logger.error('worker %d' % self.wid,'Could not resolve %s' % host)
				self._reply(cid,503,'NO DNS','could not resolve DNS for [%s]' % host)
				continue

			# classify and return the filtered page
			if method in ('GET','PUT','POST'):
				response = self._classify(cid,client,method,url)
				self._request(cid,ip,port,req)
				continue

			# someone want to use use as https proxy
			if method == 'CONNECT':
				if configuration.CONNECT:
					self._connect(cid,ip,port)
					continue
				else:
					self._reply(cid,501,'CONNECT NOT ALLOWED','We are an HTTP only proxy')
					continue

			# do not bother classfying things which do not return pages
			if method in ('HEAD','OPTIONS','DELETE'):
				if False: # It should be an option to be able to force all request
					response = self._classify(cid,client,method,url)
				self._request(cid,ip,port,request)
				continue

			if method in ('TRACE',):
				self._reply(cid,501,'TRACE NOT IMPLEMENTED','This is bad .. we are sorry.')
				continue

			self._reply(cid,405,'METHOD NOT ALLOWED','Method Not Allowed %s' % method)
			continue

		self._cleanup()
			# prevent persistence : http://tools.ietf.org/html/rfc2616#section-8.1.2.1
			# XXX: We may have more than one Connection header : http://tools.ietf.org/html/rfc2616#section-14.10
			# XXX: We may need to remove every step-by-step http://tools.ietf.org/html/rfc2616#section-13.5.1
			# XXX: We NEED to add a Via field http://tools.ietf.org/html/rfc2616#section-14.45
			# XXX: We NEED to respect Keep-Alive rules http://tools.ietf.org/html/rfc2068#section-19.7.1
			# XXX: We may look at Max-Forwards
			# XXX: We need to reply to "Proxy-Connection: keep-alive", with "Proxy-Connection: close"
			# http://homepage.ntlworld.com./jonathan.deboynepollard/FGA/web-proxy-connection-header.html