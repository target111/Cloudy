version = "2.0"

import socket
import ssl
import time
from threading import Thread
from enum import Enum

#Classes and Functions

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class PrintType (Enum):
    Error = 1
    Warning = 2
    Info = 3

def printEx (message, type):
    print_type_str = ""
    if type == PrintType.Error:
        print_type_str = "[ERROR]"
    elif type == PrintType.Warning:
        print_type_str = "[WARN]"
    elif type == PrintType.Info:
        print_type_str = "[INFO]"

    print(print_type_str + " " + message + "\n")


class IRC_User(object):

    def __init__(self, nickname):
        self.nickname = nickname

    def connect(self, server):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ssl = ssl.wrap_socket(self.sock)

        ssl.connect(server.address, server.port)
        ssl.settimeout(timeout)

        self.send("NICK " + self.nickname)
        self.send("USER " + self.nickname + " 0 * :HI IM FUN")

    def send(self, message):
        self.ssl.send(message.encode("UTF-8") + "\r\n")

    def send_chan(self, message, channel):
        self.send("PRIVMSG " + channel + " :" + message)

    def join(self, channel):
        self.send("JOIN " + channel)

    def authenticate_nickserv(self, password):
        self.send("PRIVMSG NICKSERV IDENTIFY " + password)

    def set_mode_bot(self):
        self.send("MODE " + self.nickname + " +B")

    def recieve(self):
        return self.ssl.recv(4096).decode("UTF8")

class IRC_Server(object):
    def __init__(self, address, port):
        self.address = address
        self.port = port


#############################################################################################################
#############################################################################################################


#Connection Info
#TODO: load from config file. if non-existent, take user input.

irc_server        =  "irc.anonops.com"
irc_port          =   6697
irc_nickname      =  "wtfboom"
irc_nickserv_pwd  =  ""         #TODO: DO NOT STORE THE PASSWORD HERE, CHANGE IT
irc_channels      =  ["#spam", "#bots"]

timeout = 130

#Print Splash Screen
print(bcolors.OKBLUE+"""
  /$$$$$$                                    /$$$$$$$              /$$
 /$$__  $$                                  | $$__  $$            | $$
| $$  \__/  /$$$$$$   /$$$$$$  /$$$$$$/$$$$ | $$  \ $$  /$$$$$$  /$$$$$$
|  $$$$$$  /$$__  $$ |____  $$| $$_  $$_  $$| $$$$$$$  /$$__  $$|_  $$_/
 \____  $$| $$  \ $$  /$$$$$$$| $$ \ $$ \ $$| $$__  $$| $$  \ $$  | $$
 /$$  \ $$| $$  | $$ /$$__  $$| $$ | $$ | $$| $$  \ $$| $$  | $$  | $$ /$$
|  $$$$$$/| $$$$$$$/|  $$$$$$$| $$ | $$ | $$| $$$$$$$/|  $$$$$$/  |  $$$$/
 \______/ | $$____/  \_______/|__/ |__/ |__/|_______/  \______/    \___/
          | $$
          | $$
          |__/                                                            """+bcolors.ENDC)

bot = IRC_User(irc_nickname)
server = IRC_Server(irc_server, irc_port)

printEx("Connecting to IRC server: " + irc_server + ":" + irc_port, PrintType.Info)
try:
    bot.connect(server)
except Exception as e:
    printEx("Failed to connect. Stacktrace: " + e, PrintType.Error)
    exit()

printEx("Connection successful.", PrintType.Info)

#Wait a bit
time.sleep(2)

#Connected, authenticate
printEx("Sending credentials for " + irc_nickname, PrintType.Info)

bot.authenticate_nickserv(irc_nickserv_pwd)
bot.set_mode_bot()

printEx(" Credentials send. Waiting for authentication.", PrintType.Info)

#Wait a bit more
time.sleep(7)

#Join channels
for channel in irc_channels:
    bot.join(channel)


