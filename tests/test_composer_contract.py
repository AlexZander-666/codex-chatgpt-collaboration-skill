from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    REPOSITORY
    / "skills"
    / "codex-chatgpt-collaboration"
    / "scripts"
    / "composer_contract.py"
)
SPEC = importlib.util.spec_from_file_location("composer_contract", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
composer_contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(composer_contract)


class ComposerContractTests(unittest.TestCase):
    @staticmethod
    def task_envelope(marker: str = "0123456789abcdef") -> str:
        sections = "\n\n".join(
            f"{heading}\ncontent"
            for heading in composer_contract.TASK_HEADINGS
        )
        return (
            f"{composer_contract.TASK_PREAMBLE}\n\n"
            f"CODEX_TASK_ID:{marker}\n\n"
            f"{sections}"
        )

    def test_transport_normalizes_only_line_endings(self) -> None:
        source = "标题\r\nCafe\u0301  \r最后"
        self.assertEqual(
            composer_contract.canonicalize_transport(source),
            "标题\nCafe\u0301  \n最后",
        )

    def test_task_marker_omits_existing_marker_line_without_circularity(self) -> None:
        request = "审查 NC-MARD\r\n保持证据边界"
        envelope_without_marker = "## Objective\r\n终审\r\n"
        first = composer_contract.compute_task_marker(request, envelope_without_marker)
        envelope_with_marker = (
            f"CODEX_TASK_ID:{first}\n" + composer_contract.canonicalize_transport(envelope_without_marker)
        )
        second = composer_contract.compute_task_marker(request, envelope_with_marker)
        self.assertEqual(first, second)
        fingerprint = composer_contract.compute_draft_fingerprint(envelope_with_marker)
        envelope_with_fingerprint = envelope_with_marker.replace(
            f"CODEX_TASK_ID:{first}",
            f"CODEX_TASK_ID:{first}\nCODEX_DRAFT_SHA256:{fingerprint}",
            1,
        )
        third = composer_contract.compute_task_marker(request, envelope_with_fingerprint)
        self.assertEqual(first, third)
        self.assertRegex(first, r"^[0-9a-f]{16}$")

    def test_task_marker_rejects_duplicate_marker_lines(self) -> None:
        with self.assertRaises(ValueError):
            composer_contract.compute_task_marker(
                "request",
                "CODEX_TASK_ID:first\nCODEX_TASK_ID:second\nbody",
            )

    def test_fingerprinted_task_draft_is_self_verifying(self) -> None:
        legacy = self.task_envelope()
        fingerprint = composer_contract.compute_draft_fingerprint(legacy)
        draft = legacy.replace(
            "CODEX_TASK_ID:0123456789abcdef",
            "CODEX_TASK_ID:0123456789abcdef\n"
            f"CODEX_DRAFT_SHA256:{fingerprint}",
            1,
        )
        self.assertEqual(composer_contract.classify_stale_codex_draft(draft), "fingerprinted-task")
        self.assertIsNone(composer_contract.classify_stale_codex_draft(draft + "tampered"))

    def test_legacy_reported_draft_is_recognized_for_reset(self) -> None:
        self.assertEqual(
            composer_contract.classify_stale_codex_draft(self.task_envelope()),
            "legacy-task",
        )

    def test_live_legacy_shape_marker_first_and_optional_evidence_heading(self) -> None:
        headings = [
            heading
            for heading in composer_contract.TASK_HEADINGS
            if heading != "## Evidence already available"
        ]
        sections = "\n\n".join(f"{heading}\ncontent" for heading in headings)
        live_shape = (
            "CODEX_TASK_ID:0123456789abcdef\n\n"
            "You are an external scientific, software-testing, and patent-strategy reviewer. "
            "Do not perform local actions. Audit a frozen method identity.\n\n"
            f"{sections}"
        )
        self.assertEqual(
            composer_contract.classify_stale_codex_draft(live_shape),
            "legacy-task",
        )

    def test_legacy_shape_rejects_extra_top_matter(self) -> None:
        legacy = self.task_envelope()
        self.assertIsNone(
            composer_contract.classify_stale_codex_draft("unexpected\n" + legacy)
        )

    def test_fixed_connection_draft_is_recognized_for_reset(self) -> None:
        self.assertEqual(
            composer_contract.classify_stale_codex_draft(composer_contract.CONNECTION_PAYLOAD),
            "connection",
        )

    def test_partial_or_user_draft_is_not_auto_resettable(self) -> None:
        for text in (
            "ordinary user draft",
            "CODEX_TASK_ID:0123456789abcdef",
            f"{composer_contract.TASK_PREAMBLE}\nCODEX_TASK_ID:0123456789abcdef",
            self.task_envelope().replace("## Boundaries", "## Missing boundary"),
            self.task_envelope() + "\nCODEX_UNKNOWN:unexpected",
        ):
            with self.subTest(text=text[:40]):
                self.assertIsNone(composer_contract.classify_stale_codex_draft(text))

    def test_fingerprint_must_immediately_follow_marker(self) -> None:
        legacy = self.task_envelope()
        fingerprint = composer_contract.compute_draft_fingerprint(legacy)
        misplaced = legacy + f"\nCODEX_DRAFT_SHA256:{fingerprint}"
        self.assertIsNone(composer_contract.classify_stale_codex_draft(misplaced))

    def test_prosemirror_paragraphs_preserve_lines_and_blank_lines(self) -> None:
        html = (
            "<p>alpha</p><p>beta</p>"
            '<p><br class="ProseMirror-trailingBreak"></p>'
            "<p>gamma<br>delta</p>"
        )
        self.assertEqual(
            composer_contract.canonicalize_composer_html(html),
            "alpha\nbeta\n\ngamma\ndelta",
        )

    def test_7071_code_point_envelope_survives_paragraph_serialization(self) -> None:
        prefix = "CODEX_TASK_ID:0123456789abcdef\n"
        line = "NC-MARD 终审约束与验收证据。"
        payload = prefix + (line + "\n") * 250
        payload += "x" * (7071 - len(payload))
        self.assertEqual(len(payload), 7071)

        html = "".join(
            f"<p>{part}</p>" if part else '<p><br class="ProseMirror-trailingBreak"></p>'
            for part in payload.split("\n")
        )
        observed = composer_contract.canonicalize_composer_html(html)
        self.assertEqual(observed, payload)
        self.assertEqual(
            composer_contract.utf8_sha256(observed),
            composer_contract.utf8_sha256(payload),
        )

    def test_live_rich_markdown_dom_reconstructs_exact_task_envelope(self) -> None:
        payload = (
            f"{composer_contract.TASK_PREAMBLE}\n\n"
            "CODEX_TASK_ID:a3798d24b39f93fb\n"
            "CODEX_DRAFT_SHA256:"
            "8b2dff76fdc6b2f19134b7c1172e71e133563acd04e1da44408f7b7cb4c04781\n\n"
            "## Objective\n"
            "Validate the live editor representation.\n\n"
            "## Verified context\n"
            "- First fact.\n\n"
            "## Boundaries\n"
            "- Preserve Unicode: 中文 ✅.\n\n"
            "## Evidence already available\n"
            "- Connection returned CONNECTION_OK.\n\n"
            "## Questions\n"
            "1. Is the envelope complete?\n"
            "2. Is its order preserved?\n\n"
            "## Deliverables\n"
            "- Return one token.\n\n"
            "## Acceptance criteria\n"
            "- No formatting."
        )
        html = (
            "<p><span>You are an external research and design adviser. "
            "Do not perform local actions.</span></p>"
            "<p><span>CODEX_TASK_ID</span><span>:a3798d24b39f93fb</span><br>"
            "<span>CODEX_DRAFT_SHA256:"
            "8b2dff76fdc6b2f19134b7c1172e71e133563acd04e1da44408f7b7cb4c04781"
            "</span></p>"
            "<h2><span>Objective</span></h2>"
            "<p><span>Validate the live editor representation.</span></p>"
            "<h2><span>Verified context</span></h2>"
            '<ul data-spread="false"><li><p><span>First fact.</span></p></li></ul>'
            "<h2><span>Boundaries</span></h2>"
            '<ul><li><p><span>Preserve Unicode: 中文 ✅.</span></p></li></ul>'
            "<h2><span>Evidence already available</span></h2>"
            '<ul><li><p><span>Connection returned CONNECTION_OK.</span></p></li></ul>'
            "<h2><span>Questions</span></h2>"
            '<ol start="1"><li><p><span>Is the envelope complete?</span></p></li>'
            "<li><p><span>Is its order preserved?</span></p></li></ol>"
            "<h2><span>Deliverables</span></h2>"
            "<ul><li><p><span>Return one token.</span></p></li></ul>"
            "<h2><span>Acceptance criteria</span></h2>"
            "<ul><li><p><span>No formatting.</span></p></li></ul>"
        )
        observed = composer_contract.canonicalize_composer_html(html)
        self.assertEqual(observed, payload)
        self.assertEqual(
            composer_contract.utf8_sha256(observed),
            composer_contract.utf8_sha256(payload),
        )

    def test_ambiguous_rich_markdown_shapes_fail_closed(self) -> None:
        for html in (
            "<h2>Objective</h2><p><br></p><p>body</p>",
            "<h2>Objective</h2><ul><li><p>one</p><p>two</p></li></ul>",
            '<h2>Objective</h2><ol start="zero"><li>one</li></ol>',
        ):
            with self.subTest(html=html):
                with self.assertRaises(composer_contract.ComposerTopologyError):
                    composer_contract.canonicalize_composer_html(html)

    def test_semantic_inline_markdown_fails_closed(self) -> None:
        for html in (
            "<h2>Objective</h2><p><strong>bold</strong></p>",
            "<h2>Objective</h2><p><code>path</code></p>",
            '<h2>Objective</h2><p><a href="https://example.com">label</a></p>',
        ):
            with self.subTest(html=html):
                with self.assertRaises(composer_contract.ComposerTopologyError):
                    composer_contract.canonicalize_composer_html(html)

    def test_raw_url_autolink_is_reversible(self) -> None:
        html = (
            "<h2>Evidence</h2><p><span>Source: </span>"
            '<a href="https://example.com">https://example.com</a></p>'
        )
        self.assertEqual(
            composer_contract.canonicalize_composer_html(html),
            "## Evidence\nSource: https://example.com",
        )

    def test_mixed_top_level_shapes_fail_closed(self) -> None:
        with self.assertRaises(composer_contract.ComposerTopologyError):
            composer_contract.canonicalize_composer_html("<p>alpha</p>beta")

    def test_unsupported_nested_blocks_fail_closed(self) -> None:
        for html in ("<blockquote><p>alpha</p></blockquote>", "<table><tr><td>alpha</td></tr></table>"):
            with self.subTest(html=html):
                with self.assertRaises(composer_contract.ComposerTopologyError):
                    composer_contract.canonicalize_composer_html(html)


if __name__ == "__main__":
    unittest.main()
