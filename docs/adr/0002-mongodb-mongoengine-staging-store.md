# 2. MongoDB with mongoengine as the staging store

Date: 2026-09-03 (retrospective; in force since commit `51e5825`)
Status: Accepted

## Context

The migration needs a staging area for ~540 posts, their comments, and
embedded images: queryable, schema-flexible while the data is still being
understood, with a straightforward backup story and somewhere to keep
image bytes.

## Decision

MongoDB (local `blogscraper` database) accessed through mongoengine.
Image bytes go to GridFS via `FileField`, keeping everything in one store.
`mongodump` provides backups.

## Consequences

A local `mongod` is a runtime dependency. `DynamicDocument` suits the raw,
still-being-understood data; the derived schema uses plain typed
`Document`s so validation actually bites (see ADR-0004, ADR-0005).
