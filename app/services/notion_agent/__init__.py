"""Notion AI Agent - Automated meeting report processing and project management.

This agent integrates Fireflies.ai meeting summaries, Notion workspace management,
and Obsidian project idea ingestion into a unified automation pipeline.
"""

from app.services.notion_agent.agent import NotionAgent
from app.services.notion_agent.notion_client import NotionService
from app.services.notion_agent.fireflies_processor import FirefliesProcessor
from app.services.notion_agent.obsidian_processor import ObsidianProcessor

__all__ = ["NotionAgent", "NotionService", "FirefliesProcessor", "ObsidianProcessor"]
