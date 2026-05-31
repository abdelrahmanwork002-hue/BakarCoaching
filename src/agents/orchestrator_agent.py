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
        for fname in ["02_senior_integration_mechanics.md"]:
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

    from src.agents.base import get_llm, invoke_json_mode
    llm = get_llm(temperature=0, json_mode=True)

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
1. Set daily caloric and macronutrient targets. Ensure caloric and macro intakes align with the user's primary goal.
2. Set a high-level `training_split` description reflecting the Master 12-Week Hybrid Macrocycle Architecture.
3. Assign `specialist_directives` for EXACTLY these training types: {user_profile.preferred_training_types}. 
   DO NOT include any directives for domains not in this list.
4. Integrate Conflict Resolution in Directives as per the guidelines.

Formulate highly custom, detailed coaching mandates for each downstream specialist agent ({', '.join(user_profile.preferred_training_types)}) as their directives.

Output the complete MacroStrategy now.
"""

    macro_strategy = invoke_json_mode(llm, prompt, MacroStrategy)
    
    # Programmatic enforce: remove any hallucinated domains that the user didn't request
    allowed_domains = set(user_profile.preferred_training_types)
    macro_strategy.specialist_directives = {
        k: v for k, v in macro_strategy.specialist_directives.items() if k in allowed_domains
    }
    
    # Ensure at least one fallback if LLM failed to output any valid ones
    if not macro_strategy.specialist_directives and allowed_domains:
        first_domain = list(allowed_domains)[0]
        macro_strategy.specialist_directives[first_domain] = "Follow standard progressive overload and safety protocols."

    return {"macro_strategy": macro_strategy}
