"""
Yoga Specialist Agent
=====================
Contains the Creator, Modifier, and Checker nodes for the Yoga domain.
Loads and enforces the somatic client intake, asana progression trees, and class frameworks.
"""
import os
import json
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from src.state import AgentState, ValidationLog
from src.agents.base import CreatorOutput, CheckerOutput, _invoke_with_retry, EXERCISE_FIELDS_INSTRUCTION, get_llm

_DOMAIN = "Yoga"

def _load_yoga_guidelines() -> str:
    """Loads all yoga-specific markdown documents from 'md files' directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    md_dir = os.path.join(base_dir, "md files")
    guidelines = ""
    try:
        for fname in ["01_yoga_client_assessment.md", "02_yoga_progression_matrices.md", "03_yoga_class_framework.md"]:
            path = os.path.join(md_dir, fname)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    guidelines += f"\n--- {fname} ---\n" + f.read() + "\n"
    except Exception as e:
        print(f"Error loading yoga guidelines: {e}")
    return guidelines

def yoga_creator_node(state: AgentState) -> dict:
    """
    Creates the initial Yoga plan based on the Senior Coach's directive,
    strictly adhering to somatic assessments, asana progression trees, and krama sequencing.
    """
    llm = get_llm(temperature=0.2)
    llm_structured = llm.with_structured_output(CreatorOutput)

    profile = state.get("user_profile")
    macro = state.get("macro_strategy")
    directive = macro.specialist_directives.get(
        _DOMAIN,
        "Design a restorative yoga and mobility program for active recovery, flexibility, and stress reduction."
    )

    # Load and filter exercise library
    from src.exercise_library import load_exercise_library
    library_items = load_exercise_library()
    domain_exercises = [
        item for item in library_items
        if _DOMAIN.lower() in [t.lower() for t in item.training_types]
    ]

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

    # Load custom Yoga guidelines
    yoga_guidelines = _load_yoga_guidelines()

    prompt = f"""You are the master Yoga Specialist Creator Agent.
    
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
You MUST select exercises from this library to formulate your yoga sessions whenever possible. Match them carefully to the user's targeted muscles, level, and structural mobility needs:
---
{library_text}
---

YOGA SYSTEM ARCHITECTURE & ANATOMICAL GUIDELINES (MANDATORY):
You MUST strictly follow these guidelines, asana progression trees, and class blueprints:
---
{yoga_guidelines}
---

YOUR TASK:
Create a detailed weekly Yoga regimen (list of WorkoutSession objects).
Each class sequence MUST be structured logically using the **Class Blueprint: Vinyasa & Hatha Integrated Flow Template** (Phase 1 through Phase 5) and honor the Krama (wise progression) framework:
1. Phase 1: Prana Inception & Centering (Sukasana, Sama Vritti, Gentle Spinal wakeup Cat/Cow)
2. Phase 2: Surya Namaskar & Systemic Heating (Agni building heating sequences - Surya A/B)
3. Phase 3: The Asana Krama Flow (Hip opening waves, Balance, and Peak integrations, utilizing props)
4. Phase 4: Cool-Down Counter-Poses & Integration (Static floor poses, paschimottanasana, twists, piriformis open)
5. Phase 5: Savasana & Neural Recalibration (Complete parasympathetic rest, weight integration)

For every pose/exercise selected, preserve its name and demo_url EXACTLY as specified in the library list where applicable. Customize sets (usually 1 or 2 for yoga segments), reps (or hold duration, e.g. "5 breaths" or "2 mins hold"), rest_seconds (usually 0 or very small between flow transitions), tempo, and notes specifically to address joint restrictions, ankle/hip tightness, or SI joint sensitivity.

