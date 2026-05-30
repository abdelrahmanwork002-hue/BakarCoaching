"""
Tracking Coach Agent
====================
Runs AFTER all fitness and nutrition plans are merged.
Generates a TrackingStrategy using JSON mode (more reliable than tool-calling
for complex nested schemas on Groq).
Loads and enforces the subjective check-in indices, somatic calibration rules, 
and Master Accountability Dashboard rules.
Model: Groq Llama 3.3 70B
"""
import os
import json
import time
from langchain_core.messages import HumanMessage, SystemMessage
from src.agents.base import get_llm

from src.state import AgentState, TrackingStrategy


def _load_followup_guidelines() -> str:
    """Loads all Follow-up and Calibration markdown guidelines from 'md files' directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    md_dir = os.path.join(base_dir, "md files")
    guidelines = ""
    try:
        for fname in ["01_followup_client_checkin.md", "02_followup_adaptive_calibration.md", "03_followup_accountability_dashboard.md"]:
            path = os.path.join(md_dir, fname)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    guidelines += f"\n--- {fname} ---\n" + f.read() + "\n"
    except Exception as e:
        print(f"Error loading followup guidelines: {e}")
    return guidelines


def tracking_coach_node(state: AgentState) -> dict:
    """
    Tracking Coach node. Synthesizes the complete plan into an actionable TrackingStrategy.
    Uses JSON mode for reliable structured output and enforces the follow-up guidelines.
    """
    llm_json = get_llm(temperature=0.1, json_mode=True)

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

    directives_summary = ""
    if macro and macro.specialist_directives:
        directives_summary = "\n".join(
            f"  - {k}: {v}" for k, v in macro.specialist_directives.items()
        )

    # Load follow-up guidelines
    followup_guidelines = _load_followup_guidelines()

    system_msg = SystemMessage(content="""You are the master Tracking Coach — a world-class progress tracking and somatic calibration specialist.
You MUST respond with a single valid JSON object and NOTHING else — no markdown, no explanation outside the JSON.
The JSON must have EXACTLY these 5 keys:
{
  "weekly_checkin_metrics": ["string", ...],
  "implementation_tips": ["string", ...],
  "milestone_targets": ["string", ...],
  "red_flag_warnings": ["string", ...],
  "coach_notes": "string"
}""")

    user_msg = HumanMessage(content=f"""Generate a comprehensive TrackingStrategy JSON for this client.
You MUST strictly base your metrics, warnings, thresholds, and tips on the Follow-up Specialist Guidelines provided below.

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
- Targets: {macro.target_calories if macro else 'N/A'} kcal | P:{macro.protein_g if macro else 'N/A'}g C:{macro.carbs_g if macro else 'N/A'}g F:{macro.fats_g if macro else 'N/A'}g
- Hydration: {nutrition_plan.hydration_target_L if nutrition_plan else 'N/A'} L/day
{meal_summary}

FOLLOW-UP SPECIALIST GUIDELINES:
---
{followup_guidelines}
---

Your generated JSON fields must follow these exact instructions:

1. "weekly_checkin_metrics": Include 6-8 items reflecting the Weekly Check-In Metadata and Subjective Bio-Feedback Indicators from the guidelines:
   - Bodyweight checks (including tracking weight delta vs last week).
   - Compliance logging (Nutrition, Training, Hydration target adherence out of 7 days).
   - Subjective biofeedback rating metrics (Sleep Quality 1-5, Energy Levels 1-5, Muscle Soreness/DOMS 1-5, Joint Integrity 1-5, Digestive Comfort 1-5).
   - Morning resting recovery pulse (Baseline vs Current).
   - Performance checks (Strength velocity and Yoga flexibility stance depth).

2. "implementation_tips": Include 7-10 practical tips mapping to the client's training days and incorporating the **Direct Symptom-to-Somatic Adaptation Rules**:
   - High sleep loss & DOMS modification: Drop 1 working set from Gym Tier A and add 15 minutes of passive Yin yoga recovery if sleep is <= 2 AND soreness is >= 4 over 3 consecutive days.
   - Localized Joint Pain: Swap heavy calisthenics floor holds for parallel bars or forearm modifications, and drop barbell pressing for 1 week if joint integrity is <= 2 (wrists or shoulders).
   - Severe Hunger: Replace 50% of fast-acting starches with low-glycemic, high-volume fibrous vegetables if hunger rating hits 5 on a fat loss deficit track.
   - Weight Stall Corrections: Drop carbs by 0.25g * kg for fat loss stalling >14 days; advance daily calories by +150 kcal for mass gain stalling >14 days.

