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
        self.assertRegex(first, r"^[0-9a-f]{16}$")

    def test_task_marker_rejects_duplicate_marker_lines(self) -> None:
        with self.assertRaises(ValueError):
            composer_contract.compute_task_marker(
                "request",
                "CODEX_TASK_ID:first\nCODEX_TASK_ID:second\nbody",
            )

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
        prefix = "CODEX_TASK_ID:d9081fb63abb4925\n"
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

    def test_mixed_top_level_shapes_fail_closed(self) -> None:
        with self.assertRaises(composer_contract.ComposerTopologyError):
            composer_contract.canonicalize_composer_html("<p>alpha</p>beta")

    def test_unsupported_nested_blocks_fail_closed(self) -> None:
        for html in ("<blockquote><p>alpha</p></blockquote>", "<ul><li>alpha</li></ul>"):
            with self.subTest(html=html):
                with self.assertRaises(composer_contract.ComposerTopologyError):
                    composer_contract.canonicalize_composer_html(html)


if __name__ == "__main__":
    unittest.main()
