import discord
import random
from discord import app_commands
import asyncio
from discord.ext import commands


FOTOGRAF_LINK = "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExbG1wY3JpanFwa2RkdnN3Y2F4ejk1YW5vdXA0d2dleGx2bWRjZ3VociZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/r9JXEbkaOo12vl9P1I/giphy.gif"


class CoinFlipView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=120)
        self.user_id = user_id


    async def interaction_check(self, interaction: discord.Interaction):

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This coin flip doesn't belong to you!",
                ephemeral=True
            )
            return False

        return True


    @discord.ui.button(
        label="🟡 Heads",
        style=discord.ButtonStyle.primary
    )
    async def yazi(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.coin_at(
            interaction,
            "Heads"
        )


    @discord.ui.button(
        label="⚪ Tails",
        style=discord.ButtonStyle.secondary
    )
    async def tura(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.coin_at(
            interaction,
            "Tails"
        )

    async def coin_at(
        self,
        interaction: discord.Interaction,
        secim
    ):

        bekleme_embed = discord.Embed(
            title="<a:coinflip:1533924996827713687> Coin Flip",
            description="<a:CoinFlip1:1533925133402505399> Flipping the coin...",
            color=discord.Color.gold()
        )

        bekleme_embed.set_thumbnail(
            url=FOTOGRAF_LINK
        )

        await interaction.response.edit_message(
            embed=bekleme_embed,
            view=None
        )


        await asyncio.sleep(2)


        sonuc = random.choice(
            [
                "Heads",
                "Tails"
            ]
        )


        embed = discord.Embed(
            title="<a:coinflip:1533924996827713687> Coin Flip Result",
            color=discord.Color.green()
        )

        embed.set_thumbnail(
            url=FOTOGRAF_LINK
        )


        embed.add_field(
            name="Your choice",
            value=f"**{secim}**",
            inline=True
        )


        embed.add_field(
            name="Result",
            value=f"**{sonuc}**",
            inline=True
        )


        if secim == sonuc:
            embed.description = "<a:Electrical:1533502037663154216> **You won!**"
        else:
            embed.description = "<a:REJECTEd:1533501824450170910> **You lost!**"


        await interaction.edit_original_response(
            embed=embed,
            view=None
        )



class YaziTuraCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(
        name="coinflip",
        description="Play a coin flip game. Test your luck!"
    )
    @app_commands.allowed_contexts(
        guilds=True,
        dms=True,
        private_channels=True
    )
    @app_commands.allowed_installs(
        guilds=True,
        users=True
    )
    async def coinflip(
        self,
        interaction: discord.Interaction
    ):


        embed = discord.Embed(
            title="<a:coinflip:1533924996827713687> Coin Flip",
            description="Heads or Tails? Pick one!",
            color=discord.Color.blurple()
        )


        embed.set_thumbnail(
            url=FOTOGRAF_LINK
        )


        view = CoinFlipView(
            interaction.user.id
        )


        await interaction.response.send_message(
            embed=embed,
            view=view
        )



async def setup(bot: commands.Bot):

    await bot.add_cog(
        YaziTuraCog(bot)
    )