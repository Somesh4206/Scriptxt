"""Streamlit web application for SCRIPTXT: Prompt-Powered Content Generator."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from scriptxt.calendar import CalendarGenerationError, generate_content_calendar
from scriptxt.config import (
    FREE_TIER_TEXT_MODELS,
    INSTAGRAM_MAX_CHARS,
    MAX_BRAND_VOICE_LENGTH,
    MAX_CALENDAR_DAYS,
    MAX_TOPIC_LENGTH,
    MIN_CALENDAR_DAYS,
    MODEL_ROUTING_AUTO,
    SUPPORTED_CHANNELS,
    SUPPORTED_TONES,
)
from scriptxt.exporters import (
    calendar_to_dataframe,
    export_calendar_csv,
    export_calendar_json,
    export_suite_json,
)
from scriptxt.generator import (
    GenerationError,
    create_gemini_client,
    generate_blog_outline,
    generate_instagram_caption,
    generate_linkedin_post,
    generate_x_thread,
)
from scriptxt.models import (
    BlogSection,
    ContentRequest,
    GeneratedContentSuite,
    QualityReport,
)
from scriptxt.sample_data import build_sample_suite
from scriptxt.validators import (
    InputGuardrailError,
    count_words,
    run_quality_checks,
    validate_input_request,
)

st.set_page_config(
    page_title="SCRIPTXT — Prompt-Powered Content Generator",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
  .block-container {
    padding-top: 3.1rem;
    padding-bottom: 3rem;
    max-width: 1180px;
  }
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.55rem;
  }
  .scriptxt-header {
    border-bottom: 1px solid rgba(128, 128, 128, 0.22);
    padding-bottom: 0.9rem;
    margin-bottom: 1.25rem;
  }
  .scriptxt-kicker {
    font-size: 0.78rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    color: #b45309;
    margin-bottom: 0.2rem;
  }
  .scriptxt-title {
    font-size: 2rem;
    font-weight: 750;
    line-height: 1.15;
    margin: 0;
  }
  .scriptxt-subtitle {
    font-size: 0.96rem;
    opacity: 0.78;
    margin-top: 0.35rem;
    margin-bottom: 0;
  }
  .check-row {
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.55rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
  }
  .badge-pass {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    background-color: #dcfce7;
    color: #166534;
    white-space: nowrap;
  }
  .badge-fail {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    background-color: #fee2e2;
    color: #991b1b;
    white-space: nowrap;
  }
</style>
"""


def _init_session_state() -> None:
    """Initialize required Streamlit session state keys once per session."""
    defaults: dict[str, object] = {
        "form_topic": "",
        "form_audience": "",
        "form_tone": "Professional",
        "form_model": MODEL_ROUTING_AUTO,
        "form_channels": list(SUPPORTED_CHANNELS),
        "form_calendar_days": 7,
        "form_brand_voice": "",
        "form_keywords": "",
        "form_cta": "",
        "form_content_goal": "Educate the audience and drive meaningful engagement.",
        "generated_suite": None,
        "quality_report": None,
        "last_error": None,
        "generation_notice": None,
    }
    for key, default_val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_val


def _parse_hashtag_string(raw: str) -> list[str]:
    """Parse space- or comma-separated hashtags into a normalized list."""
    tokens = [part.strip() for part in raw.replace(",", " ").split() if part.strip()]
    normalized: list[str] = []
    for token in tokens:
        tag = token if token.startswith("#") else f"#{token}"
        if tag not in normalized:
            normalized.append(tag)
    return normalized


def _refresh_quality_checks() -> None:
    """Recompute automated quality checks from current session state suite."""
    suite: GeneratedContentSuite | None = st.session_state.get("generated_suite")
    if suite is not None:
        st.session_state["quality_report"] = run_quality_checks(suite)
    else:
        st.session_state["quality_report"] = None


