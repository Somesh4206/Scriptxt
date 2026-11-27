"""Deterministic sample campaign builder for offline UI walkthroughs and testing."""

from __future__ import annotations

from scriptxt.models import (
    BlogOutline,
    BlogSection,
    CalendarItem,
    ContentCalendar,
    ContentRequest,
    GeneratedContentSuite,
    InstagramCaption,
    LinkedInPost,
    XThread,
)

SAMPLE_CALENDAR_TEMPLATES: tuple[dict[str, str], ...] = (
    {
        "channel": "LinkedIn",
        "format": "post",
        "objective": "awareness",
        "hook": "Most onboarding checklists fail because they teach buttons instead of outcomes.",
        "body": "Reframe your first-week emails around one fast operational win your customer can complete before lunch.",
        "suggested_time": "08:30 AM",
    },
    {
        "channel": "X",
        "format": "thread",
        "objective": "education",
        "hook": "Four quiet handoff gaps that slow down async product teams every week.",
        "body": "Walk through how short written briefs, owner tags, and clear review windows prevent Friday bottlenecks.",
        "suggested_time": "11:00 AM",
    },
    {
        "channel": "Instagram",
        "format": "carousel",
        "objective": "engagement",
        "hook": "Save this five-slide reset before your next sprint kickoff.",
        "body": "Break down scope pruning, risk flags, and daily check-ins in clean visual cards built for busy leads.",
        "suggested_time": "12:30 PM",
    },
    {
        "channel": "Blog",
        "format": "blog_outline",
        "objective": "lead_generation",
        "hook": "Why structured playbooks outperform ad-hoc team wikis during rapid growth.",
        "body": "Publish a step-by-step guide showing how to turn repeated project retros into reusable templates.",
        "suggested_time": "09:00 AM",
    },
    {
        "channel": "LinkedIn",
        "format": "post",
        "objective": "engagement",
        "hook": "Stop asking for status updates when a two-line decision log solves the problem.",
        "body": "Show how a shared decision register removes repeated slack threads and keeps distributed leads aligned.",
        "suggested_time": "08:45 AM",
    },
    {
        "channel": "X",
        "format": "post",
        "objective": "awareness",
        "hook": "Clarity beats urgency whenever a cross-functional launch hits mid-week turbulence.",
        "body": "Share a concise before-and-after prompt template teams can copy into their launch channel.",
        "suggested_time": "02:00 PM",
    },
    {
        "channel": "Instagram",
        "format": "reel",
        "objective": "education",
        "hook": "Three questions to ask before scheduling another recurring status call.",
        "body": "Record a 30-second breakdown contrasting synchronous status updates with written async digests.",
        "suggested_time": "05:15 PM",
    },
    {
        "channel": "LinkedIn",
        "format": "carousel",
        "objective": "lead_generation",
        "hook": "The lightweight editorial workflow our operations team uses to ship weekly guides.",
        "body": "Outline brief intake, SME review, guardrail QA, and multi-channel repurposing in six simple slides.",
        "suggested_time": "09:15 AM",
    },
    {
        "channel": "X",
        "format": "thread",
        "objective": "engagement",
        "hook": "Your best product documentation already lives inside resolved support tickets.",
        "body": "Explain how to turn recurring customer questions into clear educational threads without extra meetings.",
        "suggested_time": "10:30 AM",
    },
    {
        "channel": "Instagram",
        "format": "caption",
        "objective": "awareness",
        "hook": "Small workflow friction adds up faster than missing software features.",
        "body": "Spotlight one overlooked approval step and invite followers to share how they simplify weekly reviews.",
        "suggested_time": "01:00 PM",
    },
    {
        "channel": "Blog",
        "format": "blog_outline",
        "objective": "education",
        "hook": "How to audit your quarterly content backlog in under forty-five minutes.",
        "body": "Provide a scoring matrix for pruning stale drafts and refreshing high-intent evergreen articles.",
        "suggested_time": "09:30 AM",
    },
    {
        "channel": "LinkedIn",
        "format": "post",
        "objective": "education",
        "hook": "Great B2B copy sounds like a helpful teammate, never a brochure.",
        "body": "Contrast vague feature adjectives with concrete workflow examples your target buyers recognize.",
        "suggested_time": "08:15 AM",
    },
    {
        "channel": "X",
        "format": "post",
        "objective": "lead_generation",
        "hook": "One practical checklist beats ten abstract strategy decks.",
        "body": "Link readers to your concise implementation worksheet and ask which step they will test first.",
        "suggested_time": "03:30 PM",
    },
    {
        "channel": "Instagram",
        "format": "carousel",
        "objective": "engagement",
        "hook": "A Friday wrap-up ritual that sets Monday mornings up for calm focus.",
        "body": "Share four quick end-of-week prompts to close open loops and highlight next week's top priority.",
        "suggested_time": "04:00 PM",
    },
)


