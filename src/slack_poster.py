"""Grain Slack poster — sends summary to #--internal-tooling via webhook."""

import requests
from src.config import SLACK_WEBHOOK_URL, DRY_RUN


def post_summary(message: str) -> bool:
    if DRY_RUN:
        print(f"  [DRY RUN] Would post to Slack:\n{message}")
        return True
    response = requests.post(SLACK_WEBHOOK_URL, json={"text": message})
    if response.status_code == 200:
        print("  Posted summary to #--internal-tooling")
        return True
    else:
        print(f"  Slack webhook error: {response.status_code}")
        return False
