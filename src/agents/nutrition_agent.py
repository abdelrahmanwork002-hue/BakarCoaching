"""
Nutrition Specialist Agent
===========================
Contains the Creator, Modifier, and Checker nodes for the Nutrition domain.
Modify this file to change how meal plans are generated or validated.

Note: The Nutrition domain uses NutritionPlan (not WorkoutSession), so it has
its own creator and modifier logic rather than delegating to base_creator_node.
All LLM calls use Groq Llama 3.3 70B (no daily quota limits).
"""
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from src.state import AgentState, NutritionPlan, ValidationLog
from src.agents.base import CheckerOutput, _invoke_with_retry

_DOMAIN = "Nutrition"


def nutrition_creator_node(state: AgentState) -> dict:
    """
    Creates the initial daily meal plan aligned with macro targets.
    Model: Groq Llama 3.3 70B
    Edit this function to change how meals are structured or what constraints are applied.
    """
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)
    llm_structured = llm.with_structured_output(NutritionPlan)

    macro = state.get("macro_strategy")
    profile = state.get("user_profile")

    prompt = f"""You are the Head Nutritionist and Meal Planning Specialist.

USER PROFILE:
- Goal: {profile.primary_goal}
- Current Weight: {profile.weight_kg}kg → Target: {profile.target_weight_kg}kg
- Activity Level: {profile.activity_level}
- Injuries/Limitations: {', '.join(profile.injuries) if profile.injuries else 'None'}

DAILY MACRO TARGETS (MUST HIT THESE):
- Calories: {macro.target_calories} kcal
- Protein: {macro.protein_g}g
- Carbohydrates: {macro.carbs_g}g
- Fats: {macro.fats_g}g

YOUR TASK:
Create a practical, balanced daily meal plan (Breakfast, Morning Snack, Lunch, Afternoon Snack, Dinner) that:
1. Hits the macro targets within ±50 kcal and ±5g per macro
2. Uses whole, nutrient-dense foods
3. Respects the user's goal (e.g. high protein for muscle gain, slight deficit for weight loss)
4. Includes a realistic hydration target in liters

Also provide a precise hydration_target_L value (in liters).
"""

    output = _invoke_with_retry(llm_structured, [HumanMessage(content=prompt)])
    return {"draft_nutrition": output}


def nutrition_modifier_node(state: AgentState) -> dict:
    """
    Applies targeted corrections to a rejected nutrition plan based on checker feedback.
    Does NOT regenerate from scratch — only patches what was flagged.
    Model: Groq Llama 3.3 70B
    Edit this function to adjust how the modifier corrects meal plans.
    """
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)
    llm_structured = llm.with_structured_output(NutritionPlan)

    profile = state.get("user_profile")
    macro = state.get("macro_strategy")
    feedback = state.get("current_rejections", {}).get(_DOMAIN, "")

    # Prefer modified draft if exists (2nd+ iteration), else original draft
    current_draft = state.get("modified_nutrition") or state.get("draft_nutrition")

    prompt = f"""You are the Nutrition Plan Editor Agent.

A draft meal plan was rejected by the Nutrition Auditor with this feedback:

AUDITOR FEEDBACK:
{feedback}

CURRENT DRAFT TO FIX:
{current_draft}

MACRO TARGETS (must still be met):
- Calories: {macro.target_calories} kcal | Protein: {macro.protein_g}g | Carbs: {macro.carbs_g}g | Fats: {macro.fats_g}g

YOUR TASK:
Apply the MINIMUM changes needed to fix ONLY the issues raised above.
- Do NOT change meals that were not flagged.
- Ensure the corrected plan still hits the macro targets within ±50 kcal.
- Keep the same meal structure unless explicitly told to change it.
"""

    current_retries = state.get("domain_retries", {}).get(_DOMAIN, 0)
    output = _invoke_with_retry(llm_structured, [HumanMessage(content=prompt)])

    log = ValidationLog(
        domain=_DOMAIN,
        provider_creator="Groq",
        provider_checker="Groq (Modifier)",
        status="Modified",
        feedback=f"Modifier applied corrections based on: {feedback[:200]}",
        attempt=current_retries
    )

    return {
        "modified_nutrition": output,
        "validation_logs": [log]
    }


def nutrition_checker_node(state: AgentState) -> dict:
    """
    Safety & Efficacy Auditor for Nutrition plans.
    Uses Groq Llama 3.3 70B — no daily quota, automatic retry on rate-limits.
    Edit this function to change validation criteria for meal plans.
    """
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    llm_structured = llm.with_structured_output(CheckerOutput)

    profile = state.get("user_profile")
    macro = state.get("macro_strategy")

    # Prefer modified draft if it exists
    draft = state.get("modified_nutrition") or state.get("draft_nutrition")

    if not draft:
        raise ValueError("No nutrition draft found in state.")

    current_attempt = state.get("domain_retries", {}).get(_DOMAIN, 0)

    prompt = f"""You are the Senior Nutrition Safety & Efficacy Auditor.

USER PROFILE:
- Goal: {profile.primary_goal}
- Weight: {profile.weight_kg}kg → Target: {profile.target_weight_kg}kg

REQUIRED MACRO TARGETS:
- Calories: {macro.target_calories} kcal | Protein: {macro.protein_g}g | Carbs: {macro.carbs_g}g | Fats: {macro.fats_g}g

DRAFT MEAL PLAN TO EVALUATE:
{draft}

EVALUATION CRITERIA:
1. MACRO ACCURACY: Does the total daily intake hit within ±50 kcal and ±5g per macro?
2. MEAL COMPLETENESS: Are all meals (Breakfast, Lunch, Dinner, Snacks) described with calorie and macro breakdown?
3. FOOD QUALITY: Are the foods whole, practical, and appropriate for the user's goal?
4. HYDRATION: Is a realistic hydration_target_L provided (between 2.0L and 4.5L)?
5. MEAL BALANCE: Are calories distributed reasonably across the day (no single meal >50% of daily calories)?

If all criteria pass, approve it.
If any fail, reject with specific feedback referencing the exact meal and field that needs fixing.
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
        best_draft = state.get("modified_nutrition") or state.get("draft_nutrition")
        updates["nutrition_plan"] = best_draft
    else:
        updates["domain_retries"] = {_DOMAIN: current_attempt + 1}
        updates["current_rejections"] = {_DOMAIN: output.feedback}

    return updates
