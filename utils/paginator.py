import asyncio
import copy
import math
from collections import Counter
from datetime import datetime

import discord
from core.cache import CacheManager as cm
from discord.ext import commands


class PaginatorError(commands.CommandError):
    pass

class EmbedPages:
    def __init__(self, ctx, *args, **kwargs):
        self.ctx = ctx
        self.bot = ctx.bot
        self.message = ctx.message

        self.title = kwargs.get("title")
        self.entries = kwargs.get("entries")
        self.author = kwargs.get("author", ctx.author)
        self.thumbnail = kwargs.get("thumbnail")
        self.footericon = kwargs.get("footericon", discord.Embed.Empty)
        self.footertext = kwargs.get("footertext", discord.Embed.Empty)
        self.url = kwargs.get("url")
        self.image = kwargs.get("image")
        self.show_page_num = kwargs.get("show_page_num", False)
        self.color = kwargs.get("color", ctx.embed_color)
        self.timestamp = kwargs.get("timestamp", True)
        self.show_entry_count = kwargs.get("show_entry_count", False)
        self.per_page = kwargs.get("per_page", 1)
        self.show_entry_nums = kwargs.get("show_entry_nums", False)
        self.prefix = kwargs.get("prefix", "")
        self.suffix = kwargs.get("suffix", "")

        self.timeout = kwargs.get("timeout", 60.0)
        self.page = 1
        self.pages = math.ceil(len(self.entries)/self.per_page)
        self.paginating = False
        self.reactions = {
            str(ctx.emoji.first): self.go_to_first,
            str(ctx.emoji.previous): self.go_to_previous,
            str(ctx.emoji.cancel): self.stop_paginating,
            str(ctx.emoji.next): self.go_to_next,
            str(ctx.emoji.last): self.go_to_last
        }

    def embed(self):
        e = discord.Embed(color=self.color)
        if self.thumbnail:
            e.set_thumbnail(url=self.thumbnail)
        if self.image:
            e.set_image(url=self.image)
        e.set_footer(icon_url=self.footericon, text=self.footertext)

        if self.timestamp:
            e.timestamp = datetime.utcnow()

        if isinstance(self.url, list):
            if (ti:= len(self.url)) != (en:= self.pages):
                raise PaginatorError(f"Got a list of urls but it does not match the amount of entries: {ti}t/{en}e")
            e.url = self.url[self.page-1]
        else:
            e.url = self.url

        if isinstance(self.entries, list):
            num = (self.page - 1) * self.per_page
            if self.show_entry_nums:
                x = []
                for i, n in enumerate(self.entries, start=1):
                    x.append(f"`[{i}]` {n}")
                e.description = self.prefix + "\n".join(x[num:num + self.per_page]) + self.suffix
            else:
                e.description = self.prefix + "\n".join(self.entries[num:num + self.per_page]) + self.suffix
        elif isinstance(self.entries, str):
            e.description = self.prefix + self.entries + self.suffix

        title = ""
        if isinstance(self.title, list):
            if (ti:= len(self.title)) != (en:= self.pages):
                raise PaginatorError(f"Got a list of titles but it does not match the amount of entries: {ti}t/{en}e")
            title = str(self.title[self.page-1])
        elif isinstance(self.title, str):
            title = str(self.title)

        if self.show_page_num:
            if self.footertext != discord.Embed.Empty:
                title += f" [{self.page}/{self.pages}]"
                if self.show_entry_count:
                    en = _("entries")
                    title += f" ({len(self.entries)} {en})"
            else:
                p = _("page")
                footer = f"{p} {self.page}/{self.pages}"
                if self.show_entry_count:
                    en = _("entries")
                    footer += f" ({len(self.entries)} {en})"
                e.set_footer(text=footer)
        else:
            if self.show_entry_count:
                if self.footertext != discord.Embed.Empty:
                    en = _("entries")
                    title += f" ({len(self.entries)} {en})"
                else:
                    en = _("entries")
                    e.set_footer(text=f"({len(self.entries)} {en})")
            else:
                pass

        e.title = title

        if isinstance(self.author, (discord.User, discord.Member, discord.ClientUser)):
            e.set_author(icon_url=self.author.avatar.with_static_format("png"), name=self.author)
        elif isinstance(self.author, discord.Guild):
            e.set_author(icon_url=self.author.icon.with_format("png"), name=self.author)
        elif isinstance(self.author, str):
            e.set_author(icon_url=self.ctx.author.avatar.with_static_format("png"), name=self.author)
        return e

    async def add_reactions(self):
        if self.pages == 1 or isinstance(self.entries, str):
            await self.message.add_reaction(list(self.reactions.keys())[2])
        elif self.pages == 2:
            for e in list(self.reactions.keys())[1:4]:
                await self.message.add_reaction(e)
        else:
            for e in list(self.reactions.keys()):
                await self.message.add_reaction(e)

    def go_to_first(self):
        self.page = 1

    def go_to_previous(self):
        if self.page == 1:
            return
        self.page -= 1

    def stop_paginating(self):
        self.paginating = False

    def go_to_next(self):
        if self.page == self.pages:
            return
        self.page += 1

    def go_to_last(self):
        self.page = self.pages

    async def edit_page(self):
        await self.message.edit(embed=self.embed())

    def check(self, r, u):
        if u.id != self.ctx.author.id:
            return False

        if r.message.id != self.message.id:
            return False

        if str(r) not in self.reactions.keys():
            return False

        return True

    async def start(self):
        self.message = await self.ctx.channel.send(embed=self.embed())
        await self.add_reactions()
        self.paginating = True

        while self.paginating:
            try:
                done, pending = await asyncio.wait([
                    self.bot.wait_for('reaction_add', check=self.check),
                    self.bot.wait_for('reaction_remove', check=self.check)],
                    timeout=self.timeout,
                    return_when=asyncio.FIRST_COMPLETED)

                for task in pending:
                    task.cancel()

                if not done:
                    raise asyncio.TimeoutError()

                r, u = done.pop().result()

                do = self.reactions[str(r)]()
                if asyncio.iscoroutine(do):
                    await do
                    break


                try:
                    await self.message.remove_reaction(r, u)
                except:
                    pass
                await self.edit_page()

            except asyncio.TimeoutError:
                self.paginating = False
                try:
                    await self.message.delete()
                except:
                    pass
                finally:
                    break

        try:
            await self.message.delete()
        except:
            pass

