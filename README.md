# Nim

This project implements a text-based client and server for the game of Nim.

To run the server, enter:

```
	python nimserver.py
```

By default it will serve on the current machine's hostname, port 7849.

To serve on another host or port, enter:

```
	python nimserver.py HOST PORT
```

For help, enter:

```
	python nimserver.py -h
```

To run the client, connecting to a specific server, enter:

```
	python nim.py HOST
```

By default it will connect to port 7849.

To connect to another port, enter:

```
	python nim.py HOST PORT
```

For help, enter:

```
	python nim.py -h
```
