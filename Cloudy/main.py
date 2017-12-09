version = "2.3"

import socket, ssl, time, random, os, sys, feedparser, markovify, pygeoip, wikipedia, shodan, string, datetime, requests, json, shelve
from threading import Thread
from enum import Enum
from os import walk
from pyfiglet import Figlet
from mtranslate import translate
from urllib.request import urlopen
from rivescript import RiveScript
#############################################################################################################
#############################################################################################################

try:

    with open('config.json') as config_file:
        config = json.load(config_file)

        irc_server        = config['irc_server']
        irc_port          = config['irc_port']
        irc_nickname      = config['irc_nickname']
        irc_nickserv_pwd  = config['irc_nickserv_pwd']
        irc_channels      = config['irc_channels']
        command_character = config['command_character']


except FileNotFoundError:

    print("No configuration file present.. Creating one for you :)\n")

    irc_server        = input("IRC server to connect to: ")
    irc_port          = input("port: ")
    irc_nickname      = input("nickname: ")
    irc_nickserv_pwd  = input("NickServ pwd (you can leave this blank): ")
    irc_channels      = input("List of channels to join (separated by a space. ex: #chan1 #chan2): ")
    command_character = input("Command character of the bot (if you leave this blank it will be '='): ")

    if len(command_character) == 0:
        command_character = '='

    config = {'irc_server':irc_server, 'irc_port':irc_port, 'irc_nickname':irc_nickname, 'irc_nickserv_pwd':irc_nickserv_pwd, 'command_character':command_character, 'irc_channels':irc_channels}

    with open('config.json', 'w') as config_file:
        json.dump(config, config_file)

try:

    f = open("admins.txt", "r").read()
    bot_owner = []

    for admin in f.split("\n"):
        bot_owner.append(admin)

    del(bot_owner[-1])

except Exception as e:

    print(e)

    print("No admins file found!\n")

    f = open("admins.txt", "w")
    bot_owner = []

    bot_owner.append(input("Enter your irc nickname: "))

    f.write(bot_owner[0]+"\n")
    f.close()

uptime = datetime.datetime.utcnow()

file_quotes = "quotes.txt"
file_quotes_buffer = "quotes_buffer.txt"
api_key=""
prompt_priviledge_required = "Sorry, I can't let you do that!"
identify_required = "IDENTIFY YOURSELF!"

allheadlines = []

printed_headlines = []

shelve_ = shelve.open("user_db")

try:
    with open('feed.json') as feed_file:
        newsurls = json.load(feed_file)
except:
    print("No feed file provided!")

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
server = IRC_Server(irc_server, int(irc_port))

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
for channel in irc_channels.split():
    bot.join(channel)


#############################################################################################################
#############################################################################################################

class PingThread(Thread):
    def __init__(self, input):
        Thread.__init__(self)
        self.input = input

    def run(self):
        bot.send_raw("PONG " + self.input)

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
            bot.send(Format(Color(self.message + " | ", fg, bg), [IRCFormat.Bold]).upper() * 35, self.channel)
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

        while True:

            if self not in feedparse_threads:
                break

            else:
                for key,url in newsurls.items():
                    if newsurls.items() not in allheadlines:
                        allheadlines.extend(feedparse.getHeadlines(url))
                        if allheadlines[len(allheadlines) - 1] not in printed_headlines:
                            if "Reddit" in key:
                                fg = IRCColors.Red
                                bot.send(Color(allheadlines[len(allheadlines) - 1], fg), self.channel)
                            elif "4chan" in key:
                                fg = IRCColors.Grey
                                bot.send(Color(allheadlines[len(allheadlines) - 1], fg), self.channel)

                            printed_headlines.append(allheadlines[len(allheadlines) - 1])
                    time.sleep(4)

        bot.send("Done!", self.channel)

    def end(self):
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

omgwords_threads = []

