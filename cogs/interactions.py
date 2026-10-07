import discord
import aiohttp
import asyncio
import json
import os
from discord import app_commands
from discord.ext import commands
from typing import Optional
from collections import deque

# Configuration
ANIME_LEVEL_REQUIRED = 20
ANIME_ACTIONS = {"waifu", "neko"}
WEEBSH_API_BASE = "https://api.weeb.sh/images"
WEEBSH_FALLBACK_GIF = "https://media.tenor.com/ioRj0_a0bDMAAAAC/anime-cry.gif"
WEEBSH_SESSION: Optional[aiohttp.ClientSession] = None
WEEBSH_TYPES_CACHE = {"sfw": set(), "fetched_at": 0}
WAIFUPICS_SFW_FALLBACK = "https://api.waifu.pics/sfw"
NEKOSBEST_API_BASE = "https://nekos.best/api/v2"
NEKOSBEST_HEADERS = {"User-Agent": "Tuti-Bot/1.0 (Discord interaction commands)"}
IMAGE_URL_EXTENSIONS = (".gif", ".png", ".jpg", ".jpeg", ".webp")

# waifu.pics tarafından desteklenen SFW kategorileri
WAIFUPICS_SUPPORTED = {
    "bite", "bully", "cuddle", "cry", "hug", "awoo", "kiss", "lick", "pat",
    "smug", "bonk", "yeet", "blush", "smile", "wave", "highfive", "handhold",
    "nom", "bite", "glump", "slap", "kill", "kick", "happy", "wink", "poke",
    "dance", "cringe", "waifu", "neko"
}

# waifu.pics'te doğrudan bulunmayan kategoriler için alias eşleştirme
ACTION_ALIASES_FOR_WAIFU = {
    "feed": "nom",
    "stare": "smile",
    "think": "blush",
    "sleep": "cuddle",
    "pout": "blush",
    "tickle": "pat",
    "punch": "slap",
    "angry": "bully",
    "baka": "cringe",
    "bleh": "smile",
    "blowkiss": "kiss",
    "bored": "cringe",
    "carry": "hug",
    "clap": "dance",
    "confused": "cringe",
    "facepalm": "cringe",
    "handshake": "wave",
    "kabedon": "hug",
    "lappillow": "cuddle",
    "nod": "smile",
    "nope": "cringe",
    "nya": "neko",
    "run": "dance",
    "salute": "wave",
    "shake": "slap",
    "shocked": "cringe",
    "shoot": "yeet",
    "shrug": "smile",
    "sip": "nom",
    "tableflip": "kill",
    "thumbsup": "smile",
    "yawn": "cuddle",
    "kitsune": "neko"
}

# Dosyanın tam olarak botun ana dizininde (main.py'nin yanında) oluşmasını sağlar
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATS_FILE = os.path.join(BASE_DIR, "interaction_stats.json")

NEKOSBEST_ACTION_ALIASES = {
    "angry": "angry",
    "laugh": "laugh",
    "baka": "baka",
    "bite": "bite",
    "bleh": "bleh",
    "blowkiss": "blowkiss",
    "blush": "blush",
    "bonk": "bonk",
    "bored": "bored",
    "carry": "carry",
    "clap": "clap",
    "confused": "confused",
    "cry": "cry",
    "cuddle": "cuddle",
    "dance": "dance",
    "facepalm": "facepalm",
    "feed": "feed",
    "handhold": "handhold",
    "handshake": "handshake",
    "happy": "happy",
    "highfive": "highfive",
    "hug": "hug",
    "kabedon": "kabedon",
    "kick": "kick",
    "kiss": "kiss",
    "lappillow": "lappillow",
    "neko": "neko",
    "nod": "nod",
    "nom": "nom",
    "nope": "nope",
    "nya": "nya",
    "pat": "pat",
    "poke": "poke",
    "pout": "pout",
    "punch": "punch",
    "run": "run",
    "salute": "salute",
    "shake": "shake",
    "shocked": "shocked",
    "shoot": "shoot",
    "shrug": "shrug",
    "sip": "sip",
    "slap": "slap",
    "sleep": "sleep",
    "smile": "smile",
    "smug": "smug",
    "stare": "stare",
    "tableflip": "tableflip",
    "think": "think",
    "thumbsup": "thumbsup",
    "tickle": "tickle",
    "waifu": "waifu",
    "wave": "wave",
    "wink": "wink",
    "yawn": "yawn",
    "yeet": "yeet",
    "kitsune": "kitsune",
}




