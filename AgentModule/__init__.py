"""Convenience exports for the agent module."""

from .edu_agent import create_agent, run_agent
from .qa_agent import QA_Agent

__all__ = ["create_agent", "run_agent", "QA_Agent"]
