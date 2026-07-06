import json
import logging
import os

from pydantic import BaseModel, ValidationError


logger = logging.getLogger("edraak.gemini")

DEFAULT_VERTEX_LOCATION = "global"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"


class GeminiAgentError(RuntimeError):
    pass


def run_gemini_agent(agent_name, context, output_schema, instruction):
    if os.getenv("USE_GEMINI", "true").lower() != "true":
        raise GeminiAgentError("USE_GEMINI must be true. Production mode requires Vertex AI Gemini.")

    project_id = os.getenv("GCP_PROJECT_ID")
    if not project_id or project_id == "YOUR_PROJECT_ID":
        raise GeminiAgentError("GCP_PROJECT_ID is required for Vertex AI Gemini.")

    try:
        from google import genai
        from google.genai import types

        location = os.getenv("VERTEX_LOCATION", DEFAULT_VERTEX_LOCATION)
        model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        prompt = _build_prompt(context, output_schema, instruction)
        logger.info(
            "flow.gemini.call.start agent=%s provider=vertex_ai project_id=%s location=%s model=%s prompt_chars=%s message=Calling Vertex AI Gemini for this agent",
            agent_name,
            project_id,
            location,
            model,
            len(prompt),
        )
        client = genai.Client(vertexai=True, project=project_id, location=location)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        response_text = response.text or "{}"
        logger.info(
            "flow.gemini.response.received agent=%s chars=%s preview=%s message=Gemini returned a response",
            agent_name,
            len(response_text),
            _preview(response_text),
        )
        parsed = json.loads(response_text)
        output = output_schema.model_validate(parsed)
        logger.info("flow.gemini.response.valid agent=%s schema=%s message=Gemini response passed schema validation", agent_name, output_schema.__name__)
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


def _build_prompt(context, output_schema, instruction):
    return (
        "You are an Edraak responsible financial decision agent for a banking production workflow.\n"
        "You must use Vertex AI Gemini output only for language, reasoning, and structured agent fields.\n"
        "Use only the provided JSON context and calculated tool outputs.\n"
        "Do not invent numbers.\n"
        "Do not invent loans, transactions, income, balances, obligations, user profiles, or table rows.\n"
        "Do not use sample data, mock data, assumptions, or placeholder values.\n"
        "Do not read from decision_requests or recommendations; those tables are storage-only.\n"
        "If required source data is missing or inconsistent, report it in the requested schema instead of filling gaps.\n"
        "Return valid JSON only.\n"
        "Do not use Markdown.\n"
        "All user-facing text must be Arabic.\n\n"
        f"Role instruction:\n{instruction}\n\n"
        "Input JSON context:\n"
        f"{context.model_dump_json()}\n\n"
        "Required output JSON schema:\n"
        f"{_schema_for_prompt(output_schema)}"
    )


def _schema_for_prompt(output_schema):
    if issubclass(output_schema, BaseModel):
        return json.dumps(output_schema.model_json_schema(), ensure_ascii=False)
    return "{}"


def _preview(text, limit=1200):
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."