def _run_live_generation(
    request: ContentRequest,
    model: str = MODEL_ROUTING_AUTO,
) -> GeneratedContentSuite:
    """Execute the Gemini API pipeline in parallel across free-tier models."""
    client = create_gemini_client()

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            "calendar": pool.submit(
                generate_content_calendar, request, client=client, model=model
            ),
            "linkedin": (
                pool.submit(
                    generate_linkedin_post,
                    topic=request.topic,
                    audience=request.audience,
                    tone=request.tone,
                    cta=request.cta or "",
                    keywords=request.keywords,
                    brand_voice=request.brand_voice,
                    content_goal=request.content_goal,
                    client=client,
                    model=model,
                )
                if "LinkedIn" in request.channels
                else None
            ),
            "x_thread": (
                pool.submit(generate_x_thread, request, client=client, model=model)
                if "X" in request.channels
                else None
            ),
            "instagram": (
                pool.submit(
                    generate_instagram_caption, request, client=client, model=model
                )
                if "Instagram" in request.channels
                else None
            ),
            "blog": (
                pool.submit(generate_blog_outline, request, client=client, model=model)
                if "Blog" in request.channels
                else None
            ),
        }

        content_calendar = futures["calendar"].result()
        linkedin_post = futures["linkedin"].result() if futures["linkedin"] else None
        x_thread = futures["x_thread"].result() if futures["x_thread"] else None
        instagram_caption = (
            futures["instagram"].result() if futures["instagram"] else None
        )
        blog_outline = futures["blog"].result() if futures["blog"] else None

    return GeneratedContentSuite(
        request=request,
        linkedin_post=linkedin_post,
        x_thread=x_thread,
        instagram_caption=instagram_caption,
        blog_outline=blog_outline,
        content_calendar=content_calendar,
    )


def _handle_load_sample() -> None:
    """Callback for Load Sample Campaign button (safe to update widget keys here)."""
    st.session_state["last_error"] = None
    st.session_state["generation_notice"] = None
    if not str(st.session_state.get("form_topic", "")).strip():
        st.session_state["form_topic"] = "Async Onboarding Playbooks for Distributed SaaS Teams"
    if not str(st.session_state.get("form_audience", "")).strip():
        st.session_state["form_audience"] = "B2B SaaS Operations Leads"
    if not st.session_state.get("form_channels"):
        st.session_state["form_channels"] = list(SUPPORTED_CHANNELS)
    if not str(st.session_state.get("form_keywords", "")).strip():
        st.session_state["form_keywords"] = "async onboarding, SaaS ops, playbooks"
    if not str(st.session_state.get("form_cta", "")).strip():
        st.session_state["form_cta"] = "Comment your team's biggest onboarding bottleneck."

    try:
        request = validate_input_request(
            topic=str(st.session_state["form_topic"]),
            audience=str(st.session_state["form_audience"]),
            tone=str(st.session_state["form_tone"]),
            channels=list(st.session_state["form_channels"]),
            calendar_days=int(st.session_state["form_calendar_days"]),
            brand_voice=str(st.session_state["form_brand_voice"]),
            keywords=str(st.session_state["form_keywords"]),
            cta=str(st.session_state["form_cta"]),
            content_goal=str(st.session_state["form_content_goal"]),
        )
        suite = build_sample_suite(request)
        st.session_state["generated_suite"] = suite
        _refresh_quality_checks()
        st.session_state["generation_notice"] = (
            "Loaded offline sample campaign. Edit any field below or export to JSON/CSV."
        )
    except InputGuardrailError as exc:
        st.session_state["last_error"] = str(exc)


