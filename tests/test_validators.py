"""Unit tests for input/output guardrails, schema validation, and PII/claim checks."""

from __future__ import annotations

import pytest

from scriptxt.models import ContentRequest
from scriptxt.sample_data import build_sample_suite
from scriptxt.validators import (
    InputGuardrailError,
    OutputValidationError,
    detect_pii,
    detect_placeholders,
    detect_unsupported_claims,
    find_duplicate_hooks,
    run_quality_checks,
    validate_calendar_schema,
    validate_input_request,
)


def _valid_calendar_payload(days: int = 3) -> dict[str, object]:
    return {
        "topic": "Async Onboarding",
        "audience": "SaaS Ops Leads",
        "calendar": [
            {
                "day": i,
                "channel": "LinkedIn",
                "format": "post",
                "objective": "awareness",
                "hook": f"Unique opening hook number {i}",
                "body": f"Practical guidance for day {i}.",
                "cta": "Leave a comment",
                "hashtags": ["#SaaS", "#Ops", "#Onboarding"],
                "suggested_time": "09:00 AM",
            }
            for i in range(1, days + 1)
        ],
    }


def test_validate_input_request_enforces_guardrails() -> None:
    with pytest.raises(InputGuardrailError, match="Topic cannot be empty"):
        validate_input_request("", "Ops Leads", "Professional", ["LinkedIn"], 5)

    with pytest.raises(InputGuardrailError, match="Topic exceeds maximum length"):
        validate_input_request("a" * 301, "Ops Leads", "Professional", ["LinkedIn"], 5)

    with pytest.raises(InputGuardrailError, match="Brand voice exceeds maximum length"):
        validate_input_request(
            "Valid Topic",
            "Ops Leads",
            "Professional",
            ["LinkedIn"],
            5,
            brand_voice="b" * 1001,
        )

    with pytest.raises(InputGuardrailError, match="Unsupported channel"):
        validate_input_request("Valid Topic", "Ops Leads", "Professional", ["Snapchat"], 5)


def test_validate_calendar_schema_passes_and_rejects_length_mismatch() -> None:
    payload = _valid_calendar_payload(days=4)
    cal = validate_calendar_schema(payload, expected_days=4, allowed_channels=["LinkedIn"])
    assert len(cal.calendar) == 4

    with pytest.raises(OutputValidationError, match="Expected 7 calendar days"):
        validate_calendar_schema(payload, expected_days=7, allowed_channels=["LinkedIn"])


def test_duplicate_hook_detection_is_case_and_punctuation_insensitive() -> None:
    hooks = [
        "Most onboarding checklists fail early.",
        "Another distinct angle for day two",
        "most onboarding checklists fail early!",
    ]
    dups = find_duplicate_hooks(hooks)
    assert len(dups) == 1

    payload = _valid_calendar_payload(days=3)
    payload["calendar"][2]["hook"] = "unique opening hook number 1!"  # type: ignore[index]
    with pytest.raises(OutputValidationError, match="Duplicate hooks detected"):
        validate_calendar_schema(payload, expected_days=3, allowed_channels=["LinkedIn"])


def test_pii_detection_catches_email_phone_and_card_numbers() -> None:
    text = (
        "Contact jane.doe@example.com or call (415) 555-0199. "
        "Test card 4111 1111 1111 1111 should never appear."
    )
    findings = detect_pii(text)
    assert any("Email:" in item for item in findings)
    assert any("Phone:" in item for item in findings)
    assert any("Card-like number:" in item for item in findings)


def test_unsupported_claim_detection_and_verification_tag() -> None:
    bad_text = (
        "This framework delivers guaranteed results and is 100% safe. "
        "87% of teams doubled output overnight."
    )
    claims = detect_unsupported_claims(bad_text)
    assert len(claims) >= 3

    tagged_text = "87% of surveyed teams [Needs verification] reported faster handoffs."
    assert detect_unsupported_claims(tagged_text) == []


def test_placeholder_detection() -> None:
    text = "TODO: add real CTA. Lorem ipsum dolor sit amet. [insert link]"
    hits = detect_placeholders(text)
    assert len(hits) >= 3


def test_run_quality_checks_passes_for_clean_sample_suite() -> None:
    req = ContentRequest(
        topic="Async Onboarding Playbooks",
        audience="SaaS Operations Leads",
        tone="Professional",
        channels=["LinkedIn", "X", "Instagram", "Blog"],
        calendar_days=7,
        keywords=["onboarding", "playbooks", "async"],
        cta="Share your top onboarding tip below.",
    )
    suite = build_sample_suite(req)
    report = run_quality_checks(suite)
    assert report.all_passed, [c for c in report.checks if not c.passed]
    assert report.failed_count == 0
