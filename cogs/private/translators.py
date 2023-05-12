import asyncio
import difflib
import time
import json
import os
import random
import re
from datetime import datetime as dt

import discord
import mtranslate
from core import i18n
from core.commands import commandExtra
from db import langs
from discord.ext import commands
from utils import humanize_time as ht
from utils import checks
from core.cog import SubCog

LANGUAGES = langs.LANGUAGES

class Translators(SubCog, category="Translators"):
    def __init__(self, bot):
        self.bot = bot

    def cog_check(self, ctx):
        return ctx.author.id in self.bot.translators

    async def first_time_info(self, ctx):
        try:
            channel = await ctx.author.create_dm()
            checkmsg = await ctx.author.send("\u200b")
        except:
            c = self.bot.get_channel(592320120416632833)
            return await c.send(f"{ctx.author.mention}, you attempted to start a translate session, but I was unable to DM you. Please enable DMs and try again!")
        else:
            await ctx.send(f"{ctx.author.mention}, check your DMs!")
        
        e = discord.Embed(
            title="Charles Translations - Setup",
            color=0x6EA5F3,
            timestamp=dt.utcnow())
        e.set_author(name=ctx.author,icon_url=ctx.author.avatar.with_static_format("png"))
        e.set_thumbnail(url="https://media.discordapp.net/attachments/460568954968997890/734219167690915870/oie_3BKRpN0mtlcr.png")

        base = e.copy()
        e.title="Welcome to Charles Translations!"

        e.description = "Weclome, and thank you for translating me! Since this is your first time, I will ask you some questions to make sure everything will be set up properly! If you make a mistake somewhere, just continue and contact Dutchy. He will manually fix this.\n\nLets begin with the most important question."
        e.add_field(name="**Which language will you be translating to?**", value="Please specify the full English name for it! E.g. English, German, Dutch, etc.\n\nIf you want to translate to multiple languages, only separate them by a space!")
        await checkmsg.edit(content=None, embed=e)

        def mcheck(m):
            return m.channel == channel and m.author == ctx.author

        try:
            lang = await self.bot.wait_for("message", check=mcheck, timeout=45)
        except asyncio.TimeoutError:
            return await ctx.author.send("You took too long to answer, so I had to cancel your setup. Please run the command again to restart the setup.")

        langs = lang.content.title().split(" ")
        fuzzy = []
        no_fuzzy = []
        for l in langs:
            if not l in list(LANGUAGES.keys()):
                fuzzy_matches = difflib.get_close_matches(l, list(LANGUAGES.keys()))
                if fuzzy_matches:
                    fuzzy.append((l, fuzzy_matches[:5]))
                else:
                    no_fuzzy.append(l)

        if fuzzy or no_fuzzy:
            possible_matches = ""
            if fuzzy:
                for f in fuzzy:
                    possible_matches += f"`{f[0]}`: {', '.join(f[1])}\n"
            t = f"Uh-oh, looks like something went wrong while looking up that language! I could not find the language you provided.\n\n**Provided:** {' & '.join(langs)}\n**No Matches:** {', '.join(no_fuzzy) if no_fuzzy else 'N/A'}\n**Possible Matches:**\n{possible_matches if possible_matches else 'N/A'}\n\nPlease run the `c?start-translate` command again and provide a valid language. If you think there is a misunderstanding, please contact Dutchy about this!"
            return await ctx.author.send(t)


        e = base
        e.description = f"Ok, you will be translating to {' & '.join(langs)}! And as you might be aware of, I would like to credit the people who work for me. I do however want to give you a choice if you want to be credited or not. Please make your choice by reacting below."
        cmsg = await ctx.author.send(embed=e)
        await cmsg.add_reaction(ctx.emoji.check)
        await cmsg.add_reaction(ctx.emoji.xmark)

        def rcheck(r, u):
            return r.message.channel == channel and str(r) in (str(ctx.emoji.xmark), str(ctx.emoji.check)) and u.id == ctx.author.id

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=rcheck, timeout=45)
        except asyncio.TimeoutError:
            return await ctx.author.send("You took too long to answer, so I had to cancel your setup. Please run the command again to restart the setup.")

        e = base
        if str(reaction) == str(ctx.emoji.check):
            choice = True
            e.description = "Awesome! When you use the `c?credits` command you should see your name on there after this setup.\n\nNow there are just a few more things to go over before you can start with translating."
        elif str(reaction) == str(ctx.emoji.xmark):
            choice = False
            e.description = "That's alright, I don't want to force you things you don't like! Your name will not appear on the `c?credits` screen. But thank you still for translating me!\n*If you misclicked, DM Dutchy after the setup so he can change it*\n\nNow there are just a few more things to go over before you can start with translating."

        e.add_field(name="**Translating Do's & Don'ts:**",
            value="__**DO:**__\n- Try to translate everything. Can't find a proper translation? Leave it English or pick the closest match in your language!\n- If you see a string that contains a typo, skip it and warn Dutchy\n- Keep the format as the original. Don't put any newlines where there isn't one in the original format either.\n- Keep the markdown! **Bold text**, `code blocks`, *italic*, etc should not be forgotten!\n\n__**DON'T:**__\n- Translate command names. Multi-language command names are not supported (yet).\n- Forget a `{0}` or `{1}`. These are crucial to the format as they are \"placeholders\" for other things. Such as a prefix, member name, etc.\n- Be afraid to *ask*! Is there something you dont understand? Or you want the context of a sentence? Don't be afraid to go to <#592320120416632833> and ask for help.")
        e.add_field(name="Reaction Usage:", value=f"{ctx.emoji.rewind} - Undo your last translation\n{ctx.emoji.stop} - End your translate session\n{ctx.emoji.skip} - Skip the current string for another time\n\U0001f916 - Uses the automated translation shown (Please do not abuse this from laziness!)\n{ctx.emoji.qmark} - Shows this message\n{ctx.emoji.warn} - Report the string if it has any typos in it!")
        e.add_field(name="\u200b", value="Please verify that you have read the tips.", inline=False)
        e.set_footer(text="You can always look back at these Do's & Don'ts by looking at the pins or running the command | c?translate-tips")
        dmsg = await ctx.author.send(embed=e)
        await dmsg.pin()
        await dmsg.add_reaction(ctx.emoji.check)

        def dcheck(r, u):
            return r.message.channel == channel and str(r) == str(ctx.emoji.check) and u.id == ctx.author.id

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=dcheck, timeout=90)
        except asyncio.TimeoutError:
            return await ctx.author.send("You took too long to answer, so I had to cancel your setup. Please run the command again to restart the setup.")

        e = base
        e.title="Setup Completed!"
        e.description=f"The setup is now finished! Here are your results:\n\n**Translating To:** {' & '.join(langs)}\n**Should Credit?:** {'yes' if choice else 'no'}\n\nThe setup is closed and everything has been saved. Please run `c?translate-start` again to begin translating!"
        e.clear_fields()
        await ctx.author.send(embed=e)
        await self.bot.db.execute("DELETE FROM translators WHERE user_id = $1", ctx.author.id)
        for l in langs:
            await self.bot.db.execute("INSERT INTO translators(user_id, language, first_time, credits) VALUES($1, $2, $3, $4)", ctx.author.id, LANGUAGES[l], False, choice)
            if not os.path.exists(f'db/languages/{LANGUAGES[l]}'):
                os.mkdir(f'db/languages/{LANGUAGES[l]}')
                botfile = open(f'db/languages/{LANGUAGES[l]}/bot.json', 'w+')
                helpfile = open(f'db/languages/{LANGUAGES[l]}/help.json', 'w+')
                botfile.write("{}")
                helpfile.write("{}")
                botfile.close()
                helpfile.close()
            if not LANGUAGES[l] in self.bot.cache.i18n:
                self.bot.cache.i18n[LANGUAGES[l]] = {}
            if not LANGUAGES[l] in self.bot.cache.cmd_help:
                self.bot.cache.cmd_help[LANGUAGES[l]] = {}

    @commandExtra(category="Translators", name="translate-start", aliases=["start-tr", "tr-start"])
    async def start_translate(self, ctx):
        info = await self.bot.db.fetch("SELECT * FROM translators WHERE user_id = $1", ctx.author.id)
        if info[0]['first_time']:
            return await self.first_time_info(ctx)

        if ctx.author.id in self.bot.cache.get("translate_sessions"):
            return await ctx.send("You already have a translate session active!")

        self.bot.cache.update("translate_sessions", ctx.author.id, None)

        try:
            channel = await ctx.author.create_dm()
            checkmsg = await ctx.author.send("\u200b")
        except:
            c = self.bot.get_channel(592320120416632833)
            self.bot.cache.delete("translate_sessions", ctx.author.id)
            return await c.send(f"{ctx.author.mention}, you attempted to start a translate session, but I was unable to DM you. Please enable DMs and try again!")
        else:
            await ctx.send(f"{ctx.author.mention}, a translate session has started in your DMs!")

        langs = [x['language'] for x in info]
        lang_names = [list(LANGUAGES.keys())[list(LANGUAGES.values()).index(l)] for l in langs]


        e = discord.Embed(color=0x6EA5F3,
            title="Charles Translations",
            timestamp=dt.utcnow())
        e.set_author(name=ctx.author,icon_url=ctx.author.avatar.with_static_format("png"))
        e.set_thumbnail(url="https://media.discordapp.net/attachments/460568954968997890/734219167690915870/oie_3BKRpN0mtlcr.png")
        if len(info) > 1:
            e.description = "Welcome back to translating! You translate to multiple languages, so please pick which one you'd like to translate to today:\n- " + "\n- ".join(lang_names)
            await checkmsg.edit(embed=e)

            def check(m):
                return m.content.title() in lang_names and m.author == ctx.author and m.channel.id == channel.id

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30)
                current_lang = msg.content.title()
            except asyncio.TimeoutError:
                self.bot.cache.delete("translate_sessions", ctx.author.id)
                return await ctx.author.send("Sorry, you took to long to respond. Session will now end")
        else:
            current_lang = lang_names[0]

            if current_lang in self.bot.cache.get("translate_contents"):
                self.bot.cache.delete("translate_sessions", ctx.author.id)
                return await ctx.author.send("I'm sorry, someone else currently has a translate session running with that language. I can't open 2 sessions for the same language, so I'm afraid you'll have to wait...")

        e.description = f"Welcome back to translating! So you will be translating to `{current_lang}`. What would you like to work on today?\n\n- Command Text\n- Command Help"
        await checkmsg.edit(content=None, embed=e)

        self.bot.cache.update("translate_sessions", ctx.author.id, current_lang)
        self.bot.cache.update("translate_contents", current_lang, {})

        try:
            setting = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel.id == channel.id and m.content.lower() in ['command help', 'command text'], timeout=30)
        except asyncio.TimeoutError:
            self.bot.cache.delete("translate_sessions", ctx.author.id)
            self.bot.cache.delete("translate_contents", current_lang)
            return await ctx.author.send("Sorry, you took to long to respond. Session will now end")

        cmd_help = False
        if setting.content.lower() == 'command help':
            cmd_help = True
            e.description = "Ok! A session for translating the command help will begin. Good luck!"
            await ctx.author.send(embed=e)
        else:
            e.description = "Ok! A session for translating command text will begin. Good luck!"
            await ctx.author.send(embed=e)

        await asyncio.sleep(3)

        with open(f'db/languages/en/{"help" if cmd_help else "bot"}.json') as f:
            data = json.load(f)

        if cmd_help:
            original_strings = list(set(list(data.values())))
            if None in original_strings:
                original_strings.remove(None)
        else:
            original_strings = list(data.keys())
            if None in original_strings:
                original_strings.remove(None)

        with open(f'db/languages/{LANGUAGES[current_lang]}/bot.json') as f:
            otherdata = json.load(f)

        translated_strings = list(otherdata.keys())

        for string in translated_strings:
            if string in original_strings:
                original_strings.remove(string)


        popped = ""
        translating = True
        while translating:
            if popped:
                chosen_string = popped
                popped = ""
            else:
                chosen_string = random.choice(original_strings)
                original_strings.remove(chosen_string)

            try:
                example = mtranslate.translate(chosen_string, LANGUAGES[current_lang], 'en')
            except:
                example = None

            REACTIONS = (str(ctx.emoji.rewind), str(ctx.emoji.skip), str(ctx.emoji.stop), "\U0001f916", str(ctx.emoji.qmark), str(ctx.emoji.warn))

            e = discord.Embed(color=0x6EA5F3,
                title=f"Charles Translations - Translating {current_lang}",
                timestamp=dt.utcnow(),
                description=discord.utils.escape_markdown(chosen_string))
            if not current_lang.lower().endswith("vulgar"):
                if example:
                    if len(example) <= 1024:
                        e.add_field(name="Automatic Translation", value=discord.utils.escape_markdown(example))
                    else:
                        e.add_field(name="Automatic Translation", value="Too long for the embed, please write your manual translation.")
            e.set_author(name=ctx.author,icon_url=ctx.author.avatar.with_static_format("png"))
            if example:
                e.set_footer(text="Use the robot emoji if the automatic translation is correct. If it's not, please write your manual translation!")
            e.set_thumbnail(url="https://media.discordapp.net/attachments/460568954968997890/734219167690915870/oie_3BKRpN0mtlcr.png")
            amsg = await ctx.author.send(embed=e)

            for r in REACTIONS:
                await amsg.add_reaction(r)

            def mcheck(m):
                return m.author == ctx.author and m.channel.id == channel.id

            def rcheck(r, u):
                return str(r) in REACTIONS and r.message.channel.id == channel.id and u == ctx.author

            # try:
            #     msg = await self.bot.wait_for('message', check=check, timeout=300)
            # except asyncio.TimeoutError:
            #     translating = False
            #     await self.end_translation(ctx.author, cmd_help)
            #     return

            try:
                done, pending = await asyncio.wait([
                    self.bot.wait_for('reaction_add', check=rcheck),
                    self.bot.wait_for('message', check=mcheck)],
                    timeout=300,
                    return_when=asyncio.FIRST_COMPLETED)

                for task in pending:
                    task.cancel()

                if not done:
                    raise asyncio.TimeoutError()

                for r in REACTIONS:
                    await amsg.remove_reaction(r, self.bot.user)

                m = done.pop().result()
                try:
                    r, u = m[0], m[1]
                    if str(r) == str(ctx.emoji.rewind):
                        strings = self.bot.cache.get("translate_contents", current_lang)
                        if not strings:
                            await ctx.author.send("There is nothing left to undo.")
                            popped = chosen_string
                        else:
                            popped = strings.popitem()[0]
                            await amsg.add_reaction(ctx.emoji.skip)

                    elif str(r) == str(ctx.emoji.skip):
                        await amsg.add_reaction(ctx.emoji.skip)
                        pass

                    elif str(r) == str(ctx.emoji.stop):
                        translating = False
                        await amsg.add_reaction(ctx.emoji.stop)
                        await self.end_translation(ctx.author, cmd_help)
                        return

                    elif str(r) == "\U0001f916": # ROBOT EMOJI
                        if example:
                            if not current_lang.lower().endswith("vulgar"):
                                self.bot.cache.update("translate_contents", current_lang, chosen_string, example)
                                await amsg.add_reaction(ctx.emoji.check)
                                await amsg.add_reaction("\U0001f916")
                            else:
                                await ctx.author.send("You may not use automated translations on vulgar languages, that's why there was also no automated translation shows you blind fuck. Please just write a manual translation you lazy fucker.")
                                popped = chosen_string
                        else:
                            await ctx.author.send("Automatic translations are not available for this language, sorry.")
                            popped = chosen_string

                    elif str(r) == str(ctx.emoji.qmark):
                        e = discord.Embed(color=0x6EA5F3,
                            title=f"Charles Translations - Translating Tips",
                            timestamp=dt.utcnow(),
                            description="__**DO:**__\n- Try to translate everything. Can't find a proper translation? Leave it English or pick the closest match in your language!\n- If you see a string that contains a typo, use the warning reaction on the message\n- Keep the format as the original. Don't put any newlines where there isn't one in the original format either.\n- Keep the markdown! **Bold text**, `code blocks`, *italic*, etc should not be forgotten!\n\n__**DON'T:**__\n- Translate command names. Multi-language command names are not supported (yet).\n- Forget a `{0}` or `{1}`. These are crucial to the format as they are \"placeholders\" for other things. Such as a prefix, member name, etc.\n- Be afraid to *ask*! Is there something you dont understand? Or you want the context of a sentence? Don't be afraid to go to <#592320120416632833> and ask for help.")
                        e.add_field(name="Reaction Usage:", value=f"{ctx.emoji.rewind} - Undo your last translation\n{ctx.emoji.stop} - End your translate session\n{ctx.emoji.skip} - Skip the current string for another time\n\U0001f916 - Uses the automated translation shown (Please do not abuse this from laziness!)\n{ctx.emoji.qmark} - Shows this message\n{ctx.emoji.warn} - Report the string if it has any typos in it!")
                        await ctx.author.send(embed=e)
                        await amsg.add_reaction(ctx.emoji.qmark)
                        popped = chosen_string

                    elif str(r) == str(ctx.emoji.warn):
                        await amsg.add_reaction(ctx.emoji.warn)
                        e = discord.Embed(title="**INVALID STRING**",
                            description=chosen_string)
                        e.set_author(name=str(u),icon_url=u.avatar.url)
                        e.add_field(name="**WARNING**",
                            value="If you see this string when you're translating, please *skip* the translation. Dutchy is now aware of the incorrect string and will fix this asap!")
                        c = self.bot.get_channel(592320120416632833)
                        await c.send(f"{ctx.emoji.warn} | {self.bot.owner.mention} <@&592319743692898326> | {ctx.emoji.warn}", embed=e)#, allowed_mentions=discord.AllowedMentions(roles=False)
                        pass

                except:
                    chosen_re = sorted(re.findall(r"\{[0-9]{1}(?:\.[a-zA-Z]+)?\}", chosen_string))
                    translated_re = sorted(re.findall(r"\{[0-9]{1}(?:\.[a-zA-Z]+)?\}", chosen_string))
                    if chosen_re != translated_re:
                        for x in translated_re:
                            if x in chosen_re:
                                chosen_re.remove(x)
                        await ctx.author.send(f"{ctx.author.mention}, wait a second! You missed a crucial part of the translation. In your translation you ***must*** use the `{'`, `'.join(chosen_re)}`! You forgot those, so please try again.")
                        await asyncio.sleep(1)
                        popped = chosen_string

                    else:
                        self.bot.cache.update("translate_contents", current_lang, chosen_string, m.content)
                        await m.add_reaction(ctx.emoji.check)


            except asyncio.TimeoutError:
                translating = False
                await self.end_translation(ctx.author, cmd_help)
                try:
                    for r in REACTIONS:
                        await amsg.remove_reaction(r, self.bot.user)
                except:
                    pass
                finally:
                    break

    async def end_translation(self, user, cmd_help):
        lang = self.bot.cache.delete("translate_sessions", user.id)
        langcode = LANGUAGES[lang]
        translated = self.bot.cache.delete("translate_contents", lang)
        if cmd_help:
            allstrings = self.bot.cache.get("cmd_help", "en")
            total_strings = len(allstrings.keys())
            translated_strings = len(self.bot.cache.cmd_help.get(langcode, {}).keys())
            for string in allstrings.keys():
                for trans in translated.keys():
                    if allstrings[string] == trans:
                        if not langcode in self.bot.cache.cmd_help:
                            self.bot.cache.cmd_help[langcode] = {}
                        self.bot.cache.cmd_help[langcode].update({string: translated[trans]})
                    else:
                        continue
            with open(f'db/languages/{langcode}/help.json', 'w') as f:
                json.dump(self.bot.cache.cmd_help[langcode], f, indent=4)
        else:
            total_strings = len(self.bot.cache.get("i18n", "en").keys())
            translated_strings = len(self.bot.cache.i18n.get(langcode, {}).keys())
            if not langcode in self.bot.cache.i18n:
                self.bot.cache.i18n[langcode] = {}
            self.bot.cache.i18n[langcode].update(translated)
            with open(f'db/languages/{langcode}/bot.json', 'w') as f:
                json.dump(self.bot.cache.i18n[langcode], f, indent=4)

        translated_percent = 100 / total_strings * (translated_strings+len(translated.keys()))
        translated_session_percent = 100 / total_strings * len(translated.keys())
        total = len(self.bot.cache.get("cmd_help", "en").keys()) + len(self.bot.cache.get("i18n", "en").keys())
        total_translated = len(self.bot.cache.i18n.get(langcode, {}).keys()) + len(self.bot.cache.cmd_help.get(langcode, {}).keys())
        tp = 100 / total * total_translated

        e = discord.Embed(color=0x6EA5F3,
            title=f"Charles Translations - Translation Ended",
            timestamp=dt.utcnow())
        e.set_author(name=user,icon_url=user.avatar.with_static_format("png"))
        e.set_thumbnail(url="https://media.discordapp.net/attachments/460568954968997890/734219167690915870/oie_3BKRpN0mtlcr.png")
        e.description=f"Your session for translating to **{lang}** has ended. Thank you for the new translations!\n\nYour stats:\nYou translated `{translated_percent:.2f}%` of {'command help' if cmd_help else 'command text'} to {lang} now, that's an increase of `{translated_session_percent:.2f}%` with this session, bringing the total translated content for all {lang} content to `{tp:.2f}%`. Great work!"
        await user.send(embed=e)

        await self.bot.db.execute("UPDATE translators SET user_progress = user_progress + $1 WHERE user_id = $2 AND language = $3", len(translated.keys()), user.id, langcode)
        await self.bot.db.execute("UPDATE translators SET last_session = $1, last_progress = $2, last_session_type = $4 WHERE user_id = $3", int(time.time()), len(translated.keys()), user.id, "Command Help" if cmd_help else "Command Text")
        await self.bot.db.execute("UPDATE translators SET total_progress = total_progress + $1 WHERE language = $2", len(translated.keys()), langcode)

    @commandExtra(category="Translators", name='translate-stats')
    async def translate_stats(self, ctx, user: discord.User=None):
        user = user or ctx.author
        if user.id not in self.bot.translators:
            return await ctx.send(f"`{user}` is not a translator!")

        e = discord.Embed(color=ctx.embed_color, title="Translator Stats")
        e.set_author(name=user,icon_url=user.avatar.with_static_format("png"))
        e.set_thumbnail(url="https://media.discordapp.net/attachments/460568954968997890/734219167690915870/oie_3BKRpN0mtlcr.png")
        stats = await self.bot.db.fetch("SELECT user_progress, total_progress, last_progress, last_session, last_session_type, language FROM translators WHERE user_id = $1", user.id)
        lang_names = [list(LANGUAGES.keys())[list(LANGUAGES.values()).index(l['language'])] for l in stats]
        if (sestype := stats[0]['last_session_type']):
            if sestype == "Command Help":
                total = len(self.bot.cache.get("cmd_help", "en").keys()) 
            else:
                total = len(self.bot.cache.get("i18n", "en").keys())
            prog = 100 / total * stats[0]['last_progress']
            prog = f"{prog:.2f}%"
        else:
            prog = "N/A"

        sestype = stats[0]['last_session_type'] or "N/A"
        stamp = dt.fromtimestamp(stats[0]['last_session']) 
        description = f"{ctx.emoji.arrow} **Translating:** {', '.join(lang_names)}\n" \
                      f"{ctx.emoji.arrow} **Last Session:** {ht.date_time(stamp)} `({ht.timesince(stamp)})`\n"\
                      f"{ctx.emoji.arrow} **Last Session Translated:** {stats[0]['last_progress']} strings\n"\
                      f"{ctx.emoji.arrow} **Last Session Progress:** {prog}\n"\
                      f"{ctx.emoji.arrow} **Last Session Type:** {sestype}\n"
        if len(stats) > 1:
            for stat in stats:
                total = len(self.bot.cache.get("cmd_help", "en").keys()) + len(self.bot.cache.get("i18n", "en").keys())
                up = 100 / total * stat['user_progress']
                tp = 100 / total * stat['total_progress']
                desc = f"**User Progress:** {up:.2f}%\n"\
                       f"**Total Progress:** {tp:.2f}%\n"
                e.add_field(name=list(LANGUAGES.keys())[list(LANGUAGES.values()).index(stat['language'])], value=desc)
        else:
            total = len(self.bot.cache.get("cmd_help", "en").keys()) + len(self.bot.cache.get("i18n", "en").keys())
            up = 100 / total * stats[0]['user_progress']
            tp = 100 / total * stats[0]['total_progress']
            description += f"{ctx.emoji.arrow} **User Progress:** {up:.2f}%\n"\
                           f"{ctx.emoji.arrow} **Total Progress:** {tp:.2f}%\n"
        e.description=description
        await ctx.send(embed=e)

def setup(bot):
    pass
