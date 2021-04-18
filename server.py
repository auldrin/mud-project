import time, random, socket, select


HOST = socket.gethostbyname(socket.gethostname())
PORT = 1024

HEADER_LENGTH = 10

class Player:
    def __init__(self):
        self.initialized = 0
        self.name = ''


class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((HOST,PORT))
        self.sock.listen(5)
        self.sock.setblocking(False)
        self.conn = None
        self.address = None

    def fileno(self):
        return self.sock.fileno()

    def connect(self, host, port):
        self.sock.connect((host,port))

    def accept(self):
        self.conn, self.address = self.sock.accept()
        if self.conn:
            print('Accepted client, address: ',self.address)
            return True
        else:
            return False

def send(sock,msg):
    #convert to bytes
    msg = bytes(msg,'utf-8')

    #assemble fixed length header
    length = bytes(str(len(msg)),'utf-8')
    pad = HEADER_LENGTH-len(length)
    if pad >= 1:
        length = length + b' '*pad

    #attach header
    msg = length+msg

    totalsent = 0
    while totalsent < len(msg):
        sent = sock.send(msg[totalsent:])
        if sent == 0:
            raise RuntimeError('socket connection broken')
        totalsent = totalsent + sent

def receive(sock):
    chunks = []
    bytes_recd = 0
    #receive header
    while bytes_recd < HEADER_LENGTH:
        chunk = sock.recv(min(HEADER_LENGTH - bytes_recd, HEADER_LENGTH))
        if chunk == b'':
            raise RuntimeError('Socket closed during reading')
        chunks.append(chunk)
        bytes_recd = bytes_recd + len(chunk)
    #reassemble and decode header
    header = b''.join(chunks)
    length = int(str(header,'utf-8'))

    chunks = []
    bytes_recd = 0
    #receive body
    while bytes_recd < length:
        chunk = sock.recv(min(length - bytes_recd, length))
        if chunk == b'':
            raise RuntimeError('Socket closed during reading')
        chunks.append(chunk)
        bytes_recd = bytes_recd + len(chunk)
    return b''.join(chunks)

def handleRequest(msg):
    msg = str(msg,'utf-8')
    msg = msg.split()
    #TODO: replace this if with an actual input handler
    if msg[0].lower() == 'chat':
        msg = ' '.join(msg)
        msg = msg[4:]
        msg = 'Chat: ' + msg
        print(msg)
        for client in clients:
            if isinstance(client,Server):
                continue
            send(client,msg)

lastTime = time.time()
players = {}
clients = [Server()]

while True:
    if time.time() - lastTime < 0.1:
        continue
    else:
        lastTime = time.time()

    incomingS, outgoingS, errorS = select.select(clients,clients,clients,0.05)
    for client in incomingS:
        if isinstance(client,Server):
            if client.accept():
                clients.append(client.conn)
        else:
            try:
                handleRequest(receive(client))
            except:
                print('Disconnected player')
                clients.remove(client)

