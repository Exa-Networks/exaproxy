# encoding: utf-8


class ResponseEncoder (object):
	@staticmethod
	def icap (client_id, response, length):
		return client_id, 'icap', (response, str(length))

	@staticmethod
	def download (client_id, ip, port, upgrade, length, message):
		return client_id, 'download', (ip, str(port), upgrade, str(length), str(message))

	@staticmethod
	def connect (client_id, host, port, message):
		return client_id, 'connect', (host, str(port), str(message))

	@staticmethod
	def intercept (client_id, host, port, message):
		return client_id, 'intercept', (host, str(port), str(message))

	@staticmethod
	def file (client_id, code, reason):
		return client_id, 'file', (str(code), reason)

	@staticmethod
	def rewrite (client_id, code, reason, comment, message):
		return client_id, 'rewrite', (code, reason, comment, message.request.protocol, message.url, message.host, str(message.client))

	@staticmethod
	def http (client_id, data):
		return client_id, 'http',  data

	@staticmethod
	def monitor (client_id, path):
		return client_id, 'monitor', path

	@staticmethod
	def redirect (client_id, url):
		return client_id, 'redirect', url

	@staticmethod
	def stats (wid, timestamp, stats):
		return wid, 'stats', (timestamp, stats)

	@staticmethod
	def requeue (client_id, peer, header, subheader, source):
		# header and source are flipped to make it easier to split the values
		return client_id, 'requeue', (peer, source, header, subheader)

	@staticmethod
	def hangup (wid):
		return '', 'close', wid

	@staticmethod
	def close (client_id):
		return client_id, 'close', ''

	@staticmethod
	def defer (client_id, message):
		return client_id, 'defer', message

	@staticmethod
	def error (client_id):
		return client_id, None, None



def splithost (data, default_port):
	if ':' in data:
		host, port = data.split(':', 1)

	else:
		host, port = data, None

	if port is None or not port.isdigit():
		port = default_port

	return host, port


class ResponseFactory (object):
	encoder = ResponseEncoder

	def contentResponse (self, client_id, message, classification, data, comment):
		if classification == 'permit':
			return ('PERMIT', message.host), self.encoder.download(client_id, message.host, message.port, message.upgrade, message.content_length, message)

		if classification == 'rewrite':
			message.redirect(None, data)
			return ('REWRITE', data), self.encoder.download(client_id, message.host, message.port, '', message.content_length, message)

		if classification == 'file':
			return ('FILE', data), self.encoder.rewrite(client_id, '200', data, comment, message)

		if classification == 'redirect':
			return ('REDIRECT', data), self.encoder.redirect(client_id, data)

		if classification == 'intercept':
			host, port = splithost(data, message.port)
			return ('INTERCEPT', data), self.encoder.download(client_id, host, port, '', message.content_length, message)

		if classification == 'http':
			return ('LOCAL', ''), self.encoder.http(client_id, data)

		return ('PERMIT', message.host), self.encoder.download(client_id, message.host, message.port, message.upgrade, message.content_length, message)

	def connectResponse (self, client_id, message, classification, data, comment):
		if classification == 'permit':
			return ('PERMIT', message.host), self.encoder.connect(client_id, message.host, message.port, '')

		if classification == 'redirect':
			return ('REDIRECT', data), self.encoder.redirect(client_id, data)

		if classification == 'intercept':
			host, port = splithost(data, message.port)
			return ('INTERCEPT', data), self.encoder.intercept(client_id, host, port, message)

		if classification == 'file':
			return ('FILE', data), self.encoder.rewrite(client_id, '200', data, comment, message)

		if classification == 'http':
			return ('LOCAL', ''), self.encoder.http(client_id, data)

		return ('PERMIT', message.host), self.encoder.connect(client_id, message.host, message.port, '')
