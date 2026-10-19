# 13. Repair stale external subresource URLs at export

Date: 2026-10-19
Status: Accepted

## Context

The live site is served over HTTPS. Some post bodies embed subresources over
`http://` — across the corpus, 21 `<img src>`, 9 `<script src>`, 1 `<embed src>`
— which browsers block as **mixed content**. So the November-2011 maths posts,
whose bodies carry an in-body MathJax loader, never ran it and their LaTeX showed
as raw source. Worse, that loader points at `http://cdn.mathjax.org/mathjax/latest/
MathJax.js`, and `cdn.mathjax.org` was decommissioned around 2017 — a scheme bump
alone cannot revive a host that no longer serves.

## Decision

`export.rewrite_content` repairs subresource URLs as it already rewrites image
and link URLs:

- The dead MathJax CDN (`cdn.mathjax.org/mathjax/latest/MathJax.js`) is rewritten
  to the current HTTPS cdnjs MathJax **2.7.9**, preserving the `?config=…` query
  so the author's v2 `MathJax.Hub.Config` keeps working. (MathJax 3 has a
  different config API; staying on 2.7.9 keeps the fix a true drop-in.)
- Every other `http://` value in a `src` attribute is upgraded to `https://`.

Only subresource `src` attributes are touched. `http://` hyperlinks (`<a href>`)
are navigation, not mixed content, and are left as authored — forcing them to
`https://` would break links to http-only targets.

## Consequences

The HTTPS site stops emitting blocked/insecure subresources, and the three maths
posts render. A subresource whose host is genuinely http-only still fails, but it
was already blocked as mixed content, so https is strictly no worse. The repair
is a content transform in the generator, consistent with ADR-0012; podpack-pages
still owns site chrome.
