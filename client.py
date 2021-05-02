import socket
import select
import sys
import rsa
import tkinter as tk
from tkinter import font as tkFont

HOST = '192.168.2.15'

PORT = 1024
HEADER_LENGTH = 10
TIMEOUT = 0.5
PUBLIC_KEY = rsa.PublicKey(25225735533549590446154239934719976934564125485812868128664974319512400129448962900647860261364657347374200184501646862047716180620318795937656111092231004743228245673403201831418447465807627542356795291999638304626843013111414452018310445683427977755671257614629164865516160854280416179725923473446697801971823478617336942118730805390658888069242890374893259399375525097648546984418979507509110342128547444918265845898987465653727381056773086043649181402614557848636666664040623462583388296567481199738407416110407148170802467959298026142070547049090254980267235402311098734078328443321816391254798054871666346200741, 65537)
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
    msg = rsa.encrypt(msg,PUBLIC_KEY)
    #assemble fixed length header
    length = bytes(str(len(msg)),'utf-8')
    pad = HEADER_LENGTH-len(length)
    if pad >= 1:
        length += b' '*pad
    #attach header
    msg = length+msg
    print(length)

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
    if not text:
        return
    text = text.strip()
    textInput.delete(0,tk.END)
    output.config(state='normal')
    output.insert(tk.END,'\n'+text,"italic")
    output.config(state='disabled')
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


output = tk.Text(window,background='black',foreground='yellow',width = 100,height=40)
output.insert(tk.INSERT, "Welcome to the videogames")
output.config(state='disabled')
output.grid(row=0,sticky='N')

default_font = tkFont.nametofont(output.cget("font"))
italic_font = tkFont.Font(**default_font.configure())
italic_font.configure(slant="italic")
output.tag_configure("italic",font=italic_font)

textInput = tk.Entry(window,width=90)
textInput.grid(sticky='S',row=1)

textInputText = tk.Label(window,text='Type:',width=10)
textInputText.grid(sticky='SW',row=1)


window.update()
textHistory = []
textCursor = 0
textInput.focus()


server = Server()
server.settimeout(TIMEOUT)
output.config(state='normal')
output.insert(tk.INSERT, "\nConnecting to server...")
output.config(state='disabled')
window.update()

while True:
    while True:
        try:
            server.connect(HOST,PORT)
            output.config(state='normal')
            output.insert(tk.INSERT, "\nConnected successfully.")
            output.config(state='disabled')
            server.settimeout(None)
            window.update()
            break
        except (socket.timeout,ConnectionRefusedError):
            server.re_init()
            server.settimeout(TIMEOUT)
            window.update()
            continue

    print('Entering main loop')
    while True:
        incoming,outgoing,error = select.select([server.sock],[server.sock],[server.sock])
        if incoming:
            try:
                output.config(state='normal')
                output.insert(tk.END, '\n'+receive(server.sock))
                output.see(tk.END)
                output.config(state='disabled')
            except (ConnectionResetError):
                output.config(state='normal')
                output.insert(tk.END, '\nConnection reset by server, attempting to reconnect')
                output.config(state='disabled')
                server.re_init()
                server.settimeout(TIMEOUT)
                break
        elif error:
            print('Shit\'s fucked')
        window.update_idletasks()
        window.update()



