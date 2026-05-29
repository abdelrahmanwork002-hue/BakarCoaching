"""
Calisthenics Specialist Agent
==============================
Contains the Creator, Modifier, and Checker nodes for the Calisthenics domain.
Modify this file to change how bodyweight plans are generated or validated.
"""
from src.state import AgentState
from src.agents.base import base_creator_node, base_modifier_node, base_checker_node

_DOMAIN = "Calisthenics"


def calisthenics_creator_node(state: AgentState) -> dict:
    """
    Creates the initial Calisthenics plan based on the Senior Coach's directive.
    Model: Groq Llama 3.3 70B
    Edit this function to change what the Calisthenics Creator focuses on.
    """
    directive = state["macro_strategy"].specialist_directives.get(
        _DOMAIN,
        "Design a progressive calisthenics program focused on bodyweight mastery, core stability, and skill progressions."
    )
    return base_creator_node(state, _DOMAIN, directive)


def calisthenics_modifier_node(state: AgentState) -> dict:
    """
    Applies targeted corrections to a rejected Calisthenics plan based on checker feedback.
    Does NOT regenerate from scratch — only patches what was flagged.
    Model: Groq Llama 3.3 70B
    Edit this function to adjust how the modifier corrects calisthenics plans.
    """
    return base_modifier_node(state, _DOMAIN)


def calisthenics_checker_node(state: AgentState) -> dict:
    """
    Safety & Efficacy Auditor for Calisthenics plans.
    Validates safety, experience-appropriateness, and all 9 exercise fields.
    Model: Google Gemini Flash
    Edit this function to change validation criteria for calisthenics sessions.
    """
    return base_checker_node(state, _DOMAIN)
