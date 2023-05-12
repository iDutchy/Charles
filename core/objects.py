import json
import time
from collections import defaultdict
from datetime import date, datetime

from discord.utils import SnowflakeList as idlist

from .database import DB as db

class CacheError(Exception):
    pass

def dbupdate(*args):
    return "UPDATE {0} SET {1} = $1 WHERE {2} = $2".format(*args)


def dbdelete(*args):
    return "DELETE FROM {0} WHERE {1} = $1 AND {2} = $2".format(*args)

async def db_add(cls, table, *args, **kwargs):
    if args and isinstance(args[0], dict):
        kwargs = args[0]
    query = "INSERT INTO {tablename}({values}) VALUES({numbers})"
    insert = {}
    for index, attr in enumerate(list(kwargs.keys()), start=1):
        if attr not in cls.__slots__:
            raise CacheError("TODO")
        setattr(cls, attr, kwargs.get(attr))
        insert[attr] = f"${index}"
    await db.execute(query.format(tablename=table, values=", ".join(list(insert.keys())), numbers=", ".join(list(insert.values()))), cls.user_id, *list(kwargs.values()))


async def db_update(cls, table, *args, attr_pre="", update_type="guild", slotbegin=0, slotend=None, rm_suffix="", **kwargs):
    if args and isinstance(args[0], dict):
        kwargs = args[0]
    query = "UPDATE {tablename} SET {updates} WHERE {utype}_id = $1"
    set_ = []
    for index, attr in enumerate(list(kwargs.keys()), start=2):
        if attr not in cls.__slots__[slotbegin:slotend]:
            raise CacheError("TODO")
        setattr(cls, attr, kwargs.get(attr))
        set_.append(f"{attr_pre}{attr.removesuffix(rm_suffix)} = ${index}")
    await db.execute(query.format(tablename=table, updates=", ".join(set_), utype=update_type), getattr(cls, f"{update_type}_id"), *list(kwargs.values()))


class UserData:
    __slots__ = ('user_id', 'raw', 'voteremind', 'acknowledgements', 'socials',
                 'embedmentions', 'blacklisted', 'dm_blacklisted', 'afk', 'dms',
                 'prefixes')

    def __init__(self, user_id, data):
        self.user_id = user_id
        self.raw = data

        self.blacklisted = data.get('blacklist', False)
        self.dm_blacklisted = data.get('dm_blacklist', False)
        self.dms = data.get('dms', True)
        self.prefixes = data.get('prefixes', {})

        self.voteremind = Votereminder(data.get('voteremind', {}))
        self.acknowledgements = Acknowledgements(data.get('acknowledgements', []), user_id)
        self.socials = Socials(data.get('socials', {}), user_id)
        self.embedmentions = EmbedMentions(data.get('embed_mentions', {}))
        self.afk = AFK(data.get('afk', {}))

    def __bool__(self):
        return self.raw != {}

    async def set_prefix(self, guild_id, prefix):
        if guild_id in self.prefixes:
            await db.execute("UPDATE userprefixes SET prefix = $1 WHERE guild_id = $2 AND user_id = $3", prefix, guild_id, self.user_id)
        else:
            await db.execute("INSERT INTO userprefixes VALUES($1, $2, $3)", guild_id, self.user_id, prefix)
        self.prefixes[guild_id] = prefix

    async def set_dms(self, toggle):
        self.dms = toggle
        if toggle:
            await db.execute("DELETE FROM no_dms WHERE user_id = $1", self.user_id)
        else:
            await db.execute("INSERT INTO no_dms VALUES($1)", self.user_id)

    async def blacklist(self, dm=False, undo=False):
        if dm:
            if undo:
                await db.execute("DELETE FROM blacklists WHERE user_id_dm = $1", self.user_id)
                self.dm_blacklisted = False
            else:
                await db.execute("INSERT INTO blacklists(user_id_dm) VALUES($1)", self.user_id)
                self.dm_blacklisted = True
        else:
            if undo:
                await db.execute("DELETE FROM blacklists WHERE user_id = $1", self.user_id)
                self.blacklisted = False
            else:
                await db.execute("INSERT INTO blacklists(user_id) VALUES($1)", self.user_id)
                self.blacklisted = True


