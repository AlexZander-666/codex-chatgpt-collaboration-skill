# Final report template

```markdown
## Collaboration result

- Final state: VERIFIED / BLOCKED
- ChatGPT consulted: yes / no
- Connection gate: success / failure / not run
- Selected model tier: <observed label>
- Model-selection evidence: <visible choices and selected state>
- Pre-input baseline: <stabilization duration, read count, page/conversation/composer identity checks, initialization-attempt count, and observations>
- Persisted-draft handling: <none / resumed exact PERSISTED_SKILL_DRAFT / blocked unchanged / exact user-authorized one-shot reset and post-reload result>
- Composer ownership: <empty stable baseline / WRITTEN provenance fields and recovery result / unowned>
- Payload canonicalization: <source and LF transport lengths, code-point length, line count, UTF-8 SHA-256, and extractor rule version>
- Composer-readiness evidence: <canonical plaintext/hash/length/marker/attachment/identity equality and send-ready evidence; raw DOM lengths are diagnostic only>
- Post-send composer anomaly: <none / POST_SEND_PHANTOM_DRAFT observed and whether it self-cleared>
- Wait bounds: <finite composer, model, send-recovery, and completion bounds plus exhaustion outcomes>
- Send evidence: <exact payload or marker appeared once in canonical user-authored turns>
- Ambiguous-send recovery: <none / recovered without resend / fallback after confirmed absence / blocked>
- Completion evidence: <assistant response, generation ended, structural signal, two identical consecutive reads>
- Conversation reference: <stored locally / unavailable>
- Conversation URL: <include only when explicitly authorized>
- Questions sent: <count>
- Task marker: <CODEX_TASK_ID value>

## Responsibility split

- ChatGPT handled: <research, comparison, hypotheses, or review>
- Codex handled: <repository inspection, edits, commands, and decisions>

## Advice review

- Accepted: <recommendations supported by evidence>
- Rejected: <recommendations contradicted by evidence>
- Corrections requested: <what was sent back and why>

## Local result

- Files changed: <paths or none>
- Verification run: <commands and outcomes>
- Remaining uncertainty: <unverified risks or none>

## Security and authority

- External data sent: text only / files with authorization / none
- Secret scan: <command and result or not applicable>
- Git state: local / committed / pushed / pull request
- Deployment state: not deployed / deployed with authorization
```

Never collapse “consulted,” “implemented,” “verified,” and “published” into one claim.
