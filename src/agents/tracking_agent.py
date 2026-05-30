"""
Tracking Coach Agent
====================
Runs AFTER all fitness and nutrition plans are merged.
Generates a TrackingStrategy using JSON mode (more reliable than tool-calling
for complex nested schemas on Groq).

Modify this file to change what the Tracking Coach recommends or monitors.
Model: Groq Llama 3.3 70B
"""
import json
import time
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.state import AgentState, TrackingStrategy


def tracking_coach_node(state: AgentState) -> dict:
    """
    Tracking Coach node. Synthesizes the complete plan into an actionable TrackingStrategy.
    Uses JSON mode for reliable structured output.
    """
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)
    llm_json = llm.bind(response_format={"type": "json_object"})

    profile = state.get("user_profile")
    fitness_plan = state.get("fitness_plan")
    nutrition_plan = state.get("nutrition_plan")
    macro = state.get("macro_strategy")

    gym_days  = [s.day for s in (fitness_plan.gym_sessions or [])]
    yoga_days = [s.day for s in (fitness_plan.yoga_sessions or [])]
    cali_days = [s.day for s in (fitness_plan.calisthenics_sessions or [])]
    total_sessions = len(gym_days) + len(yoga_days) + len(cali_days)
    total_mins = sum(
        s.duration_mins
        for sessions in [fitness_plan.gym_sessions or [], fitness_plan.yoga_sessions or [], fitness_plan.calisthenics_sessions or []]
        for s in sessions
    )

    meal_summary = ""
    if nutrition_plan and nutrition_plan.daily_meals:
        meal_summary = "\n".join(
            f"  - {m.meal_name}: {m.calories} kcal P:{m.protein_g}g C:{m.carbs_g}g F:{m.fats_g}g"
            for m in nutrition_plan.daily_meals
        )

    directives_summary = "\n".join(
        f"  - {k}: {v}" for k, v in (macro.specialist_directives or {}).items()
    )

    system_msg = SystemMessage(content="""You are the Tracking Coach — a world-class fitness progress specialist.
You MUST respond with a single valid JSON object and NOTHING else — no markdown, no explanation.
The JSON must have EXACTLY these 5 keys:
{
  "weekly_checkin_metrics": ["string", ...],
  "implementation_tips": ["string", ...],
  "milestone_targets": ["string", ...],
  "red_flag_warnings": ["string", ...],
  "coach_notes": "string"
}""")

    user_msg = HumanMessage(content=f"""Generate a TrackingStrategy JSON for this client.

CLIENT PROFILE:
- Age: {profile.age} | Weight: {profile.weight_kg}kg → Target: {profile.target_weight_kg}kg
- Goal: {profile.primary_goal} | Experience: {profile.experience_level}
- Injuries: {', '.join(profile.injuries) if profile.injuries else 'None'}

SENIOR COACH DIRECTIVES:
{directives_summary or '  Not specified'}

FITNESS PLAN:
- Gym: {gym_days or 'None'} | Yoga: {yoga_days or 'None'} | Calisthenics: {cali_days or 'None'}
- Total: {total_sessions} sessions / ~{total_mins} mins/week

NUTRITION:
- Targets: {macro.target_calories} kcal | P:{macro.protein_g}g C:{macro.carbs_g}g F:{macro.fats_g}g
- Hydration: {nutrition_plan.hydration_target_L if nutrition_plan else 'N/A'} L/day
{meal_summary}

Required in your JSON:
- weekly_checkin_metrics: 5-8 measurable weekly tracking items
- implementation_tips: 6-10 practical scheduling tips referencing the actual training days
- milestone_targets: 8-12 progressive targets (format "Week N: ..." or "Month N: ...")
- red_flag_warnings: 4-8 safety signals specific to this client's injuries
- coach_notes: 2-3 paragraph motivating synthesis of the program
""")

    for attempt in range(3):
        try:
            response = llm_json.invoke([system_msg, user_msg])
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            data = json.loads(raw)
            tracking_strategy = TrackingStrategy(**data)
            return {"tracking_strategy": tracking_strategy}
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit" in err.lower():
                wait = (attempt + 1) * 15
                print(f"[Tracking Coach] Rate limit — waiting {wait}s...")
                time.sleep(wait)
            elif attempt >= 2:
                # Final fallback — return a minimal but valid strategy
                print(f"[Tracking Coach] Failed after 3 attempts: {err[:200]}")
                return {"tracking_strategy": TrackingStrategy(
                    weekly_checkin_metrics=[
                        "Body weight (kg) — same time each morning",
                        "Sessions completed vs planned",
                        "Daily protein intake (g)",
                        "Sleep quality (hours)",
                        "Energy level (1-10)"
                    ],
                    implementation_tips=[
                        "Follow the training schedule consistently",
                        "Prepare meals in advance to hit macro targets",
                        "Prioritize sleep for recovery",
                        "Warm up properly before every session",
                        "Stay hydrated — carry a water bottle"
                    ],
                    milestone_targets=[
                        "Week 2: Complete all scheduled sessions",
                        "Week 4: Track noticeable strength improvement",
                        "Month 1: Reach first weight milestone",
                        "Month 2: Establish full routine habit"
                    ],
                    red_flag_warnings=[
                        "Stop immediately if any acute pain occurs",
                        "Rest if excessively fatigued or unwell",
                        "Consult a professional if injuries worsen"
                    ],
                    coach_notes=(
                        "Your plan is well-structured and tailored to your goals. "
                        "Consistency is the most important factor in your success. "
                        "Track your progress weekly and adjust as needed."
                    )
                )}
