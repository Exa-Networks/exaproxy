from dns.resolver import Resolver
from dns.exception import DNSException
import random


# Do the hostname resolution before the backend check
# We may block the page but filling the OS DNS cache can not harm :)
# XXX: we really need an async dns .. sigh, another thread ?? 

# XXX: ipv6

class DNSResolver:
	resolverFactory = Resolver
	resolv = '/etc/resolv.conf'

	def __init__(self, resolv=None):
		self.resolver = self.resolverFactory(resolv or self.resolv)

	def resolveHost(self, hostname):
		try:
			response = self.resolver.query(hostname).response
			if not response.answer:
				ip = None

			# XXX: check that this is correct
			ips = response.answer[-1].items
			if ips:
				ip = random.choice(ips).address
			else:
				ip = None
		except DNSException:
			ip = None

		return ip