class OmgwordsThread(Thread):
    def __init__(self, player_num, players, channel):
        Thread.__init__(self)
        self.player_num = player_num
        self.channel    = channel
        self.players    = [players]

        self.solved     = False
        self.word       = []
        self.rounds     = 15

    def run(self):
        omgwords_threads.append(self)

        bot.send("Waiting for players.. join with '" + Format(command_character + "omgwords join", [IRCFormat.Bold]) + "'.", self.channel)

        while len(self.players) < self.player_num:
            pass

        bot.send("Starting.. play with '" + Format(command_character + "omgwords try <word>'", [IRCFormat.Bold]) + "'.", self.channel)

        round_   = 0
        solved_c = 0

        while True:
            if self not in omgwords_threads:
                break

            else:
                round_ += 1

                self.solved = False

                if round_ > self.rounds:
                    bot.send("Rounds finished! Solved " + Format(str(solved_c), [IRCFormat.Bold]) + " out of " + Format(str(self.rounds), [IRCFormat.Bold]) + ".", self.channel)
                    self.end()

                else:
                    timer = time.time() + random.randint(15, 30)

                    time.sleep(1)

                    bot.send("The word is " + Format(str(self.word_()), [IRCFormat.Bold]) + ". You have " + Format(str(int(timer - time.time())), [IRCFormat.Bold]) + " seconds to solve it.", self.channel)

                    while 1:
                        if time.time() > timer:
                            bot.send("Time expired. The word was " + Format(self.word, [IRCFormat.Bold]) + ". Next round..", self.channel)
                            break

                        else:
                            if self not in omgwords_threads:
                                break

                            else:
                                if self.solved:
                                    solved_c += 1
                                    break

                                else:
                                    pass


    def word_(self):
        with open("wordlist.txt", "r") as words_file:
            temp_words = []
            for word in words_file.readlines():
                temp_words.append(word.strip("\n"))

            self.word = random.choice(temp_words)

        return "".join(random.sample(self.word, len(self.word)))

    def end(self):
        omgwords_threads.remove(self)

hangman_threads = []

class HangmanThread(Thread):
    def __init__(self, word, channel, timer, tries, nickname):
        Thread.__init__(self)
        self.word     = word
        self.channel  = channel
        self.timer    = timer
        self.tries    = tries
        self.nickname = nickname

        self.reward   = 0
        self.mask     = []

    def run(self):
        hangman_threads.append(self)
        self.set_reward()

        end_time = time.time() + self.timer

        art = """
      _______
     |/      |
     |      (_)
     |      \|/
     |       |
     |      / \\
     |
    _|___"""

        while time.time() < end_time:

            if self not in hangman_threads:
                break

            else:
                if self.tries == 0:

                    for line in art.split("\n"):
                        bot.send(line, self.channel)
                        time.sleep(0.1)

                    bot.send("No tries left.. the word was '" + self.word + "'!", self.channel)

                    self.end()

        if self in hangman_threads:

            for line in art.split("\n"):
                bot.send(line, self.channel)
                time.sleep(0.1)

            bot.send("Time expired.. the word was '" + self.word + "'!", self.channel)

            self.end()

    def set_reward(self):
        if len(self.word) < 5:
            self.reward = 10
            if int(self.timer) <= 60:
                self.reward += 20
                if int(self.tries) <= 4:
                    self.reward += 20
                else:
                    self.reward += 5
            else:
                self.reward += 5

        elif len(self.word) >= 5 and len(self.word) <= 7:
            self.reward = 50
            if int(self.timer) <= 120:
                self.reward += 30
                if int(self.tries) <= 6:
                    self.reward += 40
                else:
                    self.reward += 10
            else:
                self.reward += 10

        elif len(self.word) >= 8:
            self.reward = 100
            if int(self.timer) <= 120:
                self.reward += 50
                if int(self.tries) <= 7:
                    self.reward += 55
                else:
                    self.reward += 25
            else:
                self.reward += 25

    def mask_(self):
        self.mask.append(self.word[0])

        for char in self.word[:-1][1:]:
            self.mask.append("_")

        self.mask.append(self.word[-1])

        return " ".join(self.mask)

    def unmask(self, char):
        index = -1

        for l in list(self.word):
            index += 1

            if l == char:
                self.mask[index] = self.word[index]

        return " ".join(self.mask)

    def end(self):
        hangman_threads.remove(self)

poll_threads = []

class PollThread(Thread):
    def __init__(self, nickname, channel, description, options):
        Thread.__init__(self)
        self.nickname    = nickname
        self.channel     = channel
        self.description = description
        self.options     = options

        self.timer       = time.time() + 300

    def run(self):
        poll_threads.append(self)

        bot.send('Poll started: "' + self.description + '". Vote using ' + command_character + 'poll vote <option>. Poll ends in 5 minutes!', self.channel)

        while time.time() < self.timer:
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

