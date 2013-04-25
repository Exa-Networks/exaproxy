# Modified from http://pastebin.com/wxjai3Mw linked from http://carnivore.it/2010/07/22/python_-_getifaddrs

from collections import namedtuple
from sys import platform
from ctypes import *

from socket import AF_INET, AF_INET6, inet_ntop

try:
	from socket import AF_PACKET
except ImportError:
	AF_PACKET = -1

# getifaddr structs
class ifa_ifu_u (Union):
	_fields_ = [
		("ifu_broadaddr", c_void_p),
		("ifu_dstaddr",   c_void_p),
	]

class ifaddrs (Structure):
	_fields_ = [
		("ifa_next",    c_void_p ),
		("ifa_name",    c_char_p ),
		("ifa_flags",   c_uint	),
		("ifa_addr",    c_void_p ),
		("ifa_netmask", c_void_p ),
		("ifa_ifu",     ifa_ifu_u),
		("ifa_data",    c_void_p),
	]

# AF_UNKNOWN / generic
class sockaddr_bsd (Structure):
	_fields_ = [
		("sa_len",     c_uint8),
		("sa_family",  c_uint8),
		("sa_data",    (c_uint8 * 14)),
	]

class sockaddr_linux (Structure):
	_fields_ = [
		("sa_family", c_uint16),
		("sa_data",   (c_uint8 * 14)),
	]


# AF_INET / IPv4
class in_addr(Union):
	_fields_ = [
		("s_addr", c_uint32),
	]

class sockaddr_in_bsd (Structure):
	_fields_ = [
		("sin_len",    c_uint8),
		("sin_family", c_uint8),
		("sin_port",   c_ushort),
		("sin_addr",   in_addr),
		("sin_zero",   (c_char * 8)), # padding
	]

class sockaddr_in_linux (Structure):
	_fields_ = [
		("sin_family", c_short),
		("sin_port",   c_ushort),
		("sin_addr",   in_addr),
		("sin_zero",   (c_char * 8)), # padding
	]


# AF_INET6 / IPv6
class in6_u (Union):
	_fields_ = [
		("u6_addr8",  (c_uint8 * 16)),
		("u6_addr16", (c_uint16 * 8)),
		("u6_addr32", (c_uint32 * 4)),
	]

class in6_addr (Union):
	_fields_ = [
		("in6_u", in6_u),
	]

class sockaddr_in6_bsd (Structure):
	_fields_ = [
		("sin6_len",      c_uint8),
		("sin6_family",   c_uint8),
		("sin6_port",     c_ushort),
		("sin6_flowinfo", c_uint32),
		("sin6_addr",     in6_addr),
		("sin6_scope_id", c_uint32),
	]

class sockaddr_in6 (Structure):
	_fields_ = [
		("sin6_family",   c_short),
		("sin6_port",     c_ushort),
		("sin6_flowinfo", c_uint32),
		("sin6_addr",     in6_addr),
		("sin6_scope_id", c_uint32),
	]

# AF_PACKET / Linux
class sockaddr_ll (Structure):
	_fields_ = [
		("sll_family",   c_uint16),
		("sll_protocol", c_uint16),
		("sll_ifindex",  c_uint32),
		("sll_hatype",   c_uint16),
		("sll_pktype",   c_uint8 ),
		("sll_halen",    c_uint8 ),
		("sll_addr",     (c_uint8 * 8)),
	]

# AF_LINK / BSD|OSX
class sockaddr_dl (Structure):
	_fields_ = [
		("sdl_len",    c_uint8 ),
		("sdl_family", c_uint8 ),
		("sdl_index",  c_uint16),
		("sdl_type",   c_uint8 ),
		("sdl_nlen",   c_uint8 ),
		("sdl_alen",   c_uint8 ),
		("sdl_slen",   c_uint8 ),
		("sdl_data",   (c_uint8 * 46)),
	]

#	IFT_CEPT = 0x13  # E1

if platform.startswith("darwin"):
	AF_LINK = 18

	IFT_OTHER = 0x1      # none of the following (many entries not listed here)
	IFT_ETHER = 0x6      # Ethernet CSMA/CD
	IFT_PPP = 0x17       # PPP
	IFT_LOOP = 0x18      # loopback
	IFT_IEEE1394 = 0x90  # IEEE1394 High Performance SerialBus

	# Define constants for the most useful interface flags (from if.h).
	IFF_UP            = 0x0001
	IFF_BROADCAST     = 0x0002
	IFF_LOOPBACK      = 0x0008
	IFF_POINTTOPOINT  = 0x0010
	IFF_RUNNING       = 0x0040
	IFF_MULTICAST     = 0x8000

	sockaddr = sockaddr_bsd
	sockaddr_in = sockaddr_in_bsd
	sockaddr_in6 = sockaddr_in6_bsd

	libc = CDLL('libc.dylib')

