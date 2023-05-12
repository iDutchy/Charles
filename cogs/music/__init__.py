import diorite
from core.cog import MainCog
from core.emojis import Emoji


class Music(MainCog, name="Music"):
    __all__ = ('bot', 'icon', 'big_icon', 'controls')

    def __init__(self, bot):
        self.bot = bot
        self.icon = "<:charlesDJ:615428841888022528>"
        self.big_icon = "https://cdn.discordapp.com/emojis/615428841888022528.png"
        self.controls = {Emoji.music_note: 'Main_Page',
                         Emoji.track_info: 'Song_Info_Page',
                         Emoji.lyrics: 'Lyric_Page',
                         Emoji.mp3: 'Download_Song',
                         Emoji.delete: 'Delete_Page',
                         Emoji.qmark: 'Info_Page'}

        if not hasattr(bot, "diorite"):
            bot.diorite = diorite.Client(bot)

        self.bot.loop.create_task(self.start_node())

    async def start_node(self):
        await self.bot.wait_until_ready()

        if self.bot.diorite.players:
            return

        # await self.bot.diorite.create_node(
        #     host="127.0.0.1",
        #     port=2333,
        #     password="youshallnotpass",
        #     identifier="ALPHA",
        # )

        await self.bot.diorite.create_node(
            host='lavalink.gaproknetwork.xyz',
            port=2333,
            password='gaproklavalink',
            identifier='BETA'
        )


def setup(bot):
    cog = bot.add_cog(Music(bot))
    cog.add_subcogs(__package__)