def build_sample_suite(request: ContentRequest) -> GeneratedContentSuite:
    """Create a complete, schema-valid sample ContentSuite matching the user's request."""
    cta_text = request.cta or f"Share how your team approaches {request.topic} in the comments."
    base_tags = [
        f"#{kw.strip().replace(' ', '')}"
        for kw in request.keywords[:3]
        if kw.strip()
    ]
    while len(base_tags) < 3:
        fallback = ["#ContentStrategy", "#WorkflowDesign", "#B2BMarketing"][len(base_tags)]
        if fallback not in base_tags:
            base_tags.append(fallback)

    linkedin_full = (
        f"Most teams approach {request.topic} by adding more tools instead of simplifying the workflow.\n\n"
        f"For {request.audience}, real momentum comes from turning a complex initiative into one repeatable, "
        "easy-to-audit weekly habit. When every stakeholder understands the exact goal, who owns the next step, "
        "and what a finished milestone looks like, execution gets calmer and far more consistent.\n\n"
        "Start by auditing your current process from the perspective of a first-time contributor. Remove redundant "
        "handoffs, document the core checklist in plain language, and focus each message on a single practical win "
        "instead of trying to cover everything at once. Clear structure beats last-minute hustle every single week.\n\n"
        "Practical takeaway: pick one recurring bottleneck this week, write down a three-step standard playbook, "
        "and review it with your team after one cycle to spot what still creates friction.\n\n"
        f"{cta_text}\n\n"
        f"{' '.join(base_tags[:3])}"
    )

    linkedin_post = (
        LinkedInPost(
            hook=f"Most teams approach {request.topic} by adding more tools instead of simplifying the workflow.",
            body=(
                f"For {request.audience}, real momentum comes from turning a complex initiative into one repeatable, "
                "easy-to-audit weekly habit. Start by auditing your process from the perspective of a first-time "
                "contributor, remove redundant handoffs, and document a single practical win."
            ),
            takeaway=(
                "Pick one recurring bottleneck this week, write down a three-step standard playbook, "
                "and review it after one cycle."
            ),
            cta=cta_text,
            hashtags=base_tags[:3],
            full_text=linkedin_full,
        )
        if "LinkedIn" in request.channels
        else None
    )

    x_thread = (
        XThread(
            hook_tweet=f"{request.topic} does not fail from a lack of effort—it stalls when {request.audience} lack a repeatable playbook.",
            posts=[
                f"1/ Define one clear outcome for {request.topic} before choosing channels or formats.",
                "2/ Replace long status recaps with short, structured briefs anyone on the team can scan in two minutes.",
                "3/ Build reusable checklists for recurring workflows so quality stays steady even during busy launches.",
                f"4/ End every piece with a focused next step tailored specifically for {request.audience}.",
            ],
            cta=cta_text,
            hashtags=base_tags[:3],
        )
        if "X" in request.channels
        else None
    )

    ig_tags = list(dict.fromkeys(base_tags + ["#DigitalWorkflow", "#CreatorSystems"]))[:5]
    instagram_caption = (
        InstagramCaption(
            hook=f"A calmer way for {request.audience} to tackle {request.topic}.",
            caption=(
                f"A calmer way for {request.audience} to tackle {request.topic}.\n\n"
                "Instead of reinventing your process every week, build one lightweight framework you can reuse:\n"
                "1. Clarify the audience problem in one sentence.\n"
                "2. Focus on one practical takeaway per post.\n"
                "3. Review clarity before hitting publish.\n\n"
                f"{cta_text}\n\n"
                f"{' '.join(ig_tags)}"
            ),
            cta=cta_text,
            hashtags=ig_tags,
            alt_text=(
                f"Clean editorial notebook and laptop on a bright desk illustrating a structured workflow plan for {request.topic}."
            ),
        )
        if "Instagram" in request.channels
        else None
    )

    blog_outline = (
        BlogOutline(
            title=f"A Practical Playbook for {request.topic}",
            meta_description=f"Learn how {request.audience} can apply {request.topic} with clear workflows and repeatable templates.",
            target_audience=request.audience,
            introduction=(
                f"Explain why {request.audience} often struggle to keep {request.topic} consistent, "
                "and introduce a structured, guardrail-first workflow."
            ),
            sections=[
                BlogSection(
                    heading="1. Clarify Audience Pain Points and Goals",
                    key_points=[
                        f"Identify the top weekly friction facing {request.audience}.",
                        "Align every piece of content with one measurable outcome.",
                    ],
                ),
                BlogSection(
                    heading="2. Build a Repeatable Prompt and Review Workflow",
                    key_points=[
                        "Standardize brief inputs: topic, audience, tone, and CTA.",
                        "Run quality checks for clarity, uniqueness, and factual safety.",
                    ],
                ),
                BlogSection(
                    heading="3. Repurpose Insights Across Channels",
                    key_points=[
                        "Adapt core ideas for LinkedIn, X, Instagram, and long-form guides.",
                        "Schedule balanced touchpoints across awareness and education.",
                    ],
                ),
            ],
            conclusion_cta=cta_text,
            seo_keywords=request.keywords or [request.topic, "content workflow", "editorial calendar"],
        )
        if "Blog" in request.channels
        else None
    )

    # Filter or map channels strictly to user-selected channels
    selected_channels = request.channels
    calendar_items: list[CalendarItem] = []
    for day_idx in range(1, request.calendar_days + 1):
        template = SAMPLE_CALENDAR_TEMPLATES[(day_idx - 1) % len(SAMPLE_CALENDAR_TEMPLATES)]
        channel = (
            template["channel"]
            if template["channel"] in selected_channels
            else selected_channels[(day_idx - 1) % len(selected_channels)]
        )
        format_map = {
            "LinkedIn": "post" if day_idx % 2 == 1 else "carousel",
            "X": "thread" if day_idx % 2 == 1 else "post",
            "Instagram": "carousel" if day_idx % 2 == 1 else "caption",
            "Blog": "blog_outline",
        }
        fmt = template["format"] if template["channel"] == channel else format_map[channel]
        calendar_items.append(
            CalendarItem(
                day=day_idx,
                channel=channel,  # type: ignore[arg-type]
                format=fmt,  # type: ignore[arg-type]
                objective=template["objective"],  # type: ignore[arg-type]
                hook=f"Day {day_idx}: {template['hook']}",
                body=f"{template['body']} Tailored for {request.audience} exploring {request.topic}.",
                cta=cta_text,
                hashtags=base_tags[:3],
                suggested_time=template["suggested_time"],
            )
        )

    calendar = ContentCalendar(
        topic=request.topic,
        audience=request.audience,
        calendar=calendar_items,
    )

    return GeneratedContentSuite(
        request=request,
        linkedin_post=linkedin_post,
        x_thread=x_thread,
        instagram_caption=instagram_caption,
        blog_outline=blog_outline,
        content_calendar=calendar,
    )
