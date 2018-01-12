# Remy Oukaour, 107122849
# CSE 310, Group 2

"""
Nim protocol 3.0 library. Modeled after Python's built-in httplib module.

Client- and server-specific functions are located in their own modules.
"""

__all__ = ['NIM_VERSION', 'NIM_PORT', 'NIM_MIN_SETS', 'NIM_MAX_SETS',
	'NIM_MIN_OBJECTS', 'NIM_MAX_OBJECTS', 'methods', 'OK', 'HELLO', 'BYE',
	'BEGIN_GAME', 'END_GAME', 'CONTINUED', 'ERROR', 'IMPOSSIBLE',
	'ILLEGAL_MOVE', 'FORBIDDEN', 'NOT_FOUND', 'METHOD_NOT_ALLOWED',
	'INTERNAL_ERROR', 'NOT_IMPLEMENTED', 'NIM_VERSION_NOT_SUPPORTED',
	'responses', 'NimException', 'NimPacket', 'NimRequest', 'NimResponse']

import re
from distutils.version import LooseVersion

# The version of the Nim protocol supported by this library
NIM_VERSION = LooseVersion('3.0')

# The default TCP port number for the Nim protocol
NIM_PORT = 7849

# The minimum and maximum amounts for the sets and objects
NIM_MIN_SETS = 3
NIM_MAX_SETS = 5
NIM_MIN_OBJECTS = 1
NIM_MAX_OBJECTS = 7

# The request methods supported by Nim, and their expected parameter signatures
methods = {
	'LOGIN': (str,),
	'REMOVE': (int, int),
	'BYE': (),
	'GAMES': (),
	'WHO': (),
	'PLAY': (str,),
	'OBSERVE': (int,),
	'UNOBSERVE': (int,),
	'PING': ()
}

# The response status codes supported by Nim
OK = 200
HELLO = 201
BYE = 202
BEGIN_GAME = 203
END_GAME = 204
CONTINUED = 300
ERROR = 400
IMPOSSIBLE = 401
ILLEGAL_MOVE = 402
FORBIDDEN = 403
NOT_FOUND = 404
METHOD_NOT_ALLOWED = 405
IM_A_TEAPOT = 418
INTERNAL_ERROR = 500
NOT_IMPLEMENTED = 501
SERVICE_UNAVAILABLE = 503
NIM_VERSION_NOT_SUPPORTED = 505

# The response reason phrases supported by Nim
responses = {
	OK: 'OK',
	HELLO: 'Hello',
	BYE: 'Bye',
	BEGIN_GAME: 'Begin Game',
	END_GAME: 'End Game',
	CONTINUED: 'Continued',
	ERROR: 'Error',
	IMPOSSIBLE: 'Impossible',
	ILLEGAL_MOVE: 'Illegal Move',
	FORBIDDEN: 'Forbidden',
	NOT_FOUND: 'Not Found',
	METHOD_NOT_ALLOWED: 'Method Not Allowed',
	IM_A_TEAPOT: "I'm A Teapot",
	INTERNAL_ERROR: 'Internal Error',
	NOT_IMPLEMENTED: 'Not Implemented',
	SERVICE_UNAVAILABLE: 'Service Unavailable',
	NIM_VERSION_NOT_SUPPORTED: 'Nim Version Not Supported'
}

class NimException(Exception):
	"""
	The base class of the other Nim exceptions in this module.
	"""

