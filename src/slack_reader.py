"""Grain Slack reader — pulls messages from all channels for the lookback window."""

import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.config import (
    SLACK_BOT_TOKEN, SLACK_CHANNELS, SKIP_SUBTYPES,
    MIN_MESSAGE_LENGTH, LOOKBACK_HOURS,
)


def get_slack_client() -> WebClient:
    return WebClient(token=SLACK_BOT_TOKEN)


def read_all_channels() -> dict[str, list[dict]]:
    """Read messages from all configured channels within the lookback window."""
    client = get_slack_client()
    oldest = str(time.time() - (LOOKBACK_HOURS * 3600))
    all_messages = {}

    for channel_name, config in SLACK_CHANNELS.items():
        channel_id = config["id"]
        try:
            messages = _read_channel(client, channel_id, oldest)
            if messages:
                all_messages[channel_name] = messages
                print(f"  \u2713 #{channel_name}: {len(messages)} messages")
            else:
                print(f"  \u00b7 #{channel_name}: no new messages")
        except SlackApiError as e:
            print(f"  \u2717 #{channel_name}: {e.response['error']}")

    return all_messages


def _read_channel(client: WebClient, channel_id: str, oldest: str) -> list[dict]:
    """Read and filter messages from a single channel."""
    result = client.conversations_history(
        channel=channel_id, oldest=oldest, limit=200,
    )

    messages = []
    for msg in result.get("messages", []):
        filtered = _filter_message(msg)
        if filtered:
            if msg.get("reply_count", 0) > 0:
                filtered["thread_replies"] = _read_thread(client, channel_id, msg["ts"])
            messages.append(filtered)

    messages.reverse()
    return messages


def _read_thread(client: WebClient, channel_id: str, thread_ts: str) -> list[dict]:
    """Read replies in a thread."""
    try:
        result = client.conversations_replies(channel=channel_id, ts=thread_ts, limit=50)
    except SlackApiError:
        return []

    replies = []
    for msg in result.get("messages", [])[1:]:
        filtered = _filter_message(msg)
        if filtered:
            replies.append(filtered)
    return replies


def _filter_message(msg: dict) -> dict | None:
    """Filter out low-signal messages."""
    subtype = msg.get("subtype", "")
    if subtype in SKIP_SUBTYPES:
        return None

    text = msg.get("text", "").strip()
    if len(text) < MIN_MESSAGE_LENGTH:
        return None

    user = msg.get("user", msg.get("username", "bot"))
    return {"user": user, "text": text, "ts": msg["ts"], "files": bool(msg.get("files"))}


def format_messages_for_claude(channel_messages: dict[str, list[dict]]) -> str:
    """Format all channel messages into a single string for Claude."""
    parts = []
    for channel_name, messages in channel_messages.items():
        if not messages:
            continue
        category = SLACK_CHANNELS[channel_name]["category"]
        parts.append(f"\n=== #{channel_name} (category: {category}) ===")
        for msg in messages:
            parts.append(f"[{msg['user']}]: {msg['text']}")
            for reply in msg.get("thread_replies", []):
                parts.append(f"  \u21b3 [{reply['user']}]: {reply['text']}")
    return "\n".join(parts)