class Votereminder:
    __slots__ = ('time', 'reminded', 'user_id')

    def __init__(self, data):
        self.time = data.get('time', 0)
        self.reminded = data.get('reminded', False)
        self.user_id = data.get('user_id')

    def __bool__(self):
        return self.time != 0

    async def create(self):
        query = "INSERT INTO votereminders VALUES ($1, $2, $3)"
        await db.execute(query, self.user_id, True, int(time.time()))
        self.reminded = True
        self.time = int(time.time())

    async def delete(self):
        query = "DELETE FROM votereminders WHERE user_id = $1"
        await db.execute(query, self.user_id)
        self.reminded = False
        self.time = 0


class Acknowledgements:
    __slots__ = ('all', 'user_id', 'event_winner', 'bug_hunter',
                 'found_hidden_feature', 'translator', 'owner', 'contributor')

    def __init__(self, ack_ids, user_id):
        self.user_id = user_id
        self.all = idlist(ack_ids)
        self.event_winner = self.all.has(1)
        self.bug_hunter = self.all.has(2)
        self.found_hidden_feature = self.all.has(3)
        self.translator = self.all.has(4)
        self.owner = self.all.has(5)
        self.contributor = self.all.has(6)

    def __bool__(self):
        return len(self.all) != 0

    def __iter__(self):
        for attr in self.__slots__[2:]:
            yield attr, getattr(self, attr)

    def __repr__(self):
        has = self.get_all()
        if has:
            acks = " ".join(has)
        else:
            acks = "None"
        return f"<Acknowledgements: {acks}>"

    def get_all(self):
        return [attr for attr in self.__slots__[2:] if getattr(self, attr) is True]

    async def add(self, ack):
        self.all.add(ack)
        await db.execute("INSERT INTO acknowledgements(user_id, acknowledgement_type) VALUES($1, $2)", self.user_id, ack)

    async def remove(self, ack):
        self.all.remove(ack)
        await db.execute("DELETE FROM acknowledgements WHERE user_id = $1 AND acknowledgement_type = $2", self.user_id, ack)


class Socials:
    __slots__ = ('user_id', 'snapchat', 'reddit', 'twitter', 'steam',
                 'github', 'twitch', 'psn', 'xbox', 'youtube', 'instagram')

    def __init__(self, socials, user_id):
        self.user_id = user_id
        self.snapchat = socials.get('snapchat')
        self.reddit = socials.get('reddit')
        self.twitter = socials.get('twitter')
        self.steam = socials.get('steam')
        self.github = socials.get('github')
        self.twitch = socials.get('twitch')
        self.psn = socials.get('psn')
        self.xbox = socials.get('xbox')
        self.youtube = socials.get('youtube')
        self.instagram = socials.get('instagram')

    def __getitem__(self, value):
        return getattr(self, value)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __contains__(self, value):
        return value in self.__slots__[1:] and getattr(self, value) is not None

    def __bool__(self):
        return self.get_all() != {}

    def __repr__(self):
        has = list(self.get_all().keys())
        if has:
            scs = " ".join(has)
        else:
            scs = "None"
        return f"<Socials: {scs}>"

    def get_all(self):
        return {attr: getattr(self, attr) for attr in self.__slots__[1:] if getattr(self, attr) is not None}

    async def remove(self, social):
        if social.lower() not in self.__slots__[1:]:
            raise CacheError("TODO")
        await db.execute("DELETE FROM socials WHERE socialtype = $1 AND user_id = $2", social.lower(), self.user_id)
        self.__setitem__(social, None)

    async def set(self, socialtype, username):
        if socialtype not in self.__slots__[1:]:
            raise CacheError("TODO")
        if self.__getitem__(socialtype) is None:
            query = "INSERT INTO socials(user_id, social, socialtype) VALUES($1, $2, $3)"
        else:
            query = "UPDATE socials SET social = $2 WHERE user_id = $1 AND socialtype = $3"
        self.__setitem__(socialtype, username)
        await db.execute(query, self.user_id, username, socialtype)


