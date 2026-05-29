import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Ensure src is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph import build_graph
from src.state import UserProfile, AgentState, FitnessPlan
from src.excel_engine import export_plans_to_excel
from langgraph.types import Command

def run():
    print("Building Graph...")
    graph = build_graph()
    
    # Thread config for sqlite checkpointer
    config = {"configurable": {"thread_id": "test_user_001"}}
    
    # Mock Initial State
    initial_profile = UserProfile(
        user_id="user_123",
        age=30,
        weight_kg=85.0,
        target_weight_kg=78.0,
        activity_level="Moderate",
        primary_goal="Weight Loss and Muscle Gain",
        experience_level="Intermediate",
        injuries=["Mild lower back pain"]
    )
    
    initial_state = AgentState(
        user_profile=initial_profile,
        macro_strategy=None,
        fitness_plan=FitnessPlan(),
        nutrition_plan=None,
        validation_logs=[],
        progress_history=[],
        domain_retries={},
        current_rejections={},
        draft_gym=None,
        draft_yoga=None,
        draft_calisthenics=None,
        draft_nutrition=None,
        approved_gym=None,
        approved_yoga=None,
        approved_calisthenics=None
    )
    
    print("--- Starting Execution ---")
    
    # Run until interrupt or end
    # Note: Requires GROQ_API_KEY and GOOGLE_API_KEY environment variables to actually run.
    try:
        for event in graph.stream(initial_state, config=config, stream_mode="values"):
            pass
    except Exception as e:
        print(f"Graph execution stopped or errored (API keys missing?): {e}")
        return
        
    while True:
        state_snapshot = graph.get_state(config)
        next_node = state_snapshot.next
        
        if not next_node:
            print("Graph execution finished.")
            break
            
        if "pre_release_gate" in next_node:
            print("\nWaiting at pre_release_gate. Simulating Admin Approval...")
            for event in graph.stream(Command(resume="admin_approved"), config=config, stream_mode="values"):
                pass
            
            final_state = graph.get_state(config).values
            print("\n--- Generating Final Excel Output ---")
            filepath = export_plans_to_excel(
                fitness_plan=final_state.get("fitness_plan"),
                nutrition_plan=final_state.get("nutrition_plan"),
                filepath="Final_Client_Plan.xlsx"
            )
            print(f"Success! Excel exported to {filepath}")
            break
            
        else:
            print(f"\nGraph paused at: {next_node}. Simulating admin HITL resolution...")
            for event in graph.stream(Command(resume="admin_override"), config=config, stream_mode="values"):
                pass

if __name__ == "__main__":
    run()
