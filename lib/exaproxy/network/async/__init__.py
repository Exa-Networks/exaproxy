import select

from exaproxy.util.log import log

def Poller (configuration):
	reactor = configuration.reactor
	timeout = configuration.speed
	if reactor not in ('epoll','select'):
		log.warning('supervisor','unknown reactor %s' % reactor)
	if reactor == 'epoll' and hasattr(select, 'epoll'):
		from epoll import EPoller as Poller
		return Poller(timeout)
	else:
		from selectpoll import SelectPoller as Poller
		return Poller(timeout)
