"""
Gym Specialist Agent
====================
Contains the Creator, Modifier, and Checker nodes for the Gym domain.
Loads and enforces the strength intake, compound progression trees, RPE scales, and hypertrophy splits.
"""
import os
import json
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from src.state import AgentState, ValidationLog
from src.agents.base import CreatorOutput, CheckerOutput, _invoke_with_retry, EXERCISE_FIELDS_INSTRUCTION, get_llm

_DOMAIN = "Gym"

def _load_gym_guidelines() -> str:
    """Loads all gym-specific markdown documents from 'md files' directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    md_dir = os.path.join(base_dir, "md files")
    guidelines = ""
    try:
        for fname in ["02_gym_progression_matrices.md", "03_gym_routine_framework.md"]:
            path = os.path.join(md_dir, fname)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    guidelines += f"\n--- {fname} ---\n" + f.read() + "\n"
    except Exception as e:
        print(f"Error loading gym guidelines: {e}")
    return guidelines

def _load_gym_creator_guidelines() -> str:
    """Loads only the core routine template for the Gym creator prompt to save tokens."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    md_dir = os.path.join(base_dir, "md files")
    guidelines = ""
    try:
        for fname in ["03_gym_routine_framework.md"]:
            path = os.path.join(md_dir, fname)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    guidelines += f"\n--- {fname} ---\n" + f.read() + "\n"
    except Exception as e:
        print(f"Error loading gym creator guidelines: {e}")
    return guidelines

def gym_creator_node(state: AgentState) -> dict:
    """
    Creates the initial Gym workout plan based on the Senior Coach's directive,
    strictly adhering to strength intakes, compound progression matrices, and hypertrophy routines.
    """
    llm = get_llm(temperature=0.2, json_mode=True)

    profile = state.get("user_profile")
    macro = state.get("macro_strategy")
    directive = macro.specialist_directives.get(
        _DOMAIN,
        "Design a balanced hypertrophy and strength program using compound and isolation exercises."
    )

    # Load and filter exercise library
    from src.exercise_library import load_and_filter_exercises
    domain_exercises = load_and_filter_exercises(_DOMAIN, profile.experience_level)

    library_text = ""
    for ex in domain_exercises:
        library_text += f"- NAME: {ex.name}\n"
        library_text += f"  DESCRIPTION: {ex.description}\n"
        library_text += f"  LEVELS: {', '.join(ex.levels)}\n"
        library_text += f"  TARGETED MUSCLES: {', '.join(ex.targeted_muscles)}\n"
        focus_strs = [f"{m} ({'/'.join(focs)})" for m, focs in ex.muscle_focus.items()]
        library_text += f"  FOCUS: {', '.join(focus_strs)}\n"
        library_text += f"  DEMO URL: {ex.demo_url}\n"
        if ex.next_level_progressions:
            library_text += f"  PROGRESSIONS TO: {', '.join(ex.next_level_progressions)}\n"
        library_text += "\n"

    # Load custom Gym guidelines
    gym_guidelines = _load_gym_creator_guidelines()

    prompt = f"""You are the master Gym Specialist Creator Agent.
    
USER PROFILE:
- Goal: {profile.primary_goal}
- Experience: {profile.experience_level}
- Age: {profile.age} | Weight: {profile.weight_kg}kg → Target: {profile.target_weight_kg}kg
- Activity Level: {profile.activity_level}
- Injuries/Limitations: {', '.join(profile.injuries) if profile.injuries else 'None'}

SENIOR COACH DIRECTIVE:
{directive}

WEEKLY CONTEXT:
- Training Split: {macro.training_split}
- Daily Calories: {macro.target_calories} kcal | Protein: {macro.protein_g}g | Carbs: {macro.carbs_g}g | Fats: {macro.fats_g}g

AVAILABLE EXERCISE LIBRARY:
You MUST select exercises from this library to formulate your gym sessions whenever possible. Match them carefully to the user's targeted muscles, level, and strength capabilities:
---
{library_text}
---

GYM SYSTEM OVERLOAD & FATIGUE MANAGEMENT GUIDELINES (MANDATORY):
You MUST strictly follow these compound progression systems, RPE conversions, and split layouts:
---
{gym_guidelines}
---

YOUR TASK:
Create a detailed weekly Gym regimen (list of WorkoutSession objects).
Each workout session MUST be structured logically using the **Core Framework: The Upper / Lower Hypertrophy Split Template** (Phase 1 through Phase 5):
1. Phase 1: Dynamic Warm-Up & CNS Priming (Ramping cardio, kettlebell prying, face pulls, explosive potentiation jumps/slams)
2. Phase 2: Tier A - Structural Compound Power (Mechanical tension barbell squat, bench, deadlift, or press; high rest 3 mins, RPE 8-9)
3. Phase 3: Tier B - Hypertrophy Duplets & Accompanying Lifts (Antagonist pairs dumbbells/machines, 3010 tempo, 60s/90s rest)
4. Phase 4: Tier C - Accessory Isolations & Weak Link Fixes (Targeted isolations split squats, lateral raises, hollow eccentrics)
5. Phase 5: Localized Down-Regulation & Recovery (Decompression hangs, doorways/couch static stretches)

For every exercise selected, preserve its name and demo_url EXACTLY as specified in the library list where applicable. Customize the sets, reps, rest_seconds, tempo, and notes specifically to address movement compensations, RPE limits, and injury modifications.

{EXERCISE_FIELDS_INSTRUCTION}
"""

    from src.agents.base import invoke_json_mode
    output = invoke_json_mode(llm, prompt, CreatorOutput)
    return {f"draft_{_DOMAIN.lower()}": output.sessions}

