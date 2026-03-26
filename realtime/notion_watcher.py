"""Notion → Slack sync — polls Notion pages for changes and posts updates."""

import time
import threading
import requests
import anthropic
from slack_sdk import WebClient

from realtime.config import (
    SLACK_BOT_TOKEN, NOTION_TOKEN, ANTHROPIC_API_KEY, MODEL,
    NOTION_PAGES, NOTION_TO_SLACK, NOTION_POLL_INTERVAL, PULSE_BOT_ID,
)

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _get_notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
    }


def _get_page_meta(page_id: str) -> dict:
    """Get page metadata including last_edited_time and last_edited_by."""
    try:
        resp = requests.get(f"{NOTION_API}/pages/{page_id}", headers=_get_notion_headers())
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def _fetch_recent_blocks(page_id: str, limit: int = 20) -> str:
    """Fetch the most recent blocks from a Notion page."""
    try:
        resp = requests.get(
            f"{NOTION_API}/blocks/{page_id}/children?page_size={limit}",
            headers=_get_notion_headers(),
        )
        if resp.status_code != 200:
            return ""
        blocks = resp.json().get("results", [])
        texts = []
        for block in blocks[-limit:]:
            block_type = block.get("type", "")
            content = block.get(block_type, {})
            rich_text = content.get("rich_text", [])
            for rt in rich_text:
                texts.append(rt.get("plain_text", ""))
        return "\n".join(texts)
    except Exception:
        return ""


DIFF_PROMPT = """A Notion page was just edited. Based on the most recent content blocks, write a 1-2 sentence Slack summary of what changed.

Page: {page_name}
Recent content:
{content}

If it looks like a Pulse automated update (contains "Pulse Update" or "Action Items"), respond with exactly "PULSE_UPDATE" and nothing else — we don't announce our own updates.

Otherwise write a concise update message for Slack. Use Slack markdown."""


def _summarize_change(page_key: str, content: str) -> str:
    """Use Claude to summarize what changed on a Notion page."""
    try:
        ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = ai.messages.create(
            model=MODEL,
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": DIFF_PROMPT.format(page_name=page_key, content=content[:2000]),
            }],
        )
        text = response.content[0].text.strip()
        if text == "PULSE_UPDATE":
            return None
        return text
    except Exception:
        return None


def start_watcher():
    """Start the Notion polling loop in a background thread."""
    thread = threading.Thread(target=_poll_loop, daemon=True)
    thread.start()
    print(f"  Notion watcher started (every {NOTION_POLL_INTERVAL}s)")


# Track last edit times
_last_edited = {}


def _poll_loop():
    """Poll Notion pages for changes."""
    client = WebClient(token=SLACK_BOT_TOKEN)

    # Initialize last_edited times
    for page_key, page_id in NOTION_PAGES.items():
        if page_key in ("home", "recommendations"):
            continue
        meta = _get_page_meta(page_id)
        if meta:
            _last_edited[page_key] = meta.get("last_edited_time", "")

    while True:
        time.sleep(NOTION_POLL_INTERVAL)

        for page_key, page_id in NOTION_PAGES.items():
            if page_key in ("home", "recommendations"):
                continue

            meta = _get_page_meta(page_id)
            if not meta:
                continue

            current_edit = meta.get("last_edited_time", "")
            previous_edit = _last_edited.get(page_key, "")

            if current_edit and current_edit != previous_edit:
                _last_edited[page_key] = current_edit

                # Skip if we don't have a previous time (first run)
                if not previous_edit:
                    continue

                # Fetch recent content and summarize
                content = _fetch_recent_blocks(page_id)
                summary = _summarize_change(page_key, content)

                if summary and page_key in NOTION_TO_SLACK:
                    channel_id = NOTION_TO_SLACK[page_key]
                    page_labels = {
                        "history": "Company History",
                        "tools": "Internal Tools",
                        "products": "Products & Services",
                        "ideas": "Product Ideas",
                        "learnings": "Learnings",
                        "tech_stack": "Tech Stack",
                        "team": "Team",
                    }
                    label = page_labels.get(page_key, page_key)

                    try:
                        client.chat_postMessage(
                            channel=channel_id,
                            text=f":zap: *Notion updated — {label}*\n\n{summary}",
                            unfurl_links=False,
                        )
                        print(f"  Notion change: {page_key} → #{channel_id}")
                    except Exception as e:
                        print(f"  Failed to post Notion change: {e}")
