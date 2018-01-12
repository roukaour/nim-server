# Remy Oukaour, 107122849
# CSE 310, Group 2

"""
This module defines classes for implementing Nim servers.
"""

__all__ = ['NimUser', 'NimGame', 'NimServer', 'ForkingNimServer',
	'ThreadingNimServer', 'BaseNimRequestHandler']

import socket
import SocketServer
import random
import threading
from nimlib import *

class NimUser(object):
	"""
	Represents a user connected to a server.
	"""
	
	def __init__(self, socket, name=None):
		"""
		Instantiate a user.
		"""
		# Initialize the user's socket
		self.socket = socket
		# Initialize the user's name
		self.name = name
		# Initially the user is not playing a game
		self.game = None
		# Initially the user is not observing a game
		self.observing = None
		# Initially the user has no queued messages
		self.queue = ''
	
	def enqueue(self, message):
		"""
		Add a message to the queue.
		"""
		self.queue += "\n" + message
	
	def get_queue(self):
		"""
		Return the queued messages.
		"""
		return self.queue
	
	def dequeue(self):
		"""
		Empty and return the queued messages.
		"""
		queued = self.queue
		self.queue = ''
		return queued

class NimGame(object):
	"""
	Represents an ongoing game of Nim.
	"""
	
	# The game ID for the next NimGame instance
	next_game = 1
	
	def __init__(self, player1, player2):
		"""
		Start a game of Nim between two players.
		"""
		# Initialize the game ID
		self.id = NimGame.next_game
		# Increment the class game ID for the next instance
		NimGame.next_game += 1
		# Choose a random number of sets
		m = random.randint(NIM_MIN_SETS, NIM_MAX_SETS)
		# Choose a random amount for each set
		self.sets = [random.randint(NIM_MIN_OBJECTS, NIM_MAX_OBJECTS)
			for _ in range(m)]
		# Player 1 has the first turn
		self.player1 = self.playing = player1
		# Player 2 waits for their turn
		self.player2 = self.waiting = player2
		# Initially no users are observing the game
		self.observers = set()
	
	def get_state(self):
		"""
		Return a description of the game state.
		"""
		# Show the two players' names
		state = '{} vs. {}'.format(self.player1.name, self.player2.name)
		# Show the set IDs
		state += "\nset   "
		state += '  '.join(map(str, range(1, len(self.sets) + 1)))
		# Show the object amounts
		state += "\nsize  "
		state += '  '.join(map(str, self.sets))
		return state
	
	def move(self, player, n, s):
		"""
		Apply a player's move and return a tuple of the Nim status code and
		descriptive string with which to respond.
		"""
		# Check that it is the player's turn
		if self.playing != player:
			return (METHOD_NOT_ALLOWED, 'It is not your turn!')
		# Check that the set ID is valid
		if s < 1 or s > len(self.sets):
			return (NOT_FOUND, 'There is no set {}!'.format(s))
		# Check that the object amount is valid
		if n < 1 or n > self.sets[s-1]:
			return (ILLEGAL_MOVE,
				'You cannot take {} object{} from set {}!'.format(
				n, 's' if n != 1 else '', s))
		# Remove the objects from the set
		self.sets[s-1] -= n
		# Switch whose turn it is
		self.playing, self.waiting = self.waiting, self.playing
		# Create a description of the move
		message = '{} takes {} from set {}'.format(player.name, n, s)
		message += "\n      "
		message += '  '.join(map(str, self.sets))
		# Check if the move removed the last objects and ended the game
		if not sum(self.sets):
			message += "\n{} wins.".format(player.name)
			return (END_GAME, message)
		return (OK, message)
	
	def is_playing(self, user):
		"""
		Return True if a user is playing this game, False otherwise.
		"""
		return user is self.player1 or user is self.player2
	
	def add_observer(self, user):
		"""
		Let a user observe this game.
		"""
		user.observing = self
		self.observers.add(user)
	
	def remove_observer(self, user):
		"""
		Stop a user from observing this game.
		"""
		user.observing = None
		self.observers.remove(user)
	
	def is_observing(self, user):
		"""
		Return True if a user is observing this game, False otherwise.
		"""
		return user in self.observers
	
	def all_observers(self):
		"""
		Return a generator for all the users observing this game.
		"""
		for observer in self.observers:
			yield observer

