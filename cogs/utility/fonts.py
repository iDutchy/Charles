import random

import discord
from core.cog import SubCog
from core.commands import commandExtra
from utils.converters import FontConverter


class Fonts(SubCog, category="Fonts"):
    def __init__(self, bot):
        self.bot = bot

    @commandExtra(category="Fonts")
    async def mock(self, ctx, *, text):
        await ctx.send("<:SpongebobMock:741345787593621504>: " + "".join(random.choice([c.upper(), c.lower()]) for c in text)[:1963], allowed_mentions=discord.AllowedMentions.none())

    @commandExtra(category="Fonts")
    async def clap(self, ctx, *, text):
        await ctx.send(f"👏{text.replace(' ', '👏')}👏", allowed_mentions=discord.AllowedMentions.none())

    @commandExtra(category="Fonts")
    async def fraktur(self, ctx, *, sentence: FontConverter):
        await ctx.send(sentence)

    @commandExtra(category="Fonts", aliases=['ae'])
    async def aesthetic(self, ctx, *, sentence: FontConverter):
        await ctx.send(sentence)

    @commandExtra(category="Fonts")
    async def boldfaktur(self, ctx, *, sentence: FontConverter):
        await ctx.send(sentence)

    @commandExtra(category="Fonts", aliases=['ff'])
    async def fancy(self, ctx, *, sentence: FontConverter):
        await ctx.send(sentence)

    @commandExtra(category="Fonts", aliases=['bf'])
    async def boldfancy(self, ctx, *, sentence: FontConverter):
        await ctx.send(sentence)

    @commandExtra(category="Fonts")
    async def double(self, ctx, *, sentence: FontConverter):
        await ctx.send(sentence)

    @commandExtra(category="Fonts", aliases=['sc'])
    async def smallcaps(self, ctx, *, sentence: FontConverter):
        await ctx.send(sentence)


def setup(bot):
    pass
