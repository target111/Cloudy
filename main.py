version = "2.0.0.0"

import socket
import ssl
import time
import random
from threading import Thread
from enum import Enum

#############################################################################################################
#############################################################################################################

class ConsoleColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

colors1=["\x0303", "\x0302", "\x0301", "\x0304", "\x0305", "\x0306", "\x0307","\x0309", "\x0308", "\x0310"]
colors=["\x0304,02","\x0309,12","\x0308,13", "\x0307,11", "\x0303", "\x0302", "\x0301", "\x0312,15", "\x0304", "\x0304,06", "\x0301,07", "\x0304", "\x0305", "\x0305", "\x0306", "\x0307","\x0309"]


class PrintType (Enum):
    Error = 1
    Warning = 2
    Info = 3

def printEx (message, type):
    print_type_str = ""
    if type == PrintType.Error:
        print_type_str = ConsoleColors.FAIL + "[ERROR]" + ConsoleColors.ENDC
    elif type == PrintType.Warning:
        print_type_str = ConsoleColors.WARNING + "[WARN]" + ConsoleColors.ENDC
    elif type == PrintType.Info:
        print_type_str = ConsoleColors.OKBLUE + "[INFO]" + ConsoleColors.ENDC

    print(print_type_str + " " + message + "\n")


class IRC_User(object):

    def __init__(self, nickname):
        self.nickname = nickname

    def connect(self, server):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.irc_ssl = ssl.wrap_socket(self.sock)

        self.irc_ssl.connect(server.address, server.port)
        self.irc_ssl.settimeout(timeout)

        self.send("NICK " + self.nickname)
        self.send("USER " + self.nickname + " 0 * :HI IM FUN")

    def send(self, message):
        self.irc_ssl.send(message.encode("UTF-8") + "\r\n")

    def send_chan(self, message, channel):
        self.send("PRIVMSG " + channel + " :" + message)

    def join(self, channel):
        self.send("JOIN " + channel)

    def authenticate_nickserv(self, password):
        self.send("PRIVMSG NICKSERV IDENTIFY " + password)

    def set_mode_bot(self):
        self.send("MODE " + self.nickname + " +B")

    def recieve(self):
        recvd = self.irc_ssl.recv(4096).decode("UTF8")

        #TODO: make this optional
        if recvd.find("PING") != -1:
            self.send("PONG" + recvd.split(" ")[1])

        nickname = recvd.split('!')[0][1:]
        username = recvd.split('!')[1].split('@')[0]
        host = recvd.split('@')[1].split(' ')[0]
        channel = recvd.split(' ')[2]
        message = recvd.split(':')[2]

        if (channel == self.nickname):
            channel = nickname

        data = IRC_Data(nickname, username, host, channel, message)
        return data

class IRC_Server(object):
    def __init__(self, address, port):
        self.address = address
        self.port = port

class IRC_Data(object):
    def __init__(self, nickname, username, host, channel, message):
        self.nickname = nickname
        self.username = username
        self.host = host
        self.channel = channel
        self.message = message

class Poll(object):
    def __init__(self, channel, nickname, description, options, time_started):
        self.channel = channel
        self.nickname = nickname
        self.description = description
        self.options = options
        self.time_started = time_started

class PollOption(object):
    def __init__(self, description):
        self.description = description
        self.votes = []


#############################################################################################################
#############################################################################################################


#Connection Info
#TODO: load from config file. if non-existent, take user input.

irc_server        =  "irc.anonops.com"
irc_port          =   6697
irc_nickname      =  "wtfboom_beta"
irc_nickserv_pwd  =  ""         #TODO: DO NOT STORE THE PASSWORD HERE, CHANGE IT
irc_channels      =  ["#bottest", "#bots"]

timeout = 130
command_character = "="

#TODO: Either use admin status as owner or load form config
#TODO: Also, insecure. someone can set their nick to yours and quickly execute a command before nickserv changes their name
bot_owner = ["target_",  "North_Star", "OverclockedSanic", "darko", "scribbler", "nautilus", "Gen0cide"]

prompt_priviledge_required = "This command requires sudo access, kid."

#############################################################################################################
#############################################################################################################

#Print Splash Screen
print(ConsoleColors.OKBLUE + """
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
          |__/                                                            """ + ConsoleColors.ENDC)

bot = IRC_User(irc_nickname)
server = IRC_Server(irc_server, irc_port)

printEx("Connecting to IRC server: " + irc_server + ":" + str(irc_port), PrintType.Info)
try:
    bot.connect(server)
except Exception as e:
    printEx("Failed to connect. Stacktrace: " + str(e), PrintType.Error)
    exit()

printEx("Connection successful.", PrintType.Info)

#Wait a bit
time.sleep(2)

#Connected, authenticate
printEx("Sending credentials for " + irc_nickname, PrintType.Info)

bot.authenticate_nickserv(irc_nickserv_pwd)
bot.set_mode_bot()

