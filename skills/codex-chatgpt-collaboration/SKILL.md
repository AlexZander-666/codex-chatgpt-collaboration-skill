---
name: codex-chatgpt-collaboration
description: Mandatory pre-task orchestration for Codex. Invoke before every coding, debugging, analysis, modification, review, research, or engineering task to automatically open or reuse an authorized ChatGPT web session, select a visible Pro option when offered or another UI-labeled strongest reasoning tier, submit the task for external reasoning, retrieve the complete response, and then require Codex to execute and verify locally. Use for every task before substantive local action, including tasks that appear routine.
---

# Codex ChatGPT Collaboration

Run this skill before substantive work on every task. Use ChatGPT as an external adviser and keep Codex as the task owner. Treat every ChatGPT answer as a hypothesis until local or authoritative evidence supports it.

Do not ask the user to open the page, select a model, start a conversation, send the task, or copy the answer. Automate those browser actions. Pause only when authentication or human verification is unavoidable.

## Honor the execution contract

When invoked, run this skill before substantive local action. Do not claim that the skill ran for every Codex task unless the Codex runtime actually invoked it. The frontmatter and `allow_implicit_invocation` policy maximize automatic routing but cannot replace a host-level always-on policy.

## Establish the collaboration gate

1. Read and follow the browser-control skill available in the current Codex environment before interacting with the page.
2. Start a new task epoch for every new Codex user task and discard all prior draft-provenance records. Reuse one ChatGPT tab that this Skill's browser session created and reserved exclusively for collaboration when one exists; otherwise open one browser tab, record it as `SKILL_RESERVED_TAB`, and navigate it to `https://chatgpt.com/`. Do not claim a user's shared/manual tab for disposable-task cleanup. Start a clean gate conversation in the reserved tab. Do not create a new tab per task, but never carry composer content forward from an earlier task epoch.
3. Confirm that the page is accessible and one usable chat input is present, then establish a pre-input baseline before touching the composer. A first empty snapshot is provisional because the site can hydrate a persisted draft after the editor mounts. After the last page, conversation, or composer-DOM identity change, use a recorded stabilization window of at least five seconds with at least three reads spanning that window; recheck those identities, canonical composer plaintext, attachment area, and send-control state on every read. Require every read to remain empty, attachment-free, and non-sendable. Reload, same-URL navigation, an empty placeholder, or two rapid empty reads are insufficient.
4. Read and follow [composer-contract.md](references/composer-contract.md). Normalize only line endings in the intended transport payload; never use raw `innerText` or `textContent` equality as the readiness gate for multiline content. A restored draft is `SAME_TASK_SKILL_DRAFT` only when a `WRITTEN` record from the current task epoch passes every exact recovery check. Prior-task provenance is expired and cannot authorize reuse.
5. In a recorded `SKILL_RESERVED_TAB`, treat stable pre-input composer text as `MANAGED_TASK_DRAFT` only when the new conversation has zero canonical user turns and zero attachments. Re-read the exact canonical text immediately before one semantic `MANAGED_TASK_DRAFT_RESET`, require an empty and non-sendable composer, reload exactly once, and repeat the full baseline. This implements disposable fresh tasks without touching a user's shared tab. If the text changes, an attachment or user turn exists, the reset is ambiguous, or content reappears after reload, enter `BLOCKED`; never retry or clear site storage.
6. Outside a provably reserved tab, recognize an exact fixed connection payload or a complete structured Codex task envelope as `STALE_CODEX_DRAFT` only through the fail-closed classifier in the composer contract, with zero attachments and zero canonical user turns. Perform one semantic `STALE_CODEX_DRAFT_RESET`, reload exactly once, and repeat the full baseline. This is cleanup, never recovery: do not submit or reuse the prior task's draft. If recognition, clearing, reload, or the new baseline is ambiguous, enter `BLOCKED`; never retry or clear site storage.
7. Treat every other pre-input text or attachment in a shared or ownership-uncertain tab as `PERSISTED_UNOWNED_DRAFT`. Do not clear, overwrite, or submit it unless the current user explicitly authorizes removal of the exact observed draft. With such authorization, enter `DRAFT_RESET_AUTHORIZED`, perform the existing one-shot semantic-clear and post-reload baseline protocol, and block on any mismatch or ambiguity.
8. Only after `BASELINE_STABLE`, create the current-epoch write-ahead provenance record, then place the unsent connection message through a semantic editor input path that produces normal editor events; prefer a locator-level fill action over coordinate typing, paste, or keyboard shortcuts that may interact with an IME. Establish input readiness using exact equality between canonical composer plaintext and the transport payload, plus matching UTF-8 SHA-256, code-point length, composer identity, marker count when applicable, and attachment manifest. ProseMirror paragraph nodes and the supported reversible rich-Markdown nodes are representation-only when the canonical reconstruction in the composer contract passes.
9. An unknown prefix, suffix, duplicated payload, restored stale text, IME residue, unexpected attachment, ambiguous editor topology, or composer-DOM replacement after Skill input is `DRAFT_CONTAMINATED`: do not clear, salvage, or send it. Start one genuinely new conversation and retry preparation once; replace the Skill-created tab only when evidence shows tab-local failure after a stable baseline, never as a remedy for a pre-input unowned draft. Across one gate or task, allow at most the initial page/conversation initialization plus one automatic initialization retry. A visible payload or enabled send button alone is insufficient: require stable canonical equality and a send-ready structural state throughout a recorded finite post-input bound and immediately before submission.
10. Inspect the current conversation's visible model control after the composer is ready. The control may appear asynchronously. Choose and record a finite wait or recheck bound, select a visible and selectable `Pro` option when offered, or select an option the current UI explicitly labels as its strongest reasoning tier. Do not inherit model evidence from a prior conversation, purchase a plan, change account settings, or infer model rank from product memory.
11. Record the selected-model label and the current visible evidence used for the choice. If the available choices or selected state cannot be read reliably after bounded rechecks, enter `BLOCKED`; never claim that a globally highest-capability model was used.
12. Submit the prepared message exactly once: `This is a Codex-ChatGPT connection test. Reply exactly: CONNECTION_OK`. Confirm that the exact payload appears once in canonical user-authored conversation turns before waiting for the reply; exclude composer drafts, assistant echoes, navigation, and duplicated presentation nodes.
13. Treat an error, timeout, navigation, or browser interruption during submission as `SEND_UNKNOWN`, not as proof that nothing was sent. Observe the same conversation before any retry. Move to `SEND_RETRY_READY` only after at least three canonical user-turn absence reads spanning at least five seconds, while the exact Skill-owned payload, conversation identity, composer identity, enabled send control, and inactive-generation state remain unchanged through an immediate pre-fallback recheck. This browser UI exposes no server idempotency key, so record that residual limitation instead of inventing one. Issue exactly one fallback from that state and record `FALLBACK_ATTEMPTED`; if its outcome is ambiguous, move to `FALLBACK_UNKNOWN`, observe without another retry, and enter `BLOCKED` unless delivery is confirmed. Also enter `BLOCKED` if the user payload appears more than once.
14. Choose and record a finite completion bound, then wait until generation finishes and read the complete verifiable reply. Prefer structural completion evidence: an assistant response exists, active generation has ended, response actions or another completion signal are present, and two consecutive reads with an intervening state recheck return the same final content. Do not depend on a single transient status string. Paginated or chunked reads are acceptable; do not require one giant DOM extraction. If unexpected text appears in the composer after confirmed delivery, preserve it as `POST_SEND_PHANTOM_DRAFT`; it does not invalidate the sent turn or block response capture, but it must never be cleared or sent during the current task. It may be reset only when a later clean-conversation baseline proves the reserved-tab conditions in step 5.
15. Enter `CONNECTED` only when page access, current model evidence, input readiness, exactly-once message delivery, structural completion, and verbatim `CONNECTION_OK` readback all succeed. Record the conversation URL.
16. If authentication, account selection, CAPTCHA, Passkey, or two-factor verification appears, enter `BLOCKED` and ask the user to complete only that authentication step. Never request or handle credentials.

