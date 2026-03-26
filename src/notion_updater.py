"""Pulse v2 Notion updater — with backlinks to Slack and action item tracking."""

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

    # Action items go to the learnings page under a special section
    actions = updates.pop("actions", None)
    # Articles go to learnings too
    articles = updates.pop("articles", None)

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

    # Append actions to learnings page
    if actions:
        page_id = NOTION_PAGES.get("learnings")
        if page_id:
            blocks = _build_action_blocks(actions, date_str)
            if DRY_RUN:
                print(f"  [DRY RUN] Would append {len(blocks)} action blocks to learnings")
            else:
                success = _append_blocks(page_id, blocks)
                status = "ok" if success else "FAIL"
                print(f"  [{status}] actions: {len(actions)} items")
            results["actions"] = True

    # Append articles to learnings page
    if articles:
        page_id = NOTION_PAGES.get("learnings")
        if page_id:
            blocks = _build_article_blocks(articles, date_str)
            if DRY_RUN:
                print(f"  [DRY RUN] Would append {len(blocks)} article blocks to learnings")
            else:
                success = _append_blocks(page_id, blocks)
                status = "ok" if success else "FAIL"
                print(f"  [{status}] articles: {len(articles)} items")
            results["articles"] = True

    return results


def _build_blocks(items: list[dict], date_str: str) -> list[dict]:
    """Convert update items into Notion API block objects with backlinks."""
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
        permalink = item.get("permalink", "")
        importance = item.get("importance", "medium")
        people = item.get("people", [])

        color = {"high": "red_background", "medium": "default", "low": "gray_background"}.get(importance, "default")

        # Title with people attribution
        title_text = title
        if people:
            title_text += f" ({', '.join(people)})"
        if importance == "high":
            title_text = "[!] " + title_text

        # Title as paragraph — with link to source if available
        title_rich_text = []
        if permalink:
            title_rich_text.append({
                "type": "text",
                "text": {"content": title_text, "link": {"url": permalink}},
                "annotations": {"bold": True},
            })
        else:
            title_rich_text.append({
                "type": "text",
                "text": {"content": title_text},
                "annotations": {"bold": True},
            })

        if source:
            title_rich_text.append({
                "type": "text",
                "text": {"content": f" (#{source})"},
                "annotations": {"color": "gray"},
            })

        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": title_rich_text, "color": color},
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


def _build_action_blocks(actions: list[dict], date_str: str) -> list[dict]:
    """Build Notion blocks for action items as to-do checkboxes."""
    blocks = []
    blocks.append({"object": "block", "type": "divider", "divider": {}})
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": f"Action Items -- {date_str}"}}],
            "color": "red_background",
        },
    })

    for action in actions:
        owner = action.get("owner", "?")
        title = action.get("title", "Action")
        deadline = action.get("deadline", "none")
        permalink = action.get("permalink", "")

        text = f"[{owner}] {title}"
        if deadline != "none":
            text += f" (due: {deadline})"

        rich_text = []
        if permalink:
            rich_text.append({
                "type": "text",
                "text": {"content": text, "link": {"url": permalink}},
            })
        else:
            rich_text.append({"type": "text", "text": {"content": text}})

        blocks.append({
            "object": "block",
            "type": "to_do",
            "to_do": {"rich_text": rich_text, "checked": False},
        })

    return blocks


def _build_article_blocks(articles: list[dict], date_str: str) -> list[dict]:
    """Build Notion blocks for shared articles."""
    blocks = []
    blocks.append({"object": "block", "type": "divider", "divider": {}})
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": f"Articles & Intel -- {date_str}"}}],
            "color": "purple_background",
        },
    })

    for article in articles:
        title = article.get("title", "Article")
        url = article.get("url", "")
        bullets = article.get("bullets", [])
        relevance = article.get("relevance", "")
        people = article.get("people", [])

        # Article title with link
        title_text = title
        if people:
            title_text += f" (shared by {', '.join(people)})"

        rich_text = []
        if url:
            rich_text.append({
                "type": "text",
                "text": {"content": title_text, "link": {"url": url}},
                "annotations": {"bold": True},
            })
        else:
            rich_text.append({
                "type": "text",
                "text": {"content": title_text},
                "annotations": {"bold": True},
            })

        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": rich_text},
        })

        for bullet in bullets:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": bullet[:2000]}}],
                },
            })

        if relevance:
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"type": "emoji", "emoji": "\ud83c\udfaf"},
                    "rich_text": [{"type": "text", "text": {"content": f"Why it matters: {relevance}"}}],
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
