"""FastAPI routes only — orchestration lives in app.pipeline, math in app.functions."""
import logging
import time
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import pipeline
from app.agents.gemini_client import GeminiAgentError
from app.data.bigquery_client import (
    get_alerts,
    get_customer_by_username,
    save_decision_request,
    save_recommendation,
)
from app.functions.risk_model import predict_risk


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


class RadarInput(BaseModel):
    customer_id: str


app = FastAPI(title="Edraak API", version="0.3.0")

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


@app.on_event("startup")
def warm_risk_model():
    """Load the joblib risk model once so the first analyze call is not slower."""
    predict_risk({})


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
    customer = get_customer_by_username(login_input.username)
    if not customer:
        logger.warning("flow.login.failed request_id=%s username=%s reason=not_found message=No customer found for username", request_id, login_input.username)
        raise HTTPException(status_code=404, detail="Username not found")
    logger.info(
        "flow.login.success request_id=%s customer_id=%s elapsed_ms=%s message=Login matched username to customer record",
        request_id, customer["customer_id"], _elapsed_ms(start),
    )
    return {
        "customer_id": customer["customer_id"],
        "username_en": customer["username_en"],
        "ar_name": customer["ar_name"],
        "en_name": customer["en_name"],
    }


@app.post("/api/analyze")
def analyze(decision_input: DecisionInput):
    request_id = _request_id()
    start = time.perf_counter()
    decision = decision_input.model_dump()
    logger.info(
        "flow.analysis.clicked request_id=%s customer_id=%s goal_type=%s amount=%s installment=%s message=User submitted financial goal; starting Mode A pipeline",
        request_id, decision_input.customer_id, decision_input.goal_type,
        decision_input.goal_amount, decision_input.monthly_installment,
    )
    try:
        result = pipeline.run_analysis(decision)
    except LookupError:
        raise HTTPException(status_code=404, detail="Customer not found")
    except ValueError as exc:
        logger.warning("analyze.validation_failed request_id=%s error=%s", request_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    logger.info("flow.analysis.storage.start request_id=%s message=Saving request and recommendation to storage-only tables", request_id)
    save_decision_request({**decision, "request_id": request_id})
    save_recommendation({**result, "request_id": request_id})
    logger.info(
        "flow.analysis.completed request_id=%s recommendation=%s elapsed_ms=%s message=Analysis response returned to UI",
        request_id, result["recommendation"], _elapsed_ms(start),
    )
    return result


@app.post("/api/radar/trigger")
def radar_trigger(radar_input: RadarInput):
    request_id = _request_id()
    start = time.perf_counter()
    logger.info(
        "flow.radar.triggered request_id=%s customer_id=%s message=Radar check requested (simulates the scheduled end-of-month job)",
        request_id, radar_input.customer_id,
    )
    try:
        result = pipeline.run_radar_check(radar_input.customer_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Customer not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info(
        "flow.radar.responded request_id=%s has_gap=%s elapsed_ms=%s message=Radar result returned to UI",
        request_id, result["has_gap"], _elapsed_ms(start),
    )
    return result


@app.get("/api/alerts/{customer_id}")
def list_alerts(customer_id: str):
    logger.info("flow.alerts.list customer_id=%s message=Loading stored radar alerts for UI", customer_id)
    return get_alerts(customer_id)


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
