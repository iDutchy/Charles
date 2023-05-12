import asyncio
import math
import random
import re
import time
from datetime import datetime

import diorite
import discord
from core import i18n
from core.cog import SubCog
from core.commands import commandExtra, groupExtra
from discord.ext import commands
from utils import checks

from .player import Track

RURL = re.compile(r'https?://(?:www\.)?.+')


class MusicControls(SubCog, category="Player Controls"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_diorite_track_end(self, data):
        await data.player.stop()
        await data.player.do_next()

    @commands.Cog.listener()
    async def on_diorite_track_start(self, data):
        data.player.track_start = time.time()
        await data.player.seek(0.00001)

    # async def cog_before_invoke(self, ctx: commands.Context):
    #     player = ctx.player

    #     if player.ctx:
    #         if player.ctx.channel != ctx.channel:
    #             await ctx.send(f'{ctx.author.mention}, you must be in {player.ctx.channel.mention} for this session.')
    #             return

    #     if ctx.command.name == 'connect' and not player.ctx:
    #         return
    #     elif self.is_dj(ctx) or self.is_admin(ctx):
    #         return

    #     if not player.voice_channel:
    #         return

    #     channel = player.voice_channel
    #     if not channel:
    #         return

    #     if player.is_connected:
    #         if ctx.author not in channel.members:
    #             await ctx.send(f'{ctx.author.mention}, you must be in `{channel.name}` to use voice commands.')
    #             return

    def required(self, ctx: commands.Context):
        player = ctx.player
        channel = player.voice_channel
        required = math.ceil((len(channel.members) - 1) / 2.5)

        if ctx.command.name == 'stop':
            if len(channel.members) - 1 == 2:
                required = 2

        return required

    def is_dj(self, ctx: commands.Context):
        return ctx.player.dj == ctx.author

    def is_admin(self, ctx: commands.Context):
        return ctx.author.guild_permissions.manage_guild

    def vote_check(self, ctx):
        vc_members = len(ctx.player.voice_channel.members) - 1
        votes = getattr(ctx.player, ctx.command.qualified_name + '_votes')
        if vc_members < 3 and not ctx.invoked_with == 'stop':
            votes.clear()
            return True
        else:
            votes.add(ctx.author.id)
            if len(votes) >= self.required(ctx):
                votes.clear()
                return True
        return False

    async def do_vote(self, ctx):
        votes = getattr(ctx.player, ctx.command.name + '_votes')

        if ctx.author.id in votes:
            return await ctx.send(_("{0}, you have already voted to **{1}** the current song!").format(ctx.author.mention, ctx.command.name), delete_after=15)
        elif self.vote_check(ctx):
            await ctx.send(_("Vote request for **{0}** has passed!").format(ctx.command.name), delete_after=10)
            to_do = getattr(self, f'do_{ctx.command.name}')
            await to_do(ctx)
        else:
            embed = discord.Embed(description=_("{0} has voted to {1} the song!").format(ctx.author.mention, ctx.command.name))
            embed.set_footer(text=_("{0} more votes needed to to {1}!").format(self.required(ctx) - len(votes), ctx.command.name))
            return await ctx.send(embed=embed, delete_after=45)

    @checks.music(bot_no_channel=False, same_channel=False, not_playing=False)
    @commandExtra(name="connect", aliases=['join'], category="Player Controls")
    async def _connect(self, ctx, *, channel: discord.VoiceChannel = None):
        if ctx.player.is_connected:
            return await ctx.send(_("I am already connected"))

        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                return await ctx.send(_("No channel to join. Please either specify a valid channel or join one."))

        if not channel.permissions_for(ctx.me).connect:
            return await ctx.send(_("It seems that I cannot connect to this channel. Please edit the settings of the channel if you want me to play music in it!"))

        await ctx.player.connect(channel)
        return await ctx.send(_("{0} | Joined the voice channel `{1}`!").format(ctx.emoji.music_note, channel))

    @checks.music(bot_no_channel=False, same_channel=False, not_playing=False)
    @commandExtra(name="play", category="Player Controls", aliases=['p'])
    async def _play(self, ctx, *, query: str):
        if not ctx.player.is_connected:
            try:
                await ctx.invoke(self._connect)
            except:
                return await ctx.send(_("I am not connected to a voice channel. Please join a voice channel and try again."))

        if not ctx.me.voice:
            return

        query = query.strip('<>')
        if not RURL.match(query):
            query = f'ytsearch:{query}'

        tracks = await ctx.get_tracks(query)

        if isinstance(tracks, diorite.Playlist):
            for track in tracks.tracks:
                track = Track(track.track_id, track.info, ctx=ctx)
                await ctx.player.queue.put(track)
            await ctx.send(_("{0} | **{1} songs** from playlist \"{2}\" have been added to the queue!").format(ctx.emoji.queue, str(len(tracks.tracks)), tracks.name))
        else:
            track = Track(tracks[0].track_id, tracks[0].info, ctx=ctx)
            await ctx.player.queue.put(track)
            await ctx.send(_("{0} | Track **{1}** has been added to the queue!").format(ctx.emoji.queue, track.title))

        if not ctx.player.is_playing:
            await ctx.player.do_next()

    @checks.music(no_tracks_remove=True)
    @commandExtra(name="remove", category="Player Controls")
    async def _remove(self, ctx, index: int):
        if not self.is_dj(ctx) and not self.is_admin(ctx):
            return await ctx.send(_("Only an Admin or the DJ can remove songs from the queue!"))

        upcoming = ctx.player.entries
        if index > len(upcoming) or index < 1:
            return await ctx.send(_("Index has to be between 1 and {0}!").format(len(upcoming)))

        removed = upcoming[index - 1]
        ctx.player.queue._queue.remove(removed)

        await ctx.send(_("{0} | Removed '**{1}**' from the queue.").format(ctx.emoji.delete, removed.title))

    @checks.music()
    @commandExtra(name='pause', category="Player Controls")
    async def _pause(self, ctx):
        if ctx.player.paused:
            return await ctx.send(_("The player is already paused!"))

        embed = discord.Embed(color=ctx.embed_color)
        if self.is_dj(ctx):
            embed.description = _("{0} | DJ {1} has paused the song.").format(ctx.emoji.pause, ctx.author.mention)
            await ctx.send(embed=embed, delete_after=25)
            return await self.do_pause(ctx)

        elif self.is_admin(ctx):
            embed.description = _("{0} | Admin {1} has paused the song.").format(ctx.emoji.pause, ctx.author.mention)
            await ctx.send(embed=embed, delete_after=25)
            return await self.do_pause(ctx)

        else:
            await self.do_vote(ctx)

    async def do_pause(self, ctx):
        await ctx.player.set_pause(True)

    @checks.music()
    @commandExtra(name='resume', category="Player Controls")
    async def _resume(self, ctx):
        if not ctx.player.paused:
            return await ctx.send(_("The player is not paused!"))

        embed = discord.Embed(color=ctx.embed_color)
        if self.is_dj(ctx):
            embed.description = _("{0} | DJ {1} has resumed the song.").format(ctx.emoji.play, ctx.author.mention)
            await ctx.send(embed=embed, delete_after=25)
            return await self.do_resume(ctx)

        elif self.is_admin(ctx):
            embed.description = _("{0} | Admin {1} has resumed the song.").format(ctx.emoji.play, ctx.author.mention)
            await ctx.send(embed=embed, delete_after=25)
            return await self.do_resume(ctx)

        else:
            await self.do_vote(ctx)

    async def do_resume(self, ctx):
        await ctx.player.set_pause(False)

    @checks.music()
    @commands.cooldown(5, 10, commands.BucketType.user)
    @commandExtra(name='skip', category="Player Controls")
    async def _skip(self, ctx):
        if not ctx.player.is_playing:
            return await ctx.send(_("I am not playing anything."))

        if not ctx.player.entries:
            return await ctx.send(_("There are no more songs in the queue to skip to!"))

        embed = discord.Embed(color=ctx.embed_color)
        if self.is_dj(ctx):
            embed.description = _("{0} | DJ {1}, has skipped the song.").format(ctx.emoji.skip, ctx.author.mention)
            await ctx.send(embed=embed, delete_after=25)
            return await self.do_skip(ctx)

        elif ctx.player.current.requester.id == ctx.author.id:
            embed.description = _("{0} | The requester of this song, {1} has skipped the song.").format(ctx.emoji.skip, ctx.author.mention)
            await ctx.send(embed=embed, delete_after=25)
            return await self.do_skip(ctx)

        elif self.is_admin(ctx):
            embed.description = _("{0} | Admin {1} has skipped the song.").format(ctx.emoji.skip, ctx.author.mention)
            await ctx.send(embed=embed, delete_after=25)
            return await self.do_skip(ctx)

        else:
            await self.do_vote(ctx)

    async def do_skip(self, ctx):
        await ctx.player.stop()
        # await ctx.player.do_next()

    @checks.music(not_playing=False)
    @commands.cooldown(3, 30, commands.BucketType.guild)
    @commandExtra(name='stop', category="Player Controls", aliases=["dc", "disconnect"])
    async def _stop(self, ctx):
        embed = discord.Embed(color=ctx.embed_color)
        if self.is_dj(ctx):
            embed.description = _("{0} | DJ {1} has stopped the player.").format(ctx.emoji.stop, ctx.author.mention)
            await ctx.send(embed=embed, delete_after=25)
            return await self.do_stop(ctx)

        elif self.is_admin(ctx):
            embed.description = _("{0} | Admin {1} has stopped the player.").format(ctx.emoji.stop, ctx.author.mention)
            await ctx.send(embed=embed, delete_after=25)
            return await self.do_stop(ctx)

        else:
            await self.do_vote(ctx)

    async def do_stop(self, ctx):
        await ctx.player.teardown()

    @checks.music(not_playing=False)
    @commands.cooldown(1, 2, commands.BucketType.guild)
    @commandExtra(name='volume', aliases=['vol'], category="Player Controls")
    async def _volume(self, ctx, *, value: int):
        if not 0 < value < 201:
            return await ctx.send(_("Please enter a value between 1 and 200."))

        if not self.is_admin(ctx) and not self.is_dj(ctx):
            if (len(ctx.guild.me.voice.channel.members) - 1) > 2:
                return await ctx.send(_("You need to be the DJ or an Admin to use this command!"))

        if value < ctx.player.volume:
            emoji = ctx.emoji.vol_down
        elif value > ctx.player.volume:
            emoji = ctx.emoji.vol_up
        elif value == ctx.player.volume:
            emoji = ctx.emoji.volume

        await ctx.player.set_volume(value)
        embed = discord.Embed(color=ctx.embed_color)
        if self.is_dj(ctx):
            embed.description = _("{0} | DJ {1} has set the volume to `{2}%`").format(emoji, ctx.author.mention, ctx.player.volume)
        if self.is_admin(ctx):
            embed.description = _("{0} | Admin {1} has set the volume to `{2}%`").format(emoji, ctx.author.mention, ctx.player.volume)
        await ctx.send(embed=embed, delete_after=7)

    # @checks.has_voted()
    @checks.music(no_tracks_shuffle=True)
    @commands.cooldown(2, 10, commands.BucketType.user)
    @commandExtra(name='shuffle', aliases=['mix'], category="Player Controls")
    async def _shuffle(self, ctx):
        if len(ctx.player.entries) < 3:
            return await ctx.send(_("Please add more songs to the queue before trying to shuffle."), delete_after=10)

        if self.is_dj(ctx):
            embed = discord.Embed(color=ctx.embed_color,
                                  description=_("{0} | DJ {1} has shuffled the queue.").format(ctx.emoji.shuffle, ctx.author.mention), delete_after=25)
            await ctx.send(embed=embed)
            return await self.do_shuffle(ctx)

        elif self.is_admin(ctx):
            embed = discord.Embed(color=ctx.embed_color,
                                  description=_("{0} | Admin {1} has shuffled the queue.").format(ctx.emoji.shuffle, ctx.author.mention), delete_after=25)
            await ctx.send(embed=embed)
            return await self.do_shuffle(ctx)

        else:
            await self.do_vote(ctx)

    async def do_shuffle(self, ctx):
        random.shuffle(ctx.player.queue._queue)

    # @checks.has_voted()
    @checks.music()
    @commandExtra(name='repeat', category="Player Controls", aliases=['loop'])
    async def _repeat(self, ctx):
        embed = discord.Embed(color=ctx.embed_color)
        e = ctx.emoji.loop
        if self.is_dj(ctx):
            await self.do_repeat(ctx)
            if ctx.player.loop == 0:
                embed.description = _("{0} | DJ {1} has stopped the loop.").format(e, ctx.author.mention)
            elif ctx.player.loop == 1:
                embed.description = _("{0} | DJ {1} has set the loop to `Current`.").format(e, ctx.author.mention)
            elif ctx.player.loop == 2:
                embed.description = _("{0} | DJ {1} has set the loop to `All`.").format(e, ctx.author.mention)
            return await ctx.send(embed=embed, delete_after=9)
        elif self.is_admin(ctx):
            await self.do_repeat(ctx)
            if ctx.player.loop == 0:
                embed.description = _("{0} | Admin {1} has stopped the loop.").format(e, ctx.author.mention)
            elif ctx.player.loop == 1:
                embed.description = _("{0} | Admin {1} has set the loop to `Current`.").format(e, ctx.author.mention)
            elif ctx.player.loop == 2:
                embed.description = _("{0} | Admin {1} has set the loop to `All`.").format(e, ctx.author.mention)
            return await ctx.send(embed=embed, delete_after=9)
        else:
            await self.do_vote(ctx)

    async def do_repeat(self, ctx):
        if ctx.player.loop == 0:
            ctx.player.loop = 1
        elif ctx.player.loop == 1:
            ctx.player.loop = 2
        elif ctx.player.loop == 2:
            ctx.player.loop = 0

    # @checks.has_voted()
    @checks.music(seekable=True)
    @commandExtra(name="seek", category="Player Controls")
    async def _seek(self, ctx, time: int):
        if not self.is_admin(ctx) and not self.is_dj(ctx):
            return await ctx.send(_("You need to be the DJ or an Admin to use this command!"))

        can_forward = int((ctx.player.current.length - ctx.player.position) / 1000)
        can_rewind = int(ctx.player.position / 1000)
        if time > can_forward:
            return await ctx.send(_("There are {0} seconds left. Can not skip further than that!").format(str(can_forward)))
        if time < 0 - can_rewind:
            time = 0 - can_rewind
        await ctx.player.seek(int(ctx.player.position + (time*1000)))
        newpos = str(datetime.utcfromtimestamp(ctx.player.position/1000 + time).strftime("%H:%M:%S"))
        e = discord.Embed(color=ctx.embed_color)

        if self.is_dj(ctx):
            if str(time).startswith("-"):
                e.description = _("{0} | DJ {1} rewinded the position to {2}").format(ctx.emoji.rewind, ctx.author.mention, newpos)
            else:
                e.description = _("{0} | DJ {1} has forwarded the position to {2}").format(ctx.emoji.forward, ctx.author.mention, newpos)
        elif self.is_admin(ctx):
            if str(time).startswith("-"):
                e.description = _("{0} | Admin {1} rewinded the position to {2}").format(ctx.emoji.rewind, ctx.author.mention, newpos)
            else:
                e.description = _("{0} | Admin {1} has forwarded the position to {2}").format(ctx.emoji.forward, ctx.author.mention, newpos)

        await ctx.send(embed=e)

    # @checks.has_voted()
    @checks.music(not_playing=False)
    @commandExtra(category="Player Controls")
    async def find(self, ctx, *, query):
        tracks = await ctx.get_tracks(f'ytsearch:{query}')

        tracklist = tracks[:10]

        o = []
        od = {}
        for index, track in enumerate(tracklist, start=1):
            o.append(f'`{index}.` [{track.title}]({track.uri})')
            od[str(index)] = Track(track.track_id, track.info, ctx=ctx)

        embed = discord.Embed(color=ctx.embed_color, description="\n".join(o))
        emsg = await ctx.send(embed=embed)

        if ctx.player.is_connected:
            await ctx.send(content=_("Please say the index number of the song you'd like to play"), edit=False)

            def check(m):
                return ctx.author == m.author and m.content in od.keys()

            try:
                checking = await self.bot.wait_for('message', check=check, timeout=30.0)
            except asyncio.TimeoutError:
                return

            track = od[checking.content]
            await ctx.player.queue.put(track)

            if not ctx.player.is_playing:
                await ctx.player.do_next()

            embed = discord.Embed(color=ctx.embed_color)
            embed.title = _("{0} | Track added to queue!").format(ctx.emoji.queue)
            embed.description = f"[{track.title}]({track.uri})"
            embed.set_thumbnail(url=track.thumb)
            await ctx.send(embed=embed, delete_after=15)
            await emsg.delete()

    @checks.music(no_tracks_clear=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commandExtra(name='clearqueue', aliases=['cq'], category="Player Controls")
    async def _clearqueue(self, ctx):
        upcoming = ctx.player.entries
        if not upcoming:
            return await ctx.send(embed=discord.Embed(colour=ctx.embed_color,
                                  title='<:menu:600682024558264322> ' + _("No more songs in queue!")), delete_after=15)

        if not self.is_dj(ctx) and not self.is_admin(ctx):
            return await ctx.send(_("Only the DJ or an Admin can clear the queue!"))

        ctx.player.queue._queue.clear()
        embed = discord.Embed(color=ctx.embed_color)

        await ctx.send(embed=embed, delete_after=15)
        if self.is_dj(ctx):
            embed.description = _("{0} | DJ {1} has cleared the queue!").format(ctx.emoji.delete, ctx.author.mention)
            return await ctx.send(embed=embed)
        elif self.is_admin(ctx):
            embed.description = _("{0} | Admin {1} has cleared the queue!").format(ctx.emoji.delete, ctx.author.mention)
            return await ctx.send(embed=embed)

    @checks.music()
    @groupExtra(name="filter", category="Player Controls", invoke_without_command=True)
    async def _filter(self, ctx):
        await ctx.send_help(ctx.command)

    @_filter.command(name='speed')
    async def _speed(self, ctx, speed: float):
        if not ctx.player.is_connected:
            return await ctx.send(_("I am not connected to a voice channel. Please join a voice channel and try again."))

        if not self.is_dj(ctx) and not self.is_admin(ctx):
            return await ctx.send(_("Only the DJ or an Admin can change this!"))

        if speed > 2:
            return await ctx.send(_("You can not set the speed higher than 2.0x!"))
        if speed < 0.4:
            return await ctx.send(_("You can not set the speed lower than 0.4x!"))

        ctx.player.speed = speed
        # await ctx.player.set_timescale(speed=ctx.player.speed, pitch=ctx.player.pitch)
        await self.do_filter(ctx)
        ctx.player.filter = None
        embed = discord.Embed(color=ctx.embed_color)

        # await ctx.send(_("<a:discord_loading:587812494089912340> | Applying setting..."))
        # await asyncio.sleep(5.0)
        # await ctx.send(embed=embed, delete_after=15)
        if self.is_dj(ctx):
            embed.description = _("{0} | DJ {1} has set the speed to {2}x !").format(ctx.emoji.settings, ctx.author.mention, str(speed))
            return await ctx.send(embed=embed)
        elif self.is_admin(ctx):
            embed.description = _("{0} | Admin {1} has set the speed to {2}x !").format(ctx.emoji.settings, ctx.author.mention, str(speed))
            return await ctx.send(embed=embed)

    @_filter.command(name='pitch')
    async def _pitch(self, ctx, pitch: float):
        if not ctx.player.is_connected:
            return await ctx.send(_("I am not connected to a voice channel. Please join a voice channel and try again."))

        if not self.is_dj(ctx) and not self.is_admin(ctx):
            return await ctx.send(_("Only the DJ or an Admin can change this!"))

        if pitch > 2:
            return await ctx.send(_("You can not set the pitch higher than 2.0x!"))
        if pitch < 0.4:
            return await ctx.send(_("You can not set the pitch lower than 0.4x!"))

        ctx.player.pitch = pitch
        # await ctx.player.set_timescale(speed=ctx.player.speed, pitch=ctx.player.pitch)
        embed = discord.Embed(color=ctx.embed_color)
        await self.do_filter(ctx)
        ctx.player.filter = None
        # await ctx.send(_("{0} | Applying setting...").format("<a:discord_loading:587812494089912340>"))
        # await asyncio.sleep(5.0)
        # await ctx.send(embed=embed, delete_after=15)
        if self.is_dj(ctx):
            embed.description = _("{0} | DJ {1} has set the pitch to {2}x !").format(ctx.emoji.settings, ctx.author.mention, str(pitch))
            return await ctx.send(embed=embed)
        elif self.is_admin(ctx):
            embed.description = _("{0} | Admin {1} has set the pitch to {2}x !").format(ctx.emoji.settings, ctx.author.mention, str(pitch))
            return await ctx.send(embed=embed)

    @_filter.command(name='nightcore')
    async def _nightcore(self, ctx):
        if not ctx.player.is_connected:
            return await ctx.send(_("I am not connected to a voice channel. Please join a voice channel and try again."))

        if not self.is_dj(ctx) and not self.is_admin(ctx):
            return await ctx.send(_("Only the DJ or an Admin can change this!"))

        ctx.player.pitch = 1.375
        ctx.player.speed = 1.155
        # await ctx.player.set_timescale(speed=ctx.player.speed, pitch=ctx.player.pitch)
        embed = discord.Embed(color=ctx.embed_color)
        await self.do_filter(ctx)
        ctx.player.filter = "Nightcore"
        # await ctx.send(_("{0} | Applying setting...").format("<a:discord_loading:587812494089912340>"))
        # await asyncio.sleep(5.0)
        # await ctx.send(embed=embed, delete_after=15)
        if self.is_dj(ctx):
            embed.description = _("{0} | DJ {1} has set the filter to `Nightcore`!").format(ctx.emoji.settings, ctx.author.mention)
            return await ctx.send(embed=embed)
        elif self.is_admin(ctx):
            embed.description = _("{0} | Admin {1} has set the filter to `Nightcore`!").format(ctx.emoji.settings, ctx.author.mention)
            return await ctx.send(embed=embed)

    @_filter.command(name='male')
    async def _maleify(self, ctx):
        if not ctx.player.is_connected:
            return await ctx.send(_("I am not connected to a voice channel. Please join a voice channel and try again."))

        if not self.is_dj(ctx) and not self.is_admin(ctx):
            return await ctx.send(_("Only the DJ or an Admin can change this!"))

        ctx.player.pitch = 0.725
        ctx.player.speed = 0.95
        # await ctx.player.set_timescale(speed=ctx.player.speed, pitch=ctx.player.pitch)
        embed = discord.Embed(color=ctx.embed_color)
        await self.do_filter(ctx)
        ctx.player.filter = "Male"
        # await ctx.send(_("{0} | Applying setting...").format("<a:discord_loading:587812494089912340>"))
        # await asyncio.sleep(5.0)
        # await ctx.send(embed=embed, delete_after=15)
        if self.is_dj(ctx):
            embed.description = _("{0} | DJ {1} has set the filter to `Male`!").format(ctx.emoji.settings, ctx.author.mention)
            return await ctx.send(embed=embed)
        elif self.is_admin(ctx):
            embed.description = _("{0} | Admin {1} has set the filter to `Male`!").format(ctx.emoji.settings, ctx.author.mention)
            return await ctx.send(embed=embed)

    @_filter.command(name='reset', aliases=['remove'])
    async def _resetfilter(self, ctx):
        if not ctx.player.is_connected:
            return await ctx.send(_("I am not connected to a voice channel. Please join a voice channel and try again."))

        if not self.is_dj(ctx) and not self.is_admin(ctx):
            return await ctx.send(_("Only the DJ or an Admin can change this!"))

        ctx.player.pitch = 1.0
        ctx.player.speed = 1.0

        embed = discord.Embed(color=ctx.embed_color)
        await self.do_filter(ctx)
        ctx.player.filter = None
        # await ctx.send(_("{0} | Applying setting...").format("<a:discord_loading:587812494089912340>"))
        # await asyncio.sleep(5.0)
        # await ctx.send(embed=embed, delete_after=15)
        if self.is_dj(ctx):
            embed.description = _("{0} | DJ {1} has reset the filter!").format(ctx.emoji.settings, ctx.author.mention)
            return await ctx.send(embed=embed)
        elif self.is_admin(ctx):
            embed.description = _("{0} | Admin {1} has reset the filter!").format(ctx.emoji.settings, ctx.author.mention)
            return await ctx.send(embed=embed)

    async def do_filter(self, ctx):
        await ctx.player.set_timescale(speed=ctx.player.speed, pitch=ctx.player.pitch)
        await ctx.player.seek(ctx.player.position+0.00001)

    # @_filter.command(name='distortion')
    # async def _distortion(self, ctx, value: float):
    #     if not ctx.player.is_connected:
    #         return await ctx.send(_("I am not connected to a voice channel. Please join a voice channel and try again."))

    #     if not self.is_dj(ctx) and not self.is_admin(ctx):
    #         return await ctx.send(_("Only the DJ or an Admin can change this!"))

    #     if value > 2:
    #         return await ctx.send(_("You can not set the pitch higher than 2.0x!"))
    #     if value < 0.4:
    #         return await ctx.send(_("You can not set the pitch lower than 0.4x!"))

    #     ctx.player.distortion = value
    #     # await ctx.player.set_timescale(speed=ctx.player.speed, pitch=ctx.player.pitch)
    #     embed = discord.Embed(color=ctx.embed_color)
    #     await ctx.player.node.websocket.send(op="filters", guildId=str(ctx.guild.id), )
    #     ctx.player.filter = None
    #     # await ctx.send(_("{0} | Applying setting...").format("<a:discord_loading:587812494089912340>"))
    #     # await asyncio.sleep(5.0)
    #     # await ctx.send(embed=embed, delete_after=15)
    #     if self.is_dj(ctx):
    #         embed.description = _("{0} | DJ {1} has set the pitch to {2}x !").format(ctx.emoji.settings, ctx.author.mention, str(pitch))
    #         return await ctx.send(embed=embed)
    #     elif self.is_admin(ctx):
    #         embed.description = _("{0} | Admin {1} has set the pitch to {2}x !").format(ctx.emoji.settings, ctx.author.mention, str(pitch))
    #         return await ctx.send(embed=embed)


def setup(bot):
    pass
