import socket, select, time, tkinter as tk


HOST = '192.168.2.15'
PORT = 1024
HEADER_LENGTH = 10

CLIENT_MESSAGE_MAX = 50
SERVER_MESSAGE_MAX = 200

class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, host, port):
        self.sock.connect((host,port))

def send(sock,msg):
    #convert to bytes
    msg = bytes(msg,'utf-8')

    #assemble fixed length header
    length = bytes(str(len(msg)),'utf-8')
    pad = HEADER_LENGTH-len(length)
    if pad >= 1:
        length = length + b' '*pad

    #attach header
    msg = length+msg

    totalsent = 0
    while totalsent < len(msg):
        sent = sock.send(msg[totalsent:])
        if sent == 0:
            raise RuntimeError('socket connection broken')
        totalsent = totalsent + sent
    print(str(msg,'utf-8'))

def receive(sock):
    chunks = []
    bytes_recd = 0
    #receive header
    while bytes_recd < HEADER_LENGTH:
        chunk = sock.recv(min(HEADER_LENGTH - bytes_recd, HEADER_LENGTH))
        if chunk == b'':
            raise RuntimeError('Socket closed during reading')
        chunks.append(chunk)
        bytes_recd = bytes_recd + len(chunk)
    #reassemble and decode header
    header = b''.join(chunks)
    length = int(str(header,'utf-8'))
    print('Received header: ',length)

    chunks = []
    bytes_recd = 0
    #receive body
    while bytes_recd < length:
        chunk = sock.recv(min(length - bytes_recd, length))
        if chunk == b'':
            raise RuntimeError('Socket closed during reading')
        chunks.append(chunk)
        bytes_recd = bytes_recd + len(chunk)
    return b''.join(chunks)

def handle_enter(event):
    text = textInput.get()
    textInput.delete(0,tk.END)
    output.insert(tk.INSERT,'\n'+text)
    send(server.sock,text)


window = tk.Tk()
window.title("My Application")
window.bind('<Return>',handle_enter)


output = tk.Text(window,background='black',foreground='yellow',width = 100,height=50)
output.insert(tk.INSERT, "Welcome to the videogames")
output.grid(row=0,sticky='N')

textInput = tk.Entry(window,width=50)
textInput.grid(sticky='S',row=1)

textInputText = tk.Label(window,text='Type:',width=10)
textInputText.grid(sticky='SW',row=1)

window.update()
server = Server()
output.insert(tk.INSERT, "\nConnecting to server...")
window.update()
while True:
    try:
        server.connect(HOST,PORT)
        output.insert(tk.INSERT, "\nConnected successfully.")
        window.update()
        break
    except:
        output.insert(tk.INSERT, "\nFailed to connect, retrying")
        window.update()
        continue

lastTime = time.time()
while True:
    if time.time() - lastTime < 0.01:
        continue
    else:
        lastTime = time.time()

    incoming,outgoing,error = select.select([server.sock],[server.sock],[server.sock])
    if incoming:
        output.insert(tk.INSERT, '\n'+str(receive(server.sock),'utf-8'))


    window.update_idletasks()
    window.update()


