# Task envelope

Send one bounded message using this structure. Omit fields that do not apply; do not invent facts.

Keep envelope content inside the canonical editor grammar: plain paragraphs, the exact ATX headings below, hyphen bullets, sequential decimal question numbers, and raw URLs whose label is the URL itself. Do not use emphasis, code spans or fences, labeled links, blockquotes, tables, nested lists, or blank list items; write paths, identifiers, commands, and reduced log text as ordinary Unicode text. This restriction makes the editor's rich-text conversion exactly reversible instead of visually approximate.

```markdown
You are an external research and design adviser. Do not perform local actions.

CODEX_TASK_ID:<short SHA-256 marker>
CODEX_DRAFT_SHA256:<full SHA-256 of the LF envelope with this fingerprint line omitted>

## Objective
<What decision, analysis, or correction is needed?>

## Verified context
- <Repository architecture or behavior confirmed by Codex>
- <Relevant versions and environment>

## Boundaries
- <Behavior that must remain unchanged>
- <Privacy, licensing, compatibility, or performance constraints>
- <Actions and claims that are forbidden>

## Evidence already available
- <Source locations, reduced log excerpts, test results, or official references>

## Questions
1. <A decision-ready question>
2. <A question that exposes tradeoffs or failure modes>

## Deliverables
- <Concrete recommendation, comparison table, risk list, or patch guidance>
- Separate facts, assumptions, and recommendations.
- Identify what Codex must verify locally.

## Acceptance criteria
- <Conditions a useful answer must satisfy>
```

## Correction packet

When local evidence rejects a recommendation, send:

```markdown
The previous recommendation did not pass local review.

- Recommendation under review: <summary>
- Conflicting evidence: <exact error or authoritative fact>
- Location: <file and line, command, or source URL>
- Constraint that must be preserved: <constraint>
- Requested correction: provide the smallest complete revision and list its assumptions.
```

Do not ask ChatGPT to declare its own answer verified.
