import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

# ------------------------------------------------------------------
# BOT INVITE LINK / APP BUTTON CONFIGURATION
# ------------------------------------------------------------------
BOT_INVITE_URL = "https://discord.com/oauth2/authorize?client_id=1530455235141701773&scope=applications.commands&integration_type=1"

# ------------------------------------------------------------------
# CATEGORY DATA & COMMAND DESCRIPTIONS
# ------------------------------------------------------------------
CATEGORIES = {
    "main_menu": {
        "label": "Main Menu",
        "description": "General bot information and category overview",
        "emoji": "📌"
    },
    "interaction": {
        "label": "Interaction Commands",
        "description": "Social and fun interaction commands",
        "emoji": "<a:HEART_HEART:1533502384918237244>",
        "commands": [
            ("interaction_stats", "View interaction statistics for a user"),
            ("waifu", "Show a random waifu image"),
            ("neko", "Show a random cat girl image"),
            ("hug", "Give someone a hug"),
            ("kiss", "Kiss someone"),
            ("slap", "Slap someone"),
            ("pat", "Pat someone on the head"),
            ("cuddle", "Cuddle with someone"),
            ("bite", "Bite someone"),
            ("wave", "Wave at someone"),
            ("smile", "Smile at someone"),
            ("blush", "Blush in front of someone"),
            ("cry", "Cry in front of someone"),
            ("highfive", "Give someone a high five"),
            ("handhold", "Hold hands with someone"),
            ("kick", "Kick someone"),
            ("wink", "Wink at someone"),
            ("poke", "Poke someone"),
            ("dance", "Dance with someone"),
            ("pout", "Make a pouty face"),
            ("stare", "Stare at someone"),
            ("tickle", "Tickle someone"),
            ("punch", "Punch someone"),
            ("angry", "Express your anger"),
            ("baka", "Call someone a baka"),
            ("bleh", "Stick your tongue out"),
            ("blowkiss", "Blow a kiss to someone"),
            ("bonk", "Bonk someone on the head"),
            ("bored", "Show that you are bored"),
            ("carry", "Carry someone in your arms"),
            ("clap", "Clap for someone"),
            ("confused", "Show your confusion"),
            ("facepalm", "Do a facepalm"),
            ("feed", "Feed someone"),
            ("handshake", "Shake hands with someone"),
            ("happy", "Show your happiness"),
            ("kabedon", "Kabedon someone"),
            ("lappillow", "Give someone a lap pillow"),
            ("nod", "Nod your head in agreement"),
            ("nom", "Eat or snack on something"),
            ("nope", "Shake your head no"),
            ("nya", "Say nya like a cat"),
            ("run", "Run away"),
            ("salute", "Salute someone"),
            ("shake", "Shake someone"),
            ("shocked", "Act shocked"),
            ("shoot", "Shoot at someone"),
            ("shrug", "Shrug your shoulders"),
            ("sip", "Take a sip of your drink"),
            ("laugh", "Laugh at someone"),
            ("sleep", "Fall asleep"),
            ("smug", "Show a smug grin"),
            ("tableflip", "Flip a table"),
            ("think", "Deep in thought"),
            ("thumbsup", "Give a thumbs up"),
            ("yawn", "Yawn wide"),
            ("yeet", "Yeet someone away"),
            ("kitsune", "Show a random fox girl image")
        ]
    },
    "fun": {
        "label": "Fun & Games",
        "description": "Mini-games and casual fun tools",
        "emoji": "<a:tuti:1533502289824841959>",
        "commands": [
            ("coinflip", "Flip a coin"),
            ("achievement", "Generate a custom Minecraft achievement banner"),
            ("ship", "Measure love compatibility between two users"),
            ("8ball", "Ask the magic 8-ball a question"),
            ("mc", "Ask the Minecraft AI a question"),
            ("dice", "Roll a dice"),
            ("slot", "Play a game of slots")
        ]
    },
    "gif_feedback": {
        "label": "Media & GIF",
        "description": "GIF creation and media utilities",
        "emoji": "<a:stars_star:1533501961272561824>",
        "commands": [
            ("makegif", "Convert a video or image into GIF format")
        ]
    },
    "bot_commands": {
        "label": "Bot & System",
        "description": "System status and general bot information",
        "emoji": "<a:settings:1533498892996317506>",
        "commands": [
            ("stats", "Display real-time bot statistics"),
            ("feedback", "Send feedback to the developer")
        ]
    }
}