class Funds(object):
    def __init__(self, nickname, channel):
        self.nickname = nickname
        self.channel  = channel

    def check_funds(self):
        if self.nickname in shelve_:
            bot.send(Format("You have " + Color(str(shelve_[self.nickname]) + "$", IRCColors.Green) + ".", [IRCFormat.Bold]), self.channel)

        else:
            bot.send(Format("I've added you to the database and imbursed you " + Color(str(100) + "$", IRCColors.Green) + ".", [IRCFormat.Bold]), self.channel)
            self.set_funds(100)

    def set_funds(self, amount):
        shelve_[self.nickname] = amount

    def add_funds(self, amount):
        if self.nickname in shelve_:
            shelve_[self.nickname] += amount
        else:
            shelve_[self.nickname] = 100 + amount


class HelpData(object):
    def __init__(self, command, admin_only, description):
        self.command = command
        self.admin_only = admin_only
        self.description = description

def ispangram(str1, alphabet=string.ascii_lowercase):
    alphabet = set(alphabet)
    return alphabet <= set(str1.lower())

class Brain(object):
    def __init__(self):
        self.rs = RiveScript()
        self.load()

    def load(self, path="./brain/"):
        self.rs.load_directory(path)
        self.rs.sort_replies()

    def response(self, msg, nickname):
        reply = self.rs.reply(nickname, msg)

        return reply

class Shodan(object):
    def __init__(self, input, channel):
        self.input      = input
        self.channel    = channel

        self.send_limit = 15

        try:
            self.api = shodan.Shodan(api_key)

        except NameError:
            bot.send("Error: api key not initialized.", self.channel)
            return

    def search(self):
        sent = 0

        result = self.api.search(self.input)

        bot.send("Shodan Summary Information", self.channel)
        bot.send("Querry: " + self.input, self.channel)
        bot.send("Total results: " + str(result['total']) + "\n", self.channel)

        for ip in result['matches']:
            sent += 1

            if sent > self.send_limit:
                break

            else:
                bot.send(ip['ip_str'], self.channel)
                time.sleep(0.5)

    def host(self):
        try:
            scan_host = self.api.host(self.input)

        except shodan.APIError as e:
            bot.send("Error: " + str(e), self.channel)
            return

        bot.send("IP: %s | Organization: %s | Operating System: %s" % (scan_host['ip_str'], scan_host.get('org', 'n/a'), scan_host.get('os', 'n/a')), self.channel)

        for item in scan_host['data']:
            banners = '\n'.join(item['data'].split('\n')[0:])

            bot.send("Port: %s - Banner: %s" % (str(item['port']), banners.split("\n")[0]), self.channel)

    def facets(self):
        FACETS = ["org", "domain", "port", "asn", ('country', 3)]

        FACET_TITLES = {'org': 'Top 5 Organizations','domain': 'Top 5 Domains','port': 'Top 5 Ports','asn': 'Top 5 Autonomous Systems','country': 'Top 3 Countries'}

        result = self.api.count(self.input, facets=FACETS)

        bot.send('Shodan Summary Information', self.channel)
        bot.send("Querry: " + self.input, self.channel)

        bot.send('Total Results: %s' % str(result['total']), self.channel)
        bot.send(" ", self.channel)

        for facet in result['facets']:
            bot.send(Format(FACET_TITLES[facet] + ":", [IRCFormat.Bold]), self.channel)

            for term in result['facets'][facet]:
                bot.send('%s: %s' % (term['value'], term['count']), self.channel)

            bot.send(" ", self.channel)
            time.sleep(1)

    def exploits(self):
        sent = 0

        results = self.api.exploits.search(self.input, page = "1")

        bot.send("Shodan Summary Information", self.channel)
        bot.send("Querry: " + self.input, self.channel)

        bot.send("Total Results: %s\n" % str(results['total']), self.channel)

        for exploit in results['matches']:
            sent += 1

            if sent > self.send_limit:
                break

            else:

                try:
                    bot.send(exploit['description'] + " || Platform: " + exploit['platform'], self.channel)
                except:
                    bot.send(exploit['description'], self.channel)

                time.sleep(1)

ai = Brain()

