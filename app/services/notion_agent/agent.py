"""Main Notion AI Agent orchestrator.

Coordinates Fireflies report processing, client identification,
Notion workspace management, and Obsidian project ingestion.
"""

import json
import datetime
from flask import current_app

from app import db
from app.services.notion_agent.notion_client import NotionService
from app.services.notion_agent.fireflies_processor import FirefliesProcessor
from app.services.notion_agent.obsidian_processor import ObsidianProcessor


class NotionAgent:
    """Orchestrates the full Notion AI Agent pipeline.

    Capabilities:
    1. Process Fireflies.ai meeting summaries:
       - Identify the client from the report
       - Find or create the client's Notion database/page
       - Store the meeting summary under the client page
       - Extract tasks and assign them in the client task database

    2. Process Obsidian monthly exports:
       - Parse project ideas from markdown
       - Generate project plans with tasks, milestones, timelines
       - Create project pages in Notion
    """

    def __init__(self, notion_service=None, fireflies_processor=None,
                 obsidian_processor=None):
        self.notion = notion_service or NotionService()
        self.fireflies = fireflies_processor or FirefliesProcessor()
        self.obsidian = obsidian_processor or ObsidianProcessor()

    # ─── Fireflies Pipeline ─────────────────────────────────────────────

    def process_fireflies_report(self, raw_report):
        """Full pipeline for processing a Fireflies.ai meeting summary.

        Steps:
        1. Parse the report using AI to extract structured data
        2. Identify the client
        3. Find or create the client's Notion workspace (page + database)
        4. Create a meeting summary page under the client
        5. Extract and create tasks in the client's database
        6. Log the processing result

        Args:
            raw_report: Raw text of the Fireflies.ai meeting summary.

        Returns:
            Dict with processing results and created resources.
        """
        from app.models import ClientRecord, AgentLog

        result = {
            "status": "processing",
            "steps": [],
            "errors": [],
        }

        # Step 1: Parse the report
        try:
            parsed = self.fireflies.parse_fireflies_report(raw_report)
            if parsed.get("error"):
                result["errors"].append(f"Report parsing failed: {parsed['error']}")
                result["status"] = "failed"
                self._log_event("fireflies_parse_error", result)
                return result
            result["steps"].append("Parsed Fireflies report")
            result["parsed_report"] = parsed
        except Exception as e:
            result["errors"].append(f"Report parsing exception: {str(e)}")
            result["status"] = "failed"
            self._log_event("fireflies_parse_error", result)
            return result

        # Step 2: Identify the client
        try:
            known_clients = self._get_known_clients()
            client_info = self.fireflies.identify_client(
                raw_report, known_clients=known_clients
            )
            client_name = client_info.get("client_name", parsed.get("client_name", "Unknown"))
            is_new = client_info.get("is_new_client", True)
            result["steps"].append(f"Identified client: {client_name} (new={is_new})")
            result["client_name"] = client_name
            result["is_new_client"] = is_new
        except Exception as e:
            # Fall back to parsed client name
            client_name = parsed.get("client_name", "Unknown")
            is_new = True
            result["steps"].append(f"Client identification fallback: {client_name}")

        # Step 3: Find or create client workspace
        try:
            client_record = self._ensure_client_workspace(client_name, is_new)
            result["steps"].append(
                f"Client workspace ready: page={client_record.notion_page_id}, "
                f"db={client_record.notion_database_id}"
            )
            result["client_page_id"] = client_record.notion_page_id
            result["client_database_id"] = client_record.notion_database_id
        except Exception as e:
            result["errors"].append(f"Workspace creation failed: {str(e)}")
            result["status"] = "failed"
            self._log_event("workspace_error", result)
            return result

        # Step 4: Create meeting summary page
        try:
            meeting_page = self.notion.create_meeting_summary_page(
                parent_page_id=client_record.notion_page_id,
                meeting_data=parsed,
            )
            meeting_page_id = meeting_page["id"]
            result["steps"].append(f"Created meeting summary page: {meeting_page_id}")
            result["meeting_page_id"] = meeting_page_id
        except Exception as e:
            result["errors"].append(f"Meeting page creation failed: {str(e)}")
            # Continue to try task creation even if page fails

        # Step 5: Extract and create tasks
        try:
            tasks = self.fireflies.extract_tasks(
                raw_report, attendees=parsed.get("attendees", [])
            )
            # Also include action items from parsed report
            action_items = parsed.get("action_items", [])
            all_tasks = self._merge_tasks(tasks, action_items)

            created_tasks = []
            meeting_title = parsed.get("title", "Meeting")
            meeting_date = parsed.get("date", "")

            for task in all_tasks:
                try:
                    task_data = {
                        "name": task.get("name", task.get("task", "Untitled Task")),
                        "assignee": task.get("assignee", "Unassigned"),
                        "due_date": task.get("due_date", ""),
                        "priority": task.get("priority", "Medium"),
                        "category": task.get("category", "Task"),
                        "meeting_date": meeting_date,
                        "source": meeting_title,
                        "status": "Not Started",
                    }
                    notion_task = self.notion.create_task_in_database(
                        database_id=client_record.notion_database_id,
                        task_data=task_data,
                    )
                    created_tasks.append(task_data["name"])
                except Exception as task_err:
                    result["errors"].append(
                        f"Task creation failed for '{task.get('name', '?')}': {str(task_err)}"
                    )

            result["steps"].append(f"Created {len(created_tasks)} tasks in database")
            result["created_tasks"] = created_tasks
            result["task_count"] = len(created_tasks)
        except Exception as e:
            result["errors"].append(f"Task extraction/creation failed: {str(e)}")

        # Finalize
        result["status"] = "completed" if not result["errors"] else "completed_with_errors"
        self._log_event("fireflies_processed", result)

        return result

    # ─── Obsidian Pipeline ──────────────────────────────────────────────

    def process_obsidian_export(self, markdown_content):
        """Full pipeline for processing an Obsidian monthly export.

        Steps:
        1. Parse the markdown to extract project ideas
        2. Generate project plans for each idea
        3. Create project pages in Notion

        Args:
            markdown_content: Raw markdown from Obsidian export.

        Returns:
            Dict with processing results and created projects.
        """
        result = {
            "status": "processing",
            "steps": [],
            "errors": [],
            "projects": [],
        }

        # Step 1: Parse ideas
        try:
            ideas = self.obsidian.parse_obsidian_export(markdown_content)
            result["steps"].append(f"Parsed {len(ideas)} project ideas from Obsidian")
        except Exception as e:
            result["errors"].append(f"Obsidian parsing failed: {str(e)}")
            result["status"] = "failed"
            self._log_event("obsidian_parse_error", result)
            return result

        if not ideas:
            result["status"] = "completed"
            result["steps"].append("No project ideas found in export")
            return result

        # Step 2 & 3: Generate plans and create pages
        projects_page_id = current_app.config.get(
            "NOTION_PROJECTS_PAGE_ID",
            current_app.config.get("NOTION_PARENT_PAGE_ID", ""),
        )

        if not projects_page_id:
            result["errors"].append("NOTION_PROJECTS_PAGE_ID not configured")
            result["status"] = "failed"
            return result

        for idea in ideas:
            try:
                # Generate project plan
                plan = self.obsidian.generate_project_plan(idea)
                if plan.get("error"):
                    result["errors"].append(
                        f"Plan generation failed for '{idea.get('title', '?')}': {plan['error']}"
                    )
                    continue

                result["steps"].append(f"Generated plan for: {plan.get('title', idea.get('title'))}")

                # Create Notion project page
                project_page = self.notion.create_project_page(
                    parent_page_id=projects_page_id,
                    project_data=plan,
                )

                project_info = {
                    "title": plan.get("title", idea.get("title")),
                    "page_id": project_page["id"],
                    "task_count": len(plan.get("tasks", [])),
                    "milestone_count": len(plan.get("milestones", [])),
                    "estimated_duration_weeks": plan.get("estimated_duration_weeks"),
                    "timeline": plan.get("timeline_recommendation", ""),
                }
                result["projects"].append(project_info)
                result["steps"].append(
                    f"Created Notion project page for: {project_info['title']}"
                )

            except Exception as e:
                result["errors"].append(
                    f"Project creation failed for '{idea.get('title', '?')}': {str(e)}"
                )

        result["status"] = "completed" if not result["errors"] else "completed_with_errors"
        result["project_count"] = len(result["projects"])
        self._log_event("obsidian_processed", result)

        return result

    # ─── Scan Inbox (Fireflies reports in Notion) ───────────────────────

    def scan_fireflies_inbox(self):
        """Scan a designated Notion inbox database for unprocessed Fireflies reports.

        Looks for pages in the Fireflies inbox database that haven't been processed yet,
        processes each one, and marks it as processed.

        Returns:
            Dict with scan results.
        """
        inbox_db_id = current_app.config.get("NOTION_FIREFLIES_INBOX_DB_ID", "")
        if not inbox_db_id:
            return {"status": "error", "message": "NOTION_FIREFLIES_INBOX_DB_ID not configured"}

        result = {"status": "scanning", "processed": [], "errors": []}

        try:
            # Query for unprocessed reports
            response = self.notion.query_database(
                database_id=inbox_db_id,
                filter_obj={
                    "property": "Processed",
                    "checkbox": {"equals": False},
                },
                sorts=[{"property": "Created", "direction": "ascending"}],
            )

            pages = response.get("results", [])
            result["found"] = len(pages)

            for page in pages:
                try:
                    # Extract the report content from the page
                    page_id = page["id"]
                    blocks = self.notion.get_block_children(page_id)
                    report_text = self._blocks_to_text(blocks)

                    if not report_text.strip():
                        result["errors"].append(f"Empty report in page {page_id}")
                        continue

                    # Process the report
                    process_result = self.process_fireflies_report(report_text)
                    result["processed"].append({
                        "page_id": page_id,
                        "client": process_result.get("client_name", "Unknown"),
                        "tasks_created": process_result.get("task_count", 0),
                        "status": process_result.get("status"),
                    })

                    # Mark as processed by updating the page
                    self.notion._get_client().pages.update(
                        page_id=page_id,
                        properties={
                            "Processed": {"checkbox": True},
                        },
                    )

                except Exception as e:
                    result["errors"].append(f"Failed to process page {page.get('id', '?')}: {str(e)}")

        except Exception as e:
            result["errors"].append(f"Inbox scan failed: {str(e)}")
            result["status"] = "failed"
            return result

        result["status"] = "completed"
        result["processed_count"] = len(result["processed"])
        self._log_event("inbox_scan", result)
        return result

    # ─── Internal Helpers ───────────────────────────────────────────────

    def _get_known_clients(self):
        """Get list of known client names from the database."""
        from app.models import ClientRecord
        clients = ClientRecord.query.all()
        return [c.name for c in clients]

    def _ensure_client_workspace(self, client_name, is_new=False):
        """Find or create a client's Notion workspace (page + database).

        Returns the ClientRecord with Notion IDs populated.
        """
        from app.models import ClientRecord

        # Check local database first
        record = ClientRecord.query.filter(
            db.func.lower(ClientRecord.name) == client_name.lower()
        ).first()

        if record and record.notion_page_id and record.notion_database_id:
            return record

        # Try to find existing Notion database
        if not is_new:
            existing_db = self.notion.find_client_database(client_name)
            if existing_db:
                db_id = existing_db["id"]
                # Try to find the parent page
                parent = existing_db.get("parent", {})
                page_id = parent.get("page_id", "")

                if not record:
                    record = ClientRecord(name=client_name)
                    db.session.add(record)

                record.notion_database_id = db_id
                if page_id:
                    record.notion_page_id = page_id
                db.session.commit()
                return record

        # Create new client workspace
        client_page = self.notion.create_client_page(client_name)
        client_page_id = client_page["id"]

        client_db = self.notion.create_client_database(
            client_name, parent_page_id=client_page_id
        )
        client_db_id = client_db["id"]

        if not record:
            record = ClientRecord(name=client_name)
            db.session.add(record)

        record.notion_page_id = client_page_id
        record.notion_database_id = client_db_id
        db.session.commit()

        return record

    def _merge_tasks(self, extracted_tasks, action_items):
        """Merge tasks from extraction and parsed action items, deduplicating."""
        seen = set()
        merged = []

        for task in extracted_tasks:
            name = task.get("name", "").strip().lower()
            if name and name not in seen:
                seen.add(name)
                merged.append(task)

        for item in action_items:
            if isinstance(item, dict):
                name = item.get("task", item.get("name", "")).strip().lower()
                if name and name not in seen:
                    seen.add(name)
                    merged.append({
                        "name": item.get("task", item.get("name", "")),
                        "assignee": item.get("assignee", "Unassigned"),
                        "priority": item.get("priority", "Medium"),
                        "category": item.get("category", "Action Item"),
                        "due_date": item.get("due_date", ""),
                    })
            elif isinstance(item, str):
                name = item.strip().lower()
                if name and name not in seen:
                    seen.add(name)
                    merged.append({
                        "name": item,
                        "assignee": "Unassigned",
                        "priority": "Medium",
                        "category": "Action Item",
                    })

        return merged

    def _blocks_to_text(self, blocks):
        """Convert Notion blocks to plain text for processing."""
        lines = []
        for block in blocks:
            block_type = block.get("type", "")
            content = block.get(block_type, {})
            rich_text = content.get("rich_text", [])
            text = "".join(t.get("plain_text", "") for t in rich_text)
            if text:
                lines.append(text)
        return "\n".join(lines)

    def _log_event(self, event_type, data):
        """Log an agent event to the database."""
        from app.models import AgentLog
        try:
            log = AgentLog(
                event_type=event_type,
                data=json.dumps(data, default=str),
            )
            db.session.add(log)
            db.session.commit()
        except Exception:
            # Don't let logging failures break the pipeline
            db.session.rollback()
