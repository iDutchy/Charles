import asyncio
import collections
import json
import os
import random
import re
import time
import typing
import zlib
from datetime import date, datetime
from functools import partial
from io import BytesIO, StringIO

import discord
import dropbox
import holidays
import numpy
import yaml
from aiogoogletrans import Translator
from core import i18n
from core.cog import SubCog
from core.commands import commandExtra, flagsExtra, groupExtra
from core.emojis import Emoji
from db import BaseUrls, tokens
from discord.ext import commands, flags
from geopy.geocoders import Nominatim
from utils.converters import executor
from utils.humanize_time import date as _date
from utils.humanize_time import date_time, timesince
from utils.paginator import EmbedPages
from youtube_dl import YoutubeDL
from utils import checks

translator = Translator()


def c(t, e):
    return f"{Emoji.arrow} **{t}:** {e}"


class SphinxObjectFileReader:
    # Inspired by Sphinx's InventoryFileReader
    BUFSIZE = 16 * 1024

    def __init__(self, buffer):
        self.stream = BytesIO(buffer)

    def readline(self):
        return self.stream.readline().decode('utf-8')

    def skipline(self):
        self.stream.readline()

    def read_compressed_chunks(self):
        decompressor = zlib.decompressobj()
        while True:
            chunk = self.stream.read(self.BUFSIZE)
            if len(chunk) == 0:
                break
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self):
        buf = b''
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b'\n')
            while pos != -1:
                yield buf[:pos].decode('utf-8')
                buf = buf[pos + 1:]
                pos = buf.find(b'\n')


def finder(text, collection, *, key=None, lazy=True):
    suggestions = []
    text = str(text)
    pat = '.*?'.join(map(re.escape, text))
    regex = re.compile(pat, flags=re.IGNORECASE)
    for item in collection:
        to_search = key(item) if key else item
        r = regex.search(to_search)
        if r:
            suggestions.append((len(r.group()), r.start(), item))

    def sort_key(tup):
        if key:
            return tup[0], tup[1], key(tup[2])
        return tup

    if lazy:
        return (z for _, _, z in sorted(suggestions, key=sort_key))
    else:
        return [z for _, _, z in sorted(suggestions, key=sort_key)]


