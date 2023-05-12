import re
from typing import Optional

import diorite
import discord
from core import i18n
from core.cog import SubCog
from core.commands import groupExtra
from discord.ext import commands
from utils.paginator import EmbedPages

from .player import Track

RURL = re.compile(r'https?:\/\/(?:www\.)?.+')


class Playlists(SubCog, category="Playlists"):
    def __init__(self, bot):
        self.bot = bot

    @groupExtra(aliases=['playlists', 'pl'], category="Playlists", invoke_without_command=True)
    async def playlist(self, ctx, *, user: Optional[discord.User] = None):
        if ctx.invoked_subcommand is None:
            if user is None:
                user = ctx.author

            db_check = await self.bot.db.fetchval("SELECT user_id FROM playlists WHERE user_id = $1", user.id)
            if db_check is None:
                if user != ctx.author:
                    return await ctx.send(_("This user does not have any playlists!"))
                return await ctx.send(_("You do not have any playlists created yet. Please use the `playlist create` command to make one!"))

            desc = ""
            playlists = set([n for n, in await self.bot.db.fetch("SELECT upper(name) FROM playlists WHERE user_id = $1", user.id)])
            for playlist in playlists:
                if playlist is None:
                    continue
                song_count = await self.bot.db.fetchval("SELECT COUNT(track_id) FROM playlists WHERE user_id = $1 AND upper(name) = $2", user.id, playlist.upper())
                s = _("song")
                ss = _("songs")
                desc += f"`-` {playlist.title()} ({song_count} {s if song_count == 1 else ss})\n"

            embed = discord.Embed(color=ctx.embed_color, title=_("Playlists"))
            embed.set_author(icon_url=user.avatar.url, name=str(user))
            embed.description = desc

            await ctx.send(embed=embed)

    @playlist.command()
    async def create(self, ctx, *, name: commands.clean_content):
        if len(name) > 100:
            return await ctx.send(_("Playlist names can't be longer than 100 characters!"))
        playlists = [n.upper() for n, in await self.bot.db.fetch("SELECT name FROM playlists WHERE user_id = $1", ctx.author.id)]
        if name.upper() in playlists:
            return await ctx.send(_("A playlist with that name already exists."))

        if len(playlists) == 10:
            return await ctx.send(_("You have reached the limit of 10 playlists."))

        # Always need a "dummy (None)" in case of empty playlists
        await self.bot.db.execute("INSERT INTO playlists(user_id, name, track_id) VALUES($1, $2, $3)", ctx.author.id, name, None)

        await ctx.send(_("Playlist **{0}** succesfully created! Add songs by doing `{1}playlist add {0} <song name or youtube url>`.").format(name, ctx.prefix))

    @playlist.command(name="add", aliases=['addsong'])
    async def add(self, ctx, playlist, *, song):
        playlists = await self.bot.db.fetch("SELECT * FROM playlists WHERE user_id = $1 AND upper(name) = $2", ctx.author.id, playlist.upper())
        if playlists == []:
            return await ctx.send(_("That playlist does not exist, please create it with the `playlist create` command!"))

        song_count = await self.bot.db.fetchval("SELECT COUNT(track_id) FROM playlists WHERE user_id = $1 AND upper(name) = $2", ctx.author.id, playlist.upper())
        if song_count == 150:
            return await ctx.send(_("You've reached the limit of __150__ songs for this playlist"))

        song = song.strip('<>')
        if not RURL.match(song):
            song = f'ytsearch:{song}'

        tracks = await ctx.get_tracks(song)

        db_tracks = [t for t, in await self.bot.db.fetch("SELECT track_id FROM tracks")]

        if isinstance(tracks, diorite.Playlist):  # Tracks result is a playlist
            in_db_t = []
            in_db_pl = []
            if len(tracks.tracks) > (150 - song_count):
                can_add = 150 - song_count
                await ctx.send(_("This playlists will exceed the limit for your playlist **{0}**. Your playlist can only hold **{1}** more songs, so I will pick the first {1} songs of that playlist.").format(playlist, can_add), delete_after=10, edit=False)
                for t in tracks.tracks[:int(can_add)]:
                    if t.track_id not in db_tracks:
                        in_db_t.append((t.track_id, t.info['identifier'], t.info['isSeekable'], t.info['author'], t.info['length'], t.info['isStream'], t.info['position'], t.info['title'], t.info['uri']))
                    if t.track_id in [t["track_id"] for t in playlists]:
                        continue
                    in_db_pl.append((ctx.author.id, playlist, t.track_id))
            if len(tracks.tracks) < (151 - song_count):
                for t in tracks.tracks:
                    if t.track_id not in db_tracks:
                        in_db_t.append((t.track_id, t.info['identifier'], t.info['isSeekable'], t.info['author'], t.info['length'], t.info['isStream'], t.info['position'], t.info['title'], t.info['uri']))
                    if t.track_id in [t["track_id"] for t in playlists]:
                        continue
                    in_db_pl.append((ctx.author.id, playlist, t.track_id))

            if in_db_t:
                await self.bot.db.executemany("INSERT INTO tracks VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9)", in_db_t)
            await self.bot.db.executemany("INSERT INTO playlists VALUES($1, $2, $3)", in_db_pl)
            await ctx.send(_("Added `{0}` songs to playlist **{1}**!").format(len(in_db_t), playlist.title()))

        else:  # Tracks result can be a single song
            if tracks[0].track_id in [t["track_id"] for t in playlists]:
                return await ctx.send(_("That song has already been added to that playlist."))  # Deny if it's already in the playlist
            t = tracks[0]
            if t.track_id not in db_tracks:
                await self.bot.db.execute("INSERT INTO tracks VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9)", t.track_id, t.info['identifier'], t.info['isSeekable'], t.info['author'], t.info['length'], t.info['isStream'], t.info['position'], t.info['title'], t.info['uri'])
            await self.bot.db.execute("INSERT INTO playlists VALUES($1, $2, $3)", ctx.author.id, playlist, t.track_id)
            title = t.title

            await ctx.send(_("**{0}** added to **{1}**!").format(title, playlist.title()))

    # @music_check(no_channel=True)
    @playlist.command(name='play', aliases=['start', 'p'])
    async def play(self, ctx, *, playlist):
        if not ctx.player.is_connected:
            try:
                await ctx.invoke(self.bot.get_command("connect"))
            except:
                return await ctx.send(_("I am not connected to a voice channel. Please join a voice channel and try again."))

        if not ctx.me.voice:
            return

        tracks = await self.bot.db.fetch("SELECT * FROM playlists INNER JOIN tracks ON tracks.track_id = playlists.track_id WHERE user_id = $1 AND upper(name) = $2", ctx.author.id, playlist.upper())

        if not tracks:
            return await ctx.send(_("You do now own a playlist by that name..."))

        if not ctx.player.dj:
            ctx.player.dj = ctx.author

        for t in tracks:
            info = dict(identifier=t['identifier'],
                        isSeekable=t['isseekable'],
                        author=t['author'],
                        length=t['length'],
                        isStream=t['isstream'],
                        position=t['position'],
                        title=t['title'],
                        uri=t['uri'])
            track = Track(t["track_id"], info, ctx=ctx)
            await ctx.player.queue.put(track)

        await ctx.send(_("**{0}** enqueued!").format(playlist))

        if not ctx.player.is_playing:
            await ctx.player.do_next()

    @playlist.command()
    async def clear(self, ctx, *, playlist):
        playlists = [n for n, in await self.bot.db.fetch("SELECT name FROM playlists WHERE user_id = $1", ctx.author.id)]
        if playlist not in playlists:
            return await ctx.send(_("That playlist does not exist, please create it with the `playlist create` command!"))

        msg = await ctx.send(_("Are you sure you wish to clear your playlist **{0}**?").format(playlist))
        await msg.add_reaction('check:314349398811475968')
        await msg.add_reaction('xmark:314349398824058880')

        def check(r, u):
            return r.message.id == msg.id and u.id == ctx.author.id

        react, user = await self.bot.wait_for('reaction_add', check=check)
        if str(react) == "<:check:314349398811475968>":  # Yep, let's delete
            await self.bot.db.execute("DELETE FROM playlists WHERE user_id = $1 AND upper(name) = $2 AND track_id IS NOT NULL", ctx.author.id, playlist.upper())
            await msg.delete()
            await ctx.send(_("**{0}** has succesfully been cleared!").format(playlist))

        if str(react) == "<:xmark:314349398824058880>":  # No, keep the playlist
            await msg.delete()
            await ctx.send(_("Playlist clearing cancelled."))

    @playlist.command()
    async def remove(self, ctx, playlist, *, song):
        song = song.strip('<>')
        if not RURL.match(song):
            song = f"ytsearch:{song}"

        tracks = await ctx.get_tracks(song)

        playlists = await self.bot.db.fetch("SELECT * FROM playlists WHERE user_id = $1", ctx.author.id)

        if playlist not in [t['name'] for t in playlists]:
            return await ctx.send(_("That playlist does not exist."))

        if not tracks[0].id in [t['track_id'] for t in playlists]:
            return await ctx.send(_("Couldn't find that song in that playlist."))

        await self.bot.db.execute("DELETE FROM playlists WHERE user_id = $1 AND track_id = $2", ctx.author.id, tracks[0].id)

        await ctx.send(_("Succesfully removed **{0}** from **{1}**.").format(tracks[0].title, playlist))

    @playlist.command()
    async def delete(self, ctx, *, playlist):
        playlists = [n for n, in await self.bot.db.fetch("SELECT name FROM playlists WHERE user_id = $1", ctx.author.id)]
        if playlist not in playlists:
            return await ctx.send(_("That playlist does not exist."))

        msg = await ctx.send(_("Are you sure you wish to delete your playlist **{0}**?").format(playlist))
        await msg.add_reaction('check:314349398811475968')
        await msg.add_reaction('xmark:314349398824058880')

        def check(r, u):
            return r.message.id == msg.id and u.id == ctx.author.id

        react, user = await self.bot.wait_for('reaction_add', check=check)
        if str(react) == "<:check:314349398811475968>":  # Yep, let's remove the song
            await self.bot.db.execute("DELETE FROM playlists WHERE user_id = $1 AND upper(name) = $2", ctx.author.id, playlist.upper())
            await msg.delete()
            await ctx.send(_("Playlist **{0}** has succesfully been deleted!").format(playlist))

        if str(react) == "<:xmark:314349398824058880>":  # No, keep the song
            await msg.delete()
            await ctx.send(_("Playlist deleting cancelled."))

    @playlist.command()
    async def show(self, ctx, user: Optional[discord.User] = None, *, playlist):
        user = user or ctx.author

        playlists = await self.bot.db.fetch("SELECT * FROM playlists WHERE user_id = $1 AND upper(name) = $2", user.id, playlist.upper())
        if playlist == []:
            if user == ctx.author:
                return await ctx.send(_("Couldn't find that playlist in your playlists."))
            return await ctx.send(_("Couldn't find that playlist in {0}'s playlists.").format(user.name))
        if len([n['track_id'] for n in playlists if n['track_id'] is not None]) == 0:
            return await ctx.send(_("This playlist does not contain any songs..."))

        tracks = await self.bot.db.fetch("SELECT * FROM tracks")
        queue_list = []
        for track in tracks:
            if track['track_id'] in [n['track_id'] for n in playlists]:
                queue_list.append(f'**[{track["title"]}]({track["uri"]})**')

        paginator = EmbedPages(ctx,
                          title=_("__Showing playlist:__") + f" {playlist.title()}",
                          entries=queue_list,
                          per_page=15,
                          show_entry_nums=True,
                          show_page_num=True,
                          show_entry_count=True)

        await paginator.start()

    @playlist.command()
    async def clone(self, ctx, user: discord.User, playlist: str):
        auth_pl = await self.bot.db.fetch("SELECT name FROM playlists WHERE user_id = $1", ctx.author.id)

        if len(auth_pl) == 10:
            return await ctx.send(_("You have reached the limit of 10 playlists."))

        user_pl = [x for x, in await self.bot.db.fetch("SELECT track_id FROM playlists WHERE user_id = $1 AND upper(name) = $2", user.id, playlist.upper())]

        if user_pl == []:
            return await ctx.send(_("Couldn't find that playlist in {0}'s playlists.").format(user.name))

        pl_name = playlist if playlist not in auth_pl else f"{playlist}+"

        in_db = []
        for x in user_pl:
            in_db.append((ctx.author.id, pl_name, x))
        await self.bot.db.executemany("INSERT INTO playlists VALUES($1, $2, $3)", in_db)

        await ctx.send(_("Succesfully cloned playlist `{0}` ({1} songs) from **{2}**!").format(playlist, str(len(user_pl)-1), user.name))

    # @playlist.command(name="shuffle")
    # async def shuffle(self, ctx, *, playlist):
    #     if not os.path.exists(f'/home/dutchy/Charles/db/Playlists/{ctx.author.id}.json'):
    #         return await ctx.send(_("You do not have any playlists created yet. Please use the `playlist create` command to make one!"))

    #     with open(f'db/Playlists/{ctx.author.id}.json', "r") as f:
    #         data = json.load(f)

    #     if not playlist in data["Playlists"]:
    #         return await ctx.send(_("Couldn't find that playlist in your playlists."))

    #     listdata = []
    #     for pl in data["Playlists"][playlist]:
    #         listdata.append({pl:data["Playlists"][playlist][pl]})
    #     random.shuffle(listdata)

    #     newdict = {}
    #     for entry in listdata:
    #         for k, v in entry.items():
    #             newdict[k] = v

    #     data["Playlists"][playlist] = newdict

    #     with open(f'db/Playlists/{ctx.author.id}.json', "w") as f:
    #         json.dump(data, f, indent=4)

    #     await ctx.send(_("Succesfully shuffled playlist `{0}`!").format(playlist))

    # TODO: Make 'playlist rename'


def setup(bot):
    pass
