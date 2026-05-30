import os
import json
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class ExerciseLibraryItem(BaseModel):
    id: str = Field(description="Unique snake_case identifier")
    name: str = Field(description="Full name of the exercise")
    description: str = Field(description="Detailed instructions / description")
    targeted_muscles: List[str] = Field(description="Muscles targeted, e.g. ['Chest', 'Triceps']")
    muscle_focus: Dict[str, List[str]] = Field(
        description="For each targeted muscle, list if it's 'Strength', 'Mobility', or both. E.g. {'Chest': ['Strength']}"
    )
    training_types: List[str] = Field(description="Training types: subset of ['Gym', 'Calisthenics', 'Yoga']")
    demo_url: str = Field(description="Clickable link or video URL for this exercise")
    levels: List[str] = Field(description="Suitable experience levels: subset of ['Beginner', 'Intermediate', 'Advanced']")
    next_level_progressions: List[str] = Field(default_factory=list, description="List of exercise names/IDs for next progression level")

LIBRARY_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exercise_library.json")

DEFAULT_EXERCISES = [
    {
        "id": "bench_press",
        "name": "Barbell Bench Press",
        "description": "Lie on a flat bench, grip the barbell slightly wider than shoulder-width, lower the bar to your chest, and press it back up.",
        "targeted_muscles": ["Chest", "Triceps", "Shoulders"],
        "muscle_focus": {
            "Chest": ["Strength"],
            "Triceps": ["Strength"],
            "Shoulders": ["Strength"]
        },
        "training_types": ["Gym"],
        "demo_url": "https://www.youtube.com/results?search_query=barbell+bench+press+form+tutorial",
        "levels": ["Intermediate", "Advanced"],
        "next_level_progressions": ["Incline Bench Press", "Dumbbell Flys"]
    },
    {
        "id": "barbell_squat",
        "name": "Barbell Back Squat",
        "description": "Place a barbell on your upper back, stand with feet shoulder-width apart, bend at the hips and knees to lower down until thighs are parallel to the floor, then stand back up.",
        "targeted_muscles": ["Quads", "Glutes", "Hamstrings", "Core"],
        "muscle_focus": {
            "Quads": ["Strength"],
            "Glutes": ["Strength"],
            "Hamstrings": ["Strength", "Mobility"],
            "Core": ["Strength"]
        },
        "training_types": ["Gym"],
        "demo_url": "https://www.youtube.com/results?search_query=barbell+back+squat+form+tutorial",
        "levels": ["Intermediate", "Advanced"],
        "next_level_progressions": ["Pistol Squat", "Front Squat"]
    },
    {
        "id": "romanian_deadlift",
        "name": "Barbell Romanian Deadlift",
        "description": "Stand holding a barbell at hip height, hinge at the hips, keeping your back flat and knees slightly bent, lower the barbell along your thighs until you feel a stretch in your hamstrings, then return to start.",
        "targeted_muscles": ["Hamstrings", "Glutes", "Back"],
        "muscle_focus": {
            "Hamstrings": ["Strength", "Mobility"],
            "Glutes": ["Strength"],
            "Back": ["Strength"]
        },
        "training_types": ["Gym"],
        "demo_url": "https://www.youtube.com/results?search_query=romanian+deadlift+form+tutorial",
        "levels": ["Intermediate", "Advanced"],
        "next_level_progressions": ["Barbell Deadlift"]
    },
    {
        "id": "push_up",
        "name": "Standard Push-Up",
        "description": "Start in a high plank position, lower your chest to the floor by bending your elbows, then push through your chest and triceps to return to the starting position.",
        "targeted_muscles": ["Chest", "Triceps", "Shoulders", "Core"],
        "muscle_focus": {
            "Chest": ["Strength"],
            "Triceps": ["Strength"],
            "Shoulders": ["Strength"],
            "Core": ["Strength"]
        },
        "training_types": ["Calisthenics", "Gym"],
        "demo_url": "https://www.youtube.com/results?search_query=perfect+push+up+form+tutorial",
        "levels": ["Beginner", "Intermediate"],
        "next_level_progressions": ["Decline Push-Up", "Archer Push-Up", "Dips"]
    },
    {
        "id": "pull_up",
        "name": "Standard Pull-Up",
        "description": "Hang from a pull-up bar with an overhand grip wider than shoulder-width, pull your chest up to the bar by driving your elbows down, then slowly lower back down.",
        "targeted_muscles": ["Back", "Biceps", "Core"],
        "muscle_focus": {
            "Back": ["Strength", "Mobility"],
            "Biceps": ["Strength"],
            "Core": ["Strength"]
        },
        "training_types": ["Calisthenics", "Gym"],
        "demo_url": "https://www.youtube.com/results?search_query=how+to+do+a+pull+up+tutorial",
        "levels": ["Intermediate", "Advanced"],
        "next_level_progressions": ["Weighted Pull-Up", "Muscle-Up"]
    },
    {
        "id": "dips",
        "name": "Parallel Bar Dips",
        "description": "Support your bodyweight on parallel bars, bend your elbows to lower your shoulders below elbow depth, keeping a slight forward lean, then push back up to full lockout.",
        "targeted_muscles": ["Chest", "Triceps", "Shoulders"],
        "muscle_focus": {
            "Chest": ["Strength"],
            "Triceps": ["Strength"],
            "Shoulders": ["Strength", "Mobility"]
        },
        "training_types": ["Calisthenics", "Gym"],
        "demo_url": "https://www.youtube.com/results?search_query=parallel+bar+dips+form+tutorial",
        "levels": ["Intermediate", "Advanced"],
        "next_level_progressions": ["Weighted Dips", "Muscle-Up"]
    },
    {
        "id": "pike_push_up",
        "name": "Pike Push-Up",
        "description": "Get into a push-up position and walk your feet forward, raising your hips into an inverted 'V' shape. Lower your head towards the ground between your hands, then push back up.",
        "targeted_muscles": ["Shoulders", "Triceps", "Core"],
        "muscle_focus": {
            "Shoulders": ["Strength", "Mobility"],
            "Triceps": ["Strength"],
            "Core": ["Strength"]
        },
        "training_types": ["Calisthenics"],
        "demo_url": "https://www.youtube.com/results?search_query=pike+push+up+form+tutorial",
        "levels": ["Intermediate"],
        "next_level_progressions": ["Handstand Push-Up"]
    },
    {
        "id": "pistol_squat",
        "name": "Pistol Squat",
        "description": "Stand on one leg, extend the other leg straight in front of you, lower down into a full squat on the standing leg, then drive back up to a standing position.",
        "targeted_muscles": ["Quads", "Glutes", "Hamstrings", "Calves", "Core"],
        "muscle_focus": {
            "Quads": ["Strength"],
            "Glutes": ["Strength"],
            "Hamstrings": ["Mobility"],
            "Calves": ["Mobility"],
            "Core": ["Strength"]
        },
        "training_types": ["Calisthenics", "Gym"],
        "demo_url": "https://www.youtube.com/results?search_query=pistol+squat+form+progression+tutorial",
        "levels": ["Advanced"],
        "next_level_progressions": ["Weighted Pistol Squat"]
    },
    {
        "id": "downward_dog",
        "name": "Downward-Facing Dog Pose",
        "description": "From all fours, tuck your toes, raise your hips high, and extend your arms and legs to form an inverted 'V' shape, pushing chest towards thighs.",
        "targeted_muscles": ["Hamstrings", "Shoulders", "Calves", "Back"],
        "muscle_focus": {
            "Hamstrings": ["Mobility"],
            "Shoulders": ["Mobility"],
            "Calves": ["Mobility"],
            "Back": ["Mobility"]
        },
        "training_types": ["Yoga"],
        "demo_url": "https://www.youtube.com/results?search_query=downward+facing+dog+form+tutorial",
        "levels": ["Beginner", "Intermediate"],
        "next_level_progressions": ["Three-Legged Downward Dog"]
    },
    {
        "id": "cobra_pose",
        "name": "Cobra Pose (Bhujangasana)",
        "description": "Lie prone, hands under shoulders, press the tops of your feet into the floor, inhale and lift your chest off the mat while keeping your pelvis on the floor.",
        "targeted_muscles": ["Back", "Core", "Shoulders"],
        "muscle_focus": {
            "Back": ["Mobility", "Strength"],
            "Core": ["Mobility"],
            "Shoulders": ["Mobility"]
        },
        "training_types": ["Yoga"],
        "demo_url": "https://www.youtube.com/results?search_query=cobra+pose+yoga+form+tutorial",
        "levels": ["Beginner"],
        "next_level_progressions": ["Upward-Facing Dog Pose"]
    },
    {
        "id": "crow_pose",
        "name": "Crow Pose (Bakasana)",
        "description": "Squat down, place hands flat on the floor shoulder-width apart, place knees against upper triceps, lean forward shifting weight to hands, and lift feet off the ground.",
        "targeted_muscles": ["Shoulders", "Triceps", "Core", "Wrists/Forearms"],
        "muscle_focus": {
            "Shoulders": ["Strength"],
            "Triceps": ["Strength"],
            "Core": ["Strength"],
            "Wrists/Forearms": ["Strength", "Mobility"]
        },
        "training_types": ["Yoga", "Calisthenics"],
        "demo_url": "https://www.youtube.com/results?search_query=crow+pose+yoga+step+by+step+tutorial",
        "levels": ["Intermediate", "Advanced"],
        "next_level_progressions": ["Handstand", "Side Crow Pose"]
    },
    {
        "id": "pigeon_pose",
        "name": "Pigeon Pose (Eka Pada Rajakapotasana)",
        "description": "Bring one knee forward and place it behind its wrist, lay the shin down, extend the other leg straight behind you, square your hips, and fold forward over the front leg.",
        "targeted_muscles": ["Glutes", "Hips", "Back"],
        "muscle_focus": {
            "Glutes": ["Mobility"],
            "Hips": ["Mobility"],
            "Back": ["Mobility"]
        },
        "training_types": ["Yoga"],
        "demo_url": "https://www.youtube.com/results?search_query=pigeon+pose+yoga+form+tutorial",
        "levels": ["Beginner", "Intermediate"],
        "next_level_progressions": ["King Pigeon Pose"]
    },
    {
        "id": "tree_pose",
        "name": "Tree Pose (Vrikshasana)",
        "description": "Stand tall, shift weight to one foot, place the sole of the other foot on your inner thigh or calf (never the knee), bring hands together at heart center, and extend arms up.",
        "targeted_muscles": ["Core", "Calves", "Glutes", "Hips"],
        "muscle_focus": {
            "Core": ["Strength"],
            "Calves": ["Strength"],
            "Glutes": ["Strength"],
            "Hips": ["Mobility"]
        },
        "training_types": ["Yoga"],
        "demo_url": "https://www.youtube.com/results?search_query=tree+pose+yoga+balance+tutorial",
        "levels": ["Beginner"],
        "next_level_progressions": ["Eagle Pose"]
    },
    {
        "id": "l_sit",
        "name": "L-Sit",
        "description": "Sit on the floor or parallel bars, place hands flat, press down to lift your hips off the ground, and extend legs straight out parallel to the floor forming an 'L' shape.",
        "targeted_muscles": ["Core", "Shoulders", "Triceps", "Hamstrings"],
        "muscle_focus": {
            "Core": ["Strength"],
            "Shoulders": ["Strength"],
            "Triceps": ["Strength"],
            "Hamstrings": ["Mobility"]
        },
        "training_types": ["Calisthenics"],
        "demo_url": "https://www.youtube.com/results?search_query=l+sit+form+progression+tutorial",
        "levels": ["Intermediate", "Advanced"],
        "next_level_progressions": ["V-Sit"]
    },
    {
        "id": "archer_push_up",
        "name": "Archer Push-Up",
        "description": "Adopt a wide push-up stance. As you lower down, slide your bodyweight to one side, bending that elbow, while keeping the other arm straight. Push back up and alternate sides.",
        "targeted_muscles": ["Chest", "Triceps", "Shoulders", "Core"],
        "muscle_focus": {
            "Chest": ["Strength"],
            "Triceps": ["Strength"],
            "Shoulders": ["Strength", "Mobility"],
            "Core": ["Strength"]
        },
        "training_types": ["Calisthenics"],
        "demo_url": "https://www.youtube.com/results?search_query=archer+push+up+form+progression",
        "levels": ["Intermediate", "Advanced"],
        "next_level_progressions": ["One-Arm Push-Up"]
    },
    {
        "id": "dumbbell_lateral_raise",
        "name": "Dumbbell Lateral Raise",
        "description": "Stand holding dumbbells at your sides, raise the weights out to your sides until your arms are parallel to the floor, with elbows slightly bent, then lower slowly.",
        "targeted_muscles": ["Shoulders"],
        "muscle_focus": {
            "Shoulders": ["Strength", "Mobility"]
        },
        "training_types": ["Gym"],
        "demo_url": "https://www.youtube.com/results?search_query=dumbbell+lateral+raise+form+tutorial",
        "levels": ["Beginner", "Intermediate"],
        "next_level_progressions": ["Cable Lateral Raise"]
    },
    {
        "id": "warrior_ii",
        "name": "Warrior II Pose (Virabhadrasana II)",
        "description": "Step feet wide apart, turn front foot out 90 degrees and back foot slightly in, bend front knee until thigh is parallel to floor, and extend arms out parallel to floor.",
        "targeted_muscles": ["Quads", "Glutes", "Shoulders", "Hips"],
        "muscle_focus": {
            "Quads": ["Strength"],
            "Glutes": ["Strength"],
            "Shoulders": ["Strength", "Mobility"],
            "Hips": ["Mobility"]
        },
        "training_types": ["Yoga"],
        "demo_url": "https://www.youtube.com/results?search_query=warrior+2+yoga+pose+tutorial",
        "levels": ["Beginner", "Intermediate"],
        "next_level_progressions": ["Reverse Warrior", "Extended Side Angle"]
    },
    {
        "id": "face_pulls",
        "name": "Cable Face Pull",
        "description": "Set a cable pulley at upper-chest height with a rope attachment. Pull the rope towards your face, pulling the hands apart and rotating wrists out at the finish.",
        "targeted_muscles": ["Shoulders", "Back"],
        "muscle_focus": {
            "Shoulders": ["Strength", "Mobility"],
            "Back": ["Strength", "Mobility"]
        },
        "training_types": ["Gym"],
        "demo_url": "https://www.youtube.com/results?search_query=cable+face+pull+form+tutorial",
        "levels": ["Beginner", "Intermediate"],
        "next_level_progressions": ["Dumbbell Rear Delt Fly"]
    },
    {
        "id": "childs_pose",
        "name": "Child's Pose (Balasana)",
        "description": "Kneel on the floor, touch big toes together, sit on your heels, separate knees, and fold your torso forward extending arms in front of you resting forehead on mat.",
        "targeted_muscles": ["Back", "Shoulders", "Hips"],
        "muscle_focus": {
            "Back": ["Mobility"],
            "Shoulders": ["Mobility"],
            "Hips": ["Mobility"]
        },
        "training_types": ["Yoga"],
        "demo_url": "https://www.youtube.com/results?search_query=childs+pose+yoga+tutorial",
        "levels": ["Beginner"],
        "next_level_progressions": ["Extended Puppy Pose"]
    },
    {
        "id": "muscle_up",
        "name": "Bar Muscle-Up",
        "description": "Hang from a bar, pull your chest explosively up and over the bar, transitioning your wrists and pushing through the triceps to extend your arms into lockout at the top.",
        "targeted_muscles": ["Back", "Triceps", "Chest", "Biceps", "Core"],
        "muscle_focus": {
            "Back": ["Strength"],
            "Triceps": ["Strength"],
            "Chest": ["Strength"],
            "Biceps": ["Strength"],
            "Core": ["Strength"]
        },
        "training_types": ["Calisthenics"],
        "demo_url": "https://www.youtube.com/results?search_query=bar+muscle+up+progression+step+by+step",
        "levels": ["Advanced"],
        "next_level_progressions": ["Strict Muscle-Up"]
    }
]

