import discord
from aiohttp import web
from core.cog import SubCog


class IPC(SubCog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.create_listener())

    def cog_unload(self):
        self.bot.loop.create_task(self._webserver.stop())

    async def get_bot_invite(self, data):
        d = await data.json()
        user_id = d.get('id')
        user = await self.bot.try_user(int(user_id))
        if not user.bot:
            return web.json_response({'error': f'User {user} is not a bot!'})
        else:
            perms = 1576528982 if user.id == self.bot.user.id else 0
            msg = "Invite Charles to your server! (Charles' default prefix is c?)" if user.id == self.bot.user.id else f"Invite {user.name} to your server!" 
            if not user.public_flags.verified_bot:
                msg += "\n\nWarning: this bot is not verified! Which means that if the bot is in 100+ servers you can't invite it..."
            return web.json_response({'name': user.name, 'avatar': str(user.avatar.url), 'url': discord.utils.oauth_url(user.id, discord.Permissions(perms)), 'message': msg})

    async def get_bot_support(self, data):
        d = await data.json()
        user_id = d.get('id')
        user = await self.bot.try_user(int(user_id))
        if not user.bot:
            return web.json_response({'error': f'User {user} is not a bot!'})
        else:
            try:
                botinfo = await self.bot.dblpy.get_bot_info(int(user_id))
                support = f"https://discord.gg/{botinfo['support']}"
            except:
                try:
                    r = await self.bot.session.get(f"https://discord.bots.gg/api/v1/bots/{user_id}")
                    d = await r.json()
                    support = d['supportInvite']
                except:
                    return web.json_response({'error': f'No support server found for {user}!'})
                else:
                    # av = "https://media.discordapp.net/attachments/460568954968997890/698313600472973362/Devision_eye.png" if user.id == self.bot.user.id else str(user.avatar.url)
                    return web.json_response({'name': user.name, 'avatar': user.avatar.url, 'code': support})
            else:
                # av = "https://media.discordapp.net/attachments/460568954968997890/698313600472973362/Devision_eye.png" if user.id == self.bot.user.id else str(user.avatar.url)
                return web.json_response({'name': user.name, 'avatar': user.avatar.url, 'code': support})

    async def create_listener(self):
        app = web.Application(loop=self.bot.loop)
        app.router.add_get("/get_bot_invite", self.get_bot_invite)
        app.router.add_get("/get_bot_support", self.get_bot_support)
        runner = web.AppRunner(app)
        await runner.setup()
        self._webserver = web.TCPSite(runner, '0.0.0.0', 6666)
        await self._webserver.start()
