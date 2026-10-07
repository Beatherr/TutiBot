import os
import time
import asyncio

from dotenv import load_dotenv

load_dotenv()

import discord
from discord import app_commands
from discord.ext import commands
from openai import (
    AsyncOpenAI,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing from the environment.")

MODEL_NAME = "gpt-4.1-mini"
COMMAND_COOLDOWN_SECONDS = 12


class MinecraftView(discord.ui.View):
    def __init__(
        self,
        cog,
        original_message: str,
        user_id: int,
        first_reply: str,
    ):
        super().__init__(timeout=300)

        self.cog = cog
        self.original_message = original_message
        self.user_id = user_id
        self.previous_replies = [first_reply]

    @discord.ui.button(
        label="Try another one",
        style=discord.ButtonStyle.primary,
        emoji="🔄",
    )
    async def try_another_one(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the person who used the command can press this button.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        try:
            new_reply = await self.cog._generate_reply(
                self.original_message,
                previous_replies=self.previous_replies,
            )

            if not new_reply:
                raise RuntimeError("The model returned an empty response.")

            self.previous_replies.append(new_reply)

            # Keep the prompt from growing forever.
            if len(self.previous_replies) > 6:
                self.previous_replies = self.previous_replies[-6:]

            embed = self.cog._build_embed(
                message=self.original_message,
                reply=new_reply,
            )

            await interaction.edit_original_response(
                embed=embed,
                view=self,
            )

        except RateLimitError:
            await interaction.followup.send(
                "The AI service is rate-limited right now. Please try again in a bit.",
                ephemeral=True,
            )

        except (APITimeoutError, APIConnectionError):
            await interaction.followup.send(
                "The AI service is temporarily unavailable. Please try again.",
                ephemeral=True,
            )

        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while generating a new response:\n```{e}```",
                ephemeral=True,
            )


class MinecraftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.user_cooldowns = {}

    # ------------------------------------------------------------
    # EMBED
    # ------------------------------------------------------------

    def _build_embed(self, message: str, reply: str):
        # Discord embed fields have a 1024-character value limit.
        safe_message = message[:1000]
        safe_reply = reply[:1000]

        embed = discord.Embed(
            title="⛏️ Minecraft Guide 🟩",
            color=discord.Color.green(),
            description=(
                "━━━━━━━━━━━━━━━━━━━━\n"
                "**AI Minecraft Assistant**\n"
                "━━━━━━━━━━━━━━━━━━━━"
            ),
        )

        embed.add_field(
            name="💬 Your Question",
            value=f"> {safe_message}",
            inline=False,
        )

        embed.add_field(
            name="✨ Answer",
            value=f"> {safe_reply}",
            inline=False,
        )

        embed.set_footer(
            text="Minecraft AI Assistant • Everyone can see this answer"
        )

        return embed

    # ------------------------------------------------------------
    # PROMPT
    # ------------------------------------------------------------

    def _build_messages(self, message: str, previous_replies=None):
        if previous_replies is None:
            previous_replies = []

        previous_block = ""

        if previous_replies:
            previous_block = (
                "\n\n"
                "IMPORTANT — PREVIOUSLY GENERATED REPLIES:\n"
                "These replies have already been shown to the user.\n"
                "Do NOT repeat their wording, sentence structure, punchline, "
                "idea, emotional approach, or question.\n"
                "The new reply must feel like a genuinely different response.\n\n"
                + "\n".join(
                    f"{index}. {reply}"
                    for index, reply in enumerate(previous_replies, 1)
                )
            )

        system_prompt = (
            "You are Minecraft Wiki AI, a professional Minecraft expert assistant.\n\n"

            "========================\n"
            "LANGUAGE RULE\n"
            "========================\n"
            "- ALWAYS answer in English.\n"
            "- Never answer in Turkish or any other language.\n"
            "- If the user writes Turkish, translate the meaning internally and answer in English.\n\n"

            "========================\n"
            "MINECRAFT ONLY RULE\n"
            "========================\n"
            "- You ONLY answer Minecraft related questions.\n"
            "- Allowed topics:\n"
            "  * Minecraft Java Edition\n"
            "  * Minecraft Bedrock Edition\n"
            "  * Blocks and items\n"
            "  * Crafting recipes\n"
            "  * Enchantments\n"
            "  * Brewing\n"
            "  * Mobs and bosses\n"
            "  * Villagers\n"
            "  * Redstone\n"
            "  * Farms\n"
            "  * Commands\n"
            "  * Servers\n"
            "  * Plugins\n"
            "  * Mods (Forge, Fabric, NeoForge)\n"
            "  * Datapacks\n"
            "  * Resource packs\n"
            "  * Minecraft versions\n\n"

            "- If the question is not related to Minecraft, reply EXACTLY:\n"
            "I can only answer questions related to Minecraft.\n\n"

            "========================\n"
            "ANSWER STYLE\n"
            "========================\n"
            "- Always answer in English.\n"
            "- Be concise but helpful.\n"
            "- Use bullet points when useful.\n"
            "- Give step-by-step instructions for tutorials.\n"
            "- Mention version differences when needed.\n"
            "- Never invent Minecraft mechanics.\n"
            "- Do not mention you are an AI.\n"
            "- Do not add unnecessary greetings.\n\n"

            "Act like a Minecraft Wiki editor providing accurate information.\n"

            f"{previous_block}"
        )

        # Few-shot examples matching the format
        examples = [
            {
                "role": "user",
                "content": 'Their text: "How do I craft a Netherite Pickaxe?"',
            },
            {
                "role": "assistant",
                "content": (
                    "To craft a Netherite Pickaxe, combine a Diamond Pickaxe, 1 Netherite Ingot, "
                    "and 1 Netherite Upgrade Smithing Template inside a Smithing Table."
                ),
            },
            {
                "role": "user",
                "content": 'Their text: "What is the capital of France?"',
            },
            {
                "role": "assistant",
                "content": "I can only answer questions related to Minecraft.",
            },
            {
                "role": "user",
                "content": 'Their text: "How do I spawn the Wither?"',
            },
            {
                "role": "assistant",
                "content": (
                    "Place 4 blocks of Soul Sand or Soul Soil in a T-shape on the ground, "
                    "then place 3 Wither Skeleton Skulls across the top three blocks."
                ),
            },
            {
                "role": "user",
                "content": 'Their text: "What does Redstone Repeaters do?"',
            },
            {
                "role": "assistant",
                "content": (
                    "Redstone Repeaters extend a signal strength back to 15, delay redstone signals "
                    "by 1 to 4 ticks, and restrict signal flow to one direction."
                ),
            },
        ]

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        messages.extend(examples)

        messages.append(
            {
                "role": "user",
                "content": f'Their text: "{message}"',
            }
        )

        return messages

    # ------------------------------------------------------------
    # OPENAI REQUEST
    # ------------------------------------------------------------

    async def _generate_reply(
        self,
        message: str,
        previous_replies=None,
    ) -> str:
        messages = self._build_messages(
            message,
            previous_replies=previous_replies,
        )

        for attempt in range(4):
            try:
                response = await self.client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    max_completion_tokens=1000,
                )

                choice = response.choices[0].message

                # Check content first, fall back to refusal string if safety triggers
                content = choice.content or getattr(choice, "refusal", "") or ""

                if not content:
                    return ""

                # Clean accidental wrapping if the model ignores instructions.
                content = content.strip()

                if (
                    len(content) >= 2
                    and content.startswith('"')
                    and content.endswith('"')
                ):
                    content = content[1:-1].strip()

                return content

            except (
                RateLimitError,
                APITimeoutError,
                APIConnectionError,
            ):
                if attempt == 3:
                    raise

                await asyncio.sleep(2**attempt + 0.5)

        return ""

    # ------------------------------------------------------------
    # SLASH COMMAND
    # ------------------------------------------------------------

    @app_commands.command(
        name="mc",
        description="Ask a question about Minecraft mechanics, items, or recipes.",
    )
    @app_commands.allowed_contexts(
        guilds=True,
        dms=True,
        private_channels=True,
    )
    @app_commands.allowed_installs(
        guilds=True,
        users=True,
    )
    @app_commands.describe(message="The Minecraft question you want answered")
    async def mc(
        self,
        interaction: discord.Interaction,
        message: str,
    ):
        # Basic input validation.
        message = message.strip()

        if not message:
            await interaction.response.send_message(
                "Please provide the message you want a reply to.",
                ephemeral=True,
            )
            return

        if len(message) > 1500:
            await interaction.response.send_message(
                "That message is too long. Please keep it under 1500 characters.",
                ephemeral=True,
            )
            return

        # Per-user cooldown.
        now = time.monotonic()

        last_used = self.user_cooldowns.get(
            interaction.user.id,
            0,
        )

        elapsed = now - last_used

        if elapsed < COMMAND_COOLDOWN_SECONDS:
            remaining = int(COMMAND_COOLDOWN_SECONDS - elapsed) + 1

            await interaction.response.send_message(
                f"Please wait {remaining} seconds before using this command again.",
                ephemeral=True,
            )
            return

        self.user_cooldowns[interaction.user.id] = now

        await interaction.response.defer(
            thinking=True,
        )

        try:
            first_reply = await self._generate_reply(message)

            if not first_reply:
                raise RuntimeError("The model returned an empty response.")

            embed = self._build_embed(
                message=message,
                reply=first_reply,
            )

            view = MinecraftView(
                cog=self,
                original_message=message,
                user_id=interaction.user.id,
                first_reply=first_reply,
            )

            await interaction.followup.send(
                embed=embed,
                view=view,
            )

        except RateLimitError:
            await interaction.followup.send(
                "The AI service is rate-limited right now. Please try again in a bit.",
                ephemeral=True,
            )

        except (
            APITimeoutError,
            APIConnectionError,
        ):
            await interaction.followup.send(
                "The AI service is temporarily unavailable. Please try again.",
                ephemeral=True,
            )

        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while generating a response:\n```{e}```",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(MinecraftCog(bot))