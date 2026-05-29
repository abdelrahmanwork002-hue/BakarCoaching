"""
Orchestrator Agent — Senior Head Coach
=======================================
Analyzes the client profile and outputs:
1. Daily macro targets (calories, protein, carbs, fats)
2. A high-level training split description
3. specialist_directives: a dict mapping each specialist agent to activate
   (Gym, Yoga, Calisthenics) to a specific, focused coaching mandate.

Modify this file to change how the Senior Coach assigns agents and directives.
Model: Groq Llama 3.3 70B (fast, strategic reasoning)
"""
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from src.state import AgentState, MacroStrategy


def orchestrator_node(state: AgentState) -> dict:
    """
    Senior Head Coach node.
    Reads the user profile and produces a MacroStrategy with specialist_directives.
    Each directive gives the downstream specialist agent a targeted coaching mandate.
    """
    user_profile = state.get("user_profile")
    if not user_profile:
        raise ValueError("UserProfile is missing from state.")

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    llm_structured = llm.with_structured_output(MacroStrategy)

    prompt = f"""You are the Senior Head Coach and Orchestrator for a premium AI fitness platform.

Your job is to analyze the client profile below and produce a comprehensive macro strategy that:
1. Sets precise daily caloric and macronutrient targets
2. Defines a high-level weekly training split
3. Assigns specialist_directives — a dictionary that activates ONLY the relevant training specialists
   and gives each one a specific, targeted coaching mandate tailored to this client's goals and limitations.

CLIENT PROFILE:
- Age: {user_profile.age}
- Current Weight: {user_profile.weight_kg}kg → Target Weight: {user_profile.target_weight_kg}kg
- Activity Level: {user_profile.activity_level}
- Primary Goal: {user_profile.primary_goal}
- Experience Level: {user_profile.experience_level}
- Injuries/Limitations: {', '.join(user_profile.injuries) if user_profile.injuries else 'None'}

SPECIALIST SELECTION RULES:
- Include "Gym" if the client would benefit from equipment-based resistance training
- Include "Yoga" if the client would benefit from mobility, flexibility, or active recovery (especially if injuries present)
- Include "Calisthenics" if the client would benefit from bodyweight strength and skill work
- You may include 1, 2, or all 3 specialists based on the client's needs
- You MUST NOT include a specialist if it is not appropriate for this client

For each specialist you include, write a specific directive (2-4 sentences) that:
- States the primary training focus for that specialist
- References any injury modifications or contraindications
- Aligns with the overall macro strategy and caloric goals

Example specialist_directives format:
{{
  "Gym": "Focus on compound lower body movements (squats, deadlifts) and push/pull hypertrophy. Avoid overhead pressing and any exercises that load the lumbar spine. Target 4 sessions per week with progressive overload.",
  "Yoga": "Prioritize lumbar decompression, hip flexor mobility, and thoracic extension. Include restorative poses for recovery between gym sessions. 2-3 sessions per week."
}}

Output the complete MacroStrategy now.
"""

    macro_strategy = llm_structured.invoke([HumanMessage(content=prompt)])
    return {"macro_strategy": macro_strategy}
