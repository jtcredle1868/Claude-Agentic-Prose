"""Service for editing, correcting, improving, and rewriting prose."""

from app.services.ai_client import AIClient


class EditorService:
    """Professional-grade editing, revision, and prose improvement."""

    def __init__(self, ai_client=None):
        self.ai = ai_client or AIClient()

    def developmental_edit(self, content, project_context=""):
        """Provide a developmental edit with structural and narrative feedback."""
        system = (
            "You are a senior developmental editor at a major publishing house with "
            "25+ years of experience. You provide constructive, specific, actionable "
            "feedback that respects the author's voice while strengthening the work."
        )
        prompt = f"""Provide a thorough developmental edit of the following text:

{f'PROJECT CONTEXT: {project_context}' if project_context else ''}

TEXT TO EDIT:
{content}

Provide your editorial feedback in these categories:

1. OVERALL ASSESSMENT: Strengths and general impressions (2-3 paragraphs)
2. STRUCTURE & PACING: Analysis of narrative flow, scene structure, chapter rhythm
3. CHARACTER: Voice consistency, development, authenticity of dialogue
4. PLOT & NARRATIVE: Logic, tension, stakes, foreshadowing, payoffs
5. PROSE QUALITY: Sentence-level craft, word choice, imagery, rhythm
6. THEMATIC COHERENCE: How well themes are woven through the narrative
7. SPECIFIC LINE EDITS: Cite 5-10 specific passages with suggested improvements
8. PRIORITY REVISIONS: Ordered list of the most important changes to make

Be honest but encouraging. Identify what's working well alongside what needs improvement."""

        return self.ai.generate(system, prompt, max_tokens=8192)

    def line_edit(self, content):
        """Perform detailed line editing for prose quality."""
        system = (
            "You are an expert line editor known for polishing prose to publication "
            "standard while preserving the author's unique voice. You focus on "
            "sentence-level craft: rhythm, word choice, clarity, and impact."
        )
        prompt = f"""Perform a thorough line edit of the following text. Return the edited text
with tracked changes indicated in this format:
- Deletions: [DEL: removed text]
- Additions: [ADD: new text]
- Suggestions: [SUGGEST: alternative phrasing | reason]

Focus on:
- Eliminating redundancy and wordiness
- Strengthening verbs and reducing adverb dependence
- Improving sentence rhythm and variety
- Fixing awkward constructions
- Enhancing imagery and sensory detail
- Ensuring consistent tone and voice
- Catching cliche and suggesting fresh alternatives

TEXT TO EDIT:
{content}

Provide the edited text followed by a brief summary of the types of changes made."""

        return self.ai.generate(system, prompt, max_tokens=8192)

    def copy_edit(self, content):
        """Perform copy editing for grammar, punctuation, consistency."""
        system = (
            "You are a meticulous copy editor who follows the Chicago Manual of Style. "
            "You catch every grammatical error, punctuation issue, and consistency "
            "problem while respecting intentional stylistic choices."
        )
        prompt = f"""Perform a thorough copy edit of the following text:

TEXT:
{content}

Return:
1. CORRECTED TEXT: The fully corrected text
2. CHANGES LOG: A numbered list of every change made and why
3. STYLE NOTES: Any style consistency issues to watch for in the larger work
4. QUERIES: Any questions for the author about ambiguous passages"""

        return self.ai.generate(system, prompt, max_tokens=8192)

    def rewrite_passage(self, content, instructions, preserve_voice=True):
        """Rewrite a passage according to specific instructions."""
        system = (
            "You are a skilled ghostwriter and prose artisan who can rewrite text "
            "to meet any specification while maintaining narrative coherence and "
            "literary quality."
        )
        voice_note = (
            "Carefully preserve the author's original voice, tone, and style."
            if preserve_voice else
            "You may adapt the voice and style as the instructions require."
        )
        prompt = f"""Rewrite the following passage according to these instructions:

INSTRUCTIONS: {instructions}
NOTE: {voice_note}

ORIGINAL TEXT:
{content}

Provide:
1. REWRITTEN TEXT: The complete rewritten passage
2. REVISION NOTES: Brief explanation of the key changes and why they address the instructions"""

        return self.ai.generate(system, prompt, max_tokens=8192, temperature=0.7)

    def improve_prose(self, content, focus_areas=None):
        """Generally improve prose quality across multiple dimensions."""
        areas = focus_areas or ["clarity", "imagery", "rhythm", "impact"]
        areas_str = ", ".join(areas)
        system = (
            "You are a prose improvement specialist who elevates writing from good "
            "to exceptional. You enhance without overwriting—improving the text while "
            "keeping it recognizably the author's work."
        )
        prompt = f"""Improve the following prose with focus on: {areas_str}

ORIGINAL TEXT:
{content}

Return:
1. IMPROVED TEXT: The enhanced version
2. IMPROVEMENT NOTES: What was changed and why, organized by focus area"""

        return self.ai.generate(system, prompt, max_tokens=8192, temperature=0.7)

    def check_continuity(self, chapters_content, project_context=""):
        """Check for continuity errors across chapters."""
        system = (
            "You are a continuity editor with an encyclopedic memory for detail. "
            "You catch every inconsistency in timelines, character details, settings, "
            "and plot points."
        )
        prompt = f"""Review the following chapters for continuity errors:

{f'PROJECT CONTEXT: {project_context}' if project_context else ''}

CHAPTERS:
{chapters_content}

Identify:
1. TIMELINE INCONSISTENCIES: Any chronological errors or impossible sequences
2. CHARACTER INCONSISTENCIES: Changes in appearance, behavior, knowledge, or abilities that aren't explained
3. SETTING ERRORS: Contradictions in physical descriptions, distances, layouts
4. PLOT HOLES: Logical gaps, unresolved threads, contradictory events
5. FACTUAL ERRORS: Any incorrect real-world facts or internal world-building contradictions
6. DIALOGUE CONSISTENCY: Characters saying things that contradict established knowledge

For each issue, cite the specific passages involved and suggest a fix."""

        return self.ai.generate(system, prompt, max_tokens=8192)

    def adjust_tone(self, content, target_tone, current_tone=""):
        """Adjust the tone of a passage while preserving content."""
        system = (
            "You are an expert at modulating prose tone while maintaining meaning "
            "and narrative integrity. You understand the subtle craft of how word "
            "choice, sentence structure, and pacing create emotional tone."
        )
        prompt = f"""Adjust the tone of the following passage:

CURRENT TONE: {current_tone or 'As written'}
TARGET TONE: {target_tone}

TEXT:
{content}

Return the rewritten passage with the adjusted tone. Preserve all plot points,
character actions, and essential information while shifting the emotional register."""

        return self.ai.generate(system, prompt, max_tokens=8192, temperature=0.7)

    def strengthen_dialogue(self, content):
        """Improve dialogue to be more natural, distinct, and character-revealing."""
        system = (
            "You are a dialogue specialist who makes characters sound like real people "
            "with distinct voices. Every line of dialogue you write reveals character, "
            "advances plot, or creates tension—ideally all three."
        )
        prompt = f"""Improve the dialogue in the following passage:

TEXT:
{content}

Focus on:
- Making each character's voice distinct and recognizable
- Removing on-the-nose dialogue (characters stating exactly what they feel)
- Adding subtext—what's said beneath what's said
- Using dialogue beats and action tags instead of adverb-heavy attribution
- Ensuring dialogue sounds natural when read aloud
- Cutting unnecessary pleasantries and filler

Return:
1. IMPROVED TEXT: The passage with strengthened dialogue
2. DIALOGUE NOTES: Key changes and the reasoning behind them"""

        return self.ai.generate(system, prompt, max_tokens=8192, temperature=0.8)
