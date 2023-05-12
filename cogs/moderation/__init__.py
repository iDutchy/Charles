from core.cog import MainCog

class Moderation(MainCog, name="Moderation"):
    def __init__(self, bot):
        self.bot = bot
        self.icon = "<:charlesJudge:615429146159611909>"
        self.big_icon = "https://cdn.discordapp.com/emojis/615429146159611909.png"

def setup(bot):
    cog = bot.add_cog(Moderation(bot))
    cog.add_subcogs(__package__)