def _render_sidebar() -> None:
    """Render sidebar campaign controls and generation triggers."""
    with st.sidebar:
        st.subheader("Campaign Brief")

        with st.form("campaign_brief_form"):
            st.text_input(
                "Topic *",
                key="form_topic",
                max_chars=MAX_TOPIC_LENGTH,
                placeholder="e.g., Async Onboarding Playbooks for SaaS Teams",
                help=f"Required. Up to {MAX_TOPIC_LENGTH} characters.",
            )
            st.text_input(
                "Target Audience *",
                key="form_audience",
                max_chars=MAX_TOPIC_LENGTH,
                placeholder="e.g., B2B SaaS Operations Leads",
                help="Required. Specify who this content is written for.",
            )
            st.selectbox(
                "Tone",
                options=list(SUPPORTED_TONES),
                key="form_tone",
            )
            model_options = [MODEL_ROUTING_AUTO, *FREE_TIER_TEXT_MODELS]
            st.selectbox(
                "Gemini Free-Tier Model",
                options=model_options,
                format_func=lambda m: (
                    "Auto (Route all free-tier models)" if m == MODEL_ROUTING_AUTO else m
                ),
                key="form_model",
                help="Auto routes tasks across gemini-4-hydrogen and gemini-3.1-flash-lite with automatic fallback.",
            )
            st.multiselect(
                "Channels",
                options=list(SUPPORTED_CHANNELS),
                key="form_channels",
                help="Select one or more target platforms.",
            )
            st.slider(
                "Calendar Length (Days)",
                min_value=MIN_CALENDAR_DAYS,
                max_value=MAX_CALENDAR_DAYS,
                key="form_calendar_days",
            )
            st.text_area(
                "Brand Voice (Optional)",
                key="form_brand_voice",
                max_chars=MAX_BRAND_VOICE_LENGTH,
                height=68,
                placeholder="e.g., Calm, direct, practical, zero hype.",
                help=f"Optional. Up to {MAX_BRAND_VOICE_LENGTH} characters.",
            )
            st.text_input(
                "Keywords (Optional)",
                key="form_keywords",
                placeholder="Comma-separated, e.g., async onboarding, playbooks",
            )
            st.text_input(
                "Call to Action / CTA (Optional)",
                key="form_cta",
                placeholder="e.g., Share your team's top onboarding bottleneck",
            )
            st.text_input(
                "Content Goal (Optional)",
                key="form_content_goal",
            )

            generate_submitted = st.form_submit_button(
                "Generate Content",
                type="primary",
                use_container_width=True,
            )

        st.button(
            "Load Sample Campaign",
            use_container_width=True,
            help="Populate a deterministic sample campaign locally without making an API call.",
            on_click=_handle_load_sample,
        )

        if generate_submitted:
            st.session_state["last_error"] = None
            st.session_state["generation_notice"] = None
            try:
                request = validate_input_request(
                    topic=str(st.session_state.get("form_topic", "")),
                    audience=str(st.session_state.get("form_audience", "")),
                    tone=str(st.session_state.get("form_tone", "Professional")),
                    channels=list(st.session_state.get("form_channels", [])),
                    calendar_days=int(st.session_state.get("form_calendar_days", 7)),
                    brand_voice=str(st.session_state.get("form_brand_voice", "")),
                    keywords=str(st.session_state.get("form_keywords", "")),
                    cta=str(st.session_state.get("form_cta", "")),
                    content_goal=str(st.session_state.get("form_content_goal", "")),
                )
                selected_model = str(st.session_state.get("form_model", MODEL_ROUTING_AUTO))
                with st.spinner("Generating multi-channel campaign via Gemini AI..."):
                    suite = _run_live_generation(request, model=selected_model)
                st.session_state["generated_suite"] = suite
                _refresh_quality_checks()
                st.session_state["generation_notice"] = (
                    f"Generated campaign for '{request.topic}' ({request.calendar_days}-day calendar)."
                )
            except (InputGuardrailError, GenerationError, CalendarGenerationError) as exc:
                st.session_state["last_error"] = str(exc)


def _render_linkedin_tab(suite: GeneratedContentSuite | None) -> None:
    """Render editable LinkedIn post tab."""
    if suite is None:
        st.info("Enter a Topic and Target Audience in the sidebar, then click **Generate Content** or **Load Sample Campaign**.")
        return

    post = suite.linkedin_post
    if post is None:
        st.warning("LinkedIn was not included in your selected channels.")
        return

    words = count_words(post.full_text)
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader("LinkedIn Post")
    with c2:
        st.metric("Word Count (Target 120–180)", f"{words} words")

    with st.form("edit_linkedin_form"):
        hook = st.text_input("Hook", value=post.hook)
        body = st.text_area("Body", value=post.body, height=130)
        takeaway = st.text_input("Actionable Takeaway", value=post.takeaway)
        cta = st.text_input("CTA", value=post.cta)
        hashtags_str = st.text_input(
            "Hashtags (3 recommended)",
            value=" ".join(post.hashtags),
        )
        full_text = st.text_area(
            "Full LinkedIn Post (used for word-count & guardrail checks)",
            value=post.full_text,
            height=220,
        )
        saved = st.form_submit_button("Save LinkedIn Edits")

    if saved:
        parsed_tags = _parse_hashtag_string(hashtags_str) or post.hashtags
        suite.linkedin_post = post.model_copy(
            update={
                "hook": hook.strip(),
                "body": body.strip(),
                "takeaway": takeaway.strip(),
                "cta": cta.strip(),
                "hashtags": parsed_tags,
                "full_text": full_text.strip(),
            }
        )
        st.session_state["generated_suite"] = suite
        _refresh_quality_checks()
        st.session_state["generation_notice"] = "LinkedIn post edits saved."
        st.rerun()


