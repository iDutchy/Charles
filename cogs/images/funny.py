import json
import mimetypes
import random
from io import BytesIO

import aiohttp
import discord
import sr_api
from core import i18n
from core.cog import SubCog
from core.commands import commandExtra
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from utils.converters import ImageConverter, executor


class Funny(SubCog, category="Funny"):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def better_is_image(bytesobj):
        try:
            discord.utils._get_mime_type_for_image(bytesobj)
        except:
            return False
        else:
            return True

    @staticmethod
    def is_image(url):
        mimetype, encoding = mimetypes.guess_type(url.replace('?size=1024', ''))
        return mimetype and mimetype.startswith('image')

    @executor
    def _ytkids(self, im, message):
        draw = ImageDraw.Draw(im)
        font = ImageFont.truetype('db/fonts/roboto.ttf', size=25)
        (x, y) = (30, 430)
        color = 'rgb(255, 255, 255)'
        draw.text((x, y), message, fill=color, font=font)

        return im

    @executor
    def _captcha(self, img, img2, ava, text):
        ava = ava.resize((483, 483), Image.ANTIALIAS).convert("RGB")
        img.paste(ava, (10, 157))
        img.paste(img2, mask=img2)

        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype('db/fonts/roboto.ttf', size=27)
        color = 'rgb(255, 255, 255)'
        draw.text((35, 70), text, fill=color, font=font)
        return img

    def has_transparency(self, img):
        if img.mode == "P":
            transparent = img.info.get("transparency", -1)
            for x, index in img.getcolors():
                if index == transparent:
                    return True
        elif img.mode == "RGBA":
            extrema = img.getextrema()
            if extrema[3][0] < 255:
                return True

        return False

    @executor
    def make_fight(self, bg, mask, winner, loser):
        size = (512, 512)
        mask = Image.new('RGBA', size)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0)+size, fill=(255, 255, 255, 255))

        mask2 = mask.copy()

        winner = winner.resize(size, Image.ANTIALIAS)
        loser = loser.resize(size, Image.ANTIALIAS)
        mask = mask.resize(size, Image.ANTIALIAS)
        mask2 = mask2.resize(size, Image.ANTIALIAS)

        mask.paste(winner, mask=mask)
        mask2.paste(loser, mask=mask2)

        mask = mask.resize((75, 75), Image.ANTIALIAS)
        mask2 = mask2.resize((75, 75), Image.ANTIALIAS)

        winner = winner.resize((75, 75), Image.ANTIALIAS)
        bg.paste(winner, (510, 25), mask=mask)

        loser = loser.resize((75, 75), Image.ANTIALIAS)
        bg.paste(loser, (160, 10), mask=mask2)

        return bg

    @commandExtra()
    async def http(self, ctx, statuscode: int):
        cat = BytesIO(await ctx.get(f"https://http.cat/{statuscode}.jpg", return_type="read"))
        f = discord.File(cat, f"{statuscode}.png")
        await ctx.send(file=f)

    @commandExtra()
    async def amongus(self, ctx, *, user: discord.User = None):
        async with ctx.typing():
            user = user or ctx.author
            c = sr_api.Client(self.bot.get_token("SRA"))
            r = c.amongus(user.display_name, user.avatar.url)
            b = BytesIO(await r.read())
            await ctx.send(file=discord.File(b, filename=f"{user.display_name}Impostor.gif"))
            await c.close()

    @commandExtra()
    async def ko(self, ctx, user1: discord.Member, *, user2: discord.Member = None):
        user2 = user2 or ctx.author

        win = random.choice([user1, user2])
        if win == user1:
            lose = user2
        else:
            lose = user1

        bg = Image.open('db/images/punch.png')
        mask = Image.open('db/images/circle-mask.jpg').convert("RGBA")

        winner = Image.open(BytesIO(await win.avatar.with_format("png", size=512).read())).convert("RGBA")
        loser = Image.open(BytesIO(await lose.avatar.with_format("png", size=512).read())).convert("RGBA")

        img = await self.make_fight(bg, mask, winner, loser)

        file = BytesIO()
        img.save(file, 'png')
        file.seek(0)
        img.close()
        f = discord.File(fp=file, filename='Punch.png')
        await ctx.send(embed=discord.Embed(color=ctx.embed_color, description=_("{0} has knocked out {1}!").format(win.mention, lose.mention)).set_image(url="attachment://Punch.png"), file=f)

    @commandExtra()
    async def captcha(self, ctx, url: ImageConverter, *, text: str):
        if len(text) > 30:
            return await ctx.send(_("Captcha text must not be longer than 30 characters!"))
        if not self.is_image(url):
            url = str(ctx.author.avatar.with_format("png"))

        with open('db/images/captcha.png', 'rb') as f:
            img = Image.open(BytesIO(f.read()))

        with open('db/images/captcha.png', 'rb') as f:
            img2 = Image.open(BytesIO(f.read()))

        f = await ctx.get(url, return_type="read")
        ava = Image.open(BytesIO(f))

        img = await self._captcha(img, img2, ava, text)

        buf = BytesIO()
        img.save(buf, 'png')
        buf.seek(0)
        img.close()
        f = discord.File(fp=buf, filename='captcha.png')
        await ctx.send(file=f, edit=False)

    @commandExtra()
    async def birthcontrol(self, ctx, *, url: ImageConverter = ""):
        if not self.is_image(url):
            if len(ctx.message.attachments) > 0:
                url = ctx.message.attachments[0].url
            else:
                url = str(ctx.author.avatar.url)

        with open('db/images/birthcontrol.png', 'rb') as f:
            bg = Image.open(BytesIO(f.read())).convert("RGBA")

        f = await ctx.get(url, return_type="read")
        img = Image.open(BytesIO(f))

        img.thumbnail((180, 180))

        try:
            bg.paste(img, (440, 214), img)
        except ValueError:
            bg.paste(img, (440, 214))

        buf = BytesIO()
        bg.save(buf, "png")
        buf.seek(0)

        await ctx.send(file=discord.File(buf, "birthcontrol.png"))

    @commandExtra()
    async def ytkids(self, ctx, *, message):
        if len(message) > 40:
            message = message[:37] + "..."

        with open('db/images/yt_kids.png', 'rb') as f:
            im = Image.open(BytesIO(f.read())).convert("RGBA")

        img = await self._ytkids(im, message)

        buffer = BytesIO()
        img.save(buffer, 'png')
        buffer.seek(0)

        f = discord.File(fp=buffer, filename='ytkids.png')
        await ctx.send(embed=discord.Embed(color=ctx.embed_color).set_image(url="attachment://ytkids.png"), file=f)
        img.close()

    @commandExtra()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def caption(self, ctx, *, img: ImageConverter = ""):
        if not self.is_image(img):
            if len(ctx.message.attachments) > 0:
                img = ctx.message.attachments[0].url
            else:
                img = ctx.author.avatar.url
        async with ctx.typing():
            headers = {
                "Content-Type": "application/json; charset=utf-8"
            }
            payload = {
                "Content": img,
                "Type": "CaptionRequest"
            }
            url = self.bot.get_url('captionbot')
            try:
                async with self.bot.session.post(url, headers=headers, data=json.dumps(payload)) as r:
                    data = await r.text()
            except aiohttp.client_exceptions.ClientConnectorError:
                return await ctx.send(_("Network is unreachable, please try again later!"))

            em = discord.Embed(color=ctx.embed_color, title=data)
            if data != '"I think this may be inappropriate content so I won\'t show it "':
                em.set_image(url=img)
            # lang_code = self.bot.cache.get("settings", ctx.guild.id, "language").lower()
            # if lang_code != "en":
            #     data = '"'+(await self.bot.utils.translate(str(data).strip('"'), dest=lang_code)).text + '"'
            await ctx.send(embed=em)

    @commandExtra()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def tweet(self, ctx, username: str, *, text: str):
        res = await ctx.get(self.bot.get_url('neko') + f"imagegen?type=tweet&username={username}&text={text}")

        embed = discord.Embed(color=ctx.embed_color)
        embed.set_image(url=res["message"])
        await ctx.send(embed=embed)

    @commandExtra()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def clyde(self, ctx, *, text: str):
        if len(text) > 75:
            return await ctx.send(_("Clyde's message cannot be longer than 75 characters!"))
        res = await ctx.get(self.bot.get_url('neko') + f"imagegen?type=clyde&text={text}")

        embed = discord.Embed(color=ctx.embed_color)
        embed.set_image(url=res["message"])
        await ctx.send(embed=embed)

    @commandExtra()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def deepfry(self, ctx, *, img: ImageConverter = ""):
        if not self.is_image(img):
            if len(ctx.message.attachments) > 0:
                img = ctx.message.attachments[0].url
            else:
                img = str(ctx.author.avatar.url)

        res = await ctx.get(self.bot.get_url('neko') + f"imagegen?type=deepfry&image={img}")

        embed = discord.Embed(color=ctx.embed_color)
        embed.set_image(url=res["message"])
        await ctx.send(embed=embed)

    @commandExtra()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def magik(self, ctx, img: ImageConverter = "", intensity: int = 5):
        async with ctx.loading(_("Generating image")):
            if not self.is_image(img):
                if len(ctx.message.attachments) > 0:
                    img = ctx.message.attachments[0].url
                else:
                    img = str(ctx.author.avatar.url)

            url = self.bot.get_url("dagpi")
            res = await ctx.get(f"{url}image/magik/?url={img}&scale={intensity}", headers={"Authorization": self.bot.get_token("DAGPI")}, return_type="io")
            embed = discord.Embed(color=ctx.embed_color)
            if 'gif' in img:
                embed.set_image(url="attachment://magik.gif")
                img = discord.File(res, "magik.gif")
            else:
                embed.set_image(url="attachment://magik.png")
                img = discord.File(res, "magik.png")
            await ctx.send(embed=embed, file=img)

    @commandExtra()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def threats(self, ctx, *, img: ImageConverter = ""):
        if not self.is_image(img):
            if len(ctx.message.attachments) > 0:
                img = ctx.message.attachments[0].url
            else:
                img = str(ctx.author.avatar.url)

        res = await ctx.get(self.bot.get_url('neko') + f"imagegen?type=threats&url={img}")

        embed = discord.Embed(color=ctx.embed_color)
        embed.set_image(url=res["message"])
        await ctx.send(embed=embed)


def setup(bot):
    pass
