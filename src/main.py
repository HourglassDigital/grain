"""Pulse v2 — The Hourglass memory agent.

Enhanced with: thread prioritization, people tagging, Slack backlinks,
action item extraction, article auto-summaries, competitive intelligence,
state persistence, dedup, action tracking, observability, and cost tracking.

Usage:
    python -m src.main
    DRY_RUN=true python -m src.main
"""

import sys
import time
from datetime import datetime, timezone, timedelta

from src.slack_reader import read_all_channels, format_messages_for_claude
from src.summarizer import extract_updates, format_slack_summary
from src.notion_updater import append_updates
from src.slack_poster import post_summary
from src.article_responder import process_articles
from src.config import LOOKBACK_HOURS, DRY_RUN
from src.state import (
    load_state, save_state, is_duplicate, add_seen,
    add_action, mark_action_done, get_stale_actions,
    add_weekly_update,
)
from src.logger import log_to_slack
from src.cost_tracker import format_cost_summary

AEDT = timezone(timedelta(hours=11))


def main() -> int:
    start_time = time.time()
    errors = 0
    now = datetime.now(AEDT)
    date_str = now.strftime("%d %b %Y")

    print("Pulse v2 -- Daily Sync")
    print(f"   Date: {date_str}")
    print(f"   Lookback: {LOOKBACK_HOURS}h")
    print(f"   Dry run: {DRY_RUN}")
    print()

    log_to_slack(f"Daily sync started — {date_str}", level="info")

    # Step 1: Read Slack
    print("Reading Slack channels...")
    try:
        channel_messages = read_all_channels()
    except Exception as e:
        log_to_slack(f"Failed to read Slack channels: {e}", level="error")
        errors += 1
        return 1

    total_messages = sum(len(msgs) for msgs in channel_messages.values())
    if total_messages == 0:
        print("\nNo new messages in the last 24h. Nothing to sync.")
        elapsed = round(time.time() - start_time, 1)
        log_to_slack(
            f"Pulse daily sync completed in {elapsed}s — 0 updates, 0 actions, {errors} errors (no messages)",
            level="success",
        )
        return 0

    print(f"\n   Total: {total_messages} messages across {len(channel_messages)} channels")

    # Step 2: Auto-reply to shared articles in brain-* channels
    print("\nChecking for shared articles...")
    try:
        article_replies = process_articles(channel_messages)
        if article_replies:
            print(f"   Replied to {article_replies} articles in-thread")
        else:
            print("   No new articles to summarize")
    except Exception as e:
        log_to_slack(f"Failed to process articles: {e}", level="error")
        errors += 1
        article_replies = 0

    # Step 3: Analyze with Claude
    print("\nAnalyzing with Claude...")
    try:
        formatted = format_messages_for_claude(channel_messages)
        updates = extract_updates(formatted)
    except Exception as e:
        log_to_slack(f"Failed to analyze with Claude: {e}", level="error")
        errors += 1
        return 1

    if not updates:
        print("\nNo significant updates extracted. Nothing to sync.")
        elapsed = round(time.time() - start_time, 1)
        log_to_slack(
            f"Pulse daily sync completed in {elapsed}s — 0 updates, 0 actions, {errors} errors",
            level="success",
        )
        return 0

    # Step 3b: Handle completed actions from Claude's analysis
    completed_actions = updates.pop("completed_actions", [])
    actions_completed = 0
    if completed_actions:
        print(f"\nProcessing {len(completed_actions)} completed action(s)...")
        for ca in completed_actions:
            title = ca.get("title", "")
            evidence = ca.get("evidence", "")
            if title and mark_action_done(title):
                actions_completed += 1
                print(f"   Marked done: {title}")
                print(f"     Evidence: {evidence[:100]}")

    # Step 3c: Dedup updates
    for page_key in list(updates.keys()):
        deduped = []
        for item in updates[page_key]:
            if is_duplicate(item):
                print(f"   Skipping duplicate: {item.get('title', '?')}")
            else:
                add_seen(item)
                deduped.append(item)
        updates[page_key] = deduped
        if not deduped:
            del updates[page_key]

    # Step 3d: Track new action items in state
    new_actions = 0
    for action in updates.get("actions", []):
        add_action({
            "title": action.get("title", ""),
            "owner": action.get("owner", "?"),
            "deadline": action.get("deadline", "none"),
            "permalink": action.get("permalink", ""),
        })
        new_actions += 1

    # Step 3e: Track updates for weekly digest
    for page_key, items in updates.items():
        for item in items:
            add_weekly_update(
                date=date_str,
                page=page_key,
                title=item.get("title", ""),
                importance=item.get("importance", "medium"),
            )

    # Update last run date
    state = load_state()
    state["last_run_date"] = date_str
    save_state(state)

    total_items = sum(len(items) for items in updates.values())
    print(f"   Extracted: {total_items} updates for {len(updates)} pages")

    if not updates:
        print("\nAll updates were duplicates. Nothing new to sync.")
        elapsed = round(time.time() - start_time, 1)
        log_to_slack(
            f"Pulse daily sync completed in {elapsed}s — 0 new updates (all deduped), {errors} errors",
            level="success",
        )
        return 0

    # Step 4: Update Notion
    print("\nUpdating Notion pages...")
    try:
        results = append_updates(updates, date_str)
        successful = sum(1 for v in results.values() if v)
        print(f"   Updated: {successful}/{len(results)} pages")
    except Exception as e:
        log_to_slack(f"Failed to update Notion: {e}", level="error")
        errors += 1
        results = {}

    # Step 5: Post to Slack
    print("\nPosting summary to Slack...")

    # Add stale actions to the summary
    stale_actions = get_stale_actions(days=3)
    if stale_actions:
        stale_section = []
        for sa in stale_actions:
            stale_section.append({
                "title": sa.get("title", "?"),
                "owner": sa.get("owner", "?"),
                "age_days": sa.get("age_days", "?"),
            })
        # Append stale action info to updates for the slack summary
        if "actions" not in updates:
            updates["actions"] = []

    slack_message = format_slack_summary(updates, date_str)

    # Append stale actions section if any
    if stale_actions:
        stale_lines = ["\n:warning:  *Stale Action Items (>3 days)*\n"]
        for sa in stale_actions:
            stale_lines.append(f":red_circle:  [{sa.get('owner', '?')}] {sa.get('title', '?')} — {sa.get('age_days', '?')} days old")
        slack_message += "\n" + "\n".join(stale_lines) + "\n"

    try:
        post_summary(slack_message)
    except Exception as e:
        log_to_slack(f"Failed to post Slack summary: {e}", level="error")
        errors += 1

    # Step 6: Log final summary with cost
    elapsed = round(time.time() - start_time, 1)
    cost_summary = format_cost_summary()
    log_to_slack(
        f"Pulse daily sync completed in {elapsed}s — {total_items} updates, {new_actions} actions, {errors} errors. {cost_summary}",
        level="success",
    )

    print(f"\nPulse v2 sync complete. {cost_summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