class NimPacket(object):
	"""
	The base class of the Nim request and response packet classes. Contains
	shared aspects of the two packet types, namely header and body data.
	"""
	
	# The format of all Nim request or response packets
	packet_regex_template = r'''
		^[ \t]*                   # ignore leading whitespace
		{}                        # insert via packet_regex() call
		\r\n                      # separating CRLF
		(?P<headers>(?:           # headers...
		    [A-Za-z0-9_\-+\.]+    #    header name
		    :                     #    separating colon
		    [ \t]*                #    optional leading whitespace
		    .*?                   #    optional header value
		    [ \t]*                #    optional trailing whitespace
		    \r\n                  #    terminating CRLF
		)*)                       # ...optional
		\r\n                      # separating CRLF
		(?P<body>.*)$             # optional body
		'''
	
	# The format of a Nim header
	header_regex = re.compile(r'''
		([A-Za-z0-9_\-+\.]+)    # header name
		:                       # separating colon
		[ \t]*                  # optional leading whitespace
		(.*?)                   # optional header value
		[ \t]*                  # optional trailing whitespace
		\r\n                    # terminating CRLF
		''', re.DOTALL | re.VERBOSE)
	
	@staticmethod
	def packet_regex(initial):
		"""
		Return a regular expression for the format of a Nim packet with
		an initial line's format provided as the argument.
		"""
		return re.compile(NimPacket.packet_regex_template.format(initial),
			re.DOTALL | re.VERBOSE)
	
	def __init__(self):
		"""
		NimPacket is abstract and cannot be instantiated.
		"""
		raise NotImplementedError('cannot instantiate abstract NimPacket')
	
	def initialize(self, data, parts):
		"""
		Store the raw packet data, parsed headers, and body data as fields.
		"""
		self.data = data
		self.headers = dict(re.findall(self.header_regex, parts['headers']))
		self.body = parts['body']
	
	def getheader(self, name, default=None):
		"""
		Return the value of the named header if it exists, otherwise the default value.
		"""
		return self.headers.get(name, default)
	
	def getheaders(self):
		"""
		Return a list of (name, value) pairs for each header.
		"""
		return self.headers.items()

class NimRequest(NimPacket):
	"""
	The class of a Nim request packet (sent by clients).
	"""
	
	# Regular expression matching parts of a Nim request packet
	request_regex = NimPacket.packet_regex(r'''
		(?P<method>[A-Z]+)           # method name
		[ \t]+                       # separating whitespace
		(?P<params>(?:               # method parameters...
		    [A-Za-z0-9_\-+\.]+       #    parameter value
		    [ \t]+                   #    terminating whitespace
		)*)                          # ...optional
		NIM/(?P<version>[0-9\.]+)    # protocol version
		''')
	
	def __init__(self, data):
		"""
		Store the parsed parts of raw packet data as fields.
		"""
		# Match raw packet data against request regex
		match = re.match(self.request_regex, data)
		if not match:
			raise NimException('malformed request: {!r}'.format(data))
		parts = match.groupdict()
		# Store the headers and body
		self.initialize(data, parts)
		# Store the other parts of the request
		self.request = data.split("\r\n")[0]
		self.version = LooseVersion(parts['version'])
		self.method = parts['method']
		params = parts['params'].split()
		types = methods.get(self.method, [str] * len(params))
		self.params = tuple(t(p) for (t, p) in zip(types, params))

class NimResponse(NimPacket):
	"""
	The class of a Nim response packet (sent by servers).
	"""
	
	# Regular expression matching parts of a Nim response packet
	response_regex = NimPacket.packet_regex(r'''
		NIM/(?P<version>[0-9\.]+)            # protocol version
		[ \t]+                               # separating whitespace
		(?P<status>[0-9]+)                   # numeric status code
		[ \t]+                               # separating whitespace
		(?P<reason>[A-Za-z0-9_\-+\. \t]+)    # reason phrase
		''')
	
	def __init__(self, data):
		"""
		Store the parsed parts of raw packet data as fields.
		"""
		# Match raw packet data against response regex
		match = re.match(self.response_regex, data)
		if not match:
			raise NimException('malformed response: {!r}'.format(data))
		parts = match.groupdict()
		# Store the headers and body
		self.initialize(data, parts)
		# Store the other parts of the response
		self.response = data.split("\r\n")[0]
		self.version = LooseVersion(parts['version'])
		self.status = int(parts['status'])
		self.reason = parts['reason']
