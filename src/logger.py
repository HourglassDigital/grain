"""Pulse observability — structured logging to Slack."""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from src.config import SLACK_BOT_TOKEN, POSTING_CHANNEL_ID, DRY_RUN

LEVEL_ICONS = {
    "info": ":information_source:",
    "warn": ":warning:",
    "error": ":x:",
    "success": ":white_check_mark:",
}


def log_to_slack(message: str, level: str = "info") -> bool:
    """Post a log message to #--internal-tooling as Pulse.

    Only posts errors and final summaries to Slack to avoid spam.
    All levels are printed to stdout regardless.
    """
    icon = LEVEL_ICONS.get(level, ":information_source:")
    formatted = f":zap: *Pulse Log* [{level}] {icon} {message}"

    # Always print to stdout
    print(f"  [LOG/{level}] {message}")

    # Only post errors and success (final summary) to Slack
    if level not in ("error", "success"):
        return True

    if DRY_RUN:
        print(f"  [DRY RUN] Would log to Slack: {formatted}")
        return True

    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        client.chat_postMessage(
            channel=POSTING_CHANNEL_ID,
            text=formatted,
            unfurl_links=False,
            unfurl_media=False,
        )
        return True
    except SlackApiError as e:
        print(f"  Failed to log to Slack: {e.response['error']}")
        return False