def _render_x_thread_tab(suite: GeneratedContentSuite | None) -> None:
    """Render editable X thread tab."""
    if suite is None:
        st.info("Generate or load a campaign from the sidebar to view your X thread.")
        return

    thread = suite.x_thread
    if thread is None:
        st.warning("X was not included in your selected channels.")
        return

    st.subheader(f"X Thread ({len(thread.posts)} posts)")
    with st.form("edit_x_thread_form"):
        hook_tweet = st.text_area("Hook Tweet", value=thread.hook_tweet, height=85)
        edited_posts: list[str] = []
        for idx, item in enumerate(thread.posts, start=1):
            edited_posts.append(
                st.text_area(
                    f"Post {idx} ({len(item)}/280 chars)",
                    value=item,
                    height=80,
                    key=f"x_post_input_{idx}",
                )
            )
        cta = st.text_input("Closing CTA", value=thread.cta)
        hashtags_str = st.text_input("Hashtags", value=" ".join(thread.hashtags))
        saved = st.form_submit_button("Save X Thread Edits")

    if saved:
        cleaned_posts = [p.strip() for p in edited_posts if p.strip()]
        if len(cleaned_posts) < 3 or len(cleaned_posts) > 7:
            st.error("X thread must keep between 3 and 7 non-empty posts.")
        else:
            suite.x_thread = thread.model_copy(
                update={
                    "hook_tweet": hook_tweet.strip(),
                    "posts": cleaned_posts,
                    "cta": cta.strip(),
                    "hashtags": _parse_hashtag_string(hashtags_str),
                }
            )
            st.session_state["generated_suite"] = suite
            _refresh_quality_checks()
            st.session_state["generation_notice"] = "X thread edits saved."
            st.rerun()


def _render_instagram_tab(suite: GeneratedContentSuite | None) -> None:
    """Render editable Instagram caption and alt text tab."""
    if suite is None:
        st.info("Generate or load a campaign from the sidebar to view your Instagram caption.")
        return

    ig = suite.instagram_caption
    if ig is None:
        st.warning("Instagram was not included in your selected channels.")
        return

    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader("Instagram Caption & Alt Text")
    with c2:
        st.metric("Caption Characters", f"{len(ig.caption)} / {INSTAGRAM_MAX_CHARS}")

    with st.form("edit_instagram_form"):
        hook = st.text_input("Hook", value=ig.hook)
        caption = st.text_area("Caption", value=ig.caption, height=200)
        cta = st.text_input("CTA", value=ig.cta)
        hashtags_str = st.text_input("Hashtags (3–8)", value=" ".join(ig.hashtags))
        alt_text = st.text_area("Accessibility Alt Text", value=ig.alt_text, height=95)
        saved = st.form_submit_button("Save Instagram Edits")

    if saved:
        parsed_tags = _parse_hashtag_string(hashtags_str) or ig.hashtags
        suite.instagram_caption = ig.model_copy(
            update={
                "hook": hook.strip(),
                "caption": caption.strip(),
                "cta": cta.strip(),
                "hashtags": parsed_tags,
                "alt_text": alt_text.strip(),
            }
        )
        st.session_state["generated_suite"] = suite
        _refresh_quality_checks()
        st.session_state["generation_notice"] = "Instagram caption edits saved."
        st.rerun()


