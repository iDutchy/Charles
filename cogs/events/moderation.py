import discord

from discord.ext import commands
from utils.utility import warn
from datetime import datetime, timedelta
from utils.humanize_time import date_time, timesince
from cogs.moderation.__actions import ModAction as m_action
from core.cog import SubCog

class ModEvents(SubCog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if user.id in self.bot.cache.modactions:
            self.bot.cache.modactions.remove(user.id)
            return

        mod = reason = audit = False
        if guild.me.guild_permissions.view_audit_log:
            audit = True
            action = await guild.audit_logs(action=discord.AuditLogAction.ban, limit=1).flatten() 
            if action:
                action = action[0]
                mod = action.user
                reason = action.reason
                if action.target.id == user.id and (action.created_at < datetime.utcnow()-timedelta(minutes=1)):
                    self.bot.dispatch("ban", m_action(target=user, mod=action.user, guild=guild, reason=action.reason))
                    return

        if not (cid := self.bot.cache.get("logging", guild.id, "mod_channel")):
            return

        c = guild.get_channel(cid)
        if not c:
            await warn("ban", guild, "Modlog channel not found")
            return

        u = _("Unknown")
        e = discord.Embed(
            title=_("Member Banned"),
            description=_("**Moderator:** {0} \n**Target:** {1} `({1.id})`\n**Reason:** {2}").format(f"{mod} `({mod.id})`" if mod else u, user, reason or u),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=guild,
            icon_url=guild.icon.with_format("png")
        )
        e.add_field(
            name=_("**Target Info**"),
            value=_("**Joined:** {0}\n**Stayed in server for:** {1}\n**Account created:** {2}").format(date_time(user.joined_at), timesince(user.joined_at, add_suffix=False), date_time(user.created_at))
        )
        e.set_thumbnail(
            url=user.avatar.with_static_format("png")
        )
        if not audit:
            e.set_footer(
                text=_("Moderator and Reason are unknown because I do not have permissions to view audit logs.")
            )

        await c.send(embed=e)
        
    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        if user.id in self.bot.cache.modactions:
            self.bot.cache.modactions.remove(user.id)
            return

        mod = reason = audit = False
        if guild.me.guild_permissions.view_audit_log:
            audit = True
            action = await guild.audit_logs(action=discord.AuditLogAction.unban, limit=1).flatten() 
            if action:
                action = action[0]
                mod = action.user
                reason = action.reason
                if action.target.id == user.id and (action.created_at > datetime.utcnow()-timedelta(minutes=1)):
                    self.bot.dispatch("unban", m_action(target=user, mod=action.user, guild=guild, reason=action.reason))
                    return

        if not (cid := self.bot.cache.get("logging", guild.id, "mod_channel")):
            return

        c = guild.get_channel(cid)
        if not c:
            await warn("ban", guild, "Modlog channel not found")
            return

        u = _("Unknown")
        e = discord.Embed(
            title=_("Member Unbanned"),
            description=_("**Moderator:** {0} \n**Target:** {1} `({1.id})`\n**Reason:** {2}").format(f"{mod} `({mod.id})`" if mod else u, user, reason or u),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=guild,
           icon_url=guild.icon.with_format("png")
        )
        e.add_field(
            name=_("**Target Info**"),
            value=_("**Account created:** {0}").format(date_time(user.created_at))
        )
        e.set_thumbnail(
            url=user.avatar.with_static_format("png")
        )
        if not audit:
            e.set_footer(
                text=_("Moderator and Reason are unknown because I do not have permissions to view audit logs.")
            )

        await c.send(embed=e)

#####################################################

    @commands.Cog.listener()
    async def on_kick(self, payload):
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("kick", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Member Kicked"),
            description=_("**Moderator:** {0} `({0.id})`\n**Target:** {1} `({1.id})`\n**Reason:** {2}").format(payload.mod, payload.target, payload.reason),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        e.add_field(
            name=_("**Target Info**"),
            value=_("**Joined:** {0}\n**Stayed in server for:** {1}\n**Account created:** {2}").format(date_time(payload.target.joined_at), timesince(payload.target.joined_at, add_suffix=False), date_time(payload.target.created_at))
        )
        e.set_thumbnail(
            url=payload.target.avatar.with_static_format("png")
        )

        await c.send(embed=e)


    @commands.Cog.listener()
    async def on_masskick(self, payload):
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("masskick", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Members Kicked"),
            description=_("**Moderator:** {0} `({0.id})`\n**Targets:** {1}\n**Failed:** {2}\n**Reason:** {3}").format(payload.mod, len(payload.targets), len(payload.failed.keys()), payload.reason),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        targets = "\n".join([f"**{t}** `({t.id})`" for t in payload.targets][:10])
        if len(payload.targets) > 10:
            targets += f"\n***+{len(payload.targets)-10}***"
        e.add_field(
            name=_("**Targets**"),
            value=targets,
            inline=False
        )

        await c.send(embed=e)

    @commands.Cog.listener()
    async def on_ban(self, payload):
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("ban", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Member Banned"),
            description=_("**Moderator:** {0} `({0.id})`\n**Target:** {1} `({1.id})`\n**Reason:** {2}").format(payload.mod, payload.target, payload.reason),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        e.add_field(
            name=_("**Target Info**"),
            value=_("**Joined:** {0}\n**Stayed in server for:** {1}\n**Account created:** {2}").format(date_time(payload.target.joined_at), timesince(payload.target.joined_at, add_suffix=False), date_time(payload.target.created_at))
        )
        e.set_thumbnail(
            url=payload.target.avatar.with_static_format("png")
        )

        await c.send(embed=e)

    @commands.Cog.listener()
    async def on_unban(self, payload):
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("unban", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Member Unbanned"),
            description=_("**Moderator:** {0} `({0.id})`\n**Target:** {1} `({1.id})`\n**Reason:** {2}").format(payload.mod, payload.target, payload.reason),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        e.add_field(
            name=_("**Target Info**"),
            value=_("**Account created:** {0}").format(date_time(payload.target.created_at))
        )
        e.set_thumbnail(
            url=payload.target.avatar.with_static_format("png")
        )

        await c.send(embed=e)

    @commands.Cog.listener()
    async def on_unbanall(self, payload): #WARNING: NO payload.reason !!
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("unbanall", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Members Unbanned"),
            description=_("**Moderator:** {0} `({0.id})`\n**Targets:** {1}").format(payload.mod, len(payload.targets)),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        targets = "\n".join([f"**{t}** `({t.id})`" for t in payload.targets][:10])
        if len(payload.targets) > 10:
            targets += f"\n***+{len(payload.targets)-10}***"
        e.add_field(
            name=_("**Targets**"),
            value=targets,
            inline=False
        )

        await c.send(embed=e)

    @commands.Cog.listener()
    async def on_massban(self, payload):
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("massban", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Members Banned"),
            description=_("**Moderator:** {0} `({0.id})`\n**Targets:** {1}\n**Failed:** {2}\n**Reason:** {3}").format(payload.mod, len(payload.targets), len(payload.failed.keys()), payload.reason),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        targets = "\n".join([f"**{t}** `({t.id})`" for t in payload.targets][:10])
        if len(payload.targets) > 10:
            targets += f"\n***+{len(payload.targets)-10}***"
        e.add_field(
            name=_("**Targets**"),
            value=targets,
            inline=False
        )

        await c.send(embed=e)

    @commands.Cog.listener()
    async def on_massunban(self, payload):
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("massunban", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Members Unbanned"),
            description=_("**Moderator:** {0} `({0.id})`\n**Targets:** {1}\n**Failed:** {2}\n**Reason:** {3}").format(payload.mod, len(payload.targets), len(payload.failed.keys()), payload.reason),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        targets = "\n".join([f"**{t}** `({t.id})`" for t in payload.targets][:10])
        if len(payload.targets) > 10:
            targets += f"\n***+{len(payload.targets)-10}***"
        e.add_field(
            name=_("**Targets**"),
            value=targets,
            inline=False
        )

        await c.send(embed=e)

    @commands.Cog.listener()
    async def on_softban(self, payload):
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("softban", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Member Softbanned"),
            description=_("**Moderator:** {0} `({0.id})`\n**Target:** {1} `({1.id})`\n**Reason:** {2}").format(payload.mod, payload.target, payload.reason),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        e.add_field(
            name=_("**Target Info**"),
            value=_("**Joined:** {0}\n**Stayed in server for:** {1}\n**Account created:** {2}").format(date_time(payload.target.joined_at), timesince(payload.target.joined_at, add_suffix=False), date_time(payload.target.created_at))
        )
        e.set_thumbnail(
            url=payload.target.avatar.with_static_format("png")
        )

        await c.send(embed=e)

    @commands.Cog.listener()
    async def on_masssoftban(self, payload):
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("masssoftban", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Members Softbanned"),
            description=_("**Moderator:** {0} `({0.id})`\n**Targets:** {1}\n**Failed:** {2}\n**Reason:** {3}").format(payload.mod, len(payload.targets), len(payload.failed.keys()), payload.reason),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        targets = "\n".join([f"**{t}** `({t.id})`" for t in payload.targets][:10])
        if len(payload.targets) > 10:
            targets += f"\n***+{len(payload.targets)-10}***"
        e.add_field(
            name=_("**Targets**"),
            value=targets,
            inline=False
        )

        await c.send(embed=e)

    @commands.Cog.listener()
    async def on_mute(self, payload):
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("mute", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Member Muted"),
            description=_("**Moderator:** {0} `({0.id})`\n**Target:** {1} `({1.id})`\n**Reason:** {2}").format(payload.mod, payload.target, payload.reason),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        e.add_field(
            name=_("**Target Info**"),
            value=_("**Joined:** {0}\n**Account created:** {2}").format(date_time(payload.target.joined_at), timesince(payload.target.joined_at, add_suffix=False), date_time(payload.target.created_at))
        )
        e.set_thumbnail(
            url=payload.target.avatar.with_static_format("png")
        )

        await c.send(embed=e)

    @commands.Cog.listener()
    async def on_massmute(self, payload):
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("massmute", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Members Muted"),
            description=_("**Moderator:** {0} `({0.id})`\n**Targets:** {1}\n**Failed:** {2}\n**Reason:** {3}").format(payload.mod, len(payload.targets), len(payload.failed.keys()), payload.reason),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        targets = "\n".join([f"**{t}** `({t.id})`" for t in payload.targets][:10])
        if len(payload.targets) > 10:
            targets += f"\n***+{len(payload.targets)-10}***"
        e.add_field(
            name=_("**Targets**"),
            value=targets,
            inline=False
        )

        await c.send(embed=e)

    @commands.Cog.listener()
    async def on_unmute(self, payload):
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("unmute", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Member Unmuted"),
            description=_("**Moderator:** {0} `({0.id})`\n**Target:** {1} `({1.id})`\n**Reason:** {2}").format(payload.mod, payload.target, payload.reason),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        e.add_field(
            name=_("**Target Info**"),
            value=_("**Joined:** {0}\n**Account created:** {2}").format(date_time(payload.target.joined_at), timesince(payload.target.joined_at, add_suffix=False), date_time(payload.target.created_at))
        )
        e.set_thumbnail(
            url=payload.target.avatar.with_static_format("png")
        )

        await c.send(embed=e)

    @commands.Cog.listener()
    async def on_massunmute(self, payload):
        if not (cid := self.bot.cache.get("logging", payload.guild.id, "mod_channel")):
            return

        c = payload.guild.get_channel(cid)
        if not c:
            await warn("massunmute", payload.guild, "Modlog channel not found")
            return

        e = discord.Embed(
            title=_("Members Unmuted"),
            description=_("**Moderator:** {0} `({0.id})`\n**Targets:** {1}\n**Failed:** {2}\n**Reason:** {3}").format(payload.mod, len(payload.targets), len(payload.failed.keys()), payload.reason),
            timestamp=datetime.utcnow()
        )
        e.set_author(
            name=payload.guild,
           icon_url=payload.guild.icon.with_format("png")
        )
        targets = "\n".join([f"**{t}** `({t.id})`" for t in payload.targets][:10])
        if len(payload.targets) > 10:
            targets += f"\n***+{len(payload.targets)-10}***"
        e.add_field(
            name=_("**Targets**"),
            value=targets,
            inline=False
        )

        await c.send(embed=e)

def setup(bot):
    pass