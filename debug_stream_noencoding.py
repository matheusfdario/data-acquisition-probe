import io
import numpy as np
import picamera
import socket
import pickle

def capture_image():
    with picamera.PiCamera() as camera:
        # Cria um buffer para a imagem
        stream = io.BytesIO()
        # Captura a imagem em preto e branco
        camera.capture(stream, format='jpeg', grayscale=True)
        # Converte o buffer em um array numpy
        stream.seek(0)
        image = np.frombuffer(stream.read(), dtype=np.uint8)
        # Reshape de acordo com a resolução da câmera (exemplo: 640x480)
        return image.reshape((480, 640))

# Captura a imagem
def send_image(image):
    # Configura o socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('rasp5encoder00.local', 12345))  # Substitua 'IP_DO_PI5' pelo IP do Pi5

    # Serializa o array numpy
    data = pickle.dumps(image)
    s.sendall(data)
    s.close()

while True:
    image = capture_image()
    send_image(image)
