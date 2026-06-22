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

JOBS = {
    "Cashier": (10, 30),
    "Miner": (20, 60),
    "Chef": (15, 50),
    "Delivery": (25, 80),
    "Programmer": (30, 100)
}

# =====================
# GLOBAL VARIABLES
# =====================

work_cooldown = {60}
cook_cooldown = {10800}
tips_started = False

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    user_id TEXT PRIMARY KEY,
    job TEXT
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

def get_inventory(user_id):
    cursor.execute(
        "SELECT item FROM inventory WHERE user_id = ?",
        (user_id,)
    )
    return [row[0] for row in cursor.fetchall()]


def add_item(user_id, item):
    cursor.execute(
        "INSERT INTO inventory (user_id, item) VALUES (?, ?)",
        (user_id, item)
    )
    conn.commit()

def set_job(user_id, job):
    cursor.execute("""
    INSERT INTO jobs (user_id, job)
    VALUES (?, ?)
    ON CONFLICT(user_id)
    DO UPDATE SET job = excluded.job
    """, (user_id, job))
    conn.commit()


def get_job(user_id):
    cursor.execute("SELECT job FROM jobs WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    return data[0] if data else None

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
# UI SYSTEMS
# =====================

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎣 Fishing Rod - 500 BC", style=discord.ButtonStyle.green)
    async def rod(self, interaction: discord.Interaction, button: discord.ui.Button):

        user_id = str(interaction.user.id)
        user = get_user(user_id)

        if user["wallet"] < 500:
            return await interaction.response.send_message("❌ Not enough BC", ephemeral=True)

        user["wallet"] -= 500
        update_user(user_id, user["wallet"], user["bank"])

        add_item(user_id, "Fishing Rod")

        await interaction.response.send_message("🎣 You bought Fishing Rod!", ephemeral=True)


    @discord.ui.button(label="💎 Lucky Charm - 1000 BC", style=discord.ButtonStyle.blurple)
    async def charm(self, interaction: discord.Interaction, button: discord.ui.Button):

        user_id = str(interaction.user.id)
        user = get_user(user_id)

        if user["wallet"] < 1000:
            return await interaction.response.send_message("❌ Not enough BC", ephemeral=True)

        user["wallet"] -= 1000
        update_user(user_id, user["wallet"], user["bank"])

        add_item(user_id, "Lucky Charm")

        await interaction.response.send_message("💎 You bought Lucky Charm!", ephemeral=True)

class InventoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎒 Show Items", style=discord.ButtonStyle.gray)
    async def show(self, interaction: discord.Interaction, button: discord.ui.Button):

        user_id = str(interaction.user.id)
        items = get_inventory(user_id)

        if not items:
            return await interaction.response.send_message("🎒 Empty inventory", ephemeral=True)

        await interaction.response.send_message(
            "🎒 Your Items:\n" + "\n".join([f"• {i}" for i in items]),
            ephemeral=True
        )

class JobView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💼 Cashier", style=discord.ButtonStyle.green)
    async def cashier(self, interaction: discord.Interaction, button: discord.ui.Button):
        set_job(str(interaction.user.id), "Cashier")
        await interaction.response.send_message("💼 You selected Cashier!", ephemeral=True)

    @discord.ui.button(label="⛏️ Miner", style=discord.ButtonStyle.gray)
    async def miner(self, interaction: discord.Interaction, button: discord.ui.Button):
        set_job(str(interaction.user.id), "Miner")
        await interaction.response.send_message("⛏️ You selected Miner!", ephemeral=True)

    @discord.ui.button(label="👨‍🍳 Chef", style=discord.ButtonStyle.blurple)
    async def chef(self, interaction: discord.Interaction, button: discord.ui.Button):
        set_job(str(interaction.user.id), "Chef")
        await interaction.response.send_message("👨‍🍳 You selected Chef!", ephemeral=True)

    @discord.ui.button(label="🚚 Delivery", style=discord.ButtonStyle.green)
    async def delivery(self, interaction: discord.Interaction, button: discord.ui.Button):
        set_job(str(interaction.user.id), "Delivery")
        await interaction.response.send_message("🚚 You selected Delivery!", ephemeral=True)

    @discord.ui.button(label="💻 Programmer", style=discord.ButtonStyle.blurple)
    async def programmer(self, interaction: discord.Interaction, button: discord.ui.Button):
        set_job(str(interaction.user.id), "Programmer")
        await interaction.response.send_message("💻 You selected Programmer!", ephemeral=True)

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

@tree.command(name="shop", description="Open shop", guild=guild)
async def shop(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🛒 BurgerCash Shop",
        description="Click buttons to buy items!",
        color=0x00ff99
    )

    await interaction.response.send_message(embed=embed, view=ShopView())

    embed.add_field(name="🎣 Fishing Rod", value="500 BC", inline=False)
    embed.add_field(name="💎 Lucky Charm", value="1000 BC", inline=False)
    embed.add_field(name="🏦 Bank Upgrade", value="2000 BC", inline=False)

    await interaction.response.send_message(embed=embed)

@tree.command(name="inventory", description="Open inventory", guild=guild)
async def inventory(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🎒 Inventory",
        description="Click button to view items",
        color=0x00ff99
    )

    await interaction.response.send_message(embed=embed, view=InventoryView())

@tree.command(name="joblist", description="Choose your job", guild=guild)
async def joblist(interaction: discord.Interaction):

    embed = discord.Embed(
        title="💼 Job Center",
        description="Pick a job to start working!",
        color=0x00ff99
    )

    for job, salary in JOBS.items():
        embed.add_field(
            name=job,
            value=f"💰 {salary[0]} - {salary[1]} BC",
            inline=False
        )

    await interaction.response.send_message(embed=embed, view=JobView())

@tree.command(name="work", description="Work your job", guild=guild)
async def work(interaction: discord.Interaction):

    user_id = str(interaction.user.id)
    current_time = asyncio.get_event_loop().time()

    cooldown_time = 7200  # 2 hours (change if you want)

    # check cooldown
    if user_id in work_cooldown:
        time_left = work_cooldown[user_id] - current_time

        if time_left > 0:
            hours = int(time_left // 3600)
            minutes = int((time_left % 3600) // 60)

            embed = discord.Embed(
                title="😴 You're too tired to work!",
                description=f"Take a break before working again.",
                color=0xff5555
            )
            embed.add_field(
                name="⏳ Time left",
                value=f"{hours}h {minutes}m"
            )

            return await interaction.response.send_message(embed=embed, ephemeral=True)

    # set cooldown
    work_cooldown[user_id] = current_time + cooldown_time

    job = get_job(user_id)

    if not job:
        return await interaction.response.send_message(
            "❌ You don't have a job yet. Use /joblist",
            ephemeral=True
        )

    min_pay, max_pay = JOBS[job]
    reward = random.randint(min_pay, max_pay)

    user = get_user(user_id)
    user["wallet"] += reward
    update_user(user_id, user["wallet"], user["bank"])

    embed = discord.Embed(
        title="💼 Work Completed",
        description=f"You worked as **{job}**",
        color=0x00ff99
    )

    embed.add_field(name="💰 Earned", value=f"{reward} BC")
    embed.add_field(name="😴 Status", value="You feel tired after working...")

    await interaction.response.send_message(embed=embed)

# =====================
# RUN
# =====================
bot.run(TOKEN)
