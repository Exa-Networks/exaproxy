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
from exaproxy.icap.parser import ICAPParser

from exaproxy.util.log.logger import Logger
from exaproxy.util.log.logger import UsageLogger

from exaproxy.util.log.history import Errors,History,Level


class ChildError (Exception):
	pass


class Respond (object):
	@staticmethod
	def icap (client_id, response):
		return '\0'.join((client_id, 'icap', response))

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
	def requeue (client_id, peer, header, subheader, source):
		# header and source are flipped to make it easier to split the values
		return '\0'.join((client_id, peer, source, header, subheader))

	@staticmethod
	def hangup (wid):
		return '\0'.join(('', 'hangup', wid))

	@staticmethod
	def close (client_id):
		return '\0'.join((client_id, 'close', ''))

class Redirector (Thread):
	# TODO : if the program is a function, fork and run :)
	ICAPParser = ICAPParser

	def __init__ (self, configuration, name, request_box, program):
		self.configuration = configuration
		self.icap_parser = self.ICAPParser(configuration)
		self.enabled = configuration.redirector.enable
		self.protocol = configuration.redirector.protocol
		self._transparent = configuration.http.transparent
		self.log = Logger('worker ' + str(name), configuration.log.worker)
		self.usage = UsageLogger('usage', configuration.log.worker)

		self.universal = True if self.protocol == 'url' else False
		self.icap = self.protocol[len('icap://'):].split('/')[0] if self.protocol.startswith('icap://') else ''

		r, w = os.pipe()								# pipe for communication with the main thread
		self.response_box_write = os.fdopen(w,'w',0)	# results are written here
		self.response_box_read = os.fdopen(r,'r',0)	 # read from the main thread

		self.wid = name							   # a unique name
		self.creation = time.time()				   # when the thread was created
	#	self.last_worked = self.creation			  # when the thread last picked a task
		self.request_box = request_box				# queue with HTTP headers to process

		self.program = program						# the squid redirector program to fork
		self.running = True						   # the thread is active

		self.stats_timestamp = None				   # time of the most recent outstanding request to generate stats

		self._proxy = 'ExaProxy-%s-id-%d' % (configuration.proxy.version,os.getpid())

		if self.protocol == 'url':
			self.classify = self._classify_url
		if self.protocol.startswith('icap://'):
			self.classify = self._classify_icap


		# Do not move, we need the forking AFTER the setup
		self.process = self._createProcess()		  # the forked program to handle classification
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

	def classifyICAP (self, headers):
		if not self.process:
			self.log.error('No more process to classify the HTTP request received')
			return None

		try:
			self.process.stdin.write(headers)
			response = self.process.stdout.readline()
			code = (response.rstrip().split()+[None])[1] if response else None
			length = -1

			while True:
				line = self.process.stdout.readline()
				response += line

				if not line:
					response = None
					break

				elif not line.rstrip():
					break

				if line.startswith('Encapsulated: res-hdr=0, null-body='):
					length = int(line.split('=')[-1])

			read_bytes = 0
			bytes_to_read = max(0, length)

			while read_bytes < bytes_to_read:
				headers_s = self.process.stdout.read(bytes_to_read-read_bytes)
				response += headers_s
				read_bytes += len(headers_s)

			if code is None:
				response = None

			# 304 (not modified)
			elif code != '304' and length < 0:
				response = None

		except IOError:
			response = None

		try:
			child_stderr = self.process.stderr.read(4096)
		except Exception, e:
			child_stderr = ''

		if child_stderr:
			response = None

		return response

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
			return (None, None), Respond.requeue(client_id, peer, header, '', source)

		if classification == 'http':
			return ('LOCAL', ''), Respond.http(client_id, data)

		return ('PERMIT', message.host), Respond.download(client_id, message.host, message.port, message.upgrade, message.content_length, self.transparent(message, peer))

	def connect (self,client_id, message, classification, data, comment, peer, header, source):
		if classification == 'permit':
			return ('PERMIT', message.host), Respond.connect(client_id, message.host, message.port, message)

		if classification == 'requeue':
			return (None, None), Respond.requeue(client_id, peer, header, '', source)

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



	def createRequest (self, peer, request):
		icap_request = """\
REQMOD %s ICAP/1.0
Host: %s
Pragma: client=%s
Pragma: host=%s""" % (
			self.protocol, self.icap,
			peer, request.http_request.host,
			)

		username = request.headers.get('x-authenticated-user', '').strip()
		groups = request.headers.get('x-authenticated-groups', '').strip()
		ip_addr = request.headers.get('x-client-ip', '').strip()
		customer = request.headers.get('x-customer-name', '').strip()

		if ip_addr:
			icap_request += """
X-Client-IP: %s""" % ip_addr

		if username:
			icap_request += """
X-Authenticated-User: %s""" % username

		if groups:
			icap_request += """
X-Authenticated-Groups: %s""" % groups

		if customer:
			icap_request += """
X-Customer-Name: %s""" % customer

		return icap_request + """
Encapsulated: req-hdr=0, null-body=%d

%s""" % (len(request.http_header), request.http_header)


	def parseHTTP (self, peer, http_header):
		message = HTTP(self.configuration, http_header, peer)

		if not message.parse(self._transparent):
			try:
				version = message.request.version
			except AttributeError:
				version = '1.0'

			if message.reply_string:
				response = Respond.http(client_id, http(str(message.reply_code), '%s<br/>\n<!--\n\n<![CDATA[%s]]>\n\n-->\n' % (message.reply_string,header.replace('\t','\\t').replace('\r','\\r').replace('\n','\\n\n')),version))
			else:
				response = Respond.http(client_id, http(str(message.reply_code),'',version))

			message = None

		elif message.reply_code:
			response = Respond.http(client_id, http(str(message.reply_code), self.reply_string, message.request.version))
			message = None

		else:
			response = None

		return message, response

	def doHTTPRequest (self, client_id, peer, message, http_header, source, tainted):
		method = message.request.method

		if self.enabled:
			classification = self.classify(message, http_header, tainted)
			(operation, destination), response = self.request(client_id, *(classification + (peer, http_header, source)))

			if operation is not None:
				self.usage.logRequest(client_id, peer, method, message.url, operation, destination)

		else:
			response = Respond.download(client_id, message.host, message.port, message.upgrade, message.content_length, self.transparent(message, peer))
			self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', message.host)

		return response

	def doHTTPConnect (self, client_id, peer, message):
		if not self.configuration.http.allow_connect or message.port not in self.configuration.security.connect:
			# NOTE: we are always returning an HTTP/1.1 response
			response = Respond.http(client_id, http('501', 'CONNECT NOT ALLOWED\n'))
			self.usage.logRequest(client_id, peer, method, message.url, 'DENY', 'CONNECT NOT ALLOWED')

		else:
			response = None

		return response

	def doHTTPOptions (self, client, peer, message):
		# NOTE: we are always returning an HTTP/1.1 response
		method = message.request.method

		if message.headers.get('max-forwards',''):
			max_forwards = message.headers.get('max-forwards','Max-Forwards: -1')[-1].split(':')[-1].strip()
			max_forward = int(max_forwards) if max_forwards.isdigit() else None

			if max_forward is None:
				response = Respond.http(client_id, http('400', 'INVALID MAX-FORWARDS\n'))
				self.usage.logRequest(client_id, peer, method, message.url, 'ERROR', 'INVALID MAX FORWARDS')

			elif max_forward == 0:
				response = Respond.http(client_id, http('200', ''))
				self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', method)

			else:
				response = None

			message.headers.set('max-forwards','Max-Forwards: %d' % (max_forward-1))

		if response is None:
			response = Respond.download(client_id, message.headerhost, message.port, message.upgrade, message.content_length, self.transparent(message, peer))

		return response

	def doHTTP (self, client_id, peer, http_header, source, tainted):
		message, response = self.parseHTTP(peer, http_header)

		if response is None and source == 'web':
			response = Respond.monitor(client_id, message.request.path)
			message = None

		if message is not None:
			method = message.request.method
		
			if method in ('GET', 'PUT', 'POST','HEAD','DELETE','PATCH'):
				response = self.doHTTPRequest(client_id, peer, message, http_header, source, tainted)

			elif method == 'CONNECT':
				response = self.doHTTPConnect(client_id, peer, message)
				response = response or self.doHTTPRequest(client_id, peer, message, http_header, source, tainted)

			elif method in ('OPTIONS','TRACE'):
				response = self.doHTTPOptions(client_id, peer, message)

			elif method in (
			'BCOPY', 'BDELETE', 'BMOVE', 'BPROPFIND', 'BPROPPATCH', 'COPY', 'DELETE','LOCK', 'MKCOL', 'MOVE',
			'NOTIFY', 'POLL', 'PROPFIND', 'PROPPATCH', 'SEARCH', 'SUBSCRIBE', 'UNLOCK', 'UNSUBSCRIBE', 'X-MS-ENUMATTS'):
				response = selfRespond.download(client_id, message.headerhost, message.port, message.upgrade, message.content_length, self.transparent(message, peer))
				self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', method)

			elif message.request in self.configuration.http.extensions:
				response = Respond.download(client_id, message.headerhost, message.port, message.upgrade, message.content_length, self.transparent(message, peer))
				self.usage.logRequest(client_id, peer, method, message.url, 'PERMIT', message.request)

			else:
				# NOTE: we are always returning an HTTP/1.1 respons
				response = Respond.http(client_id, http('405', '')) # METHOD NOT ALLOWED
				self.usage.logRequest(client_id, peer, method, message.url, 'DENY', method)

		return response

	def parseICAP (self, peer, icap_header, http_header):
		request = self.icap_parser.parseRequest(peer, icap_header, http_header)
		if request and not request.http_request.request:
			request = None

		return request

	def doICAP (self, client_id, peer, icap_header, http_header, tainted):
		received_request = self.parseICAP(peer, icap_header, http_header)
		icap_request = self.createRequest(peer, received_request) if received_request else None
		icap_response = self.classifyICAP(icap_request) if icap_request else None

		if icap_response:
			response = Respond.icap(client_id, icap_response)

		elif icap_request:
			self.stop()

			if not tainted:
				response = Respond.requeue(client_id, peer, icap_header, http_header, 'icap')

		else:
			response = None

		return response

	def checkChild (self):
		if self.enabled:
			ok = bool(self.process) and self.process.poll() is None
		else:
			ok = True

		return ok

	def doStats (self):
		# This code does nothing ATM, as self.stats_timestamp is always null
		stats_timestamp = self.stats_timestamp
		if stats_timestamp:
			self.stats_timestamp = None if stats_timestamp == self.stats_timestamp else self.stats_timestamp

	def receiveMessage (self):
		try:
			# The timeout is really caused by the SIGALARM sent on the main thread every second
			# BUT ONLY IF the timeout is present in this call
			data = self.request_box.get(timeout=2)
		except Empty:
			data = None
		except ValueError:
			self.log.error('Problem reading from request box')
			data = None

		try:
			if data is not None:
				client_id, peer, icap_header, http_header, source, tainted = data
			else:
				client_id, peer, icap_header, http_header, source, tainted = None, None, None, None, None, None

		except TypeError:
			self.log.alert('Received invalid message: %s' % data)
			client_id, peer, icap_header, http_header, source, tainted = None, None, None, None, None, None

		return client_id, peer, icap_header, http_header, source, tainted

	def run (self):
		while self.running:
			message = self.receiveMessage()
			client_id, peer, header, subheader, source, tainted = message
			response = None

			if client_id is not None:
				self.doStats()
			else:
				continue

			if not self.checkChild():
				response = Respond.requeue(client_id, peer, icap_header, http_header, source) if source != 'nop' else None
				if self.running:
					self.log.warning('Cleanly stopping worker thread after the forked process exited')
				self.running = False
				break

			if source == 'nop':
				continue

			if not self.running:
				self.log.warning('Consumed a message before we knew we should stop. Oh well.')

			if response is None:
				if source == 'icap':
					response = self.doICAP(client_id, peer, header, subheader, tainted)
				else:
					response = self.doHTTP(client_id, peer, header, source, tainted)

			if response is None:
				response = Respond.close(client_id)

			self.respond(response)

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

