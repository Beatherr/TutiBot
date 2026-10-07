import discord
from discord.ext import commands
from discord import app_commands
import urllib.parse

class AchievementCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Context Menu (Apps / Right-Click Menu) Definition
        self.ctx_menu = app_commands.ContextMenu(
            name="Make Achievement",
            callback=self.achievement_context_menu,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        # Removes the Context Menu from the app tree when the Cog unloads
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    def generate_achievement_url(self, text: str, icon_id: int = 1) -> str:
        """Generates a Minecraft achievement banner image URL via public API."""
        encoded_text = urllib.parse.quote(text)
        return f"https://api.alexflipnote.dev/achievement?text={encoded_text}&icon={icon_id}"

    # 1. Slash Command
    @app_commands.command(name="achievement", description="Generates a custom Minecraft achievement banner.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.describe(text="The text to display on the achievement", icon="Icon ID (1-45, default: 1)")
    async def achievement_slash(
        self,
        interaction: discord.Interaction,
        text: str,
        icon: int = 1
    ):
        try:
            await interaction.response.defer()

        except discord.NotFound:
            print("Achievement interaction expired before defer().")
            return

        except discord.HTTPException as e:
            print(f"Achievement defer failed: {e}")
            return

        image_url = self.generate_achievement_url(text, icon)

        embed = discord.Embed(color=discord.Color.green())
        embed.set_image(url=image_url)
        embed.set_footer(
            text=f"Requested by: {interaction.user.display_name}"
        )

        try:
            await interaction.followup.send(embed=embed)

        except discord.NotFound:
            print("Achievement interaction expired before followup.")
        except discord.HTTPException as e:
            print(f"Achievement followup failed: {e}")

    # 2. Context Menu Callback (Right-click on a message)
    async def achievement_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        if not message.content:
            await interaction.response.send_message("This message does not contain any text!", ephemeral=True)
            return

        await interaction.response.defer()
        
        # Limit text length to 50 characters to prevent layout overflow
        text = message.content[:50]
        image_url = self.generate_achievement_url(text)

        embed = discord.Embed(
            title="Achievement Unlocked!",
            color=discord.Color.gold()
        )
        embed.set_image(url=image_url)
        embed.set_footer(text=f"Original message by: {message.author.display_name}")

        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(AchievementCog(bot))