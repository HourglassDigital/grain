"""Pulse realtime bot configuration."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Slack ---
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]  # xapp-... for Socket Mode

# --- APIs ---
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GRANOLA_API_KEY = os.getenv("GRANOLA_API_KEY", "")  # Optional, for meeting sync

# --- Workspace ---
WORKSPACE_URL = "https://hourglass-u322467.slack.com"

# --- User Map ---
USER_MAP = {
    "U0AM2U70V2B": {"name": "Michael", "mention": "<@U0AM2U70V2B>"},
    "U0AMEV059E1": {"name": "Finlay", "mention": "<@U0AMEV059E1>"},
    "U0ANV4NPQEA": {"name": "Suhail", "mention": "<@U0ANV4NPQEA>"},
    "U0ANUB74CQ0": {"name": "Glassy", "mention": "Glassy"},
    "U0ANVJK1Q5C": {"name": "Pulse", "mention": "Pulse"},
}

PULSE_BOT_ID = "U0ANVJK1Q5C"

# --- Notion Page IDs ---
NOTION_PAGES = {
    "home": "1d9210f1ecfc82b4b6b1014bba1742fb",
    "history": "32f210f1ecfc81e1ac21f7e84d0cfcbc",
    "team": "32f210f1ecfc8180a881fdf9a23eb4a0",
    "products": "32f210f1ecfc81cc93b8f642b1637c36",
    "tech_stack": "32f210f1ecfc81daa183d4742f7e3bf7",
    "tools": "32f210f1ecfc81659fc9d2169eae4daa",
    "ideas": "32f210f1ecfc8112aed1f4f26d1f9875",
    "learnings": "32f210f1ecfc81a89414ec20ad6d5975",
    "recommendations": "32f210f1ecfc81a8a49ecb4e01b66d57",
}

# Page key -> Slack channel ID for bidirectional sync
NOTION_TO_SLACK = {
    "history": "C0AMC0JVAPM",       # --general
    "tools": "C0AMXG15E8L",         # --internal-tooling
    "products": "C0ANMQHL76U",      # product-founderclaw
    "ideas": "C0AN42CTQR2",         # product-ideas
    "learnings": "C0AP8KF0ASC",     # --learning
    "tech_stack": "C0AMXG15E8L",    # --internal-tooling
    "team": "C0AMC0JVAPM",          # --general
}

# Brain channels where article auto-reply is active
ARTICLE_CHANNELS = {"C0AMSDV638S", "C0AMQC82X8W", "C0AMP1K8AMB"}

# Client project channels for Granola meeting sync
PROJECT_CHANNELS = {
    "proj-sos": "C0AMP1R67LM",
    "proj-mainsequence": "C0AMP1Q8A2H",
    "proj-blossom": "C0ANC963EJ2",
}

# --- Claude ---
MODEL = "claude-sonnet-4-6"

# --- Polling ---
NOTION_POLL_INTERVAL = 300    # 5 minutes
GRANOLA_POLL_INTERVAL = 1800  # 30 minutes
