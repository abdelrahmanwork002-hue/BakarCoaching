"""
Nutrition Specialist Agent
===========================
Contains the Creator, Modifier, and Checker nodes for the Nutrition domain.
Loads and enforces the metabolic screenings, dynamic fueling, peri-workout timing, and meal structure blueprints.
"""
import os
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from src.state import AgentState, NutritionPlan, ValidationLog
from src.agents.base import CheckerOutput, _invoke_with_retry, get_llm

_DOMAIN = "Nutrition"

def _load_nutrition_guidelines() -> str:
    """Loads all nutrition-specific markdown documents from 'md files' directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    md_dir = os.path.join(base_dir, "md files")
    guidelines = ""
    try:
        for fname in ["01_nutritionist_assessment.md", "02_nutritionist_progression_matrices.md", "03_nutritionist_meal_blueprint.md"]:
            path = os.path.join(md_dir, fname)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    guidelines += f"\n--- {fname} ---\n" + f.read() + "\n"
    except Exception as e:
        print(f"Error loading nutrition guidelines: {e}")
    return guidelines

def nutrition_creator_node(state: AgentState) -> dict:
    """
    Creates the initial daily meal plan aligned with macro targets,
    strictly adhering to dynamic fueling matrices and four-meal timing frameworks.
    """
    llm = get_llm(temperature=0.1)
    llm_structured = llm.with_structured_output(NutritionPlan)

    macro = state.get("macro_strategy")
    profile = state.get("user_profile")

    # Load custom Nutrition guidelines
    nutrition_guidelines = _load_nutrition_guidelines()

    prompt = f"""You are the master Head Nutritionist and Meal Planning Specialist.

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

ATHLETIC NUTRITION & DYNAMIC FUELING BLUEPRINTS (MANDATORY):
You MUST strictly follow these dietary baseline screens, carbohydrate scaling rules, peri-workout timing windows, and meal schedules:
---
{nutrition_guidelines}
---

YOUR TASK:
Create a daily nutrition plan (list of Meal objects).
You MUST structure the eating timeline using the **Daily Four-Meal Tier Structure Template** and synchronize it with the client's macro goals:
1. Meal 1: Metabolic Inception & Tissue Repair (08:00 - Lean protein, complex low-glycemic starches like oats, and healthy fats).
2. Meal 2: Pre-Workout Nutrient Loading (13:00 - Lean isolates/chicken, white fish, SWEET POTATO or jasmine rice, keeping fat trace <= 5g to ensure rapid absorption).
3. Meal 3: Post-Workout Glycogen Replenishment (17:30 - Fast-acting high-glycemic starches to spike insulin like cream of rice/white potatoes, and lean rapid-digesting proteins).
4. Meal 4: Nocturnal Recovery & Anti-Catabolic Reset (21:30 - Slow-digesting casein, cottage cheese or lean beef, paired with healthy lipids like almond butter to slow digestion).

Set the `hydration_target_L` based on active training guidelines (>3.5L baseline, plus 1.0L water per hour of heavy resistance training, alongside sodium/electrolyte recommendations in Meal 2/3). Incorporate key micronutrient interventions (magnesium glycinate, Vitamin D3+K2, and Omega-3 fish oils) in the meal notes.

Provide macro and calorie breakdowns for EVERY single meal, and ensure the daily totals hit the required macro targets within ±50 kcal.
"""

    output = _invoke_with_retry(llm_structured, [HumanMessage(content=prompt)])
    return {"draft_nutrition": output}

def nutrition_modifier_node(state: AgentState) -> dict:
    """
    Applies targeted corrections to a rejected nutrition plan based on checker feedback,
    while maintaining the dynamic meal timing framework.
    """
    llm = get_llm(temperature=0.1)
    llm_structured = llm.with_structured_output(NutritionPlan)

    profile = state.get("user_profile")
    macro = state.get("macro_strategy")
    feedback = state.get("current_rejections", {}).get(_DOMAIN, "")
    current_draft = state.get("modified_nutrition") or state.get("draft_nutrition")

    # Load custom Nutrition guidelines
    nutrition_guidelines = _load_nutrition_guidelines()

    prompt = f"""You are the Nutrition Plan Editor Agent.

A draft meal plan was rejected by the Nutrition Auditor with this feedback:

AUDITOR FEEDBACK:
{feedback}

USER PROFILE:
- Goal: {profile.primary_goal}
- Weight: {profile.weight_kg}kg → Target: {profile.target_weight_kg}kg

REQUIRED MACRO TARGETS:
- Calories: {macro.target_calories} kcal | Protein: {macro.protein_g}g | Carbs: {macro.carbs_g}g | Fats: {macro.fats_g}g

ATHLETIC NUTRITION & TIMING PRINCIPLES:
---
{nutrition_guidelines}
---

CURRENT DRAFT TO FIX:
{current_draft}

YOUR TASK:
Apply the MINIMUM changes needed to fix ONLY the issues raised in the auditor feedback.
- Preserve the 4-meal metabolic timeline structure (Metabolic Inception, Pre-Workout, Post-Workout, Nocturnal Recovery).
- Maintain macronutrient totals within ±50 kcal of targets.
- Correct specific details flagged (e.g. food intolerances, micronutrient checklists, or timing).
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
    Validates macro accuracy, 4-meal structures, timing windows, hydration targets, and food intolerances.
    """
    llm = get_llm(temperature=0)
    llm_structured = llm.with_structured_output(CheckerOutput)

    profile = state.get("user_profile")
    macro = state.get("macro_strategy")
    draft = state.get("modified_nutrition") or state.get("draft_nutrition")

    if not draft:
        raise ValueError("No nutrition draft found in state.")

    current_attempt = state.get("domain_retries", {}).get(_DOMAIN, 0)
    nutrition_guidelines = _load_nutrition_guidelines()

    prompt = f"""You are the Senior Nutrition Safety & Efficacy Auditor.

USER PROFILE:
- Goal: {profile.primary_goal}
- Weight: {profile.weight_kg}kg → Target: {profile.target_weight_kg}kg

REQUIRED MACRO TARGETS:
- Calories: {macro.target_calories} kcal | Protein: {macro.protein_g}g | Carbs: {macro.carbs_g}g | Fats: {macro.fats_g}g

NUTRITIONAL AUDITING MATRIX & DIETARY BLUEPRINTS:
---
{nutrition_guidelines}
---

DRAFT MEAL PLAN TO EVALUATE:
{draft}

EVALUATION CRITERIA:
1. DAILY FOUR-MEAL TIMELINE: Does the plan utilize the 4-meal metabolic schedule (Metabolic Inception, glycogen-saturating Pre-Workout, insulin-spiking Post-Workout, slow-digesting Nocturnal)?
2. MACRO ACCURACY: Do the daily totals hit within ±50 kcal and ±5g per macro?
3. HYDRATION & SODIUM: Is a realistic hydration_target_L provided (complying with training volumes and sodium dissolved targets)?
4. INGREDIENT INCOMPATIBILITIES: Cross-reference user's listed GI issues/allergies. Ensure no dairy/whey or gluten is programmed if flagged in client profile.
5. MICRONUTRIENTS: Are Omega-3, Magnesium Glycinate, and Vitamin D3+K2 correctly integrated into meal notes?

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
