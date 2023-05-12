import asyncio
import re
from datetime import datetime, timedelta
from functools import partial

import async_timeout
import diorite
import discord
import dropbox
import lyricsgenius
from core import i18n
from db import tokens
from youtube_dl import YoutubeDL


class Track(diorite.Track):
    __slots__ = ('requester', 'ctx', 'thumb')

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self.ctx = kwargs.get('ctx')
        self.requester = self.ctx.author
        self.thumb = f"https://img.youtube.com/vi/{self.uri[32:]}/maxresdefault.jpg"


class Player(diorite.Player):
    def __init__(self, node, guild, **kwargs):
        self.ctx = kwargs.get("ctx")
        super().__init__(node, guild, **kwargs)
        self.dj = self.ctx.author

        self.node = node
        self.guild = self.ctx.guild
        self.voice_channel = None
        self.text_channel = None
        self.queue = asyncio.Queue()

        self.voice_state = {}
        self.player_state = {}
        self.waiting = False

        # self.last_position = 0
        # self.last_update = 0
        # self.time = 0
        self.volume = 100
        self.paused = False
        self.filters = None
        self.loop = 0
        self.speed = 1.0
        self.pitch = 1.0
        self.filter = None
        self.current = None
        self.track_start = 0

        self.pause_votes = set()
        self.resume_votes = set()
        self.stop_votes = set()
        self.shuffle_votes = set()
        self.skip_votes = set()
        self.repeat_votes = set()

    @property
    def entries(self):
        return list(self.queue._queue)

    # @property
    # def position(self):
    #     if not self.is_playing:
    #         return 0

    #     if not self.current:
    #         return 0

    #     if self.paused:
    #         return min(self.last_position, self.current.length)

    #     difference = (time.time() * 1000) - self.last_update
    #     return min(self.last_position + difference, self.current.length)

    async def do_next(self) -> None:
        if self.is_playing or self.waiting:
            return

        self.pause_votes.clear()
        self.resume_votes.clear()
        self.skip_votes.clear()
        self.shuffle_votes.clear()
        self.stop_votes.clear()
        self.repeat_votes.clear()

        try:
            self.waiting = True
            with async_timeout.timeout(300):
                track = await self.queue.get()
        except asyncio.TimeoutError:
            return await self.teardown()

        await self.play(track)
        if self.loop != 0:
            if self.loop == 1:
                self.queue._queue.appendleft(track)

            else:
                await self.queue.put(track)
        self.waiting = False

    async def teardown(self):
        try:
            await self.destroy()
        except KeyError:
            pass

    # @property
    # def is_playing(self):
    #     if not self.is_connected:
    #         return False

    #     if not self.last_position:
    #         return False

    #     if self.current:
    #         if self.last_position > 0 and self.last_position < self.current.length:
    #             return True

    #     return False

    @property
    def main_page(self):
        track = self.current
        if track.is_stream:
            dur = '🔴 ' + _("Live")
        else:
            dur = str(timedelta(milliseconds=int(track.length)))

        duration = _("Duration")
        volume = _("Volume")
        dj = _("DJ")
        loop = _("Loop")
        filt = _("Filter")
        nex = _("Up Next")
        position = str(datetime.utcfromtimestamp(self.position/1000).strftime("%H:%M:%S"))
        dur_time = f"{position}/{dur}"

        desc = []
        desc.append(f"<:duration:697504688114892861> | **{duration}:** {dur_time}")
        desc.append(f"<:volume:697504689499144302> | **{volume}:** {self.volume}%")

        if self.loop == 0:
            loop_opt = _("Disabled")
            loope = "<:loopD:697512088901517390>"
        if self.loop == 1:
            loop_opt = _("Current")
            loope = "<:loop1:697512087739564114>"
        if self.loop == 2:
            loop_opt = _("ALL")
            loope = "<:loopA:697512089119359016>"

        if self.filter:
            filte = self.filter
        else:
            filte = _("Speed") + f": {self.speed}x " + _("Pitch") + f": {self.pitch}x"

        desc.append(f"{loope} | **{loop}:** {loop_opt}")
        desc.append(f"<:dj:697510774792388761> | **{dj}:** {self.dj}")
        desc.append(f"<:filter:697513842367791145> | **{filt}:** {filte}")
        if self.entries:
            desc.append(f"<:queue:697528159054332026> | **{nex}:** {self.entries[0].title}")
        else:
            empty = _("No more songs in queue")
            desc.append(f"<:queue:697528159054332026> | **{nex}:** {empty}")

        main_embed = discord.Embed(color=self.ctx.embed_color,
                              title=track.title,
                              url=track.uri,
                              description='\n'.join(desc))

        main_embed.set_author(name=_("Now Playing:"),
                              icon_url="https://cdn.discordapp.com/emojis/694199307682840656.gif")
        main_embed.set_thumbnail(url=track.thumb)
        main_embed.set_footer(text=_("Requested By: {0}").format(track.requester))

        return main_embed

    @property
    def info_page(self):
        info_embed = discord.Embed(color=self.ctx.embed_color)
        info_embed.title = _("Controller Paginator Information")

        description = f"{self.ctx.emoji.music_note} • **"+_("Main Page")+"**\n"
        description += "> "+_("Show the player settings for the current playing song.")+"\n\n"

        description += f"{self.ctx.emoji.track_info} • **"+_("Song Information")+"**\n"
        description += "> "+_("Get detailed information about this song.")+"\n\n"

        description += f"{self.ctx.emoji.lyrics} • **"+_("Song Lyrics")+"**\n"
        description += "> "+_("Find  lyrics for this song.")+"\n\n"

        description += f"{self.ctx.emoji.mp3} • **"+_("Download MP3")+"**\n"
        description += "> "+_("Download an mp3 of this song.")+"\n\n"

        description += f"{self.ctx.emoji.delete} • **"+_("Delete Contoller")+"**\n"
        description += "> "+_("Delete this controller message.")+"\n\n"

        description += f"{self.ctx.emoji.qmark} • **"+_("Info Page")+"**\n"
        description += "> "+_("Shows you this page.")

        info_embed.description = description

        return info_embed

    async def lyrics_page(self):
        track = self.ctx.player.current

        ydl_opts = {
                'format': 'bestaudio',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320'}],
            }

        ytdl = YoutubeDL(ydl_opts)
        to_run = partial(ytdl.extract_info, url=track.uri, download=False)

        data = await self.ctx.bot.loop.run_in_executor(None, to_run)

        if not data:
            return discord.Embed(color=self.ctx.embed_color, description=_("I was unable to find lyrics for this song... Most likely something messed up with my connection to YouTube."))

        creator = data.get('creator', _("None"))
        title = data.get('alt_title', _("None"))

        song_title = track.title or f"{creator} - {title}"

        genius = lyricsgenius.Genius(tokens.LYRICSGENIUS)
        song = genius.search_song(song_title)

        lyric_embed = discord.Embed(color=self.ctx.embed_color,
                                  title=_("Lyrics for: {0}").format(song_title))
        lyric_embed.description = song.lyrics[:2045] + "..."
        return lyric_embed

    async def download_song(self):
        track = self.ctx.player.current
        ydl_opts = {
                'outtmpl': '{}.%(ext)s'.format(self.ctx.author.id),
                'format': 'bestaudio',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320'}],
            }

        ytdl = YoutubeDL(ydl_opts)
        to_run = partial(ytdl.extract_info, url=track.uri, download=False)

        data = await self.bot.loop.run_in_executor(None, to_run)

        if data:
            song_title = track.title
        else:
            return discord.Embed(color=self.ctx.embed_color, description=_("I was unable to download this song... Most likely something messed up with my connection to YouTube."))

        async with self.ctx.bot.session.get(data.get('url', _("None"))) as f:
            mp3_file = await f.read()

        download_embed = discord.Embed(color=self.ctx.embed_color)
        download_embed.title = _("MP3 Download")
        # filepath = f"/home/dutchy/Charles_RW/{ctx.author.id}.mp3"
        targetfile = f"/mp3_files/{song_title}.mp3"

        d = dropbox.Dropbox(tokens.DROPBOX)

        # with open(filepath, "rb") as f:
        #     meta = d.files_upload(mp3_file, targetfile, mode=dropbox.files.WriteMode("overwrite"))
        d.files_upload(mp3_file, targetfile, mode=dropbox.files.WriteMode("overwrite"))

        link = d.sharing_create_shared_link(targetfile)
        url = link.url
        dl_url = re.sub(r"\?dl\=0", "?dl=1", url)

        # os.remove(f"/home/dutchy/Charles_RW/{ctx.author.id}.mp3")

        dl = _("Click here to download!")
        download_embed.add_field(name=_("Song succesfully downloaded!"),
                                 value=f"{song_title}\n[{dl}]({dl_url})")

        return download_embed

    async def song_info_page(self):
        track = self.ctx.player.current

        ydl_opts = {
                'format': 'bestaudio',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320'}],
            }

        ytdl = YoutubeDL(ydl_opts)
        to_run = partial(ytdl.extract_info, url=track.uri, download=False)

        data = await self.ctx.bot.loop.run_in_executor(None, to_run)

        if not data:
            return discord.Embed(color=self.ctx.embed_color, description=_("Could not find any information for this song, sorry..."))

        uploader_name = data.get('uploader')
        uploader_link = data.get('uploader_url')
        date_year = data.get('upload_date')[:4]
        date_month = data.get('upload_date')[4:][:2]
        date_day = data.get('upload_date')[6:]
        creator = data.get('creator')
        title = data.get('alt_title', _("None"))
        thumbnail = data.get('thumbnail')
        description = data.get('description', _("None"))
        categories = data.get('categories', _("None"))  # ', '.join(data.get('categories', _("None")))
        tags = data.get('tags', _("None"))  # ', '.join(data.get('tags', _("None")))
        views = int(data.get('view_count') or 0)
        likes = int(data.get('like_count') or 0)
        dislikes = int(data.get('dislike_count') or 0)
        average_rating = data.get('average_rating', _("None"))
        song_url = data.get('webpage_url', _("None"))

        song_info_embed = discord.Embed(color=self.ctx.embed_color)
        song_info_embed.set_thumbnail(url=thumbnail)

        song_title = track.title or f"{creator} - {title}"

        song_info_embed.title = song_title
        song_info_embed.url = song_url

        if len(description) > 2048:
            description = description[:2040] + "..."

        song_info_embed.description = description + "\n⠀"
        song_info_embed.add_field(name=_("Other Info"),
                                  value="**"+_("Categories:")+f"**\n{', '.join(categories)}\n\n**"+_("Tags:")+f"**\n{', '.join(tags)}\n\n👀 "+_("Views:")+f" {views:,}\n<:upvote:596577438461591562> "+_("Likes:")+f" {likes:,}\n<:downvote:596577438952062977> "+_("Dislikes:")+f" {dislikes:,}\n⭐ "+_("Average Rating:")+f" {average_rating}")
        song_info_embed.add_field(name=_("Upload Info"),
                                  value=_("Uploader:")+f" [{uploader_name}]({uploader_link})\n" + _("Upload date:")+f" {date_month}/{date_day}/{date_year}\n⠀")

        return song_info_embed

    # async def player_loop(self):
    #     await self.bot.wait_until_ready()

    #     await self.set_eq(wavelink.Equalizer.flat())
    #     # We can do any pre loop prep here...
    #     await self.set_volume(self.volume)

    #     while True:
    #         self.next_event.clear()

    #         self.inactive = False

    #         song = await self.queue.get()
    #         if not song:
    #             continue

    #         self.current = song
    #         self.paused = False

    #         await self.play(song)

    #         # Wait for TrackEnd event to set our event...
    #         await self.next_event.wait()

    #         if self.loop != 0:
    #             if self.loop == 1:
    #                 self.queue._queue.appendleft(song)

    #             else:
    #                 await self.queue.put(song)

    #         # # Clear votes...
    #         # self.pauses.clear()
    #         # self.resumes.clear()
    #         # self.stops.clear()
    #         # self.shuffles.clear()
    #         # self.skips.clear()
    #         # self.repeats.clear()
