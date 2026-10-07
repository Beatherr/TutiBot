import os
import asyncio
import traceback
import time
import discord
from discord import Client, app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_CHANNEL_ID = int(os.getenv("STAY_VOICE_CHANNEL_ID", "1521953029321003054"))

# Hata log ayarları
ERROR_LOG_CHANNEL_ID = 1533462840881578114
ERROR_MENTION_USER_ID = 1386274640229568572

# Komut log kanalı
COMMAND_LOG_CHANNEL_ID = 1533462840881578114

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.message_content = True  # Mesaj eklentilerini okuyabilmek için şart


class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()
        self.voice_channel_id = VOICE_CHANNEL_ID

    async def setup_hook(self) -> None:
        # Cog'lar extension olarak yükleniyor
        initial_extensions = [
            "cogs.voice_time",
            "cogs.join_voice",
            "cogs.gif_converter",
            "cogs.yazitura",
            "cogs.menu",
            "cogs.interactions",
            "cogs.stats",
            "cogs.ship",
            "cogs.sekiztop",
            "cogs.mc",
            "cogs.achievement",
            "cogs.dice",
            "cogs.slot",
        ]

        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
            except Exception as e:
                print(f"Failed to load extension {extension}: {e}")


bot = MyBot(command_prefix="", intents=intents)


def make_error_embed(error: Exception, source: str) -> discord.Embed:
    description = str(error) or "Bilinmeyen bir hata oluştu."
    embed = discord.Embed(
        title="Bot Hatası",
        description=f"```\n{description[:2000]}\n```",
        color=discord.Color.red(),
    )
    embed.add_field(name="Kaynak", value=source, inline=False)
    embed.set_footer(text="Hata konsolda da kaydedildi.")
    return embed


async def log_error_to_channel(source: str, error: Exception, extra_info: str = ""):
    try:
        channel = bot.get_channel(ERROR_LOG_CHANNEL_ID)
        if channel is None:
            channel = await bot.fetch_channel(ERROR_LOG_CHANNEL_ID)

        traceback_text = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

        header = (
            f"<@{ERROR_MENTION_USER_ID}> **Bot Hatası**\n"
            f"**Kaynak:** `{source}`\n"
            f"**Hata Türü:** `{type(error).__name__}`\n"
        )

        if extra_info:
            header += f"**Ek Bilgi:**\n{extra_info}\n"

        # Discord 2000 karakter limiti için parçalara böl
        max_chunk = 1700
        chunks = [
            traceback_text[i:i + max_chunk]
            for i in range(0, len(traceback_text), max_chunk)
        ]

        if not chunks:
            await channel.send(f"{header}```py\nBilinmeyen traceback.\n```")
            return

        # İlk mesaj: etiket + bilgi + ilk traceback parçası
        await channel.send(f"{header}```py\n{chunks[0]}\n```")

        # Kalan parçalar
        for chunk in chunks[1:]:
            await channel.send(f"```py\n{chunk}\n```")

    except Exception as log_exc:
        print(f"Error while logging error to channel: {log_exc}")


