"""Centralized AI client for all Claude API interactions."""

import anthropic
from flask import current_app


class AIClient:
    """Wrapper around the Anthropic API for all prose operations."""

    def __init__(self, api_key=None, model=None):
        self.api_key = api_key
        self.model = model

    def _get_client(self):
        key = self.api_key or current_app.config.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file or environment."
            )
        return anthropic.Anthropic(api_key=key)

    def _get_model(self):
        return self.model or current_app.config.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    def generate(self, system_prompt, user_prompt, max_tokens=8192, temperature=0.7):
        """Send a prompt to Claude and return the text response."""
        client = self._get_client()
        message = client.messages.create(
            model=self._get_model(),
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    def generate_with_context(self, system_prompt, messages, max_tokens=8192, temperature=0.7):
        """Send a multi-turn conversation to Claude."""
        client = self._get_client()
        message = client.messages.create(
            model=self._get_model(),
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages,
        )
        return message.content[0].text
