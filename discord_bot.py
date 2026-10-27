import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import threading
import sqlite3
from typing import Optional

from config import DISCORD_BOT_TOKEN, DISCORD_LOG_CHANNEL_ID, TARGET_REGION
from database import (
    add_uid, remove_uid, get_all_uids, check_uid, get_stats,
    DB_FILE, inc_stat, log_login, lookup_geo,
)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

_log_queue = []
_log_lock = threading.Lock()


def queue_log_message(content=None, embed=None):
    with _log_lock:
        _log_queue.append((content, embed))


async def _log_worker():
    await bot.wait_until_ready()
    while True:
        items = []
        with _log_lock:
            items.extend(_log_queue)
            _log_queue.clear()
        for content, embed in items:
            try:
                channel = bot.get_channel(DISCORD_LOG_CHANNEL_ID)
                if channel:
                    await channel.send(content=content, embed=embed)
            except Exception:
                pass
        await asyncio.sleep(1)


@bot.event
async def on_ready():
    bot.loop.create_task(_log_worker())
    await bot.change_presence(
        activity=discord.Game(name="commands | /help")
    )
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"[Discord Bot] Synced {len(synced)} commands to guild: {guild.name}")
    except Exception as e:
        print(f"[Discord Bot] Failed to sync commands: {e}")
    print(f"[Discord Bot] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"[Discord Bot] Connected to {len(bot.guilds)} server(s)")


@bot.tree.command(name="help", description="Show all available commands")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Region Bypass Bot",
        description="Manage UID whitelist for the region bypass proxy.",
        color=0xf1c40f,
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.add_field(
        name="Whitelist Commands",
        value=(
            "`/whitelist <uid> [duration]` — Add UID (lifetime or hours)\n"
            "`/unwhitelist <uid>` — Remove UID\n"
            "`/whitelisted` — List all whitelisted UIDs\n"
            "`/check <uid>` — Check if a UID is authorized\n"
        ),
        inline=False,
    )
    embed.add_field(
        name="Info Commands",
        value=(
            "`/stats` — Login statistics\n"
            "`/logs [uid]` — Recent login logs\n"
            "`/status` — Quick bot status\n"
        ),
        inline=False,
    )
    embed.set_footer(text="Only server admins can manage whitelist")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="status", description="Quick bot status")
async def slash_status(interaction: discord.Interaction):
    s = get_stats()
    embed = discord.Embed(title="Bot Status", color=0x2ecc71)
    embed.add_field(name="Proxy", value="Running", inline=True)
    embed.add_field(name="Bot", value="Online", inline=True)
    embed.add_field(name="Whitelisted UIDs", value=s["whitelist_count"], inline=True)
    embed.add_field(name="Total Logins", value=s["stats"].get("total", 0), inline=True)
    embed.add_field(name="Allowed", value=s["stats"].get("allowed", 0), inline=True)
    embed.add_field(name="Blocked", value=s["stats"].get("blocked", 0), inline=True)
    embed.set_footer(text=f"Region: {TARGET_REGION}")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="whitelist", description="Add a UID to the whitelist")
