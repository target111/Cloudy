version = "2.0"

import socket
import ssl
import time
import random
from threading import Thread
from enum import Enum
import os
import sys
from os import walk

from pyfiglet import Figlet
import markovify

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
        self.irc_ssl.settimeout(timeout)

        self.send_raw("NICK " + self.nickname)
        self.send_raw("USER " + self.nickname + " 0 * :HIIMFUN")

    def send_raw(self, message):
        self.irc_ssl.send((message + "\r\n").encode("UTF-8"))

    def send(self, message, channel):
        self.send_raw("PRIVMSG " + channel + " :" + message)

    def notice(self, message, nickname):
        self.send_raw("NOTICE " + nickname + " :" + message)

    def action(self, message, channel):
        self.send("ACTION " + message, channel)

    def join(self, channel):
        self.send_raw("JOIN " + channel)

    def exit(self):
        self.send_raw("QUIT")

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
            self.nickname = input.split()[1]
            self.mode = input.split()[2]

        elif input[:7] == "PRIVMSG" and not input.split(":")[1][:6] == "ACTION":
            self.type = IRC_CommandType.Message
            self.channel = input.split()[1]
            self.message = input.split(":", 1)[1]

        elif input[:7] == "PRIVMSG" and input.split(":")[1][:7] == "ACTION":
            self.type = IRC_CommandType.Action
            self.message = input.split(":", 1)[1][6:]

        elif input[:7] == "INVITE":
            self.type = IRC_CommandType.Invite
            self.nickname = input.split()[1]
            self.channel = input.split(":", 1)[1]

        elif input[:6] == "NOTICE":
            self.type = IRC_CommandType.Notice
            self.notice_string = input.split()[1]
            self.message = input.split(":", 1)[1]

        elif input.split()[0] == "NICK":
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
irc_nickserv_pwd  =  "ushallnotpass"      #TODO: DO NOT STORE THE PASSWORD HERE, CHANGE IT
irc_channels      =  ["#spam", "#bots"]

timeout = 130
command_character = "="

