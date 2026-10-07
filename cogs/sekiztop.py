import discord
from discord import app_commands
from discord.ext import commands
import random

class SekizTopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question! 🔮")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        responses = [
            # --- Orijinal 20 Resmi Cevap ---
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful.",
            "Absolutely.", "100% yes.", "The stars align for yes.", 
            "You can count on it.", "The answer is a clear yes.", "Undeniably so.",
            "The future is unclear.", "Check back tomorrow.", "Ask the universe again.", 
            "Hard to say right now.", "The signs are mixed.", "Too close to call.",
            "No way.", "Not a chance.", "Highly unlikely.", 
            "The stars say no.", "Forget about it.", "Absolutely not.",
            "In your dreams.", "No, and don't ask again."
        ]
        
        answer = random.choice(responses)
        
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            color=discord.Color.blue()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=answer, inline=False)
        embed.set_footer(text=f"Asked by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(SekizTopCog(bot))