@bot.event
async def on_ready():
    print(f"Bot ready. Logged in: {bot.user} ({bot.user.id})")
    
    # DM ve tüm sunucularda çalışması için GLOBAL Sync
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands globally synced! Total: {len(synced)}")
    except Exception as exc:
        print(f"Error syncing slash commands: {exc}")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return

    actual_error = error.original if isinstance(error, commands.CommandInvokeError) else error
    traceback.print_exception(type(actual_error), actual_error, actual_error.__traceback__)

    # Hata kanalına logla
    try:
        await log_error_to_channel(
            source=f"Prefix Komut: {ctx.command}",
            error=actual_error,
            extra_info=(
                f"Kullanıcı: {ctx.author} ({ctx.author.id})\n"
                f"Sunucu: {ctx.guild.name if ctx.guild else 'DM'}\n"
                f"Komut Mesajı: {ctx.message.content}"
            )
        )
    except Exception as e:
        print(f"Error logging prefix command error: {e}")

    # Kullanıcıya basit hata mesajı gönder
    embed = make_error_embed(actual_error, f"Komut: {ctx.command}")
    try:
        await ctx.reply(embed=embed, mention_author=False)
    except Exception:
        pass


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    actual_error = error.original if isinstance(error, app_commands.CommandInvokeError) else error
    traceback.print_exception(type(actual_error), actual_error, actual_error.__traceback__)

    command_name = interaction.command.name if interaction.command else "Bilinmiyor"

    # Hata kanalına logla
    try:
        await log_error_to_channel(
            source=f"Slash Komut: /{command_name}",
            error=actual_error,
            extra_info=(
                f"Kullanıcı: {interaction.user} ({interaction.user.id})\n"
                f"Sunucu: {interaction.guild.name if interaction.guild else 'DM'}\n"
                f"Kanal: #{interaction.channel.name if interaction.channel else 'Bilinmiyor'}"
            )
        )
    except Exception as e:
        print(f"Error logging slash command error: {e}")

    # Kullanıcıya basit hata mesajı gönder
    embed = make_error_embed(actual_error, f"Slash Komut: {command_name}")
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception:
        pass


# Command Logging System
@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: app_commands.Command):
    """Log all slash commands to the designated channel (except gif_converter commands)"""
    try:
        if not interaction.command:
            return
        
        # Skip gif_converter commands (they have their own logging)
        if interaction.command.module and "gif_converter" in interaction.command.module:
            return
        
        log_channel = bot.get_channel(COMMAND_LOG_CHANNEL_ID)
        if not log_channel:
            return
        
        # Build log embed
        embed = discord.Embed(
            title=f"📝 Command Used: /{interaction.command.name}",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="<:user:1533502574324351116> User",
            value=f"{interaction.user.mention}\n`{interaction.user.name}`",
            inline=False
        )
        
        embed.add_field(
            name="🆔 User ID",
            value=f"`{interaction.user.id}`",
            inline=True
        )
        
        # Show location (Guild or DM)
        if interaction.guild:
            embed.add_field(
                name="<:Blurple_Server:1533502657753387219> Server",
                value=f"**{interaction.guild.name}**\nID: `{interaction.guild.id}`",
                inline=False
            )
        else:
            embed.add_field(
                name="💬 Location",
                value="**DM (Direct Message)**",
                inline=False
            )
        
        # Add command parameters if any
        if interaction.namespace:
            params = []
            for param_name, param_value in vars(interaction.namespace).items():
                if param_value is not None:
                    if isinstance(param_value, discord.User):
                        params.append(f"`{param_name}`: {param_value.mention}")
                    else:
                        params.append(f"`{param_name}`: {param_value}")
            
            if params:
                embed.add_field(
                    name="⚙️ Parameters",
                    value="\n".join(params[:5]),  # Max 5 params shown
                    inline=False
                )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Tuti Bot Command Log")
        
        await log_channel.send(embed=embed)
    
    except Exception as e:
        print(f"Error logging command: {e}")


@bot.event
async def on_error(event_method, *args, **kwargs):
    # Genel event hatası
    exc_text = traceback.format_exc()
    print(exc_text)
    print(f"Unhandled bot event error in {event_method}")

    try:
        channel = bot.get_channel(ERROR_LOG_CHANNEL_ID)
        if channel is None:
            channel = await bot.fetch_channel(ERROR_LOG_CHANNEL_ID)

        content = (
            f"<@{ERROR_MENTION_USER_ID}> **Unhandled Event Error**\n"
            f"**Event:** `{event_method}`\n"
            f"```py\n{exc_text[:1800]}\n```"
        )
        await channel.send(content)
    except Exception as log_exc:
        print(f"Error while sending on_error log: {log_exc}")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)