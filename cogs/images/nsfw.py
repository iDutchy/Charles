import discord

from discord.ext import commands

from core.commands import commandExtra
from core import i18n

from core.cog import SubCog

class NSFW(SubCog, category="Nsfw"):
    def __init__(self, bot):
        self.bot = bot

    @commandExtra() 
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.is_nsfw()
    async def phcomment(self, ctx, *, comment: commands.clean_content(fix_channel_mentions=True, use_nicknames=True, escape_markdown=True)):
        if len(comment) > 65:
            return await ctx.send(_("Comment cannot be longer than 65 characters!"))
        comment = comment.replace("&", "%26")
        res = await ctx.get(self.bot.get_url('neko') + "imagegen?type=phcomment"
                          f"&image={ctx.author.avatar.with_format('png')}"
                          f"&text={comment}&username={ctx.author.name}")
        if not res["success"]:
            return await ctx.send(_("Failed to get image."))
        embed = discord.Embed(color=ctx.embed_color)
        embed.set_image(url=res["message"])
        await ctx.send(embed=embed)

def setup(bot):
    pass