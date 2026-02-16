import datetime
import json
from app import db


class Project(db.Model):
    """A full narrative project (book, novella, collection, etc.)."""
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    subtitle = db.Column(db.String(500), default="")
    genre = db.Column(db.String(200), default="")
    project_type = db.Column(db.String(50), default="fiction")  # fiction, nonfiction
    status = db.Column(db.String(50), default="draft")  # draft, revision, final, submitted
    synopsis = db.Column(db.Text, default="")
    target_word_count = db.Column(db.Integer, default=80000)
    author_name = db.Column(db.String(300), default="")
    author_bio = db.Column(db.Text, default="")
    author_email = db.Column(db.String(300), default="")
    author_phone = db.Column(db.String(50), default="")
    author_address = db.Column(db.Text, default="")
    agent_name = db.Column(db.String(300), default="")
    agent_email = db.Column(db.String(300), default="")
    notes = db.Column(db.Text, default="")
    themes = db.Column(db.Text, default="")  # JSON array of themes
    setting_description = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow)

    chapters = db.relationship("Chapter", backref="project", lazy=True,
                               order_by="Chapter.order", cascade="all, delete-orphan")
    characters = db.relationship("Character", backref="project", lazy=True,
                                 cascade="all, delete-orphan")
    research_notes = db.relationship("ResearchNote", backref="project", lazy=True,
                                     cascade="all, delete-orphan")
    revision_history = db.relationship("RevisionHistory", backref="project", lazy=True,
                                       order_by="RevisionHistory.created_at.desc()",
                                       cascade="all, delete-orphan")

    @property
    def word_count(self):
        total = 0
        for chapter in self.chapters:
            total += chapter.word_count
        return total

    @property
    def progress_percent(self):
        if self.target_word_count == 0:
            return 0
        return min(100, round((self.word_count / self.target_word_count) * 100, 1))

    def to_dict(self, include_chapters=False):
        data = {
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "genre": self.genre,
            "project_type": self.project_type,
            "status": self.status,
            "synopsis": self.synopsis,
            "target_word_count": self.target_word_count,
            "word_count": self.word_count,
            "progress_percent": self.progress_percent,
            "author_name": self.author_name,
            "author_bio": self.author_bio,
            "author_email": self.author_email,
            "notes": self.notes,
            "themes": self.themes,
            "chapter_count": len(self.chapters),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_chapters:
            data["chapters"] = [c.to_dict() for c in self.chapters]
        return data


class Chapter(db.Model):
    """A chapter within a project."""
    __tablename__ = "chapters"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    order = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default="outline")  # outline, draft, revision, final
    summary = db.Column(db.Text, default="")
    content = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")
    pov_character = db.Column(db.String(200), default="")
    setting = db.Column(db.String(500), default="")
    timeline_position = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow)

    scenes = db.relationship("Scene", backref="chapter", lazy=True,
                             order_by="Scene.order", cascade="all, delete-orphan")

    @property
    def word_count(self):
        if self.content:
            return len(self.content.split())
        return sum(s.word_count for s in self.scenes)

    def to_dict(self, include_scenes=False):
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "order": self.order,
            "status": self.status,
            "summary": self.summary,
            "content": self.content,
            "notes": self.notes,
            "pov_character": self.pov_character,
            "setting": self.setting,
            "word_count": self.word_count,
            "scene_count": len(self.scenes),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_scenes:
            data["scenes"] = [s.to_dict() for s in self.scenes]
        return data


class Scene(db.Model):
    """A scene within a chapter."""
    __tablename__ = "scenes"

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey("chapters.id"), nullable=False)
    title = db.Column(db.String(500), default="")
    order = db.Column(db.Integer, default=0)
    content = db.Column(db.Text, default="")
    summary = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")
    scene_type = db.Column(db.String(50), default="action")  # action, reaction, exposition, dialogue
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow)

    @property
    def word_count(self):
        return len(self.content.split()) if self.content else 0

    def to_dict(self):
        return {
            "id": self.id,
            "chapter_id": self.chapter_id,
            "title": self.title,
            "order": self.order,
            "content": self.content,
            "summary": self.summary,
            "notes": self.notes,
            "scene_type": self.scene_type,
            "word_count": self.word_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Character(db.Model):
    """A character profile within a project."""
    __tablename__ = "characters"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    name = db.Column(db.String(300), nullable=False)
    role = db.Column(db.String(100), default="supporting")  # protagonist, antagonist, supporting, minor
    description = db.Column(db.Text, default="")
    backstory = db.Column(db.Text, default="")
    motivations = db.Column(db.Text, default="")
    arc_description = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "backstory": self.backstory,
            "motivations": self.motivations,
            "arc_description": self.arc_description,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ResearchNote(db.Model):
    """Research notes associated with a project."""
    __tablename__ = "research_notes"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(200), default="general")
    content = db.Column(db.Text, default="")
    source_url = db.Column(db.String(2000), default="")
    source_citation = db.Column(db.Text, default="")
    tags = db.Column(db.Text, default="")  # JSON array
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "category": self.category,
            "content": self.content,
            "source_url": self.source_url,
            "source_citation": self.source_citation,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RevisionHistory(db.Model):
    """Track revision history for content."""
    __tablename__ = "revision_history"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey("chapters.id"), nullable=True)
    revision_type = db.Column(db.String(50), default="edit")  # edit, rewrite, expand, correct, improve
    description = db.Column(db.Text, default="")
    content_before = db.Column(db.Text, default="")
    content_after = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "chapter_id": self.chapter_id,
            "revision_type": self.revision_type,
            "description": self.description,
            "content_before": self.content_before[:500] + "..." if len(self.content_before) > 500 else self.content_before,
            "content_after": self.content_after[:500] + "..." if len(self.content_after) > 500 else self.content_after,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ─── Notion AI Agent Models ─────────────────────────────────────────────


class ClientRecord(db.Model):
    """Tracks known clients and their Notion workspace IDs."""
    __tablename__ = "client_records"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False, unique=True)
    notion_page_id = db.Column(db.String(200), default="")
    notion_database_id = db.Column(db.String(200), default="")
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow)

    agent_logs = db.relationship("AgentLog", backref="client", lazy=True,
                                 order_by="AgentLog.created_at.desc()")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "notion_page_id": self.notion_page_id,
            "notion_database_id": self.notion_database_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AgentLog(db.Model):
    """Audit log for all Notion AI Agent actions."""
    __tablename__ = "agent_logs"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(100), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("client_records.id"), nullable=True)
    data = db.Column(db.Text, default="")  # JSON payload
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "event_type": self.event_type,
            "client_id": self.client_id,
            "data": self.data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
