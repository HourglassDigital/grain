"""Pulse v2 — The Hourglass memory agent.

Enhanced with: thread prioritization, people tagging, Slack backlinks,
action item extraction, article auto-summaries, and competitive intelligence.

Usage:
    python -m src.main
    DRY_RUN=true python -m src.main
"""

import sys
from datetime import datetime, timezone, timedelta

from src.slack_reader import read_all_channels, format_messages_for_claude
from src.summarizer import extract_updates, format_slack_summary
from src.notion_updater import append_updates
from src.slack_poster import post_summary
from src.article_responder import process_articles
from src.config import LOOKBACK_HOURS, DRY_RUN

AEDT = timezone(timedelta(hours=11))


def main() -> int:
    now = datetime.now(AEDT)
    date_str = now.strftime("%d %b %Y")

    print("Pulse v2 -- Daily Sync")
    print(f"   Date: {date_str}")
    print(f"   Lookback: {LOOKBACK_HOURS}h")
    print(f"   Dry run: {DRY_RUN}")
    print()

    # Step 1: Read Slack
    print("Reading Slack channels...")
    channel_messages = read_all_channels()

    total_messages = sum(len(msgs) for msgs in channel_messages.values())
    if total_messages == 0:
        print("\nNo new messages in the last 24h. Nothing to sync.")
        return 0

    print(f"\n   Total: {total_messages} messages across {len(channel_messages)} channels")

    # Step 2: Auto-reply to shared articles in brain-* channels
    print("\nChecking for shared articles...")
    article_replies = process_articles(channel_messages)
    if article_replies:
        print(f"   Replied to {article_replies} articles in-thread")
    else:
        print("   No new articles to summarize")

    # Step 3: Analyze with Claude
    print("\nAnalyzing with Claude...")
    formatted = format_messages_for_claude(channel_messages)
    updates = extract_updates(formatted)

    if not updates:
        print("\nNo significant updates extracted. Nothing to sync.")
        return 0

    total_items = sum(len(items) for items in updates.values())
    print(f"   Extracted: {total_items} updates for {len(updates)} pages")

    # Step 4: Update Notion
    print("\nUpdating Notion pages...")
    results = append_updates(updates, date_str)

    successful = sum(1 for v in results.values() if v)
    print(f"   Updated: {successful}/{len(results)} pages")

    # Step 5: Post to Slack
    print("\nPosting summary to Slack...")
    slack_message = format_slack_summary(updates, date_str)
    post_summary(slack_message)

    print("\nPulse v2 sync complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
