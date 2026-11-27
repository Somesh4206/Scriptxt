"""Offline evaluation harness for SCRIPTXT content generation and guardrails."""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from google import genai

from scriptxt.calendar import generate_content_calendar
from scriptxt.generator import (
    generate_blog_outline,
    generate_instagram_caption,
    generate_linkedin_post,
    generate_x_thread,
)
from scriptxt.models import ContentRequest, GeneratedContentSuite, QualityReport
from scriptxt.validators import run_quality_checks, validate_input_request


@dataclass
class EvaluationSampleResult:
    """Per-topic evaluation outcome and automated check metrics."""

    topic: str
    audience: str
    tone: str
    calendar_days: int
    success: bool
    latency_seconds: float
    schema_passed: bool
    length_limit_passed: bool
    duplicate_hook_failed: bool
    guardrail_violated: bool
    passed_checks: int
    total_checks: int
    error_message: str = ""


@dataclass
class EvaluationSummary:
    """Aggregate offline evaluation metrics across all sample topics."""

    total_attempts: int
    successful_generations: int
    schema_pass_rate: float
    length_limit_pass_rate: float
    duplicate_hook_failure_rate: float
    guardrail_violation_rate: float
    average_latency_seconds: float
    results: list[EvaluationSampleResult]


def load_sample_topics(csv_path: str | Path) -> list[ContentRequest]:
    """Read sample topics from CSV and convert each row to a validated ContentRequest."""
    path = Path(csv_path)
    requests: list[ContentRequest] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            channels = [
                ch.strip()
                for ch in (row.get("channels") or "LinkedIn,X,Instagram,Blog").split(",")
                if ch.strip()
            ]
            keywords = [
                kw.strip()
                for kw in (row.get("keywords") or "").split(",")
                if kw.strip()
            ]
            req = validate_input_request(
                topic=row.get("topic", ""),
                audience=row.get("audience", ""),
                tone=row.get("tone", "Professional"),
                channels=channels,
                calendar_days=int(row.get("calendar_days", 7)),
                brand_voice=row.get("brand_voice") or None,
                keywords=keywords,
                cta=row.get("cta") or None,
                content_goal=row.get("content_goal") or None,
            )
            requests.append(req)
    return requests


def _check_passed(report: QualityReport, check_name_prefix: str) -> Optional[bool]:
    """Look up pass/fail state for a named check prefix."""
    for check in report.checks:
        if check.name.startswith(check_name_prefix):
            return check.passed
    return None


def evaluate_request(
    request: ContentRequest,
    client: Optional[genai.Client] = None,
    suite_builder: Optional[Callable[[ContentRequest], GeneratedContentSuite]] = None,
) -> EvaluationSampleResult:
    """Generate content for one ContentRequest and compute automated quality metrics."""
    started = time.perf_counter()
    try:
        if suite_builder is not None:
            suite = suite_builder(request)
        else:
            linkedin_post = (
                generate_linkedin_post(
                    topic=request.topic,
                    audience=request.audience,
                    tone=request.tone,
                    cta=request.cta or "",
                    keywords=request.keywords,
                    brand_voice=request.brand_voice,
                    content_goal=request.content_goal,
                    client=client,
                )
                if "LinkedIn" in request.channels
                else None
            )
            x_thread = (
                generate_x_thread(request, client=client)
                if "X" in request.channels
                else None
            )
            instagram_caption = (
                generate_instagram_caption(request, client=client)
                if "Instagram" in request.channels
                else None
            )
            blog_outline = (
                generate_blog_outline(request, client=client)
                if "Blog" in request.channels
                else None
            )
            calendar = generate_content_calendar(request, client=client)
            suite = GeneratedContentSuite(
                request=request,
                linkedin_post=linkedin_post,
                x_thread=x_thread,
                instagram_caption=instagram_caption,
                blog_outline=blog_outline,
                content_calendar=calendar,
            )

        latency = time.perf_counter() - started
        report = run_quality_checks(suite)

        schema_ok = bool(_check_passed(report, "JSON schema validation"))
        calendar_len_ok = _check_passed(report, "Calendar length") is True
        li_len_ok = _check_passed(report, "LinkedIn post")
        x_len_ok = _check_passed(report, "X thread")
        ig_len_ok = _check_passed(report, "Instagram caption")
        length_checks = [
            flag
            for flag in (calendar_len_ok, li_len_ok, x_len_ok, ig_len_ok)
            if flag is not None
        ]
        length_limit_ok = all(length_checks)

        dup_hook_failed = _check_passed(report, "No duplicate hooks") is False
        claims_failed = _check_passed(report, "No unsupported claims") is False
        pii_failed = _check_passed(report, "No obvious PII") is False
        placeholder_failed = _check_passed(report, "No placeholder text") is False
        guardrail_violated = claims_failed or pii_failed or placeholder_failed

        return EvaluationSampleResult(
            topic=request.topic,
            audience=request.audience,
            tone=request.tone,
            calendar_days=request.calendar_days,
            success=True,
            latency_seconds=round(latency, 4),
            schema_passed=schema_ok,
            length_limit_passed=length_limit_ok,
            duplicate_hook_failed=dup_hook_failed,
            guardrail_violated=guardrail_violated,
            passed_checks=report.passed_count,
            total_checks=len(report.checks),
        )
    except Exception as exc:
        latency = time.perf_counter() - started
        return EvaluationSampleResult(
            topic=request.topic,
            audience=request.audience,
            tone=request.tone,
            calendar_days=request.calendar_days,
            success=False,
            latency_seconds=round(latency, 4),
            schema_passed=False,
            length_limit_passed=False,
            duplicate_hook_failed=False,
            guardrail_violated=True,
            passed_checks=0,
            total_checks=0,
            error_message=str(exc),
        )