def _render_blog_tab(suite: GeneratedContentSuite | None) -> None:
    """Render editable blog outline tab."""
    if suite is None:
        st.info("Generate or load a campaign from the sidebar to view your blog outline.")
        return

    outline = suite.blog_outline
    if outline is None:
        st.warning("Blog was not included in your selected channels.")
        return

    st.subheader("Blog Outline")
    with st.form("edit_blog_form"):
        title = st.text_input("Article Title (H1)", value=outline.title)
        meta_description = st.text_area(
            "Meta Description", value=outline.meta_description, height=75
        )
        introduction = st.text_area(
            "Introduction", value=outline.introduction, height=110
        )

        edited_sections: list[tuple[str, str]] = []
        for idx, section in enumerate(outline.sections, start=1):
            heading_val = st.text_input(
                f"Section {idx} Heading",
                value=section.heading,
                key=f"blog_sec_h_{idx}",
            )
            points_val = st.text_area(
                f"Section {idx} Key Points (one per line)",
                value="\n".join(section.key_points),
                height=95,
                key=f"blog_sec_p_{idx}",
            )
            edited_sections.append((heading_val, points_val))

        conclusion_cta = st.text_input("Conclusion CTA", value=outline.conclusion_cta)
        seo_keywords_str = st.text_input(
            "SEO Keywords (comma-separated)",
            value=", ".join(outline.seo_keywords),
        )
        saved = st.form_submit_button("Save Blog Outline Edits")

    if saved:
        new_sections = [
            BlogSection(
                heading=h.strip(),
                key_points=[pt.strip() for pt in pts.splitlines() if pt.strip()],
            )
            for h, pts in edited_sections
            if h.strip() and [pt.strip() for pt in pts.splitlines() if pt.strip()]
        ]
        if len(new_sections) < 2:
            st.error("Blog outline must contain at least 2 sections with key points.")
        else:
            suite.blog_outline = outline.model_copy(
                update={
                    "title": title.strip(),
                    "meta_description": meta_description.strip(),
                    "introduction": introduction.strip(),
                    "sections": new_sections,
                    "conclusion_cta": conclusion_cta.strip(),
                    "seo_keywords": [
                        kw.strip() for kw in seo_keywords_str.split(",") if kw.strip()
                    ],
                }
            )
            st.session_state["generated_suite"] = suite
            _refresh_quality_checks()
            st.session_state["generation_notice"] = "Blog outline edits saved."
            st.rerun()


def _render_calendar_tab(suite: GeneratedContentSuite | None) -> None:
    """Render expandable, editable multi-day Content Calendar tab."""
    if suite is None or suite.content_calendar is None:
        st.info("Generate or load a campaign from the sidebar to view your structured content calendar.")
        return

    calendar = suite.content_calendar
    st.subheader(
        f"{len(calendar.calendar)}-Day Content Calendar — {calendar.topic}"
    )
    st.caption(f"Target audience: {calendar.audience}")

    for idx, item in enumerate(calendar.calendar):
        expander_label = (
            f"Day {item.day} · {item.channel} · {item.format} · {item.objective} ({item.suggested_time})"
        )
        with st.expander(expander_label, expanded=(idx == 0)):
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.markdown(f"**Day**\n\n{item.day}")
            m2.markdown(f"**Channel**\n\n{item.channel}")
            m3.markdown(f"**Format**\n\n{item.format}")
            m4.markdown(f"**Objective**\n\n{item.objective}")
            m5.markdown(f"**Suggested Time**\n\n{item.suggested_time}")

            with st.form(f"calendar_day_form_{item.day}_{idx}"):
                new_hook = st.text_input(
                    "Hook",
                    value=item.hook,
                    key=f"cal_hook_{idx}",
                )
                new_body = st.text_area(
                    "Body",
                    value=item.body,
                    height=110,
                    key=f"cal_body_{idx}",
                )
                new_cta = st.text_input(
                    "CTA",
                    value=item.cta,
                    key=f"cal_cta_{idx}",
                )
                new_hashtags = st.text_input(
                    "Hashtags",
                    value=" ".join(item.hashtags),
                    key=f"cal_tags_{idx}",
                )
                save_day = st.form_submit_button(f"Save Day {item.day} Edits")

            if save_day:
                parsed_tags = _parse_hashtag_string(new_hashtags)
                if not new_hook.strip() or not new_body.strip() or not new_cta.strip():
                    st.error("Hook, Body, and CTA cannot be empty.")
                elif not parsed_tags:
                    st.error("Provide at least one hashtag.")
                else:
                    updated_item = item.model_copy(
                        update={
                            "hook": new_hook.strip(),
                            "body": new_body.strip(),
                            "cta": new_cta.strip(),
                            "hashtags": parsed_tags,
                        }
                    )
                    updated_calendar = list(calendar.calendar)
                    updated_calendar[idx] = updated_item
                    suite.content_calendar = calendar.model_copy(
                        update={"calendar": updated_calendar}
                    )
                    st.session_state["generated_suite"] = suite
                    _refresh_quality_checks()
                    st.session_state["generation_notice"] = f"Saved edits for Day {item.day}."
                    st.rerun()


