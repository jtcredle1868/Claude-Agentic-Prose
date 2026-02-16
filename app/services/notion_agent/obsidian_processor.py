"""Obsidian monthly review processor.

Parses Obsidian markdown exports containing project ideas and uses AI
to create structured project plans with tasks, milestones, and timelines.
"""

import json
import re
from app.services.ai_client import AIClient


class ObsidianProcessor:
    """Processes Obsidian markdown exports into structured project plans."""

    def __init__(self, ai_client=None):
        self.ai = ai_client or AIClient()

    def parse_obsidian_export(self, markdown_content):
        """Parse an Obsidian markdown export to extract individual project ideas.

        Args:
            markdown_content: Raw markdown text from Obsidian export.

        Returns:
            List of dicts, each with: title, raw_content, tags, links.
        """
        system_prompt = """You are an expert at parsing Obsidian markdown notes. Your job is to
identify distinct project ideas or concepts from a monthly review export.

Return ONLY valid JSON — an array of project ideas:
[
    {
        "title": "Project title or name",
        "raw_content": "The full raw content/description of this project idea",
        "tags": ["tag1", "tag2"],
        "links": ["any [[wikilinks]] or references found"],
        "category": "software/business/creative/research/infrastructure/other"
    }
]

Rules:
- Each distinct project idea should be its own entry
- Preserve the original content in raw_content
- Extract any #tags or [[wikilinks]] found
- If the export contains multiple ideas separated by headings, split them
- If it's a single cohesive idea, return a single-item array
- Categorize each idea based on its nature"""

        user_prompt = f"""Parse this Obsidian monthly review export and extract all project ideas.

--- OBSIDIAN EXPORT ---
{markdown_content}
--- END EXPORT ---

Return the structured JSON array."""

        result = self.ai.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=4096,
            temperature=0.2,
        )

        parsed = self._extract_json(result)
        if isinstance(parsed, list):
            return parsed
        return [parsed] if isinstance(parsed, dict) and "title" in parsed else []

    def generate_project_plan(self, idea):
        """Generate a full project plan from a raw idea.

        Args:
            idea: Dict with at minimum 'title' and 'raw_content'.

        Returns:
            Dict with: title, description, tasks, milestones, due_dates,
                      timeline_recommendation, requirements.
        """
        system_prompt = """You are a senior project manager and technical architect. Given a raw
project idea, create a comprehensive project plan.

Return ONLY valid JSON:
{
    "title": "Clean project title",
    "description": "2-3 paragraph project description explaining scope, goals, and expected outcomes",
    "requirements": [
        "Specific requirement 1",
        "Specific requirement 2"
    ],
    "tasks": [
        {
            "name": "Clear actionable task description (start with a verb)",
            "assignee": "Role that should handle this (e.g., 'Developer', 'Designer', 'PM')",
            "due_date": "YYYY-MM-DD (calculate realistic dates starting from today)",
            "priority": "High/Medium/Low",
            "phase": "Planning/Design/Development/Testing/Launch"
        }
    ],
    "milestones": [
        {
            "name": "Milestone name",
            "target_date": "YYYY-MM-DD",
            "description": "What this milestone represents",
            "deliverables": ["Deliverable 1", "Deliverable 2"]
        }
    ],
    "timeline_recommendation": "A detailed paragraph recommending overall timeline, key dependencies, critical path items, risks, and suggestions for execution. Include specific date ranges and phase durations.",
    "estimated_duration_weeks": 8,
    "team_size_recommendation": "Recommended team composition",
    "risks": ["Risk 1", "Risk 2"],
    "next_steps": ["Immediate next step 1", "Immediate next step 2"]
}

Rules:
- Create realistic, actionable tasks (not vague)
- Tasks should be ordered logically with dependencies in mind
- Set due dates that are realistic (don't compress everything into one week)
- Milestones should mark meaningful progress points
- The timeline recommendation should be specific and actionable
- Assign tasks to roles, not specific people (unless names are provided)
- Include both technical and non-technical tasks (design, documentation, testing)
- Factor in review cycles and iteration time"""

        from datetime import datetime
        today = datetime.utcnow().strftime("%Y-%m-%d")

        user_prompt = f"""Create a detailed project plan for this idea. Today's date is {today}.

Project Title: {idea.get('title', 'Untitled')}
Category: {idea.get('category', 'general')}
Tags: {', '.join(idea.get('tags', []))}

--- RAW IDEA ---
{idea.get('raw_content', idea.get('description', ''))}
--- END IDEA ---

Generate the complete project plan JSON."""

        result = self.ai.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=8192,
            temperature=0.3,
        )

        return self._extract_json(result)

    def batch_process_ideas(self, markdown_content):
        """Full pipeline: parse Obsidian export, then generate plans for each idea.

        Args:
            markdown_content: Raw Obsidian markdown export.

        Returns:
            List of project plan dicts.
        """
        ideas = self.parse_obsidian_export(markdown_content)
        plans = []
        for idea in ideas:
            plan = self.generate_project_plan(idea)
            if not plan.get("error"):
                plans.append(plan)
        return plans

    def _extract_json(self, text):
        """Extract JSON from AI response text."""
        text = text.strip()

        code_block = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
        if code_block:
            text = code_block.group(1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue

        return {"error": "Failed to parse AI response", "raw": text}
