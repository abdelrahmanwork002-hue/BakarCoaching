"""
Yoga Specialist Agent
=====================
Contains the Creator, Modifier, and Checker nodes for the Yoga domain.
Modify this file to change how yoga/mobility plans are generated or validated.
"""
from src.state import AgentState
from src.agents.base import base_creator_node, base_modifier_node, base_checker_node

_DOMAIN = "Yoga"


def yoga_creator_node(state: AgentState) -> dict:
    """
    Creates the initial Yoga / mobility plan based on the Senior Coach's directive.
    Model: Groq Llama 3.3 70B
    Edit this function to change what the Yoga Creator focuses on.
    """
    directive = state["macro_strategy"].specialist_directives.get(
        _DOMAIN,
        "Design a restorative yoga and mobility program for active recovery, flexibility, and stress reduction."
    )
    return base_creator_node(state, _DOMAIN, directive)


def yoga_modifier_node(state: AgentState) -> dict:
    """
    Applies targeted corrections to a rejected Yoga plan based on checker feedback.
    Does NOT regenerate from scratch — only patches what was flagged.
    Model: Groq Llama 3.3 70B
    Edit this function to adjust how the modifier corrects yoga plans.
    """
    return base_modifier_node(state, _DOMAIN)


def yoga_checker_node(state: AgentState) -> dict:
    """
    Safety & Efficacy Auditor for Yoga / mobility plans.
    Validates safety, experience-appropriateness, and all 9 exercise fields.
    Model: Google Gemini Flash
    Edit this function to change validation criteria for yoga sessions.
    """
    return base_checker_node(state, _DOMAIN)
