# -*- coding: utf-8 -*-
import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta, timezone
import aiohttp
import os
from dotenv import load_dotenv

# ================= LOAD ENV =================
load_dotenv()

CTFD_BASE_URL = os.getenv("CTFD_API_URL", "").rstrip("/")
CTFD_API_TOKEN = os.getenv("CTFD_API_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

CHECK_INTERVAL = 5 

# Tracking first bloods in memory (reset setiap bot restart)
first_blood_announced = set()

# ================= DISCORD =================
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

client = commands.Bot(command_prefix="!", intents=intents)

# ================= UTIL =================
def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


def api_headers():
    return {
        "Authorization": f"Token {CTFD_API_TOKEN}",
        "Content-Type": "application/json"
    }


# ================= CTFd API =================
async def fetch_challenge_list():
    """Fetch all challenges from CTFd"""
    url = f"{CTFD_BASE_URL}/api/v1/challenges"
    try:
        async with client.session.get(url, headers=api_headers(), timeout=10) as r:
            if r.status == 401:
                log("ERROR: Invalid API token (401 Unauthorized)")
                return []
            elif r.status != 200:
                text = await r.text()
                log(f"Failed to fetch challenges: HTTP {r.status} - {text[:200]}")
                return []
            
            data = await r.json()
            challenges = data.get("data", [])
            return challenges
    except aiohttp.ClientError as e:
        log(f"Network error fetching challenges: {e}")
        return []
    except Exception as e:
        log(f"Unexpected error fetching challenges: {e}")
        return []


async def fetch_solves_for_challenge(challenge_id: int):
    """Fetch all solves for a specific challenge"""
    url = f"{CTFD_BASE_URL}/api/v1/challenges/{challenge_id}/solves"
    try:
        async with client.session.get(url, headers=api_headers(), timeout=10) as r:
            if r.status == 401:
                log(f"ERROR: Invalid API token for challenge {challenge_id}")
                return []
            elif r.status != 200:
                return []
            
            data = await r.json()
            return data.get("data", [])
    except Exception as e:
        return []


# ================= FIRST BLOOD LOOP (REAL-TIME) =================
@tasks.loop(seconds=CHECK_INTERVAL)
async def check_first_blood():
    """Check for new first bloods and announce them in REAL-TIME"""
    
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        log(f"ERROR: Discord channel {DISCORD_CHANNEL_ID} not found!")
        return

    challenges = await fetch_challenge_list()
    if not challenges:
        return

    new_first_bloods = 0
    
    for chal in challenges:
        cid = chal["id"]
        cname = chal["name"]

        # Skip if already announced THIS SESSION
        if cid in first_blood_announced:
            continue

        # Fetch solves for this challenge
        solves = await fetch_solves_for_challenge(cid)
        if not solves:
            continue

        # Sort by date and get first blood
        solves.sort(key=lambda x: x["date"])
        fb = solves[0]

        # Extract solve information
        user = fb.get("name", "Unknown")
        
        # Parse and convert time to WIB (UTC+7)
        try:
            utc_time = datetime.strptime(fb["date"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=timezone.utc
            )
            wib_time = utc_time.astimezone(timezone(timedelta(hours=7)))
            solved_time = wib_time.strftime("%d/%m/%Y %H:%M:%S")
        except Exception as e:
            log(f"Error parsing date: {e}")
            solved_time = fb["date"]

        # Create announcement message
        message = (
            f"🩸 First blood for **{cname}** goes to **{user}**! 🩸\n"
            f"🕒 Time: `{solved_time} WIB`"
        )

        # Send to Discord
        try:
            await channel.send(message)
            log(f"🩸 FIRST BLOOD: {cname} by {user}")
            new_first_bloods += 1
        except discord.Forbidden:
            log("ERROR: Bot doesn't have permission to send messages!")
            return
        except Exception as e:
            log(f"Failed to send message to Discord: {e}")
            continue

        # Mark as announced (in-memory only)
        first_blood_announced.add(cid)

    if new_first_bloods > 0:
        log(f"✓ Announced {new_first_bloods} new first blood(s)")


@check_first_blood.before_loop
async def before_check_first_blood():
    """Wait until bot is ready before starting the loop"""
    await client.wait_until_ready()
    log("First blood checker started - Real-time monitoring active!")


# ================= DISCORD COMMANDS =================
@client.command(name="status")
async def status_command(ctx):
    """Check bot status"""
    embed = discord.Embed(
        title="🤖 Bot Status",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.add_field(name="🌐 CTFd URL", value=CTFD_BASE_URL or "Not set", inline=False)
    embed.add_field(name="⏱️ Check Interval", value=f"{CHECK_INTERVAL} seconds", inline=True)
    embed.add_field(name="🩸 Announced (This Session)", value=len(first_blood_announced), inline=True)
    embed.add_field(name="📡 Bot Latency", value=f"{round(client.latency * 1000)}ms", inline=True)
    embed.add_field(name="🔄 Mode", value="**REAL-TIME** ⚡", inline=True)
    embed.set_footer(text="First Blood Bot - Real-time!")
    
    await ctx.send(embed=embed)


@client.command(name="reset")
@commands.has_permissions(administrator=True)
async def reset_command(ctx):
    """Reset first blood tracking (Admin only)"""
    count = len(first_blood_announced)
    first_blood_announced.clear()
    await ctx.send(f"✅ Reset {count} first blood announcements! Bot will re-announce if solves still exist.")
    log("First blood tracking reset by admin")


@client.command(name="myhelp")
async def help_command(ctx):
    """Show available commands"""
    embed = discord.Embed(
        title="📚 Bot Commands",
        description="CTFd First Blood Announcer",
        color=discord.Color.blue()
    )
    embed.add_field(name="!status", value="Check bot status and stats", inline=False)
    embed.add_field(name="!reset", value="Reset first blood tracking (Admin only)", inline=False)
    embed.add_field(name="!help", value="Show this help message", inline=False)
    embed.set_footer(text="Real-time monitoring every 5 seconds")
    
    await ctx.send(embed=embed)


# ================= EVENTS =================
@client.event
async def on_ready():
    """Called when bot is ready"""
    print("=" * 60)
    print(f"✓ Logged in as {client.user}")
    print(f"✓ Bot ID: {client.user.id}")
    print(f"✓ Connected to {len(client.guilds)} guild(s)")
    print(f"✓ Monitoring: {CTFD_BASE_URL}")
    print(f"✓ Mode: REAL-TIME")
    print("=" * 60)
    
    # Validate configuration
    if not CTFD_BASE_URL or not CTFD_API_TOKEN:
        log("ERROR: CTFD_BASE_URL or CTFD_API_TOKEN not configured!")
        log("Please check your .env file")
        return
    
    if DISCORD_CHANNEL_ID == 0:
        log("ERROR: DISCORD_CHANNEL_ID not configured!")
        return

    # Set bot presence
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="Watching Hackfest0x09"
    )
    await client.change_presence(status=discord.Status.online, activity=activity)

    # Initialize aiohttp session
    client.session = aiohttp.ClientSession()
    log("HTTP session initialized")
    
    # Start the checking loop
    if not check_first_blood.is_running():
        check_first_blood.start()
        log(f"Real-time first blood monitor started (interval: {CHECK_INTERVAL}s)")


@client.event
async def on_disconnect():
    """Called when bot disconnects"""
    log("Bot disconnected")
    if hasattr(client, "session") and client.session:
        await client.session.close()
        log("HTTP session closed")


@client.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        log(f"Command error: {error}")


# ================= RUN =================
if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN not found in .env file!")
        exit(1)
    
    try:
        log("Starting First Blood Bot - Real-time Mode")
        client.run(DISCORD_BOT_TOKEN)
    except discord.LoginFailure:
        print("ERROR: Invalid Discord bot token!")
    except Exception as e:
        print(f"ERROR: Failed to start bot: {e}")