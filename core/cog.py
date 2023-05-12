import inspect

from discord.ext import commands
from utils.utility import loader

from .commands import Category


class GroupCogMeta(commands.CogMeta):
    def __new__(cls, *args, **kwargs):
        group = kwargs.pop('command_parent')

        new_cls = super().__new__(cls, *args, **kwargs)

        for subcommand in new_cls.__cog_commands__:
            # if subcommand.parent is None:
            #     subcommand.parent = group
            #     subcommand.__original_kwargs__['parent'] = group
            subcommand.category = Category(subcommand, "Other", "Owner")
            subcommand.is_guild_disabled = lambda ctx: 1 == 2
            subcommand.is_global_disabled = lambda: 1 == 2

        new_cls.__cog_commands__.append(group)
        # setattr(new_cls, group.callback.__name__, group)

        return new_cls


class SubCogMeta(commands.CogMeta):
    def __new__(cls, *args, **kwargs):
        category = kwargs.pop("category", None)
        new = super().__new__(cls, *args, **kwargs)
        new.category = category
        new._listeners_to_delete = {}
        return new

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SubCog(commands.Cog, metaclass=SubCogMeta):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _inject(self, bot, override, guild, guilds):
        cls = self.__class__

        for index, command in enumerate(self.__cog_commands__):
            self.bot._categories[self.category].all_commands[command.qualified_name] = command
            command.category = self.bot.get_category(self.category)
            if command.parent is None:
                try:
                    bot.add_command(command)
                except Exception as e:
                    # undo our additions
                    for to_undo in self.__cog_commands__[:index]:
                        bot.remove_command(to_undo.name)
                    raise e

        # check if we're overriding the default
        if cls.bot_check is not commands.Cog.bot_check:
            bot.add_check(self.bot_check)

        if cls.bot_check_once is not commands.Cog.bot_check_once:
            bot.add_check(self.bot_check_once, call_once=True)

        for name, method_name in self.__cog_listeners__:
            meth = getattr(self, method_name)
            bot.add_listener(meth, name)
            if name not in self._listeners_to_delete:
                self._listeners_to_delete[name] = [meth]
            else:
                self._listeners_to_delete[name].append(meth)

        return self

    def _eject(self, bot):
        cls = self.__class__

        try:
            for command in self.__cog_commands__:
                if command.parent is None:
                    bot.remove_command(command.name)

            for name, meths in self._listeners_to_delete.items():
                for meth in meths:
                    bot.remove_listener(meth, name)
                    self._listeners_to_delete[name].remove(meth)

            # for _, method_name in self.__cog_listeners__:
            #     bot.remove_listener(getattr(self, method_name), method_name)

            if cls.bot_check is not commands.Cog.bot_check:
                bot.remove_check(self.bot_check)

            if cls.bot_check_once is not commands.Cog.bot_check_once:
                bot.remove_check(self.bot_check_once, call_once=True)
        finally:
            self.cog_unload()


class MainCogMeta(commands.CogMeta):
    def __new__(cls, *args, **kwargs):
        new = super().__new__(cls, *args, **kwargs)
        new._subcogs = {}
        return new

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class MainCog(commands.Cog, metaclass=MainCogMeta):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_subcogs(self, package):
        cogs = loader(package)
        for cog in cogs:
            self.add_subcog(cog)

    def add_subcog(self, cog):
        cog = cog(self.bot)
        if not isinstance(cog, commands.Cog):
            raise TypeError('cogs must derive from Cog')

        cog = self._inject_category(cog)
        self._subcogs[cog.category] = cog

    def _inject_category(self, cog):
        if cog.category is None:
            cog.category = cog.qualified_name
        if cog.category not in self.bot.categories:
            self.bot._categories[cog.category] = Category(self, cog.category)

        incog = cog._inject(self.bot)
        for command in incog.__cog_commands__:
            command.cog = self
        self.__cog_commands__ += incog.__cog_commands__

        for name, meth in inspect.getmembers(incog):
            if not hasattr(self, name):
                setattr(self, name, meth)

        if hasattr(self, "__all__"):
            for attr in self.__all__:
                if not hasattr(incog, attr):
                    setattr(incog, attr, getattr(self, attr))

        return incog

    def _eject(self, bot):
        try:
            for command in self.__cog_commands__:
                if command.parent is None:
                    bot.remove_command(command.name)

            for cog in list(self._subcogs.values()):

                cog._eject(bot)
                cog.cog_unload()
                # cls = cog.__class__

                # for _, method_name in cog.__cog_listeners__:
                #     bot.remove_listener(getattr(cog, method_name))

                # if cog.cog_check is not commands.Cog.cog_check:
                #     bot.remove_check(cog.cog_check)

                # if cog.bot_check_once is not commands.Cog.bot_check_once:
                #     bot.remove_check(cog.bot_check_once, call_once=True)

                for attr in inspect.getmembers(cog):
                    try:
                        delattr(self.__class__, attr[0])
                    except:
                        continue

                self._subcogs.pop(cog.category)
        finally:
            self.cog_unload()
