import utility as u

class Room:
    def __init__(self,db):
        self.db = db
        self.playerList = []

    def broadcast(self,message,exceptPlayer=None,exceptOther=None): #Send a message to all players in the room, optionally exclude up to two players
        for player in self.playerList:
            if player == exceptPlayer or player==exceptOther:
                continue
            else:
                u.send(player.conn,message)

    def update(self,cursor):
        cursor.execute('SELECT * FROM rooms WHERE id = %s',(self.db[u.REnum['ID']],))
        self.db = cursor.fetchone()
