import asyncio
import importlib
import json
import types
from collections import Counter

import topgg
import discord
import prettify_exceptions
import toml
from db import tokens
from discord.ext import commands

from . import cache, context, database, i18n, modules, objects, themes, util

# import multiprocessing as mp

# from cogs.info.help import HelpCommand

intents = discord.Intents(
    guilds=True,  # guild/channel join/remove/update
    members=True,  # member join/remove/update
    bans=True,  # member ban/unban
    emojis=False,  # emoji update
    integrations=False,  # integrations update
    webhooks=False,  # webhook update
    invites=False,  # invite create/delete
    voice_states=True,  # voice state update
    presences=False,  # member/user update for games/activities
    guild_messages=True,  # message create/update/delete
    dm_messages=True,  # message create/update/delete
    guild_reactions=True,  # reaction add/remove/clear
    dm_reactions=True,  # reaction add/remove/clear
    guild_typing=False,  # on typing
    dm_typing=False,  # on typing
    message_content=True,  # message content (for commands)
)

mentions = discord.AllowedMentions(
    roles=True,
    users=True,
    everyone=False
)

member_cache = discord.MemberCacheFlags(
    # online=False,
    voice=True,
    joined=True
)

# help_command = HelpCommand(
#     command_attrs=dict(
#         aliases=['h', 'cmds', 'commands']
#     )
# )

async def get_prefix(bot, message):
    if not message.guild:
        custom_prefix = "c?"
        return custom_prefix

    gcache = bot.get_cache(message.guild.id)
    ucache = bot.get_user_cache(message.author.id)
    custom_prefix = [gcache.prefix]
    if (pre := ucache.prefixes.get(message.guild.id)) is not None:
        custom_prefix.append(pre)
    if message.author.id == bot.owner_id:
        if '' not in custom_prefix:
            custom_prefix.append('')
    return commands.when_mentioned_or(*custom_prefix)(bot, message)

class BotCore(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        self.to_load = kwargs.pop('extensions')
        super().__init__(*args,
                  command_prefix = get_prefix,
                       reconnect = True,
                case_insensitive = True,
                        owner_id = 171539705043615744,
                allowed_mentions = mentions,
                         intents = intents,
                     embed_color = 0xF1F33F,
              member_cache_flags = member_cache,
         chunk_guilds_at_startup = False,
         # case_insensitive_prefix = True,
         # help_command = help_command,
         **kwargs)
        # Caching
        self.votereminders = {}
        self.translations = {}
        self.text_cache = {}
        self.logs = {}
        self._categories = {}
        self.socket_stats = Counter()
        # self.mp_processes = []
        self._user_cache = {}
        self._guild_cache = {}

        # Bot vars
        # self.ipc = ipc.Server(self, "0.0.0.0", 6666, "poggers")
        self.loop = asyncio.get_event_loop()
        self.session = None
        self.dblpy = topgg.DBLClient(bot=self, token=tokens.DBL, session=self.session)
        self.config = None # IN CACHE \\ NOT IN USE YET
        self.is_ready =  False
        self.theme = None

    @property
    def owner(self):
        return self.get_user(self.owner_id)

    def get_cache(self, guild_id):
        guild = self._guild_cache.get(guild_id)
        if guild is None:
            self.create_guild_cache(guild_id)
        return self._guild_cache.get(guild_id)

    def get_user_cache(self, user_id):
        user = self._user_cache.get(user_id)
        if user is None:
            self.create_user_cache(user_id)
        return self._user_cache.get(user_id)

    def create_guild_cache(self, guild_id):
        self._guild_cache[guild_id] = objects.GuildData(guild_id, {})

    def create_user_cache(self, user_id):
        self._user_cache[user_id] = objects.UserData(user_id, {})

    def remove_listener(self, func, name=None):
        name = func.__name__ if name is None else name

        if name in self.extra_events:
            try:
                self.extra_events[name].remove(func)
            except ValueError:
                raise ValueError(f"Func {func} not found under {name}")

    def add_cog(self, cog):
        if not isinstance(cog, commands.Cog):
            raise TypeError('cogs must derive from Cog')

        cog = cog._inject(self)
        self._BotBase__cogs[cog.__cog_name__] = cog
        return cog

    @property
    def categories(self):
        return types.MappingProxyType(self._categories)

    @property
    def themes(self):
        return types.MappingProxyType({theme:getattr(themes, theme)(self) for theme in themes.__all__})

    def get_url(self, site):
        return self.config['urls'].get(site.lower(), None)

    def get_token(self, token):
        return self.config['tokens'].get(token.upper(), None)

    def exception(self, exc):
        prettify_exceptions.DefaultFormatter().theme['_ansi_enabled'] = False
        return ''.join(prettify_exceptions.DefaultFormatter().format_exception(type(exc), exc, exc.__traceback__)).strip().replace('`', '`\u200b')

    async def reload(self):
        await self.cache.update_db()
        self.cache.clear_all()
        importlib.reload(cache)
        importlib.reload(context)
        importlib.reload(database)
        importlib.reload(util)
        importlib.reload(modules)
        await self.load_bot()

    async def load_bot(self):
        await cache.CacheManager.refresh()
        self.cache = cache.CacheManager()
        self.utils = util.Utils()
        self.db = database.DB()
        self.mm = modules.ModuleManager(self)
        self.topgghook = topgg.WebhookManager(self).dbl_webhook(route="/dbl", auth_key=tokens.DBL)
        self.topgghook.run(5000)
        await self.load_extension("jishaku")

    def get_category(self, category):
        if category.title() not in self.categories.keys():
            return None

        return self.categories[category.title()]

    async def on_message(self, msg):
        if not self.is_ready or msg.author.bot:
            return

        if msg.guild:
            await self.process_commands(msg)

    async def on_connect(self):
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening,
                name="my engines booting up...")
            )

    async def on_ready(self):
        print(f'[CONNECT] Logged in as:\n{self.user} (ID: {self.user.id})\n')

        if not hasattr(self, 'uptime'):
            self.uptime = discord.utils.utcnow()

        if not self.is_ready:
            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.competing,
                    name="Roblox")
                )

            self.is_ready = True

    async def start(self, token):
        await self.bot_start()
        await super().start(token)

    async def bot_logout(self):
        # for p in self.mp_processes:
        #     p.kill()
        await self.cache.update_db()
        self.cache.clear_all()
        await self.dblpy.close()
        await self.topgghook.close()
        await self.utils.close_session()
        await self.db.close()
        await super().close()

    async def bot_start(self):
        data = toml.load("db/config.toml")
        self.theme = self.themes[data['settings'].pop("THEME", "Default")]
        self.config = data
        await self.load_bot()
        await self.utils.create_session()
        self.session = self.utils.session
        self.blacklists = {"dm": [x for x, in await self.db.fetch("SELECT user_id_dm FROM blacklists")], "user": [x for x, in await self.db.fetch("SELECT user_id FROM blacklists")], "guild": [x for x, in await self.db.fetch("SELECT guild_id FROM blacklists")]}
        self.translators = [x for x, in await self.db.fetch("SELECT user_id FROM translators")]

        users = await cache.ObjectCache.load_all_users()
        for k,v in users.items():
            self._user_cache[k] = objects.UserData(k, v)

        guilds = await cache.ObjectCache.load_all_guilds()
        for k,v in guilds.items():
            self._guild_cache[k] = objects.GuildData(k, v)

        for ext in self.to_load:
            try:
                self.load_extension(ext)
                # await self.mm.load(ext)
            except Exception as e:
                print(e)

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=context.MyContext)
