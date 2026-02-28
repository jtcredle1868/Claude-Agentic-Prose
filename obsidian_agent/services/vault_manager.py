"""
Vault Manager — handles all interactions with the local Obsidian vault:

  - Writing new notes (with front-matter, tags, links)
  - Scanning the vault index for existing notes and tags
  - Recommending additional tags and links based on vault context
  - Building a lightweight in-memory graph of the vault for relationship analysis
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from obsidian_agent import config
from obsidian_agent.services.note_analyzer import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class VaultNote:
    """Lightweight representation of an existing vault note."""
    path: Path
    title: str
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    summary: str = ""


class VaultManager:
    """Reads, writes, and indexes the Obsidian vault."""

    def __init__(self, vault_path: Path | None = None):
        self.vault_path = vault_path or config.OBSIDIAN_VAULT_PATH
        self.inbox = self.vault_path / config.OBSIDIAN_INBOX_FOLDER
        self.agent_folder = self.vault_path / config.OBSIDIAN_AGENT_FOLDER
        self._index: list[VaultNote] = []

    # ── Vault scanning ────────────────────────────────────────────────

    def build_index(self) -> list[VaultNote]:
        """Scan every .md file in the vault and build a lightweight index."""
        self._index = []
        for md_file in self.vault_path.rglob("*.md"):
            note = self._parse_note(md_file)
            if note:
                self._index.append(note)
        logger.info("Vault index built: %d notes.", len(self._index))
        return self._index

    def _parse_note(self, path: Path) -> VaultNote | None:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        title = path.stem
        tags = re.findall(r"#([a-zA-Z0-9_/-]+)", content)
        tags = list(set(tags))

        links = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", content)
        links = list(set(links))

        # Grab YAML front-matter summary if present
        summary = ""
        fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            fm = fm_match.group(1)
            for line in fm.split("\n"):
                if line.startswith("summary:"):
                    summary = line.split(":", 1)[1].strip().strip('"').strip("'")

        return VaultNote(
            path=path, title=title, tags=tags, links=links, summary=summary
        )

    @property
    def index(self) -> list[VaultNote]:
        if not self._index:
            self.build_index()
        return self._index

    def all_tags(self) -> set[str]:
        return {tag for note in self.index for tag in note.tags}

    def all_titles(self) -> set[str]:
        return {note.title for note in self.index}

    # ── Writing notes ─────────────────────────────────────────────────

    def write_note(self, analysis: AnalysisResult) -> Path:
        """
        Write an analyzed note into the vault inbox with YAML front-matter.
        Returns the path of the created file.
        """
        self.inbox.mkdir(parents=True, exist_ok=True)

        # Sanitise title for filesystem
        safe_title = re.sub(r'[<>:"/\\|?*]', "-", analysis.title).strip()
        dest = self.inbox / f"{safe_title}.md"

        # Avoid overwriting — append a counter
        counter = 1
        while dest.exists():
            dest = self.inbox / f"{safe_title} ({counter}).md"
            counter += 1

        front_matter = self._build_front_matter(analysis)
        full_content = f"{front_matter}\n{analysis.markdown}\n"

        dest.write_text(full_content, encoding="utf-8")
        logger.info("Note written → %s", dest)

        # Update index
        self._index.append(
            VaultNote(
                path=dest,
                title=analysis.title,
                tags=[t.lstrip("#") for t in analysis.tags],
                links=[
                    l.strip("[]") for l in analysis.suggested_links
                ],
                summary=analysis.summary,
            )
        )
        return dest

    def _build_front_matter(self, analysis: AnalysisResult) -> str:
        tags_line = ", ".join(t.lstrip("#") for t in analysis.tags)
        links_line = ", ".join(
            l.replace("[[", "").replace("]]", "") for l in analysis.suggested_links
        )
        return (
            "---\n"
            f"title: \"{analysis.title}\"\n"
            f"type: {analysis.note_type}\n"
            f"tags: [{tags_line}]\n"
            f"links: [{links_line}]\n"
            f"summary: \"{analysis.summary}\"\n"
            f"confidence: {analysis.confidence}\n"
            "status: inbox\n"
            "---\n"
        )

    # ── AI-powered link & tag recommendations ─────────────────────────

    def recommend_links_and_tags(
        self, analysis: AnalysisResult
    ) -> dict:
        """
        Use Claude to compare a new note's content against the vault index
        and recommend additional tags and wikilinks.
        """
        existing_tags = sorted(self.all_tags())
        existing_titles = sorted(self.all_titles())

        # Build a compact vault summary for the prompt
        vault_summary_lines = []
        for note in self.index[:200]:  # cap to keep prompt reasonable
            vault_summary_lines.append(
                f"- {note.title}  tags:[{', '.join(note.tags[:5])}]  "
                f"links:[{', '.join(note.links[:5])}]"
            )
        vault_summary = "\n".join(vault_summary_lines)

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=4096,
            system=(
                "You are a knowledge-graph expert for an Obsidian vault. "
                "Given a new note and a summary of existing vault notes, "
                "recommend additional tags and wikilinks that would strengthen "
                "the knowledge graph. Only recommend links to notes that exist. "
                "Respond with JSON: {\"additional_tags\": [\"#tag\"], "
                "\"additional_links\": [\"[[Title]]\"], \"reasoning\": \"...\"}"
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"## New note\nTitle: {analysis.title}\n"
                        f"Summary: {analysis.summary}\n"
                        f"Current tags: {analysis.tags}\n"
                        f"Current links: {analysis.suggested_links}\n"
                        f"Key concepts: {analysis.key_concepts}\n\n"
                        f"## Existing vault notes (sample)\n{vault_summary}\n\n"
                        f"## All existing tags\n{existing_tags}\n\n"
                        f"## All existing note titles\n{existing_titles}\n\n"
                        "Recommend additional tags and wikilinks."
                    ),
                }
            ],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error("Failed to parse link/tag recommendations: %s", text[:300])
            return {"additional_tags": [], "additional_links": [], "reasoning": ""}

    # ── Report writing ────────────────────────────────────────────────

    def write_agent_report(self, filename: str, content: str) -> Path:
        """Write a report note into the AgentReports folder."""
        self.agent_folder.mkdir(parents=True, exist_ok=True)
        dest = self.agent_folder / f"{filename}.md"
        dest.write_text(content, encoding="utf-8")
        logger.info("Agent report written → %s", dest)
        return dest
