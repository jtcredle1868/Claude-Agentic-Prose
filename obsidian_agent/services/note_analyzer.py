"""
Note Analyzer — takes raw input (plain English text, lists, sketched
structures, CSVs, or OCR'd image text) and uses Claude to:

  1. Understand the content and intent
  2. Identify structure (prose, list, outline, chart/table, diagram sketch)
  3. Generate tags and suggested Obsidian links
  4. Convert everything into clean Obsidian-flavoured Markdown
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from obsidian_agent import config

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Container for everything the analyzer produces from a single note."""
    title: str = ""
    markdown: str = ""
    tags: list[str] = field(default_factory=list)
    suggested_links: list[str] = field(default_factory=list)
    note_type: str = "general"          # general | list | outline | table | diagram
    summary: str = ""
    key_concepts: list[str] = field(default_factory=list)
    confidence: float = 0.0


ANALYSIS_SYSTEM_PROMPT = """\
You are an expert note analyst for an Obsidian knowledge management vault.

Given raw note content (which may be plain English, a hand-written list,
a sketched chart or table description, or any informal structure), you must:

1. **Understand** the content — determine the topic, intent, and structure.
2. **Classify** the note type: general | list | outline | table | diagram.
3. **Generate a title** — concise, descriptive, suitable as a file name.
4. **Extract key concepts** — the core ideas or entities mentioned.
5. **Suggest tags** — Obsidian-style tags (e.g. #productivity, #AI).
   Use lowercase, hyphenated multi-word tags.  Aim for 3-8 tags.
6. **Suggest wikilinks** — concepts that likely correspond to other notes
   in a knowledge vault (format: [[Concept Name]]).
7. **Convert to Markdown** — clean, well-structured Obsidian-flavoured
   Markdown.  Use headings, lists, tables, callouts as appropriate.
   Preserve the author's meaning exactly; improve only structure and
   formatting, never rewrite ideas.
8. **Write a 1-2 sentence summary** of the note.

Respond with ONLY a JSON object (no markdown fences) with these keys:
{
  "title": "...",
  "note_type": "general|list|outline|table|diagram",
  "summary": "...",
  "key_concepts": ["..."],
  "tags": ["#tag1", "#tag2"],
  "suggested_links": ["[[Link1]]", "[[Link2]]"],
  "markdown": "...",
  "confidence": 0.0-1.0
}
"""


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _extract_text_from_file(file_path: Path) -> str:
    """Read text from a supported file.  For images, attempt OCR via Claude."""
    suffix = file_path.suffix.lower()

    if suffix in (".txt", ".md", ".csv"):
        return file_path.read_text(encoding="utf-8", errors="replace")

    if suffix == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                return "\n\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
        except ImportError:
            logger.warning("pdfplumber not installed — skipping PDF %s", file_path)
            return ""

    if suffix in (".png", ".jpg", ".jpeg"):
        return _ocr_via_claude(file_path)

    # Fallback: try reading as text
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        logger.warning("Cannot read file %s", file_path)
        return ""


def _ocr_via_claude(image_path: Path) -> str:
    """Use Claude's vision capability to extract text from an image."""
    import base64

    client = _get_client()
    media_type = (
        "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    )
    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")

    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract ALL text from this image exactly as written. "
                            "If it contains a sketch, diagram, list, or chart, "
                            "describe the structure and content in detail. "
                            "Return only the extracted content."
                        ),
                    },
                ],
            }
        ],
    )
    return response.content[0].text


def analyze_note(file_path: Path) -> AnalysisResult:
    """
    Full analysis pipeline for a single note file.

    Returns an AnalysisResult with title, markdown, tags, links, etc.
    """
    raw_text = _extract_text_from_file(file_path)
    if not raw_text.strip():
        logger.warning("Empty content from %s — skipping.", file_path)
        return AnalysisResult()

    client = _get_client()
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=8192,
        system=ANALYSIS_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Analyze the following raw note and produce the JSON output.\n\n"
                    f"--- RAW NOTE ---\n{raw_text}\n--- END ---"
                ),
            }
        ],
    )

    text = response.content[0].text.strip()
    # Strip markdown fences if the model wraps anyway
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse analysis JSON — raw: %s", text[:500])
        return AnalysisResult(
            title=file_path.stem,
            markdown=raw_text,
            summary="Analysis failed; raw content preserved.",
        )

    return AnalysisResult(
        title=data.get("title", file_path.stem),
        markdown=data.get("markdown", raw_text),
        tags=data.get("tags", []),
        suggested_links=data.get("suggested_links", []),
        note_type=data.get("note_type", "general"),
        summary=data.get("summary", ""),
        key_concepts=data.get("key_concepts", []),
        confidence=float(data.get("confidence", 0.0)),
    )
