import os
import pickle


class MessageReader:
	delimiter = ':'
	eom = ','

	def read (self, pipe_in):
		# NOTE: we may block here if badly formatted data is sent
		try:
			message_s = pipe_in.read(3)
			while message_s.isdigit():
				message_s += pipe_in.read(1)

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
			os.close(self.pipe_in)

		if self.pipe_out is not None:
			os.close(self.pipe_out)

	def put (self, message):
		pickled = pickle.dumps(message)
		message_s = str(len(pickled)) + self.delimiter + str(pickled) + self.eom

		self.pipe_out.write(message_s)

	def get (self):
		pickled = self.read(self.pipe_in)

		if pickled is not None:
			try:
				message = pickle.loads(pickled)
			except (TypeError, IndexError, ValueError, EOFError):
				message = None

		else:
			message = None

		return message

