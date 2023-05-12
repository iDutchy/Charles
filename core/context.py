import asyncio
import importlib
from io import BytesIO

import aiohttp
import diorite
import discord
from discord.ext import commands
from utils.checks import MusicError

from . import emojis, i18n, util  # noqa: F401


class SessionError(commands.CommandError):
    def __init__(self, message):
        super().__init__(message)


class NoPerms(commands.CommandError):
    def __init__(self, message):
        super().__init__(message)


class MyContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __rshift__(self, other):
        return self.send(other, edit=False)

    @property
    def cache(self):
        if self.guild.id not in self.bot._guild_cache:
            self.bot.create_guild_cache(self.guild.id)
        return self.bot._guild_cache.get(self.guild.id)

    @property
    def user(self):
        if self.author.id not in self.bot._user_cache:
            self.bot.create_user_cache(self.author.id)
        return self.bot._user_cache.get(self.author.id)

    @property
    def emoji(self):
        importlib.reload(emojis)
        return emojis.Emoji(self.bot)

    @property
    def player(self):
        mod = importlib.import_module("cogs.music.player")
        importlib.reload(mod)
        # return self.bot.wavelink.get_player(guild_id=self.guild.id, cls=Player, context=self)
        return self.bot.diorite.get_player(self.guild, cls=mod.Player, ctx=self)

    @property
    def timeit(self):
        return util.TimeIt(self)

    def loading(self, message=None):
        return util.Loading(self, message)

    async def get_tracks(self, *args, **kwargs):
        try:
            tracks = await self.player.node.get_tracks(*args, **kwargs)
        except diorite.exceptions.TrackLoadError as e:
            message = e.error_message or e.message
            if e.severity == "FAULT":
                raise MusicError(_("Something went wrong while searching for songs. Please try again."))
            elif e.severity == "SUSPICIOUS":
                # if message == "Could not find tracks from mix.":
                #     raise MusicError('None ig')
                raise MusicError(_("Reveived an unexpected response from YouTube. Please try again."))
            elif e.severity == "COMMON":
                if message.startswith("This playlist is private"):
                    raise MusicError(_("Could not load tracks because this is a private playlist!"))
                elif message.startswith("This track is not available") or message.startswith("This video is not available"):
                    raise MusicError(_("The song could not be loaded at the moment. Please try again."))
                elif message.startswith("We're processing this video"):
                    raise MusicError(_("This video is still being processed. Please try again later."))
                elif "on copyright grounds" in message:
                    raise MusicError(_("This video contains copyrighted content and could therefore not be loaded."))
            else:
                raise MusicError(message)
        else:
            if not tracks:
                raise MusicError(_("No songs were found with that query. Please try again."))
            else:
                return tracks

    @property
    def embed_color(self):
        if self.guild is None:
            return 0xFE8000
        col = self.cache.color
        if col == self.bot.themes["Default"].color:
            return self.bot.theme.color
        else:
            return col

    async def get(self, url, *args, return_type="json", **kwargs):
        try:
            res = await self.bot.session.get(url, *args, **kwargs)
        except aiohttp.client_exceptions.ClientConnectorError:
            raise SessionError(_("Network is unreachable, please try again later!"))
        if res.status == 200:
            try:
                if return_type == "json":
                    res = await res.json()
                    # if not res:
                    #     raise SessionError(_("The API returned no data, the request was likely too big..."))
                elif return_type == "text":
                    res = await res.text()
                    # if not res:
                    #     raise SessionError(_("The API returned no data, the request was likely too big..."))
                elif return_type == "read":
                    res = await res.read()
                    # if not res:
                    #     raise SessionError(_("The API returned no data, the request was likely too big..."))
                elif return_type == "io":
                    res = await res.read()
                    if res:
                        res = BytesIO(res)
                    # res = BytesIO(await res.read())
                    # if not res:
                    #     raise SessionError(_("The API returned no data, the request was likely too big..."))
                    # res = BytesIO(res)
                elif return_type == "none":
                    pass
                    # if not res:
                    #     raise SessionError(_("The API returned no data, the request was likely too big..."))
                else:
                    raise ValueError(_("Invalid return type was provided: {}").format(return_type))
                if not res:
                    raise SessionError(_("The API returned no data, the request was likely too big..."))
                return res
            except:
                raise SessionError(_("Something broke in the API because I could not load it..."))
        elif res.status == 400:
            raise SessionError(_("The API received a bad request, if you provided any arguments, please check if they're correct!"))
        elif res.status == 413:
            raise SessionError(_("The request sent to the API was too big!"))
        elif res.status == 502:
            raise SessionError(_("Bad Gateway. If you provided any arguments in the command, please check if they're all correct! if they are, try again."))
        elif res.status == 503:
            raise SessionError(_("API is unavailable at the moment, try again later!"))
        elif res.status == 504:
            raise SessionError(_("The API timed out. The request was likely too big to process..."))

    async def wait_for(self, message, options=None, timeout=30, loop=False):
        await self.send(message)

        def check(m):
            return m.author == self.author and m.channel == self.channel

        if loop:
            done = False
            while done is not True:
                try:
                    msg = await self.bot.wait_for('message', check=check, timeout=timeout)

                    if options is not None:
                        if not msg.content.lower() in options:
                            await self.send(_("Invalid option, please try again!"))

                        if msg.content.lower() in options:
                            done = True
                            return msg

                except asyncio.TimeoutError:
                    done = True
                    return await self.send(_("Timed out, cancelling..."))

        msg = await self.bot.wait_for('message', check=check, timeout=timeout)
        done = True
        return msg

    async def remove(self, *args, **kwargs):
        m = await self.send(*args, **kwargs)
        await m.add_reaction(self.emoji.xmark)
        try:
            await self.bot.wait_for('reaction_add', check=lambda r, u: u.id == self.author.id and r.message.id == m.id and str(r.emoji) == str(self.emoji.xmark))
            await m.delete()
        except asyncio.TimeoutError:
            pass

    async def send(self, content=None, edit=True, **kwargs):
        try:
            prev_msg = self.bot.cache.past_invokes[self.message.id]
            if prev_msg.attachments:
                edit = False
            elif prev_msg.embeds:
                e = prev_msg.embeds[0]
                if e.thumbnail:
                    if e.thumbnail.url.startswith("https://cdn.discordapp.com/attachments/"):
                        edit = False
                elif e.image:
                    if e.image.url.startswith("https://cdn.discordapp.com/attachments/"):
                        edit = False
        except KeyError:
            pass

        if edit and not kwargs.get('file', None) and self.message.id in self.bot.cache.past_invokes:
            try:
                await prev_msg.edit(content=content, embed=kwargs.pop('embed', None), **kwargs)
                return prev_msg

            except discord.NotFound:
                pass

        try:
            new_msg = await super().send(
                content=content,
                **kwargs
            )
        except discord.Forbidden:
            raise NoPerms("Sorry, but it looks like I do not have permissions to send messages there!")
        # except discord.HTTPException:
        #     raise SessionError(_("Something broke while trying to send a message, please try again later."))
        else:
            self.bot.cache.past_invokes[self.message.id] = new_msg
            return new_msg

    async def confirm(self, content=None, timeout=60, **kwargs):
        user = kwargs.pop("user", self.author)
        if content is None:
            message = self.message
        else:
            message = await self.send(content=content, **kwargs)

        await message.add_reaction("<:check:314349398811475968>")
        await message.add_reaction("<:xmark:314349398824058880>")

        def check(r, u):
            return r.message.id == message.id and u.id == user.id and str(r) in ("<:check:314349398811475968>", "<:xmark:314349398824058880>")

        try:
            r, u = await self.bot.wait_for('reaction_add', check=check, timeout=timeout)

            if str(r) == "<:check:314349398811475968>":
                return True, message

            elif str(r) == "<:xmark:314349398824058880>":
                return False, message

        except asyncio.TimeoutError:
            return False, message
