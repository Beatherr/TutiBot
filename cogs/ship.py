import io
import random
import re
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# Helper: GMT+3 timezone generator
def get_gmt3_time() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=3)

# Helper: Fetch anime action GIFs dynamically
async def get_anime_gif(action: str) -> str:
    url = f"https://api.waifu.pics/sfw/{action}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=3) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("url", "")
    except Exception:
        pass
    return "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3h6c2xudjN6M3h6/26vhFscyF7bY7F5tC/giphy.gif"

# Helper: Generate custom avatar card with Pillow
async def generate_ship_card(user1: discord.User, user2: discord.User, compatibility: int) -> io.BytesIO:
    canvas_width, canvas_height = 650, 260
    background_color = (18, 19, 23)
    
    card = Image.new("RGBA", (canvas_width, canvas_height), background_color)
    draw = ImageDraw.Draw(card)

    async with aiohttp.ClientSession() as session:
        async with session.get(user1.display_avatar.with_format("png").url) as resp1:
            avatar1_bytes = await resp1.read()
        async with session.get(user2.display_avatar.with_format("png").url) as resp2:
            avatar2_bytes = await resp2.read()

    av1 = Image.open(io.BytesIO(avatar1_bytes)).convert("RGBA").resize((160, 160))
    av2 = Image.open(io.BytesIO(avatar2_bytes)).convert("RGBA").resize((160, 160))

    def make_circular(img):
        mask = Image.new("L", img.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, img.size[0], img.size[1]), fill=255)
        img.putalpha(mask)
        return img

    av1 = make_circular(av1)
    av2 = make_circular(av2)

    # Avatar Glow / Border
    draw.ellipse((35, 45, 205, 215), fill=None, outline=(255, 105, 180, 180), width=4)
    draw.ellipse((445, 45, 615, 215), fill=None, outline=(255, 105, 180, 180), width=4)

    card.paste(av1, (40, 50), av1)
    card.paste(av2, (450, 50), av2)

    # Center Box for Match Percentage
    heart_box = [245, 80, 405, 180]
    draw.rounded_rectangle(heart_box, radius=22, fill=(28, 30, 36), outline=(255, 64, 129), width=3)

    try:
        font_large = ImageFont.truetype("arial.ttf", 38)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    text_score = f"%{compatibility}"
    draw.text((325, 115), text_score, fill=(255, 255, 255), font=font_large, anchor="mm")
    draw.text((325, 155), "LOVE MATCH", fill=(255, 105, 180), font=font_small, anchor="mm")

    buffer = io.BytesIO()
    card.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


class ShipCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ship", description="Measures love compatibility between two users ❤️")
    @app_commands.describe(
        user1="The first user",
        user2="The second user (defaults to you if left empty)"
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def ship(
        self, 
        interaction: discord.Interaction, 
        user1: discord.User, 
        user2: discord.User = None
    ):
        if user2 is None:
            user2 = interaction.user

        if user1.id == user2.id:
            return await interaction.response.send_message(
                "💞 Shipping yourself is completely valid, but the result is always: **100% Ultimate Self-Love**!",
                ephemeral=True
            )

        await interaction.response.defer()

        now_tr = get_gmt3_time()
        
        # Consistent daily seed based on sorted IDs and current date
        uid_a, uid_b = sorted([int(user1.id), int(user2.id)])
        today_key = now_tr.strftime("%Y%m%d")
        rng = random.Random(f"{uid_a}-{uid_b}-{today_key}")

        compatibility = rng.randint(0, 100)
        filled_hearts = max(1, round(compatibility / 10))
        progress_bar = ("💖" * filled_hearts) + ("🖤" * (10 - filled_hearts))

        tiers = [
            {
                "min": 90,
                "title": "Cosmic Soulmates",
                "comment": "The energy between you two is magnetic! You seamlessly complement each other's strengths and weaknesses. A true power couple status 💍",
                "action": "kiss",
                "color": discord.Color.from_rgb(255, 64, 129),
                "badge": "Eternal Flame 🔥",
                "date_ideas": [
                    "Rooftop stargazing with hot cocoa",
                    "A surprise weekend getaway trip",
                    "Candlelight dinner at a high-end restaurant",
                    "Couples spa day & relaxation session"
                ],
                "activities": [
                    "Baking a complex dessert recipe together",
                    "Co-op gaming marathon in hard mode",
                    "Planning a dream vacation wishlist"
                ],
                "tips": [
                    "Keep the spontaneity alive with small surprise notes.",
                    "Celebrate each other's small victories every day."
                ],
                "dynamics": ["The Inseparable Duo", "Masterminds in Love", "Main Characters"]
            },
            {
                "min": 75,
                "title": "High Chemistry",
                "comment": "Incredible spark and effortless communication! You both bounce off each other's energy with ease ✨",
                "action": "cuddle",
                "color": discord.Color.from_rgb(255, 105, 180),
                "badge": "Sweet Chaos 💕",
                "date_ideas": [
                    "Late-night city drive with a shared playlist",
                    "Visiting a cozy local coffee shop & bookstore",
                    "Sunset picnic at a nearby park",
                    "Attending a live music concert or indie gig"
                ],
                "activities": [
                    "Creating a joint music playlist",
                    "Trying out a new board game together",
                    "Exploring an escape room challenge"
                ],
                "tips": [
                    "Take time for deep 1-on-1 conversations without distractions.",
                    "Try new hobbies together to keep things fresh."
                ],
                "dynamics": ["Partner in Crime", "Dynamic Duo", "Flirty Teammates"]
            },
            {
                "min": 55,
                "title": "Sweet Potential",
                "comment": "There is a warm and genuine spark here. With open communication, this connection can turn into something truly special 🌸",
                "action": "hug",
                "color": discord.Color.from_rgb(236, 72, 153),
                "badge": "Growing Strong 📈",
                "date_ideas": [
                    "Casual movie night with favorite snacks",
                    "Visiting an art gallery or local museum",
                    "Ice cream walk on a sunny afternoon",
                    "Trying out a new street food market"
                ],
                "activities": [
                    "Streaming a new TV series together",
                    "Playing casual online party games",
                    "Comparing childhood memories & stories"
                ],
                "tips": [
                    "Don't rush things—let the natural bond develop organically.",
                    "Show appreciation for the small thoughtful gestures."
                ],
                "dynamics": ["Cute Companions", "Slow-Burn Romance", "Comforting Duo"]
            },
            {
                "min": 35,
                "title": "Slow Burn Connection",
                "comment": "Building a solid foundation of friendship first will work wonders here. Take your time getting to know each other 🙂",
                "action": "handhold",
                "color": discord.Color.from_rgb(219, 39, 119),
                "badge": "Warming Up ☕",
                "date_ideas": [
                    "Casual multiplayer gaming session",
                    "Grabbing quick boba tea or coffee",
                    "Brisk evening walk while chatting",
                    "Group hangout with mutual friends"
                ],
                "activities": [
                    "Sharing favorite memes and videos",
                    "Working on study or project goals together",
                    "Trivia quiz competition"
                ],
                "tips": [
                    "Focus on finding common interests and shared values.",
                    "Be patient and let comfort build over time."
                ],
                "dynamics": ["Friendly Banter", "Steady Comrades", "Work in Progress"]
            },
            {
                "min": 0,
                "title": "Opposites Attract",
                "comment": "You have very different vibes, which might require extra patience. However, your differences can lead to surprising growth! 😬",
                "action": "pat",
                "color": discord.Color.from_rgb(190, 24, 93),
                "badge": "Patience Mode ⏳",
                "date_ideas": [
                    "Casual voice chat while relaxing",
                    "Friendly 1v1 game match to test skills",
                    "Trying an activity outside both comfort zones"
                ],
                "activities": [
                    "Teaching each other about a personal passion",
                    "Watching a random movie selection",
                    "Friendly debate on lighthearted topics"
                ],
                "tips": [
                    "Embrace your differences instead of trying to change them.",
                    "Keep expectations open and focus on mutual respect."
                ],
                "dynamics": ["Chaos & Order", "Unpredictable Pair", "Unexpected Alliance"]
            },
        ]

        tier = next(item for item in tiers if compatibility >= item["min"])

        # Select random suggestions tailored to current compatibility level
        selected_date = rng.choice(tier["date_ideas"])
        selected_activity = rng.choice(tier["activities"])
        selected_tip = rng.choice(tier["tips"])
        selected_dynamic = rng.choice(tier["dynamics"])

        # Generate custom Ship Name
        clean_name1 = re.sub(r"[^A-Za-z0-9]", "", user1.display_name)[:6]
        clean_name2 = re.sub(r"[^A-Za-z0-9]", "", user2.display_name)[:6]
        
        n1_part = clean_name1[:3] if len(clean_name1) >= 3 else clean_name1
        n2_part = clean_name2[-3:] if len(clean_name2) >= 3 else clean_name2
        ship_name = (n1_part + n2_part).strip().capitalize() or "LoveLink"

        aura = rng.choice([
            "Lavender Bliss", "Rose Gold Sparkle", "Neon Cyberpunk", 
            "Pastel Dreams", "Midnight Velvet", "Moonlight Radiance",
            "Golden Hour", "Cosmic Stardust"
        ])
        
        romantic_rating = min(5, max(1, (compatibility // 20) + 1))
        romantic_bar = "🌹" * romantic_rating + "•" * (5 - romantic_rating)
        
        match_emoji = "💞" if compatibility >= 90 else "💘" if compatibility >= 70 else "💓" if compatibility >= 50 else "💗" if compatibility >= 30 else "💔"
        
        date_str = now_tr.strftime("%B %d, %Y")
        next_refresh = (now_tr + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        next_refresh_ts = int(next_refresh.timestamp())

        # Generate Pillow Canvas Card and Fetch Action GIF
        image_buffer = await generate_ship_card(user1, user2, compatibility)
        card_file = discord.File(fp=image_buffer, filename="ship_card.png")
        gif_url = await get_anime_gif(tier["action"])

        embed = discord.Embed(
            title="💘 Love Compatibility Analysis",
            description=(
                f"{user1.mention} × {user2.mention}\n"
                f"**Match Score:** `{compatibility}%` {match_emoji}\n"
                f"{progress_bar}"
            ),
            color=tier["color"],
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(name="🧬 Ship Name", value=f"`{ship_name}`", inline=True)
        embed.add_field(name="🎨 Vibe Aura", value=f"`{aura}`", inline=True)
        embed.add_field(name="📅 Analysis Date", value=f"`{date_str}`", inline=True)
        embed.add_field(name="💎 Compatibility Tier", value=f"`{tier['title']}`", inline=True)
        embed.add_field(name="🏷️ Status Badge", value=f"`{tier['badge']}`", inline=True)
        embed.add_field(name="🎭 Dynamic Archetype", value=f"`{selected_dynamic}`", inline=True)
        embed.add_field(name="🌹 Romantic Meter", value=f"`{romantic_bar}`", inline=False)
        
        embed.add_field(
            name="📝 Compatibility Assessment", 
            value=tier["comment"], 
            inline=False
        )
        embed.add_field(
            name="🎯 Today's Recommended Date", 
            value=f"• **{selected_date}**", 
            inline=False
        )
        embed.add_field(
            name="🎮 Suggested Shared Activity", 
            value=f"• **{selected_activity}**", 
            inline=False
        )
        embed.add_field(
            name="💡 Relationship Advice", 
            value=f"• *{selected_tip}*", 
            inline=False
        )
        embed.add_field(
            name="⏳ Next Daily Refresh",
            value=f"<t:{next_refresh_ts}:F> (<t:{next_refresh_ts}:R>)",
            inline=False
        )

        embed.set_image(url="attachment://ship_card.png")
        
        if gif_url:
            embed.set_thumbnail(url=gif_url)

        embed.set_footer(text="Results refresh daily at midnight GMT+3 • Use /ship anytime!")

        await interaction.followup.send(file=card_file, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ShipCog(bot))