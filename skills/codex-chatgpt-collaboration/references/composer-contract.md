# Composer transport and ownership contract

ChatGPT uses a rich-text editor. DOM serialization is not the message payload: `innerText` can insert layout newlines between paragraphs, while `textContent` can remove paragraph boundaries. Never compare either raw value directly with a multiline task envelope.

## Canonical transport payload

Avoid circular identifiers. First create the marker basis from the LF-normalized user request, the literal separator `LF + NUL + CODEX_TASK_ENVELOPE + NUL + LF`, and the LF-normalized task envelope with the entire `CODEX_TASK_ID:` and `CODEX_DRAFT_SHA256:` lines omitted. Hash that basis and use the first 16 lowercase hexadecimal characters by default. Insert `CODEX_TASK_ID:<marker>` exactly once. Next compute SHA-256 over the LF envelope with the entire fingerprint line omitted and insert `CODEX_DRAFT_SHA256:<full hash>` exactly once. Then create the final transport payload:

1. Replace `CRLF` with `LF`, then replace any remaining `CR` with `LF`.
2. Do not trim, collapse whitespace, normalize Unicode, alter punctuation, or add a final newline.
3. Compute SHA-256 over the UTF-8 encoding of that exact final transport payload.
4. Record its Unicode code-point length, line count, SHA-256, task marker, and draft fingerprint.

All later equality checks target this transport payload. The source and transport lengths may differ only because of recorded line-ending conversion.

## Canonical composer plaintext

Read only the active editable root, not placeholder, sidebar, accessibility mirror, or surrounding UI text. Reconstruct semantic plaintext as follows:

1. Inspect the editable root's direct content children.
2. For the plain ProseMirror shape containing only direct `p`, `div`, or `pre` blocks, convert each block to logical text and join adjacent blocks with exactly one `LF`. An explicit empty direct paragraph therefore preserves a blank line between its neighbors.
3. ChatGPT may instead parse the task envelope as rich Markdown. For this shape, support only direct `h1` through `h6`, flat `ul`/`ol`, and the plain blocks above. Reconstruct canonical ATX heading markers, `- ` list markers, and sequential decimal ordered-list markers. Join a heading to its body with one `LF`; join every other adjacent top-level rich block with two `LF` characters. This reverses the editor's removal of Markdown markers and blank separator lines.
4. Inside a logical block, append text-node code points unchanged. Convert a real `<br>` to one `LF`, but ignore an editor-owned trailing sentinel such as `br.ProseMirror-trailingBreak`.
5. Rich task envelopes must use the closed canonical grammar emitted by the task template: ATX headings, hyphen bullets, sequential decimal ordered lists, plain text spans, and raw URL autolinks whose visible text exactly equals their `href`. Inline Markdown formatting, labeled links, nested lists, multiple paragraphs inside one list item, empty rich blocks, tables, blockquotes, mixed top-level block/inline content, unexplained non-editable content, nested editor roots, or any unsupported topology are ambiguous and must not be guessed.
6. A single inline/text run may be read as one block. Record the extractor rule version and a compact topology summary including direct block tags and counts. Raw `innerText` and `textContent` lengths may be recorded for diagnostics only; they are never readiness gates for multiline input.

Compare the reconstructed plaintext with the transport payload by exact Unicode code points. Also compare UTF-8 SHA-256 and code-point length, require the expected task marker exactly once, require the same composer identity, and require the frozen attachment manifest. If all checks pass, paragraph-node conversion is representation-only and does not block submission.

The bundled read-only helper at `scripts/composer_contract.py` implements the stable marker basis, draft fingerprint, stale-Codex-draft classifier, line-ending normalization, UTF-8 hashing, and fail-closed reconstruction for supported ProseMirror `innerHTML` snapshots. Use it when the active browser surface can return the editable root's exact `innerHTML`; unsupported or mixed topology raises an error instead of guessing. Browser-side semantic extraction may be used when it implements the same rules and records its version.

### Normative examples

| Intended transport payload | Representative editor DOM | Canonical plaintext |
| --- | --- | --- |
| `alpha` | `<p>alpha</p>` | `alpha` |
| `alpha\nbeta` | `<p>alpha</p><p>beta</p>` | `alpha\nbeta` |
| `alpha\n\nbeta` | `<p>alpha</p><p><br class="ProseMirror-trailingBreak"></p><p>beta</p>` | `alpha\n\nbeta` |
| `alpha\nbeta` | `<p>alpha<br>beta</p>` | `alpha\nbeta` |
| `## Objective\nReview.\n\n## Questions\n1. Complete?` | `<h2>Objective</h2><p>Review.</p><h2>Questions</h2><ol><li><p>Complete?</p></li></ol>` | `## Objective\nReview.\n\n## Questions\n1. Complete?` |

