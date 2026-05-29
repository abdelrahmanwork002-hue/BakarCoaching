"""
LangGraph State Machine — Fitness & Nutrition Orchestration
============================================================
Full graph flow:
  START
    → orchestrator (Senior Coach — assigns specialist_directives)
    → [parallel: gym_creator, yoga_creator, calisthenics_creator, nutrition_creator]
    → [parallel: gym_checker, yoga_checker, calisthenics_checker, nutrition_checker]
    → per-domain routing:
        Approved  → fitness_merge / plan_merge
        Rejected  → domain_modifier → domain_checker (retry loop)
        Max retries → hitl_<domain> → merge (escalate to human)
    → fitness_merge
    → plan_merge
    → tracking_coach (Tracking Coach — generates TrackingStrategy)
    → pre_release_gate (HITL interrupt — human review before finalizing)
    → END
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
# Routing: Orchestrator → Specialists
# ---------------------------------------------------------------------------

def route_specialists(state: AgentState) -> list[str]:
    """Routes from Senior Coach to the activated specialist creators (parallel)."""
    directives = state["macro_strategy"].specialist_directives
    routes = []
    if "Gym" in directives:
        routes.append("gym_creator")
    if "Yoga" in directives:
        routes.append("yoga_creator")
    if "Calisthenics" in directives:
        routes.append("calisthenics_creator")
    # Nutrition always runs in parallel
    routes.append("nutrition_creator")
    return routes

# ---------------------------------------------------------------------------
# Routing: Checker → Modifier / Merge / HITL
# ---------------------------------------------------------------------------

def check_gym_status(state: AgentState) -> Literal["fitness_merge", "gym_modifier", "hitl_gym"]:
    """After Gym checker: approve → merge, reject → modifier, max retries → HITL."""
    if "Gym" not in state.get("current_rejections", {}):
        return "fitness_merge"
    if state.get("domain_retries", {}).get("Gym", 0) >= 2:
        return "hitl_gym"
    return "gym_modifier"

def check_yoga_status(state: AgentState) -> Literal["fitness_merge", "yoga_modifier", "hitl_yoga"]:
    """After Yoga checker: approve → merge, reject → modifier, max retries → HITL."""
    if "Yoga" not in state.get("current_rejections", {}):
        return "fitness_merge"
    if state.get("domain_retries", {}).get("Yoga", 0) >= 2:
        return "hitl_yoga"
    return "yoga_modifier"

def check_calis_status(state: AgentState) -> Literal["fitness_merge", "calisthenics_modifier", "hitl_calis"]:
    """After Calisthenics checker: approve → merge, reject → modifier, max retries → HITL."""
    if "Calisthenics" not in state.get("current_rejections", {}):
        return "fitness_merge"
    if state.get("domain_retries", {}).get("Calisthenics", 0) >= 2:
        return "hitl_calis"
    return "calisthenics_modifier"

def check_nutrition_status(state: AgentState) -> Literal["plan_merge", "nutrition_modifier", "hitl_nutrition"]:
    """After Nutrition checker: approve → merge, reject → modifier, max retries → HITL."""
    if "Nutrition" not in state.get("current_rejections", {}):
        return "plan_merge"
    if state.get("domain_retries", {}).get("Nutrition", 0) >= 2:
        return "hitl_nutrition"
    return "nutrition_modifier"

# ---------------------------------------------------------------------------
# Merge Nodes
# ---------------------------------------------------------------------------

def fitness_merge_node(state: AgentState) -> dict:
    """Aggregates all approved fitness sessions into the global fitness_plan."""
    current_plan = state.get("fitness_plan", FitnessPlan())

    gym_sessions = state.get("approved_gym") or current_plan.gym_sessions
    yoga_sessions = state.get("approved_yoga") or current_plan.yoga_sessions
    calis_sessions = state.get("approved_calisthenics") or current_plan.calisthenics_sessions

    new_plan = FitnessPlan(
        gym_sessions=gym_sessions,
        yoga_sessions=yoga_sessions,
        calisthenics_sessions=calis_sessions
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
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("tracking_coach", tracking_coach_node)
    builder.add_node("fitness_merge", fitness_merge_node)
    builder.add_node("plan_merge", plan_merge_node)
    builder.add_node("pre_release_gate", pre_release_gate)

    # --- Domain Creators ---
    builder.add_node("gym_creator", gym_creator_node)
    builder.add_node("yoga_creator", yoga_creator_node)
    builder.add_node("calisthenics_creator", calisthenics_creator_node)
    builder.add_node("nutrition_creator", nutrition_creator_node)

    # --- Domain Modifiers (post-checker correction) ---
    builder.add_node("gym_modifier", gym_modifier_node)
    builder.add_node("yoga_modifier", yoga_modifier_node)
    builder.add_node("calisthenics_modifier", calisthenics_modifier_node)
    builder.add_node("nutrition_modifier", nutrition_modifier_node)

    # --- Domain Checkers ---
    builder.add_node("gym_checker", gym_checker_node)
    builder.add_node("yoga_checker", yoga_checker_node)
    builder.add_node("calisthenics_checker", calisthenics_checker_node)
    builder.add_node("nutrition_checker", nutrition_checker_node)

    # --- HITL Escalation Nodes ---
    builder.add_node("hitl_gym", hitl_dummy_node)
    builder.add_node("hitl_yoga", hitl_dummy_node)
    builder.add_node("hitl_calis", hitl_dummy_node)
    builder.add_node("hitl_nutrition", hitl_dummy_node)

    # --- Graph Edges ---

    # Entry
    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        route_specialists,
        ["gym_creator", "yoga_creator", "calisthenics_creator", "nutrition_creator"]
    )

    # Gym loop: Creator → Checker → [Modifier → Checker]* → Merge / HITL
    builder.add_edge("gym_creator", "gym_checker")
    builder.add_conditional_edges("gym_checker", check_gym_status)
    builder.add_edge("gym_modifier", "gym_checker")      # Modifier feeds back into checker
    builder.add_edge("hitl_gym", "fitness_merge")

    # Yoga loop
    builder.add_edge("yoga_creator", "yoga_checker")
    builder.add_conditional_edges("yoga_checker", check_yoga_status)
    builder.add_edge("yoga_modifier", "yoga_checker")
    builder.add_edge("hitl_yoga", "fitness_merge")

    # Calisthenics loop
    builder.add_edge("calisthenics_creator", "calisthenics_checker")
    builder.add_conditional_edges("calisthenics_checker", check_calis_status)
    builder.add_edge("calisthenics_modifier", "calisthenics_checker")
    builder.add_edge("hitl_calis", "fitness_merge")

    # Nutrition loop
    builder.add_edge("nutrition_creator", "nutrition_checker")
    builder.add_conditional_edges("nutrition_checker", check_nutrition_status)
    builder.add_edge("nutrition_modifier", "nutrition_checker")
    builder.add_edge("hitl_nutrition", "plan_merge")

    # Final merge → Tracking Coach → Gate → END
    builder.add_edge("fitness_merge", "plan_merge")
    builder.add_edge("plan_merge", "tracking_coach")
    builder.add_edge("tracking_coach", "pre_release_gate")
    builder.add_edge("pre_release_gate", END)

    # --- Persistence ---
    conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
    memory = SqliteSaver(conn)

    # Compile with interrupts before human review points
    graph = builder.compile(
        checkpointer=memory,
        interrupt_before=["pre_release_gate", "hitl_gym", "hitl_yoga", "hitl_calis", "hitl_nutrition"]
    )
    return graph
