from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agents.root_agent import run_edraak_agent
from app.functions.bigquery_data import (
    get_customer_by_id_from_bigquery,
    get_customer_by_username_from_bigquery,
    get_loans_from_bigquery,
    get_transactions_from_bigquery,
    get_user_profile_from_bigquery,
    save_decision_request_to_bigquery,
    save_recommendation_to_bigquery,
)
from app.functions.load_user_profiles import build_user_profile, load_all_user_profiles
from app.functions.mock_data import save_user_profile


class LoginInput(BaseModel):
    username: str = Field(..., min_length=1, examples=["fahad"])


class DecisionInput(BaseModel):
    customer_id: str
    goal_type: str = Field(..., examples=["car"])
    goal_amount: float = Field(..., gt=0)
    monthly_installment: float = Field(..., gt=0)
    duration_months: int = Field(..., gt=0)
    down_payment: float = Field(0, ge=0)
    urgency: Literal["low", "medium", "high"] = "medium"


app = FastAPI(title="Edraak API", version="0.2.0")

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


@app.post("/api/login")
def login(login_input: LoginInput):
    customer = get_customer_by_username_from_bigquery(login_input.username)
    if not customer:
        raise HTTPException(status_code=404, detail="Username not found")
    return {
        "customer_id": customer["customer_id"],
        "username_en": customer["username_en"],
        "ar_name": customer["ar_name"],
        "en_name": customer["en_name"],
    }


@app.post("/api/admin/load-user-profiles")
def load_user_profiles():
    profiles = load_all_user_profiles()
    return {"status": "completed", "profiles_loaded": len(profiles)}


@app.get("/api/customer/{customer_id}")
def get_customer(customer_id: str):
    customer = get_customer_by_id_from_bigquery(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.get("/api/customer/{customer_id}/transactions")
def get_customer_transactions(customer_id: str):
    if not get_customer_by_id_from_bigquery(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    return get_transactions_from_bigquery(customer_id)


@app.get("/api/customer/{customer_id}/loans")
def get_customer_loans(customer_id: str):
    if not get_customer_by_id_from_bigquery(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    return get_loans_from_bigquery(customer_id)


@app.get("/api/customer/{customer_id}/profile")
def get_customer_profile(customer_id: str):
    customer = get_customer_by_id_from_bigquery(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    profile = get_user_profile_from_bigquery(customer_id)
    if profile:
        return profile

    transactions = get_transactions_from_bigquery(customer_id)
    loans = get_loans_from_bigquery(customer_id)
    profile = build_user_profile(customer, transactions, loans)
    save_user_profile(profile)
    return profile


@app.post("/api/analyze")
def analyze(decision_input: DecisionInput):
    decision = decision_input.model_dump()

    # Data collection happens before any agent runs.
    customer = get_customer_by_id_from_bigquery(decision_input.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    transactions = get_transactions_from_bigquery(decision_input.customer_id)
    loans = get_loans_from_bigquery(decision_input.customer_id)
    profile = get_user_profile_from_bigquery(decision_input.customer_id)
    if not profile:
        profile = build_user_profile(customer, transactions, loans)
        save_user_profile(profile)

    save_decision_request_to_bigquery(decision)

    result = run_edraak_agent(customer, transactions, loans, profile, decision)
    save_recommendation_to_bigquery(result)
    return result


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