class EmbedMentions:
    __slots__ = ('user_id', 'guilds', 'globally')

    def __init__(self, data):
        self.user_id = data.get('user_id')
        self.guilds = data.get('guilds', [])
        self.globally = data.get('global', False)

    def __bool__(self):
        return self.globally or len(self.guilds) > 0

    # TODO: SOMEHOW UPDATE CACHE/DB HERE

    # async def update(self, *args, **kwargs):
    #     if args and isinstance(args[0], dict):
    #         kwargs = args[0]
    #     query = "UPDATE embed_mentions SET {updates} WHERE user_id = $1"
    #     set_ = []
    #     for index, attr in enumerate(list(kwargs.keys()), start=2):
    #         if not attr in self.__slots__:
    #             raise CacheError("TODO")
    #         setattr(self, attr, kwargs.get(attr))
    #         set_.append(f"{attr.removesuffix('ly')} = ${index}")
    #     await db.execute(query.format(updates=", ".join(set_)), self.user_id, *list(kwargs.values()))


class AFK:
    __slots__ = ('user_id', 'afk_set', 'reason')

    def __init__(self, data):
        self.user_id = data.get('user_id')
        self.afk_set = data.get('afk_set')
        self.reason = data.get('reason')

    def __bool__(self):
        return self.afk_set is not None

    async def set(self, reason=None):
        self.afk_set = datetime.utcnow()
        self.reason = reason or _("No reason")
        await db.execute("INSERT INTO afk(user_id, reason) VALUES($1, $2)", self.user_id, self.reason)

    async def remove(self):
        self.afk_set = None
        self.reason = None
        await db.execute("DELETE FROM afk WHERE user_id = $1", self.user_id)

# GUILD OBJECTS #


