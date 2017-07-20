version = "2.2"

import socket
import ssl
import time
import random
from threading import Thread
from enum import Enum
import os
import sys
from os import walk
import feedparser

from pyfiglet import Figlet
import markovify

#############################################################################################################
#############################################################################################################

#Connection Info
#TODO: load from config file. if non-existent, take user input.

irc_server        =  "irc.anonops.com"
irc_port          =   6697
irc_nickname      =  "wtfboom"
irc_nickserv_pwd  =  "ushallnotpass"      #TODO: DO NOT STORE THE PASSWORD HERE, CHANGE IT
irc_channels      =  ["#spam","#bots"]

command_character = "="

file_quotes = "quotes.txt"
file_quotes_buffer = "quotes_buffer.txt"

prompt_priviledge_required = "This command requires sudo access, kid."
identify_required = "IDENTIFY YOURSELF!"

allheadlines = []

printed_headlines = []

newsurls = {
    '4chan Literature Board': 'https://boards.4chan.org/lit/index.rss',
    '4chan History Board': 'https://boards.4chan.org/his/index.rss',
    '4chan Cooking Board': 'http://boards.4chan.org/ck/index.rss',
    '4chan Music Board': 'http://boards.4chan.org/mu/index.rss',
    '4chan Math and Science Board': 'http://boards.4chan.org/sci/index.rss',
    '4chan Technology Board': 'http://boards.4chan.org/g/index.rss',
    '4chan Television and Film Board': 'http://boards.4chan.org/tv/index.rss',
    '4chan Question and Answer Board': 'http://boards.4chan.org/qa/index.rss',
    '4chan Trash Board': 'http://boards.4chan.org/trash/',
    '4chan International Board': 'http://boards.4chan.org/int/index.rss',
    'Reddit r/art': 'http://reddit.com/r/Art/.rss',
    'Reddit r/AskReddit':  'http://reddit.com/r/AskReddit/.rss',
    'Rediit r/aww': 'http://reddit.com/r/aww/.rss',
    'Reddit r/funny': 'http://reddit.com/r/funny/.rss',
    'Reddit r/gifs': 'http://reddit.com/r/gifs/.rss',
    'Reddit r/Jokes': 'http://reddit.com/r/Jokes/.rss',
    'Reddit r/quotes': 'http://reddit.com/r/Quotes/.rss',






}

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
        self.irc_ssl.setblocking(True)

        self.send_raw("NICK " + self.nickname)
        self.send_raw("USER " + self.nickname + " 0 * :HIIMFUN")

    def send_raw(self, message):
        if not message == "":
            self.irc_ssl.send((message + "\r\n").encode("UTF-8"))

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

    def authenticate_nickserv(self, password):
        self.send("IDENTIFY " + password, "NICKSERV")

    def set_mode(self, nickname, mode):
        self.send_raw("MODE " + nickname + " +" + mode)

    def recieve_raw(self):
        return self.irc_ssl.recv(4096).decode("UTF-8","ignore")

    def status(self, nick):
        self.send_raw("PRIVMSG NICKSERV STATUS " + nick)
        global user_data
        user_data = self.recieve()

    def recieve(self):
        raw = self.recieve_raw()
        print(raw)

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

        if input[:1] == ":":

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

            try:
                if input.split()[0] == "PING":
                    self.type_command = IRC_CommandType.Ping
                    self.data = input.split()[1]
            except:
                pass


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


class FirstPingThread(Thread):
    def run(self):
        pingis = bot.irc_ssl.recv(9000).decode()
        pingis = bot.irc_ssl.recv(9000).decode()
        if pingis.split()[0] == "PING":
            bot.send_raw("PONG " + pingis.split()[1][1:])


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

try:
    f = open("admins.txt", "r")

except:
    printEx("No admins file found!", PrintType.Warning)
    printEx("Creating one for you..", PrintType.Info)
    f = open("admins.txt", "a")
    admins=input("Enter your irc nickname: ")
    f.write(admins+"\n")
    f.close()
    f = open("admins.txt", "r")

lines = f.read()
bot_owner = []
for admin in lines.split("\n"):
    bot_owner.append(admin)
f.close()
del bot_owner[-1]

time.sleep(2)

printEx("Connecting to IRC server: " + irc_server + ":" + str(irc_port), PrintType.Info)
try:
    bot.connect(server)
