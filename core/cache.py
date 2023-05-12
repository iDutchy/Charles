import json
import os
import traceback
from collections import Counter, defaultdict

import aiofiles
from utils.utility import SizedDict

from .database import DB as db


class ObjectCache:
    @staticmethod
    async def load_all_guilds():
        cache = defaultdict(dict)
        for x in await db.fetch("SELECT * FROM guildsettings"):
            cache[x['guild_id']] = dict(x)

        for x in await db.fetch("SELECT * FROM module_settings"):
            cache[x['guild_id']]['module_settings'] = dict(x)

        for x in await db.fetch("SELECT * FROM category_settings"):
            cache[x['guild_id']]['category_settings'] = dict(x)

        for x in await db.fetch("SELECT guild_id, array_agg(command) AS commands FROM disabledcommands GROUP BY guild_id"):
            cache[x['guild_id']]["disabled_commands"] = x['commands']

        for x in await db.fetch("SELECT guild_id, array_agg(roast) AS roasts FROM custom_roasts GROUP BY guild_id"):
            cache[x['guild_id']]["custom_roasts"] = x['roasts']

        for x in await db.fetch("SELECT * FROM role_settings"):
            cache[x['guild_id']]['roles'] = dict(x)

        for x in await db.fetch("SELECT * FROM holiday_announcements"):
            cache[x['guild_id']]['holidays-announcements'] = dict(x)

        for x in await db.fetch("SELECT * FROM welcoming"):
            cache[x['guild_id']]['welcome-leave'] = dict(x)

        # -- RRQUERY = """SELECT #TODO: FIX SO IT DOESNT MAKE A DICT FOR ALL ROLES
        # --     (format(        # IN 1 MESSAGE
        # --         '{"message_id": "%s", "role_id": %s, "emoji": "%s"}',
        # --         message_id,
        # --         role_id,
        # --         emoji
        # --     ))::json AS data,
        # --     guild_id
        # -- FROM reactionroles"""

        for x in await db.fetch("SELECT * FROM reactionrole_settings"):
            if "reactionroles" not in cache[x['guild_id']]:
                cache[x['guild_id']]['reactionroles'] = {}
            cache[x['guild_id']]['reactionroles'][x['message_id']] = {'settings': dict(x), 'data': {}}

        for x in await db.fetch("SELECT * FROM  reactionrole_data"):
            cache[x['guild_id']]['reactionroles'][x['message_id']]['data'][x['emoji']] = x['role_id']

        for x in await db.fetch("SELECT * FROM perm_settings"):
            if 'perm_settings' not in cache[x['guild_id']]:
                cache[x['guild_id']]['perm_settings'] = {'allowed': defaultdict(list), 'denied': defaultdict(list)}
            if x['allow']:
                cache[x['guild_id']]['perm_settings']['allowed'][x['_id']].append(x['perm_type'])
            else:
                cache[x['guild_id']]['perm_settings']['denied'][x['_id']].append(x['perm_type'])

        return cache

    @staticmethod
    async def load_all_users():
        users = defaultdict(dict)
        for x in await db.fetch("SELECT * FROM votereminders"):
            users[x['user_id']]['voteremind'] = dict(x)

        for x in await db.fetch("SELECT user_id, array_agg(acknowledgement_type) as types FROM acknowledgements GROUP BY user_id"):
            users[x["user_id"]]['acknowledgements'] = x['types']

        for x in await db.fetch("SELECT user_id, array_agg(guild_id) as guilds, global FROM embed_mentions GROUP BY user_id, global"):
            users[x["user_id"]]['embed_mentions'] = dict(x)

        for x in await db.fetch("SELECT * FROM socials"):
            if 'socials' not in users[x["user_id"]]:
                users[x["user_id"]]['socials'] = {}
            users[x["user_id"]]['socials'][x['socialtype']] = x['social']

        for x in await db.fetchval("SELECT array_agg(user_id_dm) FROM blacklists WHERE user_id_dm IS NOT NULL"):
            users[x]['dm_blacklist'] = True

        for x in await db.fetchval("SELECT array_agg(user_id) FROM blacklists WHERE user_id IS NOT NULL"):
            users[x]['blacklist'] = True

        for x in await db.fetch("SELECT * FROM afk"):
            users[x['user_id']]['afk'] = dict(x)

        for x in await db.fetch("SELECT * FROM no_dms"):
            users[x['user_id']]['dms'] = False

        for x in await db.fetch("SELECT * FROM userprefixes"):
            if 'prefixes' not in users[x['user_id']]:
                users[x['user_id']]['prefixes'] = {}
            users[x['user_id']]['prefixes'] |= {x['guild_id']: x['prefix']}

        return users


class CacheError(Exception):
    pass


