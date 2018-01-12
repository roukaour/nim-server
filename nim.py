#!/usr/bin/env python

# Remy Oukaour, 107122849
# CSE 310, Group 2

"""
Usage: nim.py [-h|--help] [-v|--version] HOST [PORT=7849]

This is a text-based client for the game of Nim.
"""

from __future__ import print_function

import sys
import argparse
import threading
import time
from distutils.version import LooseVersion
from functools import wraps
from nim import nimlib
from nim.client import *
from nimutils import *

class Commands(object):
	"""
	A decorator that adds parameter checking to methods intended for handling
	user commands.
	"""
	
	def __init__(self, action=print):
		"""
		Initialize a command map.
		"""
		# Initially the command:method map is empty
		self.commands = {}
		# Store the action callback for handling errors
		self.action = action
	
	def __call__(self, command, *params):
		"""
		Return a decorator that will add parameter checking to the method
		it decorates.
		"""
		def decorator(method):
			# Define a new method that checks parameters
			@wraps(method)
			def wrapper(slf, *args):
				# Check that there are not more arguments than parameters
				if len(args) > len(params):
					self.action(
						"Too many arguments to '{}'".format(
						command))
					return
				missing = len(params) - len(args)
				# Check that there are not fewer arguments than parameters
				if missing > 0:
					self.action(
						"Missing {} argument{} to '{}'".format(
						', '.join(params[-missing:]),
						's' if missing > 1 else '', command))
					return
				# Apply the handler method to the arguments
				return method(slf, *args)
			# Map the command name to the handler method
			self.commands[command] = wrapper
			return wrapper
		return decorator
	
	def __getitem__(self, slice):
		"""
		Return the method for a command name.
		"""
		return self.commands[slice]
	
	def __iter__(self):
		"""
		Return a generator for all the command names.
		"""
		for command in self.commands:
			yield command