except Exception as e:
    printEx("Failed to connect. Stacktrace: " + str(e), PrintType.Error)
    exit()

printEx("Connection successful.", PrintType.Info)

FirstPingThread().start()

#Wait a bit
time.sleep(3)

#Connected, authenticate
printEx("Sending credentials for " + irc_nickname, PrintType.Info)

bot.authenticate_nickserv(irc_nickserv_pwd)
bot.set_mode(bot.nickname, IRC_Mode.Bot)

printEx("Credentials sent. Waiting for authentication...", PrintType.Info)

#Wait a bit more
time.sleep(7)

#Join channels
for channel in irc_channels:
    bot.join(channel)


#############################################################################################################
#############################################################################################################


spam_threads = []

class SpamThread(Thread):
    def __init__(self, channel, message, times):
        Thread.__init__(self)
        self.channel = channel
        self.message = message
        self.times = times

    def run(self):
        spam_threads.append(self)

        for i in range(times): #
            fg = random.choice(IRCColors.all_colors)
            bg = random.choice(IRCColors.all_colors)
            while fg == bg:
                bg = random.choice(IRCColors.all_colors)
            bot.send(Format(Color(self.message + " | ", fg, bg), [IRCFormat.Bold]).upper() * 40, self.channel)
            time.sleep(1)

        spam_threads.remove(self)

feedparse_threads = []

class feedparse(Thread):
    def __init__(self, nickname, channel):
        Thread.__init__(self)
        self.channel  = channel
        self.nickname = nickname

    def getHeadlines(rss_url):
        headlines = []
        feed = feedparser.parse(rss_url)
        for newsitem in feed['items']:
            headlines.append(newsitem['title'] + ' || ' + newsitem['link'])
        return headlines

    def run(self):
        feedparse_threads.append(self)
        while RUNNING:
            for key,url in newsurls.items():
                if newsurls.items() not in allheadlines:
                    allheadlines.extend(feedparse.getHeadlines(url))
                    if allheadlines[len(allheadlines) - 1] not in printed_headlines:
                        bot.send((allheadlines[len(allheadlines) - 1]), self.channel)
                        printed_headlines.append(allheadlines[len(allheadlines) - 1])
                time.sleep(4)

        bot.send("Done!", self.channel)
        feedparse_threads.remove(self)

art_threads = []

class ArtThread(Thread):
    def __init__(self, channel, message):
        Thread.__init__(self)
        self.channel = channel
        self.message = message

    def run(self):
        art_threads.append(self)

        for line in self.message.split("\n"):
            bot.send(Color(line, random.choice(IRCColors.all_colors)), self.channel)
            time.sleep(0.5)

        art_threads.remove(self)

poll_threads = []

class PollThread(Thread):
    def __init__(self, nickname, channel, description, options):
        Thread.__init__(self)
        self.nickname = nickname
        self.channel = channel
        self.description = description
        self.options = options

    def run(self):
        self.time_started = time.time()
        poll_threads.append(self)

        bot.send('Poll started: "' + self.description + '". Vote using =poll vote <option>. Poll ends in 5 minutes!', self.channel)

        while time.time() - self.time_started < 300:
            time.sleep(0.1)
            if self not in poll_threads:
                break

        if self not in poll_threads:
            self.end()

    def end(self):
        bot.send("Poll ended. Results:", self.channel)
        for option in self.options:
            bot.send('"' + option.description + '": ' + str(len(option.votes)) + " votes.", self.channel)
            time.sleep(0.5)
        poll_threads.remove(self)

class PollOption(object):
    def __init__(self, description):
        self.description = description
        self.votes = []


class HelpData(object):
    def __init__(self, command, admin_only, description):
        self.command = command
        self.admin_only = admin_only
        self.description = description


