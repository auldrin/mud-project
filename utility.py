from enum import Enum
import settings as s
from Crypto.Cipher import AES

REnum = {'ID':0,
        'NAME':1,
        'EAST':2,
        'WEST':3,
        'NORTH':4,
        'SOUTH':5,
        'UP':6,
        'DOWN':7,
        'DESCRIPTION':8}
def REnumGet(number):
    #For when you have a number corresponding to a direction (2 through 7) but need a string for the direction
    return list(REnum.keys())[list(REnum.values()).index(number)]

PEnum = {'ID':0,
        'NAME':1,
        'PASSWORD':2,
        'LOCATION':3,
        'RACE':4,
        'STRENGTH':5,
        'DEXTERITY':6,
        'CONSTITUTION':7,
        'WISDOM':8,
        'INTELLIGENCE':9,
        'CHARISMA':10}

RACEnum = {'NAME':0,
            'STRENGTH':1,
            'DEXTERITY':2,
            'CONSTITUTION':3,
            'WISDOM':4,
            'INTELLIGENCE':5,
            'CHARISMA':6}

def reverseDirection(key):
    #For when you have a number corresponding to a direction, and want a number for the opposite direction
    if key % 2:
        key -= 1
    else:
        key += 1
    return key

def convertStringToRoomEnum(string):
    #When you have a direction string, and need a number for it
    if string == 'east':
        return REnum['EAST']
    elif string == 'west':
        return REnum['WEST']
    elif string == 'south':
        return REnum['SOUTH']
    elif string == 'north':
        return REnum['NORTH']
    elif string == 'up':
        return REnum['UP']
    elif string == 'down':
        return REnum['DOWN']
    else:
        return None

def lengthenDirection(d):
    #When you have a single character direction and want the full length version
    if d == 'e':
        return 'east'
    elif d == 'w':
        return 'west'
    elif d == 's':
        return 'south'
    elif d == 'n':
        return 'north'
    elif d == 'u':
        return 'up'
    elif d == 'd':
        return 'down'

def send(sock,msg,key):
    #convert to bytes
    msg = bytes(msg,'utf-8')

    #Prepare message for encryption
    length = len(msg)
    requiredPad = 16-(length%16)
    msg += b' '*requiredPad

    #Split message into 16 byte chunks
    msg = [msg[i:i+16] for i in range(0,len(msg),16)]

    #Encrypt chunks, and assemble them into a single message
    finalMessage = b''
    for x in msg:
        cipher = AES.new(key,AES.MODE_EAX)
        nonce = cipher.nonce
        ciphertext,tag = cipher.encrypt_and_digest(x)
        finalMessage += nonce+ciphertext+tag

    #assemble fixed length header stating encrypted length
    finalLength = bytes(str(len(finalMessage)),'utf-8')
    pad = s.HEADER_LENGTH-len(finalLength)
    if pad >= 1:
        finalLength = finalLength + b' '*pad

    #attach header
    finalMessage = finalLength+finalMessage
    totalsent = 0
    while totalsent < len(finalMessage):
        try:
            sent = sock.send(finalMessage[totalsent:])
        except ConnectionAbortedError:
            print('Cannot send to loose player')
            break
        if sent == 0:
            raise RuntimeError('socket connection broken')
        totalsent = totalsent + sent

def enterRoom(player,room,direction=None,revive=None):
    #Changes player location and informs the new room of the arrival. Always call in a pair with leaveRoom, unless logging in/out
    if direction:
        direction = direction.lower()
    player.location = room.db[REnum['ID']]
    room.playerList.append(player)
    if revive:
        room.broadcast(player.name + ' returns from the dead in an explosion of divine radiance.',player)
        send(player.conn,'Divine intervention returns you to life.')
        return

    message = player.name + ' has arrived from '
    if direction:
        if direction == 'up':
            message += 'above.'
        elif direction == 'down':
            message += 'below.'
        else:
            message += 'the ' + direction + '.'
    else:
        message += 'nowhere.'
    room.broadcast(message,player)

def leaveRoom(player,room,direction=None,flee=None,dead=None):
    #Tells the room that the player is no longer going to be in it. Always call in a pair with enterRoom, unless logging in/out
    room.playerList.remove(player)
    #Dead players have already announced their death, no further action required.
    if dead:
        return

    if direction:
        direction = direction.lower()
    message = player.name
    if flee:
        mode = 'fled'
    else:
        mode = 'left'
    if direction:
        if direction == 'up':
            message += ' has ' + mode + ' upwards.'
        elif direction == 'down':
            message += ' has ' + mode + ' downwards.'
        else:
            message += ' has ' + mode + ' to the ' + direction + '.'
    else:
        message += ' has vanished.'
    room.broadcast(message)
