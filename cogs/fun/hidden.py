import discord
import random
import asyncio
import sr_api

from discord.ext import commands, flags
from core.commands import flagsExtra, commandExtra
from core.cog import SubCog

class HiddenFun(SubCog, category="Funny"):
    def __init__(self, bot):
        self.bot = bot
        # with open('db/languages/en/roasts.json', 'r') as f:
        #     self.roasts = json.load(f)

    def get_roasts(self, ctx, level=None):
        custom = ctx.cache.custom_roasts
        if level is None:
            roastlevel = self.bot.cache.get("settings", ctx.guild.id, "roastlevel")
            if roastlevel == 0:
                return custom
            if roastlevel == 1:
                return custom + self.roasts["1"]
            elif roastlevel == 2:
                return custom + self.roasts["1"] + self.roasts["2"]
            elif roastlevel == 3:
                return custom + self.roasts["1"] + self.roasts["2"] + self.roasts["3"]
        else:
            if level == 0:
                return custom
            return self.roasts[str(level)]

    @flags.add_flag('user', nargs="*")
    @flags.add_flag('-l', '--level', type=int, default=None)
    @flags.add_flag('--bypass-ownerblock', action='store_true', default=False)
    @flagsExtra(category="Funny")
    async def roast(self, ctx, **flags):
        idkuser = " ".join(flags['user'])
        if idkuser:
            user = await commands.MemberConverter().convert(ctx, idkuser)
        else:
            user = ctx.author
        if user in [self.bot.owner, self.bot.user]:
            if flags.get('bypass_ownerblock') and ctx.message.content.lower().endswith('--bypass-ownerblock'):
                pass
            elif flags.get('bypass_ownerblock'):
                raise discord.ext.flags._parser.ArgumentParsingError('oops')
            else:
                return await ctx.send("Hmmmm, nope. Not gonna do that.")
        else:
            if flags.get('bypass_ownerblock'):
                raise discord.ext.flags._parser.ArgumentParsingError('oops')
        if flags.get('level', None) not in (None,0,1,2,3):
            return await ctx.send(_("There are only 3 levels of roasts. (and level 0 for custom roasts)"))
        else:
            if flags['level'] is not None:
                if flags['level'] > ctx.cache.roastlevel:
                    return await ctx.send(_("The guilds roast level has been set to {0}. You can not pick a roast from a higher level").format(str(ctx.cache.roastlevel)))
            roasts = self.get_roasts(ctx, flags['level'])
            if not roasts:
                return await ctx.send(_("This server has no custom roasts. You can submit roasts with the `{0}add-roast <roast>` command!").format(ctx.prefix))
            random.shuffle(roasts)
            roast = random.choice(roasts)
            clean_name = discord.utils.escape_markdown(user.display_name.replace("@", "@\u200b"))
            await ctx.send(_("**{0}**, {1}").format(clean_name, roast))

def setup(bot):
    pass