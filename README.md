# Prose Engine

A full-featured manuscript expansion application that transforms short ideas, concepts, and drafts into researched, narratively complex, publication-ready prose. Built with Flask and powered by Claude AI.

## Features

### Idea-to-Manuscript Pipeline
- **Concept Development** — Transform rough ideas into fleshed-out story premises with themes, conflicts, and narrative approach
- **Outline Generation** — Expand concepts into detailed chapter-by-chapter outlines with character profiles and narrative arcs
- **Chapter Expansion** — Convert chapter outlines into full, publication-quality prose with scenes, dialogue, and sensory detail
- **Scene Writing** — Generate individual scenes from brief descriptions

### Project Management
- Organize work into **Projects** containing **Chapters**, **Scenes**, and **Characters**
- Track word count progress against targets
- Manage project status (draft, revision, final, submitted)
- Full revision history with before/after tracking

### Professional Editing Suite
- **Developmental Editing** — Structural and narrative feedback on plot, character, pacing, and theme
- **Line Editing** — Sentence-level prose improvement: rhythm, word choice, imagery
- **Copy Editing** — Grammar, punctuation, and style consistency (Chicago Manual of Style)
- **Rewriting** — Rewrite passages with specific instructions while preserving voice
- **Prose Improvement** — Targeted enhancement of clarity, imagery, rhythm, and impact
- **Dialogue Strengthening** — Make character voices distinct, add subtext, improve naturalism
- **Tone Adjustment** — Shift emotional register while preserving content
- **Continuity Checking** — Catch inconsistencies across chapters

### Research Support
- **Topic Research** — Detailed research organized for writers (brief, standard, or deep)
- **Fact-Checking** — Verify accuracy of fiction and nonfiction content
- **World-Building Research** — Geography, culture, technology, politics, economics
- **Character Research** — Psychology, behavior, cultural context for authentic portrayal
- **Setting Research** — Sensory details, period accuracy, cultural atmosphere
- **Bibliography Generation** — Formatted source recommendations for nonfiction

### Manuscript Export & Submission
- **Formatted Manuscript (DOCX)** — Industry-standard formatting: Times New Roman 12pt, double-spaced, 1-inch margins, proper title page
- **Query Letter** — Professionally crafted query letters with hook, description, comps, and bio
- **Synopsis** — Short, standard, or detailed synopses in present tense
- **Full Submission Packet** — Complete package including:
  - Formatted manuscript
  - Query letter
  - Short and standard synopses
  - Author biography
  - Chapter-by-chapter outline
  - Sample chapters (first three)

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url>
cd Claude-Agentic-Prose
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key:
# ANTHROPIC_API_KEY=your-key-here
```

### 3. Run

```bash
python run.py
```

Open http://localhost:5000 in your browser.

### Production Deployment

```bash
gunicorn run:app --bind 0.0.0.0:8000 --workers 4
```

## Architecture

```
Claude-Agentic-Prose/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # Database models (Project, Chapter, Scene, etc.)
│   ├── routes.py            # API and page routes
│   ├── services/
│   │   ├── ai_client.py     # Claude API wrapper
│   │   ├── expansion.py     # Idea → outline → chapter expansion
│   │   ├── editor.py        # Editing, rewriting, improvement
│   │   ├── research.py      # Research, fact-checking, world-building
│   │   └── manuscript.py    # DOCX export, query letters, submission packets
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS and JavaScript
├── manuscripts/             # Generated manuscript files
├── config.py                # Application configuration
├── run.py                   # Entry point
└── requirements.txt         # Python dependencies
```

## API Reference

### Projects
- `GET /api/projects` — List all projects
- `POST /api/projects` — Create a project
- `GET /api/projects/:id` — Get project with chapters
- `PUT /api/projects/:id` — Update project
- `DELETE /api/projects/:id` — Delete project

### Chapters
- `GET /api/projects/:id/chapters` — List chapters
- `POST /api/projects/:id/chapters` — Add a chapter
- `GET /api/chapters/:id` — Get chapter with scenes
- `PUT /api/chapters/:id` — Update chapter
- `DELETE /api/chapters/:id` — Delete chapter

### AI Tools
- `POST /api/ai/expand-idea` — Generate full outline from an idea
- `POST /api/ai/develop-concept` — Develop a rough concept
- `POST /api/ai/expand-chapter` — Write a chapter from its outline
- `POST /api/ai/expand-scene` — Write a scene from a brief
- `POST /api/ai/developmental-edit` — Get developmental feedback
- `POST /api/ai/line-edit` — Get line-level editing
- `POST /api/ai/copy-edit` — Get copy editing
- `POST /api/ai/rewrite` — Rewrite with instructions
- `POST /api/ai/improve` — Improve prose quality
- `POST /api/ai/strengthen-dialogue` — Improve dialogue
- `POST /api/ai/adjust-tone` — Change emotional tone
- `POST /api/ai/continuity-check` — Check cross-chapter consistency
- `POST /api/ai/research` — Research a topic
- `POST /api/ai/fact-check` — Fact-check content
- `POST /api/ai/world-building` — World-building research
- `POST /api/ai/character-research` — Character development research
- `POST /api/ai/setting-research` — Setting research

### Export
- `POST /api/projects/:id/export/manuscript` — Download formatted DOCX
- `POST /api/projects/:id/export/query-letter` — Generate query letter
- `POST /api/projects/:id/export/synopsis` — Generate synopsis
- `POST /api/projects/:id/export/submission-packet` — Generate full packet
