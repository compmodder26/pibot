#!/usr/bin/python

#############################################################
#
# bot_control_backend.py
#
# Sets up a backend listener for clients to connect to,
# in order to send commands to drive the bot
#
# Employs optional ultrasonic sensor usage for collision
# avoidance.
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

# global distance storage associative array
distanceMeasures = { "front_right_distance" : 100, "front_center_distance" : 100, "front_left_distance" : 100 }

# flag indicating if we are using sensors for collision avoidance (set False to disable)
doCollisionDetect = True

# global distance thread variable declaration
distThread = None

def forward():
	global direction
	global distanceMeasures
	global doCollisionDetect
	direction = "forward"

	# don't attempt to move forward if we're too close to an object
	if not doCollisionDetect or (distanceMeasures["front_right_distance"] > 20 and distanceMeasures["front_center_distance"] > 20 and  distanceMeasures["front_left_distance"] > 20):
		GPIO.output(LEFT_FORWARD, 1)
		GPIO.output(LEFT_REVERSE, 0)
		GPIO.output(RIGHT_FORWARD, 1)
		GPIO.output(RIGHT_REVERSE, 0)
	else:
		direction = "stopped"

def reverse():
	global direction
	direction = "reverse"

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

	time.sleep(0.1)

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

	time.sleep(0.1)

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
	global distThread
	global autonomousThread
	global autonomousMode
	global server
	global sockfile
	global doCollisionDetect

	autonomousThread.do_run = False

	if doCollisionDetect:
        	distThread.do_run = False
	
	autonomousMode = False

	server.close()
	os.remove(sockfile)

	stop()

	GPIO.cleanup()

# signal handling thread to gracefully shutdown on Crtl+c
def signal_handler(signal, frame):
	cleanup()
	sys.exit(0)


# thread function to make bot run in autonomous mode
# basically tells the bot to move forward until collision detection thread says it's about to hit something
# then it makes the bot move left and then attempt to go forward again
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
				forward()
			time.sleep(0.01)

		time.sleep(0.5)



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


def getDistance(TRIG, ECHO, desiredDirection, key, threshold):
	global distanceMeasures
	global direction

	errCount = 0

	try:
	        GPIO.output(TRIG, True)
                time.sleep(0.00001)
               	GPIO.output(TRIG, False)

	        while GPIO.input(ECHO)==0:
        	        pulse_start = time.time()
	
        	while GPIO.input(ECHO)==1:
                        pulse_end = time.time()

	        pulse_duration = pulse_end - pulse_start

        	distance = round(pulse_duration * 17150, 2)

		distanceMeasures[key] = distance

		print key,": ",distance

		if direction == desiredDirection:
			if distance <= threshold:
				stop();
		
	except Exception as e:
		errCount += 1

def measureThread():
	global FRONT_RIGHT_TRIG
	global FRONT_RIGHT_ECHO 
	global FRONT_CENTER_TRIG
	global FRONT_CENTER_ECHO
	global FRONT_LEFT_TRIG
	global FRONT_LEFT_ECHO

	t = threading.currentThread()

        # keep running until our main thread sets "do_run" to false
        while getattr(t, "do_run", True):
		getDistance(FRONT_RIGHT_TRIG, FRONT_RIGHT_ECHO, "forward", "front_right_distance", 20)				
		getDistance(FRONT_CENTER_TRIG, FRONT_CENTER_ECHO, "forward", "front_center_distance", 20)				
		getDistance(FRONT_LEFT_TRIG, FRONT_LEFT_ECHO, "forward", "front_left_distance", 20)				

		time.sleep(0.15)

# signal handler to catch Ctrl+c
signal.signal(signal.SIGINT, signal_handler)

# define friendly names for our pins (change to whatever your setup is)
LEFT_FORWARD = 17
LEFT_REVERSE = 18
RIGHT_FORWARD = 22
RIGHT_REVERSE = 23
FRONT_RIGHT_TRIG = 8
FRONT_RIGHT_ECHO = 11
FRONT_CENTER_TRIG = 25
FRONT_CENTER_ECHO = 9
FRONT_LEFT_TRIG = 12
FRONT_LEFT_ECHO = 6

# init GPIO
GPIO.setmode(GPIO.BCM)

# init motor pins
GPIO.setup(LEFT_FORWARD, GPIO.OUT)
GPIO.setup(LEFT_REVERSE, GPIO.OUT)
GPIO.setup(RIGHT_FORWARD, GPIO.OUT)
GPIO.setup(RIGHT_REVERSE, GPIO.OUT)

if doCollisionDetect:
	# Init ultrasonic sensor pins
	GPIO.setup(FRONT_RIGHT_TRIG,GPIO.OUT)
	GPIO.setup(FRONT_RIGHT_ECHO,GPIO.IN)
	GPIO.setup(FRONT_CENTER_TRIG,GPIO.OUT)
	GPIO.setup(FRONT_CENTER_ECHO,GPIO.IN)
	GPIO.setup(FRONT_LEFT_TRIG,GPIO.OUT)
	GPIO.setup(FRONT_LEFT_ECHO,GPIO.IN)

	# start up our trigger pins
	GPIO.output(FRONT_RIGHT_TRIG, False)
	GPIO.output(FRONT_CENTER_TRIG, False)
	GPIO.output(FRONT_LEFT_TRIG, False)

	# give them time to settle down
	time.sleep(2)

	# start distance detection thread
	distThread = threading.Thread(target=measureThread)
	distThread.start()

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
