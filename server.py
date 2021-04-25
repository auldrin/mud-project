import time, random, socket, select, mysql.connector
from enum import Enum


HOST = socket.gethostbyname(socket.gethostname())
PORT = 1024

HEADER_LENGTH = 10
IDLE_TIMER = 30

db = mysql.connector.connect(host='localhost',user='root',password='admin',database="mydatabase")
cursor = db.cursor()

class REnum(Enum): #Enumerater which stores the order of the rooms database information
    ID = 0
    NAME = 1
    EAST = 2
    WEST = 3
    NORTH = 4
    SOUTH = 5
    UP = 6
    DOWN = 7
    DESCRIPTION = 8
    def get(number):
        return REnum(number).name

class PEnum(Enum): #Enumerater for the player database information
    ID = 0
    NAME = 1
    PASSWORD = 2
    LOCATION = 3
    def get(number):
        return PEnum(number).name

class Player:
    def __init__(self,name,conn):
        self.name = name
        self.db = None
        self.verified = True
        self.timer = 0.0
        self.conn = conn

    def upload(self,cursor):
        cursor.execute('UPDATE players SET location = %s WHERE name = %s',(self.location,self.name))

    def download(self,cursor):
        cursor.execute("SELECT * FROM players WHERE name = %s",(self.name,))
        self.db = cursor.fetchone()
        self.name = self.db[PEnum.NAME.value]
        self.location = self.db[PEnum.LOCATION.value]

class Room:
    def __init__(self,db):
        self.db = db
        self.playerList = []

    def broadcast(self,message,exceptPlayer=None,exceptOther=None): #Send a message to all players in the room, optionally exclude up to two players
        for player in self.playerList:
            if player == exceptPlayer or player==exceptOther:
                continue
            else:
                send(player.conn,message)

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
        try:
            sent = sock.send(msg[totalsent:])
        except ConnectionAbortedError:
            print('Cannot send to loose player')
            break
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
            print('Runtime error')
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
    return str(b''.join(chunks),'utf-8')

def verification(msg,player):
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
            send(connection,"Please select a name with only English letters, maximum 30 characters\n")
            verification[2] = 1
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

def parseCommand(msg):
    #TODO: replace this with a tuple iterator for the love of god
    #TODO: Also make it so that, e.g, msg == k wouldn't trigger look
    msg = msg.split()[0]
    if msg in 'look':
        return 'look'
    elif msg in 'chat':
        return 'chat'
    elif msg in 'say':
        return 'say'
    elif msg in 'dig':
        return 'dig'
    elif msg in 'tele':
        return 'tele'
    else:
        return ''

def look(player,room):
    directions = []
    players = []
    for x in range(2,7):
        if room.db[x]:
            directions.append(REnum.get(x))

    message = '\n'.join((room.db[REnum.NAME.value], room.db[REnum.DESCRIPTION.value],))
    for p in room.playerList:
        if p.name == player.name:
            continue
        message += ''.join(('\n',p.name,' is standing here.'))
    message += '\nValid directions: ' + ','.join(directions)
    send(player.conn,message)

def chat(connectionList,player,message):
    while message[0] != ' ':
        message = message[1:]
    message = '[CHAT] '+player.name+': '+message
    for connection in connectionList:
        try:
            send(connection,message)
        except AttributeError: #Will always happen when the server tries to send to itself.
            continue

def enterRoom(player,room,direction=None):
    player.location = room.db[REnum.ID.value]
    room.playerList.append(player)
    look(player,room)
    message = player.name + ' has arrived from '
    if direction:
        message += 'the ' + direction
    else:
        message += 'nowhere.'
    room.broadcast(message,player)

def leaveRoom(player,room,direction=None):
    room.playerList.remove(player)
    message = player.name
    if direction:
        if direction == 'up':
            message += ' has left upwards.'
        elif direction == 'down':
            message += ' has left downwards.'
        else:
            message += ' has left to the ' + direction
    else:
        message += ' has vanished.'
    room.broadcast(message)

def say(player,room,message):
    while message[0] != ' ':
        message = message[1:]
    newMessage = ''.join((player.name,' says \'',message,'\''))
    room.broadcast(newMessage,player)
    send(player.conn,'You say \''+message+'\'')

