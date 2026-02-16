"""Service for expanding ideas, concepts, and drafts into full prose."""

from app.services.ai_client import AIClient


class ExpansionService:
    """Transforms short ideas into narratively complex, publication-ready prose."""

    def __init__(self, ai_client=None):
        self.ai = ai_client or AIClient()

    def expand_idea_to_outline(self, idea, project_type="fiction", genre="", num_chapters=12):
        """Take a raw idea or concept and generate a full project outline."""
        system = (
            "You are a master literary architect and developmental editor with decades of "
            "experience crafting bestselling novels and acclaimed nonfiction. You create "
            "detailed, narratively compelling outlines that serve as robust blueprints for "
            "full manuscripts. Your outlines feature strong narrative arcs, thematic depth, "
            "and commercially viable structure."
        )
        prompt = f"""Take the following idea and develop it into a comprehensive {project_type} outline
with {num_chapters} chapters.

IDEA: {idea}
GENRE: {genre or 'Determine the best genre fit'}
TYPE: {project_type}

Provide the outline in this exact format:

TITLE: [Compelling title]
SUBTITLE: [If applicable]
GENRE: [Specific genre/subgenre]
SYNOPSIS: [2-3 paragraph synopsis suitable for a query letter]
THEMES: [Comma-separated list of major themes]
SETTING: [Description of the primary setting(s)]

CHARACTERS:
- [Name] | [Role: protagonist/antagonist/supporting] | [Brief description] | [Motivation] | [Arc]
(List all major characters)

CHAPTERS:
Chapter 1: [Title]
Summary: [Detailed 2-3 paragraph summary of chapter events, character development, and narrative purpose]
POV: [Point of view character if applicable]
Setting: [Chapter setting]

(Continue for all {num_chapters} chapters)

Ensure the outline has:
- A compelling narrative arc with rising action, climax, and resolution
- Well-developed character arcs that intersect meaningfully
- Thematic consistency throughout
- Proper pacing with tension and release
- A satisfying but not predictable ending"""

        return self.ai.generate(system, prompt, max_tokens=8192)

    def expand_outline_to_chapter(self, chapter_summary, project_context, chapter_num=1,
                                   style_notes="", target_words=4000):
        """Expand a chapter outline/summary into full prose."""
        system = (
            "You are an award-winning author known for literary prose that is both "
            "accessible and artistically sophisticated. You write with vivid sensory "
            "detail, psychologically complex characters, authentic dialogue, and "
            "masterful pacing. Your prose reads naturally and avoids purple prose while "
            "maintaining literary quality appropriate for traditional publication."
        )
        prompt = f"""Write Chapter {chapter_num} as full, publication-quality prose based on the following:

PROJECT CONTEXT:
{project_context}

CHAPTER SUMMARY:
{chapter_summary}

STYLE NOTES: {style_notes or 'Literary fiction with accessible prose'}
TARGET LENGTH: Approximately {target_words} words

Requirements:
- Write complete, polished prose ready for editorial review
- Open the chapter with a compelling hook
- Develop scenes with full sensory detail and interiority
- Write natural, character-revealing dialogue with distinct voices
- Use varied sentence structure and paragraph length for rhythm
- Maintain consistent tone and point of view
- End with a compelling chapter ending that drives the reader forward
- Include scene breaks (marked with ###) where appropriate
- Show, don't tell—convey emotion through action and sensory detail
- Ensure continuity with the project context provided

Write the complete chapter now:"""

        return self.ai.generate(system, prompt, max_tokens=8192, temperature=0.8)

    def expand_scene(self, scene_brief, chapter_context, scene_type="action"):
        """Expand a brief scene description into full prose."""
        system = (
            "You are a masterful prose stylist who excels at crafting immersive, "
            "emotionally resonant scenes. Every scene you write serves multiple "
            "purposes: advancing plot, revealing character, building theme, and "
            "engaging the reader's senses."
        )
        prompt = f"""Write a complete scene based on the following:

SCENE BRIEF: {scene_brief}
SCENE TYPE: {scene_type}
CHAPTER CONTEXT: {chapter_context}

Write this scene with full sensory immersion, natural dialogue, and emotional depth.
The scene should feel organic within its chapter context and serve clear narrative purposes."""

        return self.ai.generate(system, prompt, max_tokens=8192, temperature=0.8)

    def develop_concept(self, raw_concept, project_type="fiction"):
        """Take a very rough concept and develop it into a fleshed-out idea."""
        system = (
            "You are a creative development consultant who helps writers transform "
            "rough concepts into viable, compelling story ideas. You think about "
            "commercial viability, thematic resonance, narrative potential, and "
            "originality."
        )
        prompt = f"""Develop the following raw concept into a fully fleshed-out {project_type} idea:

RAW CONCEPT: {raw_concept}

Provide:
1. DEVELOPED PREMISE: A compelling, specific premise (2-3 paragraphs)
2. UNIQUE ANGLE: What makes this fresh and different from existing works
3. TARGET AUDIENCE: Who this would appeal to and comparable titles
4. THEMATIC DEPTH: Core themes and what the work explores about the human condition
5. NARRATIVE APPROACH: Recommended structure, POV, tone, and style
6. KEY CONFLICTS: Central conflicts (internal and external) that drive the narrative
7. COMMERCIAL VIABILITY: Why this would resonate with readers and publishers
8. POTENTIAL CHALLENGES: Writing challenges to be aware of and strategies to address them"""

        return self.ai.generate(system, prompt, max_tokens=4096)

    def generate_chapter_from_beats(self, beats, project_context, chapter_num=1, target_words=4000):
        """Generate a chapter from a list of story beats/plot points."""
        system = (
            "You are an expert fiction author who transforms story beats into "
            "seamless, immersive narrative prose. You understand that beats are "
            "the skeleton—your job is to add the flesh, blood, and soul."
        )
        beats_text = "\n".join(f"- {beat}" for beat in beats) if isinstance(beats, list) else beats
        prompt = f"""Transform these story beats into a complete Chapter {chapter_num}:

STORY BEATS:
{beats_text}

PROJECT CONTEXT:
{project_context}

TARGET LENGTH: ~{target_words} words

Write full, publication-quality prose that incorporates all beats naturally.
Don't let the seams show—the reader should never feel they're reading a
sequence of events, but rather experiencing an organic narrative flow."""

        return self.ai.generate(system, prompt, max_tokens=8192, temperature=0.8)