class ErrorPages(EmbedPages):
    def __init__(self, *args, **kwargs):
        self.error_ids = kwargs.pop("error_ids")
        self.status = kwargs.pop("status")
        # self.command = kwargs.pop("command")
        super().__init__(*args, **kwargs)

    def embed(self):
        page = self.page-1
        e = discord.Embed(url=self.url, color=self.color)
        e.set_thumbnail(url=self.thumbnail)

        icons = {"fix": "https://trac.cyberduck.io/raw-attachment/wiki/help/en/howto/mount/sync/overlay-sync.png",
                 "nofix": "https://trac.cyberduck.io/raw-attachment/wiki/help/en/howto/mount/sync/overlay-error.png"}

        text = {"fix": f"Change the error status to 'unresolved' by doing | {self.ctx.prefix}dev err unresolved {self.error_ids[self.page-1]}",
                "nofix": f"Change the error status to 'fixed' by doing | {self.ctx.prefix}dev error fix {self.error_ids[self.page-1]}"}

        e.description = self.entries[page]

        if self.status[page]:
            e.title = f"Error #{self.error_ids[page]} is fixed!"
        else:
            e.title = f"Error #{self.error_ids[page]} is not fixed yet!"

        e.set_author(icon_url=str(self.ctx.emoji.xmark.url), name=self.title+f" [{self.page}/{len(self.entries)}]")
        e.set_footer(icon_url=icons["fix"] if self.status[page] else icons["nofix"],
                     text=text["fix"] if self.status[page] else text["nofix"])
        return e

class MemberPages(EmbedPages):
    def __init__(self, *args, **kwargs):
        self.members = kwargs.pop("members")
        super().__init__(*args, entries=[self.members[i:i+25] for i in range(0, len(self.members), 25)], **kwargs)

    def member_page(self):
        l = []
        for i, m in enumerate(self.members, start=1):
            l.append(f"`[{i}]` {m}")
        num = (self.page - 1) * 25
        return l[num:num+25]

    def embed(self):
        e = discord.Embed(url=self.url,
                          color=self.color,
                          title=self.title,
                          description="\n".join(self.member_page()))
        e.set_footer(text=_("Page {0}/{1} ({2} entries)").format(self.page, len(self.pages), len(self.members)))
        return e

