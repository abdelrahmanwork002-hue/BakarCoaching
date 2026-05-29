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


@app.post("/api/onboard")
def onboard(req: OnboardRequest, background_tasks: BackgroundTasks):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_profile = UserProfile(
        user_id=thread_id,
        age=req.age,
        weight_kg=req.weight_kg,
        target_weight_kg=req.target_weight_kg,
        activity_level=req.activity_level,
        primary_goal=req.primary_goal,
        experience_level=req.experience_level,
        injuries=req.injuries
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

    # Macro strategy serialization
    macro = val.get("macro_strategy")
    if macro:
        macro = macro.model_dump() if hasattr(macro, "model_dump") else dict(macro)

    # Tracking strategy serialization
    tracking = val.get("tracking_strategy")
    if tracking:
        tracking = tracking.model_dump() if hasattr(tracking, "model_dump") else dict(tracking)

    # Validation logs serialization
    logs = []
    for log in val.get("validation_logs", []):
        logs.append(log.model_dump() if hasattr(log, "model_dump") else dict(log))

    # Determine status
    state_status = "completed"
    if next_node:
        if any(n.startswith("hitl_") or n == "pre_release_gate" for n in next_node):
            state_status = "paused"
        else:
            state_status = "running"

    # Rejections (filter out None values)
    raw_rejections = val.get("current_rejections", {})
    rejections = {k: v for k, v in raw_rejections.items() if v is not None}

    return {
        "status": state_status,
        "next_nodes": next_node,
        "rejections": rejections,
        "validation_logs": logs,
        "macro_strategy": macro,
        "tracking_strategy": tracking,
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