recent_gifs = deque(maxlen=20)


# ------------------------------------------------------------------
# İSTATİSTİK YÖNETİM FONKSİYONLARI (JSON)
# ------------------------------------------------------------------
def load_stats() -> dict:
    if not os.path.exists(STATS_FILE):
        return {}

    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        print(f"Stats load error: {e}")

    return {}


def save_stats(data: dict):
    try:
        temp_file = STATS_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(temp_file, STATS_FILE)
    except Exception as e:
        print(f"Stats save error: {e}")


def init_user_data(stats: dict, user_id: str) -> dict:
    if user_id not in stats or not isinstance(stats[user_id], dict):
        stats[user_id] = {
            "sent": 0,
            "received": 0,
            "likes_received": 0
        }
    else:
        stats[user_id].setdefault("sent", 0)
        stats[user_id].setdefault("received", 0)
        stats[user_id].setdefault("likes_received", 0)
    return stats


def update_interaction_count(actor_id: int, target_id: int):
    """Gönderenin 'sent', alanın 'received' sayısını artırır."""
    stats = load_stats()

    str_actor = str(actor_id)
    str_target = str(target_id)

    stats = init_user_data(stats, str_actor)
    stats = init_user_data(stats, str_target)

    stats[str_actor]["sent"] += 1
    stats[str_target]["received"] += 1

    save_stats(stats)


def update_likes_received(target_id: int, increment: int):
    """Sadece etkileşimin hedefi olan kullanıcının aldığı kalp sayısını günceller."""
    stats = load_stats()
    str_target = str(target_id)

    stats = init_user_data(stats, str_target)

    stats[str_target]["likes_received"] += increment

    if stats[str_target]["likes_received"] < 0:
        stats[str_target]["likes_received"] = 0

    save_stats(stats)


class InteractionCounterView(discord.ui.View):
    """View for interaction counter buttons"""
    def __init__(self, actor_user_id: int, target_user_id: int, action_type: str, actor_mention: str, target_mention: str):
        super().__init__(timeout=None)
        self.actor_user_id = actor_user_id
        self.target_user_id = target_user_id
        self.action_type = action_type
        self.actor_mention = actor_mention
        self.target_mention = target_mention
        self.count = 0
        self.voters = set()

    @discord.ui.button(label="❤️ 0", style=discord.ButtonStyle.red)
    async def counter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user_id = interaction.user.id

            if user_id in self.voters:
                self.voters.remove(user_id)
                self.count -= 1
                update_likes_received(self.actor_user_id, -1)
                update_likes_received(self.target_user_id, -1)
            else:
                self.voters.add(user_id)
                self.count += 1
                update_likes_received(self.actor_user_id, 1)
                update_likes_received(self.target_user_id, 1)

            button.label = f"❤️ {self.count}"

            # Edit via interaction response
            await interaction.response.edit_message(view=self)

        except Exception as e:
            print(f"Counter button error: {e}")


async def get_weebsh_session() -> aiohttp.ClientSession:
    global WEEBSH_SESSION
    if WEEBSH_SESSION is None or WEEBSH_SESSION.closed:
        WEEBSH_SESSION = aiohttp.ClientSession()
    return WEEBSH_SESSION


