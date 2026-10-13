import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class DuelButton(discord.ui.Button):
    def __init__(self, is_target: bool, index: int):
        color = discord.ButtonStyle.danger if not is_target else discord.ButtonStyle.success
        label = "🎯 DRAW & SHOOT!" if is_target else "💥 TRAP!"
        super().__init__(style=color, label=label, row=0)
        self.is_target = is_target

    async def callback(self, interaction: discord.Interaction):
        view: DuelView = self.view

        if interaction.user not in (view.player1, view.player2):
            return await interaction.response.send_message("You are not part of this duel!", ephemeral=True)

        if view.finished:
            return

        view.finished = True
        shooter = interaction.user
        opponent = view.player2 if shooter == view.player1 else view.player1

        for child in view.children:
            child.disabled = True

        if self.is_target:
            embed = discord.Embed(
                title="🤠 Western Duel - RESULTS",
                description=f"🎯 **FIRST TO CLICK THE GREEN BUTTON WINS!**\n\n🎉 {shooter.mention} hit the target first and defeated {opponent.mention}!",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="🤠 Western Duel - RESULTS",
                description=f"💥 **TRAP!**\n\n❌ {shooter.mention} clicked the wrong (red) button!\n🎉 {opponent.mention} won the duel!",
                color=discord.Color.red()
            )

        await interaction.response.edit_message(embed=embed, view=view)


class DuelView(discord.ui.View):
    def __init__(self, player1: discord.User, player2: discord.User):
        super().__init__(timeout=60)
        self.player1 = player1
        self.player2 = player2
        self.finished = False

        targets = [True, False, False]
        random.shuffle(targets)

        for idx, is_target in enumerate(targets):
            self.add_item(DuelButton(is_target, idx))


class DuelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="duel", description="Challenge another user to a Western fast-draw duel! 🤠")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def duel(self, interaction: discord.Interaction, opponent: discord.User):
        if opponent.bot:
            return await interaction.response.send_message("You cannot duel against a bot!", ephemeral=True)
        if opponent == interaction.user:
            return await interaction.response.send_message("You cannot duel against yourself!", ephemeral=True)

        embed = discord.Embed(
            title="🤠 Western Duel Starting!",
            description=f"⚔️ {interaction.user.mention} vs {opponent.mention}\n\n**Rules:**\n• When the bot says **'💥 DRAW!'**, 3 buttons will appear.\n• **2 Red 🔴, 1 Green 🟢** buttons will be shuffled.\n• The first one to hit the **GREEN** button wins, hitting red means instant defeat!",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

        await asyncio.sleep(random.randint(2, 5))

        view = DuelView(interaction.user, opponent)
        draw_embed = discord.Embed(
            title="💥 DRAW! SHOOT!",
            description=f"👉 {interaction.user.mention} & {opponent.mention}\n\nBe fast and click the **GREEN 🟢** button first!",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=draw_embed, view=view)


async def setup(bot):
    await bot.add_cog(DuelCog(bot))
