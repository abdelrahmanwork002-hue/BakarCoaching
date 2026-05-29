from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

from src.state import AgentState, FitnessPlan
from src.agents.orchestrator import orchestrator_node
from src.agents.creators import (
    gym_creator_node, yoga_creator_node, calisthenics_creator_node, nutrition_creator_node
)
from src.agents.checkers import (
    gym_checker_node, yoga_checker_node, calisthenics_checker_node, nutrition_checker_node
)

def route_specialists(state: AgentState) -> list[str]:
    """Routes from Orchestrator to the requested specialists."""
    routes = []
    specialists = state["macro_strategy"].specialist_routes
    if "Gym" in specialists:
        routes.append("gym_creator")
    if "Yoga" in specialists:
        routes.append("yoga_creator")
    if "Calisthenics" in specialists:
        routes.append("calisthenics_creator")
        
    # Nutrition is always routed in parallel
    routes.append("nutrition_creator")
    return routes

def check_gym_status(state: AgentState) -> Literal["fitness_merge", "gym_creator", "hitl_gym"]:
    retries = state.get("domain_retries", {}).get("Gym", 0)
    if "Gym" not in state.get("current_rejections", {}):
        return "fitness_merge"
    if retries >= 2:
        return "hitl_gym"
    return "gym_creator"

def check_yoga_status(state: AgentState) -> Literal["fitness_merge", "yoga_creator", "hitl_yoga"]:
    retries = state.get("domain_retries", {}).get("Yoga", 0)
    if "Yoga" not in state.get("current_rejections", {}):
        return "fitness_merge"
    if retries >= 2:
        return "hitl_yoga"
    return "yoga_creator"

def check_calis_status(state: AgentState) -> Literal["fitness_merge", "calisthenics_creator", "hitl_calis"]:
    retries = state.get("domain_retries", {}).get("Calisthenics", 0)
    if "Calisthenics" not in state.get("current_rejections", {}):
        return "fitness_merge"
    if retries >= 2:
        return "hitl_calis"
    return "calisthenics_creator"

def check_nutrition_status(state: AgentState) -> Literal["plan_merge", "nutrition_creator", "hitl_nutrition"]:
    retries = state.get("domain_retries", {}).get("Nutrition", 0)
    if "Nutrition" not in state.get("current_rejections", {}):
        return "plan_merge"
    if retries >= 2:
        return "hitl_nutrition"
    return "nutrition_creator"

def fitness_merge_node(state: AgentState) -> dict:
    """Aggregates individual approved fitness sessions into the global fitness_plan."""
    current_plan = state.get("fitness_plan", FitnessPlan())
    
    # TypedDict requires us to update the specific fields or return the replaced object
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
    """Sync point for both fitness and nutrition before pre-release gate."""
    return {}

def pre_release_gate(state: AgentState) -> dict:
    """
    Dummy node before the interrupt. 
    LangGraph will pause execution BEFORE this node if configured, 
    or we can pause before END.
    """
    return {}

def hitl_dummy_node(state: AgentState) -> dict:
    """Nodes representing manual human escalation logic."""
    return {}

def build_graph():
    builder = StateGraph(AgentState)
    
    builder.add_node("orchestrator", orchestrator_node)
    
    # Creators
    builder.add_node("gym_creator", gym_creator_node)
    builder.add_node("yoga_creator", yoga_creator_node)
    builder.add_node("calisthenics_creator", calisthenics_creator_node)
    builder.add_node("nutrition_creator", nutrition_creator_node)
    
    # Checkers
    builder.add_node("gym_checker", gym_checker_node)
    builder.add_node("yoga_checker", yoga_checker_node)
    builder.add_node("calisthenics_checker", calisthenics_checker_node)
    builder.add_node("nutrition_checker", nutrition_checker_node)
    
    # HITL Escalations
    builder.add_node("hitl_gym", hitl_dummy_node)
    builder.add_node("hitl_yoga", hitl_dummy_node)
    builder.add_node("hitl_calis", hitl_dummy_node)
    builder.add_node("hitl_nutrition", hitl_dummy_node)
    
    # Merges & Gates
    builder.add_node("fitness_merge", fitness_merge_node)
    builder.add_node("plan_merge", plan_merge_node)
    builder.add_node("pre_release_gate", pre_release_gate)
    
    # Flow
    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges("orchestrator", route_specialists, 
                                  ["gym_creator", "yoga_creator", "calisthenics_creator", "nutrition_creator"])
    
    # Gym Loop
    builder.add_edge("gym_creator", "gym_checker")
    builder.add_conditional_edges("gym_checker", check_gym_status)
    builder.add_edge("hitl_gym", "fitness_merge")
    
    # Yoga Loop
    builder.add_edge("yoga_creator", "yoga_checker")
    builder.add_conditional_edges("yoga_checker", check_yoga_status)
    builder.add_edge("hitl_yoga", "fitness_merge")
    
    # Calisthenics Loop
    builder.add_edge("calisthenics_creator", "calisthenics_checker")
    builder.add_conditional_edges("calisthenics_checker", check_calis_status)
    builder.add_edge("hitl_calis", "fitness_merge")
    
    # Nutrition Loop
    builder.add_edge("nutrition_creator", "nutrition_checker")
    builder.add_conditional_edges("nutrition_checker", check_nutrition_status)
    builder.add_edge("hitl_nutrition", "plan_merge")
    
    # Merging
    builder.add_edge("fitness_merge", "plan_merge")
    builder.add_edge("plan_merge", "pre_release_gate")
    builder.add_edge("pre_release_gate", END)
    
    # Persistence: Use local sqlite for demo purposes
    conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
    memory = SqliteSaver(conn)
    
    # Compile Graph with Interrupt before pre_release_gate
    graph = builder.compile(checkpointer=memory, interrupt_before=["pre_release_gate", "hitl_gym", "hitl_yoga", "hitl_calis", "hitl_nutrition"])
    
    return graph
