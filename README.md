# mud-project
This is a MUD,  or multi-user-dungeon, based on the d20 system. Combat rounds take place at fixed intervals across the server.

Operating a server:
0) Install Python and any library dependencies. Maybe I'll provide a full list later.
1) Generate a pair of encryption keys by running keygen.py
2) Create a new file called privatekey.py, single line which says PRIVATE_KEY = (the five part private key generated by keygen.py)
3) Change the PUBLIC_KEY constant in client.py to match the public key generated by keygen.py
4) Change the HOST constant in client.py to match your external IP address
5) Customize settings.py if desired
6) Install and set up MySQL (directions not included)
7) Change the arguments in line 3 of databasegen.py to match the name/password for your MySQL server
8) Run databasegen.py to generate the default tables
9) Change the arguments in line 22 of server.py to match the name/password for your MySQL server
10) Run the server
11) Optionally, use PyInstaller or another freezing option to make a client executable for your players

Joining a server:
0) If the server is distributing an executable, simply run it
1) Otherwise, install Python and any library dependencies of the client. Maybe I'll provide a full list later.
2) Open client.py in a text editor and change the HOST and PUBLIC_KEY constants to match those given by the server operator
3) Run client.py
