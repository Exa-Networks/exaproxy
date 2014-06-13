import socket

def validate_ip4 (address):
	try:
		socket.inet_aton(address)
		ip4_address = address
	except (socket.error, TypeError):
		ip4_address = None

	return ip4_address

def validate_ip6 (address):
	try:
		socket.inet_pton(socket.AF_INET6, address)
		ip6_address = address
	except (socket.error, TypeError):
		ip6_address = None

	return ip6_address

def invalidate (address):
	return None


class ProxyProtocol:
	ip_validators = {
		'TCP4' : validate_ip4,
		'TCP6' : validate_ip6,
		'UNKNOWN' : invalidate
	}

	def parseRequest (self, header):
		if '\r\n' in header:
			proxy_line, http_request = header.split('\r\n', 1)
		else:
			proxy_line, http_request = '', None

		try:
			magic, fproto, source, destination, sport, dport = proxy_line.split(' ')
		except ValueError:
			proxy_line, http_request = '', None
			magic, fproto, source, destination, sport, dport = None, None, None, None, None, None

		if magic != 'PROXY':
			# We don't care about parsing the source or destination ports
			http_request = None
			source, destination = None, None

		validate = self.ip_validators.get(fproto, invalidate)
		source_addr = validate(source)
		dest_addr = validate(destination)  # pylint: disable=W0612

		return source_addr, http_request
