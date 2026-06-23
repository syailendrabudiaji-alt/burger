import discord
import time
import asyncio
import random
import sqlite3
import json
import os
from discord import app_commands
from collections import counter

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

work_cooldown = {}
cook_cooldown = {}
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
# BACKUP SYSTEMS
# =====================

BACKUP_FILE = "economy_backup.json"

def load_backup():
    if not os.path.exists(BACKUP_FILE):
        return {}

    with open(BACKUP_FILE, "r") as f:
        return json.load(f)


def save_backup(user_id, wallet, bank):
    data = load_backup()

    data[user_id] = {
        "wallet": wallet,
        "bank": bank
    }

    with open(BACKUP_FILE, "w") as f:
        json.dump(data, f, indent=4)

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
        backup = load_backup()

        if user_id in backup:
            wallet = backup[user_id]["wallet"]
            bank = backup[user_id]["bank"]
        else:
            wallet = 0
            bank = 0

        cursor.execute(
            "INSERT INTO users (user_id, wallet, bank) VALUES (?, ?, ?)",
            (user_id, wallet, bank)
        )
        conn.commit()

        return {"wallet": wallet, "bank": bank}

    return {"wallet": data[0], "bank": data[1]}

def update_user(user_id, wallet, bank):
    cursor.execute("""
    UPDATE users
    SET wallet = ?, bank = ?
    WHERE user_id = ?
    """, (wallet, bank, user_id))
    conn.commit()

    save_backup(user_id, wallet, bank)

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
    cursor.execute(
        "SELECT job FROM jobs WHERE user_id = ?",
        (user_id,)
    )
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

        await 10800

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

    embed = discord.Embed(
        title="🏦 BurgerCash Bank",
        color=0x00ff99
    )

    embed.add_field(
        name="💰 Wallet",
        value=f"{user['wallet']} BC",
        inline=True
    )

    embed.add_field(
        name="🏦 Bank",
        value=f"{user['bank']} BC",
        inline=True
    )

    embed.set_footer(text=f"Requested by {interaction.user}")

    await interaction.response.send_message(embed=embed)


