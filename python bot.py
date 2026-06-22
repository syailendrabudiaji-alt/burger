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

class FishView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fish 🎣", style=discord.ButtonStyle.green)
    async def fish_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        user_id = str(interaction.user.id)
        user = get_user(user_id)

        reward = random.randint(10, 30)

        user["wallet"] += reward
        update_user(user_id, user["wallet"], user["bank"])

        await interaction.response.send_message(
            f"🎣 You caught a fish!\n💰 +{reward} BC",
            ephemeral=True
        )

if not TOKEN:
    raise ValueError("TOKEN environment variable not found!")

# =====================
# DISCORD SETUP
# =====================
intents = discord.Intents.default()

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    user_id TEXT,
    item TEXT
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
    UPDATE users
    SET wallet = ?, bank = ?
    WHERE user_id = ?
    """, (wallet, bank, user_id))
    conn.commit()

def get_inventory(user_id):
    cursor.execute(
        "SELECT item FROM inventory WHERE user_id = ?",
        (user_id,)
    )
    return [row[0] for row in cursor.fetchall()]

# =====================
# TIPS SYSTEM
# =====================
tips = [
    "🍔 Tip: Save money in your bank to protect it!",
    "💰 Tip: Check /shop for items!",
    "⚡ Tip: Use /work to earn money!",
    "🏆 Tip: Climb the leaderboard!"
]

async def tip_loop():
    await bot.wait_until_ready()

    while not bot.is_closed():
        channel = bot.get_channel(TIP_CHANNEL_ID)

        if channel:
            await channel.send(random.choice(tips))
        else:
            print("Tip channel not found!")

        await asyncio.sleep(5400)

# =====================
# READY EVENT
# =====================
@bot.event
async def on_ready():
    global tips_started

    await tree.sync(guild=guild)
    print(f"Logged in as {bot.user}")

    if not tips_started:
        bot.loop.create_task(tip_loop())
        tips_started = True

# =====================
# COMMANDS
# =====================
@tree.command(name="ping", description="Test bot", guild=guild)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@tree.command(name="balance", description="Check BurgerCash", guild=guild)
async def balance(interaction: discord.Interaction):
    user = get_user(str(interaction.user.id))

    await interaction.response.send_message(
        f"🍔 **BurgerCash Balance**\n"
        f"💰 Wallet: {user['wallet']} BC\n"
        f"🏦 Bank: {user['bank']} BC"
    )

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

@tree.command(name="addcash", description="Add BurgerCash to a member", guild=guild)
async def addcash(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int
):
    # Put allowed role IDs here
    ALLOWED_ROLE_IDS = [
        1499654765141954700,  # Owner role ID
        1499656992732483664, 
        1499657562222624848 # Admin role ID
    ]

    # Check user roles
    user_role_ids = [role.id for role in interaction.user.roles]

    if not any(role_id in ALLOWED_ROLE_IDS for role_id in user_role_ids):
        return await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True
        )

    # Check amount
    if amount <= 0:
        return await interaction.response.send_message(
            "❌ Amount must be more than 0.",
            ephemeral=True
        )

    # Get user data
    user_id = str(member.id)
    user = get_user(user_id)

    # Add cash
    user["wallet"] += amount
    update_user(user_id, user["wallet"], user["bank"])

    await interaction.response.send_message(
        f"💰 Added **{amount} BC** to {member.mention}'s wallet!"
    )

@tree.command(name="fish", description="Open fishing menu", guild=guild)
async def fish(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🎣 Fishing Area",
        description="Press the button below to fish!",
        color=0x00ff99
    )

    await interaction.response.send_message(
        embed=embed,
        view=FishView()
    )

@tree.command(name="shop", description="View shop items", guild=guild)
async def shop(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🛒 BurgerCash Shop",
        description="Buy items using your BurgerCash!",
        color=0x00ff99
    )

    embed.add_field(name="🎣 Fishing Rod", value="500 BC", inline=False)
    embed.add_field(name="💎 Lucky Charm", value="1000 BC", inline=False)
    embed.add_field(name="🏦 Bank Upgrade", value="2000 BC", inline=False)

    await interaction.response.send_message(embed=embed)

@tree.command(name="inventory", description="Check your items", guild=guild)
async def inventory(interaction: discord.Interaction):

    user_id = str(interaction.user.id)
    items = get_inventory(user_id)

    if not items:
        return await interaction.response.send_message("🎒 Your inventory is empty.")

    embed = discord.Embed(
        title="🎒 Your Inventory",
        description="\n".join([f"• {item}" for item in items]),
        color=0x00ff99
    )

    await interaction.response.send_message(embed=embed)

# =====================
# RUN
# =====================
bot.run(TOKEN)
