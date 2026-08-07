# Practical browser validation

Validation date: 2026-08-07

This record contains no account identifier, conversation URL, repository payload, secret, or uploaded file. It records only the protocol-level observations needed to reproduce the acceptance decision.

## Live scenarios

| Scenario | Readiness evidence | Send evidence | Result |
| --- | --- | --- | --- |
| Legacy prior-task draft | A 7,071-code-point envelope with one valid legacy task marker, zero attachments, and zero user turns was recognized; one semantic clear, one reload, and three empty reads spanning more than five seconds succeeded | Not sent | `STALE_CODEX_DRAFT_RESET` passed |
| Connection gate | Exact single-line payload, visible `Pro`, one enabled send control, and no prior user turn | Payload appeared in exactly one canonical user turn | Two stable final reads were exactly `CONNECTION_OK` |
| Clean new conversation | Three empty, attachment-free, non-sendable reads spanned more than five seconds | Not applicable | No legacy marker or prior connection payload returned |
| Short structured envelope | 669 canonical code points, one marker, one fingerprint, exact UTF-8 SHA-256, visible `Pro` | Marker appeared in exactly one canonical user turn | Two stable final reads were exactly `SHORT_TASK_OK` |
| Long multilingual envelope | Intended length 7,071 code points; raw `innerText` length 7,038 and raw `textContent` length 6,997; rich-DOM inverse reconstruction restored all 7,071 code points, the non-NFC sequence, marker, fingerprint, and SHA-256 exactly | Marker appeared in exactly one canonical user turn | Two stable final reads were exactly `MULTILINE_OK_中文_✅` |
| Reserved-tab editor noise | A stable three-character residual appeared before first input in the Skill-created reserved tab, with zero attachments and zero user turns; it persisted for 12.5 seconds | Not sent | One `MANAGED_TASK_DRAFT_RESET`, one reload, and three empty reads spanning more than five seconds passed |
| Adversarial protocol review | 2,423 canonical code points, exact marker, fingerprint, SHA-256, visible `Pro` | Marker appeared in exactly one canonical user turn | Complete stable review received; reserved-tab boundary accepted, closed grammar and ownership rechecks requested |
| Correction packet | Exact 1,008-code-point canonical reconstruction in the same clean composer | Correction appeared in exactly one canonical user turn | Stable final reply was exactly `UI_BOUNDARY_ACCEPT` |

## Defects found by live testing

1. ChatGPT currently materializes supported Markdown as direct `h2`, `ul`, and `ol` nodes rather than only splitting text into paragraphs. Raw `innerText`, raw `textContent`, and a paragraph-only inverse are therefore insufficient.
2. New-chat navigation can restore both complete prior task envelopes and short editor-noise strings. Route changes are not storage resets.
3. A browser UI does not expose a server idempotency key. Ambiguous-send recovery therefore requires a finite stable-absence grace gate and must report the residual limitation instead of inventing server guarantees.

## Accepted implementation boundaries

- The inverse serializer supports a closed canonical grammar and rejects unsupported or ambiguous DOM topology.
- Arbitrary residual text may be reset automatically only in a tab recorded as created and reserved by this Skill's browser session, with stable exact text, zero attachments, zero canonical user turns, immediate ownership rechecks, one semantic clear, one reload, and no retry.
- Shared or ownership-uncertain tabs retain the fail-closed unowned-draft rule.
- A fallback send requires at least three canonical absence reads spanning at least five seconds, unchanged conversation and composer identities, the exact unsent payload, enabled send control, inactive generation, and an immediate pre-fallback recheck.
- Files uploaded: none.
