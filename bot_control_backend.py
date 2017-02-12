#!/usr/bin/python

#############################################################
#
# bot_control_backend.py
#
# Sets up a backend listener for clients to connect to,
# in order to send commands to drive the bot
#
# Employs optional collision detection
# This is done by checking memcached values for front and
# rear ultrasonic sensor outputs.  To make use of this
# a separate backend needs to be running for the sensors
# that continuously updates these memcached values
#
# Author: Brian Helm
# Created On: 2017-02-10
#
############################################################# 

import RPi.GPIO as GPIO
import threading
import time
import signal
import sys
import socket
import os
import os.path
import pylibmc

# global flag to announce what direction we're moving
direction = "stopped"

# global flag to announce that we're in autonomous mode
autonomousMode = False

def forward():
	global direction
	direction = "forward"

	# don't attempt to move forward if we're too close to an object
	if not checkDistanceReading("us_front_distance"):
		GPIO.output(LEFT_FORWARD, 1)
		GPIO.output(LEFT_REVERSE, 0)
		GPIO.output(RIGHT_FORWARD, 1)
		GPIO.output(RIGHT_REVERSE, 0)
def reverse():
	global direction
	direction = "reverse"

	# don't attempt to move backward if we're too close to an object
	if not checkDistanceReading("us_rear_distance"):
		GPIO.output(LEFT_FORWARD, 0)
		GPIO.output(LEFT_REVERSE, 1)
		GPIO.output(RIGHT_FORWARD, 0)
		GPIO.output(RIGHT_REVERSE, 1)

def right():
	global direction

	direction = "right"

	GPIO.output(LEFT_FORWARD, 1)
	GPIO.output(LEFT_REVERSE, 0)
	GPIO.output(RIGHT_FORWARD, 0)
	GPIO.output(RIGHT_REVERSE, 1)

	time.sleep(0.05)

	GPIO.output(LEFT_FORWARD, 0)
	GPIO.output(LEFT_REVERSE, 0)
	GPIO.output(RIGHT_FORWARD, 0)
	GPIO.output(RIGHT_REVERSE, 0)

def left():
	global direction

	direction = "left"

	GPIO.output(LEFT_FORWARD, 0)
	GPIO.output(LEFT_REVERSE, 1)
	GPIO.output(RIGHT_FORWARD, 1)
	GPIO.output(RIGHT_REVERSE, 0)

	time.sleep(0.05)

	GPIO.output(LEFT_FORWARD, 0)
	GPIO.output(LEFT_REVERSE, 0)
	GPIO.output(RIGHT_FORWARD, 0)
	GPIO.output(RIGHT_REVERSE, 0)

def stop():
	global direction

	direction = "stopped"

	GPIO.output(LEFT_FORWARD, 0)
        GPIO.output(LEFT_REVERSE, 0)
        GPIO.output(RIGHT_FORWARD, 0)
        GPIO.output(RIGHT_REVERSE, 0)

def cleanup():
	global collisionDetectThread
	global autonomousThread
	global autonomousMode
	global server
	global sockfile

	collisionDetectThread.do_run = False
	autonomousThread.do_run = False
	
	autonomousMode = False

	server.close()
	os.remove(sockfile)

	stop()

	GPIO.cleanup()

# signal handling thread to gracefully shutdown on Crtl+c
def signal_handler(signal, frame):
	cleanup()
	sys.exit(0)


# attempts to read front or rear memcached reading for distance away from closest object
def checkDistanceReading(key):
	mem = pylibmc.Client(["127.0.0.1"], binary=True, behaviors={"tcp_nodelay": True, "ketama": True})

	retVal = False

	distance = mem.get(key)

	if distance != None:
		try:
			if float(distance) <= 2.5:
				stop()
				
				retVal = True
		except Exception as e:
			retVal = False		


	return retVal

# thread function to make bot run in autonomous mode
# basically tells the bot to move forward until collision detection thread says it's about to hit something
# then it makes the bot move left twice and then attempt to go forward again
# it will repeat the process as ncessary until collision detection no longer sees a danger
def autonomous():
	global autonomousMode
	global direction

	t = threading.currentThread()

	# keep running until our main thread sets "do_run" to false
        while getattr(t, "do_run", True):
		while autonomousMode:
			if direction != "forward":
				left()
				left()
				forward()
			time.sleep(0.1)

		time.sleep(1)



# thread function to continuously check how close our front or rear is to an object
def collisionDetect():
	global direction

	t = threading.currentThread()

	# keep running until our main thread sets "do_run" to false
	while getattr(t, "do_run", True):
		if direction == "forward":
			checkDistanceReading("us_front_distance")
				
		elif direction == "reverse":
			checkDistanceReading("us_rear_distance")

		time.sleep(0.05)


# thread function to handle socket client requests
def sockClientHandler(client, addr):
	global direction
	global autonomousMode

	try:
	        while True:
                	direction = client.recv( 1024 )

                        if not direction:
                        	break
                        else:
                                if direction == "forward":
					autonomousMode = False

                                	forward()
                                elif direction  == "reverse":
					autonomousMode = False

                                        reverse()
                                elif direction == "left":
					autonomousMode = False

                                        left()
                                elif direction == "right":
					autonomousMode = False

                                        right()
				elif direction == "autonomous":
					autonomousMode = True
                                else:
					autonomousMode = False

                                        stop()
	finally:
                client.close()	

# define friendly names for our pins
LEFT_FORWARD = 17
LEFT_REVERSE = 18
RIGHT_FORWARD = 22
RIGHT_REVERSE = 23

# init GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(LEFT_FORWARD, GPIO.OUT)
GPIO.setup(LEFT_REVERSE, GPIO.OUT)
GPIO.setup(RIGHT_FORWARD, GPIO.OUT)
GPIO.setup(RIGHT_REVERSE, GPIO.OUT)

# signal handler to catch Ctrl+c
signal.signal(signal.SIGINT, signal_handler)

# start collision detection thread
collisionDetectThread = threading.Thread(target=collisionDetect)
collisionDetectThread.start()

# start autonomous thread
autonomousThread = threading.Thread(target=autonomous)
autonomousThread.start()

# set up our socket
sockfile = "./bot_direction.sock"

# clean up dangling socket file (if present)
if os.path.exists( sockfile ):
	os.remove( sockfile )

# start our direction listener
server = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM )
server.bind(sockfile)
server.listen(2) # max of 2 queued connections

try:
	while True:
		conn, addr = server.accept()
		
		# we hand off all client connections to a new thread to avoid blocking
		clientThread = threading.Thread(target=sockClientHandler, args=(conn, addr))
		clientThread.start()

# on any error, we simply gracefully exit
except Exception as e:
	cleanup()
	sys.exit(1)

cleanup()
