"""The publish-time contract: substitute the mounted roots into a fragment.

This module is deliberately self-contained — it imports only Jinja2, none of the
scraper's own dependencies (bs4, mongoengine, requests) — so a consuming site
(holdenweb.com) can **copy** it rather than depend on the blogscraper package,
and pin it with a test. The delimiter constants and the environment they
configure are the contract every consumer of the fragment tree shares; change
them only deliberately, and announce it, because each consumer holds a copy
(ADR-0009).
"""
from __future__ import annotations

import jinja2

# All of Jinja's delimiters are moved to distinctive sentinels so that ${...},
# {{ ... }}, {% ... %} and {# ... #} in code and template samples pass through
# untouched; ${{{ROOT}}} / ${{{IMAGE_ROOT}}} are the only things that substitute.
VARIABLE_START, VARIABLE_END = "${{{", "}}}"
BLOCK_START, BLOCK_END = "${{%", "%}}}"
COMMENT_START, COMMENT_END = "${{#", "#}}}"
SENTINELS = (VARIABLE_START, BLOCK_START, COMMENT_START)

ROOT_PLACEHOLDER = f"{VARIABLE_START}ROOT{VARIABLE_END}"  # "${{{ROOT}}}"
IMAGE_ROOT_PLACEHOLDER = f"{VARIABLE_START}IMAGE_ROOT{VARIABLE_END}"  # "${{{IMAGE_ROOT}}}"


def make_publish_env() -> jinja2.Environment:
    """Jinja env whose delimiters are all moved off content-likely syntax."""
    return jinja2.Environment(
        variable_start_string=VARIABLE_START,
        variable_end_string=VARIABLE_END,
        block_start_string=BLOCK_START,
        block_end_string=BLOCK_END,
        comment_start_string=COMMENT_START,
        comment_end_string=COMMENT_END,
        undefined=jinja2.StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


def render_fragment(html: str, root: str, image_root: str | None = None) -> str:
    """Substitute the mounted roots into a fragment — the publish-time step.

    ``image_root`` defaults to ``root`` so a self-contained tree just works; a
    consumer serving images from a separate host passes it explicitly (ADR-0010).
    """
    return make_publish_env().from_string(html).render(
        ROOT=root, IMAGE_ROOT=root if image_root is None else image_root
    )
