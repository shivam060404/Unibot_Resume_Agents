"""Unibot Resume Agents — ADK package entry point.

This file exposes root_agent for ADK discovery.
Run with: adk web unibot  OR  adk run unibot
"""

from .agent import root_agent

__all__ = ["root_agent"]
