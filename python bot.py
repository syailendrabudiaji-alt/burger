import discord
import asyncio
import random
import sqlite3
import os
from discord import app_commands

# =====================
# CONFIG
# =====================

TOKEN = os.getenv("TOKEN")
GUILD_ID = 1499402690957152338
TIP_CHANNEL_ID = 1499407906213335070

if not TOKEN:
    raise ValueError("TOKEN environment variable not found!")

# =====================
# DISCORD SETUP
# =====================

intents = discord.Intents.default()
intents.guilds = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
guild = discord.Object(id=GUILD_ID)

tips_started = False

# =====================
# SQLITE SETUP
# =====================

conn = sqlite3.connect("economy.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    wallet INTEGER DEFAULT 0,
    bank INTEGER DEFAULT 0
)
""")
conn.commit()

# =====================
# DATABASE FUNCTIONS
# =====================

def get_user(user_id):
    cursor.execute(
        "SELECT wallet, bank FROM users WHERE user_id = ?",
        (user_id,)
    )
    data = cursor.fetchone()

    if data is None:
        cursor.execute(
            "INSERT INTO users (user_id, wallet, bank) VALUES (?, ?, ?)",
            (user_id, 0, 0)
        )
        conn.commit()
        return {"wallet": 0, "bank": 0}

    return {"wallet": data[0], "bank": data[1]}


def update_user(user_id, wallet, bank):
    cursor.execute("""
    UPDATE users SET wallet = ?, bank = ? WHERE user_id = ?
    """, (wallet, bank, user_id))
    conn.commit()

# =====================
# TIPS SYSTEM
# =====================

tips = [
    "🍔 Tip: Save money in your bank to protect it!",
    "💰 Tip