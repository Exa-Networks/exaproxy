import os
import sys
from .supervisor import RedirectorSupervisor
from .messagebox import ProxyToRedirectorMessageBox, RedirectorToProxyMessageBox

def fork_redirector (poller, configuration):
	r1, w1 = os.pipe()
	r2, w2 = os.pipe()

	pid = os.fork()

	if pid == 0: # the child process
		os.close(r1)
		os.close(w2)

		messagebox = RedirectorToProxyMessageBox(r2, w1)
		supervisor = RedirectorSupervisor(configuration, messagebox)
		redirector = None

		# run forever
		supervisor.run()

		# unless we don't
		sys.exit()

	else:
		os.close(w1)
		os.close(r2)

		redirector = ProxyToRedirectorMessageBox(pid, r1, w2)
		poller.addReadSocket('read_redirector', redirector.box.pipe_in)

	return redirector
