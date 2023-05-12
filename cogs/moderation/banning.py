import asyncio
from datetime import datetime
from typing import Union

import discord
from core.commands import commandExtra
from discord.ext import commands
from utils import checks
from core import i18n

from .__actions import ModAction as action
from core.cog import SubCog

class Banning(SubCog, category="Banning"):
    def __init__(self, bot):
        self.bot = bot

    @commandExtra(category="Banning")
    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, members: commands.Greedy[Union[discord.Member, int]], *, reason: str = None):
        if (arg := ctx.message.content.replace(ctx.prefix, '').replace(ctx.invoked_with, '').strip()) and not members:
            return await ctx.send(_("`{0}` is not the name of any member in this server!").format(arg))
        if not members:
            raise commands.MissingRequiredArgument(list(ctx.command.clean_params.values())[0])
        await ctx.send(_("{0} | Processing bans...").format(ctx.emoji.loading))
        file = None
        y = []
        n = {}
        bans = [x.user.id for x in await ctx.guild.bans()]
        for m in set(members):
            if isinstance(m, int):
                m = self.bot.get_user(m)
                if m is None:
                    try:
                        m = await self.bot.fetch_user(m)
                    except:
                        n[m] = 1
                        continue
            if isinstance(m, discord.Member):
                if m.top_role.position >= ctx.guild.me.top_role.position:
                    n[m] = 2
                    file=discord.File("db/images/role_position.png", filename="role.png")
                    continue
                elif m.top_role.position >= ctx.author.top_role.position:
                    n[m] = 3
                    continue
                elif m.guild_permissions.administrator:
                    n[m] = 5
                    continue
            if m.id in bans:
                n[m] = 4
                continue
            try:
                self.bot.cache.modactions.append(m.id)
                await ctx.guild.ban(discord.Object(id=m.id), reason=reason or _("No reason given."))
                y.append(m)
            except Exception:
                n[m] = 6
                continue

        e = discord.Embed(color=ctx.embed_color, timestamp=datetime.utcnow())
        e.set_author(icon_url=ctx.guild.icon.url, name=ctx.guild.name)
        if not n and len(y) == 1:
            e.description = "<:member_remove:598208865447837709> | " + _("Successfully banned **{0}** from the server!").format(list(y)[0].name)
            self.bot.dispatch('ban', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, target=y[0]))
        elif not n and len(y) > 1:
            e.description = "<:member_remove:598208865447837709> | " + _("Successfully banned **{0} members** from the server!").format(str(len(y)))
            self.bot.dispatch('massban', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, targets=y))
        else:
            if len(y) != 0:
                e.description = "<:member_remove:598208865447837709> | " + _("Successfully banned **{0} members** from the server!").format(str(len(y)))
                self.bot.dispatch('massban', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, targets=y))
            d = []
            hasimg = False
            for x in n:
                if n[x] == 1:
                    d.append(_("`{0}` - Invalid user").format(x))
                elif n[x] == 2:
                    d.append(_("`{0}` - Their top role is above __my__ top role").format(x))
                    if not hasimg:
                        e.set_image(url="attachment://role.png")
                        hasimg = True
                elif n[x] == 3:
                    d.append(_("`{0}` - Their top role is above __your__ top role").format(x))
                elif n[x] == 4:
                    d.append(_("`{0}` - Already banned").format(x))
                elif n[x] == 5:
                    d.append(_("`{0}` - You can't ban an administrator").format(x))
                elif n[x] == 6:
                    d.append(_("`{0}` - Reason unknown").format(x))

            if (len(y) + len(n.keys())) < len(members):
                d.append("\u200b")
                d.append(_("There was/were `{0}` member(s) I could not ban because one of the given arguments was not a member!").format(str(len(members) - len(y) - len(n.keys()))))

            e.add_field(name=_("I could not ban the following member(s):"), value="\n".join(d))

        await ctx.send(embed=e, file=file)

    @commandExtra(category="Banning")
    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, members: commands.Greedy[Union[discord.Member, discord.User, int]], *, reason: str = None):
        if (arg := ctx.message.content.replace(ctx.prefix, '').replace(ctx.invoked_with, '').strip()) and not members:
            return await ctx.send(_("`{0}` is not the name of any member in this server!").format(arg))
        if not members:
            raise commands.MissingRequiredArgument(list(ctx.command.clean_params.values())[0])
        await ctx.send(_("{0} | Processing unbans...").format(ctx.emoji.loading))
        y = []
        n = {}
        bans = [x.user.id for x in await ctx.guild.bans()]
        for m in set(members):
            if isinstance(m, discord.Member):
                n[m] = 1
                continue
            elif isinstance(m, discord.User):
                if m.id not in bans:
                    n[m] = 2
                    continue
            elif isinstance(m, int):
                try:
                    m = await self.bot.fetch_user(m)
                except:
                    n[m] = 3
                    continue
            if m.id not in bans:
                n[m] = 2
                continue
            try:
                self.bot.cache.modactions.append(m.id)
                await ctx.guild.unban(discord.Object(id=m.id), reason=reason or _("No reason given."))
                y.append(m)
            except Exception as e:
                n[m] = 4
                continue

        e = discord.Embed(color=ctx.embed_color, timestamp=datetime.utcnow())
        e.set_author(icon_url=ctx.guild.icon.url, name=ctx.guild.name)
        if not n and len(y) == 1:
            e.description = "<:member_remove:598208865447837709> | " + _("Successfully unbanned **{0}** from the server!").format(y[0].name)
            self.bot.dispatch('unban', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, target=y[0]))
        elif not n and len(y) > 1:
            e.description = "<:member_remove:598208865447837709> | " + _("Successfully unbanned **{0} members** from the server!").format(str(len(y)))
            self.bot.dispatch('massunban', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, targets=y))
        else:
            if len(y) != 0:
                e.description = "<:member_remove:598208865447837709> | " + _("Successfully unbanned **{0} members** from the server!").format(str(len(y)))
                self.bot.dispatch('massunban', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, targets=y))
            d = []
            for x in n:
                if n[x] == 1:
                    d.append(_("`{0}` - Member is in server").format(x))
                elif n[x] == 2:
                    d.append(_("`{0}` - Member not banned").format(x))
                elif n[x] == 3:
                    d.append(_("`{0}` - Invalid user").format(x))
                elif n[x] == 4:
                    d.append(_("`{0}` - Reason unknown").format(x))

            if (len(y) + len(n.keys())) < len(members):
                d.append("\u200b")
                d.append(_("There was/were `{0}` member(s) I could not unban because one of the given arguments was not a member!").format(str(len(members) - len(y) - len(n.keys()))))

            e.add_field(name=_("I could not unban the following member(s):"), value="\n".join(d))

        await ctx.send(embed=e)

    @commandExtra(category="Banning")
    @commands.guild_only()
    @checks.has_permissions(kick_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def softban(self, ctx, members: commands.Greedy[Union[discord.Member, int]], *, reason: str = None):
        if (arg := ctx.message.content.replace(ctx.prefix, '').replace(ctx.invoked_with, '').strip()) and not members:
            return await ctx.send(_("`{0}` is not the name of any member in this server!").format(arg))
        if not members:
            raise commands.MissingRequiredArgument(list(ctx.command.clean_params.values())[0])
        await ctx.send(_("{0} | Processing softbans...").format(ctx.emoji.loading))
        file = None
        y = []
        n = {}
        for m in set(members):
            if isinstance(m, int):
                try:
                    mem = await self.bot.fetch_user(m)
                    n[mem] = 1
                except:
                    n[m] = 2
                continue
            elif m.top_role.position >= ctx.guild.me.top_role.position:
                n[m] = 3
                file=discord.File("db/images/role_position.png", filename="role.png")
                continue
            elif m.top_role.position >= ctx.author.top_role.position:
                n[m] = 4
                continue
            try:
                self.bot.cache.modactions.append(m.id)
                await m.ban(reason=reason or _("No reason given."))
                try:
                    await self.bot.wait_for('member_ban', check=lambda u: u.id == m.id and u.guild.id == ctx.guild.id, timeout=3)
                except asyncio.TimeoutError:
                    pass
                self.bot.cache.modactions.append(m.id)
                await ctx.guild.unban(discord.Object(id=m.id), reason=reason or _("No reason given."))
                y.append(m)
            except Exception:
                n[m] = 5
                continue

        e = discord.Embed(color=ctx.embed_color, timestamp=datetime.utcnow())
        e.set_author(icon_url=ctx.guild.icon.url, name=ctx.guild.name)
        if not n and len(y) == 1:
            e.description = "<:member_remove:598208865447837709> | " + _("Successfully softbanned **{0}** from the server!").format(y[0].name)
            self.bot.dispatch('softban', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, target=y[0]))
        elif not n and len(y) > 1:
            e.description = "<:member_remove:598208865447837709> | " + _("Successfully softbanned **{0} members** from the server!").format(str(len(y)))
            self.bot.dispatch('masssoftban', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, targets=y))
        else:
            if len(y) != 0:
                e.description = "<:member_remove:598208865447837709> | " + _("Successfully softbanned **{0} members** from the server!").format(str(len(y)))
                self.bot.dispatch('masssoftban', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, targets=y))
            d = []
            hasimg = False
            for x in n:
                if n[x] == 1:
                    d.append(_("`{0}` - Member not in this server"))
                elif n[x] == 2:
                    d.append(_("`{0}` - Invalid user"))
                elif n[x] == 3:
                    d.append(_("`{0}` - Their top role is above __my__ top role").format(x))
                    if not hasimg:
                        e.set_image(url="attachment://role.png")
                        hasimg = True
                elif n[x] == 4:
                    d.append(_("`{0}` - Their top role is above __your__ top role").format(x))
                elif n[x] == 5:
                    d.append(_("`{0}` - Reason unknown").format(x))

            if (len(y) + len(n.keys())) < len(members):
                d.append("\u200b")
                d.append(_("There was/were `{0}` member(s) I could not softban because one of the given arguments was not a member!").format(str(len(members) - len(y) - len(n.keys()))))

            e.add_field(name=_("I could not softban the following member(s):"), value="\n".join(d))

        await ctx.send(embed=e, file=file)

    @commandExtra(category="Banning")
    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.max_concurrency(1, per=commands.BucketType.guild, wait=False)
    async def unbanall(self, ctx):
        total_bans = len(await ctx.guild.bans()) 

        unbanned = []

        if total_bans == 0:
            return await ctx.send(_("There are no banned members in this server..."))

        def check(m):
            return m.author == ctx.author

        checkmsg = await ctx.send(_("Are you sure you want to unban all {0} members? **This cannot be undone!** `yes / no`").format(total_bans))
        yes_no = await self.bot.wait_for('message', check=check)

        if yes_no.content.lower() == _("yes").lower():
            pass
        elif yes_no.content.lower() == _("no").lower():
            return await ctx.send(_("Okay, I will not unban all members!"), delete_after=15)
        else:
            return

        await checkmsg.delete()

        msg = await ctx.send(_("Unbanning all banned members, this may take a while...") + "  <a:discord_loading:587812494089912340>")
        await asyncio.sleep(3)
        for user in await ctx.guild.bans():
            try:
                await ctx.guild.unban(user.user)
                self.bot.cache.modactions.append(user.user.id)
                unbanned.append(user.user)
                await msg.edit(content=_("Unbanned {0} of {1} members!").format(str(len(unbanned)), total_bans))
            except:
                continue

        self.bot.dispatch('unbanall', action(guild=ctx.guild, mod=ctx.author, targets=unbanned))
        e = discord.Embed(color=ctx.embed_color)
        e.set_author(icon_url=ctx.guild.icon.url, name=ctx.guild.name)
        e.description = _("Successfully unbanned {0} member(s)!").format(str(len(unbanned)))
        await msg.edit(content="\u200B", embed=e, delete_after=10)

def setup(bot):
    pass
