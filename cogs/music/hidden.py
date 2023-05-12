from core.cog import SubCog
from core.commands import commandExtra
from discord.ext import commands
from utils.paginator import EmbedPages


class MusicHidden(SubCog, category="Hidden"):
    def __init__(self, bot):
        self.bot = bot

    # @commands.is_owner()
    # @commandExtra(category="Hidden")
    # async def playerinfo(self, ctx):
    #     stats = await ctx.player.node.stats

    #     used = humanize.naturalsize(stats['memory_used'])
    #     total = humanize.naturalsize(stats['memory_allocated'])
    #     free = humanize.naturalsize(stats['memory_free'])
    #     cpu = stats['cpu_cores']

    #     embed = discord.Embed(color=ctx.embed_color, title=f'diorite: {diorite.__version__}')

    #     fmt = f'Connected to `{len(self.bot.diorite.nodes)}` nodes.\n' \
    #           f'Best available Node `{self.bot.diorite.get_best_node().__repr__()}`\n' \
    #           f'`{len(self.bot.diorite.players)}` players are distributed on nodes.\n' \
    #           f'`{stats["players"]}` players are distributed on server.\n' \
    #           f'`{stats["playing_players"]}` players are playing on server.\n\n' \
    #           f'Server Memory: `{used}/{total}` | `({free} free)`\n' \
    #           f'Server CPU: `{cpu}`\n\n' \
    #           f'Server Uptime: `{timedelta(milliseconds=stats["uptime"])}`'

    #     embed.description = fmt
    #     await ctx.send(embed=embed)

    @commands.is_owner()
    @commandExtra(category="Hidden")
    async def players(self, ctx):
        entries = []
        for p in self.bot.diorite.players.values():
            info = []
            info.append(f"**Guild:** {p.ctx.guild.name}")
            info.append(f"**DJ:** {p.dj} ({p.dj.id})")
            info.append("\u200b")
            info.append(f"**Is Playing:** {p.is_playing}")
            if p.is_playing:
                info.append(f"**Current:** {p.current.title}")
                info.append(f"**Queue:** {len(p.queue._queue)} songs")

            entries.append("\n".join(info))

        paginator = EmbedPages(ctx,
                          title='Connected Players',
                          entries=entries)

        await paginator.start()


def setup(bot):
    pass
