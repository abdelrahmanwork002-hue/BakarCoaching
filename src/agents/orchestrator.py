from langchain_core.messages import SystemMessage, HumanMessage
from src.state import AgentState, MacroStrategy
from src.agents.base import get_llm, _invoke_with_retry

def orchestrator_node(state: AgentState) -> dict:
    """
    The Senior Orchestrator Agent.
    Analyzes the user profile, sets macro-targets, and determines the routing to sub-specialists.
    """
    user_profile = state.get("user_profile")
    if not user_profile:
        raise ValueError("UserProfile is missing from state.")
        
    # Use the centralized LLM factory (llama-3.1-8b-instant, max_tokens=1500)
    llm = get_llm(temperature=0)

    # Bind the tool to enforce output structure
    llm_with_structured_output = llm.with_structured_output(MacroStrategy)
    
    prompt = f"""
    You are the Senior Trainer and Orchestrator for a premium fitness and nutrition platform.
    Analyze the following user profile and determine the high-level macro strategy.
    
    User Profile:
    - Age: {user_profile.age}
    - Weight: {user_profile.weight_kg}kg
    - Target Weight: {user_profile.target_weight_kg}kg
    - Activity Level: {user_profile.activity_level}
    - Primary Goal: {user_profile.primary_goal}
    - Experience Level: {user_profile.experience_level}
    - Injuries/Limitations: {', '.join(user_profile.injuries) if user_profile.injuries else 'None'}
    
    Determine the daily caloric targets, macronutrient breakdown in grams, a high-level training split, 
    and output a list of exactly which specialist agents are needed. 
    Valid specialists to route to are: "Gym", "Yoga", "Calisthenics".
    (e.g., if the user wants strength and flexibility, output ["Gym", "Yoga"]).
    """
    
    macro_strategy = llm_with_structured_output.invoke([SystemMessage(content=prompt)])
    
    return {"macro_strategy": macro_strategy}
