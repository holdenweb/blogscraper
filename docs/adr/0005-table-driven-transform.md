# 5. One table-driven transform replaces the per-field scripts

Date: 2026-09-03
Status: Accepted

## Context

adhoc6–13 are eight near-copies of one pattern: verify an assumption
holds across the whole corpus ("`updated` never has attributes"), bail if
not, then flatten one field. The pattern's instinct is right — corpus-wide
assertions before irreversible change — but copy-editing eight variants
produced the adhoc12 bug, and the assertions lived in throwaway scripts
instead of anywhere durable.

## Decision

A spec table with one row per Atom element: an expected-attrib predicate,
an extractor, and target field name(s). A single pure function applies the
table to one raw entry (unit-testable without network or database). A
validator applies every predicate corpus-wide and reports violations —
the adhoc scripts' verify-then-bail idea, made durable and runnable at
will.

## Consequences

Assumptions about the corpus become executable and tested. Supporting a
new element is one spec row. The copy-paste bug class is retired.