def dig(room,message,cursor,rooms):
    mList = message.split()
    d = mList[1]
    name = ' '.join(mList[2:])
    desc = 'Default description'
    west, east, south, north, up, down = None, None, None, None, None, None
    if d == 'east':
        west = room.db[REnum.ID.value]
    elif d == 'west':
        east = room.db[REnum.ID.value]
    elif d == 'north':
        south = room.db[REnum.ID.value]
    elif d == 'south':
        north = room.db[REnum.ID.value]
    elif d == 'down':
        up = room.db[REnum.ID.value]
    elif d == 'up':
        down = room.db[REnum.ID.value]
    #Save the room as the newest entry in the room table
    cursor.execute('INSERT INTO rooms (name, east, west, north, south, up, down, description) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
    (name,east,west,north,south,up,down,desc))
    #Now get the ID of the newest room
    cursor.execute('SELECT MAX(id) FROM rooms')
    newID = cursor.fetchone()
    #Use that ID to download the room from the database and add it to the rooms dict
    cursor.execute('SELECT * FROM rooms WHERE id = %s',(newID))
    rooms[newID[0]] = Room(cursor.fetchone())
    #Set the appropriate direction in the previous room to connect to this new room
    cursor.execute('UPDATE rooms SET '+ d +' = %s WHERE id = %s',(newID[0],room.db[REnum.ID.value]))
    db.commit()
    #Download the previous room to make sure our version is up to date
    cursor.execute('SELECT * FROM rooms WHERE id = %s',(room.db[REnum.ID.value],))
    room.db = cursor.fetchone()

def tele(message,player,rooms):
    print(rooms.keys())
    try:
        target = int(message.split()[1])
        target = rooms[target]
    except KeyError:
        send(player.conn,'Room ' + str(target) + ' does not exist')
        print(rooms.keys())
        return
    except IndexError:
        send(player.conn,'Please provide a target room. Correct format: \'tele 1\'')
        return
    leaveRoom(player,rooms[player.location])
    enterRoom(player,target)

connections = {Server():None}
loosePlayers = []
idlePlayers = []
rooms = {}

##### Loads the rooms from the database into a dictionary
cursor.execute('SELECT * FROM rooms')
result = cursor.fetchall()
for roomEntry in result:
    rooms[roomEntry[REnum.ID.value]] = Room(roomEntry)
#####

previousFrame = time.time()
reportTime = 0

