import mysql.connector

db = mysql.connector.connect(host='localhost',user='root',password='admin',database="mydatabase")
cursor = db.cursor()

try:
    cursor.execute("CREATE TABLE players (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), password VARCHAR(1000), \
                    location INT DEFAULT 1, race VARCHAR(255) DEFAULT 'non-specific', \
                    strength INT DEFAULT 10, dexterity INT DEFAULT 10, \
                    constitution INT DEFAULT 10, wisdom INT DEFAULT 10, \
                    intelligence INT DEFAULT 10, charisma INT DEFAULT 10)")
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

try:
    cursor.execute("CREATE TABLE races (name VARCHAR(255), strength INT, dexterity INT, constitution INT, wisdom INT, intelligence INT, charisma INT)")
    db.commit()
    cursor.execute("INSERT INTO races (name, strength, dexterity, constitution, wisdom, intelligence, charisma)\
                   VALUES (%s, %s, %s, %s, %s, %s, %s)",('non-specific',0,0,0,0,0,0))
    db.commit()
except:
    print('Races table already exists')


cursor.execute("SHOW TABLES")
tables = cursor.fetchall()
for table in tables:
    print(table)
    cursor.execute("SELECT * from "+table[0])
    content = cursor.fetchall()
    for entry in content:
        print(entry)
