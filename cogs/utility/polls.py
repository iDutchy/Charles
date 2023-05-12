import discord
import shlex

from discord.ext import commands
from core import i18n
from db import BaseUrls
from core.commands import commandExtra
from core.cog import SubCog

def to_keycap(c):
    return '\N{KEYCAP TEN}' if c == 10 else str(c) + '\ufe0f' + '\u20e3'

class Polls(SubCog, category="Polls"):
    def __init__(self, bot):
        self.bot = bot

    def remove_empty_entries(self, thelist):
        return list(filter(lambda x: x != "" and x != " ", thelist))

    @commandExtra(category="Polls")
    async def strawpoll(self, ctx, *, question_and_choices: str):
        if "|" in question_and_choices:
            delimiter = "|"
        else:
            delimiter = ","
        question_and_choices = self.remove_empty_entries(question_and_choices.split(delimiter))
        if len(question_and_choices) <= 2: 
            return await ctx.send(_("Not enough choices supplied"))
        elif len(question_and_choices) >= 31:
            return await ctx.send(_("Too many choices"))
        question, *choices = question_and_choices
        choices = [x.lstrip() for x in choices]
        header = {"Content-Type": "application/json"}
        payload = {
            "title": question,
            "options": choices,
            "multi": False
        }
        async with self.bot.session.post(BaseUrls.strawpoll, headers=header, json=payload) as r:
            data = await r.json()

        if not 'id' in data:
            return await ctx.send(_("Strawpoll returned an error. Please try again later!"))

        link = "http://www.strawpoll.me/" + str(data["id"])

        embed=discord.Embed(color=ctx.embed_color, title=question, description=_("**Vote here:** {0}").format(link))
        embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/562784997962940476/611338971468923113/20190815_012238.png", text=_("Powered by Strawpoll"))
        await ctx.send(embed=embed)

    @commandExtra(category="Polls")
    async def poll(self, ctx, *, question_and_choices: str):
        question_and_choices = question_and_choices.strip()
        if "|" in question_and_choices:
            delimiter = "|"
        elif "," in question_and_choices:
            delimiter = ","
        else:
            delimiter = None
        if delimiter is not None:
            question_and_choices = self.remove_empty_entries(question_and_choices.split(delimiter))
        else:
            question_and_choices = self.remove_empty_entries(shlex.split(question_and_choices))

        if len(question_and_choices) < 3:
            return await ctx.send(_("Need at least 1 question with 2 choices."))
        elif len(question_and_choices) > 11:
            return await ctx.send(_("You can only have up to 10 choices."))

        question = question_and_choices[0]
        choices = []
        for e, v in enumerate(question_and_choices[1:], 1):
            choices.append(f"`{e}.` {v}")
        reactions = []
        for e, v in enumerate(question_and_choices[1:], 1):
            reactions.append(to_keycap(e))

        try:
            await ctx.message.delete()
        except:
            pass

        answer = '\n'.join(choices)

        embed = discord.Embed(color=ctx.embed_color, title=question.replace("@", "@\u200b"), description=answer.replace("@", "@\u200b"))
        embed.set_author(icon_url=ctx.author.avatar.url, name=_("Poll by: {0}").format(ctx.author)) 
        poll = await ctx.send(embed=embed)
        for emoji in reactions:
            await poll.add_reaction(emoji)

    @commandExtra(category="Polls", aliases=['yn'])
    async def yesno(self, ctx, *, question):
        roles = everyone = False
        if rm := ctx.message.role_mentions:
            for role in rm:
                if rm.mentionable:
                    roles = True
        if ctx.author.guild_permissions.mention_everyone:
            roles = everyone = True
        m = await ctx.send(question, allowed_mentions=discord.AllowedMentions(roles=roles, everyone=everyone))
        await m.add_reaction(ctx.emoji.check)
        await m.add_reaction(ctx.emoji.xmark)

    @commandExtra(category="Polls", aliases=['ynm', 'ymn'])
    async def yesnomaybe(self, ctx, *, question):
        roles = everyone = False
        if rm := ctx.message.role_mentions:
            for role in rm:
                if rm.mentionable:
                    roles = True
        if ctx.author.guild_permissions.mention_everyone:
            roles = everyone = True
        m = await ctx.send(question, allowed_mentions=discord.AllowedMentions(roles=roles, everyone=everyone))
        await m.add_reaction(ctx.emoji.check)
        await m.add_reaction(ctx.emoji.neutral)
        await m.add_reaction(ctx.emoji.xmark)

def setup(bot):
    pass