def gym_modifier_node(state: AgentState) -> dict:
    """
    Applies targeted corrections to a rejected Gym plan based on checker feedback,
    while enforcing intensity overload matrices.
    """
    llm = get_llm(temperature=0.1, json_mode=True)

    profile = state.get("user_profile")
    feedback = state.get("current_rejections", {}).get(_DOMAIN, "")
    domain_key = _DOMAIN.lower()
    current_draft = state.get(f"modified_{domain_key}") or state.get(f"draft_{domain_key}")

    # Load and filter exercise library
    from src.exercise_library import load_and_filter_exercises
    domain_exercises = load_and_filter_exercises(_DOMAIN, profile.experience_level)

    library_text = ""
    for ex in domain_exercises:
        library_text += f"- NAME: {ex.name}\n"
        library_text += f"  DESCRIPTION: {ex.description}\n"
        library_text += f"  LEVELS: {', '.join(ex.levels)}\n"
        library_text += f"  TARGETED MUSCLES: {', '.join(ex.targeted_muscles)}\n"
        focus_strs = [f"{m} ({'/'.join(focs)})" for m, focs in ex.muscle_focus.items()]
        library_text += f"  FOCUS: {', '.join(focus_strs)}\n"
        library_text += f"  DEMO URL: {ex.demo_url}\n"
        if ex.next_level_progressions:
            library_text += f"  PROGRESSIONS TO: {', '.join(ex.next_level_progressions)}\n"
        library_text += "\n"

    # Load custom Gym guidelines
    gym_guidelines = _load_gym_guidelines()

    prompt = f"""You are the Gym Plan Editor Agent.

A draft Gym workout plan was reviewed by the Safety & Efficacy Auditor and REJECTED with the following critique:

AUDITOR FEEDBACK:
{feedback}

USER PROFILE:
- Goal: {profile.primary_goal}
- Experience: {profile.experience_level}
- Injuries/Limitations: {', '.join(profile.injuries) if profile.injuries else 'None'}

EXERCISE LIBRARY FOR REFERENCE:
---
{library_text}
---

GYM PROGRESSIONS & PERFORMANCE BLUEPRINT:
---
{gym_guidelines}
---

CURRENT DRAFT TO FIX:
{current_draft}

YOUR TASK:
Apply the MINIMUM changes needed to fix ONLY the issues raised in the auditor feedback.
- Preserve the 5-phase Tiered hyperphy-split structure.
- Do NOT change compound power selections unless explicitly flagged.
- Keep the exercise name and demo_url matching the library definition.
- For any modified exercise, ensure ALL fields are still fully populated.

{EXERCISE_FIELDS_INSTRUCTION}
"""

    from src.agents.base import invoke_json_mode
    output = invoke_json_mode(llm, prompt, CreatorOutput)

    # Log the modification
    current_retries = state.get("domain_retries", {}).get(_DOMAIN, 0)
    log = ValidationLog(
        domain=_DOMAIN,
        provider_creator="Groq",
        provider_checker="Groq (Modifier)",
        status="Modified",
        feedback=f"Modifier applied corrections based on: {feedback[:200]}",
        attempt=current_retries
    )

    return {
        f"modified_{domain_key}": output.sessions,
        "validation_logs": [log]
    }

