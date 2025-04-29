
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
from dotenv import load_dotenv

# Logger pour les actions du bot
logging.basicConfig(
    filename='bot.log',
    filemode='a',
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)

# Logger pour les messages
def log_conversation(message):
    with open("conversations.log", "a", encoding="utf-8") as f:
        f.write(f"[{message.created_at}] {message.author} ({message.author.id}): {message.content}\n")

# Chargement du token
load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATA_FILE = "infractions.json"

def load_infractions():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_infractions(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_warning(guild_id, user_id, reason, mod_id):
    data = load_infractions()
    guild_id = str(guild_id)
    user_id = str(user_id)
    if guild_id not in data:
        data[guild_id] = {}
    if user_id not in data[guild_id]:
        data[guild_id][user_id] = []
    data[guild_id][user_id].append({
        "reason": reason,
        "moderator": str(mod_id)
    })
    save_infractions(data)

@bot.event
async def on_ready():
    await tree.sync()
    logging.info(f"Bot connecté en tant que {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    log_conversation(message)
    await bot.process_commands(message)

@tree.command(name="kick", description="Kick un membre")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
    await member.kick(reason=reason)
    logging.info(f"{member} a été kick par {interaction.user} pour : {reason}")
    await interaction.response.send_message(f"{member} a été kick. Raison : {reason}")

@tree.command(name="ban", description="Ban un membre")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
    await member.ban(reason=reason)
    logging.info(f"{member} a été banni par {interaction.user} pour : {reason}")
    await interaction.response.send_message(f"{member} a été banni. Raison : {reason}")

@tree.command(name="clear", description="Supprimer un nombre de messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.channel.purge(limit=amount)
    logging.info(f"{amount} messages supprimés par {interaction.user}")
    await interaction.response.send_message(f"{amount} messages supprimés.", ephemeral=True)

@tree.command(name="mute", description="Mute un membre")
@app_commands.checks.has_permissions(manage_roles=True)
async def mute(interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not role:
        role = await interaction.guild.create_role(name="Muted")
        for channel in interaction.guild.channels:
            await channel.set_permissions(role, speak=False, send_messages=False)
    await member.add_roles(role, reason=reason)
    logging.info(f"{member} a été mute par {interaction.user} pour : {reason}")
    await interaction.response.send_message(f"{member} a été mute. Raison : {reason}")

@tree.command(name="unmute", description="Unmute un membre")
@app_commands.checks.has_permissions(manage_roles=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if role in member.roles:
        await member.remove_roles(role)
        logging.info(f"{member} a été unmute par {interaction.user}")
        await interaction.response.send_message(f"{member} a été unmute.")
    else:
        await interaction.response.send_message(f"{member} n'est pas mute.", ephemeral=True)

@tree.command(name="warn", description="Donner un avertissement à un membre")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    add_warning(interaction.guild.id, member.id, reason, interaction.user.id)
    logging.info(f"{member} a reçu un avertissement par {interaction.user} : {reason}")
    await interaction.response.send_message(f"{member.mention} a reçu un avertissement. Raison : {reason}")

@tree.command(name="infractions", description="Voir les avertissements d'un membre")
@app_commands.checks.has_permissions(moderate_members=True)
async def infractions(interaction: discord.Interaction, member: discord.Member):
    data = load_infractions()
    guild_data = data.get(str(interaction.guild.id), {})
    user_warnings = guild_data.get(str(member.id), [])

    if not user_warnings:
        await interaction.response.send_message(f"{member.mention} n’a aucun avertissement.")
        return

    msg = f"**{member} a {len(user_warnings)} avertissement(s) :**\n"
    for i, warn in enumerate(user_warnings, start=1):
        mod = await interaction.guild.fetch_member(int(warn['moderator']))
        msg += f"{i}. Raison: {warn['reason']} (par {mod.mention})\n"

    await interaction.response.send_message(msg)

bot.run(TOKEN)
