from typing import TypedDict, List, Dict, Optional, Annotated
from pydantic import BaseModel, Field
import operator

# --- Pydantic Data Models ---

class UserProfile(BaseModel):
    user_id: str = Field(description="Unique identifier for the user")
    age: int = Field(description="Age of the user")
    weight_kg: float = Field(description="Current weight in kg")
    target_weight_kg: float = Field(description="Target weight in kg")
    activity_level: str = Field(description="Sedentary, Light, Moderate, Active, Very Active")
    primary_goal: str = Field(description="Muscle Gain, Weight Loss, Maintenance, Endurance")
    injuries: List[str] = Field(default_factory=list, description="List of current injuries or limitations")
    experience_level: str = Field(description="Beginner, Intermediate, Advanced")
    preferred_training_types: List[str] = Field(
        default_factory=lambda: ["Gym", "Yoga", "Calisthenics"],
        description="Training types the user explicitly wants: subset of ['Gym', 'Yoga', 'Calisthenics']"
    )

class MacroStrategy(BaseModel):
    target_calories: int = Field(description="Daily caloric target")
    protein_g: int = Field(description="Daily protein target in grams")
    carbs_g: int = Field(description="Daily carbohydrate target in grams")
    fats_g: int = Field(description="Daily fat target in grams")
    training_split: str = Field(description="High-level description of the weekly training split")
    specialist_directives: Dict[str, str] = Field(
        description="Dict mapping each specialist to activate (Gym, Yoga, Calisthenics) to a specific focused coaching mandate. "
                    "Keys must only be from: 'Gym', 'Yoga', 'Calisthenics'. "
                    "Example: {'Gym': 'Focus on lower body compounds, avoid spinal loading', 'Yoga': 'Prioritize lumbar decompression'}"
    )

class Exercise(BaseModel):
    """Enriched exercise schema with full training prescription details."""
    name: str = Field(default="", description="Name")
    sets: int = Field(default=3, description="Sets")
    reps: str = Field(default="", description="Reps")
    rest_seconds: int = Field(default=60, description="Rest seconds")
    warmup_sets: int = Field(default=0, description="Warmup sets")
    tempo: str = Field(default="2-0-2", description="Tempo")
    demo_url: str = Field(default="", description="YouTube URL")
    muscles_goal: str = Field(default="", description="Muscles targeted")
    notes: Optional[str] = Field(default=None, description="Injury/safety notes")

class WorkoutSession(BaseModel):
    day: str = Field(description="Day")
    focus: str = Field(description="Focus")
    exercises: List[Exercise] = Field(default_factory=list, description="Exercises")
    duration_mins: int = Field(default=60, description="Duration in minutes")

class FitnessPlan(BaseModel):
    gym_sessions: List[WorkoutSession] = Field(default_factory=list)
    yoga_sessions: List[WorkoutSession] = Field(default_factory=list)
    calisthenics_sessions: List[WorkoutSession] = Field(default_factory=list)

class Meal(BaseModel):
    meal_name: str = Field(description="Name")
    description: str = Field(description="Description")
    calories: int = Field(description="Calories")
    protein_g: int = Field(description="Protein")
    carbs_g: int = Field(description="Carbs")
    fats_g: int = Field(description="Fats")

class NutritionPlan(BaseModel):
    daily_meals: List[Meal] = Field(default_factory=list)
    hydration_target_L: float = Field(description="Hydration L")

class ValidationLog(BaseModel):
    domain: str = Field(description="Domain being validated (e.g., Gym, Nutrition)")
    provider_creator: str = Field(description="LLM provider used for creation")
    provider_checker: str = Field(description="LLM provider used for checking")
    status: str = Field(description="Approved, Rejected, or Modified")
    feedback: str = Field(description="Feedback or critique from the checker")
    attempt: int = Field(description="Retry attempt number")

