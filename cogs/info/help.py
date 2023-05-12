import asyncio
from datetime import datetime

import discord
from core import i18n
from core.help import HelpCore
from utils.paginator import EmbedPages, HelpPages


def setup(bot):
    pass


class HelpCommand(HelpCore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_link(self, string, link):
        return f"[{string}]({link})"

    async def send_bot_help(self, mapping):
        owner = await self.context.bot.try_user(self.context.bot.owner_id)

        links = [self.get_link(_("Support"), "https://discord.gg/wZSH7pz"),
                self.get_link(_("Invite"), "https://discordapp.com/api/oauth2/authorize?client_id=505532526257766411&permissions=1609952598&scope=bot"),
                self.get_link(_("Vote"), "https://top.gg/bot/505532526257766411/vote"),
                self.get_link(_("Donate"), "https://charles-bot.com/donate"),
                self.get_link(_("Website"), "https://charles-bot.com/")]
        # self.get_link(_("Source"), "https://github.com/iDutchy/Charles")]

        total = len(set(self.context.bot.walk_commands()))
        usable = 0
        for c in self.context.bot.walk_commands():
            try:
                await c.can_run(self.context)
                usable += 1
            except:
                continue
        emb = discord.Embed(color=self.context.embed_color)
        emb.description = _("Made by {0}\nTotal commands: {1} | Usable by you (here): {2}```diff\n- [] = optional argument\n- <> = required argument\n- Do NOT type these when using commands!\n+ Type {3}help [command | module] for more help on a command or module!```{4}").format(owner, total, usable, self.context.clean_prefix, " | ".join(links))
        emb.set_thumbnail(url="https://cdn.discordapp.com/avatars/505532526257766411/d1cde11602889bd799dec9a82e29609f.png")
        emb.set_author(icon_url=self.context.author.avatar.url, name=self.context.author)

        cogs = []
        reactions = {}
        for extension in self.context.bot.cogs.values():
            if not extension.get_commands():
                continue
            if self.context.author != owner and extension.qualified_name.title() in self.owner_cogs:
                continue
            if extension.qualified_name in self.ignore_cogs:
                continue
            if extension.qualified_name == "Jishaku":
                continue
            if extension.qualified_name == "Private":
                if self.context.author.id not in self.context.bot.translators:
                    continue
            if self.context.guild:
                if extension.qualified_name.lower() in (toggles := self.context.bot.cache.get("modules", self.context.guild.id)):
                    if not toggles[extension.qualified_name.lower()]:
                        continue

            cogs.append(f"• {extension.icon} **{extension.qualified_name}**")
            reactions[extension.icon] = extension

        emb.add_field(name=_("Modules:"), value='\n'.join(sorted(cogs)))
        emb.add_field(name="\u200b", value="\u200b")

        ac = self.context.bot.get_channel(881194304016617523)
        news_msg = self.context.bot.config['settings']["news"]["MESSAGE"]
        if _id := self.context.bot.config['settings']["news"]["ID"]:
            a_msg = await ac.fetch_message(int(_id))
            a_date = a_msg.created_at.strftime("%b %d, %Y")
            msg = self.get_link(_("Jump to full news message!"), a_msg.jump_url) + f"\n\n{news_msg}"
        else:
            a_date = datetime.utcnow().strftime("%b %d, %Y")
            msg = news_msg

        emb.add_field(name="<:news:633059687557890070> " + _("Latest News - {0}").format(a_date), value=msg, inline=True)
        if self.context.guild:
            if self.context.me.guild_permissions.add_reactions:
                emb.set_footer(text=_("You can also click on one of the reactions to view the commands of their matching module!"))
        m = await self.context.channel.send(embed=emb)

        try:
            for r in sorted(list(reactions.keys())):
                await m.add_reaction(r)

            def check(r, u):
                return r.message.id == m.id and u.id == self.context.author.id and str(r) in reactions.keys()
            try:
                r, u = await self.context.bot.wait_for('reaction_add', check=check, timeout=60.0)
                await m.delete()
                await self.send_cog_help(reactions[str(r)])
            except asyncio.TimeoutError:
                try:
                    await m.clear_reactions()
                except:
                    return
        except:
            pass

    async def send_category_help(self, category):
        if not await self.can_send_category_help(category):
            return

        cogs = set([c.cog_name for c in list(set(category.commands))])
        e = discord.Embed(color=self.context.embed_color, title=f"__**Module:**__ {' & '.join(cogs)} | __**Category:**__ {category.name}")

        total_commands = []
        for cmd in list(cmd for cmd in self.context.bot.walk_commands() if cmd.cog.qualified_name != "Jishaku" and cmd.category == category):
            if cmd.qualified_name in self.context.bot.cache.get("settings", self.context.guild.id, "disabled_commands"):
                continue
            if cmd.parent:
                continue
            cmd_brief = self.get_command_brief(cmd)
            total_commands.append(f"`{cmd.name}` - {cmd_brief}")

        e.set_thumbnail(url=list(set(category.commands))[0].cog.big_icon)

        footer_text = _("- Type {0}help <Command Name> to see more detailed help about a command.").format(self.context.clean_prefix)
        e.set_footer(text=footer_text,icon_url="https://cdn.discordapp.com/avatars/505532526257766411/d1cde11602889bd799dec9a82e29609f.webp?size=1024")
        e.description = "\n".join(total_commands)
        await self.context.send(embed=e)

    async def send_command_help(self, command):
        if not await self.can_send_command_help(command):
            return

        formatted = await self.common_command_formatting(command)
        await self.context.send(embed=formatted)

    async def send_group_help(self, group):
        if not await self.can_send_command_help(group):
            return

        formatted = await self.common_command_formatting(group)
        sub_cmd_list = ""
        for group_command in group.commands:
            sub_cmd_list += f"`{group_command.name}` - {self.get_command_brief(group_command) or '...'}\n"
        formatted.add_field(name=_("**Subcommands:**"), value=sub_cmd_list, inline=False)
        await self.context.send(embed=formatted)

    async def send_cog_help(self, cog):
        if not await self.can_send_cog_help(cog):
            return

        pages = {}
        cmnds = []
        for cmd in cog.get_commands():
            if not self.command_is_enabled(cmd):
                continue

            if not hasattr(cmd, "category"):
                # setattr(cmd, "category", self.context.bot.get_category("Other"))
                continue
            if cmd.category.name not in pages:
                pages[cmd.category.name] = []
            cmd_brief = self.get_command_brief(cmd) or '...'
            pages[cmd.category.name].append(f"`{cmd.name}` - {cmd_brief}")
            cmnds.append(cmd)

        if not list(pages.keys()):
            await self.send_error_message(self.command_not_found(list(self.context.message.content.split(" "))[len(list(self.context.prefix.split(" ")))]))
            return

        footer_text = _("- Type {0}help <Command Name> to see more detailed help about a command.").format(self.context.clean_prefix)

        paginator = HelpPages(self.context,
                           commands=cmnds,
                           thumbnai=getattr(cog, "big_icon"),
                           footericon=self.context.bot.user.avatar.with_format('png'),
                           footertext=footer_text,
                           show_page_num=True)
        await paginator.start()
