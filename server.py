import time
import random
import socket
import select
import mysql.connector
import room
import rsa
import hashlib

import privatekey
import utility as u
import command as c
import settings

HOST = socket.gethostbyname(socket.gethostname())
PORT = settings.PORT

HEADER_LENGTH = settings.HEADER_LENGTH
IDLE_TIMER = settings.IDLE_TIMER
PRIVATE_KEY = rsa.PrivateKey(privatekey.PRIVATE_KEY[0],privatekey.PRIVATE_KEY[1],privatekey.PRIVATE_KEY[2],privatekey.PRIVATE_KEY[3],privatekey.PRIVATE_KEY[4])

db = mysql.connector.connect(host='localhost',user='root',password='admin',database="mydatabase")
cursor = db.cursor()

class Weapon:
    def __init__(self,name):
        self.name = name
        #TODO: get weapon from database using its name
        self.damage = {6:2}
        self.damageType = 'slashing'

class BaseActor:
    def __init__(self,name):
        self.name = name
        self.health = 10
        self.maxHealth = 10
        self.nonLethalDamage = 0
        self.location = None
        self.target = None
        self.opponents = []
        #TODO: Consider whether to phase out inCombat. It is faster than checking opponents size.
        self.inCombat = False
        self.baseAttackBonus = 0
        self.armourClass = 10

        self.damage = {3:1}
        self.damageType = 'subdual'

class Mob(BaseActor):
    def __init__(self,name,ID,cursor):
        super().__init__(name)
        cursor.execute('SELECT * FROM mobs WHERE ID = %s',(ID))
        self.db = cursor.fetchone()

