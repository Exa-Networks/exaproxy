import select

if hasattr(select, 'epoll'):
	from epoll import EPoller as Poller
else:
	from selectpoll import SelectPoller as Poller
