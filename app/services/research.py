"""Service for research support and fact-checking for writing projects."""

from app.services.ai_client import AIClient


class ResearchService:
    """Research support for fiction and nonfiction writing projects."""

    def __init__(self, ai_client=None):
        self.ai = ai_client or AIClient()

    def research_topic(self, topic, project_context="", depth="standard"):
        """Research a topic relevant to the writing project."""
        depth_instructions = {
            "brief": "Provide a concise overview with key facts.",
            "standard": "Provide a thorough overview with key facts, historical context, and relevant details.",
            "deep": "Provide an exhaustive analysis with historical context, nuances, controversies, expert perspectives, and primary source references.",
        }
        system = (
            "You are a research specialist who supports authors with accurate, "
            "detailed, and well-organized information. You understand that writers "
            "need not just facts, but the telling details, sensory information, and "
            "authentic nuances that bring settings, characters, and events to life. "
            "Always note when information might need verification from primary sources."
        )
        prompt = f"""Research the following topic for a writing project:

TOPIC: {topic}
{f'PROJECT CONTEXT: {project_context}' if project_context else ''}
DEPTH: {depth_instructions.get(depth, depth_instructions['standard'])}

Provide your research organized as:

1. OVERVIEW: Core facts and context the writer needs to know
2. KEY DETAILS: Specific details useful for authentic writing (sensory details, period-accurate terminology, cultural nuances)
3. COMMON MISCONCEPTIONS: What most people get wrong about this topic
4. NARRATIVE OPPORTUNITIES: How this information could enrich the story/narrative
5. FURTHER RESEARCH: Specific areas the author should verify or explore further
6. SUGGESTED SOURCES: Types of primary and secondary sources to consult
7. AUTHENTICITY NOTES: Details critical for avoiding anachronisms or inaccuracies"""

        return self.ai.generate(system, prompt, max_tokens=8192)

    def fact_check(self, content, project_type="fiction"):
        """Fact-check content for accuracy."""
        system = (
            "You are a rigorous fact-checker who reviews manuscripts for accuracy. "
            "For fiction, you verify real-world references, historical accuracy, and "
            "internal consistency. For nonfiction, you verify all factual claims. "
            "You clearly distinguish between verifiable facts and areas needing "
            "author verification."
        )
        prompt = f"""Fact-check the following {project_type} text:

TEXT:
{content}

Provide:
1. VERIFIED FACTS: Claims that appear accurate based on your knowledge
2. POTENTIAL ERRORS: Claims that may be inaccurate, with corrections
3. UNVERIFIABLE CLAIMS: Statements that need primary source verification
4. ANACHRONISMS: Any time-period inconsistencies (if applicable)
5. TECHNICAL ACCURACY: Assessment of any technical, scientific, or specialized content
6. RECOMMENDATIONS: Specific suggestions for improving accuracy

Rate overall factual confidence: HIGH / MEDIUM / LOW with explanation."""

        return self.ai.generate(system, prompt, max_tokens=8192)

    def world_building_research(self, world_details, aspects=None):
        """Research to support world-building for fiction."""
        aspects = aspects or ["geography", "culture", "technology", "politics", "economics"]
        aspects_str = ", ".join(aspects)
        system = (
            "You are a world-building consultant who draws on deep knowledge of "
            "history, anthropology, geography, political science, and technology "
            "to help authors create internally consistent and believable fictional worlds."
        )
        prompt = f"""Help develop world-building research for the following:

WORLD DETAILS:
{world_details}

ASPECTS TO DEVELOP: {aspects_str}

For each aspect, provide:
- How this element would realistically function given the world's parameters
- Historical and real-world parallels for inspiration
- Internal consistency considerations
- Telling details that would make the world feel authentic
- Potential conflicts or tensions this element creates (useful for plot)"""

        return self.ai.generate(system, prompt, max_tokens=8192)

    def character_research(self, character_details, research_needs):
        """Research to support authentic character development."""
        system = (
            "You are a character research specialist who helps authors create "
            "authentic, three-dimensional characters. You draw on psychology, "
            "sociology, cultural studies, and lived experience research to ensure "
            "characters feel real and are portrayed respectfully and accurately."
        )
        prompt = f"""Research to support character development:

CHARACTER DETAILS:
{character_details}

RESEARCH NEEDS:
{research_needs}

Provide:
1. PSYCHOLOGICAL PROFILE: Realistic psychological patterns based on the character's background
2. BEHAVIORAL DETAILS: Authentic behavioral patterns, habits, speech patterns
3. CULTURAL CONTEXT: Relevant cultural details for authentic portrayal
4. SENSITIVITY NOTES: Areas requiring particular care for respectful representation
5. TELLING DETAILS: Small, specific details that would make this character feel real
6. FURTHER READING: Recommended sources for deeper understanding"""

        return self.ai.generate(system, prompt, max_tokens=4096)

    def setting_research(self, setting_description, time_period="", focus_areas=None):
        """Research to support authentic setting descriptions."""
        focus = ", ".join(focus_areas) if focus_areas else "all sensory and factual details"
        system = (
            "You are a setting research specialist who provides the rich, specific "
            "details authors need to create immersive, authentic settings. You focus "
            "on sensory details, period accuracy, and the lived experience of a place."
        )
        prompt = f"""Research the following setting for a writing project:

SETTING: {setting_description}
TIME PERIOD: {time_period or 'Contemporary'}
FOCUS: {focus}

Provide:
1. VISUAL DETAILS: What the place looks like—architecture, landscape, light, color
2. SOUNDS: The soundscape of this place
3. SMELLS & TASTES: Olfactory and gustatory details
4. TEXTURES & TEMPERATURES: Tactile sensations
5. CULTURAL ATMOSPHERE: The feel and energy of this place, social dynamics
6. PERIOD-SPECIFIC DETAILS: Technology, fashion, language, customs of the era
7. DAILY LIFE: What ordinary life looks and feels like here
8. UNIQUE FEATURES: What makes this setting distinct and memorable"""

        return self.ai.generate(system, prompt, max_tokens=4096)

    def generate_bibliography(self, topics, citation_style="chicago"):
        """Generate a recommended bibliography for nonfiction research."""
        system = (
            "You are an academic research librarian who helps nonfiction authors "
            "build comprehensive bibliographies. You recommend authoritative, "
            "well-regarded sources and format citations properly."
        )
        topics_str = "\n".join(f"- {t}" for t in topics) if isinstance(topics, list) else topics
        prompt = f"""Generate a recommended bibliography for a nonfiction project covering:

TOPICS:
{topics_str}

CITATION STYLE: {citation_style}

Provide:
1. PRIMARY SOURCES: Essential foundational works (5-10)
2. SECONDARY SOURCES: Important analytical and interpretive works (5-10)
3. CONTEMPORARY REFERENCES: Recent works and current scholarship (5-10)
4. ACCESSIBLE SOURCES: Well-written works suitable for general readers
5. MULTIMEDIA SOURCES: Documentaries, archives, databases, interviews

Format all citations in {citation_style} style.
Note: Verify all sources independently—suggest checking library catalogs."""

        return self.ai.generate(system, prompt, max_tokens=4096)
