"""Flask routes for the Notion AI Agent.

Provides API endpoints for:
- Processing Fireflies.ai meeting summaries
- Processing Obsidian monthly exports
- Scanning the Fireflies inbox
- Managing client records
- Viewing agent logs and dashboard
"""

import hmac
import hashlib
import json
from flask import Blueprint, request, jsonify, render_template, current_app

from app import db
from app.models import ClientRecord, AgentLog
from app.services.notion_agent.agent import NotionAgent
from app.services.notion_agent.fireflies_processor import FirefliesProcessor
from app.services.notion_agent.obsidian_processor import ObsidianProcessor

agent_bp = Blueprint("agent", __name__)
notion_agent = NotionAgent()


def _verify_webhook_secret():
    """Verify the webhook secret if configured."""
    secret = current_app.config.get("NOTION_AGENT_WEBHOOK_SECRET", "")
    if not secret:
        return True  # No secret configured, allow all
    provided = request.headers.get("X-Webhook-Secret", "")
    return hmac.compare_digest(secret, provided)


# ─── Agent Dashboard ────────────────────────────────────────────────────

@agent_bp.route("/")
def agent_dashboard():
    """Render the Notion AI Agent dashboard."""
    return render_template("agent_dashboard.html")


# ─── Fireflies Processing ──────────────────────────────────────────────

@agent_bp.route("/api/fireflies/process", methods=["POST"])
def process_fireflies_report():
    """Process a single Fireflies.ai meeting summary report.

    Expects JSON body:
    {
        "report": "Full text of the Fireflies.ai meeting summary"
    }

    The agent will:
    1. Parse the report and identify the client
    2. Find or create the client's Notion workspace
    3. Create a meeting summary page
    4. Extract tasks and add them to the client's task database
    """
    if not _verify_webhook_secret():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or not data.get("report"):
        return jsonify({"error": "Missing 'report' field in request body"}), 400

    result = notion_agent.process_fireflies_report(data["report"])
    status_code = 200 if result["status"] != "failed" else 500
    return jsonify(result), status_code


@agent_bp.route("/api/fireflies/scan-inbox", methods=["POST"])
def scan_fireflies_inbox():
    """Scan the Notion Fireflies inbox for unprocessed reports.

    Requires NOTION_FIREFLIES_INBOX_DB_ID to be configured.
    Processes all unprocessed reports and marks them as done.
    """
    if not _verify_webhook_secret():
        return jsonify({"error": "Unauthorized"}), 401

    result = notion_agent.scan_fireflies_inbox()
    status_code = 200 if result["status"] != "failed" else 500
    return jsonify(result), status_code


@agent_bp.route("/api/fireflies/parse-only", methods=["POST"])
def parse_fireflies_only():
    """Parse a Fireflies report without creating anything in Notion.

    Useful for previewing what the agent will extract before committing.

    Expects JSON body:
    {
        "report": "Full text of the Fireflies.ai meeting summary"
    }
    """
    data = request.get_json()
    if not data or not data.get("report"):
        return jsonify({"error": "Missing 'report' field"}), 400

    processor = FirefliesProcessor()
    parsed = processor.parse_fireflies_report(data["report"])

    # Also get tasks separately for a detailed view
    tasks = processor.extract_tasks(
        data["report"],
        attendees=parsed.get("attendees", []),
    )

    # Identify client
    known_clients = [c.name for c in ClientRecord.query.all()]
    client_info = processor.identify_client(data["report"], known_clients=known_clients)

    return jsonify({
        "parsed_report": parsed,
        "extracted_tasks": tasks,
        "client_identification": client_info,
    })


# ─── Obsidian Processing ───────────────────────────────────────────────

@agent_bp.route("/api/obsidian/process", methods=["POST"])
def process_obsidian_export():
    """Process an Obsidian monthly export to create project pages in Notion.

    Expects JSON body:
    {
        "markdown": "Raw markdown content from Obsidian export"
    }

    The agent will:
    1. Parse the markdown to extract project ideas
    2. Generate full project plans for each idea
    3. Create project pages in Notion with tasks, milestones, and timelines
    """
    if not _verify_webhook_secret():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or not data.get("markdown"):
        return jsonify({"error": "Missing 'markdown' field in request body"}), 400

    result = notion_agent.process_obsidian_export(data["markdown"])
    status_code = 200 if result["status"] != "failed" else 500
    return jsonify(result), status_code


