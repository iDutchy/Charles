import asyncio
import re
from functools import partial
from io import BytesIO
import mimetypes
import yarl
import time
import random
import string

import discord
import html2text
from bs4 import BeautifulSoup
from core import i18n
from core.cog import SubCog
from core.commands import GroupPlus, commandExtra, commandsPlus, groupExtra, flagsExtra
from core.emojis import Emoji as emoji
from discord.ext import commands, flags
from PIL import Image, ImageDraw, ImageFont
from tabulate import tabulate
from utils import checks
from utils.async_shell import run, update
from utils.converters import ImageConverter, executor
from utils.humanize_time import date, timesince
from utils.paginator import EmbedPages
from utils.utility import Acknowledgements
from youtube_dl import YoutubeDL

anilist_query = """
query ($id: Int, $search: String) {
  Page(page: 1, perPage: 1) {
    media(id: $id, search: $search) {
      id
      idMal
      isAdult
      startDate {
        year
        month
        day
      }
      endDate {
        year
        month
        day
      }
      status
      episodes
      description
      genres
      averageScore
      coverImage {
        extraLarge
        color
      }
      title {
        romaji
        english
        native
      }
    }
  }
}"""

RRQ1 = """INSERT INTO
    reactionrole_settings(
        guild_id,
        message_id,
        max_roles,
        message,
        role_restrict,
        channel_id,
        unique_id
    )
    VALUES(
        $1, $2, $3, $4, $5, $6, $7
    )"""

RRQ2 = """INSERT INTO
    reactionrole_data(
        guild_id,
        message_id,
        role_id,
        emoji
    )
    VALUES(
        $1, $2, $3, $4
    )"""


def c(t, e):
    return f"{emoji.arrow} **{t}:** {e}"


