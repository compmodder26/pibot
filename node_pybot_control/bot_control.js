var express = require('express');
var app = express();
var server = require('http').createServer(app);
var io = require('socket.io').listen(server);
var net = require('net');
  
server.listen(5555);
app.use(express.static('public'));             

var direction = 'stop';
var socketPath = '../bot_direction.sock';

io.sockets.on('connection', function (socket) {
	var client = net.createConnection(socketPath);

	socket.on('drive', function (data) {
		direction = data.value;

		switch (direction) {
			case "forward":
			case "reverse":
			case "left":
			case "right":
			case "stop":
			case "autonomous":
				client.write(direction);
				break;
			default:
				client.write("stop");
				break;
		}
	});
});
