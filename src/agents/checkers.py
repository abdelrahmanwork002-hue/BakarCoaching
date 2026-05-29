from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from src.state import AgentState, ValidationLog

class CheckerOutput(BaseModel):
    is_approved: bool = Field(description="True if the plan meets all criteria, False if it needs revision.")
    feedback: str = Field(description="Detailed feedback or critique if rejected. Empty if approved.")

def base_checker_node(state: AgentState, domain: str) -> dict:
    """Base logic for a fitness/nutrition checker node."""
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    llm_with_structured_output = llm.with_structured_output(CheckerOutput)
    
    profile = state.get("user_profile")
    draft = state.get(f"draft_{domain.lower()}")
    
    if not draft:
        raise ValueError(f"Draft for {domain} not found in state.")
        
    sys_prompt = f"""
    You are the Senior Safety & Efficacy Auditor.
    Evaluate the following {domain} draft plan against the user's profile and constraints.
    
    User Profile:
    - Goal: {profile.primary_goal}
    - Experience: {profile.experience_level}
    - Injuries/Limitations: {', '.join(profile.injuries) if profile.injuries else 'None'}
    
    Draft Plan:
    {draft}
    
    Strict Criteria:
    - Must not aggravate any listed injuries.
    - Must be appropriate for the user's experience level.
    - If Nutrition, macro targets must closely match the requested limits.
    
    If the plan is safe and effective, approve it. If not, reject it and provide specific, actionable feedback for the creator.
    """
    
    output = llm_with_structured_output.invoke([SystemMessage(content=sys_prompt)])
    
    # State Updates
    current_rejections = state.get("current_rejections", {})
    domain_retries = state.get("domain_retries", {})
    
    current_attempt = domain_retries.get(domain, 0)
    
    log = ValidationLog(
        domain=domain,
        provider_creator="Groq",
        provider_checker="Google",
        status="Approved" if output.is_approved else "Rejected",
        feedback=output.feedback,
        attempt=current_attempt + 1
    )
    
    updates = {
        "validation_logs": [log]
    }
    
    if output.is_approved:
        # Clear rejection for this domain
        new_rejections = current_rejections.copy()
        if domain in new_rejections:
            del new_rejections[domain]
        updates["current_rejections"] = new_rejections
        
        # If fitness, append to fitness plan
        if domain != "Nutrition":
            updates[f"approved_{domain.lower()}"] = draft
        else:
            updates["nutrition_plan"] = draft
    else:
        # Increment retry and set rejection message
        new_retries = domain_retries.copy()
        new_retries[domain] = current_attempt + 1
        updates["domain_retries"] = new_retries
        
        new_rejections = current_rejections.copy()
        new_rejections[domain] = output.feedback
        updates["current_rejections"] = new_rejections
        
    return updates

def gym_checker_node(state: AgentState) -> dict:
    return base_checker_node(state, "Gym")

def yoga_checker_node(state: AgentState) -> dict:
    return base_checker_node(state, "Yoga")

def calisthenics_checker_node(state: AgentState) -> dict:
    return base_checker_node(state, "Calisthenics")

def nutrition_checker_node(state: AgentState) -> dict:
    return base_checker_node(state, "Nutrition")