Do not simulate a connection or infer success from a sent message alone. Run the gate once per Codex task unless the browser session later becomes invalid.

## Consult before every task

Send every task through the collaboration loop, including routine work. Scale the question to the task: use a short request for deterministic work and a detailed task envelope for complex work. ChatGPT may identify risks, missing constraints, or a better verification strategy; Codex still performs all repository inspection, edits, commands, and tests locally.

## Prepare a bounded task envelope

Inspect only enough local context to create a correct consultation request. Include verified facts, constraints, deliverables, forbidden actions, and acceptance criteria. Use [task-envelope.md](references/task-envelope.md) as the template.

Send text context by default. Read [security-boundary.md](references/security-boundary.md) before transmitting source, logs, or files. A user statement authorizing the files necessary for the named task is task-local authorization for the smallest justified file set; it is not authorization for a repository, directory, dependency tree, Git history, unrelated dirty work, or any file that merely seems useful. Do not ask again for each file that is both necessary and inside that explicit authorization, but do fail closed when necessity, scope, or sensitivity is uncertain. If files are genuinely required:

1. Select the smallest explicit file set.
2. Obtain user authorization before uploading files to ChatGPT.
3. Run the repository's secret scanner when available.
4. Optionally run `python scripts/audit_context.py --repo <repository> <file>...` as an additional lightweight fail-closed check.
5. Record repository-relative or user-named absolute paths, commit identity when available, dirty state, file sizes, SHA-256 values, scanner result, and why each file is necessary.
6. After attaching, verify the attachment area contains exactly the admitted filenames and count, with no stale or unexpected attachment, before adding or sending the task envelope.