elif platform.startswith("freebsd"):
	AF_LINK = 18
	IFT_OTHER = 0x1      # none of the following (many entries not listed here)
	IFT_ETHER = 0x6      # Ethernet CSMA/CD
	IFT_PPP = 0x17       # PPP
	IFT_LOOP = 0x18      # loopback
	IFT_IEEE1394 = 0x90  # IEEE1394 High Performance SerialBus

	# Define constants for the most useful interface flags (from if.h).
	IFF_UP            = 0x0001
	IFF_BROADCAST     = 0x0002
	IFF_LOOPBACK      = 0x0008
	IFF_POINTTOPOINT  = 0x0010
	IFF_RUNNING       = 0x0040
	IFF_MULTICAST     = 0x8000

	sockaddr = sockaddr_bsd
	sockaddr_in = sockaddr_in_bsd
	sockaddr_in6 = sockaddr_in6_bsd

	libc = CDLL("libc.so")

elif sys.platform.startswith('linux'):
	AF_LINK = -1
	IFT_OTHER = -1
	IFT_ETHER = -1
	IFT_PPP = -1
	IFT_LOOP = -1

	# Define constants for the most useful interface flags (from if.h).
	IFF_UP            = 0x0001
	IFF_BROADCAST     = 0x0002
	IFF_LOOPBACK      = 0x0008
	IFF_POINTTOPOINT  = 0x0010
	IFF_RUNNING       = 0x0040
	IFF_MULTICAST     = 0x1000

	sockaddr = sockaddr_linux
	sockaddr_in = sockaddr_in_linux
	sockaddr_in6 = sockaddr_in6_linux

	try:
		libc = CDLL("libc.so.6")
	except OSError:
		libc = CDLL("libc.so")
else:
	raise RuntimeError('unsupported platform')

# There is a bug in FreeBSD
# (PR kern/152036) and MacOSX wherein the netmask's sockaddr may be
# truncated.  Specifically, AF_INET netmasks may have their sin_addr
# member truncated to the minimum number of bytes necessary to
# represent the netmask.  For example, a sockaddr_in with the netmask
# 255.255.254.0 may be truncated to 7 bytes (rather than the normal
# 16) such that the sin_addr field only contains 0xff, 0xff, 0xfe.
# All bytes beyond sa_len bytes are assumed to be zero.  Here we work
# around this truncation by copying the netmask's sockaddr into a
# zero-filled buffer.

def getifaddrs():
	ptr = c_void_p(None)

	if libc.getifaddrs(pointer(ptr)) < 0:
		raise OSError('can not use libc to get interfaces')

	ifa = ifaddrs.from_address(ptr.value)
	result = {}

	# Python 2 gives us a string, Python 3 an array of bytes
	name = lambda _: _.ifa_name if type(ifa.ifa_name) is str else lambda _: _.ifa_name.decode()

	result = namedtuple('ifaddrs', 'name flags family address netmask scope')

	while ifa:
		sa = sockaddr.from_address(ifa.ifa_addr)

		if sa.sa_family == AF_INET:
			address = inet_ntop(AF_INET,sockaddr_in.from_address(ifa.ifa_addr).sin_addr) if ifa.ifa_addr else None,
			netmask = inet_ntop(AF_INET,sockaddr_in.from_address(ifa.ifa_netmask).sin_addr) if ifa.ifa_netmask else None,
			yield result (name(ifa),ifa.ifa_flags,sa.sa_family,address,netmask,None)

		elif sa.sa_family == AF_INET6:
			address = inet_ntop(AF_INET6,sockaddr_in6.from_address(ifa.ifa_addr).sin6_addr) if ifa.ifa_addr else None
			netmask = inet_ntop(AF_INET6,sockaddr_in6.from_address(ifa.ifa_netmask).sin6_addr) if ifa.ifa_netmask else None
			scope = sockaddr_in6.from_address(ifa.ifa_addr).sin6_scope_id if address and address.startswith('fe80:') else None
			yield result (name(ifa),ifa.ifa_flags,sa.sa_family,address,netmask,scope)

		elif sa.sa_family == AF_PACKET:
			si = sockaddr_ll.from_address(ifa.ifa_addr)
			address = ':'.join(['%02x' % _ for _ in si.sll_addr[:si.sll_halen]])
			yield result (name(ifa),ifa.ifa_flags,sa.sa_family,address,None,None)

		elif sa.sa_family == AF_LINK:
			dl = sockaddr_dl.from_address(ifa.ifa_addr)
			if dl.sdl_type == IFT_ETHER:
				address = ':'.join(['%02x' % _ for _ in dl.sdl_data[dl.sdl_nlen:dl.sdl_nlen+dl.sdl_alen]])
				yield result (name(ifa),ifa.ifa_flags,sa.sa_family,address,None,None)

		if ifa.ifa_next:
			ifa = ifaddrs.from_address(ifa.ifa_next)
		else:
			break
 
	libc.freeifaddrs(ptr)

__all__ = ['getifaddrs'] + [n for n in dir() if n.startswith('IFF_')]

if __name__ == '__main__':
	ifaces=getifaddrs()
	for iface in ifaces:
		print(iface)

	# for family in ifaces[iface]:
	# 	print("\t%s" % { AF_INET: 'IPv4', AF_INET6 : 'IPv6', AF_PACKET: 'HW', AF_LINK: 'LINK' }[family])
	# 	for addr in ifaces[iface][family]:
	# 		for i in ['addr','netmask','scope']:
	# 			if i in addr:
	# 				print("\t\t%s %s" % (i, str(addr[i])))
	# 		print("")
	# 
