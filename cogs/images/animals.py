import discord

from discord.ext import commands
from core.commands import commandExtra
from core.cog import SubCog

class Animals(SubCog, category="Animals"):
    def __init__(self, bot):
        self.bot = bot

    @commandExtra()
    @commands.cooldown(rate=1, per=1.5, type=commands.BucketType.user)
    async def cat(self, ctx):
        r = await ctx.get('https://nekos.life/api/v2/img/meow')
        await ctx.send(embed=discord.Embed(color=ctx.embed_color).set_image(url=r['url']))

    @commandExtra()
    @commands.cooldown(rate=1, per=1.5, type=commands.BucketType.user)
    async def duck(self, ctx):
        r = await ctx.get('https://random-d.uk/api/v1/random')
        await ctx.send(embed=discord.Embed(color=ctx.embed_color).set_image(url=r['url']))

    @commandExtra()
    @commands.cooldown(rate=1, per=1.5, type=commands.BucketType.user)
    async def dog(self, ctx):
        r = await ctx.get('https://random.dog/woof.json')

        if r['url'].endswith(".mp4"):
            return await ctx.send(r['url'])
        await ctx.send(embed=discord.Embed(color=ctx.embed_color).set_image(url=r['url']))

    @commandExtra()
    @commands.cooldown(rate=1, per=1.5, type=commands.BucketType.user)
    async def fox(self, ctx):
        res = await ctx.get('https://some-random-api.ml/img/fox')
        await ctx.send(embed=discord.Embed(color=ctx.embed_color).set_image(url=res['link']))

def setup(bot):
    pass