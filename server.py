import time, random, socket, select, mysql.connector
from enum import Enum


HOST = socket.gethostbyname(socket.gethostname())
PORT = 1024

HEADER_LENGTH = 10
IDLE_TIMER = 300

db = mysql.connector.connect(host='localhost',user='root',password='admin',database="mydatabase")
cursor = db.cursor()

class Rooms(Enum):
    ID = 0
    NAME = 1
    EAST = 2
    WEST = 3
    NORTH = 4
    SOUTH = 5
    UP = 6
    DOWN = 7
    DESCRIPTION = 8
    def get(self,number):
        return self[number].name

class Players(Enum):
    ID = 0
    NAME = 1
    PASSWORD = 2
    LOCATION = 3

    def get(number):
        return self[number].name

class Player:
    def __init__(self,name):
        self.name = name
        self.db = None
        self.verified = True
        self.timer = 0.0

    def update(self,cursor):
        cursor.execute('UPDATE players SET location = %s',(self.db[Players.LOCATION.value],))

class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((HOST,PORT))
        self.sock.listen(5)
        self.sock.setblocking(False)
        self.conn = None
        self.address = None
        self.timer = 0.0

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
        cursor.execute("SELECT name FROM players WHERE name = %s;", (verification[0],))
        result = cursor.fetchone()
        if result:
            send(connection,"Please enter your password:")
        elif msg.isalpha() and len(msg) <= 30:
            send(connection,"Please select a password:")
            verification[2] = 0
        else:
            send(connection,"Please select a name with only English letters, maximum 30 characters")
            verification[2] = 0
            verification[0] = 0

    elif verification[1] == 0: #Player is either setting or entering password, depending on verification[2]
        if verification[2] == 1:
            cursor.execute("SELECT password FROM players WHERE name = %s;", (verification[0],))
            playerPassword = cursor.fetchone()
            if playerPassword[0] == msg:
                send(connection,"Welcome to the server.")
                verification[1] = 1
            else:
                send(connection,"Password incorrect, re-enter username")
                return[0,0,1,0]
        else:
            verification[1] = msg
            send(connection,"Please re-enter to confirm")

    elif verification[2] == 0: #Player is confirming the previously entered password
        if msg == verification[1]:
            send(connection,"Welcome to the server.")
            verification[2] = 1
        else:
            send(connection,"Password mismatch, clearing both. Try again.")
            verification[1] = 0
    return verification


def handleRequest(msg,player): #TODO handleRequest should return a tuple or something of the command and its targets, so another function can execute it
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
    elif msg[0].lower() == 'look':
        for client in connections:
            if isinstance(client,Server):
                continue
            send(client,look(player.db[Players.LOCATION.value]))


def look(room):
    cursor.execute("SELECT * FROM rooms WHERE id = %s;",(room,))
    result = cursor.fetchone()
    directions = []
    for x in range(2,7):
        if result[x]:
            directions.append(ROOMS.get(x))
    return result[Rooms.NAME.value] +'\n'+ result[Rooms.DESCRIPTION.value] + '\n' + 'Valid directions: ' + ','.join(directions)


connections = {Server():None}
loosePlayers = []
idlePlayers = []

previousFrame = time.time()
reportTime = 0

while True:
    timeSinceFrame = time.time() - previousFrame
    previousFrame = time.time()
    #TODO figure out why nobody is timing out anymore
    for conn in connections: #Collect any idle connected players, put them in idlePlayers, but do not remove them from connections list
        if isinstance(conn,Server):
            continue
        try:
            timer = connections[conn][3] + timeSinceFrame
            connections[conn][3] = timer
        except TypeError:
            timer = connections[conn].timer + timeSinceFrame
            connections[conn].timer = timer
        if timer > IDLE_TIMER:
            idlePlayers.append(conn)
            print('Disconnecting idle player, idle for ',timer,' seconds.')

    while len(idlePlayers): #Purge the list
        try: #Try to treat them like real players, which will fail if they're unverified.
            connections[idlePlayers[0]].update(cursor)
            db.commit()
            print('Player saved to database')
        except AttributeError:
            print('Unverified player, not saved to database')
            pass
        finally:
            connections.pop(idlePlayers[0])
            idlePlayers.pop(0)

    i = 0
    while i < len(loosePlayers): #Collect any idle disconnected players, put them in idlePlayers, remove from loosePlayers
        loosePlayers[i].timer = loosePlayers[i].timer + timeSinceFrame
        if loosePlayers[i].timer > IDLE_TIMER:
            print('Purging loose player, idle for ',connections[conn][3],' seconds')
            idlePlayers.append(loosePlayers[i])
            loosePlayers.pop(i)
        else:
            i = i + 1

    while len(idlePlayers):
        idlePlayers[0].update(cursor)
        db.commit()
        idlePlayers.pop(0)
        print('Idle player saved to database')



    incomingS, outgoingS, errorS = select.select(connections.keys(),connections.keys(),connections.keys(),0.05)
    for client in incomingS:
        if isinstance(client,Server):#If the 'client' is really the server socket,accept the connection and add an entry to connections
            if client.accept():
                #Authentication list is used to store username, password, password confirmation (if new account), and timeout timer
                connections[client.conn] = [0,0,1,0]
                send(client.conn,"Enter username:")
            continue

        else: #If it's an actual player, handle the incoming data
            try:
                data = receive(client)
            except:
                print('Disconnected player due to exception when receiving data')
                if isinstance(connections[client],Player):
                    loosePlayers.append(connections[client])
                    print('Added player to loosePlayers list')
                connections.pop(client)
                continue

            #If the player is fully logged in, handle their request like normal
            if isinstance(connections[client],Player):
                connections[client].timer = 0.0
                #TODO: Split handleRequest into a parser and something which enacts them
                handleRequest(data,(connections[client]))
            else: #Otherwise, call verification to collect the information they've provided
                connections[client][3] = 0.0
                connections[client] = verification(data,(client,connections[client]))
                if connections[client][1] == 1 and connections[client][2] == 1: #A verified existing player will have a list like ['Auldrin',1,1]
                    connections[client] = Player(connections[client][0])
                    cursor.execute("SELECT * FROM players WHERE name = %s;", (connections[client].name,))
                    connections[client].db = cursor.fetchone()
                    print('Verified existing player, replaced verification list with player object')
                    send(client,look(connections[client].db[3]))
                    #TODO: Check if player is already in-game, and transfer them to the new connection. Or just put them back in DB and re-check-out.
                elif connections[client][0] != 0 and connections[client][1] != 0 and connections[client][2] != 0: #A new player looks like ['Auldrin',admin,admin]
                    cursor.execute("INSERT INTO players (name, password, location) VALUES (%s, %s, %s)",(connections[client][0],connections[client][1]))
                    db.commit()
                    connections[client] = Player(connections[client][0])
                    cursor.execute("SELECT * FROM players WHERE name = %s;", (connections[client].name,))
                    connections[client].db = cursor.fetchone()
                    print('Verified new player, replaced verification list with player object')
                    send(client,look(connections[client].db[3]))



