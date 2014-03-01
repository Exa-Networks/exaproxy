# encoding: utf-8
"""
process.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

# prevent persistence : http://tools.ietf.org/html/rfc2616#section-8.1.2.1
# NOTE: We may have more than one Connection header : http://tools.ietf.org/html/rfc2616#section-14.10
# NOTE: We may need to remove every step-by-step http://tools.ietf.org/html/rfc2616#section-13.5.1
# NOTE: We NEED to respect Keep-Alive rules http://tools.ietf.org/html/rfc2068#section-19.7.1
# NOTE: We may look at Max-Forwards

import traceback
from threading import Thread
from exaproxy.util.messagequeue import Empty
import subprocess
import errno

import os
import time
import fcntl

from exaproxy.http.message import HTTP
from exaproxy.http.request import Request
from exaproxy.http.response import http

from exaproxy.util.log.logger import Logger
from exaproxy.util.log.logger import UsageLogger

from exaproxy.util.log.history import Errors,History,Level


class ChildError (Exception):
	pass


class Respond (object):
	@staticmethod
	def download (client_id, ip, port, upgrade, length, message):
		return '\0'.join((client_id, 'download', ip, str(port), upgrade, str(length), str(message)))

	@staticmethod
	def connect (client_id, host, port, message):
		return '\0'.join((client_id, 'connect', host, str(port), str(message)))

	@staticmethod
	def file (client_id, code, reason):
		return '\0'.join((client_id, 'file', str(code), reason))

	@staticmethod
	def rewrite (client_id, code, reason, comment, message):
		return '\0'.join((client_id, 'rewrite', code, reason, comment, message.request.protocol, message.url, message.host, str(message.client)))

	@staticmethod
	def http (client_id, *data):
		return '\0'.join((client_id, 'http')+data)

	@staticmethod
	def monitor (client_id, path):
		return '\0'.join((client_id, 'monitor', path))

	@staticmethod
	def redirect (client_id, url):
		return '\0'.join((client_id, 'redirect', url))

	@staticmethod
	def stats (wid, timestamp, stats):
		return '\0'.join((wid, 'stats', timestamp, stats))

	@staticmethod
	def requeue (client_id, peer, header, source):
		# header and source are flipped to make it easier to split the values
		return '\0'.join((client_id, peer, source, header))

	@staticmethod
	def hangup (wid):
		return '\0'.join(('', 'hangup', wid))

class Redirector (Thread):
	# TODO : if the program is a function, fork and run :)

	def __init__ (self, configuration, name, request_box, program):
		self.configuration = configuration
		self.enabled = configuration.redirector.enable
		self.protocol = configuration.redirector.protocol
		self._transparent = configuration.http.transparent
		self.log = Logger('worker ' + str(name), configuration.log.worker)
		self.usage = UsageLogger('usage', configuration.log.worker)

		self.universal = True if self.protocol == 'url' else False
		self.icap = self.protocol[len('icap://'):].split('/')[0] if self.protocol.startswith('icap://') else ''

		r, w = os.pipe()                                # pipe for communication with the main thread
		self.response_box_write = os.fdopen(w,'w',0)    # results are written here
		self.response_box_read = os.fdopen(r,'r',0)     # read from the main thread

		self.wid = name                               # a unique name
		self.creation = time.time()                   # when the thread was created
	#	self.last_worked = self.creation              # when the thread last picked a task
		self.request_box = request_box                # queue with HTTP headers to process

		self.program = program                        # the squid redirector program to fork
		self.running = True                           # the thread is active

		self.stats_timestamp = None                   # time of the most recent outstanding request to generate stats

		self._proxy = 'ExaProxy-%s-id-%d' % (configuration.proxy.version,os.getpid())

		if self.protocol == 'url':
			self.classify = self._classify_url
		if self.protocol.startswith('icap://'):
			self.classify = self._classify_icap


		# Do not move, we need the forking AFTER the setup
		self.process = self._createProcess()          # the forked program to handle classification
		Thread.__init__(self)

	def _createProcess (self):
		if not self.enabled:
			return

		def preexec():  # Don't forward signals.
			os.setpgrp()

		try:
			process = subprocess.Popen([self.program,],
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				universal_newlines=self.universal,
				preexec_fn=preexec,
			)
			self.log.debug('spawn process %s' % self.program)
		except KeyboardInterrupt:
			process = None
		except (subprocess.CalledProcessError,OSError,ValueError):
			self.log.error('could not spawn process %s' % self.program)
			process = None

		if process:
			try:
				fcntl.fcntl(process.stderr, fcntl.F_SETFL, os.O_NONBLOCK)
			except IOError:
				self.destroyProcess()
				process = None

		return process

	def destroyProcess (self):
		if not self.enabled:
			return
		self.log.debug('destroying process %s' % self.program)
		if not self.process:
			return
		try:
			if self.process:
				self.process.terminate()
				self.process.wait()
				self.log.info('terminated process PID %s' % self.process.pid)
		except OSError, e:
			# No such processs
			if e[0] != errno.ESRCH:
				self.log.error('PID %s died' % self.process.pid)

	def stop (self):
		self.log.debug('shutdown')
		# The worker thread may be blocked reading from the queue
		# so the shutdown will not be immediate
		self.running = False

	def transparent (self, message, peer):
		headers = message.headers
		# http://homepage.ntlworld.com./jonathan.deboynepollard/FGA/web-proxy-connection-header.html
		headers.pop('proxy-connection',None)
		# NOTE: To be RFC compliant we need to add a Via field http://tools.ietf.org/html/rfc2616#section-14.45 on the reply too
		# NOTE: At the moment we only add it from the client to the server (which is what really matters)
		if not self._transparent:
			headers.extend('via','Via: %s %s' % (message.request.version, self._proxy))
			headers.extend('x_forwarded_for', 'X-Forwarded-For: %s' % peer)
			headers.pop('proxy-authenticate')

		return message

	def _classify_icap (self, message, headers, tainted):
		if not self.process:
			self.log.error('No more process to classify the HTTP request received')
			return message, 'file', 'internal_error.html'

		line = """\
