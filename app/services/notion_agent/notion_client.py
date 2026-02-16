"""Notion API client for workspace management.

Handles all direct interactions with the Notion API: creating databases,
pages, querying content, and managing client workspaces.
"""

import json
import datetime
from notion_client import Client
from flask import current_app


class NotionService:
    """Manages all Notion API operations for the agent."""

    def __init__(self, token=None):
        self.token = token

    def _get_client(self):
        token = self.token or current_app.config.get("NOTION_TOKEN", "")
        if not token:
            raise ValueError(
                "NOTION_TOKEN is not set. Add it to your .env file or environment."
            )
        return Client(auth=token)

    def _get_parent_page_id(self):
        return current_app.config.get("NOTION_PARENT_PAGE_ID", "")

    # ─── Workspace Discovery ────────────────────────────────────────────

    def search_databases(self, query=""):
        """Search for databases in the workspace."""
        client = self._get_client()
        results = client.search(
            query=query,
            filter={"property": "object", "value": "database"},
        )
        return results.get("results", [])

    def search_pages(self, query=""):
        """Search for pages in the workspace."""
        client = self._get_client()
        results = client.search(
            query=query,
            filter={"property": "object", "value": "page"},
        )
        return results.get("results", [])

    def get_database(self, database_id):
        """Retrieve a database by ID."""
        client = self._get_client()
        return client.databases.retrieve(database_id=database_id)

    def query_database(self, database_id, filter_obj=None, sorts=None):
        """Query a database with optional filters and sorts."""
        client = self._get_client()
        kwargs = {"database_id": database_id}
        if filter_obj:
            kwargs["filter"] = filter_obj
        if sorts:
            kwargs["sorts"] = sorts
        return client.databases.query(**kwargs)

    # ─── Client Database Management ─────────────────────────────────────

    def find_client_database(self, client_name):
        """Find an existing client database by name."""
        databases = self.search_databases(query=client_name)
        for db in databases:
            title_parts = db.get("title", [])
            title = "".join(t.get("plain_text", "") for t in title_parts)
            if client_name.lower() in title.lower():
                return db
        return None

    def create_client_database(self, client_name, parent_page_id=None):
        """Create a new client task database with standard properties.

        Creates a database with columns for:
        - Name (title)
        - Status (select: Not Started, In Progress, Done, Blocked)
        - Assignee (rich_text)
        - Due Date (date)
        - Priority (select: High, Medium, Low)
        - Category (select: Task, Follow-up, Decision, Action Item)
        - Meeting Date (date)
        - Source (rich_text - which meeting it came from)
        """
        client = self._get_client()
        parent_id = parent_page_id or self._get_parent_page_id()

        if not parent_id:
            raise ValueError(
                "NOTION_PARENT_PAGE_ID is not set. Specify a parent page for new databases."
            )

        database = client.databases.create(
            parent={"type": "page_id", "page_id": parent_id},
            title=[{"type": "text", "text": {"content": f"{client_name} - Tasks & Meetings"}}],
            properties={
                "Name": {"title": {}},
                "Status": {
                    "select": {
                        "options": [
                            {"name": "Not Started", "color": "gray"},
                            {"name": "In Progress", "color": "blue"},
                            {"name": "Done", "color": "green"},
                            {"name": "Blocked", "color": "red"},
                        ]
                    }
                },
                "Assignee": {"rich_text": {}},
                "Due Date": {"date": {}},
                "Priority": {
                    "select": {
                        "options": [
                            {"name": "High", "color": "red"},
                            {"name": "Medium", "color": "yellow"},
                            {"name": "Low", "color": "green"},
                        ]
                    }
                },
                "Category": {
                    "select": {
                        "options": [
                            {"name": "Task", "color": "blue"},
                            {"name": "Follow-up", "color": "purple"},
                            {"name": "Decision", "color": "orange"},
                            {"name": "Action Item", "color": "pink"},
                        ]
                    }
                },
                "Meeting Date": {"date": {}},
                "Source": {"rich_text": {}},
            },
        )
        return database

    def create_client_page(self, client_name, parent_page_id=None):
        """Create a top-level client page that will contain the database and summary reports."""
        client = self._get_client()
        parent_id = parent_page_id or self._get_parent_page_id()

        if not parent_id:
            raise ValueError("NOTION_PARENT_PAGE_ID is not set.")

        page = client.pages.create(
            parent={"type": "page_id", "page_id": parent_id},
            properties={
                "title": [{"type": "text", "text": {"content": f"{client_name}"}}],
            },
            children=[
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": f"{client_name} - Client Hub"}}]
                    },
                },
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "This page is managed by the Notion AI Agent. "
                                    "Meeting summaries from Fireflies.ai are automatically filed here, "
                                    "and tasks are extracted and assigned."
                                },
                            }
                        ],
                        "icon": {"type": "emoji", "emoji": "🤖"},
                    },
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "Meeting Summaries"}}]
                    },
                },
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {},
                },
            ],
        )
        return page

    # ─── Meeting Summary Pages ──────────────────────────────────────────

    def create_meeting_summary_page(self, parent_page_id, meeting_data):
        """Create a page for a Fireflies meeting summary under a client page.

        Args:
            parent_page_id: The client page ID to nest under.
            meeting_data: Dict with keys: title, date, attendees, summary,
                         action_items, key_topics, transcript_highlights.
        """
        client = self._get_client()

        children = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Meeting Details"}}]
                },
            },
            {
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": 2,
                    "has_column_header": False,
                    "has_row_header": True,
                    "children": [
                        {
                            "type": "table_row",
                            "table_row": {
                                "cells": [
                                    [{"type": "text", "text": {"content": "Date"}}],
                                    [{"type": "text", "text": {"content": meeting_data.get("date", "N/A")}}],
                                ]
                            },
                        },
                        {
                            "type": "table_row",
                            "table_row": {
                                "cells": [
                                    [{"type": "text", "text": {"content": "Attendees"}}],
                                    [{"type": "text", "text": {"content": ", ".join(meeting_data.get("attendees", []))}}],
                                ]
                            },
                        },
                    ],
                },
            },
        ]

        # Summary section
        if meeting_data.get("summary"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Summary"}}]
                },
            })
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": meeting_data["summary"][:2000]}}]
                },
            })

        # Key topics
        if meeting_data.get("key_topics"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Key Topics"}}]
                },
            })
            for topic in meeting_data["key_topics"]:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": topic[:2000]}}]
                    },
                })

        # Action items
        if meeting_data.get("action_items"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Action Items"}}]
                },
            })
            for item in meeting_data["action_items"]:
                content = item.get("task", item) if isinstance(item, dict) else str(item)
                assignee = item.get("assignee", "") if isinstance(item, dict) else ""
                text = f"{content}"
                if assignee:
                    text += f" — Assigned to: {assignee}"
                children.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
                        "checked": False,
                    },
                })

        # Transcript highlights
        if meeting_data.get("transcript_highlights"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Notable Quotes / Highlights"}}]
                },
            })
            for highlight in meeting_data["transcript_highlights"]:
                children.append({
                    "object": "block",
                    "type": "quote",
                    "quote": {
                        "rich_text": [{"type": "text", "text": {"content": highlight[:2000]}}]
                    },
                })

        title = meeting_data.get("title", "Meeting Summary")
        date_str = meeting_data.get("date", "")
        page_title = f"{title} ({date_str})" if date_str else title

        page = client.pages.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            properties={
                "title": [{"type": "text", "text": {"content": page_title}}],
            },
            children=children,
        )
        return page

    # ─── Task Creation ──────────────────────────────────────────────────

    def create_task_in_database(self, database_id, task_data):
        """Create a task entry in a client's task database.

        Args:
            database_id: The client task database ID.
            task_data: Dict with keys: name, assignee, due_date, priority,
                      category, meeting_date, source.
        """
        client = self._get_client()

        properties = {
            "Name": {"title": [{"text": {"content": task_data.get("name", "Untitled Task")}}]},
            "Status": {"select": {"name": task_data.get("status", "Not Started")}},
        }

        if task_data.get("assignee"):
            properties["Assignee"] = {
                "rich_text": [{"text": {"content": task_data["assignee"]}}]
            }

        if task_data.get("due_date"):
            properties["Due Date"] = {"date": {"start": task_data["due_date"]}}

        if task_data.get("priority"):
            properties["Priority"] = {"select": {"name": task_data["priority"]}}

        if task_data.get("category"):
            properties["Category"] = {"select": {"name": task_data["category"]}}

        if task_data.get("meeting_date"):
            properties["Meeting Date"] = {"date": {"start": task_data["meeting_date"]}}

        if task_data.get("source"):
            properties["Source"] = {
                "rich_text": [{"text": {"content": task_data["source"]}}]
            }

        page = client.pages.create(
            parent={"database_id": database_id},
            properties=properties,
        )
        return page

    # ─── Project Pages (Obsidian Integration) ───────────────────────────

    def create_project_page(self, parent_page_id, project_data):
        """Create a full project page from an Obsidian idea.

        Args:
            parent_page_id: Parent page ID for the projects area.
            project_data: Dict with keys: title, description, tasks, milestones,
                         due_dates, timeline_recommendation, requirements.
        """
        client = self._get_client()

        children = []

        # Project overview
        children.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [
                    {"type": "text", "text": {"content": "Project sourced from Obsidian monthly review. "}},
                    {"type": "text", "text": {"content": f"Created: {datetime.datetime.utcnow().strftime('%Y-%m-%d')}"}},
                ],
                "icon": {"type": "emoji", "emoji": "📋"},
            },
        })

        # Description
        if project_data.get("description"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Project Description"}}]
                },
            })
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": project_data["description"][:2000]}}]
                },
            })

        # Requirements
        if project_data.get("requirements"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Requirements"}}]
                },
            })
            for req in project_data["requirements"]:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": req[:2000]}}]
                    },
                })

        # Task list
        if project_data.get("tasks"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Task List"}}]
                },
            })
            for task in project_data["tasks"]:
                task_text = task.get("name", task) if isinstance(task, dict) else str(task)
                assignee = task.get("assignee", "") if isinstance(task, dict) else ""
                due = task.get("due_date", "") if isinstance(task, dict) else ""
                text = task_text
                if assignee:
                    text += f" | Assignee: {assignee}"
                if due:
                    text += f" | Due: {due}"
                children.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
                        "checked": False,
                    },
                })

        # Milestones
        if project_data.get("milestones"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Milestones"}}]
                },
            })
            for milestone in project_data["milestones"]:
                m_name = milestone.get("name", milestone) if isinstance(milestone, dict) else str(milestone)
                m_date = milestone.get("target_date", "") if isinstance(milestone, dict) else ""
                text = m_name
                if m_date:
                    text += f" — Target: {m_date}"
                children.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [
                            {"type": "text", "text": {"content": text[:2000]}}
                        ]
                    },
                })

        # Timeline & Recommendations
        if project_data.get("timeline_recommendation"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Timeline & Recommendations"}}]
                },
            })
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": project_data["timeline_recommendation"][:2000]}}]
                },
            })

        page = client.pages.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            properties={
                "title": [{"type": "text", "text": {"content": project_data.get("title", "New Project")}}],
            },
            children=children,
        )
        return page

    # ─── Utility ────────────────────────────────────────────────────────

    def append_blocks_to_page(self, page_id, blocks):
        """Append blocks to an existing page."""
        client = self._get_client()
        return client.blocks.children.append(block_id=page_id, children=blocks)

    def get_page(self, page_id):
        """Retrieve a page by ID."""
        client = self._get_client()
        return client.pages.retrieve(page_id=page_id)

    def get_block_children(self, block_id):
        """Get all child blocks of a block/page."""
        client = self._get_client()
        results = []
        has_more = True
        start_cursor = None
        while has_more:
            kwargs = {"block_id": block_id}
            if start_cursor:
                kwargs["start_cursor"] = start_cursor
            response = client.blocks.children.list(**kwargs)
            results.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
        return results
