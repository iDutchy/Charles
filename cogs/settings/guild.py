import json
import typing
from datetime import date

import discord
import holidays
from core import i18n
from core.cog import SubCog
from core.commands import commandExtra, flagsPlus, groupExtra
from discord.ext import commands, flags
from utils import checks


class GuildSettings(SubCog, category="Server Settings"):
    def __init__(self, bot):
        self.bot = bot

    @checks.has_permissions(manage_guild=True)
    @groupExtra(name="perms", invoke_without_command=True)
    async def perms(self, ctx):
        await ctx.send_help(ctx.command)

    @flags.add_flag('-r', '--role', type=discord.Role, default=None)
    @flags.add_flag('-u', '--user', type=discord.Member, default=None)
    @flags.add_flag('-c', '--channel', type=discord.TextChannel, default=None)
    @checks.has_permissions(manage_guild=True)
    @perms.command(name='allow', cls=flagsPlus)
    async def perms_allow(self, ctx, perm: str.lower, **flags):
        if len(perm.split('.')) != 2:
            return await ctx.send(_("Invalid permission passed, please see the help if you're not sure what to put as permission!"))

        all_perms = []
        for cmd in self.bot.walk_commands():
            if hasattr(cmd, 'perm_names'):
                all_perms += cmd.perm_names
            if hasattr(cmd, 'category'):
                all_perms += cmd.category.perm_names

        if perm not in all_perms:
            return await ctx.send(_("Invalid permission specified! Permissions follow a specific format, here's a reminder:\n\n> To set perms for a module:\nperm = `<module name>.*`\n> To set perms for a category (all commands in that category are affected):\nperm = `<category name>.*`\n> To set perms for a single command:\nperms = `<command's module name>.<command name>`\n\nDont forget: permission settings are all in lowercase and spaces are removed! And for subcommands, write them like `maincommand_subcommand` (so with an underscore)"))

        catmod, cmd = perm.split('.')
        if cmd != "*":
            try:
                await self.bot.get_command(cmd.replace('_', ' ')).can_run(ctx)
            except:
                return await ctx.send(_("You cant set permissions for a command you dont have access to!"))
            else:
                pass
            if self.bot.get_command(cmd.replace('_', ' ')).cog_name.lower() == "owner" and ctx.author.id != self.bot.owner_id:
                return await ctx.send(_("Only the official owner can set permissions for owner commands!"))
        if (catmod == "owner" or catmod in [ct.lower().replace(' ', '') for ct in self.bot.cogs["Owner"]._subcogs.keys()]) and ctx.author.id != self.bot.owner_id:
            return await ctx.send(_("Only the official owner can set permissions for owner modules/categories!"))

        cog = self.bot.get_cog(catmod.title())
        if cog:
            if cmd != "*":
                command = self.bot.get_command(cmd.replace('_', ' '))
                if command.cog.qualified_name == cog.qualified_name:
                    try:
                        await command.can_run(ctx)
                    except:
                        pass
            else:
                for command in cog.get_commands():
                    try:
                        await command.can_run(ctx)
                    except:
                        return await ctx.send(_("You do not have permissions to all commands in this module, therefore you cannot set permissions for it!"))
                    else:
                        continue
        else:
            for cat in self.bot.categories.values():
                if cat.name.lower().replace(' ', '') == catmod:
                    for command in cat.commands:
                        try:
                            await command.can_run(ctx)
                        except:
                            return await ctx.send(_("You do not have permissions to all commands in this category, therefore you cannot set permissions for it!"))
                        else:
                            continue

        r, u, c = flags.get('role'), flags.get('user'), flags.get('channel')
        check = len(list(filter(None, [r, u, c])))
        if check == 0:
            return await ctx.send(_("Please use 1 of the flags to set who or what you want to set a permission for!"))
        if check > 1:
            return await ctx.send(_("Please only use 1 flag for setting permissions!"))

        if u:
            if ctx.author.id != self.bot.owner_id:
                if u == ctx.author:
                    return await ctx.send(_("You cannot set permissions for yourself..."))
                if u.top_role >= ctx.author.top_role:
                    return await ctx.send(_("You can't set permissions for people who have an equal or higher role than you in the hierarchy."))
            if perm in ctx.cache.get_allowed_perms(u.id):
                return await ctx.send(_("These permissions have already been enabled for this user!"))
            await ctx.cache.update_perms(u.id, perm)

        if r:
            if ctx.author.id != self.bot.owner_id:
                if r >= ctx.author.top_role:
                    return await ctx.send(_("This role is your top role or even higher than your top role. So you can't set permissions for it..."))
            if perm in ctx.cache.get_allowed_perms(r.id):
                return await ctx.send(_("These permissions have already been enabled for this role!"))
            await ctx.cache.update_perms(r.id, perm)

        if c:
            if perm in ctx.cache.get_allowed_perms(c.id):
                return await ctx.send(_("These permissions have already been enabled for this channel!"))
            await ctx.cache.update_perms(c.id, perm)

        await ctx.send(_("The `{0}` permission has successfully been updated for {1.mention}!").format(perm, u or r or c), allowed_mentions=discord.AllowedMentions.none())

    @flags.add_flag('-r', '--role', type=discord.Role, default=None)
    @flags.add_flag('-u', '--user', type=discord.Member, default=None)
    @flags.add_flag('-c', '--channel', type=discord.TextChannel, default=None)
    @checks.has_permissions(manage_guild=True)
    @perms.command(name='deny', cls=flagsPlus)
    async def perms_deny(self, ctx, perm: str.lower, **flags):
        if len(perm.split('.')) != 2:
            return await ctx.send(_("Invalid permission passed, please see the help if you're not sure what to put as permission!"))

        all_perms = []
        for cmd in self.bot.walk_commands():
            if hasattr(cmd, 'perm_names'):
                all_perms += cmd.perm_names
            if hasattr(cmd, 'category'):
                all_perms += cmd.category.perm_names

        if perm not in all_perms:
            return await ctx.send(_("Invalid permission specified! Permissions follow a specific format, here's a reminder:\n\n> To set perms for a module:\nperm = `<module name>.*`\n> To set perms for a category (all commands in that category are affected):\nperm = `<category name>.*`\n> To set perms for a single command:\nperms = `<command's category name>.<command name>`\n\nDont forget: permission settings are all in lowercase and spaces are removed!"))

        catmod, cmd = perm.split('.')
        if cmd != "*":
            try:
                await self.bot.get_command(cmd.replace('_', ' ')).can_run(ctx)
            except:
                return await ctx.send(_("You cant set permissions for a command you dont have access to!"))
            else:
                pass
            if self.bot.get_command(cmd.replace('_', ' ')).cog_name.lower() == "owner" and ctx.author.id != self.bot.owner_id:
                return await ctx.send(_("Only the official owner can set permissions for owner commands!"))
        if (catmod == "owner" or catmod in [ct.lower().replace(' ', '') for ct in self.bot.cogs["Owner"]._subcogs.keys()]) and ctx.author.id != self.bot.owner_id:
            return await ctx.send(_("Only the official owner can set permissions for owner modules/categories!"))

        cog = self.bot.get_cog(catmod.title())
        if cog:
            if cmd != "*":
                command = self.bot.get_command(cmd.replace('_', ' '))
                if command.cog.qualified_name == cog.qualified_name:
                    try:
                        await command.can_run(ctx)
                    except:
                        pass
            else:
                for command in cog.get_commands():
                    try:
                        await command.can_run(ctx)
                    except:
                        return await ctx.send(_("You do not have permissions to all commands in this module, therefore you cannot set permissions for it!"))
                    else:
                        continue

        r, u, c = flags.get('role'), flags.get('user'), flags.get('channel')
        check = len(list(filter(None, [r, u, c])))
        if check == 0:
            return await ctx.send(_("Please use 1 of the flags to set who or what you want to set a permission for!"))
        if check > 1:
            return await ctx.send(_("Please only use 1 flag for setting permissions!"))

        if u:
            if ctx.author.id != self.bot.owner_id:
                if u == ctx.author:
                    return await ctx.send(_("You cannot set permissions for yourself..."))
                if u.top_role >= ctx.author.top_role:
                    return await ctx.send(_("You can't set permissions for people who have an equal or higher role than you in the hierarchy."))
            if perm in ctx.cache.get_denied_perms(u.id):
                return await ctx.send(_("These permissions have already been disabled for this user!"))
            await ctx.cache.update_perms(u.id, perm, False)

        if r:
            if ctx.author.id != self.bot.owner_id:
                if r >= ctx.author.top_role:
                    return await ctx.send(_("This role is your top role or even higher than your top role. So you can't set permissions for it..."))
            if perm in ctx.cache.get_denied_perms(r.id):
                return await ctx.send(_("These permissions have already been disabled for this role!"))
            await ctx.cache.update_perms(r.id, perm, False)

        if c:
            if perm in ctx.cache.get_denied_perms(c.id):
                return await ctx.send(_("These permissions have already been disabled for this channel!"))
            await ctx.cache.update_perms(c.id, perm, False)

        await ctx.send(_("The `{0}` permission has successfully been updated for {1.mention}!").format(perm, u or r or c), allowed_mentions=discord.AllowedMentions.none())

    @checks.has_permissions(manage_guild=True)
    @perms.command(name="reset")
    async def perms_reset(self, ctx, *, reset_for: typing.Union[discord.Member, discord.Role, discord.TextChannel]):
        perms = ctx.cache.get_denied_perms(reset_for.id)
        perms += ctx.cache.get_allowed_perms(reset_for.id)
        if isinstance(reset_for, discord.Member):
            if ctx.author.id != self.bot.owner_id:
                if reset_for == ctx.author:
                    return await ctx.send(_("You cannot set permissions for yourself..."))
                if reset_for.top_role >= ctx.author.top_role:
                    return await ctx.send(_("You can't set permissions for people who have an equal or higher role than you in the hierarchy."))
            if not perms:
                return await ctx.send(_("There are no permissions to be reset for this user!"))

        if isinstance(reset_for, discord.Role):
            if ctx.author.id != self.bot.owner_id:
                if reset_for >= ctx.author.top_role:
                    return await ctx.send(_("This role is your top role or even higher than your top role. So you can't reset permissions for it..."))
            if not perms:
                return await ctx.send(_("There are no permissions to be reset for this role!"))

        if isinstance(reset_for, discord.TextChannel):
            if not perms:
                return await ctx.send(_("There are no permissions to be reset for this channel!"))

        ctx.cache.perms['allowed'].pop(reset_for.id, None)
        ctx.cache.perms['denied'].pop(reset_for.id, None)
        await self.bot.db.execute("DELETE FROM perm_settings WHERE guild_id = $1 AND _id = $2", ctx.guild.id, reset_for.id)
        await ctx.send(_("Permissions for {0.mention} have been successfully reset to default!").format(reset_for), allowed_mentions=discord.AllowedMentions.none())

    async def get_type(self, guild, _id):
        try:
            r = await self.bot.fetch_user(_id)
        except:
            try:
                r = await self.bot.fetch_channel(_id)
            except:
                r = guild.get_role(_id)
        return r

    @checks.has_permissions(manage_guild=True)
    @perms.command(name="list")
    async def perms_list(self, ctx, *, perms_for: typing.Union[discord.Member, discord.Role, discord.TextChannel] = None):
        e = discord.Embed(color=ctx.embed_color, title=_("Permission Settings:"))
        if perms_for is None:
            denied = ctx.cache.perms['denied']
            allowed = ctx.cache.perms['allowed']
            d = []
            a = []
            for k, v in denied.items():
                if v:
                    x = await self.get_type(ctx.guild, k)
                    d.append(f"{x.mention} - `{'`, `'.join(v)}`")
            for k, v in allowed.items():
                if v:
                    x = await self.get_type(ctx.guild, k)
                    a.append(f"{x.mention} - `{'`, `'.join(v)}`")
            e.add_field(name=_("Denied"), value="\n".join(d) if d else _("No denied perms"))
            e.add_field(name=_("Allowed"), value="\n".join(a) if a else _("No allowed perms"))
            return await ctx.send(embed=e)
        dperms = ctx.cache.get_denied_perms(perms_for.id)
        aperms = ctx.cache.get_allowed_perms(perms_for.id)
        if isinstance(perms_for, discord.Member):
            if not dperms and not aperms:
                return await ctx.send(_("There are no permissions to list for this user!"))

        if isinstance(perms_for, discord.Role):
            if not dperms and not aperms:
                return await ctx.send(_("There are no permissions to list for this role!"))

        if isinstance(perms_for, discord.TextChannel):
            if not dperms and not aperms:
                return await ctx.send(_("There are no permissions to list for this channel!"))

        e.description = _("Showing permissions for: {0}").format(perms_for.mention)
        e.add_field(name=_("Denied"), value="`{0}`".format('`\n`'.join(dperms)) if dperms else _("No denied perms"))
        e.add_field(name=_("Allowed"), value="`{0}`".format('`\n`'.join(aperms)) if aperms else _("No allowed perms"))
        await ctx.send(embed=e)

    @checks.has_permissions(manage_guild=True)
    @groupExtra(name="holiday-announce", invoke_without_command=True)
    async def holiday_announce(self, ctx):
        await ctx.send_help(ctx.command)

    @checks.has_permissions(manage_guild=True, manage_channels=True)
    @holiday_announce.command(name="channel")
    async def holiday_channel(self, ctx, *, channel: discord.TextChannel):
        if ctx.guild.id not in self.bot.cache.holiday_announcements.keys():
            self.bot.cache.holiday_announcements[ctx.guild.id] = {'toggle': False, 'role_id': None, 'channel_id': channel.id, 'country': 'UnitedStates', 'last_announce': date.today(), 'message': "I hope you're having a good day today! Because today we celebrate **{{holiday}}**!! :tada:"}
        else:
            self.bot.cache.holiday_announcements[ctx.guild.id]['channel_id'] = channel.id
            try:
                await self.bot.db.execute("UPDATE holiday_announcements SET channel_id = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
            except:
                pass

        await ctx.send(_("Holiday announcement channel has successfully been set to {0}!").format(channel.mention))

    @checks.has_permissions(manage_guild=True)
    @holiday_announce.command(name="message", aliases=['msg'])
    async def holiday_message(self, ctx, *, message: commands.clean_content):
        if "{{holiday}}" not in message:
            return await ctx.send(_("You forgot to add the `{0}` to the message, which is important to let people know which holiday is being announced :)").format("{{holiday}}"))
        if ctx.guild.id not in self.bot.cache.holiday_announcements.keys():
            self.bot.cache.holiday_announcements[ctx.guild.id] = {'toggle': False, 'role_id': None, 'channel_id': None, 'country': 'UnitedStates', 'last_announce': date.today(), 'message': message}
        else:
            self.bot.cache.holiday_announcements[ctx.guild.id]['message'] = message
            try:
                await self.bot.db.execute("UPDATE holiday_announcements SET message = $1 WHERE guild_id = $2", message, ctx.guild.id)
            except:
                pass

        return await ctx.send(_("Holiday announcement message has successfully been set to `{0}`!").format(message), allowed_mentions=discord.AllowedMentions(roles=False, everyone=False))

    @checks.has_permissions(manage_guild=True, manage_roles=True)
    @holiday_announce.command(name="role")
    async def holiday_role(self, ctx, role: discord.Role = None):
        if ctx.guild.id not in self.bot.cache.holiday_announcements.keys():
            if role is None:
                return await ctx.send(_("I cant remove the announcement role because holiday announcements have not been set up yet"))
            self.bot.cache.holiday_announcements[ctx.guild.id] = {'toggle': False, 'role_id': role.id, 'channel_id': None, 'country': 'UnitedStates', 'last_announce': date.today(), 'message': "I hope you're having a good day today! Because today we celebrate **{{holiday}}**!! :tada:"}
        else:
            self.bot.cache.holiday_announcements[ctx.guild.id]['role_id'] = role if role is None else role.id
            try:
                await self.bot.db.execute("UPDATE holiday_announcements SET role_id = $1 WHERE guild_id = $2", role if role is None else role.id, ctx.guild.id)
            except:
                pass

        if role:
            return await ctx.send(_("Holiday announcement role has successfully been set to {0}!").format(role.mention if role.id != ctx.guild.id else "@everyone"), allowed_mentions=discord.AllowedMentions(roles=False, everyone=False))
        await ctx.send(_("Holiday announcement role has successfully been removed!"))

    @checks.has_permissions(manage_guild=True)
    @holiday_announce.command(name="toggle")
    async def holiday_toggle(self, ctx):
        if ctx.guild.id not in self.bot.cache.holiday_announcements.keys():
            return await ctx.send(_("Please set an announcement channel before enabling this. You an also optionally set an annoucement role and a different country to get holidays from (defaults to America)"))
        elif self.bot.cache.holiday_announcements[ctx.guild.id]['channel_id'] is None:
            return await ctx.send(_("Please set an announcement channel before enabling this. You an also optionally set an annoucement role and a different country to get holidays from (defaults to America)"))
        else:
            if self.bot.cache.holiday_announcements[ctx.guild.id]['toggle']:
                self.bot.cache.holiday_announcements[ctx.guild.id]['toggle'] = False
                await self.bot.db.execute("UPDATE holiday_announcements SET toggle = false WHERE guild_id = $1", ctx.guild.id)
                await ctx.send(_("Holiday announcements have successfully been disabled!"))
            else:
                self.bot.cache.holiday_announcements[ctx.guild.id]['toggle'] = True
                check = await self.bot.db.fetchval("SELECT * FROM holiday_announcements WHERE guild_id = $1", ctx.guild.id)
                if check:
                    await self.bot.db.execute("UPDATE holiday_announcements SET toggle = true WHERE guild_id = $1", ctx.guild.id)
                else:
                    d = self.bot.cache.holiday_announcements[ctx.guild.id]
                    await self.bot.db.execute("INSERT INTO holiday_announcements VALUES($1, $2, $3, $4, $5, $6, $7)", ctx.guild.id, d['country'], date.today(), d['channel_id'], d['role_id'], d['toggle'], d['message'])
                await ctx.send(_("Holiday announcements have successfully been enabled!"))

    @checks.has_permissions(manage_guild=True)
    @holiday_announce.command(name="country")
    async def holiday_country(self, ctx, country):
        countries = list(filter(lambda x: x.upper() != x, holidays.list_supported_countries()))
        if country not in countries:
            e = discord.Embed(color=ctx.embed_color)
            e.title = _("Available Countries")
            e.description = _("Country {0} not found! Please pick one of the following: `{1}`").format('`, `'.join(countries))
            e.set_footer(text=_("Country names are case-sensitive!"))
            return await ctx.send(embed=e)

        if ctx.guild.id not in self.bot.cache.holiday_announcements.keys():
            self.bot.cache.holiday_announcements[ctx.guild.id] = {'toggle': False, 'role_id': None, 'channel_id': None, 'country': country, 'last_announce': date.today(), 'message': "I hope you're having a good day today! Because today we celebrate **{{holiday}}**!! :tada:"}
        else:
            self.bot.cache.holiday_announcements[ctx.guild.id]['country'] = country
            try:
                await self.bot.db.execute("UPDATE holiday_announcements SET country = $1, WHERE guild_id = $2", country, ctx.guild.id)
            except:
                pass

            await ctx.send(_("Successfully updated holiday announcements country to {0}!").format(country))

    @checks.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    @commandExtra(category="Server Settings", name='steal-emoji')
    async def steal_emoji(self, ctx, emoji: discord.PartialEmoji):
        # try:
        #     e = await commands.PartialEmojiConverter().convert(ctx, str(emoji))
        #     url = str(e.url)
        #     name = e.name
        # except:
        #     return await ctx.send(_("That was not a valid emoji!"))
        url = str(emoji.url)
        name = emoji.name
        async with self.bot.session.get(url) as f:
            e_byte = await f.read()
        try:
            em = await ctx.guild.create_custom_emoji(name=name, image=e_byte)
        except:
            return await ctx.send(_("Could not create emoji"))

        await ctx.send(_("Emoji succesfully created! {0} `:{0.name}:`").format(em))

    @checks.has_permissions(manage_messages=True)
    @commandExtra(category="Server Settings", name="delete-roast")
    async def delete_roast(self, ctx, roast_id: int):
        roasts = [x for x, in await self.bot.db.fetch("SELECT roast FROM custom_roasts WHERE guild_id = $1", ctx.guild.id)]
        if not roasts:
            return await ctx.send(_("There are no custom roasts to delete in this server!"))
        if roast_id-1 > len(roasts):
            return await ctx.send(_("Invalid roast number! Please use `{0}guildsettings roasts` to see which roast number belongs to a roast!").format(ctx.prefix))
        roast = roasts[roast_id-1]
        self.bot.cache.update("settings", ctx.guild.id, "custom_roasts", roast)
        await self.bot.db.execute("DELETE FROM custom_roasts WHERE roast = $1 AND guild_id = $2", roast, ctx.guild.id)
        await ctx.send(_("Roast `{0}` has succesfully been deleted!").format(roast))

    @commandExtra(category="Server Settings", name="add-roast", aliases=["submit-roast"])
    async def add_roast(self, ctx, *, roast):
        if len(roast) > 175:
            return await ctx.send(_("I appreciate your enthusiasm, but I had to put a limit of **175** characters on custom roasts... Your roast was **{0}** characters long!").format(len(roast)))
        self.bot.cache.update("settings", ctx.guild.id, "custom_roasts", roast)
        await self.bot.db.execute("INSERT INTO custom_roasts(guild_id, roast) VALUES($1, $2)", ctx.guild.id, roast)
        suggestchan = self.bot.get_channel(782048602511507467)
        e = discord.Embed(title="**Roast Submission**", color=0x3381A5, description=roast)
        e.set_author(icon_url=ctx.author.avatar.url, name=f"Submitted by | {ctx.author}")
        msg = await suggestchan.send(embed=e)

        await msg.add_reaction(':upvote:274492025678856192')
        await msg.add_reaction(':downvote:274492025720537088')

        e.set_footer(text=f"{msg.id} | {ctx.author.id}")
        await msg.edit(embed=e)

        await ctx.send(_("Your custom roast has been submitted! You can access custom roasts with `{0}roast @user --level 0`. Your roast has also been sent to my owner, so if he likes it you will receive a DM that he added your roast to my roast database!\n\n*Remember: spamming this with nonsense will result in a ban from my commands!*").format(ctx.prefix))

    @commands.guild_only()
    @checks.has_permissions(manage_roles=True)
    @groupExtra(category="Server Settings")
    async def joinrole(self, ctx):
        pass

    @checks.has_permissions(manage_roles=True)
    @joinrole.command(name="toggle")
    async def role_toggle(self, ctx):
        if self.bot.cache.get("settings", ctx.guild.id, "joinrole_human") is None and self.bot.cache.get("settings", ctx.guild.id, "joinrole_bot") is None:
            return await ctx.send(_("You have not set a join role for humans or bots yet. Please set one first before enabling Role On Join!"))

        if self.bot.cache.get("settings", ctx.guild.id, "joinrole_toggle") is False:
            toggle_set = self.bot.cache.update("settings", ctx.guild.id, "joinrole_toggle", True)
            await self.bot.db.execute("UPDATE guildsettings SET joinrole_toggle = $2 WHERE guild_id = $1", ctx.guild.id, True)

        elif self.bot.cache.get("settings", ctx.guild.id, "joinrole_toggle") is True:
            toggle_set = self.bot.cache.update("settings", ctx.guild.id, "joinrole_toggle", False)
            await self.bot.db.execute("UPDATE guildsettings SET joinrole_toggle = $2 WHERE guild_id = $1", ctx.guild.id, True)

        if toggle_set:
            return await ctx.send(_("Role On Join has been enabled!"))

        await ctx.send(_("Role On Join has been disabled!"))

    @checks.has_permissions(manage_roles=True)
    @joinrole.command(name="bots", aliases=['bot'])
    async def role_bots(self, ctx, role: discord.Role = None):
        if role is None:
            msg = _("Join role for bots has succesfully been removed")
        else:
            if role.position == ctx.guild.me.top_role.position or role.position > ctx.guild.me.top_role.position:
                img = discord.File(fp='db/images/role_position.png', filename='Role_Position.png')
                return await ctx.send(_("The role you tried to set (`{0}`) is equal to my top role or is higher than my top role. Please move my top role above the one you try to use.").format(role.name), file=img)
            msg = _("Join role for bots has been set to: `{0}`").format(role.name)

        d = self.bot.cache.update("settings", ctx.guild.id, "joinrole_bot", role.id if role else None)
        await self.bot.db.execute("UPDATE guildsettings SET joinrole_bot = $2 WHERE guild_id = $1", ctx.guild.id, d)

        await ctx.send(msg)

    @checks.has_permissions(manage_roles=True)
    @joinrole.command(name="humans", aliases=['human'])
    async def role_humans(self, ctx, role: discord.Role = None):
        if role is None:
            msg = _("Join role for humans has succesfully been removed")
        else:
            if role.position == ctx.guild.me.top_role.position or role.position > ctx.guild.me.top_role.position:
                img = discord.File(fp='db/images/role_position.png', filename='Role_Position.png')
                return await ctx.send(_("The role you tried to set (`{0}`) is equal to my top role or is higher than my top role. Please move my top role above the one you try to use.").format(role.name), file=img)
            msg = _("Join role for humans has been set to: `{0}`").format(role.name)

        d = self.bot.cache.update("settings", ctx.guild.id, "joinrole_human", role.id if role else None)
        await self.bot.db.execute("UPDATE guildsettings SET joinrole_human = $2 WHERE guild_id = $1", ctx.guild.id, d)

        await ctx.send(msg)

    @commands.guild_only()
    @checks.has_permissions(manage_guild=True)
    @commandExtra(category="Server Settings")
    async def logchannel(self, ctx, option=None, *, channel: discord.TextChannel = None):
        options = {
            "msgedit": "msgedit",
            "msgdelete": "msgdel",
            "memberupdate": "useredit",
            "moderation": "mod",
            "joins": "join"
        }

        optionsmsg = "```asciidoc\n"
        optionsmsg += "MemberUpdate  :: " + _("Log when a member updates their avatar/nick/etc") + "\n"
        optionsmsg += "MsgEdit       :: " + _("Log when a message is edited") + "\n"
        optionsmsg += "MsgDelete     :: " + _("Log when a message is deleted") + "\n"
        optionsmsg += "Moderation    :: " + _("Log when a member is kicked/banned/etc") + "\n"
        optionsmsg += "Joins         :: " + _("Log when a member joins/leaves the server")
        optionsmsg += "```"

        if option is None or option.lower() not in options.keys():
            e = discord.Embed(color=ctx.embed_color,
                              title=_("These are the available options for logging:") if option is None else _("Invalid option given, please choose a valid option:"),
                              description=optionsmsg)
            return await ctx.send(embed=e)

        c = self.bot.cache.update("logging", ctx.guild.id, f"{options[option.lower()]}_channel", None if channel is None else channel.id)

        await self.bot.db.execute("UPDATE logging SET {0}_channel = $2 WHERE guild_id = $1".format(options[option.lower()]), ctx.guild.id, c)

        if channel is None:
            return await ctx.send(_("Succesfully disabled logs for `{0}`!").format(option))

        await ctx.send(_("Now logging `{0}` in {1}!").format(option, channel.mention))

    @checks.has_permissions(manage_guild=True)
    @groupExtra(category="Server Settings", invoke_without_command=True)
    async def leaving(self, ctx):
        await ctx.send_help(ctx.command)

    @checks.has_permissions(manage_guild=True)
    @leaving.command(name="delete-after", aliases=['del-after'])
    async def leave_delete_msg_after(self, ctx, time: int = None):
        self.bot.cache.update("welcomer", ctx.guild.id, "leave_delafter", time)
        await self.bot.db.execute("UPDATE welcoming SET leave_delafter = $2 WHERE guild_id = $1", ctx.guild.id, time)

        if time:
            msg = _("Leaving messages will now be deleted after {0} seconds!").format(str(time))
        else:
            msg = _("Leaving messages will not be deleted.")
        await ctx.send(msg)

    @checks.has_permissions(manage_guild=True)
    @leaving.command(name='msg')
    async def leave_msg(self, ctx, *, message):
        if self.bot.cache.get("welcomer", ctx.guild.id, "leave_embedtoggle"):
            return await ctx.send(_("You enabled embedded leaving messages, please use the `leaving embedmsg` command to set the message. See `help leaving embedmsg` for more info!"))

        self.bot.cache.update("welcomer", ctx.guild.id, "leave_msg", message)
        await self.bot.db.execute("UPDATE welcoming SET leave_msg = $2 WHERE guild_id = $1", ctx.guild.id, message)
        await ctx.send(_("Leaving message has been set to:") + f"```\n{message}```")

    @checks.has_permissions(manage_guild=True)
    @leaving.command(name="embedmsg")
    async def leave_embedmsg(self, ctx, *, message):
        if self.bot.cache.get("welcomer", ctx.guild.id, "leave_toggle"):
            return await ctx.send(_("You enabled normal leaving messages, please use the `leaving msg` command to set the message."))

        try:
            d = json.loads(message)
        except json.decoder.JSONDecodeError:
            return await ctx.send(_("I could not convert that to an embed! Are you sure you copied everything correctly?"))

        try:
            e = discord.Embed.from_dict(d)
            await ctx.send(content=_("Embedded leaving message has been set to:"), embed=e)
        except discord.HTTPException:
            return await ctx.send(_("Something went wrong while loading that embed... Please check if everything is correct (like image urls)!"))

        self.bot.cache.update("welcomer", ctx.guild.id, "leave_embedmsg", d)
        await self.bot.db.execute("UPDATE welcoming SET leave_embedmsg = $2 WHERE guild_id = $1", ctx.guild.id, json.dumps(d))

    @checks.has_permissions(manage_guild=True)
    @leaving.command(name="toggle")
    async def leave_toggle(self, ctx):
        toggle_set = False
        if self.bot.cache.get("welcomer", ctx.guild.id, "leave_embedtoggle"):
            return await ctx.send(_("You already have embedded leaving messages enabled, I can not enable normal messages too."))

        if not self.bot.cache.get("welcomer", ctx.guild.id, "leave_channel"):
            return await ctx.send(_("I could not enable leaving messages because you haven't set a channel yet. Please set a channel first using the `leaving channel <channel>` command!"))

        if not self.bot.cache.get("welcomer", ctx.guild.id, "leave_msg"):
            return await ctx.send(_("You haven't set a leaving message yet! Please set one using the `leaving msg` command!"))

        if self.bot.cache.get("welcomer", ctx.guild.id, "leave_toggle") is False:
            toggle_set = self.bot.cache.update("welcomer", ctx.guild.id, "leave_toggle", True)
        elif self.bot.cache.get("welcomer", ctx.guild.id, "leave_toggle") is True:
            self.bot.cache.update("welcomer", ctx.guild.id, "leave_toggle", False)

        await self.bot.db.execute("UPDATE welcoming SET leave_toggle = $2 WHERE guild_id = $1", ctx.guild.id, toggle_set)

        if toggle_set:
            return await ctx.send(_("Leaving messages have been enabled for this server!"))
        await ctx.send(_("Leaving messages have been disabled for this server!"))

    @checks.has_permissions(manage_guild=True)
    @leaving.command(name="embedtoggle")
    async def leave_embedtoggle(self, ctx):
        toggle_set = False
        if self.bot.cache.get("welcomer", ctx.guild.id, "leave_toggle"):
            return await ctx.send(_("You already have normal leaving messages enabled, I can not enable embedded messages too."))

        if not self.bot.cache.get("welcomer", ctx.guild.id, "leave_channel"):
            return await ctx.send(_("I could not enable leaving messages because you haven't set a channel yet. Please set a channel first using the `leaving channel <channel>` command!"))

        if not self.bot.cache.get("welcomer", ctx.guild.id, "leave_embedmsg"):
            return await ctx.send(_("You haven't set a leaving message yet! Please set one using the `leaving embedmsg` command!"))

        if self.bot.cache.get("welcomer", ctx.guild.id, "leave_embedtoggle") is False:
            toggle_set = self.bot.cache.update("welcomer", ctx.guild.id, "leave_embedtoggle", True)
        elif self.bot.cache.get("welcomer", ctx.guild.id, "leave_embedtoggle") is True:
            self.bot.cache.update("welcomer", ctx.guild.id, "leave_embedtoggle", False)

        await self.bot.db.execute("UPDATE welcoming SET leave_embedtoggle = $2 WHERE guild_id = $1", ctx.guild.id, toggle_set)

        if toggle_set:
            return await ctx.send(_("Embedded leaving messages have been enabled for this server!"))
        await ctx.send(_("Embedded leaving messages have been disabled for this server!"))

    @checks.has_permissions(manage_guild=True)
    @leaving.command(name="channel")
    async def leave_channel(self, ctx, channel: discord.TextChannel):
        t = self.bot.cache.update("welcomer", ctx.guild.id, "leave_channel", channel.id)
        await self.bot.db.execute("UPDATE welcoming SET leave_channel = $2 WHERE guild_id = $1", ctx.guild.id, t)
        await ctx.send(_("Leaving message channel has been set to:") + f" {channel.mention}")

    @checks.has_permissions(manage_guild=True)
    @groupExtra(category="Server Settings", invoke_without_command=True)
    async def welcoming(self, ctx):
        await ctx.send_help(ctx.command)

    @checks.has_permissions(manage_guild=True)
    @welcoming.command(name="delete-after", aliases=['del-after'])
    async def welcome_delete_msg_after(self, ctx, time: int = None):
        self.bot.cache.update("welcomer", ctx.guild.id, "welcome_delafter", time)
        await self.bot.db.execute("UPDATE welcoming SET welcome_delafter = $2 WHERE guild_id = $1", ctx.guild.id, time)

        if time:
            msg = _("Welcoming messages will now be deleted after {0} seconds!").format(str(time))
        else:
            msg = _("Welcoming messages will not be deleted.")
        await ctx.send(msg)

    @checks.has_permissions(manage_guild=True)
    @welcoming.command(name="msg")
    async def welcome_msg(self, ctx, *, message):
        if self.bot.cache.get("welcomer", ctx.guild.id, "welcome_embedtoggle"):
            return await ctx.send(_("You enabled embedded welcoming messages, please use the `welcoming embedmsg` command to set the message. See `help welcoming embedmsg` for more info!"))

        self.bot.cache.update("welcomer", ctx.guild.id, "welcome_msg", message)
        await self.bot.db.execute("UPDATE welcoming SET welcome_msg = $2 WHERE guild_id = $1", ctx.guild.id, message)
        await ctx.send(_("Welcoming message has been set to:") + f"```\n{message}```")

    @checks.has_permissions(manage_guild=True)
    @welcoming.command(name="embedmsg")
    async def welcome_embedmsg(self, ctx, *, message):
        if self.bot.cache.get("welcomer", ctx.guild.id, "welcome_toggle"):
            return await ctx.send(_("You enabled normal welcoming messages, please use the `welcoming msg` command to set the message."))

        try:
            d = json.loads(message)
        except json.decoder.JSONDecodeError:
            return await ctx.send(_("I could not convert that to an embed! Are you sure you copied everything correctly?"))

        try:
            e = discord.Embed.from_dict(d)
            await ctx.send(content=_("Embedded welcoming message has been set to:"), embed=e)
        except discord.HTTPException:
            return await ctx.send(_("Something went wrong while loading that embed... Please check if everything is correct (like image urls)!"))

        self.bot.cache.update("welcomer", ctx.guild.id, "welcome_embedmsg", d)
        await self.bot.db.execute("UPDATE welcoming SET welcome_embedmsg = $2 WHERE guild_id = $1", ctx.guild.id, json.dumps(d))

    @checks.has_permissions(manage_guild=True)
    @welcoming.command(name="toggle")
    async def welcome_toggle(self, ctx):
        toggle_set = False
        if self.bot.cache.get("welcomer", ctx.guild.id, "welcome_embedtoggle"):
            return await ctx.send(_("You already have embedded welcoming messages enabled, I can not enable normal messages too."))

        if not self.bot.cache.get("welcomer", ctx.guild.id, "welcome_channel"):
            return await ctx.send(_("I could not enable welcoming messages because you haven't set a channel yet. Please set a channel first using the `welcoming channel <channel>` command!"))

        if not self.bot.cache.get("welcomer", ctx.guild.id, "welcome_msg"):
            return await ctx.send(_("You haven't set a welcoming message yet! Please set one using the `welcoming msg` command!"))

        if self.bot.cache.get("welcomer", ctx.guild.id, "welcome_toggle") is False:
            toggle_set = self.bot.cache.update("welcomer", ctx.guild.id, "welcome_toggle", True)
        elif self.bot.cache.get("welcomer", ctx.guild.id, "welcome_toggle") is True:
            self.bot.cache.update("welcomer", ctx.guild.id, "welcome_toggle", False)

        await self.bot.db.execute("UPDATE welcoming SET welcome_toggle = $2 WHERE guild_id = $1", ctx.guild.id, toggle_set)

        if toggle_set:
            return await ctx.send(_("Welcoming messages have been enabled for this server!"))
        await ctx.send(_("Welcoming messages have been disabled for this server!"))

    @checks.has_permissions(manage_guild=True)
    @welcoming.command(name="embedtoggle")
    async def welcome_embedtoggle(self, ctx):
        toggle_set = False
        if self.bot.cache.get("welcomer", ctx.guild.id, "welcome_toggle"):
            return await ctx.send(_("You already have normal welcoming messages enabled, I can not enable embedded messages too."))

        if not self.bot.cache.get("welcomer", ctx.guild.id, "welcome_channel"):
            return await ctx.send(_("I could not enable welcoming messages because you haven't set a channel yet. Please set a channel first using the `welcoming channel <channel>` command!"))

        if not self.bot.cache.get("welcomer", ctx.guild.id, "welcome_embedmsg"):
            return await ctx.send(_("You haven't set a welcoming message yet! Please set one using the `welcoming embedmsg` command!"))

        if self.bot.cache.get("welcomer", ctx.guild.id, "welcome_embedtoggle") is False:
            toggle_set = self.bot.cache.update("welcomer", ctx.guild.id, "welcome_embedtoggle", True)
        elif self.bot.cache.get("welcomer", ctx.guild.id, "welcome_embedtoggle") is True:
            self.bot.cache.update("welcomer", ctx.guild.id, "welcome_embedtoggle", False)

        await self.bot.db.execute("UPDATE welcoming SET welcome_embedtoggle = $2 WHERE guild_id = $1", ctx.guild.id, toggle_set)

        if toggle_set:
            return await ctx.send(_("Embedded welcoming messages have been enabled for this server!"))
        await ctx.send(_("Embedded welcoming messages have been disabled for this server!"))

    @checks.has_permissions(manage_guild=True)
    @welcoming.command(name="channel")
    async def _channel(self, ctx, channel: discord.TextChannel):
        self.bot.cache.update("welcomer", ctx.guild.id, "welcome_channel", channel.id)
        await self.bot.db.execute("UPDATE welcoming SET welcome_channel = $2 WHERE guild_id = $1", ctx.guild.id, channel.id)
        await ctx.send(_("Welcoming message channel has been set to:") + f" {channel.mention}")


def setup(bot):
    pass
