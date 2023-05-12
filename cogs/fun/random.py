import asyncio
import json
import random
import typing

import async_cleverbot as ac
import discord
import numpy
from core import i18n
from core.cog import SubCog
from core.commands import commandExtra
from core.context import SessionError
from discord.ext import commands


class Random(SubCog, category="Random"):
    def __init__(self, bot):
        self.bot = bot
        self.convos = []

    @commandExtra()
    async def advice(self, ctx):
        d = await ctx.get("https://api.adviceslip.com/advice", headers={"Content-Type": "application/json"}, return_type="read")
        dt = json.loads(d)
        await ctx.send(dt['slip']['advice'])

    @commandExtra()
    async def yomama(self, ctx):
        if random.random() > random.random():
            url = self.bot.get_url("dagpi")
            d = await ctx.get(url+"data/yomama", headers={"Authorization": self.bot.get_token("DAGPI")})
            await ctx.send(d['description'])
        else:
            d = await ctx.get("https://api.yomomma.info/")
            await ctx.send(d['joke'])

    @commandExtra()
    async def uselessfact(self, ctx):
        d = await ctx.get(self.bot.get_url('uselessfact'))
        await ctx.send(d['text'])

    async def talk(self, ctx):
        emotion = ctx.cache.cb_emotion

        def check(m):
            return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id  # and not ctx.valid

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await self.end_conversation(ctx)
            return

        if msg.content.lower() == "stop":
            await self.end_conversation(ctx)
            return

        mctx = await self.bot.get_context(msg)
        if mctx.valid:
            await self.talk(ctx)
            return

        text = msg.content
        emotions = {
            "neutral": {"t": ac.Emotion.neutral, "e": "😐"},
            "joy": {"t": ac.Emotion.joy, "e": "😄"},
            "fear": {"t": ac.Emotion.fear, "e": "😨"},
            "sad": {"t": ac.Emotion.sad, "e": "😢"},
            "anger": {"t": ac.Emotion.anger, "e": "😠"}
        }

        if emotion == "random":
            emotion = random.choice(list(emotions.values()))
        else:
            emotion = emotions[emotion]

        async with ctx.typing():
            try:
                response = await self.cb.ask(text, ctx.author.id, emotion=emotion['t'])
                await ctx.send(f"{ctx.author.mention}, {response.text} {emotion['e']}", edit=False)
            except ac.cleverbot.APIDown:
                await self.end_conversation(ctx, errored=True)
                await ctx.send(_("Oh no, it looks like I can't talk right now... There is a connection issue, please try again later!"))
                return

        await self.talk(ctx)

    async def end_conversation(self, ctx, errored=False):
        self.convos.remove(ctx.author.id)
        if not errored:
            emotion = ctx.cache.cb_emotion
            text = {
                "neutral": "Okay, let's talk again soon!",
                "joy": "Glad we talked, I had a lot of fun!",
                "fear": "Oh no, I'm scared to be alone...",
                "sad": "Are you leaving me already?...",
                "anger": "Fine, I don't need you anyway."
            }
            if emotion == "random":
                msg = random.choice(list(text.values()))
            else:
                msg = text[emotion]

            await ctx.send(f"{ctx.author.mention}, {msg}", edit=False)
        return

    @commandExtra(aliases=['talk', 'chat'])
    async def conversation(self, ctx):
        if ctx.author.id in self.convos:
            return await ctx.send(_("We are already in a conversation!"))

        self.convos.append(ctx.author.id)
        await ctx.send(_("A conversation has started! Say `stop` to end the conversation."))
        await self.talk(ctx)

    @commands.max_concurrency(number=1, per=commands.BucketType.user, wait=False)
    @commandExtra()
    async def ask(self, ctx, *, text: commands.clean_content):
        if len(text) > 60:
            return await ctx.send(_("Text must be more than 3 characters and shorter than 60!"))
        emotions = {
            "neutral": {"t": ac.Emotion.neutral, "e": "😐"},
            "joy": {"t": ac.Emotion.joy, "e": "😄"},
            "fear": {"t": ac.Emotion.fear, "e": "😨"},
            "sad": {"t": ac.Emotion.sad, "e": "😢"},
            "anger": {"t": ac.Emotion.anger, "e": "😠"}
        }

        emotion = ctx.cache.cb_emotion
        if emotion == "random":
            emotion = random.choice(list(emotions.values()))
        else:
            emotion = emotions[emotion]

        async with ctx.typing():
            try:
                response = await self.cb.ask(text, ctx.author.id, emotion=emotion['t'])
            except:
                raise SessionError(_("API is unavailable at the moment, try again later!"))
            try:
                await ctx.reply(f"{response.text} {emotion['e']}")
            except:
                await ctx.send(f"> {text}\n{ctx.author.mention} {response.text} {emotion['e']}")

    @commandExtra()
    async def xkcd(self, ctx, num: typing.Union[int, str]=None):
        if isinstance(num, int) and num > self.latest_xkcd:
            return await ctx.send(_("That xkcd does not exist! The latest is {0}, or use `xkcd latest` to get the latest!").format(str(self.latest_xkcd)))

        ext = f"/{num}"
        if isinstance(num, str) and num.lower() == "latest":
            ext = ''

        if num is None:
            ext = f"/{random.randint(1, self.latest_xkcd)}"

        res = await ctx.get(f'https://xkcd.com{ext}/info.0.json')

        e = discord.Embed(color=ctx.embed_color,
                          title=res["safe_title"],
                          description=res["alt"])
        e.set_image(url=res["img"])
        await ctx.send(embed=e)

    @commandExtra(aliases=['dice'])
    async def roll(self, ctx, amount:int=1):
        if (1 > amount) or (amount > 10):
            return await ctx.send(_("Please choose an amount between 1 and 10"))
        dices = []
        for i in range(amount):
            dices.append(random.choice(["<:dice_1:650521670616088586>", "<:dice_2:650521670712426510>", "<:dice_3:650521670653706250>", "<:dice_4:650521670641123368>", "<:dice_5:650521670486065153>", "<:dice_6:650521670725009418>"]))
        await ctx.send(_("You rolled: {0}").format(' '.join(dices)))

    @commandExtra(category="Funny")
    async def reddit(self, ctx, reddit):
        url = self.bot.get_url("reddit")
        r = await ctx.get(url.format(reddit))

        if not isinstance(r, (list, dict)):
            return await ctx.send(f"```json\n{r}```")
            return await ctx.send(_("Something went wrong while searching for that subreddit..."))

        if isinstance(r, list):
            if len(r) > 0:
                r = r[0]
            else:
                return await ctx.send(_("I could not find that subreddit!"))

        if not r['data']['children']:
            return await ctx.send(_("Something went wrong while searching for that subreddit..."))

        data = r['data']['children'][0]['data']
        if data['over_18'] and not ctx.channel.is_nsfw():
            return await ctx.send(_("This subreddit has been marked as **NSFW**! You can only view this in a NSFW channel."))

        e = discord.Embed(color=ctx.embed_color, title=f"/r/{reddit}", description=data['title'])
        e.set_image(url=data['url'])
        await ctx.send(embed=e)

    @commandExtra()
    async def fact(self, ctx, choice=None):
        facts = ['koala', 'dog', 'cat', 'panda', 'fox', 'bird', 'racoon', 'kangaroo', 'elephant', 'whale', 'giraffe']
        if choice == None:
            return await ctx.send(_("You can get a random fact from the following animals:\n\n`{0}`\n\nUse the command like: `{1}fact animal`").format(str('` | `'.join(facts)), ctx.prefix))

        if not choice.lower() in facts:
            return await ctx.send(_("You can get a random fact from the following animals:\n\n`{0}`\n\nUse the command like: `{1}fact animal`").format(str('` | `'.join(facts)), ctx.prefix))

        res = await ctx.get(self.bot.get_url('some_random_api').format(f'facts/{choice.lower()}'))
        await ctx.send(res['fact'])

    @commandExtra(aliases=['pokemon'])
    async def pokedex(self, ctx, *, pokemon: typing.Union[int, str]):
        if isinstance(pokemon, int):
            pokemon = await self.bot.db.fetchval("SELECT pokemon_name FROM pokemonlist WHERE pokemon_id = $1", pokemon)
        res = await ctx.get(self.bot.get_url('some_random_api').format(f'pokedex?pokemon={pokemon}'))

        if not res or 'error' in res:
            return await ctx.send(_("I was unable to find that pokemon..."))

        e = discord.Embed(color=ctx.embed_color)
        e.title = f"{res['name']} (#{res['id']})"
        desc = "**" + _("Type") + f":** {', '.join(res['type'])}\n"
        desc += "**" + _("Species") + f":** {', '.join(res['species'])}\n"
        desc += "**" + _("Abilities") + f":** {', '.join(res['abilities'])}\n\n"
        desc += "**" + _("Height") + f":** {res['height']}\n"
        desc += "**" + _("Weight") + f":** {res['weight']}\n"
        desc += "**" + _("Gender") + f":** {' / '.join(res['gender'])}\n\n"
        desc += "**" + _("Base Experience") + f":** {res['base_experience']}\n"
        desc += "**" + _("Egg Groups") + f":** {', '.join(res['egg_groups'])}\n\n"
        desc += "**" + _("Evolution Stage") + f":** {res['family']['evolutionStage']}\n"
        desc += "**" + _("Evolution Line") + f":** {', '.join(res['family']['evolutionLine'])}"
        e.description = desc

        stats = "**" + _("HP") + f":** {res['stats']['hp']}\n"
        stats += "**" + _("Attack") + f":** {res['stats']['attack']}\n"
        stats += "**" + _("Defense") + f":** {res['stats']['defense']}\n"
        stats += "**" + _("Special Attack") + f":** {res['stats']['sp_atk']}\n"
        stats += "**" + _("Special Defense") + f":** {res['stats']['sp_def']}\n"
        stats += "**" + _("Speed") + f":** {res['stats']['speed']}\n"
        stats += "**" + _("Total") + f":** {res['stats']['total']}"

        e.add_field(name=_("Stats"), value=stats)

        try:
            e.set_thumbnail(url=self.bot.get_url('pokedex').format(f"/{res['name']}.gif"))
        except Exception:
            e.set_thumbnail(url=self.bot.get_url('pokedex').format(f"-shiny/{res['name']}.gif"))
        e.set_footer(text=res['description'])

        await ctx.send(embed=e)

    @commandExtra(aliases=['8ball'])
    async def eightball(self, ctx, *, question):
        if len(question) > 100:
            return await ctx.send(_("The 8ball can't accept questions longer than 100 characters!"))
        yes = _("Yes")
        no = _("No")
        tal = _("Try again later...")
        ybtj = _("You'll be the judge")
        ml = _("Most likely")
        vd = _("Very doubtful")
        answer = random.choice([yes, no, tal, ybtj, ml, vd])
        question = question.rstrip("?")
        e = discord.Embed(color=ctx.embed_color, title=f"\U0001f3b1 {question}?", description=answer)
        await ctx.send(embed=e)

    @commandExtra(aliases=['flip', 'coin'])
    async def coinflip(self, ctx):
        num = numpy.random.randint(0, 100)
        if num == 50:
            return await ctx.send(_("WOAH! Big flipmaster here! You flipped the coin but it landed exactly on it's side!"))
        elif num < 50:
            return await ctx.send(_("You flipped a coin high in the air! And it landed on **tails**"))
        elif num > 50:
            return await ctx.send(_("That was a great flip! It landed on **heads**. I hope you guessed right!"))

    @commandExtra()
    async def rate(self, ctx, *, thing: commands.clean_content):
        if len(thing) > 75:
            return await ctx.send(_("I can't rate things longer than 75 characters!"))
        num = numpy.random.randint(0, 100, 2)

        if num[0] == 100:
            rating = num[0]
        else:
            rating = f"{num[0]}.{num[1]}"

        await ctx.send(_("Hmm, I would say... **{0}** is a {1}/100!").format(thing, rating))

    @commandExtra(aliases=['fite'])
    @commands.cooldown(1, 7, commands.BucketType.user)
    async def fight(self, ctx, user1: discord.Member, user2: discord.Member = None):
        user2 = user2 or ctx.author

        win = random.choice([user1, user2])
        if win == user1:
            lose = user2
        else:
            lose = user1

        await ctx.send(_("It was an intense battle, but {0} beat {1} in the fight!").format(win.mention, lose.mention))

def setup(bot):
    pass