class NimTextClient(object):
	"""
	A text-based client for the game of Nim.
	"""
	
	# The client version
	version = LooseVersion('1.0')
	
	# A mapping from command names to their methods
	commands = Commands()
	
	def __init__(self, ps='> '):
		"""
		Instantiate a Nim text client.
		"""
		fullversion = 'Nim {} (protocol NIM/{})'.format(self.version,
			nimlib.NIM_VERSION)
		# Create a parser for the command-line arguments
		argp = argparse.ArgumentParser(
			description='Client for the game of Nim.',
			formatter_class=argparse.ArgumentDefaultsHelpFormatter)
		# Describe the host, port, and version arguments
		argp.add_argument('host', metavar='HOST', type=str,
			help='the host machine of the Nim server')
		argp.add_argument('port', metavar='PORT', type=tcp_port_arg,
			default=nimlib.NIM_PORT, nargs='?',
			help='the port listened to by the Nim server')
		argp.add_argument('-v', '--version', action='version',
			version=fullversion)
		# Parse the given arguments
		args = argp.parse_args()
		# Create a Nim client to send requests
		self.client = NimClient((args.host, args.port))
		# Initially not prompting the user for a command
		self.prompting = False
		# Store the command prompt string
		self.ps = ps
		# Initially not PINGing the server for queued messages
		self.pingd = threading.Thread(target=self.ping)
		self.pingd.daemon = True
	
	def prompt(self):
		"""
		Prompt the user for a command and handle it.
		"""
		# Prompt the user for a command
		self.prompting = True
		input = raw_input(self.ps)
		self.prompting = False
		tokens = input.split()
		# Check that the user has entered something
		if not tokens:
			return
		command, arguments = tokens[0], tokens[1:]
		# Check that the command is valid
		if command not in self.commands:
			print("Unknown command: '{}'".format(command))
			return
		# Call the appropriate method to handle this command
		command_method = self.commands[command]
		command_method(self, *arguments)
	
	def run(self):
		"""
		Handle commands until sent a shutdown signal or exception.
		"""
		# Connect to the server
		try:
			self.client.connect()
		except nimlib.NimException as e:
			print("Could not connect to {}:{}!\n{}".format(self.client.host,
				self.client.port, e.message))
			self.client = None
			self.exit()
		# Start the PING daemon to get queued responses
		self.running = True
		self.pingd.start()
		# Print helpful information
		print('Welcome to Nim on {}:{}!'.format(self.client.host,
			self.client.port))
		print("Type 'help' for help, 'bye' to exit.")
		# Prompt the user for commands
		try:
			while True:
				self.prompt()
		except (EOFError, KeyboardInterrupt) as e:
			print()
			self.exit()
		except nimlib.NimException as e:
			print(e.message)
			self.exit()
	
	def ping(self):
		"""
		Send PING requests periodically until the client stops running.
		"""
		while self.running:
			# Check that the client is not handling a command
			if not self.prompting:
				# Wait for one second before PINGing again
				time.sleep(1)
				continue
			try:
				# Send a PING request to the server
				response = self.client.ping()
				# Print the response if it is non-empty
				if response.body:
					print(response.body, self.ps,
						sep="\n", end='')
				while response.status == nimlib.CONTINUED:
					response = self.client.continuation()
					if response.body:
						print(response.body, self.ps,
							sep="\n", end='')
				# Wait for one second before PINGing again
				time.sleep(1)
			except nimlib.NimException as e:
				print(e.message)
				break
	
	def exit(self):
		"""
		Disconnect from the server and exit the client.
		"""
		try:
			# Check that a BYE request has been send
			if self.client:
				response = self.client.bye()
		finally:
			# Exit the client
			self.client = None
			self.running = False
			print('Exiting...')
			sys.exit()
	
	def continued(self, response=None):
		"""
		Get further respones after a 300 Continued response.
		"""
		if not response:
			return
		while response.status == nimlib.CONTINUED:
			# Get the next response
			response = self.client.continuation()
			# Print the response
			print(response.body)
	
	@commands('help')
	def help(self):
		"""
		Handle the 'help' command.
		"""
		# Print a list of commands
		print('help - display this help message')
		print('login NAME - log in to the server with this username')
		print('games - list all the current ongoing games')
		print('who - list all the users available to play')
		print('play NAME - begin a game with this user')
		print('remove N S - remove N objects from set S on your turn')
		print('observe ID - start observing this ongoing game')
		print('unobserve ID - stop observing this game')
		print('bye - log off the server and exit')
	
	@commands('login', 'NAME')
	def login(self, name):
		"""
		Handle the 'login NAME' command.
		"""
		# Check that the provided username is valid
		if not is_nim_username(name):
			print('Invalid name; must be 1 to 32 characters from A-Z a-z 0-9 _ - + .')
			return
		# Send a LOGIN request to the server
		response = self.client.login(name)
		# Print the response
		print(response.body)
		self.continued(response)
	
	@commands('games')
	def games(self):
		"""
		Handle the 'games' command.
		"""
		# Send a GAMES request to the server
		response = self.client.games()
		# Print the response
		print(response.body)
		self.continued(response)
	
	@commands('who')
	def who(self):
		"""
		Handle the 'who' command.
		"""
		# Send a WHO request to the server
		response = self.client.who()
		# Print the response
		print(response.body)
		self.continued(response)
	
	@commands('play', 'NAME')
	def play(self, name):
		"""
		Handle the 'play NAME' command.
		"""
		# Check that the provided username is valid
		if not is_nim_username(name):
			print('Invalid name; must be 1 to 32 characters from A-Z a-z 0-9 _ - + .')
			return
		# Send a PLAY request to the server
		response = self.client.play(name)
		# Print the response
		print(response.body)
		self.continued(response)
	
	@commands('remove', 'N', 'S')
	def remove(self, n, s):
		"""
		Handle the 'remove N S' command.
		"""
		# Check that the provided object amount is valid
		try:
			n = int(n)
			if not is_natural(n):
				raise ValueError('{} is not a natural number'.format(n))
		except ValueError as e:
			print('Invalid object count; must be a positive integer')
			return
		# Check that the provided set ID is valid
		try:
			s = int(s)
			if not is_natural(s):
				raise ValueError('{} is not a natural number'.format(s))
		except ValueError as e:
			print('Invalid set ID; must be a positive integer')
			return
		# Send a REMOVE request to the server
		response = self.client.remove(n, s)
		# print the response
		print(response.body)
		self.continued(response)
	
	@commands('observe', 'ID')
	def observe(self, id):
		"""
		Handle the 'observe ID' command.
		"""
		# Check that the provided game ID is valid
		try:
			id = int(id)
			if not is_natural(id):
				raise ValueError('{} is not a natural number'.format(id))
		except ValueError as e:
			print('Invalid game ID; must be a positive integer')
			return
		# Send an OBSERVE request to the server
		response = self.client.observe(id)
		# Print the response
		print(response.body)
		self.continued(response)
	
	@commands('unobserve', 'ID')
	def unobserve(self, id):
		"""
		Handle the 'unobserve ID' command.
		"""
		# Check that the provided game ID is valid
		try:
			id = int(id)
			if not is_natural(id):
				raise ValueError('{} is not a natural number'.format(id))
		except ValueError as e:
			print('Invalid game ID; must be a positive integer')
			return
		# Send an UNOBSERVE request to the server
		response = self.client.unobserve(id)
		# Print the response
		print(response.body)
		self.continued(response)
	
	@commands('bye')
	def bye(self):
		"""
		Handle a 'bye' command.
		"""
		try:
			# Send a BYE request to the server
			response = self.client.bye()
			# Print the response
			print(response.body)
			self.continued(response)
		finally:
			# Exit the client
			self.client = None
			self.exit()

def main():
	"""
	Start a Nim client.
	"""
	client = NimTextClient()
	client.run()

if __name__ == '__main__':
	main()
