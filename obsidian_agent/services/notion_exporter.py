"""
Notion Exporter — performs a monthly dump of Obsidian notes that warrant
becoming projects into a Notion database.

The agent uses Claude to evaluate each note and decide whether it should
be promoted to a Notion project.  Qualifying notes are pushed via the
Notion API with structured properties (title, tags, status, summary,
source vault path).
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import anthropic
import requests

from obsidian_agent import config
from obsidian_agent.services.vault_manager import VaultManager

logger = logging.getLogger(__name__)


# ── Notion API helpers ────────────────────────────────────────────────

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _notion_headers() -> dict:
    return {
        "Authorization": f"Bearer {config.NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def create_notion_page(
    title: str,
    summary: str,
    tags: list[str],
    source_path: str,
    status: str = "Not Started",
) -> dict | None:
    """Create a new page (row) in the configured Notion database."""
    if not config.NOTION_API_KEY or not config.NOTION_DATABASE_ID:
        logger.warning("Notion credentials not configured — skipping export.")
        return None

    payload = {
        "parent": {"database_id": config.NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Status": {"select": {"name": status}},
            "Tags": {
                "multi_select": [{"name": t.lstrip("#")} for t in tags[:10]]
            },
            "Summary": {
                "rich_text": [{"text": {"content": summary[:2000]}}]
            },
            "Source": {
                "rich_text": [{"text": {"content": source_path}}]
            },
            "Imported": {"date": {"start": datetime.now().isoformat()}},
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": summary}}]
                },
            }
        ],
    }

    try:
        resp = requests.post(
            f"{NOTION_API_BASE}/pages",
            headers=_notion_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        page = resp.json()
        logger.info("Created Notion page: %s (%s)", title, page.get("id"))
        return page
    except requests.RequestException:
        logger.exception("Failed to create Notion page for '%s'", title)
        return None


# ── Note triage ───────────────────────────────────────────────────────

def triage_notes_for_notion(vm: VaultManager) -> list[dict]:
    """
    Use Claude to decide which vault notes should become Notion projects.

    Returns a list of dicts: [{title, reason, priority, tags}]
    """
    digest_lines = []
    for note in vm.index:
        tags = ", ".join(note.tags[:6])
        digest_lines.append(
            f"- {note.title} | tags: [{tags}] | summary: {note.summary[:120]}"
        )
    digest = "\n".join(digest_lines)

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=4096,
        system=(
            "You are a project manager reviewing an Obsidian vault.\n"
            "Identify notes that represent actionable projects — things that "
            "need task tracking, deadlines, collaboration, or sustained effort.\n"
            "Do NOT select simple reference notes, definitions, or quick ideas.\n"
            "For each qualifying note, explain why it should be a project.\n\n"
            "Respond with JSON (no fences):\n"
            '{"projects": [{"title": "...", "reason": "...", '
            '"priority": "high|medium|low", "tags": ["#tag"]}]}'
        ),
        messages=[
            {
                "role": "user",
                "content": f"## Vault notes to review\n\n{digest}",
            }
        ],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]

    try:
        data = json.loads(text)
        return data.get("projects", [])
    except json.JSONDecodeError:
        logger.error("Failed to parse triage response: %s", text[:300])
        return []


def run_monthly_export(vm: VaultManager) -> list[dict]:
    """
    Full monthly export pipeline:
      1. Triage notes via Claude
      2. Push qualifying notes to Notion
      3. Return summary of exported items
    """
    projects = triage_notes_for_notion(vm)
    if not projects:
        logger.info("No notes qualify for Notion export this month.")
        return []

    exported = []
    for proj in projects:
        title = proj["title"]
        # Find the vault note to get full details
        vault_note = next(
            (n for n in vm.index if n.title == title), None
        )
        source_path = str(vault_note.path) if vault_note else ""
        summary = vault_note.summary if vault_note else proj.get("reason", "")
        tags = proj.get("tags", [])

        result = create_notion_page(
            title=title,
            summary=summary or proj.get("reason", ""),
            tags=tags,
            source_path=source_path,
            status="Not Started",
        )
        if result:
            exported.append({"title": title, "notion_id": result.get("id")})

    logger.info("Monthly export complete: %d notes → Notion.", len(exported))
    return exported


def generate_export_report(vm: VaultManager, exported: list[dict]) -> str:
    """Produce an Obsidian report summarising what was sent to Notion."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        "---",
        f'title: "Notion Export Report — {today}"',
        "tags: [agent-report, notion-export]",
        f"date: {today}",
        "---",
        "",
        f"# Notion Export Report — {today}",
        "",
        f"**{len(exported)} notes exported to Notion.**",
        "",
    ]
    for item in exported:
        lines.append(f"- [[{item['title']}]] → Notion ID: `{item.get('notion_id', 'N/A')}`")
    lines.append("")
    return "\n".join(lines)
