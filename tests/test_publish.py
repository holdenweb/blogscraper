"""The publish-time contract (ADR-0009), tested through `blogscraper.publish`.

This module imports nothing but `blogscraper.publish`, which in turn imports
only Jinja2 — so these tests double as the "pin" a consuming site copies
alongside the module to catch delimiter drift.
"""


def test_placeholders_are_the_pinned_contract():
    from blogscraper import publish

    assert publish.ROOT_PLACEHOLDER == "${{{ROOT}}}"
    assert publish.IMAGE_ROOT_PLACEHOLDER == "${{{IMAGE_ROOT}}}"
    assert publish.SENTINELS == ("${{{", "${{%", "${{#")


def test_publish_env_substitutes_root_and_nothing_else():
    # Only the distinctive placeholder resolves; shell, Jinja-variable, block
    # and comment syntax in a code sample all pass through verbatim.
    from blogscraper.publish import render_fragment

    body = (
        "root=${{{ROOT}}} "
        "shell=${HOME} "
        "var={{ x }} "
        "block={% for i in xs %}{{ i }}{% endfor %} "
        "comment={# note #}"
    )
    out = render_fragment(body, "/blog")
    assert out == (
        "root=/blog "
        "shell=${HOME} "
        "var={{ x }} "
        "block={% for i in xs %}{{ i }}{% endfor %} "
        "comment={# note #}"
    )


def test_image_root_defaults_to_root_but_can_diverge():
    # By default images follow the content root; a consumer can point IMAGE_ROOT
    # at a shared image host without moving the content (ADR-0010).
    from blogscraper.publish import render_fragment

    frag = "page ${{{ROOT}}}/posts/x.html img ${{{IMAGE_ROOT}}}/images/y.png"
    assert render_fragment(frag, "/blog") == (
        "page /blog/posts/x.html img /blog/images/y.png"
    )
    out = render_fragment(frag, "/blog", image_root="https://img.holdenweb.com")
    assert out == "page /blog/posts/x.html img https://img.holdenweb.com/images/y.png"
