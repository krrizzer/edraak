"""FastAPI routes only — orchestration lives in app.pipeline, math in app.functions."""
import logging
import mimetypes
import time
from pathlib import Path
from uuid import uuid4

# Flutter web ships a .wasm (CanvasKit); ensure it's served with the right MIME
# so the browser can stream-compile it instead of falling back.
mimetypes.add_type("application/wasm", ".wasm")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import pipeline
from app.agents.gemini_client import GeminiAgentError
from app.data import ingestion
from app.data.bigquery_client import (
    get_accounts,
    get_alerts,
    get_connected_banks,
    get_consents,
    get_customer_by_id,
    get_customer_by_username,
    get_loans,
    get_transactions,
    ensure_runtime_tables,
    save_decision_request,
    save_recommendation,
)
from app.agents.data_sufficiency import assess as assess_sufficiency
from app.functions.completeness import STATUS_PARTIAL, build_evidence, check_completeness
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


class IngestInput(BaseModel):
    customer_id: str
    bank_code: str
    consent_id: str


class DemoResetInput(BaseModel):
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


@app.on_event("startup")
def prepare_runtime_schema():
    """Prepare additive support tables even when today's seed is already fresh."""
    from app import config

    if config.use_bigquery():
        ensure_runtime_tables()


@app.on_event("startup")
def auto_seed():
    """Re-seed the demo world if it is anchored to a different day (AUTO_SEED=true).

    This is what makes demo day zero-maintenance on Cloud Run: the first cold
    start of the day regenerates the banks' cores and the first-party data with
    dates anchored to today — no manual load_seed_data run needed.
    """
    from app import config
    if not config.auto_seed() or not config.use_bigquery():
        return
    from app.data.seed.load_seed_data import ensure_fresh_seed
    # Fail the container startup if the demo data cannot be prepared. A visible
    # deployment failure is safer than a healthy-looking app with no login data.
    ensure_fresh_seed()


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


@app.get("/api/ui-config")
def ui_config():
    """Runtime config the Flutter app reads at startup (so the gateway URL isn't baked in)."""
    from app import config
    return {"gateway_base": config.openbanking_gateway_url()}


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
    coverage_report = _coverage(decision_input.customer_id, deep=True)
    if coverage_report is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    if coverage_report["is_blocking"]:
        message = "؛ ".join(f["message_ar"] for f in coverage_report["findings"] if f["severity"] == "critical")
        logger.warning("analyze.blocked_incomplete request_id=%s message=Data insufficient to analyze", request_id)
        raise HTTPException(status_code=422, detail=message or "البيانات المرتبطة غير كافية للتحليل.")

    try:
        result = pipeline.run_analysis(decision)
    except LookupError:
        raise HTTPException(status_code=404, detail="Customer not found")
    except ValueError as exc:
        logger.warning("analyze.validation_failed request_id=%s error=%s", request_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result["coverage"] = coverage_report

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


@app.post("/api/ingest")
def ingest(ingest_input: IngestInput):
    """Pull one consented bank's data through the gateway into BigQuery (bronze→silver)."""
    request_id = _request_id()
    logger.info("flow.ingest.requested request_id=%s customer_id=%s bank=%s message=Consent approved; ingesting",
                request_id, ingest_input.customer_id, ingest_input.bank_code)
    try:
        summary = ingestion.ingest_bank(
            ingest_input.customer_id, ingest_input.bank_code, ingest_input.consent_id)
    except ingestion.IngestionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"status": "ingested", **summary, "coverage": _coverage(ingest_input.customer_id)}


@app.get("/api/coverage/{customer_id}")
def coverage(customer_id: str, deep: bool = False):
    """Report whether the linked data is enough. deep=true adds the AI sufficiency judgment."""
    logger.info("flow.coverage.check customer_id=%s deep=%s message=Assessing data completeness", customer_id, deep)
    result = _coverage(customer_id, deep=deep)
    if result is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return result


@app.get("/api/consents/{customer_id}")
def list_consents(customer_id: str):
    """List the customer's linked-account consents for the management screen."""
    return get_consents(customer_id)


@app.post("/api/demo/reset")
def demo_reset(reset_input: DemoResetInput):
    """Hidden demo control: revoke bank consents and restore host-bank-only data."""
    customer_id = reset_input.customer_id
    if not get_customer_by_id(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")

    try:
        revoked = ingestion.reset_gateway_consents(customer_id)
        from app.data.seed.load_seed_data import reset_demo_customer
        restored = reset_demo_customer(customer_id)
    except ingestion.IngestionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except LookupError:
        raise HTTPException(status_code=404, detail="Demo customer not found")

    for key in [key for key in _sufficiency_cache if key[0] == customer_id]:
        _sufficiency_cache.pop(key, None)
    logger.warning("flow.demo_reset.completed customer_id=%s revoked_consents=%s", customer_id, revoked)
    return {
        "status": "reset",
        "revoked_consents": revoked,
        "restored": restored,
    }


# One sufficiency judgment per (customer, linked-banks, data volume): re-linking a
# bank changes the key, so the agent re-runs exactly when the picture changes.
_sufficiency_cache: dict[tuple, dict] = {}


def _coverage(customer_id: str, deep: bool = False) -> dict | None:
    """Build the coverage report. deep=False → deterministic facts only (fast, for
    screens); deep=True → adds the Data Sufficiency Agent judgment (used on analyze)."""
    customer = get_customer_by_id(customer_id)
    if not customer:
        return None
    accounts = get_accounts(customer_id)
    transactions = get_transactions(customer_id)
    loans = get_loans(customer_id)
    connected = get_connected_banks(customer_id)

    report = check_completeness(customer, accounts, transactions, loans, connected)
    if not deep or report["is_blocking"]:
        return report  # screens stay fast; a missing salary needs no LLM either

    key = (customer_id, tuple(sorted(connected)), len(transactions))
    judgment = _sufficiency_cache.get(key)
    if judgment is None:
        try:
            evidence = build_evidence(customer, accounts, transactions, loans, connected)
            output = assess_sufficiency(evidence)
            judgment = {
                "looks_complete": output.looks_complete,
                "confidence": output.confidence,
                "findings": [{"code": "llm_sufficiency", "severity": "medium", "message_ar": f}
                             for f in output.findings_ar],
            }
        except GeminiAgentError:
            logger.warning("coverage.sufficiency_unavailable customer_id=%s message=Falling back to deterministic-only coverage", customer_id)
            judgment = {
                "looks_complete": True,
                "confidence": 0.0,
                "findings": [{"code": "llm_unavailable", "severity": "low",
                              "message_ar": "التحقق الذكي من اكتمال البيانات غير متاح حاليًا — النتائج من الفحوصات الحتمية فقط."}],
            }
        _sufficiency_cache[key] = judgment

    report["findings"] = report["findings"] + judgment["findings"]
    report["sufficiency_confidence"] = judgment["confidence"]
    if not judgment["looks_complete"] and report["status"] == "كافية":
        report["status"] = STATUS_PARTIAL
    return report


@app.get("/{path:path}")
def serve_flutter_app(path: str):
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
