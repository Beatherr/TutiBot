import os
import json
import time
import discord
from discord import app_commands
from discord.ext import commands

# ============================================================
# CONFIG & PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "stats_data.json")

# ============================================================
# DATA MANAGEMENT
# ============================================================

def get_default_data():
    return {
        "total_commands_used": 0,
        "total_gifs_converted": 0,
        "users": []
    }

def load_stats_data():
    default_data = get_default_data()
    if not os.path.exists(DATA_FILE):
        save_stats_data(default_data)
        return default_data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in default_data.items():
                data.setdefault(k, v)
            return data
    except Exception as e:
        print(f"[STATS] Data load error: {e}")
        return default_data

def save_stats_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[STATS] Data save error: {e}")

def increment_stat(key: str, amount: int = 1):
    """GIF dönüştürme gibi özel komutlarında bu fonksiyonu çağırabilirsin."""
    data = load_stats_data()
    data[key] = data.get(key, 0) + amount
    save_stats_data(data)

# ============================================================
# HELPERS
# ============================================================

def format_uptime(seconds: int) -> str:
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m {seconds}s"

# ============================================================
# VIEW
# ============================================================

class StatsView(discord.ui.View):
    def __init__(self, cog, owner_id: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This panel can only be refreshed by the user who executed the command.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        start = time.perf_counter()
        embed = self.cog.create_stats_embed(interaction, response_start=start)
        await interaction.response.edit_message(embed=embed, view=self)

# ============================================================
# COG
# ============================================================

class BotStatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(self.bot, "start_time"):
            self.bot.start_time = time.time()

    # --------------------------------------------------------
    # AUTOMATIC COMMAND & USER TRACKER
    # --------------------------------------------------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:
            data = load_stats_data()
            
            # Komut sayısını artır
            data["total_commands_used"] = data.get("total_commands_used", 0) + 1
            
            # Benzersiz kullanıcı kontrolü
            users = data.setdefault("users", [])
            if interaction.user.id not in users:
                users.append(interaction.user.id)
            
            save_stats_data(data)

    # --------------------------------------------------------
    # EMBED CREATOR
    # --------------------------------------------------------
    def create_stats_embed(self, interaction: discord.Interaction, response_start=None):
        # Fresh Data Read
        stats = load_stats_data()

        # Metrics
        latency = round(self.bot.latency * 1000)
        response_ms = round((time.perf_counter() - response_start) * 1000) if response_start else 0
        uptime = format_uptime(int(time.time() - getattr(self.bot, "start_time", time.time())))

        # System Health Indicator
        health_icon = "🟢" if latency < 200 else "🟡" if latency < 400 else "🔴"

        embed = discord.Embed(
            title="🤖 Tuti Stats",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="⚡ Performance",
            value=(
                f"{health_icon} **Ping:** `{latency} ms`\n"
                f"📨 **Response:** `{response_ms} ms`\n"
                f"⏱️ **Uptime:** `{uptime}`"
            ),
            inline=True
        )

        embed.add_field(
            name="🌐 Discord",
            value=(
                f"🏠 **Servers:** `{len(self.bot.guilds):,}`\n"
                f"👥 **User Installations:** `{len(stats.get('users', [])):,}`"
            ),
            inline=True
        )

        embed.add_field(
            name="📊 Kullanım İstatistikleri",
            value=(
                f"⚡ **Commands Used:** `{stats.get('total_commands_used', 0):,}`\n"
                f"🎬 **GIFs Converted:** `{stats.get('total_gifs_converted', 0):,}`"
            ),
            inline=False
        )

        embed.set_footer(text="Tuti Bot • Statistics")

        if self.bot.user and self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        return embed

    # --------------------------------------------------------
    # SLASH COMMAND
    # --------------------------------------------------------
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.command(name="stats", description="Show bot status and statistics 📊")
    async def stats(self, interaction: discord.Interaction):
        start = time.perf_counter()
        embed = self.create_stats_embed(interaction, response_start=start)
        view = StatsView(self, interaction.user.id)
        
        await interaction.response.send_message(embed=embed, view=view)

# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(BotStatsCog(bot))