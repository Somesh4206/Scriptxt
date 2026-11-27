"""Input and output guardrails, schema validation, and quality checks for SCRIPTXT."""

from __future__ import annotations

import re
from typing import Any, Iterable, Optional

import jsonschema
from pydantic import ValidationError

from scriptxt.config import (
    INSTAGRAM_MAX_CHARS,
    LINKEDIN_MAX_WORDS,
    LINKEDIN_MIN_WORDS,
    MAX_BRAND_VOICE_LENGTH,
    MAX_CALENDAR_DAYS,
    MAX_HASHTAGS,
    MAX_TOPIC_LENGTH,
    MIN_CALENDAR_DAYS,
    MIN_HASHTAGS,
    SUPPORTED_CHANNELS,
    SUPPORTED_FORMATS,
    SUPPORTED_OBJECTIVES,
    SUPPORTED_TONES,
    X_THREAD_MAX_POSTS,
    X_THREAD_MIN_POSTS,
)
from scriptxt.models import (
    BlogOutline,
    ContentCalendar,
    ContentRequest,
    GeneratedContentSuite,
    InstagramCaption,
    LinkedInPost,
    QualityCheckResult,
    QualityReport,
    XThread,
)
from scriptxt.schemas import CONTENT_CALENDAR_JSON_SCHEMA

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)"
)
CARD_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)")

UNSUPPORTED_CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bguaranteed\s+results?\b", re.IGNORECASE),
    re.compile(r"\b100%\s+(?:safe|guaranteed|effective|proven|risk[- ]?free)\b", re.IGNORECASE),
    re.compile(r"\bzero\s+risk\b", re.IGNORECASE),
    re.compile(r"\bnever\s+fails?\b", re.IGNORECASE),
    re.compile(r"\bmiracle\s+(?:cure|solution|results?)\b", re.IGNORECASE),
    re.compile(r"\b(?:studies|research|scientists)\s+(?:prove|show)\s+that\s+\d+%", re.IGNORECASE),
    re.compile(
        r"\b\d{1,3}(?:\.\d+)?%\s+(?:of\s+(?:users|customers|teams|companies|people)|"
        r"increase|decrease|boost|higher|lower|faster|more\s+revenue)\b",
        re.IGNORECASE,
    ),
)

PLACEHOLDER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\blorem\s+ipsum\b", re.IGNORECASE),
    re.compile(r"\binsert\s+(?:text|here|link|cta|name|topic)\b", re.IGNORECASE),
    re.compile(r"\[insert[^\]]*\]", re.IGNORECASE),
    re.compile(r"<insert[^>]*>", re.IGNORECASE),
    re.compile(r"\bplaceholder\b", re.IGNORECASE),
)


class InputGuardrailError(ValueError):
    """Raised when user inputs violate SCRIPTXT input guardrails."""


class OutputValidationError(ValueError):
    """Raised when generated content violates schema or guardrail rules."""


def count_words(text: str) -> int:
    """Count whitespace-delimited words in text."""
    return len(re.findall(r"\S+", text.strip()))


