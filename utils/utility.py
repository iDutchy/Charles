import asyncio
import importlib
import inspect
import itertools
import os
import pathlib
import re
import typing
from collections import OrderedDict
from datetime import datetime
from enum import Enum

import discord

OFFSET_TAG = 0xE0000
BLACKFLAG = u"\U0001F3F4"
OFFSET = 127397  # = ord("🇦") - ord("A")
CANCELTAG = u"\U000E007F"


def unflag(flag, subregions=False):
    def dflag(i):
        points = tuple(ord(x) - OFFSET for x in i)
        return ":%c%c:" % points

    def dflag_repl(matchobj):
        return dflag(matchobj.group(0))

    regex = re.compile(u"([\U0001F1E6-\U0001F1FF]{2})", flags=re.UNICODE)

    text = regex.sub(dflag_repl, flag)

    if subregions:

        def unflag_subregional(text):

            def dflag(i):
                points = [ord(x) - OFFSET_TAG for x in i]
                suffix = "".join(["%c" % point for point in points[2:]]) + ":"
                return ":%c%c-%s" % (points[0], points[1], suffix)

            def dflag_repl(matchobj):
                return dflag(matchobj.group(1))

            regex = re.compile(
                BLACKFLAG +
                u"([\U000E0030-\U000E0039\U000E0061-\U000E007A]{3,6})" +
                CANCELTAG,
                flags=re.UNICODE)
            text = regex.sub(dflag_repl, text)

            return text

        text = unflag_subregional(text)

    return text


def get_all_cases(string):
    return list(map(''.join, itertools.product(*((c.upper(), c.lower()) for c in string))))


class Acknowledgements(Enum):
    event_winner = 1
    bug_hunter = 2
    found_hidden_feature = 3
    translator = 4
    owner = 5
    contributor = 6


class SizedDict(OrderedDict):

    def __init__(self, maxsize=1000, *args, **kwargs):
        self.maxsize = maxsize
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            self.popitem(last=False)


async def warn(bot, event, user_guild: typing.Union[discord.Member, discord.User, discord.Guild], err):
    log = bot.get_channel(522855838881284100)
    e = discord.Embed(title="**Event Log Warning!**",
                      color=0xb53a3a,
                      timestamp=datetime.utcnow())
    if isinstance(user_guild, (discord.Member, discord.User)):
        e.description = f"Error sending `{event}` log!\n**User:** {user_guild.name}\n\n**Error:** ```sh\n{err}```"
        e.set_author(name=user_guild.name,icon_url=user_guild.avatar.url)
    else:
        e.description = f"Error sending `{event}` log!\n**Guild:** {user_guild.name}\n\n**Error:** ```sh\n{err}```"
        e.set_author(name=user_guild.name,icon_url=user_guild.icon.url)
    await log.send(embed=e)


def get_locale_strings():
    strings = []
    p = pathlib.Path('./')
    for f in p.rglob('*.py'):
        if str(f).startswith("venv"):
            continue
        with f.open() as of:
            file = of.read()
        if (matches := re.findall(r'\_\(\"([\w\D]+?)\"\)\D', file)):
            strings += [m.replace("\\t", "\t").replace("\\n", "\n").replace('\\\"', '\"') for m in matches]
        if (matches := re.findall(r"\_\(\'([\w\D]+?)\'\)", file)):
            strings += [m.replace("\\t", "\t").replace("\\n", "\n").replace('\\\"', '\"') for m in matches]
    return strings


def loader(package):
    classes = []
    for file in os.listdir(f'./{package.replace(".", "/")}'):
        if file.startswith("__"):
            continue

        mod = importlib.import_module(f"{package}.{file[:-3]}")
        importlib.reload(mod)
        x = inspect.getmembers(mod)
        for n, m in x:
            if inspect.isclass(m):
                if m.__class__.__name__ == "SubCogMeta":
                    cog = getattr(mod, n)
                    if cog.__name__ != "SubCog":
                        classes.append(cog)

    return classes
