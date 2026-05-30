import sys
import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uuid

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph import build_graph
from src.state import UserProfile, AgentState, FitnessPlan
from src.excel_engine import export_plans_to_excel
from langgraph.types import Command

app = FastAPI(title="AI Coaching Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)

graph = build_graph()


class OnboardRequest(BaseModel):
    age: int
    weight_kg: float
    target_weight_kg: float
    activity_level: str
    primary_goal: str
    experience_level: str
    injuries: list[str]
    preferred_training_types: list[str] = ["Gym", "Yoga", "Calisthenics"]


def _serialize(obj):
    """Recursively serialize Pydantic models and lists."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


@app.post("/api/onboard")
def onboard(req: OnboardRequest, background_tasks: BackgroundTasks):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Validate training types
    valid_types = {"Gym", "Yoga", "Calisthenics"}
    preferred = [t for t in req.preferred_training_types if t in valid_types]
    if not preferred:
        preferred = ["Gym"]  # fallback

    initial_profile = UserProfile(
        user_id=thread_id,
        age=req.age,
        weight_kg=req.weight_kg,
        target_weight_kg=req.target_weight_kg,
        activity_level=req.activity_level,
        primary_goal=req.primary_goal,
        experience_level=req.experience_level,
        injuries=req.injuries,
        preferred_training_types=preferred
    )

    initial_state = AgentState(
        user_profile=initial_profile,
        macro_strategy=None,
        fitness_plan=FitnessPlan(),
        nutrition_plan=None,
        tracking_strategy=None,
        validation_logs=[],
        progress_history=[],
        domain_retries={},
        current_rejections={},
        draft_gym=None,
        draft_yoga=None,
        draft_calisthenics=None,
        draft_nutrition=None,
        modified_gym=None,
        modified_yoga=None,
        modified_calisthenics=None,
        modified_nutrition=None,
        approved_gym=None,
        approved_yoga=None,
        approved_calisthenics=None
    )

    def run_graph():
        for _ in graph.stream(initial_state, config=config, stream_mode="values"):
            pass

    background_tasks.add_task(run_graph)
    return {"thread_id": thread_id}


@app.get("/api/status/{thread_id}")
def get_status(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = graph.get_state(config)
    except Exception as e:
        return {"status": "error", "message": str(e)}

    if not snapshot or not snapshot.values:
        return {"status": "not_found"}

    next_node = snapshot.next
    val = snapshot.values

    # Determine status
    state_status = "completed"
    if next_node:
        if any(n.startswith("hitl_") or n == "pre_release_gate" for n in next_node):
            state_status = "paused"
        else:
            state_status = "running"

    # Serialize macro strategy
    macro = _serialize(val.get("macro_strategy"))

    # Serialize tracking strategy
    tracking = _serialize(val.get("tracking_strategy"))

    # Serialize full fitness plan (all sessions + exercises)
    fitness_plan_raw = val.get("fitness_plan")
    fitness_plan = _serialize(fitness_plan_raw)

    # Serialize nutrition plan
    nutrition_plan = _serialize(val.get("nutrition_plan"))

    # Serialize validation logs
    logs = [_serialize(log) for log in val.get("validation_logs", [])]

    # Rejections (filter out None values)
    raw_rejections = val.get("current_rejections", {})
    rejections = {k: v for k, v in raw_rejections.items() if v is not None}

    # User profile (for displaying preferred types etc.)
    user_profile = _serialize(val.get("user_profile"))

    return {
        "status": state_status,
        "next_nodes": next_node,
        "rejections": rejections,
        "validation_logs": logs,
        "macro_strategy": macro,
        "tracking_strategy": tracking,
        "fitness_plan": fitness_plan,
        "nutrition_plan": nutrition_plan,
        "user_profile": user_profile,
    }


@app.post("/api/resume/{thread_id}")
def resume_graph(thread_id: str, background_tasks: BackgroundTasks):
    config = {"configurable": {"thread_id": thread_id}}

    def run_resume():
        for _ in graph.stream(Command(resume="admin_override"), config=config, stream_mode="values"):
            pass

    background_tasks.add_task(run_resume)
    return {"status": "resumed"}


@app.get("/api/download/{thread_id}")
def download_excel(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)

    if not snapshot or snapshot.next:
        raise HTTPException(status_code=400, detail="Plan not completed yet.")

    final_state = snapshot.values
    filepath = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        f"Final_Client_Plan_{thread_id}.xlsx"
    )

    export_plans_to_excel(
        fitness_plan=final_state.get("fitness_plan"),
        nutrition_plan=final_state.get("nutrition_plan"),
        tracking_strategy=final_state.get("tracking_strategy"),
        filepath=filepath
    )

    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="My_Coaching_Plan.xlsx"
    )


# Mount static frontend last so API routes take priority
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
