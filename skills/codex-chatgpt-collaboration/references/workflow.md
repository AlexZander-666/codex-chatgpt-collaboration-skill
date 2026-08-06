# Collaboration state machine

Use the following states literally for the consultation portion of a task.

| State | Entry condition | Allowed work | Exit condition |
| --- | --- | --- | --- |
| `CONNECTING` | Every Codex task starts | Open or reuse one managed tab, prepare the unsent gate message, establish composer readiness and current model evidence, submit once, and verify the complete reply | All connection checks pass, or a concrete failure occurs |
| `CONNECTED` | Page access, send, complete reply, and verbatim readback succeeded | Prepare the bounded task envelope | A complete envelope is ready |
| `CONSULTING` | The complete envelope was sent | Wait for completion, read the response, preserve its URL and question count | A complete response was captured, or recovery fails |
| `REVIEWING` | A complete response was captured | Compare with repository constraints, inspect source, implement authorized changes, and verify | Acceptance evidence passes, a correction is needed, or verification cannot proceed |
| `VERIFIED` | Every relevant acceptance criterion has supporting evidence | Produce the final report | Terminal |
| `BLOCKED` | A required capability, authorization, complete response, or verification result is unavailable | Preserve evidence and report the exact blocker | Resume only after the missing condition changes |

## Required transitions

```text
CONNECTING -> CONNECTED -> CONSULTING -> REVIEWING -> VERIFIED
     |             |             |             |
     +-------------+-------------+-------------+-> BLOCKED

REVIEWING -> CONSULTING  when contradictory evidence is sent for correction
BLOCKED   -> CONNECTING  after the user completes authentication or browser access is restored
```

Do not transition directly from `CONSULTING` to `VERIFIED`.

## Connection gate

Require all of the following:

1. The intended ChatGPT page is visible and usable.
2. The selected model and the visible UI evidence for choosing it are readable.
3. The intended message is present after sending.
4. ChatGPT produced a complete response.
5. Codex can read the response verbatim.

A visible and selectable `Pro` option may prove the selected tier for that moment. If `Pro` is unavailable, use a choice the current UI explicitly labels as its strongest reasoning tier. Do not claim a global capability ranking, infer a paid tier from account assumptions, or rely on product memory or a prior task. Do not buy or upgrade a plan.

## Browser and conversation reuse

Maintain one browser tab across tasks when possible. Open a tab only when no managed or claimable ChatGPT tab exists. For every task, start a clean conversation inside that tab so unrelated task context does not leak. A new-chat route isolates canonical turns; it does not prove that same-origin composer storage is empty or erase verified Skill authorship.

Include a deterministic `CODEX_TASK_ID:<marker>` in the submitted envelope. After interruption, search the current conversation for that marker before retrying. If the message exists, recover or wait for its response; do not resend it.

## Interaction checkpoints

Use these substates for both the connection message and the task envelope. They refine the top-level collaboration state without replacing it.

| Substate | Required evidence | Allowed next step |
| --- | --- | --- |
| `BASELINE_UNSET` | The active page, conversation, or composer identity is new or changed | Observe without input until the stabilization bound passes, or classify pre-input content |
| `BASELINE_STABLE` | At least three empty, attachment-free, non-sendable reads span at least five seconds after the last identity change | Freeze the transport payload and attachment manifest, create write-ahead provenance, then use one semantic input action |
| `PERSISTED_SKILL_DRAFT` | A pre-existing `WRITTEN` provenance record and every exact recovery check prove this unsent draft was placed by this Skill for the active task before navigation | Resume canonical readiness validation without rewriting, clearing, or consuming another initialization attempt |
| `PERSISTED_UNOWNED_DRAFT` | Pre-input text or attachments exist without complete write-ahead ownership proof | Preserve unchanged; request exact task-local removal authorization or enter `BLOCKED` |
| `DRAFT_RESET_AUTHORIZED` | The user explicitly authorized removal of the exact observed unowned text and there are zero attachments | Perform one semantic clear, one reload, and one complete stabilization cycle; never retry |
| `INPUT_UNREADY` | Canonical payload equality, attachment equality, stable composer identity, or a send-ready structural state has not yet been established | Wait and recheck; do not use raw DOM serialization as a multiline equality gate |
| `DRAFT_CONTAMINATED` | After Skill input, the canonical draft has an unknown prefix/suffix, duplicate, stale content, IME residue, unsupported topology, identity replacement, or an unexpected attachment | Do not clear or send; use the one clean-conversation initialization retry if still available |
| `INPUT_READY` | Canonical composer plaintext exactly matches the transport payload by code points, UTF-8 SHA-256, length, marker count, attachment manifest, and stable identity, and the composer is structurally send-ready with current model evidence | Attempt one submission |
| `SEND_ATTEMPTED` | One send action was issued | Observe the conversation; do not issue a second send action |
| `SEND_CONFIRMED` | The exact user payload or task marker appears exactly once in canonical user-authored turns | Wait for the response |
| `POST_SEND_PHANTOM_DRAFT` | Unexpected composer text appears only after delivery was confirmed | Do not focus, clear, overwrite, or send it; continue observing the already-sent response and record the draft separately |
| `SEND_UNKNOWN` | The send action timed out, errored, navigated, or was interrupted before its outcome was established | Reacquire and inspect the same conversation |
| `SEND_RETRY_READY` | Canonical user-turn evidence confirms absence, and the exact Skill-owned unsent payload remains available | Issue at most one fallback submission |
| `FALLBACK_ATTEMPTED` | The single permitted fallback send action was issued | Observe the conversation; never issue another send action |
| `FALLBACK_UNKNOWN` | The fallback action had an ambiguous outcome | Reacquire and inspect; confirm delivery or enter `BLOCKED` |
| `RESPONSE_OBSERVED` | An assistant response exists and active generation has ended | Confirm stable completion and read final content |
| `CONTENT_VERIFIED` | The complete response is readable and satisfies any exact-content requirement | Continue to review |

