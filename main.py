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

    print(print_type_str + " " + message)


class IRC_Client(object):

    def __init__(self, nickname):
        self.nickname = nickname

    def connect(self, server):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.irc_ssl = ssl.wrap_socket(self.sock)

        self.irc_ssl.connect((server.address, server.port))
        self.irc_ssl.settimeout(timeout)

        self.send_raw("NICK " + self.nickname)
        self.send_raw("USER " + self.nickname + " 0 * :HIIMFUN")

    def send_raw(self, message):
        self.irc_ssl.send((message + "\r\n").encode("UTF-8"))

    def send(self, message, channel):
        self.send_raw("PRIVMSG " + channel + " :" + message)

    def action(self, message, channel):
        self.send("ACTION " + message, channel)

    def join(self, channel):
        self.send_raw("JOIN " + channel)

    def authenticate_nickserv(self, password):
        self.send("IDENTIFY " + password, "NICKSERV")

    def set_mode(self, nickname, mode):
        self.send_raw("MODE " + nickname + " " + mode)

    def recieve_raw(self):
        return self.irc_ssl.recv(4096).decode("UTF8")

    def recieve(self):
        raw = self.recieve_raw()

        print(raw)

        if raw.split()[0] == "PING":
            bot.send_raw("PONG " + raw.split()[1][1:])

        sender = raw.split()[0][1:]
        command = raw.split(" ", 1)[1]

        return IRC_Data(sender, command)

class IRC_Server(object):
    def __init__(self, address, port):
        self.address = address
        self.port = port

    def toString(self):
        return self.address + ":" + self.port

class IRC_Data(object):
    def __init__(self, sender, command):
        self.sender = IRC_Entity(sender)
        self.command = IRC_Command(command)

class IRC_Command(object):
    def __init__(self, input):

        if input[:4] == "JOIN":
            self.type = IRC_CommandType.Join
            self.channel = input[6:]

        elif input[:4] == "MODE":
            self.type = IRC_CommandType.Mode
            #print(input)
            self.nickname = input.split()[1]
            self.mode = input.split()[2]

        elif input[:7] == "PRIVMSG" and not input.split(":")[1][:6] == "ACTION":
            self.type = IRC_CommandType.Message
            self.channel = input.split()[1]
            self.message = input.split(":", 1)[1]

        elif input[:7] == "PRIVMSG" and input.split(":")[1][:7] == "ACTION":
            self.type = IRC_CommandType.Action
            self.message = input.split(":", 1)[1][6:]

        elif input [:7] == "INVITE":
            self.type = IRC_CommandType.Invite
            self.nickname = input.split()[1]
            self.channel = input.split(":", 1)[1]

        elif input[:6] == "NOTICE":
            self.type = IRC_CommandType.Notice
            self.notice_string = input.split()[1]
            self.message = input.split(":", 1)[1]

        elif input.split()[1] == "NICK":
            self.type = IRC_CommandType.Nick
            self.nickname = input.split()[1]

        else:
            self.type = IRC_CommandType.Unknown


class IRC_CommandType(Enum):
    Unknown = 0
    Join    = 1
    Mode    = 2
    Message = 3
    Action  = 4
    Invite  = 5
    Notice  = 6
    Nick    = 7


class IRC_Entity(object):
    def __init__(self, input):
        if "!" in input and "@" in input:
            self.type = IRC_EntityType.Client
            self.entity = IRC_User(input)
        else:
            self.type = IRC_EntityType.Server
            self.entity = input

class IRC_EntityType(Enum):
    Server = 0
    Client = 1

class IRC_User(object):
    def __init__(self, input):
        self.nickname = input.split("!")[0]
        self.username = input.split("!")[1].split("@")[0]
        self.host     = input.split("@")[1]

    def toString(self):
        return self.nickname + "!" + self.username + "@" + self.host


class FirstPingThread(Thread):
    def run(self):
        pingis = bot.irc_ssl.recv(9000).decode("UTF-8")
        pingis = bot.irc_ssl.recv(9000).decode("UTF-8")
        if pingis.split()[0] == "PING":
            bot.send_raw("PONG " + pingis.split()[1][1:])


#############################################################################################################
#############################################################################################################


#Connection Info
#TODO: load from config file. if non-existent, take user input.

irc_server        =  "irc.anonops.com"
irc_port          =   6697
irc_nickname      =  "wtfboom"
irc_nickserv_pwd  =  "fy8tgheuty"         #TODO: DO NOT STORE THE PASSWORD HERE, CHANGE IT
irc_channels      =  ["#bottest"]

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

bot = IRC_Client(irc_nickname)
server = IRC_Server(irc_server, irc_port)

printEx("Connecting to IRC server: " + irc_server + ":" + str(irc_port), PrintType.Info)
try:
    bot.connect(server)
except Exception as e:
    printEx("Failed to connect. Stacktrace: " + str(e), PrintType.Error)
    exit()

printEx("Connection successful.", PrintType.Info)

FirstPingThread().start()

#Wait a bit
time.sleep(2)

#Connected, authenticate
printEx("Sending credentials for " + irc_nickname, PrintType.Info)

bot.authenticate_nickserv(irc_nickserv_pwd)
bot.set_mode(bot.nickname, "+B")

printEx("Credentials sent. Waiting for authentication...", PrintType.Info)

#Wait a bit more
time.sleep(7)

#Join channels
for channel in irc_channels:
    bot.join(channel)


#############################################################################################################
#############################################################################################################

'''
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
'''

#Main Loop
while True:

    data = bot.recieve()

    if data.sender.type == IRC_EntityType.Client and data.command.type == IRC_CommandType.Message:

        #Treats multiple args in quotes as a single arg
        args = []
        args_temp = data.command.message.split()

        arg_index = 0

        while arg_index <= len(args_temp) - 1:

            arg = args_temp[arg_index]
            if arg[:1] == "\"":

                if arg[-1:] == "\"":

                    arg_temp = arg[1:-1]
                    arg_index += 1

                else:

                    arg_temp = arg[arg_index][:1]
                    arg_index += 1

                    for arg2 in args_temp[arg_index:]:
                        if arg2[1:] == "\"":
                            arg_temp += " " + arg2[:-1]
                        else:
                            arg_temp += " " + arg2

                        arg_index += 1

            else:
                arg_temp = arg

            args.append(arg_temp)
            arg_index += 1


        print(args)

    '''
    data = bot.recieve()

    if data.message[:len(command_character)] == command_character:

        argsTemp = data.message[len(command_character):].split(' ')
        args = []

        arg_index = 0
        for arg in argsTemp:
            if arg[:1] == "\"":
                args_to_merge = args_to_merge
                #for arg2 in argsTemp[arg_index:]:

            arg_index += 1

        #TODO: Handle multiple arguments in quotes as one argument
        args = argsTemp

        cmd = args[0].lower()



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
    '''