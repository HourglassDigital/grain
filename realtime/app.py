"""Pulse realtime bot — always-on Slack Bolt app via Socket Mode.

Handles:
- Real-time article auto-reply in brain-* channels
- /pulse slash command for querying company knowledge
- Notion → Slack change detection (polling)
- Granola meeting → Notion + Slack sync (polling)

Usage:
    python -m realtime.app
"""

import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from realtime.config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN
from realtime.article_watcher import register as register_articles
from realtime.ask_pulse import register as register_ask
from realtime.notion_watcher import start_watcher as start_notion_watcher
from realtime.granola_sync import start_syncer as start_granola_syncer
from realtime.meeting_prep import start_prep_agent
from realtime.obs import log, log_error, log_success

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pulse-realtime")


def create_app() -> App:
    app = App(token=SLACK_BOT_TOKEN)

    # Register event handlers
    print("Registering handlers...")
    register_articles(app)
    register_ask(app)
    print("  Article watcher: ready")
    print("  Ask Pulse (/pulse): ready")

    return app


def main():
    log_success("Pulse Realtime Bot starting up")
    print()
    print("=== Pulse Realtime Bot ===")
    print()

    app = create_app()

    # Start background pollers
    print("Starting background services...")
    start_notion_watcher()
    start_granola_syncer()
    start_prep_agent()
    print("  Meeting prep: ready")
    print()

    # Start Socket Mode
    log("Connecting to Slack via Socket Mode...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    main()
