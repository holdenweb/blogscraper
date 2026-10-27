# Backlog

Working plan: rebuild the pipeline as raw → derived → export (see docs/adr/).
Kept in rough priority order within sections; done items move to the bottom
with their commit rather than being deleted.

## In progress

- (nothing — image harvest landed; see Next for the follow-ups it surfaced)

## Next

- [ ] External post images (~28 references: 19 `<img src>` + 9 full-size
      `<a href>`, e.g. Amazon, PayPal, quiz badges) are deliberately left as
      absolute URLs, not copied onto the new site. Revisit only if any turn out
      to matter enough to self-host.
- [ ] Artima follow-ups deferred from ADR-0011: harvest Artima's own
      (artima.com-hosted) images so its fragments are self-contained;
      cross-source internal-link rewriting (export only rewrites blogspot
      links); and converge comments (Blogger `comment` collection vs Artima
      embedded) once the line actually renders comments.

## Awaiting Steve's decision (destructive or policy)

- [ ] Drop stray collections `ingested`, `blog_post_processed`,
      `duplicated_blog_post` once nothing is wanted from them.
- [ ] Drop legacy `blog_post` collection after the rebuilt `posts` collection
      is verified against it.
- [ ] Drop legacy `photo_image` collection (superseded by `photo`); note its
      GridFS files in the shared `fs` bucket orphan on drop and want cleanup.
- [ ] Retention of the generator `--decorator` hook. Decoration *selection* is
      decided (ADR-0007, 2026-09-05: the serve-time processor decorates `posts/`
      / manifest members, serves the rest literally), which places site chrome
      on the publisher side. The generator hook is no longer the chrome
      mechanism — decide whether to keep it for generation-time content
      transforms or drop it.
- [ ] Better inter-linking of the blog articles, possibly via a sidebar.

- [ ] `dump/` BSON dumps: keep in-tree untracked, commit, or relocate.

## Later

- [ ] `version.py` (0.2.0b3) disagrees with pyproject (0.2.0rc1); reconcile or
      generate one from the other.
- [ ] Decide fate of posts present in `dump/` but no longer in the live feed
      (reconciliation report will surface any — none expected).
- [ ] Untitled posts: 12 of 16 now take their title from a leading bold heading
      (ADR-0012); the remaining 4 open with plain prose and stay untitled (their
      slug still comes from the URL). Give those a display title only if wanted.

## Done

- [x] Read-only analysis; thumbnail corruption confirmed by query (2026-09-03).
- [x] Phase 0 baseline commit — Steve, `54103e8`.
- [x] shotlands workspace stanza removed — `b36be5b`.
- [x] Phase 1 scaffold: ADRs 0001–0008, backlog, pytest + live fixtures —
      `c71ebac`.
- [x] Phase 2 + 3: `blogscraper` package (ingest, transform), CLI, justfile —
      `80d6b3d`, `e68adc7`.
- [x] Phase 3 data rebuild verified against the live blog (2026-09-03):
      539 posts, 1126 comments, 0 spec violations. Thumbnail corruption
      repaired (67 distinct URLs, was 1); author_name populated for all;
      dates are BSON datetimes; comment linkage exact (Σ comment_count ==
      comment count, 0 orphans); re-scrape + re-transform idempotent. Legacy
      `blog_post` (538) left untouched for comparison.
