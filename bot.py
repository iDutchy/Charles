import os
import logging
import discord
import asyncio
from db import tokens
from logging.handlers import RotatingFileHandler

os.environ['PY_PRETTIFY_EXC'] = 'True'

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s: %(message)s'
DATE_FORMAT = f'%d/%m/%Y %H:%M:%S'
FORMATTER = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

discord_log = logging.getLogger('discord')
discord_log.setLevel(logging.DEBUG)
discord_handler = RotatingFileHandler(filename='logs/discord.log', mode='w', backupCount=5, encoding='utf-8',
                                      maxBytes=2**22)
discord_handler.setFormatter(FORMATTER)
discord_log.addHandler(discord_handler)

diorite_log = logging.getLogger('diorite')
diorite_log.setLevel(logging.DEBUG)
diorite_handler = RotatingFileHandler(filename='logs/diorite.log', mode='w', backupCount=5, encoding='utf-8',
                                      maxBytes=2**22)
diorite_handler.setFormatter(FORMATTER)
diorite_log.addHandler(diorite_handler)

import importlib

from core import bot as botfile
from core import i18n

BOT_EXTENSIONS = [
    'cogs.owner',
    'cogs.fun',
    'cogs.info',
    'cogs.moderation',
    'cogs.utility',
    'cogs.images',
    'cogs.events',
    'cogs.settings',
    # 'cogs.music',
    'cogs.private'
]

bot = botfile.BotCore(extensions=BOT_EXTENSIONS)
bot.maintenance_mode = False

@bot.before_invoke
async def bot_before_invoke(ctx):
    if ctx.guild is None:
        i18n.set_locale('en')
    else:
        i18n.set_locale(bot.cache.get("settings", ctx.guild.id, 'language'))

@bot.check
async def maintenance_mode(ctx):
    if bot.maintenance_mode:
        if ctx.author.id == bot.owner_id:
            return True
        e = discord.Embed(title=f"{ctx.emoji.warn} | Maintenance Mode")
        e.description = 'My owner is currently working on some things. Maintenance mode has been enabled because important things may not be loaded or my owner needs to reboot me a lot. Apologies for the incoveniences, I\'ll be back soon!'
        await ctx.send(embed=e)
        return False
    else:
        return True

@bot.check
async def is_disabled(ctx):
    if ctx.author.id == bot.owner_id:
        return True

    if not hasattr(ctx.command, 'perm_name') and not hasattr(ctx.command, 'category'):
        return True

    can_use = True

    perms = ctx.command.category.perm_names
    perms += ctx.command.perm_names

    e = discord.Embed(color=0xFF7070)
    e.title = _("{0} | No Access!").format(ctx.emoji.warn)

    if cperms := ctx.cache.get_denied_perms(ctx.channel.id):
        need = None
        for x in cperms:
            if x in perms:
                can_use = False
                need = x
                break
        e.description = "This command can not be used here because the `{0}` permission has been disabled in this channel!".format(need)
    if uperms := ctx.cache.get_denied_perms(ctx.author.id):
        need = None
        for x in uperms:
            if x in perms:
                can_use = False
                need = x
                break
        e.description = "You can not use this command because you dont have the `{0}` permission!".format(need)
    for role in list(ctx.author._roles):
        if rperms := ctx.cache.get_denied_perms(role):
            need = None
            for x in rperms:
                if x in perms:
                    can_use = False
                    need = x
                    break
            e.description = "You can not use this command because your role <@&{1}> doesn't have the `{0}` permission!".format(need, role)
        else:
            if not can_use:
                break
            else: 
                continue
    if can_use:
        return True
    else:
        await ctx.message.delete(silent=True)
        await ctx.send(embed=e, delete_after=6)
        return False

# @bot.ipc.route()
# async def get_test_data(data):


# bot.ipc.start()
async def main():
    async with bot:
        await bot.start(tokens.BOT)

asyncio.run(main())