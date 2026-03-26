"""Granola meeting sync — polls for new meetings, syncs to Notion + Slack."""

import time
import threading
import requests
import anthropic
from slack_sdk import WebClient
from datetime import datetime, timezone, timedelta

from realtime.config import (
    SLACK_BOT_TOKEN, NOTION_TOKEN, ANTHROPIC_API_KEY, GRANOLA_API_KEY,
    MODEL, NOTION_PAGES, PROJECT_CHANNELS, GRANOLA_POLL_INTERVAL,
)

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
GRANOLA_API = "https://api.granola.ai/v1"

# Track seen meeting IDs
_seen_meetings = set()


def _get_notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _get_granola_headers():
    return {
        "Authorization": f"Bearer {GRANOLA_API_KEY}",
        "Content-Type": "application/json",
    }


def _fetch_recent_meetings() -> list[dict]:
    """Fetch meetings from the last 24 hours via Granola API."""
    if not GRANOLA_API_KEY:
        return []

    try:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        resp = requests.get(
            f"{GRANOLA_API}/meetings",
            headers=_get_granola_headers(),
            params={"since": since, "limit": 20},
        )
        if resp.status_code == 200:
            return resp.json().get("meetings", [])
    except Exception as e:
        print(f"  Granola API error: {e}")
    return []


def _get_meeting_details(meeting_id: str) -> dict:
    """Fetch full meeting details including summary and transcript."""
    if not GRANOLA_API_KEY:
        return None

    try:
        resp = requests.get(
            f"{GRANOLA_API}/meetings/{meeting_id}",
            headers=_get_granola_headers(),
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


MEETING_PROMPT = """You are Pulse, the Hourglass Digital meeting agent.

Summarize this client meeting for the team. Extract:
1. Key decisions made
2. Action items (who, what, deadline if any)
3. Next steps
4. Any pricing or deal details mentioned

Meeting: {title}
Attendees: {attendees}
Date: {date}

Summary/Notes:
{summary}

Format as a clean Slack message with bold headers and bullet points.
Keep it concise — the team should be able to read this in 30 seconds."""


def _match_project_channel(meeting: dict) -> str:
    """Try to match a meeting to a project channel by title or attendees."""
    title = meeting.get("title", "").lower()
    attendees = " ".join(a.get("name", "") for a in meeting.get("attendees", [])).lower()
    combined = f"{title} {attendees}"

    # Simple keyword matching
    if "blossom" in combined or "gaby" in combined:
        return PROJECT_CHANNELS.get("proj-blossom")
    if "mainsequence" in combined or "main sequence" in combined:
        return PROJECT_CHANNELS.get("proj-mainsequence")
    if "sos" in combined or "freya" in combined:
        return PROJECT_CHANNELS.get("proj-sos")

    return None


def _append_to_notion(page_id: str, meeting: dict, summary_text: str) -> bool:
    """Append meeting summary to a Notion page."""
    title = meeting.get("title", "Meeting")
    date = meeting.get("date", "")

    blocks = [
        {"object": "block", "type": "divider", "divider": {}},
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": f"Meeting: {title} — {date}"}}],
                "color": "green_background",
            },
        },
    ]

    for line in summary_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": line[:2000]}}],
            },
        })

    try:
        resp = requests.patch(
            f"{NOTION_API}/blocks/{page_id}/children",
            headers=_get_notion_headers(),
            json={"children": blocks},
        )
        return resp.status_code == 200
    except Exception:
        return False


def _process_meeting(meeting: dict) -> bool:
    """Process a single meeting: summarize, sync to Notion, post to Slack."""
    meeting_id = meeting.get("id", "")
    title = meeting.get("title", "Untitled")
    date = meeting.get("date", "")
    attendees = meeting.get("attendees", [])
    summary = meeting.get("summary", "") or meeting.get("notes", "")

    if not summary:
        details = _get_meeting_details(meeting_id)
        if details:
            summary = details.get("summary", "") or details.get("notes", "")

    if not summary:
        return False

    attendee_names = ", ".join(a.get("name", "?") for a in attendees)

    # Generate Slack-formatted summary
    try:
        ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = ai.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": MEETING_PROMPT.format(
                    title=title,
                    attendees=attendee_names,
                    date=date,
                    summary=summary[:3000],
                ),
            }],
        )
        formatted = response.content[0].text.strip()
    except Exception as e:
        print(f"  Meeting summarize error: {e}")
        return False

    # Match to project channel
    channel_id = _match_project_channel(meeting)
    slack_client = WebClient(token=SLACK_BOT_TOKEN)

    # Post to Slack
    if channel_id:
        try:
            slack_client.chat_postMessage(
                channel=channel_id,
                text=f":clipboard:  *Meeting Synced — {title}*\n\n{formatted}",
                unfurl_links=False,
            )
            print(f"  Meeting posted: {title} → project channel")
        except Exception as e:
            print(f"  Meeting Slack post failed: {e}")

    # Also post to #--general for visibility
    try:
        slack_client.chat_postMessage(
            channel="C0AMC0JVAPM",
            text=f":clipboard:  *Meeting — {title}* ({attendee_names})\n\n{formatted}",
            unfurl_links=False,
        )
    except Exception:
        pass

    # Append to Notion history page
    history_id = NOTION_PAGES.get("history")
    if history_id:
        _append_to_notion(history_id, meeting, formatted)
        print(f"  Meeting synced to Notion: {title}")

    return True


def start_syncer():
    """Start the Granola polling loop in a background thread."""
    if not GRANOLA_API_KEY:
        print("  Granola sync disabled (no API key)")
        return

    thread = threading.Thread(target=_poll_loop, daemon=True)
    thread.start()
    print(f"  Granola syncer started (every {GRANOLA_POLL_INTERVAL}s)")


def _poll_loop():
    """Poll Granola for new meetings."""
    while True:
        time.sleep(GRANOLA_POLL_INTERVAL)

        meetings = _fetch_recent_meetings()
        for meeting in meetings:
            meeting_id = meeting.get("id", "")
            if meeting_id in _seen_meetings:
                continue
            _seen_meetings.add(meeting_id)

            if _process_meeting(meeting):
                print(f"  Processed meeting: {meeting.get('title', '?')}")