def normalize_hook(hook: str) -> str:
    """Normalize hook text for duplicate detection."""
    cleaned = re.sub(r"[^\w\s]", "", hook.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def validate_input_request(
    topic: str,
    audience: str,
    tone: str,
    channels: Iterable[str],
    calendar_days: int,
    brand_voice: Optional[str] = None,
    keywords: Optional[Iterable[str] | str] = None,
    cta: Optional[str] = None,
    content_goal: Optional[str] = None,
) -> ContentRequest:
    """Validate raw UI/CLI inputs against input guardrails and return a ContentRequest."""
    errors: list[str] = []

    topic_clean = (topic or "").strip()
    audience_clean = (audience or "").strip()

    if not topic_clean:
        errors.append("Topic cannot be empty.")
    elif len(topic_clean) > MAX_TOPIC_LENGTH:
        errors.append(
            f"Topic exceeds maximum length of {MAX_TOPIC_LENGTH} characters "
            f"({len(topic_clean)} provided)."
        )

    if not audience_clean:
        errors.append("Audience cannot be empty.")

    if tone not in SUPPORTED_TONES:
        errors.append(
            f"Unsupported tone '{tone}'. Choose one of: {', '.join(SUPPORTED_TONES)}."
        )

    channel_list = [ch.strip() for ch in channels if ch and ch.strip()]
    unsupported = [ch for ch in channel_list if ch not in SUPPORTED_CHANNELS]
    if unsupported:
        errors.append(
            f"Unsupported channel(s): {', '.join(unsupported)}. "
            f"Allowed: {', '.join(SUPPORTED_CHANNELS)}."
        )
    if not channel_list:
        errors.append("At least one channel must be selected.")

    if not (MIN_CALENDAR_DAYS <= int(calendar_days) <= MAX_CALENDAR_DAYS):
        errors.append(
            f"Calendar days must be between {MIN_CALENDAR_DAYS} and {MAX_CALENDAR_DAYS}."
        )

    if brand_voice and len(brand_voice.strip()) > MAX_BRAND_VOICE_LENGTH:
        errors.append(
            f"Brand voice exceeds maximum length of {MAX_BRAND_VOICE_LENGTH} characters "
            f"({len(brand_voice.strip())} provided)."
        )

    if errors:
        raise InputGuardrailError(" ".join(errors))

    try:
        return ContentRequest(
            topic=topic_clean,
            audience=audience_clean,
            tone=tone,  # type: ignore[arg-type]
            channels=channel_list,  # type: ignore[arg-type]
            calendar_days=calendar_days,
            brand_voice=brand_voice,
            keywords=keywords or [],  # type: ignore[arg-type]
            cta=cta,
            content_goal=content_goal or "Educate the audience and drive meaningful engagement.",
        )
    except ValidationError as exc:
        raise InputGuardrailError(str(exc)) from exc


def find_duplicate_hooks(hooks: Iterable[str]) -> list[str]:
    """Return duplicate hooks (preserving first duplicate text found)."""
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for hook in hooks:
        norm = normalize_hook(hook)
        if not norm:
            continue
        if norm in seen:
            duplicates.append(hook)
        else:
            seen[norm] = hook
    return duplicates


def detect_unsupported_claims(text: str) -> list[str]:
    """Detect unsupported absolute claims or unverified statistics in text."""
    if not text:
        return []
    findings: list[str] = []
    for pattern in UNSUPPORTED_CLAIM_PATTERNS:
        for match in pattern.finditer(text):
            snippet = match.group(0).strip()
            # Allow percentages if explicitly tagged as needing verification in context window.
            window_start = max(0, match.start() - 40)
            window_end = min(len(text), match.end() + 40)
            context = text[window_start:window_end].lower()
            if "[needs verification]" in context and "%" in snippet:
                continue
            if snippet not in findings:
                findings.append(snippet)
    return findings


def _passes_luhn(digits: str) -> bool:
    """Check if a digit string satisfies the Luhn checksum."""
    if not digits.isdigit() or not (13 <= len(digits) <= 19):
        return False
    total = 0
    reverse_digits = digits[::-1]
    for index, char in enumerate(reverse_digits):
        num = int(char)
        if index % 2 == 1:
            num *= 2
            if num > 9:
                num -= 9
        total += num
    return total % 10 == 0


def detect_pii(text: str) -> list[str]:
    """Detect obvious PII (emails, phone numbers, card-like numbers) in text."""
    if not text:
        return []
    findings: list[str] = []

    for match in EMAIL_PATTERN.finditer(text):
        findings.append(f"Email: {match.group(0)}")

    for match in PHONE_PATTERN.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) >= 10:
            findings.append(f"Phone: {match.group(0).strip()}")

    for match in CARD_PATTERN.finditer(text):
        raw = match.group(0).strip()
        digits = re.sub(r"\D", "", raw)
        if 13 <= len(digits) <= 19 and (_passes_luhn(digits) or len(digits) == 16):
            findings.append(f"Card-like number: {raw}")

    # Deduplicate preserving order
    return list(dict.fromkeys(findings))


def detect_placeholders(text: str) -> list[str]:
    """Detect leftover placeholder strings such as TODO, Lorem ipsum, or insert here."""
    if not text:
        return []
    findings: list[str] = []
    for pattern in PLACEHOLDER_PATTERNS:
        for match in pattern.finditer(text):
            snippet = match.group(0).strip()
            if snippet not in findings:
                findings.append(snippet)
    return findings