Use this transition graph as the normative recovery contract:

<!-- CONTRACT_TRANSITIONS_START -->
```text
BASELINE_UNSET -> BASELINE_STABLE | PERSISTED_SKILL_DRAFT | PERSISTED_UNOWNED_DRAFT | BLOCKED
PERSISTED_SKILL_DRAFT -> INPUT_UNREADY | INPUT_READY | BLOCKED
PERSISTED_UNOWNED_DRAFT -> DRAFT_RESET_AUTHORIZED | BLOCKED
DRAFT_RESET_AUTHORIZED -> BASELINE_UNSET | BLOCKED
BASELINE_STABLE -> INPUT_UNREADY | BLOCKED
INPUT_UNREADY -> INPUT_READY | DRAFT_CONTAMINATED | BLOCKED
DRAFT_CONTAMINATED -> BASELINE_UNSET | BLOCKED
INPUT_READY -> SEND_ATTEMPTED | BLOCKED
SEND_ATTEMPTED -> SEND_CONFIRMED | SEND_UNKNOWN | BLOCKED
SEND_UNKNOWN -> SEND_CONFIRMED | SEND_RETRY_READY | BLOCKED
SEND_RETRY_READY -> FALLBACK_ATTEMPTED | BLOCKED
FALLBACK_ATTEMPTED -> SEND_CONFIRMED | FALLBACK_UNKNOWN | BLOCKED
FALLBACK_UNKNOWN -> SEND_CONFIRMED | BLOCKED
SEND_CONFIRMED -> POST_SEND_PHANTOM_DRAFT | RESPONSE_OBSERVED | BLOCKED
POST_SEND_PHANTOM_DRAFT -> RESPONSE_OBSERVED | BLOCKED
RESPONSE_OBSERVED -> CONTENT_VERIFIED | BLOCKED
```
<!-- CONTRACT_TRANSITIONS_END -->

Never transition directly from `SEND_UNKNOWN` to `SEND_ATTEMPTED`. A fallback submission is allowed only from `SEND_RETRY_READY`, which is consumed by `FALLBACK_ATTEMPTED` and cannot be re-entered. `FALLBACK_UNKNOWN` permits observation only, never another send. Exactly-once delivery is the invariant; a confirmed failed initial action followed by one fallback may produce two send attempts but still only one canonical user message. More than one matching user message is a duplicate-send violation and requires `BLOCKED`.

Canonical message evidence counts only user-authored conversation turns in the active conversation. Exclude composer drafts, assistant content or echoes, sidebar and navigation text, accessibility duplicates, and repeated presentation nodes. The task marker is the preferred canonical key for an envelope; use the exact payload for the connection gate.

Use [composer-contract.md](composer-contract.md) as the normative payload, editor-extraction, and provenance contract. Normalize only `CRLF` and `CR` to `LF` before hashing and input; do not trim or apply Unicode normalization. Reconstruct canonical composer plaintext from semantic editor blocks. Raw `innerText` and `textContent` are diagnostics only because rich-text layout can respectively add or remove newlines. Exact canonical code-point equality, UTF-8 SHA-256, code-point length, marker count, attachment manifest, and stable composer identity are the readiness gate.

The baseline bound begins after the last page, conversation, or composer-DOM identity change and requires at least three empty text-and-attachment reads spanning at least five seconds; every read must also show a non-sendable composer. Identity and route rechecks must occur between reads; a composer node replacement restarts the bound. A first empty render, reload, same-URL navigation, placeholder text, or two rapid empty reads does not establish a reset. Revalidate identity, ownership, canonical payload, attachments, and send readiness immediately before submission.

Immediately before semantic input, create an in-memory provenance record in state `PREPARED`. Promote it to `WRITTEN` only after the post-write canonical checks pass. Never backfill authorship from content discovered later. After a conversation or composer change, exact content restored from a `WRITTEN` record with zero send actions and zero matching canonical user turns is `PERSISTED_SKILL_DRAFT`; continue without another fill or clear. Thus route changes do not erase authorship, but a marker or visual match alone never creates it.

