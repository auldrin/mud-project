from enum import Enum
import settings as s


class REnum(Enum):
    #Enumerater which tells you where to look in a room db to find specific things
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
        #For when you have a number corresponding to a direction (2 through 7) but need a string for the direction
        return REnum(number).name

class PEnum(Enum):
    #Same as REnum but for rooms
    ID = 0
    NAME = 1
    PASSWORD = 2
    LOCATION = 3
    def get(number):
        #Probably useless
        return PEnum(number).name

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
        return REnum.EAST.value
    elif string == 'west':
        return REnum.WEST.value
    elif string == 'south':
        return REnum.SOUTH.value
    elif string == 'north':
        return REnum.NORTH.value
    elif string == 'up':
        return REnum.UP.value
    elif string == 'down':
        return REnum.DOWN.value
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

def send(sock,msg):
    #convert to bytes
    msg = bytes(msg,'utf-8')

    #assemble fixed length header
    length = bytes(str(len(msg)),'utf-8')
    pad = s.HEADER_LENGTH-len(length)
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

def enterRoom(player,room,direction=None):
    #Changes player location and informs the new room of the arrival. Always call in a pair with leaveRoom, unless logging in/out
    if direction:
        direction = direction.lower()
    player.location = room.db[REnum.ID.value]
    room.playerList.append(player)
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

def leaveRoom(player,room,direction=None,flee=None):
    #Tells the room that the player is no longer going to be in it. Always call in a pair with enterRoom, unless logging in/out
    if direction:
        direction = direction.lower()
    room.playerList.remove(player)
    message = player.name
    if flee:
        mode = 'fled'
    else:
        mode = 'left'
    if direction:
        if direction == 'up':
            message += ' has ' + mode + 'upwards.'
        elif direction == 'down':
            message += ' has ' + mode + ' downwards.'
        else:
            message += ' has ' + mode + ' to the ' + direction + '.'
    else:
        message += ' has vanished.'
    room.broadcast(message)
