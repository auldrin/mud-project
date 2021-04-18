import time, random, socket, select


HOST = socket.gethostbyname(socket.gethostname())
PORT = 1024

CLIENT_MESSAGE_MAX = 50
SERVER_MESSAGE_MAX = 200

class Player:
    def __init__(self, conn):
        self.sock = conn
        self.initialized = False
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
    msg = bytes(pad(msg),'utf-8')
    totalsent = 0
    while totalsent < SERVER_MESSAGE_MAX:
        sent = sock.send(msg[totalsent:])
        if sent == 0:
            raise RuntimeError('socket connection broken')
        totalsent = totalsent + sent

def receive(sock):
    chunks = []
    bytes_recd = 0
    while bytes_recd < CLIENT_MESSAGE_MAX:
        chunk = sock.recv(min(CLIENT_MESSAGE_MAX - bytes_recd, 2048))
        if chunk == b'':
            raise RuntimeError('Socket closed during reading')
        chunks.append(chunk)
        bytes_recd = bytes_recd + len(chunk)
    return b''.join(chunks)

def pad(msg):
    if len(msg) < SERVER_MESSAGE_MAX:
        return msg + ('`' * (SERVER_MESSAGE_MAX - len(msg)))

def handleRequest(msg):
    msg = str(msg,'utf-8')
    msg = msg.replace('`','')
    msg = msg.split()
    #TODO: replace this if with an actual input handler
    if msg[0].lower() == 'chat':
        msg = msg[4:]
        msg = 'Chat:' + msg
        print('Player chatting: ',msg)
        for client in clients:
            if isinstance(client,Server):
                continue
            send(client,msg)



lastTime = time.time()
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

