from core.cog import MainCog

class Private(MainCog, name="Private"):
    def __init__(self, bot):
        self.bot = bot
        self.icon = "<:charlesthink:603647216787128351>"
        self.big_icon = "https://cdn.discordapp.com/emojis/603647216787128351.png"

def setup(bot):
    cog = bot.add_cog(Private(bot))
    cog.add_subcogs(__package__)