from enum import Enum
import settings as s


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

def reverseDirection(key):
    if key % 2:
        key -= 1
    else:
        key += 1
    return key

def convertStringToRoomEnum(string):
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
