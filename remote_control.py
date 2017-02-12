#!/usr/bin/python

import time
import curses
import signal
import sys
import socket
from subprocess import call

def cleanup():
	global sock

	sock.close()
	curses.endwin()

def signal_handler(singnal, frame):
	cleanup()
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

stdscr = curses.initscr()
stdscr.keypad(1)

# Create a UDS socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

# Connect the socket to the port where the server is listening
server_address = './bot_direction.sock'

try:
	sock.connect(server_address)

except socket.error, msg:
	print >>sys.stderr, msg
	sys.exit(1)

try:
	while True:
		char = stdscr.getch()

		if char == curses.KEY_UP:
			sock.sendall("forward")
		elif char  == curses.KEY_DOWN:
			sock.sendall("reverse")
		elif char == curses.KEY_LEFT:
			sock.sendall("left")
		elif char == curses.KEY_RIGHT:
			sock.sendall("right")
		else:
			sock.sendall("stop")

		time.sleep(0.01)

except Exception as e:
	cleanup()
	sys.exit(1)

cleanup()
