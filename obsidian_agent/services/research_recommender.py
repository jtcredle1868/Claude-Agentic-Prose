"""
Research Recommender — analyzes the vault to identify opportunities for:

  1. **NBLM (Next-Best-Learning-Move) projects** — knowledge gaps or
     emerging themes that deserve deeper investigation.
  2. **Perplexity research reports** — focused research queries that could
     benefit consulting, clients, or personal development.
  3. **Class / presentation ideas** — topics where the vault has enough
     depth to create teaching material or a talk.

Results are written as an actionable Obsidian report.
"""

import json
import logging
from datetime import datetime

import anthropic

from obsidian_agent import config
from obsidian_agent.services.vault_manager import VaultManager

logger = logging.getLogger(__name__)


def identify_opportunities(vm: VaultManager) -> dict:
    """
    Use Claude to scan the vault digest and surface research opportunities.

    Returns dict with keys: nblm_projects, perplexity_queries,
    class_ideas, consulting_opportunities.
    """
    digest_lines = []
    for note in vm.index:
        tags = ", ".join(note.tags[:6])
        links = ", ".join(note.links[:6])
        digest_lines.append(
            f"- {note.title} | tags: [{tags}] | links: [{links}] "
            f"| summary: {note.summary[:100]}"
        )
    digest = "\n".join(digest_lines)

    domains = ", ".join(config.CONSULTING_DOMAINS)

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=8192,
        system=(
            "You are a strategic research advisor and innovation consultant.\n\n"
            "Given a digest of notes from a knowledge vault and the user's "
            f"consulting domains ({domains}), identify:\n\n"
            "1. **NBLM Projects** — Next-Best-Learning-Move projects.  These are "
            "knowledge gaps, emerging themes, or under-developed ideas in the vault "
            "that deserve a dedicated research sprint.  Each should have a clear "
            "learning objective and suggested resources.\n\n"
            "2. **Perplexity Research Queries** — specific, well-formed research "
            "questions that could be submitted to Perplexity (or similar deep-search "
            "tools) to generate reports.  Each should target a gap or opportunity.\n\n"
            "3. **Class / Presentation Ideas** — topics where the vault contains "
            "enough depth and breadth to develop a class, workshop, or conference "
            "talk.  Include a tentative outline.\n\n"
            "4. **Consulting Opportunities** — insights from the vault that could "
            "directly benefit the user's consulting clients or open new engagements.\n\n"
            "Respond with JSON (no fences):\n"
            "{\n"
            '  "nblm_projects": [\n'
            '    {"title": "...", "objective": "...", "source_notes": ["..."],\n'
            '     "suggested_resources": ["..."], "priority": "high|medium|low"}\n'
            "  ],\n"
            '  "perplexity_queries": [\n'
            '    {"query": "...", "context": "...", "expected_value": "..."}\n'
            "  ],\n"
            '  "class_ideas": [\n'
            '    {"title": "...", "description": "...", "source_notes": ["..."],\n'
            '     "outline": ["..."]}\n'
            "  ],\n"
            '  "consulting_opportunities": [\n'
            '    {"opportunity": "...", "client_relevance": "...",\n'
            '     "source_notes": ["..."]}\n'
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
        logger.error("Failed to parse research recommendations: %s", text[:500])
        return {
            "nblm_projects": [],
            "perplexity_queries": [],
            "class_ideas": [],
            "consulting_opportunities": [],
        }


def generate_report(vm: VaultManager) -> str:
    """Run analysis and produce a formatted Obsidian Markdown report."""
    results = identify_opportunities(vm)
    today = datetime.now().strftime("%Y-%m-%d")

    sections = [
        "---",
        f'title: "Research Opportunities Report — {today}"',
        "tags: [agent-report, research-opportunities, nblm]",
        f"date: {today}",
        "---",
        "",
        f"# Research Opportunities Report — {today}",
        "",
    ]

    # NBLM Projects
    sections.append("## NBLM Projects")
    sections.append("")
    for proj in results.get("nblm_projects", []):
        sources = ", ".join(f"[[{n}]]" for n in proj.get("source_notes", []))
        priority = proj.get("priority", "medium").upper()
        sections.append(f"### [{priority}] {proj.get('title', 'Untitled')}")
        sections.append(f"**Objective:** {proj.get('objective', '')}")
        sections.append(f"**Source notes:** {sources}")
        resources = proj.get("suggested_resources", [])
        if resources:
            sections.append("**Suggested resources:**")
            for r in resources:
                sections.append(f"- {r}")
        sections.append("")

    # Perplexity queries
    sections.append("## Perplexity Research Queries")
    sections.append("")
    for q in results.get("perplexity_queries", []):
        sections.append(f"### Query: {q.get('query', '')}")
        sections.append(f"**Context:** {q.get('context', '')}")
        sections.append(f"**Expected value:** {q.get('expected_value', '')}")
        sections.append("")

    # Class ideas
    sections.append("## Class & Presentation Ideas")
    sections.append("")
    for idea in results.get("class_ideas", []):
        sources = ", ".join(f"[[{n}]]" for n in idea.get("source_notes", []))
        sections.append(f"### {idea.get('title', 'Untitled')}")
        sections.append(f"{idea.get('description', '')}")
        sections.append(f"**Source notes:** {sources}")
        outline = idea.get("outline", [])
        if outline:
            sections.append("**Tentative outline:**")
            for i, item in enumerate(outline, 1):
                sections.append(f"{i}. {item}")
        sections.append("")

    # Consulting opportunities
    sections.append("## Consulting Opportunities")
    sections.append("")
    for opp in results.get("consulting_opportunities", []):
        sources = ", ".join(f"[[{n}]]" for n in opp.get("source_notes", []))
        sections.append(f"### {opp.get('opportunity', 'Untitled')}")
        sections.append(f"**Client relevance:** {opp.get('client_relevance', '')}")
        sections.append(f"**Source notes:** {sources}")
        sections.append("")

    return "\n".join(sections)
