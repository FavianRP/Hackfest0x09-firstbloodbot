# -*- coding: utf-8 -*-
import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta, timezone
import aiohttp
import csv
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

CTFD_API_KEY = os.getenv("CTFD_API_KEY")
CTFD_API_URL = os.getenv("CTFD_API_URL")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MESSAGE_THUMBNAIL = os.getenv("MESSAGE_THUMBNAIL")

CHECK_INTERVAL = 5 

# ---------- DISCORD INTENTS ----------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

client = commands.Bot(command_prefix="!", intents=intents)

FIRST_BLOOD_FILE = "announced_first_bloods.csv"
first_blood_announced = set()


def log(msg):
    print(f"[DEBUG] {msg}")


def load_first_bloods_from_csv():
    if os.path.isfile(FIRST_BLOOD_FILE):
        with open(FIRST_BLOOD_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].isdigit():
                    first_blood_announced.add(int(row[0]))
    log(f"Loaded announced first-blood IDs: {first_blood_announced}")


def save_first_blood_to_csv(challenge_id):
    with open(FIRST_BLOOD_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([challenge_id])


# ------------------- FETCH CHALLENGES -------------------
async def fetch_challenge_list():
    headers = {"Authorization": f"Token {CTFD_API_KEY}"}

    log(f"Fetching challenge list from: {CTFD_API_URL}")

    try:
        async with client.session.get(CTFD_API_URL, headers=headers) as r:
            log(f"Challenge list status: {r.status}")
            if r.status != 200:
                text = await r.text()
                log(f"Challenge API error: {text}")
                return []

            data = await r.json()
            log(f"Fetched {len(data.get('data', []))} challenges")
            return data.get("data", [])

    except Exception as e:
        log(f"Exception fetching challenges: {e}")
        return []


# ------------------- FETCH SOLVES -------------------
async def fetch_solves_for_challenge(cid):
    solves_url = f"{CTFD_API_URL}/{cid}/solves"
    headers = {"Authorization": f"Token {CTFD_API_KEY}"}

    log(f"Fetching solves from: {solves_url}")

    try:
        async with client.session.get(solves_url, headers=headers) as r:
            log(f"Solves status: {r.status}")
            if r.status != 200:
                text = await r.text()
                log(f"Solves API error: {text}")
                return []

            data = await r.json()
            solves = data.get("data", [])
            log(f"Challenge {cid} solves: {len(solves)}")
            return solves

    except Exception as e:
        log(f"Exception fetching solves: {e}")
        return []


# ------------------- FIRST BLOOD CHECK LOOP -------------------
@tasks.loop(seconds=CHECK_INTERVAL)
async def check_first_blood():
    log("Checking for first bloods...")

    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if channel is None:
        log("ERROR: Channel not found — check DISCORD_CHANNEL_ID!")
        return

    challenges = await fetch_challenge_list()

    for chal in challenges:
        cid = chal["id"]
        cname = chal["name"]

        log(f"Checking challenge {cid} ({cname})")

        if cid in first_blood_announced:
            log(f"Already announced: {cid}, skipping")
            continue

        solves = await fetch_solves_for_challenge(cid)

        if not solves:
            log(f"No solves for {cid}")
            continue

        # FIRST BLOOD FOUND
        fb = solves[0]
        user = fb.get("name", "Unknown")
        # Parse UTC time dari CTFd
        utc_time = datetime.strptime(fb["date"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)

        # Konversi ke WIB (UTC+7)
        wib = utc_time.astimezone(timezone(timedelta(hours=7)))
        time_solved = wib.strftime("%d/%m/%Y %H:%M:%S")

        log(f"FIRST BLOOD for {cid} by {user} at {time_solved}")

        message = (
            f"🩸 First blood for **{cname}** "
            f"goes to **{user}**! 🩸\n"
            f"🕒 Time: `{time_solved}`"
)
        await channel.send(message)

        first_blood_announced.add(cid)
        save_first_blood_to_csv(cid)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    
    # Set bot activity
    activity = discord.Activity(type=discord.ActivityType.watching, name=" Watching Hackfest0x09")
    await client.change_presence(status=discord.Status.online, activity=activity)

    # Create aiohttp session
    client.session = aiohttp.ClientSession()

    # Load previously announced first bloods
    load_first_bloods_from_csv()

    # Start first blood checking loop
    check_first_blood.start()


@client.event
async def on_disconnect():
    if hasattr(client, "session"):
        await client.session.close()


client.run(DISCORD_BOT_TOKEN)
