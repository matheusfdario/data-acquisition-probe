import io
import logging
import socketserver
from http import server
from threading import Condition, Thread
from libcamera import controls
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
import time
import board
import adafruit_bno055

# Variáveis globais
imu_data = "0,0,0,0"
bno_enabled = False

PAGE = f'''\
<html>
<head>
<title>picamera3 MJPEG streaming demo</title>
</head>
<body>
<h1>Picamera3 MJPEG Streaming Demo</h1>
<img src="stream.mjpg" width="640" height="480" />
<h2>IMU: {imu_data}</h2>
</body>
</html>
'''

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
        elif self.path.startswith('/focus.html'):
            # Executa o ajuste de foco em uma thread separada
            Thread(target=self.handle_focus_request).start()
        elif self.path.startswith('/exposure.html'):
            # Executa o ajuste de exposição em uma thread separada
            Thread(target=self.handle_exposure_request).start()
        elif self.path == '/stream.mjpg':
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
        else:
            self.send_error(404)
            self.end_headers()

    def handle_focus_request(self):
        try:
            number = int(self.path.split('/')[-1])
            picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": number})
            texto = f"LensPosition = {number}"
        except (ValueError, IndexError):
            texto = "Por favor, envie um número inteiro positivo."
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(texto))
        self.end_headers()
        self.wfile.write(texto.encode('utf-8'))

    def handle_exposure_request(self):
        try:
            number = int(self.path.split('/')[-1])
            picam2.set_controls({"ExposureTime": number})
            texto = f"ExposureTime = {number}"
        except (ValueError, IndexError):
            texto = "Por favor, envie um número inteiro positivo."
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(texto))
        self.end_headers()
        self.wfile.write(texto.encode('utf-8'))

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

# Inicialização do sensor IMU
i2c = board.I2C()
try:
    sensor = adafruit_bno055.BNO055_I2C(i2c, 0x29)
    bno_enabled = True
except:
    print("Erro ao iniciar o BNO055")
    bno_enabled = False

# Inicialização da câmera
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.controls.FrameRate = 60  # Definindo a taxa de quadros
time.sleep(2)
output = StreamingOutput()
picam2.start_recording(JpegEncoder(), FileOutput(output))

# Inicialização do servidor
try:
    address = ('', 7123)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()
finally:
    picam2.stop_recording()
