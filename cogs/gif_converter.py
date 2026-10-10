import os
import asyncio
import random
import tempfile
import subprocess
import time
import re
import discord
from discord import app_commands
from discord.ext import commands
from concurrent.futures import ProcessPoolExecutor
from PIL import Image
from cogs.stats import increment_stat
from typing import Optional

DEFAULT_MAX_DURATION_SEC = 25 
TARGET_FPS = 20                
MAX_WIDTH = 512                
MAX_CONCURRENT_TASKS = 2       
USER_COOLDOWN_SEC = 6
MAX_GIF_NAME_LENGTH = 25
MAX_CLIP_DURATION_SEC = 25

FFMPEG_PATH = r"C:\ffmpeg\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
FFPROBE_PATH = r"C:\ffmpeg\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"

# Special temporary directory for GIF Converter.
GIF_TEMP_DIR = os.path.join(tempfile.gettempdir(), "TutiGIFConverter")
os.makedirs(GIF_TEMP_DIR, exist_ok=True)

async def remove_gif_temp_file(path, retries=3, delay=0.5):
    """Async retry mechanism for Windows file lock issues (WinError 32) without blocking the event loop."""
    if not path or not os.path.exists(path):
        return

    for _ in range(retries):
        try:
            await asyncio.to_thread(os.remove, path)
            break
        except PermissionError:
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"Failed to delete temporary file {path}: {e}")
            break

async def cleanup_gif_temp_files():
    """Cleans up all temporary GIF converter files left over from previous or failed operations."""
    try:
        os.makedirs(GIF_TEMP_DIR, exist_ok=True)
        for filename in os.listdir(GIF_TEMP_DIR):
            path = os.path.join(GIF_TEMP_DIR, filename)
            try:
                if os.path.isfile(path):
                    await remove_gif_temp_file(path)
            except Exception as e:
                print(f"Failed to delete temporary file {path}: {e}")
    except Exception as e:
        print(f"GIF temporary cleanup error: {e}")

def create_gif_temp_file(suffix: str):
    """Creates a temporary file with a unique name inside the temporary directory."""
    fd, path = tempfile.mkstemp(dir=GIF_TEMP_DIR, suffix=suffix)
    os.close(fd)
    return path

FEEDBACK_CHANNEL_ID = 1536188884558286908  
GIF_LOG_CHANNEL_ID = 1533546444189995008

GIF_NOTICE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gif_converter_notice.json")

def _load_gif_notice_data():
    try:
        if os.path.exists(GIF_NOTICE_FILE):
            import json
            with open(GIF_NOTICE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"Error loading GIF notice data: {e}")
    return {}

def _save_gif_notice_data(data):
    try:
        import json
        with open(GIF_NOTICE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving GIF notice data: {e}")

gif_notice_data = _load_gif_notice_data()

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm")

LOADING_TIPS = [
    "<a:stars_star:1533501961272561824> **You can name your gif!**",
    "<a:Electrical:1533502037663154216> **Info:** Discord upload limits adjust automatically based on server boosts and Nitro status.",
    "<a:video:1533502131598921978> **Your GIF will be ready to share in just a few seconds.**",
    "<a:tuti:1533502289824841959> **Bot Note:** Applying the most suitable resolution for smooth and high-quality GIFs.",
    "<a:tuti:1533502289824841959> **Add the app to your profile to use it in DMs or other servers!**",
    "<a:developer_bot:1533502486101364746> **We want your ideas! Please use the /feedback` command to share your thoughts.**"
]

def sanitize_gif_filename(name: Optional[str]) -> str:
    """Converts user-provided GIF name into a safe filename."""
    if not name or not name.strip():
        return "generated_gif.gif"
    name = os.path.basename(name.strip())
    if name.lower().endswith(".gif"):
        name = name[:-4]
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name).strip(" ._")
    if not name:
        return "generated_gif.gif"
    name = name[:MAX_GIF_NAME_LENGTH].rstrip(" ._")
    return f"{name or 'generated_gif'}.gif"

process_pool = ProcessPoolExecutor(max_workers=MAX_CONCURRENT_TASKS)

def get_max_upload_limit(guild: Optional[discord.Guild]) -> int:
    if guild is None:
        return 25
    limit_bytes = getattr(guild, "filesize_limit", 10485760)
    return int(limit_bytes / (1024 * 1024))

def make_progress_bar(pct: int, length: int = 10) -> str:
    filled = int(round((pct / 100.0) * length))
    return "█" * filled + "░" * (length - filled)

