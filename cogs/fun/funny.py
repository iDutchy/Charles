import discord
import asyncio
import random

from discord.ext import commands, flags
from core.commands import commandExtra, flagsExtra
from core import i18n
from utils.progressbar import create as make_pb
from db import BaseUrls, actions
from core.cog import SubCog

class Funny(SubCog, category="Funny"):
    def __init__(self, bot):
        self.bot = bot

    @commandExtra()
    async def meme(self, ctx):
        x = random.choice(["meme", "memes"])
        r = await ctx.get(self.bot.get_url('reddit').format(x))

        data = r[0]['data']['children'][0]['data']
        e = discord.Embed(color=ctx.embed_color, title=f"/r/{x}", description=data['title'])
        e.set_image(url=data['url'])
        await ctx.send(embed=e)

    @commandExtra()
    async def dadjoke(self, ctx):
        res = await ctx.get(self.bot.get_url('dadjoke'), headers={"Accept": "application/json"})
        await ctx.send(res['joke'])

    @commandExtra()
    @commands.max_concurrency(number=1, per=commands.BucketType.guild, wait=False)
    async def hack(self, ctx, *, user: discord.User):
        msg = await ctx.send("<a:Smooth_Loading:470313388782911489> | " + _("Hacking {0}'s IP-Address...").format(user.display_name))
        await asyncio.sleep(3)
        newmsg = "<:tick:528774982067814441> | " + _("Found {0}'s IP-Address!").format(user.display_name)
        await msg.edit(content=newmsg)
        await asyncio.sleep(1)
        await msg.edit(content=newmsg + "\n<a:Smooth_Loading:470313388782911489> | " + _("Locating {0}... ").format(user.display_name))
        await asyncio.sleep(3)
        newmsg += "\n<:tick:528774982067814441> | " + _("Found {0}'s location!").format(user.display_name)
        await msg.edit(content=newmsg)
        await asyncio.sleep(1)
        await msg.edit(content=newmsg + "\n<a:Smooth_Loading:470313388782911489> | " + _("Scanning through {0}'s files...").format(user.display_name))
        await asyncio.sleep(3)
        newmsg += "\n<:tick:528774982067814441> | " + _("Scanned all of {0}'s files!").format(user.display_name)
        await msg.edit(content=newmsg)
        await asyncio.sleep(1)
        await msg.edit(content=newmsg + "\n<a:Smooth_Loading:470313388782911489> | "  + _("Searching for useful information... "))
        await asyncio.sleep(3)
        newmsg += "\n<:tick:528774982067814441> | " + _("Completed!")
        await msg.edit(content=newmsg)
        await asyncio.sleep(1)
        await msg.edit(content=newmsg + "\n<a:Smooth_Loading:470313388782911489> | " + _("Loading search result..."))

        imgs = []

        for channel in ctx.guild.text_channels:
            if channel.permissions_for(ctx.guild.me).read_messages is False:
                continue
            if channel.overwrites_for(ctx.guild.default_role).read_messages is False:
                continue
            if channel.is_nsfw():
                continue
            async for message in channel.history(limit=500):
                if message.attachments and message.author == user:
                    if str(message.attachments[0].url).endswith(".mp4"):
                        continue
                    imgs.append(message.attachments[0].url)

        if len(imgs) == 0:
            imgs = actions.hack

        newmsg += "\n\n" + _("Here's what I found:")
        await msg.edit(content=newmsg)

        hackimg = random.choice(imgs)

        embed=discord.Embed(color=ctx.embed_color)
        embed.set_image(url=hackimg)
        await msg.edit(content=newmsg, embed=embed)

    @commandExtra()
    async def shoot(self, ctx, *, member: discord.User):
        if member == self.bot.user:
            gif = random.choice(actions.shoot_bot)
            message = _("Nice try, {0}, but I am immune to bullets!").format(ctx.author.name)

        elif member == ctx.author:
            gif = random.choice(actions.shoot_self)
            message = _("{0} looked into the barrel and shot themselves...").format(ctx.author.name)

        else:
            gif = random.choice(actions.shoot_user)
            message = _("{0} shot {1}! **Bullseye**").format(ctx.author.name, member.name)

        e=discord.Embed(color=ctx.embed_color, title=message)
        e.set_image(url=gif)
        await ctx.send(embed=e)

    @commandExtra()
    async def stab(self, ctx, *, member: discord.User):
        if member == self.bot.user:
            gif = random.choice(actions.stab_bot)
            message = _("Nice try, {0}, but a blade won't work on me!").format(ctx.author.name)

        elif member == ctx.author:
            gif = random.choice(actions.stab_self)
            message = _("{0} held their blade the wrong way and stabbed their selves...").format(ctx.author.name)

        else:
            gif = random.choice(actions.stab_user)
            message = _("{0} stabbed {1} to death!").format(ctx.author.name, member.name)

        e=discord.Embed(color=ctx.embed_color, title=message)
        e.set_image(url=gif)
        await ctx.send(embed=e)

    @commandExtra()
    async def punch(self, ctx, *, member: discord.User):
        if member == self.bot.user:
            gif = random.choice(actions.punch_bot)
            message = _("Nice try, {0}, but you can't hit me!").format(ctx.author.name)

        elif member == ctx.author:
            gif = random.choice(actions.punch_self)
            message = _("{0} attempted to facepalm, but punched their selves in stead...").format(ctx.author.name)

        else:
            gif = random.choice(actions.punch_user)
            message = _("{0} punched {1}! **A critical hit!**").format(ctx.author.name, member.name)

        e=discord.Embed(color=ctx.embed_color, title=message)
        e.set_image(url=gif)
        await ctx.send(embed=e)

    @commandExtra()
    async def reverse(self, ctx, *, text: commands.clean_content):
        await ctx.send(text[::-1], allowed_mentions=discord.AllowedMentions.none())

    @commandExtra(aliases=['howhot', 'hot'])
    async def hotcalc(self, ctx, *, user: discord.Member = None):
        user = user or ctx.author

        if user.id == self.bot.owner_id:
            return await ctx.send(_("Nice try, he's my owner... I'm not gay, but he's definitely **100%** hot!!") +  " \U0001f49e")

        if user == self.bot.user:
            return await ctx.send(_("Me? You want me to rate myself? Any clue how hard that is?! How about you rate me? Or do you think you're too good for that huh?"))

        rnd = random.Random(user.id//2)
        hot_ = rnd.randint(1, 100)
        hot_dec = rnd.randint(0, 10)
        hot = f"{hot_}.{hot_dec}" if hot_ != 100 else hot_

        total_hot = int(10/100*hot_)
        total_not = 10-total_hot
        emojis = '\U0001f525'*total_hot + '\U0001f538'*total_not

        await ctx.send(_("**{0}** is **{1}%** hot!\n`{2}`").format(user.name, str(hot), emojis))

    @commandExtra()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ship(self, ctx, user1: discord.Member, *, user2: discord.Member = None):
        user2 = user2 or ctx.author

        self_length = len(user1.display_name)
        first_length = round(self_length / 2)
        first_half = user1.display_name[0:first_length]
        usr_length = len(user2.display_name)
        second_length = round(usr_length / 2)
        second_half = user2.display_name[second_length:]
        finalName = first_half + second_half

        rng = random.Random((user1.id + user2.id) //2)
        score = rng.randint(0, 100)
        pb = make_pb(100, 10, score)

        em = discord.Embed(color=ctx.embed_color)
        em.title = f"{user1.display_name} + {user2.display_name} = {finalName} ❤"
        em.description = f"**{score}%** "+ _("Love") +"\n" + pb

        await ctx.send(embed=em)

    @commandExtra(aliases=["dick", "penis", "pp"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def dong(self, ctx, *, user: discord.Member=None):
        user = user or ctx.author

        if user.id in [self.bot.user.id, 171539705043615744]: # self.bot.owner_id
            return await ctx.send(_("Output too long..."))

        rng = random.Random(user.id//2)
        dong = '8{}D'.format('=' * rng.randint(0, 30))
        em = discord.Embed(title=_("{0}'s Dong Size").format(user), description=dong, colour=ctx.embed_color)
        await ctx.send(embed=em)

def setup(bot):
    pass
