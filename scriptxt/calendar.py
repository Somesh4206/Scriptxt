"""Structured multi-day content calendar generator for SCRIPTXT using Gemini AI."""

from __future__ import annotations

from typing import Optional

from google import genai

from scriptxt.generator import GenerationError, invoke_structured_response
from scriptxt.models import ContentCalendar, ContentRequest
from scriptxt.prompts import build_content_calendar_prompt
from scriptxt.schemas import build_content_calendar_schema
from scriptxt.validators import OutputValidationError, validate_calendar_schema


class CalendarGenerationError(GenerationError):
    """Raised when structured calendar generation or validation fails."""


def generate_content_calendar(
    request: ContentRequest,
    client: Optional[genai.Client] = None,
    model: Optional[str] = None,
) -> ContentCalendar:
    """Generate and validate a multi-day ContentCalendar using Gemini Structured Outputs."""
    prompt = build_content_calendar_prompt(
        topic=request.topic,
        audience=request.audience,
        tone=request.tone,
        calendar_days=request.calendar_days,
        channels=request.channels,
        content_goal=request.content_goal,
        cta=request.cta,
        keywords=request.keywords,
        brand_voice=request.brand_voice,
    )

    schema = build_content_calendar_schema(allowed_channels=request.channels)

    try:
        payload = invoke_structured_response(
            prompt=prompt,
            schema_name="content_calendar",
            schema=schema,
            client=client,
            model=model,
        )
    except GenerationError as exc:
        raise CalendarGenerationError(str(exc)) from exc

    try:
        return validate_calendar_schema(
            payload,
            expected_days=request.calendar_days,
            allowed_channels=request.channels,
        )
    except OutputValidationError as exc:
        raise CalendarGenerationError(str(exc)) from exc
