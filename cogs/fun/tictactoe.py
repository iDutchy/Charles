import discord
import random
import asyncio

from discord.ext import commands
from core.commands import commandExtra
from PIL import Image as img, ImageOps as imgops
from io import BytesIO as b
from core.cog import SubCog

# GAME BOARD LAYOUT
#
#  1 | 2 | 3    | 1 = (30, 30),  2 = (395, 30),  3 = (760, 30)  | win(123) = (30, 100), win(147) = (100, 30)
# ——— ——— ———  |                                                              | win(159) = (30, 30)
#  4 | 5 | 6    | 4 = (30, 395), 5 = (395, 395), 6 = (760, 395) | win(456) = (30, 465), win(258) = (465, 30)
# ——— ——— ———  |                                                              | win(357) = (15, 15) + mirror
#  7 | 8 | 9    | 7 = (30, 760), 8 = (395, 760), 9 = (760, 760) | win(789) = (30, 840), win(369) = (840, 30)

O = img.open(b(open('db/images/ttt/o.png', 'rb').read()))
X = img.open(b(open('db/images/ttt/x.png', 'rb').read()))
WH = img.open(b(open('db/images/ttt/ttt_won_h.png', 'rb').read()))
WV = img.open(b(open('db/images/ttt/ttt_won_v.png', 'rb').read()))
WD = img.open(b(open('db/images/ttt/ttt_won_d.png', 'rb').read()))
BOARD = img.open(b(open('db/images/ttt/tttboard.png', 'rb').read()))
LAYOUT = "```GAME BOARD LAYOUT\n\n 1 | 2 | 3\n ——— ——— ———\n 4 | 5 | 6\n ——— ——— ———\n 7 | 8 | 9```"


class TTTGame:
    def __init__(self, **kwargs):
        self.player1 = kwargs.get("player1")
        self.player2 = kwargs.get("player2")
        self.against_bot = kwargs.get("against_bot")
        self.channel = kwargs.get("channel")
        self.current_turn = kwargs.get("beginner")
        self.player1_choices = []
        self.player2_choices = []
        self.board = BOARD.copy()
        self.message = None

