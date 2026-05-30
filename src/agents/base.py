"""
Base agent logic shared across all domain specialist files.
Contains: CreatorOutput schema, CheckerOutput schema,
          base_creator_node, base_checker_node, base_modifier_node.

NOTE ON MODELS:
  - Creators  → Groq Llama 3.3 70B  (fast, creative)
  - Modifiers → Groq Llama 3.3 70B  (fast, targeted edits)
  - Checkers  → Groq Llama 3.3 70B  (free, no daily quota)
    Reason: Gemini free tier has a hard limit of 20 requests/day,
    which is exhausted immediately when 4 checkers run in parallel.
"""
import time
from typing import List, Optional
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from src.state import AgentState, WorkoutSession, ValidationLog

def get_llm(temperature: float = 0.2, json_mode: bool = False):
    """
    Central LLM factory — uses Groq Llama 3.3 70B exclusively.
    Groq is free with no daily quota limit (only a per-minute token limit,
    handled by the _invoke_with_retry backoff logic).
    """
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=temperature)
    if json_mode:
        return llm.bind(response_format={"type": "json_object"})
    return llm


# ---------------------------------------------------------------------------
# Output Schemas
# ---------------------------------------------------------------------------

class CreatorOutput(BaseModel):
    sessions: List[WorkoutSession] = Field(description="The planned workout sessions for the week.")

class CheckerOutput(BaseModel):
    is_approved: bool = Field(description="True if the plan meets all criteria, False if it needs revision.")
    feedback: str = Field(description="Detailed, actionable feedback if rejected. Empty string if approved.")

# ---------------------------------------------------------------------------
# Exercise field instruction block (injected into all creator/modifier prompts)
# ---------------------------------------------------------------------------

EXERCISE_FIELDS_INSTRUCTION = """
For EVERY exercise you include, you MUST populate ALL of the following fields:
- name: Full exercise name (e.g. "Romanian Deadlift")
- sets: Number of working sets as an integer (e.g. 4)
- reps: Rep range as a string (e.g. "8-12" or "45 sec" or "10 each side")
- rest_seconds: Rest between sets in seconds as an integer (e.g. 90)
- warmup_sets: Number of warm-up sets as an integer. Use 0 for Yoga/mobility work.
- tempo: Eccentric-pause-concentric notation as a string (e.g. "3-1-2" means 3s lower, 1s pause, 2s lift). Use "1-0-1" for dynamic movements.
- demo_url: A YouTube search URL. Format exactly as: https://www.youtube.com/results?search_query=EXERCISE+NAME+tutorial+form (replace spaces with + signs)
- muscles_goal: Primary muscles targeted and goal (e.g. "Hamstrings, Glutes — Strength & Hypertrophy")
- notes: Specific form cues or injury modifications for this user. Always reference the user's injury/limitation if relevant.
"""

# ---------------------------------------------------------------------------
# Retry helper — handles transient rate-limit errors from any provider
# ---------------------------------------------------------------------------

