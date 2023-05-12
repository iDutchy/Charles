import discord
from core import emoji, i18n
from core.cog import SubCog
from core.commands import commandExtra
from db import langs
from discord.ext import commands
from utils.humanize_time import date, timesince
from utils.utility import Acknowledgements


# class UserInfo(commands.Cog, name="Info"):
class UserInfo(SubCog, category="Member Info"):
    def __init__(self, bot):
        self.bot = bot

    def get_socials(self, user):
        socials = []
        for stype, social in user.socials.get_all():
            socials.append(f"{emoji.socials[stype]} **{stype.title()}** - `{social}`")
        return socials

    def get_acknowledgements(self, user):
        tr = {
            "event_winner": "<:trophy:642177400565792798> " + _("Event Winner"),
            "bug_hunter": "<:bughunter:633796873144238090> " + _("Bug Hunter"),
            "found_hidden_feature": ":egg:" + _("Discovered Hidden Feature"),
            "translator": "<:google_tr:621435195102461952> " + _("Bot Translator"),
            "owner": "<:owner:621436626257838090> " + _("Bot Owner"),
            "contributor": "<:contribution:643397975732912142> " + _("Contributor")
        }
        if user.id not in self.bot.cache.acknowledgements:
            return []
        acknowledgements = [tr[Acknowledgements(x).name] for x in self.bot.cache.acknowledgements[user.id]]
        return acknowledgements

    @commandExtra(category="User Info")
    async def shared(self, ctx):
        shared = [g.name for g in self.bot.guilds if ctx.author in g.members]
        e = discord.Embed(color=ctx.embed_color,
                          title=_("Servers we share ({0}):").format(str(len(shared))),
                          description='\n'.join(shared))
        await ctx.send(embed=e)

    @commandExtra(category="User Info")
    async def credits(self, ctx):
        embed = discord.Embed(color=ctx.embed_color, title=_(
            "I'd like to thank these people for their help to improve Charles!"))

        translators = await self.bot.db.fetch("SELECT language, array_agg(user_id) FROM translators WHERE user_progress != 0 GROUP BY language")

        # desc = []
        # for lang, userslist in translators:
        #     langname = f"**{list(langs.LANGUAGES.keys())[list(langs.LANGUAGES.values()).index(lang)]}:**"
        #     users = []
        #     for u_id in userlist:
        #         users.append(await self.bot.try_user(u_id))

        template = "**{}:** {}"

        bar = []
        for x in translators:
            bar.append(template.format(list(langs.LANGUAGES.keys())[list(langs.LANGUAGES.values()).index(x['language'])], ', '.join([discord.utils.escape_markdown(str(await self.bot.try_user(y))) for y in x['array_agg']])))

        foo = sorted(bar)

        trdesc = '\n'.join(foo)

        # trdesc = '\n'.join(sorted([f":** {', '.join([discord.utils.escape_markdown(str(self.bot.get_user(y))) for y in x['array_agg']])}" for x in translators]))
        tr = _("Translators")
        embed.add_field(name=f"__**{tr}:**__\n\n", value=trdesc, inline=False)

        jup = await self.bot.try_user(431954469606129695)
        gy = await self.bot.try_user(299899233924939776)
        bread = await self.bot.try_user(284798894448050198)
        badesc = f"- **{gy}** (logos)\n"
        badesc += "⠀⠀ட <:instagram:595712748088721409> @trashygarbagebin\n"
        badesc += f"- **{jup}** (icons)\n"
        badesc += f"- **{bread}** (themes)"
        ba = _("Bot Artist")
        embed.add_field(name=f"__**{ba}:**__\n\n", value=badesc)

        tom = await self.bot.try_user(547861735391100931)
        xua = await self.bot.try_user(455289384187592704)
        contdesc = f"- **{tom}**\n"
        contdesc += f"- **{xua}**"
        cont = _("Notable Contributors")
        embed.add_field(name=f"__**{cont}:**__\n\n", value=contdesc)

        await ctx.send(embed=embed)

    @commandExtra(category="User Info", aliases=['joinedat'])
    @commands.guild_only()
    async def joindate(self, ctx, *, user: discord.Member = None):
        if user is None:
            user = ctx.author

        embed = discord.Embed(colour=ctx.embed_color)
        embed.set_thumbnail(url=user.avatar.url)
        embed.description = _("**{0}** joined **{1}**\n\n{2}\n*{3}*").format(user, ctx.guild.name, date(user.joined_at), timesince(user.joined_at))
        await ctx.send(embed=embed)

    @commandExtra(category="User Info", aliases=['avy', 'av', 'pfp'])
    async def avatar(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        av = user.avatar

        png = av.with_format("png")
        jpeg = av.with_format("jpeg")
        webp = av.with_format("webp")
        gif = av.with_format("gif") if user.is_avatar_animated() else None

        em = discord.Embed(color=ctx.embed_color)
        em.set_image(url=user.avatar.url)
        em.description = f"[png]({png}) | [jpeg]({jpeg}) | [webp]({webp})" + (f" | [gif]({gif})" if gif else '')

        bot_artist = await self.bot.try_user(299899233924939776)

        if user == ctx.me:
            em.set_footer(text=_("Credits to {0} for making my avatar!").format(str(bot_artist)))

        await ctx.send(embed=em)

    @commandExtra(category="User Info", aliases=['user', 'ui'])
    @commands.guild_only()
    async def userinfo(self, ctx, *, user: discord.Member = None):
        if user is None:
            user = ctx.author
        cuser = self.bot.get_user_cache(user.id)

        # status = {
        #     "online": "<:online2:464520569975603200>",
        #     "idle": "<:away2:464520569862357002>",
        #     "dnd": "<:dnd2:464520569560498197>",
        #     "offline": "<:offline2:464520569929334784>"
        # }

        embed = discord.Embed(colour=ctx.embed_color)
        shared = str(len([i for i in ctx.bot.guilds if i.get_member(user.id)]))

        # m = _("Mobile Status")
        # d = _("Desktop Status")
        # w = _("Web Status")
        c = _("click here")

        info = []
        info.append(_("**Full Name:**") + f" {user} {' <:botTag:230105988211015680>' if user.bot else ''}")
        info.append(_("**User ID:**") + f" {user.id}")
        info.append(_("**Nickname:**") + f" {user.nick if hasattr(user, 'nick') else '<:xmark:314349398824058880>'}")
        info.append(_("**Shared Servers:**") + f" {shared}")
        info.append(_("**Joined Server:**") + f" {date(user.joined_at)} ({timesince(user.joined_at)})")
        info.append(_("**Bot:**") + ('<:check:314349398811475968>' if user.bot else '<:xmark:314349398824058880>'))
        info.append(_("**User Created:**") + f" {date(user.created_at)} ({timesince(user.created_at)})")
        info.append(_("**Avatar URL:**") + f" [{c}]({user.avatar.url})")
        # embed.add_field(name=_("**Status**"),
        #                 value=f"{status[str(user.mobile_status)]} | <:phone:678975238192496643> {m}\n"
        #                       f"{status[str(user.desktop_status)]} | <:pc:678972796445130772> {d}\n"
        #                       f"{status[str(user.web_status)]} | <:web:678724316464152589> {w}")

        embed.description = '<:arrow:735653783366926931> ' + '\n<:arrow:735653783366926931> '.join(info)

        acknowledgements = self.get_acknowledgements(user)
        if acknowledgements:
            embed.add_field(name=_("**Acknowledgements**"),
                            value="\n".join(acknowledgements))

        embed.set_thumbnail(url=user.avatar.with_static_format('png'))

        userroles = []
        for role in user.roles:
            userroles.append(role.id)
        userroles = userroles[::-1][:-1]
        if len(user.roles) == 1:
            roles = _("None")
        elif len(user.roles) > 15:
            roles = ', '.join([f"<@&{x}>" for x in userroles][:15]) + f" (+{len(user.roles)-15})"
        else:
            roles = ', '.join([f"<@&{x}>" for x in userroles])

        clear_backticks = lambda x: x.replace('`', '\u200b`\u200b')
        if cuser.socials:
            embed.add_field(name=_("**Socials**"),
                            value="\n".join([f"{emoji.socials[stype]} **{stype.title()}** - `{clear_backticks(social)}`" for stype, social in cuser.socials.get_all().items()]))

        embed.add_field(
            name=_("**Roles**") + f" **({len(user.roles)-1})**",
            value=roles,
            inline=False
        )

        await ctx.send(embed=embed)


def setup(bot):
    pass
