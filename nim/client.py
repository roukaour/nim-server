# Remy Oukaour, 107122849
# CSE 310, Group 2

"""
This module defines classes necessary for implementing Nim clients.
"""

__all__ = ['is_natural', 'is_nim_username', 'NimConnection', 'NimClient']

import socket
import re
from nimlib import *

def is_natural(n):
	"""
	Return True if a value is a natural number (a positive integer), False
	otherwise.
	"""
	return isinstance(n, int) and n > 0

def is_nim_username(name):
	"""
	Return True if a value is a valid Nim username (a string of 1 to 32 characters,
	using only A-Z a-z 0-9 _ - + .), False otherwise.
	"""
	name_regex = re.compile(r'^[A-Za-z0-9_\-+\.]{1,32}$', re.DOTALL)
	return isinstance(name, str) and re.match(name_regex, name)

class NimConnection(object):
	"""
	Represents a single, persistent transaction with a Nim server.
	Modeled after Python's built-in httplib.HTTPConnection class.
	"""
	
	def __init__(self, host, port=NIM_PORT):
		"""
		Instantiate a connection with a Nim server.
		"""
		# Initialize the server's host and port
		self.host = host
		self.port = port
		# Initially not waiting for a response
		self.waiting = False
		# Connect to server
		try:
			self.socket = socket.create_connection((self.host, self.port))
		except socket.error as e:
			raise NimException(e.strerror)
	
	def close(self):
		"""
		Close the connection to the server.
		"""
		# Close connection
		if self.socket:
			self.socket.close()
		self.socket = None
	
	def request(self, method, params='', body='', headers=None):
		"""
		Send a request to the server using the given request method, parameters,
		body, and headers. The Content-Length header is automatically set to
		the correct value. The headers should map valid header names to values.
		"""
		# Do not make requests after connection is closed
		if not self.socket:
			raise ValueError('operation on closed connection')
		# Do not send request if a response is pending
		if self.waiting:
			raise NimException('waiting for response to prior request')
		# Check that request method is valid
		if method not in methods:
			raise ValueError("no such method: '{}'".format(method))
		# Convert parameter string to ensure leading whitespace
		params = ' ' + params.strip() if params else ''
		# Convert header dictionary to CRLF-separated string
		headers = headers or dict()
		headers['Content-Length'] = len(body)
		headers = ''.join("{}: {}\r\n".format(k, headers[k]) for k in headers)
		# Send constructed packet to server
		data = "{}{} NIM/{}\r\n{}\r\n{}".format(method, params, NIM_VERSION, headers, body)
		try:
			self.socket.sendall(data)
		except socket.error as e:
			raise NimException(e.strerror)
		# Wait for response from server
		self.waiting = True
	
	def getresponse(self, requested=True):
		"""
		Returns a response from the server. Should be called after a request
		is sent unless requested=False is specified.
		"""
		# Do not take responses after connection is closed
		if not self.socket:
			raise ValueError('operation on closed connection')
		# Do not receive response if no request was made
		if requested and not self.waiting:
			raise NimException('no request was made')
		# Read response from server
		try:
			data = self.socket.recv(4096)
		except socket.error as e:
			raise NimException(e.strerror)
		# Stop waiting for response to prior request
		if requested:
			self.waiting = False
		# Return response parsed into a NimResponse object
		try:
			response = NimResponse(data)
			# Wait for continued response
			if response.status == CONTINUED:
				self.waiting = True
			return response
		except NimException as e:
			return None

