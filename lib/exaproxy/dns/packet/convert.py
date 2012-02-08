from struct import unpack
import socket

def u8(s):
	return ord(s)

def u16(s):
	return unpack('>H', s)[0]

def u32(s):
	return unpack('>I', s)[0]

def ipv4_ntoa(ip):
	return socket.inet_ntoa(ip)

def ipv4_aton(s):
	return socket.inet_aton(ip)
