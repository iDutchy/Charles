import asyncio

import discord
from core import context, i18n
from core.cog import SubCog
from db import BaseUrls
from discord.ext import commands, flags
from PIL import Image
from utils import checks, utility


class CommandEvents(SubCog):
    def __init__(self, bot):
        self.bot = bot

    async def bot_check(self, ctx):
        if ctx.author.id == ctx.bot.owner_id:
            return True

        if ctx.author.id in self.bot.cache.get("blacklist", "user"):
            raise checks.DisabledCommand(_("You have been blocked from using my commands!"))

        if ctx.command.qualified_name == "help":
            return True

        if (cmd := ctx.command.qualified_name) in self.bot.cache.get("globaldisabled").keys():
            raise checks.DisabledCommand(_("**{0}** has been disabled by the bot owner for: `{1}`").format(cmd, self.bot.cache.get('globaldisabled', cmd)))

        if not ctx.guild:
            return True

        if ctx.command.cog:
            if (cog := ctx.command.cog.qualified_name.lower()) in self.bot.cache.get("modules", ctx.guild.id).keys():
                if self.bot.cache.get("modules", ctx.guild.id, cog) == False:
                    return False

                if hasattr(ctx.command, "category"):
                    if ctx.command.category.name == "Hidden":
                        return True
                    if self.bot.cache.get("categories", ctx.guild.id, ctx.command.category.cachestring) == False:
                        return False

        if ctx.command.qualified_name in self.bot.cache.get("settings", ctx.guild.id, "disabled_commands"):
            return False

        return True

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if ctx.guild is None:
            return

        # if not ctx.guild.chunked:
        #     await ctx.guild.chunk()
            # p = mp.Process(target=utility.GuildChunker().chunk_one, args=(ctx.guild,))
            # p.start()
            # self.bot.mp_processes.append(p)

        if ctx.command.cog_name == "Private":
            return

        g = ctx.guild.id
        u = ctx.author.id
        c = ctx.command.qualified_name

        if not g in self.bot.cache.cmd_stats.keys():
            self.bot.cache.cmd_stats[g] = dict()

        if not u in self.bot.cache.cmd_stats[g].keys():
            self.bot.cache.cmd_stats[g][u] = dict()

        if not c in self.bot.cache.cmd_stats[g][u].keys():
            self.bot.cache.cmd_stats[g][u][c] = 1
        else:
            self.bot.cache.cmd_stats[g][u][c] += 1

    @staticmethod
    async def send_error(ctx, title, desc):
        e = discord.Embed(color=0xFF7070)
        e.title = title
        e.description = desc
        await ctx.send(embed=e)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, exc):
        HANDLES = {
            commands.DisabledCommand: _("This command has been disabled by the bot owner!"),
            commands.BadUnionArgument: _("I could not convert the argument you provided to `{0}`..."),
            # commands.CheckFailure: _("Yeah, so... I really have no clue what happened, but something with permissions broke I gues..."),
            commands.NotOwner: _("This command can only be executed by my owner!"),
            commands.UserInputError: _("The input you provided was invalid."),
            commands.TooManyArguments: _("You provided *too many* arguments for this command!"),
            commands.NSFWChannelRequired: _("This command can only be used in NSFW channels!"),
            commands.PrivateMessageOnly: _("This command can only be used in my DMs!"),
            asyncio.TimeoutError: _("The requested server took too long to respond..."),
            checks.Private: _("This is a private command and can therefore not be used in this server."),
            Image.DecompressionBombError: _("Nice try, but I'm not allowing DOS attacks with a decompression bomb. Do it again and you'll be blacklisted from my commands!")
        }

        if ctx.cog and commands.Cog._get_overridden_method(ctx.cog.cog_command_error):
            return

        if hasattr(ctx.command, 'on_error'):
            return

        if isinstance(exc, context.NoPerms):
            try:
                await ctx.author.send(str(exc))
                return
            except:
                return

        if isinstance(exc, commands.CommandInvokeError):
            ctx.command.reset_cooldown(ctx)
            exc = exc.original

        if isinstance(exc, commands.CommandNotFound):
            return

        if isinstance(exc, commands.CommandOnCooldown):
            await self.send_error(ctx,
                _("{0} | **Command On Cooldown!**").format(ctx.emoji.clock),
                _("`Woah! Easy there. You can use this command again in {0:.2f} seconds!").format(exc.retry_after))
            return

        if isinstance(exc, commands.MaxConcurrencyReached):
            types = {
                commands.BucketType.guild: _("This command is already running in this server! Please wait for it to finish."),
                commands.BucketType.channel: _("This command is already running in this channel! Please wait for it to finish or use a different channel."),
                commands.BucketType.user:  _("You are already using this command! Please wait for it to finish.")
            }
            await self.send_error(ctx,
                _("{0} | **Command On Cooldown!**").format(ctx.emoji.clock),
                types.get(exc.per))
            return

        ctx.command.reset_cooldown(ctx)

        if isinstance(exc, checks.DisabledCommand):
            await self.send_error(ctx,
                _("{0} | No Access!").format(ctx.emoji.warn),
                str(exc))
            return


        if isinstance(exc, context.NoPerms):
            try:
                await ctx.author.send(_("Sorry, but it looks like I do not have permissions to send messages there!"))
                return
            except:
                return

        if isinstance(exc, context.SessionError):
            await self.send_error(ctx,
                _("{0} | API Issue!").format(ctx.emoji.warn),
                str(exc))
            return

        if isinstance(exc, commands.NoPrivateMessage):
            await self.send_error(ctx,
                _("{0} | **Server Only!**").format(ctx.emoji.warn),
                _("This command can only be used in servers, not in my DMs..."))
            return

        if isinstance(exc, commands.BadArgument):
            param = list(ctx.command.clean_params)[len(ctx.args[2:])]
            await self.send_error(ctx,
                _("{0} | **Invalid Argument!**").format(ctx.emoji.warn),
                _("You provided an invalid argument for the parameter `{0}`!").format(param.title()))
            return

        if isinstance(exc, commands.TooManyArguments):
            if isinstance(ctx.command, commands.Group):
                return

        if isinstance(exc, commands.MissingRequiredArgument):
            await self.send_error(ctx,
                _("{0} | **Missing Arguments!**").format(ctx.emoji.warn),
                _("You forgot the `{0}` parameter while using `{1}`!").format(exc.param.name.title(), ctx.prefix + str(ctx.command)))
            return

        if isinstance(exc, commands.BotMissingPermissions):
            await self.send_error(ctx,
                _("{0} | **Missing Permissions!**").format(ctx.emoji.warn),
                _("I need the `{0}` permission to execute this command!").format(exc.missing_perms[0].replace('_', ' ').title()))
            return

        if isinstance(exc, commands.MissingPermissions):
            await self.send_error(ctx,
                _("{0} | **Missing Permissions!**").format(ctx.emoji.warn),
                _("You need the `{0}` permission to execute this command!").format(exc.missing_perms[0].replace('_', ' ').title()))
            return

        if isinstance(exc, flags._parser.ArgumentParsingError):
            await self.send_error(ctx,
                _("{0} | **Invalid Usage!**").format(ctx.emoji.warn),
                _("Invalid use of the flags for this command. See `{0}` for more info on using the flags.").format(f"{ctx.prefix}help {ctx.command.qualified_name}"))
            return

        if isinstance(exc, checks.MusicError):
            await self.send_error(ctx,
                _("{0} | **Music Error!**").format(ctx.emoji.warn),
                str(exc))
            return

        if isinstance(exc, checks.NoVoter):
            await self.send_error(ctx,
                _("{0} | **Missing Permissions!**").format(ctx.emoji.warn),
                _("You have not voted yet! To use this command, please [vote here]({0}).\n\n*After voting, it may take up to 1 minute for your vote to register*").format("https://charles-bot.xyz/vote"))
            return

        msg = HANDLES.get(type(exc), None)
        if not msg:
            if isinstance(exc, commands.CheckFailure):
                return
            log = self.bot.get_channel(522855838881284100)
            e = discord.Embed(color=0xFF7070)

            tb = self.bot.exception(exc)
            se = f"{type(exc).__name__}: {exc}"
            check = await self.bot.db.fetchval("SELECT id FROM errors WHERE command = $1 AND short_error = $2 AND status = $3", ctx.command.qualified_name, se, False)
            if check:
                await self.send_error(ctx,
                    _("{0} | Known Error!").format(ctx.emoji.warn),
                    _("This command raised an error which is already known by my developer!\nYou can reference to this error with ID **#{0}**.\n\nIf you want to keep updated with the status of this error, you can track it by doing `{1}error track {0}`!\n```sh\n{2}: {3}```\n[Visit Support Server To Learn More!](https://discord.gg/wZSH7pz)").format(check, ctx.prefix, type(exc).__name__, exc))

                e.title = f"Error #{check} occured again during command execution"
                e.description = f"```sh\n{se}```"
                e.add_field(name='Info', value=f"`{ctx.message.clean_content}`\nServer: **{ctx.guild}** ({ctx.guild.id})\nChannel: **{ctx.channel}** ({ctx.channel.id})\nAuthor: **{ctx.author}** ({ctx.author.id})")
                await log.send(embed=e)
            else:
                if ctx.command.cog_name != "Owner":
                    err_id = await self.bot.db.fetchval("INSERT INTO errors(command, error, invocation, short_error) VALUES($1, $2, $3, $4) RETURNING id", ctx.command.qualified_name, ''.join(tb), ctx.message.clean_content, se)
                    await self.send_error(ctx,
                        _("{0} | Uncaught Error!").format(ctx.emoji.warn),
                        _("This command raised an unknown error. My developer has been notified of it!\nYou can also refer to this error with ID **#{2}**.\n\nIf you want to keep updated with the status of this error, you can track it by doing `{3}error track {2}`!\n```sh\n{0}: {1}```\n[Visit Support Server To Learn More!](https://discord.gg/wZSH7pz)").format(type(exc).__name__, exc, err_id, ctx.prefix))
                    desc = f"```sh\n{''.join(tb)}```"
                    if len(desc) > 2048:
                        async with self.bot.session.post(BaseUrls.hb+"documents", data=''.join(tb)) as resp:
                            data = await resp.json()
                            key = data['key']
                            desc = f"Content too long, so I uploaded it to CharlesBin:\n{BaseUrls.hb}{key}.sh"
                    e.title=f"Error occured during command execution. | ID: #{err_id}"
                    e.description = desc
                    e.add_field(name='Info', value=f'''`{ctx.message.clean_content}`
    Server: **{ctx.guild}** ({ctx.guild.id})
    Channel: **{ctx.channel}** ({ctx.channel.id})
    Author: **{ctx.author}** ({ctx.author.id})
    ''')
                    await log.send(embed=e)
                else:
                    await self.send_error(ctx,
                        f"{ctx.emoji.warn} | Owner Command Error",
                        f"It borked, here's ur stupid mess. Just, don't fuck up so much ok?\n\n```sh\n{''.join(tb)}```")
            return

        if hasattr(exc, 'param'):
            await self.send_error(ctx,
                _("{0} | Command Error!").format(ctx.emoji.warn),
                msg.format(exc.param.name.title()))
        else:
            await self.send_error(ctx,
                _("{0} | Command Error!").format(ctx.emoji.warn),
                msg)

def setup(bot):
    pass
