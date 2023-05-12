import collections
import holidays
import time
import asyncio

import discord
import psutil
from db import tokens
from discord.ext import commands, tasks
from utils.utility import warn
from core.cog import SubCog
from datetime import datetime, date, timedelta

class Tasks(SubCog):
    def __init__(self, bot):
        self.bot = bot
        self.votereminder.start()
        self.post_stats.start()
        self.holiday_announcing.start()

    def cog_unload(self):
        print("Cancelling votereminders...")
        self.votereminder.cancel()
        self.post_stats.cancel()
        self.holiday_announcing.cancel()

    @commands.Cog.listener()
    async def on_socket_response(self, data: dict):
        if not hasattr(self.bot, "counts"):
            self.bot.counts = collections.Counter()
        if data.get("t") is not None:
            self.bot.counts[data['t']] += 1

    @tasks.loop(seconds=60)
    async def post_stats(self):
        if not hasattr(self.bot, "counts"):
            self.bot.counts = collections.Counter()

        proc = psutil.Process()
        with proc.oneshot():
            mem = proc.memory_full_info()

        payload = {
            "metrics": {
                a: b for a, b in self.bot.counts.items()
            },
            "usercount": len(self.bot.users),
            "guildcount": len(self.bot.guilds),
            "ramusage": round(mem.rss / 1048576),  # in mb
            "latency": round(self.bot.latency*1000)  # in ms
        }
        await self.bot.session.post("https://idevision.net/api/bots/updates",
                                    json=payload, headers={"Authorization": tokens.IDEVISION})

    @tasks.loop(minutes=10)
    async def votereminder(self):
        for x in self.bot.cache.votereminders.keys():
            if self.bot.cache.votereminders[x]["reminded"] == True:
                continue
            if self.bot.cache.votereminders[x]["time"] == None:
                continue
            t = self.bot.cache.votereminders[x]["time"]
            if t <= int(time.time()):
                u = await self.bot.try_user(int(x))
                try:
                    await u.send(f"Hey, {u}! You asked me to remind you when you can vote again, so here I am :D\n\nhttps://top.gg/bot/505532526257766411/vote")
                    self.bot.cache.votereminders[x]['reminded'] = True
                    await self.bot.db.execute("UPDATE votereminders SET reminded = $2 WHERE user_id = $1", int(x), True)
                except Exception as exc:
                    tb = self.bot.exception(exc)
                    await warn(self.bot, "Vote Reminder", u, f"Error while sending vote reminder:\n\n{tb}")
                    continue

    @post_stats.before_loop
    @votereminder.before_loop
    async def before_tasks(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=24)
    async def holiday_announcing(self):
        now = datetime.now()
        then = now + timedelta(hours=24)
        
        for guild in self.bot.cache.holiday_announcements.keys():
            data = self.bot.cache.holiday_announcements[guild]
            if not data['toggle']:
                continue

            dates = getattr(holidays, data['country'])(years=date.today().year)
            celebrate = dates.get(date.today())
            if not celebrate:
                continue

            if data['last_announce'] == date.today():
                continue

            c_id = data['channel_id']
            try:
                channel = await self.bot.fetch_channel(c_id)
            except:
                continue
            if channel is None:
                continue

            mention = ""
            if data['role_id']:
                if data['role_id'] == guild:
                    mention = "@everyone, "
                else:
                    mention = f"<@&{data['role_id']}>, "

            message = data['message']
            await channel.send(f"{mention}{message.replace('{{holiday}}', celebrate)}", allowed_mentions=discord.AllowedMentions(roles=True, everyone=True))
            self.bot.cache.holiday_announcements[guild]['last_announce'] = date.today()
            await self.bot.db.execute("UPDATE holiday_announcements SET last_announce = $1 WHERE guild_id = $2", date.today(), guild)

        now = datetime.now()
        interval = then - now
        # self.holiday_announcing.change_interval(hours=interval.hours, minutes=interval.minutes, seconds=interval.seconds)

    @holiday_announcing.before_loop
    async def holiday_announcing_before(self):
        await self.bot.wait_until_ready()
        now = datetime.now()
        then = datetime.now()
        then = then.replace(hour=22, minute=46, second=0)
        if then < now:
            then = then + timedelta(hours=24)
        await asyncio.sleep((then - now).total_seconds())

def setup(bot):
    pass