#Main Loop
while True:

    recieved = bot.recieve()


    if recieved.find('PING') != -1:
        bot.send("PONG " + recieved.split()[1] + '\r\n')

    if recieved.find(':=version') != -1:
        bot.send_chan(version, irc_channels[0])

    if recieved.find(':=die') != -1:
        user = recieved.split(':')
        user2 = [user1.split('!', 1) for user1 in user]
        user3 = user2[1][0]
        if user3 not in botowner:
            bot.message("This function is for admins only!")
        else:
            bot.message("oh...okay. :'(")
            bot._send("QUIT \r\n")
            exit()

    if recieved.find(":=quote") != -1:
        user = recieved.split(':')
        user2 = [user1.split('!', 1) for user1 in user]
        user3 = user2[1][0]
        arg = recieved.split()
        try:
            arg1 = arg[4]
            if arg1 == "add":
                if user3 not in botowner:
                    bot.message("This function is for admins only!")
                else:
                    quote = recieved.split('"')
                    bot.message("Quote added! Also cocks")
                    open("quotes.txt", "a").write(quote[1] + "\n")
            elif arg1 == "read":
                f = open("quotes.txt", "r").readlines()
                arg2 = arg[5]
                bot.message(f[int(arg2)])
            elif arg1 == "count":
                with open("quotes.txt", "r") as f:
                    for i, l in enumerate(f):
                        pass
                    x = i
                    bot.message("I have %r quotes!" % x)
        except:
            try:
                with open("quotes.txt") as f:
                    for i, l in enumerate(f):
                        pass
                    x = i
                arg2 = arg[5]
                if int(arg2) > x:
                    bot.message("I dont have more then %r" % x)
            except:
                bot.message('Use =quote add/read/count "<quote>"/<number>')

    if recieved.find(":=memetic") != -1:
        text = open("quotes.txt", "r").read()
        text_model = markovify.Text(text)
        try:
            output = text_model.make_short_sentence(10000)
            bot.message(output)
        except:
            bot.message('Whoops! COCKS!')

    if recieved.find(":=poll") != -1:
        options = recieved.split()[4]
        if options == "new":
            user = recieved.split(':')
            user2 = [user1.split('!', 1) for user1 in user]
            user3 = user2[1][0]
            global description
            description = recieved.split('"')[1]
            starter = user3
            if pollRunning == False:
                Thread.start_new_thread(bot.poll, ())
            else:
                bot.message("A poll is already running! Wait till its done.")
        elif options == "finish" and starter == user3:
            timepassed = 1200

    if recieved.find(":=ascii") != -1:
        try:
            message = recieved.split()
            cfont = message[4]
            text = message[5]
            f = Figlet(font=cfont)
            printascii = f.renderText(text)
            printascii2 = printascii.split('\n')
            for asciii in printascii2:
                bot.message(random.choice(colors1) + asciii + "\x03")
        except:
            bot.message("Use =ascii <font> <text>. For a list of fonts visit https://pastebin.com/TvwCcNUd ")

    if recieved.find(':=spam') != -1:
        try:
            spam1 = recieved.split('"')
            spam = recieved.split()
            word = spam1[1] + " | \x03"
            times = spam1[2]
            if int(times) > 150:
                bot.message("Don't abuse meh! Use a number smaller then 150")
            else:
                for i in range(int(times)):
                    time.sleep(1)
                    cword = random.choice(colors) + word
                    bot.message(str(cword) * 40)
        except:
            bot.message('Use =spam "<message>" <times>')

    if recieved.find(':=art') != -1:
        try:
            asciiart1 = random.choice(asciiart)
            asciiart2 = asciiart1.split('\n')
            for asciiart3 in asciiart2:
                time.sleep(1)
                bot.message(random.choice(colors1) + asciiart3 + "\x03")
        except:
            pass

    if recieved.find(':=help') != -1:
        try:
            helpcoms1 = helpcoms.split('\n')
            for helpcoms2 in helpcoms1:
                bot.message(helpcoms2)
        except:
            pass