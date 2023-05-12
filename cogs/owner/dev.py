import copy
import inspect
import os
from io import BytesIO
from typing import Union

import discord
from core.cog import SubCog
from core.commands import groupExtra
from db import BaseUrls
from discord.ext import commands
from prettytable import PrettyTable
from utils import checks, tomledit
from utils.paginator import ErrorPages


class Developer(SubCog, category="Developer"):
    def __init__(self, bot):
        self.bot = bot

    @checks.is_owner(dev=True)
    @groupExtra(category="Developer", invoke_without_command=True)
    async def dev(self, ctx):
        await ctx.send_help(ctx.command)

    @checks.is_owner(dev=True)
    @dev.command(name="sql")
    async def sql(self, ctx, *, query):
        try:
            if not query.lower().startswith("select"):
                data = await self.bot.db.execute(query)
                return await ctx.send(data)

            data = await self.bot.db.fetch(query)
            if not data:
                return await ctx.send("Oops, something went wrong there...")
            columns = []
            values = []
            for k in data[0].keys():
                columns.append(k)

            for y in data:
                rows = []
                for v in y.values():
                    rows.append(v)
                values.append(rows)

            x = PrettyTable(columns)
            for d in values:
                x.add_row(d)

            await ctx.send(f"```ml\n{x}```")
        except Exception as e:
            await ctx.send(e)

    @checks.is_owner(dev=True)
    @dev.command(name="reboot", aliases=['shutdown', 'kys'])
    async def dev_reboot(self, ctx, *, force=None):
        if len(self.bot.diorite.players) != 0:
            if force is None:
                total = sum(1 for p in self.bot.diorite.players.values() if self.bot.diorite.get_player(p.guild).is_playing)
                if total != 0:
                    return await ctx.send(f"There are still {total} guilds using me for music. Use `{ctx.prefix}reboot -f` to force reboot me.")

            for player in self.bot.diorite.players.values():
                try:
                    await player.destroy()
                except:
                    continue

        await ctx.message.add_reaction('a:Gears_Loading:470313276832743425')
        # embed = discord.Embed(title="Rebooting...", color=0xfdac2b, timestamp=datetime.datetime.utcnow())
        # channel = self.bot.get_channel(514959099235008513)
        # await channel.send(embed=embed)
        await self.bot.bot_logout()

    @checks.is_owner(dev=True)
    @dev.command(name="su", aliases=['as'])
    async def dev_su(self, ctx, who: Union[discord.Member, discord.User], *, command: str):
        if who.id == self.bot.owner_id:
            return await ctx.send(file=discord.File('db/images/snyt.jpg'))
        msg = copy.copy(ctx.message)
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        await self.bot.invoke(new_ctx)

    @checks.is_owner(dev=True)
    @dev.group(name="cog", aliases=['module'], invoke_without_command=True)
    async def _cog(self, ctx):
        await ctx.send_help(ctx.command)

    @checks.is_owner(dev=True)
    @_cog.command(name="load", aliases=['l'])
    async def dev_cog_load(self, ctx, cog):
        try:
            self.bot.load_extension(f"cogs.{cog.lower()}")
        except commands.ExtensionNotFound:
            return await ctx.send(f"\U000026a0 Could not find module `cogs.{cog.lower()}.py`...")
        except commands.ExtensionAlreadyLoaded:
            return await ctx.send(f"\U000026a0 `cogs.{cog.lower()}.py` has already been loaded!")
        except commands.ExtensionFailed as e:
            return await ctx.send(f"\U000026a0 Module `cogs.{cog.lower()}` raised an Exception!\n\n```sh\n{e}```")
        await ctx.send(f"\U0001f4e5 Loaded module **{cog.lower()}.py**")

    @checks.is_owner(dev=True)
    @_cog.command(name="reload", aliases=['rl', 'r'])
    async def dev_cog_reload(self, ctx, cog=None):
        if cog is None:
            ext = []
            for f in os.listdir('cogs'):
                if str(f) in ('tests', '__pycache__'):
                    continue
                try:
                    self.bot.reload_extension(f"cogs.{f}")
                    ext.append(f"{ctx.emoji.check} | {f}")
                except:
                    ext.append(f"{ctx.emoji.xmark} | {f}")
                    continue
            return await ctx.send("\n".join(ext))

        try:
            self.bot.reload_extension(f"cogs.{cog.lower()}")
        except commands.ExtensionNotFound:
            return await ctx.send(f"\U000026a0 Could not find module `cogs.{cog.lower()}.py`...")
        except commands.ExtensionNotLoaded:
            return await ctx.send(f"\U000026a0 Module `cogs.{cog.lower()}` is not loaded.")
        except commands.ExtensionFailed as e:
            return await ctx.send(f"\U000026a0 Module `cogs.{cog.lower()}` raised an Exception!\n\n```sh\n{e}```")
        await ctx.send(f"\U0001f501 Reloaded module **{cog.lower()}.py**")

    @checks.is_owner(dev=True)
    @_cog.command(name="unload", aliases=['ul', 'u'])
    async def dev_cog_unload(self, ctx, cog):
        try:
            self.bot.unload_extension(f"cogs.{cog.lower()}")
        except commands.ExtensionNotFound:
            return await ctx.send(f"\U000026a0 Could not find module `cogs.{cog.lower()}.py`...")
        except commands.ExtensionNotLoaded:
            return await ctx.send(f"\U000026a0 Module `cogs.{cog.lower()}` is not loaded.")
        except commands.ExtensionFailed as e:
            return await ctx.send(f"\U000026a0 Module `cogs.{cog.lower()}` raised an Exception!\n\n```sh\n{e}```")
        await ctx.send(f"\U0001f4e4 Unloaded module **{cog.lower()}.py**")

    @checks.is_owner(dev=True)
    @dev.group(name="command", aliases=['cmd'], invoke_without_command=True)
    async def _command(self, ctx):
        await ctx.send_help(ctx.command)

    @checks.is_owner(dev=True)
    @_command.command(name="disable")
    async def dev_command_disable(self, ctx, command, *, reason):
        cant_disable = ["help", "jishaku", "disable-command", "enable-command", "toggle-module", "toggle-category", "modules", "categories", "dev"]
        cmd = self.bot.get_command(command)
        if cmd is None:
            return await ctx.send(f"Command `{command}` not found!")

        disabled = list(self.bot.cache.globaldisabled.keys())

        cmd_name = cmd.qualified_name

        if cmd_name in disabled and disabled != [None]:
            return await ctx.send("This command is already globally disabled!")

        if cmd.name in cant_disable or cmd.root_parent in cant_disable:
            return await ctx.send("Yea.... I'm not going to disable that command, that'd be really stupid...")

        await self.bot.db.execute("INSERT INTO globaldisabled VALUES($1, $2)", cmd_name, reason)
        self.bot.cache.update("globaldisabled", cmd_name, reason)

        await ctx.send(f"`{cmd_name}` has been globally disabled for **{reason}**!")

    @checks.is_owner(dev=True)
    @_command.command(name="enable")
    async def dev_command_enable(self, ctx, *, command):
        cmd = self.bot.get_command(command)
        if cmd is None:
            return await ctx.send(f"Command `{command}` not found!")

        disabled = list(self.bot.cache.globaldisabled.keys())

        cmd_name = cmd.qualified_name

        if cmd_name not in disabled and disabled != [None]:
            return await ctx.send("This command is already enabled!")

        await self.bot.db.execute("DELETE FROM globaldisabled WHERE command = $1", cmd_name)
        self.bot.cache.delete("globaldisabled", cmd_name)

        await ctx.send(f"`{cmd_name}` has been re-enabled!")

    @checks.is_owner(dev=True)
    @_command.command(name="info")
    async def dev_command_info(self, ctx, *, command):
        cmd = self.bot.get_command(command)
        if cmd is None:
            return await ctx.send(f"Command `{command}` not found!")

        source = cmd.callback.__code__
        filename = source.co_filename
        totallines, firstline = inspect.getsourcelines(source)

        cmd_name = f"{cmd.parent} {cmd.name}" if cmd.parent else cmd.name
        e = discord.Embed(color=0x36393E, title=f"__Command Info For:__ **{cmd_name}**")
        e.set_thumbnail(url=cmd.cog.big_icon)
        desc = f"**File location:** {filename[36:]}\n"
        desc += f"**Lines:** L{firstline}-L{firstline + len(totallines) -1} ({len(totallines)} lines)\n"
        cmd_usage = await self.bot.db.fetchval("SELECT sum(usage) FROM cmd_stats WHERE command = $1", cmd.qualified_name)
        desc += f"**Used:** {cmd_usage if cmd_usage else '0'}x"

        e.description = desc

        err = await self.bot.db.fetch("SELECT status FROM errors WHERE command = $1", cmd.qualified_name)
        if err != []:
            fix = len([x for x in err if x['status'] is True])
            unr = len([x for x in err if x['status'] is False])
            total = fix + unr
            e.add_field(name='Errors', value=f"<:check:314349398811475968> {fix} fixed\n<:xmark:314349398824058880> {unr} unresolved\n<:empty:314349398723264512> {total} total")
        else:
            e.add_field(name='Errors', value="<:check:314349398811475968> 0 fixed\n<:xmark:314349398824058880> 0 unresolved\n<:empty:314349398723264512> 0 total")

        await ctx.send(embed=e)

    @checks.is_owner(dev=True)
    @dev.group(name="errors", aliases=['err', 'error'], invoke_without_command=True)
    async def _errors(self, ctx):
        await ctx.send_help(ctx.command)

    @checks.is_owner(dev=True)
    @_errors.command(name="list", aliases=['l'])
    async def dev_errors_list(self, ctx):
        errors = await self.bot.db.fetch("SELECT command, array_agg(id) AS ids FROM errors WHERE status = false GROUP BY command, status ORDER BY ids")
        if not errors:
            return await ctx.send("There are no more errors to list that arent fixed.")
        tracked = [x for x, in await self.bot.db.fetch("SELECT error_id FROM error_tracking")]
        s = "\\*"
        entries = [f"`{x['command']}` - **{'**, **'.join((str(i) if i not in tracked else str(i)+s) for i in x['ids'])}**" for x in errors]
        await self.bot.utils.paginate(
            ctx,
            entries=entries,
            title="Errors IDs per command",
            footertext=f"Commands: {len(errors)} | Total Unresolved: {sum(len(err['ids']) for err in errors)}",
            show_page_num=True,
            per_page=15,
            timeout=120,
            suffix=f"\n*{s} = error is being tracked by someone*"
        )

    @checks.is_owner(dev=True)
    @_errors.command(name="command", aliases=['cmd'])
    async def dev_errors_cmd(self, ctx, *, command):
        cmd = self.bot.get_command(command)
        if cmd is None:
            return await ctx.send(f"Command `{command}` not found!")

        err = await self.bot.db.fetch("SELECT * FROM errors WHERE command = $1", cmd.qualified_name)
        if err == []:
            return await ctx.send(f"No errors found for command `{command}`!")

        errors = []
        for x in err:
            content = f"`{x['invocation']}`\n```sh\n{x['error']}```"
            if len(content) > 2048:
                async with self.bot.session.post(BaseUrls.hb+"documents", data=x['error']) as resp:
                    data = await resp.json()
                    key = data['key']
                    content = f"`{x['invocation']}`\nContent too long, so I uploaded it to CharlesBin:\n{BaseUrls.hb}{key}.sh"
            errors.append(content)

        paginator = ErrorPages(ctx,
                           error_ids=[x['id'] for x in err],
                           entries=errors,
                           status=[x['status'] for x in err],
                           title=f"Errors for command `{command}`",
                           thumbnail="https://i.dlpng.com/static/png/3949766-error-png-92-images-in-collection-page-3-error-png-900_858_preview.png")
        await paginator.start()

    @checks.is_owner(dev=True)
    @_errors.command(name="fix")
    async def dev_errors_fix(self, ctx, *error_ids: int):
        valid_ids = []
        for error_id in error_ids:
            e = await self.bot.db.fetchrow("SELECT * FROM errors WHERE id = $1", error_id)
            if not e:
                continue
                # return await ctx.send(f"`{error_id} is not a valid error ID!")

            if e['status']:
                continue
                # return await ctx.send("This error has already been marked as **fixed**!")

            valid_ids.append((error_id,))
            users = [x for x, in await self.bot.db.fetch("SELECT user_id FROM error_tracking WHERE error_id = $1", error_id)]
            if users:
                for _id in users:
                    user = self.bot.get_user(_id)
                    if user is not None:
                        try:
                            await user.send(f"Hey there! You were tracking error **#{error_id}** which my owner has now marked as | {ctx.emoji.check} fixed!\n\n*If you dont remember:*\n**Command:** `{e['command']}`\n**Error:** ```sh\n{e['short_error']}```")
                        except:
                            pass

        if not valid_ids:
            return await ctx.send("Apparently, all IDs passed were either invalid IDs or were already marked as fixed.")
        await self.bot.db.executemany("UPDATE errors SET status = $2 WHERE id IN ($1)", [(_id[0], True) for _id in valid_ids])
        await self.bot.db.executemany("DELETE FROM error_tracking WHERE error_id IN ($1)", valid_ids)
        if len(valid_ids) > 1:
            return await ctx.send(f"`{len(valid_ids)}/{len(error_ids)}` errors have successfully been marked as **fixed**!")
        await ctx.send(f"Error `{valid_ids[0][0]}` has successfully been marked as **fixed**!")

    @checks.is_owner(dev=True)
    @_errors.command(name="unresolved", aliases=['set'])
    async def dev_errors_set(self, ctx, error_id: int):
        e = await self.bot.db.fetchrow("SELECT status FROM errors WHERE id = $1", error_id)
        if e is None:
            return await ctx.send(f"`{error_id} is not a valid error ID!")

        if not e['status']:
            return await ctx.send("This error has already been marked as **unresolved**!")

        await self.bot.db.execute("UPDATE errors SET status = $2 WHERE id = $1", error_id, False)
        await ctx.send(f"Error `{error_id}` has successfully been marked as **unresolved**!")

    @checks.is_owner(dev=True)
    @_errors.command(name="show")
    async def dev_errors_show(self, ctx, error_id: int):
        e = await self.bot.db.fetchrow("SELECT * FROM errors WHERE id = $1", error_id)
        if e is None:
            return await ctx.send(f"`{error_id} is not a valid error ID!")

        if e['status']:
            # status = f"<:check:314349398811475968> Error {e['id']} is fixed!"
            footer = {"icon": "https://trac.cyberduck.io/raw-attachment/wiki/help/en/howto/mount/sync/overlay-error.png", "text": f"Change the error status to 'unresolved' by doing | {ctx.prefix}dev cmd set-error <error ID>"}
        else:
            # status = f"<:xmark:314349398824058880> Error {e['id']} is not fixed yet..."
            footer = {"icon": "https://trac.cyberduck.io/raw-attachment/wiki/help/en/howto/mount/sync/overlay-sync.png", "text": f"Change the error status to 'fixed' by doing | {ctx.prefix}dev cmd fix-error <error ID>"}
        content = f"`{e['invocation']}`\n```sh\n{e['error']}```"
        if len(content) > 2048:
            async with self.bot.session.post(BaseUrls.hb+"documents", data=e['error']) as resp:
                data = await resp.json()
                key = data['key']
                content = f"`{e['invocation']}`\nContent too long, so I uploaded it to CharlesBin:\n{BaseUrls.hb}{key}.sh"

        emb = discord.Embed(title=f"Error `{e['id']}`", color=ctx.embed_color, description=content)
        emb.set_thumbnail(url="https://i.dlpng.com/static/png/3949766-error-png-92-images-in-collection-page-3-error-png-900_858_preview.png")
        emb.set_footer(icon_url=footer['icon'], text=footer['text'])
        await ctx.send(embed=emb)

    @checks.is_owner(dev=True)
    @_errors.command(name="all", aliases=['showall', 'need-fix'])
    async def dev_errors_all(self, ctx):
        e = await self.bot.db.fetch("SELECT * FROM errors WHERE status = $1", False)

        errors = []
        for x in e:
            # status = f"<:xmark:314349398824058880> Error `{x['id']}`"
            content = f"`{x['invocation']}`\n```sh\n{x['error']}```"
            if len(content) > 2048:
                async with self.bot.session.post(BaseUrls.hb+"documents", data=x['error']) as resp:
                    data = await resp.json()
                    key = data['key']
                    content = f"`{x['invocation']}`\nContent too long, so I uploaded it to CharlesBin:\n{BaseUrls.hb}{key}.sh"
            errors.append(content)

        paginator = ErrorPages(ctx,
                           error_ids=[x['id'] for x in e],
                           entries=errors,
                           status=[x['status'] for x in e],
                           title="Unresolved errors",
                           thumbnail="https://i.dlpng.com/static/png/3949766-error-png-92-images-in-collection-page-3-error-png-900_858_preview.png")

        await paginator.start()

    @checks.is_owner(dev=True)
    @dev.group(name="edit", aliases=['botedit', 'change'], invoke_without_command=True)
    async def _change(self, ctx):
        await ctx.send_help(ctx.command)

    @checks.is_owner(dev=True)
    @_change.command(name="streaming")
    async def dev_change_streaming(self, ctx, *, status):
        await self.bot.change_presence(
            activity=discord.Streaming(
                platform="Twitch",
                name=status,
                game="Discord",
                url="https://twitch.tv/iDutchy"),
            status=discord.Status.online
        )
        await ctx.send(f"Status updated to **Streaming {status}**")

    @checks.is_owner(dev=True)
    @_change.command(name="playing")
    async def dev_change_playing(self, ctx, *, status):
        await self.bot.change_presence(
            activity=discord.Game(type=0, name=status),
            status=discord.Status.online
        )
        await ctx.send(f"Status updated to **Playing {status}**")

    @checks.is_owner(dev=True)
    @_change.command(name="listening")
    async def dev_change_listening(self, ctx, *, status):
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening,
                name=status)
            )
        await ctx.send(f"Status updated to **Listening to {status}**")

    @checks.is_owner(dev=True)
    @_change.command(name="watching")
    async def dev_change_watching(self, ctx, *, status):
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching,
                name=status)
            )
        await ctx.send(f"Status updated to **Watching {status}**")

    @checks.is_owner(dev=True)
    @_change.command(name="competing")
    async def dev_change_competing(self, ctx, *, status):
        if status.lower().startswith('in '):
            status = status[3:]
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.competing,
                name=status)
            )
        await ctx.send(f"Status updated to **Competing in {status}**")

    @checks.is_owner(dev=True)
    @_change.command(name="nickname", aliases=['nick'])
    async def dev_change_nickname(self, ctx, *, name: str = None):
        await ctx.guild.me.edit(nick=name)
        if name:
            await ctx.send(f"Now using **{name}** as nickname in this server")
        else:
            await ctx.send("Nickname removed")

    @checks.is_owner(dev=True)
    @_change.command(name="avatar")
    async def dev_change_avatar(self, ctx, url: str = None):
        if url is None and not ctx.message.attachments:
            return await ctx.send("Without an URL or attachment I can't really change the avatar.... :/")

        url = url or ctx.message.attachments[0].url

        async with self.bot.session.get(url) as f:
            bio = await f.read()
        await self.bot.user.edit(avatar=bio)
        await ctx.send("Avatar has been changed to", file=discord.File(BytesIO(bio), filename="avatar.png"))

    @checks.is_owner(dev=True)
    @_change.command(name="botversion")
    async def dev_change_botversion(self, ctx, *, version):
        tomledit.change_value("db/config.toml", "settings", "BOT_VERSION", f"v{version}")
        self.bot.config['settings']["BOT_VERSION"] = f"v{version}"
        await ctx.send(f"Version has been updated to **v{version}**!")


def setup(bot):
    pass
