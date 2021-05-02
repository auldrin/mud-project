import utility as u
import random
import room as r

def say(player,room,message):
    message = message.partition(' ')[2]
    newMessage = ''.join((player.name,' says \'',message,'\''))
    room.broadcast(newMessage,player)
    u.send(player.conn,'You say \''+message+'\'')

def dig(room,message,rooms,cursor):
    #TODO: Replace this with code that works. Partition functionality not as expected.
    message = message.split()
    d = message[1]
    name = ' '.join(message[2:])
    #name = message.partition(' ')[2] #e.g 'dig west The Place' becomes 'west The Place'
    #d,pointlessVar,name = message.partition(' ')[2] #e.g 'west The Place' becomes 'west',' ','The Place'
    desc = 'Default description'
    west, east, south, north, up, down = 0, 0, 0, 0, 0, 0
    if d == 'east':
        west = room.db[u.REnum['ID']]
    elif d == 'west':
        east = room.db[u.REnum['ID']]
    elif d == 'north':
        south = room.db[u.REnum['ID']]
    elif d == 'south':
        north = room.db[u.REnum['ID']]
    elif d == 'down':
        up = room.db[u.REnum['ID']]
    elif d == 'up':
        down = room.db[u.REnum['ID']]
    #Save the room as the newest entry in the room table
    cursor.execute('INSERT INTO rooms (name, east, west, north, south, up, down, description) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
    (name,east,west,north,south,up,down,desc))
    #Now get the ID of the newest room
    cursor.execute('SELECT MAX(id) FROM rooms')
    newID = cursor.fetchone()
    #Use that ID to download the room from the database and add it to the rooms dict
    cursor.execute('SELECT * FROM rooms WHERE id = %s',(newID))
    rooms[newID[0]] = r.Room(cursor.fetchone())
    #Set the appropriate direction in the previous room to connect to this new room
    cursor.execute('UPDATE rooms SET '+ d +' = %s WHERE id = %s',(newID[0],room.db[u.REnum['ID']]))
    #db.commit()
    #Update the origin room to reflect the new link
    room.update(cursor)

def tele(player,message,rooms):
    print(rooms.keys())
    try:
        target = int(message.split()[1])
        target = rooms[target]
    except KeyError:
        u.send(player.conn,'Room ' + str(target) + ' does not exist')
        print(rooms.keys())
        return
    except (IndexError,ValueError):
        u.send(player.conn,'Please provide a target room. Correct format: \'tele 1\'')
        return
    u.leaveRoom(player,rooms[player.location])
    u.enterRoom(player,target)
    look(player,'',rooms)

def link(player,message,rooms,cursor):
    try:
        message = message.lower()
        message = message.split()
        d = message[1]
        t = message[2]
    except (AttributeError,TypeError,KeyError):
        send(player.conn,'Invalid usage, try: \'link west 1\' format instead.')
        return

    key = u.convertStringToRoomEnum(d)
    if not key:
        u.send(player.conn,'Direction invalid')
    try:
        cursor.execute('UPDATE rooms SET '+d+' = %s WHERE id = %s',(t,player.location,))
    except:
        u.send(player.conn,'Invalid usage, try: \'link west 1\' format instead.')
        return
    rooms[player.location].update(cursor)
    u.send(player.conn,'Successfully linked rooms')

def editDesc(player,message,rooms,cursor):
    message = message.partition(' ')[2]
    cursor.execute('UPDATE rooms set description = %s WHERE id = %s',(message,player.location))
    rooms[player.location].update(cursor)
    u.send(player.conn,'Successfully edited room description')

def editName(player,message,rooms,cursor):
    message = message.partition(' ')[2]
    cursor.execute('UPDATE rooms set name = %s WHERE id = %s',(message,player.location))
    rooms[player.location].update(cursor)
    u.send(player.conn,'Successfully edited room name')

def move(player,message,rooms,multi=False):
    if player.inCombat:
        u.send(player.conn,'You can\'t just walk out of combat!')
        return
    if multi: #message will be, for example, 'eeeswdu'
        for c in message:
            d = u.lengthenDirection(c) #take 'e' and make it 'east'
            try:
                destination = rooms[rooms[player.location].db[u.convertStringToRoomEnum(d)]] #convert east to the appropriate enum key for the database
            except KeyError:
                u.send(player.conn,'There\'s nothing that way')
                continue
            u.leaveRoom(player,rooms[player.location],d) #Inform the room and its players that the player is departing
            u.enterRoom(player,destination,u.REnumGet(u.reverseDirection(u.convertStringToRoomEnum(d)))) #convert east to the enum key, then flip it and convert it back
            look(player,'',rooms)
    else: #message will be, for example, 'east'
        try:
            destination = rooms[rooms[player.location].db[u.convertStringToRoomEnum(message)]] #turn east to an enum key for the database
        except KeyError:
            u.send(player.conn,'There\'s nothing that way')
            return
        u.leaveRoom(player,rooms[player.location],message)
        u.enterRoom(player,destination,u.REnumGet(u.reverseDirection(u.convertStringToRoomEnum(message)))) #convert east to an enum key, then reverse it
        look(player,'',rooms)

