import select

from exaproxy.util.log.logger import Logger
from exaproxy.configuration import load

configuration = load()
log = Logger('supervisor', configuration.log.supervisor)

def Poller (configuration, speed=None):
	reactor = configuration.reactor
	timeout = speed if speed is not None else configuration.speed

	if reactor not in ('epoll','kqueue','select'):
		log.warning('unknown reactor %s' % reactor)

	if reactor == 'epoll' and hasattr(select, 'epoll'):
		from epoll import EPoller as Poller
		return Poller(timeout)

	if reactor == 'kqueue' and hasattr(select, 'kqueue'):
		from kqueue import KQueuePoller as Poller
		return Poller(timeout)

	from selectpoll import SelectPoller as Poller
	return Poller(timeout)
