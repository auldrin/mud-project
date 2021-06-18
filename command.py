import utility as u
import random
import room as r
import settings as s

class Controller:
    def __init__(self, rooms, cursor, playerList):
        self.commandList = {}
        self.commandList["chat"] = Chat(playerList)
        self.commandList["tell"] = Tell(playerList)
        self.commandList["who"] = Who(playerList)
        self.commandList["say"] = Say(rooms)
        self.commandList["look"] = Look(rooms)
        self.commandList["kill"] = Kill(rooms)
        self.commandList["me"] = Me(rooms)
        self.commandList["character"] = self.commandList["sheet"] = CharacterSheet()
        self.commandList["quit"] = Quit()
        self.commandList["level"] = Level(cursor)
        self.commandList["dig"] = Dig(rooms, cursor)
        self.commandList["link"] = Link(rooms, cursor)
        self.commandList["editdesc"] = EditDesc(rooms, cursor)
        self.commandList["editname"] = EditName(rooms, cursor)
        self.commandList["move"] = Move(rooms, self.commandList["look"])
        self.commandList["flee"] = Flee(rooms, self.commandList["look"])
        self.commandList["tele"] = Tele(rooms, self.commandList["look"])
        print(f"Created {len(self.commandList)} command aliases.")

    def execute(self, player, message):
        word = message.split()[0].lower()
        if u.checkForMultiMove(message) or word in ("north", "east", "south", "west", "up", "down"):
            self.commandList["move"].execute(player, message)
            return

        for key in self.commandList.keys():
            if key.startswith(word):
                self.commandList[key].execute(player, message)
                return
        else:
            u.send(player.conn,"Do what? (Try typing 'help')",player.key)

class Chat:
    def __init__(self, playerList):
        self.playerList = playerList

    def execute(self, player, message):
        message = message.partition(" ")[2]
        message = f"[CHAT] {player.name}: {message}"
        for recipient in self.playerList.values():
            try:
                u.send(recipient.conn, message, recipient.key)
            except (TypeError, AttributeError):
                # Will always happen when the server tries to send to itself.
                continue

class Quit:
    def __init__(self):
        pass

    def execute(self, player, message):
        try:
            confirmation = message.split()[1]
            if confirmation == "confirm":
                player.conn.close()
                # If room is safe, exit the player instantly. Otherwise, leave them loose.
                # Only way I can currently think of to cleanly remove the player from the game, unfortunately, is to set their AFK timer extremely high
                player.timer = 99999
                return
        except IndexError:
            u.send(player.conn, "To quit, type 'quit confirm'", player.key)
            return


class Say:
    def __init__(self, rooms):
        self.rooms = rooms

    def execute(self, player, message):
        room = self.rooms[player.location]
        message = message.partition(" ")[2]
        if message == "":
            u.send(player.conn, "What do you want to say?", player.key)
            return
        newMessage = f"{player.name} says '{message}'"
        room.broadcast(newMessage, player)
        u.send(player.conn, f"You say '{message}'", player.key)

class Dig:
    def __init__(self, rooms, cursor):
        self.rooms = rooms
        self.cursor = cursor

    def execute(self, player, message):
        room = self.rooms[player.location]
        message = message.split()
        try:
            d = message[1]
            name = " ".join(message[2:])
        except KeyError:
            u.send(
                player.conn, "Incorrect usage, try: dig [n,e,s,w,u,d] New_Name", player.key
            )
            return
        desc = "Default description"
        west, east, south, north, up, down = 0, 0, 0, 0, 0, 0
        if d == "east":
            west = room.db[u.REnum["ID"]]
        elif d == "west":
            east = room.db[u.REnum["ID"]]
        elif d == "north":
            south = room.db[u.REnum["ID"]]
        elif d == "south":
            north = room.db[u.REnum["ID"]]
        elif d == "down":
            up = room.db[u.REnum["ID"]]
        elif d == "up":
            down = room.db[u.REnum["ID"]]
        else:
            u.send(player.conn,"Invalid direction, try: dig [n,e,s,w,u,d] New_Name",player.key)
            return
        # Save the room as the newest entry in the room table
        self.cursor.execute(
            "INSERT INTO rooms (name, east, west, north, south, up, down, description) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (name, east, west, north, south, up, down, desc),
        )
        # Now get the ID of the newest room
        self.cursor.execute("SELECT MAX(id) FROM rooms")
        newID = self.cursor.fetchone()
        # Use that ID to download the room from the database and add it to the rooms dict
        self.cursor.execute("SELECT * FROM rooms WHERE id = %s", (newID))
        self.rooms[newID[0]] = r.Room(self.cursor.fetchone())
        # Set the appropriate direction in the previous room to connect to this new room
        self.cursor.execute(
            "UPDATE rooms SET " + d + " = %s WHERE id = %s",
            (newID[0], room.db[u.REnum["ID"]]),
        )
        # Update the origin room to reflect the new link
        room.update(self.cursor)

