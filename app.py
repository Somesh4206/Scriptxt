"""CLI entry point for generating a LinkedIn post with SCRIPTXT."""

from __future__ import annotations

import sys

from scriptxt.config import SUPPORTED_TONES
from scriptxt.generator import GenerationError, generate_linkedin_post


def main() -> int:
    """Prompt for topic, audience, tone, and CTA via stdin and print the generated post."""
    print("=== SCRIPTXT: LinkedIn Post Generator (CLI) ===")
    topic = input("Topic: ").strip()
    audience = input("Target audience: ").strip()
    tone = input(f"Tone ({', '.join(SUPPORTED_TONES)}) [Professional]: ").strip() or "Professional"
    cta = input("Call to Action (CTA) [optional]: ").strip()

    if tone not in SUPPORTED_TONES:
        print(f"Error: Tone must be one of {', '.join(SUPPORTED_TONES)}.", file=sys.stderr)
        return 1

    try:
        post = generate_linkedin_post(
            topic=topic,
            audience=audience,
            tone=tone,
            cta=cta,
        )
    except (ValueError, GenerationError) as exc:
        print(f"Generation failed: {exc}", file=sys.stderr)
        return 1

    print("\n--- Generated LinkedIn Post ---\n")
    print(post.full_text)
    print("\nHashtags:", " ".join(post.hashtags))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