class GuildData:
    def __init__(self, guild_id, settings):
        self.id = guild_id
        self.prefix = settings.get("prefix", "c?")
        self.language = settings.get("language", "en")
        self.color = settings.get("embedcolor", 3178180)
        self.roastlevel = settings.get("roastlevel", 1)
        self.custom_roasts = settings.get('custom_roasts', [])
        self.disabled_commands = settings.get('disabled_commands', [])
        self.cb_mention = settings.get("cb_mention", False)
        self.cb_emotion = settings.get("cb_emotion", "neutral")
        self.rtt = settings.get("react_to_translate", False)
        self.perms = settings.get("perm_settings", {'allowed': defaultdict(list), 'denied': defaultdict(list)})

        self.modules = ModuleSettings(settings.get('module_settings', {}))
        self.categories = CategorySettings(settings.get('category_settings', {}))
        self.role = Roles(settings.get('roles', {}))
        self.logs = Logging(settings.get('logging', {}))
        self.joinrole = JoinRole(settings)
        self.holidays = Holidays(settings.get('holidays-announcements', {}))
        self.welcoming = WelcomeLeave(settings.get("welcome-leave", {}), "welcome_")
        self.leaving = WelcomeLeave(settings.get("welcome-leave", {}), "leave_")
        self.reactionroles = ReactionRoleData(settings.get('reactionroles', {}))

    def get_allowed_perms(self, _id):
        return self.perms['allowed'].get(_id, [])

    def get_denied_perms(self, _id):
        return self.perms['denied'].get(_id, [])

    async def update_perms(self, _id, perm, allow=True):
        if allow:
            if perm in self.get_denied_perms(_id):
                self.perms['denied'][_id].remove(perm)
                self.perms['allowed'][_id].append(perm)
                await db.execute("UPDATE perm_settings SET allow = true WHERE perm_type = $1 AND guild_id = $2 AND _id = $3", perm, self.id, _id)
            else:
                self.perms['allowed'][_id].append(perm)
                await db.execute("INSERT INTO perm_settings(guild_id, _id, allow, perm_type) VALUES($1,$2,$3,$4)", self.id, _id, True, perm)
        else:
            if perm in self.get_allowed_perms(_id):
                self.perms['allowed'][_id].remove(perm)
                self.perms['denied'][_id].append(perm)
                await db.execute("UPDATE perm_settings SET allow = false WHERE perm_type = $1 AND guild_id = $2 AND _id = $3", perm, self.id, _id)
            else:
                self.perms['denied'][_id].append(perm)
                await db.execute("INSERT INTO perm_settings(guild_id, _id, allow, perm_type) VALUES($1,$2,$3,$4)", self.id, _id, False, perm)

    async def update(self, column, data, table='guildsettings', delete=False):
        action = dbdelete if delete is True else dbupdate
        await db.execute(action(table, column, 'guild_id'), data, self.id)

    async def toggle_rtt(self):
        if self.rtt:
            toggle = False
        else:
            toggle = True
        self.rtt = toggle
        await self.update("react_to_translate", toggle)
        return toggle

    async def set_prefix(self, new_pre):
        self.prefix = new_pre
        await self.update('prefix', new_pre)

    async def set_language(self, lang):
        self.language = lang
        await self.update('language', lang)

    async def set_color(self, col):
        self.color = col
        await self.update('embedcolor', col)

    async def set_roastlevel(self, level):
        self.roastlevel = level
        await self.update('roastlevel', level)

    async def add_roast(self, roast):
        self.custom_roasts.append(roast)
        await db.execute("INSERT INTO custom_roasts(guild_id, roast) VALUES($1,$2)", self.id, roast)

    async def remove_roast(self, roast):
        self.custom_roasts.delete(roast)
        await self.update('roast', roast, table='custom_roasts', delete=True)

    async def blacklist(self):
        await db.execute("INSERT INTO blacklists(guild_id) VALUES($1)", self.guild_id)


class ModuleSettings:
    __slots__ = ('fun', 'images', 'info', 'moderation', 'music', 'utility', 'guild_id')

    def __init__(self, settings):
        self.fun = settings.get('fun', True)
        self.images = settings.get('images', True)
        self.info = settings.get('info', True)
        self.moderation = settings.get('moderation', True)
        self.music = settings.get('music', True)
        self.utility = settings.get('utility', True)
        self.guild_id = settings.get('guild_id')

    async def toggle(self, *args, **kwargs):
        if args and isinstance(args[0], dict):
            kwargs = args[0]
        query = "UPDATE module_settings SET {updates} WHERE guild_id = $1"
        if (toggle := kwargs.pop('all')):
            if toggle not in (True, False):
                raise ValueError("Toggling all modules must either be done with a True or False value, you passed: {}".format(toggle))
            q = []
            for attr in self.__slots__[:-1]:
                setattr(self, attr, toggle)
                q.append(f"{attr} = $2")
            await db.execute(query.format(updates=", ".join(q)), self.guild_id, toggle)
        else:
            set_ = []
            for index, attr in enumerate(list(kwargs.keys()), start=2):
                if attr not in self.__slots__:
                    raise CacheError("TODO")
                setattr(self, attr, kwargs.get(attr))
                set_.append(f"{attr} = ${index}")
            await db.execute(query.format(updates=", ".join(set_)), self.guild_id, *list(kwargs.values()))


