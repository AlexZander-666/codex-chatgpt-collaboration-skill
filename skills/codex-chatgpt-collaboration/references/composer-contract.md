# Composer transport and ownership contract

ChatGPT uses a rich-text editor. DOM serialization is not the message payload: `innerText` can insert layout newlines between paragraphs, while `textContent` can remove paragraph boundaries. Never compare either raw value directly with a multiline task envelope.

## Canonical transport payload

Avoid a circular marker calculation. First create the marker basis from the LF-normalized user request, the literal separator `LF + NUL + CODEX_TASK_ENVELOPE + NUL + LF`, and the LF-normalized task envelope with the entire `CODEX_TASK_ID:` line omitted. Hash that basis and use the first 16 lowercase hexadecimal characters by default. Insert `CODEX_TASK_ID:<marker>` exactly once, then create the final transport payload:

1. Replace `CRLF` with `LF`, then replace any remaining `CR` with `LF`.
2. Do not trim, collapse whitespace, normalize Unicode, alter punctuation, or add a final newline.
3. Compute SHA-256 over the UTF-8 encoding of that exact final transport payload.
4. Record its Unicode code-point length, line count, SHA-256, and task marker.

All later equality checks target this transport payload. The source and transport lengths may differ only because of recorded line-ending conversion.

## Canonical composer plaintext

Read only the active editable root, not placeholder, sidebar, accessibility mirror, or surrounding UI text. Reconstruct semantic plaintext as follows:

1. Inspect the editable root's direct content children.
2. For the normal ProseMirror shape, convert each direct block child to logical text and join adjacent direct blocks with exactly one `LF`. An empty direct paragraph therefore preserves a blank line between its neighbors.
3. Inside a block, append text-node code points unchanged. Convert a real `<br>` to one `LF`, but ignore an editor-owned trailing sentinel such as `br.ProseMirror-trailingBreak`.
4. A single inline/text run may be read as one block. Mixed top-level block and non-whitespace inline content, unexplained non-editable content, nested editor roots, or an unsupported topology is ambiguous and must not be guessed.
5. Record the extractor rule version and a compact topology summary such as direct block count. Raw `innerText` and `textContent` lengths may be recorded for diagnostics only; they are never readiness gates for multiline input.

Compare the reconstructed plaintext with the transport payload by exact Unicode code points. Also compare UTF-8 SHA-256 and code-point length, require the expected task marker exactly once, require the same composer identity, and require the frozen attachment manifest. If all checks pass, paragraph-node conversion is representation-only and does not block submission.

The bundled read-only helper at `scripts/composer_contract.py` implements the stable marker basis, line-ending normalization, UTF-8 hashing, and fail-closed reconstruction for supported ProseMirror `innerHTML` snapshots. Use it when the active browser surface can return the editable root's exact `innerHTML`; unsupported or mixed topology raises an error instead of guessing. Browser-side semantic extraction may be used when it implements the same rules and records its version.

### Normative examples

| Intended transport payload | Representative editor DOM | Canonical plaintext |
| --- | --- | --- |
| `alpha` | `<p>alpha</p>` | `alpha` |
| `alpha\nbeta` | `<p>alpha</p><p>beta</p>` | `alpha\nbeta` |
| `alpha\n\nbeta` | `<p>alpha</p><p><br class="ProseMirror-trailingBreak"></p><p>beta</p>` | `alpha\n\nbeta` |
| `alpha\nbeta` | `<p>alpha<br>beta</p>` | `alpha\nbeta` |

## Write-ahead draft provenance

Draft ownership is based on recorded authorship, not the current route.

Immediately before the first semantic write, create an in-memory, non-repository provenance record containing:

- operation kind (`connection` or `task`), task marker when applicable, payload SHA-256, code-point length, and line count;
- frozen attachment manifest and expected count;
- page, conversation, and composer identities;
- initialization-attempt number and send-action count;
- state `PREPARED`, created before observing any post-write content.

After the semantic write, promote the record to `WRITTEN` only when canonical composer plaintext, hash, length, marker count, attachment manifest, and composer identity all match. Never create or backfill a `WRITTEN` record merely because matching text was later discovered.

If ChatGPT restores the draft after a route, conversation, or composer identity change, classify it as `PERSISTED_SKILL_DRAFT` only when all of these hold:

- a pre-existing `WRITTEN` record exists for the active gate or task;
- no send action has been issued for that payload;
- canonical plaintext, SHA-256, code-point length, marker count, and attachment manifest exactly match the record;
- canonical user-authored turns contain no matching gate payload or task marker.

Resume validation without rewriting or clearing the draft. A new-chat route is context isolation, not storage isolation, but it does not erase verifiable Skill authorship.

If any condition fails, treat pre-input content as `PERSISTED_UNOWNED_DRAFT`. A matching marker, substring, visual similarity, route history, or current-task intent alone is insufficient ownership evidence.

## Post-send phantom drafts

After exactly-once delivery is confirmed, unexpected composer text is `POST_SEND_PHANTOM_DRAFT`. Do not clear, overwrite, focus, or send it. It does not invalidate the already confirmed message or prevent reading its response. Observe it separately; if it disappears, record that fact. Before any later write, start the normal baseline/ownership protocol again. If the text persists into that next pre-input check without a qualifying `WRITTEN` record, it is `PERSISTED_UNOWNED_DRAFT`.
