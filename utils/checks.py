import discord
from core import i18n
from discord.ext import commands


class Private(commands.CommandError):
    def __init__(self, message=""):
        super().__init__(message)

class MusicError(commands.CommandError):
    def __init__(self, message=""):
        super().__init__(message)

class DisabledCommand(commands.CommandError):
    def __init__(self, message=""):
        super().__init__(message)

class NoVoter(commands.CommandError):
    def __init__(self, message=""):
        super().__init__(message)

def is_owner(dev=False):
    async def predicate(ctx):
        if ctx.author.id == ctx.bot.owner_id:
            return True

        if dev:
            if ctx.author.id in ctx.bot.config['settings']['BOT_DEVS']:
                return True

        if not hasattr(ctx.command, 'perm_name') and not hasattr(ctx.command, 'category'):
            pass
        else:
            can_use = False

            perms = ctx.command.category.perm_names
            perms += ctx.command.perm_names

            if cperms := ctx.cache.get_allowed_perms(ctx.channel.id):
                for x in cperms:
                    if x in perms:
                        can_use = True
                        break
            if uperms := ctx.cache.get_allowed_perms(ctx.author.id):
                for x in uperms:
                    if x in perms:
                        can_use = True
                        break
            for role in list(ctx.author._roles):
                if rperms := ctx.cache.get_allowed_perms(role):
                    for x in rperms:
                        if x in perms:
                            can_use = True
                            break
                else:
                    continue
            if can_use:
                return True

        return await commands.is_owner().predicate(ctx)
    return commands.check(predicate)

def has_permissions(**baseperms):
    async def predicate(ctx):
        if ctx.author.id == ctx.bot.owner_id:
            return True

        if not hasattr(ctx.command, 'perm_name') and not hasattr(ctx.command, 'category'):
            pass
        else:
            can_use = False

            perms = ctx.command.category.perm_names
            perms += ctx.command.perm_names

            if cperms := ctx.cache.get_allowed_perms(ctx.channel.id):
                for x in cperms:
                    if x in perms:
                        can_use = True
                        break
            if uperms := ctx.cache.get_allowed_perms(ctx.author.id):
                for x in uperms:
                    if x in perms:
                        can_use = True
                        break
            for role in list(ctx.author._roles):
                if rperms := ctx.cache.get_allowed_perms(role):
                    for x in rperms:
                        if x in perms:
                            can_use = True
                            break
                else:
                    if not can_use:
                        break
                    else:
                        continue
            if can_use:
                return True
            else:
                return await commands.has_permissions(**baseperms).predicate(ctx)
    return commands.check(predicate)

def is_guild(ID):
    def predicate(ctx):
        if ctx.guild.id == ID:
            return True
        else:
            raise Private()
    return commands.check(predicate)

def has_voted():
    async def predicate(ctx):
        check = await ctx.bot.dblpy.get_user_vote(ctx.author.id)
        if check:
            return True
        else:
            raise NoVoter()
    return commands.check(predicate)

def music(**perms):
    async def predicate(ctx):
        if perms.get("no_channel", True):
            if not ctx.author.voice or not ctx.author.voice.channel:
                raise MusicError(_('You must be in a voice channel to use this command.'))

        if perms.get("bot_no_channel", True):
            if not ctx.player.is_connected:
                raise MusicError(_('I am not connected to any voice channels.'))

        if perms.get("same_channel", True):
            if not ctx.player.voice_channel.id == ctx.author.voice.channel.id:
                raise MusicError(_('You must be in the same voice channel as me to use this command.'))

        if perms.get("not_playing", True):
            if not ctx.player.current:
                raise MusicError(_('No tracks currently playing.'))

        if perms.get("seekable", False):
           if not ctx.player.current.is_seekable:
               raise MusicError(_('This track is not seekable.'))

        if perms.get("no_tracks_shuffle", False):
            if not ctx.player.entries:
                raise MusicError('Add more tracks to the queue to enable queue track shuffling.')

        if perms.get("no_tracks_clear", False):
           if not ctx.player.entries:
               raise MusicError(_('Add more tracks to the queue to enable queue clearing.'))

        if perms.get("no_tracks_remove", False):
           if not ctx.player.entries:
               raise MusicError(_('Add more tracks to the queue to enable queue track removing.'))

        return True

    return commands.check(predicate)
