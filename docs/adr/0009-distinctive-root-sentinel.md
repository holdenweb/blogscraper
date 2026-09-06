# 9. Distinctive `${{{ROOT}}}` sentinel and Jinja delimiter hardening

Date: 2026-09-04
Status: Accepted (supersedes the delimiter and escaping decisions in ADR-0007)

## Context

ADR-0007 chose `${ROOT}` as the publish-time root placeholder, with Jinja
configured `variable_start_string="${"` / `variable_end_string="}"`, and made
the generator *escape* any literal `${` in post bodies so that shell and code
samples would not be mis-parsed as placeholders at publish time.

Two findings reopened that decision:

- The escaping guards a non-problem. A scan of all 539 migrated posts finds
  `${` in **0** of them; `${ROOT}` collides with no current content. Escaping
  every body to solve a zero-occurrence case is cost without benefit, and it
  mutates content — the thing we most want to keep faithful.
- `${` and `}` are short enough that *future* content could collide, so merely
  dropping the escape step under those delimiters would be fragile.

Steve's proposal: spell the placeholder `${{{ROOT}}}`, distinctive enough that
collision with authored content is negligible and escaping is unnecessary.

A completeness check across the whole of Jinja's syntax — not just its variable
delimiter — found the real latent risk. With only the variable delimiter moved,
Jinja's default **block** `{% %}` and **comment** `{# #}` delimiters stay live.
Neither occurs in the corpus today (0 and 0), but two posts already contain
`{{` (a LaTeX `\(e^{{\pi i}}\)` and a literal `{{placeholder}}`), and a Python
blog may well publish a Jinja or Django tutorial containing `{% for %}` — which
`StrictUndefined` would turn into a publish-time failure.

## Decision

- The root placeholder is `${{{ROOT}}}`. Publish-time Jinja moves *every*
  delimiter to a distinctive, collision-resistant sentinel, not just the
  variable one:
  - variable `${{{` … `}}}`
  - block `${{%` … `%}}}`
  - comment `${{#` … `#}}}`
  - `undefined=StrictUndefined`; `autoescape=False` — fragments are HTML we emit
    deliberately, and the only substitution is a root-prefix URL.
- These delimiter strings and the publish helpers (`make_publish_env`,
  `render_fragment`) live in one dependency-free module, `blogscraper/publish.py`
  (Jinja2 only). The generator imports them, so the strings it must avoid and the
  strings Jinja will interpret cannot drift apart; and because the module carries
  none of the scraper's dependencies (bs4, mongoengine, requests), a consuming
  site **copies** it rather than depending on the scraper package, pinning it
  with a test so a delimiter change here surfaces there instead of silently
  breaking rendering.
- No content is escaped. The generator instead **scans** each fragment's source
  for any of the three start sentinels and reports collisions — loud, not
  silent. Zero today; if authored content ever contains one, we hear about it
  and decide then, rather than mutating every body pre-emptively.

## Consequences

Content stays byte-faithful apart from the deliberate `src`/`href` rewrites.
All of Jinja's syntax — variables, blocks, comments — is inert against post
content, so code and template examples publish untouched. The placeholder is
longer, but it appears only in generated attribute values, never hand-typed.
The escaping machinery proposed in ADR-0007 is withdrawn; its tree structure,
path mirroring, manifest, and decorator-injection decisions stand.
