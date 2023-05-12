from datetime import date
from io import BytesIO

import discord
import holidays
from utils import tomledit

from . import cm, db

BASE_IMAGES_PATH = "db/images/themes/"
LOGO_FULL_PATH = "Devision.png"
LOGO_EYE_PATH = "Devision_eye.png"
AVATAR_PATH = "Charles.png"
DEFAULT_COLOR = DEFAULT_COLOUR = 0x307EC4

TEMPLATE = """
class TEMPLATE(Theme):
    def __init__(self, bot):
        super().__init__(bot)
        self.color = 0x000000
        self.colour = self.color
        self.logo_path = ""
        self.guild_name = "Devision"
        self.channel_icon = ""

    @property
    def date(self):
        return date(date.today().year, 12, 31)
"""

__all__ = (
    "Default",
    "Christmas",
    "Valentines",
    "Thanksgiving",
    "Halloween",
    "Corona",
    "Easter",
    "July4th",
    "NewYears"
)

class Theme:
    def __init__(self, bot):
        self.bot = bot

    @property
    def logo_full(self):
        return discord.File(BASE_IMAGES_PATH + self.logo_path + "/" + LOGO_FULL_PATH, LOGO_FULL_PATH)

    @property
    def logo_eye(self):
        return discord.File(BASE_IMAGES_PATH + self.logo_path + "/" + LOGO_EYE_PATH, LOGO_EYE_PATH)

    @property
    def avatar(self):
        return discord.File(BASE_IMAGES_PATH + self.logo_path + "/" + AVATAR_PATH, AVATAR_PATH)

    @property
    def name(self):
        return getattr(self, "theme_name", self.__class__.__name__)

    @staticmethod
    def get_date(holiday, next_year=False):
        inverse = {v: k for k, v in holidays.US(years=date.today().year + (1 if next_year else 0)).items()}
        _date = inverse.get(holiday, date.today())
        return _date

    async def load(self):
        self.set_theme()
        await self.set_color()
        await self.set_avatar()
        await self.set_guild_icon()
        await self.set_channel_names()

    async def set_color(self):
        await db.execute("UPDATE guildsettings SET embedcolor = $1 WHERE embedcolor = $2", int(self.color), int(DEFAULT_COLOR))
        for cache in self.bot._guild_cache.values():
            if cache.color == int(DEFAULT_COLOR):
                await cache.set_color(int(self.color))

    async def set_avatar(self):
        await self.bot.user.edit(avatar=open(self.avatar.fp.name, "rb").read())

    def set_theme(self):
        self.bot.theme = self
        tomledit.change_value("db/config.toml", "settings", "THEME", self.__class__.__name__)

    async def set_guild_icon(self):
        guild = self.bot.get_guild(514232441498763279)
        await guild.edit(icon=open(self.logo_eye.fp.name, "rb").read(), name=self.guild_name, reason=f"Loaded theme: {self.name}")

    async def set_channel_names(self):
        guild = self.bot.get_guild(514232441498763279)
        for chan in guild.text_channels:
            if self.channel_icon:
                if "┃" in chan.name:
                    await chan.edit(name=f"{self.channel_icon}┃"+chan.name.split("┃")[1])
                else:
                    await chan.edit(name=f"{self.channel_icon}┃{chan.name}")
            else:
                if "┃" in chan.name:
                    await chan.edit(name=chan.name.split("┃")[1])
                else:
                    continue

class Default(Theme):
    def __init__(self, bot):
        super().__init__(bot)
        self.color = 0x307EC4
        self.colour = self.color
        self.logo_path = "Default"
        self.guild_name = "Devision"
        self.channel_icon = ""

    @property
    def date(self):
        return date.today()

class Christmas(Theme):
    def __init__(self, bot):
        super().__init__(bot)
        self.color = 0xE40A2D
        self.colour = self.color
        self.logo_path = "Christmas"
        self.guild_name = "Devision"
        self.channel_icon = "🎄"

    @property
    def date(self):
        return self.get_date("Christmas Day")

class Valentines(Theme):
    def __init__(self, bot):
        super().__init__(bot)
        self.color = 0xFFB7DD
        self.colour = self.color
        self.logo_path = "Valentines Day"
        self.guild_name = "Devision"
        self.channel_icon = "💘"

    @property
    def date(self):
        return date(date.today().year, 2, 14)

class Thanksgiving(Theme):
    def __init__(self, bot):
        super().__init__(bot)
        self.color = 0xCB7723
        self.colour = self.color
        self.logo_path = "Thanksgiving"
        self.guild_name = "Devision"
        self.channel_icon = "🦃"

    @property
    def date(self):
        return self.get_date("Thanksgiving")

class Halloween(Theme):
    def __init__(self, bot):
        super().__init__(bot)
        self.color = 0xF75F1C
        self.colour = self.color
        self.logo_path = "Halloween"
        self.guild_name = "Devision"
        self.channel_icon = "👻"

    @property
    def date(self):
        return date(date.today().year, 10, 31)

class Corona(Theme):
    def __init__(self, bot):
        super().__init__(bot)
        self.color = 0x66D9F0
        self.colour = self.color
        self.logo_path = "Coronavirus"
        self.guild_name = "Devision"
        self.channel_icon = "😷"

    @property
    def date(self):
        return date.today()

class Easter(Theme):
    def __init__(self, bot):
        super().__init__(bot)
        self.color = 0xE0ABD2
        self.colour = self.color
        self.logo_path = "Easter"
        self.guild_name = "Devision"
        self.channel_icon = "🥚"

    @property
    def date(self):
        return date(2021, 4, 4)

class July4th(Theme):
    def __init__(self, bot):
        super().__init__(bot)
        self.color = 0x0168AD
        self.colour = self.color
        self.theme_name = "4th of July"
        self.logo_path = "4th of July"
        self.guild_name = "Devision"
        self.channel_icon = "🇺🇸"

    @property
    def date(self):
        return date(date.today().year, 7, 4)

class NewYears(Theme):
    def __init__(self, bot):
        super().__init__(bot)
        self.color = 0x000000
        self.colour = self.color
        self.theme_name = "New Years"
        self.logo_path = "New Years"
        self.guild_name = "Devision"
        self.channel_icon = "🎆"

    @property
    def date(self):
        return date(date.today().year, 12, 31)