file_quotes = "quotes.txt"
file_quotes_buffer = "quotes_buffer.txt"

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
bot.set_mode(bot.nickname, "+B")

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

        if self in poll_threads:
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
            if arg[:1] == '"' or arg == '"':

                if arg[-1:] == '"' and arg != '"':

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
                bot.send("Version: " + version, data.command.channel)


            if cmd == "die":
                if data.sender.entity.nickname not in bot_owner:
                    bot.send(prompt_priviledge_required, data.command.channel)
                else:
                    bot.send("oh...okay. :'(", data.command.channel)
                    bot.exit()
                    exit()


            if cmd == "restart":
                if data.sender.entity.nickname not in bot_owner:
                    bot.send(prompt_priviledge_required, data.command.channel)
                else:
                    bot.send("sure...", data.command.channel)
                    os.execv(sys.executable, ["python3"] + sys.argv)
                    bot.exit()
                    exit()


            if cmd == "spam":
                try:
                    times = int(args[1])
                    word = " ".join(args[2:]).upper()
                    # TODO: set configuarble limit
                    spam_limit = 100
                    if times > spam_limit:
                        bot.send("Don't abuse meh! Use a number smaller than " + str(spam_limit), data.command.channel)
                    else:
                        start_new_thread = True
                        for thread in spam_threads:
                            if thread.channel == data.command.channel:
                                start_new_thread = False
                                break
                        if start_new_thread:
                            SpamThread(data.command.channel, word, times).start()
                except:
                    bot.send("Use " + command_character + "spam <times> <message>", data.command.channel)


            if cmd == "quote":
                try:
                    if args[1].lower() == "add":
                        if data.sender.entity.nickname not in bot_owner:
                            open(file_quotes_buffer, "a").write(" ".join(args[2:]) + "\n")
                            bot.send("Quote will be added to the main list once an admin approves it.", data.command.channel)
                        else:
                            open(file_quotes, "a").write(" ".join(args[2:]) + "\n")
                            bot.send("Quote added! Also cocks.", data.command.channel)

                    elif args[1].lower() == "count":
                        with open(file_quotes) as f:
                            x = None
                            for i, l in enumerate(f):
                                pass
                                x = i
                            bot.send("I have " + str(x) + " quotes.", data.command.channel)

                    elif args[1].lower() == "read":
                        f = open(file_quotes, "r").readlines()
                        bot.send("Quote #" + args[2] + ": " + f[int(args[2])] + '"', data.command.channel)

                    elif args[1].lower() == "approve":
                        if data.sender.entity.nickname not in bot_owner:
                            bot.send(prompt_priviledge_required, data.command.channel)
                        else:
                            try:
                                if args[2].lower() == "all":
                                    f = open(file_quotes_buffer, "r").readlines()
                                    open(file_quotes_buffer, "w").close()
                                    for i in f:
                                        open(file_quotes, "a").write(str(i))
                                        bot.send("All quotes approved!", data.command.channel)
                                elif args[2].lower() == "show":
                                    f = open(file_quotes_buffer, "r").readlines()
                                    quotenumber = -1
                                    for i in f:
                                        i = i.split('\n')[0]
                                        quotenumber += 1
                                        bot.send("Quote #" + str(quotenumber) + ": " + i, data.command.channel)
                                else:
                                    try:
                                        f = open(file_quotes_buffer, "r").readlines()
                                        open(file_quotes, "a").write(f[int(args[2])])
                                        quote = f[int(args[2])]
                                        bot.send("Approved quote " + args[2] + " - " + quote.split("\n")[0], data.command.channel)
                                        os.system("sed '%rd' %r > quotes_buffer_temp; mv quotes_buffer_temp %r" % (args[2], file_quotes_buffer, file_quotes_buffer))
                                    except Exception as e:
                                        bot.send("Use " + command_character + "quote approve <number>", data.command.channel)
                            except:
                                bot.send("Use " + command_character + "quote approve all/show/<number_to_approve>", data.command.channel)
                except:
                    bot.send("Use " + command_character + "quote read/add/count", data.command.channel)


            if cmd == "ascii":
                try:
                    figlet = Figlet(args[1])
                    render = figlet.renderText(args[2]).split('\n')
                    for ascii in render:
                        bot.send(Color(ascii, random.choice(IRCColors.all_colors)), data.command.channel)
                except Exception as e:
                    print(e)
                    bot.send("Use " + command_character + "ascii <font> <text>. For a list of fonts visit https://pastebin.com/TvwCcNUd ",data.command.channel)


            if cmd == "memetic":
                text = open(file_quotes, "r").read()
                text_model = markovify.Text(text)
                try:
                    output = text_model.make_short_sentence(10000)
                    bot.send('"' + output + '"', data.command.channel)
                except:
                    bot.send("Whoops! COCKS!", data.command.channel)


            if cmd == "art":
                try:
                    if args[1].lower() == "draw":
                        start_new_thread = True
                        for thread in art_threads:
                            if thread.channel == data.command.channel:
                                start_new_thread = False
                                break
                        if start_new_thread:
                            try:
                                if len(args) == 3:
                                    file = args[2].replace(".", "") + ".txt"
                                else:
                                    files = []
                                    for (dirpath, dirnames, filenames) in walk("art"):
                                        files.extend(filenames)
                                        break
                                    file = random.choice(files)

                                ArtThread(data.command.channel, open("art/" + file, "r").read()).start()
                            except:
                                bot.send("Whoops! COCKS!", data.command.channel)
                    elif args[1].lower() == "list":
                        files = []
                        for (dirpath, dirnames, filenames) in walk("art"):
                            files.extend(filenames)
                            break

                        art_list = []
                        for file in files:
                            art_list.append(".".join(file.split(".")[:-1]))

                        bot.send("Art List: " + ", ".join(art_list), data.command.channel)
                    else:
                        bot.send("Use " + command_character + "art list/draw <optional:name>.", data.command.channel)
                except:
                    bot.send("Use " + command_character + "art list/draw <optional:name>.", data.command.channel)


            if cmd == "poll":
                try:
                    if args[1].lower() == "new":
                        start_new_thread = True
                        for thread in poll_threads:
                            if thread.channel == data.command.channel:
                                start_new_thread = False
                                break
                        if start_new_thread:
                            try:
                                options = []
                                for option in args[3:]:
                                    options.append(PollOption(option))
                                if options == []:
                                    bot.send('No options specified. Please use "' + command_character + 'help poll" for more info.', data.command.channel)
                                else:
                                    PollThread(data.sender.entity.nickname, data.command.channel, args[2], options).start()
                            except:
                                bot.send("Whoops! COCKS!", data.command.channel)
                    elif args[1] == "vote":
                        vote_valid = True
                        vote_thread = None
                        vote_option = None
                        for thread in poll_threads:
                            if thread.channel == data.command.channel:
                                vote_thread = thread
                                for option in thread.options:
                                    if data.sender.entity.nickname in option.votes:
                                        vote_valid = False
                                    if args[2] == option.description:
                                        vote_option = option
                            break
                        if vote_thread == None:
                            bot.send("There are no polls running.", data.command.channel)
                        else :
                            if vote_valid:
                                if vote_option == None:
                                    bot.send('No suck option: "' + args[2] + '"', data.command.channel)
                                else:
                                    #Actually add the vote
                                    vote_option.votes.append(data.sender.entity.nickname)
                            else:
                                bot.send("Sorry " + data.sender.entity.nickname + ", you already voted.", data.command.channel)
                    elif args[1] == "end":
                        thread_to_end = None
                        for thread in poll_threads:
                            if thread.channel == data.command.channel:
                                thread_to_end = thread
                                break
                        if thread_to_end == None:
                            bot.send("There are no polls running.", data.command.channel)
                        else:
                            if thread_to_end.nickname == data.sender.entity.nickname or data.sender.entity.nickname in bot_owner:
                                thread_to_end.end()
                            else:
                                bot.send("You did not create that poll, GTFO. ", data.command.channel)
                except:
                    bot.send("Whoops! COCKS!", data.command.channel)


            if cmd == "help":
                commands = ["spam", "ascii", "quote", "art", "version", "memetic", "poll"]
                op_commands = commands + ["die", "restart"]

                help_spam    = "spam <times> <text> - Floods the channel with text."
                help_quote   = "quote <add/count/read> - Inspirational quotes by 4chan."
                help_art     = "art list/draw <optional:name> - Draw like picasso!"
                help_ascii   = "ascii <font> <text> - Transform text into ascii art made of... text... Font list: https://pastebin.com/TvwCcNUd"
                help_version = "version - Prints bot version"
                help_memetic = "memetic - Generates a quote using ARTIFICIAL INTELLIGENCE!!!"
                help_poll    = "poll new <description> <option1> <option2> ... / vote <option> / end - DEMOCRACY, BITCH!"

                help_die     = "die - [Admins Only] Rapes the bot, murders it, does funny things to its corpse, and disposes of it."
                help_restart = "restart - [Admins Only] Did you try turning it Off and On again?"

                if len(args) == 1:
                    if data.sender.entity.nickname in bot_owner:
                        bot.send("Available commands: " + ", ".join(op_commands), data.command.channel)
                    else:
                        bot.send("Available commands: " + ", ".join(commands), data.command.channel)
                    bot.send("Use " + command_character + "help <command> for more detailed info.", data.command.channel)
                else:
                    try:
                        #TODO: Rename that variable to something less ridiculous
                        help_me = args[1].lower()
                        help_output = 'Unknown command "' + args[1] + '". Please use "' + command_character + 'help" for a list of available commands.'

                        if help_me == "spam":
                            help_output = help_spam
                        elif help_me == "quote":
                            help_output = help_quote
                        elif help_me == "art":
                            help_output = help_art
                        elif help_me == "ascii":
                            help_output = help_ascii
                        elif help_me == "version":
                            help_output = help_version
                        elif help_me == "memetic":
                            help_output = help_memetic
                        elif help_me == "die":
                            help_output = help_die
                        elif help_me == "restart":
                            help_output = help_restart
                        elif help_me == "poll":
                            help_output = help_poll

                        help_output = data.sender.entity.nickname + ", " + command_character + help_output
                        bot.send(help_output, data.command.channel)
                    except:
                        bot.send("Whoops! COCKS!", data.command.channel)
