import json
import numpy as np
import socket

def transmit(sock, data):
    serial_data = data.tobytes()
    metadata = {'type': data.dtype.name,
                'shape': data.shape,
                'length': len(serial_data)}
    sock.sendall(json.dumps(metadata).encode() + b'\n')
    sock.sendall(serial_data)

with socket.socket() as s:
    s.connect(('rasp5encoder00.local', 5000))
    data = np.array([[1,2,3],[4,5,6],[7,8,9]], dtype=np.float32)
    transmit(s, data)
    data = np.array([[[1,2],[3,4]],[[5,6],[7,8]]], dtype=np.int16)
    transmit(s, data)