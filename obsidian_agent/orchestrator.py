"""
Orchestrator — ties all agent services together into coherent pipelines.

Pipelines:
  1. ingest     — Watch Drive → analyze → tag/link → write to vault
  2. analyze    — Full vault relationship + congruency analysis
  3. export     — Monthly Obsidian → Notion dump
  4. research   — NBLM / Perplexity / class opportunity scan
  5. run_all    — Execute all pipelines in sequence
"""

import logging
from datetime import datetime
from pathlib import Path

from obsidian_agent import config
from obsidian_agent.services.note_analyzer import AnalysisResult, analyze_note
from obsidian_agent.services.vault_manager import VaultManager
from obsidian_agent.services import relationship_analyzer
from obsidian_agent.services import notion_exporter
from obsidian_agent.services import research_recommender

logger = logging.getLogger(__name__)


class ObsidianAgent:
    """Top-level agent that coordinates all sub-services."""

    def __init__(self, vault_path: Path | None = None):
        self.vm = VaultManager(vault_path)
        self._setup_logging()

    def _setup_logging(self) -> None:
        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL, logging.INFO),
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(config.LOG_FILE),
            ],
        )

    # ── Pipeline 1: Ingest ────────────────────────────────────────────

    def ingest_file(self, file_path: Path) -> Path | None:
        """
        Process a single file through the full ingestion pipeline:
          1. Analyze content (OCR if image, parse if text/pdf)
          2. Apply AI-generated tags and links
          3. Request additional tag/link recommendations from vault context
          4. Write the final note to the Obsidian vault inbox
        """
        logger.info("Ingesting: %s", file_path)

        # Step 1: Analyze
        analysis = analyze_note(file_path)
        if not analysis.markdown.strip():
            logger.warning("No usable content from %s", file_path)
            return None

        # Step 2: Recommend additional links/tags from vault context
        recs = self.vm.recommend_links_and_tags(analysis)
        additional_tags = recs.get("additional_tags", [])
        additional_links = recs.get("additional_links", [])

        # Merge recommendations (above threshold) into analysis
        for tag in additional_tags:
            if tag not in analysis.tags:
                analysis.tags.append(tag)
        for link in additional_links:
            if link not in analysis.suggested_links:
                analysis.suggested_links.append(link)

        # Step 3: Write to vault
        note_path = self.vm.write_note(analysis)
        logger.info("Ingestion complete → %s", note_path)
        return note_path

    def ingest_from_drive(self) -> list[Path]:
        """
        Single-pass: poll Google Drive, ingest all new files.
        Returns list of vault note paths created.
        """
        from obsidian_agent.services.gdrive_watcher import poll_once

        created = []
        for meta, local_path in poll_once():
            result = self.ingest_file(local_path)
            if result:
                created.append(result)
        return created

    def watch_drive(self) -> None:
        """Continuous Drive watcher — runs until interrupted."""
        from obsidian_agent.services.gdrive_watcher import watch

        logger.info("Starting continuous Drive watch…")
        watch(lambda meta, path: self.ingest_file(path))

    # ── Pipeline 2: Vault Relationship Analysis ───────────────────────

    def analyze_vault(self) -> Path:
        """
        Run full congruency + catalytic analysis and write the report
        to the AgentReports folder.
        """
        logger.info("Running vault relationship analysis…")
        self.vm.build_index()
        report = relationship_analyzer.generate_report(self.vm)
        today = datetime.now().strftime("%Y-%m-%d")
        return self.vm.write_agent_report(
            f"Vault Relationship Report — {today}", report
        )

    # ── Pipeline 3: Notion Export ─────────────────────────────────────

    def export_to_notion(self) -> Path:
        """
        Triage vault notes and export project-worthy items to Notion.
        Writes a summary report to the vault.
        """
        logger.info("Running monthly Notion export…")
        self.vm.build_index()
        exported = notion_exporter.run_monthly_export(self.vm)
        report = notion_exporter.generate_export_report(self.vm, exported)
        today = datetime.now().strftime("%Y-%m-%d")
        return self.vm.write_agent_report(
            f"Notion Export Report — {today}", report
        )

    # ── Pipeline 4: Research Opportunities ────────────────────────────

    def recommend_research(self) -> Path:
        """
        Scan vault for NBLM projects, Perplexity queries, class ideas,
        and consulting opportunities.  Write report to vault.
        """
        logger.info("Running research opportunity scan…")
        self.vm.build_index()
        report = research_recommender.generate_report(self.vm)
        today = datetime.now().strftime("%Y-%m-%d")
        return self.vm.write_agent_report(
            f"Research Opportunities Report — {today}", report
        )

    # ── Pipeline 5: Run All ───────────────────────────────────────────

    def run_all(self) -> dict:
        """Execute all pipelines in sequence and return a summary."""
        results = {}

        # Ingest from Drive
        try:
            ingested = self.ingest_from_drive()
            results["ingested"] = [str(p) for p in ingested]
        except Exception:
            logger.exception("Drive ingestion failed")
            results["ingested"] = "error"

        # Vault analysis
        try:
            report_path = self.analyze_vault()
            results["vault_analysis"] = str(report_path)
        except Exception:
            logger.exception("Vault analysis failed")
            results["vault_analysis"] = "error"

        # Notion export (only on configured day)
        today_day = datetime.now().day
        if today_day == config.NOTION_DUMP_DAY:
            try:
                report_path = self.export_to_notion()
                results["notion_export"] = str(report_path)
            except Exception:
                logger.exception("Notion export failed")
                results["notion_export"] = "error"
        else:
            results["notion_export"] = (
                f"skipped (runs on day {config.NOTION_DUMP_DAY})"
            )

        # Research recommendations
        try:
            report_path = self.recommend_research()
            results["research"] = str(report_path)
        except Exception:
            logger.exception("Research recommendation failed")
            results["research"] = "error"

        return results
