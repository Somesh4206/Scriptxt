"""Mocked Gemini API unit tests for generator, calendar, and evaluation harness."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from google.genai import errors

from scriptxt.calendar import CalendarGenerationError, generate_content_calendar
from scriptxt.evaluation import run_evaluation
from scriptxt.generator import (
    GenerationError,
    generate_blog_outline,
    generate_instagram_caption,
    generate_linkedin_post,
    generate_x_thread,
    resolve_candidate_models,
)
from scriptxt.models import ContentRequest
from scriptxt.sample_data import build_sample_suite


def _mock_client_returning(payload: dict[str, object]) -> MagicMock:
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(payload)
    )
    return client


def test_resolve_candidate_models_routes_across_all_free_tier_models() -> None:
    assert resolve_candidate_models("linkedin_post", "auto") == [
        "gemini-4-hydrogen",
        "gemini-3.1-flash-lite",
    ]
    assert resolve_candidate_models("x_thread", "auto") == [
        "gemini-3.1-flash-lite",
        "gemini-4-hydrogen",
    ]
    assert resolve_candidate_models("instagram_caption", "auto") == [
        "gemini-3.1-flash-lite",
        "gemini-4-hydrogen",
    ]
    assert resolve_candidate_models("linkedin_post", "gemini-3.1-flash-lite") == [
        "gemini-3.1-flash-lite"
    ]


def test_auto_fallback_to_second_free_tier_model_on_rate_limit() -> None:
    words_135 = " ".join(["workflow"] * 135)
    payload = {
        "hook": "Fallback worked",
        "body": "Practical insight body",
        "takeaway": "Actionable takeaway",
        "cta": "Comment below",
        "hashtags": ["#B2B", "#Ops", "#Workflow"],
        "full_text": words_135,
    }
    client = MagicMock()
    client.models.generate_content.side_effect = [
        errors.ClientError(429, {"error": {"message": "RESOURCE_EXHAUSTED"}}),
        SimpleNamespace(text=json.dumps(payload)),
    ]

    post = generate_linkedin_post(
        topic="Async Workflows",
        audience="SaaS Ops",
        tone="Professional",
        cta="Comment below",
        client=client,
        model="auto",
    )
    assert post.hook == "Fallback worked"
    assert client.models.generate_content.call_count == 2
    first_model = client.models.generate_content.call_args_list[0].kwargs["model"]
    second_model = client.models.generate_content.call_args_list[1].kwargs["model"]
    assert first_model == "gemini-4-hydrogen"
    assert second_model == "gemini-3.1-flash-lite"


def test_generate_linkedin_post_uses_gemini_structured_json_and_returns_valid_model() -> None:
    words_135 = " ".join(["workflow"] * 135)
    payload = {
        "hook": "Strong opening hook",
        "body": "Practical insight body",
        "takeaway": "Actionable takeaway",
        "cta": "Comment below",
        "hashtags": ["#B2B", "#Ops", "#Workflow"],
        "full_text": words_135,
    }
    mock_client = _mock_client_returning(payload)

    post = generate_linkedin_post(
        topic="Async Workflows",
        audience="SaaS Ops",
        tone="Professional",
        cta="Comment below",
        client=mock_client,
        model="gemini-4-hydrogen",
    )
    assert post.hook == "Strong opening hook"
    assert len(post.hashtags) == 3
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-4-hydrogen"
    assert call_kwargs["config"].response_mime_type == "application/json"
    assert call_kwargs["config"].response_json_schema is not None
    assert "B2B social-media copywriter" in call_kwargs["config"].system_instruction


def test_generate_linkedin_post_handles_empty_response_gracefully() -> None:
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(text="   ")
    with pytest.raises(GenerationError, match="empty response"):
        generate_linkedin_post("Topic", "Audience", "Professional", "CTA", client=client)


def test_generate_linkedin_post_handles_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "")
    with pytest.raises(GenerationError, match="GEMINI_API_KEY"):
        generate_linkedin_post("Topic", "Audience", "Professional", "CTA")


def test_generate_linkedin_post_handles_client_error_gracefully() -> None:
    client = MagicMock()
    client.models.generate_content.side_effect = errors.ClientError(
        403, {"error": {"message": "PERMISSION_DENIED"}}
    )
    with pytest.raises(GenerationError, match="GEMINI_API_KEY"):
        generate_linkedin_post("Topic", "Audience", "Professional", "CTA", client=client)


def test_generate_x_instagram_and_blog_with_mocked_gemini() -> None:
    req = ContentRequest(
        topic="Design Tokens",
        audience="Frontend Engineers",
        tone="Educational",
        channels=["LinkedIn", "X", "Instagram", "Blog"],
        calendar_days=3,
    )

    x_client = _mock_client_returning(
        {
            "hook_tweet": "Hook tweet",
            "posts": ["1/ First", "2/ Second", "3/ Third"],
            "cta": "Follow for more",
            "hashtags": ["#DesignTokens", "#UI", "#Frontend"],
        }
    )
    thread = generate_x_thread(req, client=x_client)
    assert len(thread.posts) == 3

    ig_client = _mock_client_returning(
        {
            "hook": "IG Hook",
            "caption": "Short visual breakdown",
            "cta": "Save this post",
            "hashtags": ["#Design", "#Tokens", "#UI"],
            "alt_text": "Diagram of color and spacing design tokens.",
        }
    )
    ig = generate_instagram_caption(req, client=ig_client)
    assert "tokens" in ig.alt_text.lower()

    blog_client = _mock_client_returning(
        {
            "title": "Design Tokens in Practice",
            "meta_description": "How frontend teams manage design tokens.",
            "target_audience": "Frontend Engineers",
            "introduction": "Intro paragraph",
            "sections": [
                {"heading": "1. Naming", "key_points": ["Semantic names"]},
                {"heading": "2. Tooling", "key_points": ["Automated exports"]},
            ],
            "conclusion_cta": "Try a token audit",
            "seo_keywords": ["design tokens", "frontend"],
        }
    )
    outline = generate_blog_outline(req, client=blog_client)
    assert len(outline.sections) == 2


def test_generate_content_calendar_enforces_strict_schema_and_length() -> None:
    req = ContentRequest(
        topic="Release Checklists",
        audience="Engineering Leads",
        tone="Professional",
        channels=["LinkedIn", "X"],
        calendar_days=4,
    )
    payload = {
        "topic": "Release Checklists",
        "audience": "Engineering Leads",
        "calendar": [
            {
                "day": i,
                "channel": "LinkedIn" if i % 2 == 1 else "X",
                "format": "post" if i % 2 == 1 else "thread",
                "objective": "education",
                "hook": f"Distinct hook for day {i}",
                "body": f"Body for day {i}",
                "cta": "Comment below",
                "hashtags": ["#Engineering", "#QA", "#Release"],
                "suggested_time": "09:00 AM",
            }
            for i in range(1, 5)
        ],
    }
    client = _mock_client_returning(payload)
    cal = generate_content_calendar(req, client=client, model="gemini-4-hydrogen")
    assert len(cal.calendar) == 4
    call_kwargs = client.models.generate_content.call_args.kwargs
    schema = call_kwargs["config"].response_json_schema
    assert schema["properties"]["calendar"]["items"]["properties"]["channel"]["enum"] == ["LinkedIn", "X"]


def test_generate_content_calendar_raises_on_wrong_day_count() -> None:
    req = ContentRequest(
        topic="Release Checklists",
        audience="Engineering Leads",
        tone="Professional",
        channels=["LinkedIn"],
        calendar_days=5,
    )
    payload = {
        "topic": "Release Checklists",
        "audience": "Engineering Leads",
        "calendar": [
            {
                "day": i,
                "channel": "LinkedIn",
                "format": "post",
                "objective": "awareness",
                "hook": f"Hook {i}",
                "body": "Body",
                "cta": "CTA",
                "hashtags": ["#Engineering", "#QA", "#Ops"],
                "suggested_time": "09:00 AM",
            }
            for i in range(1, 4)
        ],
    }
    client = _mock_client_returning(payload)
    with pytest.raises(CalendarGenerationError, match="Expected 5 calendar days"):
        generate_content_calendar(req, client=client)


def test_offline_evaluation_harness_writes_results_csv(tmp_path: Path) -> None:
    results_csv = tmp_path / "results.csv"
    summary = run_evaluation(
        sample_csv_path="evaluations/sample_topics.csv",
        results_csv_path=results_csv,
        suite_builder=build_sample_suite,
    )
    assert summary.total_attempts == 5
    assert summary.successful_generations == 5
    assert summary.schema_pass_rate == 1.0
    assert summary.duplicate_hook_failure_rate == 0.0
    assert summary.guardrail_violation_rate == 0.0
    assert results_csv.exists()
