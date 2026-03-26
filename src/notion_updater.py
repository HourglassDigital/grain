"""Pulse Notion updater — appends extracted updates to the right Notion pages."""

import requests
from src.config import NOTION_TOKEN, NOTION_PAGES, DRY_RUN

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def append_updates(updates: dict, date_str: str) -> dict[str, bool]:
    """Append extracted updates to their respective Notion pages."""
    results = {}
    for page_key, items in updates.items():
        page_id = NOTION_PAGES.get(page_key)
        if not page_id:
            print(f"  Unknown page key: {page_key}")
            results[page_key] = False
            continue
        blocks = _build_blocks(items, date_str)
        if DRY_RUN:
            print(f"  [DRY RUN] Would append {len(blocks)} blocks to {page_key}")
            results[page_key] = True
            continue
        success = _append_blocks(page_id, blocks)
        results[page_key] = success
        status = "ok" if success else "FAIL"
        print(f"  [{status}] {page_key}: {len(items)} updates")
    return results


def _build_blocks(items: list[dict], date_str: str) -> list[dict]:
    """Convert update items into Notion API block objects."""
    blocks = []
    blocks.append({"object": "block", "type": "divider", "divider": {}})
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": f"Pulse Update -- {date_str}"}}],
            "color": "blue_background",
        },
    })
    for item in items:
        title = item.get("title", "Update")
        bullets = item.get("bullets", [])
        source = item.get("source_channel", "")
        importance = item.get("importance", "medium")
        color = {"high": "red_background", "medium": "default", "low": "gray_background"}.get(importance, "default")
        title_text = title
        if importance == "high":
            title_text = "[!] " + title_text
        if source:
            title_text += f" (#{source})"
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": title_text}, "annotations": {"bold": True}}],
                "color": color,
            },
        })
        for bullet in bullets:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": bullet[:2000]}}],
                },
            })
    return blocks


def _append_blocks(page_id: str, blocks: list[dict]) -> bool:
    """Append blocks to a Notion page using the API."""
    url = f"{NOTION_API}/blocks/{page_id}/children"
    for i in range(0, len(blocks), 100):
        batch = blocks[i : i + 100]
        response = requests.patch(url, headers=get_headers(), json={"children": batch})
        if response.status_code != 200:
            print(f"    Notion API error: {response.status_code} -- {response.text[:200]}")
            return False
    return True