class TicTacToe(SubCog, category="Games"):
    def __init__(self, bot):
        self.bot = bot
        self.possible_wins = [ 
                (1,2,3),
                (4,5,6),
                (7,8,9),
                (1,4,7),
                (2,5,8),
                (3,6,9),
                (1,5,9),
                (3,5,7)
          ]
        self.games = []
        self.pending_invites = []

    def create_ttt_game(self, **kwargs):
        game = TTTGame(player1=kwargs.get("author"),
                        player2=kwargs.get("against"),
                        against_bot=kwargs.get("against_bot", False),
                        channel=kwargs.get("channel"),
                        beginner=kwargs.get("beginner"))
        self.games.append(game)
        return game

    def is_in_ttt_game(self, user):
        if user in [g.player1 for g in self.games]:
            return True
        elif user in [g.player2 for g in self.games]:
            return True
        else:
            return False

    def get_ttt_game(self, user):
        if self.is_in_ttt_game(user.id):
            for g in self.games:
                if user.id == g.player1 or user.id == g.player2:
                    return g
        return None

    def check_for_win(self, game):
        for win in self.possible_wins:
            if set(win) <= set(game.player1_choices):
                return (set(win), 1)
            elif set(win) <= set(game.player2_choices):
                return (set(win), 2)
        else:
            return False

    @staticmethod
    def get_move_position(move):
        positions = {
            1: (30, 30),
            2: (395, 30),
            3: (760, 30),
            4: (30, 395),
            5: (395, 395),
            6: (760, 395),
            7: (30, 760),
            8: (395, 760),
            9: (760, 760)
        }
        return positions[move]

    @staticmethod
    def get_winstripe_position(win):
        num = int("".join(map(str, sorted(win))))
        positions = {
            123: {
                "stripe": WH,
                "mirror": False,
                "position": (30, 100)
            },
            456: {
                "stripe": WH,
                "mirror": False,
                "position": (30, 465)
            },
            789: {
                "stripe": WH,
                "mirror": False,
                "position": (30, 840)
            },
            147:  {
                "stripe": WV,
                "mirror": False,
                "position": (100, 30)
            },
            258:  {
                "stripe": WV,
                "mirror": False,
                "position": (465, 30)
            },
            369:  {
                "stripe": WV,
                "mirror": False,
                "position": (840, 30)
            },
            159:  {
                "stripe": WD,
                "mirror": False,
                "position": (30, 30)
            },
            357:  {
                "stripe": WD,
                "mirror": True,
                "position": (15, 15)
            }
        }
        return positions[num]


    @staticmethod
    def get_possible_moves(game):
        all_choices = list(range(1, 10))
        for c in game.player1_choices:
            all_choices.remove(c)
        for c in game.player2_choices:
            all_choices.remove(c)
        return all_choices

    def check_for_gameover(self, game):
        if not self.get_possible_moves(game):
            return True
        return False

    def update_board(self, game, move):
        moves = {1: X, 2: O}
        char = moves[game.current_turn]
        game.board.paste(char, self.get_move_position(move), char)

    @staticmethod
    def get_board_file(game):
        buf = b()
        game.board.save(buf, 'png')
        buf.seek(0)
        return discord.File(fp=buf, filename="ttt_board.png")

    @staticmethod
    def update_board_win(game, data):
        if data['mirror']:
            stripe = imgops.mirror(data['stripe'])
        else:
            stripe = data['stripe']
        game.board.paste(stripe, data['position'], stripe)

    async def make_bot_move(self, game):
        if self.check_for_gameover(game):
            await self.end_game_win(game, endtype=3)
            return

        choices = self.get_possible_moves(game)

        playerchoice = None
        if len(game.player2_choices) >= 2 or len(game.player1_choices) >= 2:
            for choice in choices:
                for win in self.possible_wins:
                    cantpick = []
                    newchoices = game.player2_choices.copy()
                    newchoices.append(choice)
                    if set(win) <= set(newchoices):
                        playerchoice = choice
                        break
                if playerchoice is None:
                    for win in self.possible_wins:
                        newchoices = game.player1_choices.copy()
                        newchoices.append(choice)
                        if set(win) <= set(newchoices):
                            playerchoice = choice
                            break
                        else:
                            continue
        else:
            if any(n not in choices for n in (1,3,7,9,)):
                if 5 in choices:
                    playerchoice = 5
            playerchoice = random.choice(choices)
        if not playerchoice:
            if any(n not in choices for n in (1,3,7,9,)):
                if 5 in choices:
                    playerchoice = 5
            playerchoice = random.choice(choices)

        game.player2_choices.append(playerchoice)
        self.update_board(game, playerchoice)
        if self.check_for_win(game):
            await self.end_game_win(game)
            return

        game.current_turn = 1
        if game.message:
            try:
                await game.message.delete()
            except:
                pass
        msg = await self.make_message(game)
        channel = self.bot.get_channel(game.channel)
        game.message = await channel.send(embed=msg, file=self.get_board_file(game), allowed_mentions=discord.AllowedMentions(users=False))

        await self.make_player_move(game)

    async def new_player_move(self, game):
        await self.make_player_move(game)

    async def make_message(self, game, end=False):
        user1 = await self.bot.try_user(game.player1)
        if game.against_bot:
            user2 = self.bot.user
            currentuser = await self.bot.try_user(game.player1)
        else:
            user2 = await self.bot.try_user(game.player2)
            currentuser = await self.bot.try_user(getattr(game, f"player{game.current_turn}"))

        e = discord.Embed(color=0x323c80, title="**Tic Tac Toe**")
        e.set_image(url="attachment://ttt_board.png")

        if not end:
            e.description = f"Player 1: {user1.mention} (`X`)\nPlayer 2: {user2.mention} (`O`)\n\nCurrent Turn: {currentuser.mention}"
            return e
        else:
            e.description = f"Player 1: {user1.mention} (`X`)\nPlayer 2: {user2.mention} (`O`)"
            return e

    async def make_player_move(self, game):
        if self.check_for_gameover(game):
            await self.end_game_win(game, endtype=3)
            return

        choices = self.get_possible_moves(game)

        def check(m):
            return m.content.isdigit() and m.content.isascii() and int(m.content) in choices and m.author.id == getattr(game, f"player{game.current_turn}") and m.channel.id == game.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=40)
        except asyncio.TimeoutError:
            channel = self.bot.get_channel(game.channel)
            await channel.send(_("Hey, {0}! It's your move but your time is running out. Please make your move in 20 seconds or the game will end.").format((await self.bot.try_user(getattr(game, f"player{game.current_turn}"))).mention))
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=20)
            except asyncio.TimeoutError:
                await self.end_game_win(game, endtype=2)
                return

        choice = int(msg.content)
        getattr(game, f"player{game.current_turn}_choices").append(choice)
        self.update_board(game, choice)
        if self.check_for_win(game):
            await self.end_game_win(game)
            return

        if game.against_bot:
            game.current_turn = 2
        else:
            if game.current_turn == 1:
                game.current_turn = 2
            else:
                game.current_turn = 1


        if game.against_bot:
            await self.make_bot_move(game)
        else:
            if game.message:
                try:
                    await game.message.delete()
                except:
                    pass
            msg = await self.make_message(game)
            channel = self.bot.get_channel(game.channel)
            game.message = await channel.send(embed=msg, file=self.get_board_file(game), allowed_mentions=discord.AllowedMentions(users=False))
            await self.new_player_move(game)

    async def end_game_win(self, game, endtype=1):
        channel = self.bot.get_channel(game.channel)
        try:
            await game.message.delete()
        except:
            pass
        msg = await self.make_message(game, end=True)
        if endtype == 1:
            win_nums, winner = self.check_for_win(game)
            data = self.get_winstripe_position(win_nums)
            self.update_board_win(game, data)
            win_user = await self.bot.try_user(getattr(game, f"player{winner}"))
            msg.description += f"\n\nWinner: {win_user.mention} 🎉"
        elif endtype == 2:
            msg.description += "\n\n**No winner, game timed out!**"
        elif endtype == 3:
            msg.description += "\n\n**No winner, ran out of possible moves!**"
        board = self.get_board_file(game)
        await channel.send(embed=msg, file=board, allowed_mentions=discord.AllowedMentions(users=False))
        self.games.remove(game)

    @commands.bot_has_permissions(attach_files=True)
    @commandExtra()
    async def ttt(self, ctx, user:discord.Member=None):
        if ctx.author.id in self.pending_invites:
            return await ctx.send(_("You already have an invite pending!"))
        if self.is_in_ttt_game(ctx.author.id):
            return await ctx.send(_("You are already playing Tic Tac Toe with someone!"))
        if not user:
            await ctx.send(_("You will be playing against me, I'm now randomly choosing who should go first!"), edit=False)
            await asyncio.sleep(3)
            first = random.choice([1,2])
            if first == 1:
                await ctx.send(_("Ok, you go first and will play as `X`! Good luck.\n\n**Instructions:**\nIt's very simple. Just say the number of the place you want to place your move! {0}").format(LAYOUT), edit=False)
            else:
                await ctx.send(_("I'm going first, you will be playing as `X`! Good luck.\n\n**Instructions:**\nIt's very simple. Just say the number of the place you want to place your move! {0}").format(LAYOUT), edit=False)
            await asyncio.sleep(4)
            game = self.create_ttt_game(
                author=ctx.author.id,
                against=self.bot.user.id,
                against_bot=True,
                channel=ctx.channel.id,
                beginner=first)
            msg = await self.make_message(game)
            game.message = await ctx.channel.send(embed=msg, file=self.get_board_file(game), allowed_mentions=discord.AllowedMentions(users=False))
            if first == 1:
                await self.make_player_move(game)
            else:
                await self.make_bot_move(game)
        else:
            if user.id == ctx.author.id:
                return await ctx.send(_("Sorry, but winning wont be that easy... You will need to find someone else to play with."))
            if user.id in self.pending_invites:
                return await ctx.send(_("Sorry, but `{0}` currently already has an invite for Tic Tac Toe pending...").format(str(user)))
            if self.is_in_ttt_game(user.id):
                return await ctx.send(_("Sorry, but `{0}` is already in a game of Tic Tac Toe!").format(str(user)))
            if user.bot:
                return await ctx.send(_("The only bot you can play against is me. If you wish to do so, run the command again but don't provide an user!"))
            self.pending_invites.append(user.id)
            self.pending_invites.append(ctx.author.id)
            check, message = await ctx.confirm(_("{0}, you have been invited to a game of Tic Tac Toe by {1}! Do you accept this invitation?").format(user.mention, ctx.author.mention), user=user)
            if not check:
                self.pending_invites.remove(user.id)
                self.pending_invites.remove(ctx.author.id)
                return await ctx.send(_("{0}, {1} did not accept your invitation...").format(ctx.author.mention, str(user)), edit=False)
            self.pending_invites.remove(user.id)
            self.pending_invites.remove(ctx.author.id)
            await ctx.send(_("The invitation has been accepted! I'm now choosing who will begin..."))
            await asyncio.sleep(3)
            first = random.choice([1,2])
            if first == 1:
                await ctx.send(_("{0} goes first and will play as `X`, {1} will play as `O`! Good luck.\n\n**Instructions:**\nIt's very simple. Just say the number of the place you want to place your move! {2}").format(str(ctx.author), str(user), LAYOUT), edit=False)
            else:
                await ctx.send(_("{0} goes first and will play as `O`, {1} will play as `X`! Good luck.\n\n**Instructions:**\nIt's very simple. Just say the number of the place you want to place your move! {2}").format(str(user), str(ctx.author), LAYOUT), edit=False)
            await asyncio.sleep(4)
            game = self.create_ttt_game(
                author=ctx.author.id,
                against=user.id,
                channel=ctx.channel.id,
                beginner=first)
            msg = await self.make_message(game)
            game.message = await ctx.channel.send(embed=msg, file=self.get_board_file(game), allowed_mentions=discord.AllowedMentions(users=False))
            await self.make_player_move(game)


def setup(bot):
    pass