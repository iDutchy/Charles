import discord

from discord.ext import commands
from db import tokens
from utils.utility import warn
from core.cog import SubCog

class GuildEvents(SubCog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        logchannel = self.bot.get_channel(520047388950396928)

        e=discord.Embed(title="Left a guild...", color=0x307EC4)
        e.set_thumbnail(url=guild.icon.url)
        e.description=f"**Guild name:** {guild.name}\n{guild.member_count} members"
        await logchannel.send(embed=e)

        await self.bot.db.execute("DELETE FROM guilds WHERE guild_id = $1", guild.id)
        self.bot.cache.delete_guild(guild.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        logchannel = self.bot.get_channel(520047388950396928)
        blacklisted_guilds = self.bot.cache.get('blacklist', 'guild')
        if guild.id in blacklisted_guilds:
            e = discord.Embed(color=0xff6047, title="Attempted Invite", description=f"A blacklisted guild ({guild.name}) attempted to invite me.")
            e.set_thumbnail(url=guild.icon.url)
            await logchannel.send(embed=e)
            return await guild.leave()

        await self.bot.db.add_guild(guild.id)
        self.bot.cache.add_guild(guild.id)
        # await guild.chunk()

        # try:
        to_send = discord.utils.find(lambda c: "general" in c.name.lower(), guild.text_channels)
        if to_send is None or not to_send.permissions_for(guild.me).send_messages:
            to_send = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages][0]
            if to_send is None:
                return

        if to_send.permissions_for(guild.me).embed_links:
            e = discord.Embed(color=0x307EC4, title="Thank you for adding me!")
            e.description = "I'm here to help you have a nice server. I do however have a small announcement from my developer.\n\nUnfortunately, due to this bot not having the success I hoped for, I will no longer be pushing updates to this bot. It will stay online and work as far as it works, but nothing new will be added anymore.\n\nIf you like gaming, please consider adding my new bot project! You can play games in discord (Cards Against Humanity, Guess Who and a lot more!), connect your gaming platforms, get notified about free games, set twitch live notifications and a lot more! This bot is actively maintained and will have many more updates to come.\n- [Invite](https://discord.com/oauth2/authorize?client_id=747984555352260750&scope=bot+applications.commands&permissions=388160)\n- [Support](https://discord.gg/TvqYBrGXEm)"
            await to_send.send(embed=e)
        else:
            msg = "I'm here to help you have a nice server. I do however have a small announcement from my developer.\n\nUnfortunately, due to this bot not having the success I hoped for, I will no longer be pushing updates to this bot. It will stay online and work as far as it works, but nothing new will be added anymore.\n\nIf you like gaming, please consider adding my new bot project! You can play games in discord (Cards Against Humanity, Guess Who and a lot more!), connect your gaming platforms, get notified about free games, set twitch live notifications and a lot more! This bot is actively maintained and will have many more updates to come.\n- Invite: https://discord.com/oauth2/authorize?client_id=747984555352260750&scope=bot+applications.commands&permissions=388160\n- Support: https://discord.gg/TvqYBrGXEm"
            await to_send.send(msg)
        # except Exception as e:
        #     await warn(self.bot, "Guild Join Message", guild, e)

        tch = len(guild.text_channels)
        vch = len(guild.voice_channels)
        e=discord.Embed(title="Joined a new guild!", color=0x307EC4)
        e.set_thumbnail(url=guild.icon.url)
        e.description=f"**Guild name:** {guild.name}\n**Guild owner:** {guild.owner}\n**Guild ID:** {guild.id}\n\n{guild.member_count} members\n{tch} text channels\n{vch} voice channels\n\n"
        if (em := len(guild.emojis)) > 0:
            if em > 25:
                e.description += f"\n\n__**Custom emoji:**__\n{', '.join([str(e) for e in guild.emojis if e.is_usable()][:25])} `(+{em-25})`"
            else:
                e.description += f"\n\n__**Custom emoji:**__\n{', '.join([str(e) for e in guild.emojis if e.is_usable()])}"
        await logchannel.send(embed=e)

        humans = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)
        perc_h = 100/guild.member_count*humans
        perc_b = 100/guild.member_count*bots
        if perc_b > 50:
            e = discord.Embed(color=0x961002,
                              title="Possible Bot Farm!")
            e.description = f"Server {guild.name} `({guild.id})` could be a bot farm!\n\n**Total Members:** {guild.member_count}\n**Humans:** {humans} ({perc_h}%)\n**Bots:** {bots} ({perc_b}%)"
            e.set_author(name=guild.name,icon_url=guild.icon.url)
            await logchannel.send(embed=e)

    @commands.Cog.listener('on_ready')
    async def offline_guild_join(self):
        bot_guilds = [g.id for g in self.bot.guilds]
        blacklisted_guilds = self.bot.cache.get('blacklist', 'guild')
        db_guilds = [x for x, in await self.bot.db.fetch("SELECT guild_id FROM guilds")]
        for x in blacklisted_guilds:
            if x in bot_guilds:
                await guild.leave()

        for x in bot_guilds:
            if not x in db_guilds:
                await self.bot.db.add_guild(x)
                self.bot.cache.add_guild(x)

def setup(bot):
    pass
