from picamera2 import Picamera2
import numpy as np
import io


def capture_image():
    picam2 = Picamera2()
    picam2.start_preview()

    # Captura a imagem em preto e branco (gray)
    picam2.configure(picam2.create_still_configuration())
    image = picam2.capture_array()

    # Converte a imagem para escala de cinza, se necessário
    if len(image.shape) == 3 and image.shape[2] == 3:
        image = np.dot(image[..., :3], [0.299, 0.587, 0.114])

    picam2.close()
    return image




import socket
import pickle

def send_image(image):
    # Configura o socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('IP_DO_PI5', 12345))  # Substitua 'IP_DO_PI5' pelo IP do Pi5

    # Serializa o array numpy
    data = pickle.dumps(image)
    s.sendall(data)
    s.close()


while True:
    # Captura a imagem
    image = capture_image()
    send_image(image)
