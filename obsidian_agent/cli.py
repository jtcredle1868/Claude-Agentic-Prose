"""
CLI entry point for the Obsidian AI Agent.

Usage:
  python -m obsidian_agent ingest          # One-shot: poll Drive and ingest
  python -m obsidian_agent watch           # Continuous Drive watcher
  python -m obsidian_agent analyze         # Vault relationship analysis
  python -m obsidian_agent export          # Monthly Notion export
  python -m obsidian_agent research        # Research opportunity scan
  python -m obsidian_agent run-all         # Execute all pipelines
  python -m obsidian_agent ingest-file <path>  # Ingest a single local file
"""

import argparse
import json
import sys
from pathlib import Path

from obsidian_agent.orchestrator import ObsidianAgent


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="obsidian-agent",
        description="Obsidian AI Agent — automated note ingestion, analysis, and research.",
    )
    parser.add_argument(
        "--vault",
        type=Path,
        default=None,
        help="Path to the Obsidian vault (overrides OBSIDIAN_VAULT_PATH env var).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="One-shot: poll Google Drive and ingest new notes.")
    sub.add_parser("watch", help="Continuously watch Google Drive for new notes.")
    sub.add_parser("analyze", help="Run vault relationship & congruency analysis.")
    sub.add_parser("export", help="Run monthly Notion export of project-worthy notes.")
    sub.add_parser("research", help="Scan vault for research opportunities (NBLM, classes, consulting).")
    sub.add_parser("run-all", help="Execute all pipelines in sequence.")

    ingest_file = sub.add_parser("ingest-file", help="Ingest a single local file into the vault.")
    ingest_file.add_argument("file", type=Path, help="Path to the file to ingest.")

    args = parser.parse_args()
    agent = ObsidianAgent(vault_path=args.vault)

    if args.command == "ingest":
        created = agent.ingest_from_drive()
        print(f"Ingested {len(created)} note(s).")
        for p in created:
            print(f"  → {p}")

    elif args.command == "watch":
        print("Watching Google Drive (Ctrl+C to stop)…")
        try:
            agent.watch_drive()
        except KeyboardInterrupt:
            print("\nStopped.")

    elif args.command == "analyze":
        report = agent.analyze_vault()
        print(f"Relationship report written → {report}")

    elif args.command == "export":
        report = agent.export_to_notion()
        print(f"Notion export report written → {report}")

    elif args.command == "research":
        report = agent.recommend_research()
        print(f"Research report written → {report}")

    elif args.command == "run-all":
        results = agent.run_all()
        print(json.dumps(results, indent=2))

    elif args.command == "ingest-file":
        path = args.file
        if not path.exists():
            print(f"Error: file not found — {path}", file=sys.stderr)
            sys.exit(1)
        result = agent.ingest_file(path)
        if result:
            print(f"Note written → {result}")
        else:
            print("No usable content extracted.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
