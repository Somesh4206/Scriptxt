"""JSON and CSV exporters for SCRIPTXT generated content."""

from __future__ import annotations

import json
from io import StringIO
from typing import Any

import pandas as pd

from scriptxt.models import ContentCalendar, GeneratedContentSuite


def calendar_to_dataframe(calendar: ContentCalendar) -> pd.DataFrame:
    """Convert a ContentCalendar into a normalized pandas DataFrame."""
    rows: list[dict[str, Any]] = []
    for item in calendar.calendar:
        rows.append(
            {
                "topic": calendar.topic,
                "audience": calendar.audience,
                "day": item.day,
                "channel": item.channel,
                "format": item.format,
                "objective": item.objective,
                "hook": item.hook,
                "body": item.body,
                "cta": item.cta,
                "hashtags": " ".join(item.hashtags),
                "suggested_time": item.suggested_time,
            }
        )
    columns = [
        "topic",
        "audience",
        "day",
        "channel",
        "format",
        "objective",
        "hook",
        "body",
        "cta",
        "hashtags",
        "suggested_time",
    ]
    return pd.DataFrame(rows, columns=columns)


def export_calendar_json(calendar: ContentCalendar, indent: int = 2) -> str:
    """Serialize a ContentCalendar to formatted JSON matching the strict schema."""
    return json.dumps(calendar.model_dump(mode="json"), indent=indent, ensure_ascii=False)


def export_calendar_csv(calendar: ContentCalendar) -> str:
    """Serialize a ContentCalendar to UTF-8 CSV string using pandas."""
    df = calendar_to_dataframe(calendar)
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()


def export_suite_json(suite: GeneratedContentSuite, indent: int = 2) -> str:
    """Serialize the complete GeneratedContentSuite (request + all channels + calendar) to JSON."""
    return json.dumps(suite.model_dump(mode="json"), indent=indent, ensure_ascii=False)
