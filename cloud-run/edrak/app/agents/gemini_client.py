"""One place for Vertex AI Gemini calls, strict schema validation, and number auditing."""
import json
import logging
import re

from pydantic import BaseModel, ValidationError

from app import config


logger = logging.getLogger("edraak.gemini")


class GeminiAgentError(RuntimeError):
    pass


def run_gemini_agent(agent_name: str, payload: dict, output_schema: type[BaseModel],
                     instruction: str) -> BaseModel:
    """Call Gemini with a JSON payload and validate the response against the schema.

    Hard-fails on invalid output — no static fallback text. The only tolerated
    repair is the amount-echo fallback inside the Transaction Intelligence Agent.
    """
    if not config.use_gemini():
        raise GeminiAgentError("USE_GEMINI must be true. Production mode requires Vertex AI Gemini.")
    project_id = config.gcp_project_id()
    if not project_id or project_id == "YOUR_PROJECT_ID":
        raise GeminiAgentError("GCP_PROJECT_ID is required for Vertex AI Gemini.")

    try:
        from google import genai
        from google.genai import types

        prompt = _build_prompt(payload, output_schema, instruction)
        logger.info(
            "flow.gemini.call.start agent=%s provider=vertex_ai project_id=%s location=%s model=%s prompt_chars=%s message=Calling Vertex AI Gemini for this agent",
            agent_name, project_id, config.vertex_location(), config.gemini_model(), len(prompt),
        )
        client = genai.Client(vertexai=True, project=project_id, location=config.vertex_location())
        response = client.models.generate_content(
            model=config.gemini_model(),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        response_text = response.text or "{}"
        logger.info(
            "flow.gemini.response.received agent=%s chars=%s preview=%s message=Gemini returned a response",
            agent_name, len(response_text), _preview(response_text),
        )
        parsed = json.loads(response_text)
        output = output_schema.model_validate(parsed)
        logger.info("flow.gemini.response.valid agent=%s schema=%s message=Gemini response passed schema validation",
                    agent_name, output_schema.__name__)
        return output
    except json.JSONDecodeError as exc:
        logger.exception("gemini.response.invalid_json agent=%s", agent_name)
        raise GeminiAgentError(f"Gemini returned invalid JSON for {agent_name}.") from exc
    except ValidationError as exc:
        logger.exception("gemini.response.schema_error agent=%s", agent_name)
        raise GeminiAgentError(f"Gemini response did not match schema for {agent_name}.") from exc
    except GeminiAgentError:
        raise
    except Exception as exc:
        logger.exception("gemini.call.failed agent=%s", agent_name)
        raise GeminiAgentError(f"Gemini call failed for {agent_name}.") from exc


def audit_numbers(agent_name: str, texts: list[str], payload: dict) -> None:
    """Log any number in the agent's Arabic text that does not exist in its input payload.

    Log-only guardrail: the deterministic layer already owns every displayed
    number; this catches an agent drifting into invented figures during demos.
    """
    allowed = _numbers_in(payload)
    for text in texts:
        for token in re.findall(r"\d[\d,\.]*", _normalize_digits(text or "")):
            value = token.replace(",", "").rstrip(".")
            # Small counts (days of a plan, list ordinals) are legitimate prose.
            if not value or float(value) <= 90:
                continue
            if value not in allowed and str(int(float(value))) not in allowed:
                logger.warning(
                    "gemini.number_audit.mismatch agent=%s number=%s message=Number not found in agent input payload",
                    agent_name, token,
                )


def _numbers_in(payload: dict) -> set[str]:
    """Collect every numeric value in the payload as normalized strings."""
    found: set[str] = set()

    def walk(node) -> None:
        if isinstance(node, bool):
            return
        if isinstance(node, (int, float)):
            found.add(str(int(abs(node))))
            found.add(str(abs(node)))
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            for token in re.findall(r"\d+", node):
                found.add(token.lstrip("0") or "0")

    walk(payload)
    return found


def _normalize_digits(text: str) -> str:
    """Map Eastern Arabic numerals to Western so the audit sees one digit system."""
    return text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))


def _build_prompt(payload: dict, output_schema: type[BaseModel], instruction: str) -> str:
    return (
        "You are an Edraak agent inside a cross-bank financial safety product.\n"
        "The deterministic Python layer computes every number; you understand messy data and communicate.\n"
        "Use only the provided JSON payload. Do not invent numbers, transactions, loans, balances, or obligations.\n"
        "Do not use sample data, assumptions, or placeholder values.\n"
        "If required data is missing, say so inside the requested schema instead of filling gaps.\n"
        "Return valid JSON only. Do not use Markdown.\n"
        "All user-facing text must be Arabic.\n\n"
        f"Role instruction:\n{instruction}\n\n"
        "Input JSON payload:\n"
        f"{json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
        "Required output JSON schema:\n"
        f"{json.dumps(output_schema.model_json_schema(), ensure_ascii=False)}"
    )


def _preview(text: str, limit: int = 1200) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."