while True:
    timeSinceFrame = time.time() - previousFrame
    previousFrame = time.time()
    for conn in connections: #Collect any idle connected players, put them in idlePlayers, don't remove from connections yet because iterator
        if isinstance(conn,Server):
            continue
        try: #Unverified players use entry 3 as their timeout
            timer = connections[conn][3] + timeSinceFrame
            connections[conn][3] = timer
        except TypeError: #Verified players use .timer on the player object
            timer = connections[conn].timer + timeSinceFrame
            connections[conn].timer = timer
        if timer > IDLE_TIMER:
            idlePlayers.append(conn)

    while len(idlePlayers): #Purge the list
        try: #Try to treat them like real players, which will fail if they're unverified.
            idleP = connections[idlePlayers[0]]
            idleP.upload(cursor)
            db.commit()
            print('Idle player',idleP.name,'saved to database')
            leaveRoom(idleP,rooms[idleP.location])
        except AttributeError:
            print('Unverified player disconnected')
        finally:
            send(idlePlayers[0],'You are being disconnected for inactivity, sorry!')
            idlePlayers[0].close()
            connections.pop(idlePlayers[0])
            idlePlayers.pop(0)
            del idleP

    i = 0
    while i < len(loosePlayers): #Check each loose player, put them in idlePlayers if they are idle, remove from loosePlayers
        loosePlayers[i].timer = loosePlayers[i].timer + timeSinceFrame
        if loosePlayers[i].timer > IDLE_TIMER:
            idlePlayers.append(loosePlayers[i])
            loosePlayers.pop(i)
        else:
            i = i + 1

    while len(idlePlayers): #Purge the players who are both loose and idle
        idlePlayers[0].upload(cursor)
        db.commit()
        print('Idle player',idlePlayers[0].name,'saved to database')
        leaveRoom(idlePlayers[0],rooms[idlePlayers[0].location])
        idlePlayers.pop(0)

    incomingS, outgoingS, errorS = select.select(connections.keys(),connections.keys(),connections.keys(),0.05)
    for client in incomingS:
        #If the 'client' is really the server socket, accept the connection and add an entry to connections
        if isinstance(client,Server):
            if client.accept():
                #Authentication list [username, password, password confirmation (if new account),timeoutTimer]
                connections[client.conn] = [0,0,1,0]
                send(client.conn,"Enter username:")
            continue
        ###################################################################
        #If the client is an actual player, receive the data
        try:
            data = receive(client)
        except:
            print('Disconnected player due to exception when receiving data')
            if isinstance(connections[client],Player):
                loosePlayers.append(connections[client])
                print('Added player to loosePlayers list')
            connections.pop(client)
            continue
        ###################################################################
        #If the player is fully logged in, parse and handle their command
        #TODO: Avoid checking the command twice somehow, while still supporting 'e' for 'east' and such.
        if isinstance(connections[client],Player):
            connections[client].timer = 0.0
            command = parseCommand(data)
            if command == 'chat':
                chat(connections,connections[client],data)
            elif command == 'look':
                look(connections[client],rooms[connections[client].location])
            elif command == 'say':
                say(connections[client],rooms[connections[client].location],data)
            elif command == 'dig':
                dig(rooms[connections[client].location],data,cursor,rooms)
            elif command == 'tele':
                tele(data,connections[client],rooms)
            continue
        ###################################################################
        #If the player is unverified, attempt to verify using their input
        connections[client][3] = 0.0
        connections[client] = verification(data,(client,connections[client]))
        if connections[client][1] == 1 and connections[client][2] == 1: #A verified existing player will have a list like ['Auldrin',1,1,0]
            #TODO: Check if player is already in-game, and transfer them to the new connection. Or just put them back in DB and re-check-out.
            connections[client][0] = connections[client][0].capitalize()
            foundPlayer = False
            connectedToExisting = False
            for oldPlayer in connections:
                if isinstance(oldPlayer, Server) or isinstance(connections[oldPlayer],list):
                    continue #Don't want to bother the server, or any unverified players.
                if connections[oldPlayer].name == connections[client][0]:
                    #Set the new connection's player as the old player object
                    connections[client] = connections[oldPlayer]
                    #Set the old player object's connection reference to the new connection
                    connections[oldPlayer].conn = client
                    #Delete the old connection from connections list, but warn them first
                    try:
                        send(oldPlayer,'You are being usurped by someone who knows your username and password. Sorry if it\'s not you')
                    except:
                        pass
                    connections.pop(oldPlayer)
                    foundPlayer = True
                    connectedToExisting = True
                    print('Player is already logged in, connecting to existing body')
                    rooms[connections[client].db[PEnum.LOCATION.value]].broadcast(connections[client].name + '\'s body has been taken over by a new soul.',connections[client])
                    send(connections[client].conn,'You have entered your body, forcing out the soul inhabiting it.')
                    break
            if not foundPlayer: #If the player wasn't in the main list, check if they're in the loose player list
                for looseP in loosePlayers:
                    if looseP.name == connections[client][0]:
                        connections[client] = looseP #Replace the new connection's verification tuple with the old body
                        looseP.conn = client #Tell the old body about its new connection
                        loosePlayers.remove(looseP) #Remove the body from loose players
                        connectedToExisting = True
                        print('Player being connected to loose body')
                        print(connections[client])
                        rooms[connections[client].db[PEnum.LOCATION.value]].broadcast(connections[client].name + '\'s soul has returned to their body.',connections[client])
                        send(connections[client].conn,'You have re-entered your body, right where you left it.')
                        break
            if connectedToExisting:
                break
            connections[client] = Player(connections[client][0],client) #Make a new player with the verified name
            connections[client].download(cursor)
            print('Verified existing player '+connections[client].name)
            enterRoom(connections[client],rooms[connections[client].location])
        elif connections[client][0] != 0 and connections[client][1] != 0 and connections[client][2] != 0: #A new player looks like ['Auldrin',admin,admin,0]
            cursor.execute("INSERT INTO players (name, password, location) VALUES (%s, %s, %s)",(connections[client][0].capitalize(),connections[client][1],1))
            db.commit()
            connections[client] = Player(connections[client][0],client)
            connections[client].download(cursor)
            print('Verified new player ',connections[client].name)
            enterRoom(connections[client],rooms[connections[client].location])




