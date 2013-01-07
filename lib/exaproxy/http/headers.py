# encoding: utf-8
"""
http.py

Created by Thomas Mangin on 2011-12-02.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

#import re
#reg=re.compile('(\w+)[:=] ?"?(\w+)"?')
#reg=re.compile('(\w+)[:=] ?"?([^" ,]+)"?')
#dict(reg.findall(headers))

class ExpectationFailed (Exception):
	pass

class Headers (object):
	def __init__ (self,http_version,separator):
		self._order = []
		self._data = {}
		self.http_version = http_version
		self.separator = separator

	def get (self,key,default):
		return self._data.get(key,default)

	def set (self,key,value):
		if key not in self._order:
			self._order.append(key)

		self._data[key] = [value]
		return self

	def replace (self,key,value):
		self._data[key] = [value]

	def default (self,key,value):
		if key not in self._data:
			self._data[key] = [value]

	def extend (self,key,value):
		if key in self._order:
			self._data[key].append(value)
			return self
		self._order.append(key)
		self._data[key] = [value]
		return self

	def pop (self, key, default=None):
		if key in self._data:
			value = self._data.pop(key)
			self._order.remove(key)
			return value
		else:
			return default

	def count_quotes (self, line):
		return line.count('"') - line.count('\\"')

	def parse (self, transparent, lines):
		if lines and lines[0].isspace():
			raise ValueError('Malformed headers, headers starts with a white space')

		key = ''
		quoted = False

		try:
			for line in lines.split('\n'):
				line = line.strip('\r')

				if quoted:
					self.extend(key, line)
					if self.count_quotes(line) % 2:
						quoted = False

					continue
				
				if not line: break

				if self.count_quotes(line) % 2:
					quoted = True

				if line[0].isspace():
					# ValueError if key is not already there
					# IndexError the list is empty
					self.extend(key,line)
					continue

				# KeyError if split does not return two elements
				key, value = line.split(':', 1)
				key = key.strip().lower()
				self.extend(key,line)

		except (KeyError,TypeError,IndexError):
			raise ValueError('Malformed headers (line : %s) headers %s' % (line,lines.replace('\n','\\n').replace('\r','\\r')))

		if quoted:
			raise ValueError, 'End of headers reached while in quoted content'

		try:
			if not transparent:

				# follow rules about not forwarding connection header as set in section s14.10
				if self.http_version == '1.1':
					upgrades = self.get('upgrade',[])
					for upgrade in upgrades[:]:
						key, value = upgrade.split(':', 1)
						value = value.strip().lower()
						if not (value == 'websocket' or value.startswith('tls/')):
							upgrades.remove(upgrade)
							self.pop(value.lower())
					# we modified the list in data directly
					if not upgrades:
						self.pop('upgrade')

					connections = self.get('connection',[])
					for connection in connections[:]:
						key, value = connection.split(':', 1)
						value = value.strip().lower()
						# we keep connection: close
						if value == 'close':
							continue
						# we have a websocket in upgrade
						if value == 'upgrade' and upgrades:
							continue
						# otherwise we remove the unknown upgrade
						connections.remove(connection)
					# we modified the list in data directly
					if not connections:
						self.pop('connection')

				# remove keep-alive header for http/1.0
				if self.http_version == '1.0':
					self.pop('keep-alive')

				# this proxy can not honour expect, so we are returning a 417 through the use of an exception
				expect = self.get('expect',None)
				if expect:
					raise ExpectationFailed()

		except (KeyError,TypeError,IndexError):
			raise ValueError('Can not remove connection tokens from headers')


		# we got a line starting with a :
		if '' in self._data:
			raise ValueError ('Malformed headers, line starts with colon (:)')
		
		return self

	def __str__ (self):
		return self.separator.join([self.separator.join(self._data[key]) for key in self._order])


