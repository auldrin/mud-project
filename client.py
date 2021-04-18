import socket, select, time, tkinter as tk


HOST = '192.168.2.15'
PORT = 1024

CLIENT_MESSAGE_MAX = 50
SERVER_MESSAGE_MAX = 200

class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, host, port):
        self.sock.connect((host,port))

    def send(self,msg):
        msg = bytes(pad(msg),'utf-8')
        totalsent = 0
        while totalsent < CLIENT_MESSAGE_MAX:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError('socket connection broken')
            totalsent = totalsent + sent
        print('Finished sending data')

    def receive(self):
        chunks = []
        bytes_recd = 0
        while bytes_recd < SERVER_MESSAGE_MAX:
            chunk = self.sock.recv(min(SERVER_MESSAGE_MAX - bytes_recd, 2048))
            if chunk == b'':
                raise RuntimeError('socket connection broken')
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return b''.join(chunks)

def pad(msg):
    if len(msg) < CLIENT_MESSAGE_MAX:
        return msg + ('`' * (CLIENT_MESSAGE_MAX - len(msg)))
    else:
        return msg


def handle_enter(event):
    global server
    text = textInput.get()
    textInput.delete(0,tk.END)

    output.insert(tk.INSERT,'\n'+text)
    server.send(pad(text))

def cleanString(msg):
    msg = str(msg,'utf-8')
    msg = msg.replace('`','')
    return msg


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
        output.insert(tk.INSERT, '\n'+cleanString(server.receive()))


    window.update_idletasks()
    window.update()


