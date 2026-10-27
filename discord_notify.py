import time


def send_discord_notification(uid, status, ip, country, city, reason=""):
    try:
        from discord_bot import queue_log_message
        import discord

        color = 0x2ecc71 if status == "ALLOWED" else 0xe74c3c
        icon = "✅" if status == "ALLOWED" else "❌"

        embed = discord.Embed(
            title=f"{icon} Login {status}",
            color=color,
            timestamp=__import__("datetime").datetime.utcnow(),
        )
        embed.add_field(name="UID", value=f"`{uid or 'N/A'}`", inline=True)
        embed.add_field(name="Reason", value=reason or "N/A", inline=True)
        embed.add_field(name="IP", value=f"`{ip or 'Unknown'}`", inline=True)
        embed.add_field(name="Location", value=f"{city or '?'}, {country or '?'}", inline=True)
        embed.set_footer(text="Region Bypass Proxy")
        queue_log_message(embed=embed)
    except Exception:
        pass