class NimServer(SocketServer.TCPServer):
	"""
	Represents a Nim server which can accept connections from clients and
	send responses. Modeled after Python 3's http.server.HTTPServer class.
	"""
	
	def __init__(self, server_address, RequestHandlerClass):
		"""
		Instantiate a Nim server. Binds a TCP socket to the server address.
		"""
		# Bind to the socket created by the parent class, but do not listen
		try:
			SocketServer.TCPServer.__init__(self, server_address,
				RequestHandlerClass, bind_and_activate=False)
			self.server_bind()
		except socket.error as e:
			raise NimException(e.strerror)
		# Initialize the server's lock
		self.lock = threading.Lock()
		# Initialize the server's host and port
		self.host, self.port = self.server_address
		# Initially the socket:NimUser map is empty
		self.users = {}
		# Initially the username:NimUser map is empty
		self.usernames = {}
		# Initially the id:NimGame map is empty
		self.games = {}
	
	def listen(self):
		"""
		Start listening on the socket for incoming connections.
		"""
		try:
			self.server_activate()
		except socket.error as e:
			raise NimException(e.strerror)
	
	def add_user(self, socket, name=None):
		"""
		Add a new user to the server and return their NimUser instance.
		"""
		user = NimUser(socket, name)
		self.users[socket] = user
		return user
	
	def get_user(self, socket):
		"""
		Return the user with a socket, or None if none exists.
		"""
		return self.users.get(socket, None)
	
	def get_user_named(self, name):
		"""
		Return the user with a username, or None if none exists.
		"""
		return self.usernames.get(name, None)
	
	def name_user(self, user, name):
		"""
		Assign a name to a user.
		"""
		user.name = name
		self.usernames[name] = user
	
	def remove_user(self, user):
		"""
		Remove a user from the server.
		"""
		del self.users[user.socket]
		if user.name:
			del self.usernames[user.name]
		if user.observing:
			user.observing.remove_observer(user)
	
	def all_users(self, logged_in=None, available=None):
		"""
		Return a generator for all the users connected to the server. Optionally
		limit them to users with usernames and/or users not playing games.
		"""
		for user in self.users.values():
			if logged_in is False and user.name:
				continue
			if logged_in is True and not user.name:
				continue
			if available is False and not user.game:
				continue
			if available is True and user.game:
				continue
			yield user
	
	def username_taken(self, name):
		"""
		Return True if a name is assigned to a user, False otherwise.
		"""
		return name in self.usernames
	
	def start_game(self, player1, player2):
		"""
		Start a game between two users and return the NimGame instance.
		"""
		game = NimGame(player1, player2)
		self.games[game.id] = player1.game = player2.game = game
		return game
	
	def end_game(self, game):
		"""
		End a game and remove it from the server.
		"""
		game.player1.game = game.player2.game = None
		del self.games[game.id]
	
	def get_game(self, id):
		"""
		Return the game with an ID, or None if none exists.
		"""
		return self.games.get(id, None)
	
	def all_games(self):
		"""
		Return a generator for all the games on the server.
		"""
		for game in self.games.values():
			yield game

class ForkingNimServer(SocketServer.ForkingMixIn, NimServer):
	"""
	Extends NimServer to start a new process for each connection.
	"""

class ThreadingNimServer(SocketServer.ThreadingMixIn, NimServer):
	"""
	Extends NimServer to start a new thread for each connection.
	"""