class Tele:
    def __init__(self, rooms, look):
        self.rooms = rooms
        self.look = look

    def execute(self, player, message):
        print(self.rooms.keys())
        try:
            target = int(message.split()[1])
            target = self.rooms[target]
        except KeyError:
            u.send(player.conn, f"Room {target} does not exist", player.key)
            return
        except (IndexError, ValueError):
            u.send(
                player.conn,
                "Please provide a target room. Correct format: 'tele 1'",
                player.key,
            )
            return
        u.leaveRoom(player, self.rooms[player.location])
        u.enterRoom(player, target)
        self.look.execute(player, "")


class Link:
    def __init__(self, rooms, cursor):
        self.rooms = rooms
        self.cursor = cursor

    def execute(self, player, message):
        try:
            message = message.lower()
            message = message.split()
            direction = message[1]
            target = message[2]
        except (AttributeError, TypeError, KeyError, IndexError):
            u.send(player.conn, "Invalid usage, try: 'link west 1' format instead.", player.key)
            return

        key = u.convertStringToRoomEnum(direction)
        if not key:
            u.send(player.conn, "Direction invalid", player.key)
        try:
            self.cursor.execute(
                "UPDATE rooms SET " + direction + " = %s WHERE id = %s",
                (
                    target,
                    player.location,
                ),
            )
        except:
            u.send(player.conn, "Invalid usage, try: 'link west 1' format instead.", player.key)
            return
        self.rooms[player.location].update(cursor)
        u.send(player.conn, "Successfully linked rooms")


class EditDesc:
    def __init__(self, rooms, cursor):
        self.rooms = rooms
        self.cursor = cursor

    def execute(self, player, message):
        room = rooms[player.location]
        message = message.partition(" ")[2]
        self.cursor.execute(
            "UPDATE rooms set description = %s WHERE id = %s", (message, player.location)
        )
        room.update(cursor)
        u.send(player.conn, "Successfully edited room description", player.key)


class EditName:
    def __init__(self, rooms, cursor):
        self.rooms = rooms
        self.cursor = cursor
    def execute(self, player, message):
        message = message.partition(" ")[2]
        room = rooms[player.location]
        self.cursor.execute(
            "UPDATE rooms set name = %s WHERE id = %s", (message, player.location)
        )
        room.update(cursor)
        u.send(player.conn, "Successfully edited room name", player.key)


class Move:
    def __init__(self, rooms, look):
        self.rooms = rooms
        self.look = look
    def execute(self, player, message):
        if player.inCombat:
            u.send(player.conn, "You can't just walk out of combat!", player.key)
            return
        multi = u.checkForMultiMove(message)
        if multi:  # message will be, for example, 'eeeswdu'
            for c in message:
                d = u.lengthenDirection(c)  # take 'e' and make it 'east'
                try:
                    destination = self.rooms[
                        self.rooms[player.location].db[u.convertStringToRoomEnum(d)]
                    ]  # convert east to the appropriate enum key for the database
                except KeyError:
                    u.send(player.conn, "There's nothing that way", player.key)
                    continue
                u.leaveRoom(
                    player, self.rooms[player.location], d
                )  # Inform the room and its players that the player is departing
                u.enterRoom(
                    player,
                    destination,
                    u.REnumGet(u.reverseDirection(u.convertStringToRoomEnum(d))),
                )  # convert east to the enum key, then flip it to west's enum key and convert it back to west
                self.look.execute(player, "")
        else:  # message will be, for example, 'east'
            try:
                destination = self.rooms[
                    self.rooms[player.location].db[u.convertStringToRoomEnum(message)]
                ]  # turn east to an enum key for the database
            except KeyError:
                u.send(player.conn, "There's nothing that way", player.key)
                return
            u.leaveRoom(player, self.rooms[player.location], message)
            u.enterRoom(
                player,
                destination,
                u.REnumGet(u.reverseDirection(u.convertStringToRoomEnum(message))),
            )  # convert east to an enum key, then reverse it
            self.look.execute(player, "")