class CategorySettings:
    __slots__ = ('funny', 'games', 'random', 'server_info',
               'user_info', 'bot_info', 'banning', 'basic',
               'fonts', 'colors', 'reaction_roles', 'utility',
               'polls', 'nsfw', 'animals', 'server_settings',
               'server_backups', 'bot_settings', 'playlists',
               'player_controls', 'player_information', 'guild_id')

    def __init__(self, settings):
        self.funny = settings.get('funny', True)
        self.games = settings.get('games', True)
        self.random = settings.get('random', True)
        self.server_info = settings.get('server_info', True)
        self.user_info = settings.get('user_info', True)
        self.bot_info = settings.get('bot_info', True)
        self.banning = settings.get('banning', True)
        self.basic = settings.get('basic', True)
        self.fonts = settings.get('fonts', True)
        self.colors = settings.get('colors', True)
        self.reaction_roles = settings.get('reaction_roles', True)
        self.utility = settings.get('utility', True)
        self.polls = settings.get('polls', True)
        self.nsfw = settings.get('nsfw', True)
        self.animals = settings.get('animals', True)
        self.server_settings = settings.get('server_settings', True)
        self.server_backups = settings.get('server_backups', True)
        self.bot_settings = settings.get('bot_settings', True)
        self.playlists = settings.get('playlists', True)
        self.player_controls = settings.get('player_controls', True)
        self.player_information = settings.get('player_information', True)
        self.guild_id = settings.get('guild_id')

    async def toggle(self, *args, **kwargs):
        await db_update(self, 'category_settings', *args, **kwargs)


class Roles:
    __slots__ = ('moderator', 'muted', 'dj', 'booster', 'guild_id')

    def __init__(self, roles):
        self.moderator = roles.get('moderator_id')
        self.muted = roles.get('mute_id')
        self.dj = roles.get('dj_id')
        self.booster = roles.get('booster_id')
        self.guild_id = roles.get('guild_id')

    async def update(self, *args, **kwargs):
        await db_update(self, 'role_settings', *args, **kwargs)


class Logging:
    __slots__ = ('msgedit', 'msgdel', 'join', 'useredit', 'mod', 'guild_id')

    def __init__(self, channels):
        self.msgedit = channels.get('msgedit')
        self.msgdel = channels.get('msgdel')
        self.join = channels.get('join')
        self.useredit = channels.get('useredit')
        self.mod = channels.get('mod')
        self.guild_id = channels.get('guild_id')

    async def update(self, *args, **kwargs):
        await db_update(self, 'logging', *args, **kwargs)


class JoinRole:
    __slots__ = ('toggle', 'human', 'bot', 'guild_id')

    def __init__(self, settings):
        self.toggle = settings.get('joinrole_toggle', False)
        self.human = settings.get('joinrole_human')
        self.bot = settings.get('joinrole_bot')
        self.guild_id = settings.get('guild_id')

    def __bool__(self):
        return self.toggle

    async def update(self, *args, **kwargs):
        await db_update(self, 'guildsettings', *args, attr_pre="joinrole_", **kwargs)


class Holidays:
    __slots__ = ('country', 'last_announce', 'channel_id',
                 'role_id', 'toggle', 'message', 'guild_id')

    def __init__(self, settings):
        self.country = settings.get("country", "UnitedStates")
        self.last_announce = settings.get("last_announce", date(2021, 1, 1))
        self.channel_id = settings.get('channel_id')
        self.role_id = settings.get('role_id')
        self.toggle = settings.get('toggle', False)
        self.message = settings.get('message', "")
        self.guild_id = settings.get('guild_id')

    async def update(self, *args, **kwargs):
        await db_update(self, 'holiday_announcements', *args, **kwargs)


class WelcomeLeave:
    __slots__ = ('channel', 'toggle', 'embedtoggle', 'msg', 'embedmsg', 'delafter', 'pre', 'guild_id')

    def __init__(self, data, pre):
        self.channel = data.get(pre+"channel")
        self.toggle = data.get(pre+"toggle", False)
        self.embedtoggle = data.get(pre+"embedtoggle", False)
        self.msg = data.get(pre+"msg")
        self.embedmsg = json.loads(data.get(pre+"embedmsg") or "{}")
        self.delafter = data.get(pre+"delafter")
        self.pre = pre
        self.guild_id = data.get('guild_id')

    async def update(self, *args, **kwargs):
        await db_update(self, 'welcoming', *args, attr_pre=self.pre, **kwargs)


