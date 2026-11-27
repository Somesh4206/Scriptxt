"""Google Gemini API client and structured content generation functions for SCRIPTXT."""

from __future__ import annotations

import json
import time
from typing import Any, Iterable, Optional

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from scriptxt.config import (
    DEFAULT_MODEL,
    DEFAULT_TASK_MODELS,
    FREE_TIER_TEXT_MODELS,
    MODEL_ROUTING_AUTO,
    ConfigurationError,
    get_settings,
)
from scriptxt.models import (
    BlogOutline,
    ContentRequest,
    InstagramCaption,
    LinkedInPost,
    XThread,
)
from scriptxt.prompts import (
    RenderedPrompt,
    build_blog_outline_prompt,
    build_instagram_caption_prompt,
    build_linkedin_post_prompt,
    build_x_thread_prompt,
)
from scriptxt.schemas import (
    BLOG_OUTLINE_JSON_SCHEMA,
    INSTAGRAM_CAPTION_JSON_SCHEMA,
    LINKEDIN_POST_JSON_SCHEMA,
    X_THREAD_JSON_SCHEMA,
)


class GenerationError(RuntimeError):
    """Raised when a Gemini generation request fails or returns invalid data."""


def create_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """Create a Google GenAI client configured from GEMINI_API_KEY."""
    http_options = {"headers": {"User-Agent": "aistudio-build"}}
    if api_key is not None:
        cleaned = api_key.strip()
        if not cleaned or cleaned in {"MY_GEMINI_API_KEY", "your_api_key_here"}:
            raise ConfigurationError("Provided GEMINI_API_KEY is empty or invalid.")
        return genai.Client(api_key=cleaned, http_options=http_options)

    settings = get_settings(require_api_key=True)
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=http_options,
    )


def resolve_candidate_models(
    content_type: str,
    model: Optional[str] = None,
) -> list[str]:
    """Return ordered list of free-tier models for the task, supporting auto-routing and fallback."""
    configured = (model or "").strip()
    if not configured:
        configured = get_settings(require_api_key=False).gemini_model

    if configured.lower() != MODEL_ROUTING_AUTO:
        return [configured]

    primary = DEFAULT_TASK_MODELS.get(content_type, DEFAULT_MODEL)
    candidates = [primary]
    for fallback in FREE_TIER_TEXT_MODELS:
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


def extract_output_text(response: Any) -> str:
    """Extract text safely from a Gemini GenerateContentResponse object."""
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    raise GenerationError("The Gemini API returned an empty response.")


def _is_auth_error(exc: errors.ClientError) -> bool:
    """Return True if ClientError indicates an invalid or unauthorized API key."""
    code = getattr(exc, "code", None)
    message = str(exc)
    return code in (400, 403) or "API_KEY_INVALID" in message or "PERMISSION_DENIED" in message


def _map_client_error(exc: errors.ClientError, model: str) -> GenerationError:
    """Translate Gemini 4xx ClientError responses into clear user-facing errors."""
    code = getattr(exc, "code", None)
    message = str(exc)
    if _is_auth_error(exc):
        return GenerationError(
            "Gemini API key is invalid or lacks permission. "
            "Please check GEMINI_API_KEY in Settings > Secrets."
        )
    if code == 404 or "NOT_FOUND" in message:
        return GenerationError(
            f"Gemini model '{model}' was not found or is unsupported."
        )
    if code == 429 or "RESOURCE_EXHAUSTED" in message:
        return GenerationError(
            "Gemini API quota or rate limit exceeded across free-tier models. "
            "Please retry shortly or check your API key in Settings > Secrets."
        )
    return GenerationError(f"Gemini API client error: {message}")


def invoke_structured_response(
    prompt: RenderedPrompt,
    schema_name: str,
    schema: dict[str, Any],
    client: Optional[genai.Client] = None,
    model: Optional[str] = None,
    max_retries: int = 1,
) -> dict[str, Any]:
    """Call Gemini generate_content with free-tier model routing, fallback, and JSON Schema output."""
    try:
        active_client = client or create_gemini_client()
    except ConfigurationError as exc:
        raise GenerationError(str(exc)) from exc

    candidate_models = resolve_candidate_models(prompt.content_type, model=model)
    last_error: Optional[Exception] = None
    response: Any = None

    for model_idx, active_model in enumerate(candidate_models):
        has_fallback = model_idx < len(candidate_models) - 1
        thinking_cfg = (
            types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW)
            if active_model.startswith(("gemini-3", "gemini-4"))
            else None
        )
        config = types.GenerateContentConfig(
            system_instruction=prompt.system_prompt,
            response_mime_type="application/json",
            response_json_schema=schema,
            thinking_config=thinking_cfg,
        )
        for attempt in range(max_retries + 1):
            try:
                response = active_client.models.generate_content(
                    model=active_model,
                    contents=prompt.user_prompt,
                    config=config,
                )
                break
            except errors.ClientError as exc:
                if _is_auth_error(exc):
                    raise _map_client_error(exc, active_model) from exc
                last_error = _map_client_error(exc, active_model)
                if has_fallback:
                    break
                raise last_error from exc
            except (errors.ServerError, errors.APIError, OSError, TimeoutError) as exc:
                last_error = exc
                if attempt < max_retries:
                    time.sleep(0.5 * (2**attempt))
                    continue
                if has_fallback:
                    break
                raise GenerationError(
                    f"Gemini API request failed across {', '.join(candidate_models)}: {exc}"
                ) from exc
            except Exception as exc:
                raise GenerationError(
                    f"Unexpected error during Gemini content generation: {exc}"
                ) from exc

        if response is not None:
            break

    if response is None:
        if isinstance(last_error, GenerationError):
            raise last_error
        raise GenerationError(f"Gemini generation failed: {last_error}")

    raw_text = extract_output_text(response)
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise GenerationError(
            f"Model output was not valid JSON for {schema_name}: {exc}"
        ) from exc

    if not isinstance(parsed, dict):
        raise GenerationError(
            f"Expected JSON object for {schema_name}, got {type(parsed).__name__}."
        )
    return parsed