#Main Loop
while True:

    data = bot.recieve()

    #Respond to pings
    if data.type_command == IRC_CommandType.Ping:
        bot.send_raw("PONG " + data.data)

    if data.sender_type == IRC_SenderType.Client and data.type_command == IRC_CommandType.Message:

        #Treats multiple args in quotes as a single arg
        args = []
        args_temp = data.message.split()

        arg_index = 0
        while arg_index <= len(args_temp) - 1:

            arg = args_temp[arg_index]
            if arg[:1] == '"' or arg == '"':

                if arg[-1:] == '"' and not arg == '"':

                    arg_temp = arg[1:-1]
                    arg_index += 1

                else:

                    arg_temp = arg[1:]
                    arg_index += 1

                    for arg2 in args_temp[arg_index:]:
                        if arg2[-1:] == '"' or arg2 == '"':
                            arg_temp += " " + arg2[:-1]
                            arg_index += 1
                            break
                        else:
                            arg_temp += " " + arg2
                            arg_index += 1

            else:
                arg_temp = arg
                arg_index += 1

            args.append(arg_temp)


        print(args)


        if args[0][:len(command_character)] == command_character:
            cmd = args[0][1:].lower()


            if cmd == "version":
                bot.send("Version: " + version  + " - GitHub: https://github.com/OverclockedSanic/SpamBot", data.channel)


            if cmd == "die":
                if data.sender.nickname not in bot_owner:
                    bot.send(prompt_priviledge_required, data.channel)
                else:
                    bot.status(data.sender.nickname)
                    if user_data.data != None and user_data.data == 3:
                        bot.send("oh...okay. :'(", data.channel)
                        bot.exit()
                        exit()
                    else:
                        bot.send(identify_required, data.channel)


            if cmd == "restart":
                if data.sender.nickname not in bot_owner:
                    bot.send(prompt_priviledge_required, data.channel)
                else:
                    bot.status(data.sender.nickname)
                    if user_data.data != None and user_data.data == 3:
                        bot.send("sure...", data.channel)
                        os.execv(sys.executable, ["python3"] + sys.argv)
                        bot.exit()
                        exit()
                    else:
                        bot.send(identify_required, data.channel)

            if cmd == "msg" and data.sender.nickname in bot_owner and data.channel == irc_nickname:
                if data.sender.nickname not in bot_owner:
                    bot.send(prompt_priviledge_required, data.sender.nickname)
                else:
                    bot.status(data.sender.nickname)
                    if user_data.data != None and user_data.data == 3:
                        try:
                            if args[1] in irc_channels:
                                bot.send(" ".join(args[2:]),args[1])
                            else:
                                bot.send("Not allowed", data.sender.nickname)
                        except:
                            bot.send("Use "+command_character+"msg <channel> <message>", data.sender.nickname)
                    else:
                        bot.send(identify_required, data.sender.nickname)

            if cmd == "part" and data.sender.nickname in bot_owner and data.channel == irc_nickname:
                if data.sender.nickname not in bot_owner:
                    bot.send(prompt_priviledge_required, data.sender.nickname)
                else:
                    bot.status(data.sender.nickname)
                    if user_data.data != None and user_data.data == 3:
                        try:
                            if args[1] in irc_channels:
                                bot.send_raw("PART "+args[1])
                            else:
                                bot.send("Not allowed", data.sender.nickname)
                        except:
                            bot.send("Use "+command_character+"part <channel>", data.sender.nickname)
                    else:
                        bot.send(identify_required, data.sender.nickname)

            if cmd == "join" and data.sender.nickname in bot_owner and data.channel == irc_nickname:
                if data.sender.nickname not in bot_owner:
                    bot.send(prompt_priviledge_required, data.sender.nickname)
                else:
                    bot.status(data.sender.nickname)
                    if user_data.data != None and user_data.data == 3:
                        try:
                            if args[1] in irc_channels:
                                bot.send_raw("JOIN "+args[1])
                            else:
                                bot.send("Not allowed!", data.sender.nickname)
                        except:
                            bot.send("Use "+command_character+"join <channel>", data.sender.nickname)
                    else:
                        bot.send(identify_required, data.sender.nickname)

            if cmd == "mode" and data.sender.nickname in bot_owner and data.channel == irc_nickname:
                if data.sender.nickname not in bot_owner:
                    bot.send(prompt_priviledge_required, data.sender.nickname)
                else:
                    bot.status(data.sender.nickname)
                    if user_data.data != None and user_data.data == 3:
                        try:
                            bot.send_raw("MODE " + irc_nickname + " " +args[1])
                        except:
                            bot.send("Use "+command_character+"mode <mode>")
                    else:
                        bot.send(identify_required, data.sender.nickname)

            if cmd == "spam":
                try:
                    times = int(args[1])
                    word = " ".join(args[2:]).upper()
                    # TODO: set configuarble limit
                    spam_limit = 100
                    if times > spam_limit:
                        bot.send("Don't abuse meh! Use a number smaller than " + str(spam_limit), data.channel)
                    else:
                        start_new_thread = True
                        for thread in spam_threads:
                            if thread.channel == data.channel:
                                start_new_thread = False
                                break
                        if start_new_thread:
                            SpamThread(data.channel, word, times).start()
                except:
                    bot.send("Use " + command_character + "spam <times> <message>", data.channel)


            if cmd == "admin":
                if args[1].lower() == "list":
                    if data.sender.nickname not in bot_owner:
                        bot.send(prompt_priviledge_required, data.channel)
                    else:
                        bot.status(data.sender.nickname)
                        if user_data.data != None and user_data.data == 3:
                            bot.send("Admins are: " + str(", ".join(bot_owner)), data.channel)
                        else:
                            bot.send(identify_required, data.channel)

                elif args[1].lower() == "remove":
                    if data.sender.nickname not in bot_owner:
                        bot.send(prompt_priviledge_required, data.channel)

                    else:
                        bot.status(data.sender.nickname)
                        if user_data.data != None and user_data.data == 3:
                            if args[2] in bot_owner:
                                f = open("admins.txt", "r")
                                lines = f.readlines()
                                f.close()
                                f = open("admins.txt", "w")
                                for line in lines:
                                    if line != args[2] + "\n":
                                        f.write(line)
                                bot_owner.remove(args[2])
                            else:
                                bot.send("Admin doesn't exist!", data.channel)
                        else:
                            bot.send(identify_required, data.channel)

                elif args[1].lower() == "add":
                    if data.sender.nickname not in bot_owner:
                        bot.send(prompt_priviledge_required, data.channel)

                    else:
                        bot.status(data.sender.nickname)
                        if user_data.data != None and user_data.data == 3:
                            f = open("admins.txt", "a")
                            f.write(args[2]+"\n")
                            f.close()
                            bot_owner.append(args[2])
                        else:
                            bot.send(identify_required, data.channel)
                else:
                    bot.send("Unknown option. Please use "+command_character+"help "+cmd, data.channel)


            if cmd == "quote":
                try:
                    if args[1].lower() == "add":
                        if data.sender.nickname not in bot_owner:
                            open(file_quotes_buffer, "a").write(" ".join(args[2:]) + "\n")
                            bot.send("Quote will be added to the main list once an admin approves it.", data.channel)
                        else:
                            bot.status(data.sender.nickname)
                            if user_data.data != None and user_data.data == 3:
                                open(file_quotes, "a").write(" ".join(args[2:]) + "\n")
                                bot.send("Quote added! Also cocks.", data.channel)
                            else:
                                bot.send(identify_required, data.channel)


                    elif args[1].lower() == "count":
                        with open(file_quotes) as f:
                            x = None
                            for i, l in enumerate(f):
                                pass
                                x = i
                            bot.send("I have " + str(x) + " quotes.", data.channel)

                    elif args[1].lower() == "read":
                        f = open(file_quotes, "r").readlines()
                        try:
                            bot.send("Quote #" + args[2] + ": " + f[int(args[2])] + '"', data.channel)
                        except:
                            bot.send("I only have " + str(len(f) - 1) + " quotes!", data.channel)

                    elif args[1].lower() == "approve":
                        if data.sender.nickname not in bot_owner:
                            bot.send(prompt_priviledge_required, data.channel)
                        else:
                            bot.status(data.sender.nickname)
                            if user_data.data != None and user_data.data == 3:
                                try:
                                    if args[2].lower() == "all":
                                        f = open(file_quotes_buffer, "r").readlines()
                                        open(file_quotes_buffer, "w").close()
                                        for i in f:
                                            open(file_quotes, "a").write(str(i))
                                        bot.send("All quotes approved!", data.channel)
                                    elif args[2].lower() == "show":
                                        f = open(file_quotes_buffer, "r").readlines()
                                        quotenumber = -1
                                        for i in f:
                                            i = i.split('\n')[0]
                                            quotenumber += 1
                                        bot.send("Quote #" + str(quotenumber) + ": " + i, data.channel)
                                    else:
                                        try:
                                            f = open(file_quotes_buffer, "r").readlines()
                                            open(file_quotes, "a").write(f[int(args[2])])
                                            quote = f[int(args[2])]
                                            bot.send("Approved quote " + args[2] + " - " + quote.split("\n")[0], data.channel)
                                        except Exception as e:
                                            bot.send("Use " + command_character + "quote approve <number>", data.channel)
                                except:
                                    bot.send("Use " + command_character + "quote approve all/show/<number_to_approve>", data.channel)
                            else:
                                bot.send(identify_required, data.channel)

                except:
                    bot.send("Use " + command_character + "quote read/add/count", data.channel)


            if cmd == "ascii":
                try:
                    figlet = Figlet(args[1])
                    render = figlet.renderText(args[2]).split('\n')
                    for ascii in render:
                        bot.send(Color(ascii, random.choice(IRCColors.all_colors)), data.channel)
                except Exception as e:
                    print(e)
                    bot.send("Use " + command_character + "ascii <font> <text>. For a list of fonts visit https://pastebin.com/TvwCcNUd ",data.channel)


            if cmd == "memetic":
                text = open(file_quotes, "r").read()
                text_model = markovify.Text(text)
                try:
                    output = text_model.make_short_sentence(10000)
                    bot.send('"' + output + '"', data.channel)
                except:
                    bot.send("Whoops! COCKS!", data.channel)


            if cmd == "feed":
                try:
                    if args[1].lower() == "on":
                        if data.sender.nickname not in bot_owner:
                            bot.send(prompt_priviledge_required, data.channel)
                        else:
                            bot.status(data.sender.nickname)
                            if user_data.data != None and user_data.data == 3:
                                start_new_thread = True
                                for thread in feedparse_threads:
                                    if thread.channel == data.channel:
                                        bot.send("Already running!", data.channel)
                                        start_new_thread = False
                                        break
                                if start_new_thread:
                                    RUNNING=True
                                    feedparse(data.sender.nickname, data.channel).start()
                                    print(feedparse_threads)
                            else:
                                bot.send(identify_required, data.channel)

                    elif args[1].lower() == "off":
                        thread_to_end = None
                        for thread in feedparse_threads:
                            if thread.channel == data.channel:
                                thread_to_end = thread
                                break
                        if thread_to_end == None:
                            bot.send("Feed is not running.", data.channel)
                        else:
                            if data.sender.nickname in bot_owner:
                                bot.status(data.sender.nickname)
                                if user_data.data != None and user_data.data == 3:
                                    bot.send("Stoping..", data.channel)
                                    RUNNING=False
                                else:
                                    bot.send(identify_required, data.channel)
                            else:
                                bot.send(prompt_priviledge_required, data.channel)

                except Exception as e:
                    print(e)


            if cmd == "art":
                try:
                    if args[1].lower() == "draw":
                        start_new_thread = True
                        for thread in art_threads:
                            if thread.channel == data.channel:
                                start_new_thread = False
                                break
                        if start_new_thread:
                            try:
                                file = None
                                files = []
                                for (dirpath, dirnames, filenames) in walk("art"):
                                    files.extend(filenames)
                                    break

                                if len(args) >= 3:
                                    #Local File Injection Fix
                                    file_temp = " ".join(args[2:]) + ".txt"
                                    if file_temp in files:
                                        file = file_temp
                                    else:
                                        bot.send("Whoops! COCKS!", data.channel)
                                else:
                                    file = random.choice(files)

                                if not file == None:
                                    ArtThread(data.channel, open("art/" + file, "r").read()).start()
                            except:
                                bot.send("Whoops! COCKS!", data.channel)
                    elif args[1].lower() == "list":
                        files = []
                        for (dirpath, dirnames, filenames) in walk("art"):
                            files.extend(filenames)
                            break

                        art_list = []
                        for file in files:
                            art_list.append(".".join(file.split(".")[:-1]))

                        bot.send("Art List: " + ", ".join(art_list), data.channel)
                    else:
                        bot.send("Use " + command_character + "art list/draw <optional:name>.", data.channel)
                except:
                    bot.send("Use " + command_character + "art list/draw <optional:name>.", data.channel)
            if cmd == "poll":
                try:
                    if args[1].lower() == "new":
                        bot.status(data.sender.nickname)
                        if user_data.data != None and user_data.data == 3:
                            start_new_thread = True
                            for thread in poll_threads:
                                if thread.channel == data.channel:
                                    start_new_thread = False
                                    break
                            if start_new_thread:
                                try:
                                    options = []
                                    for option in args[3:]:
                                        options.append(PollOption(option))
                                    if options == []:
                                        bot.send('No options specified. Please use "' + command_character + 'help poll" for more info.', data.channel)
                                    else:
                                        PollThread(data.sender.nickname, data.channel, args[2], options).start()
                                except:
                                    bot.send("Whoops! COCKS!", data.channel)
                        else:
                            bot.send(identify_required, data.channel)

                    elif args[1] == "vote":
                        vote_valid = True
                        vote_thread = None
                        vote_option = None
                        bot.status(data.sender.nickname)
                        for thread in poll_threads:
                            if thread.channel == data.channel:
                                vote_thread = thread
                                for option in thread.options:
                                    if user_data.data != None and user_data.data == 3:
                                        if data.sender.nickname in option.votes:
                                            vote_valid = False
                                    else:
                                        bot.send(identify_required, data.channel)

                                    if args[2] == option.description:
                                        vote_option = option
                            break
                        if vote_thread == None:
                            bot.send("There are no polls running.", data.channel)
                        else :
                            if vote_valid:
                                if vote_option == None:
                                    bot.send('No such option: "' + args[2] + '"', data.channel)
                                else:
                                    #Actually add the vote
                                    vote_option.votes.append(data.sender.nickname)
                            else:
                                bot.send("Sorry " + data.sender.nickname + ", you already voted.", data.channel)

                    elif args[1] == "end":
                        thread_to_end = None
                        for thread in poll_threads:
                            if thread.channel == data.channel:
                                thread_to_end = thread
                                break
                        if thread_to_end == None:
                            bot.send("There are no polls running.", data.channel)
                        else:
                            if thread_to_end.nickname == data.sender.nickname or data.sender.nickname in bot_owner:
                                bot.status(data.sender.nickname)
                                if user_data.data != None and user_data.data == 3:
                                    thread_to_end.end()
                                else:
                                    bot.send(identify_required, data.channel)

                            else:
                                bot.send("You did not create that poll, GTFO. ", data.channel)
                except:
                    bot.send("Whoops! COCKS!", data.channel)


            if cmd == "flipcoin":
                bot.send("Coin landed on: " + random.choice(["Heads", "Tails"]), data.channel)


            if cmd == "help":

                help_data = [         #Admin Only?
                    HelpData("spam",     False, "spam <times> <text> - Floods the channel with text."),
                    HelpData("quote",    False, "quote <add/count/read> - Inspirational quotes by 4chan."),
                    HelpData("art",      False, "art list/draw <optional:name> - Draw like picasso!"),
                    HelpData("ascii",    False, "ascii <font> <text> - Transform text into ascii art made of... text... Font list: https://pastebin.com/TvwCcNUd"),
                    HelpData("version",  False, "version - Prints bot version and GitHub link."),
                    HelpData("memetic",  False, "memetic - Generates a quote using ARTIFICIAL INTELLIGENCE!!!"),
                    HelpData("poll",     False, "poll new <description> <option1> <option2> ... / vote <option> / end - DEMOCRACY, BITCH!"),
                    HelpData("flipcoin", False, "flipcoin - Unlike Effy, it generates a random output!"),
                    HelpData("die",      True,  "die - [Admins Only] Rapes the bot, murders it, does funny things to its corpse, and disposes of it."),
                    HelpData("restart",  True,  "restart - [Admins Only] Did you try turning it Off and On again?"),
                    HelpData("feed",     True,  "feed - [Admins Only] on/off - rss feed system"),
                    HelpData("admin",    True,  "admin - [Admins Only] list/remove/add  - Manage list of admins")
                ]

                if len(args) == 1:
                    command_list = []

                    for command in help_data:
                        command_list.append(command.command)

                    bot.send("Available commands: " + ", ".join(command_list), data.channel)
                    bot.send("Use " + command_character + "help <command> for more detailed info.", data.channel)
                else:
                    command = " ".join(args[1:])

                    help_output = 'Unknown command "' + command + '". Please use "' + command_character + 'help" for a list of available commands.'

                    for help in help_data:
                        if help.command.lower() == command.lower():
                            help_output = help.command + " " + help.description
                            break

                    help_output = data.sender.nickname + ", " + command_character + help_output
                    bot.send(help_output, data.channel)