class CacheManager:
    blacklist = dict(dm=[], user=[], guild=[])
    categories = dict()
    cmd_stats = dict()
    config = dict()
    dms = dict()
    globaldisabled = dict()
    i18n = dict()
    logging = dict()
    modules = dict()
    past_invokes = SizedDict()
    prefix = dict()
    rr = defaultdict(dict)
    settings = dict()
    votereminders = dict()
    welcomer = dict()
    modactions = list()
    translate_sessions = dict()
    translate_contents = dict()
    cmd_help = dict()
    roles = dict()
    acknowledgements = dict()
    afk = dict()
    embed_mentions = dict()
    socials = defaultdict(dict)
    holiday_announcements = dict()

    @staticmethod
    def format_exception(exc):
        return "\n".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    # @classmethod
    # async def load_members(cls, bot):
    #     for guild in bot.guilds:
    #         await guild.chunk()

    @classmethod
    async def load_guilds(cls): #MOVED
        for x in await db.fetch("SELECT * FROM guilds"):
            cls.settings[x['guild_id']] = dict(disabled_commands=[])
            cls.modules[x['guild_id']] = dict()
            cls.categories[x['guild_id']] = dict()
            cls.logging[x['guild_id']] = dict()

    @classmethod
    async def load_settings(cls): #MOVED
        for x in await db.fetch("SELECT * FROM guildsettings"):
            cls.prefix[x['guild_id']] = x['prefix']
            cls.settings[x['guild_id']]["language"] = x['language']
            cls.settings[x['guild_id']]["color"] = x['embedcolor']
            cls.settings[x['guild_id']]["roastlevel"] = x['roastlevel']
            cls.settings[x['guild_id']]["joinrole_toggle"] = x['joinrole_toggle']
            cls.settings[x['guild_id']]["joinrole_human"] = x['joinrole_human']
            cls.settings[x['guild_id']]["joinrole_bot"] = x['joinrole_bot']
            cls.settings[x['guild_id']]["cb_emotion"] = x["cb_emotion"]
            cls.settings[x['guild_id']]["cb_mention"] = x["cb_mention"]
            cls.settings[x['guild_id']]['custom_roasts'] =[]

    @classmethod
    async def load_module_settings(cls): #MOVED
        for x in await db.fetch("SELECT * FROM module_settings"):
            for k, v in list(x.items())[1:]:
                cls.modules[x['guild_id']][k] = v

    @classmethod
    async def load_category_settings(cls): #MOVED
        for x in await db.fetch("SELECT * FROM category_settings"):
            for k, v in list(x.items())[1:]:
                cls.categories[x['guild_id']][k] = v

    @classmethod
    async def load_logging(cls): #MOVED
        for x in await db.fetch("SELECT * FROM logging"):
            for k, v in list(x.items())[1:]:
                cls.logging[x['guild_id']][k] = v

    @classmethod
    async def load_disabled_commands(cls): #MOVED
        for x in await db.fetch("SELECT guild_id, array_agg(command) AS commands FROM disabledcommands GROUP BY guild_id"):
            cls.settings[x['guild_id']]["disabled_commands"] = x['commands']
        else:
            pass

    @classmethod
    async def load_custom_roasts(cls): #MOVED
        for x in await db.fetch("SELECT guild_id, array_agg(roast) AS roasts FROM custom_roasts GROUP BY guild_id"):
            cls.settings[x['guild_id']]["custom_roasts"] = x['roasts']
        else:
            pass

    @classmethod
    async def load_reactionroles(cls): #MOVED
        for x in await db.fetch("SELECT * FROM reactionroles"):
            cls.rr[x['message_id']][x['emoji']] = x['role_id']
        else:
            pass

    @classmethod
    async def load_global_disabled_commands(cls):
        for x in await db.fetch("SELECT * FROM globaldisabled"):
            cls.globaldisabled[x['command']] = x['reason']
        else:
            pass

    @classmethod
    async def load_votereminders(cls): #MOVED
        for x in await db.fetch("SELECT * FROM votereminders"):
            cls.votereminders[x['user_id']] = dict(time=x['time'], reminded=x['reminded'])
        else:
            pass

    @classmethod
    async def load_blacklist(cls): #MOVED
        x = await db.fetchval("SELECT array_agg(user_id_dm) FROM blacklists WHERE user_id_dm IS NOT NULL")
        if x:
            cls.blacklist['dm'] = x
        y = await db.fetchval("SELECT array_agg(user_id) FROM blacklists WHERE user_id IS NOT NULL")
        if y:
            cls.blacklist['user'] = y
        z = await db.fetchval("SELECT array_agg(guild_id) FROM blacklists WHERE guild_id IS NOT NULL")
        if z:
            cls.blacklist['guild'] = z

    @classmethod
    async def load_welcoming(cls): #MOVED
        for x in await db.fetch("SELECT * FROM welcoming"):
            cls.welcomer[x['guild_id']] = dict(welcome_channel=x['welcome_channel'], welcome_toggle=x['welcome_toggle'], welcome_msg=x['welcome_msg'], welcome_embedmsg=json.loads(x['welcome_embedmsg']) if x['welcome_embedmsg'] else None, welcome_embedtoggle=x['welcome_embedtoggle'],
                                                welcome_delafter=x['welcome_delafter'], leave_channel=x['leave_channel'], leave_toggle=x['leave_toggle'], leave_msg=x['leave_msg'], leave_embedmsg=json.loads(x['leave_embedmsg']) if x['leave_embedmsg'] else None, leave_embedtoggle=x['leave_embedtoggle'], leave_delafter=x['leave_delafter'])

    @classmethod
    async def load_config(cls):
        async with aiofiles.open('db/config.json', mode='r') as f:
            data = await f.read()
        cls.config = json.loads(data)

    @classmethod
    async def load_locale(cls):
        langs = os.listdir('db/languages')
        for lang in langs:
            async with aiofiles.open(f'db/languages/{lang}/bot.json') as bf:
                cmdtext = await bf.read()
                cls.i18n[lang] = json.loads(cmdtext)
            async with aiofiles.open(f'db/languages/{lang}/help.json') as hf:
                cmdhelp = await hf.read()
                cls.cmd_help[lang] = json.loads(cmdhelp)

    @classmethod
    async def load_rolesettings(cls): #MOVED
        for x in await db.fetch("SELECT * FROM role_settings"):
            cls.roles[x['guild_id']] = dict(moderator=x['moderator_id'], booster=x['booster_id'], dj=x['dj_id'], muted=x['mute_id'])

    @classmethod
    async def load_acknowledgements(cls): #MOVED
        for x in await db.fetch("SELECT user_id, array_agg(acknowledgement_type) FROM acknowledgements GROUP BY user_id"):
            cls.acknowledgements[x["user_id"]] = x["array_agg"]

    @classmethod
    async def load_afk(cls):
        for x in await db.fetch("SELECT * FROM afk"):
            cls.afk[x['user_id']] = {'afk_set': x['afk_set'], 'reason': x['reason']}

    @classmethod
    async def load_embed_mentions(cls): #MOVED
        for x in await db.fetch("SELECT user_id, array_agg(guild_id), global FROM embed_mentions GROUP BY user_id, global"):
            cls.embed_mentions[x["user_id"]] = {"guilds": x["array_agg"], "global": x['global']}

    @classmethod
    async def load_socials(cls): #MOVED
        for x in await db.fetch("SELECT * FROM socials"):
            cls.socials[x["user_id"]][x['socialtype']] = x['social']

    @classmethod
    async def load_holiday_announcements(cls): #MOVED
        for x in await db.fetch("SELECT * FROM holiday_announcements"):
            cls.holiday_announcements[x['guild_id']] = {'country': x['country'], 'last_announce': x['last_announce'], 'channel_id': x['channel_id'], 'role_id': x['role_id'], 'toggle': x['toggle'], 'message': x['message']}

    @classmethod
    async def update_db(cls):
        stats = []
        for x in cls.cmd_stats:
            for y in cls.cmd_stats[x]:
                for z in cls.cmd_stats[x][y]:
                    stats.append((x, y, z, cls.cmd_stats[x][y][z]))

        await db.executemany("INSERT INTO cmd_stats VALUES($1, $2, $3, $4) ON CONFLICT (guild_id, user_id, command) DO UPDATE SET usage = cmd_stats.usage + $4 WHERE excluded.command = $3 AND excluded.user_id = $2 AND excluded.guild_id = $1", stats)
        cls.cmd_stats.clear()


    @classmethod
    async def start(cls):
        await cls.load_guilds()
        await cls.load_settings()
        await cls.load_module_settings()
        await cls.load_category_settings()
        await cls.load_logging()
        await cls.load_disabled_commands()
        await cls.load_custom_roasts()
        await cls.load_reactionroles()
        await cls.load_global_disabled_commands()
        await cls.load_votereminders()
        await cls.load_blacklist()
        await cls.load_welcoming()
        await cls.load_config()
        await cls.load_locale()
        await cls.load_rolesettings()
        await cls.load_acknowledgements()
        await cls.load_afk()
        await cls.load_socials()
        await cls.load_holiday_announcements()

    @classmethod
    def clear_all(cls):
        cls.blacklist.clear()
        cls.blacklist = dict(dm=[], user=[], guild=[])
        cls.config.clear()
        cls.categories.clear()
        cls.dms.clear()
        cls.globaldisabled.clear()
        cls.logging.clear()
        cls.modules.clear()
        cls.prefix.clear()
        cls.rr.clear()
        cls.settings.clear()
        cls.welcomer.clear()
        cls.modactions.clear()
        cls.i18n.clear()
        cls.cmd_help.clear()
        cls.roles.clear()
        cls.acknowledgements.clear()
        cls.afk.clear()
        cls.socials.clear()
        cls.holiday_announcements.clear()

    @classmethod
    async def refresh(cls):
        await cls.update_db()
        cls.clear_all()
        await cls.start()

    @classmethod
    async def refresh_locale(cls):
        cls.i18n.clear()
        cls.cmd_help.clear()
        await cls.load_locale()

    @classmethod
    def get(cls, attr: str, _id = None, key=None):
        if not hasattr(cls, attr):
            raise CacheError(f"CacheManager has no attribute: `{attr}`.")

        x = getattr(cls, attr.lower())
        if _id is None:
            return x

        try:
            data = x[_id]
        except KeyError:
            raise CacheError(f'Cache for `{attr}` contains no data for `{_id}`!')

        if key is not None:
            try:
                data = data[key]
            except KeyError:
                raise CacheError(f"Data for `{_id}` in the cache for `{attr}` has no value named `{key}`.")

        return data

    @classmethod
    def update(cls, attr: str, _id, key: str, value="Some Empty Value"):
        if not hasattr(cls, attr):
            raise CacheError(f"CacheManager has no attribute: `{attr}`.")

        x = getattr(cls, attr.lower())
        try:
            data = x.get(_id)
        except KeyError:
            raise CacheError(f'Cache for `{attr}` contains no data for `{_id}`!')

        if value == "Some Empty Value":
            if isinstance(data, list):
                if key in data:
                    x[_id].remove(key)
                else:
                    x[_id].append(key)
            else:
                x[_id] = key

            return x[_id]

        if isinstance(data.get(key), list):
            if value in data[key]:
                data[key].remove(value)
            else:
                data[key].append(value)
        else:
            data[key] = value

        return data[key]

    @classmethod
    def delete(cls, attr: str, _id, key=None):
        if not hasattr(cls, attr):
            raise CacheError(f"CacheManager has no attribute: `{attr}`.")

        x = getattr(cls, attr.lower())
        try:
            data = x.get(_id)
        except KeyError:
            raise CacheError(f'Cache for `{attr}` contains no data for `{_id}`!')

        if key is not None:
            try:
                data = data.pop(key)
            except KeyError:
                raise CacheError(f"Data for `{_id}` in the cache for `{attr}` has no value named `{key}`.")
        else:
            data = x.pop(_id)

        return data

    @classmethod
    def add_guild(cls, guild_id: int):
        cls.settings[guild_id] = dict(disabled_commands=[], language="en", color=3178180, roastlevel=1,
                                  joinrole_toggle=False, joinrole_human=None, joinrole_bot=None,
                                  cb_emotion="neutral", cb_mention=False, custom_roasts=[])
        cls.modules[guild_id] = dict(
            fun=True, music=True, info=True, moderation=True, utility=True, images=True)
        cls.categories[guild_id] = {"fun_funny": True, "fun_random": True, "fun_games": True,
                                "music_playlists": True, "music_player-information": True, "music_player-controls": True, "music_basic": True,
                                "info_guild-info": True, "info_member-info": True, "info_bot-info": True,
                                "moderation_basic": True, "moderation_banning": True,
                                "utility_fonts": True, "utility_polls": True, "utility_colors": True, "utility_utils": True, "utility_reaction-roles": True,
                                "images_nsfw": True, "images_funny": True, "images_animals": True,
                                }
        cls.logging[guild_id] = dict(msgedit_channel=None,
                                     msgdel_channel=None,
                                     join_channel=None,
                                     useredit_channel=None,
                                     mod_channel=None)

        cls.welcomer[guild_id] = dict(welcome_channel=None, welcome_toggle=False, welcome_msg=None, welcome_embedmsg=None, welcome_embedtoggle=False, welcome_delafter=None,
                             leave_channel=None, leave_toggle=False, leave_msg=None, leave_embedmsg=None, leave_embedtoggle=False, leave_delafter=None)

        cls.prefix[guild_id] = "c?"

        cls.roles[guild_id] = dict(moderator=None, booster=None, dj=None, muted=None)

    @classmethod
    def delete_guild(cls, guild_id: int):
        try:
            cls.settings.pop(guild_id)
            cls.modules.pop(guild_id)
            cls.categories.pop(guild_id)
            cls.logging.pop(guild_id)
            cls.welcomer.pop(guild_id)
            cls.prefix.pop(guild_id)
            cls.roles.pop(guild_id)
        except:
            raise CacheError(f"Guild ID `{guild_id}` was not found in the cache!")
