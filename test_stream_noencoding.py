import io
import logging
import socketserver
from http import server
from threading import Condition
from libcamera import controls
from picamera2 import Picamera2
from picamera2.outputs import FileOutput
import time
import board
import adafruit_bno055
import numpy as np
import cv2

imu_data = "0,0,0,0"

PAGE = f'''\
<html>
<head>
<title>Picamera3 Streaming Demo</title>
</head>
<body>
<h1>Picamera3 Streaming Demo</h1>
<img src="stream.bmp" width="640" height="480" />
</body>
</html>
'''
t0 = str(time.time())

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

class StreamingHandler(server.BaseHTTPRequestHandler):

    def do_GET(self):
        global t0
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/imu.html':
            if bno_enabled == True:
                texto0 = str(sensor.quaternion)
            else:
                texto0 = "0,0,0,0"
            t1 = str(time.time())
            texto = t0 + "_" + t1 + "_" + texto0
            content = texto.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path.startswith('/focus.html'):
            try:
                number = int(self.path.split('/')[-1])
                texto = f"LensPosition = {number}"
            except (ValueError, IndexError):
                texto = "Por favor, envie um número inteiro positivo."
            number = float(number)
            picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": number})
            t0 = str(time.time())
            content = texto.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path.startswith('/exposure.html'):
            try:
                number = int(self.path.split('/')[-1])
                texto = f"ExposureTime = {number}"
            except (ValueError, IndexError):
                texto = "Por favor, envie um número inteiro positivo."
            picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": number})
            picam2.set_controls({"ExposureTime": number})
            t0 = str(time.time())
            content = texto.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.bmp':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'image/bmp')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    # Converte o frame de JPEG para um array numpy
                    np_frame = np.frombuffer(frame, dtype=np.uint8)
                    # Decodifica o frame para imagem em escala de cinza
                    gray_frame = cv2.imdecode(np_frame, cv2.IMREAD_GRAYSCALE)
                    # Codifica a imagem em formato BMP
                    _, bmp_frame = cv2.imencode('.bmp', gray_frame)
                    self.wfile.write(bmp_frame.tobytes())
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

i2c = board.I2C()
bno_enabled = False

try:
    sensor = adafruit_bno055.BNO055_I2C(i2c, 0x29)
    bno_enabled = True
except:
    print("Erro ao iniciar o BNO055")
    bno_enabled = False

picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.controls.FrameRate = 60
time.sleep(2)
output = StreamingOutput()
picam2.start_recording(JpegEncoder(), FileOutput(output))

try:
    address = ('', 7123)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()
finally:
    picam2.stop_recording()
