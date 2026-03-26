"""Pulse v2 summarizer — enhanced with action items, people tagging, article summaries, and thread prioritization."""

import json

from src.config import MODEL, MAX_TOKENS, NOTION_PAGES, USER_MAP
from src.cost_tracker import get_tracked_client, record_usage


SYSTEM_PROMPT = """You are Pulse, the Hourglass Digital memory agent. You read today's Slack messages and extract what matters for the company's Notion documentation.

## Categories (Notion pages)
- history: Company decisions, milestones, team changes, client wins, strategic moves
- tools: New tools built, automations deployed, skills created, infrastructure changes
- products: Product updates, pricing changes, service offerings, client feedback
- ideas: New product ideas, feature requests, brainstorms
- learnings: Lessons learned, pricing insights, process improvements, useful resources
- tech_stack: New tools adopted, migrations, infrastructure decisions
- team: Team changes, role updates, new members
- actions: Open action items — when someone commits to doing something ("I'll do X", "let's do X", "need to X by Thursday")
- articles: Shared articles/links with summaries and relevance to Hourglass

## Rules
- PRIORITIZE threaded discussions. Messages with [THREAD] tags contain the richest decisions and context. Weight them higher than standalone messages.
- ALWAYS include who said/decided what using their real name (Michael, Finlay, Suhail). Attribution matters.
- Preserve specific numbers (prices, dates, metrics, percentages).
- Capture the WHY behind decisions, not just the what.
- Group related messages into single updates (a pricing discussion = one item, not five).
- Skip casual chat, greetings, emoji-only messages, bot noise.
- For articles marked [SHARED_ARTICLE]: summarize the article's key points in 3-5 bullets, then add a bullet on why it's relevant to Hourglass specifically.
- For action items: include WHO owns it, WHAT they committed to, and any DEADLINE mentioned. If no deadline, note that.
- Include the Slack permalink (from the "link:" field) for each update so we can backlink.
- When analyzing messages, also check if any previous action items appear to be completed. Look for signals like "done", "finished X", "shipped X", "deployed X", "completed X". If you detect completions, include them in the "completed_actions" key in your JSON output.
"""

EXTRACT_PROMPT = """Here are today's Slack messages from Hourglass Digital.

Analyze them and extract updates for each relevant Notion page.

Return a JSON object where:
- Keys are page names: "history", "tools", "products", "ideas", "learnings", "tech_stack", "team", "actions", "articles"
- Values are arrays of update objects, each with:
  - "title": Short title (5-10 words)
  - "bullets": Array of bullet point strings with details
  - "people": Array of people names involved (e.g. ["Michael", "Finlay"])
  - "source_channel": Which Slack channel
  - "permalink": Slack message permalink (from the "link:" field in the message)
  - "importance": "high", "medium", or "low"

For "actions" items, also include:
  - "owner": Who owns this action (name)
  - "deadline": Deadline if mentioned, or "none"
  - "status": "open"

For "articles" items, also include:
  - "url": The article URL
  - "relevance": One sentence on why this matters to Hourglass

Also include a top-level key "completed_actions" — an array of objects with:
  - "title": The original action title that appears to be completed (match as closely as possible)
  - "evidence": The message text that shows it's done

If no completed actions are detected, omit the key or use an empty array.

Only include pages with actual updates. Skip empty ones.
Return ONLY valid JSON, no markdown code fences.

--- TODAY'S MESSAGES ---
{messages}
"""


def extract_updates(formatted_messages: str) -> dict:
    """Use Claude to extract structured updates from Slack messages."""
    client = get_tracked_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": EXTRACT_PROMPT.format(messages=formatted_messages)}],
    )
    record_usage(response)
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        updates = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  Failed to parse Claude response: {e}")
        print(f"  Raw: {text[:500]}")
        return {}
    valid_pages = set(NOTION_PAGES.keys()) | {"actions", "articles"}
    valid_pages -= {"home", "recommendations"}
    return {k: v for k, v in updates.items() if k in valid_pages and v}


def _resolve_people_mentions(people: list[str]) -> str:
    """Convert people names to Slack @mentions."""
    name_to_id = {v["name"]: v["mention"] for v in USER_MAP.values()}
    mentions = []
    for name in people:
        mentions.append(name_to_id.get(name, name))
    return ", ".join(mentions)


def format_slack_summary(updates: dict, date_str: str) -> str:
    """Format updates into a Slack message with @mentions and clean formatting."""
    if not updates:
        return f":zap: *Pulse -- {date_str}*\n\nNo significant updates captured today."

    lines = [f":zap: *Pulse -- Daily Sync ({date_str})*"]
    lines.append("")
    lines.append("---")
    lines.append("")

    page_labels = {
        "history": ":scroll:  *Company History*",
        "tools": ":gear:  *Internal Tools*",
        "products": ":briefcase:  *Products & Services*",
        "ideas": ":bulb:  *Product Ideas*",
        "learnings": ":blue_book:  *Learnings*",
        "tech_stack": ":hammer_and_wrench:  *Tech Stack*",
        "team": ":busts_in_silhouette:  *Team*",
        "actions": ":clipboard:  *Action Items*",
        "articles": ":newspaper:  *Articles & Intel*",
    }

    # Render actions first if present (most actionable)
    ordered_keys = []
    if "actions" in updates:
        ordered_keys.append("actions")
    for k in updates:
        if k != "actions":
            ordered_keys.append(k)

    total_updates = 0
    for page_key in ordered_keys:
        items = updates[page_key]
        label = page_labels.get(page_key, f"*{page_key}*")
        lines.append(label)
        lines.append("")

        for item in items:
            title = item.get("title", "Update")
            bullets = item.get("bullets", [])
            people = item.get("people", [])

            # Build title with people mentions
            people_str = ""
            if people:
                people_str = f" ({_resolve_people_mentions(people)})"

            if page_key == "actions":
                owner = item.get("owner", "?")
                deadline = item.get("deadline", "none")
                name_to_id = {v["name"]: v["mention"] for v in USER_MAP.values()}
                owner_mention = name_to_id.get(owner, owner)
                deadline_str = f" | due: *{deadline}*" if deadline != "none" else ""
                lines.append(f":white_square:  *{title}*  -- {owner_mention}{deadline_str}")
            elif page_key == "articles":
                url = item.get("url", "")
                relevance = item.get("relevance", "")
                lines.append(f":link:  *{title}*{people_str}")
                if url:
                    lines.append(f"    {url}")
                if relevance:
                    lines.append(f"    _Why it matters:_ {relevance}")
            else:
                lines.append(f":black_small_square:  *{title}*{people_str}")

            for bullet in bullets:
                lines.append(f"    :small_orange_diamond:  {bullet}")

            total_updates += 1

        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(f"_Synced {total_updates} updates across {len(updates)} Notion pages._")
    lines.append("_Every pulse counts._ :zap:")
    return "\n".join(lines)
