import os
import sys

from exaproxy.util.control import SlaveBox

from .supervisor import RedirectorSupervisor
from .messagebox import ProxyToRedirectorMessageBox, RedirectorToProxyMessageBox
from .dispatch import RedirectorDispatcher

def redirector_message_thread (message_box):
	dispatcher = RedirectorDispatcher(message_box)
	dispatcher.start()

	return dispatcher
	

def fork_redirector (poller, configuration):
	r1, w1 = os.pipe()
	r2, w2 = os.pipe()

	cr1, cw1 = os.pipe()
	cr2, cw2 = os.pipe()

	pid = os.fork()

	if pid == 0:  # the child process
		os.close(r1)
		os.close(w2)
		os.close(cr1)
		os.close(cw2)

		messagebox = RedirectorToProxyMessageBox(r2, w1)
		controlbox = SlaveBox(cr2, cw1)
		supervisor = RedirectorSupervisor(configuration, messagebox, controlbox)
		redirector = None

		# run forever
		try:
			supervisor.run()

		except KeyboardInterrupt:
			pass

		except IOError:
			pass

		# unless we don't
		sys.exit()

	else:
		os.close(w1)
		os.close(r2)
		os.close(cw1)
		os.close(cr2)

		redirector = ProxyToRedirectorMessageBox(pid, r1, w2, cr1, cw2)
		poller.addReadSocket('read_redirector', redirector.box.pipe_in)
		poller.addReadSocket('read_control', redirector.control.box.pipe_in)

	return redirector
