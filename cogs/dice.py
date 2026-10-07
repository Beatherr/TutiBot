import discord
import random
import asyncio
from discord import app_commands
from discord.ext import commands

# --- ZAR ATMA BUTONLARI VE MANTIĞI ---
class ZarAtView(discord.ui.View):
    def __init__(self, author: discord.User | discord.Member, timeout=60):
        super().__init__(timeout=timeout)
        self.author = author  # Komutu başlatan kullanıcıyı saklıyoruz

    @discord.ui.button(label="Roll Dice!", style=discord.ButtonStyle.primary, emoji="🎲")
    async def zar_at_buton(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Güvenlik Kontrolü: Butona basan kişi komutu başlatan kişi mi?
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "❌ Bu zarı sadece komutu yazan kişi atabilir! Kendi zarını atmak için `/dice` yazabilirsin.",
                ephemeral=True
            )
            return

        # 1. Bekleme Embed'i
        bekleme_embed = discord.Embed(
            title="🎲 Dice Game",
            description="Dice is rolling...",
            color=discord.Color.gold()
        )
        
        # Butona tıklandığı an mesajı güncelle
        await interaction.response.edit_message(embed=bekleme_embed, view=None)
        
        # 2 Saniye efekt simülasyonu
        await asyncio.sleep(2)
        
        # 2. Sonuç Embed'i
        sonuc = random.randint(1, 6)
        sonuc_embed = discord.Embed(
            title="🎲 Dice Result",
            description=f"**{interaction.user.display_name}**, rolled a **{sonuc}**!",
            color=discord.Color.green()
        )
        
        # Orijinal mesajı sonuçla güncelle
        await interaction.edit_original_response(embed=sonuc_embed, view=None)


# --- COG TANIMI ---
class DiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Loglama fonksiyonu (DM güvenliği mevcut)
    async def dice_log(self, interaction: discord.Interaction):
        nerede = f"Sunucu: {interaction.guild.name}" if interaction.guild else "DM / Özel Mesaj"
        print(f"[LOG] {interaction.user} ({interaction.user.id}) '/dice' komutunu kullandı. ({nerede})")

    @app_commands.command(
        name="dice",
        description="Roll the dice and see what you get!"
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
    async def dice(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎲 Dice Game",
            description="Click the button below to roll the dice!",
            color=discord.Color.blurple()
        )
        view = ZarAtView(author=interaction.user)

        await interaction.response.send_message(
            embed=embed,
            view=view
        )

        # Loglama çağrısı
        await self.dice_log(interaction)

async def setup(bot: commands.Bot):
    await bot.add_cog(DiceCog(bot))