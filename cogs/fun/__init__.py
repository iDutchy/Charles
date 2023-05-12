import json
import async_cleverbot as ac

from discord.ext import tasks
from core.cog import MainCog

class Fun(MainCog, name="Fun"):
    __all__ = ('bot', 'icon', 'big_icon', 'latest_xkcd', 'cb', 'roasts')
    def __init__(self, bot):
        self.bot = bot
        self.icon = "<:charlesClown:615429008745693184>"
        self.big_icon = "https://cdn.discordapp.com/emojis/615429008745693184.png"
        self.latest_xkcd = 1
        self.cb = ac.Cleverbot(bot.get_token("CB"))
        self.cb.set_context(ac.DictContext(self.cb))
        self.refresh_xkcd.start()

        with open('db/languages/en/roasts.json', 'r') as f:
            self.roasts = json.load(f)

    @tasks.loop(hours=5)
    async def refresh_xkcd(self):
        async with self.bot.session.get("https://xkcd.com/info.0.json") as f:
            res = await f.json()
        self.latest_xkcd = res['num']

    @refresh_xkcd.before_loop
    async def before_xkcdrefresh(self):
        await self.bot.wait_until_ready()

def setup(bot):
    cog = bot.add_cog(Fun(bot))
    cog.add_subcogs(__package__)