import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

class MemeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="meme", description="Get a random internet meme! 🖼️")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def meme(self, interaction: discord.Interaction):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://meme-api.com/gimme") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title=data.get("title"), url=data.get("postLink"), color=discord.Color.orange())
                    embed.set_image(url=data.get("url"))
                    embed.set_footer(text=f"Subreddit: r/{data.get('subreddit')} • Requested by {interaction.user.display_name}")
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("Could not fetch a meme right now, try again later!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MemeCog(bot))
