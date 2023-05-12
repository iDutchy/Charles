import discord

from discord.ext import commands
from core.commands import commandExtra

from core.cog import SubCog

class Hidden(SubCog, category="Hidden"):
    def __init__(self, bot):
        self.bot = bot

    @commandExtra(hidden=True)
    async def rainbowline(self, ctx):
        e=discord.Embed(color=0x36393E)
        e.set_image(url="https://cdn.discordapp.com/attachments/537583728948674580/538691432719056926/1273.gif")
        await ctx.send(embed=e)

    @commandExtra(name="fuck-up", hidden=True)
    async def fuck_up(self, ctx):
        await ctx.send(f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.channel.id}")

def setup(bot):
    pass