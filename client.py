import socket

HEADER = 64
PORT = 5050
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"
SERVER = "192.168.0.112"  # Use the same IP as in your server.py
ADDR = (SERVER, PORT)

# Set up and connect
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDR)  # CONNECT TO SERVER

def send(msg):
    message = msg.encode(FORMAT)
    msg_length = len(message)
    send_length = str(msg_length).encode(FORMAT)
    send_length += b' ' * (HEADER - len(send_length))  # Padding to HEADER size
    client.send(send_length)
    client.send(message)

# Send a test message
send("Hello, Server!")

# Disconnect after sending
send(DISCONNECT_MESSAGE)
client.close()
