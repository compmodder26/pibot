var express = require('express');
var app = express();
var server = require('http').createServer(app);
var io = require('socket.io').listen(server);
var net = require('net');
var fs = require('fs');
  
server.listen(5555);
app.use(express.static('public'));             

var direction = 'stop';
var socketPath = '../bot_direction.sock';

io.sockets.on('connection', function (socket) {
	var client = net.createConnection(socketPath);

	socket.on('drive', function (data) {
		direction = data.value;

		if (direction == "forward" || direction == "reverse" || direction == "left" || direction == "right" || direction == "stop" || direction == "autonomous" || direction.match(/calibrate_steering:\d+/)) {
			client.write(direction);
		}
		else {
			client.write("stop");
		}
	});

	socket.on('getCalibrationReading', function(data) {
		fs.readFile('/home/pi/pibot/steer_calibration.txt', 'utf8', function (err,data) {
			if (err) {
			    return console.log(err);
			}
			

			data = data.replace(/^\s+|\s+$/g, '');

			console.log(data);

			socket.emit('calibrationRead', data);
		});		
	});
});