def get_video_duration(input_path: str) -> float:
    cmd = [
        FFPROBE_PATH, "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def standalone_conversion_task(
    input_path: str,
    output_path: str,
    max_width: int,
    target_fps: int,
    start_sec: Optional[float] = None,
    end_sec: Optional[float] = None,
):
    vf_filter = (
        f"fps={target_fps},scale={max_width}:-2:flags=lanczos,"
        "split[s0][s1];[s0]palettegen=stats_mode=diff[p];"
        "[s1][p]paletteuse=dither=bayer:bayer_scale=5"
    )

    cmd = [FFMPEG_PATH, "-y"]

    if start_sec is not None:
        cmd += ["-ss", f"{start_sec:.3f}"]

    cmd += ["-i", input_path]

    if start_sec is not None and end_sec is not None:
        cmd += ["-t", f"{max(end_sec - start_sec, 0.001):.3f}"]
    elif end_sec is not None:
        cmd += ["-t", f"{end_sec:.3f}"]

    cmd += [
        "-vf", vf_filter,
        "-gifflags", "+transdiff",
        output_path
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg Error: {result.stderr}")

class InviteBotView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Add Bot", url=url, style=discord.ButtonStyle.link))

class FeedbackModal(discord.ui.Modal, title="Suggestions & Feedback"):
    feedback_text = discord.ui.TextInput(
        label="What features would you like to see added?",
        style=discord.TextStyle.paragraph,
        placeholder="Example: Add GIF playback speed adjustment or video trimming feature...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(FEEDBACK_CHANNEL_ID)
        
        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(FEEDBACK_CHANNEL_ID)
            except Exception:
                channel = None

        if channel:
            embed = discord.Embed(
                title="💡 New Suggestion / Feedback",
                color=discord.Color.gold(),
                timestamp=interaction.created_at
            )
            embed.add_field(name="<:user:1533502574324351116> User", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
            embed.add_field(name="🆔 User ID", value=f"`{interaction.user.id}`", inline=True)
            
            location_info = f"Server: **{interaction.guild.name}**" if interaction.guild else "💬 **DM (Direct Message)**"
            embed.add_field(name="<:Blurple_Server:1533502657753387219> Sent From", value=location_info, inline=False)
            
            embed.add_field(name="📝 Message", value=self.feedback_text.value, inline=False)
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="Tuti Bot Feedback System")

            await channel.send(embed=embed)
            await interaction.response.send_message("<a:dm_done:1533498882150105149> **Your feedback has been delivered to the developer!** Thank you for your contribution.", ephemeral=True)
        else:
            await interaction.response.send_message("<a:REJECTEd:1533501824450170910> Feedback channel not found. Please notify the bot owner.", ephemeral=True)

class GifSafetyNoticeView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="I Understand", style=discord.ButtonStyle.success, emoji="✅")
    async def acknowledge(self, interaction: discord.Interaction, button: discord.ui.Button):
        gif_notice_data[str(interaction.user.id)] = True
        _save_gif_notice_data(gif_notice_data)

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            embed=self.cog._make_status_embed(
                "✅ GIF Converter Ready",
                "You can now use the **/makegif** command. Please adhere to Discord guidelines and only upload content you have permission to share.",
                discord.Color.green(),
            ),
            view=self,
        )

class GifConverterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
        self.queue_counter = 0
        self.user_cooldowns = {}

    @commands.Cog.listener()
    async def on_ready(self):
        """Cleans up leftover temporary GIF converter files when the bot starts."""
        await cleanup_gif_temp_files()

    def _check_user_cooldown(self, user_id: int) -> int:
        now = time.monotonic()
        last_used = self.user_cooldowns.get(user_id, 0.0)
        remaining = USER_COOLDOWN_SEC - (now - last_used)
        if remaining > 0:
            return int(remaining) + 1
        self.user_cooldowns[user_id] = now
        return 0

    def _get_invite_url(self) -> str:
        bot_id = self.bot.user.id if self.bot.user else self.bot.application_id
        return f"https://discord.com/oauth2/authorize?client_id={bot_id}&scope=applications.commands&integration_type=1"

    def _make_status_embed(self, title: str, description: str, color: discord.Color = discord.Color.blurple()) -> discord.Embed:
        invite_url = self._get_invite_url()
        full_desc = f"{description}\n\n<:discord_link:1533498995928993812> **[Add App]({invite_url})**"
        embed = discord.Embed(title=title, description=full_desc, color=color)
        embed.set_footer(text="Click 'Add App' button to create GIFs in servers or direct messages.")
        return embed

    async def _safe_status_edit(self, status_msg, *, embed=None, view=None):
        if not status_msg:
            return False

        try:
            kwargs = {}
            if embed is not None:
                kwargs["embed"] = embed
            if view is not None:
                kwargs["view"] = view

            await status_msg.edit(**kwargs)
            return True
        except discord.NotFound:
            return False
        except discord.HTTPException as e:
            print(f"Failed to edit GIF status message: {e}")
            return False
        except Exception as e:
            print(f"Unexpected GIF status edit error: {e}")
            return False

    async def _send_msg(self, destination, content=None, embed=None, file=None, view=None):
        kwargs = {}
        if content is not None:
            kwargs["content"] = content
        if embed is not None:
            kwargs["embed"] = embed
        if file is not None:
            kwargs["file"] = file
        if view is not None:
            kwargs["view"] = view

        try:
            if isinstance(destination, discord.Webhook):
                return await destination.send(**kwargs)
            if hasattr(destination, "send_message"):
                return await destination.send_message(**kwargs)
            if hasattr(destination, "send"):
                return await destination.send(**kwargs)
        except discord.HTTPException as e:
            if e.code == 20009:
                print("Discord rejected media (error 20009: explicit content).")
                return None
            raise

    def _has_acknowledged_notice(self, user_id: int) -> bool:
        return gif_notice_data.get(str(user_id), False) is True

    async def _send_safety_notice(self, destination):
        embed = discord.Embed(
            title="⚠️ GIF Converter Terms Notice",
            description=(
                "By using the GIF Converter, you acknowledge and agree that you are solely responsible "
                "for all content uploaded, processed, and generated, and that your usage complies with "
                "Discord guidelines and applicable laws."
            ),
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="Responsibility",
            value=(
                "You are responsible for the content you upload, process, and generate with this bot. "
                "Please use the bot in accordance with Discord Community Guidelines and applicable laws."
            ),
            inline=False,
        )
        embed.add_field(
            name="Continue",
            value="Click the **I Understand** button to proceed with using the converter.",
            inline=False,
        )
        embed.set_footer(text="This notice is shown only once per user.")
        return await self._send_msg(
            destination,
            embed=embed,
            view=GifSafetyNoticeView(self),
        )

    async def process_gif_conversion(
        self,
        destination,
        attachment: discord.Attachment,
        author: discord.User | discord.Member,
        guild: Optional[discord.Guild] = None,
        gif_name: Optional[str] = None,
        start_sec: Optional[float] = None,
        end_sec: Optional[float] = None
    ):
        if not self._has_acknowledged_notice(author.id):
            return await self._send_safety_notice(destination)

        cooldown_remaining = self._check_user_cooldown(author.id)
        if cooldown_remaining > 0:
            return await self._send_msg(destination, content=f"⏳ Please wait **{cooldown_remaining} seconds** before starting another GIF conversion.")

        output_filename_display = sanitize_gif_filename(gif_name)

        #### 1. UZANTI VE BOYUT KONTROLÜ
        attachment_name = attachment.filename.lower()
        if attachment_name.endswith(VIDEO_EXTENSIONS):
            is_video = True
        elif attachment_name.endswith(IMAGE_EXTENSIONS):
            is_video = False
        else:
            return await self._send_msg(destination, content="Please upload an **MP4/MOV/WEBM** video or a **PNG/JPEG/GIF** image.")

        file_size_mb = attachment.size / (1024 * 1024)
        if is_video and file_size_mb > 200:
            return await self._send_msg(destination, content=f"<a:REJECTEd:1533501824450170910> **Video Too Large!** ({file_size_mb:.2f} MB). Limit is 200 MB.")

        status_msg = await self._send_msg(
            destination,
            embed=self._make_status_embed("<a:time:1533499488478691609> Request Received", f"Queuing process... (Size: **{file_size_mb:.2f} MB**)", discord.Color.blurple())
        )

        #### 2. GEÇİCİ DOSYA OLUŞTURMA
        suffix = os.path.splitext(attachment_name)[1]
        input_filename = create_gif_temp_file(suffix)
        output_filename = create_gif_temp_file(".gif")

        try:
            await attachment.save(input_filename)

            #### 3. RESİM / GIF DÖNÜŞTÜRME
            if not is_video:
                await self._safe_status_edit(
                    status_msg,
                    embed=self._make_status_embed(
                        "🖼️ Converting Image / GIF",
                        "Converting to GIF format...",
                        discord.Color.blue()
                    )
                )
                
                def process_image():
                    with Image.open(input_filename) as img:
                        if img.format == "GIF":
                            img.save(output_filename, format="GIF", save_all=True, optimize=True)
                        elif img.mode not in ("RGB", "RGBA", "P", "L"):
                            converted_img = img.convert("RGB")
                            converted_img.save(output_filename, format="GIF", save_all=True)
                        else:
                            img.save(output_filename, format="GIF", save_all=True)

                await asyncio.to_thread(process_image)

                try:
                    increment_stat("total_gifs_converted", 1)
                except Exception as e:
                    print(f"Stat increment error: {e}")
                gif_size_mb = os.path.getsize(output_filename) / (1024 * 1024)

                sent_gif_message = await self._send_msg(
                    destination,
                    file=discord.File(
                        output_filename,
                        filename=output_filename_display
                    )
                )

                if sent_gif_message is None:
                    await self._safe_status_edit(
                        status_msg,
                        embed=self._make_status_embed(
                            "❌ Discord Rejected This GIF",
                            "Discord rejected this media for the recipient. Please try a different and suitable source file.",
                            discord.Color.red(),
                        )
                    )
                    return

                gif_url = None
                if sent_gif_message and hasattr(sent_gif_message, "attachments"):
                    if sent_gif_message.attachments:
                        gif_url = sent_gif_message.attachments[0].url

                await self._send_gif_log(
                    gif_path=output_filename,
                    author=author,
                    guild=guild,
                    gif_url=gif_url,
                    gif_name=output_filename_display
                )
                
                await self._safe_status_edit(
                    status_msg,
                    embed=self._make_status_embed(
                        "<a:dm_done:1533498882150105149> Conversion Complete", 
                        f"`[{make_progress_bar(100)}]` **100%**\n📦 Size: **{gif_size_mb:.2f} MB**", 
                        discord.Color.green()
                    )
                )
                return

            #### 4. VİDEO SÜRE VE KUYRUK KONTROLÜ
            loop = asyncio.get_running_loop()
            duration = await loop.run_in_executor(None, get_video_duration, input_filename)

            if start_sec is not None or end_sec is not None:
                start_value = 0.0 if start_sec is None else float(start_sec)
                end_value = duration if end_sec is None else float(end_sec)

                if start_value < 0 or end_value <= start_value:
                    await self._safe_status_edit(
                        status_msg,
                        embed=self._make_status_embed(
                            "❌ Invalid Time Range",
                            "**End time** must be greater than **start time**.",
                            discord.Color.red()
                        )
                    )
                    return

                if start_value >= duration:
                    await self._safe_status_edit(
                        status_msg,
                        embed=self._make_status_embed(
                            "❌ Invalid Start Time",
                            f"Start time must be before the end of the video (**{duration:.2f}s**).",
                            discord.Color.red()
                        )
                    )
                    return

                end_value = min(end_value, duration)

                if end_value - start_value > MAX_CLIP_DURATION_SEC:
                    await self._safe_status_edit(
                        status_msg,
                        embed=self._make_status_embed(
                            "❌ Clip Too Long",
                            f"The selected duration cannot exceed **{MAX_CLIP_DURATION_SEC} seconds**.",
                            discord.Color.red()
                        )
                    )
                    return

                start_sec = start_value
                end_sec = end_value
                duration = end_value - start_value

            if duration > DEFAULT_MAX_DURATION_SEC:
                await self._safe_status_edit(
                    status_msg,
                    embed=self._make_status_embed(
                        "<a:REJECTEd:1533501824450170910> Video Too Long", 
                        f"Maximum allowed duration is **{DEFAULT_MAX_DURATION_SEC} seconds**. (Your video: {int(duration)}s)", 
                        discord.Color.red()
                    )
                )
                return

            if self.semaphore.locked():
                self.queue_counter += 1
                await self._safe_status_edit(
                    status_msg,
                    embed=self._make_status_embed(
                        "<a:Stats:1533503186332160152> In Queue", 
                        f"Your position: **#{self.queue_counter}**\nPlease wait...", 
                        discord.Color.gold()
                    )
                )

            #### 5. ARKA PLAN GIF DÖNÜŞTÜRME & İLERLEME TAKİBİ
            async with self.semaphore:
                if self.queue_counter > 0:
                    self.queue_counter -= 1

                estimated_total_sec = max(int(duration * 0.8), 3)
                future = loop.run_in_executor(
                    process_pool,
                    standalone_conversion_task,
                    input_filename,
                    output_filename,
                    MAX_WIDTH,
                    TARGET_FPS,
                    start_sec,
                    end_sec
                )
                start_time, last_tip = loop.time(), ""

                while not future.done():
                    elapsed = int(loop.time() - start_time)
                    pct = min(int((elapsed / estimated_total_sec) * 90), 90)
                    remaining_sec = max(estimated_total_sec - elapsed, 1)
                    time_str = f"~{remaining_sec} seconds" if remaining_sec > 1 else "Almost done..."
                    
                    available_tips = [tip for tip in LOADING_TIPS if tip != last_tip]
                    if not available_tips:
                        available_tips = LOADING_TIPS

                    current_tip = random.choice(available_tips)
                    last_tip = current_tip

                    status_desc = (
                        f"<a:video:1533502131598921978> **Processing GIF...**\n\n`[{make_progress_bar(pct)}]` **{pct}% Complete**\n"
                        f"<a:clock:1533503414116552766> **Remaining Time:** {time_str}\n"
                        f"📐 **Quality:** {MAX_WIDTH}p/{TARGET_FPS}FPS | 📦 **Input:** {file_size_mb:.2f} MB\n\n{current_tip}"
                    )
                    
                    await self._safe_status_edit(
                        status_msg,
                        embed=self._make_status_embed("<a:settings:1533498892996317506> Converting", status_desc, discord.Color.blue())
                    )
                    await asyncio.sleep(2.0)

                await future

            #### 6. TESLİMAT VE ÇIKTI KONTROLÜ
            if not os.path.exists(output_filename):
                raise Exception("Failed to create output file.")

            gif_size_mb = os.path.getsize(output_filename) / (1024 * 1024)
            await self._safe_status_edit(
                status_msg,
                embed=self._make_status_embed(
                    "<a:rocket:1533501733831966750> Uploading", 
                    f"`[{make_progress_bar(98)}]` **98%**\n📦 GIF Size: {gif_size_mb:.2f} MB", 
                    discord.Color.gold()
                )
            )

            sent_gif_message = await self._send_msg(
                destination,
                file=discord.File(
                    output_filename,
                    filename=output_filename_display
                )
            )

            if sent_gif_message is None:
                await self._safe_status_edit(
                    status_msg,
                    embed=self._make_status_embed(
                        "❌ Discord Rejected This GIF",
                        "Discord rejected this media for the recipient. Please try a different and suitable source file.",
                        discord.Color.red(),
                    )
                )
                return

            gif_url = None
            if sent_gif_message and hasattr(sent_gif_message, "attachments"):
                if sent_gif_message.attachments:
                    gif_url = sent_gif_message.attachments[0].url

            await self._send_gif_log(
                gif_path=output_filename,
                author=author,
                guild=guild,
                gif_url=gif_url,
                gif_name=output_filename_display
            )
            try:
                increment_stat("total_gifs_converted", 1)
            except Exception as e:
                print(f"Stat increment error: {e}")
                
            await self._safe_status_edit(
                status_msg,
                embed=self._make_status_embed(
                    "<a:dm_done:1533498882150105149> Conversion Complete", 
                    f"`[{make_progress_bar(100)}]` **100%**\n📦 **GIF Size:** {gif_size_mb:.2f} MB", 
                    discord.Color.green()
                )
            )

        #### 7. HATA VE TEMİZLİK
        except discord.HTTPException as http_err:
            if http_err.status == 413 or http_err.code == 40005:
                await self._safe_status_edit(
                    status_msg,
                    embed=self._make_status_embed(
                        "<a:REJECTEd:1533501824450170910> Discord Upload Limit Exceeded",
                        f"GIF size is **{gif_size_mb:.2f} MB**, which exceeds Discord's file upload limit.",
                        discord.Color.red()
                    )
                )
                return

            if http_err.code == 10008:
                print("GIF status message no longer exists; continuing.")
                return

            raise http_err
        except Exception as err:
            print(f"[GIF CONVERSION ERROR] {author} ({author.id}): {err}")
            
            await self._safe_status_edit(
                status_msg,
                embed=self._make_status_embed(
                    "<a:REJECTEd:1533501824450170910> Error", 
                    "An unexpected error occurred during conversion. Please try again, or use the **/feedback** command if the issue persists.", 
                    discord.Color.red()
                )
            )
        finally:
            await remove_gif_temp_file(input_filename)
            await remove_gif_temp_file(output_filename)
            await cleanup_gif_temp_files()

    async def _send_gif_log(
        self,
        gif_path: str,
        author: discord.User | discord.Member,
        guild: Optional[discord.Guild] = None,
        gif_url: Optional[str] = None,
        gif_name: Optional[str] = None
    ):
        """Uploads a permanent copy to the GIF log channel and records its link."""
        channel = self.bot.get_channel(GIF_LOG_CHANNEL_ID)

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(GIF_LOG_CHANNEL_ID)
            except Exception as e:
                print(f"GIF log channel not found: {e}")
                return

        if channel is None:
            return

        try:
            gif_size_mb = os.path.getsize(gif_path) / (1024 * 1024)
        except Exception:
            gif_size_mb = 0

        if guild:
            location_info = (
                f"Server: **{guild.name}**\n"
                f"Server ID: `{guild.id}`"
            )
        else:
            location_info = "💬 **DM (Direct Message)**"

        permanent_gif_url = gif_url
        try:
            uploaded = await channel.send(
                file=discord.File(
                    gif_path,
                    filename=gif_name or "generated_gif.gif"
                )
            )
            if uploaded.attachments:
                permanent_gif_url = uploaded.attachments[0].url
        except discord.HTTPException as http_err:
            if http_err.status == 413 or http_err.code == 40005:
                pass
            else:
                print(f"HTTP Error while uploading GIF archive: {http_err}")
        except Exception as e:
            print(f"Failed to upload archive copy of GIF: {e}")

        embed = discord.Embed(
            title="🎬 New GIF Created",
            description="A user created a GIF.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 GIF Creator",
            value=f"{author.mention}\n`{author.name}`\nID: `{author.id}`",
            inline=False
        )
        embed.add_field(name="📍 Location", value=location_info, inline=False)
        embed.add_field(name="📦 GIF Size", value=f"`{gif_size_mb:.2f} MB`", inline=True)
        embed.add_field(
            name="🏷️ GIF Name",
            value=f"`{gif_name or 'generated_gif.gif'}`",
            inline=True
        )

        if permanent_gif_url:
            embed.add_field(
                name="🔗 Generated GIF",
                value=f"[View GIF]({permanent_gif_url})",
                inline=False
            )
        else:
            embed.add_field(
                name="⚠️ GIF Link",
                value="GIF was created but archive attachment link could not be retrieved.",
                inline=False
            )

        embed.set_thumbnail(url=author.display_avatar.url)
        embed.set_footer(text="GIF Creation Logging System")

        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"GIF log embed error: {e}")

    # ==================== COMMANDS ====================
    @app_commands.command(name="makegif", description="Converts your uploaded video or image/GIF into a high-quality GIF.")
    @app_commands.describe(
        file="MP4/MOV/WEBM video or PNG/JPEG/GIF file to convert into a GIF",
        name="Optional name for the generated GIF (without .gif)",
        start="Optional start time in seconds",
        end="Optional end time in seconds"
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def makegif_slash(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
        name: Optional[app_commands.Range[str, 1, 25]] = None,
        start: Optional[app_commands.Range[float, 0.0, 999999.0]] = None,
        end: Optional[app_commands.Range[float, 0.0, 999999.0]] = None
    ):
        try:
            await interaction.response.defer()
        except discord.NotFound:
            return

        if not self._has_acknowledged_notice(interaction.user.id):
            await interaction.followup.send(
                embed=discord.Embed(
                    title="⚠️ GIF Converter Terms Notice",
                    description=(
                        "By using the GIF Converter, you acknowledge and agree that you are "
                        "solely responsible for all content uploaded, processed, and generated, "
                        "and that your usage complies with Discord guidelines and applicable laws.\n\n"
                        "Click the **I Understand** button to proceed."
                    ),
                    color=discord.Color.orange(),
                ),
                view=GifSafetyNoticeView(self),
                ephemeral=True,
            )
            return

        await self.process_gif_conversion(
            interaction.followup,
            file,
            interaction.user,
            interaction.guild,
            gif_name=name,
            start_sec=start,
            end_sec=end
        )

    # --- FEEDBACK COMMANDS ---
    @app_commands.command(name="feedback", description="Send feature requests and feedback to the bot developer.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def feedback_slash(self, interaction: discord.Interaction):
        await interaction.response.send_modal(FeedbackModal())

async def setup(bot: commands.Bot):
    await bot.add_cog(GifConverterCog(bot))
