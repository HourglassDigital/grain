"""Pulse observability — structured logging to Slack + stdout."""

from datetime import datetime, timezone, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from realtime.config import SLACK_BOT_TOKEN

AEDT = timezone(timedelta(hours=11))
LOG_CHANNEL = "C0AMXG15E8L"  # --internal-tooling

LEVEL_EMOJI = {
    "info": ":information_source:",
    "warn": ":warning:",
    "error": ":x:",
    "success": ":white_check_mark:",
}

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = WebClient(token=SLACK_BOT_TOKEN)
    return _client


def log(message, level="info", post_to_slack=False):
    """Log a message. Always prints to stdout. Optionally posts to Slack."""
    now = datetime.now(AEDT).strftime("%H:%M:%S")
    emoji = LEVEL_EMOJI.get(level, "")

    # Always stdout
    print(f"[{now}] [{level.upper()}] {message}")

    # Only post errors and explicit slack posts
    if post_to_slack or level in ("error", "warn"):
        try:
            _get_client().chat_postMessage(
                channel=LOG_CHANNEL,
                text=f"{emoji} *Pulse* [{level}] {message}",
                unfurl_links=False,
            )
        except SlackApiError:
            print(f"  Failed to post log to Slack")


def log_error(message):
    log(message, level="error", post_to_slack=True)


def log_success(message):
    log(message, level="success", post_to_slack=True)


def log_warn(message):
    log(message, level="warn", post_to_slack=True)
