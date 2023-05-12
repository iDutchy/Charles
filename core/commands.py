import asyncio
import json

import discord
from discord.ext import commands, flags
from jishaku import Feature

from .cache import CacheManager as cm


class Category:
    def __init__(self, cog, name):
        self.name = name
        self.cog = cog
        self.cog_name = cog.qualified_name
        self.cachestring = f"{self.cog_name.lower()}_{self.name.lower().replace(' ', '-')}"
        self.all_commands = {}

    @property
    def perm_names(self):
        c = self.cog_name.lower()
        n = self.name.replace(' ', '').lower()
        return [f"{c}.*", f"{c}.{n}", f"{n}.*"]

    @property
    def commands(self):
        return set(self.all_commands.values())

    def __repr__(self):
        return f"<Category name={self.name} cog={self.cog_name}>"

    def __str__(self):
        return self.name

    def is_guild_disabled(self, ctx):
        return not cm.get("categories", ctx.guild.id, self.cachestring)

class groupPlusMixin(commands.GroupMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def command(self, *args, **kwargs):
        def decorator(func):
            kwargs.setdefault('parent', self)
            result = commandExtra(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator

    def group(self, *args, **kwargs):
        def decorator(func):
            kwargs.setdefault('parent', self)
            result = groupExtra(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator

class commandsPlus(commands.Command):
    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)

    def __repr__(self):
        return f"<Command name={self.qualified_name} cog={self.cog_name} category={self.category.name}>"

    @property
    def perm_names(self):
        c = self.cog_name.lower()
        n = self.qualified_name.replace(' ', '_').lower()
        p = [f"{c}.{n}"]
        if self.parent:
            pn = self.root_parent.qualified_name.replace(' ', '').lower()
            p.append(f"{c}.{pn}")
        for a in self.aliases:
            p.append(f"{c}.{a.replace(' ', '').lower()}")
        return p

    def is_guild_disabled(self, ctx):
        return self.qualified_name in cm.get("settings", ctx.guild.id, "disabled_commands")

    def is_global_disabled(self):
        return self.name in list(cm.globaldisabled.keys())

    async def can_run(self, ctx):
        if not self.enabled:
            raise commands.DisabledCommand('{0.name} command is disabled'.format(self))

        original = ctx.command
        ctx.command = self

        try:
            if not await ctx.bot.can_run(ctx):
                raise commands.CheckFailure('The global check functions for command {0.qualified_name} failed.'.format(self))

            cog = self.cog
            if cog is not None:
                local_sub_check = commands.Cog._get_overridden_method(cog._subcogs[ctx.command.category.name].cog_check)
                if local_sub_check is not None:
                    ret = await discord.utils.maybe_coroutine(local_sub_check, ctx)
                    if not ret:
                        return False
                local_check = commands.Cog._get_overridden_method(cog.cog_check)
                if local_check is not None:
                    ret = await discord.utils.maybe_coroutine(local_check, ctx)
                    if not ret:
                        return False


            predicates = self.checks
            if not predicates:
                # since we have no checks, then we just return True.
                return True

            return await discord.utils.async_all(predicate(ctx) for predicate in predicates)
        finally:
            ctx.command = original

def commandExtra(*args, cls=commandsPlus, **kwargs):
    return commands.command(*args, **kwargs, cls=cls)

class jishakuPlus(Feature.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._category = kwargs.pop("category", "No Category")
        self.qualified_name = kwargs.pop("name", "jishaku")
        if self.parent:
            self.qualified_name = self.parent.qualified_name + kwargs.pop("name", "jishaku")
        self.cog_name = self.category.cog_name

    def __repr__(self):
        return f"<Command name={self.qualified_name} cog={self.cog_name} category={self._category}>"

    @property
    def perm_names(self):
        c = self.cog_name.lower()
        n = self.qualified_name.replace(' ', '_').lower()
        p = [f"{c}.{n}"]
        if self.parent:
            pn = self.root_parent.qualified_name.replace(' ', '').lower()
            p.append(f"{c}.{pn}")

        return p

    # @property
    # def category(self):
    #     return Category(None, self._category, "Owner")

    def is_guild_disabled(self, ctx):
        return self.qualified_name in cm.get("settings", ctx.guild.id, "disabled_commands")

    def is_global_disabled(self):
        return self.qualified_name in list(cm.globaldisabled.keys())

def jskcmdExtra(*args, **kwargs):
    return jishakuPlus(*args, **kwargs)

class GroupPlus(groupPlusMixin, commands.Group):
    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)

    def __repr__(self):
        return f"<GroupCommand name={self.qualified_name} cog={self.cog_name} category={self.category.name}>"

    @property
    def perm_names(self):
        c = self.cog_name.lower()
        n = self.qualified_name.replace(' ', '_').lower()
        p = [f"{c}.{n}"]
        if self.parent:
            pn = self.root_parent.qualified_name.replace(' ', '').lower()
            p.append(f"{c}.{pn}")
        return p

    def is_guild_disabled(self, ctx):
        return self.qualified_name in cm.get("settings", ctx.guild.id, "disabled_commands")

    def is_global_disabled(self):
        return self.name in list(cm.globaldisabled.keys())

    async def can_run(self, ctx):
        if not self.enabled:
            raise commands.DisabledCommand('{0.name} command is disabled'.format(self))

        original = ctx.command
        ctx.command = self

        try:
            if not await ctx.bot.can_run(ctx):
                raise commands.CheckFailure('The global check functions for command {0.qualified_name} failed.'.format(self))

            cog = self.cog
            if cog is not None:
                local_sub_check = commands.Cog._get_overridden_method(cog._subcogs[ctx.command.category.name].cog_check)
                if local_sub_check is not None:
                    ret = await discord.utils.maybe_coroutine(local_sub_check, ctx)
                    if not ret:
                        return False
                local_check = commands.Cog._get_overridden_method(cog.cog_check)
                if local_check is not None:
                    ret = await discord.utils.maybe_coroutine(local_check, ctx)
                    if not ret:
                        return False
            predicates = self.checks
            if not predicates:
                # since we have no checks, then we just return True.
                return True

            return await discord.utils.async_all(predicate(ctx) for predicate in predicates)
        finally:
            ctx.command = original

def groupExtra(*args, **kwargs):
    return commands.group(*args, case_insensitive=True, **kwargs, cls=GroupPlus)

class flagsPlus(flags.FlagCommand):
    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)

    def __repr__(self):
        return f"<FlagCommand name={self.qualified_name} cog={self.cog_name} category={self.category.name}>"

    @property
    def perm_names(self):
        c = self.cog_name.lower()
        n = self.qualified_name.replace(' ', '_').lower()
        p = [f"{c}.{n}"]
        if self.parent:
            pn = self.root_parent.qualified_name.replace(' ', '').lower()
            p.append(f"{c}.{pn}")
        return p

    def is_guild_disabled(self, ctx):
        return self.qualified_name in cm.get("settings", ctx.guild.id, "disabled_commands")

    def is_global_disabled(self):
        return self.name in list(cm.globaldisabled.keys())

    async def can_run(self, ctx):
        if not self.enabled:
            raise commands.DisabledCommand('{0.name} command is disabled'.format(self))

        original = ctx.command
        ctx.command = self

        try:
            if not await ctx.bot.can_run(ctx):
                raise commands.CheckFailure('The global check functions for command {0.qualified_name} failed.'.format(self))

            cog = self.cog
            if cog is not None:
                local_sub_check = commands.Cog._get_overridden_method(cog._subcogs[ctx.command.category.name].cog_check)
                if local_sub_check is not None:
                    ret = await discord.utils.maybe_coroutine(local_sub_check, ctx)
                    if not ret:
                        return False
                local_check = commands.Cog._get_overridden_method(cog.cog_check)
                if local_check is not None:
                    ret = await discord.utils.maybe_coroutine(local_check, ctx)
                    if not ret:
                        return False

            predicates = self.checks
            if not predicates:
                # since we have no checks, then we just return True.
                return True

            return await discord.utils.async_all(predicate(ctx) for predicate in predicates)
        finally:
            ctx.command = original

def flagsExtra(*args, **kwargs):
    return commands.command(*args, **kwargs, cls=flagsPlus)
