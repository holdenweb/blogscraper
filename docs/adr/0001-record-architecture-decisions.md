# 1. Record architecture decisions

Date: 2026-09-03
Status: Accepted

## Context

The project is moving from exploratory scripts to a maintained migration
tool. Until now decisions lived implicitly in code and in the ordering of
justfile recipes; the commit `54103e8` message anticipates them being
written down.

## Decision

Keep Nygard-style ADRs in `docs/adr/`, numbered sequentially. An accepted
ADR is not edited to change its meaning; it is superseded by a later one.

## Consequences

The "why" survives the code that embodied it. Ceremony is kept in
proportion: an ADR is a page, not a document.