# ------------------------------------------------------------------
# UI COMPONENTS
# ------------------------------------------------------------------
class CategorySelect(discord.ui.Select):
    def __init__(self, cog, current_category: str):
        self.cog = cog
        options = []
        for cat_key, cat_data in CATEGORIES.items():
            options.append(
                discord.SelectOption(
                    label=cat_data["label"],
                    value=cat_key,
                    description=cat_data["description"],
                    emoji=cat_data["emoji"],
                    default=(cat_key == current_category)
                )
            )
        super().__init__(
            placeholder="📌 Select a category...",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        selected_category = self.values[0]
        view = MenuView(self.cog, selected_category, current_page=0)
        embed = self.cog.build_menu_embed(selected_category, current_page=0, interaction=interaction)
        await interaction.response.edit_message(embed=embed, view=view)


class MenuView(discord.ui.View):
    def __init__(self, cog, current_category: str = "main_menu", current_page: int = 0, page_size: int = 6):
        super().__init__(timeout=180)

        self.cog = cog
        self.current_category = current_category
        self.current_page = current_page
        self.page_size = page_size

        # Dropdown Menu (Row 0)
        self.add_item(CategorySelect(cog, current_category))

        commands_list = CATEGORIES.get(current_category, {}).get("commands", [])
        total_pages = (len(commands_list) - 1) // page_size + 1 if commands_list else 1

        is_main = (current_category == "main_menu")

        # --- BUTTONS (Row 1) ---
        prev_btn = discord.ui.Button(
            emoji="◀️", 
            style=discord.ButtonStyle.primary if not is_main else discord.ButtonStyle.secondary, 
            disabled=(current_page == 0 or is_main), 
            row=1
        )
        prev_btn.callback = self.prev_page
        self.add_item(prev_btn)

        page_indicator = discord.ui.Button(
            label=f"{current_page + 1}/{total_pages}" if not is_main else "🏠",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            row=1
        )
        self.add_item(page_indicator)

        next_btn = discord.ui.Button(
            emoji="▶️", 
            style=discord.ButtonStyle.primary if not is_main else discord.ButtonStyle.secondary, 
            disabled=(current_page >= total_pages - 1 or is_main), 
            row=1
        )
        next_btn.callback = self.next_page
        self.add_item(next_btn)

        # Mavi "Add App" Butonu
        invite_url = BOT_INVITE_URL
        
        add_app_btn = discord.ui.Button(
            label="Add App",
            style=discord.ButtonStyle.link,
            url=invite_url,
            emoji="<:discord_link:1533498995928993812>",
            row=1
        )
        self.add_item(add_app_btn)

        close_btn = discord.ui.Button(
            emoji="🗑️", 
            style=discord.ButtonStyle.danger, 
            row=1
        )
        close_btn.callback = self.close_menu
        self.add_item(close_btn)

    async def prev_page(self, interaction: discord.Interaction):
        self.current_page -= 1
        view = MenuView(self.cog, self.current_category, self.current_page, self.page_size)
        embed = self.cog.build_menu_embed(self.current_category, self.current_page, interaction=interaction, page_size=self.page_size)
        await interaction.response.edit_message(embed=embed, view=view)

    async def next_page(self, interaction: discord.Interaction):
        self.current_page += 1
        view = MenuView(self.cog, self.current_category, self.current_page, self.page_size)
        embed = self.cog.build_menu_embed(self.current_category, self.current_page, interaction=interaction, page_size=self.page_size)
        await interaction.response.edit_message(embed=embed, view=view)

    async def close_menu(self, interaction: discord.Interaction):
        try:
            # 1. Discord'a buton etkileşiminin alındığını bildir (zaman aşımını önler)
            await interaction.response.defer()
            # 2. Mesajı sil
            await interaction.delete_original_response()
        except Exception:
            try:
                # Alternatif olarak mesaj nesnesi üzerinden silmeyi dene
                await interaction.message.delete()
            except Exception:
                pass


# ------------------------------------------------------------------
# COG DEFINITION
# ------------------------------------------------------------------
class MenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cmd_cache = {}

    def get_cmd_mention(self, cmd_name: str) -> str:
        """Fetches registered command ID to build clickable </command:id> mentions."""
        if not self.cmd_cache and self.bot.tree:
            for cmd in self.bot.tree.get_commands():
                cmd_id = getattr(cmd, "id", None)
                if cmd_id:
                    self.cmd_cache[cmd.name] = cmd_id

        cmd_id = self.cmd_cache.get(cmd_name, 0)
        return f"</{cmd_name}:{cmd_id}>"

    def build_progress_bar(self, current: int, total: int) -> str:
        """Generates a visual progress bar for menu pagination."""
        if total <= 1:
            return ""
        bar_length = 10
        progress = int((current / total) * bar_length)
        return "▪" * progress + "▫" * (bar_length - progress)

    def build_menu_embed(self, category_key: str, current_page: int = 0, interaction: discord.Interaction = None, page_size: int = 6) -> discord.Embed:
        cat_data = CATEGORIES[category_key]
        
        embed = discord.Embed(color=discord.Color.from_rgb(114, 137, 218))

        invite_url = BOT_INVITE_URL

        if category_key == "main_menu":
            embed.title = "<a:stars_star:1533501961272561824> **Command Guide & Help Menu**"
            embed.description = (
                f"Select a category from the dropdown menu below to explore available commands.\n"
                f"👉 [**Add Tuti Bot to your Profile**]({invite_url})\n\n"
                "📂 **Available Categories:**\n"
            )

            for key, data in CATEGORIES.items():
                if key == "main_menu":
                    continue
                cmd_count = len(data.get("commands", []))
                embed.description += f"> {data['emoji']} **{data['label']}** — `{cmd_count} Commands`\n> └ *{data['description']}*\n\n"

            embed.set_thumbnail(url=self.bot.user.display_avatar.url if self.bot.user else None)
        else:
            commands_list = cat_data.get("commands", [])
            total_commands = len(commands_list)
            total_pages = (total_commands - 1) // page_size + 1 if total_commands else 1

            start_idx = current_page * page_size
            end_idx = start_idx + page_size
            page_commands = commands_list[start_idx:end_idx]

            formatted_cmds = []
            for name, desc in page_commands:
                mention = self.get_cmd_mention(name)
                formatted_cmds.append(f"> {mention}\n> ↳ *{desc}*")

            body_text = "\n\n".join(formatted_cmds)
            progress_bar = self.build_progress_bar(current_page + 1, total_pages)

            embed.title = f"{cat_data['emoji']} {cat_data['label']}"
            embed.description = (
                f"*{cat_data['description']}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{body_text}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**Page:** `{current_page + 1}/{total_pages}` {progress_bar}"
            )

        user_avatar = interaction.user.display_avatar.url if interaction else None
        user_name = interaction.user.display_name if interaction else "User"
        
        embed.set_footer(
            text=f"Requested by {user_name} • Tuti Bot",
            icon_url=user_avatar
        )
        return embed

    @app_commands.command(name="menu", description="Displays all available bot commands and categories.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def help_cmd(self, interaction: discord.Interaction):
        initial_category = "main_menu"
        embed = self.build_menu_embed(initial_category, interaction=interaction)
        view = MenuView(self, initial_category)

        await interaction.response.send_message(
            embed=embed,
            view=view
        )


async def setup(bot):
    await bot.add_cog(MenuCog(bot))