class ReactionRoleData:
    __slots__ = ('all_data', 'message_id', 'role_id', 'emoji')

    def __init__(self, data):
        self.all_data = data

    def __bool__(self):
        return self.all_data != {}

    def __iter__(self):
        for message_id in list(self.all_data.keys()):
            yield message_id

    def get_message(self, message_id):
        data = self.all_data.get(message_id)
        if data is None:
            raise CacheError("TODO")
        return ReactionRoleMessage(data)

    def get_message_by_id(self, unique_id):
        x = {k: v for k, v in self.all_data.items() if v.get('settings', {}).get('unique_id', '') == unique_id}
        if x == {}:
            raise CacheError("TODO")
        return self.get_message(list(x.keys())[0])

    async def delete(self, message_id):
        self.all_data.pop(message_id)
        await db.execute("DELETE FROM reactionrole_settings WHERE message_id = $1", message_id)

    async def create(self, guild_id, message_id, max_roles, dm_msg, role_limitation, channel_id, unique_id, data):
        RRQ1 = """INSERT INTO
            reactionrole_settings(
                guild_id,
                message_id,
                max_roles,
                message,
                role_restrict,
                channel_id,
                unique_id
            )
            VALUES(
                $1, $2, $3, $4, $5, $6, $7
            )"""

        RRQ2 = """INSERT INTO
            reactionrole_data(
                guild_id,
                message_id,
                role_id,
                emoji
            )
            VALUES(
                $1, $2, $3, $4
            )"""
        await db.execute(RRQ1, guild_id, message_id, max_roles, dm_msg, role_limitation, channel_id, unique_id)
        for emoji, role_id in data.items():
            await db.execute(RRQ2, guild_id, message_id, role_id, emoji)

        self.all_data[message_id] = {'data': data, 'settings': {'guild_id': guild_id, 'max_roles': max_roles, 'message': dm_msg, 'role_restrict': role_limitation, 'channel_id': channel_id, 'unique_id': unique_id, 'message_id': message_id}}


class ReactionRoleMessage:
    __slots__ = ('max_roles', 'usable', 'role_restriction', 'guild_id', 'channel_id', 'rawsettings', 'rawdata', 'message_id', 'emojis', 'roles', 'unique_id', 'dm_msg')

    def __init__(self, datas):
        settings = datas.get('settings', {})
        data = datas.get('data', {})
        self.max_roles = settings.get('max_roles')
        self.usable = settings.get('usable', True)
        self.role_restriction = settings.get('role_restrict')
        self.guild_id = settings.get('guild_id')
        self.channel_id = settings.get('channel_id')
        self.message_id = settings.get('message_id')
        self.unique_id = settings.get('unique_id')
        self.dm_msg = settings.get('message')
        self.rawsettings = settings

        self.rawdata = data
        self.emojis = list(data.keys())
        self.roles = list(data.values())

    def __bool__(self):
        return self.rawdata != {}

    @property
    def jump_url(self):
        return f"https://discord.com/channels/{self.guild_id}/{self.channel_id}/{self.message_id}" if self.channel_id else None

    def get_role(self, emoji):
        return self.rawdata.get(emoji)

    def can_add(self, user):
        if not self.max_roles:
            return True
        hasroles = sum(1 for role in self.roles if user._roles.has(role))
        return hasroles < self.max_roles

    async def set_usable(self, toggle):
        self.rawsettings['usable'] = toggle
        await db.execute("UPDATE reactionrole_settings SET usable = $1 WHERE message_id = $2", toggle, self.message_id)

    async def set_channel(self, channel_id):
        self.rawsettings['channel_id'] = channel_id
        await db.execute("UPDATE reactionrole_settings SET channel_id = $1 WHERE message_id = $2", channel_id, self.message_id)
