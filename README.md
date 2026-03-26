# 🏖️ Grain

**The Hourglass memory agent.** Every grain of sand is a captured moment.

Grain reads all Hourglass Slack channels daily, extracts decisions, learnings, and tool deployments using Claude, and documents them in the company Notion workspace. Then posts a summary back to `#--internal-tooling`.

## What it captures

| Category | Slack Source | Notion Destination |
|----------|-------------|--------------------|
| Company decisions & milestones | `#--general`, all channels | Company History & Timeline |
| New tools, agents, skills | `#--internal-tooling`, `#product-shipped` | Internal Tools & Automations |
| Sales learnings & pricing | `#--pipeline`, `#--wins`, `#--learning` | Learnings & Playbook |
| Product ideas | `#product-ideas` | Product Ideas |
| AI/tech insights | `#brain-ai-geekout`, `#brain-reading` | Learnings & Playbook |
| Client project updates | `#proj-*` channels | Company History & Timeline |
| Product updates | `#product-*` channels | Products & Services |

## Architecture

```
Slack (16 channels)
    ↓ Read via Slack API
Grain Agent
    ↓ Categorize & summarize via Claude API
Notion (8 pages)
    ↓ Post summary
Slack #--internal-tooling
```

## Setup

### 1. Environment variables

```bash
cp .env.example .env
# Fill in your tokens
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run manually

```bash
python src/main.py
```

### 4. Scheduled (GitHub Actions)

The included workflow runs daily at 7:00 AM AEDT (20:00 UTC previous day). Set the required secrets in your GitHub repo settings:

- `SLACK_BOT_TOKEN` — Slack Bot User OAuth Token (xoxb-...)
- `SLACK_WEBHOOK_URL` — Webhook URL for `#--internal-tooling`
- `NOTION_TOKEN` — Notion integration token
- `ANTHROPIC_API_KEY` — Claude API key

## How it works

1. **Read** — Pulls last 24h of messages from all 16 Slack channels via Slack API
2. **Filter** — Strips bot joins, channel renames, and low-signal messages
3. **Categorize** — Claude classifies each meaningful message into categories (decision, learning, tool, idea, client update, etc.)
4. **Summarize** — Groups by category, generates structured summaries
5. **Update Notion** — Appends new content to the relevant Notion page under a dated section
6. **Post to Slack** — Sends a bullet-point summary of all Notion updates to `#--internal-tooling`

## Notion Page IDs

| Page | ID |
|------|----|
| Home | `1d9210f1ecfc82b4b6b1014bba1742fb` |
| Company History & Timeline | `32f210f1ecfc81e1ac21f7e84d0cfcbc` |
| Team | `32f210f1ecfc8180a881fdf9a23eb4a0` |
| Products & Services | `32f210f1ecfc81cc93b8f642b1637c36` |
| Tech Stack | `32f210f1ecfc81daa183d4742f7e3bf7` |
| Internal Tools & Automations | `32f210f1ecfc81659fc9d2169eae4daa` |
| Product Ideas | `32f210f1ecfc8112aed1f4f26d1f9875` |
| Learnings & Playbook | `32f210f1ecfc81a89414ec20ad6d5975` |
| Workflow Recommendations | `32f210f1ecfc81a8a49ecb4e01b66d57` |

## Slack Channel IDs

| Channel | ID |
|---------|----|
| `#--general` | `C0AMC0JVAPM` |
| `#--random` | `C0AMJC0H6LS` |
| `#--wins` | `C0AMW1PA3J8` |
| `#--pipeline` | `C0AMSDZ5AR0` |
| `#--learning` | `C0AP8KF0ASC` |
| `#--internal-tooling` | `C0AMXG15E8L` |
| `#product-founderclaw` | `C0ANMQHL76U` |
| `#product-shipped` | `C0AMMJ2PZQB` |
| `#product-ideas` | `C0AN42CTQR2` |
| `#proj-sos` | `C0AMP1R67LM` |
| `#proj-mainsequence` | `C0AMP1Q8A2H` |
| `#proj-blossom` | `C0ANC963EJ2` |
| `#agent-social-star` | `C0AMU1VG066` |
| `#brain-reading` | `C0AMSDV638S` |
| `#brain-podcasts` | `C0AMQC82X8W` |
| `#brain-ai-geekout` | `C0AMP1K8AMB` |

---

Built by Hourglass Digital. Every grain counts.
