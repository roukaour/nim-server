# Remy Oukaour, 107122849
# CSE 310, Group 2

"""
Utility functions for the text-based Nim client and server programs.
"""

__all__ = ['tcp_port_arg']

import argparse

def tcp_port_arg(port):
	"""
	Convert a value to a valid TCP port number (a non-negative integer), if possible.
	"""
	try:
		port = int(port)
		if not isinstance(port, int) or port < 0:
			raise ValueError('not a valid TCP port number: {}'.format(port))
		return port
	except (TypeError, ValueError) as e:
		message = '{!r} is not a valid port number.'.format(port)
		raise argparse.ArgumentTypeError(message)
