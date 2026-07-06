from pathlib import Path
import logging
import time
from uuid import uuid4
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agents.gemini_client import GeminiAgentError
from app.agents.root_agent import run_edraak_agent
from app.functions.bigquery_data import (
    get_customer_by_id_from_bigquery,
    get_customer_by_username_from_bigquery,
    get_loans_from_bigquery,
    get_transactions_from_bigquery,
    get_user_profile_from_bigquery,
    save_decision_request_to_bigquery,
    save_recommendation_to_bigquery,
    save_user_profile_to_bigquery,
)
from app.functions.profile_loader import build_user_profile_from_sources, load_user_profiles_from_bigquery


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("edraak.api")


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


class ProfileLoadInput(BaseModel):
    customer_id: str | None = None


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


@app.exception_handler(GeminiAgentError)
def gemini_agent_exception_handler(_request: Request, exc: GeminiAgentError):
    logger.error("request.failed source=gemini error=%s", exc)
    return JSONResponse(status_code=502, content={"detail": "Gemini agent failed", "error": str(exc)})


@app.exception_handler(RuntimeError)
def runtime_exception_handler(_request: Request, exc: RuntimeError):
    logger.error("request.failed source=runtime error=%s", exc)
    return JSONResponse(status_code=500, content={"detail": "Production configuration or storage failed", "error": str(exc)})


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "edraak"}


@app.post("/api/login")
def login(login_input: LoginInput):
    request_id = _request_id()
    start = time.perf_counter()
    logger.info("flow.login.submitted request_id=%s username=%s message=User submitted login form", request_id, login_input.username)
    customer = get_customer_by_username_from_bigquery(login_input.username)
    if not customer:
        logger.warning("flow.login.failed request_id=%s username=%s reason=not_found message=No customer found for username", request_id, login_input.username)
        raise HTTPException(status_code=404, detail="Username not found")
    logger.info(
        "flow.login.success request_id=%s customer_id=%s elapsed_ms=%s message=Login matched username to customer record",
        request_id,
        customer["customer_id"],
        _elapsed_ms(start),
    )
    return {
        "customer_id": customer["customer_id"],
        "username_en": customer["username_en"],
        "ar_name": customer["ar_name"],
        "en_name": customer["en_name"],
    }


@app.post("/api/admin/load-user-profiles")
def load_user_profiles(load_input: ProfileLoadInput | None = None):
    request_id = _request_id()
    start = time.perf_counter()
    customer_id = load_input.customer_id if load_input else None
    logger.info(
        "flow.admin.profile_loader.clicked request_id=%s customer_id=%s message=Admin requested user_profiles generation",
        request_id,
        customer_id or "ALL",
    )
    profiles = load_user_profiles_from_bigquery(customer_id)
    logger.info(
        "flow.admin.profile_loader.completed request_id=%s profiles_loaded=%s elapsed_ms=%s message=user_profiles generation finished",
        request_id,
        len(profiles),
        _elapsed_ms(start),
    )
    return {
        "status": "completed",
        "profiles_loaded": len(profiles),
        "customer_ids": [profile["customer_id"] for profile in profiles],
    }


@app.get("/api/customer/{customer_id}")
def get_customer(customer_id: str):
    logger.info("flow.customer.retrieve.start customer_id=%s message=Loading customer details from BigQuery", customer_id)
    customer = get_customer_by_id_from_bigquery(customer_id)
    if not customer:
        logger.warning("flow.customer.retrieve.failed customer_id=%s message=Customer not found", customer_id)
        raise HTTPException(status_code=404, detail="Customer not found")
    logger.info("flow.customer.retrieve.success customer_id=%s message=Customer details loaded", customer_id)
    return customer


@app.get("/api/customer/{customer_id}/transactions")
def get_customer_transactions(customer_id: str):
    logger.info("flow.transactions.retrieve.start customer_id=%s message=Loading transactions from BigQuery", customer_id)
    if not get_customer_by_id_from_bigquery(customer_id):
        logger.warning("transactions.get.customer_not_found customer_id=%s", customer_id)
        raise HTTPException(status_code=404, detail="Customer not found")
    transactions = get_transactions_from_bigquery(customer_id)
    logger.info("flow.transactions.retrieve.success customer_id=%s count=%s message=Transactions loaded", customer_id, len(transactions))
    return transactions


@app.get("/api/customer/{customer_id}/loans")
def get_customer_loans(customer_id: str):
    logger.info("flow.loans.retrieve.start customer_id=%s message=Loading active loans from BigQuery", customer_id)
    if not get_customer_by_id_from_bigquery(customer_id):
        logger.warning("loans.get.customer_not_found customer_id=%s", customer_id)
        raise HTTPException(status_code=404, detail="Customer not found")
    loans = get_loans_from_bigquery(customer_id)
    logger.info("flow.loans.retrieve.success customer_id=%s count=%s message=Active loans loaded", customer_id, len(loans))
    return loans


