"""Unit tests for JSON and CSV exporters in scriptxt.exporters."""

from __future__ import annotations

import csv
import json
from io import StringIO

from scriptxt.exporters import (
    calendar_to_dataframe,
    export_calendar_csv,
    export_calendar_json,
    export_suite_json,
)
from scriptxt.models import ContentRequest
from scriptxt.sample_data import build_sample_suite


def test_export_calendar_json_round_trip() -> None:
    req = ContentRequest(
        topic="Release QA Checklists",
        audience="Engineering Managers",
        tone="Educational",
        channels=["LinkedIn", "X", "Instagram", "Blog"],
        calendar_days=5,
    )
    suite = build_sample_suite(req)
    assert suite.content_calendar is not None

    json_str = export_calendar_json(suite.content_calendar)
    parsed = json.loads(json_str)
    assert parsed["topic"] == "Release QA Checklists"
    assert parsed["audience"] == "Engineering Managers"
    assert len(parsed["calendar"]) == 5
    assert parsed["calendar"][0]["day"] == 1


def test_export_calendar_csv_columns_and_rows() -> None:
    req = ContentRequest(
        topic="Release QA Checklists",
        audience="Engineering Managers",
        tone="Educational",
        channels=["LinkedIn", "X"],
        calendar_days=4,
    )
    suite = build_sample_suite(req)
    assert suite.content_calendar is not None

    df = calendar_to_dataframe(suite.content_calendar)
    assert len(df) == 4
    assert list(df.columns) == [
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

    csv_text = export_calendar_csv(suite.content_calendar)
    rows = list(csv.DictReader(StringIO(csv_text)))
    assert len(rows) == 4
    assert rows[0]["day"] == "1"
    assert rows[0]["topic"] == "Release QA Checklists"


def test_export_suite_json_includes_all_sections() -> None:
    req = ContentRequest(
        topic="Design Systems",
        audience="Product Designers",
        tone="Bold",
        channels=["LinkedIn", "X", "Instagram", "Blog"],
        calendar_days=3,
    )
    suite = build_sample_suite(req)
    raw = export_suite_json(suite)
    parsed = json.loads(raw)
    assert parsed["linkedin_post"] is not None
    assert parsed["x_thread"] is not None
    assert parsed["instagram_caption"] is not None
    assert parsed["blog_outline"] is not None
    assert len(parsed["content_calendar"]["calendar"]) == 3
