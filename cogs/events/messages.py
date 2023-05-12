import asyncio
import json
import re
from datetime import datetime

import discord
from core import i18n
from core.cog import SubCog
from discord.ext import commands
from utils.humanize_time import timesince
from utils.utility import unflag, warn


class MessageEvents(SubCog):
    def __init__(self, bot):
        self.bot = bot
        self.translated = []

    @commands.Cog.listener()
    async def on_private_channel_create(self, channel):
        e = discord.Embed(color=0x2F3136, title="Hey there!", description="Your DMs are logged in my support server, this is to provide quick support or have a nice chat with my dev. Abuse of this (eg inappropriate content) will result in a block from my DMs.\n\nTo opt-out and disable your DMs from being logged, simply say the magic phrase 'I Solemnly Swear That I Am Up To No Good' (case sensitive). To opt-in again, say 'Mischief Managed' :)")
        e.set_footer(text="To use my commands, use the c?help command in your server. Commands in DMs are currently unavailable...")
        await channel.send(embed=e)

    @commands.Cog.listener('on_message')
    async def dms_opt_out_check(self, msg):
        if msg.guild:
            return
        if msg.author.bot:
            return

        chan = self.bot.get_channel(520042138264797185)
        if msg.content == 'I Solemnly Swear That I Am Up To No Good':
            user = self.bot.get_user_cache(msg.author.id)
            await user.set_dms(toggle=False)
            await chan.send(f"*`{msg.author}` ({msg.author.id}) opted out of DM logging...*")
        if msg.content == 'Mischief Managed':
            user = self.bot.get_user_cache(msg.author.id)
            await user.set_dms(toggle=True)
            await chan.send(f"*`{msg.author}` ({msg.author.id}) re-enabled DM logging!*")

    @commands.Cog.listener('on_raw_reaction_add')
    async def flag_translator(self, payload):
        cache = self.bot.get_cache(payload.guild_id)
        if not cache.rtt:
            return

        # if not payload.guild.chunked:
        #     await payload.guild.chunk()

        if payload.member.bot:
            return

        if payload.message_id in self.translated:
            return

        flag = unflag(str(payload.emoji))
        if not flag.startswith(":"):
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        if not message.content:
            return

        exceptions = {
            "us": "en",
            "um": "en",
            "gb": "en",
            "jp": "ja"
        }

        flag = flag.strip(":").lower()
        flag = exceptions.get(flag, flag)
        trans = await self.bot.utils.translate(message.content, flag)
        if not trans:
            return

        with open('db/Languages.json') as f:
            d = json.load(f)

        to_name = flag
        for lcode in d:
            if lcode['code'] == flag:
                to_name = lcode['name']

        e = discord.Embed(color=cache.color, title=f"Translation to {payload.emoji} **{to_name}**", description=trans, timestamp=datetime.utcnow())
        e.set_author(icon_url=message.author.avatar.url, name=f"{message.author} said:")
        e.set_footer(icon_url=payload.member.avatar.url, text=f"Requested by: {payload.member}")
        await channel.send(embed=e)
        self.translated.append(payload.message_id)
        await asyncio.sleep(150)
        self.translated.remove(payload.message_id)

    @commands.Cog.listener('on_message')
    async def afk_mention_check(self, msg):
        if not msg.guild:
            return
        if msg.author.bot:
            return
        if not msg.mentions:
            return

        for x in list(map(int, msg.mentions)):
            if x not in self.bot.cache.afk:
                continue
            else:
                u = await msg.guild.try_member(x)
                if u is None:
                    del self.bot.cache.afk[x]
                else:
                    await msg.reply(_("Hey, sorry to bother. But **{0}** went afk {1} ago for: `{2}`.").format(str(u), timesince(self.bot.cache.afk[x]['afk_set'], add_suffix=False), self.bot.cache.afk[x]['reason']))

    @commands.Cog.listener('on_message')
    async def afk_remove(self, msg):
        if not msg.guild:
            return
        if msg.author.bot:
            return
        if msg.author.id not in self.bot.cache.afk:
            return
        if (datetime.utcnow() - self.bot.cache.afk[msg.author.id]['afk_set']).total_seconds() <= 1:
            return

        del self.bot.cache.afk[msg.author.id]
        await self.bot.db.execute("DELETE FROM afk WHERE user_id = $1", msg.author.id)

        i18n.set_locale(self.bot.cache.get("settings", msg.guild.id, 'language'))
        try:
            await msg.reply(_("Welcome back, {0}! I have removed your AFK status.").format(msg.author.mention))
        except:
            try:
                await msg.author.send(_("Welcome back! I have removed your AFK status. I was unable to send a message there so here's a DM!").format(msg.guild.name))
            except:
                return

    # @commands.Cog.listener('on_message')
    # async def embed_mentions_check(self, msg):
    #     if not msg.author.bot:
    #         return
    #     if not msg.embeds:
    #         return
    #     txt = json.dumps(msg.embeds[0].to_dict())
    #     mentions = re.findall(r"<@(!?)([0-9]+)>", txt)
    #     if not mentions:
    #         return

    #     users = list(set([int(x[1]) for x in mentions]))
    #     for _id in users:
    #         cache = self.bot.get_user_cache(_id)
    #         em = cache.embedmentions
    #         if not em:
    #             continue
    #         if not em.globally:
    #             if msg.guild.id not in em.guilds:
    #                 continue

    #         if not msg.guild.chunked:
    #             await msg.guild.chunk()
    #         if not msg.guild.get_member(_id):
    #             continue

    #         try:
    #             await self.bot.wait_for('message', check=lambda m: m.author.id == _id and m.channel.id == msg.channel.id, timeout=10)
    #         except asyncio.TimeoutError:
    #             user = await self.bot.try_user(_id)
    #             msg = f"Hey {user.mention}! You have been mentioned in an embed in **{msg.guild.name}**.\n\nMessage link: {msg.jump_url}"
    #             try:
    #                 await user.send(msg)
    #             except:
    #                 continue
    #         else:
    #             continue

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        if not message.guild and message.author.id in self.bot.cache.get('blacklist', 'dm'):
            blockeddm = discord.Embed(description="<:banhammer:523695899726053377> **DM Block!**", color=0xff1414)
            blockeddm.set_footer(text="Sorry, but my owner blocked your DM's to me. If you wish to appeal, contact him. | Dutchy#6127")
            return await message.author.send(embed=blockeddm)

        if message.guild is None:
            if message.author.id in self.bot.cache.translate_sessions.keys():
                return
            if message.content in ('I Solemnly Swear That I Am Up To No Good', 'Mischief Managed'):
                return
            user = self.bot.get_user_cache(message.author.id)
            if not user.dms:
                return
            # if message.content.lower().startswith("c?"):
            #     return await message.author.send("Hey there! In my DMs you can use commands without a prefix :)")

            logchannel = self.bot.get_channel(520042138264797185)
            if message.author.id not in (dms := self.bot.cache.dms.keys()):
                _id = self.bot.cache.update("dms", message.author.id, len(dms)+1)
            else:
                _id = self.bot.cache.get("dms", message.author.id)
            msgembed = discord.Embed(title=f"{message.author} | ID: {_id}",
                                     description=message.content,
                                     color=0x638ccf)
            msgembed.set_thumbnail(url=message.author.avatar.with_static_format("png"))
            if message.attachments:
                attachment_url = message.attachments[0].url
                msgembed.set_image(url=attachment_url)
            await logchannel.send(embed=msgembed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot:
            return

        if before.content == after.content:
            return

        ctx = await self.bot.get_context(after)
        if ctx.valid:
            await self.bot.process_commands(after)

        if cid := self.bot.cache.get("logging", before.guild.id, "msgedit_channel"):
            i18n.set_locale(self.bot.cache.get("settings", before.guild.id, 'language'))

            embed = discord.Embed(title=_("Message Edited"),
                                color=0xcb5f06,
                                timestamp=datetime.utcnow(),
                                description=_("Message by {0} edited in {1}").format(before.author, before.channel.mention))
            embed.set_author(name=before.author,icon_url=before.author.avatar.with_static_format("png"))
            embed.add_field(name=_("**Before**"), value=(before.content[:1021]+"...") if len(before.content) > 1024 else before.content, inline=False)
            embed.add_field(name=_("**After**"), value=(after.content[:1021]+"...") if len(after.content) > 1024 else after.content, inline=False)
            embed.set_footer(text=_("Message ID: {0}").format(before.id))

            channel = before.guild.get_channel(cid)
            try:
                await channel.send(embed=embed)
            except Exception:
                return
        else:
            return

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        if not message.guild:
            return

        if cid := self.bot.cache.get("logging", message.guild.id, "msgdel_channel"):
            i18n.set_locale(self.bot.cache.get("settings", message.guild.id, 'language'))
            embed = discord.Embed(title=_("Message Deleted"),
                                color=0xe94e51,
                                timestamp=datetime.utcnow())
            if message.content:
                inf = _("Message from {0} deleted in {1}").format(message.author, message.channel.mention)
                if message.guild.me.guild_permissions.view_audit_log:
                    entry = (await message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete).flatten())[0]
                    inf += ", "
                    inf += _("deleted by {0}").format(entry.user)
                inf += "\n\n"
                embed.description = inf + (message.content if len(message.content) < (2048-len(inf)) else message.content[:2048-len(inf)])
            if message.attachments:
                if not message.content:
                    embed.description = _("Message did not contain any content, but it did contain an image *which may not be visible*.")
                embed.set_image(url=message.attachments[0].proxy_url)
            if not message.content and not message.attachments:
                await warn(self.bot, "Message Delete", message.guild, "Log could not be sent because message didn't contain any content ot image. So idk what it did, must've been some weird voodoo stuff.")
                return

            embed.set_footer(text=_("Message ID: {0}").format(message.id))

            channel = message.guild.get_channel(cid)
            try:
                await channel.send(embed=embed)
            except Exception:
                return
        else:
            return

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if payload.message_id not in self.bot.cache.rr.keys():
            return

        self.bot.cache.rr.pop(payload.message_id)
        await self.bot.db.execute("DELETE FROM reactionroles WHERE message_id = $1", payload.message_id)

    # @commands.Command() #TODO: FIX CTX STUFF
    # async def on_raw_bulk_message_delete(self, payload):
    #     if self.bot.gc[str(payload.guild_id)]["logging"]["msgdel"]["toggle"]:
    #         guild = self.bot.get_guild(payload.guild_id)
    #         embed=discord.Embed(title=,
    #                             color=0xe94e51,
    #                             description=_(ctx, "events", "events.obmd_count"),
    #                             timestamp=datetime.utcnow())

    #         channel = guild.get_channel(self.bot.gc[str(payload.guild_id)]["logging"]["msgdel"]["channel"])
    #         try:
    #             await channel.send(embed=embed)
    #         except Exception:
    #             return


def setup(bot):
    pass
