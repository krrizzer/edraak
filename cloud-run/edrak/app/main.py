from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agents.root_agent import run_edraak_agent
from app.functions.mock_data import get_profile_by_id, get_profiles, get_transactions_by_user

#ss
class DecisionInput(BaseModel):
    user_id: str
    goal_type: str = Field(..., examples=["car"])
    goal_amount: float = Field(..., gt=0)
    monthly_installment: float = Field(..., ge=0)
    duration_months: int = Field(..., gt=0)
    down_payment: float = Field(0, ge=0)
    urgency: Literal["low", "medium", "high"] = "medium"


app = FastAPI(title="Edraak API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
assets_dir = static_dir / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "edraak"}


@app.get("/api/profiles")
def profiles():
    return get_profiles()


@app.get("/api/transactions/{user_id}")
def transactions(user_id: str):
    if not get_profile_by_id(user_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    return get_transactions_by_user(user_id)


@app.post("/api/analyze")
def analyze(decision_input: DecisionInput):
    profile = get_profile_by_id(decision_input.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    transactions_for_user = get_transactions_by_user(decision_input.user_id)
    return run_edraak_agent(profile, transactions_for_user, decision_input.model_dump())


@app.get("/{path:path}")
def serve_react_app(path: str):
    requested_file = static_dir / path
    index_file = static_dir / "index.html"

    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    if requested_file.is_file():
        return FileResponse(requested_file)
    if index_file.exists():
        return FileResponse(index_file)
    return {"service": "edraak", "ui": "not built"}
