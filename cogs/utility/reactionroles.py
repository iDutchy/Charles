import asyncio
import copy
import secrets

import discord
from core import i18n
from core.cog import SubCog
from core.commands import groupExtra
from discord.ext import commands
from utils import checks
from utils.paginator import RrListPages


class ReactionRoles(SubCog, category="Reaction Roles"):
    def __init__(self, bot):
        self.bot = bot
        self.rr_example = {}

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        cache = self.bot.get_cache(payload.guild_id)

        if payload.message_id not in list(cache.reactionroles):
            return

        guild = self.bot.get_guild(payload.guild_id)
        user = await guild.try_member(payload.user_id)
        rr = cache.reactionroles.get_message(payload.message_id)
        if not rr.message_id:
            await rr.set_channel(payload.channel_id)

        if not rr.can_add(user):
            try:
                await user.send("You have reached the limit of roles you can get from this message!")
                await self.bot.http.remove_reaction(payload.channel_id, payload.message_id, payload.emoji, payload.user_id)
                return
            except:
                return

        if not (role_id := rr.get_role(str(payload.emoji))):
            await rr.set_usable(False)
            return
        if not (role := guild.get_role(role_id)):
            await rr.set_usable(False)
            return

        try:
            await user.add_roles(role)
        except:
            pass

        if rr.dm_msg:
            msg = copy.copy(rr.dm_msg)
            msg = msg.replace("\U0000007bserver\U0000007d", guild.name)
            msg = msg.replace("\U0000007brole\U0000007d", role.name)
            try:
                await user.send(msg)
            except:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        cache = self.bot.get_cache(payload.guild_id)

        if payload.message_id not in list(cache.reactionroles):
            return

        guild = self.bot.get_guild(payload.guild_id)
        user = await guild.try_member(payload.user_id)
        emoji = str(payload.emoji)
        if not emoji.startswith("<"):
            try:
                emoji = self.bot.get_emoji(payload.emoji.id)
                if emoji.animated:
                    emoji = str(payload.emoji).replace("<", "<a:")
            except:
                emoji = str(payload.emoji)
        rr = cache.reactionroles.get_message(payload.message_id)
        if not rr.message_id:
            await rr.set_channel(payload.channel_id)

        if not (role_id := rr.get_role(emoji)):
            await rr.set_usable(False)
            return
        if not (role := guild.get_role(role_id)):
            await rr.set_usable(False)
            return

        try:
            await user.remove_roles(role)
        except:
            return

    @groupExtra(invoke_without_command=True, aliases=['rr'])
    async def reactionrole(self, ctx):
        await ctx.send_help(ctx.command)

    async def get_message_new(self, ctx, e):
        e.title = _("{0} - Message Used").format(e.title.split(' - ')[0])
        e.description = _("For reactionroles we can either use an existing message that you pre-made, but I can also generate a new message for you! Please make your selection below.\n\n:one: - Create new message\n:two: - Use existing message")
        msg = await ctx.send(embed=e, edit=False)
        await msg.add_reaction("\U00000031\U0000fe0f\U000020e3")
        await msg.add_reaction("\U00000032\U0000fe0f\U000020e3")
        r, u = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id and u.id == ctx.author.id, timeout=30)
        await msg.delete()
        return str(r.emoji) == "\U00000031\U0000fe0f\U000020e3"

    async def get_message_type(self, ctx, e):
        e.title = _("{0} - Message Type").format(e.title.split(' - ')[0])
        e.description = _("Reaction Roles can be setup in 2 ways. Embeds or plain messages. Please make your selection below.\n\n:one: - Embed\n:two: - Plain message")
        msg = await ctx.send(embed=e, edit=False)
        await msg.add_reaction("\U00000031\U0000fe0f\U000020e3")
        await msg.add_reaction("\U00000032\U0000fe0f\U000020e3")
        r, u = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id and u.id == ctx.author.id, timeout=30)
        await msg.delete()
        return r.emoji

    async def get_emoji(self, ctx, e, data, cancel):
        e.title = _("{0} - Reaction Emoji").format(e.title.split(' - ')[0])
        e.description = _("Please now send me the name, id or emoji itself which you want to use! Remember, you can only use emojis from servers which I have access to. If you'd like to see all emojis I can access, use `{0}emojis [optional search term]` to see all my emojis (and their IDs!).").format(ctx.clean_prefix)
        if cancel:
            e.description = _("That one is done! If you'd like to add another reactionrole, please send me the next emoji. If you wish to leave it like this, please say \"cancel\"")
        msg = await ctx.send(embed=e, edit=False)
        emoji = None
        while emoji is None:
            m = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and not m.content.startswith(f"{ctx.clean_prefix}emojis"), timeout=90)
            if cancel:
                if m.content.lower() in ('cancel', '"cancel"'):
                    await msg.delete()
                    return None
            try:
                emoji = await commands.EmojiConverter().convert(ctx, m.content)
                if str(emoji) in data.keys():
                    await ctx.send(_("You're already using that emoji for this message. Please use a different emoji!"), delete_after=5, edit=False)
                    emoji = None
            except:
                try:
                    await m.add_reaction(m.content)
                    emoji = m.content
                    if str(emoji) in data.keys():
                        await ctx.send(_("You're already using that emoji for this message. Please use a different emoji!"), delete_after=5, edit=False)
                        emoji = None
                except:
                    await ctx.send(_("I could not find that emoji! Please try again."), delete_after=3, edit=False)
                    emoji = None
            
        await msg.delete()
        return emoji

    async def get_role(self, ctx, e, data):
        e.title = _("{0} - The Role").format(e.title.split(' - ')[0])
        e.description = _("Now please send me the name, id or mention of the role you want to bind to that emoji!")
        msg = await ctx.send(embed=e, edit=False)
        role = None
        while role is None:
            m = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id, timeout=90)
            try:
                role = await commands.RoleConverter().convert(ctx, m.content)
                if role.id in data.values():
                    await ctx.send(_("You're already using that role in this message. Please use a different role!"), delete_after=5, edit=False)
                    role = None
                elif role >= ctx.me.top_role:
                    await ctx.send(_("I can't add roles to people that are equal to or higher than my top role!"), delete_after=3.5)
                    role = None
            except:
                await ctx.send(_("I could not find that role! Please try again."), delete_after=3, edit=False)
                role = None
            
        await msg.delete()
        return role

    async def get_max_roles(self, ctx, e, total):
        e.title = _("{0} - Max Roles").format(e.title.split(' - ')[0])
        e.description = _("If you would like to limit the amount of roles someone can get from this message, please send the number of roles they can get. The limit is {0} roles for this message. If you dont want to set a limit, please send the total number ({0})!").format(total)
        msg = await ctx.send(embed=e, edit=False)
        maxa = None
        while maxa is None:
            m = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id, timeout=30)
            if not m.content.isdigit():
                await ctx.send(_("You did not provide me with a number, please try again!"), delete_after=4, edit=False)
            elif int(m.content) < 1:
                await ctx.send(_("You can net set a max of a negative numer or zero."), delete_after=4, edit=False)
            elif int(m.content) > total:
                await ctx.send(_("That number is too high! The max number of roles a user can get for this message is {0}.").format(total), delete_after=4, edit=False)
            else:
                maxa = int(m.content)
            
        await msg.delete()
        return maxa

    async def get_role_limit(self, ctx, e, roles):
        e.title = _("{0} - Role Limitation").format(e.title.split(' - ')[0])
        e.description = _("Do you want members to require a specific role to get reactionroles from this message? If yes, please send the role id, name or mention. If you want everyone to be able to access this, please say \"no\"")
        msg = await ctx.send(embed=e, edit=False)
        role = None
        while role is None:
            m = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id, timeout=90)
            if m.content.lower() in ('no', '"no"'):
                break
            try:
                role = await commands.RoleConverter().convert(ctx, m.content)
                if role.id in roles:
                    await ctx.send(_("That role is being used in this reaction role message! I can't require users to have this role if they need to get it from this message."), delete_after=5, edit=False)
                    role = None
            except:
                await ctx.send(_("I could not find that role! Please try again."), delete_after=3, edit=False)
                role = None
            
        await msg.delete()
        return role.id if role else None

    async def get_dm_message(self, ctx, e):
        e.title = _("{0} - DM Message").format(e.title.split(' - ')[0])
        e.description = _("Do you want to DM members when they receive a role? If yes, please tell me what message you want to use. If you don't, play say \"cancel\".\n\nIf you want to send a DM message, you can include th following in your message:\n`{server}` - will be replaced with your server name\n`{role}` - will be replaced with the name of the role they picked")
        msg = await ctx.send(embed=e, edit=False)
        dm = None
        while dm is None:
            m = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id, timeout=90)
            if m.content.lower() in ('cancel', '"cancel"'):
                
                break
            else:
                dm = m.content
            
        await msg.delete()
        return dm

    async def get_message_customization(self, ctx, e):
        e.title = _("{0} - Message Customization").format(e.title.split(' - ')[0])
        e.description = _("Since we will be making a new message, I'd like to know how you want to display it. The role list you can see in the example, but you can also set a customized message.\n\n:one: - Keep the message as the role list\n:two: - Add a custom message, but add the role list below it\n:three: - Set a custom message and remove the role list")
        msg = await ctx.send(embed=e, edit=False)
        await msg.add_reaction("\U00000031\U0000fe0f\U000020e3")
        await msg.add_reaction("\U00000032\U0000fe0f\U000020e3")
        await msg.add_reaction("\U00000033\U0000fe0f\U000020e3")
        r, u = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id and u.id == ctx.author.id, timeout=30)
        if str(r.emoji) == "\U00000031\U0000fe0f\U000020e3":
            await msg.delete()
            return None, False
        elif str(r.emoji) == "\U00000032\U0000fe0f\U000020e3":
            e.description = _("Okay, what do you want the message to be?")
            msg2 = await ctx.send(embed=e, edit=False)
            m = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id, timeout=300)
            await msg2.delete()
            rt = m.content, False
            
            await msg.delete()
            return rt
        elif str(r.emoji) == "\U00000033\U0000fe0f\U000020e3":
            e.description = _("Okay, what do you want the message to be?")
            msg2 = await ctx.send(embed=e, edit=False)
            m = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id, timeout=300)
            await msg2.delete()
            rt = m.content, True
            
            await msg.delete()
            return rt

    async def get_rr_channel(self, ctx, e):
        e.title = _("{0} - Channel").format(e.title.split(' - ')[0])
        e.description = _("Since you want me to make a new message, please tell me which channel to send it to.")
        msg = await ctx.send(embed=e, edit=False)
        channel = None
        while channel is None:
            m = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id, timeout=90)
            try:
                channel = await commands.TextChannelConverter().convert(ctx, m.content)
            except:
                await ctx.send(_("I could not find that channel! Please try again."), delete_after=3, edit=False)
                channel = None
            
        await msg.delete()
        return channel.id

    async def get_rr_message(self, ctx, e):
        e.title = _("{0} - Message").format(e.title.split(' - ')[0])
        e.description = _("Since you want to use a pre existing message, now please give me the *link* to the message you want to use.")
        msg = await ctx.send(embed=e, edit=False)
        message = None
        while message is None:
            m = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id, timeout=90)
            try:
                message = await commands.MessageConverter().convert(ctx, m.content)
                if message.id in list(ctx.cache.reactionroles.all_data.keys()):
                    message = None
                    await ctx.send(_("That message is already being used for reactionroles! Please pick a different message."), edit=False, delete_after=4)
            except:
                await ctx.send(_("I could not find that message! Please try again."), delete_after=3, edit=False)
                message = None
            
        await msg.delete()
        return message.channel.id, message.id

    @commands.max_concurrency(1, commands.BucketType.channel)
    @checks.has_permissions(manage_messages=True, manage_roles=True, add_reactions=True)
    @commands.bot_has_permissions(manage_messages=True, manage_roles=True, add_reactions=True)
    @reactionrole.command(name='create', aliases=['add', 'setup'])
    async def create_rr(self, ctx):
        try:
            embed = edit = False
            data = {}

            e = discord.Embed(color=ctx.embed_color, title=_("Reaction Roles Setup"))
            e.set_thumbnail(url="https://media.discordapp.net/attachments/460568954968997890/798380126185193492/rr.png")
            e.description = _("Welcome to my Reaction Role setup! I will guide you through this interactive setup. Let's begin!")
            await ctx.send(embed=e, delete_after=20, edit=False)

            await asyncio.sleep(2.5)

            mnew = await self.get_message_new(ctx, e)

            if mnew:
                edit = True
                mtype = await self.get_message_type(ctx, e)
                if mtype == "\U00000031\U0000fe0f\U000020e3":  # Embed
                    embed = True
                    msg = await ctx.send(embed=discord.Embed(color=ctx.embed_color, title=_("Reaction Role Message - Live Example")), edit=False)
                elif mtype == "\U00000032\U0000fe0f\U000020e3":  # Plain text
                    msg = await ctx.send("Reaction Role Message - Live Example", edit=False)
                self.rr_example[ctx.channel.id] = msg
            else:
                msg = await ctx.send("Reaction Role Message - Live Example", edit=False)
                self.rr_example[ctx.channel.id] = msg

            busy = lambda x: x in self.rr_example
            can_cancel = False
            while busy(ctx.channel.id):
                emoji = await self.get_emoji(ctx, e, data, can_cancel)
                if emoji is None:
                    break

                role = await self.get_role(ctx, e, data)
                data[str(emoji)] = role.id

                if embed:
                    msg = self.rr_example[ctx.channel.id]
                    em = msg.embeds[0]
                    desc = []
                    for k, v in data.items():
                        desc.append(f"{k} | <@&{v}>")
                    em.description = "\n".join(desc)
                    await self.rr_example[ctx.channel.id].edit(embed=em)
                else:
                    msg = self.rr_example[ctx.channel.id]
                    cnt = []
                    for k, v in data.items():
                        cnt.append(f"{k} | <@&{v}>")
                    await self.rr_example[ctx.channel.id].edit(content="Reaction Role Message - Live Example"+"\n\n"+"\n".join(cnt), allowed_mentions=discord.AllowedMentions.none())
                can_cancel = True

            e.title = _("{0} - Halfway Done").format(e.title.split(' - ')[0])
            e.description = _("Great! The emojis and roles have been configured now. All thats left to do now are a few extra settings.")
            await ctx.send(embed=e, delete_after=10, edit=False)
            await asyncio.sleep(3)

            if (total := len(data.keys())) > 1:
                max_roles = await self.get_max_roles(ctx, e, total)
                if max_roles == total:
                    e.description = _("Okay, I won't set a limit on the roles.")
                else:
                    e.description = _("Okay, I have set the limit to {0}!").format(max_roles)
                await ctx.send(embed=e, edit=False, delete_after=3.5)
            else:
                max_roles = 1

            role_limitation = await self.get_role_limit(ctx, e, list(data.values()))
            if role_limitation is not None:
                e.description = _("Alright, only members with the <@&{0}> role can get reaction roles from this message!").format(role_limitation)
            else:
                e.description = _("Okay, I'll leave these reaction roles available to everyone!")
            await ctx.send(embed=e, edit=False, delete_after=3.5)
            await asyncio.sleep(1.5)

            dm_msg = await self.get_dm_message(ctx, e)
            if dm_msg is not None:
                e.description = _("Alright, I will send that message to the members when they react for a role!")
            else:
                e.description = _("Okay, I will not DM them.")
            await ctx.send(embed=e, edit=False, delete_after=3.5)
            await asyncio.sleep(1.5)

            if not edit:
                channel_id, message_id = await self.get_rr_message(ctx, e)
                e.title = _("{0} - Finished").format(e.title.split(' - ')[0])
                e.description = _("And that was all! Your reaction roles have been completely setup!")
                await ctx.send(embed=e, edit=False)
                chan = ctx.guild.get_channel(channel_id)
                msg = await chan.fetch_message(message_id)
                for em in list(data.keys()):
                    await msg.add_reaction(em)
            else:
                if not embed:
                    msg, del_rl = await self.get_message_customization(ctx, e)
                    m = self.rr_example[ctx.channel.id]
                    if del_rl:
                        await self.rr_example[ctx.channel.id].edit(content=msg)
                    else:
                        await self.rr_example[ctx.channel.id].edit(content=f"{msg}\n\n{m.content}")
                else:
                    msg, del_rl = await self.get_message_customization(ctx, e)
                    if not msg:
                        e.title = _("{0} - Finished").format(e.title.split(' - ')[0])
                        e.description = _("And that was all! Since you want to keep it the way it is, your reaction roles have now been completely setup!")
                        await ctx.send(embed=e, edit=False)
                    if del_rl:
                        msg = self.rr_example[ctx.channel.id]
                        em = msg.embeds[0]
                        em.description = msg
                        await self.rr_example[ctx.channel.id].edit(embed=em)
                    else:
                        msg = self.rr_example[ctx.channel.id]
                        em = msg.embeds[0]
                        em.description = f"{msg}\n\n{em.description}"
                    await self.rr_example[ctx.channel.id].edit(embed=em)

                channel_id = await self.get_rr_channel(ctx, e)

                e.title = _("{0} - Finished").format(e.title.split(' - ')[0])
                e.description = _("Your reaction role setup has finished!")
                await ctx.send(embed=e, edit=False)

                chan = ctx.guild.get_channel(channel_id)
                msg = self.rr_example[ctx.channel.id]
                if msg.embeds:
                    em = msg.embeds[0]
                    if em.title == "Reaction Role Message - Live Example":
                        em.title = ""
                    message = await chan.send(embed=em)
                else:
                    if "Reaction Role Message - Live Example" in msg.content:
                        msg.content.replace("Reaction Role Message - Live Example", "").strip()
                    message = await chan.send(msg.content, allowed_mentions=discord.AllowedMentions.none())
                message_id = message.id
                for em in list(data.keys()):
                    await message.add_reaction(em)

            self.rr_example.pop(ctx.channel.id)
            await ctx.cache.reactionroles.create(ctx.guild.id, message_id, max_roles, dm_msg, role_limitation, channel_id, secrets.token_urlsafe(5), data)
            # await self.bot.db.execute(RRQ1, ctx.guild.id, message_id, max_roles, dm_msg, role_limitation, channel_id, secrets.token_urlsafe(5))
            # for emoji, role_id in data.items():
            #     await self.bot.db.execute(RRQ2, ctx.guild.id, message_id, role_id, emoji)
        except asyncio.TimeoutError:
            return await ctx.send(_("You took too long to reply, so I am cancelling the setup..."))

    @reactionrole.command(name='list')
    async def rr_list(self, ctx):
        if not ctx.cache.reactionroles:
            return await ctx.send("This server has no reactionroles setup")

        fields = []
        for mid in ctx.cache.reactionroles.all_data.keys():
            txt = []
            rr = ctx.cache.reactionroles.get_message(mid)
            txt.append(f"**Emojis:** {', '.join(rr.emojis)}")
            txt.append(f"**Channel:** {ctx.guild.get_channel(rr.channel_id).mention if rr.channel_id else 'Unknown'}")
            txt.append(f"**Requires role:** {ctx.guild.get_role(rr.role_restriction).mention if rr.role_restriction else 'None'}")
            txt.append(f"**Max roles:** {rr.max_roles}")
            txt.append(f"**Message:** {f'[jump]({rr.jump_url})' if rr.channel_id else 'Could not locate'}")
            if not rr.usable:
                txt.append("**WARNING:** This reactionrole message has been automatically flagged as 'not usable'. For more info, join the support server and contact my developer! He can help you fix it to make it usable again.")

            fields.append(dict(name=f"**ID:** `{rr.unique_id}`", value="\n".join(txt)))

        pages = RrListPages(ctx, fields=fields, title=_("Reaction Roles"))
        await pages.start()

    @reactionrole.command(name='delete')
    async def rr_delete(self, ctx, unique_id):
        try:
            msg = ctx.cache.reactionroles.get_message_by_id(unique_id)
        except:
            return await ctx.send(_("No reactionrole message with that ID was found!"))

        check, m = await ctx.confirm(_("Are you sure you want to delete this reactionrole message?"))
        await m.delete()

        if not check:
            return await ctx.send(_("Okay, I won't delete it."))

        await ctx.cache.reactionroles.delete(msg.message_id)
        await ctx.send(_("Reactionrole message with ID {0} has been deleted!").format(unique_id), edit=False)

        if not msg.jump_url:
            return

        check, m = await ctx.confirm(_("Do you want me to delete the message that was used for this reactionrole message too?"))
        await m.delete()

        if not check:
            return await ctx.send(_("Okay, I won't delete it."))

        try:
            await self.bot.http.delete_message(msg.channel_id, msg.message_id)
            await ctx.send(_("Okay, I have deleted the message!"))
        except:
            await ctx.send(_("Could not delete the message due to an unexpected error. Perhaps it's already deleted?"))


def setup(bot):
    pass
