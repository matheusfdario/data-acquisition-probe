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
        global imu_data  # Para modificar a variável global imu_data
        
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            # Renderiza a página com os dados IMU mais recentes
            content = PAGE_TEMPLATE.format(imu_data=imu_data).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path.startswith('/focus.html'):
            try:
                # Extrair número da URL, assumindo que ele vem logo após 'focus.html/'
                number = int(self.path.split('/')[-1])
                # Você pode agora usar o número da maneira que quiser
                texto = f"LensPosition = {number}"
            except (ValueError, IndexError):
                # Se não houver número ou se não for um inteiro válido
                texto = "Por favor, envie um número inteiro positivo."
            number = float(number)
            picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": number}) #"LensPosition": number (number -- set the focus position to 1/number, number is any value you set, for example, if you set 2, it means that it will focus on the position of 0.5m.)
            content = texto.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
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
                        
                        # Atualiza imu_data com a leitura mais recente do sensor
                        imu_data = str(sensor.quaternion)
                    
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