{EXERCISE_FIELDS_INSTRUCTION}
"""

    output = _invoke_with_retry(llm_structured, [HumanMessage(content=prompt)])
    return {f"draft_{_DOMAIN.lower()}": output.sessions}

def yoga_modifier_node(state: AgentState) -> dict:
    """
    Applies targeted corrections to a rejected Yoga plan based on checker feedback,
    while enforcing the Krama wise progression sequencing.
    """
    llm = get_llm(temperature=0.1)
    llm_structured = llm.with_structured_output(CreatorOutput)

    profile = state.get("user_profile")
    feedback = state.get("current_rejections", {}).get(_DOMAIN, "")
    domain_key = _DOMAIN.lower()
    current_draft = state.get(f"modified_{domain_key}") or state.get(f"draft_{domain_key}")

    # Load and filter exercise library
    from src.exercise_library import load_exercise_library
    library_items = load_exercise_library()
    domain_exercises = [
        item for item in library_items
        if _DOMAIN.lower() in [t.lower() for t in item.training_types]
    ]

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

    # Load custom Yoga guidelines
    yoga_guidelines = _load_yoga_guidelines()

    prompt = f"""You are the Yoga Plan Editor Agent.

A draft Yoga workout plan was reviewed by the Safety & Efficacy Auditor and REJECTED with the following critique:

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

YOGA PROGRESSIONS & ANATOMICAL BLUEPRINT:
---
{yoga_guidelines}
---

CURRENT DRAFT TO FIX:
{current_draft}

YOUR TASK:
Apply the MINIMUM changes needed to fix ONLY the issues raised in the auditor feedback.
- Preserve the 5-phase Vinyasa Krama framework structure.
- Do NOT change poses/exercises that were not flagged.
- Keep the pose name and demo_url matching the library definition.
- For any modified exercise, ensure ALL fields are still fully populated.

{EXERCISE_FIELDS_INSTRUCTION}
"""

    output = _invoke_with_retry(llm_structured, [HumanMessage(content=prompt)])

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

def yoga_checker_node(state: AgentState) -> dict:
    """
    Safety & Efficacy Auditor for Yoga / mobility plans.
    Validates anatomical safety, somatic alignment, sustainability of breath, and Vinyasa Krama sequence structure.
    """
    llm = get_llm(temperature=0)
    llm_structured = llm.with_structured_output(CheckerOutput)

    profile = state.get("user_profile")
    domain_key = _DOMAIN.lower()
    draft = state.get(f"modified_{domain_key}") or state.get(f"draft_{domain_key}")

    if not draft:
        raise ValueError(f"No draft found for domain '{_DOMAIN}'. Cannot check.")

    domain_retries = state.get("domain_retries", {})
    current_attempt = domain_retries.get(_DOMAIN, 0)
    yoga_guidelines = _load_yoga_guidelines()

    prompt = f"""You are the Senior Safety & Efficacy Auditor specialized in Yoga, somatic alignment, and Vinyasa Krama sequencing.

USER PROFILE:
- Goal: {profile.primary_goal}
- Experience: {profile.experience_level}
- Injuries/Limitations: {', '.join(profile.injuries) if profile.injuries else 'None'}

YOGA ANATOMICAL RULES, PROGRESSIONS, AND SEQUENCING TEMPLATES:
---
{yoga_guidelines}
---

YOGA DRAFT PLAN TO EVALUATE:
{draft}

EVALUATION CRITERIA:
1. KRAMA TEMPLATE ADHERENCE: Are the poses structured logically across the 5 Phases (Prana Inception, Surya Namaskar, Asana Krama Flow, Cool-down, Savasana)?
2. PROGRESSION MATRICES: Are the backbends and inversions scaled correctly to the user's level (e.g., supported headstands or forearm stands only for advanced practitioners; locust or legs-up-wall for beginners)?
3. STRUCTURAL MODIFICATION: Ensure blocks, blankets, or parallel setups are specified in the notes/notes field when joint restrictions are flagged (e.g. tight hips/ankles in Yogi Squats or hamstring shortening in Half Lifts).
4. SAFETY & COMPLETENESS: Does any pose risk aggravating listed injuries (e.g., SI joint sensitivities)? Are all 9 fields fully populated?

If the plan passes ALL criteria, approve it.
If ANY criterion fails, reject it with specific, actionable feedback referencing the exact pose(s) and field(s) that need fixing.
"""

    output = _invoke_with_retry(llm_structured, [HumanMessage(content=prompt)])

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
