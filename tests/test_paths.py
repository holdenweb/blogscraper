"""Target-path helpers: where each source's entries live in the fragment tree."""
import datetime

import pytest


def test_blogger_path_mirrors_dated_url():
    from blogscraper.paths import blogger_path

    assert (
        blogger_path("https://holdenweb.blogspot.com/2026/02/im-depressed.html")
        == "posts/2026/02/im-depressed.html"
    )
    # An untitled post still has a dated URL, so its slug comes from the URL.
    assert blogger_path("https://holdenweb.blogspot.com/2007/09/.html") == "posts/2007/09/.html"


def test_blogger_path_rejects_unmirrorable_url():
    from blogscraper.paths import blogger_path

    with pytest.raises(ValueError):
        blogger_path("https://holdenweb.blogspot.com/p/about.html")


def test_slugify_lowercases_and_dashes():
    from blogscraper.paths import slugify

    assert slugify("What Matters About Python?") == "what-matters-about-python"
    assert slugify("Java is Object-Oriented COBOL") == "java-is-object-oriented-cobol"
    assert slugify("United We Stand [Not]?") == "united-we-stand-not"
    assert slugify("") == "post"  # never empty


def test_artima_path_from_date_and_title():
    from blogscraper.paths import artima_path

    posted = datetime.datetime(2007, 8, 6, 23, 27)
    assert (
        artima_path(posted, "What Matters About Python?")
        == "posts/2007/08/what-matters-about-python.html"
    )