#Main Loop
while True:

    data = bot.recieve()

    #Respond to pings
    if data.type_command == IRC_CommandType.Ping:
        PingThread(data.data).start()

    if data.type_command == IRC_CommandType.Join:
        for thread in poll_threads:
            if thread.channel == data.channel:
                bot.send(data.sender.nickname + ', a poll is currently running: "' + poll_description + '". The options are ' + ", ".join(options_poll) + '. Vote using ' + command_character + 'poll vote <option>. Poll ends in ' + str(int(thread.timer - time.time())) + ' secconds!', data.channel)

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



        if ispangram(" ".join(args[0:])):
            bot.send(data.sender.nickname + " just made a pangram!", data.channel)

        if args[0] == "hi" or args[0] == "hello" or args[0] == "hey":
            try:
                if args[1] == irc_nickname:
                    greeting = random.choice(('Hi', 'Hey', 'Hello'))
                    bot.send(greeting + " " + data.sender.nickname, data.channel)
            except:
                pass

        if args[0] == "screw" and args[1] == irc_nickname or args[0] == "fuck":
            try:
                if args[1] == irc_nickname:
                    bot.send("Watch your mouth, " + data.sender.nickname + ", or I'll tell your mother!", data.channel)
            except:
                pass

        if args[0] == irc_nickname + ":":
            response = ai.response(" ".join(args[1:]), data.sender.nickname)
            for line in response.split("\n"):
                bot.send(str(line), data.channel)

        if args[0][:len(command_character)] == command_character:
            cmd = args[0][1:].lower()

            if cmd == "lmgtfy":
                bot.send("http://lmgtfy.com/?q="+ "%20".join(args[1:]), data.channel)

            if cmd == "reload":

                if data.sender.nickname not in bot_owner:
                    bot.send(prompt_priviledge_required)

                else:
                    bot.status(data.sender.nickname)
                    if user_data.data != None and user_data.data == 3:
                        ai.load()
                        bot.send("Brain rebooted! :P", data.channel)

            if cmd == "version":
                bot.send("Version: " + version, data.channel)


            if cmd == "omgwords":
                if len(args) > 1:

                    if args[1] == "start":
                        if len(args) == 3:
                            start_new_thread = True

                            for thread in omgwords_threads:
                                if thread.channel == data.channel:
                                    bot.send("There is already a game running on " + data.channel + "!", data.channel)
                                    start_new_thread = False
                                    break

                            if start_new_thread:
                                try:
                                    OmgwordsThread(int(args[2]), data.sender.nickname, data.channel).start()
                                except Exception as e:
                                    bot.send(e, data.channel)

                    elif args[1] == "join":
                        for thread in omgwords_threads:
                            if thread.channel == data.channel:
                                if data.sender.nickname not in thread.players:
                                    thread.players.append(data.sender.nickname)
                                else:
                                    bot.send("You cannot join twice!", data.channel)

                            else:
                                bot.send("No games running in #" + data.channel + ".", data.channel)

                    elif args[1] == "try":
                        if len(args) == 3:
                            for thread in omgwords_threads:
                                if thread.channel == data.channel:
                                    if args[2] == thread.word:
                                        thread.solved = True
                                        bot.send("Correct " + Format(data.sender.nickname, [IRCFormat.Bold]) + ", you win " + Format(Color("20$", IRCColors.Green), [IRCFormat.Bold]) + "!", data.channel)
                                        Funds(data.sender.nickname, data.channel).add_funds(20)

                                    else:
                                        bot.send("Wrong!", data.channel)

                    elif args[1] == "end":
                        for thread in omgwords_threads:
                            if thread.channel == data.channel:
                                if thread.players[0] == data.sender.nickname or data.sender.nickname in bot_owner:
                                    bot.send(data.sender.nickname + " decided to end this omgwords game.", data.channel)
                                    thread.end()
                                else:
                                    bot.send("You did not start this game, GTFO!", data.channel)

            if cmd == "funds":
                if len(args) > 1:

                    if args[1] == "add":

                        if data.sender.nickname not in bot_owner:
                            bot.send(prompt_priviledge_required, data.channel)

                        else:
                            bot.status(data.sender.nickname)
                            if user_data.data != None and user_data.data == 3:
                                if len(args) == 4:
                                    try:
                                        Funds(args[2], data.channel).add_funds(int(args[3]))
                                    except:
                                        bot.send("Please use " + command_character + "help " + cmd, data.channel)
                                else:
                                    bot.send("Please use " + command_character + "help " + cmd, data.channel)
                            else:
                                bot.send(identify_required, data.channel)

                    elif args[1] == "set":

                        if data.sender.nickname not in bot_owner:
                            bot.send(prompt_priviledge_required, data.channel)

                        else:
                            bot.status(data.sender.nickname)
                            if user_data.data != None and user_data.data == 3:
                                if len(args) == 4:
                                    try:
                                        Funds(args[2], data.channel).set_funds(int(args[3]))
                                    except:
                                        bot.send("Please use " + command_character + "help " + cmd, data.channel)

                                else:
                                    bot.send("Please use " + command_character + "help " + cmd, data.channel)
                            else:
                                bot.send(identify_required, data.channel)

                    else:
                        bot.send("Please use " + command_character + "help " + cmd, data.channel)

                else:
                    Funds(data.sender.nickname, data.channel).check_funds()


            if cmd == "shodan":
                if len(args) > 1:
                    if args[1] == "init" and data.channel == irc_nickname:
                        if len(args) == 3:
                            if data.sender.nickname not in bot_owner:
                                bot.send(prompt_priviledge_required, data.sender.nickname)

                            else:
                                api_key=args[2]
                                bot.send("Api key updated successfuly!", data.sender.nickname)
                        else:
                            bot.send("Please use " + command_character + "help " + cmd, data.channel)

                    elif args[1] == "host":
                        if len(args) == 3:
                            Shodan(args[2], data.channel).host()
                        else:
                            bot.send("Please use " + command_character + "help " + cmd, data.channel)

                    elif args[1] == "search":
                        if len(args) > 2:
                            Shodan(" ".join(args[2:]), data.channel).search()
                        else:
                            bot.send("Please use " + command_character + "help " + cmd, data.channel)

                    elif args[1] == "facets":
                        if len(args) > 2:
                            Shodan(" ".join(args[2:]), data.channel).facets()
                        else:
                            bot.send("Please use " + command_character + "help " + cmd, data.channel)

                    elif args[1] == "exploits":
                        if len(args) > 2:
                            Shodan(" ".join(args[2:]), data.channel).exploits()
                        else:
                            bot.send("Please use " + command_character + "help " + cmd, data.channel)

                else:
                   bot.send("Please use " + command_character + "help " + cmd, data.channel)

            if cmd == "resolve":

                if len(args) == 2:
                    try:
                        bot.send(args[1] + " --> " + socket.gethostbyname(args[1]), data.channel)
                    except Exception as e :
                        bot.send(str(e), data.channel)
                else:
                    bot.send("Please use " + command_character + "help " + cmd, data.channel)

            if cmd == "hangman":
                if len(args) >= 2:
                    if args[1] == "start":
                        if data.channel == irc_nickname:
                            if len(args) == 6:
                                if args[3] in irc_channels:
                                    start_new_thread = True
                                    for thread in hangman_threads:
                                        if thread.channel == args[3]:
                                            bot.send("There is already a game running on " + args[3] + "!", data.sender.nickname)
                                            start_new_thread = False
                                            break

                                    if start_new_thread:

                                        try:
                                            HangmanThread(args[2], args[3], int(args[4]), int(args[5]), data.sender.nickname).start()

                                            for thread in hangman_threads:
                                                if thread.channel == args[3]:
                                                    bot.send(data.sender.nickname + " started a new hangman game! The word is " + Format(str(thread.mask_()), [IRCFormat.Bold]) + ", timer set for " + str(thread.timer) + " seconds and maximum attempts is " + str(thread.tries) + "! Play with " + command_character + cmd + " try <letter> OR " + command_character + cmd + " guess <word>. Whoever gets the word first wins " + Format(Color(str(thread.reward) + "$", IRCColors.Green), [IRCFormat.Bold]) + "!", args[3])

                                        except Exception as e:
                                            print(e)

                                else:
                                    bot.send("You need to specify a channel in which I'm already in.", data.sender.nickname)
                            else:
                                bot.send("Please use " + command_character + "help " + cmd, data.sender.nickname)
                        else:
                            bot.send("You must pm me this command.", data.channel)

                    elif args[1] == "guess":
                        if len(args) == 3:
                            if len(hangman_threads) > 0:
                                for thread in hangman_threads:
                                    if thread.channel == data.channel:
                                        if args[2] == thread.word:
                                            bot.send("Congratulations " + data.sender.nickname + ", you won " + Format(Color(str(thread.reward) + "$",IRCColors.Green), [IRCFormat.Bold]) + "!", data.channel)
                                            Funds(data.sender.nickname, data.channel).add_funds(thread.reward)
                                            thread.end()

                                        else:
                                            bot.send("Wrong!", data.channel)
                                            thread.tries -= 1
                                            bot.send(str(thread.tries) + " tries left.", data.channel)

                                    else:
                                        pass
                            else:
                                bot.send("There are no games running in " + data.channel + ".", data.channel)
                        else:
                            bot.send("Please use " + command_character + "help " + cmd, data.channel)

                    elif args[1] == "try":
                        if len(args) == 3:
                            if len(hangman_threads) > 0:
                                for thread in hangman_threads:
                                    if thread.channel == data.channel:
                                        if len(args[2]) == 1:

                                            if args[2] in thread.word:
                                                bot.send(thread.unmask(args[2]), data.channel)

                                                if "_" not in thread.mask:
                                                    bot.send("Congratulations " + data.sender.nickname + ", you won " + Format(Color(str(thread.reward) + "$", IRCColors.Green), [IRCFormat.Bold]) + "!", data.channel)
                                                    Funds(data.sender.nickname, data.channel).add_funds(thread.reward)
                                                    thread.end()

                                            else:
                                                bot.send("Letter not in word!", data.channel)
                                                thread.tries -= 1
                                                bot.send(str(thread.tries) + " tries left.", data.channel)
                                        else:
                                            bot.send("You can only try one letter at a time!", data.channel)

                                    else:
                                        pass
                            else:
                                bot.send("There are no games running in " + data.channel + ".", data.channel)
                        else:
                            bot.send("Please use " + command_character + "help " + cmd, data.channel)

                    elif args[1] == "end":
                        if len(hangman_threads) > 0:
                            for thread in hangman_threads:
                                if thread.channel == data.channel:
                                    if thread.nickname == data.sender.nickname:
                                        bot.send(data.sender.nickname + " decided to end this game.", data.channel)
                                        thread.end()
                                    else:
                                        bot.send("You did not start this game, GTFO!", data.channel)
                                else:
                                    bot.send("There are no games running in " + data.channel + ".", data.channel)
                        else:
                            bot.send("There are no games running in " + data.channel + ".", data.channel)

            if cmd == "py":
                BASE_TUMBOLIA_URI = 'https://tumbolia-two.appspot.com/'
                uri = BASE_TUMBOLIA_URI + 'py/'
                querry = " ".join(args[1:])
                try:
                    answer = requests.get(uri+querry, timeout=15, verify=False)
                    if len(answer.text) > 60:
                        if len(answer.text) > 4000:
                            bot.send("Too much text!", data.channel)
                        else:
                            line = answer.text
                            n = 60
                            line1 = [line[i:i+n] for i in range(0, len(line), n)]
                            for line2 in line1:
                                time.sleep(1)
                                bot.send("~ "+line2, data.channel)
                    else:
                        bot.send("~ "+answer.text, data.channel)
                except:
                    bot.send("Connection timed out!", data.channel)

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
                            if args[1] in irc_channels or data.sender.nickname=='target_':
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

            if cmd == "iplookup":
                try:
                    gi_city = pygeoip.GeoIP("GeoLiteCity.dat")
                    gi_org = pygeoip.GeoIP("GeoIPASNum.dat")
                    host = socket.getfqdn(args[1])
                    response = "[IP/Host Lookup] Hostname: %s" % host
                    try:
                        response += " | Location: %s" % gi_city.country_name_by_name(args[1])
                    except AttributeError:
                        response += ' | Location: Unknown'
                    except socket.gaierror:
                        bot.send('[IP/Host Lookup] Unable to resolve IP/Hostname', data.channel)

                    region_data = gi_city.region_by_name(args[1])
                    try:
                        region = region_data['region_code'] # pygeoip >= 0.3.0
                    except KeyError:
                        region = region_data['region_name'] # pygeoip < 0.3.0
                    if region:
                        response += " | Region: %s" % region

                    isp = gi_org.org_by_name(args[1])
                    response += " | ISP: %s" % isp
                    bot.send(response, data.channel)

                except:
                    bot.send("Please use "+command_character+"help "+cmd, data.channel)

            if cmd == "uptime":
                delta = datetime.timedelta(seconds=round((datetime.datetime.utcnow() - uptime).total_seconds()))
                bot.send("I've been sitting here for " + str(delta) + " and I keep going!", data.channel)

            if cmd == "movie":
                if len(args) >= 2:
                    movie = " ".join(args[1:])
                    payload = { 'keyword': movie }
                    data_ = requests.get("http://theapache64.xyz:8080/movie_db/search", params=payload)
                    json_data = data_.json()

                    if json_data['message'] == "Movie found":
                        response = "Movie: %s" % json_data['data']['name']

                        try:
                            response += " || Year: %s" % json_data['data']['year']
                        except:
                            response += " || Year: unkown"

                        try:
                            response += " || Plot: %s" % json_data['data']['plot']
                        except:
                            response += " || Plot: unkown"

                        try:
                            response += " || Director: %s" % json_data['data']['director']
                        except:
                            response += " || Director: unkown" % json_data['data']['director']

                        try:
                            response += " || Rating: %s" % json_data['data']['rating']
                        except:
                            response += " || Rating: unkown"

                        try:
                            response += " || Genre: %s" % json_data['data']['genre']
                        except:
                            response += " || Genre: unkown"

                        bot.send(response, data.channel)

                    else:
                        bot.send("Movie not in database", data.channel)

                else:
                    bot.send("Please use " + command_character + "help " + cmd, data.channel)

            if cmd == "admin":
                if len(args) > 1:
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
                                if len(args) == 3:
                                    if args[2] in bot_owner:
                                        f = open("admins.txt", "r")
                                        lines = f.readlines()
                                        f.close()

                                        with open("admins.txt", "w") as out:
                                            for line_ in lines:
                                                if line_ != args[2] + "\n":
                                                    out.write(line_)

                                        bot_owner.remove(args[2])
                                    else:
                                        bot.send("Admin doesn't exist!", data.channel)
                                else:
                                    bot.send("Please use " + command_character + "help " + cmd, data.channel)
                            else:
                                bot.send(identify_required, data.channel)

                    elif args[1].lower() == "add":
                        if data.sender.nickname not in bot_owner:
                            bot.send(prompt_priviledge_required, data.channel)

                        else:
                            bot.status(data.sender.nickname)
                            if user_data.data != None and user_data.data == 3:
                                if len(args) == 3:
                                    f = open("admins.txt", "a")
                                    f.write(args[2]+"\n")
                                    f.close()
                                    bot_owner.append(args[2])
                                else:
                                    bot.send("Please use " + command_character + "help " + cmd, data.channel)
                            else:
                                bot.send(identify_required, data.channel)
                    else:
                        bot.send("Unknown option. Please use "+command_character+"help "+cmd, data.channel)

                else:
                    bot.send("Please use " + command_character + "help " + cmd, data.channel)

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
                    if args[1] == "base16":
                        bot.send(Color(hex(int(args[2])), random.choice(IRCColors.all_colors)), data.channel)
                    else:
                        figlet = Figlet(args[1])
                        render = figlet.renderText(args[2]).split('\n')
                        for ascii in render:
                            bot.send(Color(ascii, random.choice(IRCColors.all_colors)), data.channel)
                except Exception:
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
                                    feedparse(data.sender.nickname, data.channel).start()
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
                                    bot.send("Stopping..", data.channel)
                                    thread_to_end.end()
                                else:
                                    bot.send(identify_required, data.channel)
                            else:
                                bot.send(prompt_priviledge_required, data.channel)
                    elif args[1].lower() == "list":
                        for key,url in newsurls.items():
                            bot.send(key+" - "+url,data.channel)
                except:
                    pass

            if cmd == "w":
                try:
                    bot.send(wikipedia.summary(" ".join(args[1:]), sentences=2), data.channel)
                except:
                    bot.send("No results!", data.channel)

            if cmd == "translate":
                try:
                    check=args[1]
                    bot.send("Translation: " + translate(" ".join(args[1:])), data.channel)
                except:
                    bot.send("Please enter a string to translate!", data.channel)

            if cmd == "countdown":
                try:
                    if (args[1].isdigit() and args[2].isdigit() and args[3].isdigit()):
                        try:
                            diff = (datetime.datetime(int(args[1]), int(args[2]), int(args[3])) - datetime.datetime.today())
                            bot.send(str(diff.days) + " days, " + str(diff.seconds // 3600) + " hours and " + str(diff.seconds % 3600 // 60) + " minutes until " + args[1] + " " + args[2] + " " + args[3], data.channel)

                        except:
                            bot.send("Please use correct format: "+command_character+"countdown 2017 12 21", data.channel)
                except:
                    bot.send("Please use correct format: "+command_character+"countdown 2017 12 21", data.channel)


            if cmd == "isup":
                try:
                    request = urlopen('http://www.isup.me/' + args[1]).read()
                    if type(request) != type(''):
                        request = request.decode('utf-8')
                    if "t's just you" in request:
                        bot.send("- "+args[1]+" - looks up for me!", data.channel)
                    else:
                        bot.send("- "+args[1]+" - is DOWN!", data.channel)
                except:
                    bot.send("Please enter an address to check!", data.channel)

            if cmd == "announce":
                if data.sender.nickname in bot_owner:
                    for channel in irc_channels:
                        bot.send(" ".join(args[1:]), channel)
                    bot.send("Done!", data.channel)
                else:
                    bot.send(prompt_priviledge_required, data.channel)

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
                                    options_poll = args[3:]
                                    poll_description = args[2]
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
                    HelpData("spam",     False, "<times> <text> - Floods the channel with text."),
                    HelpData("quote",    False, "<add/count/read> - Inspirational quotes by 4chan."),
                    HelpData("art",      False, "list/draw <optional:name> - Draw like picasso!"),
                    HelpData("ascii",    False, "<font> <text> - Transform text into ascii art made of... text... Font list: https://pastebin.com/TvwCcNUd"),
                    HelpData("version",  False, "- Prints bot version and GitHub link."),
                    HelpData("memetic",  False, "- Generates a quote using ARTIFICIAL INTELLIGENCE!!!"),
                    HelpData("poll",     False, "new <description> <option1> <option2> ... / vote <option> / end - DEMOCRACY, BITCH!"),
                    HelpData("flipcoin", False, "- Unlike Effy, it generates a random output!"),
                    HelpData("die",      True,  "- [Admins Only] Rapes the bot, murders it, does funny things to its corpse, and disposes of it."),
                    HelpData("restart",  True,  "- [Admins Only] Did you try turning it Off and On again?"),
                    HelpData("feed",     True,  "- [Admins Only] on/off/list - rss feed system."),
                    HelpData("admin",    True,  "- [Admins Only] list/remove/add  - Manage list of admins."),
                    HelpData("iplookup", False, "<ip> - Ip lookup tool."),
                    HelpData("w",        False, "<thing> - Wikipedia - Tired of feeling stupid when someone says something smart? We've got you covered!"),
                    HelpData("translate",False, "<string> - Translate anything to english!"),
                    HelpData("isup",     False, "<address> - Check if a site is up or down."),
                    HelpData("shodan",   False, "<host/search/facets/exploits> (ex: =shodan search port:22 ssh; shodan host 8.8.8.8; shodan facets apache; shodan exploits port:22 type:remote) - Scan with Shodan."),
                    HelpData("lmgtfy",   False, "<string> - Let me just.. google that for you."),
                    HelpData("countdown",False, "<year> <month> <day> - displays a countdown to a given date."),
                    HelpData("uptime",   False, "- Returns the uptime of SpamBot."),
                    HelpData("py",       False, "<expression> - Evaluate a python expression"),
                    HelpData("announce", True,  "- [Admins Only] <announcement> Send an announcement to all channels the bot is in."),
                    HelpData("movie",    False, "<movie> - Get info about any movie."),
                    HelpData("resolve",  False, "<host> - Resolve dns."),
                    HelpData("omgwords", False, "start/try/end (ex: =omgwords start <number_of_players>; =omgwords try <word>; =omgwords end) - Try to solve the shuffled word and be first!"),
                    HelpData("hangman",  False, "start/try/guess/end (ex: =hangman start <word> <channel> <time> <max_tries>; =hangman try <letter>; =hangman guess <word>) - Hangman game!! :D"),
                    HelpData("funds",    False, "- Currency system.")
                ]

                if len(args) == 1:
                    command_list = []

                    for command in help_data:

                        if data.sender.nickname not in bot_owner:

                            if command.admin_only == False:
                                command_list.append(command.command)

                            else:
                                pass

                        else:
                            command_list.append(command.command)

                    bot.send("Available commands: " + ", ".join(command_list), data.channel)
                    bot.send("Use " + command_character + "help <command> for more detailed info.", data.channel)
                else:
                    command = " ".join(args[1:])

                    help_output = 'Unknown command "' + command + '". Please use "' + command_character + 'help" for a list of available commands.'

                    for help in help_data:

                        if help.command.lower() == command.lower():

                            if help.admin_only == True:

                                if data.sender.nickname not in bot_owner:
                                    help_output = prompt_priviledge_required
                                    break

                                else:
                                    help_output = command_character + help.command + " " + help.description
                                    break
                            else:
                                help_output = command_character + help.command + " " + help.description

                    help_output = data.sender.nickname + ", " + help_output
                    bot.send(help_output, data.channel)
