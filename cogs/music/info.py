import asyncio

import discord
from core import i18n
from core.cog import SubCog
from core.commands import commandExtra
from discord.ext import commands
from utils.paginator import EmbedPages


class MusicInfo(SubCog, category="Player Information"):
    def __init__(self, bot):
        self.bot = bot

    # @music_check(no_channel=True, bot_no_channel=True, same_channel=True, not_playing=True)
    @commandExtra(name='nowplaying', aliases=['np', 'current', 'currentsong'], category="Player Information")
    async def now_playing(self, ctx):
        if not ctx.player.current or not ctx.player.is_playing:
            return await ctx.send(embed=discord.Embed(colour=ctx.embed_color,
                                  title=_("{0} | No song is currently playing!").format(ctx.emoji.queue)), delete_after=15)
        controller_msg = await ctx.send(embed=ctx.player.main_page)

        for reaction in self.controls:
            await controller_msg.add_reaction(str(reaction))

        def check(r, u):
            return u.id == ctx.author.id and r.message.id == controller_msg.id

        while controller_msg:

            try:
                react, user = await self.bot.wait_for('reaction_add', check=check, timeout=60)
                control = self.controls.get(getattr(ctx.emoji, react.emoji.name))
            except asyncio.TimeoutError:
                try:
                    await controller_msg.delete()
                except:
                    return
                return

            try:
                await controller_msg.remove_reaction(react, user)
            except discord.Forbidden:
                pass

            if control == 'Main_Page':
                await controller_msg.edit(embed=ctx.player.main_page)
            if control == 'Song_Info_Page':
                await controller_msg.edit(embed=discord.Embed(color=ctx.embed_color,
                                                              description=_("Loading song information...") + " <a:discord_loading:587812494089912340>"))
                await controller_msg.edit(embed=await ctx.player.song_info_page())
            if control == 'Info_Page':
                await controller_msg.edit(embed=ctx.player.info_page)
            if control == 'Delete_Page':
                await controller_msg.delete()
            if control == 'Download_Song':
                if ctx.player.current.length > 300000:
                    await controller_msg.edit(embed=discord.Embed(color=ctx.embed_color, description=_("Sorry, I can't download songs longer than 5 minutes...")))

                else:
                    check, msg = await ctx.confirm(_("This will download an mp3 of this song, are you sure you wish to continue?"), edit=False)

                    if check:
                        await msg.delete()
                        await controller_msg.edit(embed=discord.Embed(color=ctx.embed_color, description=_("Downloading your mp3 file...") + " <a:discord_loading:587812494089912340>\n" + _("Please be patient, this may take a while... Bigger songs take longer to download! :)")))
                        await controller_msg.edit(embed=await ctx.player.download_song())
                    if not check:
                        await msg.delete()
                        await controller_msg.edit(embed=discord.Embed(color=ctx.embed_color, description=_("Cancelled mp3 download.")))
            if control == 'Lyric_Page':
                await controller_msg.edit(embed=discord.Embed(color=ctx.embed_color, description=_("Searching for lyrics...") + " <a:discord_loading:587812494089912340>"))
                try:
                    await controller_msg.edit(embed=await ctx.player.lyrics_page())
                except AttributeError:
                    await controller_msg.edit(embed=discord.Embed(color=ctx.embed_color, description=_("I was unable to find lyrics for this song.")))

    # @music_check(no_channel=True, bot_no_channel=True, same_channel=True, not_playing=True)
    @commandExtra(name='queue', aliases=['q', 'que'], category="Player Information")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def _queue(self, ctx):
        upcoming = list(ctx.player.entries)
        if not upcoming:
            return await ctx.send(embed=discord.Embed(colour=ctx.embed_color,
                                  title=_("{0} | No more songs in queue!").format(ctx.emoji.queue)), delete_after=15)

        queue_list = []
        for track in upcoming:
            queue_list.append(f'[**{track.title}**]({track.uri})')

        # description=_("{0} tracks").format(len(upcoming)) + f'\n\n{queue_list}')
        # embed.set_footer(text=_("Viewing page {0}/{1}").format(page, pages))

        paginator = EmbedPages(ctx,
                          title=_("{0} | Player Queue").format(ctx.emoji.queue),
                          entries=queue_list,
                          per_page=10,
                          show_entry_count=True)

        await paginator.start()


def setup(bot):
    pass