class Tests(SubCog, category="Test Commands"):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.sessions = set()
        self.tomd = html2text.HTML2Text()

    async def cog_check(self, ctx):
        return await checks.is_owner().predicate(ctx)

    @staticmethod
    def is_image(url):
        mimetype, encoding = mimetypes.guess_type(url.replace('?size=1024', ''))
        return mimetype and mimetype.startswith('image')

    @flags.add_flag("--scratches", "-s", action="store_true", default=False)
    @flagsExtra(name='repair')
    async def restore(self, ctx, image: ImageConverter = "", **options):
        # url = self.bot.get_url("hotpot") + "colorize-picture"
        headers = {'Authorization': self.bot.get_token("HOTPOT")}
        if not self.is_image(image):
            if len(ctx.message.attachments) > 0:
                image = ctx.message.attachments[0].url
            else:
                image = ctx.author.avatar.url

        data = {'image': await ctx.get(image, return_type='read'),
                'withScratch': 'true' if options.get("scratches") else 'false'}

        async with self.bot.session.post("https://api-bin.hotpot.ai/restore-picture", headers=headers, data=data) as f:
            res = await f.read()
        file = discord.File(BytesIO(res), 'repair.png')
        e = discord.Embed(title="AI Picture Repair", color=0x3E2B47)
        e.set_image(url="attachment://repair.png")
        e.set_footer(text="Powered by hotpot.ai",icon_url="https://miro.medium.com/fit/c/1360/1360/1*iYlDLt-RAQciyrtEexw_GA.jpeg")
        await ctx.send(embed=e, file=file)

    @commandExtra()
    async def prntsc(self, ctx):
        ss = "".join(random.choice(string.ascii_lowercase + string.digits) for i in range(6))
        await ctx.send("https://prnt.sc/"+ss, edit=False)

    @commandExtra(name='remove-bg')
    async def remove_bg(self, ctx, image: ImageConverter = ""):
        # url = self.bot.get_url("hotpot") + "colorize-picture"
        headers = {'Authorization': self.bot.get_token("HOTPOT")}
        if not self.is_image(image):
            if len(ctx.message.attachments) > 0:
                image = ctx.message.attachments[0].url
            else:
                image = ctx.author.avatar.url

        data = {'image': await ctx.get(image, return_type='read')}

        async with self.bot.session.post("https://api-bin.hotpot.ai/remove-background", headers=headers, data=data) as f:
            res = await f.read()
        file = discord.File(BytesIO(res), 'removebg.png')
        e = discord.Embed(title="AI Background Remover", color=0x3E2B47)
        e.set_image(url="attachment://removebg.png")
        e.set_footer(text="Powered by hotpot.ai",icon_url="https://miro.medium.com/fit/c/1360/1360/1*iYlDLt-RAQciyrtEexw_GA.jpeg")
        await ctx.send(embed=e, file=file)

    @flags.add_flag("--factor", '-f', type=int, default=12)
    @flagsExtra()
    async def colorize(self, ctx, image: ImageConverter = "", **options):
        if 0 > options.get('factor') > 50:
            return await ctx.send("Colorization factor must be between 0-50")
        # url = self.bot.get_url("hotpot") + "colorize-picture"
        headers = {'Authorization': self.bot.get_token("HOTPOT")}
        if not self.is_image(image):
            if len(ctx.message.attachments) > 0:
                image = ctx.message.attachments[0].url
            else:
                image = ctx.author.avatar.url

        data = {'image': await ctx.get(image, return_type='read'),
                'renderFactor': str(options.get('factor'))}

        async with self.bot.session.post("https://api-bin.hotpot.ai/colorize-picture", headers=headers, data=data) as f:
            res = await f.read()
        file = discord.File(BytesIO(res), 'colorize.png')
        e = discord.Embed(title="AI Black&White Colorizer", color=0x3E2B47)
        e.set_image(url="attachment://colorize.png")
        e.set_footer(text="Powered by hotpot.ai",icon_url="https://miro.medium.com/fit/c/1360/1360/1*iYlDLt-RAQciyrtEexw_GA.jpeg")
        await ctx.send(embed=e, file=file)

    @flags.add_flag('--factor4', '-f4', action="store_true", default=False)
    @flags.add_flag("--anime", '-a', action="store_true", default=False)
    @flagsExtra()
    async def enlarge(self, ctx, image: ImageConverter = "", **options):
        # url = self.bot.get_url("hotpot") + "colorize-picture"
        headers = {'Authorization': self.bot.get_token("HOTPOT")}
        if not self.is_image(image):
            if len(ctx.message.attachments) > 0:
                image = ctx.message.attachments[0].url
            else:
                image = ctx.author.avatar.url

        data = {'image': await ctx.get(image, return_type='read'),
                'noiseCancellationFactor': "2",
                'imageStyle': "anime" if options.get('anime') else "default",
                'sizeFactor': "4" if options.get('factor4') else "2"}

        async with self.bot.session.post("https://api-bin.hotpot.ai/supersize-image", headers=headers, data=data) as f:
            res = await f.read()
        file = discord.File(BytesIO(res), 'large.png')
        e = discord.Embed(title="AI Image Enlarger", color=0x3E2B47)
        e.set_image(url="attachment://large.png")
        e.set_footer(text="Powered by hotpot.ai",icon_url="https://miro.medium.com/fit/c/1360/1360/1*iYlDLt-RAQciyrtEexw_GA.jpeg")
        await ctx.send(embed=e, file=file)

    @executor
    def get_ss(self, url):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        opts = Options()
        opts.add_argument('--no-sandbox')
        opts.add_argument("--headless")
        opts.add_argument("--hide-scrollbars")
        opts.binary_location = "/usr/bin/google-chrome"
        chrome_driver = "/usr/bin/chromedriver"
        driver = webdriver.Chrome(options=opts, executable_path=chrome_driver)
        driver.get(str(url))
        time.sleep(0.5)
        driver.execute_script("document.body.innerHTML = document.body.innerHTML.replace(/38.105.209.124/g, 'Imagine trying to find IP! Smh...');")
        file = discord.File(BytesIO(driver.get_screenshot_as_png()), "ss.png")
        return file

    @commandExtra()
    async def ss(self, ctx, site):
        url = yarl.URL(site.strip("<>"))
        with open("db/pornsites.txt") as f:
            sites = [s.strip("\n") for s in f.readlines()]
        if url.host in sites:
            return await ctx.send("NSFW sites are blocked!")

        try:
            file = await self.get_ss(url)
        except Exception as e:
            return await ctx.send(f"***CATASTROPHIC FAILURE!!!!!*** `{e}`")
        await ctx.send(embed=discord.Embed(color=ctx.embed_color, title=str(url)).set_image(url="attachment://ss.png"), file=file)

    @commandExtra()
    async def tib(self, ctx, *, url: ImageConverter=""):

        def has_transparency(img):
            if img.mode == "P":
                transparent = img.info.get("transparency", -1)
                for x, index in img.getcolors():
                    if index == transparent:
                        return True
            elif img.mode == "RGBA":
                extrema = img.getextrema()
                if extrema[3][0] < 255:
                    return True

            return False

        def is_image(url):
            import mimetypes
            mimetype, encoding = mimetypes.guess_type(url.replace('?size=1024', ''))
            return mimetype and mimetype.startswith('image')

        if not is_image(url):
            if len(ctx.message.attachments) > 0:
                url = ctx.message.attachments[0].url
            else:
                url = str(ctx.author.avatar.url)

        async with self.bot.session.get("https://cdn.discordapp.com/attachments/821763480189141042/821764021296037968/final_5c11652ff41bff00120b1c29_347144.jpg") as f:
            bg = Image.open(BytesIO(await f.read()))
        async with self.bot.session.get(url) as f:
            av = Image.open(BytesIO(await f.read()))

        av = av.resize((int(bg.size[0]/4), int(bg.size[1]/4)))
        if has_transparency(av):
            bg.paste(av, (432,42), av)
            bg.paste(av, (432,380), av)
        else:
            bg.paste(av, (432,42))
            bg.paste(av, (432,380))
        buf = BytesIO()
        bg.save(buf, 'PNG')
        buf.seek(0)
        f = discord.File(buf, 'th.png')
        await ctx.send(file=f)

    @commandExtra()
    async def wide(self, ctx, user: discord.User):
        async with self.bot.session.get(str(user.avatar.with_format("png"))) as res:
            img = Image.open(BytesIO(await res.read()))

        @executor
        def resize(img):
            img = img.resize((int(img.size[0]*2), int(img.size[1]/2)))
            return img

        img = await resize(img)
        buf = BytesIO()
        img.save(buf, "PNG")
        buf.seek(0)
        img.close()
        await ctx.send(file=discord.File(buf, 'wide.png'))

    # @flags.add_flag('content', nargs="+", type=str)
    # @flags.add_flag('-bg', '--background', type=int, default=None)
    # @flags.add_flag('-txt', '--text', type=int, default=None)
    # @flagsExtra()
    # async def retrosign(self, ctx, **flags):
    #     content = " ".join(flags.get('content'))
    #     words = [t.strip() for t in content.split("|")]
    #     if len(words) == 1:
    #         word1, word2, word3 = "", words[0], ""
    #     elif len(words) == 3:
    #         word1, word2, word3 = words[0], words[1], words[2]
    #     else:
    #         return await ctx.send("Please provide either 1 or 3 lines, separated by a |")

    #     def normalize(text):
    #         return re.sub(r'[^A-Za-z0-9 ]', '', unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('UTF-8'))

    #     word1, word2, word3 = normalize(word1), normalize(word2), normalize(word3)

    #     if len(word1) > 14:
    #         return await ctx.send(f"{ctx.emoji.xmark} | Your first line exceeded the limit! ({len(word1)}/14)")
    #     if len(word2) >= 13:
    #         if not word1:
    #             return await ctx.send(f"{ctx.emoji.xmark} | Your line exceeded the limit! ({len(word2)}/12)")
    #         return await ctx.send(f"{ctx.emoji.xmark} | Your second line exceeded the limit! ({len(word2)}/12)")
    #     if len(word3) >= 26:
    #         return await ctx.send(f"{ctx.emoji.xmark} | Your third line exceeded the limit! ({len(word3)}/25)")

    #     if not (bcg := flags.get('background')):
    #         bcg = random.randint(1, 5)
    #     if not (txt := flags.get('text')):
    #         txt = random.randint(1, 4)

    #     if bcg not in range(1, 6):
    #         return await ctx.send("Background type must be a number between 1 and 5!")
    #     if txt not in range(1, 5):
    #         return await ctx.send("Text type must be a number between 1 and 4!")

    #     data = {
    #         "bcg": bcg,
    #         "txt": txt,
    #         "text1": word1,
    #         "text2": word2,
    #         "text3": word3
    #     }

    #     async with ctx.channel.typing():
    #         async with self.bot.session.post("https://photofunia.com/effects/retro-wave", data=data) as response:
    #             if response.status != 200:
    #                 return await ctx.send("API failed, please try again later...")

    #             soup = BeautifulSoup(await response.text(), "html.parser")
    #             download_url = soup.find("div", class_="downloads-container").ul.li.a["href"]
    #             image = await ctx.get(download_url, return_type="io")
    #             await ctx.send(file=discord.File(fp=image, filename="retro.png"))

    @commandExtra()
    @commands.guild_only()
    async def createdat(self, ctx, *, user: discord.User = None):
        user = user or ctx.author

        embed = discord.Embed(colour=ctx.embed_color)
        embed.set_thumbnail(url=user.avatar.url)
        embed.description = _("**{0}** created their account on:\n\n{1}\n*{2}*").format(user, date(user.created_at), timesince(user.created_at))
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_socket_response(self, m):
        if m['op'] == 0:
            self.bot.socket_stats[m['t']] += 1

    @commandExtra(name="socketstats")
    async def socketstats(self, ctx):
        table = [[k, v] for k, v in self.bot.socket_stats.items()]
        tab = tabulate(table, headers=["EVENT", "TOTAL"], tablefmt="fancy_grid", stralign='right', numalign='left')
        tab_pre = "\n".join(tab.splitlines()[:3])
        tab_suf = tab.splitlines()[-1]
        entries = [t for t in tab.splitlines()[3:-1] if not t.startswith("├─")]
        await EmbedPages(ctx, prefix=f"```ml\n{tab_pre}\n", suffix=f"\n{tab_suf}```", entries=entries, per_page=15).start()
        # await ctx.send(f"```ml\n{tab}```")

    @commandExtra(name='tableinfo')
    async def tableinfo(self, ctx, table):
        q = """SELECT
            table_name,
            column_name,
            column_default,
            is_nullable,
            data_type,
            character_maximum_length
        FROM
            INFORMATION_SCHEMA.COLUMNS
        WHERE
            table_name = $1
            """
        try:
            d = await self.bot.db.fetch(q, table)
        except:
            return await ctx.send("Something fucked")

        e = discord.Embed(color=ctx.embed_color, title=f"Table: {d[0]['table_name']}")
        desc = []
        for item in d:
            for k, v in dict(item).items():
                desc.append(f"{ctx.emoji.arrow} **{k.replace('_', ' ').title()}:** {v}")
            desc.append('\n')
        e.description = "\n".join(desc)
        try:
            await ctx.send(embed=e)
        except:
            await ctx.send("Too long, make it paginated first mkay.")

    @groupExtra(invoke_without_command=True)
    async def raidmode(self, ctx):
        await ctx.invoke(self.bot.get_command('raidmode medium'))

    @raidmode.command(name='low')
    async def raidmode_low(self, ctx):
        pass

    # @commandExtra()
    # async def testidk(self, ctx, user1: discord.User, user2: discord.User):
    #     img1 = Image.open(BytesIO(await user1.avatar.with_format("png", size=1024).read()))
    #     img2 = Image.open(BytesIO(await user2.avatar.with_format("png", size=1024).read()))
    #     img1 = img1.convert("RGBA")
    #     img2 = img2.convert("RGBA")
    #     img2 = img2.resize(img1.size)
    #     pixdata1 = img1.load()
    #     pixdata2 = img2.load()

    #     for x in range(0, img1.size[0]):
    #         # nums = list(range(0, img1.size[0]))
    #         # half = int(len(nums)/2)
    #         # for i in range(half):
    #         #     nums.remove(random.choice(nums))
    #         for y in range(0, img1.size[1]):
    #             # if x <= (img1.size[1]/2-50) or x >= (img1.size[1]/2+50):
    #             #     pixdata1[x, y] = pixdata2[x, y]
    #             # else:
    #             xd, _ = divmod(x, random.randint(1, 100))
    #             yd, _ = divmod(y, random.randint(1, 100))
    #             # if (xd % 2) == 0 and (yd % 2) == 0:
    #             if yd > xd:
    #                 pixdata1[x, y] = pixdata2[x, y]
    #                 # idk = 1
    #             # if (xd % 2) != 0 and (yd % 2) == 0:
    #             #     pixdata1[x, y] = pixdata2[x, y]
    #             else:
    #                 # idk += 1
    #                 continue

    #     buf = BytesIO()
    #     img1.save(buf, "png")
    #     buf.seek(0)

    #     await ctx.send(file=discord.File(buf, 'idfk.png'))

    @groupExtra(name='pip', invoke_without_command=True)
    async def pip_management(self, ctx):
        await ctx.send_help(ctx.command)

    @pip_management.command(name='outdated')
    async def pip_outdated(self, ctx):
        txt = []
        async with ctx.loading("Looking for outdated pip packages"):
            t = await run('pip list --outdated')
            out = t.splitlines()[2:]
            for line in out:
                data = list(filter(None, line.split(' ')))
                txt.append(f"`{data[0]}` - **v{data[1]}** >> **v{data[2]}**")

        await self.bot.utils.paginate(ctx,
                                      show_entry_count=True,
                                      entries=txt,
                                      per_page=10)

    @pip_management.command(name='update')
    async def pip_update(self, ctx, package):
        async with ctx.loading(f"Updating `{package}`"):
            up = await update(package)
            if not up.updated:
                await ctx.send(f"`{package}` is already on the latest version...")
            else:
                await ctx.send(f"`{package}` has been updated from **v{up.old_version}** to **v{up.new_version}**!")

    @pip_management.command(name="show")
    async def pip_show(self, ctx, package):
        async with ctx.loading("Gathering package info"):
            t = await run(f"pip show {package}")
            if t.startswith("WARNING"):
                await ctx.send(f"Package `{package}` not found!")
            else:
                txt = re.sub(r"^([a-zA-Z_]+?\S?[a-zA-Z_]+\:)", r"<:arrow:735653783366926931> **\1**", t, flags=re.MULTILINE)
                # lines = []
                # for line in t.splitlines():
                #     lines.append(re.sub(r"^([a-zA-Z_]+?\S?[a-zA-Z_]+\:)", r"<:arrow:735653783366926931> **\1**", line))
                e = discord.Embed(color=ctx.embed_color, title=f"Package info for `{package}`", description=txt)  # "\n".join(lines))
                await ctx.send(embed=e)

    @commandExtra(category="Test Commands", name='get-claimable-tags')
    async def getclaimabletags(self, ctx):
        with open('tags.txt', 'r') as f:
            tags = f.read()

        claims = []

        all_ = tags.splitlines()[3:-1]
        for z in all_:
            try:
                if z.split("|")[6].strip() == "True":
                    continue
                uid = z.split("|")[3]
                if not uid.strip().isdigit():
                    continue
                try:
                    if not ctx.guild.get_member(int(uid.strip())):
                        claims.append(z.split("|")[2].strip())
                except discord.NotFound:
                    claims.append(z.split("|")[2].strip())
            except:
                continue

        with open('to_claim.txt', 'w') as f:
            f.write("\n".join(f"?tag claim {x}" for x in claims))

        await ctx.send(f"Found {len(claims)} tags to claim!")

    @commandExtra(category="Test Commands", name="add-acknowledgement")
    async def add_acknowledgement(self, ctx, user: discord.User = None, atype: int = None):
        if not user:
            types = "\n".join(f"`{x.value}` - **{x.name.replace('_', ' ').title()}**" for x in list(Acknowledgements.__members__.values()))
            return await ctx.send(f"Available acknowledgements are:\n\n{types}")
        if user.id in self.bot.cache.acknowledgements:
            if atype in self.bot.cache.acknowledgements[user.id]:
                return await ctx.send("This user already has this acknowledgement!")
            self.bot.cache.acknowledgements[user.id].append(atype)
        else:
            self.bot.cache.acknowledgements[user.id] = [atype]
        await self.bot.db.execute("INSERT INTO acknowledgements(user_id, acknowledgement_type) VALUES($1, $2)", user.id, atype)
        await ctx.send(f"Succesfully added **{Acknowledgements(atype).name.replace('_', ' ').title()}** to `{user}`'s acknowledgements!")

    def makebar(self, im, progress):
        bgcolor = 'rgb(255, 255, 255)'
        color = 'rgb(180, 180, 180)'
        x = 650
        y = 350
        w = 900
        h = 100

        drawObject = ImageDraw.Draw(im)

        drawObject.ellipse((x+w, y, x+h+w, y+h), fill=bgcolor)
        drawObject.ellipse((x, y, x+h, y+h), fill=bgcolor)
        drawObject.rectangle((x+(h/2), y, x+w+(h/2), y+h), fill=bgcolor)

        # if(progress<=0):
        #    progress = 0.01
        # if(progress>1):
        #    progress=1
        w = w / 100 * progress

        drawObject.ellipse((x+w, y, x+h+w, y+h), fill=color)
        drawObject.ellipse((x, y, x+h, y+h), fill=color)
        drawObject.rectangle((x+(h/2), y, x+w+(h/2), y+h), fill=color)

        return im

    def adduser(self, bg, user, mask, username, userdiscrim):
        p_bar = self.makebar(bg, 72.95)

        mask = mask.resize((400, 400), Image.ANTIALIAS)
        user = user.resize((400, 400), Image.ANTIALIAS)
        p_bar.paste(user, (125, 125), mask)

        draw = ImageDraw.Draw(p_bar)
        font = ImageFont.truetype('db/fonts/roboto.ttf', size=150)
        color = 'rgb(255, 255, 255)'
        draw.text((650, 145), username, fill=color, font=font)
        font = ImageFont.truetype('db/fonts/roboto.ttf', size=75)
        color = 'rgb(180, 180, 180)'
        draw.text((1125, 210), f"#{userdiscrim}", fill=color, font=font)

        return p_bar

    @commandExtra(category="Test Commands")
    async def profiletest(self, ctx):
        with open('db/images/b_bg.jpg', 'rb') as f:
            bg = Image.open(BytesIO(f.read())).convert("RGBA")

        with open('db/images/circle-mask.jpg', 'rb') as f:
            mask = Image.open(BytesIO(f.read())).convert("L")

        async with self.bot.session.get(str(ctx.author.avatar.with_format("png"))) as r:
            user = Image.open(BytesIO(await r.read()))

        name = ctx.author.name
        discrim = ctx.author.discriminator

        to_run = partial(self.adduser, bg, user, mask, name, discrim)

        img = await self.bot.loop.run_in_executor(None, to_run)

        buffer = BytesIO()
        img.save(buffer, 'png')
        buffer.seek(0)

        f = discord.File(fp=buffer, filename='testing.png')
        await ctx.send(content="testing", file=f)
        img.close()

    @commandExtra(category="Test Commands")
    async def anime(self, ctx, *, search: str):
        await ctx.trigger_typing()
        async with self.bot.session.post("https://graphql.anilist.co", json={
            "query": anilist_query,
            "variables": {
                "search": search
            }
        }) as res:
            data = await res.json()
        if data.get("errors", []):
            return await ctx.send("Error getting data from anilist: {}".format(data["errors"][0]["message"]))
        media = data["data"]["Page"]["media"]
        if not media:
            return await ctx.send("Nothing found.")
        media = media[0]
        if media["isAdult"] is True and not ctx.channel.is_nsfw():
            return await ctx.send("NSFW Anime can't be displayed in non NSFW channels.")
        color = int(media["coverImage"]["color"].replace("#", ""), 16) if media["coverImage"]["color"] else 0xdeadbf
        em = discord.Embed(colour=color)
        em.title = "{} ({})".format(media["title"]["romaji"], media["title"]["english"])
        if media["description"]:
            desc = BeautifulSoup(media["description"], "lxml")
            if desc:
                em.description = desc.text
        em.url = "https://anilist.co/anime/{}".format(media["id"])
        em.set_thumbnail(url=media["coverImage"]["extraLarge"])
        em.add_field(name="Status", value=media["status"].title(), inline=True)
        em.add_field(name="Episodes", value=media["episodes"], inline=True)
        em.add_field(name="Score", value=str(media["averageScore"]), inline=True)
        em.add_field(name="Genres", value=", ".join(media["genres"]))
        dates = "{}/{}/{}".format(media["startDate"]["day"], media["startDate"]["month"], media["startDate"]["year"])
        if media["endDate"]["year"] is not None:
            dates += " - {}/{}/{}".format(media["endDate"]["day"], media["endDate"]["month"], media["endDate"]["year"])
        em.add_field(name="Date", value=dates)
        await ctx.send(embed=em)

    @commandExtra(category="Test Commands")
    async def movie(self, ctx, *, movie):
        movie = movie.replace(" ", "+")
        async with self.bot.session.get(f'http://www.omdbapi.com/?apikey=35629e47&t={movie}') as r:
            data = await r.json()

        e = discord.Embed(color=ctx.embed_color)
        e.title = data['Title']

        desc = f"{data['Plot']}\n\n"
        desc += f"**Year:** {data['Year']}\n"
        desc += f"**Rated:** {data['Rated']}\n"
        desc += f"**Released:** {data['Released']}\n"
        desc += f"**Duration:** {data['Runtime']}\n"
        desc += f"**On DVD:** {data['DVD']}\n"
        desc += f"**Genre:** {data['Genre']}\n\n"
        desc += f"**Director:** {data['Director']}\n"
        desc += f"**Writer(s):** {data['Writer']}\n"
        desc += f"**Actors:** {data['Actors']}\n\n"
        desc += f"**Language:** {data['Language']}\n"
        desc += f"**Country:** {data['Country']}\n"
        desc += f"**Awards:** {data['Awards']}"

        e.description = desc
        if not data['Poster'] == "N/A":
            e.set_thumbnail(url=data['Poster'])

        ratings = ""

        for entry in data['Ratings']:
            ratings += f"{entry['Source']} - {entry['Value']}\n"

        if ratings:
            e.add_field(name="Ratings", value=ratings)

        await ctx.send(embed=e)

    @groupExtra(category="Test Commands")
    async def number(self, ctx):
        pass

    @number.command()
    async def year(self, ctx, year=None):
        if year is None:
            year = "random"

        data = await ctx.get(f"http://numbersapi.com/{year}/year", headers={"Content-Type": "application/json"})

        await ctx.send(data['text'])

    @number.command()
    async def trivia(self, ctx, number=None):
        if number is None:
            number = "random"

        data = await ctx.get(f"http://numbersapi.com/{number}/trivia", headers={"Content-Type": "application/json"})

        await ctx.send(data['text'])

    @number.command()
    async def math(self, ctx, number=None):
        if number is None:
            number = "random"

        data = await ctx.get(f"http://numbersapi.com/{number}/math", headers={"Content-Type": "application/json"})

        await ctx.send(data['text'])

    @number.command()
    async def date(self, ctx, *, number=None):
        if number is None:
            number = "random"

        data = await ctx.get(f"http://numbersapi.com/{number}/date", headers={"Content-Type": "application/json"})

        await ctx.send(data['text'])

    @commandExtra(category="Test Commands", name="song-info")
    async def song_info(self, ctx, *, query):
        msg = await ctx.send("Loading song information... <a:discord_loading:587812494089912340>")

        loop = asyncio.get_event_loop()

        ydl_opts = {
                'format': 'best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320'}],
            }

        ytdl = YoutubeDL(ydl_opts)
        to_run = partial(ytdl.extract_info, url=f"ytsearch:{query}", download=False)

        tdata = await loop.run_in_executor(None, to_run)

        if 'entries' in tdata:
            # take first item from a playlist
            data = tdata['entries'][0]

        uploader_name = data['uploader']
        uploader_link = data['uploader_url']
        date_year = data['upload_date'][:4]
        date_month = data['upload_date'][4:][:2]
        date_day = data['upload_date'][6:]
        creator = data['creator']
        title = data['alt_title']
        thumbnail = data['thumbnail']
        description = data['description']
        categories = ', '.join(data['categories'])
        tags = ', '.join(data['tags'])
        views = data['view_count']
        likes = data['like_count']
        dislikes = data['dislike_count']
        average_rating = data['average_rating']
        song_url = data['webpage_url']

        embed = discord.Embed(color=self.bot.embed_color)
        embed.set_thumbnail(url=thumbnail)
        embed.title = f"{creator} - {title}"
        embed.url = song_url

        if len(description) > 2048:
            description = description[:2040] + "..."

        embed.description = description + "\n⠀"
        embed.add_field(name="Other Info", value=f"**Categories:**\n{categories}\n\n**Tags:**\n{tags}\n\n👀 Views: {views:,}\n<:upvote:596577438461591562> Likes: {likes:,}\n<:downvote:596577438952062977> Dislikes: {dislikes:,}\n⭐ Avarage Rating: {average_rating}")
        embed.add_field(name="Upload Info", value=f"Uploader: [{uploader_name}]({uploader_link})\nUpload date: {date_month}/{date_day}/{date_year}\n⠀")

        await msg.delete()
        await ctx.send(embed=embed)

    @commandExtra(category="Test Commands")
    async def guildchannels(self, ctx):
        m = ""
        for CategoryChannel in ctx.guild.categories:
            m += f"**{CategoryChannel.name}**\n"
            for TextChannel in CategoryChannel.text_channels:
                perms = TextChannel.overwrites_for(ctx.guild.default_role)
                if perms.read_messages is False:
                    m += "    <:channel_locked:585783907350478848> " + TextChannel.name + "\n"
                elif TextChannel.is_nsfw():
                    m += "    <:channel_nsfw:585783907660857354> " + TextChannel.name + "\n"
                else:
                    m += "    <:channel:585783907841212418> " + TextChannel.name + "\n"
            for VoiceChannel in CategoryChannel.voice_channels:
                perms = VoiceChannel.overwrites_for(ctx.guild.default_role)
                if perms.connect is False:
                    m += "    <:voice_locked:585783907488628797> " + VoiceChannel.name + "\n"
                else:
                    m += "    <:voice:585783907673440266> " + VoiceChannel.name + "\n"
        embed = discord.Embed(color=0x36393E, description=m)
        embed.set_author(icon_url=ctx.guild.icon.url, name=f"Channels for - {ctx.guild.name}")

        await ctx.send(embed=embed)

    # @commandExtra(category="Test Commands")
    # async def ocr(self, ctx, *, url: ImageConverter=""):
    #     if not re.fullmatch(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", url):
    #         if len(ctx.message.attachments) > 0:
    #             url = ctx.message.attachments[0].url
    #         else:
    #             url = str(ctx.author.avatar.with_format("png"))

    #     async with self.bot.session.get(url) as r:
    #         image = Image.open(BytesIO(await r.read()))
    #     string = pytesseract.image_to_string(image)

    #     e = discord.Embed(description=string)
    #     e.set_image(url=url)
    #     await ctx.send(embed=e)

    @commandExtra(category="Test Commands")
    async def pikachu(self, ctx):
        async with self.bot.session.get('https://some-random-api.ml/pikachuimg') as r:
            res = await r.json()
            await ctx.send(embed=discord.Embed(color=ctx.embed_color).set_image(url=res['link']))

    @commandExtra(category="Test Commands")
    async def qh(self, ctx):
        e = discord.Embed(color=ctx.embed_color)
        ignore = ["Events", "Economy", "Jishaku", "Private", "Owner"]
        cmdcount = 0
        fields = []
        for c in self.bot.cogs.values():
            if c.qualified_name in ignore:
                continue
            # try:
            #     if self.bot.gc[str(ctx.guild.id)]["modules"][c.qualified_name.lower()]["module_toggle"] == False:
            #         continue
            # except KeyError:
            #     pass
            cmds = []
            subcount = 0
            for cmd in set(c.walk_commands()):
                # if cmd.qualified_name in self.bot.gc[str(ctx.guild.id)]["settings"]["disabled_commands"]:
                #     continue
                if hasattr(cmd, "category"):
                    if cmd.category.name.lower() in ("hidden", "no-category"):
                        continue
                    # try:
                    #     if self.bot.gc[str(ctx.guild.id)]["modules"][cmd.cog_name.lower()][cmd.category.lower().replace(' ', '-')] == False:
                    #         continue
                    # except KeyError:
                    #     pass
                if isinstance(cmd, commandsPlus) or isinstance(cmd, GroupPlus):
                    cmds.append(str(cmd.name))
                    cmdcount += 1
                    if isinstance(cmd, GroupPlus):
                        for cmdd in cmd.commands:
                            subcount += 1
            v = "` ∙ `".join(cmds)
            fields.append((f"{c.icon} **{c.qualified_name} ({len(set(c.get_commands()))}) [{subcount}]**", f"`{v}`"))
        sfields = sorted(fields, key=lambda x: len(x[1]))
        for name, value in sfields:
            e.add_field(name=name, value=value)
        e.title = f"Quick Help ({cmdcount} commands)"
        e.description = '`(X)` = Command Count\n`[X]` = Subcommand Count'

        await ctx.send(embed=e)


def setup(bot):
    pass
