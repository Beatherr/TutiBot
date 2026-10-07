import discord
import random
import asyncio
from discord import app_commands
from discord.ext import commands

FOTOGRAF_LINK = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExbmsxaGZ0dDR1NTVwbXdqbmdhcmprOGo5ODkxaXVrdnA1bmtibTFmeCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/26uf2YTgF5upXUTm0/giphy.gif"

class SlotView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=120)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This slot spin doesn't belong to you!",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="🎰 Spin Slot", style=discord.ButtonStyle.success)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        bekleme_embed = discord.Embed(
            title="🎰 Slot Machine",
            description="[ ❓ | ❓ | ❓ ]\n\n*Spinning the reels...*",
            color=discord.Color.gold()
        )
        bekleme_embed.set_thumbnail(url=FOTOGRAF_LINK)

        await interaction.response.edit_message(embed=bekleme_embed, view=None)
        await asyncio.sleep(2)

        emojis = ["🍎", "🍋", "🍒", "🍇", "💎", "7️⃣"]
        slot1 = random.choice(emojis)
        slot2 = random.choice(emojis)
        slot3 = random.choice(emojis)

        reel_result = f"[ {slot1} | {slot2} | {slot3} ]"

        # Kazanan Koşulları
        if slot1 == slot2 == slot3:
            result_text = f"🔥 **JACKPOT!** You got 3 of a kind!\n\n{reel_result}"
            color = discord.Color.green()
        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            result_text = f"✨ **MINI WIN!** You got 2 matching symbols!\n\n{reel_result}"
            color = discord.Color.gold()
        else:
            result_text = f"❌ **No match!** Better luck next time.\n\n{reel_result}"
            color = discord.Color.red()

        embed = discord.Embed(
            title="🎰 Slot Machine Result",
            description=result_text,
            color=color
        )
        embed.set_thumbnail(url=FOTOGRAF_LINK)

        await interaction.edit_original_response(embed=embed, view=None)


class SlotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="slot",
        description="Try your luck at the slot machine!"
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def slot(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎰 Slot Machine",
            description="Click the button below to spin!",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=FOTOGRAF_LINK)

        view = SlotView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(SlotCog(bot))