printEx("Credentials sent. Waiting for authentication...", PrintType.Info)

#Wait a bit more
time.sleep(7)

#Join channels
for channel in irc_channels:
    bot.join(channel)


#############################################################################################################
#############################################################################################################

poll_threads = []

class ThreadPoll(Thread):

   def __init__(self, poll):
        self.poll = poll
        self.time_started = time.time()
        Thread.__init__(self)

   def run(self):
        while time.time() - self.time_started < 60:
            #TODO
            print("IM GONNA EAT YO ASS BOII")

        poll_threads.remove(self)


#Main Loop
while True:

    data = bot.recieve()
    print(data)
    if data.find(":="):
        cmd=data.split()[4]
        if cmd == "version":
            bot.send_chan("Version :" + version, data.channel)


        if cmd == "die":
            if data.nickname not in bot_owner:
                bot.send_chan(prompt_priviledge_required, data.channel)
            else:
                bot.send_chan("oh...okay. :'(", data.channel)
                bot.send("QUIT")
                exit()


        #TODO: Clean up this mess
        if cmd == "quote":
            try:
                if args[1].lower() == "add":
                    if data.nickname not in bot_owner:
                        bot.send_chan(prompt_priviledge_required, data.channel)
                    else:
                        quote = data.message.split('"')
                        bot.send_chan("Quote added! Also cocks", data.channel)
                        open("quotes.txt", "a").write(quote[1] + "\n")
                elif (args[1].lower() == "count") or (False):
                    with open("quotes.txt", "r") as f:
                        for i, l in enumerate(f):
                            pass
                        x = i
                        bot.send_chan("I have %r quotes!" % x, data.channel)
                elif arg1 == "read":
                    f = open("quotes.txt", "r").readlines()
                    arg2 = arg[5]
                    bot.send_chan(f[int(arg2)], data.channel)
            except:
                try:
                    with open("quotes.txt") as f:
                        for i, l in enumerate(f):
                            pass
                        x = i
                    arg2 = arg[5]
                    if int(arg2) > x:
                        bot.send_chan("I dont have more then %r" % x, data.channel)
                except:
                    bot.send_chan('Use =quote add/read/count "<quote>"/<number>', data.channel)


        #TODO: Resolve dependency
        if cmd == "memetic":
            text = open("quotes.txt", "r").read()
            text_model = markovify.Text(text)
            try:
                output = text_model.make_short_sentence(10000)
                bot.send_chan(output, data.channel)
            except:
                bot.send_chan("Whoops! COCKS!", data.channel)


        #TODO: Finish this and clean up the mess
        if cmd == "poll":
            if args[1].lower() == "new":

                create_poll = True
                for poll_thread in poll_threads:
                    if poll_thread.poll.channel == data.channel:
                        create_poll = False
                        #TODO: msg
                        break

                if create_poll:

                    thread_new = ThreadPoll(Poll(data.channel, data.nickname, args[2], args[3:], time.time()))
                    thread_new.start()
                    poll_threads.append(thread_new)

            elif args[1].lower() == "vote":

                poll_exists = False
                for poll_thread in poll_threads:
                    if poll_thread.poll.channel == data.channel:
                        poll_exists = True
                        # TODO: msg
                        break

                if poll_running:
                    poll_voted = False
                    for option in poll_intended.options:
                        for voter in option.votes:
                            if voter == data.nickname:
                                poll_voted = True
                                break
                    if poll_voted:
                        bot.send_chan( "Sorry " + data.nickname + ", you already voted.", data.channel)
                    #else:
                        #TODO: Announce
                else:
                    bot.send_chan("No poll currently running." ,data.channel)


        #TODO: Dependency
        if cmd == "ascii":
            try:
                message = data.split()
                cfont = message[4]
                text = message[5]
                f = Figlet(font=cfont)
                printascii = f.renderText(text)
                printascii2 = printascii.split('\n')
                for asciii in printascii2:
                    bot.send_chan(random.choice(colors1) + asciii + "\x03", data.channel)
            except:
                bot.send_chan("Use " + command_character + "ascii <font> <text>. For a list of fonts visit https://pastebin.com/TvwCcNUd ", data.channel)



        if cmd == "spam":
            try:
                word = args[2] + " | \x03"
                times = args[1]
                #TODO: set configuarble limit
                spam_limit = 100
                if int(times) > spam_limit:
                    bot.send_chan("Don't abuse meh! Use a number smaller than " + str(spam_limit), data.channel)
                else:
                    for i in range(int(times)):
                        time.sleep(1)
                        cword = random.choice(colors) + word
                        bot.send_chan(str(cword) * 40, data.channel)
            except:
                bot.send_chan("Use " + command_character + "spam <times> <message>", data.channel)


        if cmd == "art":
            if not art_running:
                ThreadArt.start()


        #if cmd == "help":
            #if len(args) == 1:

            #else:
                #if args[2] == "":

                #elif :
