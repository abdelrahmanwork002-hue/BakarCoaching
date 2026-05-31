"""
Calisthenics Specialist Agent
==============================
Contains the Creator, Modifier, and Checker nodes for the Calisthenics domain.
Loads and enforces the client intake, progression matrices, and structural mastery templates.
"""
import os
import json
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from src.state import AgentState, ValidationLog
from src.agents.base import CreatorOutput, CheckerOutput, _invoke_with_retry, EXERCISE_FIELDS_INSTRUCTION, get_llm

_DOMAIN = "Calisthenics"

def _load_cali_guidelines() -> str:
    """Loads all calisthenics-specific markdown documents from 'md files' directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    md_dir = os.path.join(base_dir, "md files")
    guidelines = ""
    try:
        for fname in ["02_progression_matrices.md", "03_core_routine_template.md"]:
            path = os.path.join(md_dir, fname)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    guidelines += f"\n--- {fname} ---\n" + f.read() + "\n"
    except Exception as e:
        print(f"Error loading cali guidelines: {e}")
    return guidelines

def _load_cali_creator_guidelines() -> str:
    """Loads only the core routine template for the Calisthenics creator prompt to save tokens."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    md_dir = os.path.join(base_dir, "md files")
    guidelines = ""
    try:
        for fname in ["03_core_routine_template.md"]:
            path = os.path.join(md_dir, fname)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    guidelines += f"\n--- {fname} ---\n" + f.read() + "\n"
    except Exception as e:
        print(f"Error loading cali creator guidelines: {e}")
    return guidelines

def calisthenics_creator_node(state: AgentState) -> dict:
    """
    Creates the initial Calisthenics plan based on the Senior Coach's directive,
    strictly adhering to client assessment, progression matrices, and structural templates.
    """
    llm = get_llm(temperature=0.2, json_mode=True)

    profile = state.get("user_profile")
    macro = state.get("macro_strategy")
    directive = macro.specialist_directives.get(
        _DOMAIN,
        "Design a progressive calisthenics program focused on bodyweight mastery, core stability, and skill progressions."
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

    # Load custom Calisthenics guidelines
    cali_guidelines = _load_cali_creator_guidelines()

    prompt = f"""You are the master Calisthenics Specialist Creator Agent.
    
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
You MUST select exercises from this library to formulate your workout sessions whenever possible. Match them carefully to the user's targeted muscles, level, and safety needs:
---
{library_text}
---

CALISTHENICS SYSTEM ARCHITECTURE GUIDELINES (MANDATORY):
You MUST strictly follow these guidelines, progression trees, and core templates when constructing workout sessions:
---
{cali_guidelines}
---

YOUR TASK:
Create a detailed weekly Calisthenics regimen (list of WorkoutSession objects).
Each workout session MUST be structured logically using the **Core Framework: The Structural Mastery Template** (Phase 1 through Phase 5).
For every session, include exercises mapped to the 5 training phases:
1. Phase 1: Joint Prep & Activation (Wrist Mobility, Scapular Mechanics, Hollow Holds)
2. Phase 2: Skill Acquisition (sub-maximal holds or balances aligned with client experience)
3. Phase 3: Primary Strength Duplets (Paired supersets: Pulling + Pushing dynamic variations)
4. Phase 4: Structural Integration & Accessory (Hanging leg raises, hyperextensions, etc.)
5. Phase 5: Decompression & Flexibility (Passive Dead Hang, German Hang, skin-the-cat)

For every exercise selected, preserve its name and demo_url EXACTLY as specified in the library list where applicable, and structure the phase order logically. Customize the sets, reps, rest_seconds, tempo, and notes specifically for this user's profile and injury limitations.

{EXERCISE_FIELDS_INSTRUCTION}
"""

    from src.agents.base import invoke_json_mode
    output = invoke_json_mode(llm, prompt, CreatorOutput)
    return {f"draft_{_DOMAIN.lower()}": output.sessions}

def calisthenics_modifier_node(state: AgentState) -> dict:
    """
    Applies targeted corrections to a rejected Calisthenics plan based on checker feedback,
    while enforcing the Calisthenics guidelines and progression structures.
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

    # Load custom Calisthenics guidelines
    cali_guidelines = _load_cali_guidelines()

    prompt = f"""You are the Calisthenics Plan Editor Agent.

A draft Calisthenics workout plan was reviewed by the Safety & Efficacy Auditor and REJECTED with the following critique:

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

CALISTHENICS PROGRESSIONS & TEMPLATE GUIDELINES:
---
{cali_guidelines}
---

CURRENT DRAFT TO FIX:
{current_draft}

YOUR TASK:
Apply the MINIMUM changes needed to fix ONLY the issues raised in the auditor feedback.
- Preserve the 5-phase structure (Joint Prep, Skill, Duplets, Accessories, Decompression).
- Do NOT change exercises that were not flagged.
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

def calisthenics_checker_node(state: AgentState) -> dict:
    """
    Safety & Efficacy Auditor for Calisthenics plans.
    Validates safety, experience-appropriateness, and adherence to the 5-phase Core mastery structure.
    """
    llm = get_llm(temperature=0, json_mode=True)

    profile = state.get("user_profile")
    domain_key = _DOMAIN.lower()
    draft = state.get(f"modified_{domain_key}") or state.get(f"draft_{domain_key}")

    if not draft:
        raise ValueError(f"No draft found for domain '{_DOMAIN}'. Cannot check.")

    domain_retries = state.get("domain_retries", {})
    current_attempt = domain_retries.get(_DOMAIN, 0)
    cali_guidelines = _load_cali_guidelines()

    prompt = f"""You are the Senior Safety & Efficacy Auditor specialized in Calisthenics.

USER PROFILE:
- Goal: {profile.primary_goal}
- Experience: {profile.experience_level}
- Injuries/Limitations: {', '.join(profile.injuries) if profile.injuries else 'None'}

CALISTHENICS RULES, PROGRESSION SKILL TREES, AND CORE Mastery TEMPLATE:
---
{cali_guidelines}
---

CALISTHENICS DRAFT PLAN TO EVALUATE:
{draft}

EVALUATION CRITERIA:
1. CORE TEMPLATE ADHERENCE: Are the exercises structured logically across the 5 Phases (Joint Prep, Skill Acquisition, Strength Duplets, Accessories, Decompression)?
2. PROGRESSION MATRICES: Are the exercises assigned in accordance with the user's experience level (e.g. L-Sit Pull-ups or muscle-ups only for Advanced; scapular activations or negatives for Beginners)?
3. PREREQUISITE SAFETY: Ensure no advanced skills are programmed unless basic prerequisites are verified or scaled.
4. SAFETY & COMPLETENESS: Does any exercise risk aggravating injuries? Are all 9 exercise fields populated (name, sets, reps, rest_seconds, warmup_sets, tempo, demo_url, muscles_goal, notes)?

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