@tree.command(name="deposit", description="Deposit money", guild=guild)
async def deposit(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    user = get_user(user_id)

    if amount <= 0:
        embed = discord.Embed(
            title="❌ Error",
            description="Amount must be greater than 0.",
            color=0xff0000
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    if user["wallet"] < amount:
        embed = discord.Embed(
            title="❌ Error",
            description="Not enough money in wallet.",
            color=0xff0000
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    user["wallet"] -= amount
    user["bank"] += amount
    update_user(user_id, user["wallet"], user["bank"])

    embed = discord.Embed(
        title="🏦 Deposit Successful",
        description=f"You deposited **{amount} BC**",
        color=0x00ff99
    )

    embed.add_field(name="💰 Wallet", value=f"{user['wallet']} BC")
    embed.add_field(name="🏦 Bank", value=f"{user['bank']} BC")

    await interaction.response.send_message(embed=embed)


@tree.command(name="withdraw", description="Withdraw money", guild=guild)
async def withdraw(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    user = get_user(user_id)

    if amount <= 0:
        embed = discord.Embed(
            title="❌ Error",
            description="Amount must be greater than 0.",
            color=0xff0000
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    if user["bank"] < amount:
        embed = discord.Embed(
            title="❌ Error",
            description="Not enough money in bank.",
            color=0xff0000
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    user["bank"] -= amount
    user["wallet"] += amount
    update_user(user_id, user["wallet"], user["bank"])

    embed = discord.Embed(
        title="💸 Withdrawal Successful",
        description=f"You withdrew **{amount} BC**",
        color=0x00ff99
    )

    embed.add_field(name="💰 Wallet", value=f"{user['wallet']} BC")
    embed.add_field(name="🏦 Bank", value=f"{user['bank']} BC")

    await interaction.response.send_message(embed=embed)

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

    embed.add_field(name="🎣 Fishing Rod", value="500 BC", inline=False)
    embed.add_field(name="💎 Lucky Charm", value="1000 BC", inline=False)

    await interaction.response.send_message(embed=embed, view=ShopView())

@tree.command(name="inventory", description="View your inventory", guild=guild)
async def inventory(interaction: discord.Interaction):

    user_id = str(interaction.user.id)
    items = get_inventory(user_id)

    # 🔹 If empty inventory
    if not items:
        embed = discord.Embed(
            title="🎒 Inventory",
            description="You currently have no items.",
            color=0x3498db
        )
        await interaction.response.send_message(embed=embed)
        return

    # 🔹 OPTIONAL: randomize order
    random.shuffle(items)

    # 🔹 Count items
    counts = Counter(items)

    # 🔹 Sort into categories (EDIT THIS LIST LATER)
    fishing_items = []
    mining_items = []
    digging_items = []
    tools_items = []
    food_items = []
    misc_items = []

    for item, qty in counts.items():

        line = f"{item} x{qty}"

        # 🎣 Fishing
        if "Fish" in item:
            fishing_items.append(line)

        # ⛏️ Mining
        elif "Ore" in item or "Gem" in item:
            mining_items.append(line)

        # 🪏 Digging
        elif "Treasure" in item or "Coin" in item:
            digging_items.append(line)

        # 🛠️ Tools
        elif "Rod" in item or "Pickaxe" in item or "Shovel" in item:
            tools_items.append(line)

        # 🍳 Food
        elif "Cooked" in item or "Food" in item:
            food_items.append(line)

        # 📦 Misc
        else:
            misc_items.append(line)

    # 🔹 Build embed
    embed = discord.Embed(
        title="🎒 Your Inventory",
        color=0x3498db
    )

    def format_section(items_list):
        return "\n".join(items_list) if items_list else "0 items"

    embed.add_field(name="🎣 Fishing Items", value=format_section(fishing_items), inline=False)
    embed.add_field(name="⛏️ Mining Items", value=format_section(mining_items), inline=False)
    embed.add_field(name="🪏 Digging Loot", value=format_section(digging_items), inline=False)
    embed.add_field(name="🛠️ Tools", value=format_section(tools_items), inline=False)
    embed.add_field(name="🍳 Food", value=format_section(food_items), inline=False)
    embed.add_field(name="📦 Misc", value=format_section(misc_items), inline=False)

    await interaction.response.send_message(embed=embed)

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

    try:
        import time

        user_id = str(interaction.user.id)
        current_time = time.time()
        cooldown_time = 7200  # 2 hours

        # =====================
        # COOLDOWN CHECK
        # =====================
        if user_id in work_cooldown:
            time_left = work_cooldown[user_id] - current_time

            if time_left > 0:
                hours = int(time_left // 3600)
                minutes = int((time_left % 3600) // 60)

                embed = discord.Embed(
                    title="😴 You're tired!",
                    description="You already worked recently. Rest a bit!",
                    color=0xff5555
                )

                embed.add_field(
                    name="⏳ Time left",
                    value=f"{hours}h {minutes}m"
                )

                return await interaction.response.send_message(embed=embed, ephemeral=True)

        # =====================
        # JOB CHECK
        # =====================
        job = get_job(user_id)

        if not job:
            return await interaction.response.send_message(
                "❌ You don't have a job yet. Use /joblist",
                ephemeral=True
            )

        if job not in JOBS:
            return await interaction.response.send_message(
                "❌ Job not found in system. Please use /joblist again.",
                ephemeral=True
            )

        # =====================
        # REWARD SYSTEM
        # =====================
        min_pay, max_pay = JOBS[job]
        reward = random.randint(min_pay, max_pay)

        user = get_user(user_id)
        user["wallet"] += reward
        update_user(user_id, user["wallet"], user["bank"])

        # =====================
        # SET COOLDOWN
        # =====================
        work_cooldown[user_id] = current_time + cooldown_time

        # =====================
        # RESPONSE
        # =====================
        embed = discord.Embed(
            title="💼 Work Complete",
            description=f"You worked as **{job}**",
            color=0x00ff99
        )

        embed.add_field(name="💰 Earned", value=f"{reward} BC")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        print("WORK ERROR:", e)
        await interaction.response.send_message(
            "❌ Something went wrong with /work.",
            ephemeral=True
        )
# =====================
# RUN
# =====================
bot.run(TOKEN)
