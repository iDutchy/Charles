import argparse
import json
import re
import shlex
from collections import Counter
from datetime import datetime
from typing import Union

import discord
from core import i18n
from core.cog import SubCog
from core.commands import commandExtra, groupExtra
from discord.ext import commands
from utils import checks

from .__actions import ModAction as action


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class Basic(SubCog, category="Basic"):
    def __init__(self, bot):
        self.bot = bot

    async def do_removal(self, ctx, limit, predicate, *, before=None, after=None):
        if limit > 2000:
            return await ctx.send(_("Too many messages to search given ({0}/2000)").format(limit))

        if before is None:
            before = ctx.message
        else:
            before = discord.Object(id=before)

        if after is not None:
            after = discord.Object(id=after)

        try:
            deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
        except:
            return await ctx.send(_("I do not have permissions to delete messages."))

        spammers = Counter(m.author.display_name for m in deleted)
        deleted = len(deleted)
        if deleted == 1:
            messages = [_("1 message was removed.")]
        else:
            messages = [_("{0} messages were removed.").format(deleted)]
        if deleted:
            messages.append('')
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f'**{name}**: {count}' for name, count in spammers)

        to_send = '\n'.join(messages)

        if len(to_send) > 2000:
            await ctx.send(_("Successfully removed {0} messages.").format(deleted), delete_after=10)
        else:
            e = discord.Embed(color=ctx.embed_color)
            e.set_author(icon_url=ctx.guild.icon.url, name=ctx.guild.name)
            e.description = to_send
            await ctx.send(embed=e, delete_after=10)
        await ctx.message.delete()

    @checks.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @commandExtra(name="prune-members", category="Basic")
    async def prune_members(self, ctx, days: int, *, reason=None):
        if days <= 0:
            return await ctx.send(_("Days to prune members should be greater than or equal to 1."))
        if days > 30:
            return await ctx.send(_("Days to prune members should be less than or equal to 30."))

        count = await ctx.guild.estimate_pruned_members(days=days)
        if count == 0:
            return await ctx.send(_("There are no members to prune with an inactivity of {0} days.").format(str(days)))

        check, msg = await ctx.confirm(_("Pruning members that have been inactive for {0}+ days will remove {1} member(s) from this server!\n\nAre you sure you wish to continue?").format(str(days), str(count)))

        if check:
            if ctx.guild.large:
                await ctx.guild.prune_members(days=days, compute_prune_count=False, reason=reason)
            else:
                await ctx.guild.prune_members(days=days, reason=reason)
            if count == 1:
                return await ctx.send(_("1 member has succesfully been removed from the guild!"))
            return await ctx.send(_("{0} members have succesfully been removed from the guild!").format(str(count)))
        return await ctx.send(_("Ok, cancelling member pruning."))

    @commandExtra(category="Basic")
    async def cleanup(self, ctx, amount=50):

        def check(m):
            return m.author == ctx.guild.me or m.content.startswith(ctx.prefix)

        if ctx.me.permissions_in(ctx.channel).manage_messages:
            purge = await ctx.channel.purge(limit=amount, check=check)
            purged = Counter(m.author.display_name for m in purge)
        else:
            count = 0
            async for msg in ctx.history(limit=amount):
                if msg.author == ctx.me:
                    await msg.delete()
                    count += 1
            purged = {ctx.me.display_name: count}

        if len(purged) == 1:
            msg = _("{0} of my messages were deleted!").format(str(purged[ctx.me.display_name]))

        else:
            _msg = [_("Deleted command messages:")]
            users = sorted(purged.items(), key=lambda c: c[1], reverse=True)
            for u, c in users:
                _msg.append(f"- **{u:20}** `{c}`")
            msg = '\n'.join(_msg)
        await ctx.send(msg, delete_after=10)

    @commandExtra(category="Basic")
    @commands.guild_only()
    @checks.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, members: commands.Greedy[Union[discord.Member, int]], *, reason: str = None):
        if (arg := ctx.message.content.replace(ctx.prefix, '').replace(ctx.invoked_with, '').strip()) and not members:
            return await ctx.send(_("`{0}` is not the name of any member in this server!").format(arg))
        if not members:
            raise commands.MissingRequiredArgument(list(ctx.command.clean_params.values())[0])
        await ctx.send(_("{0} | Processing kicks...").format(ctx.emoji.loading))
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
                file = discord.File("db/images/role_position.png", filename="role.png")
                continue
            elif m.top_role.position >= ctx.author.top_role.position:
                n[m] = 4
                continue
            elif m.guild_permissions.administrator:
                n[m] = 5
                continue
            try:
                self.bot.cache.modactions.append(m.id)
                await m.kick(reason=reason or _("No reason given."))
                y.append(m)
            except Exception:
                n[m] = 6
                continue

        e = discord.Embed(color=ctx.embed_color, timestamp=datetime.utcnow())
        e.set_author(icon_url=ctx.guild.icon.url, name=ctx.guild.name)
        if not n and len(y) == 1:
            e.description = "<:member_remove:598208865447837709> | " + _("Successfully kicked **{0}** from the server!").format(y[0].name)
            self.bot.dispatch('kick', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, target=y[0]))
        elif not n and len(y) > 1:
            e.description = "<:member_remove:598208865447837709> | " + _("Successfully kicked **{0} members** from the server!").format(str(len(y)))
            self.bot.dispatch('masskick', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, targets=y))
        else:
            if len(y) != 0:
                e.description = "<:member_remove:598208865447837709> | " + _("Successfully kicked **{0} members** from the server!").format(str(len(y)))
                self.bot.dispatch('masskick', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, targets=y))
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
                    d.append(_("`{0}` - You can't kick an administrator").format(x))
                elif n[x] == 6:
                    d.append(_("`{0}` - Reason unknown").format(x))

            if (len(y) + len(n.keys())) < len(members):
                d.append("\u200b")
                d.append(_("There was/were `{0}` member(s) I could not kick because one of the given arguments was not a member!").format(str(len(members) - len(y) - len(n.keys()))))

            e.add_field(name=_("I could not kick the following member(s):"), value="\n".join(d))

        await ctx.send(embed=e, file=file)

    @commandExtra(category="Basic", aliases=['nick'])
    @commands.guild_only()
    @checks.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    async def nickname(self, ctx, member: discord.Member, *, name: str = None):
        if member.top_role.position >= ctx.guild.me.top_role.position:
            return await ctx.send(_("I could not perform this action due to the role hierarchy. Please make sure my top role is above the top role of `{0}`!").format(str(member)), file=discord.File("db/images/role_position.png"))

        e = discord.Embed(color=ctx.embed_color)

        if name is not None:
            if (n := len(name)) > 32:
                return await ctx.send(_("Sorry, but discord has a limit for nickname lengths which you exceeded... {0}/32").format(n))

            e.description = "<:member_edit:598206376816279577> " + _("Changed **{0}'s** nickname to **{1}**").format(member.name, name)

        e.set_author(icon_url=member.avatar.url, name=member)
        e.description = "<:member_edit:598206376816279577> " + _("Removed **{0}'s** nickname").format(member.name)

        await member.edit(nick=name)

        await ctx.send(embed=e, delete_after=10)

    @commandExtra(category="Basic", aliases=['stfu', 'shush'])
    @commands.guild_only()
    @checks.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx, members: commands.Greedy[Union[discord.Member, int]], *, reason: str = None):
        if (arg := ctx.message.content.replace(ctx.prefix, '').replace(ctx.invoked_with, '').strip()) and not members:
            return await ctx.send(_("`{0}` is not the name of any member in this server!").format(arg))
        if not members:
            raise commands.MissingRequiredArgument(list(ctx.command.clean_params.values())[0])
        await ctx.send(_("{0} | Processing mutes...").format(ctx.emoji.loading))
        file = None
        y = []
        n = {}
        nc = []
        if (rid := self.bot.cache.get("roles", ctx.guild.id, "muted")):
            try:
                muterole = ctx.guild.get_role(rid)
            except:
                return await ctx.send(_("The mute role that has been set could not be found, please set the new 'Muted' role using `{0}set-role muted @newrole`!").format(ctx.prefix))
        muterole = discord.utils.find(lambda r: r.name.lower() == _("muted"), ctx.guild.roles)
        if muterole is None:
            edited = False
            try:
                muterole = await ctx.guild.create_role(name=_("muted").title(), color=discord.Color.greyple())
                mr = [r for r in ctx.me.roles if not r.is_default()]
                if len(mr) != 0 or len(mr) != 1:
                    await muterole.edit(position=ctx.guild.me.top_role.position-1)
                    edited = True
            except Exception:
                return await ctx.send(_("Could not find a role called **{0}** in this server's roles and I was unable to create one. Make sure to create one and try again.").format(_("muted").title()))

            for channel in ctx.guild.text_channels:
                try:
                    await channel.set_permissions(muterole, send_messages=False)
                except:
                    nc.append(channel)

            if edited:
                add = _("The role I created can be used to mute people with the role {0} and lower.").format(ctx.guild.roles[ctx.me.top_role.position-1].mention)
            else:
                add = _("The role I just created is at the bottom of the role list because I couldn't move it higher. Please change the position to where you want to use it.")

            if nc:
                nc = _("I could not find a role called \"{0}\" in this server and no mute role was set in the settings, so I created one for you! But, I didn't have permissions to set permissions for it on all channels. If you give me that permission and run `{1}fix-mute-perms` I will correct all channels settings for the mute role!").format(_("muted").title(), ctx.prefix) + f" {add}"
            else:
                nc = _("I could not find a role called \"{0}\" in this server and no mute role was set in the settings, so I created one for you! I have also set all permissions on each channel for the mute role for you!").format(_("muted").title()) + f" {add}"

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
                file = discord.File("db/images/role_position.png", filename="role.png")
                continue
            elif m.top_role.position >= ctx.author.top_role.position:
                n[m] = 4
                continue
            elif m.top_role.position >= muterole.position:
                n[m] = 5
                continue
            elif m.guild_permissions.administrator:
                n[m] = 6
                continue
            elif muterole in m.roles:
                n[m] = 7
                continue
            try:
                await m.add_roles(muterole, reason=reason or _("No reason given."))
                y.append(m)
            except Exception:
                n[m] = 8
                continue

        e = discord.Embed(color=ctx.embed_color, timestamp=datetime.utcnow())
        e.set_author(icon_url=ctx.guild.icon.url, name=ctx.guild.name)
        if not n and len(y) == 1:
            e.description = "<:member_remove:598208865447837709> | " + _("Successfully muted **{0}**!").format(y[0].name)
            self.bot.dispatch('mute', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, target=y[0]))
        elif not n and len(y) > 1:
            e.description = "<:member_remove:598208865447837709> | " + _("Successfully muted **{0} members**!").format(str(len(y)))
            self.bot.dispatch('massmute', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, targets=y))
        else:
            if len(y) != 0:
                e.description = "<:member_remove:598208865447837709> | " + _("Successfully muted **{0} members**!").format(str(len(y)))
                self.bot.dispatch('massmute', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, targets=y))
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
                    d.append(_("`{0}` - Their top role is above the 'Muted' role").format(x))
                elif n[x] == 6:
                    d.append(_("`{0}` - This user is an administrator, muting them does nothing").format(x))
                elif n[x] == 7:
                    d.append(_("`{0}` - Member already muted").format(x))
                elif n[x] == 8:
                    d.append(_("`{0}` - Reason unknown").format(x))

            if (len(y) + len(n.keys())) < len(members):
                d.append("\u200b")
                d.append(_("There was/were `{0}` member(s) I could not mute because one of the given arguments was not a member!").format(str(len(members) - len(y) - len(n.keys()))))

            e.add_field(name=_("I could not mute the following member(s):"), value="\n".join(d))

            if nc:
                e.add_field(name=_("**Role Warning!**"), value=nc, inline=False)

        await ctx.send(embed=e, file=file)

    @commandExtra(category="Basic")
    @commands.guild_only()
    @checks.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx, members: commands.Greedy[Union[discord.Member, int]], *, reason: str = None):
        if (arg := ctx.message.content.replace(ctx.prefix, '').replace(ctx.invoked_with, '').strip()) and not members:
            return await ctx.send(_("`{0}` is not the name of any member in this server!").format(arg))
        if not members:
            raise commands.MissingRequiredArgument(list(ctx.command.clean_params.values())[0])
        await ctx.send(_("{0} | Processing unmutes..."))
        file = None
        y = []
        n = {}  # TODO: ADD SETTING TO SET CUSTOM ROLES
        muterole = discord.utils.find(lambda r: r.name.lower() == _("muted"), ctx.guild.roles)
        if muterole is None:
            return await ctx.send(_("I could not find a role named \"Muted\" on this server and no mute role has been set! I can't unmute people if the role doesn't exist..."))

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
                file = discord.File("db/images/role_position.png", filename="role.png")
                continue
            elif m.top_role.position >= ctx.author.top_role.position:
                n[m] = 4
                continue
            elif m.top_role.position >= muterole.position:
                n[m] = 5
                continue
            elif muterole not in m.roles:
                n[m] = 6
                continue
            try:
                await m.remove_roles(muterole, reason=reason or _("No reason given."))
                y.append(m)
            except Exception:
                n[m] = 7
                continue

        e = discord.Embed(color=ctx.embed_color, timestamp=datetime.utcnow())
        e.set_author(icon_url=ctx.guild.icon.url, name=ctx.guild.name)
        if not n and len(y) == 1:
            e.description = "<:member_remove:598208865447837709> | " + _("Successfully unmuted **{0}**!").format(y[0].name)
            self.bot.dispatch('unmute', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, target=y[0]))
        elif not n and len(y) > 1:
            e.description = "<:member_remove:598208865447837709> | " + _("Successfully unmuted **{0} members**!").format(str(len(y)))
            self.bot.dispatch('massunmute', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, targets=y))
        else:
            if len(y) != 0:
                e.description = "<:member_remove:598208865447837709> | " + _("Successfully unmuted **{0} members**!").format(str(len(y)))
                self.bot.dispatch('massunmute', action(guild=ctx.guild, mod=ctx.author, reason=reason, failed=n, targets=y))
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
                    d.append(_("`{0}` - Their top role is above the 'Muted' role").format(x))
                elif n[x] == 6:
                    d.append(_("`{0}` - Member not muted").format(x))
                elif n[x] == 7:
                    d.append(_("`{0}` - Reason unknown").format(x))

            if (len(y) + len(n.keys())) < len(members):
                d.append("\u200b")
                d.append(_("There was/were `{0}` member(s) I could not unmute because one of the given arguments was not a member!").format(str(len(members) - len(y) - len(n.keys()))))

            e.add_field(name=_("I could not unmute the following member(s):"), value="\n".join(d))

        await ctx.send(embed=e, file=file)

    @groupExtra(aliases=['delete', 'prune'], category="Basic")
    @commands.guild_only()
    @checks.has_permissions(manage_messages=True)
    async def purge(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @purge.command()
    async def embeds(self, ctx, search=100):
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @purge.command()
    async def files(self, ctx, search=100):
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @purge.command()
    async def images(self, ctx, search=100):
        await self.do_removal(ctx, search, lambda e: len(e.embeds) or len(e.attachments))

    @purge.command(name='all')
    async def _remove_all(self, ctx, search=100):
        await self.do_removal(ctx, search, lambda e: True)

    @purge.command()
    async def user(self, ctx, member: discord.Member, search=100):
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @purge.command()
    async def contains(self, ctx, *, substr: str):
        if len(substr) < 3:
            await ctx.send(_("The content length must be at least 3 characters."))
        else:
            await self.do_removal(ctx, 100, lambda e: substr in e.content)

    @purge.command(name='bot')
    async def _bot(self, ctx, search=100):
        def predicate(m):
            return (m.webhook_id is None and m.author.bot)

        await self.do_removal(ctx, search, predicate)

    @purge.command(name='emoji')
    async def _emoji(self, ctx, search=100):
        custom_emoji = re.compile(r'<:[^\s]+:[0-9]*>')

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command(name='reactions')
    async def _reactions(self, ctx, search=100):
        if search > 2000:
            return await ctx.send(_("Too many messages to search given ({0}/2000)").format(search))

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()

        await ctx.send(_("Successfully removed {0} reactions.").format(total_reactions))

    @purge.command()
    async def custom(self, ctx, *, args: str):
        parser = Arguments(add_help=False, allow_abbrev=False)
        parser.add_argument('--user', nargs='+')
        parser.add_argument('--contains', nargs='+')
        parser.add_argument('--exclude', nargs='+')
        parser.add_argument('--starts', nargs='+')
        parser.add_argument('--ends', nargs='+')
        parser.add_argument('--or', action='store_true', dest='_or')
        parser.add_argument('--not', action='store_true', dest='_not')
        parser.add_argument('--emoji', action='store_true')
        parser.add_argument('--bot', action='store_const', const=lambda m: m.author.bot)
        parser.add_argument('--embeds', action='store_const', const=lambda m: len(m.embeds))
        parser.add_argument('--files', action='store_const', const=lambda m: len(m.attachments))
        parser.add_argument('--reactions', action='store_const', const=lambda m: len(m.reactions))
        parser.add_argument('--search', type=int, default=100)
        parser.add_argument('--after', type=int)
        parser.add_argument('--before', type=int)

        try:
            args = parser.parse_args(shlex.split(args))
        except Exception as e:
            await ctx.send(str(e))
            return

        predicates = []
        if args.bot:
            predicates.append(args.bot)

        if args.embeds:
            predicates.append(args.embeds)

        if args.files:
            predicates.append(args.files)

        if args.reactions:
            predicates.append(args.reactions)

        if args.emoji:
            custom_emoji = re.compile(r'<:(\w+):(\d+)>')
            predicates.append(lambda m: custom_emoji.search(m.content))

        if args.user:
            users = []
            converter = commands.MemberConverter()
            for u in args.user:
                try:
                    user = await converter.convert(ctx, u)
                    users.append(user)
                except Exception as e:
                    await ctx.send(str(e))
                    return

            predicates.append(lambda m: m.author in users)

        if args.contains:
            contains = "".join(args.contains)
            if args.embeds:
                predicates.append(lambda m: any(sub in json.dumps(m.embeds[0].to_dict()) for sub in contains.split('|') if m.embeds))
            else:
                predicates.append(lambda m: any(sub in m.content for sub in contains.split('|')))

        if args.exclude:
            excl = "".join(args.exclude)
            if args.embeds:
                predicates.append(lambda m: all(sub not in json.dumps(m.embeds[0].to_dict()) for sub in excl.split('|') if m.embeds))
            else:
                predicates.append(lambda m: all(sub not in m.content for sub in excl.split('|')))

        if args.starts:
            predicates.append(lambda m: any(m.content.startswith(s) for s in args.starts))

        if args.ends:
            predicates.append(lambda m: any(m.content.endswith(s) for s in args.ends))

        op = all if not args._or else any

        def predicate(m):
            r = op(p(m) for p in predicates)
            if args._not:
                return not r
            return r

        args.search = max(0, min(2000, args.search))  # clamp from 0-2000
        await self.do_removal(ctx, args.search, predicate, before=args.before, after=args.after)


def setup(bot):
    pass