def generate_linkedin_post(
    topic: str,
    audience: str,
    tone: str,
    cta: str = "",
    *,
    keywords: Optional[Iterable[str]] = None,
    brand_voice: Optional[str] = None,
    content_goal: str = "Educate the audience and drive practical B2B engagement.",
    client: Optional[genai.Client] = None,
    model: Optional[str] = None,
) -> LinkedInPost:
    """Generate a structured 120-180 word LinkedIn post with hook, insight, takeaway, and 3 hashtags."""
    if not topic or not topic.strip():
        raise ValueError("Topic must not be empty.")
    if not audience or not audience.strip():
        raise ValueError("Audience must not be empty.")

    prompt = build_linkedin_post_prompt(
        topic=topic,
        audience=audience,
        tone=tone,
        content_goal=content_goal,
        cta=cta,
        keywords=keywords,
        brand_voice=brand_voice,
    )
    payload = invoke_structured_response(
        prompt=prompt,
        schema_name="linkedin_post",
        schema=LINKEDIN_POST_JSON_SCHEMA,
        client=client,
        model=model,
    )
    try:
        post = LinkedInPost.model_validate(payload)
    except ValidationError as exc:
        raise GenerationError(f"Generated LinkedIn post failed validation: {exc}") from exc

    if len(post.hashtags) != 3:
        if len(post.hashtags) > 3:
            post = post.model_copy(update={"hashtags": post.hashtags[:3]})
        else:
            raise GenerationError(
                f"LinkedIn post must contain exactly 3 hashtags (got {len(post.hashtags)})."
            )
    return post


def generate_x_thread(
    request: ContentRequest,
    client: Optional[genai.Client] = None,
    model: Optional[str] = None,
) -> XThread:
    """Generate a structured 3-7 post X thread from a validated ContentRequest."""
    prompt = build_x_thread_prompt(
        topic=request.topic,
        audience=request.audience,
        tone=request.tone,
        content_goal=request.content_goal,
        cta=request.cta,
        keywords=request.keywords,
        brand_voice=request.brand_voice,
    )
    payload = invoke_structured_response(
        prompt=prompt,
        schema_name="x_thread",
        schema=X_THREAD_JSON_SCHEMA,
        client=client,
        model=model,
    )
    try:
        return XThread.model_validate(payload)
    except ValidationError as exc:
        raise GenerationError(f"Generated X thread failed validation: {exc}") from exc


def generate_instagram_caption(
    request: ContentRequest,
    client: Optional[genai.Client] = None,
    model: Optional[str] = None,
) -> InstagramCaption:
    """Generate a structured Instagram caption and accessibility alt text."""
    prompt = build_instagram_caption_prompt(
        topic=request.topic,
        audience=request.audience,
        tone=request.tone,
        content_goal=request.content_goal,
        cta=request.cta,
        keywords=request.keywords,
        brand_voice=request.brand_voice,
    )
    payload = invoke_structured_response(
        prompt=prompt,
        schema_name="instagram_caption",
        schema=INSTAGRAM_CAPTION_JSON_SCHEMA,
        client=client,
        model=model,
    )
    try:
        return InstagramCaption.model_validate(payload)
    except ValidationError as exc:
        raise GenerationError(
            f"Generated Instagram caption failed validation: {exc}"
        ) from exc


def generate_blog_outline(
    request: ContentRequest,
    client: Optional[genai.Client] = None,
    model: Optional[str] = None,
) -> BlogOutline:
    """Generate a structured SEO-ready blog outline."""
    prompt = build_blog_outline_prompt(
        topic=request.topic,
        audience=request.audience,
        tone=request.tone,
        content_goal=request.content_goal,
        cta=request.cta,
        keywords=request.keywords,
        brand_voice=request.brand_voice,
    )
    payload = invoke_structured_response(
        prompt=prompt,
        schema_name="blog_outline",
        schema=BLOG_OUTLINE_JSON_SCHEMA,
        client=client,
        model=model,
    )
    try:
        return BlogOutline.model_validate(payload)
    except ValidationError as exc:
        raise GenerationError(f"Generated blog outline failed validation: {exc}") from exc
