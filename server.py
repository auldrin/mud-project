import time, random, socket, select, mysql.connector


HOST = socket.gethostbyname(socket.gethostname())
PORT = 1024

HEADER_LENGTH = 10

db = mysql.connector.connect(host='localhost',user='root',password='admin',database="mydatabase")
cursor = db.cursor()

class Player:
    def __init__(self,name):
        self.name = name
        self.db = None
        self.verified = True

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

def verification(msg,player):
    msg = str(msg,'utf-8')
    verification = player[1]
    connection = player[0]
    #If player[1] is a list, this will work and progress through authentication. If it is not, it will except
    if verification[0] == 0: #Player is selecting username
        verification[0] = msg
        cursor.execute("SELECT name FROM players WHERE name = \'" + verification[0] + '\'')
        result = cursor.fetchone()
        if result:
            send(connection,"Please enter your password:")
        else:
            send(connection,"Please select a password:")
            verification[2] = 0
    elif verification[1] == 0:
        if verification[2] == 1:
            cursor.execute("SELECT password FROM players WHERE name = \'" + verification[0] + '\'')
            playerPassword = cursor.fetchone()
            if playerPassword[0] == msg:
                send(connection,"Welcome to the server.")
                verification[1] = 1
            else:
                send(connection,"Password incorrect, re-enter username")
                return[0,0,1]
        else:
            verification[1] = msg
            send(connection,"Please re-enter to confirm")
    elif verification[2] == 0:
        if msg == verification[1]:
            send(connection,"Welcome to the server.")
            verification[2] = 1
        else:
            send(connection,"Password mismatch, clearing both. Try again.")
            verification[1] = 0
    return verification


def handleRequest(msg,player):
    msg = str(msg,'utf-8')
    #TODO: replace this if with an actual input handler
    msg = msg.split()
    if msg[0].lower() == 'chat':
        msg = ' '.join(msg)
        msg = msg[4:]
        msg = '[chat]'+ player.name+ ':' + msg
        print(msg)
        for client in connections:
            if isinstance(client,Server):
                continue
            send(client,msg)

lastTime = time.time()
connections = {Server():None}

while True:
    if time.time() - lastTime < 0.1:
        continue
    else:
        lastTime = time.time()

    incomingS, outgoingS, errorS = select.select(connections.keys(),connections.keys(),connections.keys(),0.05)
    for client in incomingS:
        if isinstance(client,Server):#If the 'client' is really the server socket,accept the connection and add an entry to connections
            if client.accept():
                #Authentication tuple will be used to store username, password, and password confirmation (if new account)
                connections[client.conn] = [0,0,1]
                send(client.conn,"Enter username:")

        else: #If it's an actual player, handle the incoming data
            try:
                data = receive(client)
            except:
                print('Disconnected player')
                connections.pop(client)
            #Tries to verify the player, which will fail if connections[client] is a tuple rather than a real player
            if isinstance(connections[client],Player):
                handleRequest(data,(connections[client]))
            else:
                connections[client] = verification(data,(client,connections[client]))
                print(connections[client])
                if connections[client][1] == 1 and connections[client][2] == 1: #A verified existing player will have a list like ['Auldrin',1,1]
                    connections[client] = Player(connections[client][0])
                    cursor.execute("SELECT * FROM players WHERE name = \'" + connections[client].name + '\'')
                    connections[client].db = cursor.fetchone()
                    print('Verified existing player, replaced vTuple with player object')
                elif connections[client][0] != 0 and connections[client][1] != 0 and connections[client][2] != 0: #A new player looks like ['Auldrin',admin,admin]
                    cursor.execute("INSERT INTO players (name, password) VALUES (%s, %s)",(connections[client][0],connections[client][1]))
                    db.commit()
                    connections[client] = Player(connections[client][0])
                    cursor.execute("SELECT * FROM players WHERE name = \'" + connections[client].name + '\'')
                    connections[client].db = cursor.fetchone()
                    print('Verified new player, replaced vTuple with player object')



