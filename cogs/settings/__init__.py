import json

from core.cog import MainCog

class Settings(MainCog, name="Settings"):
    __all__ = ('bot', 'icon', 'big_icon', 'roasts')
    def __init__(self, bot):
        self.bot = bot
        self.icon = "<:charlesSetting:615429320311046145>"
        self.big_icon = "https://cdn.discordapp.com/emojis/615429320311046145.png"

        with open('db/languages/en/roasts.json', 'r') as f:
            self.roasts = json.load(f)

def setup(bot):
    cog = bot.add_cog(Settings(bot))
    cog.add_subcogs(__package__)