class Player(BaseActor):
    def __init__(self,name,conn):
        super().__init__(name)
        self.db = None
        self.timer = 0.0
        self.conn = conn

    def upload(self,cursor):
        cursor.execute('UPDATE players SET location = %s WHERE name = %s',(self.location,self.name))

    def download(self,cursor):
        cursor.execute("SELECT * FROM players WHERE name = %s",(self.name,))
        self.db = cursor.fetchone()
        self.name = self.db[u.PEnum.NAME.value]
        self.location = self.db[u.PEnum.LOCATION.value]

    def attack(self,rooms):
        try:
            attackCount = max(1,self.baseAttackBonus//5)
        except ZeroDivisionError:
            attackCount = 1

        for a in range(attackCount):
            print('attempted attack')
            roll = random.randint(1,20)
            rollTotal = self.baseAttackBonus + roll
            if rollTotal > self.target.armourClass:
                for key in self.damage.keys():
                    for die in range(self.damage[key]):
                        damageTotal = random.randint(1,key)
                        print('Rolled ',self.damage[key],'d',key)
                u.send(self.conn,'['+str(rollTotal)+','+str(damageTotal)+'] You hit ' + self.target.name + ' with your attack!')
                u.send(self.target.conn,'['+str(rollTotal)+','+str(damageTotal)+'] '+self.name + ' lands a blow against you!')
                rooms[self.location].broadcast(self.name+' lands a blow against '+self.target.name+'!',self,self.target)
                self.target.takeDamage(damageTotal,self.damageType,self,rooms)
            else:
                u.send(self.conn,'[' + str(rollTotal) + '] You miss ' + self.target.name + ' with your attack!')
                u.send(self.target.conn,'['+str(rollTotal)+']'+self.name + ' misses you with their attack!')
                rooms[self.location].broadcast(self.name+' misses '+self.target.name+' with an attack!',self,self.target)
            #Players with multiple attacks could easily end up killing their enemy in the middle of a flurry
            if not self.target:
                break

    def takeDamage(self,damage,dType,attacker,rooms):
        if dType == 'subdual':
            self.nonLethalDamage += damage
        else:
            self.health -= damage

        if self.health < 0 or self.nonLethalDamage > self.health:
            #die
            rooms[self.location].broadcast(self.name+' falls to the ground, dead.',self)
            u.send(self.conn,'You are dead!')
            self.inCombat = False
            while self.opponents:
                self.opponents[0].opponents.remove(self)
                if self.opponents[0].target == self:
                    if self.opponents[0].opponents:
                        self.opponents[0].target = self.opponents[0].opponents[0]
                    else:
                        self.opponents[0].inCombat = False
                self.opponents.pop(0)
            self.target = None
            u.leaveRoom(self,rooms[self.location],dead=True)
            u.enterRoom(self,rooms[1],None,True)
            self.health = self.maxHealth

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
    msg = b''.join(chunks)
    msg = rsa.decrypt(msg,PRIVATE_KEY)
    return str(msg,'utf-8')

def verification(msg,player):
    verification = player[1]
    connection = player[0]
    #If player[1] is a list, this will work and progress through authentication. If it is not, it will except
    if verification[0] == 0: #Player is selecting username
        verification[0] = msg
        cursor.execute("SELECT name FROM players WHERE name = %s;", (verification[0],))
        result = cursor.fetchone()
        if result:
            u.send(connection,"Please enter your password:")
        elif msg.isalpha() and len(msg) <= 30:
            u.send(connection,"Please select a password:")
            verification[2] = 0
        else:
            u.send(connection,"Please select a name with only English letters, maximum 30 characters\n")
            verification[2] = 1
            verification[0] = 0
    elif verification[1] == 0: #Player is either setting or entering password, depending on verification[2]
        m = hashlib.sha256()
        m.update(bytes(msg,'utf-8'))
        msg = m.hexdigest()
        if verification[2] == 1:
            cursor.execute("SELECT password FROM players WHERE name = %s;", (verification[0],))
            playerPassword = cursor.fetchone()
            if playerPassword[0] == msg:
                u.send(connection,"Welcome to the server.")
                verification[1] = 1
            else:
                u.send(connection,"Password incorrect, re-enter username")
                return[0,0,1,0]
        else:
            verification[1] = msg
            u.send(connection,"Please re-enter to confirm")
    elif verification[2] == 0: #Player is confirming the previously entered password
        m = hashlib.sha256()
        m.update(bytes(msg,'utf-8'))
        msg = m.hexdigest()
        print(msg)
        if msg == verification[1]:
            u.send(connection,"Welcome to the server.")
            verification[2] = 1
        else:
            u.send(connection,"Password mismatch, clearing both. Try again.")
            verification[1] = 0
    return verification

def parseCommand(msg):
    msg = msg.lower()
    if all([char in ['n','e','w','s','u','d'] for char in msg]):
        return 'multimove'
    elif msg in ('north','east','south','west','up','down'):
        return 'move'
    msg = msg.split()[0]
    for command in commandList:
        if command.startswith(msg):
            return command
    return None

connections = {Server():None}
loosePlayers = []
idlePlayers = []
rooms = {}
commandList = ('look','kill','chat','say','flee','me','dig','tele','link','editdesc','editname','quit')

##### Loads the rooms from the database into a dictionary
cursor.execute('SELECT * FROM rooms')
result = cursor.fetchall()
for roomEntry in result:
    rooms[roomEntry[u.REnum['ID']]] = room.Room(roomEntry)
print(len(rooms),'rooms loaded successfully.')
#####

previousFrame = time.time()
reportTime = 0
previousCombatRound = previousFrame

while True:
    #Maybe this is dumb, but timeNow avoids having to call time.time three additional times times? Requires testing.
    timeNow = time.time()
    timeSinceFrame = timeNow - previousFrame
    previousFrame = timeNow
    timeSinceCombatRound = timeNow - previousCombatRound
    #TODO: Decide how often mobs act. Could be just each combat round, or they could be on a 3 second timer or something.
    if timeSinceCombatRound >= settings.COMBAT_TIME:
        previousCombatRound = time.time()
        #Do a combat round
        for conn in connections:
            if not isinstance(connections[conn],Player):
                continue
            player = connections[conn]
            if player.inCombat:
                player.attack(rooms)
                pass
            else:
                continue
        #for mob in mobs:
            #Do mob combat stuff
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

    while idlePlayers: #Purge the list
        try: #Try to treat them like real players, which will fail if they're unverified.
            idleP = connections[idlePlayers[0]]
            idleP.upload(cursor)
            db.commit()
            print('Idle player',idleP.name,'saved to database')
            u.leaveRoom(idleP,rooms[idleP.location])
        except AttributeError:
            print('Unverified player disconnected')
        finally:
            try:
                u.send(idlePlayers[0],'You are being disconnected for inactivity, sorry!')
            except OSError:
                pass
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

    while idlePlayers: #Purge the players who are both loose and idle
        idlePlayers[0].upload(cursor)
        db.commit()
        print('Idle player',idlePlayers[0].name,'saved to database')
        u.leaveRoom(idlePlayers[0],rooms[idlePlayers[0].location])
        idlePlayers.pop(0)

    incomingS, outgoingS, errorS = select.select(connections.keys(),connections.keys(),connections.keys(),0.05)
    for client in incomingS:
        #If the 'client' is really the server socket, accept the connection and add an entry to connections
        if isinstance(client,Server):
            if client.accept():
                #Authentication list [username, password, password confirmation (if new account),timeoutTimer]
                connections[client.conn] = [0,0,1,0]
                u.send(client.conn,"Enter username:")
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
            if command == 'move':
                c.move(connections[client],data,rooms)
            elif command == 'multimove':
                c.move(connections[client],data,rooms,True)
            elif command == 'kill':
                c.kill(connections[client],data,rooms)
            elif command == 'chat':
                c.chat(connections[client],data,connections)
            elif command == 'look':
                c.look(connections[client],data,rooms)
            elif command == 'say':
                c.say(connections[client],rooms[connections[client].location],data)
            elif command == 'flee':
                c.flee(connections[client],data,rooms)
            elif command == 'me':
                c.me(connections[client],data,rooms)
            elif command == 'dig':
                c.dig(rooms[connections[client].location],data,rooms,cursor)
                db.commit()
            elif command == 'tele':
                c.tele(connections[client],data,rooms)
            elif command == 'link':
                c.link(connections[client],data,rooms, cursor)
                db.commit()
            elif command == 'editdesc':
                c.editDesc(connections[client],data,rooms[connections[client].location],cursor)
                db.commit()
            elif command == 'editname':
                c.editName(connections[client],data,rooms[connections[client].location],cursor)
                db.commit()
            elif command == 'quit':
                c.quit(connections[client],data,rooms[connections[client].location],cursor)
                db.commit()
                pass
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
                    u.send(connections[client].conn,'You have entered your body, forcing out the soul inhabiting it.')
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
                        rooms[connections[client].location].broadcast(connections[client].name + '\'s soul has returned to their body.',connections[client])
                        u.send(connections[client].conn,'You have re-entered your body, right where you left it.')
                        break
            if connectedToExisting:
                break
            connections[client] = Player(connections[client][0],client) #Make a new player with the verified name
            connections[client].download(cursor)
            print('Verified existing player '+connections[client].name)
            try:
                u.enterRoom(connections[client],rooms[connections[client].location])
            except KeyError:
                #indicates the room the player logged out in no longer exists
                u.enterRoom(connections[client],rooms[1])
            c.look(connections[client],'',rooms)
        elif connections[client][0] != 0 and connections[client][1] != 0 and connections[client][2] != 0: #A new player looks like ['Auldrin',admin,admin,0]
            cursor.execute("INSERT INTO players (name, password, location) VALUES (%s, %s, %s)",(connections[client][0].capitalize(),connections[client][1],1))
            db.commit()
            connections[client] = Player(connections[client][0],client)
            connections[client].download(cursor)
            print('Verified new player ',connections[client].name)
            u.enterRoom(connections[client],rooms[connections[client].location])
