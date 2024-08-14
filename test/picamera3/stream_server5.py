import io
import logging
import socketserver
from http import server
from threading import Condition
from libcamera import controls
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
import time
import board
import adafruit_bno055

imu_data = "0,0,0,0"  # Variável global para armazenar os dados mais recentes do IMU

PAGE_TEMPLATE = '''\
<html>
<head>
<title>Picamera3 MJPEG Streaming Demo</title>
</head>
<body>
<h1>Picamera3 MJPEG Streaming Demo</h1>
<img src="stream.mjpg" width="640" height="480" />
<h2>IMU: <span id="imu-data">{imu_data}</span></h2>
<script>
    // Estabelece conexão com o servidor para receber eventos SSE
    const eventSource = new EventSource('/imu_stream');
    eventSource.onmessage = function(event) {
        document.getElementById('imu-data').textContent = event.data;
    };
</script>
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
        global imu_data
        
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE_TEMPLATE.format(imu_data=imu_data).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/imu_stream':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            try:
                while True:
                    # Atualiza imu_data com a leitura mais recente do sensor
                    imu_data = str(sensor.quaternion)
                    
                    # Envia os dados do IMU via SSE
                    self.wfile.write(f"data: {imu_data}\n\n".encode('utf-8'))
                    self.wfile.flush()
                    time.sleep(1)  # Ajuste conforme necessário para a taxa de atualização
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
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


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

# Configuração do sensor IMU
i2c = board.I2C()
sensor = adafruit_bno055.BNO055_I2C(i2c, 0x29)

# Configuração da câmera
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
output = StreamingOutput()
picam2.start_recording(JpegEncoder(), FileOutput(output))

try:
    address = ('', 7123)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()
finally:
    picam2.stop_recording()
