"""The tags collection: an inverted index from category term to post ids."""


def test_tag_index_inverts_categories_to_post_ids():
    from blogscraper.tags import tag_index

    class P:  # minimal stand-in exposing what tag_index needs
        def __init__(self, post_id, categories):
            self.post_id = post_id
            self.categories = categories

    index = tag_index(
        [
            P("post-1", ["python", "security"]),
            P("post-2", ["python"]),
            P("post-3", []),
            P("post-4", None),
        ]
    )
    assert index == {"python": ["post-1", "post-2"], "security": ["post-1"]}
    # Tags and the entries within each are both sorted, so rebuilds diff cleanly.
    assert list(index) == ["python", "security"]


def test_tag_index_dedupes_a_repeated_term_within_one_post():
    from blogscraper.tags import tag_index

    class P:
        post_id = "post-1"
        categories = ["python", "python"]

    assert tag_index([P()]) == {"python": ["post-1"]}


def test_build_tags_rebuilds_the_collection(test_db):
    from blogscraper.models import Post, Tag
    from blogscraper.tags import build_tags

    Post(post_id="post-1", categories=["python", "web"]).save()
    Post(post_id="post-2", categories=["python"]).save()

    result = build_tags()
    assert result == {"tags": 2, "taggings": 3}
    assert Tag.objects.get(tag="python").entries == ["post-1", "post-2"]
    assert Tag.objects.get(tag="web").entries == ["post-1"]

    # Idempotent: the collection is dropped and remade, not appended to, so a
    # post that no longer carries a tag drops out of its entries.
    Post.objects(post_id="post-2").delete()
    build_tags()
    assert Tag.objects.get(tag="python").entries == ["post-1"]
    assert Tag.objects.count() == 2
