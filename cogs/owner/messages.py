import discord
from core.cog import SubCog
from core.commands import commandExtra
from discord.ext import commands
from utils import checks


class Messages(SubCog, category="Messages"):
    def __init__(self, bot):
        self.bot = bot

    @checks.is_owner()
    @commandExtra(category="Messages")
    async def msg(self, ctx, channel: discord.TextChannel, *, message: str):
        try:
            await channel.send(message)
        except Exception as e:
            await ctx.send(e)
        await ctx.message.delete()

    @checks.is_owner()
    @commandExtra(aliases=['edit'], category="Messages")
    @commands.guild_only()
    async def editmessage(self, ctx, msg: discord.Message, *, newmsg: str):
        if msg.author != self.bot.user:
            return await ctx.send("That message was not sent by me")
        await msg.edit(content=newmsg)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

    @checks.is_owner()
    @commandExtra(category="Messages")
    async def dm(self, ctx, uid: int, *, msg: str):
        try:
            user_id = list(self.bot.cache.dms.keys())[list(self.bot.cache.dms.values()).index(uid)]
            cache = True
        except ValueError:
            user_id = uid
            cache = False
        user = self.bot.get_user(user_id)
        if user is None:
            await ctx.send(f"User `{user_id}` not found...", delete_after=5)
            try:
                await ctx.message.delete()
            except:
                pass
            return

        try:
            await user.send(msg)

            logchannel = self.bot.get_channel(520042138264797185)
            logembed = discord.Embed(title=str(user) + (f' | ID: {uid}' if cache else ' | ID: Unknown'), description=msg, color=0x63cf9b)
            logembed.set_thumbnail(url=user.avatar.with_format("png"))
            await logchannel.send(embed=logembed)

        except discord.Forbidden:
            await ctx.author.send("Sorry bro, I can't send messages to that person...")

        finally:
            try:
                await ctx.message.delete()
            except:
                pass

    @checks.is_owner()
    @commandExtra(category="Messages")
    async def delmsg(self, ctx, message: str = None):
        if not message:
            if not ctx.message.reference:
                return
            msg = ctx.message.reference.resolved
        else:
            msg = await commands.MessageConverter().convert(ctx, message)
        if msg.author != ctx.me:
            return await ctx.send("Not my message...", delete_after=3)
        else:
            await msg.delete()
            try:
                await ctx.message.delete()
            except:
                await ctx.message.add_reaction(ctx.emoji.check)


def setup(bot):
    pass
