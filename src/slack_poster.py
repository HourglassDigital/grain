"""Pulse Slack poster — sends summary to #--internal-tooling as the Pulse bot."""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from src.config import SLACK_BOT_TOKEN, POSTING_CHANNEL_ID, DRY_RUN


def post_summary(message: str) -> bool:
    """Post the Pulse summary to #--internal-tooling as the Pulse bot."""
    if DRY_RUN:
        print(f"  [DRY RUN] Would post to Slack:\n{message}")
        return True

    client = WebClient(token=SLACK_BOT_TOKEN)
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
