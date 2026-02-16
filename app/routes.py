"""Flask routes for the Manuscript Expansion Application."""

import os
import json
import datetime
from flask import Blueprint, request, jsonify, render_template, current_app, send_file

from app import db
from app.models import Project, Chapter, Scene, Character, ResearchNote, RevisionHistory
from app.services.expansion import ExpansionService
from app.services.editor import EditorService
from app.services.research import ResearchService
from app.services.manuscript import ManuscriptService

main_bp = Blueprint("main", __name__)
api_bp = Blueprint("api", __name__)

expansion = ExpansionService()
editor = EditorService()
research = ResearchService()
manuscript = ManuscriptService()


# ─── Page Routes ─────────────────────────────────────────────────────────

@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/project/<int:project_id>")
def project_view(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template("project.html", project=project)


@main_bp.route("/project/<int:project_id>/chapter/<int:chapter_id>")
def chapter_view(project_id, chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    return render_template("chapter.html", chapter=chapter, project=chapter.project)


# ─── Project API ─────────────────────────────────────────────────────────

@api_bp.route("/projects", methods=["GET"])
def list_projects():
    projects = Project.query.order_by(Project.updated_at.desc()).all()
    return jsonify([p.to_dict() for p in projects])


@api_bp.route("/projects", methods=["POST"])
def create_project():
    data = request.get_json()
    project = Project(
        title=data.get("title", "Untitled Project"),
        subtitle=data.get("subtitle", ""),
        genre=data.get("genre", ""),
        project_type=data.get("project_type", "fiction"),
        synopsis=data.get("synopsis", ""),
        target_word_count=data.get("target_word_count", 80000),
        author_name=data.get("author_name", ""),
        author_bio=data.get("author_bio", ""),
        author_email=data.get("author_email", ""),
        author_phone=data.get("author_phone", ""),
        author_address=data.get("author_address", ""),
        agent_name=data.get("agent_name", ""),
        agent_email=data.get("agent_email", ""),
        notes=data.get("notes", ""),
        themes=data.get("themes", ""),
        setting_description=data.get("setting_description", ""),
    )
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict(include_chapters=True)), 201


@api_bp.route("/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    return jsonify(project.to_dict(include_chapters=True))


@api_bp.route("/projects/<int:project_id>", methods=["PUT"])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    for field in ["title", "subtitle", "genre", "project_type", "status", "synopsis",
                   "target_word_count", "author_name", "author_bio", "author_email",
                   "author_phone", "author_address", "agent_name", "agent_email",
                   "notes", "themes", "setting_description"]:
        if field in data:
            setattr(project, field, data[field])
    db.session.commit()
    return jsonify(project.to_dict(include_chapters=True))


@api_bp.route("/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"message": "Project deleted"})


# ─── Chapter API ─────────────────────────────────────────────────────────

@api_bp.route("/projects/<int:project_id>/chapters", methods=["GET"])
def list_chapters(project_id):
    chapters = Chapter.query.filter_by(project_id=project_id).order_by(Chapter.order).all()
    return jsonify([c.to_dict() for c in chapters])


@api_bp.route("/projects/<int:project_id>/chapters", methods=["POST"])
def create_chapter(project_id):
    Project.query.get_or_404(project_id)
    data = request.get_json()
    max_order = db.session.query(db.func.max(Chapter.order)).filter_by(project_id=project_id).scalar() or 0
    chapter = Chapter(
        project_id=project_id,
        title=data.get("title", f"Chapter {max_order + 1}"),
        order=data.get("order", max_order + 1),
        summary=data.get("summary", ""),
        content=data.get("content", ""),
        notes=data.get("notes", ""),
        pov_character=data.get("pov_character", ""),
        setting=data.get("setting", ""),
        status=data.get("status", "outline"),
    )
    db.session.add(chapter)
    db.session.commit()
    return jsonify(chapter.to_dict()), 201


@api_bp.route("/chapters/<int:chapter_id>", methods=["GET"])
def get_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    return jsonify(chapter.to_dict(include_scenes=True))


@api_bp.route("/chapters/<int:chapter_id>", methods=["PUT"])
def update_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    data = request.get_json()

    # Save revision history if content changes
    if "content" in data and data["content"] != chapter.content:
        revision = RevisionHistory(
            project_id=chapter.project_id,
            chapter_id=chapter.id,
            revision_type="edit",
            description="Chapter content updated",
            content_before=chapter.content or "",
            content_after=data["content"],
        )
        db.session.add(revision)

    for field in ["title", "order", "status", "summary", "content", "notes",
                   "pov_character", "setting", "timeline_position"]:
        if field in data:
            setattr(chapter, field, data[field])
    db.session.commit()
    return jsonify(chapter.to_dict())


@api_bp.route("/chapters/<int:chapter_id>", methods=["DELETE"])
def delete_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    db.session.delete(chapter)
    db.session.commit()
    return jsonify({"message": "Chapter deleted"})


# ─── Scene API ───────────────────────────────────────────────────────────

@api_bp.route("/chapters/<int:chapter_id>/scenes", methods=["POST"])
def create_scene(chapter_id):
    Chapter.query.get_or_404(chapter_id)
    data = request.get_json()
    max_order = db.session.query(db.func.max(Scene.order)).filter_by(chapter_id=chapter_id).scalar() or 0
    scene = Scene(
        chapter_id=chapter_id,
        title=data.get("title", ""),
        order=data.get("order", max_order + 1),
        content=data.get("content", ""),
        summary=data.get("summary", ""),
        notes=data.get("notes", ""),
        scene_type=data.get("scene_type", "action"),
    )
    db.session.add(scene)
    db.session.commit()
    return jsonify(scene.to_dict()), 201


@api_bp.route("/scenes/<int:scene_id>", methods=["PUT"])
def update_scene(scene_id):
    scene = Scene.query.get_or_404(scene_id)
    data = request.get_json()
    for field in ["title", "order", "content", "summary", "notes", "scene_type"]:
        if field in data:
            setattr(scene, field, data[field])
    db.session.commit()
    return jsonify(scene.to_dict())


@api_bp.route("/scenes/<int:scene_id>", methods=["DELETE"])
def delete_scene(scene_id):
    scene = Scene.query.get_or_404(scene_id)
    db.session.delete(scene)
    db.session.commit()
    return jsonify({"message": "Scene deleted"})


# ─── Character API ───────────────────────────────────────────────────────

@api_bp.route("/projects/<int:project_id>/characters", methods=["GET"])
def list_characters(project_id):
    chars = Character.query.filter_by(project_id=project_id).all()
    return jsonify([c.to_dict() for c in chars])


@api_bp.route("/projects/<int:project_id>/characters", methods=["POST"])
def create_character(project_id):
    data = request.get_json()
    char = Character(
        project_id=project_id,
        name=data.get("name", "Unnamed Character"),
        role=data.get("role", "supporting"),
        description=data.get("description", ""),
        backstory=data.get("backstory", ""),
        motivations=data.get("motivations", ""),
        arc_description=data.get("arc_description", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(char)
    db.session.commit()
    return jsonify(char.to_dict()), 201


@api_bp.route("/characters/<int:char_id>", methods=["PUT"])
def update_character(char_id):
    char = Character.query.get_or_404(char_id)
    data = request.get_json()
    for field in ["name", "role", "description", "backstory", "motivations", "arc_description", "notes"]:
        if field in data:
            setattr(char, field, data[field])
    db.session.commit()
    return jsonify(char.to_dict())


@api_bp.route("/characters/<int:char_id>", methods=["DELETE"])
def delete_character(char_id):
    char = Character.query.get_or_404(char_id)
    db.session.delete(char)
    db.session.commit()
    return jsonify({"message": "Character deleted"})


# ─── Research API ────────────────────────────────────────────────────────

@api_bp.route("/projects/<int:project_id>/research", methods=["GET"])
def list_research(project_id):
    notes = ResearchNote.query.filter_by(project_id=project_id).order_by(ResearchNote.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notes])


@api_bp.route("/projects/<int:project_id>/research", methods=["POST"])
def create_research_note(project_id):
    data = request.get_json()
    note = ResearchNote(
        project_id=project_id,
        title=data.get("title", "Research Note"),
        category=data.get("category", "general"),
        content=data.get("content", ""),
        source_url=data.get("source_url", ""),
        source_citation=data.get("source_citation", ""),
        tags=data.get("tags", ""),
    )
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@api_bp.route("/research/<int:note_id>", methods=["PUT"])
def update_research_note(note_id):
    note = ResearchNote.query.get_or_404(note_id)
    data = request.get_json()
    for field in ["title", "category", "content", "source_url", "source_citation", "tags"]:
        if field in data:
            setattr(note, field, data[field])
    db.session.commit()
    return jsonify(note.to_dict())


@api_bp.route("/research/<int:note_id>", methods=["DELETE"])
def delete_research_note(note_id):
    note = ResearchNote.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return jsonify({"message": "Research note deleted"})


# ─── AI-Powered Endpoints ───────────────────────────────────────────────

@api_bp.route("/ai/expand-idea", methods=["POST"])
def expand_idea():
    """Expand a raw idea into a full project outline."""
    data = request.get_json()
    result = expansion.expand_idea_to_outline(
        idea=data["idea"],
        project_type=data.get("project_type", "fiction"),
        genre=data.get("genre", ""),
        num_chapters=data.get("num_chapters", 12),
    )
    return jsonify({"result": result})


@api_bp.route("/ai/develop-concept", methods=["POST"])
def develop_concept():
    """Develop a rough concept into a fleshed-out idea."""
    data = request.get_json()
    result = expansion.develop_concept(
        raw_concept=data["concept"],
        project_type=data.get("project_type", "fiction"),
    )
    return jsonify({"result": result})


@api_bp.route("/ai/expand-chapter", methods=["POST"])
def expand_chapter():
    """Expand a chapter summary into full prose."""
    data = request.get_json()
    chapter_id = data.get("chapter_id")
    project_context = data.get("project_context", "")

    if chapter_id:
        chapter = Chapter.query.get_or_404(chapter_id)
        project = chapter.project
        project_context = project_context or f"Title: {project.title}\nGenre: {project.genre}\nSynopsis: {project.synopsis}"
        summary = data.get("summary", chapter.summary)
        chapter_num = chapter.order
    else:
        summary = data["summary"]
        chapter_num = data.get("chapter_num", 1)

    result = expansion.expand_outline_to_chapter(
        chapter_summary=summary,
        project_context=project_context,
        chapter_num=chapter_num,
        style_notes=data.get("style_notes", ""),
        target_words=data.get("target_words", 4000),
    )

    # Save to chapter if chapter_id provided
    if chapter_id:
        revision = RevisionHistory(
            project_id=chapter.project_id,
            chapter_id=chapter.id,
            revision_type="expand",
            description="Chapter expanded from outline via AI",
            content_before=chapter.content or "",
            content_after=result,
        )
        db.session.add(revision)
        chapter.content = result
        chapter.status = "draft"
        db.session.commit()

    return jsonify({"result": result})


@api_bp.route("/ai/expand-scene", methods=["POST"])
def ai_expand_scene():
    """Expand a scene brief into full prose."""
    data = request.get_json()
    result = expansion.expand_scene(
        scene_brief=data["scene_brief"],
        chapter_context=data.get("chapter_context", ""),
        scene_type=data.get("scene_type", "action"),
    )
    return jsonify({"result": result})


@api_bp.route("/ai/developmental-edit", methods=["POST"])
def developmental_edit():
    """Get a developmental edit of content."""
    data = request.get_json()
    result = editor.developmental_edit(
        content=data["content"],
        project_context=data.get("project_context", ""),
    )
    return jsonify({"result": result})


@api_bp.route("/ai/line-edit", methods=["POST"])
def line_edit():
    """Get a line edit of content."""
    data = request.get_json()
    result = editor.line_edit(content=data["content"])
    return jsonify({"result": result})


@api_bp.route("/ai/copy-edit", methods=["POST"])
def copy_edit():
    """Get a copy edit of content."""
    data = request.get_json()
    result = editor.copy_edit(content=data["content"])
    return jsonify({"result": result})


@api_bp.route("/ai/rewrite", methods=["POST"])
def rewrite():
    """Rewrite a passage according to instructions."""
    data = request.get_json()
    result = editor.rewrite_passage(
        content=data["content"],
        instructions=data["instructions"],
        preserve_voice=data.get("preserve_voice", True),
    )
    return jsonify({"result": result})


@api_bp.route("/ai/improve", methods=["POST"])
def improve():
    """Improve prose quality."""
    data = request.get_json()
    result = editor.improve_prose(
        content=data["content"],
        focus_areas=data.get("focus_areas"),
    )
    return jsonify({"result": result})


@api_bp.route("/ai/strengthen-dialogue", methods=["POST"])
def strengthen_dialogue():
    """Improve dialogue in a passage."""
    data = request.get_json()
    result = editor.strengthen_dialogue(content=data["content"])
    return jsonify({"result": result})


@api_bp.route("/ai/adjust-tone", methods=["POST"])
def adjust_tone():
    """Adjust the tone of a passage."""
    data = request.get_json()
    result = editor.adjust_tone(
        content=data["content"],
        target_tone=data["target_tone"],
        current_tone=data.get("current_tone", ""),
    )
    return jsonify({"result": result})


@api_bp.route("/ai/continuity-check", methods=["POST"])
def continuity_check():
    """Check continuity across chapters."""
    data = request.get_json()
    project_id = data.get("project_id")
    if project_id:
        project = Project.query.get_or_404(project_id)
        chapters_content = ""
        for ch in sorted(project.chapters, key=lambda c: c.order):
            chapters_content += f"\n--- Chapter {ch.order}: {ch.title} ---\n{ch.content or ch.summary}\n"
        project_context = f"Title: {project.title}\nGenre: {project.genre}"
    else:
        chapters_content = data["content"]
        project_context = data.get("project_context", "")

    result = editor.check_continuity(chapters_content, project_context)
    return jsonify({"result": result})


@api_bp.route("/ai/research", methods=["POST"])
def ai_research():
    """Research a topic for a writing project."""
    data = request.get_json()
    result = research.research_topic(
        topic=data["topic"],
        project_context=data.get("project_context", ""),
        depth=data.get("depth", "standard"),
    )
    return jsonify({"result": result})


@api_bp.route("/ai/fact-check", methods=["POST"])
def fact_check():
    """Fact-check content."""
    data = request.get_json()
    result = research.fact_check(
        content=data["content"],
        project_type=data.get("project_type", "fiction"),
    )
    return jsonify({"result": result})


@api_bp.route("/ai/world-building", methods=["POST"])
def world_building():
    """Research for world-building."""
    data = request.get_json()
    result = research.world_building_research(
        world_details=data["world_details"],
        aspects=data.get("aspects"),
    )
    return jsonify({"result": result})


@api_bp.route("/ai/character-research", methods=["POST"])
def character_research():
    """Research to support character development."""
    data = request.get_json()
    result = research.character_research(
        character_details=data["character_details"],
        research_needs=data["research_needs"],
    )
    return jsonify({"result": result})


@api_bp.route("/ai/setting-research", methods=["POST"])
def setting_research():
    """Research a setting for authentic descriptions."""
    data = request.get_json()
    result = research.setting_research(
        setting_description=data["setting"],
        time_period=data.get("time_period", ""),
        focus_areas=data.get("focus_areas"),
    )
    return jsonify({"result": result})


# ─── Manuscript Export Endpoints ─────────────────────────────────────────

@api_bp.route("/projects/<int:project_id>/export/manuscript", methods=["POST"])
def export_manuscript(project_id):
    """Export the full manuscript as a formatted DOCX."""
    project = Project.query.get_or_404(project_id)
    output_dir = os.path.join(current_app.config["MANUSCRIPTS_DIR"], str(project_id))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{ManuscriptService._safe_filename(project.title)}_manuscript.docx")
    manuscript.generate_full_manuscript_docx(project, output_path)
    return send_file(output_path, as_attachment=True)


@api_bp.route("/projects/<int:project_id>/export/query-letter", methods=["POST"])
def export_query_letter(project_id):
    """Generate and return a query letter."""
    project = Project.query.get_or_404(project_id)
    result = manuscript.generate_query_letter(project)
    return jsonify({"result": result})


@api_bp.route("/projects/<int:project_id>/export/synopsis", methods=["POST"])
def export_synopsis(project_id):
    """Generate a synopsis."""
    project = Project.query.get_or_404(project_id)
    data = request.get_json() or {}
    result = manuscript.generate_synopsis(project, length=data.get("length", "standard"))
    return jsonify({"result": result})


@api_bp.route("/projects/<int:project_id>/export/submission-packet", methods=["POST"])
def export_submission_packet(project_id):
    """Generate a complete submission packet."""
    project = Project.query.get_or_404(project_id)
    output_dir = os.path.join(current_app.config["MANUSCRIPTS_DIR"], str(project_id), "submission_packet")
    files = manuscript.generate_submission_packet(project, output_dir)
    return jsonify({
        "message": "Submission packet generated",
        "files": [{"name": name, "path": path} for name, path in files],
    })


@api_bp.route("/projects/<int:project_id>/export/download/<path:filename>", methods=["GET"])
def download_file(project_id, filename):
    """Download a generated file."""
    output_dir = os.path.join(current_app.config["MANUSCRIPTS_DIR"], str(project_id))
    file_path = os.path.join(output_dir, filename)
    if not os.path.isfile(file_path):
        return jsonify({"error": "File not found"}), 404
    return send_file(file_path, as_attachment=True)


# ─── Revision History ───────────────────────────────────────────────────

@api_bp.route("/projects/<int:project_id>/revisions", methods=["GET"])
def list_revisions(project_id):
    revisions = RevisionHistory.query.filter_by(project_id=project_id)\
        .order_by(RevisionHistory.created_at.desc()).limit(50).all()
    return jsonify([r.to_dict() for r in revisions])
