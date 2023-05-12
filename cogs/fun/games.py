import asyncio
import os
import random
import time
from collections import defaultdict
from datetime import datetime
from functools import partial

import discord
import numpy
from core import i18n
from core.cog import SubCog
from core.commands import commandExtra, groupExtra
from discord.ext import commands
from utils.images import pokemon_bw, pokemon_col
from discord.ui import View, Button


class Games(SubCog, category="Games"):
    def __init__(self, bot):
        self.bot = bot

    @commandExtra()
    async def rps(self, ctx):
        rock, paper, scissors = choices = ("\U0001faa8", "\U0001f4f0", "\U00002702")
        beats = {rock: scissors, scissors: paper, paper: rock}
        bot = random.choice(choices)
        msg = await ctx.send(_("Alright, lets see if you can beat me!"))
        for e in ("\U0001faa8", "\U0001f4f0", "\U00002702"):
            await msg.add_reaction(e)
        try:
            r, u = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id and u.id == ctx.author.id and str(r) in choices, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send(_("You took to long to respond..."))
        if str(r) == bot:
            await msg.edit(content=_("Oh no, we both picked the same..."))
        elif beats[str(r)] == bot:
            await msg.edit(content=_("NOO, you won! I'll get you next time.."))
        else:
            await msg.edit(content=_("Haha, yes! I win! Better luck next time."))

    @commandExtra(category="Games")
    async def gta(self, ctx):
        data = await ctx.get(self.bot.get_url('anime'))
        char = data['data'][0]['character']
        quote = data['data'][0]['quote']
        anime = data['data'][0]['anime']
        await ctx.send(embed=discord.Embed(title=_("Guess the anime!"), description=f"**{char} >>** {quote}").set_footer(text=_("Answer will show in 20s")), edit=False)
        await asyncio.sleep(20)
        await ctx.send(embed=discord.Embed(title=_("Answer:"), description=anime),edit=False)

    async def command_moved(self, ctx):
        e = discord.Embed(title="Command moved",
                          description="Since Charles is no longer being maintained in favor of the new bot, this command has been removed from Charles.\n\nDon't worry about your leaderboard status, this has all been transferred to the new bot!\n\nThe new bot is a game bot, with several games to play in discord and many more gaming related features (including this command, but improved!). If you'd like to try it out, you can invite My Games by clicking the button below. (prefix is `g/` and beta version prefix is `beta/`)")
        v = View()
        v.add_item(Button(url="https://discord.com/oauth2/authorize?client_id=747984555352260750&scope=bot+applications.commands&permissions=388160",
                          emoji="<:mygames:907424181476552724>",
                          label="Invite My Games"))
        return await ctx.send(embed=e, view=v)

    @commands.max_concurrency(number=1, per=commands.BucketType.user, wait=False)
    @groupExtra(category="Games", invoke_without_command=True)
    async def wtp(self, ctx):
        await self.command_moved(ctx)

    @wtp.command(name="leaderboard", aliases=['lb'])
    async def wtp_lb(self, ctx):
        await self.command_moved(ctx)

    @wtp.command(name="global-leaderboard", aliases=['lbg', 'glb', 'global-lb'])
    async def wtp_lbg(self, ctx):
        await self.command_moved(ctx)

    @groupExtra(name="10s", category="Games", invoke_without_command=True)
    @commands.max_concurrency(number=1, per=commands.BucketType.user, wait=False)
    async def ten_sec(self, ctx):
        await self.command_moved(ctx)

    @ten_sec.command(name='leaderboard', aliases=['lb'])
    async def ten_sec_lb(self, ctx):
        await self.command_moved(ctx)

    @ten_sec.command(name="global-leaderboard", aliases=['lbg', 'glb', 'global-lb'])
    async def ten_sec_lbg(self, ctx):
        await self.command_moved(ctx)

def setup(bot):
    pass