def _invoke_with_retry(llm_structured, messages, max_retries=8):
    """
    Invoke LLM with automatic exponential backoff on rate-limit (429) errors.
    Uses up to 8 retries with waits of 30s, 60s, 90s... to handle Groq TPM limits
    when multiple parallel creators fire simultaneously.
    """
    for attempt in range(max_retries):
        try:
            return llm_structured.invoke(messages)
        except Exception as e:
            err_str = str(e)
            is_rate_limit = (
                "429" in err_str
                or "RESOURCE_EXHAUSTED" in err_str
                or "rate_limit" in err_str.lower()
                or "RateLimitError" in err_str
                or "rate limit" in err_str.lower()
                or "quota" in err_str.lower()
            )
            if is_rate_limit:
                wait = (attempt + 1) * 30  # 30s, 60s, 90s, 120s, 150s, 180s, 210s, 240s
                print(f"[Rate limit] Waiting {wait}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait)
            else:
                raise  # non-quota error — propagate immediately
    raise RuntimeError(f"Max retries exceeded ({max_retries} attempts) for LLM call.")

# ---------------------------------------------------------------------------
# Base Creator Node
# ---------------------------------------------------------------------------

def base_creator_node(state: AgentState, domain: str, directive: str) -> dict:
    """
    Generates a fresh weekly workout plan for a given domain.
    Uses Gemini for fast, creative plan generation, selecting exercises from the Exercise Library.
    """
    llm = get_llm(temperature=0.2)
    llm_structured = llm.with_structured_output(CreatorOutput)


    profile = state.get("user_profile")
    macro = state.get("macro_strategy")

    # Load and filter exercise library for this domain
    from src.exercise_library import load_exercise_library
    library_items = load_exercise_library()
    domain_exercises = [
        item for item in library_items
        if domain.lower() in [t.lower() for t in item.training_types]
    ]

    library_text = ""
    for ex in domain_exercises:
        library_text += f"- NAME: {ex.name}\n"
        library_text += f"  DESCRIPTION: {ex.description}\n"
        library_text += f"  LEVELS: {', '.join(ex.levels)}\n"
        library_text += f"  TARGETED MUSCLES: {', '.join(ex.targeted_muscles)}\n"
        # Format muscle focus
        focus_strs = [f"{m} ({'/'.join(focs)})" for m, focs in ex.muscle_focus.items()]
        library_text += f"  FOCUS: {', '.join(focus_strs)}\n"
        library_text += f"  DEMO URL: {ex.demo_url}\n"
        if ex.next_level_progressions:
            library_text += f"  PROGRESSIONS TO: {', '.join(ex.next_level_progressions)}\n"
        library_text += "\n"

    prompt = f"""You are the {domain} Specialist Creator Agent.

USER PROFILE:
- Goal: {profile.primary_goal}
- Experience: {profile.experience_level}
- Age: {profile.age} | Weight: {profile.weight_kg}kg → Target: {profile.target_weight_kg}kg
- Activity Level: {profile.activity_level}
- Injuries/Limitations: {', '.join(profile.injuries) if profile.injuries else 'None'}

SENIOR COACH DIRECTIVE FOR {domain.upper()}:
{directive}

WEEKLY CONTEXT:
- Training Split: {macro.training_split}
- Daily Calories: {macro.target_calories} kcal | Protein: {macro.protein_g}g | Carbs: {macro.carbs_g}g | Fats: {macro.fats_g}g

AVAILABLE EXERCISE LIBRARY FOR {domain.upper()}:
You MUST select exercises from this library to formulate your workout sessions whenever possible. Match them carefully to the user's targeted muscles, level, and safety needs:
---
{library_text}
---

YOUR TASK:
Create a detailed weekly {domain} regimen (list of WorkoutSession objects). Each session targets a specific day and focus area aligned with the Senior Coach directive.
Select exercises from the library above. For every exercise chosen, preserve its name and demo_url EXACTLY as specified in the library list. Customize the sets, reps, rest_seconds, tempo, warmup_sets, and notes specifically for this user's profile and injury limitations.

{EXERCISE_FIELDS_INSTRUCTION}
"""

    output = _invoke_with_retry(llm_structured, [HumanMessage(content=prompt)])
    return {f"draft_{domain.lower()}": output.sessions}

# ---------------------------------------------------------------------------
# Base Modifier Node
# ---------------------------------------------------------------------------

def base_modifier_node(state: AgentState, domain: str) -> dict:
    """
    Applies targeted corrections to an existing draft based on checker feedback.
    Does NOT regenerate — only patches the specific issues raised.
    Uses Gemini for fast corrections, matching exercises to the library.
    """
    llm = get_llm(temperature=0.1)
    llm_structured = llm.with_structured_output(CreatorOutput)


    profile = state.get("user_profile")
    feedback = state.get("current_rejections", {}).get(domain, "")

    # Use the modified draft if it exists (2nd+ iteration), else use the original draft
    domain_key = domain.lower()
    current_draft = state.get(f"modified_{domain_key}") or state.get(f"draft_{domain_key}")

    # Load and filter exercise library for this domain
    from src.exercise_library import load_exercise_library
    library_items = load_exercise_library()
    domain_exercises = [
        item for item in library_items
        if domain.lower() in [t.lower() for t in item.training_types]
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

    prompt = f"""You are the {domain} Plan Editor Agent.

A draft {domain} workout plan was reviewed by the Safety & Efficacy Auditor and REJECTED with the following critique:

AUDITOR FEEDBACK:
{feedback}

USER PROFILE (for context):
- Goal: {profile.primary_goal}
- Experience: {profile.experience_level}
- Injuries/Limitations: {', '.join(profile.injuries) if profile.injuries else 'None'}

EXERCISE LIBRARY FOR REFERENCE:
---
{library_text}
---

CURRENT DRAFT TO FIX:
{current_draft}

YOUR TASK:
Apply the MINIMUM changes needed to fix ONLY the issues raised in the feedback above.
- Do NOT change exercises that were not flagged.
- Do NOT change the session structure unless explicitly flagged.
- Preserve all fields of unchanged exercises exactly as they are.
- For any modified exercise, select it from the exercise library or align it with the library guidelines. Keep the name and demo_url matching the library definition.
- For any modified exercise, ensure ALL fields are still fully populated.

{EXERCISE_FIELDS_INSTRUCTION}
"""

    output = _invoke_with_retry(llm_structured, [HumanMessage(content=prompt)])

    # Log the modification
    current_retries = state.get("domain_retries", {}).get(domain, 0)
    log = ValidationLog(
        domain=domain,
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

# ---------------------------------------------------------------------------
# Base Checker Node  (Groq — no daily quota limit)
# ---------------------------------------------------------------------------

def base_checker_node(state: AgentState, domain: str) -> dict:
    """
    Evaluates the latest draft (modified > draft) for safety and efficacy.
    Uses Gemini — no daily quota, automatic retry on rate-limits.
    """
    llm = get_llm(temperature=0)
    llm_structured = llm.with_structured_output(CheckerOutput)


    profile = state.get("user_profile")
    domain_key = domain.lower()

    # Prefer the modified draft if it exists
    draft = state.get(f"modified_{domain_key}") or state.get(f"draft_{domain_key}")

    if not draft:
        raise ValueError(f"No draft found for domain '{domain}'. Cannot check.")

    domain_retries = state.get("domain_retries", {})
    current_attempt = domain_retries.get(domain, 0)

    prompt = f"""You are the Senior Safety & Efficacy Auditor for a premium fitness platform.

USER PROFILE:
- Goal: {profile.primary_goal}
- Experience: {profile.experience_level}
- Injuries/Limitations: {', '.join(profile.injuries) if profile.injuries else 'None'}

{domain.upper()} DRAFT PLAN TO EVALUATE:
{draft}

EVALUATION CRITERIA (check ALL of the following):
1. SAFETY: Does any exercise risk aggravating the user's listed injuries?
2. APPROPRIATENESS: Is the intensity and complexity suitable for the user's experience level?
3. COMPLETENESS: Does every exercise have all 9 fields populated (name, sets, reps, rest_seconds, warmup_sets, tempo, demo_url, muscles_goal, notes)?
4. DEMO URLs: Are all demo_url fields formatted as valid YouTube search URLs (starting with https://www.youtube.com/results?search_query=)?
5. TEMPO: Is the tempo notation realistic and appropriate (e.g. not "10-0-10" for beginners)?
6. REST PERIODS: Are rest periods appropriate for the goal and experience level?

If the plan passes ALL criteria, approve it.
If ANY criterion fails, reject it with specific, actionable feedback referencing the exact exercise(s) and field(s) that need fixing.
"""

    output = _invoke_with_retry(llm_structured, [HumanMessage(content=prompt)])

    log = ValidationLog(
        domain=domain,
        provider_creator="Groq",
        provider_checker="Groq",
        status="Approved" if output.is_approved else "Rejected",
        feedback=output.feedback,
        attempt=current_attempt + 1
    )

    updates = {"validation_logs": [log]}

    if output.is_approved:
        updates["current_rejections"] = {domain: None}
        best_draft = state.get(f"modified_{domain_key}") or state.get(f"draft_{domain_key}")
        if domain != "Nutrition":
            updates[f"approved_{domain_key}"] = best_draft
        else:
            updates["nutrition_plan"] = best_draft
    else:
        updates["domain_retries"] = {domain: current_attempt + 1}
        updates["current_rejections"] = {domain: output.feedback}

    return updates