class HelpPages(EmbedPages):
    def __init__(self, ctx, *args, **kwargs):
        self.ctx = ctx
        self.commands = kwargs.pop("commands")
        self.title = []
        self.entries = []
        self.generate_pages()
        super().__init__(ctx, *args, title=self.title, entries=self.entries, **kwargs)
        self.reactions = {
            str(ctx.emoji.first): self.go_to_first,
            str(ctx.emoji.previous): self.go_to_previous,
            str(ctx.emoji.cancel): self.stop_paginating,
            str(ctx.emoji.next): self.go_to_next,
            str(ctx.emoji.last): self.go_to_last,
            str(ctx.emoji.home): self.go_to_home
        }

    async def add_reactions(self):
        if self.pages == 1 or isinstance(self.entries, str):
            await self.message.add_reaction(list(self.reactions.keys())[2])
            await self.message.add_reaction(list(self.reactions.keys())[-1])
        elif self.pages == 2:
            for e in list(self.reactions.keys())[1:4]:
                await self.message.add_reaction(e)
            await self.message.add_reaction(list(self.reactions.keys())[-1])
        else:
            for e in list(self.reactions.keys()):
                await self.message.add_reaction(e)

    def get_command_brief(self, command):
        lang = cm.get("settings", self.ctx.guild.id, "language")
        brief = cm.cmd_help.get(lang, {"uhoh": "NotFound"}).get(f"{command.qualified_name} - brief")
        if not brief:
            brief = cm.get("cmd_help", "en", f"{command.qualified_name} - brief")
        return brief or "..."

    def generate_pages(self):
        count = Counter()
        for cmd in self.commands:
            count[cmd.category] += 1



        for cat in count.keys():
            base_commands = [c for c in cat.commands if not c.parent]
            if len(base_commands) >= 25:
                for index, i in enumerate(range(0, len(base_commands), 13), start=1):
                    self.title.append(f"{cat.cog_name.upper()} ({index}) | {cat.name}")
                    self.entries.append("\n".join([f"`{cmd.name}` - {self.get_command_brief(cmd)}" for cmd in sorted(base_commands, key=lambda x: x.name)[i:i+13]]))
                # self.title.append(f"{cat.cog_name.upper()} (2) | {cat.name}")
                # self.entries.append("\n".join([f"`{cmd.name}` - {self.get_command_brief(cmd)}" for cmd in sorted(list(cat.commands), key=lambda x: x.name)[15:]]))
            else:
                self.title.append(f"{cat.cog_name.upper()} | {cat.name}")
                self.entries.append("\n".join([f"`{cmd.name}` - {self.get_command_brief(cmd)}" for cmd in sorted(base_commands, key=lambda x: x.name)]))

    # async def start(self):
    #     self.generate_pages()
    #     super().start()

    async def go_to_home(self):
        self.paginating = False
        await self.message.delete()
        msg = copy.copy(self.ctx.message)
        msg.content = self.ctx.prefix + "help"
        new_ctx = await self.bot.get_context(msg, cls=type(self.ctx))
        # helpcmd = self.bot.get_command("help")
        await new_ctx.reinvoke()

class RrListPages(EmbedPages):
    def __init__(self, *args, **kwargs):
        self.fields = kwargs.pop("fields")
        super().__init__(*args, entries=[self.fields[i:i+2] for i in range(0, len(self.fields), 2)], **kwargs)

    def get_fields(self):
        num = (self.page - 1) * 2
        return self.fields[num:num+2]

    def embed(self):
        pages = math.ceil(len(self.fields)/2)
        fields = self.get_fields()
        e = discord.Embed(color=self.color,
                          title=self.title)
        e.set_footer(text=_("Page {0}/{1} ({2} entries)").format(self.page, pages, len(self.fields)))
        for field in fields:
            e.add_field(**field)
        e.set_thumbnail(url="https://media.discordapp.net/attachments/460568954968997890/798380126185193492/rr.png")
        return e