@app_commands.describe(uid="The UID to whitelist", duration="Lifetime or hours (default: lifetime)")
@app_commands.choices(duration=[
    app_commands.Choice(name="Lifetime", value="lifetime"),
    app_commands.Choice(name="24 hours", value="24"),
    app_commands.Choice(name="48 hours", value="48"),
    app_commands.Choice(name="72 hours", value="72"),
    app_commands.Choice(name="1 week", value="168"),
])
async def slash_whitelist(interaction: discord.Interaction, uid: str, duration: Optional[app_commands.Choice[str]] = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need Administrator permission.", ephemeral=True)
        return
    if not uid.isdigit():
        await interaction.response.send_message("UID must be a number.", ephemeral=True)
        return
    dur = duration.value if duration else "lifetime"
    add_uid(uid, TARGET_REGION, dur)
    duration_text = "Lifetime" if dur == "lifetime" else f"{dur} hours"
    embed = discord.Embed(title="UID Whitelisted", color=0x2ecc71)
    embed.add_field(name="UID", value=f"`{uid}`", inline=True)
    embed.add_field(name="Region", value=TARGET_REGION, inline=True)
    embed.add_field(name="Duration", value=duration_text, inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="unwhitelist", description="Remove a UID from the whitelist")
@app_commands.describe(uid="The UID to remove")
async def slash_unwhitelist(interaction: discord.Interaction, uid: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need Administrator permission.", ephemeral=True)
        return
    if not uid.isdigit():
        await interaction.response.send_message("UID must be a number.", ephemeral=True)
        return
    remove_uid(uid)
    embed = discord.Embed(title="UID Removed", color=0xe74c3c)
    embed.add_field(name="UID", value=f"`{uid}`", inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="whitelisted", description="List all whitelisted UIDs")
async def slash_whitelisted(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need Administrator permission.", ephemeral=True)
        return
    uids = get_all_uids()
    if not uids:
        embed = discord.Embed(title="Whitelisted UIDs", description="No UIDs in whitelist.", color=0x95a5a6)
        await interaction.response.send_message(embed=embed)
        return
    embed = discord.Embed(title=f"Whitelisted UIDs ({len(uids)})", color=0x3498db)
    lines = []
    for i, entry in enumerate(uids[:30], 1):
        exp = "Never" if entry["expires_at"] == 0 else f"<t:{entry['expires_at']}:R>"
        lines.append(f"**{i}.** `{entry['uid']}` — {entry['region']} — {exp}")
    embed.description = "\n".join(lines)
    if len(uids) > 30:
        embed.set_footer(text=f"Showing 30 of {len(uids)} UIDs")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="check", description="Check if a UID is whitelisted")
@app_commands.describe(uid="The UID to check")
async def slash_check(interaction: discord.Interaction, uid: str):
    if not uid.isdigit():
        await interaction.response.send_message("UID must be a number.", ephemeral=True)
        return
    sub = check_uid(uid)
    if sub["valid"]:
        embed = discord.Embed(title="UID Authorized", color=0x2ecc71)
        embed.add_field(name="UID", value=f"`{uid}`", inline=True)
        embed.add_field(name="Status", value=f"Whitelisted ({sub['reason']})", inline=True)
    else:
        embed = discord.Embed(title="UID Not Authorized", color=0xe74c3c)
        embed.add_field(name="UID", value=f"`{uid}`", inline=True)
        embed.add_field(name="Status", value=f"{sub['reason']}", inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="stats", description="Show login statistics")
async def slash_stats(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need Administrator permission.", ephemeral=True)
        return
    s = get_stats()
    embed = discord.Embed(title="Login Statistics", color=0x9b59b6)
    embed.add_field(name="Whitelisted", value=s["whitelist_count"], inline=True)
    embed.add_field(name="Blacklisted", value=s["blacklist_count"], inline=True)
    embed.add_field(name="Total Logins", value=s["stats"].get("total", 0), inline=True)
    embed.add_field(name="Allowed", value=s["stats"].get("allowed", 0), inline=True)
    embed.add_field(name="Blocked", value=s["stats"].get("blocked", 0), inline=True)
    allowed = s["stats"].get("allowed", 0)
    total = s["stats"].get("total", 0)
    rate = f"{(allowed/total*100):.1f}%" if total > 0 else "N/A"
    embed.add_field(name="Allow Rate", value=rate, inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="logs", description="Show recent login logs")
@app_commands.describe(uid="Filter by specific UID")
async def slash_logs(interaction: discord.Interaction, uid: Optional[str] = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need Administrator permission.", ephemeral=True)
        return
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    if uid:
        cur.execute(
            "SELECT uid, ip, country, city, ts, status FROM login_logs WHERE uid=? ORDER BY id DESC LIMIT 10",
            (uid,),
        )
    else:
        cur.execute(
            "SELECT uid, ip, country, city, ts, status FROM login_logs ORDER BY id DESC LIMIT 10"
        )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        embed = discord.Embed(title="Login Logs", description="No logs found.", color=0x95a5a6)
        await interaction.response.send_message(embed=embed)
        return

    title = "Recent Logins" + (f" — `{uid}`" if uid else "")
    embed = discord.Embed(title=title, color=0x3498db)
    lines = []
    for row in rows:
        log_uid, ip, country, city, ts, status = row
        t = f"<t:{ts}:R>" if ts else "?"
        icon = "\u2705" if "ALLOWED" in status else "\u274c"
        lines.append(f"{icon} `{log_uid}` — {status}\n       IP: `{ip}` | {city}, {country} | {t}")
    embed.description = "\n\n".join(lines)
    await interaction.response.send_message(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    pass


def start_bot():
    try:
        bot.run(DISCORD_BOT_TOKEN)
    except discord.errors.PrivilegedIntentsRequired:
        print("[Discord Bot] ERROR: Enable MESSAGE CONTENT INTENT in Discord Developer Portal")
    except discord.errors.LoginFailure:
        print("[Discord Bot] ERROR: Invalid bot token.")
    except Exception as e:
        print(f"[Discord Bot] ERROR: {e}")


if __name__ == "__main__":
    start_bot()
