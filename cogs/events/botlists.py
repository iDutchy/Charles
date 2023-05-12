import discord
import time

from discord.ext import commands
from db import tokens
from utils.utility import warn
from core.cog import SubCog
import topgg

class BotLists(SubCog):
    def __init__(self, bot):
        self.bot = bot
        self.token = tokens.DBL        

    @commands.Cog.listener()
    async def on_dbl_test(self, data):
        c = self.bot.get_channel(659606634321936417)
        await c.send("A vote test has ran succesfully!")

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        channel = self.bot.get_channel(659606634321936417)
        user = await self.bot.try_user(data.user)
        data = await self.bot.dblpy.get_bot_info()
        e = discord.Embed(color=0x5E82AC,
                          title="Received Upvote!",
                          description=f"New upvote received from **{user}**!\n\n**This Month's Upvotes:** {data.monthly_points}\n**All Time Upvotes:** {data.points}")
        e.set_author(icon_url=user.avatar.url, name=str(user))
        e.set_thumbnail(url="https://cdn.discordapp.com/attachments/638902095520464908/659611283443941376/upvote.png")
        await channel.send(embed=e)

        cache = self.bot.get_cache(user.id)
        if not cache.voteremind:
            return

        await self.bot.db.execute("UPDATE votereminders SET time = $1, reminded = $2 WHERE user_id = $3", int(time.time()) + 43200, False, user.id)
        cache.voteremind.reminded = False
        cache.voteremind.time = int(time.time()) + 43200

    async def post_count(self):
        try:
            await self.bot.dblpy.post_guild_count()
        except Exception as e:
            await warn(self.bot, "DBL Guild Count Post", self.bot.owner, self.bot.exception(e))
        try:
            await self.bot.session.post('https://discordextremelist.xyz/api/bot/505532526257766411', headers={"Authorization": tokens.DEL}, data={"guildCount": len(self.bot.guilds)})
        except Exception as e:
            await warn(self.bot, "DEL Guild Count Post", self.bot.owner, self.bot.exception(e))

    @commands.Cog.listener('on_guild_join')
    async def post_join_guild_count(self, guild):
        await self.post_count()

    @commands.Cog.listener('on_guild_remove')
    async def post_leave_guild_count(self, guild):
        await self.post_count()

def setup(bot):
    pass
