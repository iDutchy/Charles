import discord
from core.cog import SubCog
from core.commands import groupExtra
from utils import checks


class Settings(SubCog, category="Settings"):
    def __init__(self, bot):
        self.bot = bot

    @checks.is_owner()
    @groupExtra(category="Settings", aliases=['botblock', 'block'], invoke_without_command=True)
    async def blacklist(self, ctx):
        await ctx.send_help(ctx.command)

    @checks.is_owner()
    @blacklist.command(name="guild")
    async def blacklist_guild(self, ctx, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send("No guild found with that ID!")
        db_check = await self.bot.db.fetchval("SELECT guild_id FROM blacklists WHERE guild_id = $1", guild.id)

        if db_check is not None:
            return await ctx.send("This guild is already blacklisted!")

        await self.bot.db.execute("INSERT INTO blacklists(guild_id) VALUES ($1)", guild.id)
        self.bot.cache.update("blacklist", "guild", guild.id)

        await ctx.send(f"Guild `{guild.name}` has been added to the blacklist!")

        try:
            await guild.leave()
        except Exception:
            pass

    @checks.is_owner()
    @blacklist.command(name="user")
    async def blacklist_user(self, ctx, user: discord.User):
        db_check = await self.bot.db.fetchval("SELECT user_id FROM blacklists WHERE user_id = $1", user.id)

        if db_check is not None:
            return await ctx.send("This user is already blacklisted!")

        await self.bot.db.execute("INSERT INTO blacklists(user_id) VALUES ($1)", user.id)
        self.bot.cache.update("blacklist", "user", user.id)

        await ctx.send(f"User `{user}` has been added to the blacklist!")

    @checks.is_owner()
    @blacklist.command(name="dm")
    async def blacklist_user_dm(self, ctx, user: discord.User):
        db_check = await self.bot.db.fetchval("SELECT user_id_dm FROM blacklists WHERE user_id_dm = $1", user.id)

        if db_check is not None:
            return await ctx.send("This user is already DM blacklisted!")

        await self.bot.db.execute("INSERT INTO blacklists(user_id_dm) VALUES ($1)", user.id)
        self.bot.cache.update("blacklist", "dm", user.id)

        await ctx.send(f"User `{user}` has been added to the DM blacklist!")

    @checks.is_owner()
    @groupExtra(category="Settings", aliases=['botunblock', 'unblock'], invoke_without_command=True)
    async def whitelist(self, ctx):
        await ctx.send_help(ctx.command)

    @checks.is_owner()
    @whitelist.command(name="guild")
    async def whitelist_guild(self, ctx, guild_id: int):
        if guild_id not in self.bot.cache.get("blacklist", "guild"):
            return await ctx.send("A guild with that ID has not been blacklisted!")

        await self.bot.db.execute("DELETE FROM blacklists WHERE guild_id = $1", guild_id)
        self.bot.cache.update("blacklist", "guild", guild_id)

        await ctx.send(f"Guild `{guild_id}` has been removed from the blacklist!")

    @checks.is_owner()
    @whitelist.command(name="user")
    async def whitelist_user(self, ctx, user: discord.User):
        db_check = await self.bot.db.fetchval("SELECT user_id FROM blacklists WHERE user_id = $1", user.id)

        if db_check is None:
            return await ctx.send("This user is not blacklisted!")

        await self.bot.db.execute("DELETE FROM blacklists WHERE user_id = $1", user.id)
        self.bot.cache.update("blacklist", "user", user.id)

        await ctx.send(f"User `{user}` has been removed from the blacklist!")

    @checks.is_owner()
    @whitelist.command(name="dm")
    async def whitelist_user_dm(self, ctx, user: discord.User):
        db_check = await self.bot.db.fetchval("SELECT user_id_dm FROM blacklists WHERE user_id_dm = $1", user.id)

        if db_check is None:
            return await ctx.send("This user is not blacklisted from DMs!")

        await self.bot.db.execute("DELETE FROM blacklists WHERE user_id_dm = $1", user.id)
        self.bot.cache.update("blacklist", "dm", user.id)

        await ctx.send(f"User `{user}` has been removed from the DM blacklist!")


def setup(bot):
    pass