- [x] Phase 4 export core (2026-09-04): `${{{ROOT}}}` sentinel + Jinja
      delimiter hardening (ADR-0009, supersedes 0007's escaping); `export.py`
      with path mirroring, link/image rewriting, manifest, decorator hook.
      Verified against the live corpus: 539 fragments on mirrored paths,
      37 internal links rewritten, publish round-trip resolves, 0 collisions.
      README written.
- [x] Decoration selection recorded (ADR-0007, 2026-09-05): serve-time, by kind
      (`posts/`/manifest decorate, rest literal), plus the multi-consumer
      rationale. Separate `${{{IMAGE_ROOT}}}` image placeholder defaulting to
      `${{{ROOT}}}` (ADR-0010), so one source serves many sites.
- [x] Image harvest (`images.py`, 2026-09-05): Blogger-hosted `<img src>` into
      the `photo` collection — unique src, idempotent, external images skipped,
      failures reported (not swallowed like adhoc15). Live run: 96 images stored
      (82 png, 14 jpeg), 19 external left in place, 0 failed. Re-export
      self-hosts them: 96 files under `build/images/`, 97 `${{{IMAGE_ROOT}}}`
      refs across 67 fragments; divergent-IMAGE_ROOT round-trip verified.
      5 tests red-first; 36 green.
- [x] Full-size image links (2026-09-05): `images.py` also harvests the
      full-size Blogger image behind each thumbnail's `<a href>`, and export
      rewrites those links to `${{{IMAGE_ROOT}}}/images/…` so "click for full
      size" survives cutover (ADR-0010 updated). Live: `photo` now holds 180
      images (+84); export rewrites 97 `<img src>` and 89 `<a href>`, leaving
      9 external image links absolute. 3 tests red-first; 39 green. README and
      ADR-0010 updated.
- [x] Legacy flat pipeline retired — deleted in another session (`d797529`,
      `be0c134`): all `adhoc*.py`, `scraper.py`, `db.py`, `drop.py`,
      `no_attribs.py`, `zz_adhoc*.py`. Reconciled here: justfile `legacy-*`
      recipes removed (they called the deleted files), README layout updated.
- [x] Consumer-facing hardening (2026-09-05, from the podpack-pages session):
      (a) ADR-0007 notes that `manifest.json` is served literally and that
      untitled posts are titled by the consumer; (b) the publish contract
      (delimiters + `make_publish_env`/`render_fragment`) extracted to the
      dependency-free `blogscraper/publish.py` for consumers to copy and pin
      (ADR-0009; `test_publish.py` imports only it); (c) export now writes
      `redirects.json` — 539 cutover 301s, old Blogger path →
      `${{{ROOT}}}/posts/…`. 41 tests green.
- [x] Tag collection (2026-09-11): `just tags` builds a `tag` collection — one
      document per category term with the `post_id`s carrying it, derived from
      `Post.categories`, drop-and-rebuild (ADR-0004). Live: 752 tags over 1781
      taggings. Steve renamed the collection `tags`→`tag` and the model was
      reconciled to match. 44 tests green.
- [x] Artima weblog scraped (2026-09-14, `aac8312`): `just artima` captures the
      7 old Artima posts — entries + 111 comments — into the `artima` collection
      via its own Jive-JSP scraper. No tags (Artima had none).
- [x] Parallel source streams (ADR-0011, 2026-09-14): both blogs converge into
      one source-tagged `post` collection feeding one production line. Each
      source sets its own target `path` at transform time (`paths.py`); export
      is now source-blind (uses `post.path`); `transform` rebuilds `post` from
      `raw_post` + `artima`; redirects stay Blogger-only. Verified live: 546
      fragments (539 + 7), Artima under `posts/YYYY/MM/slug.html`. 54 green.
- [x] On-page furniture + comment pages (ADR-0012, 2026-10-18): each fragment
      gains a provenance line, bold tags, and an "N comments" link to paginated
      comment pages (10/page) generated under `slug.comments/`; comments are
      converged at render time from both sources; untitled posts take a leading
      bold heading as their title. Verified live: 546 fragments + 310 comment
      pages, 276 posts with comments (biggest 80 → 8 pages), 12/16 untitled
      promoted, redirects still 539, publish round-trip clean. 62 green.
- [x] Repair stale subresource URLs (ADR-0013, 2026-10-19): export rewrites the
      dead `http://cdn.mathjax.org` loader to HTTPS cdnjs MathJax 2.7.9 (fixing
      the 3 maths posts, reported live by Steve) and upgrades every other
      `http://` `src` to `https://` (21 img, 9 script, 1 embed) so nothing is
      mixed-content-blocked; http hyperlinks left as authored. 64 green. Steve
      re-publishes.
- [x] Comment pages are decorated content (ADR-0014, 2026-10-27): live
      comment-page nav reached the browser as literal `${{{ROOT}}}` because
      podpack-pages served comment pages as stored. An interim relative-links
      fix (`b76a71f`) was reverted (`dc143eb`) in favour of the consumer
      decorating them like posts; ADR-0014 makes `comment_pages` (always
      present, ordered, export-relative) consumer contract, and export now
      collision-scans each comment's body, heading and author. Live: 1237
      comments scanned, 0 sentinels; 546 posts all carry `comment_pages`, 276
      with 310 pages. README `render_fragment` import corrected. 65 green.
      **Do not republish** until podpack-pages decorates comment pages and is
      deployed.