class ProgressUpdate(BaseModel):
    date: str = Field(description="Date of the update")
    weight_kg: float = Field(description="Current weight in kg")
    adherence_score: int = Field(description="Self-reported adherence score (1-10)")
    notes: str = Field(description="Any specific notes from the user")

class TrackingStrategy(BaseModel):
    """Output of the Tracking Coach — a holistic implementation roadmap."""
    weekly_checkin_metrics: List[str] = Field(
        description="Metrics the user should track weekly (e.g. 'Weight (kg)', 'Adherence Score 1-10', 'Sleep Quality')"
    )
    implementation_tips: List[str] = Field(
        description="Practical tips for implementing the plan (e.g. 'Schedule gym on Mon/Wed/Fri', 'Do yoga on rest days as active recovery')"
    )
    milestone_targets: List[str] = Field(
        description="Progressive weekly/monthly milestones (e.g. 'Week 2: Lose 0.5kg', 'Week 4: Complete full push-up', 'Month 2: Run 5km')"
    )
    red_flag_warnings: List[str] = Field(
        description="Injury or safety signals to watch for (e.g. 'Stop immediately if lower back pain worsens', 'Skip session if dizzy')"
    )
    coach_notes: str = Field(
        description="Free-text overall coaching synthesis — motivation, key priorities, and strategy overview"
    )

# --- LangGraph State Reducers ---

def merge_validation_logs(existing: List[ValidationLog], new: List[ValidationLog]) -> List[ValidationLog]:
    return existing + new

def merge_dicts(existing: dict, new: dict) -> dict:
    res = existing.copy() if existing else {}
    if new:
        for k, v in new.items():
            if v is None:
                res.pop(k, None)
            else:
                res[k] = v
    return res

def merge_fitness_plan(existing: FitnessPlan, new: FitnessPlan) -> FitnessPlan:
    """
    Accumulates fitness sessions across parallel branches.
    When Gym, Yoga, and Calisthenics branches all write to fitness_plan,
    each write is merged additively — no branch overwrites the others.
    Sessions from the new plan take priority if non-empty.
    """
    if existing is None:
        return new
    if new is None:
        return existing
    return FitnessPlan(
        gym_sessions=new.gym_sessions if new.gym_sessions else existing.gym_sessions,
        yoga_sessions=new.yoga_sessions if new.yoga_sessions else existing.yoga_sessions,
        calisthenics_sessions=new.calisthenics_sessions if new.calisthenics_sessions else existing.calisthenics_sessions,
    )

# --- LangGraph State Definition ---

class AgentState(TypedDict):
    # Core Data
    user_profile: Optional[UserProfile]
    macro_strategy: Optional[MacroStrategy]
    fitness_plan: Annotated[FitnessPlan, merge_fitness_plan]
    nutrition_plan: Optional[NutritionPlan]
    tracking_strategy: Optional[TrackingStrategy]

    # Progress & Audit
    validation_logs: Annotated[List[ValidationLog], merge_validation_logs]
    progress_history: List[ProgressUpdate]

    # Creator Drafts (initial generation)
    draft_gym: Optional[List[WorkoutSession]]
    draft_yoga: Optional[List[WorkoutSession]]
    draft_calisthenics: Optional[List[WorkoutSession]]
    draft_nutrition: Optional[NutritionPlan]

    # Modifier Drafts (post-checker corrections)
    modified_gym: Optional[List[WorkoutSession]]
    modified_yoga: Optional[List[WorkoutSession]]
    modified_calisthenics: Optional[List[WorkoutSession]]
    modified_nutrition: Optional[NutritionPlan]

    # Approved (passed checker)
    approved_gym: Optional[List[WorkoutSession]]
    approved_yoga: Optional[List[WorkoutSession]]
    approved_calisthenics: Optional[List[WorkoutSession]]

    # Validation Loop Tracking
    domain_retries: Annotated[Dict[str, int], merge_dicts]
    current_rejections: Annotated[Dict[str, str], merge_dicts]
