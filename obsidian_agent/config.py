"""
Central configuration for the Obsidian AI Agent.

All paths, API keys, and tuning knobs live here.  Values are read from
environment variables (or a .env file) with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Anthropic / Claude ────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

# ── Google Drive ──────────────────────────────────────────────────────
# Path to the Google service-account JSON credential file
GOOGLE_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CREDENTIALS_FILE", "credentials/google_service_account.json"
)
# The Google Drive folder ID that acts as the "inbox"
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "")
# Local staging directory where downloaded Drive files land before processing
GDRIVE_STAGING_DIR = Path(
    os.getenv("GDRIVE_STAGING_DIR", "staging/gdrive_inbox")
)
# How often (seconds) the watcher polls Google Drive for new files
GDRIVE_POLL_INTERVAL = int(os.getenv("GDRIVE_POLL_INTERVAL", "60"))

# ── Obsidian Vault ────────────────────────────────────────────────────
OBSIDIAN_VAULT_PATH = Path(
    os.getenv("OBSIDIAN_VAULT_PATH", "")
)
# Sub-folder inside the vault where freshly ingested notes land
OBSIDIAN_INBOX_FOLDER = os.getenv("OBSIDIAN_INBOX_FOLDER", "Inbox")
# Sub-folder for agent-generated recommendation notes
OBSIDIAN_AGENT_FOLDER = os.getenv("OBSIDIAN_AGENT_FOLDER", "AgentReports")

# ── Notion ────────────────────────────────────────────────────────────
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

# ── Research / NBLM ──────────────────────────────────────────────────
# Perplexity API (optional — falls back to Claude for research)
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

# Comma-separated consulting domains for research scoping
CONSULTING_DOMAINS = [
    d.strip()
    for d in os.getenv(
        "CONSULTING_DOMAINS",
        "technology,business strategy,innovation,education",
    ).split(",")
]

# ── Agent behaviour ──────────────────────────────────────────────────
# Minimum confidence (0-1) before auto-applying a tag
TAG_CONFIDENCE_THRESHOLD = float(os.getenv("TAG_CONFIDENCE_THRESHOLD", "0.7"))
# Minimum relevance score to surface a vault link recommendation
LINK_RELEVANCE_THRESHOLD = float(os.getenv("LINK_RELEVANCE_THRESHOLD", "0.6"))
# Day of month for the Notion dump (1-28)
NOTION_DUMP_DAY = int(os.getenv("NOTION_DUMP_DAY", "1"))

# ── Logging ───────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "obsidian_agent.log")
