import discord
from discord import app_commands
from discord.ext import commands
import random

CARD_NAMES = {1: "A (1)", 11: "J (11)", 12: "Q (12)", 13: "K (13)"}

def get_card_name(val: int) -> str:
    return CARD_NAMES.get(val, str(val))

class HigherLowerView(discord.ui.View):
    def __init__(self, player: discord.User):
        super().__init__(timeout=60)
        self.player = player
        self.current_card = random.randint(1, 13)
        self.score = 0

    @discord.ui.button(label="Higher 📈", style=discord.ButtonStyle.success)
    async def higher(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_guess(interaction, guess="higher")

    @discord.ui.button(label="Lower 📉", style=discord.ButtonStyle.danger)
    async def lower(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_guess(interaction, guess="lower")

    async def process_guess(self, interaction: discord.Interaction, guess: str):
        if interaction.user != self.player:
            return await interaction.response.send_message("This is not your game!", ephemeral=True)

        next_card = random.randint(1, 13)
        while next_card == self.current_card:
            next_card = random.randint(1, 13)

        is_correct = (guess == "higher" and next_card > self.current_card) or \
                     (guess == "lower" and next_card < self.current_card)

        if is_correct:
            self.score += 1
            prev_card_str = get_card_name(self.current_card)
            self.current_card = next_card
            next_card_str = get_card_name(self.current_card)

            embed = discord.Embed(
                title="🃏 Higher or Lower",
                description=f"✅ **Correct Guess!**\n\nPrevious Card: `{prev_card_str}` ➔ New Card: **`{next_card_str}`**\n\nWill the next card be higher or lower?",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Player: {self.player.display_name} • Current Score: {self.score}")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            prev_card_str = get_card_name(self.current_card)
            next_card_str = get_card_name(next_card)

            for child in self.children:
                child.disabled = True

            embed = discord.Embed(
                title="💥 Wrong Guess - Game Over!",
                description=f"❌ You lost!\n\nCurrent Card: `{prev_card_str}` ➔ Drawn Card: **`{next_card_str}`**\n\n**Total Score:** `{self.score}`",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Player: {self.player.display_name}")
            await interaction.response.edit_message(embed=embed, view=self)

class HigherLowerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="higherlower", description="Predict if the next card will be higher or lower! 🃏")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def higherlower(self, interaction: discord.Interaction):
        view = HigherLowerView(interaction.user)
        card_str = get_card_name(view.current_card)

        embed = discord.Embed(
            title="🃏 Higher or Lower",
            description=f"Your First Card: **`{card_str}`**\n\nWill the next card be **HIGHER** or **LOWER**?",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Player: {interaction.user.display_name} • Score: 0")
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(HigherLowerCog(bot))