class Util(SubCog, category="Utils"):
    def __init__(self, bot):
        self.bot = bot
        self.coliru_mapping = {
            'cpp': 'g++ -std=c++1z -O2 -Wall -Wextra -pedantic -pthread main.cpp -lstdc++fs && ./a.out',
            'c++': 'g++ -std=c++1z -O2 -Wall -Wextra -pedantic -pthread main.cpp -lstdc++fs && ./a.out',
            'c': 'mv main.cpp main.c && gcc -std=c11 -O2 -Wall -Wextra -pedantic main.c && ./a.out',
            'py': 'python3 main.cpp',
            'python': 'python3 main.cpp'
        }

    def parse_object_inv(self, stream, url):
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result = {}

        # first line is version info
        inv_version = stream.readline().rstrip()

        if inv_version != '# Sphinx inventory version 2':
            raise RuntimeError('Invalid objects.inv file version.')

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]  # noqa: F841

        # next line says if it's a zlib header
        line = stream.readline()
        if 'zlib' not in line:
            raise RuntimeError('Invalid objects.inv file, not z-lib compatible.')

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(r'(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)')
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, prio, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(':')
            if directive == 'py:module' and name in result:
                # From the Sphinx Repository:
                # due to a bug in 1.1 and below,
                # two inventory entries are created
                # for Python modules, and the first
                # one is correct
                continue

            # Most documentation pages have a label
            if directive == 'std:doc':
                subdirective = 'label'

            if location.endswith('$'):
                location = location[:-1] + name

            key = name if dispname == '-' else dispname
            prefix = f'{subdirective}:' if domain == 'std' else ''

            if projname == 'discord.py':
                key = key.replace('discord.ext.commands.', '').replace('discord.', '').replace('ext.menus.', '')

            result[f'{prefix}{key}'] = os.path.join(url, location)

        return result

    async def build_rtfm_lookup_table(self, page_types):
        cache = {}
        for key, page in page_types.items():
            cache[key] = {}
            async with self.bot.session.get(page + '/objects.inv') as resp:
                if resp.status != 200:
                    raise RuntimeError('Cannot build rtfm lookup table, try again later.')

                stream = SphinxObjectFileReader(await resp.read())
                cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx, obj):
        oobj = obj
        url = 'https://enhanced-dpy.readthedocs.io/en/latest'
        key = 'latest'
        page_types = {key: url}

        if obj is None:
            await ctx.send(url)
            return

        if not hasattr(self, '_rtfm_cache'):
            await ctx.trigger_typing()
            await self.build_rtfm_lookup_table(page_types)

        obj = re.sub(r'^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)', r'\1', obj)

        if key.startswith('latest'):
            # point the abc.Messageable types properly:
            q = obj.lower()
            for name in dir(discord.abc.Messageable):
                if name[0] == '_':
                    continue
                if q == name:
                    obj = f'abc.Messageable.{name}'
                    break

        cache = list(self._rtfm_cache[key].items())

        def transform(tup):
            return tup[0]

        matches = finder(obj, cache, key=lambda t: t[0], lazy=False)[:12]

        if len(matches) == 0:
            return await ctx.send(_('Could not find anything. Sorry.'))

        e = discord.Embed(colour=ctx.embed_color, title=f"RTFM Search: `{oobj}`")
        e.set_author(icon_url=ctx.guild.icon.url, name=f"Latest version: {discord.__version__} (click me to see changelog)",  url="https://enhanced-dpy.readthedocs.io/en/latest/whats_new.html")
        e.set_thumbnail(url="https://media.discordapp.net/attachments/460568954968997890/761037965987807232/dpycogs.png")
        e.description = '\n'.join(f'[`{key}`]({url})' for key, url in matches)
        e.set_footer(text=_("WARNING: This is NOT the documentation for the original discord.py lib! This is only for the enhanced version."))
        await ctx.send(embed=e)

    @executor
    def make_choices(self, times, options):
        all_options = numpy.random.choice(options, times)
        count = collections.Counter(all_options)
        return count

    @commandExtra(aliases=['cbo'])
    async def choosebestof(self, ctx, times: int, *options):
        times = times if times <= 1000000 else 1000000
        if len(options) < 2:
            return await ctx.send(_("You need to provide at least 2 options to choose from!"))
        async with ctx.loading(_("Making choices")):
            count = await self.make_choices(times, options)
        percentages = []
        for opt, tim in count.items():
            perc = 100 / times * tim
            percentages.append((opt, tim, perc))
        e = discord.Embed(color=ctx.cache.color)
        percentages = sorted(percentages, key=lambda x: x[1], reverse=True)
        e.description = "\n".join([f"`{x[2]:.2f}%` {x[0]} ({x[1]}x)"for x in percentages])
        await ctx.send(embed=e)

    @commandExtra()
    async def coliru(self, ctx, *, code):
        if not code.startswith("```") or not code.endswith("```"):
            return await ctx.send(_("The code must be wrapped in code blocks with a valid language identifier."))

        block, code = code.split("\n", 1)
        language = block[3:]

        if language not in self.coliru_mapping.keys():
            return await ctx.send(_("Supported languages for code blocks are `py`, `python`, `c`, `cpp`."))

        payload = {
            "src": code.rstrip("`").replace("```", ""),
            "cmd": self.coliru_mapping[language]
        }

        data = json.dumps(payload)

        response = await self.bot.session.post("http://coliru.stacked-crooked.com/compile", data=data)
        clean = await commands.clean_content(use_nicknames=False).convert(ctx, (await response.read()).decode('utf8'))

        try:
            await ctx.send(f"```\n{clean}```")
        except discord.HTTPException:
            url = await self.bot.utils.bin(clean)
            await ctx.send(url)

    @commandExtra()
    async def msgraw(self, ctx, msgid: int, chanid: int = None):
        try:
            msg = await self.bot.http.get_message(chanid or ctx.channel.id, msgid)
        except:
            if chanid:
                return await ctx.send(_("I could not find that message in that channel!"))
            return await ctx.send(_("I could not find that message in this channel!"))
        txt = json.dumps(msg, indent=2)
        pag = commands.Paginator()
        for line in txt.splitlines():
            pag.add_line(line)
        await self.bot.utils.paginate(ctx, entries=[p.strip('```') for p in pag.pages], prefix="```json\n", suffix="```")

    @commandExtra(aliases=['g'])
    async def google(self, ctx, *, search):
        SEARCH_ENGINE_ID = "008062882105305048247:n4hmfxyc0vk"
        API_KEY = "AIzaSyChWsc_WDCZEQkARwY1Cx1QFKme7AVq15c"
        async with self.bot.session.get(f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={SEARCH_ENGINE_ID}&q={search.replace(' ', '%20')}") as f:
            data = await f.json()

        search_items = data.get("items")
        searches = []
        for search_item in search_items:
            title = search_item.get("title")
            snippet = search_item.get("snippet")
            link = search_item.get("link")
            searches.append(f"**[{title}]({link})**\n\n{snippet}")
        await self.bot.utils.paginate(ctx,
            title=_("Google search for: {0}").format(search),
            entries=searches,
            author=ctx.author)

    @commandExtra()
    async def afk(self, ctx, *, reason=None):
        if ctx.author.id in self.bot.cache.afk:
            await asyncio.sleep(1)

        reason = reason or _("No reason")
        self.bot.cache.afk[ctx.author.id] = {"afk_set": datetime.utcnow(), "reason": reason}
        await self.bot.db.execute("INSERT INTO afk(user_id, reason) VALUES($1, $2)", ctx.author.id, reason)
        await ctx.send(_("{0}, I have set your AFK to `{1}`").format(ctx.author.mention, reason.replace("`", "\u200b`")))

    @commandExtra()
    async def redirectcheck(self, ctx, url):
        url = url.strip("<>")
        async with self.bot.session.get(f"https://api.redirect-checker.net/?url={url}&timeout=5&maxhops=10&meta-refresh=1&format=json") as f:
            try:
                d = await f.json()
            except:
                return await ctx.send(_("Invalid URL!"))

        if len(d['data']) == 1:
            return await ctx.send(_("No redirects found."))

        total = len(d['data']) - 1

        warning = ""
        if "grabify.link" in [d['data'][x]['request']['info']['idn']['host'] for x in range(len(d['data']))]:
            warning = f"\n\n{ctx.emoji.warn} **WARNING** {ctx.emoji.warn}\nDo NOT click this link! The person who created this used `grabify.link` to create an url that will grab your IP!"

        red_url = d['data'][total]['request']['info']['url']

        await ctx.send(f"A redirect for `{url}` has been found. A total of **{total}** redirects eventually lead to `{red_url}`{warning}")

    @commandExtra(name="holidays")
    async def list_holidays(self, ctx, country=None, year: int = None):
        countries = list(filter(lambda x: x.upper() != x, holidays.list_supported_countries()))
        if country is None:
            e = discord.Embed(color=ctx.embed_color)
            e.title = _("Available Countries")
            e.description = _("I can list you holidays for the following countries: `{0}`").format('`, `'.join(countries))
            e.set_footer(text=_("Country names are case-sensitive!"))
            return await ctx.send(embed=e)
        elif country not in holidays.list_supported_countries():
            e = discord.Embed(color=ctx.embed_color)
            e.title = _("Available Countries")
            e.description = _("Country not found!") + "\n" + _("I can list you holidays for the following countries: `{0}`").format('`, `'.join(countries))
            e.set_footer(text=_("Country names are case-sensitive!"))
            return await ctx.send(embed=e)
        else:
            upcoming = False
            if year is None:
                year = [date.today().year, date.today().year + 1]
                upcoming = True
                years = " & ".join(list(map(str, year)))
                title = _("Upcoming holidays for {0} in {1}")
            else:
                title = _("Holidays for {0} in {1}")
                years = year
            days = getattr(holidays, country)(years=year)
            days = sorted([(k, v) for k, v in days.items()], key=lambda x: x[0])
            entries = []
            added = set()
            for k, v in days:
                if k < date.today():
                    if upcoming:
                        continue
                    ago = (date.today() - k).days
                    entries.append(f"`{_date(k)}` - {v} ({ago} days ago)")
                elif k == date.today():
                    entries.append(f"> **`{_date(k)}` - {v} (today :tada:)**")
                    added.add(v)
                else:
                    if v in added:
                        continue
                    in_ = (k - date.today()).days
                    entries.append(f"`{_date(k)}` - {v} (in {in_} days)")
            await self.bot.utils.paginate(ctx, title=title.format(country, years), entries=entries, per_page=10)

    @commandExtra(category="Utility")
    async def bigemoji(self, ctx, emoji: typing.Union[discord.Emoji, discord.PartialEmoji, str]):
        if isinstance(emoji, (discord.Emoji, discord.PartialEmoji)):
            url = str(emoji.url)
        else:
            try:
                url = f"http://twemoji.maxcdn.com/v/latest/72x72/{format(ord(emoji), 'x')}.png"
            except:
                return await ctx.send(_("That was either not a valid emoji or not an emoji at all..."))

        await ctx.send(url)

    @commandExtra(category="Utility", name="id")
    async def get_id(self, ctx, *, anything: typing.Union[discord.Member, discord.User, discord.Emoji, discord.PartialEmoji, discord.TextChannel, discord.VoiceChannel, discord.Role, discord.CategoryChannel, discord.Message, str] = None):
        if isinstance(anything, str):
            return await ctx.send(_("I could not find an ID for **{0}**... Remember that you can only get the ID for users, roles, emojis (not default emojis), channels and messages!").format(anything))
        anything = anything or ctx.author
        await ctx.send(anything.id)

    @commandExtra(category="Utility")
    async def npm(self, ctx, query):
        d = await ctx.get(f"http://api.npmjs.org/search?text={query}&size=6")

        # d = json.loads(dt)
        if d["total"] == 0:
            return await ctx.send(_("Nothing found for: `{0}`!").format(query))

        match = False
        check = [x for x in d['objects'] if x['package']['name'].lower() == query.lower()]
        if check:
            match = check[0]
            d["objects"].remove(match)

        e = discord.Embed(title=_("NPM Search: `{0}`").format(query), color=ctx.embed_color)
        e.set_thumbnail(url="https://media.discordapp.net/attachments/460568954968997890/776279593807773716/unknown.png")
        if match:
            upd = match["package"]["date"]
            if not upd[-1].isdigit():
                upd = upd[:-1]

            tr_urls = {
                "npm": _("NPM"),
                "homepage": _("Home"),
                "repository": _("Repo"),
                "bugs": _("Bugs")
            }

            desc = []
            desc.append(c(_("Name"), match["package"]["name"]))
            desc.append(c(_("Version"), match["package"]["version"]))
            desc.append(c(_("Last Updated"), date_time(datetime.fromisoformat(upd))))
            desc.append(c(_("Description"), match["package"]["description"]))
            desc.append(c(_("Tags"), ", ".join(f"`{x}`" for x in match["package"].get("keywords", ["-"]))))
            desc.append(c(_("Links"), " | ".join(f"[{tr_urls[k]}]({v})" for k, v in match['package']['links'].items())))
            e.description = "\n".join(desc)
            if d["objects"]:
                e.add_field(name=_("Close Matches:"), value="\n".join(f"[{x['package']['name']} {x['package']['version']}]({x['package']['links']['npm']})" for x in d['objects']), inline=False)
        else:
            e.description = _("**No exact match found with your search, but here are some close matches:**") + "\n\n" + "\n".join(f"[{x['package']['name']} {x['package']['version']}]({x['package']['links']['npm']})" for x in d['objects'])

        e.set_footer(text=_("Total results found: {0}").format(d['total']))

        await ctx.send(embed=e)

    @commandExtra(aliases=['rtfd'], category="Utility")
    async def rtfm(self, ctx, *, obj: str = None):
        await self.do_rtfm(ctx, obj)

    @commandExtra(category="Utility", aliases=['ip', 'lookup', 'iplookup'])
    async def ipcheck(self, ctx, ip):
        res = await ctx.get(BaseUrls.ipcheck.format(ip))

        await ctx.send(f"```json\n{json.dumps(res, indent=2)}```")

    @commandExtra(category="Utility")
    async def location(self, ctx, *, locate: commands.clean_content):
        try:
            geolocator = Nominatim(user_agent="Charles")
            location = geolocator.geocode(locate)
            adress = location.address
            lat = (location.latitude, location.longitude)
        except:
            return await ctx.send(_("No location found for search: {0}").format(locate))

        await ctx.send(f"{adress}\n\n{lat}")

    @commandExtra(category="Utility")
    async def pypi(self, ctx, package):
        d = await ctx.get(f'https://pypi.org/pypi/{package}/json/')
        if not d:
            return await ctx.send(_("Could not find package `{0}` on Pypi...").format(package))

        e = discord.Embed(color=ctx.embed_color)
        e.description = d['info']['summary']
        e.title = d['info']['name'] + ' ' + d['info']['version']
        e.url = d['info']['package_url']

        none = _("None provided...")

        a_info, p_info = [], []
        a_info.append(_("**Author Name:** {0}").format(d['info']['author']))
        a_info.append(_("**Author Email:** {0}").format(d['info']['author_email'] or none))

        p_info.append(_("**Download URL:** {0}").format(d['info']['download_url'] or none))
        if d['info']['project_urls']:
            p_info.append(_("**Documentation URL:** {0}").format(d['info']['project_urls'].get('Documentation', none)))
        p_info.append(_("**Home Page:** {0}").format(d['info']['home_page'] or none))
        p_info.append(_("**Keywords:** {0}").format(d['info']['keywords'] or none))
        p_info.append(_("**License:** {0}").format(d['info']['license'] or none))

        e.add_field(name=_("**Author Info**"), value='\n'.join(a_info), inline=False)
        e.add_field(name=_("**Package Info:**"), value='\n'.join(p_info), inline=False)
        e.set_thumbnail(url="https://images-ext-1.discordapp.net/external/Ko5_nvJz886Ep3Yd-Dn234gRBpnEZyvoyCQNxDX1OZ0/https/cdn-images-1.medium.com/max/1200/1%2A2FrV8q6rPdz6w2ShV6y7bw.png")

        await ctx.send(embed=e)

    @groupExtra(name="error", category="Utility", invoke_without_command=True)
    async def error_tracker(self, ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @error_tracker.command()
    async def track(self, ctx, error_id: int):
        check = await self.bot.db.fetchrow("SELECT * FROM error_tracking WHERE user_id = $1 AND error_id = $2", ctx.author.id, error_id)
        if check:
            return await ctx.send(_("You are already tracking this error!"))

        check2 = await self.bot.db.fetchrow("SELECT * FROM errors WHERE id = $1", error_id)
        if not check2:
            return await ctx.send(_("There is no error known with that ID!"))

        await self.bot.db.execute("INSERT INTO error_tracking VALUES($1, $2)", ctx.author.id, error_id)
        await ctx.send(_("You are now tracking error **#{0}**!").format(error_id))

    @error_tracker.command()
    async def untrack(self, ctx, error_id: int):
        check = await self.bot.db.fetchrow("SELECT * FROM error_tracking WHERE user_id = $1 AND error_id = $2", ctx.author.id, error_id)
        if not check:
            return await ctx.send(_("You are not tracking this error!"))

        check2 = await self.bot.db.fetchrow("SELECT * FROM errors WHERE id = $1", error_id)
        if not check2:
            return await ctx.send(_("There is no error known with that ID!"))

        await self.bot.db.execute("DELETE FROM error_tracking WHERE user_id = $1 AND error_id = $2", ctx.author.id, error_id)
        await ctx.send(_("You are no longer tracking error **#{0}**!").format(error_id))

    @commands.max_concurrency(number=1, per=commands.BucketType.user, wait=False)
    @commandExtra(name="mp3", category="Utility")
    async def music_download(self, ctx, *, query):
        # if not ctx.player.is_connected: # TODO
        #     return await ctx.send("I need to be connected to a channel to do this")
        msg = await ctx.send(_("{0} Downloading your mp3 file!\n*This may take a while...*").format("<a:discord_loading:587812494089912340> |"))
        ydl_opts = {
                'outtmpl': '{}.%(ext)s'.format(ctx.author.id),
                'format': 'bestaudio',
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320'}
                ]
            }

        tracks = await ctx.player.node.get_tracks(f"ytsearch:{query}")
        if not tracks:
            return await msg.edit(content=_("No tracks have been found with that query. Please try again later."))
        track = tracks[0]
        length = int(track.length/1000/60)
        if length > 5:
            return await ctx.send(_("This song exceeds the length limit of 5 minutes!"))

        ytdl = YoutubeDL(ydl_opts)
        to_run = partial(ytdl.extract_info, url=track.uri, download=False)

        data = await self.bot.loop.run_in_executor(None, to_run)

        if data:
            song_title = track.title
        else:
            return discord.Embed(color=ctx.embed_color, description=_("I was unable to download this song... Most likely something messed up with my connection to YouTube."))

        mp3_file = await ctx.get(data['url'], timeout=None, return_type="read")

        if len(mp3_file) > ctx.guild.filesize_limit:
            d = dropbox.Dropbox(tokens.DROPBOX)
            d.files_upload(mp3_file, f"/mp3_files/{song_title}.mp3", mode=dropbox.files.WriteMode("overwrite"))
            link = d.sharing_create_shared_link(f"/mp3_files/{song_title}.mp3")
            dl_url = re.sub(r"\?dl\=0", "?dl=1", link.url)
            await msg.delete()
            return await ctx.send(_("{0}, your mp3 download has completed!\nThe file size exceeded the limit for this server, so you can find the file here:\n{1}").format(ctx.author.mention, dl_url))

        buf = BytesIO(mp3_file)

        file = discord.File(buf, filename=f"{song_title}.mp3")

        await msg.delete()
        await ctx.send(_("{0}, your mp3 download has completed!").format(ctx.author.mention), file=file)

    @commandExtra(category="Utility")
    async def lyrics(self, ctx, *, lyr: str):
        dat = await ctx.get(f'https://some-random-api.ml/lyrics?title={lyr.replace(" ", "+")}')

        if not dat:
            return await ctx.send(_("I could not find any lyrics for that song..."))
        lyrics = dat.get('lyrics')
        if not lyrics:
            return await ctx.send(_("I could not find any lyrics for that song..."))
        lyrics = lyrics.split(' ')
        lyric_pages = [' '.join(lyrics[i:i+150]) for i in range(0, len(lyrics), 150)]

        paginator = EmbedPages(ctx,
                          title=_("Lyrics for: {0}").format(lyr),
                          entries=lyric_pages,
                          timeout=None,
                          show_page_num=True)
        return await paginator.start()

    @flags.add_flag('text', nargs='+')
    @flags.add_flag('--delafter', type=int, default=None)
    @flags.add_flag('--channel', type=discord.TextChannel)
    @flags.add_flag('--mentions', action='store_true', default=False)
    @flags.add_flag('--edit', action='store_true', default=False)
    @checks.has_permissions(manage_messages=True)
    @flagsExtra(category="Utility", aliases=['say'])
    async def send(self, ctx, **flags):
        channel = flags['channel'] or ctx.channel
        delafter = flags['delafter']
        text = ' '.join(flags['text'])
        if not flags['mentions'] or not ctx.author.guild_permissions.mention_everyone:
            text = await commands.clean_content().convert(ctx, text)
        
        if flags['edit']:
            if not ctx.message.reference:
                return await ctx.send("To edit a message, please reply to the message you want to edit while using this command!")
            try:
                await ctx.message.reference.resolved.edit(content=text)
            except Exception as e:
                return await ctx.send(f"ERROR: {e}")
        else:
            await channel.send(text, delete_after=delafter)
        try:
            await ctx.message.delete()
        except:
            pass

    @commandExtra(category="Utility")
    async def embed(self, ctx, *, embed_msg):
        try:
            d = json.loads(embed_msg)
        except json.decoder.JSONDecodeError:
            return await ctx.send(_("I could not load that to an embed. Are you sure you copied everything?"))
        try:
            e = discord.Embed.from_dict(d)
            await ctx.send(embed=e)
        except discord.HTTPException:
            return await ctx.send(_("Something went wrong while loading that embed... Please check if everything is correct (like image urls)!"))

    @groupExtra(category="Utility")
    async def todo(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.list)

    @todo.command()
    async def add(self, ctx, *, todo: commands.clean_content):
        current = await self.bot.db.fetchval("SELECT current FROM todo_settings WHERE user_id = $1", ctx.author.id)
        if not current:
            current = await self.bot.db.fetchval("INSERT INTO todo_settings(user_id) VALUES($1) RETURNING current", ctx.author.id)
        todos = await self.bot.db.fetch("SELECT * FROM todos WHERE user_id = $1 AND list = $2", ctx.author.id, current)
        _todos = [t['todo'].lower() for t in todos]
        if todo.lower() in _todos:
            txt = _("`{0}` is already on your todo list!")
            if (len(txt) + len(todo)) > 2000:
                todo = todo[:1997-len(txt)] + "..."
            return await ctx.send(txt.format(todo))
        await self.bot.db.execute("INSERT INTO todos(user_id, todo, jump_url, list) VALUES($1, $2, $3, $4)", ctx.author.id, todo, ctx.message.jump_url, current)
        txt = _("Added to your todo list `{0}`:\n\t**[#{1}]** - {2}")
        to_send = txt.format(current, len(todos)+1, todo)
        if len(to_send) > 2000:
            to_send = to_send[:1997] + "..."
        await ctx.send(to_send)

    @todo.command(aliases=['rm'])
    async def remove(self, ctx, *todo: int):
        current = await self.bot.db.fetchval("SELECT current FROM todo_settings WHERE user_id = $1", ctx.author.id)
        todos = await self.bot.db.fetch("SELECT DISTINCT todo, sort_date, ROW_NUMBER () OVER (ORDER BY sort_date) FROM todos WHERE user_id = $1 AND list = $2 ORDER BY sort_date", ctx.author.id, current)
        if not todos:
            return await ctx.send(_("Your todo list is empty..."))
        no_todo = []
        for t in todo:
            if t not in [x['row_number'] for x in todos]:
                no_todo.append(t)
        if no_todo:
            return await ctx.send(_("A todo with ID `{0}` is not in your todo list!").format(str(no_todo[0])))
        todo_r = []
        for x in todo:
            todo_r.append((ctx.author.id, todos[x-1]['todo'], current))
        await self.bot.db.executemany("DELETE FROM todos WHERE user_id = $1 AND todo = $2 AND list = $3", todo_r)

        await ctx.send(_("Removed from your todo list `{0}`:\n\t- {1}").format(current, '\n\t- '.join([(todos[x-1]['todo'] if len(todos[x-1]['todo']) <= 100 else todos[x-1]['todo'][:97]+'...') for x in todo])))

    @todo.command()
    async def edit(self, ctx, pos: int, *, todo: commands.clean_content):
        current = await self.bot.db.fetchval("SELECT current FROM todo_settings WHERE user_id = $1", ctx.author.id)
        todos = await self.bot.db.fetch("SELECT DISTINCT todo, sort_date, ROW_NUMBER () OVER (ORDER BY sort_date) FROM todos WHERE user_id = $1 AND list = $2 ORDER BY sort_date", ctx.author.id, current)
        if not todos:
            return await ctx.send(_("Your todo list is empty..."))
        if pos not in [t['row_number'] for t in todos]:
            return await ctx.send(_("A todo with ID {0} is not in your todo list!").format(str(pos)))

        await self.bot.db.execute("UPDATE todos SET todo = $1 WHERE user_id = $2 AND sort_date = $3 AND list = $4", todo, ctx.author.id, todos[pos-1]['sort_date'], current)
        await ctx.send(_("Todo with position `{0}` succesfully edited to: **{1}**").format(str(pos), todo))

    @todo.command()
    async def list(self, ctx):
        current = await self.bot.db.fetchval("SELECT current FROM todo_settings WHERE user_id = $1", ctx.author.id)
        todos = await self.bot.db.fetch("SELECT DISTINCT todo, sort_date, ROW_NUMBER () OVER (ORDER BY sort_date) FROM todos WHERE user_id = $1 AND list = $2 ORDER BY sort_date", ctx.author.id, current)
        if not todos:
            return await ctx.send(_("Your todo list is empty..."))

        paginator = EmbedPages(ctx,
                          title=_("Todo list {}:").format(current),
                          entries=[f"`[{t['row_number']}]` {t['todo'] if len(t['todo']) <= 100 else t['todo'][:97]+'...'}" for t in todos],
                          per_page=10,
                          show_entry_count=True,
                          show_page_num=True,
                          timeout=None)
        return await paginator.start()

    @todo.command()
    async def swap(self, ctx, todo1: int, todo2: int):
        current = await self.bot.db.fetchval("SELECT current FROM todo_settings WHERE user_id = $1", ctx.author.id)
        todos = await self.bot.db.fetch("SELECT DISTINCT todo, sort_date, ROW_NUMBER () OVER (ORDER BY sort_date) FROM todos WHERE user_id = $1 AND list = $2 ORDER BY sort_date", ctx.author.id, current)
        if not todos:
            return await ctx.send(_("Your todo list is empty..."))
        if todo1 not in [t['row_number'] for t in todos]:
            return await ctx.send(_("A todo with ID {0} is not in your todo list!").format(str(todo1)))
        if todo2 not in [t['row_number'] for t in todos]:
            return await ctx.send(_("A todo with ID {0} is not in your todo list!").format(str(todo2)))
        if todo1 == todo2:
            return await ctx.send(_("I can not swap a todo with a position it already has..."))

        await self.bot.db.execute("UPDATE todos SET sort_date = $1 WHERE todo = $2 AND sort_date = $3 AND user_id = $4 AND list = $5", todos[todo2-1]['sort_date'], todos[todo1-1]['todo'], todos[todo1-1]['sort_date'], ctx.author.id, current)
        await self.bot.db.execute("UPDATE todos SET sort_date = $1 WHERE todo = $2 AND sort_date = $3 AND user_id = $4 AND list = $5", todos[todo1-1]['sort_date'], todos[todo2-1]['todo'], todos[todo2-1]['sort_date'], ctx.author.id, current)

        await ctx.send(_("Succesfully swapped places of todo #{0} and #{1}").format(str(todo1), str(todo2)))

    @todo.command()
    async def clear(self, ctx):
        current = await self.bot.db.fetchval("SELECT current FROM todo_settings WHERE user_id = $1", ctx.author.id)
        todos = await self.bot.db.fetch("SELECT * FROM todos WHERE user_id = $1 AND list = $2", ctx.author.id, current)
        if not todos:
            return await ctx.send(_("Your todo list is already empty..."))

        check, msg = await ctx.confirm(_("Are you sure you want to clear your todo list `{0}`?").format(current))

        await msg.delete()

        if check:
            await self.bot.db.execute("DELETE FROM todos WHERE user_id = $1 AND list = $2", ctx.author.id, current)
            return await ctx.send(_("Cleared all items from your todo list!"), edit=False)

        else:
            return await ctx.send(_("Okay, cancelled."), edit=False)

    @todo.command()
    async def info(self, ctx, pos: int):
        current = await self.bot.db.fetchval("SELECT current FROM todo_settings WHERE user_id = $1", ctx.author.id)
        todos = await self.bot.db.fetch("SELECT DISTINCT todo, sort_date, insert_date, jump_url, ROW_NUMBER () OVER (ORDER BY sort_date) FROM todos WHERE user_id = $1 AND list = $2 ORDER BY sort_date", ctx.author.id, current)
        if not todos:
            return await ctx.send(_("Your todo list is empty..."))
        if pos not in [t['row_number'] for t in todos]:
            return await ctx.send(_("A todo with ID {0} is not in your todo list!").format(str(pos)))

        e = discord.Embed(title=_("Todo Info | Todo #{0} | List `{1}`").format(pos, current),
                          color=ctx.embed_color,
                          description=todos[pos-1]['todo'])
        info = []
        if time := todos[pos-1]['insert_date']:
            e.timestamp = time
            info.append(_("This todo has been on your todo list for: `{0}`").format(timesince(time, False)))
            e.set_footer(text=_("-- Todo Created:"))
        else:
            time = todos[pos-1]['sort_date']
            e.timestamp = time
            e.set_footer(text=_("-- Todo Created:"))
            info.append(_("Time may not be accurate due to todo sorting and this being an old todo"))
            info.append(_("This todo has been on your todo list for: `{0}`").format(timesince(time, False)))
        if jump := todos[pos-1]['jump_url']:
            info.append(_("[Jump to todo creation moment]({0})").format(jump))
        if info:
            e.add_field(name=_("Extra Info"), value="\n".join(info))

        await ctx.send(embed=e)

    @todo.command()
    async def raw(self, ctx, pos: int):
        current = await self.bot.db.fetchval("SELECT current FROM todo_settings WHERE user_id = $1", ctx.author.id)
        todos = await self.bot.db.fetch("SELECT DISTINCT todo, sort_date, insert_date, jump_url, ROW_NUMBER () OVER (ORDER BY sort_date) FROM todos WHERE user_id = $1 AND list = $2 ORDER BY sort_date", ctx.author.id, current)
        if not todos:
            return await ctx.send(_("Your todo list is empty..."))
        if pos not in [t['row_number'] for t in todos]:
            return await ctx.send(_("A todo with ID {0} is not in your todo list!").format(str(pos)))

        raw_data = discord.utils.escape_markdown(todos[pos-1]['todo'])
        await ctx.send(raw_data)

    @todo.command()
    async def lists(self, ctx):
        lists = await self.bot.db.fetch("SELECT list_name, current FROM todo_settings WHERE user_id = $1", ctx.author.id)
        todos = {x['list']: x['total'] for x in await self.bot.db.fetch("SELECT list, COUNT(todo) AS total FROM todos WHERE user_id = $1 GROUP BY list", ctx.author.id)}
        if not lists:
            return await ctx.send(_("You dont have any todo lists."))

        e = discord.Embed(title=_("Your todo lists:"),
                          description="\n".join([f"- {x['list_name']} {'({} todos)'.format(todos.get(x['list_name'], 0)) if todos.get(x['list_name'], 0) != 1 else '({} todo)'.format(todos.get(x['list_name'], 0))} {'**Current**' if x['list_name'] == x['current'] else ''}" for x in lists]),
                          color=ctx.embed_color)
        await ctx.send(embed=e)

    @todo.command()
    async def switch(self, ctx, to_list):
        current = await self.bot.db.fetchval("SELECT current FROM todo_settings WHERE user_id = $1", ctx.author.id)
        lists = [i for i, in await self.bot.db.fetch("SELECT list_name FROM todo_settings WHERE user_id = $1", ctx.author.id)]
        if to_list == current:
            return await ctx.send(_("You're already using that list now!"))
        if to_list not in lists:
            return await ctx.send(_("You dont have a todo list by that name!"))
        await self.bot.db.execute("UPDATE todo_settings SET current = $2 WHERE user_id = $1", ctx.author.id, to_list)
        await ctx.send(_("Succesfully switched to todo list {0}!").format(to_list))

    @todo.command()
    async def create(self, ctx, name: commands.clean_content):
        lists = [i for i, in await self.bot.db.fetch("SELECT list_name FROM todo_settings WHERE user_id = $1", ctx.author.id)]
        if len(lists) == 20:
            return await ctx.send(_("Sorry, but you've reached the limit of 20 todo lists..."))
        if name in lists:
            return await ctx.send(_("You already have a todo list with that name!"))
        current = await self.bot.db.fetchval("SELECT current FROM todo_settings WHERE user_id = $1", ctx.author.id)
        await self.bot.db.execute("INSERT INTO todo_settings(user_id, list_name, current) VALUES($1,$2,$3)", ctx.author.id, name, current)
        await ctx.send(_("A todo list with name '{0}' has succesfully been created!").format(name))

    @todo.command()
    async def delete(self, ctx, name: commands.clean_content):
        lists = [i for i, in await self.bot.db.fetch("SELECT list_name FROM todo_settings WHERE user_id = $1", ctx.author.id)]
        if len(lists) == 1:
            return await ctx.send(_("Sorry, but you need at least 1 todo list active and this is your only list..."))
        if name not in lists:
            return await ctx.send(_("You dont have a todo list with that name!"))

        check, msg = await ctx.confirm(_("Are you sure you want to delete this todo list?"))
        await msg.delete()

        if check:
            idk = await self.bot.db.fetch("SELECT current, list_name FROM todo_settings WHERE user_id = $1", ctx.author.id)
            current = idk[0]['current']
            await self.bot.db.execute("DELETE FROM todo_settings WHERE user_id = $1 AND list_name = $2", ctx.author.id, name)
            if current == name:
                others = [x['list_name'] for x in idk]
                others.remove(current)
                newcurrent = random.choice(others)
                await self.bot.db.execute("UPDATE todo_settings SET current = $1 WHERE user_id = $2", newcurrent, ctx.author.id)
            await ctx.send(_("Todo list with name '{0}' has succesfully been deleted!").format(name), edit=False)
        else:
            await ctx.send(_("Okay, cancelled."))

    @todo.command(name='export')
    async def todo_export(self, ctx, todolist=None):
        buf = StringIO()
        data = {}
        if todolist is None:
            todos = await self.bot.db.fetch("SELECT DISTINCT list, todo, sort_date, ROW_NUMBER () OVER (ORDER BY sort_date) FROM todos WHERE user_id = $1 ORDER BY sort_date", ctx.author.id)
            for todo in todos:
                if f"List: {todo['list']}" not in data:
                    data[f"List: {todo['list']}"] = []
                data[f"List: {todo['list']}"].append({todo['row_number']: {'Added on': todo['sort_date'].strftime("%B %d, %Y at %H:%M %p"), "Todo": todo['todo']}})
        else:
            todos = await self.bot.db.fetch("SELECT DISTINCT list, todo, sort_date, ROW_NUMBER () OVER (ORDER BY sort_date) FROM todos WHERE user_id = $1 AND list = $2 ORDER BY sort_date", ctx.author.id, todolist)
            if not todos:
                return await ctx.send(_("No todo list was found with that name!"))
            for todo in todos:
                if f"List: {todo['list']}" not in data:
                    data[f"List: {todo['list']}"] = []
                data[f"List: {todo['list']}"].append({todo['row_number']: {'Added on': todo['sort_date'].strftime("%B %d, %Y at %H:%M %p"), "Todo": todo['todo']}})

        yaml.dump(data, buf, indent=4)
        buf.seek(0)
        file = discord.File(buf, 'todos.yml')
        await ctx.send(file=file)

    # @todo.command(name='transfer')
    # async def todo_transfer(self, ctx, todo_id: int, to_list: str):
    #     current = await self.bot.db.fetchval("SELECT current FROM todo_settings WHERE user_id = $1", ctx.author.id)
    #     to_list_check = await self.bot.db.fetchval("SELECT * FROM todo_settings WHERE user_id = $1 AND list_name = $2", ctx.author.id, to_list)
    #     if not to_list_check:
    #         return await ctx.send(_("No list found with that name... Remember, list names are case-sensitive!"))
    #     to_count = await self.bot.db.fetchval("SELECT COUNT(*) FROM todos WHERE user_id = $1 AND list = $2", ctx.author.id, to_list)
    #     todos = await self.bot.db.fetch("SELECT DISTINCT todo, sort_date, ROW_NUMBER () OVER (ORDER BY sort_date) FROM todos WHERE user_id = $1 AND list = $2 ORDER BY sort_date", ctx.author.id, current)
    #     if not todos:
    #         return await ctx.send(_("Your todo list is empty..."))
    #     if todo_id > len(todos):
    #         return await ctx.send(_("You don't have a todo with that ID in your current list!"))

    #     todo = todos[todo_id-1]['todo']
    #     await self.bot.db.execute("UPDATE todos SET list = $2 WHERE user_id = $1 AND todo = $3", ctx.author.id, to_list, todo)
    #     to_send = _("Succesfully transfered from list `{0}` to list `{1}`:\n\t**[#{2} `>` #{3}]** - {4}").format(current, to_list, todo_id, to_count+1, todo)
    #     if len(to_send) > 2000:
    #         to_send = to_send[:1997] + "..."
    #     await ctx.send(to_send)

    @commandExtra(category="Utility")
    async def voteremind(self, ctx):
        if str(ctx.author.id) in self.bot.cache.votereminders.keys():
            await self.bot.db.execute("DELETE FROM votereminders WHERE user_id = $1", ctx.author.id)
            self.bot.cache.votereminders.pop(str(ctx.author.id))
            return await ctx.send(_("Ok, I will no longer send you vote reminders!"))

        await self.bot.db.execute("INSERT INTO votereminders VALUES ($1, $2, $3)", ctx.author.id, True, int(time.time()))
        self.bot.cache.votereminders[str(ctx.author.id)] = {'time': int(time.time()), 'reminded': True}

        await ctx.send(_("I will now DM you vote reminders! Be sure to have DMs from me enabled :)\n\n*Vote reminders will start the next time you vote!*"))

    @commandExtra(category="Utility", aliases=['shorten'])
    async def tinyurl(self, ctx, *, link: str):
        url = link.strip("<>")
        if not re.fullmatch(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", url):
            return await ctx.send(_("I could not shorten that because it is not a valid url!"))
        geturl = BaseUrls.tinyurl + url
        new = (await ctx.get(geturl, return_type="read")).decode('utf8')
        if len(new) >= len(url):
            return await ctx.send(_("Sorry, I cant make that url any shorter than it already is..."))
        emb = discord.Embed(color=ctx.embed_color)
        emb.add_field(name=_("Original Link"), value=link, inline=False)
        emb.add_field(name=_("Shortened Link"), value=new, inline=False)
        emb.set_footer(text=_("Powered by tinyurl.com"),icon_url='https://blog.dzhuneyt.com/wp-content/uploads/2011/11/tinyurl.png')
        await ctx.send(embed=emb)
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            pass

    @commandExtra(category="Utility")
    @commands.is_nsfw()
    @commands.cooldown(rate=1, per=2.0, type=commands.BucketType.user)
    async def urban(self, ctx, *, search: str):
        url = await ctx.get(BaseUrls.ud + search.replace(' ', '+'))

        if not url['list']:
            return await ctx.send(_("I searched the whole urban dictionary, but I could not find anything for your search: \"{0}\"...").format(search))

        results = url['list']
        t = []
        d = []

        for r in results:
            definition = r['definition']
            if len(definition) > 1000:
                definition = definition[:997].strip()+"..."
            example = r['example']

            lang_code = self.bot.cache.get("settings", ctx.guild.id, "language").lower()
            try:
                definition = await self.bot.utils.translate(definition, dest=lang_code)
                example = await self.bot.utils.translate(example, dest=lang_code)
            except:
                pass
            desc = _("**URL:** [click here]({0})").format(r['permalink']) + "\n"
            desc += _("**By:** {0}").format(r['author']) + "\n\n"
            desc += _("**Definition:** {0}").format(definition) + "\n\n"
            if len(example) > 500:
                example = example[:497]+"..."
            desc += _("**Example:** {0}").format(example)
            d.append(desc)
            t.append(r['word'])

        paginator = EmbedPages(ctx,
            entries=d,
            title=t,
            show_page_num=True)

        await paginator.start()

    @commandExtra(category="Utility")
    async def bin(self, ctx, *, code):
        url = await self.bot.utils.bin(code)
        embed = discord.Embed(color=ctx.embed_color, title=_("CharlesBin Upload"), description=url)
        embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/562784997962940476/611010770603343872/twitter_400x400.png", text=_("Powered by CharlesBin"))
        await ctx.send(embed=embed)

    @commandExtra(category="Utility", aliases=['translate'])
    async def tr(self, ctx, *, translate: commands.clean_content):
        word_list = translate.split(" ")

        if len(word_list) < 2:
            return await ctx.send(embed=discord.Embed(title=_("Something went wrong..."), description=_("I couldn't find that language!"), color=ctx.embed_color))

        lang = word_list[len(word_list)-1]
        from_lang = word_list[len(word_list)-2] if len(word_list) >= 3 else "auto"

        # Get the from language
        from_lang_back = [x for x in self.languages if x["code"].lower() == from_lang.lower()]
        from_lang_code = from_lang_back[0]["code"] if len(from_lang_back) else "auto"
        from_lang_name = from_lang_back[0]["name"] if len(from_lang_back) else _("Auto Detected")
        # Get the to language
        lang_back = [x for x in self.languages if x["code"].lower() == lang.lower()]
        lang_code = lang_back[0]["code"] if len(lang_back) else "en"
        lang_name = lang_back[0]["name"] if len(lang_back) else "English"

        # Translate all but our language codes
        if len(word_list) > 2 and word_list[len(word_list)-2].lower() == from_lang_code.lower():
            trans = " ".join(word_list[:-2])
        else:
            trans = " ".join(word_list[:-1])

        if not lang_code:
            return await ctx.send(embed=discord.Embed(title=_("Something went wrong..."), description=_("I couldn't find that language!"), color=ctx.embed_color))

        try:
            result = await self.bot.utils.translate(trans, lang_code, from_lang_code)
        except:
            return await ctx.send(_("Network is unreachable, please try again later!"))

        if not result:
            return await ctx.send(embed=discord.Embed(title=_("Something went wrong..."), description=_("I wasn't able to translate that!"), color=ctx.embed_color))

        if result == trans:
            return await ctx.send(embed=discord.Embed(title=_("Something went wrong..."), description=_("The text returned from Google was the same as the text put in.  Either the translation failed - or you were translating from/to the same language (en -> en)"), color=ctx.embed_color))

        embed = discord.Embed(color=ctx.embed_color, title=f"{from_lang_name} --> {lang_name}", description=result)
        embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/562784997962940476/611346692549378068/gtr.png", text=_("Powered by Google Translate"))

        await ctx.send(embed=embed)


def setup(bot):
    pass
