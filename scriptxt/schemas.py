"""Strict JSON Schemas for OpenAI Structured Outputs and local validation."""

from __future__ import annotations

from typing import Any

from scriptxt.config import (
    MAX_CALENDAR_DAYS,
    MIN_CALENDAR_DAYS,
    SUPPORTED_CHANNELS,
    SUPPORTED_FORMATS,
    SUPPORTED_OBJECTIVES,
)

LINKEDIN_POST_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["hook", "body", "takeaway", "cta", "hashtags", "full_text"],
    "properties": {
        "hook": {"type": "string"},
        "body": {"type": "string"},
        "takeaway": {"type": "string"},
        "cta": {"type": "string"},
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
        },
        "full_text": {"type": "string"},
    },
}

X_THREAD_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["hook_tweet", "posts", "cta", "hashtags"],
    "properties": {
        "hook_tweet": {"type": "string"},
        "posts": {
            "type": "array",
            "items": {"type": "string"},
        },
        "cta": {"type": "string"},
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}

INSTAGRAM_CAPTION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["hook", "caption", "cta", "hashtags", "alt_text"],
    "properties": {
        "hook": {"type": "string"},
        "caption": {"type": "string"},
        "cta": {"type": "string"},
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
        },
        "alt_text": {"type": "string"},
    },
}

BLOG_OUTLINE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title",
        "meta_description",
        "target_audience",
        "introduction",
        "sections",
        "conclusion_cta",
        "seo_keywords",
    ],
    "properties": {
        "title": {"type": "string"},
        "meta_description": {"type": "string"},
        "target_audience": {"type": "string"},
        "introduction": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["heading", "key_points"],
                "properties": {
                    "heading": {"type": "string"},
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "conclusion_cta": {"type": "string"},
        "seo_keywords": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}


def build_content_calendar_schema(
    allowed_channels: list[str] | tuple[str, ...] = SUPPORTED_CHANNELS,
) -> dict[str, Any]:
    """Return a strict JSON Schema for Gemini Structured Outputs."""
    channels = list(allowed_channels) if allowed_channels else list(SUPPORTED_CHANNELS)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["topic", "audience", "calendar"],
        "properties": {
            "topic": {"type": "string"},
            "audience": {"type": "string"},
            "calendar": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "day",
                        "channel",
                        "format",
                        "objective",
                        "hook",
                        "body",
                        "cta",
                        "hashtags",
                        "suggested_time",
                    ],
                    "properties": {
                        "day": {"type": "integer"},
                        "channel": {
                            "type": "string",
                            "enum": channels,
                        },
                        "format": {
                            "type": "string",
                            "enum": list(SUPPORTED_FORMATS),
                        },
                        "objective": {
                            "type": "string",
                            "enum": list(SUPPORTED_OBJECTIVES),
                        },
                        "hook": {"type": "string"},
                        "body": {"type": "string"},
                        "cta": {"type": "string"},
                        "hashtags": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "suggested_time": {"type": "string"},
                    },
                },
            },
        },
    }


CONTENT_CALENDAR_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["topic", "audience", "calendar"],
    "properties": {
        "topic": {"type": "string", "minLength": 1},
        "audience": {"type": "string", "minLength": 1},
        "calendar": {
            "type": "array",
            "minItems": MIN_CALENDAR_DAYS,
            "maxItems": MAX_CALENDAR_DAYS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "day",
                    "channel",
                    "format",
                    "objective",
                    "hook",
                    "body",
                    "cta",
                    "hashtags",
                    "suggested_time",
                ],
                "properties": {
                    "day": {"type": "integer", "minimum": 1, "maximum": MAX_CALENDAR_DAYS},
                    "channel": {"type": "string", "enum": list(SUPPORTED_CHANNELS)},
                    "format": {"type": "string", "enum": list(SUPPORTED_FORMATS)},
                    "objective": {"type": "string", "enum": list(SUPPORTED_OBJECTIVES)},
                    "hook": {"type": "string", "minLength": 1},
                    "body": {"type": "string", "minLength": 1},
                    "cta": {"type": "string", "minLength": 1},
                    "hashtags": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "suggested_time": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}

# Explicit 7-day strict schema alias for documentation and validation checks.
SEVEN_DAY_CALENDAR_JSON_SCHEMA: dict[str, Any] = {
    **CONTENT_CALENDAR_JSON_SCHEMA,
    "properties": {
        **CONTENT_CALENDAR_JSON_SCHEMA["properties"],
        "calendar": {
            **CONTENT_CALENDAR_JSON_SCHEMA["properties"]["calendar"],
            "minItems": 7,
            "maxItems": 7,
        },
    },
}