async def fetch_nekosbest_url(
    session: aiohttp.ClientSession,
    category: str,
) -> Optional[str]:
    try:
        url = f"{NEKOSBEST_API_BASE}/{category}"
        async with session.get(url, headers=NEKOSBEST_HEADERS, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("results", [])
                if results:
                    return results[0].get("url") or results[0].get("image_url")
    except Exception as e:
        print(f"Error fetching from nekos.best: {e}")
    
    return None


def remember_gif(url: Optional[str]) -> Optional[str]:
    if url:
        recent_gifs.append(url)
    return url


async def fetch_waifupics_url(session: aiohttp.ClientSession, category: str) -> Optional[str]:
    """nekos.best yanıt vermezse veya kategori yoksa waifu.pics üzerinden GIF çeker."""
    target_category = category
    if target_category not in WAIFUPICS_SUPPORTED:
        target_category = ACTION_ALIASES_FOR_WAIFU.get(category)
    
    if not target_category or target_category not in WAIFUPICS_SUPPORTED:
        return None

    try:
        url = f"https://api.waifu.pics/sfw/{target_category}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("url")
    except Exception:
        pass
    return None


async def get_anime_gif(action: str) -> str:
    try:
        session = await get_weebsh_session()
        
        # 1. Öncelik: nekos.best
        if action in NEKOSBEST_ACTION_ALIASES:
            url = await fetch_nekosbest_url(session, action)
            if url:
                return remember_gif(url)
        
        # 2. Öncelik: waifu.pics (Kategori Dönüştürme Destekli)
        waifu_url = await fetch_waifupics_url(session, action)
        if waifu_url:
            return remember_gif(waifu_url)

        # 3. Son Çare: Çalışan Yedek GIF
        return WEEBSH_FALLBACK_GIF
    except Exception as e:
        print(f"Error getting anime gif: {e}")
        return WEEBSH_FALLBACK_GIF


class InteractionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def etkilesim_motoru(
        self,
        interaction: discord.Interaction,
        kullanici: discord.User,
        tur: str,
        mesaj: str,
        renk: discord.Color,
        actor_user=None,
        allow_counter_view=True,
        note_text: Optional[str] = None,
    ):
        """Main interaction engine"""
        if not actor_user:
            actor_user = interaction.user
        
        # Kendine etkileşim engeli
        if kullanici.id == actor_user.id:
            msg = "You can't apply this interaction to yourself! 😅"
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        # Etkileşim istatistiğini kaydet (Sent/Received)
        update_interaction_count(actor_user.id, kullanici.id)

        # GIF al
        gif_url = await get_anime_gif(tur)
        
        # Format mesajı
        final_mesaj = mesaj.format(user=actor_user.mention, target=kullanici.mention)
        
        embed_description = f"<a:NEKO_NEKO_NEKO:1534367520927256806> **{final_mesaj}**"
        if note_text:
            embed_description += f"\n\n💬 {note_text}"

        embed = discord.Embed(
            description=embed_description,
            color=renk
        )
        embed.set_image(url=gif_url)
        
        user_avatar = actor_user.avatar.url if actor_user.avatar else actor_user.default_avatar.url
        embed.set_footer(text=f"Requested by {actor_user.display_name}", icon_url=user_avatar)
        
        view = None
        if allow_counter_view:
            view = InteractionCounterView(
                actor_user.id,
                kullanici.id,
                tur,
                actor_user.mention,
                kullanici.mention
            )
        
        await interaction.edit_original_response(embed=embed, view=view)

    @app_commands.command(name="interaction_stats", description="View interaction analytics for a user 📊")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def interaction_stats(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        target = user or interaction.user
        stats = load_stats()
        user_data = stats.get(str(target.id), {"sent": 0, "received": 0, "likes_received": 0})

        sent = user_data.get("sent", 0)
        received = user_data.get("received", 0)
        likes_received = user_data.get("likes_received", 0)

        # Toplam etkileşime (Sent + Received) göre kalp oranını hesaplar
        total_interactions = sent + received
        heart_ratio = (likes_received / total_interactions * 100) if total_interactions > 0 else 0.0

        embed = discord.Embed(
            title=f"📊 Interaction Profile — {target.display_name}",
            description=f"Detailed statistics overview for {target.mention}",
            color=discord.Color.blurple()
        )
        avatar_url = target.avatar.url if target.avatar else target.default_avatar.url
        embed.set_thumbnail(url=avatar_url)

        embed.add_field(
            name="📤 Interactions Sent",
            value=f"```yaml\n{sent} times\n```",
            inline=True
        )
        embed.add_field(
            name="📥 Interactions Received",
            value=f"```yaml\n{received} times\n```",
            inline=True
        )
        embed.add_field(
            name="💖 Total Hearts Received",
            value=f"```yaml\n{likes_received} ❤️\n```",
            inline=False
        )
        embed.add_field(
            name="📈 Popularity Rate",
            value=f"```ansi\n\x1b[32m{heart_ratio:.1f}%\x1b[0m heart ratio\n```",
            inline=False
        )

        embed.set_footer(text="Tuti Bot • Interaction Tracker", icon_url=self.bot.user.display_avatar.url if self.bot.user else None)
        await interaction.response.send_message(embed=embed)

    # Interaction commands
    @app_commands.command(name="waifu", description="Show a waifu 😍")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def waifu(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "waifu", "{user} showed an amazing waifu energy to {target}! 😍", discord.Color.pink()
        )

    @app_commands.command(name="neko", description="Show a cat girl 🐱")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def neko(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "neko", "{user} brought a cat girl to {target}! Meow~ 🐱", discord.Color.pink()
        )

    @app_commands.command(name="kitsune", description="Show a fox girl 🦊")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def kitsune(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "kitsune", "{user} showed a cute kitsune to {target}! 🦊", discord.Color.pink()
        )

    @app_commands.command(name="kabedon", description="Show a kabedon 🪶")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def kabedon(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "kabedon", "{user} showed a cute kabedon to {target}! 🪶", discord.Color.pink()
        )

    @app_commands.command(name="hug", description="Give someone a hug 🤗")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def hug(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "hug", "{user} gave {target} a tight hug! 🤗", discord.Color.blue()
        )

    @app_commands.command(name="kiss", description="Kiss someone 💋")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def kiss(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "kiss", "{user} kissed {target} romantically 💋", discord.Color.red()
        )

    @app_commands.command(name="slap", description="Slap someone 🖐️")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def slap(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "slap", "{user} gave {target} a hard slap! 🖐️", discord.Color.yellow()
        )

    @app_commands.command(name="pat", description="Pat someone 🫳")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def pat(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "pat", "{user} gently patted {target}'s head 😚", discord.Color.green()
        )

    @app_commands.command(name="cuddle", description="Cuddle with someone 🫂")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def cuddle(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "cuddle", "{user} cuddled {target} lovingly 🫂", discord.Color.light_grey()
        )

    @app_commands.command(name="bite", description="Bite someone 🦷")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def bite(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "bite", "{user} gently bit {target}'s arm! 🦷", discord.Color.dark_red()
        )

    @app_commands.command(name="wave", description="Wave at someone 👋")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def wave(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "wave", "{user} waved at {target} from afar 👋", discord.Color.gold()
        )

    @app_commands.command(name="smile", description="Smile at someone 😊")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def smile(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "smile", "{user} smiled warmly at {target} 😊", discord.Color.teal()
        )

    @app_commands.command(name="blush", description="Blush in front of someone 😳")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def blush(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "blush", "{user} turned bright red in front of {target}! 😳", discord.Color.magenta()
        )

    @app_commands.command(name="cry", description="Cry in front of someone 😭")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def cry(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "cry", "{user} cried in front of {target}... 😭", discord.Color.dark_blue()
        )

    @app_commands.command(name="highfive", description="Give a high five 👋")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def highfive(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "highfive", "{user} and {target} gave an amazing high five! 👋", discord.Color.brand_green()
        )

    @app_commands.command(name="handhold", description="Hold hands 🤝")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def handhold(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "handhold", "{user} held {target}'s hand... So romantic! 🤝", discord.Color.fuchsia()
        )

    @app_commands.command(name="kick", description="Kick someone 🦶")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def kick(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "kick", "{user} kicked {target}! 🦶", discord.Color.dark_grey()
        )

    @app_commands.command(name="wink", description="Wink at someone 😉")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def wink(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "wink", "{user} secretly winked at {target} 😉", discord.Color.dark_magenta()
        )

    @app_commands.command(name="poke", description="Poke someone 👉")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def poke(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "poke", "{user} went and poked {target} with a finger 👉", discord.Color.light_embed()
        )

    @app_commands.command(name="dance", description="Dance with someone 💃")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def dance(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "dance", "{user} and {target} are dancing on the floor! 💃", discord.Color.random()
        )

    @app_commands.command(name="pout", description="Make a pouty face 😋")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def pout(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "pout", "{user} made a pouty face at {target}! 😋", discord.Color.pink()
        )

    @app_commands.command(name="stare", description="Stare at someone 👀")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def stare(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "stare", "{user} stared intensely at {target}! 👀", discord.Color.greyple()
        )

    @app_commands.command(name="tickle", description="Tickle someone 😆")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def tickle(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "tickle", "{user} tickled {target}! 😆", discord.Color.lighter_grey()
        )

    @app_commands.command(name="punch", description="Punch someone 👊")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def punch(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "punch", "{user} punched {target}! 👊", discord.Color.darker_grey()
        )

    # Additional nekos.best SFW categories added as interaction commands
    @app_commands.command(name="angry", description="Express anger 😡")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def angry(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "angry", "{user} got angry at {target}! 😡", discord.Color.red()
        )

    @app_commands.command(name="baka", description="Call someone a baka 🤪")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def baka(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "baka", "{user} called {target} a baka! 🤪", discord.Color.orange()
        )

    @app_commands.command(name="bleh", description="Stick tongue out 😛")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def bleh(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "bleh", "{user} stuck their tongue out at {target}! 😛", discord.Color.purple()
        )

    @app_commands.command(name="blowkiss", description="Blow a kiss 💋")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def blowkiss(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "blowkiss", "{user} blew a kiss to {target}! 💋", discord.Color.magenta()
        )

    @app_commands.command(name="bonk", description="Bonk someone 🔨")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def bonk(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "bonk", "{user} bonked {target}! 🔨", discord.Color.dark_orange()
        )

    @app_commands.command(name="bored", description="Show boredom 🥱")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def bored(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "bored", "{user} is bored with {target}... 🥱", discord.Color.dark_grey()
        )

    @app_commands.command(name="carry", description="Carry someone 🏋️")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def carry(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "carry", "{user} carried {target}! 🏋️", discord.Color.blue()
        )

    @app_commands.command(name="clap", description="Clap for someone 👏")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def clap(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "clap", "{user} clapped for {target}! 👏", discord.Color.gold()
        )

    @app_commands.command(name="confused", description="Look confused 😕")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def confused(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "confused", "{user} looked at {target} confusedly... 😕", discord.Color.light_grey()
        )

    @app_commands.command(name="facepalm", description="Facepalm 🤦")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def facepalm(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "facepalm", "{user} facepalmed because of {target}! 🤦", discord.Color.dark_grey()
        )

    @app_commands.command(name="feed", description="Feed someone 🍧")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def feed(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "feed", "{user} fed {target}! 🍧", discord.Color.green()
        )

    @app_commands.command(name="handshake", description="Shake hands 🤝")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def handshake(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "handshake", "{user} shook hands with {target}! 🤝", discord.Color.blue()
        )

    @app_commands.command(name="happy", description="Be happy 😊")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def happy(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "happy", "{user} is super happy around {target}! 😊", discord.Color.gold()
        )

    @app_commands.command(name="lappillow", description="Give a lap pillow 🛌")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def lappillow(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "lappillow", "{user} gave {target} a lap pillow! 🛌", discord.Color.pink()
        )

    @app_commands.command(name="nod", description="Nod head 🙂")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def nod(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "nod", "{user} nodded at {target}! 🙂", discord.Color.green()
        )

    @app_commands.command(name="nom", description="Nom nom 😋")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def nom(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "nom", "{user} is nomming next to {target}! 😋", discord.Color.teal()
        )

    @app_commands.command(name="nope", description="Say nope 🙅")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def nope(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "nope", "{user} said nope to {target}! 🙅", discord.Color.red()
        )

    @app_commands.command(name="nya", description="Say nya 🐱")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def nya(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "nya", "{user} went Nya~ at {target}! 🐱", discord.Color.pink()
        )

    @app_commands.command(name="run", description="Run away 🏃")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def run(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "run", "{user} ran away from {target}! 🏃", discord.Color.dark_teal()
        )

    @app_commands.command(name="salute", description="Salute someone 🫡")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def salute(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "salute", "{user} saluted {target}! 🫡", discord.Color.gold()
        )

    @app_commands.command(name="shake", description="Shake someone 🫨")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def shake(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "shake", "{user} shook {target}! 🫨", discord.Color.dark_orange()
        )

    @app_commands.command(name="shocked", description="Be shocked 😱")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def shocked(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "shocked", "{user} was shocked by {target}! 😱", discord.Color.yellow()
        )

    @app_commands.command(name="shoot", description="Shoot someone 🔫")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def shoot(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "shoot", "{user} shot finger guns at {target}! 🔫", discord.Color.dark_red()
        )

    @app_commands.command(name="shrug", description="Shrug 🤷")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def shrug(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "shrug", "{user} shrugged at {target}! 🤷", discord.Color.greyple()
        )

    @app_commands.command(name="sip", description="Sip tea/coffee ☕")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def sip(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "sip", "{user} took a sip while looking at {target}... ☕", discord.Color.dark_teal()
        )

    @app_commands.command(name="sleep", description="Sleep 😴")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def sleep(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "sleep", "{user} fell asleep next to {target}... 😴", discord.Color.blue()
        )

    @app_commands.command(name="smug", description="Be smug 😏")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def smug(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "smug", "{user} acted smug towards {target}! 😏", discord.Color.magenta()
        )

    @app_commands.command(name="tableflip", description="Flip a table ┬─┬ノ( º _ ºノ)")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def tableflip(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "tableflip", "{user} flipped a table at {target}! ┬─┬ノ( º _ ºノ)", discord.Color.red()
        )

    @app_commands.command(name="think", description="Think 💭")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def think(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "think", "{user} is thinking deeply about {target}... 💭", discord.Color.blurple()
        )

    @app_commands.command(name="thumbsup", description="Give thumbs up 👍")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def thumbsup(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "thumbsup", "{user} gave a thumbs up to {target}! 👍", discord.Color.green()
        )

    @app_commands.command(name="yawn", description="Yawn 🥱")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def yawn(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "yawn", "{user} yawned near {target}... 🥱", discord.Color.light_grey()
        )
    @app_commands.command(name="laugh", description="Laugh at someone 😂")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def laugh(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction,
            user,
            "laugh",
            "{user} laughed with {target}! 😂",
            discord.Color.gold()
        )

    @app_commands.command(name="yeet", description="Yeet someone 🚀")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def yeet(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.etkilesim_motoru(
            interaction, user, "yeet", "{user} yeeted {target} into orbit! 🚀", discord.Color.dark_red()
        )


async def setup(bot):
    await bot.add_cog(InteractionsCog(bot))