# 0001. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** @DaniPopov

## Context

Muninn is an open-source project. People will join at different times, and many
won't have been part of the early conversations. Without a written record, decisions
get lost, or worse, get argued again from scratch every few months.

## Decision

We record every significant architecture decision as a short Markdown file in
`docs/architecture_decisions/`, using the format in [`0000-template.md`](0000-template.md)
(based on Michael Nygard's
[ADR format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)).

"Significant" means: it's hard to reverse, it affects more than one part of the
system, or someone will reasonably ask "why?" later.

## Consequences

- New contributors can read the ADRs to understand the project's shape quickly.
- Decisions are made in the open, through pull requests, so anyone can comment.
- ADRs are never deleted. If we change our mind, a new ADR supersedes the old one,
  so the history stays readable.
