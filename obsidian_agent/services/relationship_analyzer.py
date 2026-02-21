"""
Relationship Analyzer — examines the entire Obsidian vault for:

  1. **Congruency** — notes that share themes, concepts, or domains and
     could be combined or cross-referenced.
  2. **Catalytic relationships** — pairs (or clusters) of notes whose
     combination could spark a new idea, app, procedure, or workflow.
  3. **Real-world potential** — concrete recommendations for new apps,
     procedures, workflows, classes, or presentations derived from the
     vault's collective knowledge.

Results are written as a structured Obsidian report note.
"""

import json
import logging
from datetime import datetime

import anthropic

from obsidian_agent import config
from obsidian_agent.services.vault_manager import VaultManager

logger = logging.getLogger(__name__)


def _build_vault_digest(vm: VaultManager) -> str:
    """Create a compact text digest of the vault for the prompt."""
    lines = []
    for note in vm.index:
        tags = ", ".join(note.tags[:8])
        links = ", ".join(note.links[:8])
        summary_part = f" — {note.summary}" if note.summary else ""
        lines.append(f"- **{note.title}**  [tags: {tags}] [links: {links}]{summary_part}")
    return "\n".join(lines)


def analyze_relationships(vm: VaultManager) -> dict:
    """
    Run a full vault relationship analysis via Claude.

    Returns a dict with keys:
      - congruent_clusters: groups of related notes
      - catalytic_pairs: pairs with combinatory potential
      - recommendations: concrete real-world ideas
    """
    digest = _build_vault_digest(vm)

    if not digest.strip():
        logger.warning("Vault is empty — nothing to analyze.")
        return {
            "congruent_clusters": [],
            "catalytic_pairs": [],
            "recommendations": [],
        }

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=8192,
        system=(
            "You are an innovation analyst and knowledge-graph expert.\n\n"
            "Given a digest of notes from an Obsidian vault, perform three analyses:\n\n"
            "1. **Congruency Analysis** — Identify clusters of notes that share "
            "themes, domains, or concepts.  For each cluster, explain the shared "
            "thread and how the notes reinforce each other.\n\n"
            "2. **Catalytic Relationship Analysis** — Find pairs or small groups "
            "of notes that, when combined, could catalyze a new insight.  These "
            "are notes from *different* domains whose intersection is non-obvious "
            "but promising.\n\n"
            "3. **Real-World Recommendations** — Based on the above, propose "
            "concrete, actionable ideas: a new app, tool, workflow, standard "
            "operating procedure, class, or presentation.  Each recommendation "
            "should cite the vault notes that inspired it.\n\n"
            "Respond with ONLY a JSON object (no markdown fences):\n"
            "{\n"
            '  "congruent_clusters": [\n'
            '    {"notes": ["Title1","Title2"], "theme": "...", "explanation": "..."}\n'
            "  ],\n"
            '  "catalytic_pairs": [\n'
            '    {"notes": ["TitleA","TitleB"], "spark": "...", "potential": "..."}\n'
            "  ],\n"
            '  "recommendations": [\n'
            '    {"type": "app|workflow|procedure|class|presentation",\n'
            '     "title": "...", "description": "...", "source_notes": ["..."],\n'
            '     "next_steps": ["..."]}\n'
            "  ]\n"
            "}"
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"## Vault Digest ({len(vm.index)} notes)\n\n{digest}"
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
        logger.error("Failed to parse relationship analysis: %s", text[:500])
        return {
            "congruent_clusters": [],
            "catalytic_pairs": [],
            "recommendations": [],
        }


def generate_report(vm: VaultManager) -> str:
    """Run analysis and produce a formatted Obsidian Markdown report."""
    results = analyze_relationships(vm)
    today = datetime.now().strftime("%Y-%m-%d")

    sections = [
        "---",
        f'title: "Vault Relationship Report — {today}"',
        "tags: [agent-report, relationship-analysis]",
        f"date: {today}",
        "---",
        "",
        f"# Vault Relationship Report — {today}",
        "",
    ]

    # Congruent clusters
    sections.append("## Congruent Clusters")
    sections.append("")
    for i, cluster in enumerate(results.get("congruent_clusters", []), 1):
        notes = ", ".join(f"[[{n}]]" for n in cluster.get("notes", []))
        sections.append(f"### Cluster {i}: {cluster.get('theme', 'Unnamed')}")
        sections.append(f"**Notes:** {notes}")
        sections.append(f"\n{cluster.get('explanation', '')}")
        sections.append("")

    # Catalytic pairs
    sections.append("## Catalytic Relationships")
    sections.append("")
    for pair in results.get("catalytic_pairs", []):
        notes = " × ".join(f"[[{n}]]" for n in pair.get("notes", []))
        sections.append(f"### {notes}")
        sections.append(f"**Spark:** {pair.get('spark', '')}")
        sections.append(f"**Potential:** {pair.get('potential', '')}")
        sections.append("")

    # Recommendations
    sections.append("## Real-World Recommendations")
    sections.append("")
    for rec in results.get("recommendations", []):
        rtype = rec.get("type", "idea").upper()
        sources = ", ".join(f"[[{n}]]" for n in rec.get("source_notes", []))
        sections.append(f"### [{rtype}] {rec.get('title', 'Untitled')}")
        sections.append(f"{rec.get('description', '')}")
        sections.append(f"\n**Source notes:** {sources}")
        next_steps = rec.get("next_steps", [])
        if next_steps:
            sections.append("**Next steps:**")
            for step in next_steps:
                sections.append(f"- [ ] {step}")
        sections.append("")

    return "\n".join(sections)
