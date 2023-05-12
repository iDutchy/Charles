import json

from core.cog import MainCog

class Utility(MainCog, name="Utility"):
    __all__ = ('bot', 'icon', 'big_icon', 'languages')
    def __init__(self, bot):
        self.bot = bot
        self.icon = "<:charlesWorker:615429082397671424>"
        self.big_icon = "https://cdn.discordapp.com/emojis/615429082397671424.png"

        with open("db/Languages.json",'r') as f:
            self.languages = json.loads(f.read())

def setup(bot):
    cog = bot.add_cog(Utility(bot))
    cog.add_subcogs(__package__)