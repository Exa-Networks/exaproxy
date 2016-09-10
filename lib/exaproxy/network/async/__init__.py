# encoding: utf-8
"""
async/__init__.py

Created by David Farrar on 2012-01-31.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import sys
import select

from exaproxy.util.log.logger import Logger
from exaproxy.configuration import load

configuration = load()
log = Logger('supervisor', configuration.log.supervisor)

def Poller (configuration, speed=None):
	reactor = configuration.reactor

	if reactor == 'best':
		if sys.platform.startswith('linux'):
			configuration.reactor = 'epoll'
		elif sys.platform.startswith('freebsd'):
			configuration.reactor = 'kqueue'
		elif sys.platform.startswith('darwin'):
			configuration.reactor = 'kqueue'
		else:
			log.error('we could not autodetect an high performance reactor for your OS')
			log.error('as the "select" reactor is not suitable for production,')
			log.error('please consider changing reactor by hand')
			configuration.reactor = 'select'

		reactor = configuration.reactor
		log.info('the chosen polling reactor was %s' % reactor)

	if reactor not in ('epoll','kqueue','select'):
		log.error('invalid reactor name: "%s"' % reactor)
		sys.exit(1)

	timeout = speed if speed is not None else configuration.speed

	if reactor == 'epoll' and hasattr(select, 'epoll'):
		from epoll import EPoller as Poller
		return Poller(timeout)

	if reactor == 'kqueue' and hasattr(select, 'kqueue'):
		from kqueue import KQueuePoller as Poller
		return Poller(timeout)

	if hasattr(select, 'select'):
		from selectpoll import SelectPoller as Poller
		return Poller(timeout)

	log.error('this version of python does not have the requested reactor %s or select' % reactor)
	sys.exit(1)
