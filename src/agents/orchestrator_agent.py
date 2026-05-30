"""
Orchestrator Agent — Senior Head Coach
=======================================
Analyzes the client profile and outputs a MacroStrategy with specialist_directives.
Loads and enforces the senior integration mechanics, Master Macrocycle Frameworks,
and somatic cross-check screenings.
"""
import os
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from src.state import AgentState, MacroStrategy

_DOMAIN = "Orchestrator"

def _load_senior_guidelines() -> str:
    """Loads all Senior Orchestrator markdown guidelines from 'md files' directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    md_dir = os.path.join(base_dir, "md files")
    guidelines = ""
    try:
        for fname in ["01_senior_orchestrator_assessment.md", "02_senior_integration_mechanics.md", "03_senior_macrocycle_framework.md"]:
            path = os.path.join(md_dir, fname)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    guidelines += f"\n--- {fname} ---\n" + f.read() + "\n"
    except Exception as e:
        print(f"Error loading senior guidelines: {e}")
    return guidelines

def orchestrator_node(state: AgentState) -> dict:
    """
    Senior Head Coach and Orchestrator node.
    Reads the user profile and produces a MacroStrategy with specialist_directives.
    Integrates all dynamic cross-disciplinary intake rules and conflict resolution frameworks.
    """
    user_profile = state.get("user_profile")
    if not user_profile:
        raise ValueError("UserProfile is missing from state.")

    from src.agents.base import get_llm
    llm = get_llm(temperature=0)
    llm_structured = llm.with_structured_output(MacroStrategy)

    # Load Senior Orchestrator guidelines
    senior_guidelines = _load_senior_guidelines()

    prompt = f"""You are the master Senior Head Coach and Orchestrator for a premium AI hybrid fitness and nutrition platform.

Your job is to analyze the client profile below and produce a comprehensive macro strategy that setting daily caloric targets, macronutrients, and high-level training splits.

CLIENT PROFILE:
- Age: {user_profile.age}
- Current Weight: {user_profile.weight_kg}kg → Target Weight: {user_profile.target_weight_kg}kg
- Activity Level: {user_profile.activity_level}
- Primary Goal: {user_profile.primary_goal}
- Experience Level: {user_profile.experience_level}
- Injuries/Limitations: {', '.join(user_profile.injuries) if user_profile.injuries else 'None'}

IMPORTANT — THE CLIENT HAS EXPLICITLY REQUESTED THESE TRAINING TYPES ONLY:
{user_profile.preferred_training_types}

SENIOR INTEGRATION MECHANICS & MACROCYCLE GUIDELINES (MANDATORY):
You MUST strictly follow these cross-disciplinary intake rules, 12-week hybrid macrocycle layouts, and structural conflict resolution matrices:
---
{senior_guidelines}
---

Your outputted MacroStrategy must:
1. Set daily caloric and macronutrient targets. Ensure caloric and macro intakes align with the user's primary goal (e.g. slight surplus for Phase 1 accumulation, high-protein maintenance for Phase 2 intensification, or controlled deficit for Phase 3 recomposition).
2. Set a high-level `training_split` description reflecting the Master 12-Week Hybrid Macrocycle Architecture and the Weekly Integration Timeline (e.g. designating Gym Compound + Calisthenics Pulls, Yoga Vinyasa, CNS Rest, pressing/planche work, and hybrid circuits).
3. Assign `specialist_directives` for ONLY the training types the client explicitly requested (e.g. subset of ['Gym', 'Yoga', 'Calisthenics']). Do not include or omit any requested type.
4. Integrate Conflict Resolution in Directives:
   - Cap overlapping shoulder loading (e.g. if Bench Press and Calisthenics Dips run, cap volumes and mandate 1:1 rear-delt balance).
   - Ensure a 24-hour neural buffer between heavy barbell lifting (Axial loads/Squats/Deadlifts) and Yoga/Calisthenics handstands.
   - For wrist extension fatigue, replace Yoga wrist balance holds with forearm-grounded poses (e.g. Dolphin Pose).
   - Sync metabolic demands (if on aggressive caloric deficit, direct gym reps to lower volume 4-6 reps to maintain strength and protect muscle mass).

Formulate highly custom, detailed coaching mandates for each downstream specialist agent (Gym, Calisthenics, Yoga) as their directives.

Output the complete MacroStrategy now.
"""

    macro_strategy = llm_structured.invoke([HumanMessage(content=prompt)])
    return {"macro_strategy": macro_strategy}
