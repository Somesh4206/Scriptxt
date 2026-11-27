"""Unit tests for prompt templates in scriptxt.prompts."""

from __future__ import annotations

from scriptxt.config import PROMPT_VERSION
from scriptxt.models import ContentRequest
from scriptxt.prompts import (
    build_blog_outline_prompt,
    build_content_calendar_prompt,
    build_instagram_caption_prompt,
    build_linkedin_post_prompt,
    build_x_thread_prompt,
    prompts_from_request,
)


def test_linkedin_prompt_renders_all_parameters_and_guardrails() -> None:
    rendered = build_linkedin_post_prompt(
        topic="Async Standups",
        audience="Engineering Managers",
        tone="Educational",
        content_goal="Improve team alignment",
        cta="Share your async ritual",
        keywords=["async", "standups"],
        brand_voice="Calm and direct",
    )
    assert rendered.version == PROMPT_VERSION
    assert "Async Standups" in rendered.user_prompt
    assert "Engineering Managers" in rendered.user_prompt
    assert "Educational" in rendered.user_prompt
    assert "Improve team alignment" in rendered.user_prompt
    assert "Share your async ritual" in rendered.user_prompt
    assert "async, standups" in rendered.user_prompt
    assert "Calm and direct" in rendered.user_prompt
    assert "120 and 180 words" in rendered.system_prompt
    assert "EXACTLY 3 relevant hashtags" in rendered.system_prompt
    assert "Do NOT invent statistics" in rendered.system_prompt
    assert "High-quality example" in rendered.system_prompt


def test_all_prompt_templates_include_examples_and_safety_rules() -> None:
    prompts = [
        build_x_thread_prompt("Topic A", "Founders", "Bold"),
        build_instagram_caption_prompt("Topic B", "Designers", "Friendly"),
        build_blog_outline_prompt("Topic C", "Ops Leads", "Professional"),
        build_content_calendar_prompt(
            topic="Topic D",
            audience="Marketers",
            tone="Witty",
            calendar_days=5,
            channels=["LinkedIn", "X"],
        ),
    ]
    for prompt in prompts:
        assert "High-quality example" in prompt.system_prompt
        assert "Do NOT provide medical, legal, or financial advice" in prompt.system_prompt
        assert "Avoid plagiarism" in prompt.system_prompt


def test_prompts_from_request_generates_all_five_templates() -> None:
    req = ContentRequest(
        topic="Design Systems",
        audience="Frontend Engineers",
        tone="Professional",
        channels=["LinkedIn", "X", "Instagram", "Blog"],
        calendar_days=7,
        brand_voice="Technical and crisp",
        keywords=["accessibility", "tokens"],
        cta="Download our token checklist",
    )
    rendered = prompts_from_request(req)
    assert set(rendered.keys()) == {
        "linkedin_post",
        "x_thread",
        "instagram_caption",
        "blog_outline",
        "content_calendar",
    }
    assert "7-day content calendar" in rendered["content_calendar"].user_prompt
    assert "Design Systems" in rendered["blog_outline"].user_prompt
