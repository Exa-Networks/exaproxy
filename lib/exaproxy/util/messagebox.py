import os
import pickle

from exaproxy.network.errno_list import errno_block

class MessageReader:
	delimiter = ':'
	eom = ','

	def read (self, pipe_in):
		# NOTE: we may block here if badly formatted data is sent

		while True:
			try:
				message_s = pipe_in.read(3)
				break
			except IOError:
				pass

		while message_s.isdigit():
			try:
				message_s += pipe_in.read(1)
			except IOError:
				pass

		try:
			if self.delimiter in message_s:
				pickled_size, pickled = message_s.split(self.delimiter, 1)

			else:
				pickled_size, pickled = None, None

			if pickled_size is not None and pickled_size.isdigit():
				pickled_len = int(pickled_size)

			else:
				pickled_len, pickled = None, None

			if pickled_len is not None:
				remaining = pickled_len + 1 - len(pickled)

			else:
				remaining = 0

			while remaining > 0:
				data = pipe_in.read(remaining)
				remaining = remaining - len(data)
				pickled += data

		except (ValueError, TypeError): # I/O operation on closed file
			pickled = None

		if pickled is not None and pickled.endswith(self.eom):
			pickled = pickled[:-1]

		else:
			pickled = None

		return pickled

	def get (self, pipe_in):
		pickled = self.read(pipe_in)

		if pickled is not None:
			try:
				message = pickle.loads(pickled)
			except (TypeError, IndexError, ValueError, EOFError):
				message = None

		else:
			message = None

		return message


class MessageBox (MessageReader):
	def __init__ (self, pipe_in, pipe_out):
		self.pipe_in = os.fdopen(pipe_in, 'r', 0)
		self.pipe_out = os.fdopen(pipe_out, 'w', 0)

	def close (self):
		if self.pipe_in is not None:
			try:
				self.pipe_in.close()
			except IOError:
				pass

		if self.pipe_out is not None:
			try:
				self.pipe_out.close()
			except IOError:
				pass

	def put (self, message):
		pickled = pickle.dumps(message)
		message_s = str(len(pickled)) + self.delimiter + str(pickled) + self.eom

		while True:
			try:
				return self.pipe_out.write(message_s)
			except IOError, e:
				if e.errno not in errno_block:
					raise e

	def get (self):
		while True:
			try:
				pickled = self.read(self.pipe_in)
				break
			except IOError, e:
				if e.errno not in errno_block:
					raise e

		if pickled is not None:
			try:
				message = pickle.loads(pickled)
			except (TypeError, IndexError, ValueError, EOFError):
				message = None

		else:
			message = None

		return message

