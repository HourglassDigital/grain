"""Pulse weekly digest — generates a week-in-review summary and posts to Slack.

Usage:
    python -m src.weekly_digest
"""

import sys
import json
from datetime import datetime, timezone, timedelta

from src.state import get_weekly_updates, get_open_actions, get_stale_actions, load_state
from src.cost_tracker import get_tracked_client, record_usage, format_cost_summary
from src.logger import log_to_slack
from src.config import MODEL, MAX_TOKENS, SLACK_BOT_TOKEN, POSTING_CHANNEL_ID, DRY_RUN
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

AEDT = timezone(timedelta(hours=11))

DIGEST_SYSTEM_PROMPT = """You are Pulse, the Hourglass Digital memory agent. You are generating a weekly digest of everything that happened this week.

Given a list of updates captured throughout the week, produce a structured week-in-review.

Return a JSON object with:
- "decisions": Array of key decisions made (strings, each including who and when)
- "tools_shipped": Array of tools/features shipped (strings)
- "pipeline_movement": A short summary of pipeline/revenue movement, or "No significant movement" if none
- "momentum": A one-line assessment of the team's momentum this week
- "highlights": Array of 2-3 most important things that happened

Keep it concise. Focus on what matters strategically.
Return ONLY valid JSON, no markdown code fences.
"""


def generate_digest() -> str:
    """Generate the weekly digest message."""
    now = datetime.now(AEDT)
    week_ago = now - timedelta(days=7)
    date_range = f"{week_ago.strftime('%d %b')} - {now.strftime('%d %b %Y')}"

    # Gather data
    weekly_updates = get_weekly_updates(days=7)
    open_actions = get_open_actions()
    stale_actions = get_stale_actions(days=3)
    state = load_state()

    # Count completed actions this week
    completed_this_week = 0
    for action in state.get("action_items", []):
        if action.get("done") and action.get("completed_date"):
            try:
                completed_dt = datetime.fromisoformat(action["completed_date"])
                if (now - completed_dt).days <= 7:
                    completed_this_week += 1
            except (ValueError, TypeError):
                pass

    if not weekly_updates:
        return (
            f":zap: Pulse -- Week in Review ({date_range})\n\n"
            f"No updates captured this week. Pulse had nothing to sync."
        )

    # Use Claude to analyze the week
    updates_text = json.dumps(weekly_updates, indent=2)
    client = get_tracked_client()

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=DIGEST_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Here are all the updates from this week:\n\n{updates_text}"}],
        )
        record_usage(response)
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        analysis = json.loads(text)
    except Exception as e:
        print(f"  Failed to analyze week with Claude: {e}")
        analysis = {
            "decisions": [],
            "tools_shipped": [],
            "pipeline_movement": "Unable to analyze",
            "momentum": "Unable to assess",
            "highlights": [],
        }

    # Count by type
    decisions = analysis.get("decisions", [])
    tools_shipped = analysis.get("tools_shipped", [])
    pipeline_movement = analysis.get("pipeline_movement", "No significant movement")
    momentum = analysis.get("momentum", "Steady")

    # Build the message
    lines = [f":zap: Pulse -- Week in Review ({date_range})"]
    lines.append("")
    lines.append("---")
    lines.append("")

    # Numbers section
    lines.append(":bar_chart:  *This Week by the Numbers*")
    lines.append(f"  :small_blue_diamond:  {len(decisions)} decisions captured")
    lines.append(f"  :small_blue_diamond:  {len(tools_shipped)} tools/features shipped")
    lines.append(f"  :small_blue_diamond:  {pipeline_movement}")
    lines.append(f"  :small_blue_diamond:  {len(open_actions)} action items opened, {completed_this_week} completed, {len(stale_actions)} stale")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Key decisions
    if decisions:
        lines.append(":key:  *Key Decisions*")
        for d in decisions:
            lines.append(f"  :small_orange_diamond:  {d}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Stale actions
    if stale_actions:
        lines.append(":warning:  *Stale Action Items*")
        for sa in stale_actions:
            owner = sa.get("owner", "?")
            title = sa.get("title", "?")
            age = sa.get("age_days", "?")
            lines.append(f"  :red_circle:  [{owner}] {title} -- {age} days old")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Momentum
    lines.append(f":chart_with_upwards_trend:  *Momentum:* {momentum}")
    lines.append("")
    lines.append(f"_{format_cost_summary()}_")
    lines.append("_Every pulse counts._ :zap:")

    return "\n".join(lines)


def post_digest(message: str) -> bool:
    """Post the weekly digest to #--internal-tooling."""
    if DRY_RUN:
        print(f"[DRY RUN] Would post weekly digest:\n{message}")
        return True

    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        client.chat_postMessage(
            channel=POSTING_CHANNEL_ID,
            text=message,
            unfurl_links=False,
            unfurl_media=False,
        )
        print("  Posted weekly digest to #--internal-tooling")
        return True
    except SlackApiError as e:
        print(f"  Failed to post digest: {e.response['error']}")
        return False


def main() -> int:
    print("Pulse -- Weekly Digest")
    print()

    log_to_slack("Weekly digest generation started", level="info")

    digest = generate_digest()
    print("\n--- DIGEST ---")
    print(digest)
    print("--- END ---\n")

    success = post_digest(digest)

    if success:
        log_to_slack("Weekly digest posted successfully", level="success")
    else:
        log_to_slack("Failed to post weekly digest", level="error")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