class Look:
    def __init__(self, rooms):
        self.rooms = rooms

    def execute(self, player, message):
        room = self.rooms[player.location]
        try:
            arg = message.split()[1]
            for p in room.playerList:
                if p.name.startswith(arg.capitalize()):
                    lookAtPlayer(player, p)
                    return
            if arg == "self":
                lookAtPlayer(player, player)
        except IndexError:  # Triggered by message only containing one word, just means doing a default look
            pass

        try:
            key = u.convertStringToRoomEnum(arg)
            room = rooms[room.db[key]]
        except KeyError:  # Triggered by rooms when room.db[key] is None, which means there is no room that way. Inform the player.
            u.send(player.conn, "There is nothing that way.", player.key)
            return
        except TypeError:
            pass  # Type error will be triggered if key = None, which means arg was an unlisted direction. Just do a default look.
        except UnboundLocalError:
            pass  # Triggered by trying to access arg for conversion, means there was no argument. Do a default look.

        directions = []
        players = []
        for x in range(2, 8):
            if room.db[x]:
                directions.append(u.REnumGet(x))

        message = "\n".join(
            (
                room.db[u.REnum["NAME"]],
                room.db[u.REnum["DESCRIPTION"]],
            )
        )
        for p in room.playerList:
            if p.name == player.name:
                continue
            message += f"\n{p.name} is standing here."
        message += "\nValid directions: " + ",".join(directions)
        u.send(player.conn, message, player.key)

class Tell:
    def __init__(self, playerList):
        self.playerList = playerList
    def execute(self, player, message):
        message = message.split()
        try:
            target = message[1].capitalize()
        except IndexError:
            u.send(player.conn, "Tell who what?", player.key)
            return
        try:
            content = message[2]
        except IndexError:
            u.send(player.conn, "Tell them what?", player.key)
            return
        for p in self.playerList:
            try:
                if p.name.startswith(target):
                    sentContent = f"[TELL] {player.name}: {content}"
                    returnedContent = f"You tell {player.name}: {content}"
                    u.send(p.conn, sentContent, p.key)
                    u.send(player.conn, returnedContent, player.key)
                    return
            except AttributeError:
                # Will always happen when the server tries to send to itself.
                continue
        u.send(player.conn, "Player not found", player.key)
        return


class Flee:
    def __init__(self, rooms,look):
        self.rooms = rooms
        self.look = look

    def execute(self, player, message):
        # Calculate direction to go in
        options = []
        for index, direction in enumerate(range(2, 8)):
            if self.rooms[player.location].db[direction]:
                options.append((self.rooms[player.location].db[direction], index))
        if not options:
            # In the unlikely(?) event the player is trapped in a room with no exits
            u.send(player.conn, "There is nowhere to flee.", player.key)
            return
        if player.inCombat:
            # Check whether the attempt to flee is going to be successful
            success = random.randint(0, 1)
        else:
            success = True
        # Leave the room, end combat and unlock targets
        if success:
            direction = random.choice(options)
            u.leaveRoom(player, self.rooms[player.location], u.REnumGet(direction[1]), True)
            u.enterRoom(player, self.rooms[direction[0]], u.REnumGet(u.reverseDirection(direction[1])))
            self.look.execute(player, "")
            if player.target:
                u.send(
                    player.conn,
                    f"You successfully escaped {player.target.name}",
                    player.key,
                )
            elif player.inCombat:
                u.send(player.conn, "You successfully escaped.", player.key)
            else:
                u.send(player.conn, "You successfully 'escaped'.", player.key)
        else:
            u.send(player.conn, "You fail to get away!", player.key)
        return