@agent_bp.route("/api/obsidian/parse-only", methods=["POST"])
def parse_obsidian_only():
    """Parse Obsidian markdown and generate plans without creating Notion pages.

    Useful for previewing what the agent will create.

    Expects JSON body:
    {
        "markdown": "Raw markdown content from Obsidian export"
    }
    """
    data = request.get_json()
    if not data or not data.get("markdown"):
        return jsonify({"error": "Missing 'markdown' field"}), 400

    processor = ObsidianProcessor()
    plans = processor.batch_process_ideas(data["markdown"])
    return jsonify({"projects": plans, "count": len(plans)})


# ─── Client Management ─────────────────────────────────────────────────

@agent_bp.route("/api/clients", methods=["GET"])
def list_clients():
    """List all known clients."""
    clients = ClientRecord.query.order_by(ClientRecord.name).all()
    return jsonify([c.to_dict() for c in clients])


@agent_bp.route("/api/clients", methods=["POST"])
def create_client():
    """Manually create a client record.

    Expects JSON body:
    {
        "name": "Client Name",
        "notion_page_id": "(optional) existing Notion page ID",
        "notion_database_id": "(optional) existing Notion database ID",
        "notes": "(optional) notes about this client"
    }
    """
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Missing 'name' field"}), 400

    existing = ClientRecord.query.filter(
        db.func.lower(ClientRecord.name) == data["name"].lower()
    ).first()
    if existing:
        return jsonify({"error": f"Client '{data['name']}' already exists", "client": existing.to_dict()}), 409

    client = ClientRecord(
        name=data["name"],
        notion_page_id=data.get("notion_page_id", ""),
        notion_database_id=data.get("notion_database_id", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(client)
    db.session.commit()
    return jsonify(client.to_dict()), 201


@agent_bp.route("/api/clients/<int:client_id>", methods=["GET"])
def get_client(client_id):
    """Get a client record with its recent logs."""
    client = ClientRecord.query.get_or_404(client_id)
    data = client.to_dict()
    data["recent_logs"] = [log.to_dict() for log in client.agent_logs[:20]]
    return jsonify(data)


@agent_bp.route("/api/clients/<int:client_id>", methods=["PUT"])
def update_client(client_id):
    """Update a client record."""
    client = ClientRecord.query.get_or_404(client_id)
    data = request.get_json()
    for field in ["name", "notion_page_id", "notion_database_id", "notes"]:
        if field in data:
            setattr(client, field, data[field])
    db.session.commit()
    return jsonify(client.to_dict())


@agent_bp.route("/api/clients/<int:client_id>", methods=["DELETE"])
def delete_client(client_id):
    """Delete a client record."""
    client = ClientRecord.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    return jsonify({"message": f"Client '{client.name}' deleted"})


# ─── Agent Logs ─────────────────────────────────────────────────────────

@agent_bp.route("/api/logs", methods=["GET"])
def list_logs():
    """List recent agent activity logs.

    Query params:
    - limit: Number of logs to return (default 50, max 200)
    - event_type: Filter by event type
    """
    limit = min(int(request.args.get("limit", 50)), 200)
    event_type = request.args.get("event_type")

    query = AgentLog.query.order_by(AgentLog.created_at.desc())
    if event_type:
        query = query.filter_by(event_type=event_type)

    logs = query.limit(limit).all()
    return jsonify([log.to_dict() for log in logs])


# ─── Agent Status ───────────────────────────────────────────────────────

@agent_bp.route("/api/status", methods=["GET"])
def agent_status():
    """Get the current status and configuration of the agent."""
    notion_configured = bool(current_app.config.get("NOTION_TOKEN"))
    anthropic_configured = bool(current_app.config.get("ANTHROPIC_API_KEY"))
    inbox_configured = bool(current_app.config.get("NOTION_FIREFLIES_INBOX_DB_ID"))
    projects_configured = bool(current_app.config.get("NOTION_PROJECTS_PAGE_ID"))

    client_count = ClientRecord.query.count()
    log_count = AgentLog.query.count()
    recent_log = AgentLog.query.order_by(AgentLog.created_at.desc()).first()

    return jsonify({
        "configured": {
            "notion_api": notion_configured,
            "anthropic_api": anthropic_configured,
            "fireflies_inbox": inbox_configured,
            "projects_page": projects_configured,
        },
        "ready": notion_configured and anthropic_configured,
        "stats": {
            "known_clients": client_count,
            "total_events_logged": log_count,
            "last_activity": recent_log.created_at.isoformat() if recent_log else None,
        },
    })
