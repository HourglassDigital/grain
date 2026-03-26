"""Pulse v2 Slack poster — posts as the Pulse bot with article thread replies."""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from src.config import SLACK_BOT_TOKEN, POSTING_CHANNEL_ID, DRY_RUN


def get_client() -> WebClient:
    return WebClient(token=SLACK_BOT_TOKEN)


def post_summary(message: str) -> bool:
    """Post the Pulse summary to #--internal-tooling as the Pulse bot."""
    if DRY_RUN:
        print(f"  [DRY RUN] Would post to Slack:\n{message}")
        return True

    client = get_client()
    try:
        client.chat_postMessage(
            channel=POSTING_CHANNEL_ID,
            text=message,
            unfurl_links=False,
            unfurl_media=False,
        )
        print("  Posted summary to #--internal-tooling as Pulse")
        return True
    except SlackApiError as e:
        print(f"  Slack API error: {e.response['error']}")
        return False


def reply_to_article(channel_id: str, thread_ts: str, summary: str) -> bool:
    """Reply in-thread to a shared article with Pulse's summary."""
    if DRY_RUN:
        print(f"  [DRY RUN] Would reply to article in {channel_id}")
        return True

    client = get_client()
    try:
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=summary,
            unfurl_links=False,
            unfurl_media=False,
        )
        print(f"  Replied to article in #{channel_id}")
        return True
    except SlackApiError as e:
        print(f"  Failed to reply to article: {e.response['error']}")
        return False
