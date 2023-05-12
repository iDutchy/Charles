from datetime import datetime, timedelta

import discord
import asyncio
from discord.ext import commands
from utils.utility import warn
from utils import humanize_time as ht
from cogs.moderation.__actions import ModAction as m_action
from core import i18n
from core.cog import SubCog

class UserEvents(SubCog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def value_replacer(emb_dict, member):
        for thing in emb_dict:
            if isinstance(emb_dict[thing], str):
                emb_dict[thing] = emb_dict[thing].replace("{{member.name}}", member.name)
                emb_dict[thing] = emb_dict[thing].replace("{{member.mention}}", member.mention)
                emb_dict[thing] = emb_dict[thing].replace("{{member.fullname}}", str(member))
                emb_dict[thing] = emb_dict[thing].replace("{{member.count}}", f"{sum(1 for m in member.guild.members if not m.bot)}")
                emb_dict[thing] = emb_dict[thing].replace("{{member.fullcount}}", str(member.guild.member_count))
                emb_dict[thing] = emb_dict[thing].replace("{{member.created_at}}", f"<t:{int(member.created_at.timestamp())}>")
                emb_dict[thing] = emb_dict[thing].replace("{{member.created_ago}}", f"<t:{int(member.created_at.timestamp())}:R>")
                emb_dict[thing] = emb_dict[thing].replace("{{server.name}}", member.guild.name)
                emb_dict[thing] = emb_dict[thing].replace("{{server.owner}}", member.guild.owner.name)
        return emb_dict

    @commands.Cog.listener('on_voice_state_update')
    async def music_leave(self, member, before, after):
        if before.channel is not None and after.channel is None:
            if member.guild.me in before.channel.members:
                if len([m for m in before.channel.members if not m.bot]) == 0:
                    # channel = member.guild.get_channel(self._last_command_channel)
                    # await channel.send(_("Everyone left the channel, I will stop playing music."))

                    player = self.bot.diorite.get_player(member.guild)
                    await player.destroy()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.bot:
            return

        lang = self.bot.cache.get("settings", before.guild.id, "language")

        if cid := self.bot.cache.get("logging", before.guild.id, "useredit_channel"):
            channel = before.guild.get_channel(cid)
            if channel is None:
                return await warn(self.bot, "Member Update", before.guild, "Channel does not exist in this guild anymore!")

            if before.nick != after.nick:
                try:
                    i18n.set_locale(self.bot.cache.get("settings", before.guild.id, 'language'))
                    e = discord.Embed(color=self.bot.cache.get("settings", before.guild.id, "color"),
                                      title=_("Nickname Updated"),
                                      timestamp=datetime.utcnow())
                    e.set_author(name=before,icon_url=before.avatar.url)
                    e.description = _("**Before:** `{0}`\n**After:** `{1}`").format(before.nick if before.nick else _("No nickname..."), after.nick if after.nick else _("No nickname..."))
                    e.set_footer(text=_("User ID: {0}").format(before.id))
                    await channel.send(embed=e)
                except Exception as exc:
                    tb = self.bot.exception(exc)
                    return await warn(self.bot, "Member Update", before.guild, f"Error while sending message:\n\n{tb}")

        else:
            return

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if before.bot:
            return

        user_guilds = [g for g in self.bot.guilds if before in g.members]
        for guild in user_guilds:
            if not (cid := self.bot.cache.get("logging", guild.id, "useredit_channel")):
                continue

            channel = guild.get_channel(cid)
            if channel is None:
                await warn(self.bot, "User Update", guild, "Channel does not exist in this guild anymore!")
                continue

            lang = self.bot.cache.get("settings", guild.id, "language")
            e = discord.Embed(color=self.bot.cache.get("settings", guild.id, "color"),
                              timestamp=datetime.utcnow())
            e.set_author(name=after,icon_url=after.avatar.url)

            if before.avatar != after.avatar:
                try:
                    i18n.set_locale(self.bot.cache.get("settings", guild.id, 'language'))
                    e.title = _("Avatar Updated")
                    e.description = _("**User:** {0} (`{1}`)").format(after.mention, str(after))
                    e.set_thumbnail(url=after.avatar.url)
                    # e.set_image(url=before.avatar.url)
                    e.set_footer(text=_("User ID: {0}").format(after.id))
                    await channel.send(embed=e)
                except Exception as exc:
                    tb = self.bot.exception(exc)
                    await warn(self.bot, "User Update", guild, f"Error while sending message:\n\n{tb}")
                    continue

            if before.name != after.name:
                try:
                    i18n.set_locale(self.bot.cache.get("settings", guild.id, 'language'))
                    e.title = _("Username Updated")
                    e.description = _("**Before:** `{0}`\n**After:** `{1}`").format(before.name, after.name)
                    await channel.send(embed=e)
                except Exception as exc:
                    tb = self.bot.exception(exc)
                    await warn(self.bot, "User Update", guild, f"Error while sending message:\n\n{tb}")
                    continue

    @commands.Cog.listener('on_member_join')
    async def welcoming_members_custom_message(self, member):
        if member.bot:
            return

        if self.bot.cache.get("welcomer", member.guild.id, "welcome_toggle"):
            text = self.bot.cache.get("welcomer", member.guild.id, "welcome_msg")
            new_text = text.replace("{{member.name}}", member.name)
            new_text = new_text.replace("{{member.mention}}", member.mention)
            new_text = new_text.replace("{{server.name}}", member.guild.name)

            channel = member.guild.get_channel(self.bot.cache.get("welcomer", member.guild.id, "welcome_channel"))
            if channel is None:
                await warn(self.bot, "Member Join (Custom Message)", member.guild, "Channel no longer exists")
                return
            await channel.send(new_text, delete_after=self.bot.cache.get("welcomer", member.guild.id, "welcome_delafter"))

        if self.bot.cache.get("welcomer", member.guild.id, "welcome_embedtoggle"):

            emb_dict = self.bot.cache.get("welcomer", member.guild.id, "welcome_embedmsg")
            new_dict = self.value_replacer(emb_dict.copy(), member)
            if "author" in emb_dict:
                new_dict["author"] = self.value_replacer(emb_dict["author"], member)
            if "footer" in emb_dict:
                new_dict["footer"] = self.value_replacer(emb_dict["footer"], member)
            if "fields" in emb_dict:
                for field in emb_dict["fields"]:
                    new_dict["fields"] = self.value_replacer(field["name"], member)
                    new_dict["fields"] = self.value_replacer(field["value"], member)

            content = None
            if "plainText" in emb_dict.keys():
                content = new_dict["plainText"].replace("{{member.mention}}", member.mention)

            channel = self.bot.get_channel(self.bot.cache.get("welcomer", member.guild.id, "welcome_channel"))
            if channel is None:
                await warn(self.bot, "Member Join (Custom Message)", member.guild, "Channel no longer exists")
                return
            await channel.send(content=content, 
                               embed=discord.Embed.from_dict(new_dict),
                               delete_after=self.bot.cache.get("welcomer", member.guild.id, "welcome_delafter"))

        else:
            return

    @commands.Cog.listener('on_member_join')
    async def joinroles(self, member):
        if member.bot:
            return

        if self.bot.cache.get("settings", member.guild.id, "joinrole_toggle"):
            if member.bot:
                if role_id:= self.bot.cache.get("settings", member.guild.id, "joinrole_bot"):
                    role = member.guild.get_role(role_id)
                    if role is None:
                        await warn(self.bot, "Joinroles", member.guild, "Human role does not exist anymore")
                    await member.add_roles(role)
            if not member.bot:
                if role_id:= self.bot.cache.get("settings", member.guild.id, "joinrole_human"):
                    role = member.guild.get_role(role_id)
                    if role is None:
                        await warn(self.bot, "Joinroles", member.guild, "Human role does not exist anymore")
                    await member.add_roles(role)

        else:
            return

    @commands.Cog.listener('on_member_remove')
    async def member_leave_custom_message(self, member):
        if member.bot:
            return

        if self.bot.cache.get("welcomer", member.guild.id, "leave_toggle"):

            text = self.bot.cache.get("welcomer", member.guild.id, "leave_msg")
            text = text.replace("{{member.name}}", member.name)
            text = text.replace("{{server.name}}", member.guild.name)
            text = text.replace("{{member.fullname}}", str(member))
            text = text.replace("{{member.created_at}}", f"<t:{int(member.created_at.timestamp())}>")
            text = text.replace("{{member.created_ago}}", f"<t:{int(member.created_at.timestamp())}:R>")
            text = text.replace("{{member.count}}", str(sum(1 for m in member.guild.members if not m.bot)))
            text = text.replace("{{member.fullcount}}", str(member.guild.member_count))
            text = text.replace("{{server.owner}}", self.bot.get_user(member.guild.owner_id).name)

            channel = self.bot.get_channel(self.bot.cache.get("welcomer", member.guild.id, "leave_channel"))
            await channel.send(text, delete_after=self.bot.cache.get("welcomer", member.guild.id, "leave_delafter"))

        if self.bot.cache.get("welcomer", member.guild.id, "leave_embedtoggle"):

            emb_dict = self.bot.cache.get("welcomer", member.guild.id, "leave_embedmsg")
            emb_dict = self.value_replacer(emb_dict.copy(), member)
            if "author" in emb_dict:
                emb_dict["author"] = self.value_replacer(emb_dict["author"], member)
            if "footer" in emb_dict:
                emb_dict["footer"] = self.value_replacer(emb_dict["footer"], member)
            if "fields" in emb_dict:
                for field in emb_dict["fields"]:
                    emb_dict["fields"] = self.value_replacer(field["name"], member)
                    emb_dict["fields"] = self.value_replacer(field["value"], member)

            content = None
            if "plainText" in emb_dict.keys():
                content = emb_dict["plainText"]

            channel = self.bot.get_channel(self.bot.cache.get("welcomer", member.guild.id, "leave_channel"))
            await channel.send(content=content, 
                               embed=discord.Embed.from_dict(emb_dict),
                               delete_after=self.bot.cache.get("welcomer", member.guild.id, "leave_delafter"))

        else:
            return

    @commands.Cog.listener('on_member_join')
    async def member_join_log(self, member):
        if not (cid := self.bot.cache.get("logging", member.guild.id, "join_channel")):
            return

        c = member.guild.get_channel(cid)
        if not c:
            return await warn(self.bot, "Member Join", member.guild, "Channel does not exist in this guild anymore!")

        e = discord.Embed(
            timestamp = datetime.utcnow(),
            color=0x5eb876
        )

        if member.bot:
            e.title = _("A bot has been added to the server!")

            try:
                info = await self.bot.dblpy.get_bot_info(member.id)
                d = []
                nf = _("Not found...")
                d.append(_("**Prefix:**") + f" {info.get('prefix')}")
                d.append(_("**Website:**") + f" {info.get('website') or nf}")
                d.append(_("**Support:**") + f" {('https://discord.gg/'+ info.get('support')) or nf}")
                d.append(_("**Server Count:**") + f" {info.get('server_count'):,d}")
                d.append(_("**Current Vote Count:**") + f" {info.get('monthlyPoints')}")
                i = "\n".join(d)
                e.description = _("__Bot info:__") + f"\n{i}"
            except:
                e.description = _("Could not find any information about this bot...")

        else:
            e.title= _("New member joined the server!")

            info = []
            info.append(_("**Name:**") + f" {member}")
            info.append(_("**ID:**") + f" {member.id}")
            info.append(_("**Created at:**") + f" {ht.date_time(member.created_at)} ({ht.timesince(member.created_at)})")
            i = "\n".join(info)
            e.description = _("__User info:__") + f"\n{i}"


        e.set_thumbnail(url=member.avatar.with_static_format("png"))
        e.set_author(icon_url=member.avatar.with_static_format("png"), name=member)
        e.set_footer(text=_("Joined at"))

        await c.send(embed=e)

    @commands.Cog.listener('on_member_remove')
    async def member_leave_log(self, member):
        if member.id in self.bot.cache.modactions:
            self.bot.cache.modactions.remove(member.id)
            return

        if not (cid := self.bot.cache.get("logging", member.guild.id, "join_channel")):
            if not (cid := self.bot.cache.get("logging", member.guild.id, "mod_channel")):
                return

        c = member.guild.get_channel(cid)
        if not c:
            return await warn(self.bot, "Member Leave", member.guild, "Channel does not exist in this guild anymore!")

        await asyncio.sleep(1)
        if member.guild.me.guild_permissions.ban_members:
            try:
                await member.guild.fetch_ban(member)
                return
            except:
                pass

        audit = False
        if member.guild.me.guild_permissions.view_audit_log:
            audit = True

            action = await member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1).flatten() 
            if action:
                action = action[0]
                if action.target.id == member.id and (action.created_at > datetime.utcnow()-timedelta(minutes=1)):
                    self.bot.dispatch("kick", m_action(target=member, mod=action.user, guild=member.guild, reason=action.reason))
                    return

        e = discord.Embed(
            timestamp = datetime.utcnow(),
            color=0x5eb876
        )

        e.title= _("A member left or was kicked")

        info = []
        info.append(_("**Name:**") + f" {member}")
        info.append(_("**ID:**") + f" {member.id}")
        info.append(_("**Created at:**") + f" {ht.date_time(member.created_at)} ({ht.timesince(member.created_at)})")
        info.append(_("**Joined at:**") + f" {ht.date_time(member.joined_at)} ({ht.timesince(member.joined_at)})")
        roles = f" {', '.join([r.mention for r in member.roles if not r.is_default()][:10])} "
        if len(member.roles) > 10:
            roles += _("*+ {0} more...*").format(str(len(member.roles)-10))
        info.append(_("**Roles:**") + roles)
        i = "\n".join(info)
        e.description = _("__User info:__") + f"\n{i}"


        e.set_thumbnail(url=member.avatar.with_static_format("png"))
        e.set_author(icon_url=member.avatar.with_static_format("png"), name=member)

        if not audit:
            e.set_footer(text=_("I could not check if this member was kicked or just left... If you want me to log them separately, I need permissions to view the audit logs!"))

        await c.send(embed=e)

def setup(bot):
    pass
