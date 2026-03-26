"""Ask Pulse — /pulse slash command to query company knowledge."""

import requests
import anthropic
from slack_bolt import App

from realtime.config import (
    ANTHROPIC_API_KEY, NOTION_TOKEN, MODEL, NOTION_PAGES,
)

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _get_notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
    }


def _fetch_page_text(page_id: str) -> str:
    """Fetch all text blocks from a Notion page."""
    url = f"{NOTION_API}/blocks/{page_id}/children?page_size=100"
    try:
        resp = requests.get(url, headers=_get_notion_headers())
        if resp.status_code != 200:
            return ""
        blocks = resp.json().get("results", [])
        texts = []
        for block in blocks:
            block_type = block.get("type", "")
            content = block.get(block_type, {})
            rich_text = content.get("rich_text", [])
            for rt in rich_text:
                texts.append(rt.get("plain_text", ""))
        return "\n".join(texts)
    except Exception:
        return ""


def _build_knowledge_base() -> str:
    """Build a knowledge base string from all Notion pages."""
    parts = []
    for page_key, page_id in NOTION_PAGES.items():
        if page_key == "home":
            continue
        text = _fetch_page_text(page_id)
        if text.strip():
            parts.append(f"\n=== {page_key.upper()} ===\n{text[:3000]}")
    return "\n".join(parts)


ASK_PROMPT = """You are Pulse, the Hourglass Digital knowledge agent. Someone on the team is asking you a question about the company.

Answer based ONLY on the knowledge base below. If you don't know, say so — don't make things up.

Be concise and direct. Use Slack markdown. Include specific numbers, dates, and names when available.
If the answer comes from a specific page, mention which one (e.g. "from Learnings & Playbook").

--- HOURGLASS KNOWLEDGE BASE ---
{knowledge}

--- QUESTION ---
{question}
"""


def register(app: App):
    """Register /pulse slash command."""

    @app.command("/pulse")
    def handle_pulse_command(ack, command, respond):
        ack()  # Acknowledge within 3 seconds

        question = command.get("text", "").strip()
        if not question:
            respond(":zap: *Pulse* — Ask me anything about Hourglass.\n\nUsage: `/pulse what did we decide about audit pricing?`")
            return

        respond(f":zap: _Thinking about: {question}_")

        try:
            # Build knowledge base from Notion
            knowledge = _build_knowledge_base()

            if not knowledge.strip():
                respond(":warning: Couldn't load Notion pages. Try again in a moment.")
                return

            # Ask Claude
            ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            response = ai.messages.create(
                model=MODEL,
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": ASK_PROMPT.format(knowledge=knowledge, question=question),
                }],
            )
            answer = response.content[0].text.strip()
            respond(f":zap: *Pulse*\n\n{answer}")

        except Exception as e:
            respond(f":x: Something went wrong: {str(e)[:200]}")
            print(f"  Ask Pulse error: {e}")