def _render_export_tab(suite: GeneratedContentSuite | None) -> None:
    """Render JSON/CSV downloads and copyable output blocks."""
    if suite is None or suite.content_calendar is None:
        st.info("Generate or load a campaign from the sidebar before exporting.")
        return

    calendar = suite.content_calendar
    calendar_json = export_calendar_json(calendar)
    calendar_csv = export_calendar_csv(calendar)
    full_suite_json = export_suite_json(suite)

    st.subheader("Export Campaign Assets")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            label="Download Calendar JSON",
            data=calendar_json,
            file_name="scriptxt_content_calendar.json",
            mime="application/json",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            label="Download Calendar CSV",
            data=calendar_csv,
            file_name="scriptxt_content_calendar.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col3:
        st.download_button(
            label="Download Full Campaign JSON",
            data=full_suite_json,
            file_name="scriptxt_full_campaign.json",
            mime="application/json",
            use_container_width=True,
        )

    st.markdown("#### Calendar Preview Table")
    st.dataframe(calendar_to_dataframe(calendar), use_container_width=True, hide_index=True)

    st.markdown("#### Copy-Ready Output")
    copy_format = st.radio(
        "Preview format to copy (use the copy button in the top-right corner of the code block)",
        options=["Calendar JSON", "Calendar CSV", "Full Campaign JSON"],
        horizontal=True,
    )
    if copy_format == "Calendar JSON":
        st.code(calendar_json, language="json")
    elif copy_format == "Calendar CSV":
        st.code(calendar_csv, language="csv")
    else:
        st.code(full_suite_json, language="json")


def _render_quality_checks_tab(
    suite: GeneratedContentSuite | None,
    report: QualityReport | None,
) -> None:
    """Render automated pass/fail guardrails and schema checks."""
    if suite is None or report is None:
        st.info("Generate or load a campaign from the sidebar to run automated quality checks.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Checks Passed", f"{report.passed_count} / {len(report.checks)}")
    c2.metric("Checks Failed", str(report.failed_count))
    c3.metric("Status", "PASS" if report.all_passed else "NEEDS REVIEW")

    st.divider()
    for check in report.checks:
        badge_cls = "badge-pass" if check.passed else "badge-fail"
        badge_label = "PASS" if check.passed else "FAIL"
        st.markdown(
            f"""
            <div class="check-row">
              <div>
                <strong>{check.name}</strong><br/>
                <span style="opacity:0.8;font-size:0.9rem;">{check.details}</span>
              </div>
              <span class="{badge_cls}">{badge_label}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    """Render the SCRIPTXT Streamlit interface."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    _init_session_state()

    st.markdown(
        """
        <div class="scriptxt-header">
          <div class="scriptxt-kicker">Controlled LLM Content Pipeline</div>
          <h1 class="scriptxt-title">SCRIPTXT: Prompt-Powered Content Generator</h1>
          <p class="scriptxt-subtitle">
            Turn one topic into platform-native LinkedIn posts, X threads, Instagram captions, blog outlines, and a schema-validated multi-day content calendar.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_sidebar()

    if st.session_state.get("last_error"):
        st.error(st.session_state["last_error"])

    if st.session_state.get("generation_notice"):
        st.success(st.session_state["generation_notice"])

    suite: GeneratedContentSuite | None = st.session_state.get("generated_suite")
    report: QualityReport | None = st.session_state.get("quality_report")

    tabs = st.tabs(
        [
            "LinkedIn Post",
            "X Thread",
            "Instagram Caption",
            "Blog Outline",
            "Content Calendar",
            "Export",
            "Quality Checks",
        ]
    )

    with tabs[0]:
        _render_linkedin_tab(suite)
    with tabs[1]:
        _render_x_thread_tab(suite)
    with tabs[2]:
        _render_instagram_tab(suite)
    with tabs[3]:
        _render_blog_tab(suite)
    with tabs[4]:
        _render_calendar_tab(suite)
    with tabs[5]:
        _render_export_tab(suite)
    with tabs[6]:
        _render_quality_checks_tab(suite, report)


if __name__ == "__main__":
    main()
