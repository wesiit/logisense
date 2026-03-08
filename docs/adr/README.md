# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records for the LogiSense platform.

## What is an ADR?

An Architecture Decision Record captures an important architectural decision made along with its context and consequences.

## ADR Format

Each ADR should follow this template:

```markdown
# ADR-NNNN: Title

## Status

[Proposed | Accepted | Deprecated | Superseded]

## Context

What is the issue that we're seeing that motivates this decision or change?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?
```

## Naming Convention

ADR files should be named using the pattern: `NNNN-short-title.md`

Examples:

- `0001-use-postgresql-for-primary-database.md`
- `0002-adopt-event-driven-architecture.md`

## References

- [ADR GitHub Organization](https://adr.github.io/)
- [Michael Nygard's article on ADRs](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
