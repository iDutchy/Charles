from core.cog import MainCog

class Images(MainCog, name="Images"):
    def __init__(self, bot):
        self.bot = bot
        self.icon = "<:charlesArtist:615429245749166100>"
        self.big_icon = "https://cdn.discordapp.com/emojis/615429245749166100.png"

def setup(bot):
    cog = bot.add_cog(Images(bot))
    cog.add_subcogs(__package__)