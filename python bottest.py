import discord
import time
import asyncio
import random
import sqlite3
import json
import os
from discord import app_commands
from collections import Counter

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

# ==============================
# 🎮 GAME DATA SYSTEM
# ==============================

# ------------------------------
# RODS SYSTEM DATA
# ------------------------------
RODS = {
    "Stick Rod": {"min": 1, "max": 2, "rarity": ["Common"], "price": 0},
    "Rusty Rod": {"min": 2, "max": 3, "rarity": ["Common", "Uncommon"], "price": 50},
    "Plastic Rod": {"min": 3, "max": 4, "rarity": ["Common", "Uncommon"], "price": 300},
    "Trainer Rod": {"min": 5, "max": 10, "rarity": ["Common", "Uncommon"], "price": 150},

    "Double Rod": {"min": 6, "max": 8, "rarity": ["Uncommon", "Rare", "Epic"], "price": 2500},
    "Extended Rod": {"min": 6, "max": 8, "rarity": ["Common", "Rare"], "price": 3500},
    "Net Rod": {"min": 12, "max": 12, "rarity": "ALL", "price": 7000},

    "Steel Rod": {"min": 14, "max": 14, "rarity": ["Rare", "Epic", "Legendary"], "price": 15000},
    "Magnet Rod": {"min": 10, "max": 18, "rarity": "ALL", "price": 25000},
    "Ping Rod": {"min": 10, "max": 14, "rarity": "ALL", "price": 30000},
    "Pickpocket Rod": {"min": 15, "max": 20, "rarity": "ALL", "price": 40000},

    "Platinum Rod": {"min": 42, "max": 42, "rarity": ["Epic", "Legendary"], "price": 100000},
    "Portable Rod": {"min": 30, "max": 38, "rarity": ["Epic", "Legendary"], "price": 120000},
    "Carbon Rod": {"min": 43, "max": 49, "rarity": ["Epic", "Legendary"], "price": 150000},
    "Distributor Rod": {"min": 42, "max": 42, "rarity": ["Epic", "Legendary"], "price": 200000},

    "Titanium Rod": {"min": 30, "max": 50, "rarity": ["Epic", "Legendary"], "price": 300000},
    "Diamond Rod": {"min": 50, "max": 60, "rarity": ["Legendary", "Mythic"], "price": 600000},

    "Omni Rod": {"min": 80, "max": 80, "rarity": ["Mythic", "Deepsea", "Abyssal"], "price": 2000000},
}

FISH = {
    "Common": ["Sardine", "Anchovy", "Minnow", "Tilapia", "Mudfish"],
    "Uncommon": ["Catfish", "Mackerel", "Bluegill", "Redfin"],
    "Rare": ["Salmon", "Tuna", "Trout", "Snapper"],
    "Epic": ["Swordfish", "Barracuda", "Bluefin Tuna", "King Crab", "Lobster"],
    "Legendary": ["Blue Marlin", "Whale Shark", "Manta Ray", "Giant Grouper", "Giant Squid"],
    "Mythic": ["Coelacanth", "Oarfish", "Goblin Shark", "Frilled Shark"],
    "Deepsea": ["Sunfish", "Colossal Squid", "Japanese Spider Crab", "Viperfish"],
    "Abyssal": ["Anglerfish", "Fangtooth Fish", "Barreleye Fish", "Giant Isopod"],
    "Exotic": ["Lionfish", "Napoleon Wrasse", "Ribbonfish", "Electric Eel"],
}

SPECIAL_FISH = {
    "King Crab": {"price": (2500000, 5000000), "type": "Secret"},
    "Burger Lobster": {"price": (1000000, 3000000), "type": "Limited"},
}

