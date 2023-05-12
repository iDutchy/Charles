import asyncpg
from db import BaseUrls

class DB:
    pool = None

    @classmethod
    async def create_pool(cls):
        if cls.pool:
            return
        cls.pool = await asyncpg.create_pool(dsn=BaseUrls.db)

    @classmethod
    async def fetch(cls, query, *args, timeout=None):
        if not cls.pool:
            await cls.create_pool()
        return await cls.pool.fetch(query, *args, timeout=timeout)
    
    @classmethod
    async def fetchval(cls, query, *args, column=0, timeout=None):
        if not cls.pool:
            await cls.create_pool()
        return await cls.pool.fetchval(query, *args, column=0, timeout=None)

    @classmethod
    async def fetchrow(cls, query, *args, timeout=None):
        if not cls.pool:
            await cls.create_pool()
        return await cls.pool.fetchrow(query, *args, timeout=None)

    @classmethod
    async def execute(cls, query, *args, timeout=None):
        if not cls.pool:
            await cls.create_pool()
        return await cls.pool.execute(query, *args, timeout=timeout)

    @classmethod
    async def executemany(cls, command: str, args, *, timeout: float=None):
        if not cls.pool:
            await cls.create_pool()
        return await cls.pool.executemany(command, args, timeout=timeout)

    @classmethod
    async def close(cls):
        if not cls.pool:
            return
        return await cls.pool.close()

    @classmethod
    async def add_guild(cls, guild_id: int):
        if not cls.pool:
            await cls.create_pool()
        await cls.pool.execute("INSERT INTO guilds VALUES($1)", guild_id)
        await cls.pool.execute("INSERT INTO guildsettings(guild_id) VALUES($1)", guild_id)
        await cls.pool.execute("INSERT INTO module_settings(guild_id) VALUES($1)", guild_id)
        await cls.pool.execute("INSERT INTO category_settings(guild_id) VALUES($1)", guild_id)
        await cls.pool.execute("INSERT INTO logging(guild_id) VALUES($1)", guild_id)
        await cls.pool.execute("INSERT INTO welcoming(guild_id) VALUES($1)", guild_id)
        await cls.pool.execute("INSERT INTO role_settings(guild_id) VALUES($1)", guild_id)

    @classmethod
    async def delete_guild(cls, guild_id: int):
        await cls.pool.execute("DELETE FROM guilds WHERE guild_id = $1", guild_id)

    @classmethod
    async def insert(cls, *, table: str, columns: list, values: list):
        if not cls.pool:
            await cls.create_pool()
        return await cls.pool.execute("INSERT INTO {table}({columns}) VALUES({values})".format(table=table, columns=", ".join(columns), values=", ".join([f"${x}" for x in range(len(columns))])), *values)

    @classmethod
    async def update(cls, *, table: str, column: str, value: str, guild_id: int=None, user_id=None):
        if not cls.pool:
            await cls.create_pool()
        if guild_id and user_id:
            raise ValueError("Can not update data for Guild and User in 1 update")
        if guild_id or user_id:
            return await cls.pool.execute("UPDATE {table} SET {column} = {value} WHERE {id_type} = {_id}".format(table=table, column=column, value=value, id_type="guild_id" if guild_id else "user_id", _id=_id))
        else:
            return await cls.pool.execute("UPDATE {table} SET {column} = {value}".format(table=table, column=column, value=value))