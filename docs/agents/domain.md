# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Layout: single-context

This repo is **single-context**: one `CONTEXT.md` at the repo root and one `docs/adr/` directory hold the whole project's domain language and architecture decisions. There is no `CONTEXT-MAP.md` and no per-package `CONTEXT.md`.

Neither `CONTEXT.md` nor `docs/adr/` exists yet. They are created lazily by `/domain-modeling` (reached via `/grill-with-docs` and `/improve-codebase-architecture`) the first time a term or a decision is actually resolved — not upfront.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the project glossary.
- **`docs/adr/`** — read ADRs that touch the area you're about to work in.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront.

## File structure

```
/
├── CONTEXT.md
├── docs/
│   ├── adr/
│   │   ├── 0001-<decision>.md
│   │   └── 0002-<decision>.md
│   ├── agents/            ← this file, issue-tracker.md, triage-labels.md
│   └── cn/                ← user-facing guides (pre-existing)
└── src/
    ├── agentarts/sdk/     ← core SDK
    └── agentarts/toolkit/ ← CLI; depends on sdk, never the reverse
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
