"""
Tracking Coach Agent
====================
Runs AFTER all fitness and nutrition plans are merged.
Performs a holistic review of the complete plan and generates a TrackingStrategy:
- Weekly check-in metrics the client should track
- Implementation tips (which days to train, how to schedule sessions)
- Progressive milestone targets (week-by-week goals)
- Red flag warnings (injury signals or safety concerns)
- Overall coach notes synthesizing the full program

Modify this file to change what the Tracking Coach recommends or monitors.
Model: Google Gemini Flash (analytical, detail-oriented synthesis)
"""
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.state import AgentState, TrackingStrategy


def tracking_coach_node(state: AgentState) -> dict:
    """
    Tracking Coach node.
    Synthesizes the complete fitness + nutrition plan into an actionable
    TrackingStrategy the client can follow for progress monitoring.
    """
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
    llm_structured = llm.with_structured_output(TrackingStrategy)

    profile = state.get("user_profile")
    fitness_plan = state.get("fitness_plan")
    nutrition_plan = state.get("nutrition_plan")
    macro = state.get("macro_strategy")

    # Summarize the fitness plan for context
    gym_days = [s.day for s in (fitness_plan.gym_sessions or [])]
    yoga_days = [s.day for s in (fitness_plan.yoga_sessions or [])]
    cali_days = [s.day for s in (fitness_plan.calisthenics_sessions or [])]

    total_sessions = len(gym_days) + len(yoga_days) + len(cali_days)
    total_weekly_duration = sum(
        s.duration_mins
        for domain_sessions in [
            fitness_plan.gym_sessions or [],
            fitness_plan.yoga_sessions or [],
            fitness_plan.calisthenics_sessions or []
        ]
        for s in domain_sessions
    )

    meal_summary = ""
    if nutrition_plan and nutrition_plan.daily_meals:
        meal_summary = "\n".join(
            f"  - {m.meal_name}: {m.calories} kcal, P:{m.protein_g}g, C:{m.carbs_g}g, F:{m.fats_g}g"
            for m in nutrition_plan.daily_meals
        )

    directives_summary = "\n".join(
        f"  - {domain}: {directive}"
        for domain, directive in (macro.specialist_directives or {}).items()
    )

    prompt = f"""You are the Tracking Coach — a world-class fitness progress specialist.

Your job is to review a client's complete fitness and nutrition plan and generate a practical
TrackingStrategy that will help them stay on track, measure progress, and avoid injury.

CLIENT PROFILE:
- Age: {profile.age} | Weight: {profile.weight_kg}kg → Target: {profile.target_weight_kg}kg
- Goal: {profile.primary_goal} | Experience: {profile.experience_level}
- Injuries/Limitations: {', '.join(profile.injuries) if profile.injuries else 'None'}

SENIOR COACH DIRECTIVES:
{directives_summary if directives_summary else '  Not specified'}

APPROVED FITNESS PLAN SUMMARY:
- Gym Sessions: {gym_days if gym_days else 'None'}
- Yoga Sessions: {yoga_days if yoga_days else 'None'}
- Calisthenics Sessions: {cali_days if cali_days else 'None'}
- Total Weekly Sessions: {total_sessions}
- Total Weekly Training Time: ~{total_weekly_duration} minutes

APPROVED NUTRITION PLAN:
- Daily Target: {macro.target_calories} kcal | P:{macro.protein_g}g | C:{macro.carbs_g}g | F:{macro.fats_g}g
- Meals:
{meal_summary if meal_summary else '  Not available'}
- Hydration Target: {nutrition_plan.hydration_target_L if nutrition_plan else 'N/A'} liters/day

YOUR TASK — Generate a TrackingStrategy with:

1. weekly_checkin_metrics (5-8 items):
   Specific measurable metrics the client should log every week.
   Examples: "Body weight (kg) — weigh in same time each morning", "Workout adherence (sessions completed / planned)"

2. implementation_tips (6-10 items):
   Practical scheduling and lifestyle tips for successfully implementing this specific plan.
   Reference the actual training days and session types from the plan above.

3. milestone_targets (8-12 items):
   Week-by-week and month-by-month progressive targets.
   Be specific and realistic for this client's goal and starting point.
   Format: "Week 2: [specific target]", "Month 1: [specific target]"

4. red_flag_warnings (4-8 items):
   Specific injury or safety signals this client should watch for given their profile.
   Reference their listed injuries/limitations directly.

5. coach_notes (2-3 paragraphs):
   A motivating, synthesizing overview of the program strategy, key priorities,
   and how the fitness and nutrition plans work together for this client's goal.
"""

    tracking_strategy = llm_structured.invoke([HumanMessage(content=prompt)])
    return {"tracking_strategy": tracking_strategy}
