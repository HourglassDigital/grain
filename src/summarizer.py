"""Pulse summarizer — uses Claude to categorize and summarize Slack messages."""

import json
import anthropic

from src.config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, NOTION_PAGES


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


SYSTEM_PROMPT = """You are Pulse, the Hourglass Digital memory agent. Your job is to read today's Slack messages and extract what matters for the company's documentation.

You categorize content into these Notion pages:
- history: Company decisions, milestones, team changes, client wins, strategic moves
- tools: New tools built, automations deployed, skills created, infrastructure changes
- products: Product updates, pricing changes, service offerings, client feedback on products
- ideas: New product ideas, feature requests, brainstorms
- learnings: Lessons learned, pricing insights, process improvements, useful articles/resources
- tech_stack: New tools adopted, migrations, infrastructure decisions
- team: Team changes, role updates, new members

Rules:
- Only extract MEANINGFUL content. Skip casual chat, greetings, reactions.
- Preserve specific numbers (prices, dates, metrics).
- Preserve who said what when it matters for attribution.
- Capture the WHY behind decisions, not just the what.
- Use bullet points, be concise.
- If a message does not fit any category, skip it.
- Group related messages together.
"""

EXTRACT_PROMPT = """Here are today's Slack messages from Hourglass Digital.

Analyze them and extract updates for each relevant Notion page.

Return a JSON object where:
- Keys are Notion page names: "history", "tools", "products", "ideas", "learnings", "tech_stack", "team"
- Values are arrays of update objects, each with:
  - "title": Short bold title for the update (5-10 words)
  - "bullets": Array of bullet point strings with the details
  - "source_channel": Which Slack channel this came from
  - "importance": "high", "medium", or "low"

Only include pages that have actual updates. Skip pages with nothing new.
Return ONLY valid JSON, no markdown code fences.

--- TODAY'S MESSAGES ---
{messages}
"""


def extract_updates(formatted_messages: str) -> dict:
    """Use Claude to extract structured updates from Slack messages."""
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": EXTRACT_PROMPT.format(messages=formatted_messages)}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        updates = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  Failed to parse Claude response: {e}")
        return {}
    valid_pages = set(NOTION_PAGES.keys()) - {"home", "recommendations"}
    return {k: v for k, v in updates.items() if k in valid_pages and v}


def format_slack_summary(updates: dict, date_str: str) -> str:
    """Format updates into a Slack message for #--internal-tooling."""
    if not updates:
        return f":zap: *Pulse -- {date_str}*\nNo significant updates captured today."
    lines = [f":zap: *Pulse -- Daily Notion Sync ({date_str})*", ""]
    page_labels = {
        "history": ":scroll: Company History",
        "tools": ":gear: Internal Tools",
        "products": ":briefcase: Products & Services",
        "ideas": ":bulb: Product Ideas",
        "learnings": ":blue_book: Learnings",
        "tech_stack": ":hammer_and_wrench: Tech Stack",
        "team": ":busts_in_silhouette: Team",
    }
    total_updates = 0
    for page_key, items in updates.items():
        label = page_labels.get(page_key, page_key)
        lines.append(f"*{label}*")
        for item in items:
            lines.append(f"  - {item.get('title', 'Update')}")
            total_updates += 1
        lines.append("")
    lines.append(f"_Updated {total_updates} items across {len(updates)} Notion pages._")
    return "\n".join(lines)
