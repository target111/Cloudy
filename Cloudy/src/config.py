import json
from utils import printEx, PrintType

class LoadConfig(object):
    def __init__(self):
        self.options = {}

    def load_config(self, file):
        try:
            config_file = open(file, "r")
            self.options = json.load(config_file)
        # File did not exist or we can't open it for another reason
        except IOError:
            printEx("Can't open %s file!" % file, PrintType.Error)
        # Thrown by json.load() when the content isn't valid JSON
        except ValueError:
            printEx("Invalid JSON in %s!" % file, PrintType.Error)

        if self.options == {} :
            printEx("Config file appeares to be empty!" % file, PrintType.Error)

        return self.options

class MakeConfig(object):
    def __init__(self, file):
        self.file    = file
        self.options = {}

    def add_options(self):
        self.options["irc_server"]        = input("IRC server to connect to: ")
        self.options["irc_port"]          = input("port: ")
        self.options["irc_nickname"]      = input("nickname: ")
        self.options["irc_nickserv_pwd"]  = input("NickServ pwd (you can leave this blank): ")
        self.options["irc_channels"]      = input("List of channels to join (separated by a space. ex: #chan1 #chan2): ")
        self.options["command_character"] = input("Command character of the bot (if you leave this blank it will be '='): ")

        if len(command_character) == 0:
            command_character = '='

        # write options to file
        self.write_config()

        return self.options

    def write_config(self):
        try:
            config_file = open(self.file, "w")
            json.dump(self.options, config_file)
        except IOError:
            printEx("Couldn't write to file. Error: %s" % self.file, PrintType.Error)

        printEx("Config successfuly created!", PrintType.Info)