JOBS = {
    "Cashier": {"min": 35, "max": 110},
"Programmer": {"min": 150, "max": 450}, 
    "Fisherman": {"min": 20, "max": 80},
    "Miner": {"min": 25, "max": 100},
    "Delivery Worker": {"min": 30, "max": 90},
    "Builder": {"min": 25, "max": 85},
    "Hunter": {"min": 50, "max": 150},
    "Engineer": {"min": 60, "max": 180},
    "Chef": {"min": 40, "max": 140},
    "Mechanic": {"min": 90, "max": 250},
    "Electrician": {"min": 100, "max": 280},
    "Deep Miner": {"min": 120, "max": 350},
    "Reactor Technician": {"min": 200, "max": 600}
}

PICKAXE_SHOP = {
    "Rusty Pickaxe": {"price": 0, "strength": 7},
    "Copper Pickaxe": {"price": 40, "strength": 12},
    "Iron Pickaxe": {"price": 500, "strength": 20},
    "Steel Pickaxe": {"price": 4500, "strength": 35},
    "Platinum Pickaxe": {"price": 18000, "strength": 60},
    "Titanium Pickaxe": {"price": 55000, "strength": 100},
    "Infernum Pickaxe": {"price": 180000, "strength": 200},
    "Diamond Pickaxe": {"price": 550000, "strength": 400},
    "Mithril Pickaxe": {"price": 1450000, "strength": 600},
    "Adamantium Pickaxe": {"price": 3500000, "strength": 800},
    "Unobtainium Pickaxe": {"price": 7800000, "strength": 1000}
}

ROD_ABILITIES = {
    "Distributor Rod": ["auto_sell"],
    "Magnet Rod": ["bonus_cash"],
    "Pickpocket Rod": ["steal"],
}

# =====================
# GLOBAL VARIABLES
# =====================

work_cooldown = {}
cook_cooldown = {}
tips_started = False
user_locks = {}

def get_lock(user_id: str):
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]

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

# ---------------------
# USERS TABLE
# ---------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    wallet INTEGER DEFAULT 0,
    bank INTEGER DEFAULT 0,
    rod TEXT DEFAULT 'Stick Rod'
)
""")
conn.commit()

# ---------------------
# JOBS TABLE
# ---------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    user_id TEXT PRIMARY KEY,
    job TEXT
)
""")
conn.commit()

# ---------------------
# INVENTORY TABLE (FIXED)
# ---------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    user_id TEXT,
    item TEXT,
    amount INTEGER DEFAULT 1,
    PRIMARY KEY (user_id, item)
)
""")
conn.commit()

cursor.execute("""
UPDATE users
SET rod = 'Stick Rod'
WHERE rod IS NULL
""")
conn.commit()

cursor.execute("PRAGMA table_info(inventory)")
columns = [col[1] for col in cursor.fetchall()]

if "amount" not in columns:
    cursor.execute("""
    ALTER TABLE inventory ADD COLUMN amount INTEGER DEFAULT 1
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

