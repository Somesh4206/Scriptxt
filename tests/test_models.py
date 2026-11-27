"""Unit tests for Pydantic models in scriptxt.models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from scriptxt.models import (
    BlogOutline,
    BlogSection,
    CalendarItem,
    ContentCalendar,
    ContentRequest,
    InstagramCaption,
    LinkedInPost,
    XThread,
)


def test_content_request_valid_defaults_and_parsing() -> None:
    req = ContentRequest(
        topic="Async Onboarding Playbooks",
        audience="SaaS Operations Leads",
        tone="Professional",
        channels=["LinkedIn", "X"],
        calendar_days=5,
        keywords="onboarding, async, playbooks",
    )
    assert req.topic == "Async Onboarding Playbooks"
    assert req.channels == ["LinkedIn", "X"]
    assert req.calendar_days == 5
    assert req.keywords == ["onboarding", "async", "playbooks"]


@pytest.mark.parametrize("bad_topic", ["", "   ", "x" * 301])
def test_content_request_rejects_invalid_topic(bad_topic: str) -> None:
    with pytest.raises(ValidationError):
        ContentRequest(
            topic=bad_topic,
            audience="Operations Leads",
            tone="Professional",
            channels=["LinkedIn"],
            calendar_days=5,
        )


@pytest.mark.parametrize("bad_audience", ["", "   "])
def test_content_request_rejects_empty_audience(bad_audience: str) -> None:
    with pytest.raises(ValidationError):
        ContentRequest(
            topic="Valid Topic",
            audience=bad_audience,
            tone="Professional",
            channels=["LinkedIn"],
            calendar_days=5,
        )


def test_content_request_rejects_invalid_tone() -> None:
    with pytest.raises(ValidationError):
        ContentRequest(
            topic="Valid Topic",
            audience="Product Managers",
            tone="Sarcastic",  # type: ignore[arg-type]
            channels=["LinkedIn"],
            calendar_days=5,
        )


@pytest.mark.parametrize("days", [0, 2, 15, 30])
def test_content_request_rejects_out_of_range_days(days: int) -> None:
    with pytest.raises(ValidationError):
        ContentRequest(
            topic="Valid Topic",
            audience="Product Managers",
            tone="Educational",
            channels=["LinkedIn"],
            calendar_days=days,
        )


@pytest.mark.parametrize("bad_channels", [[], ["TikTok"], ["LinkedIn", "YouTube"]])
def test_content_request_rejects_invalid_channels(bad_channels: list[str]) -> None:
    with pytest.raises(ValidationError):
        ContentRequest(
            topic="Valid Topic",
            audience="Product Managers",
            tone="Educational",
            channels=bad_channels,  # type: ignore[arg-type]
            calendar_days=5,
        )


def test_content_request_rejects_overlong_brand_voice() -> None:
    with pytest.raises(ValidationError):
        ContentRequest(
            topic="Valid Topic",
            audience="Product Managers",
            tone="Friendly",
            channels=["LinkedIn"],
            calendar_days=5,
            brand_voice="a" * 1001,
        )


def test_output_models_validate_and_normalize_hashtags() -> None:
    li = LinkedInPost(
        hook="Hook line",
        body="Body text",
        takeaway="Takeaway line",
        cta="Comment below",
        hashtags=["SaaS", "#Ops", "Growth"],
        full_text="Full text",
    )
    assert li.hashtags == ["#SaaS", "#Ops", "#Growth"]

    thread = XThread(
        hook_tweet="Opening tweet",
        posts=["1/ First", "2/ Second", "3/ Third"],
        cta="Reply",
        hashtags=["#SaaS"],
    )
    assert len(thread.posts) == 3

    ig = InstagramCaption(
        hook="Hook",
        caption="Caption text",
        cta="Save this",
        hashtags=["#Design", "#UX", "#Workflow"],
        alt_text="Notebook on a bright wooden desk.",
    )
    assert ig.alt_text.startswith("Notebook")

    blog = BlogOutline(
        title="Guide Title",
        meta_description="Meta summary",
        target_audience="Ops Leads",
        introduction="Intro",
        sections=[
            BlogSection(heading="Sec 1", key_points=["Point 1"]),
            BlogSection(heading="Sec 2", key_points=["Point 2"]),
        ],
        conclusion_cta="Try this checklist",
        seo_keywords=["ops"],
    )
    assert len(blog.sections) == 2

    cal = ContentCalendar(
        topic="Topic",
        audience="Audience",
        calendar=[
            CalendarItem(
                day=i,
                channel="LinkedIn",
                format="post",
                objective="awareness",
                hook=f"Hook {i}",
                body="Body",
                cta="CTA",
                hashtags=["One", "#Two", "Three"],
                suggested_time="09:00 AM",
            )
            for i in range(1, 4)
        ],
    )
    assert cal.calendar[0].hashtags == ["#One", "#Two", "#Three"]
