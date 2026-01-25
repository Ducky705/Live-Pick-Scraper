import json
import collections
from collections import Counter

OUTPUT_FILE = r"D:\Programs\Sports Betting\TelegramScraper\v0.0.15\data\output\verified_messages_2026-01-24.json"


def generate_report():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            messages = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {OUTPUT_FILE}")
        return

    stats = {
        "discord": Counter(),
        "twitter": Counter(),
        "telegram": Counter(),
        "unknown": Counter(),
    }

    total_msgs = len(messages)

    for msg in messages:
        source = msg.get("source", "unknown").lower()
        channel = msg.get("channel_name", "Unknown Channel")

        if source in stats:
            stats[source][channel] += 1
        else:
            stats["unknown"][channel] += 1

    print("=" * 60)
    print(f"  SCRAPING REPORT - {len(messages)} Total Messages")
    print("=" * 60)

    # Discord
    print(f"\n[DISCORD] Total: {sum(stats['discord'].values())}")
    for channel, count in stats["discord"].most_common():
        print(f"  - {channel}: {count}")

    # Telegram
    print(f"\n[TELEGRAM] Total: {sum(stats['telegram'].values())}")
    for channel, count in stats["telegram"].most_common():
        print(f"  - {channel}: {count}")

    # Twitter
    print(f"\n[TWITTER] Total: {sum(stats['twitter'].values())}")
    for channel, count in stats["twitter"].most_common():
        print(f"  - {channel}: {count}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    generate_report()
