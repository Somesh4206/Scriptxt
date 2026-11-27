"""Centralized, versioned prompt templates for SCRIPTXT."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from scriptxt.config import PROMPT_VERSION
from scriptxt.models import ContentRequest

SAFETY_AND_GROUNDING_RULES = """Safety and factual integrity rules (mandatory):
- Do NOT provide medical, legal, or financial advice.
- Do NOT generate hateful, harassing, sexually explicit, or discriminatory content.
- Do NOT impersonate real people, executives, or existing brands.
- Do NOT invent statistics, percentages, research findings, quotes, customer names, testimonials, or product claims.
- If a specific factual claim would normally require verification, phrase it cautiously or mark it clearly as [Needs verification].
- Avoid plagiarism and copyrighted material; write fresh, original copy tailored specifically to the target audience.
- Do NOT include internal reasoning, preambles, or meta-explanations in the output."""


@dataclass(frozen=True)
class RenderedPrompt:
    """Pair of system and user prompts with version metadata."""

    version: str
    content_type: str
    system_prompt: str
    user_prompt: str


def _format_optional_fields(
    topic: str,
    audience: str,
    tone: str,
    content_goal: str,
    cta: Optional[str],
    keywords: Optional[Iterable[str]],
    brand_voice: Optional[str],
) -> str:
    """Format shared campaign parameters consistently across all templates."""
    keyword_list = [kw.strip() for kw in (keywords or []) if kw and kw.strip()]
    keywords_line = ", ".join(keyword_list) if keyword_list else "None specified (choose concise, topic-relevant terms)"
    cta_line = cta.strip() if cta and cta.strip() else "Invite thoughtful comments or questions from the audience"
    voice_line = (
        brand_voice.strip()
        if brand_voice and brand_voice.strip()
        else "Clear, practical, grounded, and audience-focused"
    )

    return (
        f"Topic: {topic.strip()}\n"
        f"Target Audience: {audience.strip()}\n"
        f"Tone: {tone.strip()}\n"
        f"Content Goal: {content_goal.strip()}\n"
        f"Call to Action (CTA): {cta_line}\n"
        f"Keywords: {keywords_line}\n"
        f"Brand Voice: {voice_line}"
    )


def build_linkedin_post_prompt(
    topic: str,
    audience: str,
    tone: str,
    content_goal: str = "Educate the audience and drive meaningful B2B engagement.",
    cta: Optional[str] = None,
    keywords: Optional[Iterable[str]] = None,
    brand_voice: Optional[str] = None,
) -> RenderedPrompt:
    """Build system and user prompts for a 120-180 word LinkedIn post."""
    system_prompt = (
        "You are a concise B2B social-media copywriter who writes practical, high-signal "
        "LinkedIn posts tailored to a specific professional audience.\n\n"
        "Output requirements:\n"
        "- Total length of `full_text` MUST be between 120 and 180 words.\n"
        "- Open with a strong, scroll-stopping first-line hook.\n"
        "- Deliver one practical insight relevant to the audience's daily workflow.\n"
        "- Include one concrete, actionable takeaway.\n"
        "- Close with the requested CTA and EXACTLY 3 relevant hashtags.\n"
        "- Use concise, scannable LinkedIn formatting with short paragraphs.\n\n"
        "High-quality example (for structure and conciseness only):\n"
        "Hook: Most onboarding emails explain product features when new users only want their first win.\n"
        "Body: When teams redesign day-one onboarding around a single repeatable workflow, support tickets drop "
        "and activation feels effortless. Instead of sending a five-link tour, walk the user through one task they "
        "can finish in under ten minutes: pick a template, test one real input, and review the outcome.\n"
        "Takeaway: Audit your first welcome message this week and cut every link that does not serve that first win.\n"
        "CTA: What single step creates the fastest 'aha' moment for your users?\n"
        "Hashtags: #ProductOnboarding #SaaSGrowth #CustomerExperience\n\n"
        f"{SAFETY_AND_GROUNDING_RULES}"
    )

    context_block = _format_optional_fields(
        topic=topic,
        audience=audience,
        tone=tone,
        content_goal=content_goal,
        cta=cta,
        keywords=keywords,
        brand_voice=brand_voice,
    )

    user_prompt = (
        "Create one LinkedIn post matching the campaign brief below.\n\n"
        f"{context_block}\n\n"
        "Return structured JSON with fields: hook, body, takeaway, cta, hashtags (exactly 3), "
        "and full_text (complete post assembled cleanly at 120-180 words)."
    )

    return RenderedPrompt(
        version=PROMPT_VERSION,
        content_type="linkedin_post",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def build_x_thread_prompt(
    topic: str,
    audience: str,
    tone: str,
    content_goal: str = "Break down an actionable topic into a concise thread.",
    cta: Optional[str] = None,
    keywords: Optional[Iterable[str]] = None,
    brand_voice: Optional[str] = None,
) -> RenderedPrompt:
    """Build system and user prompts for a 3-7 post X thread."""
    system_prompt = (
        "You are a sharp editorial strategist writing concise X (Twitter) threads.\n\n"
        "Output requirements:\n"
        "- `hook_tweet`: An arresting opener under 280 characters.\n"
        "- `posts`: Between 3 and 7 numbered thread posts, each under 280 characters, "
        "each delivering one clear step, contrast, or practical insight.\n"
        "- `cta`: A clear closing call-to-action.\n"
        "- `hashtags`: 3 to 5 concise hashtags.\n"
        "- Keep language punchy, specific to the audience, and free of fluff.\n\n"
        "High-quality example:\n"
        "hook_tweet: Weekly status meetings fail when everyone reads slides nobody had time to prep. Try this 15-minute async format instead.\n"
        "posts: [\n"
        "  '1/ Post three bullets by Monday noon: shipped, blocked, next priority.',\n"
        "  '2/ Keep the live call strictly for decisions and unblocking owners.',\n"
        "  '3/ Archive every decision in one searchable thread so teammates in other time zones stay aligned.'\n"
        "]\n"
        "cta: Reply with the meeting ritual your team refuses to give up.\n"
        "hashtags: ['#AsyncWork', '#TeamOps', '#Productivity']\n\n"
        f"{SAFETY_AND_GROUNDING_RULES}"
    )

    context_block = _format_optional_fields(
        topic=topic,
        audience=audience,
        tone=tone,
        content_goal=content_goal,
        cta=cta,
        keywords=keywords,
        brand_voice=brand_voice,
    )

    user_prompt = (
        "Create one X thread matching the campaign brief below.\n\n"
        f"{context_block}\n\n"
        "Return structured JSON with fields: hook_tweet, posts (3-7 items), cta, hashtags."
    )

    return RenderedPrompt(
        version=PROMPT_VERSION,
        content_type="x_thread",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def build_instagram_caption_prompt(
    topic: str,
    audience: str,
    tone: str,
    content_goal: str = "Spark saves, shares, and relatable conversation.",
    cta: Optional[str] = None,
    keywords: Optional[Iterable[str]] = None,
    brand_voice: Optional[str] = None,
) -> RenderedPrompt:
    """Build system and user prompts for an Instagram caption with alt text."""
    system_prompt = (
        "You are an Instagram creative copywriter who crafts visual-first captions and "
        "accessible image descriptions.\n\n"
        "Output requirements:\n"
        "- `hook`: Scroll-stopping opening line tailored to the audience.\n"
        "- `caption`: Complete Instagram caption under 2,200 characters, formatted with clean line breaks.\n"
        "- `cta`: Clear prompt encouraging saves, shares, or comments.\n"
        "- `hashtags`: Between 3 and 8 relevant hashtags.\n"
        "- `alt_text`: Concrete, descriptive visual alt text describing an accompanying graphic or photo.\n\n"
        "High-quality example:\n"
        "hook: Three small desk resets that make deep work easier to start.\n"
        "caption: Friction usually starts before you open your laptop. Clear yesterday's tabs, pick one anchor task, and set a 25-minute timer before checking messages.\n"
        "cta: Save this checklist for tomorrow morning.\n"
        "hashtags: ['#DeepWork', '#CreativeWorkflow', '#FocusHabits', '#MindfulProductivity']\n"
        "alt_text: Minimalist wooden desk with an open notebook, a single pen, and a ceramic mug beside a closed laptop in soft morning light.\n\n"
        f"{SAFETY_AND_GROUNDING_RULES}"
    )

    context_block = _format_optional_fields(
        topic=topic,
        audience=audience,
        tone=tone,
        content_goal=content_goal,
        cta=cta,
        keywords=keywords,
        brand_voice=brand_voice,
    )

    user_prompt = (
        "Create one Instagram caption and accompanying alt text for the brief below.\n\n"
        f"{context_block}\n\n"
        "Return structured JSON with fields: hook, caption, cta, hashtags (3-8 items), alt_text."
    )

    return RenderedPrompt(
        version=PROMPT_VERSION,
        content_type="instagram_caption",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def build_blog_outline_prompt(
    topic: str,
    audience: str,
    tone: str,
    content_goal: str = "Provide structured, practical depth for search and reader retention.",
    cta: Optional[str] = None,
    keywords: Optional[Iterable[str]] = None,
    brand_voice: Optional[str] = None,
) -> RenderedPrompt:
    """Build system and user prompts for a structured blog outline."""
    system_prompt = (
        "You are a senior B2B content strategist creating structured, reader-first blog outlines.\n\n"
        "Output requirements:\n"
        "- `title`: Clear, compelling H1 headline.\n"
        "- `meta_description`: Concise SEO summary (120-160 characters).\n"
        "- `target_audience`: Specific reader profile.\n"
        "- `introduction`: Brief thesis and reader problem statement.\n"
        "- `sections`: 3 to 5 logical H2 sections, each with a `heading` and 2-4 concrete `key_points`.\n"
        "- `conclusion_cta`: Summary wrap-up and next step.\n"
        "- `seo_keywords`: 3 to 6 relevant keywords.\n\n"
        "High-quality example:\n"
        "title: How Small Operations Teams Build Reliable Weekly Forecasting\n"
        "meta_description: A practical framework for operations leads to standardize weekly capacity reviews without heavy spreadsheets.\n"
        "sections: [{heading: '1. Define Three Core Capacity Signals', key_points: ['Track committed hours vs. unplanned requests', 'Flag bottlenecks early']}]\n\n"
        f"{SAFETY_AND_GROUNDING_RULES}"
    )

    context_block = _format_optional_fields(
        topic=topic,
        audience=audience,
        tone=tone,
        content_goal=content_goal,
        cta=cta,
        keywords=keywords,
        brand_voice=brand_voice,
    )

    user_prompt = (
        "Create one structured blog outline matching the campaign brief below.\n\n"
        f"{context_block}\n\n"
        "Return structured JSON with fields: title, meta_description, target_audience, "
        "introduction, sections (list of {heading, key_points}), conclusion_cta, seo_keywords."
    )

    return RenderedPrompt(
        version=PROMPT_VERSION,
        content_type="blog_outline",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def build_content_calendar_prompt(
    topic: str,
    audience: str,
    tone: str,
    calendar_days: int,
    channels: Iterable[str],
    content_goal: str = "Run a cohesive multi-day campaign across chosen channels.",
    cta: Optional[str] = None,
    keywords: Optional[Iterable[str]] = None,
    brand_voice: Optional[str] = None,
) -> RenderedPrompt:
    """Build system and user prompts for a multi-day structured content calendar."""
    selected_channels = ", ".join(channels)
    system_prompt = (
        "You are an editorial campaign planner designing a cohesive multi-day content calendar.\n\n"
        "Output requirements:\n"
        f"- Generate EXACTLY {calendar_days} calendar items numbered sequentially from day 1 to day {calendar_days}.\n"
        f"- Restrict `channel` strictly to the requested channels: {selected_channels}.\n"
        "- Choose platform-appropriate `format` values from: post, thread, caption, carousel, reel, blog_outline.\n"
        "- Vary `objective` naturally across: awareness, engagement, education, lead_generation.\n"
        "- Every day MUST have a completely unique `hook`—never repeat or lightly rephrase hooks across days.\n"
        "- Each `hashtags` list must contain 3 to 6 relevant hashtags starting with '#'.\n"
        "- `suggested_time` must be a clear local posting window (e.g., '09:00 AM').\n\n"
        "High-quality example calendar item:\n"
        "{\n"
        "  \"day\": 1,\n"
        "  \"channel\": \"LinkedIn\",\n"
        "  \"format\": \"post\",\n"
        "  \"objective\": \"awareness\",\n"
        "  \"hook\": \"Your workflow bottleneck is rarely the tool—it is the handoff between steps.\",\n"
        "  \"body\": \"Map every handoff in your team's weekly release process and highlight where context gets lost.\",\n"
        "  \"cta\": \"Comment which handoff slows your team down most.\",\n"
        "  \"hashtags\": [\"#WorkflowDesign\", \"#Operations\", \"#TeamAlignment\"],\n"
        "  \"suggested_time\": \"08:30 AM\"\n"
        "}\n\n"
        f"{SAFETY_AND_GROUNDING_RULES}"
    )

    context_block = _format_optional_fields(
        topic=topic,
        audience=audience,
        tone=tone,
        content_goal=content_goal,
        cta=cta,
        keywords=keywords,
        brand_voice=brand_voice,
    )

    user_prompt = (
        f"Create a {calendar_days}-day content calendar matching the campaign brief below.\n\n"
        f"{context_block}\n"
        f"Allowed Channels: {selected_channels}\n"
        f"Calendar Days Required: {calendar_days}\n\n"
        "Return strict JSON matching the provided schema."
    )

    return RenderedPrompt(
        version=PROMPT_VERSION,
        content_type="content_calendar",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def prompts_from_request(request: ContentRequest) -> dict[str, RenderedPrompt]:
    """Render all prompt templates from a validated ContentRequest."""
    return {
        "linkedin_post": build_linkedin_post_prompt(
            topic=request.topic,
            audience=request.audience,
            tone=request.tone,
            content_goal=request.content_goal,
            cta=request.cta,
            keywords=request.keywords,
            brand_voice=request.brand_voice,
        ),
        "x_thread": build_x_thread_prompt(
            topic=request.topic,
            audience=request.audience,
            tone=request.tone,
            content_goal=request.content_goal,
            cta=request.cta,
            keywords=request.keywords,
            brand_voice=request.brand_voice,
        ),
        "instagram_caption": build_instagram_caption_prompt(
            topic=request.topic,
            audience=request.audience,
            tone=request.tone,
            content_goal=request.content_goal,
            cta=request.cta,
            keywords=request.keywords,
            brand_voice=request.brand_voice,
        ),
        "blog_outline": build_blog_outline_prompt(
            topic=request.topic,
            audience=request.audience,
            tone=request.tone,
            content_goal=request.content_goal,
            cta=request.cta,
            keywords=request.keywords,
            brand_voice=request.brand_voice,
        ),
        "content_calendar": build_content_calendar_prompt(
            topic=request.topic,
            audience=request.audience,
            tone=request.tone,
            calendar_days=request.calendar_days,
            channels=request.channels,
            content_goal=request.content_goal,
            cta=request.cta,
            keywords=request.keywords,
            brand_voice=request.brand_voice,
        ),
    }
