"""
LearningPlanModule
------------------
Provides functionality to generate personalized learning plans based on quiz results
or custom learning goals. Integrates with LLM to recommend resources per topic.
"""

from .learning_plan import LearningPlan
from .plan_agent import Plan_Agent

__all__ = ["LearningPlan", "Plan_Agent"]