def validate_calendar_schema(
    data: dict[str, Any],
    expected_days: Optional[int] = None,
    allowed_channels: Optional[Iterable[str]] = None,
) -> ContentCalendar:
    """Validate a raw calendar dictionary against JSON Schema, Pydantic, and business rules."""
    try:
        jsonschema.validate(instance=data, schema=CONTENT_CALENDAR_JSON_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise OutputValidationError(f"Calendar JSON schema validation failed: {exc.message}") from exc

    try:
        calendar = ContentCalendar.model_validate(data)
    except ValidationError as exc:
        raise OutputValidationError(f"Calendar Pydantic validation failed: {exc}") from exc

    if expected_days is not None and len(calendar.calendar) != expected_days:
        raise OutputValidationError(
            f"Expected {expected_days} calendar days, got {len(calendar.calendar)}."
        )

    allowed = set(allowed_channels) if allowed_channels else set(SUPPORTED_CHANNELS)
    for item in calendar.calendar:
        if item.channel not in allowed:
            raise OutputValidationError(
                f"Day {item.day} uses disallowed channel '{item.channel}'."
            )
        if item.format not in SUPPORTED_FORMATS:
            raise OutputValidationError(
                f"Day {item.day} uses invalid format '{item.format}'."
            )
        if item.objective not in SUPPORTED_OBJECTIVES:
            raise OutputValidationError(
                f"Day {item.day} uses invalid objective '{item.objective}'."
            )
        for field_name, field_val in (
            ("hook", item.hook),
            ("body", item.body),
            ("cta", item.cta),
            ("suggested_time", item.suggested_time),
        ):
            if not field_val.strip():
                raise OutputValidationError(f"Day {item.day} has an empty '{field_name}'.")

    duplicates = find_duplicate_hooks(item.hook for item in calendar.calendar)
    if duplicates:
        raise OutputValidationError(
            f"Duplicate hooks detected in calendar: {', '.join(duplicates)}"
        )

    return calendar


def _collect_suite_text(suite: GeneratedContentSuite) -> str:
    """Gather all generated text across outputs for safety and PII scans."""
    parts: list[str] = []
    if suite.linkedin_post:
        parts.extend(
            [
                suite.linkedin_post.hook,
                suite.linkedin_post.body,
                suite.linkedin_post.takeaway,
                suite.linkedin_post.cta,
                suite.linkedin_post.full_text,
            ]
        )
    if suite.x_thread:
        parts.append(suite.x_thread.hook_tweet)
        parts.extend(suite.x_thread.posts)
        parts.append(suite.x_thread.cta)
    if suite.instagram_caption:
        parts.extend(
            [
                suite.instagram_caption.hook,
                suite.instagram_caption.caption,
                suite.instagram_caption.cta,
                suite.instagram_caption.alt_text,
            ]
        )
    if suite.blog_outline:
        parts.extend(
            [
                suite.blog_outline.title,
                suite.blog_outline.meta_description,
                suite.blog_outline.introduction,
                suite.blog_outline.conclusion_cta,
            ]
        )
        for section in suite.blog_outline.sections:
            parts.append(section.heading)
            parts.extend(section.key_points)
    if suite.content_calendar:
        parts.extend([suite.content_calendar.topic, suite.content_calendar.audience])
        for item in suite.content_calendar.calendar:
            parts.extend([item.hook, item.body, item.cta, item.suggested_time])
    return "\n".join(parts)


def run_quality_checks(suite: GeneratedContentSuite) -> QualityReport:
    """Execute all automated quality, schema, length, and safety guardrail checks."""
    checks: list[QualityCheckResult] = []
    req = suite.request

    # 1. JSON schema validation (Calendar)
    if suite.content_calendar is not None:
        raw_cal = suite.content_calendar.model_dump()
        try:
            jsonschema.validate(instance=raw_cal, schema=CONTENT_CALENDAR_JSON_SCHEMA)
            checks.append(
                QualityCheckResult(
                    name="JSON schema validation",
                    passed=True,
                    details="Content calendar conforms strictly to CONTENT_CALENDAR_JSON_SCHEMA.",
                )
            )
        except jsonschema.ValidationError as exc:
            checks.append(
                QualityCheckResult(
                    name="JSON schema validation",
                    passed=False,
                    details=f"Schema error: {exc.message}",
                )
            )
    else:
        checks.append(
            QualityCheckResult(
                name="JSON schema validation",
                passed=False,
                details="No content calendar generated to validate.",
            )
        )

    # 2. Required fields present
    missing_sections: list[str] = []
    if "LinkedIn" in req.channels and suite.linkedin_post is None:
        missing_sections.append("LinkedIn Post")
    if "X" in req.channels and suite.x_thread is None:
        missing_sections.append("X Thread")
    if "Instagram" in req.channels and suite.instagram_caption is None:
        missing_sections.append("Instagram Caption")
    if "Blog" in req.channels and suite.blog_outline is None:
        missing_sections.append("Blog Outline")
    if suite.content_calendar is None:
        missing_sections.append("Content Calendar")

    checks.append(
        QualityCheckResult(
            name="Required fields present",
            passed=len(missing_sections) == 0,
            details=(
                "All requested channel outputs and required fields are present."
                if not missing_sections
                else f"Missing outputs: {', '.join(missing_sections)}."
            ),
        )
    )

    # 3. Calendar length matches requested days
    if suite.content_calendar is not None:
        actual_days = len(suite.content_calendar.calendar)
        expected_days = req.calendar_days
        checks.append(
            QualityCheckResult(
                name="Calendar length matches requested days",
                passed=actual_days == expected_days,
                details=f"Expected {expected_days} days; found {actual_days} days.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="Calendar length matches requested days",
                passed=False,
                details="No content calendar generated.",
            )
        )

    # 4. No duplicate hooks
    if suite.content_calendar is not None:
        dup_hooks = find_duplicate_hooks(
            item.hook for item in suite.content_calendar.calendar
        )
        checks.append(
            QualityCheckResult(
                name="No duplicate hooks",
                passed=len(dup_hooks) == 0,
                details=(
                    "All calendar item hooks are unique."
                    if not dup_hooks
                    else f"Duplicate hook(s) detected: {', '.join(dup_hooks)}."
                ),
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="No duplicate hooks",
                passed=False,
                details="No content calendar generated.",
            )
        )

    # 5. LinkedIn post word count (120-180 words)
    if suite.linkedin_post is not None:
        li_words = count_words(suite.linkedin_post.full_text)
        li_ok = LINKEDIN_MIN_WORDS <= li_words <= LINKEDIN_MAX_WORDS
        checks.append(
            QualityCheckResult(
                name="LinkedIn post is 120–180 words",
                passed=li_ok,
                details=f"Word count: {li_words} words (target {LINKEDIN_MIN_WORDS}–{LINKEDIN_MAX_WORDS}).",
            )
        )

    # 6. X thread has 3-7 posts
    if suite.x_thread is not None:
        post_count = len(suite.x_thread.posts)
        x_ok = X_THREAD_MIN_POSTS <= post_count <= X_THREAD_MAX_POSTS
        checks.append(
            QualityCheckResult(
                name="X thread has 3–7 posts",
                passed=x_ok,
                details=f"Thread post count: {post_count} (target {X_THREAD_MIN_POSTS}–{X_THREAD_MAX_POSTS}).",
            )
        )

    # 7. Instagram caption under 2,200 characters
    if suite.instagram_caption is not None:
        ig_chars = len(suite.instagram_caption.caption)
        ig_ok = 0 < ig_chars < INSTAGRAM_MAX_CHARS
        checks.append(
            QualityCheckResult(
                name="Instagram caption is under 2,200 characters",
                passed=ig_ok,
                details=f"Character count: {ig_chars} / {INSTAGRAM_MAX_CHARS}.",
            )
        )

    # 8. Hashtag count between 3 and 8
    hashtag_issues: list[str] = []
    if suite.linkedin_post is not None:
        li_tags = len(suite.linkedin_post.hashtags)
        if not (MIN_HASHTAGS <= li_tags <= MAX_HASHTAGS):
            hashtag_issues.append(f"LinkedIn has {li_tags} hashtags")
    if suite.instagram_caption is not None:
        ig_tags = len(suite.instagram_caption.hashtags)
        if not (MIN_HASHTAGS <= ig_tags <= MAX_HASHTAGS):
            hashtag_issues.append(f"Instagram has {ig_tags} hashtags")
    if suite.content_calendar is not None:
        for item in suite.content_calendar.calendar:
            c_tags = len(item.hashtags)
            if not (MIN_HASHTAGS <= c_tags <= MAX_HASHTAGS):
                hashtag_issues.append(f"Calendar Day {item.day} has {c_tags} hashtags")

    checks.append(
        QualityCheckResult(
            name="Hashtag count is between 3 and 8",
            passed=len(hashtag_issues) == 0,
            details=(
                "All checked items have 3–8 hashtags."
                if not hashtag_issues
                else "; ".join(hashtag_issues)
            ),
        )
    )

    # 9. No unsupported claims
    full_text = _collect_suite_text(suite)
    claims = detect_unsupported_claims(full_text)
    checks.append(
        QualityCheckResult(
            name="No unsupported claims or invented statistics",
            passed=len(claims) == 0,
            details=(
                "No absolute claims or unverified statistics detected."
                if not claims
                else f"Flagged phrase(s): {', '.join(claims)}."
            ),
        )
    )

    # 10. No obvious PII
    pii_hits = detect_pii(full_text)
    checks.append(
        QualityCheckResult(
            name="No obvious PII",
            passed=len(pii_hits) == 0,
            details=(
                "No emails, phone numbers, or card-like numbers detected."
                if not pii_hits
                else f"PII detected: {', '.join(pii_hits)}."
            ),
        )
    )

    # 11. No empty or placeholder text
    placeholders = detect_placeholders(full_text)
    checks.append(
        QualityCheckResult(
            name="No placeholder text",
            passed=len(placeholders) == 0,
            details=(
                "No placeholder markers (TODO, Lorem ipsum, insert here) found."
                if not placeholders
                else f"Placeholder text detected: {', '.join(placeholders)}."
            ),
        )
    )

    return QualityReport(checks=checks)
