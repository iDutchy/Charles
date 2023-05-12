from datetime import datetime

import discord
import time_str
from core import i18n
from core.cog import SubCog
from core.commands import commandExtra, flagsExtra, groupExtra
from core.emojis import Emoji
from discord.ext import commands, flags
from utils.converters import readable_bytes
from utils.humanize_time import date, date_time, timesince
from utils.images import changePNGColor
from utils.paginator import EmbedPages
from utils.progressbar import create as make_pb

t_on = "<:set_no_off:670629085051093002><:set_yes_on:670629085365534740> "
t_off = "<:set_no_on:670629085050961950><:set_yes_off:670629085025796137> "


def c(t, e):
    return f"{Emoji.arrow} **{t}:** {e}"


# class GuildInfo(commands.Cog, name="Info"):
class GuildInfo(SubCog, category="Guild Info"):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return ctx.guild is not None

    def next_level_calc(self, ctx):
        if ctx.guild.premium_tier == 0:
            count = int(2 - ctx.guild.premium_subscription_count)

        elif ctx.guild.premium_tier == 1:
            count = int(15 - ctx.guild.premium_subscription_count)

        elif ctx.guild.premium_tier == 2:
            count = int(30 - ctx.guild.premium_subscription_count)

        elif ctx.guild.premium_tier == 3:
            return _("Maximum boost level reached!")

        txt = _("Next level in {0} boosts").format(count)
        return txt

    @commandExtra(category="Server Info", aliases=['firstmsg'])
    async def firstmessage(self, ctx, *, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        if not channel.permissions_for(ctx.me).read_messages or not channel.permissions_for(ctx.me).read_message_history:
            return await ctx.send(_("I can not view messages from that channel..."))
        msg, = await channel.history(limit=1, oldest_first=True).flatten()
        if msg.embeds:
            return await ctx.send(_("Message was an embed, so here is the link to the message: {0}").format(msg.jump_url))
        e = discord.Embed(color=ctx.embed_color, description=msg.content)
        e.set_author(name=f"{msg.author} | #{msg.channel.name}",icon_url=msg.author.avatar.url)
        e.add_field(name="\u200b", value=_("[Go to message!]({0})").format(msg.jump_url))
        e.set_footer(icon_url=ctx.guild.icon.url, text=_("Message was sent at {0}").format(date_time(msg.created_at)))
        await ctx.send(embed=e)

    @commandExtra(category="Server Info", aliases=['ri'])
    async def roleinfo(self, ctx, *, role: discord.Role):
        e = discord.Embed(title=f"**{role.name}**", color=role.color)
        img = changePNGColor("db/images/role_tag.png", "#000000", str(role.color))
        desc = []
        perms = ", ".join(f"`{p.replace('_', ' ').title()}`" for p, v in role.permissions if v)
        desc.append(c(_("Mention"), role.mention))
        desc.append(c(_("ID"), role.id))
        desc.append(c(_("In Role"), f'👤 {sum(1 for m in role.members if not m.bot)} | 🤖 {sum(1 for m in role.members if m.bot)}'))
        desc.append(c(_("Created"), date_time(role.created_at)))
        desc.append(c(_("Position"), role.position))
        desc.append(c(_("Hoisted"), ctx.emoji.check if role.hoist else ctx.emoji.xmark))
        desc.append(c(_("Mentionable"), ctx.emoji.check if role.mentionable else ctx.emoji.xmark))
        desc.append(c(_("Managed"), ctx.emoji.check if role.managed else ctx.emoji.xmark))
        desc.append(c(_("Special Permissions"), perms if perms else _("None")))
        e.description = "\n".join(desc)
        file = discord.File(img, "RoleColor.png")
        e.set_thumbnail(url="attachment://RoleColor.png")
        await ctx.send(embed=e, file=file)

    @commandExtra(category="Server Info")
    async def inrole(self, ctx, *, role: discord.Role):
        if not role.members:
            return await ctx.send(_("It looks like this nobody has this role..."))
        users = [f'**{u}** ({u.id})' for u in sorted(role.members, key=lambda m: m.name)]
        await self.bot.utils.paginate(ctx, prefix=_("Members with role: {0}").format(role.mention)+"\n", entries=users, show_entry_count=True, show_entry_nums=True, show_page_num=True, per_page=15)

    @flags.add_flag('name', nargs="*")
    @flags.add_flag("--include-nicks", action='store_true', default=False)
    @flags.add_flag("--nicks-only", action='store_true', default=False)
    @flags.add_flag("--full-match", action='store_true', default=False)
    @flags.add_flag("--export-ids", action='store_true', default=False)
    @flags.add_flag("--kick-members", action='store_true', default=False)
    @flags.add_flag("--has-role", type=discord.Role, default=None)
    @flags.add_flag("--role-count", type=int, default=-1)
    @flags.add_flag("--bots", action='store_true', default=False)
    @flags.add_flag("--humans", action='store_true', default=False)
    @flags.add_flag("--discrim", type=int, default=-1)
    @flags.add_flag("--join-age", default=None, nargs="+")
    @flags.add_flag("--account-age", default=None, nargs="+")
    @flagsExtra(name='members', category="Server Info")
    async def members(self, ctx, **flags):
        name = ' '.join(flags.get('name', []))
        checks = []

        namefilters = ('include_nicks', 'nicks_only', 'full_match')

        if not name and any([k for k, v in flags.items() if v is True and k in namefilters]):
            return await ctx.send(_("You attempted to use name filters but didnt provide a name to search for. Please use the command as `{0}`").format(f'{ctx.clean_prefix}members <NAME> [filters]'))

        if flags.get('include_nicks') and flags.get('nicks_only'):
            return await ctx.send(_("Please pick either only `--include-nicks` *or* `--nicks-only`, not both!"))

        if flags.get('export_ids') and flags.get('kick_members'):
            return await ctx.send(_("Please pick only 1 return action. By default I will send a list of members with the given filters. Still confused? Please check the help of this command for more info."))

        if flags.get('bots') and flags.get('humans'):
            return await ctx.send(_("Please pick either `--bots` or `--humans` and not both. If you want to list both bots and humans, then dont provide either of these 2 filters."))

        match = flags.get('full_match')

        if flags.get('include_nicks'):
            if match:
                checks.append(lambda m: name.lower() in (m.display_name.lower(), m.name.lower()))
            else:
                checks.append(lambda m: name.lower() in m.display_name.lower() or name.lower() in m.name.lower())

        elif flags.get('nicks_only'):
            if match:
                checks.append(lambda m: name.lower() == m.display_name.lower() and m.nick is not None)
            else:
                checks.append(lambda m: name.lower() in m.display_name.lower() and m.nick is not None)

        else:
            if match:
                checks.append(lambda m: name.lower() == m.name.lower())
            else:
                checks.append(lambda m: name.lower() in m.name.lower())

        if role := flags.get('has_role'):
            checks.append(lambda m: role in m.roles)

        if (rolecount := flags.get('role_count')) >= 0:
            checks.append(lambda m: len(m.roles)-1 == rolecount)

        if (discrim := flags.get('discrim')) != -1:
            checks.append(lambda m: int(m.discriminator) == discrim)

        if flags.get('bots'):
            checks.append(lambda m: m.bot is True)

        if flags.get('humans'):
            checks.append(lambda m: m.bot is False)

        if age := flags.get('join_age'):
            dt = datetime.utcnow() - time_str.convert(' '.join(age))
            checks.append(lambda m: m.joined_at >= dt)

        if age := flags.get('account_age'):
            dt = datetime.utcnow() - time_str.convert(' '.join(age))
            checks.append(lambda m: m.created_at >= dt)

        members = [m for m in ctx.guild.members if all(check(m) for check in checks)]

        if not members:
            return await ctx.send(_("No members found with the given filters!"))

        if flags.get('export_ids'):
            url = await self.bot.utils.bin("\n".join(map(str, map(int, members))))
            return await ctx.send(url)

        if flags.get('kick_members'):
            if not ctx.author.guild_permissions.kick_members:
                return await ctx.send(_("To kick the filtered members, you need the `Kick Members` permission!"))
            if not ctx.me.guild_permissions.kick_members:
                return await ctx.send(_("To kick the filtered members, I need the `Kick Members` permission!"))

            kick = self.bot.get_command('kick')
            await ctx.invoke(kick, members)
            return

        await self.bot.utils.paginate(ctx,
                          title=_("Users found with the given filter(s):") if checks else _("All members in this server:"),
                          entries=[f"[`{m.id}`] `{m}`" + (f" (**{m.nick}**)" if m.nick else '') for m in members],
                          per_page=25,
                          # show_entry_nums=True,
                          author=ctx.guild,
                          show_page_num=True,
                          show_entry_count=True)

    @commandExtra(category="Server Info")
    async def categories(self, ctx):
        m_settings = await self.bot.db.fetchrow("SELECT * FROM module_settings WHERE guild_id = $1", ctx.guild.id)
        c_settings = await self.bot.db.fetchrow("SELECT * FROM category_settings WHERE guild_id = $1", ctx.guild.id)

        e = discord.Embed(color=ctx.embed_color,
                          title=_("**Category Settings**"))

        m_count = 0

        settings_dict = {}
        for m in list(c_settings.keys())[1:]:
            settings_dict[m.split('_')[0]] = {}
        for m, x in list(c_settings.items())[1:]:
            settings_dict[m.split('_')[0]][m.split('_')[1]] = x

        for x in settings_dict.keys():
            if m_settings[x] is False:
                continue
            m_count += 1
            val = []
            for k, v in settings_dict[x].items():
                if v:
                    val.append(f"{t_on}{k.replace('-', ' ').title()}")
                if not v:
                    val.append(f"{t_off}{k.replace('-', ' ').title()}")
            e.add_field(name=f"**{x.title()}**", value="\n".join(val))

        if m_count == 0:
            e.description = _("All ***modules*** are disabled. Please enable at least **1** module to view the category settings!")

        await ctx.send(embed=e)

    @commandExtra(category="Server Info")
    async def modules(self, ctx):
        settings = self.bot.cache.get("modules", ctx.guild.id)

        e = discord.Embed(color=ctx.embed_color,
                          title="\U00002699 " + _("**Module Settings**"))

        toggles = []
        for m in settings.keys():
            if settings[m]:
                toggles.append(f"{t_on}{m.title()}")
            if not settings[m]:
                toggles.append(f"{t_off}{m.title()}")

        e.description = "\n".join(toggles)

        await ctx.send(embed=e)

    @groupExtra(invoke_without_command=True, category="Server Info", aliases=['gs', 'settings'])
    async def guildsettings(self, ctx):
        e = discord.Embed(color=ctx.embed_color)
        e.set_author(icon_url=ctx.guild.icon.url,
                     name=_("Settings for: {0}").format(ctx.guild.name))

        roastvalues = {
            1: _("Low"),
            2: _("Medium"),
            3: _("High")
        }

        logging = self.bot.cache.get("logging", ctx.guild.id)
        welcomer = self.bot.cache.get("welcomer", ctx.guild.id)
        settings = self.bot.cache.get("settings", ctx.guild.id)
        logs = []
        logs.append((t_on if logging['msgedit_channel'] else t_off) + _("Edited Messages"))
        logs.append((t_on if logging['msgdel_channel'] else t_off) + _("Deleted Messages"))
        logs.append((t_on if logging['mod_channel'] else t_off) + _("Moderation"))
        logs.append((t_on if logging['useredit_channel'] else t_off) + _("Member Updates"))
        e.add_field(name=_("Logs:"), value='\n'.join(logs))

        botsettings = []
        botsettings.append((t_on if settings['joinrole_toggle'] else t_off) + _("Role On Join"))
        botsettings.append((t_on if welcomer['welcome_toggle'] or welcomer['welcome_embedtoggle'] else t_off) + _("Welcoming Messages"))
        botsettings.append((t_on if welcomer['leave_toggle'] or welcomer['leave_embedtoggle'] else t_off) + _("Leaving Messages"))
        botsettings.append((t_on if settings['cb_mention'] else t_off) + _("CB On Mention"))
        e.add_field(name=_("Settings:"), value='\n'.join(botsettings))

        customized = []
        customized.append(_("**Embed Color:**") + f" {discord.Color(settings['color'])}")
        customized.append(_("**Language:**") + f" {settings['language']}")
        customized.append(_("**Roast Level:**") + f" {roastvalues[settings['roastlevel']]}")
        customized.append(_("**CB Emotion:**") + f" {settings['cb_emotion']}")
        customized.append(_("**Prefix:**") + f" {self.bot.cache.get('prefix', ctx.guild.id)}")
        e.add_field(name=_("Custom Settings:"), value='\n'.join(customized))

        # e.add_field(name="Disabled Commands:", value="None")

        if welcomer['welcome_embedtoggle']:
            welcome_msg = _("Embedded welcome message.\nUse `guildsettings welcomemsg` to view it.")
        else:
            welcome_msg = welcomer['welcome_msg']

        if welcomer['leave_embedtoggle']:
            leave_msg = _("Embedded leave message.\nUse `guildsettings leavemsg` to view it.")
        else:
            leave_msg = welcomer['leave_msg']

        if welcomer['welcome_toggle'] or welcomer['welcome_embedtoggle']:
            e.add_field(name=_("Welcoming Message:"), value=welcome_msg, inline=False)
        else:
            e.add_field(name=_("Welcoming Message:"),
                        value=_("**[Welcoming message is not enabled]**"),
                        inline=False)

        if welcomer['leave_toggle'] or welcomer['leave_embedtoggle']:
            e.add_field(name=_("Leaving Message:"), value=leave_msg, inline=False)
        else:
            e.add_field(name=_("Leaving Message:"),
                        value=_("**[Leaving message is not enabled]**"),
                        inline=False)

        await ctx.send(embed=e)

    @guildsettings.command()
    async def welcomemsg(self, ctx):
        if not self.bot.cache.get("welcomer", ctx.guild.id, 'welcome_embedtoggle'):
            return

        emb_dict = self.bot.cache.get("welcomer", ctx.guild.id, 'welcome_embedmsg')

        await ctx.send(embed=discord.Embed.from_dict(emb_dict))

    @guildsettings.command()
    async def roasts(self, ctx):
        if not (roasts := self.bot.cache.get("settings", ctx.guild.id, 'custom_roasts')):
            return await ctx.send(_("No custom roasts have been added for this server!"))

        paginator = EmbedPages(ctx,
                          title=_("Custom Roasts:"),
                          entries=roasts,
                          per_page=10,
                          show_entry_nums=True,
                          author=ctx.guild,
                          show_page_num=True,
                          show_entry_count=True)

        return await paginator.start()

    @guildsettings.command()
    async def leavemsg(self, ctx):
        if not self.bot.cache.get("welcomer", ctx.guild.id, 'leave_embedtoggle'):
            return

        emb_dict = self.bot.cache.get("welcomer", ctx.guild.id, 'leave_embedmsg')

        await ctx.send(embed=discord.Embed.from_dict(emb_dict))

    @guildsettings.command(hidden=True, name="roles")
    async def guild_roles(self, ctx):
        def makestring(i18ntext, othertext):
            return f"<:arrow:735653783366926931> **{i18ntext}:** {othertext}"

        def try_role(role_id):
            if role_id is None:
                return _("Not set")
            role = ctx.guild.get_role(role_id)
            if role is None:
                return _("Role set, but was deleted. Please set a new role!")
            return role.mention

        roles = self.bot.cache.get("roles", ctx.guild.id)

        e = discord.Embed(color=ctx.embed_color, title=_("Role Settings"))
        desc = []
        desc.append(makestring(_("Moderator"), try_role(roles['moderator'])))
        desc.append(makestring(_("Booster"), try_role(roles['booster'])))
        desc.append(makestring(_("DJ"), try_role(roles['dj'])))
        desc.append(makestring(_("Muted"), try_role(roles['muted'])))
        e.description = "\n".join(desc)
        await ctx.send(embed=e)

    @commandExtra(category="Server Info", aliases=['server', 'si'])
    @commands.guild_only()
    async def serverinfo(self, ctx):
        findbots = len(ctx.guild.bots)
        b = _("bots")
        c = _("click here")

        roles = []
        for role in ctx.guild.roles:
            if role.name == "@everyone":
                continue
            if role.managed:
                continue
            roles.append(role)

        has_features = []
        features = set(ctx.guild.features)
        all_features = {
            'PARTNERED': _("Partnered"),
            'VERIFIED': _("Verified"),
            'INVITE_SPLASH': _("Invite Splash"),
            'VANITY_URL': _("Vanity Invite"),
            'MORE_EMOJI': _("More Emoji"),
            'ANIMATED_ICON': _("Animated Icon"),
            'BANNER': _("Banner")
        }

        for feature, label in all_features.items():
            if feature in features:
                has_features.append(label)

        embed = discord.Embed(color=ctx.embed_color)
        if d := ctx.guild.description:
            embed.description = d
        if i := ctx.guild.icon.url:
            embed.set_thumbnail(url=i)
        else:
            embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")

        def makestring(i18ntext, othertext):
            return f"<:arrow:735653783366926931> **{i18ntext}:** {othertext}"

        info = []
        info.append(makestring(_("Name"), ctx.guild.name))
        info.append(makestring(_("ID"), ctx.guild.id))
        info.append(makestring(_("Region"), ctx.guild.region))
        info.append(makestring(_("Verification Level"), ctx.guild.verification_level.name.capitalize()))
        info.append(makestring(_("Upload Limit"), readable_bytes(ctx.guild.filesize_limit)))
        info.append(makestring(_("Channels"), f"<:channel:585783907841212418> {len(ctx.guild.text_channels)} | <:voice:585783907673440266> {len(ctx.guild.voice_channels)}"))
        info.append(makestring(_("Emojis"), f"{len(ctx.guild.emojis)} / {ctx.guild.emoji_limit}"))
        if banner := ctx.guild.banner_url_as(format="png")._url:
            info.append(makestring(_("Banner"), f" [{c}](https://cdn.discordapp.com{banner})"))
        info.append(makestring(_("Created"), f" {date(ctx.guild.created_at)} ({timesince(ctx.guild.created_at)})"))
        if has_features:
            info.append(makestring(_("Features"), ', '.join(has_features)))

        embed.add_field(name=_("**General Info**"), value='\n'.join(info), inline=False)

        members = []
        members.append(makestring(_("Owner"), ctx.guild.owner))
        members.append(makestring(_("Members"), f"{len(ctx.guild.humans)} (+{findbots} {b})"))
        if ctx.guild.me.guild_permissions.ban_members:
            members.append(makestring(_("Banned"), len(await ctx.guild.bans())))
        members.append(makestring(_("Mods"), sum(1 for m in ctx.guild.humans if m.guild_permissions.kick_members)))
        members.append(makestring(_("Admins"), sum(1 for m in ctx.guild.humans if m.guild_permissions.ban_members)))

        embed.add_field(name=_("**Member Info**"), value='\n'.join(members), inline=False)

        last_boost = max(ctx.guild.members, key=lambda m: m.premium_since or ctx.guild.created_at)
        if last_boost.premium_since is not None:
            boosts = []
            boosts.append(_("{0} Boosts").format(str(ctx.guild.premium_subscription_count)))
            boosts.append(self.next_level_calc(ctx))
            boosts.append("\n0⠀" + make_pb(14, 1, (ctx.guild.premium_subscription_count if ctx.guild.premium_subscription_count <= 14 else 14)) + "⠀14")

            embed.add_field(name=_("Boosts"), value='\n'.join(boosts), inline=False)

        rl = ", ".join([r.mention for r in roles])
        if len(rl) > 1024:
            rl = f"`{'`, `'.join([r.name for r in roles])}`"
            if len(rl) > 1024:
                rl = ", ".join([r.mention for r in roles][:10]) + f" *+{len(roles)-10}*"
        if rl:
            embed.add_field(name=_("Roles ({0})").format(len(roles)), value=rl, inline=False)
        await ctx.send(embed=embed)

    @commandExtra(category="Server Info", aliases=['mods', 'moderators', 'admins', 'administrators'])
    async def staff(self, ctx):
        status = {
            "online": "<:online2:464520569975603200>",
            "idle": "<:away2:464520569862357002>",
            "dnd": "<:dnd2:464520569560498197>",
            "offline": "<:offline2:464520569929334784>"
        }

        e = discord.Embed(color=ctx.embed_color, title=_("Server Staff"))
        e.set_author(icon_url=ctx.guild.icon.with_format("png"), name=ctx.guild.name)
        e.add_field(name=_("**Moderators** (can kick)"), value='\n'.join([f'{status[str(m.status)]} {m}' for m in ctx.guild.humans if m.guild_permissions.kick_members]))
        e.add_field(name=_("**Admins** (can ban)"), value='\n'.join([f'{status[str(m.status)]} {m}' for m in ctx.guild.humans if m.guild_permissions.ban_members]))
        await ctx.send(embed=e)


def setup(bot):
    pass