REQMOD %s ICAP/1.0
Host: %s
Pragma: client=%s
Pragma: host=%s
Encapsulated: req-hdr=0, null-body=%d

%s""" % (
			self.protocol,self.icap,
			message.client, message.host,
			len(headers),
			headers
		)
		try:
			self.process.stdin.write(line)
			try:
				data = self.process.stdout.readline()
				if not data:
					raise ChildError('')

				code = data.rstrip().split()[1]
				length = -1

				comment = ''
				while True:
					line = self.process.stdout.readline()
					if not line:
						raise ChildError('')

					line = line.rstrip()
					if not line:
						break

					if line.startswith('Pragma: comment:'):
						comment = line.split(':',2)[2].strip()
						continue

					if line.startswith('Encapsulated: res-hdr=0, null-body='):
						# BIG Shortcut for performance - we know the last header is the size
						length = int(line.split('=')[-1])
						continue

				try:
					child_stderr = self.process.stderr.read(4096)
				except Exception, e:
					child_stderr = ''

				if child_stderr:
					raise ChildError(child_stderr)

				# 304 (no modified)
				if code == '304':
					return message, 'permit', None, None

				if length < 0:
					return message, 'file', 'internal_error.html', ''

				headers = ''
				read_bytes = 0

				while read_bytes < length:
					headers_s = self.process.stdout.read(length)
					headers += headers_s
					read_bytes += len(headers_s)

			except (ValueError,IndexError):
				# IndexError can be raised with split()
				# ValueError can be raised when converting to int and other bits
				self.log.critical('problem detected, the redirector program did not send valid data')
				self.log.critical('returning our internal error page to the client even if we are not to blame.')
				self.log.critical('stopping this thread as we can not assume that the process will behave from now on.')

				self.stop()

				# for line in traceback.format_exc().split('\n'):
				# 	self.log.info(line)

				return message, 'file', 'internal_error.html', ''

			except ChildError, e:
				self.log.critical('problem detected, the redirector program did not send valid data')
				self.log.critical('returning our internal error page to the client even if we are not to blame.')
				self.log.critical('stopping this thread as we can not assume that the process will behave from now on.')

				self.stop()

				# wow this is nasty but we may be here because we read something from stderr and
				# we'd like to know what we read
				child_stderr = str(e)
				try:
					while True:
						data = self.process.stderr.read(4096)
						if not data:
							break
						child_stderr += data
				except:
					pass

				for line in child_stderr.strip().split('\n'):
					self.log.critical("child said : %s" % line)

				errors = Errors()
				snap = History().snapshot()
				errors.messages.extend(snap[-len(snap)/4:])
				#errors.record(time.localtime(), self.process.pid, Level.value.CRITICAL, child_stderr)

				return message, 'file', 'internal_error.html', ''

			except Exception:
				self.log.critical('problem detected, the redirector program did not send valid data')
				self.log.critical('returning our internal error page to the client even if we are not to blame.')
				self.log.critical('stopping this thread as we can not assume that the process will behave from now on.')
				self.stop()

				# for line in traceback.format_exc().split('\n'):
				# 	self.log.info(line)

				return message, 'file', 'internal_error.html', ''

		except IOError:
			self.log.error('IO/Error when sending to process')
			for line in traceback.format_exc().split('\n'):
				self.log.info(line)
			if tainted is False:
				self.log.info('retrying ...')
				return message, 'requeue', None, None
			self.log.info('stopping this thread as we can not assume that the process will behave from now on.')
			self.stop()
			return message, 'file', 'internal_error.html', ''

		if headers.startswith('HTTP/') and (headers.split() + [''])[1].isdigit():
			return message, 'http', headers, comment

		# QUICK and DIRTY, let do a intercept using the CONNECT syntax
		if headers.startswith('CONNECT'):
			_ = headers.replace('\r\n','\n').split('\n\n',1)
			if _[1]:  # is not an empty string
				connect = _[0]
				headers = _[1]
				request = Request(connect.split('\n')[0]).parse()

				if not request:
					return message, 'file', 'internal_error.html', ''
				h = HTTP(self.configuration,headers,message.client)
				if not h.parse(self._transparent) or h.reply_code:
					return message, 'file', 'internal_error.html', ''

				# The trick to not have to extend ICAP
				h.host = request.host
				h.port = request.port
				return h,'permit',None,comment

		# Parsing the request from the ICAP server
		h = HTTP(self.configuration,headers,message.client)
		if not h.parse(self._transparent) or h.reply_code:
			return message, 'file', 'internal_error.html', comment

		return h, 'permit', None, comment

	def _classify_url (self, message, headers, tainted):
		if not self.process:
			self.log.error('No more process to evaluate message')
			return message, 'file', 'internal_error.html', ''

		try:
			squid = '%s %s - %s -' % (message.url_noport, message.client, message.request.method)
			self.process.stdin.write(squid + os.linesep)

			response = None
			while not response:
				response = self.process.stdout.readline()

			response = response.strip()
		except IOError, e:
			self.log.error('IO/Error when sending to process: %s' % str(e))
			if tainted is False:
				return message, 'requeue', None, ''
			return message, 'file', 'internal_error.html', ''

		if not response:
			return message, 'permit', None, ''

		if response.startswith('http://'):
			response = response[7:]

			if response == message.url_noport:
				return message, 'permit', None, ''
			if response.startswith(message.url.split('/', 1)[0]+'/'):
				return message, 'rewrite', ('/'+response.split('/', 1)[1]) if '/' in message.url else '', ''
			return message, 'redirect', 'http://' + response, ''

		if response.startswith('file://'):
			return message, 'file', response[7:], ''

		if response.startswith('intercept://'):
			return message, 'intercept', response[12:], ''

		if response.startswith('redirect://'):
			return message, 'redirect', response[11:], ''

		return message, 'file', 'internal_error.html', ''

	def respond(self, response):
		self.response_box_write.write(str(len(response)) + ':' + response + ',')
		self.response_box_write.flush()

	def request (self,client_id, message, classification, data, comment, peer, header, source):
		if classification == 'permit':
			return ('PERMIT', message.host), Respond.download(client_id, message.host, message.port, message.upgrade, message.content_length, self.transparent(message, peer))

		if classification == 'rewrite':
			message.redirect(None, data)
			return ('REWRITE', data), Respond.download(client_id, message.host, message.port, '', message.content_length, self.transparent(message, peer))

		if classification == 'file':
			return ('FILE', data), Respond.rewrite(client_id, '200', data, comment, message)

		if classification == 'redirect':
			return ('REDIRECT', data), Respond.redirect(client_id, data)

		if classification == 'intercept':
			return ('INTERCEPT', data), Respond.download(client_id, data, message.port, '', message.content_length, self.transparent(message, peer))

		if classification == 'requeue':
			return (None, None), Respond.requeue(client_id, peer, header, source)

		if classification == 'http':
			return ('LOCAL', ''), Respond.http(client_id, data)

		return ('PERMIT', message.host), Respond.download(client_id, message.host, message.port, message.upgrade, message.content_length, self.transparent(message, peer))

	def connect (self,client_id, message, classification, data, comment, peer, header, source):
		if classification == 'permit':
			return ('PERMIT', message.host), Respond.connect(client_id, message.host, message.port, message)

		if classification == 'requeue':
			return (None, None), Respond.requeue(client_id, peer, header, source)

		if classification == 'redirect':
			return ('REDIRECT', data), Respond.redirect(client_id, data)

		if classification == 'intercept':
			return ('INTERCEPT', data), Respond.connect(client_id, data, message.port, message)

		if classification == 'file':
			return ('FILE', data), Respond.rewrite(client_id, '200', data, comment, message)

		if classification == 'http':
			return ('LOCAL', ''), Respond.http(client_id, data,message.request.version)

		self.log.error('no classification, going default open [%s]' % str(classification))
		return ('PERMIT', message.host), Respond.connect(client_id, message.host, message.port, message)


	def run (self):
		while self.running:
			try:
				# The timeout is really caused by the SIGALARM sent on the main thread every second
				# BUT ONLY IF the timeout is present in this call
				data = self.request_box.get(timeout=2)
			except Empty:
				if self.enabled:
					if not self.process or self.process.poll() is not None:
						if self.running:
							self.log.error('stopping the worker as the forked process exited !')
						self.running = False
				continue
			except ValueError:
				self.log.error('Problem reading from request_box')
				continue

			try:
				client_id, peer, header, source, tainted = data
			except TypeError:
				self.log.alert('Received invalid message: %s' % data)
				continue

			if self.enabled:
				if not self.process or self.process.poll() is not None:
					if self.running:
						self.log.error('cleanly stopping the worker, as the forked process died on us !')
					self.running = False
					if source != 'nop':
						self.respond(Respond.requeue(client_id, peer, header, source))
					break

			if source == 'nop':
				continue  # /break

			if not self.running:
				self.log.warning('Consumed a message before we knew we should stop.')

			# This code does nothing ATM, as self.stats_timestamp is always null
			stats_timestamp = self.stats_timestamp
			if stats_timestamp:
				# Is this actually atomic as I am guessing?
				# There's a race condition here if not. We're unlikely to hit it though, unless
				# the classifier can take a long time
				self.stats_timestamp = None if stats_timestamp == self.stats_timestamp else self.stats_timestamp

				# we still have work to do after this so don't continue
				stats = self._stats()
				self.respond(Respond.stats(self.wid, stats))

			message = HTTP(self.configuration,header,peer)
			if not message.parse(self._transparent):
				try:
					version = message.request.version
				except AttributeError:
					version = '1.0'
				if message.reply_string:
					self.respond(Respond.http(client_id, http(str(message.reply_code), '%s<br/>\n<!--\n\n<![CDATA[%s]]>\n\n-->\n' % (message.reply_string,header.replace('\t','\\t').replace('\r','\\r').replace('\n','\\n\n')),version)))
				else:
					self.respond(Respond.http(client_id, http(str(message.reply_code),'',version)))
				continue
			if message.reply_code:
				self.respond(Respond.http(client_id, http(str(message.reply_code), self.reply_string, message.request.version)))
				continue

			method = message.request.method

			if source == 'web':
				self.respond(Respond.monitor(client_id, message.request.path))
				continue

			# classify and return the filtered page
			if method in ('GET', 'PUT', 'POST','HEAD','DELETE','PATCH'):
				if not self.enabled:
					self.respond(Respond.download(client_id, message.host, message.port, message.upgrade, message.content_length, self.transparent(message, peer)))
					self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', message.host)
					continue

				(operation, destination), response = self.request(client_id, *(self.classify (message,header,tainted) + (peer, header, source)))
				self.respond(response)
				if operation is not None:
					self.usage.logRequest(client_id, peer, method, message.url, operation, destination)
				continue


			# someone want to use us as https prox, peery
			if method == 'CONNECT':
				# we do allow connect
				if not self.configuration.http.allow_connect or message.port not in self.configuration.security.connect:
					# NOTE: we are always returning an HTTP/1.1 response
					self.respond(Respond.http(client_id, http('501', 'CONNECT NOT ALLOWED\n')))
					self.usage.logRequest(client_id, peer, method, message.url, 'DENY', 'CONNECT NOT ALLOWED')
					pass

				if not self.enabled:
					self.respond(Respond.connect(client_id, message.host, message.port, http))
					self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', message.host)
					continue

				(operation, destination), response = self.connect(client_id, *(self.classify(message,header,tainted)+(peer,header,source)))
				self.respond(response)
				if operation is not None:
					self.usage.logRequest(client_id, peer, method, message.url, operation, destination)
				continue

			if method in ('OPTIONS','TRACE'):
				if message.headers.get('max-forwards',''):
					max_forwards = message.headers.get('max-forwards','Max-Forwards: -1')[-1].split(':')[-1].strip()
					if not max_forwards.isdigit():
						# NOTE: we are always returning an HTTP/1.1 response
						self.respond(Respond.http(client_id, http('400', 'INVALID MAX-FORWARDS\n')))
						self.usage.logRequest(client_id, peer, method, message.url, 'ERROR', 'INVALID MAX FORWARDS')
						continue
					max_forward = int(max_forwards)
					if max_forward < 0 :
						# NOTE: we are always returning an HTTP/1.1 response
						self.respond(Respond.http(client_id, http('400', 'INVALID MAX-FORWARDS\n')))
						self.usage.logRequest(client_id, peer, method, message.url, 'ERROR', 'INVALID MAX FORWARDS')
						continue
					if max_forward == 0:
						if method == 'OPTIONS':
							# NOTE: we are always returning an HTTP/1.1 response
							self.respond(Respond.http(client_id, http('200', '')))
							self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', 'OPTIONS')
							continue
						if method == 'TRACE':
							# NOTE: we are always returning an HTTP/1.1 response
							self.respond(Respond.http(client_id, http('200', header)))
							self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', 'TRACE')
							continue
						raise RuntimeError('should never reach here')
					message.headers.set('max-forwards','Max-Forwards: %d' % (max_forward-1))
				# Carefull, in the case of OPTIONS message.host is NOT message.headerhost
				self.respond(Respond.download(client_id, message.headerhost, message.port, message.upgrade, message.content_length, self.transparent(message, peer)))
				self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', message.headerhost)
				continue

			# WEBDAV
			if method in (
			  'BCOPY', 'BDELETE', 'BMOVE', 'BPROPFIND', 'BPROPPATCH', 'COPY', 'DELETE','LOCK', 'MKCOL', 'MOVE',
			  'NOTIFY', 'POLL', 'PROPFIND', 'PROPPATCH', 'SEARCH', 'SUBSCRIBE', 'UNLOCK', 'UNSUBSCRIBE', 'X-MS-ENUMATTS'):
				self.respond(Respond.download(client_id, message.headerhost, message.port, message.upgrade, message.content_length, self.transparent(message, peer)))
				self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', method)
				continue

			if message.request in self.configuration.http.extensions:
				self.respond(Respond.download(client_id, message.headerhost, message.port, message.upgrade, message.content_length, self.transparent(message, peer)))
				self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', message.request)
				continue

			# NOTE: we are always returning an HTTP/1.1 response
			self.respond(Respond.http(client_id, http('405', '')))  # METHOD NOT ALLOWED
			self.usage.logRequest(client_id, peer, method, message.url, 'DENY', method)
			continue

		self.respond(Respond.hangup(self.wid))

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

