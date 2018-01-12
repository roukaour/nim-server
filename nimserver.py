#!/usr/bin/env python

# Remy Oukaour, 107122849
# CSE 310, Group 2

"""
Usage: nimserver.py [-h|--help] [-v|--version] [PORT=7849]

This is a command-line server for the game of Nim.
"""

from __future__ import print_function

import sys
import argparse
import threading
import socket
from datetime import datetime
from distutils.version import LooseVersion
from nim import nimlib
from nim.server import *
from nimutils import *

# A "message of the day"-style ASCII art banner sent to clients upon connection
WELCOME_BANNER = """                           W e l c o m e   t o . . .
 _____ _             ____                               __   _   _ _
|_   _| |__   ___   / ___| __ _ _ __ ___   ___    ___  / _| | \\ | (_)_ __ ___
  | | | '_ \\ / _ \\ | |  _ / _` | '_ ` _ \\ / _ \\  / _ \\| |_  |  \\| | | '_ ` _ \\
  | | | | | |  __/ | |_| | (_| | | | | | |  __/ | (_) |  _| | |\\  | | | | | | |
  |_| |_| |_|\\___|  \\____|\\__,_|_| |_| |_|\\___|  \\___/|_|   |_| \\_|_|_| |_| |_|

Have fun on this server!
"""

class NimTextRequestHandler(BaseNimRequestHandler):
	"""
	Represents a connection to a NimTextServer. An instance of this class is
	created for each request.
	"""
	
	def setup(self):
		"""
		Called before the handle() method to initialize the handler.
		"""
		BaseNimRequestHandler.setup(self)
		this_user = self.server.get_user(self.socket)
		# Send the user a welcome banner
		this_user.enqueue(WELCOME_BANNER)
		host, port = self.client_address
		thread = threading.current_thread()
		# Print the connection information
		print('Connection from {}:{} on socket {}, thread {}'.format(host,
			port, self.socket.fileno(), thread.ident))
	
	def finish(self):
		"""
		Called after the handle() method to clean up after the handler.
		"""
		BaseNimRequestHandler.finish(self)
		host, port = self.client_address
		thread = threading.current_thread()
		# Print the disconnection information
		print('Disconnection by {}:{} on socket {}, thread {}'.format(host,
			port, self.socket.fileno(), thread.ident))
	
	def preamble(self):
		"""
		Print information about an individual request.
		"""
		host, port = self.client_address
		timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
		print('{}:{} [{}] "{}"'.format(host, port, timestamp,
			self.request.request), end='')
	
	def conclusion(self):
		"""
		Print information about a response to an individual request.
		"""
		print(' {} {} {}'.format(self.response.status,
			nimlib.responses[self.response.status],
			repr(self.response.body)))
	
	def unsupported_version(self):
		"""
		Respond to a request sent by an unsupported version of Nim.
		"""
		self.preamble()
		BaseNimRequestHandler.unsupported_version(self)
		self.conclusion()
	
	def unsupported_method(self):
		"""
		Respond to a request using an unsupported method.
		"""
		self.preamble()
		BaseNimRequestHandler.unsupported_method(self)
		self.conclusion()
	
	def do_LOGIN(self):
		"""
		Respond to a LOGIN request.
		"""
		self.preamble()
		BaseNimRequestHandler.do_LOGIN(self)
		self.conclusion()
	
	def do_REMOVE(self):
		"""
		Respond to a REMOVE request.
		"""
		self.preamble()
		BaseNimRequestHandler.do_REMOVE(self)
		self.conclusion()
	
	def do_BYE(self):
		"""
		Respond to a BYE request.
		"""
		self.preamble()
		BaseNimRequestHandler.do_BYE(self)
		self.conclusion()
	
	def do_GAMES(self):
		"""
		Respond to a GAMES request.
		"""
		self.preamble()
		BaseNimRequestHandler.do_GAMES(self)
		self.conclusion()
	
	def do_WHO(self):
		"""
		Respond to a WHO request.
		"""
		self.preamble()
		BaseNimRequestHandler.do_WHO(self)
		self.conclusion()
	
	def do_PLAY(self):
		"""
		Respond to a PLAY request.
		"""
		self.preamble()
		BaseNimRequestHandler.do_PLAY(self)
		self.conclusion()
	
	def do_OBSERVE(self):
		"""
		Respond to an OBSERVE request.
		"""
		self.preamble()
		BaseNimRequestHandler.do_OBSERVE(self)
		self.conclusion()
	
	def do_UNOBSERVE(self):
		"""
		Respond to an UNOBSERVE request.
		"""
		self.preamble()
		BaseNimRequestHandler.do_UNOBSERVE(self)
		self.conclusion()
	
	def do_PING(self):
		"""
		Respond to a PING request.
		"""
		this_user = self.server.get_user(self.socket)
		message = this_user.get_queue() if this_user else None
		# Only print the request information for non-empty responses
		if message:
			self.preamble()
		BaseNimRequestHandler.do_PING(self)
		# Only print the response information for non-empty responses
		if message:
			self.conclusion()

class NimTextServer(object):
	"""
	A text-based server for the game of Nim.
	"""
	
	# The server version
	version = LooseVersion('1.0')
	
	def __init__(self):
		"""
		Instantiate a Nim text server.
		"""
		fullversion = 'Nim server {} (protocol NIM/{})'.format(self.version,
			nimlib.NIM_VERSION)
		# Create a parser for the command-line arguments
		argp = argparse.ArgumentParser(
			description='Server for the game of Nim.',
			formatter_class=argparse.ArgumentDefaultsHelpFormatter)
		argp.add_argument('host', metavar='HOST', type=str,
			default=socket.gethostname(), nargs='?',
			help='the host machine of the Nim server')
		argp.add_argument('port', metavar='PORT', type=tcp_port_arg,
			default=nimlib.NIM_PORT, nargs='?',
			help='the port listened to by the Nim server')
		argp.add_argument('-v', '--version', action='version',
			version=fullversion)
		# Parse the given arguments
		args = argp.parse_args()
		# Create a threaded Nim server to handle requests
		self.server = ThreadingNimServer((args.host, args.port),
			NimTextRequestHandler)
	
	def serve_forever(self):
		"""
		Handle requests until sent a shutdown signal or exception.
		"""
		self.server.listen()
		# Print information needed for clients to connect
		print('Listening on {}:{}... (^C to shut down)'.format(
			self.server.host, self.server.port))
		# Listen for requests until sent a shutdown signal or exception
		try:
			self.server.serve_forever()
		except (EOFError, KeyboardInterrupt) as e:
			print('Shutting down...')
			self.server.shutdown()
		except Exception as e:
			print(e)
			print('Shutting down...')
			self.server.shutdown()

def main():
	"""
	Start a Nim server.
	"""
	try:
		server = NimTextServer()
		server.serve_forever()
	except nimlib.NimException as e:
		print("Unable to serve!\n{}".format(e.message))

if __name__ == '__main__':
	main()
