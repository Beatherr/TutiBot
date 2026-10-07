import time
from discord.ext import commands, tasks
from utils.storage import load_voice_data, save_voice_data
from discord import app_commands
import discord

# Hedef Sunucu ID'si
TARGET_GUILD_ID = 1521953028842721280

class VoiceTimeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = load_voice_data()
        self.save_task_handle = None

    async def cog_load(self) -> None:
        self.save_task_handle = self.save_task.start()

    def cog_unload(self) -> None:
        if self.save_task.is_running():
            self.save_task.cancel()
        self.save_data()

    def save_data(self) -> None:
        save_voice_data(self.data)

    def get_total_seconds(self, user_id: int) -> int:
        base = int(self.data["times"].get(str(user_id), 0))
        if str(user_id) in self.data["active"]:
            active = self.data["active"][str(user_id)]
            base += int(time.time() - active["joined_at"])
        return base

    def is_active(self, user_id: int) -> bool:
        return str(user_id) in self.data["active"]

    def format_duration(self, seconds: int) -> str:
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours} saat {minutes} dakika {sec} saniye"

    def register_join(self, member, channel) -> None:
        if member.bot:
            return
        self.data["active"][str(member.id)] = {
            "channel_id": channel.id,
            "joined_at": time.time(),
        }
        self.save_data()

    def register_leave(self, member) -> None:
        if member.bot:
            return
        user_id = str(member.id)
        active = self.data["active"].get(user_id)
        if not active:
            return
        elapsed = int(time.time() - active["joined_at"])
        self.data["times"][user_id] = int(self.data["times"].get(user_id, 0)) + elapsed
        self.data["active"].pop(user_id, None)
        self.save_data()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        current_voice_users = set()
        for guild in self.bot.guilds:
            for channel in guild.voice_channels:
                for member in channel.members:
                    if member.bot:
                        continue
                    current_voice_users.add(str(member.id))
                    if str(member.id) not in self.data["active"]:
                        self.data["active"][str(member.id)] = {
                            "channel_id": channel.id,
                            "joined_at": time.time(),
                        }

        stale_users = [user_id for user_id in self.data["active"] if user_id not in current_voice_users]
        for user_id in stale_users:
            self.data["active"].pop(user_id, None)

        self.save_data()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after) -> None:
        if member.bot:
            return
        before_channel = before.channel if before else None
        after_channel = after.channel if after else None

        if before_channel is None and after_channel is not None:
            self.register_join(member, after_channel)
            return

        if before_channel is not None and after_channel is None:
            self.register_leave(member)
            return

        if before_channel is not None and after_channel is not None and before_channel.id != after_channel.id:
            if str(member.id) not in self.data["active"]:
                self.register_join(member, after_channel)

    @tasks.loop(minutes=1)
    async def save_task(self) -> None:
        self.save_data()

    @save_task.before_loop
    async def before_save_task(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="ses-süresi",
        description="Bir kullanıcının Discord ses kanallarındaki toplam süresini gösterir."
    )
    @app_commands.describe(
        kullanıcı="Ses süresini görmek istediğin kullanıcı."
    )
    @app_commands.guilds(discord.Object(id=TARGET_GUILD_ID))
    async def ses_suresi(
        self,
        interaction: discord.Interaction,
        kullanıcı: discord.Member | None = None
    ):
        kullanıcı = kullanıcı or interaction.user

        user_id = str(kullanıcı.id)

        total_seconds = self.get_total_seconds(
            kullanıcı.id
        )

        active = self.data["active"].get(
            user_id
        )

        if active:
            current_session = int(
                time.time() - active["joined_at"]
            )
        else:
            current_session = 0

        total_seconds = max(
            0,
            total_seconds
        )

        current_session = max(
            0,
            current_session
        )

        hours, remainder = divmod(
            total_seconds,
            3600
        )

        minutes, seconds = divmod(
            remainder,
            60
        )

        if hours > 0:
            total_text = (
                f"**{hours} saat** "
                f"**{minutes} dakika** "
                f"**{seconds} saniye**"
            )
        elif minutes > 0:
            total_text = (
                f"**{minutes} dakika** "
                f"**{seconds} saniye**"
            )
        else:
            total_text = (
                f"**{seconds} saniye**"
            )

        if active:
            session_hours, session_remainder = divmod(
                current_session,
                3600
            )

            session_minutes, session_seconds = divmod(
                session_remainder,
                60
            )

            if session_hours > 0:
                session_text = (
                    f"{session_hours} saat "
                    f"{session_minutes} dakika "
                    f"{session_seconds} saniye"
                )
            elif session_minutes > 0:
                session_text = (
                    f"{session_minutes} dakika "
                    f"{session_seconds} saniye"
                )
            else:
                session_text = (
                    f"{session_seconds} saniye"
                )

            channel = self.bot.get_channel(
                active["channel_id"]
            )

            channel_text = (
                channel.mention
                if channel
                else "Bilinmeyen kanal"
            )

            status_text = (
                f"🟢 **Şu anda ses kanalında**\n"
                f"🎧 Kanal: {channel_text}\n"
                f"⏱️ Bu oturum: **{session_text}**"
            )

        else:
            status_text = (
                "⚫ **Şu anda ses kanalında değil.**"
            )

        embed = discord.Embed(
            title="🎙️ Ses Süresi",
            color=discord.Color.blurple()
        )

        if kullanıcı.avatar:
            embed.set_thumbnail(
                url=kullanıcı.avatar.url
            )

        embed.add_field(
            name="👤 Kullanıcı",
            value=kullanıcı.mention,
            inline=False
        )

        embed.add_field(
            name="⏱️ Toplam Ses Süresi",
            value=total_text,
            inline=False
        )

        embed.add_field(
            name="📡 Durum",
            value=status_text,
            inline=False
        )

        embed.set_footer(
            text=f"Kullanıcı ID: {kullanıcı.id}"
        )

        await interaction.response.send_message(
            embed=embed
        )

async def setup(bot):
    await bot.add_cog(VoiceTimeCog(bot))