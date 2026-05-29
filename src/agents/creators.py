from typing import List
from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from src.state import AgentState, WorkoutSession, NutritionPlan

class CreatorOutput(BaseModel):
    sessions: List[WorkoutSession] = Field(description="The planned workout sessions for the week.")

def base_creator_node(state: AgentState, domain: str, focus_prompt: str) -> dict:
    """Base logic for a fitness creator node."""
    llm = ChatGroq(model="llama-3.1-70b-versatile", temperature=0.2)
    llm_with_structured_output = llm.with_structured_output(CreatorOutput)
    
    macro = state.get("macro_strategy")
    profile = state.get("user_profile")
    rejection_feedback = state.get("current_rejections", {}).get(domain, "")
    
    sys_prompt = f"""
    You are the {domain} Specialist.
    User Profile: Goal={profile.primary_goal}, Experience={profile.experience_level}, Injuries={', '.join(profile.injuries) if profile.injuries else 'None'}
    Overall Strategy: {macro.training_split}
    
    Your Focus: {focus_prompt}
    
    Create a weekly regimen (list of sessions) specifically for your domain. 
    """
    
    if rejection_feedback:
        sys_prompt += f"\n\nPREVIOUS SUBMISSION REJECTED. Fix these issues: {rejection_feedback}"
        
    output = llm_with_structured_output.invoke([SystemMessage(content=sys_prompt)])
    
    return {f"draft_{domain.lower()}": output.sessions}

def gym_creator_node(state: AgentState) -> dict:
    return base_creator_node(
        state, 
        "Gym", 
        "Hypertrophy, strength conditioning, and progressive overload using weights."
    )

def yoga_creator_node(state: AgentState) -> dict:
    return base_creator_node(
        state, 
        "Yoga", 
        "Active recovery, mobility, flexibility, and stress regulation."
    )

def calisthenics_creator_node(state: AgentState) -> dict:
    return base_creator_node(
        state, 
        "Calisthenics", 
        "Bodyweight mastery, core stability, and progressions."
    )

def nutrition_creator_node(state: AgentState) -> dict:
    llm = ChatGroq(model="llama-3.1-70b-versatile", temperature=0.1)
    llm_with_structured_output = llm.with_structured_output(NutritionPlan)
    
    macro = state.get("macro_strategy")
    profile = state.get("user_profile")
    rejection_feedback = state.get("current_rejections", {}).get("Nutrition", "")
    
    sys_prompt = f"""
    You are the Head Nutritionist.
    User Profile: Goal={profile.primary_goal}, Weight={profile.weight_kg}kg -> {profile.target_weight_kg}kg.
    Targets: Calories={macro.target_calories}, Protein={macro.protein_g}g, Carbs={macro.carbs_g}g, Fats={macro.fats_g}g.
    
    Create a daily meal structure (Breakfast, Lunch, Dinner, Snacks) meeting these exact targets.
    Also define a hydration target.
    """
    
    if rejection_feedback:
        sys_prompt += f"\n\nPREVIOUS SUBMISSION REJECTED. Fix these issues: {rejection_feedback}"
        
    output = llm_with_structured_output.invoke([SystemMessage(content=sys_prompt)])
    return {"draft_nutrition": output}
