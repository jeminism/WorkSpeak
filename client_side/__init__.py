"""
WorkSpeak Client-Side Agent

A local monitoring and rewriting agent that intercepts messages before sending
to Slack, providing professional rewriting for all message types including
1:1 DMs to other humans.

Architecture:
- Core: Message interception, LLM integration, quality control
- Integrations: Slack desktop app hooks, accessibility APIs
- Interfaces: UI components, configuration management
"""

__version__ = "0.1.0"
