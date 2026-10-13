import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class DuelRequestView(discord.ui.View):
    def __init__(self, challenger: discord.User, opponent: discord.User):
        super().__init__(timeout=30)
        self.challenger = challenger
        self.opponent = opponent
        self.accepted = False

    @discord.ui.button(label="Accept ⚔️", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            return await interaction.response.send_message("This duel request is not for you!", ephemeral=True)
        
        self.accepted = True
        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.description = f"⚔️ {self.opponent.mention} accepted the duel request from {self.challenger.mention}!\n\n**Get ready... The duel is about to begin!**"
        
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="Decline ❌", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            return await interaction.response.send_message("This duel request is not for you!", ephemeral=True)

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.description = f"❌ {self.opponent.mention} declined the duel request from {self.challenger.mention}."

        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        # Timeout durumunda mesajın güncellenmesi için try-except kullanılabilir


class DuelButton(discord.ui.Button):
    def __init__(self, is_target: bool, index: int):
        color = discord.ButtonStyle.danger if not is_target else discord.ButtonStyle.success
        label = "🎯 DRAW & SHOOT!" if is_target else "💥 TRAP!"
        super().__init__(style=color, label=label, row=0)
        self.is_target = is_target

    async def callback(self, interaction: discord.Interaction):
        view: DuelPlayView = self.view

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


class DuelPlayView(discord.ui.View):
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

        # 1. İstek Gönderme Aşaması
        request_embed = discord.Embed(
            title="🤠 Western Duel Request",
            description=f"⚔️ {interaction.user.mention} has challenged {opponent.mention} to a Western Duel!\n\n**{opponent.mention}**, please accept or decline the request using the buttons below.",
            color=discord.Color.gold()
        )
        
        view = DuelRequestView(interaction.user, opponent)
        await interaction.response.send_message(content=opponent.mention, embed=request_embed, view=view)

        # İstek yanıtını bekle (30 saniye)
        timed_out = not await view.wait()
        
        if timed_out and not view.accepted:
            try:
                await interaction.edit_original_response(content="⏱️ Duel request timed out.", view=None)
            except Exception:
                pass
            return

        if not view.accepted:
            return

        # 2. Hazırlık ve Bekleme Aşımı
        ready_embed = discord.Embed(
            title="🤠 Get Ready!",
            description=f"⚔️ **{interaction.user.mention} vs {opponent.mention}**\n\nGet ready... Hand on your holster! ⏳",
            color=discord.Color.orange()
        )
        await interaction.edit_original_response(content=None, embed=ready_embed, view=None)

        # 2 ile 5 saniye arası rastgele bekleme (Heyecan unsuru)
        await asyncio.sleep(random.randint(2, 5))

        # 3. Oyun Başlangıcı (Çek / Shoot)
        play_view = DuelPlayView(interaction.user, opponent)
        draw_embed = discord.Embed(
            title="💥 DRAW! SHOOT!",
            description=f"👉 {interaction.user.mention} & {opponent.mention}\n\nBe fast and click the **GREEN 🟢** button first!",
            color=discord.Color.green()
        )
        
        await interaction.edit_original_response(embed=draw_embed, view=play_view)


async def setup(bot):
    await bot.add_cog(DuelCog(bot))
