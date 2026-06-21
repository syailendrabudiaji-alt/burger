import discord
import asyncio
import random
import sqlite3
from discord import app_commands

# =====================
# CONFIG
# =====================
TOKEN = "MTUxODE5NzEyMzU3OTkwODI0Ng.GkwPbU.Df-n8MXIRCSPBUFv5daJlwqEZkvm_O27TA_h1w"
GUILD_ID = 1499402690957152338
TIP_CHANNEL_ID = 1499407906213335070

# =====================
# DISCORD SETUP
# =====================
intents = discord.Intents.default()

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

guild = discord.Object(id=GUILD_ID)

# =====================
# SQLITE SETUP
# =====================
conn = sqlite3.connect("economy.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    wallet INTEGER,
    bank INTEGER
)
""")

conn.commit()

# =====================
# DATABASE FUNCTIONS
# =====================
def get_user(user_id):
    cursor.execute("SELECT wallet, bank FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()

    if data is None:
        cursor.execute(
            "INSERT INTO users VALUES (?, ?, ?)",
            (user_id, 0, 0)
        )
        conn.commit()
        return {"wallet": 0, "bank": 0}

    return {"wallet": data[0], "bank": data[1]}

def update_user(user_id, wallet, bank):
    cursor.execute("""
    UPDATE users
    SET wallet = ?, bank = ?
    WHERE user_id = ?
    """, (wallet, bank, user_id))

    conn.commit()

# =====================
# TIPS SYSTEM
# =====================
tips = [
    "🍔 Tip : Did you know that you cant install me in another server.",
    "💰 Tip : Save money in your bank to protect it !",
    "🛒 Tip : Check /shop for limited items !",
    "⚡ Tip : Working with /work gives random rewards !",
    "🏆 Tip : Climb the leaderboard to become richest !"
]

async def tip_loop():
    await bot.wait_until_ready()

    channel = bot.get_channel(TIP_CHANNEL_ID)

    while not bot.is_closed():
        if channel:
            await channel.send(random.choice(tips))

        await asyncio.sleep(1800)  # 30 minutes

# =====================
# READY EVENT
# =====================
@bot.event
async def on_ready():
    await tree.sync(guild=guild)
    print(f"Logged in as {bot.user}")

    bot.loop.create_task(tip_loop())

# =====================
# BALANCE
# =====================
@tree.command(name="balance", description="Check BurgerCash", guild=guild)
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user = get_user(user_id)

    await interaction.response.send_message(
        f"🍔 **BurgerCash Balance**\n"
        f"💰 Wallet: {user['wallet']} BC\n"
        f"🏦 Bank: {user['bank']} BC"
    )

# =====================
# DEPOSIT
# =====================
@tree.command(name="deposit", description="Deposit money", guild=guild)
async def deposit(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    user = get_user(user_id)

    if amount <= 0:
        return await interaction.response.send_message("❌ Invalid amount")

    if user["wallet"] < amount:
        return await interaction.response.send_message("❌ Not enough wallet money")

    user["wallet"] -= amount
    user["bank"] += amount

    update_user(user_id, user["wallet"], user["bank"])

    await interaction.response.send_message(f"🏦 Deposited {amount} BC!")

# =====================
# WITHDRAW
# =====================
@tree.command(name="withdraw", description="Withdraw money", guild=guild)
async def withdraw(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    user = get_user(user_id)

    if amount <= 0:
        return await interaction.response.send_message("❌ Invalid amount")

    if user["bank"] < amount:
        return await interaction.response.send_message("❌ Not enough bank money")

    user["bank"] -= amount
    user["wallet"] += amount

    update_user(user_id, user["wallet"], user["bank"])

    await interaction.response.send_message(f"💰 Withdrew {amount} BC!")

# =====================
# PING
# =====================
@tree.command(name="ping", description="Test bot", guild=guild)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

# =====================
# RUN BOT
# =====================
bot.run(TOKEN)