import jishaku
import sys
import discord
import humanize
import psutil
import import_expression

# from discord.ext import commands
# from jishaku.cog import JishakuBase
from core.cog import GroupCogMeta
from core.commands import jskcmdExtra
from jishaku import repl, Feature

NEW_CORO_CODE = """
async def _repl_coroutine({{0}}):
    import asyncio
    from importlib import import_module as {0}

    import aiohttp
    import discord
    from discord.ext import commands

    from core.cache import CacheManager as cm
    from core.database import DB as db

    try:
        import jishaku
    except ImportError:
        jishaku = None  # keep working even if in panic recovery mode

    try:
        pass
    finally:
        _async_executor.scope.globals.update(locals())
""".format(import_expression.constants.IMPORTER)
repl.compilation.CORO_CODE = NEW_CORO_CODE

@jskcmdExtra(name="jishaku", aliases=["jsk"], invoke_without_command=True, ignore_extra=False, category="Other")
async def jsk(self, ctx):
    summary = [
        f"Jishaku v{jishaku.__version__}, enhanced-dpy (custom d.py) `{discord.__version__}`, "
        f"`Python {sys.version}` on `{sys.platform}`".replace("\n", ""),
        f"Module was loaded {humanize.naturaltime(self.load_time)}, "
        f"cog was loaded {humanize.naturaltime(self.start_time)}.",
        ""
    ]

    proc = psutil.Process()
    with proc.oneshot():
        mem = proc.memory_full_info()
        summary.append(f"Using {humanize.naturalsize(mem.rss)} physical memory and "
                       f"{humanize.naturalsize(mem.vms)} virtual memory, "
                       f"{humanize.naturalsize(mem.uss)} of which unique to this process.")
        name = proc.name()
        pid = proc.pid
        thread_count = proc.num_threads()
        summary.append(f"Running on PID {pid} (`{name}`) with {thread_count} thread(s).")

        summary.append("")

    cache_summary = f"{len(self.bot.guilds)} guild(s) and {len(self.bot.users)} user(s)"

    summary.append(f"This bot is automatically sharded and can see {cache_summary}.")

    presence_setting = "ON" if self.bot._connection.guild_subscriptions else "OFF"

    if self.bot._connection.max_messages is None:
        summary.append(f"Message cache is disabled and presence/typing events are {presence_setting}")
    else:
        summary.append(
            f"Message cache capped at {self.bot._connection.max_messages} and "
            f"presence/typing events are {presence_setting}"
        )

    summary.append(f"Average websocket latency: {round(self.bot.latency * 1000, 2)}ms")

    await ctx.send("\n".join(summary))

class NewJsk(*jishaku.OPTIONAL_FEATURES, *jishaku.STANDARD_FEATURES, metaclass=GroupCogMeta, command_parent=jsk):
    def __init__(self, bot):
        super(NewJsk, self).__init__(bot=bot)
        self.bot = bot
        self.icon = ""
        self.big_icon = ""

def setup(bot):
    bot.add_cog(NewJsk(bot=bot))