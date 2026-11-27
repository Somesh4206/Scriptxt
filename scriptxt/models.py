"""Pydantic data models for SCRIPTXT requests, outputs, and validation reports."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from scriptxt.config import (
    MAX_AUDIENCE_LENGTH,
    MAX_BRAND_VOICE_LENGTH,
    MAX_CALENDAR_DAYS,
    MAX_TOPIC_LENGTH,
    MIN_CALENDAR_DAYS,
    SUPPORTED_CHANNELS,
)

ToneType = Literal[
    "Professional",
    "Friendly",
    "Bold",
    "Educational",
    "Inspirational",
    "Witty",
]

ChannelType = Literal["LinkedIn", "X", "Instagram", "Blog"]

CalendarFormatType = Literal[
    "post",
    "thread",
    "caption",
    "carousel",
    "reel",
    "blog_outline",
]

CalendarObjectiveType = Literal[
    "awareness",
    "engagement",
    "education",
    "lead_generation",
]


class ContentRequest(BaseModel):
    """Validated user request for generating multi-channel content."""

    model_config = ConfigDict(str_strip_whitespace=True)

    topic: str = Field(..., description="Core subject or campaign topic.")
    audience: str = Field(..., description="Intended target audience.")
    tone: ToneType = Field(default="Professional", description="Desired writing tone.")
    channels: list[ChannelType] = Field(
        default_factory=lambda: ["LinkedIn", "X", "Instagram", "Blog"],
        description="Selected distribution channels.",
    )
    calendar_days: int = Field(
        default=7,
        ge=MIN_CALENDAR_DAYS,
        le=MAX_CALENDAR_DAYS,
        description="Number of days in the generated content calendar (3-14).",
    )
    brand_voice: Optional[str] = Field(
        default=None,
        description="Optional brand voice guidelines (max 1,000 characters).",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Optional SEO or campaign keywords.",
    )
    cta: Optional[str] = Field(
        default=None,
        description="Optional call-to-action to weave into generated pieces.",
    )
    content_goal: str = Field(
        default="Educate the audience and drive meaningful engagement.",
        description="Primary strategic goal for the campaign.",
    )

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        """Ensure topic is non-empty and within the 300-character ceiling."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Topic must not be empty.")
        if len(cleaned) > MAX_TOPIC_LENGTH:
            raise ValueError(
                f"Topic must be {MAX_TOPIC_LENGTH} characters or fewer (got {len(cleaned)})."
            )
        return cleaned

    @field_validator("audience")
    @classmethod
    def validate_audience(cls, value: str) -> str:
        """Ensure audience is non-empty and reasonably bounded."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Audience must not be empty.")
        if len(cleaned) > MAX_AUDIENCE_LENGTH:
            raise ValueError(
                f"Audience must be {MAX_AUDIENCE_LENGTH} characters or fewer (got {len(cleaned)})."
            )
        return cleaned

    @field_validator("brand_voice")
    @classmethod
    def validate_brand_voice(cls, value: Optional[str]) -> Optional[str]:
        """Ensure optional brand voice does not exceed 1,000 characters."""
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) > MAX_BRAND_VOICE_LENGTH:
            raise ValueError(
                f"Brand voice must be {MAX_BRAND_VOICE_LENGTH} characters or fewer "
                f"(got {len(cleaned)})."
            )
        return cleaned

    @field_validator("cta", "content_goal")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        """Strip whitespace and collapse empty optional strings."""
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("content_goal")
    @classmethod
    def ensure_content_goal(cls, value: Optional[str]) -> str:
        """Provide a clear default goal if omitted or blank."""
        return value or "Educate the audience and drive meaningful engagement."

    @field_validator("channels", mode="before")
    @classmethod
    def validate_channels(cls, value: object) -> list[str]:
        """Validate channels as a non-empty subset of supported channels."""
        if not isinstance(value, (list, tuple, set)):
            raise ValueError("Channels must be provided as a list of channel names.")
        deduped: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError(f"Unsupported channel value: {item!r}")
            cleaned = item.strip()
            if cleaned not in SUPPORTED_CHANNELS:
                raise ValueError(
                    f"Unsupported channel '{cleaned}'. "
                    f"Allowed channels: {', '.join(SUPPORTED_CHANNELS)}."
                )
            if cleaned not in deduped:
                deduped.append(cleaned)
        if not deduped:
            raise ValueError("Select at least one channel from LinkedIn, X, Instagram, or Blog.")
        return deduped

    @field_validator("keywords", mode="before")
    @classmethod
    def parse_keywords(cls, value: object) -> list[str]:
        """Accept either a list of keywords or a comma-separated string."""
        if value is None:
            return []
        if isinstance(value, str):
            items = [part.strip() for part in value.split(",")]
        elif isinstance(value, (list, tuple)):
            items = [str(part).strip() for part in value]
        else:
            raise ValueError("Keywords must be a list of strings or comma-separated string.")
        deduped: list[str] = []
        for item in items:
            if item and item not in deduped:
                deduped.append(item)
        return deduped


class LinkedInPost(BaseModel):
    """Structured LinkedIn post output."""

    hook: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    takeaway: str = Field(..., min_length=1)
    cta: str = Field(..., min_length=1)
    hashtags: list[str] = Field(..., min_length=1)
    full_text: str = Field(..., min_length=1)

    @field_validator("hashtags")
    @classmethod
    def normalize_hashtags(cls, value: list[str]) -> list[str]:
        """Normalize hashtags to include a leading '#' and remove blanks."""
        normalized: list[str] = []
        for tag in value:
            cleaned = tag.strip().replace(" ", "")
            if not cleaned:
                continue
            if not cleaned.startswith("#"):
                cleaned = f"#{cleaned}"
            if cleaned not in normalized:
                normalized.append(cleaned)
        if not normalized:
            raise ValueError("LinkedIn post must contain at least one hashtag.")
        return normalized


class XThread(BaseModel):
    """Structured X (Twitter) thread output."""

    hook_tweet: str = Field(..., min_length=1)
    posts: list[str] = Field(..., min_length=3, max_length=7)
    cta: str = Field(..., min_length=1)
    hashtags: list[str] = Field(default_factory=list)


class InstagramCaption(BaseModel):
    """Structured Instagram caption with accessibility alt text."""

    hook: str = Field(..., min_length=1)
    caption: str = Field(..., min_length=1)
    cta: str = Field(..., min_length=1)
    hashtags: list[str] = Field(..., min_length=1)
    alt_text: str = Field(..., min_length=1)


class BlogSection(BaseModel):
    """Single structured section in a blog outline."""

    heading: str = Field(..., min_length=1)
    key_points: list[str] = Field(..., min_length=1)


class BlogOutline(BaseModel):
    """Structured long-form blog outline."""

    title: str = Field(..., min_length=1)
    meta_description: str = Field(..., min_length=1)
    target_audience: str = Field(..., min_length=1)
    introduction: str = Field(..., min_length=1)
    sections: list[BlogSection] = Field(..., min_length=2)
    conclusion_cta: str = Field(..., min_length=1)
    seo_keywords: list[str] = Field(default_factory=list)


class CalendarItem(BaseModel):
    """Single scheduled entry in a multi-day content calendar."""

    day: int = Field(..., ge=1, le=MAX_CALENDAR_DAYS)
    channel: ChannelType
    format: CalendarFormatType
    objective: CalendarObjectiveType
    hook: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    cta: str = Field(..., min_length=1)
    hashtags: list[str] = Field(..., min_length=1)
    suggested_time: str = Field(..., min_length=1)

    @field_validator("hashtags")
    @classmethod
    def clean_hashtags(cls, value: list[str]) -> list[str]:
        """Ensure hashtags are formatted cleanly with leading '#'."""
        cleaned_list: list[str] = []
        for tag in value:
            cleaned = tag.strip().replace(" ", "")
            if not cleaned:
                continue
            if not cleaned.startswith("#"):
                cleaned = f"#{cleaned}"
            if cleaned not in cleaned_list:
                cleaned_list.append(cleaned)
        if not cleaned_list:
            raise ValueError("Calendar item must include at least one hashtag.")
        return cleaned_list


class ContentCalendar(BaseModel):
    """Structured multi-day content calendar."""

    topic: str = Field(..., min_length=1)
    audience: str = Field(..., min_length=1)
    calendar: list[CalendarItem] = Field(..., min_length=MIN_CALENDAR_DAYS, max_length=MAX_CALENDAR_DAYS)


class GeneratedContentSuite(BaseModel):
    """Aggregated outputs generated for a single SCRIPTXT campaign."""

    request: ContentRequest
    linkedin_post: Optional[LinkedInPost] = None
    x_thread: Optional[XThread] = None
    instagram_caption: Optional[InstagramCaption] = None
    blog_outline: Optional[BlogOutline] = None
    content_calendar: Optional[ContentCalendar] = None


class QualityCheckResult(BaseModel):
    """Single pass/fail guardrail or structural check result."""

    name: str
    passed: bool
    severity: Literal["error", "warning", "info"] = "error"
    details: str


class QualityReport(BaseModel):
    """Summary of all automated quality and safety checks."""

    checks: list[QualityCheckResult] = Field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """Return True if every check passed."""
        return all(check.passed for check in self.checks)

    @property
    def passed_count(self) -> int:
        """Count checks that passed."""
        return sum(1 for check in self.checks if check.passed)

    @property
    def failed_count(self) -> int:
        """Count checks that failed."""
        return sum(1 for check in self.checks if not check.passed)
