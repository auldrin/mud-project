import mysql.connector

db = mysql.connector.connect(host='localhost',user='root',password='admin',database="mydatabase")

try:
    cursor.execute("CREATE TABLE players (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), password VARCHAR(1000), location INT)")
    db.commit()
except:
    print('Players table already exists')

try:
    cursor.execute("CREATE TABLE rooms (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), \
                    east INT, west INT, north INT, south INT, up INT, down INT, description VARCHAR(3000))")
    db.commit()
    cursor.execute("INSERT INTO rooms (name, east, west, north, south, up, down, description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",('Default Spawn',0,0,0,0,0,0,'Default spawn description'))
    db.commit()
except:
    print('Room table already exists')
