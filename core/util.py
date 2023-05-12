import asyncio
import datetime
import dis
import os
import time
from itertools import cycle

import aiohttp
import discord
import mtranslate
from aiogoogletrans import Translator
from dateutil.relativedelta import relativedelta
from db import BaseUrls
from utils.converters import executor
from utils.paginator import EmbedPages

from .cache import CacheManager as cm
from .database import DB as db

# from google.cloud.translate_v3beta1.services.translation_service import TranslationServiceAsyncClient
# from google.oauth2 import service_account
# from google.cloud.translate_v3beta1.types import TranslateTextRequest

# credentials = service_account.Credentials.from_service_account_file('db/google_key.json')
# scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/cloud-platform'])
# translator = TranslationServiceAsyncClient(credentials=credentials)

class TimeIt:
    def __init__(self, ctx):
        self.ctx = ctx
        self.start = 0
        self.end = 0

    async def __aenter__(self):
        self.start = time.time()

    async def __aexit__(self, exc_type, exc, tb):
        self.end = time.time()
        diff = self.end - self.start
        return await self.ctx.send(f"Finished in `{diff:.4f}s`!", edit=False)

class Loading:
    def __init__(self, ctx, message="Loading"):
        self.ctx = ctx
        self.text = message
        self.message = None
        self.loading = True
        self.dots = cycle(['.', '..', '...'])

    async def do_edit(self):
        while True:
            await self.message.edit(content="<a:loading:747680523459231834> | " + self.text.strip() + next(self.dots))
            await asyncio.sleep(1.5)

    def __enter__(self):
        self.task = asyncio.ensure_future(self.do_edit(), loop=self.ctx.bot.loop)
        self.task.add_done_callback(discord.context_managers._typing_done_callback)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.task.cancel()

    async def __aenter__(self):
        msg = await self.ctx.channel.send("<a:loading:747680523459231834> | " + self.text.strip().rstrip('.'))
        self.message = msg
        return self.__enter__()

    async def __aexit__(self, exc_type, exc, tb):
        self.task.cancel()
        await self.message.delete()


class Utils:
    session = None

    @staticmethod
    def codeblock(code, markdown="py"):
        return f"```{markdown}\n{code}```"

    @staticmethod
    def format_date(target):
        return target.strftime("%d %B %Y")

    @staticmethod
    def format_date_time(target, include_seconds=True):
        if include_seconds is False:
            return target.strftime("%d %B %Y, %H:%M")
        return target.strftime("%d %B %Y, %H:%M:%S")

    @staticmethod
    def format_time(target, include_seconds=True):
        if include_seconds is False:
            return target.strftime("%H:%M")
        return target.strftime("%H:%M:%S")

    @staticmethod
    def timesince(dt: datetime.datetime, add_suffix=True, add_prefix=True):
        prefix = ''
        suffix = ''
        now = datetime.datetime.utcnow()
        now.replace(microsecond=0)
        dt.replace(microsecond=0)
        if now < dt:
            delta = relativedelta(dt, now)
            if add_prefix:
                prefix = 'In '
        else:
            delta = relativedelta(now, dt)
            if add_suffix:
                suffix = ' ago'
        output = []
        units = ('year', 'month', 'day', 'hour', 'minute', 'second')
        for unit in units:
            elem = getattr(delta, unit + 's')
            if not elem:
                continue
            if unit == 'day':
                weeks = delta.weeks
                if weeks:
                    elem -= weeks * 7
                    output.append('{} week{}'.format(weeks, 's' if weeks > 1 else ''))
            output.append('{} {}{}'.format(elem, unit, 's' if elem > 1 else ''))
        output = output[:3]
        return prefix + ', '.join(output) + suffix

    @classmethod
    async def create_session(cls):
        if cls.session is None:
            cls.session = aiohttp.ClientSession()

    @classmethod
    async def close_session(cls):
        if cls.session is not None:
            await cls.session.close()

    @classmethod
    async def bin(cls, code):
        code = code.strip('```')
        async with cls.session.post(BaseUrls.hb+"documents", data=code) as resp:
            data = await resp.json()
            key = data['key']
        return BaseUrls.hb+key

    @staticmethod
    async def paginate(*args, **kwargs):
        return await EmbedPages(*args, **kwargs).start()

    @staticmethod
    @executor
    def translate(text, /, dest, from_lang='auto'):
        result = mtranslate.translate(text, dest, from_lang)
        return result

    @staticmethod
    def strip(string, /, left=None, right=None, *, prefix=None, suffix=None):
        if left:
            string.lstrip(left)
        if right:
            string.rstrip(right)
        if prefix:
            string.removeprefix(prefix)
        if suffix:
            string.removesuffix(suffix)
        return string

    @staticmethod
    def timeit(ctx):
        return TimeIt(ctx)

    @staticmethod
    def loading(ctx, message=None):
        return Loading(ctx, message)
