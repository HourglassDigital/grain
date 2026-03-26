"""Meeting prep agent — posts briefs 30 min before meetings."""

import time
import threading
import requests
import anthropic
from datetime import datetime, timezone, timedelta
from slack_sdk import WebClient

from realtime.config import (
    SLACK_BOT_TOKEN, ANTHROPIC_API_KEY, NOTION_TOKEN, MODEL,
    NOTION_PAGES, PROJECT_CHANNELS, USER_MAP,
)

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
GCAL_POLL_INTERVAL = 900  # 15 minutes
PREP_LEAD_TIME = 1800     # 30 minutes before meeting

# Track meetings we've already prepped
_prepped_meetings = set()


def _get_notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
    }


def _fetch_page_text(page_id):
    """Fetch text from a Notion page for context."""
    url = f"{NOTION_API}/blocks/{page_id}/children?page_size=50"
    try:
        resp = requests.get(url, headers=_get_notion_headers())
        if resp.status_code != 200:
            return ""
        blocks = resp.json().get("results", [])
        texts = []
        for block in blocks:
            bt = block.get("type", "")
            content = block.get(bt, {})
            for rt in content.get("rich_text", []):
                texts.append(rt.get("plain_text", ""))
        return "\n".join(texts)
    except Exception:
        return ""


def _match_meeting_to_channel(title, attendees_str):
    """Match a meeting to a project Slack channel."""
    combined = f"{title} {attendees_str}".lower()
    if "blossom" in combined or "gaby" in combined:
        return PROJECT_CHANNELS.get("proj-blossom")
    if "mainsequence" in combined or "main sequence" in combined:
        return PROJECT_CHANNELS.get("proj-mainsequence")
    if "sos" in combined or "freya" in combined:
        return PROJECT_CHANNELS.get("proj-sos")
    if "founderclaw" in combined:
        return "C0ANMQHL76U"
    return "C0AMC0JVAPM"  # Default to --general


PREP_PROMPT = """You are Pulse, the Hourglass Digital meeting prep agent.

Generate a concise meeting prep brief. Include:
1. Who's attending and their role/company
2. Relevant context from our Notion pages (deals, pricing, past decisions)
3. Key questions or topics to raise
4. Any open action items related to this client/project

Meeting: {title}
Time: {time}
Attendees: {attendees}

Context from Notion:
{context}

Format as a clean Slack message. Use bold headers, bullets. Keep it scannable — the team should read this in 30 seconds before the meeting starts."""


def _generate_prep(title, time_str, attendees, context):
    """Generate a meeting prep brief using Claude."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": PREP_PROMPT.format(
                    title=title,
                    time=time_str,
                    attendees=attendees,
                    context=context[:3000],
                ),
            }],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  Meeting prep generation failed: {e}")
        return None


def _get_upcoming_meetings():
    """Get meetings in the next 45 minutes.

    Note: This requires Google Calendar API access.
    For now, this uses a simple approach — if the Google Calendar MCP
    is not available in the realtime bot context, this will return
    an empty list and meeting prep will be handled by the Claude Code
    scheduled task instead.
    """
    # Placeholder: In production, integrate with Google Calendar API
    # The user has gcal access via Claude Code MCP but not in this bot
    # For now, return empty — meeting prep will be added as a Claude Code
    # scheduled task similar to granola sync
    return []


def start_prep_agent():
    """Start the meeting prep polling loop."""
    thread = threading.Thread(target=_poll_loop, daemon=True)
    thread.start()
    print(f"  Meeting prep agent started (every {GCAL_POLL_INTERVAL}s)")


def _poll_loop():
    """Poll for upcoming meetings and generate prep briefs."""
    slack = WebClient(token=SLACK_BOT_TOKEN)

    while True:
        time.sleep(GCAL_POLL_INTERVAL)

        meetings = _get_upcoming_meetings()
        for meeting in meetings:
            meeting_id = meeting.get("id", "")
            if meeting_id in _prepped_meetings:
                continue

            title = meeting.get("title", "Meeting")
            time_str = meeting.get("start_time", "")
            attendees = meeting.get("attendees", "")

            # Gather context from relevant Notion pages
            context_parts = []
            for page_key in ("history", "products", "learnings"):
                page_id = NOTION_PAGES.get(page_key)
                if page_id:
                    text = _fetch_page_text(page_id)
                    if text:
                        context_parts.append(f"=== {page_key} ===\n{text[:1000]}")

            context = "\n\n".join(context_parts)
            prep = _generate_prep(title, time_str, attendees, context)

            if prep:
                channel = _match_meeting_to_channel(title, attendees)
                try:
                    slack.chat_postMessage(
                        channel=channel,
                        text=f":calendar:  *Meeting Prep — {title}*\n_Starting at {time_str}_\n\n{prep}",
                        unfurl_links=False,
                    )
                    _prepped_meetings.add(meeting_id)
                    print(f"  Meeting prep posted: {title}")
                except Exception as e:
                    print(f"  Meeting prep post failed: {e}")