@app.get("/api/customer/{customer_id}/profile")
def get_customer_profile(customer_id: str):
    logger.info("flow.profile.retrieve.start customer_id=%s message=Loading derived user profile from BigQuery", customer_id)
    customer = get_customer_by_id_from_bigquery(customer_id)
    if not customer:
        logger.warning("profile.get.customer_not_found customer_id=%s", customer_id)
        raise HTTPException(status_code=404, detail="Customer not found")

    profile = get_user_profile_from_bigquery(customer_id)
    if profile:
        logger.info("flow.profile.retrieve.success customer_id=%s source=user_profiles message=Derived user profile loaded", customer_id)
        return profile

    logger.info(
        "flow.profile.generate_on_demand.start customer_id=%s message=No user_profiles row found; generating from real BigQuery source tables",
        customer_id,
    )
    transactions = get_transactions_from_bigquery(customer_id)
    loans = get_loans_from_bigquery(customer_id)
    profile = build_user_profile_from_sources(customer, transactions, loans)
    save_user_profile_to_bigquery(profile)
    logger.info(
        "flow.profile.generate_on_demand.completed customer_id=%s transactions=%s loans=%s message=Generated profile saved to user_profiles",
        customer_id,
        len(transactions),
        len(loans),
    )
    return profile

# start here
@app.post("/api/analyze")
def analyze(decision_input: DecisionInput):
    request_id = _request_id()
    start = time.perf_counter()
    decision = decision_input.model_dump()
    logger.info(
        "flow.analysis.clicked request_id=%s customer_id=%s goal_type=%s amount=%s installment=%s message=User submitted financial goal; starting analysis",
        request_id,
        decision_input.customer_id,
        decision_input.goal_type,
        decision_input.goal_amount,
        decision_input.monthly_installment,
    )

    logger.info("flow.analysis.data_collection.start request_id=%s message=Collecting required BigQuery tables before agents run", request_id)
    retrieval_start = time.perf_counter()
    logger.info("flow.analysis.data_collection.customer request_id=%s message=Loading customer row", request_id)
    customer = get_customer_by_id_from_bigquery(decision_input.customer_id)
    if not customer:
        logger.warning("analyze.customer_not_found request_id=%s customer_id=%s", request_id, decision_input.customer_id)
        raise HTTPException(status_code=404, detail="Customer not found")

    logger.info("flow.analysis.data_collection.transactions request_id=%s message=Loading transaction history", request_id)
    transactions = get_transactions_from_bigquery(decision_input.customer_id)
    logger.info("flow.analysis.data_collection.loans request_id=%s message=Loading active loans", request_id)
    loans = get_loans_from_bigquery(decision_input.customer_id)
    logger.info("flow.analysis.data_collection.profile request_id=%s message=Loading derived user profile", request_id)
    profile = get_user_profile_from_bigquery(decision_input.customer_id)
    if not profile:
        logger.info(
            "flow.analysis.profile_generate_on_demand.start request_id=%s customer_id=%s message=No user_profiles row found; generating from already loaded customer, transactions, and loans",
            request_id,
            decision_input.customer_id,
        )
        profile = build_user_profile_from_sources(customer, transactions, loans)
        save_user_profile_to_bigquery(profile)
        logger.info(
            "flow.analysis.profile_generate_on_demand.completed request_id=%s customer_id=%s message=Generated profile saved to user_profiles; continuing agent workflow",
            request_id,
            decision_input.customer_id,
        )
    logger.info(
        "flow.analysis.data_collection.completed request_id=%s customer_id=%s transactions=%s loans=%s profile_found=%s elapsed_ms=%s message=All source data loaded; agents can start",
        request_id,
        decision_input.customer_id,
        len(transactions),
        len(loans),
        bool(profile),
        _elapsed_ms(retrieval_start),
    )

    agent_start = time.perf_counter()
    logger.info("flow.analysis.agents.start request_id=%s message=Starting sequential agent workflow", request_id)
    try:
        result = run_edraak_agent(customer, transactions, loans, profile, decision)
    except ValueError as exc:
        logger.warning("analyze.validation_failed request_id=%s error=%s", request_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info(
        "flow.analysis.agents.completed request_id=%s recommendation=%s risk_score=%s elapsed_ms=%s message=Agents finished and produced recommendation",
        request_id,
        result["recommendation"],
        result["risk_score"],
        _elapsed_ms(agent_start),
    )

    save_start = time.perf_counter()
    logger.info("flow.analysis.storage.start request_id=%s message=Saving request and recommendation to storage-only BigQuery tables", request_id)
    decision_record = {**decision, "request_id": request_id}
    save_decision_request_to_bigquery(decision_record)
    save_recommendation_to_bigquery({**result, "request_id": request_id})
    logger.info("flow.analysis.storage.completed request_id=%s elapsed_ms=%s message=Storage tables updated", request_id, _elapsed_ms(save_start))
    logger.info("flow.analysis.completed request_id=%s elapsed_ms=%s message=Analysis response returned to UI", request_id, _elapsed_ms(start))
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
    raise HTTPException(status_code=404, detail="UI build not found")


def _request_id():
    return uuid4().hex[:10]


def _elapsed_ms(start):
    return round((time.perf_counter() - start) * 1000)