class BaseNimRequestHandler(SocketServer.BaseRequestHandler):
	"""
	Represents a connection to a NimServer. An instance of this class is created
	for each request.
	"""
	
	def __init__(self, socket, client_address, server):
		"""
		Instantiate a Nim request handler and handle requests until finished.
		Identical to SocketServer.BaseRequestHandler.__init__ except for
		renaming self.request to self.socket, since self.request is
		defined in setup() to hold the NimRequest object.
		"""
		self.socket = socket
		self.client_address = client_address
		self.server = server
		self.setup()
		try:
			self.handle()
		finally:
			self.finish()
	
	def setup(self):
		"""
		Called before the handle() method to initialize the handler.
		The default implementation initializes some instance variables
		and adds a NimUser object to the server.
		"""
		# Initialize the client's host and port
		self.host, self.port = self.client_address
		# Initially there is no stored NimRequest object
		self.request = None
		# Initially there is no stored NimResponse object
		self.response = None
		# Add the user of this connection to the server
		self.server.lock.acquire()
		self.server.add_user(self.socket)
		self.server.lock.release()
	
	def handle(self):
		"""
		Service a request by a client.
		"""
		# Repeatedly parse and handle client requests until disconnection
		while self.parse_request():
			method_method = None
			# Check that the client supports this version of Nim
			if self.request.version > NIM_VERSION:
				method_method = self.unsupported_version
			else:
				do_method = 'do_' + self.request.method
				# Check that the request method is supported
				if not hasattr(self, do_method):
					method_method = self.unsupported_method
				else:
					method_method = getattr(self, do_method)
			# Call the appropriate method to handle this request
			try:
				self.server.lock.acquire()
				method_method()
				self.server.lock.release()
			except Exception as e:
				raise NimException(e.message)
	
	def finish(self):
		"""
		Called after the handle() method to clean up after the handler.
		The default implementation does nothing.
		"""
	
	def parse_request(self):
		"""
		Receive a request from the client and store it as a NimRequest object.
		Return True if the request could be parsed, False otherwise.
		"""
		# Do not receive responses after connection is closed
		if not self.socket:
			raise ValueError('operation on closed connection')
		# Read request from client
		try:
			data = self.socket.recv(4096)
		except socket.error as e:
			self.request = None
			return False
		# Pending response to client
		self.response = None
		# Store request as parsed NimRequest object, if possible
		try:
			self.request = NimRequest(data)
			return True
		except NimException as e:
			self.request = None
			return False
	
	def send_response(self, status, body='', headers=None):
		"""
		Send a response to the client and store it as a NimResponse object.
		Return True if the response could be parsed, False otherwise.
		"""
		# Do not send responses after connection is closed
		if not self.socket:
			raise ValueError('operation on closed connection')
		# Check if the user has queued messages to be sent first
		this_user = self.server.get_user(self.socket)
		if this_user.queue:
			self.send_response(CONTINUED, this_user.dequeue())
		# Check that status code is valid
		if status not in responses:
			raise ValueError('no such status: {}'.format(status))
		reason = responses[status]
		# Convert header dictionary to CRLF-separated string
		headers = headers or dict()
		headers['Content-Length'] = len(body)
		headers = ''.join("{}: {}\r\n".format(h, headers[h]) for h in headers)
		# Send constructed packet to client
		data = 'NIM/{} {} {}\r\n{}\r\n{}'.format(NIM_VERSION, status,
			reason, headers, body)
		try:
			self.socket.sendall(data)
		except socket.error as e:
			raise NimException(e.strerror)
		# Wait for request from client
		self.request = None
		# Store response as parsed NimResponse object, if possible
		try:
			self.response = NimResponse(data)
			return True
		except NimException as e:
			self.response = None
			return False
	
	def unsupported_version(self):
		"""
		Respond to a request sent by an unsupported version of Nim.
		"""
		self.send_response(NIM_VERSION_NOT_SUPPORTED,
			'Unsupported Nim version ({})'.format(self.request.version))
	
	def unsupported_method(self):
		"""
		Respond to a request using an unsupported method.
		"""
		self.send_response(NOT_IMPLEMENTED,
			'Unsupported method ({})'.format(self.request.method))
	
	def do_LOGIN(self):
		"""
		Respond to a LOGIN request.
		"""
		this_user = self.server.get_user(self.socket)
		# Check that the user is not already logged in
		if this_user.name:
			self.send_response(METHOD_NOT_ALLOWED,
				'You are already logged in!')
			return
		new_name = self.request.params[0]
		# Check that the requested username is available
		if self.server.username_taken(new_name):
			self.send_response(IMPOSSIBLE,
				"The username '{}' is already taken!".format(new_name))
			return
		# Log the user in with the requested username
		self.server.name_user(this_user, new_name)
		self.send_response(HELLO, 'Hello, {}!'.format(new_name))
	
	def do_REMOVE(self):
		"""
		Respond to a REMOVE request.
		"""
		this_user = self.server.get_user(self.socket)
		this_game = this_user.game
		# Check that the user is playing a game
		if not this_game:
			self.send_response(METHOD_NOT_ALLOWED,
				'You are not playing a game!')
			return
		n, s = self.request.params
		# Attempt to make the move
		status, body = this_game.move(this_user, n, s)
		self.send_response(status, body)
		# Notify the opponent and observers of the move
		if status < ERROR:
			opponent = this_game.playing
			opponent.enqueue(body)
			for observer in this_game.all_observers():
				observer.enqueue(body)
		# Check if the move ended the game
		if status == END_GAME:
			self.server.end_game(this_game)
	
	def do_BYE(self):
		"""
		Respond to a BYE request.
		"""
		try:
			this_user = self.server.get_user(self.socket)
			this_name = this_user.name or ''
			self.send_response(BYE, 'Goodbye{}!'.format(', ' +
				this_name if this_name else ''))
		finally:
			this_user = self.server.get_user(self.socket)
			this_game = this_user.game
			# Check if the user was playing a game
			if this_game:
				# Notify the opponent and observers of the departure
				message = '{} has quit.'.format(this_user.name)
				this_game.player1.enqueue(message)
				this_game.player2.enqueue(message)
				for observer in this_game.all_observers():
					observer.enqueue(message)
				# End the game
				self.server.end_game(this_game)
			# Remove user from server
			self.server.remove_user(this_user)
	
	def do_GAMES(self):
		"""
		Respond to a GAMES request.
		"""
		games = []
		# List all the ongoing games, if any
		for game in self.server.all_games():
			games.append('{} - {} vs. {}'.format(game.id,
				game.player1.name, game.player2.name))
		if not games:
			games.append('There are no ongoing games.')
		self.send_response(OK, "\n".join(games))
	
	def do_WHO(self):
		"""
		Respond to a WHO request.
		"""
		players = []
		# List all the logged-in users available to play a game, if any
		for player in self.server.all_users(logged_in=True, available=True):
			if player.socket != self.socket:
				players.append(player.name)
		if not players:
			players.append('There are no available players.')
		self.send_response(OK, "\n".join(players))
	
	def do_PLAY(self):
		"""
		Respond to a PLAY request.
		"""
		this_user = self.server.get_user(self.socket)
		# Check that the user is logged in
		if not this_user.name:
			self.send_response(METHOD_NOT_ALLOWED,
				'You are not logged in!')
			return
		# Check that the user is not already playing a game
		if this_user.game:
			self.send_response(METHOD_NOT_ALLOWED,
				'You are already playing a game!')
			return
		opponent_name = self.request.params[0]
		opponent = self.server.get_user_named(opponent_name)
		# Check that the requested opponent exists
		if not opponent:
			self.send_response(NOT_FOUND,
				'There is no user named {}!'.format(opponent_name))
			return
		# Check that the requested opponent is not the user
		if opponent is this_user:
			self.send_response(FORBIDDEN,
				'You cannot play with yourself!')
			return
		# Check that the requested opponent is not already playing a game
		if opponent.game:
			self.send_response(IMPOSSIBLE,
				'{} is not available to play!'.format(opponent_name))
			return
		# Start a game between the user and opponent
		new_game = self.server.start_game(this_user, opponent)
		body = new_game.get_state()
		self.send_response(BEGIN_GAME, body)
		# Notify the opponent of the game
		opponent.enqueue(body)
	
	def do_OBSERVE(self):
		"""
		Respond to an OBSERVE request.
		"""
		id = self.request.params[0]
		game = self.server.get_game(id)
		# Check that the requested game exists
		if not game:
			self.send_response(NOT_FOUND, 'There is no game {}!'.format(id))
			return
		this_user = self.server.get_user(self.socket)
		# Check that the user is not already observing the game
		if game.is_observing(this_user):
			self.send_response(IMPOSSIBLE,
				'You are already observing game {}!'.format(id))
			return
		# Check that the user is not playing the requested game
		if game.is_playing(this_user):
			self.send_response(FORBIDDEN,
				'You cannot observe your own game!')
			return
		# Add the user as an observer of the game
		game.add_observer(this_user)
		self.send_response(OK, 'You are observing game {}.'.format(id))
	
	def do_UNOBSERVE(self):
		"""
		Respond to an UNOBSERVE request.
		"""
		id = self.request.params[0]
		game = self.server.get_game(id)
		# Check that the requested game exists
		if not game:
			self.send_response(NOT_FOUND, 'There is no game {}!'.format(id))
			return
		this_user = self.server.get_user(self.socket)
		# Check that the user is observing the game
		if not game.is_observing(this_user):
			self.send_response(IMPOSSIBLE,
				'You are not observing game {}!'.format(id))
			return
		# Remove the user as an observer of the game
		game.remove_observer(this_user)
		self.send_response(OK, 'You are no longer observing game {}.'.format(id))
	
	def do_PING(self):
		"""
		Respond to a PING request.
		"""
		this_user = self.server.get_user(self.socket)
		# Remove the response message from the user's queue
		self.send_response(OK, this_user.dequeue())
