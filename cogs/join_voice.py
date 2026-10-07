import asyncio
import discord
from discord.ext import commands, tasks


class JoinVoiceCog(commands.Cog):

    def __init__(self, bot: commands.Bot, channel_id: int):
        self.bot = bot
        self.channel_id = channel_id
        self._connect_lock = asyncio.Lock()

    async def cog_load(self):
        self.ensure_voice_loop.start()

    def cog_unload(self):
        self.ensure_voice_loop.cancel()


    @tasks.loop(minutes=5)
    async def ensure_voice_loop(self):
        """Botun ses kanalında kalmasını sağlar."""

        if not self.bot.is_ready():
            return

        if self._connect_lock.locked():
            return

        channel = self.bot.get_channel(self.channel_id)

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except Exception as exc:
                print(f"JoinVoiceCog: Kanal alınamadı: {exc}")
                return

        if not isinstance(channel, discord.VoiceChannel):
            print("JoinVoiceCog: Kanal ses kanalı değil.")
            return


        voice_client = channel.guild.voice_client


        # Zaten bağlı
        if voice_client:

            if voice_client.is_connected():
                return

            # Discord kendi reconnect işlemini yapıyorsa dokunma
            if getattr(voice_client, "reconnecting", False):
                print("JoinVoiceCog: Discord reconnect yapıyor.")
                return


            # Bozuk bağlantıyı temizle
            try:
                await voice_client.disconnect(force=True)
                await asyncio.sleep(3)
            except Exception:
                pass


        await self._connect(channel)


    @ensure_voice_loop.before_loop
    async def before_voice_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)


    async def _connect(self, channel: discord.VoiceChannel):

        if self._connect_lock.locked():
            return


        async with self._connect_lock:

            if not self.bot.is_ready():
                return


            guild = channel.guild

            voice_client = guild.voice_client


            if voice_client and voice_client.is_connected():
                return


            try:
                print(
                    f"JoinVoiceCog: Ses kanalına bağlanılıyor "
                    f"({channel.id})..."
                )


                await channel.connect(
                    reconnect=True,
                    timeout=120,
                    self_deaf=True
                )


                print(
                    f"JoinVoiceCog: Ses kanalına başarıyla bağlandı "
                    f"({channel.id})."
                )


            except asyncio.TimeoutError:
                print(
                    "JoinVoiceCog: Ses bağlantısı zaman aşımına uğradı."
                )


            except discord.ClientException as exc:
                print(
                    f"JoinVoiceCog: Discord bağlantı hatası: {exc}"
                )


            except Exception as exc:
                print(
                    f"JoinVoiceCog: Bağlantı hatası "
                    f"{type(exc).__name__}: {exc}"
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(
        JoinVoiceCog(
            bot,
            1521953029321003054
        )
    )