class NimClient(object):
	"""
	Represents a Nim client which can connect to a server and make requests.
	Provides an abstraction over the NimConnection class.
	"""
	
	def __init__(self, client_address):
		"""
		Instantiate a Nim client ready to connect to a server.
		"""
		# Initialize the server's host and port
		self.host, self.port = client_address
		# Initially has no connection to the server
		self.conn = None
	
	def connect(self):
		"""
		Connect to the server.
		"""
		# Do not overwrite already-open connection
		if self.conn:
			raise ValueError('already opened connection')
		# Connect to server
		self.conn = NimConnection(self.host, self.port)
	
	def disconnect(self):
		"""
		Disconnect from the server.
		"""
		# Close connection
		if self.conn:
			self.conn.close()
		self.conn = None
	
	def login(self, name):
		"""
		Send a LOGIN request with the given name and return the response.
		"""
		# Do not send request on closed connection
		if not self.conn:
			raise ValueError('operation on closed connection')
		# Check that name is valid
		if not is_nim_username(name):
			raise ValueError('{!r} is not a valid username'.format(name))
		# Send request and return response
		try:
			self.conn.request('LOGIN', name)
			response = self.conn.getresponse()
			return response
		except (NimException, ValueError) as e:
			raise NimException(e.message)
	
	def games(self):
		"""
		Send a GAMES request and return the response.
		"""
		# Do not send request on closed connection
		if not self.conn:
			raise ValueError('operation on closed connection')
		# Send request and return response
		try:
			self.conn.request('GAMES')
			response = self.conn.getresponse()
			return response
		except (NimException, ValueError) as e:
			raise NimException(e.message)
	
	def who(self):
		"""
		Send a WHO request and return the response.
		"""
		# Do not send request on closed connection
		if not self.conn:
			raise ValueError('operation on closed connection')
		# Send request and return response
		try:
			self.conn.request('WHO')
			response = self.conn.getresponse()
			return response
		except (NimException, ValueError) as e:
			raise NimException(e.message)
	
	def play(self, name):
		"""
		Send a PLAY request with the given name and return the response.
		"""
		# Do not send request on closed connection
		if not self.conn:
			raise ValueError('operation on closed connection')
		# Check that name is valid
		if not is_nim_username(name):
			raise ValueError('{!r} is not a valid username'.format(name))
		# Send request and return response
		try:
			self.conn.request('PLAY', name)
			response = self.conn.getresponse()
			return response
		except (NimException, ValueError) as e:
			raise NimException(e.message)
	
	def remove(self, n, s):
		"""
		Send a REMOVE request with the given parameters and return the response.
		"""
		# Do not send request on closed connection
		if not self.conn:
			raise ValueError('operation on closed connection')
		# Check that number of objects is valid
		if not is_natural(n):
			raise ValueError('{!r} is not a valid object amount'.format(n))
		# Check that set ID is valid
		if not is_natural(s):
			raise ValueError('{!r} is not a valid set ID'.format(s))
		# Send request and return response
		try:
			self.conn.request('REMOVE', '{} {}'.format(n, s))
			response = self.conn.getresponse()
			return response
		except (NimException, ValueError) as e:
			raise NimException(e.message)
	
	def observe(self, id):
		"""
		Send an OBSERVE request with the given game ID and return the response.
		"""
		# Do not send request on closed connection
		if not self.conn:
			raise ValueError('operation on closed connection')
		# Check that game ID is valid
		if not is_natural(id):
			raise ValueError('{!r} is not a valid game ID'.format(id))
		# Send request and return response
		try:
			self.conn.request('OBSERVE', str(id))
			response = self.conn.getresponse()
			return response
		except (NimException, ValueError) as e:
			raise NimException(e.message)
	
	def unobserve(self, id):
		"""
		Send an UNOBSERVE request with the given game ID and return the response.
		"""
		# Do not send request on closed connection
		if not self.conn:
			raise ValueError('operation on closed connection')
		# Check that game ID is valid
		if not is_natural(id):
			raise ValueError('{!r} is not a valid game ID'.format(id))
		# Send request and return response
		try:
			self.conn.request('UNOBSERVE', str(id))
			response = self.conn.getresponse()
			return response
		except (NimException, ValueError) as e:
			raise NimException(e.message)
	
	def bye(self):
		"""
		Send a BYE request and return the response. Disconnect from the
		server regardless of the response.
		"""
		# Do not send request on closed connection
		if not self.conn:
			raise ValueError('operation on closed connection')
		# Send request and return response
		try:
			self.conn.request('BYE')
			response = self.conn.getresponse()
			return response
		except (NimException, ValueError) as e:
			raise NimException(e.message)
		# Disconnect from server
		finally:
			self.disconnect()
	
	def ping(self):
		"""
		Send a PING request and return the response.
		"""
		# Do not send request on closed connection
		if not self.conn:
			raise ValueError('operation on closed connection')
		# Send request and return response
		try:
			self.conn.request('PING')
			response = self.conn.getresponse()
			return response
		except (NimException, ValueError) as e:
			raise NimException(e.message)
	
	def continuation(self):
		"""
		Return a response following a previous 300 Continued response.
		"""
		# Do not get response on closed connection
		if not self.conn:
			raise ValueError('operation on closed connection')
		# Return response
		try:
			response = self.conn.getresponse()
			return response
		except (NimException, ValueError) as e:
			raise NimException(e.message)
