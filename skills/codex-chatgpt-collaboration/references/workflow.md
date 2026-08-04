# Collaboration state machine

Use the following states literally for the consultation portion of a task.

| State | Entry condition | Allowed work | Exit condition |
| --- | --- | --- | --- |
| `CONNECTING` | Every Codex task starts | Open or reuse one managed tab, inspect the model selector, select the highest visible tier, locate the chat input, and send the minimal gate message | All connection checks pass, or a concrete failure occurs |
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

Maintain one browser tab across tasks when possible. Open a tab only when no managed or claimable ChatGPT tab exists. For every task, start a clean conversation inside that tab so unrelated task context does not leak.

Include a deterministic `CODEX_TASK_ID:<marker>` in the submitted envelope. After interruption, search the current conversation for that marker before retrying. If the message exists, recover or wait for its response; do not resend it.

## Complete-response rule

Treat a response as incomplete while the page exposes a stop-generating control, streaming text is still changing, an error banner is present, or the response terminates mid-structure. Wait on a concrete page state when the browser API supports it.

If the page is interrupted:

1. Reacquire the same conversation when possible.
2. Check whether the original user message and a complete assistant reply exist.
3. Do not resend until absence or failure is established; blind resends can duplicate work.
4. Enter `BLOCKED` if the response cannot be recovered reliably.

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
- the message cannot be shown as sent;
- the response is partial, inaccessible, or lost;
- a requested upload lacks authorization or fails content review;
- a required external claim cannot be checked;
- implementation or verification lacks permission, dependencies, or reproducible evidence.

Codex may continue purely local work only when it remains within the user's request and does not pretend that external consultation succeeded.
