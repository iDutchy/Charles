import json
import os
import typing
from functools import partial

import discord
import toml
from core.cog import SubCog
from core.commands import commandExtra
from db import langs
from discord.ext import commands
from jishaku.exception_handling import ReplResponseReactor
from jishaku.paginators import PaginatorInterface, WrappedPaginator
from jishaku.shell import ShellReader
from utils import checks
from utils.images import pokemon_bw_fix, pokemon_col_fix
from utils.utility import get_locale_strings


class Other(SubCog, category="Other"):
    def __init__(self, bot):
        self.bot = bot

    @checks.is_owner()
    @commandExtra(name="project-info", category="Other")
    async def project_info(self, ctx):
        await ctx.message.delete()
        e = discord.Embed(color=ctx.embed_color, title="Charles")
        e.set_thumbnail(url=self.bot.user.avatar.with_format("png"))
        e.description = "Charles is my main bot. He is made for everyone who does not like having 1 bot for each category. Charles is an amazing multi-purpose bot with many functions. He is also made to be very customizable.  Other than that, Charles is completely modular. Meaning that you can completely disable each module and category! Charles can provide you with some good music, moderation, fun, image manipulation and much more."
        await ctx.send(embed=e)

    @checks.is_owner()
    @commandExtra(category="Other", name='git')
    async def git(self, ctx: commands.Context, pull_push, *, commit_msg=None):
        if pull_push == "push":
            if commit_msg is None:
                commit_msg = "Updates"
            shellcmd = f'git add .&&git commit -m "{commit_msg}"&&git push'
        if pull_push == "pull":
            shellcmd = 'git pull'
        if pull_push.lower() not in ['pull', 'push']:
            return await ctx.send("Invalid option given")

        async with ReplResponseReactor(ctx.message):
            paginator = WrappedPaginator(prefix="```sh", max_size=1985)
            paginator.add_line(f"$ git {pull_push}\n")

            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
            self.bot.loop.create_task(interface.send_to(ctx))

            with ShellReader(shellcmd) as reader:
                async for line in reader:
                    if interface.closed:
                        return
                    await interface.add_line(line)

    @checks.is_owner()
    @commandExtra(category="Other")
    async def setnews(self, ctx, m_id: typing.Optional[int] = "", *, news: str = "update"):
        d = toml.load("db/config.toml")

        d['settings']["news"]["ID"] = self.bot.config['settings']["news"]["ID"] = m_id
        d['settings']["news"]["MESSAGE"] = self.bot.config['settings']["news"]["MESSAGE"] = news

        with open('db/config.toml', "w") as f:
            toml.dump(d, f)

        await ctx.send(f"Bot news has been set to: ```css\n{news}```")

    @checks.is_owner()
    @commandExtra(category="Other", aliases=['suggest-approve', 'approve-suggestion', 'approvesuggestion'])
    async def suggestapprove(self, ctx, message_id: int, *, note: str = None):
        if note is None:
            note = "No extra notes provided"

        channel = self.bot.get_channel(531628986573258784)
        message = await channel.fetch_message(message_id)
        embed = message.embeds[0]

        # Send message to the user first before we edit out the user ID
        author = await self.bot.try_user(int(embed.title))

        e = discord.Embed(color=0x34ab22)
        e.description = f"Your suggestion has been approved by {ctx.author}\n\n**Extra note:**\n{note}"
        e.add_field(name="Info", value="To see the progress of your suggestion, [join the support server](https://discord.gg/wZSH7pz)!")
        e.add_field(name="Your approved suggestion:", value=embed.fields[0].value)
        try:
            await author.send(embed=e)
        except:
            pass

        up = [r for r in message.reactions if r.emoji.name == "upvote"][0].count - 1
        down = [r for r in message.reactions if r.emoji.name == "downvote"][0].count - 1

        embed.color = 0x34ab22
        embed.title = "Suggestion Approved"
        embed.description = f"Suggestion has been approved by {ctx.author}\n\n**Extra Note:**\n{note}"
        embed.set_footer(text=f"Vote results: ⠀ 👍 {up} ⠀⠀|⠀⠀ 👎 {down}")
        await message.clear_reactions()
        await message.edit(embed=embed)
        await ctx.message.delete(silent=True)

    @checks.is_owner()
    @commandExtra(category="Other", aliases=['roast-approve', 'approve-roast', 'approveroast'])
    async def roastapprove(self, ctx, message_id: int, level: int = 1):
        channel = self.bot.get_channel(782048602511507467)
        message = await channel.fetch_message(message_id)
        embed = message.embeds[0]

        # Send message to the user first before we edit out the user ID
        author = await self.bot.try_user(int(embed.footer.text.split("|")[1].strip()))

        e = discord.Embed(color=0x34ab22)
        e.description = f"Your submitted roast has been added to my database by {ctx.author} as a level {level} roast!"
        e.add_field(name="Your submitted roast:", value=embed.description)
        try:
            await author.send(embed=e)
        except:
            pass

        with open("db/languages/en/roasts.json", "r") as f:
            d = json.load(f)

        d[str(level)].append(embed.description)
        self.bot.cogs["Fun"].roasts[str(level)].append(embed.description)

        with open("db/languages/en/roasts.json", "w") as f:
            json.dump(d, f, indent=4)

        up = [r for r in message.reactions if r.emoji.name == "upvote"][0].count - 1
        down = [r for r in message.reactions if r.emoji.name == "downvote"][0].count - 1

        embed.color = 0x34ab22
        embed.title = "Roast Approved!"
        embed.set_footer(text=f"Vote results: ⠀ 👍 {up} ⠀⠀|⠀⠀ 👎 {down}\nAdded as level {level} roast")
        await message.clear_reactions()
        await message.edit(embed=embed)
        await ctx.message.delete(silent=True)

    @checks.is_owner()
    @commandExtra(category="Other", aliases=['roast-deny', 'deny-roast', 'denyroast'])
    async def roastdeny(self, ctx, message_id: int):
        channel = self.bot.get_channel(782048602511507467)
        message = await channel.fetch_message(message_id)
        embed = message.embeds[0]

        # Send message to the user first before we edit out the user ID
        author = await self.bot.try_user(int(embed.footer.text.split("|")[1].strip()))

        e = discord.Embed(color=0xc22727)
        e.description = f"Your submitted roast has **not** been added to my database by {ctx.author}... Sorry, maybe another roast will be added some other time! You can still access your roast by using `--level 0` in the roast command!"
        e.add_field(name="Your submitted roast:", value=embed.description)
        try:
            await author.send(embed=e)
        except:
            pass

        up = [r for r in message.reactions if r.emoji.name == "upvote"][0].count - 1
        down = [r for r in message.reactions if r.emoji.name == "downvote"][0].count - 1

        embed.color = 0xc22727
        embed.title = "Roast Denied!"
        embed.set_footer(text=f"Vote results: ⠀ 👍 {up} ⠀⠀|⠀⠀ 👎 {down}")
        await message.clear_reactions()
        await message.edit(embed=embed)
        await ctx.message.delete()

    @checks.is_owner()
    @commandExtra(category="Other", aliases=['suggest-deny', 'deny-suggestion', 'denysuggestion'])
    async def suggestdeny(self, ctx, message_id: int, *, reason: str = None):
        if reason is None:
            reason = "No reason given"

        channel = self.bot.get_channel(531628986573258784)
        message = await channel.fetch_message(message_id)
        embed = message.embeds[0]

        # Send message to the user first before we edit out the user ID
        author = self.bot.get_user(int(embed.title))

        e = discord.Embed(color=0xc22727)
        e.description = f"Your suggestion has been denied by {ctx.author}\n\n**Reason:**\n{reason}"
        e.add_field(name="Info", value="For more info, [join the support server](https://discord.gg/wZSH7pz)!")
        e.add_field(name="Your denied suggestion:", value=embed.fields[0].value)
        try:
            await author.send(embed=e)
        except:
            pass

        up = [r for r in message.reactions if r.emoji.name == "upvote"][0].count - 1
        down = [r for r in message.reactions if r.emoji.name == "downvote"][0].count - 1

        # Edit embed after sending a message to the user
        embed.color = 0xc22727
        embed.title = "Suggestion Denied"
        embed.description = f"Suggestion has been denied by {ctx.author}\n\n**Reason:**\n{reason}"
        embed.set_footer(text=f"Vote results: ⠀ 👍 {up} ⠀⠀|⠀⠀ 👎 {down}")

        await message.clear_reactions()
        await message.edit(embed=embed)
        await ctx.message.delete()

    @checks.is_owner()
    @commandExtra(category="Other", aliases=['fix-wtp'])
    async def fixwtp(self, ctx, wtpID: int, w: int, h: int):
        thing = partial(pokemon_bw_fix, wtpID, w, h)
        buf_bw, saveimg_bw = await self.bot.loop.run_in_executor(None, thing)
        check, msg = await ctx.confirm("Is the image better now?", file=discord.File(buf_bw, filename="wtpfix.png"))
        if not check:
            return await ctx.send("Ok, I will not save this one.")

        thing = partial(pokemon_col_fix, wtpID, w, h)
        buf_col, saveimg_col = await self.bot.loop.run_in_executor(None, thing)

        saveimg_bw.save(f'db/images/pokemon/bw/{wtpID}.png')
        saveimg_col.save(f'db/images/pokemon/col/{wtpID}.png')
        saveimg_col.close()
        saveimg_bw.close()

        await ctx.send("New WTP image has succesfully been saved!")

    @checks.is_owner()
    @commandExtra(name='reset-help')
    async def reset_help(self, ctx, to_remove: str.lower, *, command: str.lower):
        cmd = self.bot.get_command(command)
        if not cmd:
            return await ctx.send(f"No command found named `{command}`!")
        if to_remove not in ('usage', 'brief', 'desc'):
            return await ctx.send("Invalid item provided, can only accept `usage`, `brief` or `desc`!")

        LANGUAGES = langs.LANGUAGES
        n = cmd.qualified_name
        removed = []
        for lang in os.listdir('db/languages'):
            if lang == 'en':
                continue
            with open(f'db/languages/{lang}/help.json', 'r') as f:
                data = json.load(f)

            if data.pop(f"{n} - {to_remove}", None):
                removed.append(list(LANGUAGES.keys())[list(LANGUAGES.values()).index(lang)])

                with open(f'db/languages/{lang}/help.json', 'w', encoding="utf8") as f:
                    json.dump(data, f, indent=4)

        if not removed:
            return await ctx.send("There was nothing to remove...")

        await ctx.send(f"Removed the {to_remove} of `{n}` from: **{'**, **'.join(removed)}**")

    @checks.is_owner()
    @commandExtra(category="Other", aliases=['ul'], name="update-locale")
    async def update_locale(self, ctx):
        async with ctx.loading("Updating locale"):
            strings = set(get_locale_strings())
            added = set()
            addedcmds = set()
            removed = set()

            for lang in os.listdir('db/languages'):
                with open(f'db/languages/{lang}/bot.json', 'r') as f:
                    data = json.load(f)

                for k in list(data.keys()):
                    if k not in strings:
                        data.pop(k)
                        removed.add(k)

                with open(f'db/languages/{lang}/bot.json', 'w', encoding="utf8") as f:
                    json.dump(data, f, indent=4)

            with open('db/languages/en/bot.json', 'r') as f:
                en_data = json.load(f)

            for string in strings:
                if string in list(en_data.keys()):
                    continue
                en_data[string] = ""
                added.add(string)
                self.bot.cache.update('i18n', 'en', string, '')

            with open('db/languages/en/bot.json', 'w', encoding="utf8") as f:
                json.dump(en_data, f, indent=4)

            if (f := len(en_data.keys())) != len(strings):
                await ctx.send(f"Something went wrong when updating!\n\nFound strings: {f}\nIn file: {len(strings)}", edit=False)

            with open('db/languages/en/help.json', 'r') as f:
                helpdata = json.load(f)

            for cmd in set(self.bot.walk_commands()):
                if f"{cmd.qualified_name} - desc" not in helpdata.keys():
                    helpdata[f"{cmd.qualified_name} - usage"] = None
                    helpdata[f"{cmd.qualified_name} - brief"] = None
                    helpdata[f"{cmd.qualified_name} - desc"] = None
                    addedcmds.add(cmd)
                    self.bot.cache.update("cmd_help", "en", f"{cmd.qualified_name} - usage", None)
                    self.bot.cache.update("cmd_help", "en", f"{cmd.qualified_name} - brief", None)
                    self.bot.cache.update("cmd_help", "en", f"{cmd.qualified_name} - desc", None)

            with open('db/languages/en/help.json', 'w') as f:
                json.dump(helpdata, f, indent=4)

            await ctx.send(f'Translate content has been updated in all locale files!\n\n{ctx.emoji.add} `{len(addedcmds)} commands`\n{ctx.emoji.add} `{len(added)} strings`\n{ctx.emoji.remove} `{len(removed)} strings`', edit=False)
            await self.bot.cache.refresh_locale()

    @checks.is_owner()
    @commandExtra(category="Other", name="add-translator")
    async def add_translator(self, ctx, user: discord.User):
        try:
            await ctx.message.delete()
        except:
            pass
        if user.id in self.bot.translators:
            return await ctx.send(f"{user} is already a translator!")
        devision = self.bot.get_guild(514232441498763279)
        if user not in devision.members:
            try:
                await user.send("Hey there, Dutchy told me you want to be a translator. That's awesome! But you should join my server so I can add the translator role to you. There you will also be updated about new content being added to translate!\n\nClick this to join: https://charles-bot.xyz/support")
                return await ctx.send(f"{user} is not in the server, but I sent them a link to join!")
            except:
                return await ctx.send(f"{user} is not in the server and I was unable to send them an invite link...")

        translator = devision.get_role(592319743692898326)
        user = devision.get_member(user.id)
        await user.add_roles(translator)

        await self.bot.db.execute("INSERT INTO translators(user_id) VALUES($1)", user.id)
        self.bot.translators.append(user.id)

        translator_chat = devision.get_channel(592320120416632833)
        await translator_chat.send(f"Welcome to the translator squad {user.mention}! Thank you for joining us. To get started, all you need to do is `c?translate-start`. First you will see a setup to get you started. After that you can start translating! :D")

    @checks.is_owner()
    @commandExtra(category="Other", name='add-translator-language')
    async def add_translator_language(self, ctx, user: discord.User, language):
        if user.id not in self.bot.translators:
            return await ctx.send(f"`{user}` is not a translator...")

        LANGUAGES = langs.LANGUAGES

        if language.title() not in LANGUAGES:
            return await ctx.send(f"Language `{language}` not found in listed languages!")

        cred = await self.bot.db.fetchval("SELECT credits FROM translators WHERE user_id = $1", user.id)

        await self.bot.db.execute("INSERT INTO translators(user_id, language, first_time, credits) VALUES($1, $2, $3, $4)", user.id, LANGUAGES[language.title()], False, cred)
        if not os.path.exists(f'db/languages/{LANGUAGES[language]}'):
            os.mkdir(f'db/languages/{LANGUAGES[language]}')
            botfile = open(f'db/languages/{LANGUAGES[language]}/bot.json', 'w+')
            helpfile = open(f'db/languages/{LANGUAGES[language]}/help.json', 'w+')
            botfile.write("{}")
            helpfile.write("{}")
            botfile.close()
            helpfile.close()
        if not LANGUAGES[language] in self.bot.cache.i18n:
            self.bot.cache.i18n[LANGUAGES[language]] = {}
        if not LANGUAGES[language] in self.bot.cache.cmd_help:
            self.bot.cache.cmd_help[LANGUAGES[language]] = {}
        await ctx.send(f"Added language **{language}** to `{user}`!")

    @checks.is_owner()
    @commandExtra(category="Other", name="remove-translator")
    async def remove_translator(self, ctx, user: discord.User):
        try:
            await ctx.message.delete()
        except:
            pass
        if user.id not in self.bot.translators:
            return await ctx.send(f"{user} is not a translator!")
        devision = self.bot.get_guild(514232441498763279)
        if user in devision.members:
            user = devision.get_member(user.id)
            translator = devision.get_role(592319743692898326)
            await user.remove_roles(translator)

        try:
            await user.send("Thank you for the time you've spent on translating me. I hope you enjoyed doing it! I sure am happy with your help. Thank you! And if you want to be a translator again some day, you know where to find me ;)")
        except:
            pass

        await self.bot.db.execute("DELETE FROM translators WHERE user_id = $1", user.id)
        self.bot.translators.remove(user.id)

        await ctx.send(f"{user} has been removed from the translator team.")


def setup(bot):
    pass
