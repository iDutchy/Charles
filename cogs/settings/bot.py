import re
from collections import Counter

import discord
from discord.utils import escape_markdown
from core import i18n
from core.cog import SubCog
from core.commands import commandExtra, groupExtra
from db import langs
from discord.ext import commands
from utils import checks

HEX = re.compile(r'^(#|0x)[A-Fa-f0-9]{6}$')


class BotSettings(SubCog, category="Bot Settings"):
    def __init__(self, bot):
        self.bot = bot

    @checks.has_permissions(manage_messages=True)
    @commandExtra(name='react-to-translate', aliases=['rtt'])
    async def react_to_translate(self, ctx):
        toggle = await ctx.cache.toggle_rtt()
        if toggle:
            return await ctx.send(_("React To Translate has been enabled!"))
        await ctx.send(_("React To Translate has been disabled!"))

    @groupExtra(name="embed-mentions", aliases=["emtoggle", "em-toggle"], invoke_without_command=True)
    async def embed_mentions(self, ctx):
        if ctx.author.id in self.bot.cache.embed_mentions.keys():
            if self.bot.cache.embed_mentions[ctx.author.id]['global']:
                return await ctx.send(_("You have global embed mention checks enabled, please disable that if you want to check per server!"))

            if ctx.guild.id in self.bot.cache.embed_mentions[ctx.author.id]['guilds']:
                self.bot.cache.embed_mentions[ctx.author.id]['guilds'].remove(ctx.guild.id)
                if not self.bot.cache.embed_mentions[ctx.author.id]['guilds']:
                    self.bot.cache.embed_mentions.pop(ctx.author.id)
                await self.bot.db.execute("DELETE FROM embed_mentions WHERE user_id = $1 AND guild_id = $2", ctx.author.id, ctx.guild.id)
                return await ctx.send(_("I have removed this server from your settings!"))

            else:
                self.bot.cache.embed_mentions[ctx.author.id]['guilds'].append(ctx.guild.id)
                await self.bot.db.execute("INSERT INTO embed_mentions VALUES($1, $2)", ctx.guild.id, ctx.author.id)
                return await ctx.send(_("I have added this server to your settings!"))
        else:
            try:
                await ctx.author.send(_("Hi, just checking if I can DM you! :)"))
            except:
                return await ctx.send(_("Sorry {0}, but I need to be able to DM you. Please enable your DMs and try again!").format(ctx.author.mention))

            self.bot.cache.embed_mentions[ctx.author.id] = {'guilds': [ctx.guild.id], "global": False}
            await self.bot.db.execute("INSERT INTO embed_mentions VALUES($1, $2)", ctx.guild.id, ctx.author.id)
            await ctx.send(_("I have enabled embed mention notifications for you in this server! If you want to check for embed mentions in all servers we share, use `{0}`!").format(f"{ctx.clean_prefix} em-toggle global"))

    @embed_mentions.command(name="global")
    async def global_mentions(self, ctx):
        if ctx.author.id in self.bot.cache.embed_mentions.keys():
            if not self.bot.cache.embed_mentions[ctx.author.id]['guilds']:
                self.bot.cache.embed_mentions[ctx.author.id]['guilds'].append(ctx.guild.id)
            if self.bot.cache.embed_mentions[ctx.author.id]['global']:
                try:
                    self.bot.cache.embed_mentions[ctx.author.id]['guilds'].remove(ctx.guild.id)
                except:
                    pass
                self.bot.cache.embed_mentions[ctx.author.id]['global'] = False
                await self.bot.db.execute("UPDATE embed_mentions SET global = false WHERE user_id = $1", ctx.author.id)
                return await ctx.send(_("I have disabled global mention checks for you!"))
            else:
                self.bot.cache.embed_mentions[ctx.author.id]['global'] = True
                await self.bot.db.execute("UPDATE embed_mentions SET global = true WHERE user_id = $1", ctx.author.id)
                return await ctx.send(_("I have enabled global mention checks for you!"))
        else:
            try:
                await ctx.author.send(_("Hi, just checking if I can DM you! :)"))
            except:
                return await ctx.send(_("Sorry {0}, but I need to be able to DM you. Please enable your DMs and try again!").format(ctx.author.mention))

            self.bot.cache.embed_mentions[ctx.author.id] = {'global': True, 'guilds': [ctx.guild.id]}
            await self.bot.db.execute("INSERT INTO embed_mentions VALUES ($1, $2, true)", ctx.guild.id, ctx.author.id)
            return await ctx.send(_("I have enabled global mention checks for you!"))

    @groupExtra(invoke_without_command=True)
    async def socials(self, ctx):
        await ctx.send(_("Available socials are: `{0}`.\nYou can set them with `{1}`").format("`, `".join(list(ctx.emoji.socials.keys())), f"{ctx.clean_prefix}socials set <platform> <username>"))

    @socials.command(name="add", aliases=['set', 'edit'])
    async def socials_add(self, ctx, socialtype, *, username: commands.clean_content):
        stype = socialtype.lower()
        social = username.replace("`", "").replace("\\", "").replace("\`", "")
        if len(social) > 50:
            return await ctx.send("Usernames cannot be longer than 50 characters.")
        
        if stype not in ctx.emoji.socials.keys():
            return await ctx.send(_("I do not support that social platform (yet)! Valid platforms are: {0}").format(", ".join(list(ctx.emoji.socials.keys()))))

        if stype not in ctx.user.socials:
            msg = _("I have set your **{0}** username to {1}").format(socialtype.lower(), social)
        else:
            msg = _("I have edited your **{0}** username to {1}").format(socialtype.lower(), social)

        await ctx.user.socials.set(stype, social)

        await ctx.send(msg)

    @socials.command(name="remove", aliases=['delete', 'del'])
    async def socials_remove(self, ctx, socialtype):
        stype = socialtype.lower()
        if stype not in ctx.emoji.socials.keys():
            return await ctx.send(_("I do not support that social platform (yet)! Valid platforms are: {0}").format(", ".join(list(ctx.emoji.socials.keys()))))

        if not ctx.user.socials:
            return await ctx.send(_("You don't have any socials set yet!"))

        if stype not in ctx.user.socials:
            return await ctx.send(_("You didn't have anything set yet for this social, so I couldn't remove it..."))

        await ctx.user.socials.remove(stype)

        await ctx.send(_("I have succesfully removed your **{0}** username from your profile!").format(socialtype.lower()))

    @checks.has_permissions(manage_guild=True)
    @commandExtra(name="reset-color", category="Bot Settings")
    async def reset_color(self, ctx):
        col = await self.bot.db.fetchval("UPDATE guildsettings SET embedcolor = DEFAULT WHERE guild_id = $1 RETURNING embedcolor", ctx.guild.id)
        self.bot.cache.update("settings", ctx.guild.id, "color", col)
        await ctx.send(embed=discord.Embed(color=col, description=_("Embed color has been reset back to default value!")))

    @checks.has_permissions(manage_messages=True)
    @commandExtra(category="Bot Settings", name="cb-emotion", aliases=['set-cb-emotion'])
    async def cb_emotion(self, ctx, emotion):
        if emotion not in ("neutral", "sad", "fear", "joy", "anger", "random"):
            return await ctx.send(_("Invalid emotion provided! Available emotions are:\n\n{}").format(", ".join(["neutral", "sad", "fear", "joy", "anger", "random"])))

        await self.bot.db.execute("UPDATE guildsettings SET cb_emotion = $2 WHERE guild_id = $1", ctx.guild.id, emotion.lower())
        self.bot.cache.update("settings", ctx.guild.id, "cb_emotion", emotion.lower())
        await ctx.send(_("Cleverbot emotion has succesfully been updated to `{}`!").format(emotion.lower()))

    @checks.has_permissions(manage_messages=True)
    @commandExtra(category="Bot Settings", name="set-roast-level", aliases=['roast-level'])
    async def set_roast_level(self, ctx, value: int = None):
        values = {
            0: _("Custom"),
            1: _("Low"),
            2: _("Medium"),
            3: _("High")
        }

        if value is None or value not in values.keys():
            settings = []
            roasts = _("roasts")
            for k, v in values.items():
                if k == 0:
                    settings.append(f"[{k}] - {v} ({len(self.bot.cache.get('settings', ctx.guild.id, 'custom_roasts'))} {roasts})")
                else:
                    settings.append(f"[{k}] - {v} ({len(self.roasts[str(k)])} {roasts})")
            return await ctx.send(_("**Current roast level:** {1}\nThere are 3 levels of roasts:\n```\n{0}```\nRoast levels 2 and 3 will have roasts from their level and all levels below.\n**Warning:** Roasts from level 3 can be very extreme! These are not meant to use to actually insult someone!").format('\n'.join(settings), str(self.bot.cache.get("settings", ctx.guild.id, "roastlevel"))))

        if value == 3:
            check, msg = await ctx.confirm(_("Are you sure you want to set the roast level to `level 3`? The roasts from this level can be a trigger for some people, so if you do choose to set it to this level, be careful who you roast!"), edit=False)
            if not check:
                await ctx.send(_("Ok, no changes will be made!"), edit=False)
                await msg.delete()
                return
            else:
                await msg.delete()

        await ctx.cache.set_roastlevel(value)

        await ctx.send(_("The roast level has been set to: `{0}`!").format(values[value]), edit=False)

    @checks.has_permissions(manage_guild=True)  # TODO: UPDATE USAGE IN HELP
    @commandExtra(name="disable-category", aliases=['disable-cat'], category="Bot Settings")
    async def disable_category(self, ctx, *, category: str):
        cat = self.bot.get_category(category)
        if not cat:
            return await ctx.send(_("That is not a valid category!"))

        c = Counter()
        for k, v in self.bot.cache.get("categories", ctx.guild.id).items():
            if k.startswith(cat.cog.qualified_name.lower()):
                c[v] += 1

        if c[True] == 1:
            return await ctx.send(_("You need to have at least 1 category enabled. If you want all disabled, please disable the whole module using the `disable-module` command!"))

        if not self.bot.cache.get("categories", ctx.guild.id, cat.cachestring):
            return await ctx.send(_("You can not disable this category as it is already disabled!"))

        self.bot.cache.update("categories", ctx.guild.id, cat.cachestring, False)
        await self.bot.db.execute('UPDATE category_settings SET "{}" = $2 WHERE guild_id = $1'.format(cat.cachestring), ctx.guild.id, False)

        await ctx.send(_("Category `{0}` has been toggled **off**!").format(category.title()))

    @checks.has_permissions(manage_guild=True)  # TODO: UPDATE USAGE IN HELP
    @commandExtra(name="enable-category", aliases=['enable-cat'], category="Bot Settings")
    async def enable_category(self, ctx, *, category: str):
        cat = self.bot.get_category(category.title())
        if cat is None:
            return await ctx.send(_("That is not a valid category!"))

        if self.bot.cache.get("categories", ctx.guild.id, cat.cachestring):
            return await ctx.send(_("You can not enable this category as it is already enabled!"))

        self.bot.cache.update("categories", ctx.guild.id, cat.cachestring, True)
        await self.bot.db.execute('UPDATE category_settings SET "{}" = $2 WHERE guild_id = $1'.format(cat.cachestring), ctx.guild.id, True)

        await ctx.send(_("Category `{0}` has been toggled **on**!").format(cat.name))

    @checks.has_permissions(manage_guild=True)
    @commandExtra(name="disable-module", category="Bot Settings")
    async def disable_module(self, ctx, module: str):
        if module.lower() in ["*", _("all")]:
            for m in self.bot.cache.get("modules", ctx.guild.id).keys():
                self.bot.cache.update("modules", ctx.guild.id, m, False)

            await self.bot.db.execute("UPDATE module_settings SET fun = $2, music = $2, info = $2, moderation = $2, utility = $2, images = $2 WHERE guild_id = $1", ctx.guild.id, False)
            return await ctx.send(_("All modules have been toggled **off**!"))

        if not module.lower() in self.bot.cache.get("modules", ctx.guild.id).keys():
            return await ctx.send(_("That is not a valid module!"))

        if not self.bot.cache.get("modules", ctx.guild.id, module.lower()):
            return await ctx.send(_("This module is already disabled!"))

        self.bot.cache.update("modules", ctx.guild.id, module.lower(), False)
        await self.bot.db.execute("UPDATE module_settings SET {0} = $2 WHERE guild_id = $1".format(module.lower()), ctx.guild.id, False)
        await ctx.send(_("Module `{0}` has been toggled **off**!").format(module.title()))

    @checks.has_permissions(manage_guild=True)
    @commandExtra(name="enable-module", category="Bot Settings")
    async def enable_module(self, ctx, module: str):
        if module.lower() in ["*", _("all")]:
            for m in self.bot.cache.get("modules", ctx.guild.id).keys():
                self.bot.cache.update("modules", ctx.guild.id, m, True)

            await self.bot.db.execute("UPDATE module_settings SET fun = $2, music = $2, info = $2, moderation = $2, utility = $2, images = $2 WHERE guild_id = $1", ctx.guild.id, True)
            return await ctx.send(_("All modules have been toggled **on**!"))

        if not module.lower() in self.bot.cache.get("modules", ctx.guild.id).keys():
            return await ctx.send(_("That is not a valid module!"))

        if self.bot.cache.get("modules", ctx.guild.id, module.lower()):
            return await ctx.send(_("This module is already enabled!"))

        self.bot.cache.update("modules", ctx.guild.id, module.lower(), True)
        await self.bot.db.execute("UPDATE module_settings SET {0} = $2 WHERE guild_id = $1".format(module.lower()), ctx.guild.id, True)
        await ctx.send(_("Module `{0}` has been toggled **on**!").format(module.title()))

    @checks.has_permissions(manage_guild=True)
    @commandExtra(name='set-color', category="Bot Settings", aliases=['embedcolor', 'embed-color', 'embedcolour', 'embed-colour', 'set-colour'])
    async def embed_color(self, ctx, color):
        if not HEX.match(color):
            return await ctx.send(_("That is not a valid HEX color! Please only use a `#******` or `0x******` HEX format!"))

        color = color.replace('#', '0x')
        color = int(color, 16)

        await ctx.cache.set_color(color)

        e = discord.Embed(color=color,
                          title=_("Embed color succesfully changed!"))

        await ctx.send(embed=e)

    @checks.has_permissions(manage_guild=True)
    @commandExtra(name="set-language", aliases=['set-lang'], category="Bot Settings")
    async def set_language(self, ctx, *, language=None):
        languages = {}
        total_strings = len(list(self.bot.cache.i18n['en'].keys())) + len(list(self.bot.cache.cmd_help['en'].keys()))
        for lang in list(self.bot.cache.i18n.keys()):
            translated = len(list(self.bot.cache.i18n[lang].keys())) + len(list(self.bot.cache.cmd_help[lang].keys()))
            if translated == 0:
                continue
            translated_percent = 100/total_strings*translated
            if lang == "en":
                languages['English'] = 100
            else:
                languages[list(langs.LANGUAGES.keys())[list(langs.LANGUAGES.values()).index(lang)]] = translated_percent

        language_txt = _("Language:")
        trans_txt = _("Translated")

        lang_list = []
        prefix = "```ini\n"
        prefix += f"{language_txt}{' '*int(20-len(language_txt))}| % {trans_txt}\n"
        prefix += f"--------------------+----{'-'*int(len(trans_txt))}\n"
        for k, v in sorted(languages.items()):
            lang_list.append(f"{k:20}| [{v:.2f}%]")
        suffix = "```"

        col = ctx.embed_color
        footer = _("If you would like to help to translate me to your language, contact my owner: Dutchy#6127")

        if language is None:
            title = _("Available languages:")
            return await self.bot.utils.paginate(ctx, color=col, per_page=10, footertext=footer, title=title, entries=lang_list, show_page_num=True, prefix=prefix, suffix=suffix)

        if language.title() not in languages.keys() and language.title() != "English":
            title = _("I couldn't find that language! Available languages:")
            return await self.bot.utils.paginate(ctx, color=col, per_page=10, footertext=footer, title=title, entries=lang_list, show_page_num=True, prefix=prefix, suffix=suffix)

        if language.title() == "English":
            langcode = "en"
        else:
            langcode = langs.LANGUAGES[language.title()]

        self.bot.cache.update("settings", ctx.guild.id, "language", langcode)
        await self.bot.db.execute("UPDATE guildsettings SET language = $2 WHERE guild_id = $1", ctx.guild.id, langcode)

        await ctx.send(_("Language succesfully set to `{0}`!").format(language.capitalize()))

    @checks.has_permissions(manage_guild=True)
    @commandExtra(name="disable-command", aliases=["disablecmd", "disable-cmd"], category="Bot Settings")
    async def disablecmd(self, ctx, *, command):
        cant_disable = ["help", "jishaku", "disable-command", "enable-command", "toggle-module", "toggle-category", "modules", "categories", "disabled"]

        if command.title() in self.bot.cogs.keys():
            return await ctx.send(_("This command is for toggling **commands**. `{0}` is a __module__ which you can disable by doing `{1}disable-module {0}`").format(command, ctx.prefix))

        cmd = self.bot.get_command(command.strip("<>"))

        if cmd is None:
            return await ctx.send(_("Could not find command `{0}`!").format(command.strip("<>")))

        if cmd.qualified_name in self.bot.cache.get("settings", ctx.guild.id, "disabled_commands"):
            return await ctx.send(_("This command is already disabled!"))

        if cmd.qualified_name in cant_disable:
            return await ctx.send(_("Not going to disable that command, that'd be really stupid..."))

        self.bot.cache.update("settings", ctx.guild.id, "disabled_commands", cmd.qualified_name)
        await self.bot.db.execute("INSERT INTO disabledcommands VALUES($1, $2)", ctx.guild.id, command)

        await ctx.send(_("`{0}` is now disabled!").format(cmd.qualified_name))

    @checks.has_permissions(manage_guild=True)
    @commandExtra(name="enable-command", aliases=["enablecmd", "enable-cmd"], category="Bot Settings")
    async def enablecmd(self, ctx, *, command):
        if command.title() in self.bot.cogs.keys():
            return await ctx.send(_("This command is for toggling **commands**. `{0}` is a __module__ which you can enable by doing `{1}enable-module {0}`").format(command, ctx.prefix))

        cmd = self.bot.get_command(command.strip("<>"))

        if cmd is None:
            return await ctx.send(_("Could not find command `{0}`!").format(command.strip("<>")))

        if cmd.qualified_name not in self.bot.cache.get("settings", ctx.guild.id, "disabled_commands"):
            return await ctx.send(_("This command is already enabled!"))

        self.bot.cache.update("settings", ctx.guild.id, "disabled_commands", cmd.qualified_name)
        await self.bot.db.execute("DELETE FROM disabledcommands WHERE guild_id = $1 AND command = $2", ctx.guild.id, command)

        await ctx.send(_("`{0}` has been re-enabled!").format(cmd.qualified_name))

    @groupExtra(name="prefix", category="Bot Settings", invoke_without_command=True)
    async def get_bot_prefix(self, ctx):
        msg = _("The prefix for this server is `{0}`!").format(ctx.cache.prefix)
        if pre := ctx.user.prefixes.get(ctx.guild.id):
            msg += "\n\n"
            msg += _("*You also have a personal prefix set here, which is `{0}`!*").format(pre)
        await ctx.send(msg)

    @checks.has_permissions(manage_guild=True)
    @get_bot_prefix.command(name="set")
    async def set_bot_prefix(self, ctx, prefix: str):
        await ctx.cache.set_prefix(prefix)
        await ctx.send(_("The prefix has been set to `{0}`!").format(prefix))

    @get_bot_prefix.command(name="me")
    async def set_me_prefix(self, ctx, prefix: str):
        await ctx.user.set_prefix(ctx.guild.id, prefix)
        await ctx.send(_("Your prefix has been set to `{0}`!").format(prefix))

    @groupExtra(name='set-role', category="Bot Settings", hidden=True, invoke_without_command=True)
    async def set_role(self, ctx):
        await ctx.send_help(ctx.command)

    @checks.has_permissions(manage_guild=True, manage_roles=True)
    @set_role.command(name="moderator")
    async def set_moderator(self, ctx, *, role: discord.Role):
        if self.bot.cache.get("roles", ctx.guild.id, "moderator") == role.id:
            return await ctx.send(_("This is already the moderator role!"))

        await self.bot.db.execute("UPDATE role_settings SET moderator_id = $1 WHERE guild_id = $2", role.id, ctx.guild.id)
        self.bot.cache.update("roles", ctx.guild.id, "moderator", role.id)

        await ctx.send(_("Role for moderators has been set to {0}!").format(role.mention), allowed_mentions=discord.AllowedMentions(roles=False))

    @checks.has_permissions(manage_guild=True, manage_roles=True)
    @set_role.command(name="booster")
    async def set_booster(self, ctx, *, role: discord.Role):
        if self.bot.cache.get("roles", ctx.guild.id, "booster") == role.id:
            return await ctx.send(_("This is already the booster role!"))

        await self.bot.db.execute("UPDATE role_settings SET booster_id = $1 WHERE guild_id = $2", role.id, ctx.guild.id)
        self.bot.cache.update("roles", ctx.guild.id, "booster", role.id)

        await ctx.send(_("Role for boosters has been set to {0}!").format(role.mention), allowed_mentions=discord.AllowedMentions(roles=False))

    @checks.has_permissions(manage_guild=True, manage_roles=True)
    @set_role.command(name="dj")
    async def set_dj(self, ctx, *, role: discord.Role):
        if self.bot.cache.get("roles", ctx.guild.id, "dj") == role.id:
            return await ctx.send(_("This is already the DJ role!"))

        await self.bot.db.execute("UPDATE role_settings SET dj_id = $1 WHERE guild_id = $2", role.id, ctx.guild.id)
        self.bot.cache.update("roles", ctx.guild.id, "dj", role.id)

        await ctx.send(_("Role for DJs has been set to {0}!").format(role.mention), allowed_mentions=discord.AllowedMentions(roles=False))

    @checks.has_permissions(manage_guild=True, manage_roles=True)
    @set_role.command(name="muted")
    async def set_muted(self, ctx, *, role: discord.Role):
        if self.bot.cache.get("roles", ctx.guild.id, "muted") == role.id:
            return await ctx.send(_("This is already the Muted role!"))

        await self.bot.db.execute("UPDATE role_settings SET mute_id = $1 WHERE guild_id = $2", role.id, ctx.guild.id)
        self.bot.cache.update("roles", ctx.guild.id, "muted", role.id)

        await ctx.send(_("The `Muted` role has been set to {0}!").format(role.mention), allowed_mentions=discord.AllowedMentions(roles=False))


def setup(bot):
    pass
