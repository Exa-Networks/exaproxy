import select

from exaproxy.util.logger import logger


def Poller (configuration):
	reactor = configuration.reactor
	timeout = configuration.speed
	if reactor not in ('epoll','select'):
		logger.warning('supervisor','unknown reactor %s' % reactor)
	if reactor == 'epoll' and hasattr(select, 'epoll'):
		from epoll import EPoller as Poller
		return Poller(timeout)
	else:
		from selectpoll import SelectPoller as Poller
		return Poller(timeout)
