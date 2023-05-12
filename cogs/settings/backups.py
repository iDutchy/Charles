import discord
import random
import asyncio

from discord.ext import commands
from core.commands import commandExtra
from utils import checks
from core import i18n
from datetime import datetime
from core.cog import SubCog

class Backups(SubCog, category="Server Backups"):
    def __init__(self, bot):
        self.bot = bot

    @checks.has_permissions(administrator=True)
    @commandExtra(category="Server Backups")
    async def backup(self, ctx):
        backupID = random.randint(1, 9999)
        await self.bot.db.execute("INSERT INTO backups VALUES($1, $2, $3, $4, $5, $6, $7)", backupID, ctx.author.id, str(datetime.utcnow().strftime("%b %d, %Y - %H:%M:%S")), ctx.guild.name, True, False, None)

        for cat in ctx.guild.categories:
            await self.bot.db.execute("INSERT INTO channel_backups(backup_id, cat_name, cat_restore, owner) VALUES($1, $2, $3, $4)", backupID, cat.name, True, ctx.author.id)

        for c in ctx.guild.text_channels:
            cat = c.category.name if c.category else None
            await self.bot.db.execute("INSERT INTO channel_backups(backup_id, text_name, text_topic, text_pos, text_slow, text_nsfw, text_cat, text_restore, owner) VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9)", backupID, c.name, c.topic, c.position, c.slowmode_delay, c.is_nsfw(), cat, True, ctx.author.id)

        for v in ctx.guild.voice_channels:
            cat = c.category.name if c.category else None
            await self.bot.db.execute("INSERT INTO channel_backups(backup_id, voice_name, voice_pos, voice_cat, voice_limit, voice_restore, owner) VALUES($1, $2, $3, $4, $5, $6, $7)", backupID, v.name, v.position, cat, v.user_limit, True, ctx.author.id)

        for r in ctx.guild.roles:
            if r.name == "@everyone":
                continue
            await self.bot.db.execute("INSERT INTO role_backups VALUES($1, $2, $3, $4, $5, $6, $7, $8)", backupID, r.name, r.permissions.value, str(r.color), r.mentionable, r.hoist, True, ctx.author.id)

        for e in ctx.guild.emojis:
            await self.bot.db.execute("INSERT INTO emoji_backups VALUES($1, $2, $3, $4, $5)", backupID, e.name, str(e.url), True, ctx.author.id)

        await ctx.send(_("Backup with ID `{0}` has been created!").format(str(backupID)))

    @commandExtra(category="Server Backups", name="backup-list", aliases=['restore-list'])
    async def list_backups(self, ctx):
        backups = await self.bot.db.fetch("SELECT backup_id, server, backup_time FROM backups WHERE owner = $1", ctx.author.id)
        if len(backups) == 0:
            return await ctx.send(_("You have not made any backups yet."))

        e = discord.Embed(color=ctx.embed_color,
                          title=_("Backups made:"))
        e.set_author(name=ctx.author,icon_url=ctx.author.avatar.with_static_format("png"))

        for b in backups:
            e.add_field(name=_("ID: {0}").format(str(b['backup_id'])), value=_("**Server:** {0}\n**Created at:** {1}").format(b['server'], b['backup_time']), inline=False)
        await ctx.send(embed=e)

    @commandExtra(category="Server Backups", name="reset-backup")
    async def reset_backup(self, ctx, id: int):
        i = str(id)
        backups = await self.bot.db.fetchval("SELECT backup_id FROM backups WHERE owner = $1 AND backup_id = $2", ctx.author.id, id)
        if backups is None:
            return await ctx.send(_("You do not have a backup with that ID."))

        await self.bot.db.execute("UPDATE channel_backups SET text_restore = $3, voice_restore = $3, cat_restore = $3 WHERE owner = $1 AND backup_id = $2", ctx.author.id, id, True)
        await self.bot.db.execute("UPDATE emoji_backups SET emoji_restore = $3 WHERE owner = $1 AND backup_id = $2", ctx.author.id, id, True)
        await self.bot.db.execute("UPDATE role_backups SET role_restore = $3 WHERE owner = $1 AND backup_id = $2", ctx.author.id, id, True)
        await self.bot.db.execute("UPDATE backups SET guild_id = $3 WHERE owner = $1 AND backup_id = $2", ctx.author.id, id, None)

        await ctx.send(_("Backup `{0}` has been reset and can now be used again.").format(i))

    @commandExtra(category="Server Backups", name="delete-backup")
    async def delete_backup(self, ctx, id: int):
        i = str(id)

        backups = await self.bot.db.fetchval("SELECT backup_id FROM backups WHERE owner = $1 AND backup_id = $2", ctx.author.id, id)
        if backups is None:
            return await ctx.send(_("You do not have a backup with that ID."))

        msg = await ctx.send(_("Are you sure you wish to delete backup {0}? **This cannot be undone!**").format(i))
        await msg.add_reaction("<:tickYes:315009125694177281>")
        await msg.add_reaction("<:tickNo:315009174163685377>")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["<:tickYes:315009125694177281>", "<:tickNo:315009174163685377>"]

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send(_("You took to long to reply, command has been cancelled."))
        else:
            if str(reaction.emoji) == "<:tickNo:315009174163685377>":
                await msg.delete()
                return await ctx.send(_("Ok, command has been cancelled."), delete_after=10)
            elif str(reaction.emoji) == "<:tickYes:315009125694177281>":
                await msg.delete()
                await self.bot.db.execute("DELETE FROM backups WHERE owner = $1 AND backup_id = $2", ctx.author.id, id)
                await ctx.send(_("Ok, backup {0} has been deleted!").format(i), delete_after=10)

    @commandExtra(category="Server Backups")
    async def restore(self, ctx, id: int, guild: int):
        backup = await self.bot.db.fetchrow("SELECT * FROM backups WHERE owner = $1 AND backup_id = $2", ctx.author.id, id)
        if not backup:
            return await ctx.send(_("You do not have a backup with that ID."))

        g = self.bot.get_guild(guild)
        if g is None:
            return await ctx.send(_("Could not find a guild with that ID. Are you sure I am in that guild?"))
        i = str(id)

        if len(g.channels) > 0:
            return await ctx.send(_("There are still category, text or voice channels in this server. Please make sure this server is completely empty before restoring a backup!"))

        if len(g.roles) > 2:
            return await ctx.send(_("There are still roles in this server. Please make sure this server is completely empty before restoring a backup!"))

        if len(g.emojis) > 0:
            return await ctx.send(_("There are still emojis in this server. Please make sure this server is completely empty before restoring a backup!"))

        if g.owner_id != ctx.author.id:
            return await ctx.send(_("You need to be the owner of the server to load a restore file"))

        failures = False

        if backup['usable'] == False:
            return await ctx.send(_("This backup cannot be used. Please run `reset-backup {0}` to fix this.").format(i))

        if backup['fix_only']:
            return await ctx.send(_("You already attempted to restore this backup, please use the `fix-restore` command to fix everything that hasnt been restored yet."))

        text = await self.bot.db.fetch("SELECT text_name, text_topic, text_pos, text_slow, text_nsfw, text_cat FROM channel_backups WHERE owner = $1 AND backup_id = $2 AND text_name IS NOT NULL", ctx.author.id, id)
        voice = await self.bot.db.fetch("SELECT voice_name, voice_pos, voice_cat, voice_limit FROM channel_backups WHERE owner = $1 AND backup_id = $2 AND voice_name IS NOT NULL", ctx.author.id, id)
        cat = await self.bot.db.fetch("SELECT cat_name FROM channel_backups WHERE owner = $1 AND backup_id = $2 AND cat_name IS NOT NULL", ctx.author.id, id)
        roles = await self.bot.db.fetch("SELECT role_name, role_perms, role_color, role_mention, role_hoist FROM role_backups WHERE owner = $1 AND backup_id = $2", ctx.author.id, id)
        emoji = await self.bot.db.fetch("SELECT emoji_name, emoji_url FROM emoji_backups WHERE owner = $1 AND backup_id = $2", ctx.author.id, id)

        m = "<:tick:528774982067814441> | " + _("Initialisation completed!")

        msg = await ctx.send("<a:discord_loading:587812494089912340> | " + _("Initiating restore..."))

        await asyncio.sleep(1.5)

        await msg.edit(content=f"{m}\n<a:discord_loading:587812494089912340> | " + _("Restoring `Categories`..."))

        async def create_category():
            await g.create_category_channel(name=c["cat_name"])

        c_count = 0

        for c in cat:
            try:
                await asyncio.wait_for(create_category(), timeout=10.0)
                c_count += 1
                await self.bot.db.execute("UPDATE channel_backups SET cat_restore = $4 WHERE owner = $1 AND backup_id = $2 AND cat_name = $3", ctx.author.id, id, c["cat_name"], False)
            except (asyncio.TimeoutError, discord.HTTPException):
                m += '\n<:warn:620414236010741783> | ' + _("Categories restored!") + f' {c_count}/{len(cat)}'
                failures = True
                break
        else:
            m += f"\n<:tick:528774982067814441> | {c_count} " + _("Categories restored!")

        await msg.edit(content=f"{m}\n<a:discord_loading:587812494089912340> | " + _("Restoring `Text Channels`..."))

        async def create_text():
            cat = discord.utils.get(g.categories, name=t["text_cat"]) if t["text_cat"] else None
            await g.create_text_channel(name=t["text_name"], position=t["text_pos"], topic=t["text_topic"], slowmode_delay=t["text_slow"], nsfw=t["text_nsfw"], category=cat, reason="Server Backup")

        t_count = 0
        for t in text:
            try:
                await asyncio.wait_for(create_text(), timeout=10.0)
                t_count += 1
                await self.bot.db.execute("UPDATE channel_backups SET text_restore = $4 WHERE owner = $1 AND backup_id = $2 AND text_name = $3", ctx.author.id, id, t["text_name"], False)
            except (asyncio.TimeoutError, discord.HTTPException): 
                m += '\n<:warn:620414236010741783> | ' + _("Text Channels restored!") + f' {t_count}/{len(text)}'
                failures = True
                break
        else:
            m += f"\n<:tick:528774982067814441> | {t_count} " + _("Text Channels restored!")

        await msg.edit(content=f"{m}\n<a:discord_loading:587812494089912340> | " + _("Restoring `Voice Channels`..."))

        async def create_voice():
            cat = discord.utils.get(g.categories, name=v["voice_cat"]) if v["voice_cat"] else None
            await g.create_voice_channel(name=v["voice_name"], position=v["voice_pos"], category=cat, user_limit=v["voice_limit"], reason="Server Backup")

        v_count = 0
        for v in voice:
            try:
                await asyncio.wait_for(create_voice(), timeout=10.0)
                v_count += 1
                await self.bot.db.execute("UPDATE channel_backups SET voice_restore = $4 WHERE owner = $1 AND backup_id = $2 AND voice_name = $3", ctx.author.id, id, v["voice_name"], False)
            except (asyncio.TimeoutError, discord.HTTPException): 
                m += '\n<:warn:620414236010741783> | ' + _("Voice Channels restored!") + f' {v_count}/{len(voice)}'
                failures = True
                break
        else:
            m += f"\n<:tick:528774982067814441> | {v_count} " + _("Voice Channels restored!")

        await msg.edit(content=f"{m}\n<a:discord_loading:587812494089912340> | " + ("Restoring `Roles`..."))

        async def create_role():
            perms = discord.Permissions(r["role_perms"])
            col = r["role_color"].replace("#", "0x")
            color = discord.Color(int(col, 16))
            await g.create_role(name=r["role_name"], permissions=perms, color=color, mentionable=r["role_mention"], hoist=r["role_hoist"], reason="Server Backup")

        r_count = 0
        for r in roles[::-1]:
            try:
                await asyncio.wait_for(create_role(), timeout=10.0)
                r_count += 1
                await self.bot.db.execute("UPDATE role_backups SET role_restore = $4 WHERE owner = $1 AND backup_id = $2 AND role_name = $3", ctx.author.id, id, r["role_name"], False)
            except (asyncio.TimeoutError, discord.HTTPException):
                m += '\n<:warn:620414236010741783> | ' + _("Roles restored!") + f' {r_count}/{len(roles)}'
                failures = True
                break
        else:
            m += f"\n<:tick:528774982067814441> | {r_count} " + _("Roles restored!")

        await msg.edit(content=f"{m}\n<a:discord_loading:587812494089912340> | " + _("Restoring `Emojis`..."))

        async def create_emoji():
            async with self.bot.session.get(e["emoji_url"]) as r:
                img = await r.read()
            await g.create_custom_emoji(name=e["emoji_name"], image=img, reason="Server Backup")

        e_count = 0
        for e in emoji:
            try:
                await asyncio.wait_for(create_emoji(), timeout=10.0)
                e_count += 1
                await self.bot.db.execute("UPDATE emoji_backups SET emoji_restore = $4 WHERE owner = $1 AND backup_id = $2 AND emoji_name = $3", ctx.author.id, id, e["emoji_name"], False)
            except (asyncio.TimeoutError, discord.HTTPException): 
                m += '\n<:warn:620414236010741783> | ' + _("Emojis restored!") + f' {e_count}/{len(emoji)}'
                failures = True
                break
        else:
            m += f"\n<:tick:528774982067814441> | {e_count} " + _("Emojis restored!")

        if failures:
            await msg.edit(content=f"{m}\n\n<:tick:528774982067814441> | " + _("Guild restore complete, but there were some issues... I either got ratelimited (try doing the `fix-restore` command later) or you've reached a limit (more info: <https://discordia.me/en/server-limits>)."))
        else:
            await msg.edit(content=f"{m}\n\n<:tick:528774982067814441> | " + _("Guild restore complete!"))
            if c_count == 0 and t_count == 0 and v_count == 0 and r_count == 0 and e_count == 0:
                await self.bot.db.execute("UPDATE backups SET usable = $3 WHERE owner = $1 AND backup_id = $2", ctx.author.id, id, False)

        await self.bot.db.execute("UPDATE backups SET guild_id = $3, fix_only = $4 WHERE owner = $1 AND backup_id = $2", ctx.author.id, id, g.id, True)

    @commandExtra(category="Server Backups", name="fix-restore")
    async def fix_restore(self, ctx, id: int):
        backup = await self.bot.db.fetchrow("SELECT * FROM backups WHERE owner = $1 AND backup_id = $2", ctx.author.id, id)
        if not backup:
            return await ctx.send(_("You do not have a backup with that ID."))

        g = self.bot.get_guild(backup["guild_id"])
        if g is None:
            return await ctx.send("I could not find the guild this backup was used in. Are you sure I am (still) in that guild?")

        if g.owner_id != ctx.author.id:
            return await ctx.send(_("You need to be the owner of the server to load a restore file"))
        i = str(id)

        failures = False

        if not backup["usable"]:
            return await ctx.send(_("This backup cannot be used. Please run `reset-backup {0}` to fix this.").format(i))

        if not backup["fix_only"]:
            return await ctx.send(_("This is still a fresh backup, please use the regular `restore` command in stead of the fix. :)"))


        text = await self.bot.db.fetch("SELECT text_name, text_topic, text_pos, text_slow, text_nsfw, text_cat FROM channel_backups WHERE owner = $1 AND backup_id = $2 AND text_restore = $3", ctx.author.id, id, True)
        voice = await self.bot.db.fetch("SELECT voice_name, voice_pos, voice_cat, voice_limit FROM channel_backups WHERE owner = $1 AND backup_id = $2 AND voice_restore = $3", ctx.author.id, id, True)
        cat = await self.bot.db.fetch("SELECT cat_name FROM channel_backups WHERE owner = $1 AND backup_id = $2 AND cat_restore = $3", ctx.author.id, id, True)
        roles = await self.bot.db.fetch("SELECT role_name, role_perms, role_color, role_mention, role_hoist FROM role_backups WHERE owner = $1 AND backup_id = $2 AND role_restore = $3", ctx.author.id, id, True)
        emoji = await self.bot.db.fetch("SELECT emoji_name, emoji_url FROM emoji_backups WHERE owner = $1 AND backup_id = $2 AND emoji_restore = $3", ctx.author.id, id, True)

        m = "<:tick:528774982067814441> | " + _("Initialisation completed!")
        msg = await ctx.send("<a:discord_loading:587812494089912340> | Initiating fix...")
        await asyncio.sleep(1.5)

        await msg.edit(content=f"{m}\n<a:discord_loading:587812494089912340> | " + _("Attempting to fix `Categories`..."))

        async def create_category():
            await g.create_category_channel(name=c["cat_name"])

        c_count = 0
        for c in cat:
            try:
                await asyncio.wait_for(create_category(), timeout=10.0)
                c_count += 1
                await self.bot.db.execute("UPDATE channel_backups SET cat_restore = $4 WHERE owner = $1 AND backup_id = $2 AND cat_name = $3", ctx.author.id, id, c["cat_name"], False)
            except (asyncio.TimeoutError, discord.HTTPException):
                m += '\n<:warn:620414236010741783> | ' + _("Categories could not be fixed! {0} were fixed.").format(str(c_count))
                failures = True
                break
        else:
            if c_count == 0:
                m += "\n<:tick:528774982067814441> | " + _("There were no Categories that needed to be fixed!")
            else:
                m += f"\n<:tick:528774982067814441> | {c_count} " + _("Categories fixed!")

        await msg.edit(content=f"{m}\n<a:discord_loading:587812494089912340> | " + _("Attempting to fix `Text Channels`..."))

        async def create_text():
            cat = discord.utils.get(g.categories, name=t["text_cat"]) if t["text_cat"] else None
            await g.create_text_channel(name=t["text_name"], position=t["text_pos"], topic=t["text_topic"], slowmode_delay=t["text_slow"], nsfw=t["text_nsfw"], category=cat, reason="Server Backup")

        t_count = 0
        for t in text:
            try:
                await asyncio.wait_for(create_text(), timeout=10.0)
                t_count += 1
                await self.bot.db.execute("UPDATE channel_backups SET text_restore = $4 WHERE owner = $1 AND backup_id = $2 AND text_name = $3", ctx.author.id, id, t["text_name"], False)
            except (asyncio.TimeoutError, discord.HTTPException):
                m += '\n<:warn:620414236010741783> | ' + _("Text Channels could not be fixed! {0} were fixed.").format(str(t_count))
                failures = True
                break
        else:
            if t_count == 0:
                m += "\n<:tick:528774982067814441> | " + _("There were no Text Channels that needed to be fixed!")
            else:
                m += f"\n<:tick:528774982067814441> | {t_count} " + _("Text Channels fixed!")

        await msg.edit(content=f"{m}\n<a:discord_loading:587812494089912340> | " + _("Attempting to fix `Voice Channels`..."))

        async def create_voice():
            cat = discord.utils.get(g.categories, name=v["voice_cat"]) if v["voice_cat"] else None
            await g.create_voice_channel(name=v["voice_name"], position=v["voice_pos"], category=cat, user_limit=v["voice_limit"], reason="Server Backup")

        v_count = 0
        for v in voice:
            try:
                await asyncio.wait_for(create_voice(), timeout=10.0)
                v_count += 1
                await self.bot.db.execute("UPDATE channel_backups SET voice_restore = $4 WHERE owner = $1 AND backup_id = $2 AND voice_name = $3", ctx.author.id, id, v["voice_name"], False)
            except (asyncio.TimeoutError, discord.HTTPException): 
                m += '\n<:warn:620414236010741783> | ' + _("Voice Channels could not be fixed! {0} were fixed.").format(str(v_count))
                failures = True
                break
        else:
            if v_count == 0:
                m += "\n<:tick:528774982067814441> | " + _("There were no Voice Channels that needed to be fixed!")
            else:
                m += f"\n<:tick:528774982067814441> | {v_count} " + _("Voice Channels fixed!")

        await msg.edit(content=f"{m}\n<a:discord_loading:587812494089912340> | " + _("Attempting to fix `Roles`..."))

        async def create_role():
            perms = discord.Permissions(r["role_perms"])
            col = r["role_color"].replace("#", "0x")
            color = discord.Color(int(col, 16))
            await g.create_role(name=r["role_name"], permissions=perms, color=color, mentionable=r["role_mention"], hoist=r["role_hoist"], reason="Server Backup")

        r_count = 0
        for r in roles[::-1]:
            try:
                await asyncio.wait_for(create_role(), timeout=10.0)
                r_count += 1
                await self.bot.db.execute("UPDATE role_backups SET role_restore = $4 WHERE owner = $1 AND backup_id = $2 AND role_name = $3", ctx.author.id, id, r["role_name"], False)
            except (asyncio.TimeoutError, discord.HTTPException):
                m += '\n<:warn:620414236010741783> | ' + _("Roles could not be fixed! {0} were fixed.").format(str(r_count))
                failures = True
                break
        else:
            if r_count == 0:
                m += "\n<:tick:528774982067814441> | " + _("There were no Roles that needed to be fixed!")
            else:
                m += f"\n<:tick:528774982067814441> | {r_count} " + _("Roles fixed!")

        await msg.edit(content=f"{m}\n<a:discord_loading:587812494089912340> | " + _("Attempting to fix `Emojis`..."))

        async def create_emoji():
            async with self.bot.session.get(e["emoji_url"]) as r:
                img = await r.read()
            await g.create_custom_emoji(name=e["emoji_name"], image=img, reason="Server Backup")

        e_count = 0
        for e in emoji:
            try:
                await asyncio.wait_for(create_emoji(), timeout=10.0)
                e_count += 1
                await self.bot.db.execute("UPDATE emoji_backups SET emoji_restore = $4 WHERE owner = $1 AND backup_id = $2 AND emoji_name = $3", ctx.author.id, id, e["emoji_name"], False)
            except (asyncio.TimeoutError, discord.HTTPException): 
                m += '\n<:warn:620414236010741783> | ' + _("Emojis could not be fixed! {0} were fixed.").format(str(e_count))
                failures = True
                break
        else:
            if e_count == 0:
                m += "\n<:tick:528774982067814441> | " + _("There were no Emojis that needed to be fixed!")
            else:
                m += f"\n<:tick:528774982067814441> | {e_count} " + _("Emojis fixed!")

        if failures:
            await msg.edit(content=f"{m}\n\n<:tick:528774982067814441> | " + _("Guild restore fix complete, but there were some issues... I either got ratelimited (try doing the `fix-restore` command later) or you've reached a limit (more info: <https://discordia.me/en/server-limits>)."))
        else:
            await msg.edit(content=f"{m}\n\n<:tick:528774982067814441> | " + _("Guild restore fix complete!"))
            if c_count == 0 and t_count == 0 and v_count == 0 and r_count == 0 and e_count == 0:
                await self.bot.db.execute("UPDATE backups SET usable = $3 WHERE owner = $1 AND backup_id = $2", ctx.author.id, id, False)

def setup(bot):
    pass