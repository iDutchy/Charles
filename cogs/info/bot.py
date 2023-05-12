import codecs
import inspect
import os
import pathlib
import platform
import time
from collections import Counter
from datetime import datetime, timezone

import discord
import psutil
from core import i18n
from core.cog import SubCog
from core.commands import commandExtra, groupExtra
from discord.ext import commands
from tabulate import tabulate
from utils.converters import readable_bytes as rb
from utils.humanize_time import date, timesince
from utils.paginator import EmbedPages


# class BotInfo(commands.Cog, name="Info"):
class BotInfo(SubCog, category="Bot Info"):
	def __init__(self, bot):
		self.bot = bot

	@staticmethod
	async def giveyouup(ctx, user):
		await ctx.send(f"Never gonna give {user.mention} up\nNever gonna let {user.mention} down\nNever gonna run around and desert {user.mention} \nNever gonna make {user.mention} cry\nNever gonna say goodbye\nNever gonna tell a lie and hurt {user.mention} \nNever gonna give {user.mention} up\nNever gonna let {user.mention} down\nNever gonna run around and desert {user.mention} \nNever gonna make {user.mention} cry\nNever gonna say goodbye\nNever gonna tell a lie and hurt {user.mention} \nNever gonna give {user.mention} up\nNever gonna let {user.mention} down\nNever gonna run around and desert {user.mention} \nNever gonna make {user.mention} cry\nNever gonna say goodbye\nNever gonna tell a lie and hurt {user.mention}")

	@commandExtra()
	async def donate(self, ctx):
		await ctx.send("Thanks for considering to donate, please DM `Dutchy#6127` if you want to make a donation :)")

	@commandExtra()
	async def privacy(self, ctx):
		await ctx.send("No other data is stored than the settings you configure in Charles. The settings are needed to display the items you set in the therefore related commands. You may at all times request to view what is all stored and to have it all deleted. You can also manually remove your data by using the provided commands. Any messages sent to the bot in DMs are logged in the support server by fault to provide an extra service of support through the bot. Once you create a DM with the bot you will also be notified about this along with the option to opt-out of the logging.")

	@groupExtra(category="Bot Info", invoke_without_command=True)
	async def top(self, ctx):
		await ctx.send_help(ctx.command)

	@top.command(name="commands")
	async def _commands(self, ctx):
		stats = await self.bot.db.fetch("SELECT command, SUM(usage) as total_usage FROM cmd_stats WHERE user_id != 171539705043615744 GROUP BY command ORDER BY total_usage DESC LIMIT 10")

		table = [[x['command'], x['total_usage']] for x in stats]
		tab = tabulate(table, headers=["Command", "Used"], tablefmt="fancy_grid").replace("├───────────┼────────┤\n", "")

		e = discord.Embed(color=ctx.embed_color, title="Top Command Usage")
		# msg  = "Command             | Used\n"
		# msg += "--------------------+------\n"
		# msg += "\n".join([f"{x['command']:20}| {x['total_usage']}" for x in stats])

		e.description = f"```ml\n{tab}```"

		await ctx.send(embed=e)

	@commandExtra(category="Bot Info", aliases=['emoji'])
	async def emojis(self, ctx, search=None):
		if search:
			if len(search) > 32:
				return await ctx.send(_("Emojis have a maximum name length of 32 characters. Your search term contained {0} characters").format(len(search)))
			sorted_emojis = sorted([e for e in self.bot.emojis if search.lower() in e.name.lower() and e.is_usable()], key=lambda e: e.name)
		else:
			sorted_emojis = sorted([e for e in self.bot.emojis if e.is_usable()], key=lambda e: e.name)
		emojis = [f"{e} | `{e.id}` | **{discord.utils.escape_markdown(e.name)}**" for e in sorted_emojis]
		paginator = EmbedPages(ctx,
							title=_("All bot emojis") + ((" "+_("containing '{0}'").format(search)) if search else "") + ":",  # noqa: E128
							author=self.bot.user,
							entries=emojis,
							per_page=15,
							show_entry_count=True,
							timeout=120)
		return await paginator.start()

	@commandExtra(category="Bot Info")
	async def disabled(self, ctx):
		globally, modules, categories, commands = [], [], [], []

		if len(self.bot.cache.globaldisabled) >= 1:
			for k, v in self.bot.cache.globaldisabled.items():
				globally.append(f"`{k}` - {v}")
		for x in (m := self.bot.cache.get("modules", ctx.guild.id)):
			if m[x] is False:
				modules.append(x)
		for y in (c := self.bot.cache.get("categories", ctx.guild.id)):
			if c[y] is False:
				categories.append(y)
		if cmds := self.bot.cache.get("settings", ctx.guild.id, "disabled_commands"):
			for x in cmds:
				commands.append(x)

		e = discord.Embed(color=ctx.embed_color, title=_("Disabled `modules`/`categories`/`commands`"))
		if globally:
			e.add_field(name=_("**Global (disabled by bot owner)**"), value="\n".join(globally), inline=False)
		e.add_field(name=_("**Modules**"), value="\n".join(modules) if modules else _("None"), inline=False)
		e.add_field(name=_("**Categories**"), value="\n".join(categories) if categories else _("None"), inline=False)
		e.add_field(name=_("**Commands**"), value=f"`{'`, `'.join(commands)}`" if commands else _("None"), inline=False)

		await ctx.send(embed=e)

	@commandExtra(aliases=['source', 'src'], category="Bot Info")
	async def sourcecode(self, ctx, *, command=None):
		if ctx.author.id != self.bot.owner_id:
			return await ctx.send(_("Charles is now **private sourced**! You may request access by DMing `Dutchy#6127`. Dm him your __username__ and the __reason__ why you wish to view the source. Your request will then be reviewed."))

		source_url = 'https://github.com/iDutchy/Charles'
		if command is None:
			return await ctx.send(source_url)

		if command.lower() == "help":
			return await ctx.send(source_url + '/blob/master/cogs/Help.py')

		cmd = self.bot.get_command(command)
		if cmd is None:
			return await ctx.send(_("This command doesn't exist!"))

		if cmd.cog_name.lower() == "test":
			return await ctx.send(_("This is a testing command. I can not show you the source of this command yet."))

		if cmd.cog_name.lower() == "ytt":
			return await ctx.send(_("This is a private command."))

		try:
			source = inspect.getsource(cmd.callback)
		except AttributeError:
			return await ctx.send(_("This command doesn't exist!"))
		if len(source) + 8 <= 2000:
			await ctx.send(f'```py\n{source}\n```')
		else:
			branch = 'master'
			obj = self.bot.get_command(command.replace('.', ' '))

			# since we found the command we're looking for, presumably anyway, let's
			# try to access the code itself
			src = obj.callback.__code__
			module = obj.callback.__module__

			lines, firstlineno = inspect.getsourcelines(src)
			location = module.replace('.', '/') + '.py'

			final_url = f'<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>'
			await ctx.send(_("Source was too long to post on discord, so here's the url to the source on GitHub:") + f"\n{final_url}")

	@commandExtra(category="Bot Info", aliases=['cloc', 'lc'])
	async def linecount(self, ctx):
		comments = coros = funcs = classes = lines = pyfiles = imgs = imports = chars = 0
		for path, subdirs, files in os.walk('.'):
			if str(path).startswith("./venv"):
				continue
			for name in files:
				if name.endswith('.py'):
					pyfiles += 1
					with open(f"{path}/{name}") as of:
						for l in of.readlines():
							l = l.strip()
							if l.startswith('import') or l.startswith('from'):
								l = l.lstrip('import')
								imports += len(l.split(','))
							if l.startswith('class'):
								classes += 1
							if l.startswith('def'):
								funcs += 1
							if l.startswith('async def'):
								coros += 1
							if '#' in l:
								comments += 1
							lines += 1
							chars += len(l)

				if name.endswith('.png') or name.endswith('.jpg') or name.endswith('.jpeg'):
					imgs += 1

		countmsg = ['```yaml']
		countmsg.append(f"     Files: {pyfiles:,d}")
		countmsg.append(f"     Lines: {lines:,d}")
		countmsg.append(f"Characters: {chars:,d}")
		countmsg.append(f"   Imports: {imports:,d}")
		countmsg.append(f"   Classes: {classes:,d}")
		countmsg.append(f" Functions: {funcs:,d}")
		countmsg.append(f"Coroutines: {coros:,d}")
		countmsg.append(f"  Comments: {comments:,d}")
		countmsg.append("")
		countmsg.append(f"    Images: {imgs:,d}")
		countmsg.append('```')

		e = discord.Embed(color=ctx.embed_color,
						  title=_("Source lines info"),
						  description = "\n".join(countmsg))
		await ctx.send(embed=e)

	@commandExtra(category="Bot Info")
	async def system(self, ctx):
		# try:
		swap = psutil.swap_memory()
		svmem = psutil.virtual_memory()
		disk = psutil.disk_usage('/')
		bt = datetime.fromtimestamp(psutil.boot_time()).replace(tzinfo=timezone.utc)
		cpufreq = psutil.cpu_freq()

		system = []
		system.append(_("**Host OS**") + f" : {platform.platform()}")
		system.append(_("**Boot time**") + f" : {bt.month}/{bt.day}/{bt.year} {bt.hour}:{bt.minute}:{bt.second}")
		system.append(_("**Uptime**") + f" : {timesince(bt)[:-3]}")
		cpu = []
		# cpu.append(_("**Max frequency**") + f" : {cpufreq.max:.2f}Mhz")
		# cpu.append(_("**Min frequency**") + f" : {cpufreq.min:.2f}Mhz")
		cpu.append(_("**Current frequency**") + f" : {cpufreq.current:.2f}Mhz")
		cpu.append(_("**Total cores**") + f" : {psutil.cpu_count(logical=True)}")
		cpu.append(_("**Physical cores**") + f" : {psutil.cpu_count(logical=False)}")
		for i, percentage in enumerate(psutil.cpu_percent(percpu=True), start=1):
			cpu.append(_("**Core {0}**").format(str(i)) + f" : {percentage}%")
		cpu.append(_("**Total usage**") + f" : {psutil.cpu_percent()}%")
		memory = []
		memory.append("**●▬▬▬๑ " + _("Storage") + " ๑▬▬▬●**")
		memory.append(_("**Total**") + f" : {rb(disk.total)} | " + _("**Free**") + f" : {rb(disk.free)} | " + _("**Used**") + f" : {rb(disk.used)} ({disk.percent}%)")
		memory.append("**●▬▬▬๑ " + _("Swap") + " ๑▬▬▬●**")
		memory.append(_("**Total**") + f" : {rb(swap.total)} | " + _("**Free**") + f" : {rb(swap.free)} | " + _("**Used**") + f" : {rb(swap.used)} ({swap.percent}%)")
		memory.append("**●▬▬▬๑ " + _("RAM") + " ๑▬▬▬●**")
		memory.append(_("**Total**") + f" : {rb(svmem.total)} | " + _("**Free**") + f" : {rb(svmem.available)} | " + _("**Used**") + f" : {rb(svmem.used)} ({svmem.percent}%)")

		em = discord.Embed(color=ctx.embed_color, title=_("System Info"))
		em.add_field(name=_("**System**"), value='\n'.join(system), inline=False)
		em.add_field(name=_("**CPU**"), value='\n'.join(cpu), inline=False)
		em.add_field(name=_("**Memory**"), value='\n'.join(memory), inline=False)
		em.set_thumbnail(url="https://img.icons8.com/cotton/2x/server.png")
		await ctx.send(embed=em)
		# except Exception as e:
		#     await ctx.send(_("Failed to get system info"))

	@commandExtra(category="Bot Info")
	async def ping(self, ctx, user: discord.User = None):
		if user:
			await self.giveyouup(ctx, user)
			return
		before = time.perf_counter()
		message = await ctx.send("Pong")
		ping = (time.perf_counter() - before) * 1000

		before_db = time.perf_counter()
		await self.bot.db.fetchrow("SELECT * FROM guildsettings LIMIT 1")
		db_ping = (time.perf_counter() - before_db) * 1000

		# try:
		#     before_web = time.perf_counter()
		#     r = await self.bot.session.get("https://charles-bot.com/")
		#     await r.read()
		#     web_ping = (time.perf_counter() - before_web) * 1000
		# except:
		#     web_ping = 0.0

		# try:
		#     before_api = time.perf_counter()
		#     r = await self.bot.session.get("https://api.charles-bot.com/")
		#     await r.read()
		#     api_ping = (time.perf_counter() - before_api) * 1000
		# except:
		#     api_ping = 0.0

		c = {
			"t": _("typing"),
			"ws": _("websocket"),
			"d": _("database"),
			"w": _("website"),
			"a": _("api")
		}

		e = discord.Embed(color=ctx.embed_color, title="Pong")
		e.add_field(name=f"<a:typing:597589448607399949> | {c['t']}", value=f"`{ping:.2f}ms`")
		e.add_field(name=f"<:charles:639898570564042792> | {c['ws']}", value=f"`{int(self.bot.latency*1000):.2f}ms`")
		e.add_field(name=f"<:postgres:750507236815667251> | {c['d']}", value=f"`{db_ping:.2f}ms`")
		# e.add_field(name=f"<:web:678724316464152589> | {c['w']}", value=f"`{web_ping:.2f}ms`")
		# e.add_field(name=f"<:webn:677258573314523189> | {c['a']}", value=f"`{api_ping:.2f}ms`")
		# e.add_field(name="\u200b", value="\u200b")

		await message.edit(content=None, embed=e)

	@ping.error
	async def ping_error(self, ctx, exc):
		if isinstance(exc, commands.BadArgument):
			await ctx.invoke(ctx.command)
		else:
			pass

	@commandExtra(category="Bot Info")
	async def support(self, ctx, user: discord.User = None):
		bot = user or self.bot.user
		if not bot.bot:
			return await ctx.send(_("If you want support from an user, just DM them... This is to find support servers for bots."))
		try:
			await self.bot.dblpy.get_bot_info(bot.id)
		except:
			try:
				r = await self.bot.session.get(f"https://discord.bots.gg/api/v1/bots{bot.id}")
				d = await r.json()
				support = d['supportInvite']
			except:
				return await ctx.send(_("I could not find a support server for this bot..."))
		await ctx.send("https://charles-bot.com/support" + ("" if bot.id == self.bot.user.id else f"?bot={bot.id}"))
		# await ctx.send("https://discord.gg/wZSH7pz")

	@commandExtra(category="Bot Info", aliases=['botinfo'])
	@commands.guild_only()
	async def about(self, ctx):
		process = psutil.Process(os.getpid())
		ramUsage = process.memory_full_info().rss / 1024**2
		channel_types = Counter(type(c) for c in self.bot.get_all_channels())
		voice = channel_types[discord.channel.VoiceChannel]
		text = channel_types[discord.channel.TextChannel]

		embed = discord.Embed(colour=ctx.embed_color)
		embed.set_author(icon_url=self.bot.user.avatar.url, name=f"{self.bot.user} | {self.bot.config['settings']['BOT_VERSION']}")
		info = []
		info.append(_("**Developer:**") + " Dutchy#6127")
		info.append(_("**Library:**") + f" [enhanced-dpy (custom d.py) {discord.__version__}](https://github.com/iDutchy/discord.py)")
		info.append(_("**Last Boot:**") + f" {timesince(self.bot.uptime)}")
		info.append(_("**Created:**") + f" {date(self.bot.user.created_at)} ({timesince(self.bot.user.created_at)})")
		embed.add_field(name=_("**General Info**"), value='<:arrow:735653783366926931> ' + '\n<:arrow:735653783366926931> '.join(info), inline=False)

		stats = []
		cmds = await self.bot.db.fetchval("SELECT SUM(usage) FROM cmd_stats")
		stats.append(_("**Commands Loaded:**") + f" {len(set(self.bot.walk_commands()))}")
		stats.append(_("**Commands Used:**") + f" {int(cmds):,d}")
		stats.append(_("**Servers:**") + f" {len(self.bot.guilds)}")
		stats.append(_("**RAM Usage:**") + f" {ramUsage:.2f} MB")
		stats.append(_("**Users:**") + f" {sum(g.member_count for g in self.bot.guilds if not g.unavailable):,d}")
		stats.append(_("**Channels:**") + f" <:channel:585783907841212418> {text:,d} | <:voice:585783907673440266> {voice:,d}")
		embed.add_field(name=_("**Stats**"), value='<:arrow:735653783366926931> ' + '\n<:arrow:735653783366926931> '.join(stats), inline=False)

		# embed.add_field(name=_("Channels"), value=f"<:channel:585783907841212418> {text}\n<:voice:585783907673440266> {voice}")
		# embed.add_field(name=_("Commands Loaded"), value=len([x.name for x in self.bot.commands]), inline=True)
		# embed.add_field(name=_("Servers"), value=len(self.bot.guilds))
		# embed.add_field(name=_("RAM Usage"), value=f"{ramUsage:.2f} MB", inline=True)
		# embed.add_field(name=_("Last Boot"), value=timesince(self.bot.uptime), inline=True)
		# embed.add_field(name=_("Users"), value=f"<:online:313956277808005120>⠀{unique_online} \n"
		#                                        f"<:offline:313956277237710868>⠀{unique_offline} \n"
		#                                        f"<:away:313956277220802560>⠀{unique_idle} \n"
		#                                        f"<:dnd:313956276893646850>⠀{unique_dnd} \n"
		#                                        f"**~~------------------~~**\n" +
		#                                        _("Total") + f":⠀{len(unique_members)}\n")
		# embed.add_field(name=_("Created"), value=f"{date(self.bot.user.created_at)}\n({timesince(self.bot.user.created_at)})")
		embed.set_image(url="attachment://Devision.png")
		embed.set_footer(text=_("Charles is one of the bots created by Devision."))
		await ctx.send(embed=embed, file=self.bot.theme.logo_full)
		# embed.add_field(name=_("Developer"), value="Dutchy#6127", inline=True)
		# embed.add_field(name=_("Library"), value="[Discord.py](https://github.com/Rapptz/discord.py)")

	@commandExtra(category="Bot Info", aliases=['joinme', 'botinvite'])
	async def invite(self, ctx, user: discord.User = None):
		bot = user or self.bot.user
		if not bot.bot:
			return await ctx.send(_("Thats not how inviting users works... You can only use this to generate an invite link for a bot!"))
		# await ctx.send("https://charles-bot.com/invite")
		await ctx.send("https://charles-bot.com/invite" + ("" if bot.id == self.bot.user.id else f"?bot={bot.id}"))

	@commandExtra(category="Bot Info")
	async def vote(self, ctx):
		t = _("TIP: You can be reminded by me when you can vote again! To toggle vote reminders, do: `{0}voteremind`").format(ctx.prefix)
		await ctx.send(f"https://charles-bot.com/vote\n\n{t}")
		# await ctx.send(f"https://top.gg/bot/505532526257766411/vote\n\n{t}")

	@commandExtra(category="Bot Info")
	async def suggest(self, ctx, *, suggestion: str):
		schan = self.bot.get_channel(531628986573258784)

		semb = discord.Embed(color=0xf0c92d,
			title=ctx.author.id,
			description=f"__**New suggestion!**__\n\nFrom: {ctx.author}\nSubmitted in: {ctx.guild.name}"
		)
		semb.set_author(name=ctx.author,icon_url=ctx.author.avatar.url)
		semb.add_field(name="SUGGESTION:",
			value=f"```fix\n{suggestion}```"
		)
		semb.set_footer(text=ctx.author.id)

		smsg = await schan.send(embed=semb)

		await smsg.add_reaction(':upvote:274492025678856192')
		await smsg.add_reaction(':downvote:274492025720537088')

		newsmsg = smsg.embeds[0]
		newsmsg.set_footer(text=smsg.id)
		await smsg.edit(embed=newsmsg)

		# Build the thanks embed
		tyemb = discord.Embed(color=ctx.embed_color)
		tyemb.set_author(name=ctx.author.name,icon_url=ctx.author.avatar.url)

		n = _("support server")
		support_hyperlink = f"[{n}](https://discord.gg/wZSH7pz)"

		tyemb.add_field(name="<:thanks:465678993576689665> " + _("Thank you!"),
			value=_("Thank you for submitting this suggestion, {0}! Check out the {1} to see if your suggestion has been accepted or denied.").format(ctx.author.display_name, support_hyperlink) + ":smile:"
		)
		tyemb.add_field(name=_("Your submitted suggestion:"), value=f"```fix\n{suggestion}```")

		await ctx.send(embed=tyemb)
		await ctx.message.delete(silent=True)


def setup(bot):
	pass