def look(player,message,rooms):
    room = rooms[player.location]
    try:
        arg = message.split()[1]
    except IndexError: #Triggered by message only containing one word, just means doing a default look
        pass
    try:
        key = u.convertStringToRoomEnum(arg)
        room = rooms[room.db[key]]
    except KeyError: #Triggered by rooms when room.db[key] is None, which means there is no room that way. Inform the player.
        u.send(player.conn,'There is nothing that way.')
        return
    except TypeError:
        pass #Type error will be triggered if key = None, which means arg was an unlisted direction. Just do a default look.
    except UnboundLocalError:
        pass #Triggered by trying to access arg for conversion, means there was no argument. Do a default look.

    directions = []
    players = []
    for x in range(2,8):
        if room.db[x]:
            directions.append(u.REnumGet(x))

    message = '\n'.join((room.db[u.REnum['NAME']], room.db[u.REnum['DESCRIPTION']],))
    for p in room.playerList:
        if p.name == player.name:
            continue
        message += ''.join(('\n',p.name,' is standing here.'))
    message += '\nValid directions: ' + ','.join(directions)
    u.send(player.conn,message)

def chat(player,message,connectionList):
    message = message.partition(' ')[2]
    message = '[CHAT] '+player.name+': '+message
    for connection in connectionList:
        try:
            u.send(connection,message)
        except AttributeError: #Will always happen when the server tries to send to itself.
            continue

def flee(player,message,rooms):
    #Calculate direction to go in
    options = []
    for index,direction in enumerate(range(2,8)):
        if rooms[player.location].db[direction]:
            options.append((rooms[player.location].db[direction],index))
    if not options:
        u.send(player.conn,'There is nowhere to flee.')
        return
    #Check success
    if player.inCombat:
        success = random.randint(0,1)
    else:
        success = True
    #Leave the room, end combat and unlock targets
    if success:
        target = random.choice(options)
        for enemy in player.opponents:
            enemy.opponents.remove(player)
            if enemy.target == player:
                enemy.target = None
            if not enemy.opponents:
                enemy.inCombat = False
            else:
                enemy.target = enemy.opponents[0]
        player.opponents = []
        player.target = None
        player.inCombat = False
        u.leaveRoom(player,rooms[player.location],u.REnumGet(target[1]),True)
        u.enterRoom(player,rooms[target[0]],u.REnumGet(u.reverseDirection(target[1])))
        look(player,'',rooms)
        if player.target:
            u.send(player.conn,'You successfully escaped ' + player.target.name)
        elif player.inCombat:
            u.send(player.conn,'You successfully escaped.')
        else:
            u.send(player.conn,'You successfully \'escaped\'.')
    else:
        u.send(player.conn,'You fail to get away!')

def kill(player, message, rooms):
    message = message.split()[1].capitalize()
    targetFound = False
    selfFound = False
    #See if the name matches anyone in the room, other than themselves
    for p in rooms[player.location].playerList:
        if p.name.startswith(message):
            if player == p:
                selfFound = True
                continue
            target = p
            targetFound = True
            break
    if selfFound and not targetFound:
        u.send(player.conn,'You can\'t kill yourself.')
        return
    elif not targetFound:
        u.send(player.conn,'There\'s nobody by that name here.')
        return
    #check if room is a valid location for combat, I guess?
    #
    if player.target == target:
        u.send(player.conn,'You\'re trying as hard as you can!')
        return
    #If they weren't already, both people are in combat now
    target.inCombat = True
    player.inCombat = True
    player.target = target
    if not target.target:
        target.target = player
    #It's possible the combatants were already engaged, but focusing different targets. Check that before adding to the opponent lists.
    if not target in player.opponents:
        player.opponents.append(target)
    if not player in target.opponents:
        target.opponents.append(player)
    #Tell the attacker, defender, and any bystanders, what's going on.
    u.send(player.conn,'You attack ' + target.name + '!')
    u.send(target.conn,player.name + ' attacks you!')
    rooms[player.location].broadcast(player.name + ' attacks ' + target.name +'!',player,target)

def me(player,message,rooms):
    try:
        message = message.partition(' ')[2]
    except KeyError:
        send(player.conn,'Do what?')
    rooms[player.location].broadcast(player.name + ' ' + message + '.')