## Task epoch and write-ahead provenance

Every new Codex user task starts a new task epoch. Discard all prior in-memory draft provenance at that boundary. A clean ChatGPT conversation is required for the new task; an unsent draft from an earlier task is never resumed merely because its marker, hash, body, or prior provenance is known.

Within one task epoch, draft ownership is based on recorded authorship, not the current route.

Immediately before the first semantic write, create an in-memory, non-repository provenance record containing:

- current task-epoch identity, operation kind (`connection` or `task`), task marker when applicable, draft fingerprint when applicable, payload SHA-256, code-point length, and line count;
- frozen attachment manifest and expected count;
- page, conversation, and composer identities;
- initialization-attempt number and send-action count;
- state `PREPARED`, created before observing any post-write content.

After the semantic write, promote the record to `WRITTEN` only when canonical composer plaintext, hash, length, marker count, attachment manifest, and composer identity all match. Never create or backfill a `WRITTEN` record merely because matching text was later discovered.

If ChatGPT restores the draft after a route, conversation, or composer identity change during the same task epoch, classify it as `SAME_TASK_SKILL_DRAFT` only when all of these hold:

- a pre-existing `WRITTEN` record exists in the current task epoch for the active gate or task;
- no send action has been issued for that payload;
- canonical plaintext, SHA-256, code-point length, marker count, and attachment manifest exactly match the record;
- canonical user-authored turns contain no matching gate payload or task marker.

Resume validation without rewriting or clearing the draft. This exception exists only for interruption recovery inside the current Codex task; it expires before the next user task begins.

## Prior-task Codex draft reset

At the beginning of a new task epoch, classify an unsent prior draft as `STALE_CODEX_DRAFT` only when there are zero attachments, the active clean conversation contains zero canonical user turns, and canonical text is one of:

- the exact fixed Codex connection-test payload;
- a fingerprinted Codex task envelope whose preamble, single hexadecimal marker, single fingerprint, ordered required headings, and recomputed fingerprint all validate;
- a legacy Codex task envelope without a fingerprint whose two non-empty top lines contain exactly one hexadecimal marker and one Codex external-review preamble beginning `You are an external ` and containing `Do not perform local actions.`, followed by the six core headings in exact order; the older optional `Evidence already available` heading may be present or absent.

The legacy case exists to remove drafts created before the fingerprint protocol. A marker or a few matching headings alone is insufficient. Attachments, extra protocol lines, malformed identifiers, missing or reordered headings, a fingerprint mismatch, canonical user turns, or any non-Codex text disqualifies automatic reset and remains `PERSISTED_UNOWNED_DRAFT`.

For `STALE_CODEX_DRAFT`, perform one `STALE_CODEX_DRAFT_RESET` action: re-read and reclassify the exact canonical draft immediately before the action, use one semantic clear that produces normal editor events, verify empty canonical text, zero attachments, and a disabled send control, then reload exactly once and repeat the full baseline stabilization window. If the draft changes, reappears, the clear is ambiguous, or any attachment exists, enter `BLOCKED`; never retry the reset or clear site storage.

This automatic reset is limited to a new task epoch and a fully recognized Codex-generated draft. It must never clear a same-task recovery draft, arbitrary user prose, a partial envelope, or any attachment. A draft that fails either same-task provenance or stale-Codex recognition is `PERSISTED_UNOWNED_DRAFT` and still requires exact user authorization before removal.

## Post-send phantom drafts

After exactly-once delivery is confirmed, unexpected composer text is `POST_SEND_PHANTOM_DRAFT`. Do not clear, overwrite, focus, or send it. It does not invalidate the already confirmed message or prevent reading its response. Observe it separately; if it disappears, record that fact. Before any later write, start the normal task-epoch baseline protocol again. In the same task epoch it needs qualifying provenance; in a later task epoch it may be reset only if it satisfies the complete `STALE_CODEX_DRAFT` classifier above. Otherwise it is `PERSISTED_UNOWNED_DRAFT`.