def run_evaluation(
    sample_csv_path: str | Path = "evaluations/sample_topics.csv",
    results_csv_path: str | Path = "evaluations/results.csv",
    client: Optional[genai.Client] = None,
    suite_builder: Optional[Callable[[ContentRequest], GeneratedContentSuite]] = None,
) -> EvaluationSummary:
    """Run offline evaluation across sample topics and persist results to CSV."""
    requests = load_sample_topics(sample_csv_path)
    results = [
        evaluate_request(req, client=client, suite_builder=suite_builder)
        for req in requests
    ]

    output_path = Path(results_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "topic",
        "audience",
        "tone",
        "calendar_days",
        "success",
        "latency_seconds",
        "schema_passed",
        "length_limit_passed",
        "duplicate_hook_failed",
        "guardrail_violated",
        "passed_checks",
        "total_checks",
        "error_message",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            writer.writerow(
                {
                    "topic": item.topic,
                    "audience": item.audience,
                    "tone": item.tone,
                    "calendar_days": item.calendar_days,
                    "success": item.success,
                    "latency_seconds": item.latency_seconds,
                    "schema_passed": item.schema_passed,
                    "length_limit_passed": item.length_limit_passed,
                    "duplicate_hook_failed": item.duplicate_hook_failed,
                    "guardrail_violated": item.guardrail_violated,
                    "passed_checks": item.passed_checks,
                    "total_checks": item.total_checks,
                    "error_message": item.error_message,
                }
            )

    total = len(results)
    if total == 0:
        return EvaluationSummary(
            total_attempts=0,
            successful_generations=0,
            schema_pass_rate=0.0,
            length_limit_pass_rate=0.0,
            duplicate_hook_failure_rate=0.0,
            guardrail_violation_rate=0.0,
            average_latency_seconds=0.0,
            results=[],
        )

    successful = sum(1 for r in results if r.success)
    return EvaluationSummary(
        total_attempts=total,
        successful_generations=successful,
        schema_pass_rate=round(sum(1 for r in results if r.schema_passed) / total, 4),
        length_limit_pass_rate=round(
            sum(1 for r in results if r.length_limit_passed) / total, 4
        ),
        duplicate_hook_failure_rate=round(
            sum(1 for r in results if r.duplicate_hook_failed) / total, 4
        ),
        guardrail_violation_rate=round(
            sum(1 for r in results if r.guardrail_violated) / total, 4
        ),
        average_latency_seconds=round(
            sum(r.latency_seconds for r in results) / total, 4
        ),
        results=results,
    )


if __name__ == "__main__":
    summary = run_evaluation()
    print(
        f"Completed {summary.successful_generations}/{summary.total_attempts} "
        f"generations | schema pass rate={summary.schema_pass_rate:.1%} | "
        f"avg latency={summary.average_latency_seconds:.2f}s"
    )
