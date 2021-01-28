#!/usr/bin/python3
#
# Web streaming example
# Source code from the official PiCamera package
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

import io
import sys
import picamera
import logging
import socketserver
from threading import Condition
from http import server
import RPi.GPIO as gpio

PAGE="""\
<html>
<head>
<title>Camara Frankonstin</title>
</head>
<body>
<center><h1>Raspberry Pi - Surveillance Camera</h1></center>
<center><img src="stream.mjpg" width="640" height="480"></center>

<center>
<form action="" method="post">
    <button name="ir_filter" value="change">IR Cut %s</button>
</form>
</center>

<center>
<form action="" method="post">
    <button name="stop" value="stop">STOP</button>
</form>
</center>


</body>
</html>
"""

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)


class StreamingHandler(server.BaseHTTPRequestHandler):
    ""
    def do_POST(self):
        ""
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        response = io.BytesIO()
        response.write(body)
        button = str(response.getvalue().decode('UTF-8'))
        logging.warning(button)
        
        if "ir_filter" in button:
            if gpio.input(15) == 1:
                self.status = 'OFF'
                gpio.output(15, 0)
            else:
                self.status = 'ON'
                gpio.output(15, 1)
        
            self.do_GET()
        
        if "stop" in button:
            logging.warning('lets stop')
            gpio.cleanup()
            server.socket.close()
            server.shutdown()
            camera.stop_recording()
            camera.close()
            sys.exit()
         
          
    def do_GET(self):
        ""
        try:
            s = self.status
        except AttributeError:
            self.status = 'OFF'

        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            MYPAGE = PAGE % self.status
            content = MYPAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.stream()
        else:
            self.send_error(404)
            self.end_headers()
            
    def stream(self):
        self.send_response(200)
        self.send_header('Age', 0)
        self.send_header('Cache-Control', 'no-cache, private')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.end_headers()
        try:
            while True:
                with output.condition:
                    output.condition.wait()
                    frame = output.frame
                self.wfile.write(b'--FRAME\r\n')
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', len(frame))
                self.end_headers()
                self.wfile.write(frame)
                self.wfile.write(b'\r\n')
        except Exception as e:
            logging.warning(
                'Removed streaming client %s: %s',
                self.client_address, str(e))


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    
    gpio.setmode(gpio.BOARD)
    gpio.setup(15, gpio.OUT)
    gpio.output(15, 0)

    with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
        output = StreamingOutput()
        #Uncomment the next line to change your Pi's Camera rotation (in degrees)
        #camera.rotation = 90
        camera.start_recording(output, format='mjpeg')
        try:
            address = ('', 8000)
            server = StreamingServer(address, StreamingHandler)
            server.serve_forever()
        finally:
            camera.stop_recording()
            camera.close()