# ---------------------
# BALANCE FUNCTIONS
# ---------------------
def get_user(user_id):
    cursor.execute(
        "SELECT wallet, bank FROM users WHERE user_id = ?",
        (user_id,)
    )
    data = cursor.fetchone()

    if not data:
        cursor.execute(
            "INSERT INTO users (user_id, wallet, bank) VALUES (?, 0, 0)",
            (user_id,)
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


# ---------------------
# INVENTORY FUNCTIONS
# ---------------------
def get_inventory(user_id):
    cursor.execute(
        "SELECT item, amount FROM inventory WHERE user_id = ?",
        (user_id,)
    )
    return cursor.fetchall()

def add_item(user_id, item):
    cursor.execute("""
        INSERT INTO inventory (user_id, item, amount)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, item)
        DO UPDATE SET amount = amount + 1
    """, (user_id, item))
    conn.commit()

# ---------------------
# JOB FUNCTIONS
# ---------------------
def set_job(user_id, job):
    cursor.execute("""
        INSERT INTO jobs (user_id, job)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET job = excluded.job
    """, (user_id, job))
    conn.commit()


def get_job(user_id):
    cursor.execute(
        "SELECT job FROM jobs WHERE user_id = ?",
        (user_id,)
    )
    data = cursor.fetchone()
    return data[0] if data else None


def get_work_reward(user_id):
    job = get_job(user_id)

    if not job:
        return 0

    job_data = JOBS.get(job)
    if not job_data:
        return 0

    return random.randint(job_data["min"], job_data["max"])

# ---------------------
# FISHING FUNCTIONS
# ---------------------
def get_random_fish(rarity):
    fish_list = FISH.get(rarity, ["Trash Fish"])
    fish = random.choice(fish_list)
    return fish


def fish_with_rod(rod_name):
    rod = RODS.get(rod_name, RODS["Stick Rod"])

    # safe luck value
    luck = rod.get("luck", 0)

    # use float so 99.7 etc works
    roll = random.uniform(1, 100)

    # luck improves fish rarity
    roll -= luck

    if roll <= 45:
        rarity = "Common"
    elif roll <= 70:
        rarity = "Uncommon"
    elif roll <= 85:
        rarity = "Rare"
    elif roll <= 93:
        rarity = "Epic"
    elif roll <= 97:
        rarity = "Legendary"
    elif roll <= 99:
        rarity = "Mythic"
    elif roll <= 99.7:
        rarity = "Deepsea"
    elif roll <= 99.95:
        rarity = "Abyssal"
    else:
        rarity = "Exotic"

    fish = get_random_fish(rarity)
    return fish, rarity


def get_user_rod(user_id):
    cursor.execute(
        "SELECT rod FROM users WHERE user_id = ?",
        (user_id,)
    )
    data = cursor.fetchone()

    if not data or not data[0]:
        return "Stick Rod"

    return data[0]


ROD_ABILITIES = {
    "Magnet Rod": ["bonus_cash"],
    "Pickpocket Rod": ["steal"],
    "Distributor Rod": ["auto_sell"]
}


def apply_abilities(user, rod_name, fish_list):
    abilities = ROD_ABILITIES.get(rod_name, [])

    # AUTO SELL
    if "auto_sell" in abilities:
        user["wallet"] += len(fish_list) * 1000
        fish_list.clear()

    # BONUS CASH
    if "bonus_cash" in abilities:
        if random.randint(1, 3) == 1:
            user["wallet"] += 500

    # STEAL
    if "steal" in abilities:
        if random.randint(1, 5) == 1:
            user["wallet"] += 2000

    return fish_list


def get_fish_value(fish):
    if fish in SPECIAL_FISH:
        return random.randint(*SPECIAL_FISH[fish]["price"])

    return random.randint(10, 5000)

# ---------------------
# MULTIPLIER SYSTEM
# ---------------------
def get_fish_multiplier(job):
    if job == "Fisherman":
        return 1.2
    return 1.0

# ---------------------
# MINING FUNCTIONS
# ---------------------
def get_pickaxe_shop_text():
    text = []

    for name, data in PICKAXE_SHOP.items():
        text.append(
            f"{name} — {data['price']} BC | STR {data['strength']}"
        )

    return "\n".join(text)

# ---------------------
# GLOBAL FUNCTIONS
# ---------------------

def clean_cooldowns():
    current = time.time()
    expired = [user for user, t in work_cooldown.items() if t < current]

    for user in expired:
        del work_cooldown[user]

# =====================
# TIPS SYSTEM
# =====================

tips = [
    "🍔 Tip: Save money in your bank to protect it !",
    "💰 Tip: Check /shop for items !",
    "⚡ Tip: Use /work to earn money !",
    "🏆 Tip: Climb the leaderboard !"
]

async def tip_loop():
    await bot.wait_until_ready()

    while not bot.is_closed():
        channel = bot.get_channel(TIP_CHANNEL_ID)

        if channel:
            await channel.send(random.choice(tips))
        else:
            print("Tip channel not found!")

        await asyncio.sleep(10800)  # every 3 hours

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

# ---------------------
# SHOP UI
# -

class BurgerShopSelect(discord.ui.Select):
    def __init__(self):

        options = [
            discord.SelectOption(label="⛏️ Pickaxes", value="pickaxes"),
            discord.SelectOption(label="🪏 Shovels", value="shovels"),
            discord.SelectOption(label="🔫 Weapons", value="weapons"),
            discord.SelectOption(label="⚡ Boosters", value="boosters"),
            discord.SelectOption(label="🍳 Food", value="food"),
            discord.SelectOption(label="💎 Rare Items", value="rare"),
        ]

        super().__init__(
            placeholder="Choose a shop section...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        section = self.values[0]

        if section == "pickaxes":
            content = get_pickaxe_shop_text()
            title = "⛏️ Pickaxes"

        elif section == "shovels":
            content = "Shovel system coming soon..."
            title = "🪏 Shovels"

        elif section == "weapons":
            content = "Weapons coming soon..."
            title = "🔫 Weapons"

        elif section == "boosters":
            content = "Boosters coming soon..."
            title = "⚡ Boosters"

        elif section == "food":
            content = "Food system coming soon..."
            title = "🍳 Food"

        else:
            content = "Rare items coming soon..."
            title = "💎 Rare Items"

        embed = discord.Embed(
            title=title,
            description=content,
            color=0xffc107
        )

        await interaction.response.edit_message(
            embed=embed,
            view=BurgerShopView()
        )


class BurgerShopView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(BurgerShopSelect())

    @discord.ui.button(
        label="🎒 Show Items",
        style=discord.ButtonStyle.gray
    )
    async def show(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        user_id = str(interaction.user.id)
        items = get_inventory(user_id)

        if not items:
            return await interaction.response.send_message(
                "🎒 Empty inventory",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🎒 Your Items:\n" +
            "\n".join([f"• {i}" for i in items]),
            ephemeral=True
        )

# =====================
# UI SYSTEMS
# 8.2 JOB UI
# =====================
class JobSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=job, value=job)
            for job in JOBS.keys()
        ]

        super().__init__(
            placeholder="Choose your job...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
    selected_job = self.values[0]

    if selected_job not in JOBS:
        return await interaction.response.send_message(
            "❌ Invalid job selected.",
            ephemeral=True
        )

    set_job(str(interaction.user.id), selected_job)

    await interaction.response.send_message(
        f"✅ Job set to **{selected_job}**",
        ephemeral=True
    )

class JobView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(JobSelect())
           
# =====================
# CHUNK 8.3 — INVENTORY UI
# =====================
class InventoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Refresh Inventory", style=discord.ButtonStyle.green)
    async def refresh_inventory(self, interaction: discord.Interaction, button: discord.ui.Button):

        user_id = str(interaction.user.id)
        items = get_inventory(user_id)

        if not items:
            embed = discord.Embed(
                title="🎒 Inventory",
                description="You currently have no items.",
                color=0x3498db
            )
            return await interaction.response.edit_message(embed=embed, view=self)

        fishing_items = []
        mining_items = []
        digging_items = []
        tools_items = []
        food_items = []
        misc_items = []

        for item, qty in items:
            line = f"{item} x{qty}"

            # safer fishing detection
            if any(fish in item for fish_list in FISH.values() for fish in fish_list):
                fishing_items.append(line)

            elif "Ore" in item or "Gem" in item:
                mining_items.append(line)

            elif "Treasure" in item or "Coin" in item:
                digging_items.append(line)

            elif "Rod" in item or "Pickaxe" in item or "Shovel" in item:
                tools_items.append(line)

            elif "Cooked" in item or "Food" in item:
                food_items.append(line)

            else:
                misc_items.append(line)

        def fmt(lst):
            return "\n".join(lst) if lst else "0 items"

        embed = discord.Embed(title="🎒 Your Inventory", color=0x3498db)

        embed.add_field(name="🎣 Fishing Items", value=fmt(fishing_items), inline=False)
        embed.add_field(name="⛏️ Mining Items", value=fmt(mining_items), inline=False)
        embed.add_field(name="🪏 Digging Loot", value=fmt(digging_items), inline=False)
        embed.add_field(name="🛠️ Tools", value=fmt(tools_items), inline=False)
        embed.add_field(name="🍳 Food", value=fmt(food_items), inline=False)
        embed.add_field(name="📦 Misc", value=fmt(misc_items), inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

# =====================
# UI SYSTEMS — INVENTORY / SELL UI
# Chunk 8.4
# =====================

class SellItemSelect(discord.ui.Select):
    def __init__(self, items, user_id):
        options = [
            discord.SelectOption(label=item, value=item)
            for item in items[:25]
        ]

        super().__init__(
            placeholder="Choose item to sell",
            options=options
        )

        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        item = self.values[0]

        view = SellQuantityView(item, self.user_id)

        embed = discord.Embed(
            title=f"💰 Selling: {item}",
            description="Choose quantity to sell",
            color=0x00ff99
        )

        await interaction.response.edit_message(
            embed=embed,
            view=view
        )


class SellQuantityView(discord.ui.View):
    def __init__(self, item, user_id):
        super().__init__()
        self.item = item
        self.user_id = user_id

    @discord.ui.button(
        label="Sell 1",
        style=discord.ButtonStyle.primary
    )
    async def sell_one(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.sell_item(interaction, 1)

    @discord.ui.button(
        label="Sell 5",
        style=discord.ButtonStyle.primary
    )
    async def sell_five(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.sell_item(interaction, 5)

    @discord.ui.button(
        label="Sell ALL",
        style=discord.ButtonStyle.danger
    )
    async def sell_all(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.sell_item(interaction, "all")

    async def sell_item(self, interaction, amount):

    user_id = self.user_id

    async with get_lock(user_id):

        item = self.item

    cursor.execute(
        "SELECT amount FROM inventory WHERE user_id = ? AND item = ?",
        (user_id, item)
    )
    row = cursor.fetchone()

    if not row:
        return await interaction.response.send_message(
            "❌ You don't own this item.",
            ephemeral=True
        )

    owned = row[0]

    if amount == "all":
        amount = owned

    amount = min(amount, owned)

    price_table = {
        "Tin Ore": 10,
        "Gold Ore": 100,
        "Diamond": 500,
        "Common Fish": 5,
        "Rare Fish": 50
    }

    price = price_table.get(item, 10)
    total = price * amount

    new_amount = owned - amount

    if new_amount <= 0:
        cursor.execute(
            "DELETE FROM inventory WHERE user_id = ? AND item = ?",
            (user_id, item)
        )
    else:
        cursor.execute(
            "UPDATE inventory SET amount = ? WHERE user_id = ? AND item = ?",
            (new_amount, user_id, item)
        )

    conn.commit()

    user = get_user(user_id)
    user["wallet"] += total
    update_user(user_id, user["wallet"], user["bank"])

    embed = discord.Embed(
        title="✅ Sale Complete",
        description=f"Sold **{item} x{amount}**",
        color=0x00ff99
    )
    embed.add_field(name="💰 Earned", value=f"{total} BC")

    await interaction.response.edit_message(
        embed=embed,
        view=None
    )


class SellItemView(discord.ui.View):
    def __init__(self, items, user_id):
        super().__init__(timeout=60)
        self.add_item(SellItemSelect(items, user_id))
# =====================
# COMMANDS
# =====================


# =====================
# BASIC COMMANDS
# =====================

# ---------------------
# Ping
# ---------------------
@tree.command(name="ping", description="Test bot", guild=guild)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")


# =====================
# BANKING COMMANDS
# =====================

# ---------------------
# Balance
# ---------------------
@tree.command(name="balance", description="Check BurgerCash", guild=guild)
async def balance(interaction: discord.Interaction):
    user = get_user(str(interaction.user.id))

    embed = discord.Embed(title="🏦 BurgerCash Bank", color=0x00ff99)
    embed.add_field(name="💰 Wallet", value=f"{user['wallet']} BC", inline=True)
    embed.add_field(name="🏦 Bank", value=f"{user['bank']} BC", inline=True)
    embed.set_footer(text=f"Requested by {interaction.user}")

    await interaction.response.send_message(embed=embed)


# ---------------------
# Deposit
# ---------------------
@tree.command(name="deposit", description="Deposit money", guild=guild)
async def deposit(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    user = get_user(user_id)

    if amount <= 0:
        return await interaction.response.send_message(
            "❌ Amount must be greater than 0.",
            ephemeral=True
        )

    if user["wallet"] < amount:
        return await interaction.response.send_message(
            "❌ Not enough money in wallet.",
            ephemeral=True
        )

    user["wallet"] -= amount
    user["bank"] += amount
    update_user(user_id, user["wallet"], user["bank"])

    await interaction.response.send_message(
        f"🏦 Deposited **{amount} BC**"
    )


# ---------------------
# Withdraw
# ---------------------
@tree.command(name="withdraw", description="Withdraw money", guild=guild)
async def withdraw(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    user = get_user(user_id)

    if amount <= 0:
        return await interaction.response.send_message(
            "❌ Amount must be greater than 0.",
            ephemeral=True
        )

    if user["bank"] < amount:
        return await interaction.response.send_message(
            "❌ Not enough money in bank.",
            ephemeral=True
        )

    user["bank"] -= amount
    user["wallet"] += amount
    update_user(user_id, user["wallet"], user["bank"])

    await interaction.response.send_message(
        f"💸 Withdrew **{amount} BC**"
    )


# ---------------------
# Add Cash (Admin)
# ---------------------
@tree.command(name="addcash", description="Add BurgerCash", guild=guild)
async def addcash(interaction: discord.Interaction, member: discord.Member, amount: int):
    ALLOWED_ROLE_IDS = [
        1499654765141954700,
        1499656992732483664,
        1499657562222624848
    ]

    user_roles = [role.id for role in interaction.user.roles]

    if not any(role in ALLOWED_ROLE_IDS for role in user_roles):
        return await interaction.response.send_message(
            "❌ No permission.",
            ephemeral=True
        )

    if amount <= 0:
        return await interaction.response.send_message(
            "❌ Invalid amount.",
            ephemeral=True
        )

    user_id = str(member.id)
    user = get_user(user_id)
    user["wallet"] += amount
    update_user(user_id, user["wallet"], user["bank"])

    await interaction.response.send_message(
        f"💰 Added {amount} BC to {member.mention}"
    )


# =====================
# SHOP COMMANDS
# =====================

# ---------------------
# Shop
# ---------------------
@tree.command(name="shop", description="Burger Shop", guild=guild)
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🍔 Burger Shop",
        description="Welcome to Burger Shop",
        color=0xffc107
    )
    embed.add_field(
        name="💬 Description",
        value="Buy items, upgrades, and more!",
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        view=BurgerShopView()
    )


# =====================
# INVENTORY COMMANDS
# =====================

# ---------------------
# Inventory
# ---------------------
@tree.command(name="inventory", description="View inventory", guild=guild)
async def inventory(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    items = get_inventory(user_id)

    if not items:
        return await interaction.response.send_message("🎒 Inventory is empty.")

    embed = discord.Embed(title="🎒 Inventory", color=0x3498db)

    # categories
    fishing = []
    mining = []
    tools = []
    misc = []

    for item, amount in items:
        line = f"{item} x{amount}"

        if item in sum(FISH.values(), []):
            fishing.append(line)
        elif "Ore" in item or "Gem" in item:
            mining.append(line)
        elif "Rod" in item or "Pickaxe" in item:
            tools.append(line)
        else:
            misc.append(line)

    def fmt(lst):
        return "\n".join(lst) if lst else "0 items"

    embed.add_field(name="🎣 Fishing", value=fmt(fishing), inline=False)
    embed.add_field(name="⛏️ Mining", value=fmt(mining), inline=False)
    embed.add_field(name="🛠️ Tools", value=fmt(tools), inline=False)
    embed.add_field(name="📦 Misc", value=fmt(misc), inline=False)

    await interaction.response.send_message(embed=embed)


# ---------------------
# Sell
# ---------------------
@tree.command(name="sell", description="Sell items", guild=guild)
async def sell(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    items = get_inventory(user_id)

    if not items:
        return await interaction.response.send_message(
            "❌ Inventory empty.",
            ephemeral=True
        )

    unique_items = [item for item, amount in items]
    view = SellItemView(unique_items, user_id)

    embed = discord.Embed(
        title="💰 Sell Items",
        description="Select item to sell",
        color=0x00ff99
    )

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# =====================
# JOB COMMANDS
# =====================

# ---------------------
# Job List
# ---------------------
@tree.command(name="joblist", description="View jobs", guild=guild)
async def joblist(interaction: discord.Interaction):
    embed = discord.Embed(title="💼 Job List", color=0x00ff99)
    embed.add_field(name="Jobs", value="\n".join(JOBS.keys()), inline=False)
    await interaction.response.send_message(embed=embed)


# ---------------------
# Set Job
# ---------------------
@tree.command(name="setjob", description="Choose job", guild=guild)
async def setjob(interaction: discord.Interaction, job: str):
    if job not in JOBS:
        return await interaction.response.send_message(
            "❌ Invalid job.",
            ephemeral=True
        )

    set_job(str(interaction.user.id), job)
    await interaction.response.send_message(f"✅ Job set to **{job}**")


# ---------------------
# Work
# ---------------------
@tree.command(name="work", description="Work your job", guild=guild)
async def work(interaction: discord.Interaction):

    clean_cooldowns()

    user_id = str(interaction.user.id)
    current_time = time.time()

    # cooldown check
    if user_id in work_cooldown:
        remaining = work_cooldown[user_id] - current_time

        if remaining > 0:
            return await interaction.response.send_message(
                f"😴 Cooldown: {int(remaining // 60)} mins left",
                ephemeral=True
            )

    job = get_job(user_id)

    if not job:
        return await interaction.response.send_message(
            "❌ Get a job first.",
            ephemeral=True
        )

    min_pay = JOBS[job]["min"]
    max_pay = JOBS[job]["max"]
    reward = random.randint(min_pay, max_pay)

    user = get_user(user_id)
    user["wallet"] += reward
    update_user(user_id, user["wallet"], user["bank"])

    work_cooldown[user_id] = current_time + 7200

    await interaction.response.send_message(
        f"💼 Worked as **{job}** and earned **{reward} BC**"
    )


# =====================
# FISHING COMMANDS
# =====================

# ---------------------
# Fish
# ---------------------
@tree.command(name="fish", description="Go fishing", guild=guild)
async def fish_cmd(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user = get_user(user_id)

    rod_name = get_user_rod(user_id)

    fish, rarity = fish_with_rod(rod_name)
    add_item(user_id, fish)

    fish_prices = {
        "Common": 20,
        "Uncommon": 50,
        "Rare": 100,
        "Epic": 250,
        "Legendary": 500,
        "Mythic": 1000,
        "Deepsea": 2500,
        "Abyssal": 5000,
        "Exotic": 10000
    }

    total = fish_prices.get(rarity, 20)

    if get_job(user_id) == "Fisherman":
        total = int(total * 1.2)

    user["wallet"] += total
    update_user(user_id, user["wallet"], user["bank"])

    await interaction.response.send_message(
        f"🎣 You caught **{fish}** ({rarity}) | 💰 +{total} BC"
    )

# =====================
# RUN BOT
# =====================

bot.run(TOKEN)