import discord
import random
import re

from discord.ext import commands
from core.commands import commandExtra
from utils.images import changePNGColor
from core import i18n
from db import BaseUrls
from core.cog import SubCog

HEX = re.compile(r'^(#|0x)[A-Fa-f0-9]{6}$')

class Colors(SubCog, category="Colors"):
    def __init__(self, bot):
        self.bot = bot

    @commandExtra(category="Colors", aliases=['randomcolour'])
    async def randomcolor(self, ctx):
        r = lambda: random.randint(0,255)
        color = f"{f'{r():x}':0>2}{f'{r():x}':0>2}{f'{r():x}':0>2}"

        embed=discord.Embed(color=discord.Color(int(f"0x{color}", 16)))

        embed.add_field(name="Hex", value=f"#{color}")

        img = changePNGColor("db/images/circle.png", "#FFFFFF", f"#{color}")

        lv = len(color)
        rgb_color = tuple(int(color[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        embed.add_field(name="RGB", value=rgb_color, inline=False)

        f = discord.File(img, filename="image.png")
        embed.set_thumbnail(url="attachment://image.png")
        info_cmd = f"{ctx.prefix}colorinfo #{color}"
        embed.set_footer(text=_("For more info on this color, type {0}").format(str(info_cmd)))

        await ctx.send(file=f, embed=embed)

    @commandExtra(category="Colors", aliases=['colourinfo'])
    async def colorinfo(self, ctx, color):
        if not HEX.match(color):
            return await ctx.send(_("That is not a valid HEX color! Please only use a `#******` or `0x******` HEX format!"))
        color = color.replace('0x', '#').strip('#')


        img = changePNGColor("db/images/normal-circle.png", "#FFFFFF", f"#{color}")

        embed=discord.Embed()

        async with self.bot.session.get(self.bot.get_url("colorapi") + color) as r:
            res = await r.json()

        hex = res['hex']['value']
        rgb = f"({res['rgb']['r']}, {res['rgb']['g']}, {res['rgb']['b']})"
        hsl = f"({res['hsl']['h']}, {res['hsl']['s']}%, {res['hsl']['l']}%)"
        hsv = f"({res['hsv']['h']}, {res['hsv']['s']}%, {res['hsv']['v']}%)"
        name = res['name']['value']
        cmyk = f"({res['cmyk']['c']}, {res['cmyk']['m']}, {res['cmyk']['y']}, {res['cmyk']['k']})"
        xyz = f"({res['XYZ']['X']}, {res['XYZ']['Y']}, {res['XYZ']['Z']})"

        f = discord.File(img, filename="image.png")
        embed.set_thumbnail(url="attachment://image.png")

        embed.title = name
        embed.color = discord.Color(int(f"0x{color}", 16))
        embed.add_field(name="Hex", value=hex)
        embed.add_field(name="rgb", value=rgb)
        embed.add_field(name="cmyk", value=cmyk)
        embed.add_field(name="hsv", value=hsv)
        embed.add_field(name="hsl", value=hsl)
        embed.add_field(name="XYZ", value=xyz)

        await ctx.send(embed=embed, file=f)

def setup(bot):
    pass
