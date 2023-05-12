import sys
from discord.ext import commands

class ModuleLoadError(commands.CommandError):
    pass

class Module:
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot
        self.load_path = cog.__module__

    @property
    def is_loaded(self):
        return bool(self.cog.qualified_name in self.bot.cogs)

    @staticmethod
    async def load(cog):
        try:
            await cog.bot.load_extension(cog.__module__)
        except Exception as e:
            # raise ModuleLoadError(cog.bot.exception(e))
            print(self.bot.exception(e))
            sys.stdout.flush()

class ModuleManager:
    modules = {}
    def __init__(self, bot):
        self.bot = bot

    def __iadd__(self, other):
        self.load(other)

    def __isub__(self, other):
        self.unload(other)

    async def load(self, module):
        try:
            await self.bot.load_extension(module)
        except Exception as e:
            # raise ModuleLoadError(self.bot.exception(e))
            print(self.bot.exception(e))
            sys.stdout.flush()
        else:
            module = self.bot.get_cog(module.split('.')[2].title())
            self.modules[module.qualified_name] = Module(module)

    async def unload(self, module, del_module=False):
        try:
            await self.bot.unload_extension(module)
            if del_module:
                del self.modules[module]
        except Exception as e:
            # raise ModuleLoadError(self.bot.exception(e))
            print(self.bot.exception(e))
            sys.stdout.flush()

    async def reload(self, module):
        try:
            await self.bot.reload_extension(module)
        except Exception as e:
            # raise ModuleLoadError(self.bot.exception(e))
            print(self.bot.exception(e))
            sys.stdout.flush()

    def _inject(self, bot):
        cls = self.__class__

        # realistically, the only thing that can cause loading errors
        # is essentially just the command loading, which raises if there are
        # duplicates. When this condition is met, we want to undo all what
        # we've added so far for some form of atomic loading.
        for index, command in enumerate(self.__cog_commands__):
            command.cog = self
            if command.parent is None:
                try:
                    bot.add_command(command)
                except Exception as e:
                    # undo our additions
                    for to_undo in self.__cog_commands__[:index]:
                        bot.remove_command(to_undo.name)
                    raise e

        # check if we're overriding the default
        if cls.bot_check is not Cog.bot_check:
            bot.add_check(self.bot_check)

        if cls.bot_check_once is not Cog.bot_check_once:
            bot.add_check(self.bot_check_once, call_once=True)

        # while Bot.add_listener can raise if it's not a coroutine,
        # this precondition is already met by the listener decorator
        # already, thus this should never raise.
        # Outside of, memory errors and the like...
        for name, method_name in self.__cog_listeners__:
            bot.add_listener(getattr(self, method_name), name)

        return self

    def add_cog(self, cog):
        """Adds a "cog" to the bot.

        A cog is a class that has its own event listeners and commands.

        Parameters
        -----------
        cog: :class:.Cog
            The cog to register to the bot.

        Raises
        -------
        TypeError
            The cog does not inherit from :class:.Cog.
        CommandError
            An error happened during loading.
        """

        if not isinstance(cog, Cog):
            raise TypeError('cogs must derive from Cog')

        cog = cog._inject(self)
        self.__cogs[cog.__cog_name__] = cog