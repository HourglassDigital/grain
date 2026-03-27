"""Real-time article auto-reply — summarizes shared links in brain-* channels."""

import re
import anthropic
from slack_bolt import App

from realtime.config import (
    ANTHROPIC_API_KEY, MODEL, ARTICLE_CHANNELS, PULSE_BOT_ID,
    USER_MAP,
)
from realtime.ask_pulse import handle_mention
from realtime.obs import log, log_error

URL_PATTERN = re.compile(r'<(https?://[^>|]+)(?:\|[^>]*)?>')


ARTICLE_PROMPT = """You are Pulse, the Hourglass Digital intelligence agent.

Someone on the team shared this article/link in Slack. Summarize it and explain why it matters to Hourglass.

Context about Hourglass Digital:
- AI consulting company making Australia AI-native
- Services: AI Audits ($3k-$10k), AI Builds, FounderClaw (AI assistant for founders at $2k setup + $99/mo)
- Team: Michael Batko (growth, community, ex-Startmate), Finlay Ekins (founder, sales, OpenClaw), Suhail Najeeb (AI PhD, engineering)
- Uses Claude Code as primary dev tool, building internal AI agents and automations
- Key insight areas: agent pricing, AI-first company operations, founder tools, enterprise AI adoption

Article shared by {who} in #{channel}:
URL: {url}
Context: {context}

Before summarizing, consider how this article connects to what Hourglass already knows:
- AI Audit pricing: 1 interview ≈ $1k, tiers at $3k/$6k/$10k
- FounderClaw: $2k setup + $99/mo hosting, ~3h setup, targeting 10 beta founders
- Core philosophy: build for yourself first, sell to others
- Claude Code as primary dev interface for both founders
- Speed over polish — ship today, iterate tomorrow
- Agent pricing insight: can charge human salary equivalent (faster training, no externalities)
- Key products: AI Audits, AI Builds, FounderClaw, Newsletter Sponsorship
- Mission: Make Australia AI-native

Write a concise Slack reply:
1. :newspaper:  *Title or topic* (2-5 words max)
2. Blank line
3. 3-5 bullet points summarizing key takeaways (use :small_orange_diamond: before each)
4. Blank line
5. :dart:  *Why this matters for Hourglass:* — one concise paragraph on specific relevance to our services, pricing, or operations
6. Blank line
7. :link:  *Connections:* — one or two sentences linking this article to Hourglass's existing strategy, pricing, or operations. Be specific.

Use Slack markdown. Keep it tight — no fluff."""


def register(app: App):
    """Register article watcher event handler."""

    @app.event("message")
    def handle_message(event, say, client):
        # Skip bot messages, edits, deletes
        if event.get("subtype") in ("bot_message", "message_changed", "message_deleted"):
            return
        if event.get("bot_id"):
            return
        if event.get("user") == PULSE_BOT_ID:
            return

        # Check if Pulse was @mentioned — handle as a question
        text = event.get("text", "")
        if f"<@{PULSE_BOT_ID}>" in text:
            handle_mention(event, say)
            return

        # Only watch brain-* channels for article auto-reply
        channel = event.get("channel", "")
        if channel not in ARTICLE_CHANNELS:
            return

        # Skip thread replies (only respond to top-level shares)
        if event.get("thread_ts") and event.get("thread_ts") != event.get("ts"):
            return

        text = event.get("text", "")
        urls = URL_PATTERN.findall(text)

        # Filter out Slack internal URLs
        external_urls = [u for u in urls if "slack.com" not in u]
        if not external_urls:
            return

        url = external_urls[0]
        user_id = event.get("user", "")
        user_name = USER_MAP.get(user_id, {}).get("name", "someone")

        # Get channel name for context
        try:
            info = client.conversations_info(channel=channel)
            channel_name = info["channel"]["name"]
        except Exception:
            channel_name = "brain"

        # Summarize with Claude
        try:
            ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            response = ai.messages.create(
                model=MODEL,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": ARTICLE_PROMPT.format(
                        who=user_name,
                        channel=channel_name,
                        url=url,
                        context=text[:500],
                    ),
                }],
            )
            summary = response.content[0].text.strip()

            say(
                text=summary,
                thread_ts=event["ts"],
                unfurl_links=False,
                unfurl_media=False,
            )
            log(f"Article reply: #{channel_name} — {url[:60]}")

        except Exception as e:
            log_error(f"Article reply failed: {e}")