class Kill:
    def __init__(self, rooms):
        self.rooms = rooms

    def execute(self, player, message):
        message = message.split()[1].capitalize()
        targetFound = False
        selfFound = False
        # See if the name matches anyone in the room, other than themselves
        for p in self.rooms[player.location].playerList:
            if p.name.startswith(message):
                if player == p:
                    selfFound = True
                    continue
                target = p
                targetFound = True
                break
        if selfFound and not targetFound:
            u.send(player.conn, "You can't kill yourself.", player.key)
            return
        elif not targetFound:
            u.send(player.conn, "There's nobody by that name here.", player.key)
            return
        elif player.target == target:
            u.send(player.conn, "You're trying as hard as you can!", target.key)
            return
        # check if room is a valid location for combat, I guess?
        #
        # If they weren't already, both people are in combat now
        if not player.inCombat:
            player.initiativeTotal = player.initiativeBonus + random.randint(1, 20)
            player.inCombat = True
        if not target.inCombat:
            target.initiativeTotal = target.initiativeBonus + random.randint(1, 20)
            target.inCombat = True
        # Whoever issued the command should target the target (obviously), but the target may already have a target
        player.target = target
        if not target.target:
            target.target = player
        # It's possible the combatants were already engaged, but focusing different targets. Check that before adding to the opponent lists.
        if not target in player.opponents:
            player.opponents.append(target)
        if not player in target.opponents:
            target.opponents.append(player)
        # Tell the attacker, defender, and any bystanders, what's going on.
        u.send(player.conn, f"You attack {target.name}!", player.key)
        u.send(target.conn, f"{player.name} attacks you!", target.key)
        self.rooms[player.location].broadcast(
            f"{player.name} attacks {target.name}!", player, target
        )


class Me:
    def __init__(self, rooms):
        self.rooms = rooms

    def execute(self, player, message):
        try:
            message = message.partition(" ")[2]
        except KeyError:
            send(player.conn, "Do what?", player.key)
            return
        self.rooms[player.location].broadcast(f"{player.name} {message}.")


def lookAtPlayer(viewer, target):
    if target.race[0] in "aeio":
        racial_article = "an"
    else:
        racial_article = "a"
    if target.inCombat:
        output = f"{target.name} is locked in battle against {target.target.name}\n"
    else:
        output = f"{target.name} is standing here.\n"
    output += f"{target.name} is {racial_article} {target.race}.\n"
    output += f"{target.name} is {target.healthCheck()}."
    u.send(viewer.conn, output, viewer.key)


class CharacterSheet:
    def __init__(self):
        pass

    def execute(self, player, messsage):
        if player.race[0] in "aeio":
            racial_article = "an"
        else:
            racial_article = "a"
        # The name and race
        output = f"You are {player.name}, {racial_article} {player.race}.\n"
        # level/class?
        # Health
        output += f"Hitpoints: {player.health}/{player.maxHealth}."
        # Attributes
        for attr in player.attributes.keys():
            output += f"\n {attr}: {player.attributesTotal[attr]}"
        # Saves
        # Skills
        # Other stuff?
        # send
        u.send(player.conn, output, player.key)


class Level:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(player, message):
        message = message.split()
        # Check if the player has specified a class, and if that class exists
        try:
            cursor.execute("SELECT * FROM classes WHERE name = %s", (message[1],))
        except IndexError:
            u.send(player.conn, "Gain a level in which class?", player.key)
            return
        c = cursor.fetchone()
        if not c:
            u.send(
                player.conn,
                "Class not found, try 'help classes' for a full list of valid choices",
                player.key,
            )
            return
        # Check if the player typed 'confirm'
        try:
            if not message[2] == "confirm":
                u.send(player.conn, "Type 'level [class] confirm' to level", player.key)
                return
        except IndexError:
            u.send(player.conn, "Type 'level [class] confirm' to level", player.key)
            return
        # Check if the player has enough xp (or hasn't chosen a starting class yet)
        lvl = len(player.levels)
        xpReq = (lvl * (lvl - 1) * s.XP_CONSTANT) - (lvl - 1 * (lvl - 2) * s.XP_CONSTANT)
        if lvl == 0 or player.xp >= xpReq:
            print(
                "level up"
            )  # apply all benefits of class in a function on the player, I think.
        else:
            u.send(
                player.conn,
                f"XP requirements not met, you need {xpReq - player.xp} more.",
                player.key,
            )
            return

class Who:
    def __init__(self, playerList):
        self.playerList = playerList

    def execute(player, message):
        output = "Online Players\n-------------"
        for p in self.playerList:
            try:
                output += f"\n{p.name}, {p.raceName}"
            except AttributeError:
                # First entry in playerList is actually the server, which will cause an error
                continue
        u.send(player.conn, output, player.key)