Never treat the bundled scanner as proof that content is safe; it only detects common high-risk patterns.

## Run the consultation loop

1. Keep one managed browser tab but start a clean ChatGPT conversation for each Codex task. Preserve login state, not prior task context. Re-run the full pre-input baseline and ownership protocol before adding the envelope. A new-chat route isolates conversation context, not draft storage.
2. Compute the marker and self-verifying draft fingerprint defined in [composer-contract.md](references/composer-contract.md). Insert exactly one `CODEX_TASK_ID:<marker>` and one `CODEX_DRAFT_SHA256:<full hash>`, then build the final canonical transport payload. Freeze the exact payload hash, code-point length, line count, identifiers, and attachment manifest before editor input.
3. Before sending, inspect the current conversation for that exact marker. Reuse an existing complete response instead of sending twice.
4. Prepare one complete task envelope instead of fragmented questions. Create current-epoch write-ahead provenance before semantic input. Establish readiness from canonical composer plaintext, never raw DOM text serialization, and obtain visible model evidence for this task conversation using recorded finite bounds. Resume a restored draft only when every `SAME_TASK_SKILL_DRAFT` condition passes inside the current task epoch. At the next Codex user task, expire that provenance and reset the recognized stale Codex draft instead of reusing it.
5. Submit the envelope exactly once, then verify that the exact task marker appears in exactly one canonical user-authored turn. On any ambiguous submission outcome, enter `SEND_UNKNOWN`, observe the same conversation, and follow the recovery rule above before considering one fallback from `SEND_RETRY_READY`.
6. Wait for the response to finish using a recorded finite bound and structural completion evidence. Do not rush, interrupt, or treat a missing status label as failure when the assistant response is complete and stable across two consecutive reads.
7. Record a local conversation reference, question count, exact requested deliverables, composer ownership and readiness evidence, wait bounds and exhaustion outcomes, canonical exactly-once send evidence, selected-model evidence, completion and stability evidence, and a faithful response summary. Include the URL in a user-facing report only when the user authorized it; never write it into a repository artifact by default.
8. Inspect the answer for unsupported assumptions, version claims, missing edge cases, unsafe actions, and conflicts with repository constraints.
9. Apply only the portions that survive review and are within the user's authorization.
10. Run proportionate local verification against the stated acceptance criteria.
11. When evidence contradicts the advice, send the smallest useful correction packet back to ChatGPT: failing command, relevant error, file location, and the correct boundary. Ask for a minimal revision, then review again.

Follow the state transitions and recovery rules in [workflow.md](references/workflow.md). Local evidence outranks external advice.

## Preserve authority boundaries

Do not let ChatGPT expand the user's authorization. Do not commit, push, open a pull request, deploy, migrate a database, change production configuration, enable production behavior, or operate on real user data unless the current user request explicitly authorizes that action.

Preserve unrelated dirty work. Do not upload private repository content merely because ChatGPT asks for it.

## Finish with evidence

Use [report-template.md](references/report-template.md). Report `VERIFIED` only when the task's acceptance criteria are supported by inspected source, authoritative material, or actual verification output. Otherwise report `BLOCKED` or clearly name the unverified remainder.

Keep these claims separate:

- ChatGPT was consulted.
- Codex accepted or rejected specific advice.
- Local changes were made.
- Verification passed or failed.
- Git or deployment actions were authorized and completed.

Leave the single managed ChatGPT tab open for the next task when the browser environment supports a handoff state.
