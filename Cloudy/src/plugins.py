class PluginManager(object):
    def __init__(self):
        self.modules = {}
        self.help    = {}

    def load_module(self, name, params):
        """
        Load a module with given parameters.
        Args:
            name (str): name of the module to load
            params (dict): parameters to initialize the module with
        Raise:
            TypeError: if a modules required parameters are missing
            ImportError: if the requested module could not be found
        """
        module = __import__("modules." + name, globals(), locals(), [name], -1)
        instance = getattr(module, name)(**params)
        command = instance.get_command()
        description = instance.get_description()
        help_msg = command + ': ' + instance.get_help()

        self.modules[command] = instance
        self.help[command] = help_msg

        printEx('Loaded module "' + name + '": ' + description, PrintType.Info)

    def call_command(self, user, channel, message):

        
#TODO finish this
