"""Fireflies.ai report processor.

Uses AI to parse Fireflies meeting summaries, identify clients,
extract tasks and action items, and determine assignees.
"""

import json
import re
from app.services.ai_client import AIClient


class FirefliesProcessor:
    """Processes Fireflies.ai meeting summaries using AI analysis."""

    def __init__(self, ai_client=None):
        self.ai = ai_client or AIClient()

    def parse_fireflies_report(self, raw_report):
        """Parse a raw Fireflies.ai summary report into structured data.

        Args:
            raw_report: The full text of a Fireflies.ai meeting summary.

        Returns:
            Dict with: title, date, attendees, client_name, summary,
                      key_topics, action_items, transcript_highlights.
        """
        system_prompt = """You are an expert meeting analyst. Your job is to parse Fireflies.ai
meeting summary reports and extract structured data.

You must return ONLY valid JSON with no extra text. The JSON must have this exact structure:
{
    "title": "Meeting title or subject",
    "date": "YYYY-MM-DD format if found, otherwise empty string",
    "attendees": ["List", "of", "attendee", "names"],
    "client_name": "The external client/company name (not your own company). Look for company names, client references, or external participant affiliations. If unclear, use the most prominent external name.",
    "summary": "A concise 2-3 paragraph summary of the meeting",
    "key_topics": ["Topic 1 discussed", "Topic 2 discussed"],
    "action_items": [
        {
            "task": "Description of the task or action item",
            "assignee": "Person responsible (full name if available)",
            "priority": "High/Medium/Low",
            "category": "Task/Follow-up/Decision/Action Item"
        }
    ],
    "transcript_highlights": ["Notable quote or key statement 1", "Notable quote 2"]
}

Rules for client identification:
- The client is typically the external party, not the host organization
- Look for mentions of company names, project names tied to external parties
- If the meeting is between two external parties, identify the one being served
- If no clear client is identifiable, use the most prominent external name or company
- Never return an empty client_name — make your best determination

Rules for task extraction:
- Extract ALL action items, commitments, and follow-ups mentioned
- Assign each task to the person who volunteered or was assigned it
- If no specific person was assigned, use "Unassigned"
- Infer priority from context (urgency words, deadlines mentioned, etc.)
- Categorize as Task (concrete deliverable), Follow-up (needs further discussion),
  Decision (something to decide), or Action Item (general action needed)"""

        user_prompt = f"""Parse the following Fireflies.ai meeting summary report and extract all structured data.

--- FIREFLIES REPORT START ---
{raw_report}
--- FIREFLIES REPORT END ---

Return the structured JSON."""

        result = self.ai.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=4096,
            temperature=0.2,
        )

        return self._extract_json(result)

    def identify_client(self, report_text, known_clients=None):
        """Identify which client a meeting report belongs to.

        Args:
            report_text: The raw meeting report text.
            known_clients: Optional list of known client names for matching.

        Returns:
            Dict with: client_name, confidence, is_new_client, matched_existing.
        """
        known_list = json.dumps(known_clients or [])

        system_prompt = """You are a client identification specialist. Given a meeting report
and a list of known clients, determine which client this meeting is associated with.

Return ONLY valid JSON:
{
    "client_name": "The client name (normalized/cleaned)",
    "confidence": "high/medium/low",
    "is_new_client": true/false,
    "matched_existing": "Name of the matched existing client, or null if new",
    "reasoning": "Brief explanation of how you identified the client"
}

Rules:
- Match against known clients using fuzzy matching (e.g., "Acme" matches "Acme Corp", "ACME Inc")
- If the client is clearly a known client (even with slight name variations), set is_new_client to false
- If no known client matches, set is_new_client to true
- Normalize the client name (proper capitalization, remove unnecessary suffixes for matching)
- The client_name should be the canonical/clean version of the name"""

        user_prompt = f"""Identify the client from this meeting report.

Known clients: {known_list}

--- MEETING REPORT ---
{report_text[:3000]}
--- END REPORT ---

Return the identification JSON."""

        result = self.ai.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=1024,
            temperature=0.1,
        )

        return self._extract_json(result)

    def extract_tasks(self, report_text, attendees=None):
        """Extract and structure all tasks from a meeting report.

        Args:
            report_text: The meeting report text.
            attendees: Optional list of attendees for better assignee matching.

        Returns:
            List of task dicts with: name, assignee, due_date, priority, category.
        """
        attendees_str = ", ".join(attendees) if attendees else "Unknown"

        system_prompt = """You are a task extraction specialist. Extract ALL actionable tasks,
commitments, follow-ups, and decisions from meeting transcripts and summaries.

Return ONLY a valid JSON array:
[
    {
        "name": "Clear, actionable description of the task",
        "assignee": "Person responsible (from attendees list if possible)",
        "due_date": "YYYY-MM-DD if mentioned or inferable, otherwise empty string",
        "priority": "High/Medium/Low",
        "category": "Task/Follow-up/Decision/Action Item"
    }
]

Rules:
- Be thorough — capture every commitment, promise, or planned action
- Write task names as clear, actionable statements (start with a verb)
- Match assignees to the attendees list when possible
- If someone says "I'll do X", assign X to that person
- If a deadline is mentioned, include it as due_date in YYYY-MM-DD format
- Infer priority: explicit urgency = High, standard items = Medium, nice-to-haves = Low
- If no tasks are found, return an empty array []"""

        user_prompt = f"""Extract all tasks from this meeting report.

Meeting attendees: {attendees_str}

--- MEETING REPORT ---
{report_text}
--- END REPORT ---

Return the tasks JSON array."""

        result = self.ai.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=4096,
            temperature=0.2,
        )

        parsed = self._extract_json(result)
        if isinstance(parsed, list):
            return parsed
        return parsed.get("tasks", []) if isinstance(parsed, dict) else []

    def _extract_json(self, text):
        """Extract JSON from AI response text, handling markdown code blocks."""
        text = text.strip()

        # Try to find JSON in code blocks
        code_block = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
        if code_block:
            text = code_block.group(1).strip()

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object or array
        for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue

        return {"error": "Failed to parse AI response", "raw": text}
