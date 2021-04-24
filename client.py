import socket, select, sys, tkinter as tk


HOST = '192.168.2.15'
PORT = 1024
HEADER_LENGTH = 10

class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, host, port):
        self.sock.connect((host,port))

    def settimeout(self, time):
        self.sock.settimeout(time)

    def re_init(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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

def receive(sock):
    chunks = []
    bytes_recd = 0
    #receive header
    while bytes_recd < HEADER_LENGTH:
        chunk = sock.recv(min(HEADER_LENGTH - bytes_recd, HEADER_LENGTH))
        if chunk == b'':
            raise ConnectionResetError('Socket closed during reading')
        chunks.append(chunk)
        bytes_recd = bytes_recd + len(chunk)
    #reassemble and decode header
    header = b''.join(chunks)
    length = int(str(header,'utf-8'))

    chunks = []
    bytes_recd = 0
    #receive body
    while bytes_recd < length:
        chunk = sock.recv(min(length - bytes_recd, length))
        if chunk == b'':
            raise ConnectionResetError('Socket closed during reading')
        chunks.append(chunk)
        bytes_recd = bytes_recd + len(chunk)
    return str(b''.join(chunks),'utf-8')

def handle_enter(event):
    global textCursor
    text = textInput.get()
    textInput.delete(0,tk.END)
    output.insert(tk.INSERT,'\n'+text)
    send(server.sock,text)
    textHistory.append(text)
    textCursor = 0

def history_up(event):
    global textCursor
    textCursor = textCursor-1
    textInput.delete(0,tk.END)
    try:
        textInput.insert(tk.INSERT,textHistory[textCursor])
    except:
        textCursor = textCursor+1
        textInput.insert(tk.INSERT,textHistory[textCursor])

def history_down(event):
    global textCursor
    textCursor = min(0,textCursor + 1)
    textInput.delete(0,tk.END)
    if textCursor != 0:
        textInput.insert(tk.INSERT,textHistory[textCursor])

def on_close():
    window.destroy()


window = tk.Tk()
window.title("PyMUD2021 Client")
window.bind('<Return>',handle_enter)
window.bind('<Up>',history_up)
window.bind('<Down>',history_down)
window.protocol("WM_DELETE_WINDOW", on_close)

output = tk.Text(window,background='black',foreground='yellow',width = 100,height=50)
output.insert(tk.INSERT, "Welcome to the videogames")
output.grid(row=0,sticky='N')

textInput = tk.Entry(window,width=50)
textInput.grid(sticky='S',row=1)

textInputText = tk.Label(window,text='Type:',width=10)
textInputText.grid(sticky='SW',row=1)


window.update()
textHistory = []
textCursor = 0
textInput.focus()


server = Server()
server.settimeout(0.05)
output.insert(tk.INSERT, "\nConnecting to server...")
window.update()

while True:
    while True:
        try:
            server.connect(HOST,PORT)
            output.insert(tk.INSERT, "\nConnected successfully.")
            server.settimeout(None)
            window.update()
            break
        except (socket.timeout,ConnectionRefusedError):
            server.re_init()
            server.settimeout(0.05)
            window.update()
            continue

    print('Entering main loop')
    while True:
        incoming,outgoing,error = select.select([server.sock],[server.sock],[server.sock])
        if incoming:
            try:
                output.insert(tk.INSERT, '\n'+receive(server.sock))
            except (ConnectionResetError):
                output.insert(tk.INSERT, '\nConnection reset by server, attempting to reconnect')
                server.re_init()
                server.settimeout(0.05)
                break
        elif error:
            print('Shit\'s fucked')
        window.update_idletasks()
        window.update()