def gym_checker_node(state: AgentState) -> dict:
    """
    Safety & Efficacy Auditor for Gym plans.
    Validates safety, RPE/RIR volume limits, deload checkmarks, and 5-phase split structures.
    """
    llm = get_llm(temperature=0, json_mode=True)

    profile = state.get("user_profile")
    domain_key = _DOMAIN.lower()
    draft = state.get(f"modified_{domain_key}") or state.get(f"draft_{domain_key}")

    if not draft:
        raise ValueError(f"No draft found for domain '{_DOMAIN}'. Cannot check.")

    domain_retries = state.get("domain_retries", {})
    current_attempt = domain_retries.get(_DOMAIN, 0)
    gym_guidelines = _load_gym_guidelines()

    prompt = f"""You are the Senior Safety & Efficacy Auditor specialized in Gym strength and hypertrophy splits.

USER PROFILE:
- Goal: {profile.primary_goal}
- Experience: {profile.experience_level}
- Injuries/Limitations: {', '.join(profile.injuries) if profile.injuries else 'None'}

GYM OVERLOAD, PROGRESSION MATRICES, AND SPLIT BLUEPRINTS:
---
{gym_guidelines}
---

GYM DRAFT PLAN TO EVALUATE:
{draft}

EVALUATION CRITERIA:
1. FIVE PHASE SPLIT: Are the exercises structured logically across the 5 Phases (CNS Priming, Tier A Barbell Compound, Tier B Hypertrophy Duplets, Tier C Isolations, Down-Regulation)?
2. INTENSITY & RPE BOUNDS: Ensure Tier A barbell compounds match RPE 8-9 (1-2 RIR) and have sufficient 3-minute rest periods.
3. INJURY MITIGATION: Verify that movement patterns screen restrictions (e.g. ankle mobility or overhead shoulder hyperextensions) are handled appropriately with safety variations.
4. COMPLETENESS: Are all 9 exercise fields populated (name, sets, reps, rest_seconds, warmup_sets, tempo, demo_url, muscles_goal, notes)?

If the plan passes ALL criteria, approve it.
If ANY criterion fails, reject it with specific, actionable feedback referencing the exact exercise(s) and field(s) that need fixing.
"""

    from src.agents.base import invoke_json_mode
    output = invoke_json_mode(llm, prompt, CheckerOutput)

    log = ValidationLog(
        domain=_DOMAIN,
        provider_creator="Groq",
        provider_checker="Groq",
        status="Approved" if output.is_approved else "Rejected",
        feedback=output.feedback,
        attempt=current_attempt + 1
    )

    updates = {"validation_logs": [log]}

    if output.is_approved:
        updates["current_rejections"] = {_DOMAIN: None}
        best_draft = state.get(f"modified_{domain_key}") or state.get(f"draft_{domain_key}")
        updates[f"approved_{domain_key}"] = best_draft
    else:
        updates["domain_retries"] = {_DOMAIN: current_attempt + 1}
        updates["current_rejections"] = {_DOMAIN: output.feedback}

    return updates
