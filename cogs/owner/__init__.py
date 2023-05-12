from core.cog import MainCog
import importlib

from discord.ext import commands as err

class Owner(MainCog, name="Owner"):
    def __init__(self, bot):
        self.bot = bot
        self.icon = "<:charles:639898570564042792>"
        self.big_icon = "https://cdn.discordapp.com/avatars/505532526257766411/d1cde11602889bd799dec9a82e29609f.png?size=1024"

    # async def cog_check(self, ctx):
    #     cmd = ctx.command
    #     if not hasattr(cmd, "category"):
    #         cmd = ctx.command.root_parent
    #     if cmd.qualified_name == "ttt" and ctx.author.id == 282958751852658690:
    #         return True
    #     if cmd.category.name == "Developer" and not ctx.author.id in self.bot.config['settings']['BOT_DEVS']:
    #         raise err.NotOwner()
    #     elif cmd.category.name != "Developer" and ctx.author.id != ctx.bot.owner_id:
    #         raise err.NotOwner()
    #     return True

def setup(bot):
    cog = bot.add_cog(Owner(bot))
    cog.add_subcogs(__package__)

    #Also load the test commands to owner cog
    from cogs.tests import abc
    importlib.reload(abc)
    cog.add_subcog(abc.Tests)