from core.cog import MainCog


class Info(MainCog, name="Info"):
    def __init__(self, bot):
        self.bot = bot
        self.icon = "<:charlesInfo:615429388644777994>"
        self.big_icon = "https://cdn.discordapp.com/emojis/615429388644777994.png"


def setup(bot):
    cog = bot.add_cog(Info(bot))
    cog.add_subcogs(__package__)
    from .help import HelpCommand
    bot.help_command = HelpCommand(command_attrs=dict(aliases=['h', 'cmds', 'commands']))
    bot.help_command.cog = cog
    bot.help_command._command_impl.category = bot.get_category("Bot Info")
    bot.help_command._command_impl.is_guild_disabled = lambda ctx: 1 == 2
    bot.help_command._command_impl.is_global_disabled = lambda: 1 == 2
    bot.help_command._command_impl.perm_names = ["*"]
    bot._categories["Bot Info"].all_commands['help'] = bot.help_command._command_impl
