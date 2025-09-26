"""
QuizModule
----------
This module provides functionality for generating subject-based quizzes
and corresponding learning plans based on user performance.
"""

from .quiz_operations import (
    generate_quiz,
    generate_learning_plan_from_quiz,
    prepare_quiz_questions,
)

__all__ = [
    "generate_quiz",
    "generate_learning_plan_from_quiz",
    "prepare_quiz_questions",
]
