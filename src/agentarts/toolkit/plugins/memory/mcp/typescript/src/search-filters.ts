import { z } from "zod";

export const MEMORY_KINDS = ["observation", "experience"] as const;

// Snapshot of claude-mem/plugin/modes/code.json's observation_types.
export const OBSERVATION_CATEGORIES = [
  "bugfix", "feature", "refactor", "change", "discovery", "decision",
  "security_alert", "security_note", "sensitive",
] as const;

// Experience extraction contract: classify reusable knowledge independently
// of the source observation's type.
export const EXPERIENCE_CATEGORIES = ["feature", "bugfix", "testing", "build-env"] as const;

export type MemoryKind = (typeof MEMORY_KINDS)[number];
export type MemoryCategory =
  | (typeof OBSERVATION_CATEGORIES)[number]
  | (typeof EXPERIENCE_CATEGORIES)[number];

const CATEGORIES_BY_KIND: Record<MemoryKind, readonly MemoryCategory[]> = {
  observation: OBSERVATION_CATEGORIES,
  experience: EXPERIENCE_CATEGORIES,
};

// Both source tuples are nonempty; deduplicate shared categories for JSON Schema.
export const MEMORY_CATEGORIES = [...new Set<MemoryCategory>([
  ...OBSERVATION_CATEGORIES, ...EXPERIENCE_CATEGORIES,
])] as [MemoryCategory, ...MemoryCategory[]];

const OBSERVATION_DESCRIPTIONS: Record<(typeof OBSERVATION_CATEGORIES)[number], string> = {
  bugfix: "something broken was fixed",
  feature: "a new capability was added",
  refactor: "code was restructured without changing behavior",
  change: "a general change to docs, config or other content",
  discovery: "a finding about the existing system",
  decision: "an architectural or design choice with rationale",
  security_alert: "a security issue needing attention before continuing",
  security_note: "a non-urgent security-relevant finding",
  sensitive: "context-sensitive information that should not leak into unrelated work",
};

const EXPERIENCE_DESCRIPTIONS: Record<(typeof EXPERIENCE_CATEGORIES)[number], string> = {
  feature: "reusable implementation, integration or design methods and trade-offs",
  bugfix: "reusable diagnosis, causes, correction paths or failed repair lessons",
  testing: "test design, coverage, assertions, mocks, fixtures, isolation or reliability",
  "build-env": "builds, dependencies, runtimes, CI/CD, OS, shells or toolchain configuration",
};

export const memoryClassificationFields = {
  kind: z.enum(MEMORY_KINDS).optional().describe(
    "Optional single coding-memory kind. observation answers 'what happened, changed or was found, and why': " +
    "concrete technical facts, fixes and decisions. experience answers 'how to handle a similar problem': " +
    "evidence-backed reusable methods, diagnostic paths, failure lessons and applicability limits. " +
    "Omit when unsure or when both facts and lessons could help; no kind filter is then sent. " +
    "Do not send an empty string, null or 'all'. Setting kind or category automatically forces " +
    "strategy_type=procedural, overriding any supplied strategy_type.",
  ),
  category: z.enum(MEMORY_CATEGORIES).optional().describe(
    "Optional single category that narrows recall. Prefer omission unless the desired memory category is clear. " +
    "With kind=observation: " +
    OBSERVATION_CATEGORIES.map(c => `${c} (${OBSERVATION_DESCRIPTIONS[c]})`).join("; ") +
    ". With kind=experience: " +
    EXPERIENCE_CATEGORIES.map(c => `${c} (${EXPERIENCE_DESCRIPTIONS[c]})`).join("; ") +
    ". When kind is set, category must belong to that kind. Without kind, search this category " +
    "across both kinds (feature and bugfix are shared). Classify experience by the reusable " +
    "problem, not the source observation type. A debugging task may also need discovery/decision facts, " +
    "so do not automatically restrict it to bugfix. Using a test to verify a fix does not by itself make " +
    "the experience testing. Omit when unsure to leave category unrestricted; " +
    "do not send an empty string, null or 'all'. Setting category forces strategy_type=procedural.",
  ),
};

export const memoryClassificationSchema = z.object(memoryClassificationFields).superRefine(
  ({ kind, category }, ctx) => {
    if (kind !== undefined && category !== undefined && !CATEGORIES_BY_KIND[kind].includes(category)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["category"],
        message: `category '${category}' is not valid for kind '${kind}'. Use one of: ` +
          `${CATEGORIES_BY_KIND[kind].join(", ")}; omit category when unsure.`,
      });
    }
  },
);
