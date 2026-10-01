import json
import asyncio
import sys

# Using standard library or simple websockets if available
# We can do raw websocket with standard library or simple socket handshake
import socket
import base64
import os
import hashlib

def ws_handshake():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 4455))
    key = base64.b64encode(os.urandom(16)).decode('utf-8')
    req = (
        f"GET / HTTP/1.1\r\n"
        f"Host: 127.0.0.1:4455\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    s.sendall(req.encode('utf-8'))
    resp = s.recv(4096)
    return s

def send_frame(s, msg):
    payload = msg.encode('utf-8')
    length = len(payload)
    mask = os.urandom(4)
    frame = bytearray([0x81]) # FIN + text
    if length <= 125:
        frame.append(0x80 | length)
    elif length <= 65535:
        frame.append(0x80 | 126)
        frame.extend(length.to_bytes(2, 'big'))
    else:
        frame.append(0x80 | 127)
        frame.extend(length.to_bytes(8, 'big'))
    frame.extend(mask)
    masked_payload = bytearray(payload[i] ^ mask[i % 4] for i in range(length))
    frame.extend(masked_payload)
    s.sendall(frame)

def recv_frame(s):
    header = s.recv(2)
    if not header:
        return None
    b1, b2 = header[0], header[1]
    length = b2 & 0x7F
    if length == 126:
        length = int.from_bytes(s.recv(2), 'big')
    elif length == 127:
        length = int.from_bytes(s.recv(8), 'big')
    
    # Read payload
    payload = bytearray()
    while len(payload) < length:
        chunk = s.recv(length - len(payload))
        if not chunk:
            break
        payload.extend(chunk)
    return payload.decode('utf-8', errors='ignore')

def call_obs(request_type, request_data=None):
    s = ws_handshake()
    hello = json.loads(recv_frame(s))
    
    # Identify
    send_frame(s, json.dumps({"op": 1, "d": {"rpcVersion": 1}}))
    identified = json.loads(recv_frame(s))
    
    # Send Request
    d = {"requestType": request_type, "requestId": "req1"}
    if request_data:
        d["requestData"] = request_data
    send_frame(s, json.dumps({"op": 6, "d": d}))
    
    resp = json.loads(recv_frame(s))
    s.close()
    return resp

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else "GetHotkeyList"
    print(json.dumps(call_obs(cmd), indent=2))