All other content appearing before the first Skill input is `PERSISTED_UNOWNED_DRAFT`. Opening another tab or new-chat route does not isolate same-origin draft persistence. Do not loop on tabs, clear site storage, use keyboard selection/deletion, overwrite the draft with the payload, or relabel it as IME residue. Without exact task-local authorization, preserve it and enter `BLOCKED`. General urgency, permission to continue, or the fact that the draft matches the current topic is not deletion authorization.

When the user explicitly identifies and authorizes removal of the exact observed draft, `DRAFT_RESET_AUTHORIZED` permits one clear attempt only. Immediately before clearing, require exact canonical code-point equality with the authorized text and zero attachments. Use a semantic editor replacement action that produces normal editor events, then require empty text, zero attachments, and a disabled send control. Reload the Skill-created page exactly once and run the complete baseline bound again. A changed draft, attachment, action error, reappearance, or sendable empty editor is `BLOCKED`; do not retry or clear broader site data.

After `BASELINE_STABLE`, prefer a locator-level fill action. Do not use coordinate typing, paste, or keyboard shortcuts as the primary path because they can interact with IME composition or the wrong focused node. If unexpected canonical content or a composer-DOM replacement appears after Skill input, use `DRAFT_CONTAMINATED` and abandon it without clearing. Retry once in a genuinely new conversation only after establishing another stable baseline. Across one gate or task, the initial page/conversation initialization plus one automatic initialization retry is the hard maximum. A failed baseline consumes that attempt; recovery cannot recurse, create more tabs, or reset the exactly-once send-action ledger.

Unexpected composer text observed only after `SEND_CONFIRMED` is `POST_SEND_PHANTOM_DRAFT`. It cannot be cleared, overwritten, focused, or sent, but it does not retroactively invalidate the canonical sent turn or block completion reads. If it persists into a later pre-input baseline without qualifying provenance, reclassify it as `PERSISTED_UNOWNED_DRAFT` for that later write attempt.

Model evidence may appear only after the composer becomes ready. Before each asynchronous wait, choose and record a finite deadline or maximum recheck count supported by the active browser surface. Record the chosen bound, observations, and exhaustion outcome. Do not infer the current conversation's selection from account tier, prior conversations, or product memory. If the input or model bound expires without evidence, enter `BLOCKED`; if a send-recovery bound expires, remain `SEND_UNKNOWN` and enter `BLOCKED`.

## Complete-response rule

Treat a response as incomplete while the page exposes an active-generation control, streaming text is still changing, an error banner is present, or the response terminates mid-structure. Before waiting, choose and record a finite completion bound. Treat the response as complete only when the assistant response exists, generation has ended, response actions or another structural completion signal are present, and two consecutive content reads separated by a state recheck are identical and readable. A localized or transient status string is supporting evidence only and must not be the sole completion test. Enter `BLOCKED` if the completion bound expires without stable evidence.

For an exact reply such as `CONNECTION_OK`, inspect the final assistant content after structural completion and then compare it verbatim. Do not convert a failed status-locator wait into a failed reply claim when the completed content can still be recovered.

If the page is interrupted:

1. Reacquire the same conversation when possible.
2. Count exact matches for the original user message or task marker in canonical user-authored turns only.
3. If one match exists, recover or wait for its response. If more than one exists, enter `BLOCKED` for a duplicate-send violation.
4. Do not resend until the message is confirmed absent; an action error is not evidence of absence.
5. Enter `BLOCKED` if the send outcome or response cannot be recovered reliably.

## Review and correction loop

Classify each material recommendation as `ACCEPT`, `REJECT`, or `NEEDS_EVIDENCE`.

- `ACCEPT`: local constraints and evidence support it.
- `REJECT`: source, authoritative documentation, or executed verification contradicts it.
- `NEEDS_EVIDENCE`: verification has not yet been performed or is inconclusive.

When a correction is useful, send only the conflicting evidence and necessary context. Keep the task in `REVIEWING` until the revised answer is captured; then reassess. Repeated disagreement does not override local evidence.

## Fail-closed cases

Enter `BLOCKED` for the consultation path when:

- the required browser surface is unavailable;
- authentication or human verification is required;
- the target Pro or UI-labeled strongest reasoning tier cannot be identified or selected from visible page evidence;
- a pre-input persisted draft lacks either complete write-ahead Skill provenance or exact task-local removal authorization;
- an authorized one-shot draft reset is ambiguous or the draft reappears during the post-reload stabilization window;
- canonical composer plaintext cannot be reconstructed unambiguously from the active editable root;
- canonical payload hash, code-point length, marker count, attachment manifest, or composer identity differs after the one permitted initialization retry;
- an occupied composer cannot be proven empty or Skill-owned;
- the message cannot be shown as sent;
- the submission outcome remains unknown or a matching message appears more than once;
- the response is partial, inaccessible, or lost;
- a requested upload lacks authorization or fails content review;
- a required external claim cannot be checked;
- implementation or verification lacks permission, dependencies, or reproducible evidence.

Codex may continue purely local work only when it remains within the user's request and does not pretend that external consultation succeeded.
