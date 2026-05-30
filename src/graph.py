"""
LangGraph State Machine — Fitness & Nutrition Orchestration
============================================================
Full graph flow:
  START
    → orchestrator (Senior Coach — assigns specialist_directives)
    → [parallel: only the creators the user selected + nutrition_creator]
    → per-domain Creator → Checker → [Modifier → Checker]* → fitness_merge / plan_merge / HITL
    → fitness_merge (aggregates only selected domains)
    → plan_merge
    → tracking_coach (Tracking Coach — generates TrackingStrategy)
    → pre_release_gate (HITL interrupt — human review before finalizing)
    → END

KEY DESIGN: specialist_directives keys drive routing. Domains NOT in directives
are skipped entirely — their creators, checkers, and modifiers never run.
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

from src.state import AgentState, FitnessPlan

# Agents
from src.agents.orchestrator_agent import orchestrator_node
from src.agents.tracking_agent import tracking_coach_node

# Domain specialists
from src.agents.gym_agent import gym_creator_node, gym_modifier_node, gym_checker_node
from src.agents.yoga_agent import yoga_creator_node, yoga_modifier_node, yoga_checker_node
from src.agents.calisthenics_agent import (
    calisthenics_creator_node, calisthenics_modifier_node, calisthenics_checker_node
)
from src.agents.nutrition_agent import (
    nutrition_creator_node, nutrition_modifier_node, nutrition_checker_node
)

# ---------------------------------------------------------------------------
# Routing: Orchestrator → Specialists (dynamic, only selected domains)
# ---------------------------------------------------------------------------

def route_specialists(state: AgentState) -> list[str]:
    """
    Routes from Senior Coach to the specialist creators that are activated.
    Only domains present in specialist_directives will run.
    Nutrition always runs.
    """
    directives = state["macro_strategy"].specialist_directives
    routes = []
    if "Gym" in directives:
        routes.append("gym_creator")
    if "Yoga" in directives:
        routes.append("yoga_creator")
    if "Calisthenics" in directives:
        routes.append("calisthenics_creator")
    # Nutrition always runs regardless
    routes.append("nutrition_creator")
    return routes

# ---------------------------------------------------------------------------
# Routing: Checker → Modifier / Merge / HITL
#
# CRITICAL: check if the domain was even activated before checking rejections.
# If not activated → go directly to merge (skip domain).
# If activated and approved (rejection is None or missing) → merge.
# If activated and rejected → modifier or HITL.
# ---------------------------------------------------------------------------

def _is_domain_active(state: AgentState, domain: str) -> bool:
    """Returns True if this domain was selected by the user/orchestrator."""
    directives = state.get("macro_strategy", {})
    if hasattr(directives, "specialist_directives"):
        return domain in directives.specialist_directives
    return False

def _was_rejected(state: AgentState, domain: str) -> bool:
    """Returns True if the domain checker explicitly rejected the draft."""
    rejections = state.get("current_rejections", {})
    return rejections.get(domain) not in (None, "")

def check_gym_status(state: AgentState) -> Literal["fitness_merge", "gym_modifier", "hitl_gym"]:
    if not _is_domain_active(state, "Gym"):
        return "fitness_merge"
    if not _was_rejected(state, "Gym"):
        return "fitness_merge"
    if state.get("domain_retries", {}).get("Gym", 0) >= 2:
        return "hitl_gym"
    return "gym_modifier"

def check_yoga_status(state: AgentState) -> Literal["fitness_merge", "yoga_modifier", "hitl_yoga"]:
    if not _is_domain_active(state, "Yoga"):
        return "fitness_merge"
    if not _was_rejected(state, "Yoga"):
        return "fitness_merge"
    if state.get("domain_retries", {}).get("Yoga", 0) >= 2:
        return "hitl_yoga"
    return "yoga_modifier"

def check_calis_status(state: AgentState) -> Literal["fitness_merge", "calisthenics_modifier", "hitl_calis"]:
    if not _is_domain_active(state, "Calisthenics"):
        return "fitness_merge"
    if not _was_rejected(state, "Calisthenics"):
        return "fitness_merge"
    if state.get("domain_retries", {}).get("Calisthenics", 0) >= 2:
        return "hitl_calis"
    return "calisthenics_modifier"

def check_nutrition_status(state: AgentState) -> Literal["plan_merge", "nutrition_modifier", "hitl_nutrition"]:
    if not _was_rejected(state, "Nutrition"):
        return "plan_merge"
    if state.get("domain_retries", {}).get("Nutrition", 0) >= 2:
        return "hitl_nutrition"
    return "nutrition_modifier"

# ---------------------------------------------------------------------------
# Merge Nodes
# ---------------------------------------------------------------------------

def fitness_merge_node(state: AgentState) -> dict:
    """
    Aggregates approved sessions into the global fitness_plan.
    Called once per active fitness domain (parallel branches converge here).
    Each call adds its domain's sessions to the accumulating plan.
    Non-active domains are ignored — they never produce approved_X data.
    """
    current = state.get("fitness_plan", FitnessPlan())

    # Pick up the best available data for each domain.
    # For active domains: approved_X will be set. For inactive: it stays None.
    # We use `or current.X` so each parallel call accumulates without wiping siblings.
    gym_sessions  = state.get("approved_gym")         or current.gym_sessions  or []
    yoga_sessions = state.get("approved_yoga")        or current.yoga_sessions or []
    cali_sessions = state.get("approved_calisthenics") or current.calisthenics_sessions or []

    new_plan = FitnessPlan(
        gym_sessions=gym_sessions,
        yoga_sessions=yoga_sessions,
        calisthenics_sessions=cali_sessions,
    )
    return {"fitness_plan": new_plan}

def plan_merge_node(state: AgentState) -> dict:
    """Sync point — waits for both fitness and nutrition to complete before Tracking Coach."""
    return {}

def pre_release_gate(state: AgentState) -> dict:
    """Final human-in-the-loop gate before the plan is released. LangGraph interrupts here."""
    return {}

def hitl_dummy_node(state: AgentState) -> dict:
    """Escalation node — pauses for human review when a domain exceeds max retries."""
    return {}

# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------

def build_graph():
    builder = StateGraph(AgentState)

    # --- Core Nodes ---
    builder.add_node("orchestrator",      orchestrator_node)
    builder.add_node("tracking_coach",    tracking_coach_node)
    builder.add_node("fitness_merge",     fitness_merge_node)
    builder.add_node("plan_merge",        plan_merge_node)
    builder.add_node("pre_release_gate",  pre_release_gate)

    # --- Domain Creators ---
    builder.add_node("gym_creator",           gym_creator_node)
    builder.add_node("yoga_creator",          yoga_creator_node)
    builder.add_node("calisthenics_creator",  calisthenics_creator_node)
    builder.add_node("nutrition_creator",     nutrition_creator_node)

    # --- Domain Modifiers ---
    builder.add_node("gym_modifier",          gym_modifier_node)
    builder.add_node("yoga_modifier",         yoga_modifier_node)
    builder.add_node("calisthenics_modifier", calisthenics_modifier_node)
    builder.add_node("nutrition_modifier",    nutrition_modifier_node)

    # --- Domain Checkers ---
    builder.add_node("gym_checker",           gym_checker_node)
    builder.add_node("yoga_checker",          yoga_checker_node)
    builder.add_node("calisthenics_checker",  calisthenics_checker_node)
    builder.add_node("nutrition_checker",     nutrition_checker_node)

    # --- HITL Escalation Nodes ---
    builder.add_node("hitl_gym",       hitl_dummy_node)
    builder.add_node("hitl_yoga",      hitl_dummy_node)
    builder.add_node("hitl_calis",     hitl_dummy_node)
    builder.add_node("hitl_nutrition", hitl_dummy_node)

    # --- Graph Edges ---

    # Entry
    builder.add_edge(START, "orchestrator")

    # Dynamic fan-out: only run creators for selected domains
    # All 4 nodes must be listed as possible targets even if not all will be used
    builder.add_conditional_edges(
        "orchestrator",
        route_specialists,
        ["gym_creator", "yoga_creator", "calisthenics_creator", "nutrition_creator"]
    )

    # Gym loop: Creator → Checker → [Modifier → Checker]* → Merge / HITL
    builder.add_edge("gym_creator",   "gym_checker")
    builder.add_conditional_edges("gym_checker", check_gym_status,
        {"fitness_merge": "fitness_merge", "gym_modifier": "gym_modifier", "hitl_gym": "hitl_gym"})
    builder.add_edge("gym_modifier",  "gym_checker")
    builder.add_edge("hitl_gym",      "fitness_merge")

    # Yoga loop
    builder.add_edge("yoga_creator",  "yoga_checker")
    builder.add_conditional_edges("yoga_checker", check_yoga_status,
        {"fitness_merge": "fitness_merge", "yoga_modifier": "yoga_modifier", "hitl_yoga": "hitl_yoga"})
    builder.add_edge("yoga_modifier", "yoga_checker")
    builder.add_edge("hitl_yoga",     "fitness_merge")

    # Calisthenics loop
    builder.add_edge("calisthenics_creator",  "calisthenics_checker")
    builder.add_conditional_edges("calisthenics_checker", check_calis_status,
        {"fitness_merge": "fitness_merge", "calisthenics_modifier": "calisthenics_modifier", "hitl_calis": "hitl_calis"})
    builder.add_edge("calisthenics_modifier", "calisthenics_checker")
    builder.add_edge("hitl_calis",            "fitness_merge")

    # Nutrition loop
    builder.add_edge("nutrition_creator",  "nutrition_checker")
    builder.add_conditional_edges("nutrition_checker", check_nutrition_status,
        {"plan_merge": "plan_merge", "nutrition_modifier": "nutrition_modifier", "hitl_nutrition": "hitl_nutrition"})
    builder.add_edge("nutrition_modifier", "nutrition_checker")
    builder.add_edge("hitl_nutrition",     "plan_merge")

    # Final merge → Tracking Coach → Gate → END
    builder.add_edge("fitness_merge",    "plan_merge")
    builder.add_edge("plan_merge",       "tracking_coach")
    builder.add_edge("tracking_coach",   "pre_release_gate")
    builder.add_edge("pre_release_gate", END)

    # --- Persistence ---
    conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
    memory = SqliteSaver(conn)

    graph = builder.compile(
        checkpointer=memory,
        interrupt_before=["pre_release_gate", "hitl_gym", "hitl_yoga", "hitl_calis", "hitl_nutrition"]
    )
    return graph
