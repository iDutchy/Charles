from core.cog import MainCog

class Events(MainCog, name="Events"):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    cog = bot.add_cog(Events(bot))
    cog.add_subcogs(__package__)