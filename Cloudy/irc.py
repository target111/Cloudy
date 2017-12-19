from threading import Thread
from enum import Enum
import socket
import ssl

class IRCColors:
    White   = "00"
    Black   = "01"
    Blue    = "02"
    Green   = "03"
    Red     = "04"
    Brown   = "05"
    Purple  = "06"
    Orange  = "07"
    Yellow  = "08"
    Lime    = "09"
    Cyan    = "10"
    Aqua    = "11"
    LBlue   = "12"
    Pink    = "13"
    Grey    = "14"
    LGrey   = "15"

    all_colors = [White, Black, Blue, Green, Red, Brown, Purple, Orange, Yellow, Lime, Cyan, Aqua, LBlue, Pink, Grey, LGrey]

class IRCFormat:
    Action    = "\x01"
    Bold      = "\x02"
    Color     = "\x03"
    Italic    = "\x1D"
    Underline = "\x1F"
    Swap      = "\x16" #Swaps BG and FG colors
    Reset     = "\x0F"

def Format(string, format):
    return "".join(format) + string + "".join(format[::-1])

def Color(string, fg, bg=None):
    if bg == None:
        return IRCFormat.Color + fg + string + IRCFormat.Color
    else:
        return IRCFormat.Color + fg + "," + bg + string + IRCFormat.Color

class IRC_Client(object):

    def __init__(self, nickname):
        self.nickname = nickname

    def connect(self, server, use_ssl):

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        #SSL
        if use_ssl:
            self.sock = ssl.wrap_socket(self.sock)
        
        self.sock.connect((server.address, server.port))
        self.sock.setblocking(True)

        self.send_raw("NICK " + self.nickname)
        self.send_raw("USER " + self.nickname + " 0 * :HIIMFUN")

        #Respond to initial ping
        for _ in range(2):
            pingis = self.recieve_raw()
        if pingis.split()[0] == "PING":
            self.send_raw("PONG " + pingis.split()[1][1:])

    def send_raw(self, message):
        if not message == "":
            self.sock.send((message + "\r\n").encode("UTF-8"))

    def send(self, message, channel):
        self.send_raw("PRIVMSG " + channel + " :" + message)

    def notice(self, message, nickname):
        self.send_raw("NOTICE " + nickname + " :" + message)

    def action(self, message, channel):
        self.send(Format("ACTION " + message, IRCFormat.Action), channel)

    def join(self, channel):
        self.send_raw("JOIN " + channel)

    def exit(self):
        self.send_raw("QUIT")

    def set_mode(self, nickname, mode):
        self.send_raw("MODE " + nickname + " +" + mode)

    def recieve_raw(self):
        return self.sock.recv(4096).decode("UTF-8","ignore")

    def recieve(self):
        raw = self.recieve_raw()
        return IRC_Data(raw)


class IRC_Server(object):
    def __init__(self, address, port):
        self.address = address
        self.port = port

    def toString(self):
        return self.address + ":" + self.port


class IRC_Data(object):
    def __init__(self, input):

        self.type_command = IRC_CommandType.Unknown

        if "PING" in input:

            self.sender_type = None
            self.sender = None

            try:
                if input.split()[0] == "PING":
                    self.type_command = IRC_CommandType.Ping
                    self.data = input.split()[1]

                else:
                    if ":PING" in input:
                        index_ = input.split().index(":PING")
                    else:
                        index_ = input.split().index("PING")

                    if len(input.split()) > index_:
                        self.type_command = IRC_CommandType.Ping
                        self.data = input.split()[index_ + 1]

            except:
                pass


        elif input[:1] == ":":

            input = input[1:]
            sender = input.split()[0]

            if "!" in sender and "@" in sender:
                self.sender_type = IRC_SenderType.Client
                self.sender = IRC_User(sender)
            else:
                self.sender_type = IRC_SenderType.Server
                self.sender = sender


            try:
                if input.split()[1] == "JOIN":
                    self.type_command = IRC_CommandType.Join
                    self.channel = input.split()[2][1:]
            except:
                pass

            try:
                if input.split()[1] == "MODE":
                    self.type_command = IRC_CommandType.Mode
                    self.nickname = input.split()[2]
                    self.mode = input.split()[3]
                    if len(input.split(":", 1)) == 1:
                        self.channel = None
                    else:
                        self.channel = input.split(":", 1)[1]
            except:
                pass

            try:
                if input.split()[1] == "PRIVMSG" and not input.split(":")[1].split()[0] == IRCFormat.Action + "ACTION":
                    self.type_command = IRC_CommandType.Message
                    self.channel = input.split()[2]
                    self.message = input.split(":", 1)[1]
            except:
                pass

            try:
                if input.split()[1] == "PRIVMSG" and input.split(":")[1].split()[0] == "ACTION" and input[-1:] == IRCFormat.Action:
                    self.type_command = IRC_CommandType.Action
                    self.message = input.split(":", 1)[1].split(" ", 1)[1][:-1]
            except:
                pass

            try:
                if input.split()[1] == "INVITE":
                    self.type_command = IRC_CommandType.Invite
                    self.nickname = input.split()[2]
                    self.channel = input.split(":", 1)[1]
            except:
                pass

            try:
                if input.split()[1] == "NOTICE":
                    self.type = IRC_CommandType.Notice
                    self.notice_string = input.split()[1]
                    self.message = input.split(":", 1)[1]
            except:
                pass

            try:
                if input.split("!")[0] == "NickServ":
                    self.type_command = IRC_CommandType.Nickserv
                    try:
                        self.data = int(input.split()[5])
                    except:
                        self.data = None
            except:
                pass

            try:
                if input.split()[1] == "NICK":
                    self.type_command = IRC_CommandType.Nick
                    self.nickname = input.split()[2]
            except:
                pass

            try:
                if input.split()[1] == "TOPIC":
                    self.channel = input.split()[2]
                    self.message = input.split(":", 1)[1]
            except:
                pass

            try:
                if input.split()[1] == "QUIT":
                    self.type_command = IRC_CommandType.Quit
                    self.message = input.split(":", 1)[1]
            except:
                pass

        else:
            self.sender_type = None
            self.sender = None


class IRC_CommandType(Enum):
    Unknown =  0
    Join    =  1
    Mode    =  2
    Message =  3
    Action  =  4
    Invite  =  5
    Notice  =  6
    Nick    =  7
    Ping    =  8
    Kick    =  9
    Topic   = 10
    Quit    = 11
    Nickserv= 12

class IRC_SenderType(Enum):
    Server = 0
    Client = 1

class IRC_User(object):
    def __init__(self, input):
        self.nickname = input.split("!")[0]
        self.username = input.split("!")[1].split("@")[0]
        self.host     = input.split("@")[1]

    def toString(self):
        return self.nickname + "!" + self.username + "@" + self.host

class IRC_Mode:
    Bot      = "B"
    Ban      = "b"
    Operator = "a"
