import discord
from discord import app_commands
from discord.ext import commands

class TicTacToeButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="‎", row=x)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view
        
        if interaction.user != view.current_player:
            return await interaction.response.send_message("It's not your turn!", ephemeral=True)

        if view.board[self.x][self.y] != 0:
            return await interaction.response.send_message("This spot is already taken!", ephemeral=True)

        if view.current_player == view.player1:
            self.style = discord.ButtonStyle.danger
            self.label = "X"
            self.disabled = True
            view.board[self.x][self.y] = 1
            view.current_player = view.player2
        else:
            self.style = discord.ButtonStyle.success
            self.label = "O"
            self.disabled = True
            view.board[self.x][self.y] = 2
            view.current_player = view.player1

        winner = view.check_winner()
        if winner is not None:
            if winner == 1:
                content = f"🎉 {view.player1.mention} (X) wins the game!"
            elif winner == 2:
                content = f"🎉 {view.player2.mention} (O) wins the game!"
            else:
                content = "🤝 It's a tie!"
            
            for child in view.children:
                child.disabled = True
            return await interaction.response.edit_message(content=content, view=view)

        content = f"🎮 Tic-Tac-Toe: {view.current_player.mention}'s turn ({'X' if view.current_player == view.player1 else 'O'})"
        await interaction.response.edit_message(content=content, view=view)


class TicTacToeView(discord.ui.View):
    def __init__(self, player1: discord.User, player2: discord.User):
        super().__init__(timeout=120)
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]

        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    def check_winner(self):
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != 0:
                return self.board[i][0]
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != 0:
                return self.board[0][i]

        if self.board[0][0] == self.board[1][1] == self.board[2][2] != 0:
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != 0:
            return self.board[0][2]

        if all(self.board[i][j] != 0 for i in range(3) for j in range(3)):
            return 0

        return None


class TicTacToeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="xox", description="Play a game of Tic-Tac-Toe with another user! ❌⭕")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def xox(self, interaction: discord.Interaction, opponent: discord.User):
        if opponent.bot:
            return await interaction.response.send_message("You cannot play against a bot!", ephemeral=True)
        if opponent == interaction.user:
            return await interaction.response.send_message("You cannot play against yourself!", ephemeral=True)

        view = TicTacToeView(interaction.user, opponent)
        await interaction.response.send_message(
            content=f"🎮 Tic-Tac-Toe: {interaction.user.mention} (X) vs {opponent.mention} (O)\nIt's {interaction.user.mention}'s turn!",
            view=view
        )

async def setup(bot):
    await bot.add_cog(TicTacToeCog(bot))