def load_exercise_library() -> List[ExerciseLibraryItem]:
    """Loads all exercises from the library, initializing defaults if missing."""
    if not os.path.exists(LIBRARY_FILE_PATH):
        save_exercise_library([ExerciseLibraryItem(**ex) for ex in DEFAULT_EXERCISES])
    
    try:
        with open(LIBRARY_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [ExerciseLibraryItem(**item) for item in data]
    except Exception as e:
        print(f"Error loading exercise library: {e}. Falling back to default list.")
        return [ExerciseLibraryItem(**ex) for ex in DEFAULT_EXERCISES]

def save_exercise_library(items: List[ExerciseLibraryItem]) -> None:
    """Saves all exercises to the JSON library."""
    with open(LIBRARY_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump([item.model_dump() for item in items], f, indent=4, ensure_ascii=False)

def add_or_update_exercise(item: ExerciseLibraryItem) -> List[ExerciseLibraryItem]:
    """Adds a new exercise or updates an existing one by matching its snake_case ID or name."""
    library = load_exercise_library()
    updated = False
    
    for i, ex in enumerate(library):
        if ex.id == item.id or ex.name.lower() == item.name.lower():
            library[i] = item
            updated = True
            break
            
    if not updated:
        library.append(item)
        
    save_exercise_library(library)
    return library

def query_exercises(
    training_type: Optional[str] = None,
    muscle: Optional[str] = None,
    level: Optional[str] = None,
    focus: Optional[str] = None
) -> List[ExerciseLibraryItem]:
    """Filters the exercise library based on criteria."""
    library = load_exercise_library()
    filtered = []
    
    for ex in library:
        if training_type and all(t.lower() != training_type.lower() for t in ex.training_types):
            continue
        if muscle and all(m.lower() != muscle.lower() for m in ex.targeted_muscles):
            continue
        if level and all(l.lower() != level.lower() for l in ex.levels):
            continue
        if focus and muscle:
            # Check if focus (Strength/Mobility) matches for the given muscle
            muscle_match = False
            for m, focuses in ex.muscle_focus.items():
                if m.lower() == muscle.lower() and focus.lower() in [f.lower() for f in focuses]:
                    muscle_match = True
                    break
            if not muscle_match:
                continue
        filtered.append(ex)
        
    return filtered
