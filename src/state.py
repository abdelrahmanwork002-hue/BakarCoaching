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

class MacroStrategy(BaseModel):
    target_calories: int = Field(description="Daily caloric target")
    protein_g: int = Field(description="Daily protein target in grams")
    carbs_g: int = Field(description="Daily carbohydrate target in grams")
    fats_g: int = Field(description="Daily fat target in grams")
    training_split: str = Field(description="High-level description of the weekly training split")
    specialist_routes: List[str] = Field(description="List of specialists to engage, e.g., ['Gym', 'Yoga']")

class WorkoutSession(BaseModel):
    day: str = Field(description="Day of the week")
    focus: str = Field(description="Primary focus (e.g., Upper Body, Core, Flexibility)")
    exercises: List[Dict[str, str]] = Field(description="List of exercises with sets and reps")
    duration_mins: int = Field(description="Estimated duration in minutes")

class FitnessPlan(BaseModel):
    gym_sessions: List[WorkoutSession] = Field(default_factory=list)
    yoga_sessions: List[WorkoutSession] = Field(default_factory=list)
    calisthenics_sessions: List[WorkoutSession] = Field(default_factory=list)

class Meal(BaseModel):
    meal_name: str = Field(description="Breakfast, Lunch, Dinner, Snack")
    description: str = Field(description="Description of the meal")
    calories: int = Field(description="Estimated calories")
    protein_g: int = Field(description="Protein in grams")
    carbs_g: int = Field(description="Carbs in grams")
    fats_g: int = Field(description="Fats in grams")

class NutritionPlan(BaseModel):
    daily_meals: List[Meal] = Field(default_factory=list)
    hydration_target_L: float = Field(description="Daily hydration target in liters")

class ValidationLog(BaseModel):
    domain: str = Field(description="Domain being validated (e.g., Gym, Nutrition)")
    provider_creator: str = Field(description="LLM provider used for creation")
    provider_checker: str = Field(description="LLM provider used for checking")
    status: str = Field(description="Approved or Rejected")
    feedback: str = Field(description="Feedback or critique from the checker")
    attempt: int = Field(description="Retry attempt number")

class ProgressUpdate(BaseModel):
    date: str = Field(description="Date of the update")
    weight_kg: float = Field(description="Current weight in kg")
    adherence_score: int = Field(description="Self-reported adherence score (1-10)")
    notes: str = Field(description="Any specific notes from the user")

# --- LangGraph State Definition ---

def merge_validation_logs(existing: List[ValidationLog], new: List[ValidationLog]) -> List[ValidationLog]:
    return existing + new

class AgentState(TypedDict):
    # Core Data
    user_profile: Optional[UserProfile]
    macro_strategy: Optional[MacroStrategy]
    fitness_plan: FitnessPlan
    nutrition_plan: Optional[NutritionPlan]
    
    # Progress & Audit
    validation_logs: Annotated[List[ValidationLog], merge_validation_logs]
    progress_history: List[ProgressUpdate]
    
    # Validation Loop Tracking
    domain_retries: Dict[str, int]
    current_rejections: Dict[str, str]
