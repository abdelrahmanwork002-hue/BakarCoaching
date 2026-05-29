"""
Gym Specialist Agent
====================
Contains the Creator, Modifier, and Checker nodes for the Gym domain.
Modify this file to change how gym workout plans are generated or validated.
"""
from src.state import AgentState
from src.agents.base import base_creator_node, base_modifier_node, base_checker_node

_DOMAIN = "Gym"


def gym_creator_node(state: AgentState) -> dict:
    """
    Creates the initial Gym workout plan based on the Senior Coach's directive.
    Model: Groq Llama 3.3 70B
    Edit this function to change what the Gym Creator focuses on.
    """
    directive = state["macro_strategy"].specialist_directives.get(
        _DOMAIN,
        "Design a balanced hypertrophy and strength program using compound and isolation exercises."
    )
    return base_creator_node(state, _DOMAIN, directive)


def gym_modifier_node(state: AgentState) -> dict:
    """
    Applies targeted corrections to a rejected Gym plan based on checker feedback.
    Does NOT regenerate from scratch — only patches what was flagged.
    Model: Groq Llama 3.3 70B
    Edit this function to adjust how the modifier corrects gym plans.
    """
    return base_modifier_node(state, _DOMAIN)


def gym_checker_node(state: AgentState) -> dict:
    """
    Safety & Efficacy Auditor for Gym plans.
    Validates safety, experience-appropriateness, and all 9 exercise fields.
    Model: Google Gemini Flash
    Edit this function to change validation criteria for gym exercises.
    """
    return base_checker_node(state, _DOMAIN)
