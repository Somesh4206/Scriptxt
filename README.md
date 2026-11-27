# SCRIPTXT: Prompt-Powered Content Generator

**SCRIPTXT** is a controlled LLM content pipeline built with Python 3.11+, Streamlit, Pydantic, and the **Google GenAI Python SDK (`google-genai`)** using Gemini Structured Outputs. It converts a single campaign topic into platform-native LinkedIn posts, X threads, Instagram captions with alt text, SEO-ready blog outlines, and a schema-validated multi-day content calendar—with editable outputs, automated quality/safety guardrails, and JSON/CSV export.

---

## Architecture

```text
+-------------------------------------------------------------------+
|                        Streamlit UI (streamlit_app.py)            |
|  Sidebar Brief  |  7 Tabs: LinkedIn, X, IG, Blog, Calendar,       |
|  & Controls     |          Export, Quality Checks (st.session)    |
+--------+-----------------------------------+----------------------+
         |                                   |
         v                                   v
+------------------------+       +----------------------------------+
| Input Guardrails       |       | Exporters (exporters.py)         |
| (validators.py)        |       |  - JSON (strict calendar/suite)  |
|  - ContentRequest      |       |  - CSV (pandas DataFrame)        |
+--------+---------------+       +----------------------------------+
         |
         v
+------------------------+       +----------------------------------+
| Prompt Registry        |       | Strict JSON Schemas (schemas.py) |
| (prompts.py, versioned)|       |  - response_mime_type=json       |
+--------+---------------+       |  - response_json_schema          |
         |                       +----------------+-----------------+
         v                                        |
+-------------------------------------------------+-----------------+
| Generation Pipeline (generator.py & calendar.py)                  |
|  - Google Gemini API (`client.models.generate_content`)           |
|  - Retry & error handling (auth, quota, timeout, empty output)    |
+--------+----------------------------------------------------------+
         |
         v
+-------------------------------------------------------------------+
| Output Guardrails & Offline Evaluation (validators.py, eval)      |
|  - Schema validation, word/char limits, duplicate hook check      |
|  - Claim, PII, and placeholder detection                          |
+-------------------------------------------------------------------+
```

---

## Setup Instructions

### 1. Prerequisites

- Python **3.11+**
- A Gemini API key (`GEMINI_API_KEY`, automatically provided in AI Studio or set in `.env` for local runs)

### 2. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and add your Gemini API key if running outside AI Studio:

```bash
cp .env.example .env
```

`.env`:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=auto
```

> Never commit `.env` to version control (it is listed in `.gitignore`).

---

## Running the Applications

### Run the Streamlit Web App

```bash
streamlit run streamlit_app.py
```

In the sidebar:
1. Enter a **Topic** and **Target Audience**.
2. Choose **Tone**, **Channels** (`LinkedIn`, `X`, `Instagram`, `Blog`), and **Calendar Length** (`3–14` days).
3. Optionally add **Brand Voice**, **Keywords**, **CTA**, and **Content Goal**.
4. Click **Generate Content** (live Gemini API) or **Load Sample Campaign** (offline deterministic demo).
5. Edit any generated asset or calendar day directly in the tabs, inspect automated **Quality Checks**, and export via the **Export** tab.

### Run the Week 1 CLI Entry Point

```bash
python app.py
```

### Run Unit Tests (Mocked LLM Calls)

```bash
pytest -v
```

### Run Offline Evaluation Harness

```bash
python -m scriptxt.evaluation
```

Reads `evaluations/sample_topics.csv`, runs generation and automated guardrail checks, and writes metrics to `evaluations/results.csv`. See `evaluations/evaluation_rubric.md` for the 1–5 human evaluation rubric.

---

## Example Input & Output

### Example Input

- **Topic**: `Async Onboarding Playbooks for Distributed SaaS Teams`
- **Target Audience**: `B2B SaaS Operations Leads`
- **Tone**: `Professional`
- **Channels**: `LinkedIn`, `X`, `Instagram`, `Blog`
- **Calendar Length**: `7` days
- **Keywords**: `async onboarding, SaaS ops, playbooks`
- **CTA**: `Comment your team's top onboarding bottleneck`

### Example Calendar JSON Item

```json
{
  "topic": "Async Onboarding Playbooks for Distributed SaaS Teams",
  "audience": "B2B SaaS Operations Leads",
  "calendar": [
    {
      "day": 1,
      "channel": "LinkedIn",
      "format": "post",
      "objective": "awareness",
      "hook": "Most onboarding checklists fail because they teach buttons instead of outcomes.",
      "body": "Reframe your first-week emails around one fast operational win your customer can complete before lunch.",
      "cta": "Comment your team's top onboarding bottleneck",
      "hashtags": ["#AsyncOnboarding", "#SaaSOps", "#Playbooks"],
      "suggested_time": "08:30 AM"
    }
  ]
}
```

---

## Limitations, Assumptions, and Safety Notes

- **API Dependency & Free-Tier Multi-Model Routing**: Live generation uses the `google-genai` Python SDK (`client.models.generate_content`) with `response_mime_type="application/json"` and `response_json_schema`. In `auto` mode (the default), SCRIPTXT routes tasks across all active free-tier text models (`gemini-4-hydrogen` for LinkedIn posts, blog outlines, and multi-day calendars; `gemini-3.1-flash-lite` for fast X threads and Instagram captions) with automatic fallback between them if a model hits a rate limit or transient error.
- **Factual Verification**: Prompts instruct the model never to fabricate statistics, customer names, testimonials, or product claims, and to mark unverified claims with `[Needs verification]`. Human editorial review is still required before publishing.
- **Automated Guardrails Scope**: Built-in regex and schema checks catch common absolute claims, placeholder strings (`TODO`, `Lorem ipsum`), duplicate hooks, length violations, and obvious PII (emails, phone numbers, card-like sequences), but are not a substitute for brand/legal review.
- **No Medical, Legal, or Financial Advice**: System prompts explicitly prohibit medical, legal, financial, hateful, harassing, or impersonation outputs.
- **Local Session State**: Edits and generated outputs live in Streamlit's `st.session_state` for the active browser session; export JSON or CSV before closing if you want to keep a copy.
