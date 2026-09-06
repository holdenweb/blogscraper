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
- [ ] Comment rendering: how (and whether) captured comments appear in the
      exported fragment tree.
- [ ] `dump/` BSON dumps: keep in-tree untracked, commit, or relocate.

## Later

- [ ] `version.py` (0.2.0b3) disagrees with pyproject (0.2.0rc1); reconcile or
      generate one from the other.
- [ ] Decide fate of posts present in `dump/` but no longer in the live feed
      (reconciliation report will surface any — none expected).
- [ ] Untitled posts (16, empty `<title type="text"/>`) get a slug from the URL
      already, so export handles them; if they need a display title later,
      derive one at decoration time.

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
