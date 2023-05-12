import difflib

import discord
from core import i18n
from discord.ext import commands

from .cache import CacheManager as cm

# class BetterHelpCommandImpl(commands.help._HelpCommandImpl, cmds.commandsPlus):
#     def __init__(self, inject, *args, **kwargs):
#         super().__init__(inject.command_callback, *args, **kwargs)


class HelpCore(commands.HelpCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verify_checks = False

        self.owner_cogs = ['Owner', 'Economy', "Newjsk", "Running Tests"]
        self.ignore_cogs = ["Help", "Events", "Test"]

    # def _add_to_bot(self, bot):
    #     command = BetterHelpCommandImpl(self, **self.command_attrs)
    #     command._category = "Bot Info"
    #     bot.add_command(command)
    #     self._command_impl = command

    async def perm_check(self, cmd):
        try:
            return await cmd.can_run(self.context)
        except:
            return False

    def get_command_signature(self, command):
        if not hasattr(command, "category"):
            setattr(command, "category", self.context.bot.get_category("Other"))
        return f"{command.cog_name} | {command.category.name if not command.parent else command.root_parent.category.name}"

    def get_command_usage(self, command):
        lang = cm.get("settings", self.context.guild.id, "language")
        usage = cm.cmd_help.get(lang, {"uhoh": "NotFound"}).get(f"{command.qualified_name} - usage")
        if not usage:
            usage = cm.get("cmd_help", "en", f"{command.qualified_name} - usage")
        return usage

    def get_command_desc(self, command):
        lang = cm.get("settings", self.context.guild.id, "language")
        desc = cm.cmd_help.get(lang, {"uhoh": "NotFound"}).get(f"{command.qualified_name} - desc")
        if not desc:
            desc = cm.get("cmd_help", "en", f"{command.qualified_name} - desc")
        return desc

    def get_command_brief(self, command):
        lang = cm.get("settings", self.context.guild.id, "language")
        brief = cm.cmd_help.get(lang, {"uhoh": "NotFound"}).get(f"{command.qualified_name} - brief")
        if not brief:
            brief = cm.get("cmd_help", "en", f"{command.qualified_name} - brief")
        return brief

    async def command_callback(self, ctx, *, command=None):
        await self.prepare_help_command(ctx, command)

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        # Check if it's a cog
        cog = ctx.bot.get_cog(command.title())
        if cog is not None:
            return await self.send_cog_help(cog)

        maybe_coro = discord.utils.maybe_coroutine

        category = ctx.bot.get_category(command.title())
        if category is not None:
            return await self.send_category_help(category)

        # If it's not a cog then it's a command.
        keys = command.split(' ')
        cmd = ctx.bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(self.command_not_found, self.remove_mentions(keys[0]))
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)

    async def common_command_formatting(self, command):
        e = discord.Embed(color=self.context.embed_color)
        if command.cog_name != "Jishaku":
            e.set_thumbnail(url=command.cog.big_icon)
        e.description = self.get_command_desc(command) or _("No description provided...")
        e.title = f"{command.qualified_name} {self.get_command_usage(command) or ''}"
        e.set_author(icon_url=self.context.bot.user.avatar.with_static_format("png"), name=self.get_command_signature(command))
        if await self.perm_check(command) is not True:
            e.set_footer(text=_("This command can not be used because you or I do not have the required permissions here..."),icon_url="https://cdn.discordapp.com/emojis/620414236010741783.png?v=1")

        if command.aliases:
            aliases = f"`{'`, `'.join(command.aliases)}`"
            e.add_field(name=_("Aliases:"), value=aliases)
        return e

    def command_not_found(self, string):
        fuzzy_matches = []
        can_run_commands = []
        if self.context.guild:
            for command in set(self.context.bot.walk_commands()):
                if command.qualified_name in cm.get("settings", self.context.guild.id, "disabled_commands"):
                    continue
                try:
                    if not cm.get("modules", self.context.guild.id, command.cog.qualified_name.lower()):
                        continue
                except:
                    continue
                if hasattr(command, 'category'):
                    try:
                        if not cm.get("categories", self.context.guild.id, command.category.cachestring):
                            continue
                    except:
                        continue

                can_run_commands.append(command.qualified_name)

        fuzzy_matches = difflib.get_close_matches(string, set(can_run_commands))
        if not fuzzy_matches:
            return _('Sorry, I have no command called "{0}"...').format(string)[:2000]

        return _("**Command '{0}' not found!**\nDid you mean...\n\n{1}").format(string, '\n'.join(fuzzy_matches[:4]))

    async def can_send_category_help(self, category):
        if category.cog_name in self.ignore_cogs:
            await self.send_error_message(self.command_not_found(category.name.lower()))
            return False

        if category.name == "Translators":
            if self.context.author.id in self.context.bot.translators:
                return True

        if category.cog_name == "Settings":
            return True

        if self.context.author.id in self.context.bot.config['settings']['BOT_DEVS'] and category.name == 'Developer':
            return True

        if category.cog_name in self.owner_cogs and self.context.author.id == self.context.bot.owner_id:
            return True

        if not self.context.guild:
            return True

        if category.cog_name in self.owner_cogs and self.context.author.id != self.context.bot.owner_id:
            await self.send_error_message(self.command_not_found(category.name.lower()))
            return False

        try:
            if not cm.get("modules", self.context.guild.id, category.cog_name.lower()):
                await self.send_error_message(self.command_not_found(category.name.lower()))
                return False

            if not cm.get("categories", self.context.guild.id, category.cachestring):
                await self.send_error_message(self.command_not_found(category.name.lower()))
                return False
        except:
            badarg = list(self.context.message.content.split(" "))[len(list(self.context.prefix.split(" ")))]
            await self.send_error_message(self.command_not_found(badarg))
            return False
        else:
            return True

    async def can_send_command_help(self, command):
        # if self.context.command.qualified_name == "help":
        #     return True

        badarg = list(self.context.message.content.split(" "))[len(list(self.context.prefix.split(" ")))]
        if hasattr(command, 'category'):
            category = command.category
        else:
            if command.cog_name == 'Jishaku':
                category = self.context.bot.get_category('Other')
            elif command.qualified_name == "help":
                category = self.context.bot.get_category('Bot Info')
            else:
                category = command.root_parent.category

        if command.cog_name in self.ignore_cogs[1:]:
            await self.send_error_message(self.command_not_found(badarg))
            return False

        if category.name == "Translators":
            if self.context.author.id in self.context.bot.translators:
                return True

        if category.name == "Developer" and self.context.author.id in self.context.bot.config['settings']['BOT_DEVS']:
            return True

        if category.cog_name in self.owner_cogs and self.context.author.id == self.context.bot.owner_id:
            return True

        if category.name == "Hidden":
            return True

        if not self.context.guild:
            return True

        if command.cog_name in self.owner_cogs and self.context.author.id != self.context.bot.owner_id:
            await self.send_error_message(self.command_not_found(badarg))
            return False

        if command.cog_name == "Settings":
            return True

        try:
            if not cm.get("modules", self.context.guild.id, command.cog_name.lower()):
                await self.send_error_message(self.command_not_found(badarg))
                return False

            if command.qualified_name in cm.get("settings", self.context.guild.id, "disabled_commands"):
                await self.send_error_message(self.command_not_found(badarg))
                return False

            if command.parent:
                command = command.root_parent

            if not cm.get("categories", self.context.guild.id, category.cachestring):
                await self.send_error_message(self.command_not_found(badarg))
                return False
        except:
            await self.send_error_message(self.command_not_found(badarg))
            return False
        return True

    async def can_send_cog_help(self, cog):
        if self.context.command.qualified_name == "help":
            return True

        if cog.qualified_name == "Settings":
            return True

        badarg = list(self.context.message.content.split(" "))[len(list(self.context.prefix.split(" ")))]

        if cog.qualified_name.title() in self.ignore_cogs:
            await self.send_error_message(self.command_not_found(badarg))
            return False

        if cog.qualified_name.title() in self.owner_cogs and self.context.author.id not in self.context.bot.config['settings']['BOT_DEVS']:
            await self.send_error_message(self.command_not_found(badarg))
            return False

        if not self.context.guild:
            return True

        try:
            if not cm.get("modules", self.context.guild.id, cog.qualified_name.lower()):
                await self.send_error_message(self.command_not_found(badarg))
                return False
        except:
            await self.send_error_message(self.command_not_found(badarg))
            return False
        return True

    def command_is_enabled(self, command):
        if self.context.author.id != self.context.bot.owner_id and (command.hidden or command.category.name.lower() == "hidden"):
            return False

        if self.context.author.id == self.context.bot.owner_id and command.cog_name.title() in self.owner_cogs:
            return True

        if self.context.author.id in self.context.bot.config['settings']['BOT_DEVS'] and command.category.name == "Developer":
            return True

        if command.category.name == "Translators":
            if self.context.author.id in self.context.bot.translators:
                return True

        if command.cog_name == "Settings":
            return True

        if not self.context.guild:
            return True
        try:
            if not cm.get("categories", self.context.guild.id, command.category.cachestring):
                return False

            if command.qualified_name in cm.get("settings", self.context.guild.id, "disabled_commands"):
                return False
        except:
            return False
        return True
