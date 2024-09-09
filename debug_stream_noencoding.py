import json
import numpy as np
import socket
from picamera2 import Picamera2
import time

def transmit(sock, data):
    serial_data = data.tobytes()
    metadata = {'type': data.dtype.name,
                'shape': data.shape,
                'length': len(serial_data)}
    sock.sendall(json.dumps(metadata).encode() + b'\n')
    sock.sendall(serial_data)

def capture_image():
    picam2 = Picamera2()
    picam2.configure(picam2.create_still_configuration())
    picam2.start()
    image = picam2.capture_array()
    picam2.stop()
    return image

with socket.socket() as s:
    s.connect(('rasp5encoder00.local', 5000))  # Substitua pelo nome de host ou IP apropriado

    while True:
        # Captura uma imagem em preto e branco
        image = capture_image()

        # Se a imagem não estiver em preto e branco, converta para preto e branco
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = np.dot(image[...,:3], [0.299, 0.587, 0.114])
            image = image.astype(np.uint8)

        # Transmite a imagem
        transmit(s, image)

        # Aguarda antes de capturar a próxima imagem (ajuste o intervalo conforme necessário)
        time.sleep(1)  # Aguarda 1 segundo
