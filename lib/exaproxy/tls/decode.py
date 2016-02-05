from struct import unpack

from .header import TLS_HEADER_LEN
from .header import TLS_HANDSHAKE_CONTENT_TYPE
from .header import TLS_HANDSHAKE_TYPE_CLIENT_HELLO


# inspired from https://raw.githubusercontent.com/dlundquist/sniproxy/master/src/tls.c

ALERT = [
	0x15,		# TLS Alert
	0x03, 0x01,  # TLS version
	0x00, 0x02,  # Payload length
	0x02, 0x28,  # Fatal, handshake failure
]

def short (data):
	return unpack('!H',data)[0]


def get_tls_hello_size (data):
	return short(data[3:5]) + TLS_HEADER_LEN


def parse_hello (data):
	try:
		# Check that our TCP payload is at least large enough for a TLS header

		if len(data) < TLS_HEADER_LEN+1:  # HEADER + HELLO
			# Not enough data to be a TLS header
			return None

		# SSL 2.0 compatible Client Hello
		# High bit of first byte (length) and content type is Client Hello
		# See RFC5246 Appendix E.2

		tls_content_type = ord(data[0])

		if tls_content_type != TLS_HANDSHAKE_CONTENT_TYPE:
			# Request did not begin with TLS handshake
			return None

		tls_version_major = ord(data[1])
		tls_version_minor = ord(data[2])

		if tls_content_type & 0x80 and tls_version_minor == 1:
			# Received SSL 2.0 Client Hello which can not support SNI')
			return None

		if tls_version_major < 3:
			# "Received SSL %d.%d handshake which which can not support SNI." % (tls_version_major, tls_version_minor)
			return None

		# TLS record length
		length = short(data[3:5]) + TLS_HEADER_LEN
		data = data[TLS_HEADER_LEN:]
		data = data[:length]

		# Handshake
		if ord(data[0]) != TLS_HANDSHAKE_TYPE_CLIENT_HELLO:
			# Not a TLS Client HELLO
			return None

		# Skip past fixed length records:
		#   1   Handshake Type
		#   3   Length
		#   2   Version (again)
		#   32  Random
		#   to  Session ID Length

		data = data[38:]

		# Session ID
		length = ord(data[0])
		data = data[length+1:]

		# Cipher Suites
		length = short(data[:2])
		data = data[length+2:]

		# Compression methods
		length = ord(data[0])
		data = data[length+1:]

		if not data and tls_version_major == 3 and tls_version_minor == 0:
			# Received SSL 3.0 handshake without extensions
			return None

		# Extensions
		length = short(data[:2])
		data = data[2:]
		data = data[:length]

		# parse extension
		while data:
			length = short(data[2:4])
			if short(data[0:2]) == 0x0000:
				data = data[4+2:length+4:]  # +2 to eat the outter length
				break
			data = data[length+4:]

		# name extension not found
		if not data:
			return None

		while data:
			length = short(data[1:3])
			# found name
			if ord(data[0]) == 0x00:
				return data[3:length+3]
			data = data[length+3:]

		return None

	except IndexError:
		# Buffer Underflow
		return None

if __name__ == '__main__':
	# Google TLS HELLO
	raw = ''.join([ chr(_) for _ in [
		0x16, 0x03, 0x01, 0x00, 0xb9, 0x01, 0x00, 0x00,
		0xb5, 0x03, 0x03, 0xdc, 0xb1, 0xcb, 0xde, 0x25,
		0x3b, 0xc4, 0x7c, 0x10, 0xb0, 0x23, 0xee, 0xed,
		0x47, 0xeb, 0xa1, 0xa1, 0x43, 0xbb, 0x39, 0x87,
		0x0b, 0x5f, 0x64, 0x6a, 0xd1, 0x1c, 0x5c, 0xe9,
		0x2d, 0x9f, 0xc9, 0x00, 0x00, 0x16, 0xc0, 0x2b,
		0xc0, 0x2f, 0xc0, 0x0a, 0xc0, 0x09, 0xc0, 0x13,
		0xc0, 0x14, 0x00, 0x33, 0x00, 0x39, 0x00, 0x2f,
		0x00, 0x35, 0x00, 0x0a, 0x01, 0x00, 0x00, 0x76,
		0x00, 0x00, 0x00, 0x15, 0x00, 0x13, 0x00, 0x00,
		0x10, 0x77, 0x77, 0x77, 0x2e, 0x67, 0x6f, 0x6f,
		0x67, 0x6c, 0x65, 0x2e, 0x63, 0x6f, 0x2e, 0x75,
		0x6b, 0xff, 0x01, 0x00, 0x01, 0x00, 0x00, 0x0a,
		0x00, 0x08, 0x00, 0x06, 0x00, 0x17, 0x00, 0x18,
		0x00, 0x19, 0x00, 0x0b, 0x00, 0x02, 0x01, 0x00,
		0x00, 0x23, 0x00, 0x00, 0x33, 0x74, 0x00, 0x00,
		0x00, 0x10, 0x00, 0x17, 0x00, 0x15, 0x02, 0x68,
		0x32, 0x08, 0x73, 0x70, 0x64, 0x79, 0x2f, 0x33,
		0x2e, 0x31, 0x08, 0x68, 0x74, 0x74, 0x70, 0x2f,
		0x31, 0x2e, 0x31, 0x00, 0x05, 0x00, 0x05, 0x01,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x0d, 0x00, 0x16,
		0x00, 0x14, 0x04, 0x01, 0x05, 0x01, 0x06, 0x01,
		0x02, 0x01, 0x04, 0x03, 0x05, 0x03, 0x06, 0x03,
		0x02, 0x03, 0x04, 0x02, 0x02, 0x02
	]])

	print get_tls_hello_size(raw), '==', len(raw)
	print parse_hello(raw)
