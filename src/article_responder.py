"""Pulse v2 article responder — summarizes shared articles and replies in-thread."""

import anthropic
from src.config import ANTHROPIC_API_KEY, SLACK_CHANNELS
from src.slack_poster import reply_to_article

MODEL = "claude-sonnet-4-6"


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


ARTICLE_PROMPT = """You are Pulse, the Hourglass Digital intelligence agent.

Someone on the team just shared this article/link in Slack. Summarize it and explain why it matters to Hourglass.

Context about Hourglass Digital:
- AI consulting company making Australia AI-native
- Services: AI Audits ($3k-$10k), AI Builds, FounderClaw (AI assistant for founders)
- Team: Michael Batko (growth, community), Finlay Ekins (founder, sales, OpenClaw), Suhail Najeeb (AI PhD, engineering)
- Uses Claude Code as primary dev tool, building internal AI agents and automations

The article was shared in #{channel} by {who}.

Article URL: {url}
Message context: {context}

Respond with a clean Slack message:
1. :newspaper: *Article title or topic* (2-4 words)
2. 3-5 bullet point summary of key takeaways
3. :dart: *Why it matters for Hourglass:* one paragraph on specific relevance

Keep it concise. Use Slack markdown (bold with *, bullets with •).
"""


def process_articles(channel_messages: dict[str, list[dict]]) -> int:
    """Find shared articles in brain-* channels and reply with summaries."""
    client = get_client()
    replied = 0

    for channel_name, messages in channel_messages.items():
        # Only auto-reply in brain/reading channels
        if not channel_name.startswith("brain-"):
            continue

        channel_id = SLACK_CHANNELS[channel_name]["id"]

        for msg in messages:
            if not msg.get("has_article"):
                continue

            # Skip if already has thread replies (might already be summarized)
            if msg.get("thread_replies"):
                continue

            urls = [u for u in msg.get("urls", []) if not u.startswith("https://hourglass")]
            if not urls:
                continue

            url = urls[0]
            prompt = ARTICLE_PROMPT.format(
                channel=channel_name,
                who=msg["user_name"],
                url=url,
                context=msg["text"][:500],
            )

            try:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                summary = response.content[0].text.strip()

                if reply_to_article(channel_id, msg["ts"], summary):
                    replied += 1
                    print(f"  Replied to article in #{channel_name}: {url[:60]}")
            except Exception as e:
                print(f"  Failed to summarize article: {e}")

    return replied