3. "milestone_targets": Include 6-10 progressive targets (format "Week N: ...") detailing the **4-Week Progress Evaluation Index** zones:
   - Category Alpha: Score >= 85% (automatic rollover, retain baseline, generate positive reinforcement).
   - Category Beta: Score 60% - 84% (trigger micro-calibration updates, adjust training/meal schedules).
   - Category Gamma: Score < 60% (hard state interrupt, request complete manual overview from Senior Orchestrator).

4. "red_flag_warnings": Include 5-8 highly specific warnings based on the Systemic Performance Telemetry Scorecard danger zones:
   - Morning resting HR rising >6 bpm over 4 consecutive days.
   - Weekly compliance <= 4 marked days.
   - Sleep score <= 2 or Joint integrity <= 2.
   - 3 consecutive drops in lift capacity or volume loads.
   - Missing more than 2 entries on the Excel or App tracking spreadsheet (which prompts automated support alerts).

5. "coach_notes": Synthesize the program in 2-3 inspiring paragraphs. Detail how their progress updates sync bidirectionally via Excel spreadsheet columns directly into the state graph (progress_history), and explain the Alpha/Beta/Gamma compliance routing mechanics.
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
                # Premium fallback aligned with the exact somatic/scorecard guidelines
                print(f"[Tracking Coach] Failed after 3 attempts: {err[:200]}")
                
                # Check goal type for stall correction fallback
                is_fat_loss = profile.primary_goal.lower() in ["weight loss", "fat loss", "recomposition"]
                stall_action = "Drop carbs by $0.25\\text{g} \\times \\text{kg}$" if is_fat_loss else "Advance daily calories by +150 kcal"
                hunger_action = "Replace 50% fast starches with high-volume fibrous vegetables if hunger hits 5" if is_fat_loss else "Monitor satiety and adjust meal sizes"
                
                return {"tracking_strategy": TrackingStrategy(
                    weekly_checkin_metrics=[
                        "Bodyweight checks (kg) — compare morning weight delta vs last week",
                        "Training compliance — target >= 6 out of 7 days completed",
                        "Nutrition & Hydration compliance — log daily calories, macros, and hydration",
                        "Biofeedback Scores (1-5) — Sleep Quality, Energy, DOMS, Joint Integrity, Digestion",
                        "Morning resting heart rate (bpm) — check for nervous system fatigue",
                        "Performance benchmarks — strength velocity (dead-hang pulls/barbell lifts) & yoga depth"
                    ],
                    implementation_tips=[
                        "Systemic Sleep & Soreness Override: If sleep score <= 2 AND DOMS >= 4 for 3 days, drop 1 set from Gym Tier A and add 15 mins Yin yoga.",
                        "Localized Joint Pain Override: If wrist/shoulder integrity falls <= 2, swap to parallel bars/forearms and drop barbell pressing for 1 week.",
                        f"Satiety & Hunger Override: {hunger_action}.",
                        f"Weight Stall Correction: If weight stalls > 14 days, {stall_action}.",
                        "Prioritize your active recovery days to keep systemic fatigue low and joint integrity high."
                    ],
                    milestone_targets=[
                        "Category Alpha Gate (Score >= 85%): Rollover to next week with positive reinforcement and baseline parameters.",
                        "Category Beta Gate (Score 60% - 84%): Trigger micro-calibration and schedule adjustment loops.",
                        "Category Gamma Gate (Score < 60%): Hard state interrupt (lock plan progression and trigger manual Senior Coach overview)."
                    ],
                    red_flag_warnings=[
                        "Danger Zone: Morning resting heart rate rising >6 bpm over 4 consecutive days.",
                        "Danger Zone: Weekly compliance falling <= 4 marked days.",
                        "Danger Zone: 3 consecutive drops in lift capacity or strength volume loads.",
                        "Somatic Danger: Subjective Sleep Score <= 2 or Joint Integrity <= 2.",
                        "Spreadsheet Logging: Missing more than 2 entries in your Excel sheet triggers automated support notifications."
                    ],
                    coach_notes=(
                        f"Your program is scientifically structured to balance mechanical tension, movement mastery, and metabolic timing. "
                        f"Consistent progression is managed through bidirectional tracking: your uploads sync directly into your progress history, "
                        f"allowing our real-time calibration engine to apply the 4-week accountability evaluation gates. "
                        f"Category Alpha targets ensure smooth rollover, while Beta allows for micro-calibrations. "
                        f"If compliance slips into Category Gamma, a state interrupt is triggered for safety. Stay consistent and log your telemetry!"
                    )
                )}
