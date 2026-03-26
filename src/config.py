"""Grain configuration — channel mappings, page IDs, and constants."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Secrets ---
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# --- Timing ---
LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "24"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

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

# --- Slack Channel Config ---
SLACK_CHANNELS = {
    "--general": {"id": "C0AMC0JVAPM", "notion_pages": ["history"], "category": "decisions"},
    "--wins": {"id": "C0AMW1PA3J8", "notion_pages": ["history", "learnings"], "category": "wins"},
    "--pipeline": {"id": "C0AMSDZ5AR0", "notion_pages": ["products", "learnings"], "category": "pipeline"},
    "--learning": {"id": "C0AP8KF0ASC", "notion_pages": ["learnings"], "category": "learnings"},
    "--internal-tooling": {"id": "C0AMXG15E8L", "notion_pages": ["tools", "tech_stack"], "category": "tools"},
    "product-founderclaw": {"id": "C0ANMQHL76U", "notion_pages": ["products"], "category": "product"},
    "product-shipped": {"id": "C0AMMJ2PZQB", "notion_pages": ["tools"], "category": "shipped"},
    "product-ideas": {"id": "C0AN42CTQR2", "notion_pages": ["ideas"], "category": "ideas"},
    "proj-sos": {"id": "C0AMP1R67LM", "notion_pages": ["history"], "category": "client"},
    "proj-mainsequence": {"id": "C0AMP1Q8A2H", "notion_pages": ["history"], "category": "client"},
    "proj-blossom": {"id": "C0ANC963EJ2", "notion_pages": ["history"], "category": "client"},
    "agent-social-star": {"id": "C0AMU1VG066", "notion_pages": ["tools"], "category": "agent"},
    "brain-reading": {"id": "C0AMSDV638S", "notion_pages": ["learnings"], "category": "reading"},
    "brain-podcasts": {"id": "C0AMQC82X8W", "notion_pages": ["learnings"], "category": "reading"},
    "brain-ai-geekout": {"id": "C0AMP1K8AMB", "notion_pages": ["learnings", "tools"], "category": "ai"},
}

# --- Filtering ---
SKIP_SUBTYPES = {
    "channel_join", "channel_leave", "channel_name", "channel_purpose",
    "channel_topic", "channel_archive", "channel_unarchive",
    "bot_add", "bot_remove", "group_join", "group_leave",
}

MIN_MESSAGE_LENGTH = 10

# --- Claude ---
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
