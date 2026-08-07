from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
SKILL = REPOSITORY / "skills" / "codex-chatgpt-collaboration"


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        cls.workflow_text = (SKILL / "references" / "workflow.md").read_text(encoding="utf-8")
        cls.composer_text = (SKILL / "references" / "composer-contract.md").read_text(encoding="utf-8")
        cls.report_text = (SKILL / "references" / "report-template.md").read_text(encoding="utf-8")
        cls.openai_text = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")

    def parse_transitions(self) -> dict[str, set[str]]:
        block = re.search(
            r"<!-- CONTRACT_TRANSITIONS_START -->\s*```text\s*(.*?)\s*```\s*<!-- CONTRACT_TRANSITIONS_END -->",
            self.workflow_text,
            re.DOTALL,
        )
        self.assertIsNotNone(block)
        assert block is not None
        transitions: dict[str, set[str]] = {}
        for line in block.group(1).splitlines():
            source, targets = (part.strip() for part in line.split("->", 1))
            transitions[source] = {target.strip() for target in targets.split("|")}
        return transitions

    def assert_valid_trace(self, trace: list[str]) -> None:
        transitions = self.parse_transitions()
        for source, target in zip(trace, trace[1:]):
            self.assertIn(target, transitions[source], f"invalid transition: {source} -> {target}")

    def test_frontmatter_contains_only_supported_fields(self) -> None:
        _, frontmatter, _ = self.skill_text.split("---", 2)
        keys = {
            line.split(":", 1)[0].strip()
            for line in frontmatter.splitlines()
            if line.strip() and not line.startswith((" ", "\t"))
        }
        self.assertEqual(keys, {"name", "description"})
        self.assertIn("name: codex-chatgpt-collaboration", frontmatter)

    def test_all_local_markdown_references_resolve(self) -> None:
        references = re.findall(r"\[[^]]+\]\(([^)]+)\)", self.skill_text)
        local_references = [item for item in references if "://" not in item]
        self.assertTrue(local_references)
        for relative in local_references:
            with self.subTest(relative=relative):
                self.assertTrue((SKILL / relative).is_file())

    def test_implicit_invocation_policy_and_default_prompt(self) -> None:
        self.assertRegex(self.openai_text, r"(?m)^\s*allow_implicit_invocation:\s*true\s*$")
        self.assertIn("$codex-chatgpt-collaboration", self.openai_text)
        self.assertIn("submit exactly once", self.openai_text)
        self.assertNotIn("highest-tier", self.openai_text)
        description = re.search(
            r'(?m)^\s*short_description:\s*"([^"]+)"\s*$',
            self.openai_text,
        )
        self.assertIsNotNone(description)
        assert description is not None
        self.assertLessEqual(len(description.group(1)), 64)
        self.assertGreaterEqual(len(description.group(1)), 25)

    def test_skill_requires_current_accepted_input_and_model_evidence(self) -> None:
        for phrase in (
            "never use raw `innerText` or `textContent` equality",
            "current conversation's visible model control",
            "Do not inherit model evidence from a prior conversation",
            "Confirm that the exact payload appears once in canonical user-authored conversation turns",
            "Do not depend on a single transient status string",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill_text)

    def test_interaction_recovery_states_are_complete(self) -> None:
        required_states = {
            "BASELINE_UNSET",
            "BASELINE_STABLE",
            "SAME_TASK_SKILL_DRAFT",
            "MANAGED_TASK_DRAFT",
            "MANAGED_TASK_DRAFT_RESET",
            "STALE_CODEX_DRAFT",
            "STALE_CODEX_DRAFT_RESET",
            "PERSISTED_UNOWNED_DRAFT",
            "DRAFT_RESET_AUTHORIZED",
            "INPUT_UNREADY",
            "DRAFT_CONTAMINATED",
            "INPUT_READY",
            "SEND_ATTEMPTED",
            "SEND_CONFIRMED",
            "SEND_UNKNOWN",
            "SEND_RETRY_READY",
            "FALLBACK_ATTEMPTED",
            "FALLBACK_UNKNOWN",
            "POST_SEND_PHANTOM_DRAFT",
            "RESPONSE_OBSERVED",
            "CONTENT_VERIFIED",
        }
        for state in required_states:
            with self.subTest(state=state):
                self.assertIn(f"`{state}`", self.workflow_text)
        self.assertIn(
            "Never transition directly from `SEND_UNKNOWN` to `SEND_ATTEMPTED`",
            self.workflow_text,
        )
        self.assertIn("exactly once", self.workflow_text)
        self.assertIn("confirmed absent", self.workflow_text)
        self.assertIn(
            "three canonical absence reads span at least five seconds",
            self.workflow_text,
        )
        self.assertIn("cannot create a server idempotency key", self.workflow_text)
        self.assertIn("matching message appears more than once", self.workflow_text)

    def test_transition_graph_supports_success_and_recovery_traces(self) -> None:
        self.assert_valid_trace(
            [
                "BASELINE_UNSET",
                "BASELINE_STABLE",
                "INPUT_UNREADY",
                "INPUT_READY",
                "SEND_ATTEMPTED",
                "SEND_CONFIRMED",
                "RESPONSE_OBSERVED",
                "CONTENT_VERIFIED",
            ]
        )
        self.assert_valid_trace(
            [
                "INPUT_UNREADY",
                "INPUT_READY",
                "SEND_ATTEMPTED",
                "SEND_CONFIRMED",
                "RESPONSE_OBSERVED",
                "CONTENT_VERIFIED",
            ]
        )
        self.assert_valid_trace(
            [
                "INPUT_UNREADY",
                "INPUT_READY",
                "SEND_ATTEMPTED",
                "SEND_UNKNOWN",
                "SEND_CONFIRMED",
                "RESPONSE_OBSERVED",
                "CONTENT_VERIFIED",
            ]
        )

    def test_transition_graph_supports_same_task_draft_resume(self) -> None:
        self.assert_valid_trace(
            [
                "BASELINE_UNSET",
                "SAME_TASK_SKILL_DRAFT",
                "INPUT_READY",
                "SEND_ATTEMPTED",
                "SEND_CONFIRMED",
                "POST_SEND_PHANTOM_DRAFT",
                "RESPONSE_OBSERVED",
                "CONTENT_VERIFIED",
            ]
        )

    def test_transition_graph_resets_stale_codex_draft_for_new_task(self) -> None:
        self.assert_valid_trace(
            [
                "BASELINE_UNSET",
                "STALE_CODEX_DRAFT",
                "STALE_CODEX_DRAFT_RESET",
                "BASELINE_UNSET",
                "BASELINE_STABLE",
                "INPUT_UNREADY",
                "INPUT_READY",
            ]
        )
        transitions = self.parse_transitions()
        self.assertNotIn("INPUT_READY", transitions["STALE_CODEX_DRAFT"])
        self.assertNotIn("SEND_ATTEMPTED", transitions["STALE_CODEX_DRAFT"])

    def test_reserved_tab_residual_draft_is_reset_before_input(self) -> None:
        self.assert_valid_trace(
            [
                "BASELINE_UNSET",
                "MANAGED_TASK_DRAFT",
                "MANAGED_TASK_DRAFT_RESET",
                "BASELINE_UNSET",
                "BASELINE_STABLE",
                "INPUT_UNREADY",
                "INPUT_READY",
            ]
        )
        transitions = self.parse_transitions()
        self.assertNotIn("INPUT_READY", transitions["MANAGED_TASK_DRAFT"])
        self.assertNotIn("SEND_ATTEMPTED", transitions["MANAGED_TASK_DRAFT"])
        for phrase in (
            "record it as `SKILL_RESERVED_TAB`",
            "zero canonical user turns",
            "must never be inferred from the ChatGPT domain",
            "do not claim or relabel a user's shared/manual tab",
            "Revalidate the reserved-tab identity immediately before the semantic clear",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.workflow_text + self.skill_text)

    def test_unowned_draft_cannot_be_relabelled_or_auto_cleared(self) -> None:
        transitions = self.parse_transitions()
        self.assertEqual(
            transitions["PERSISTED_UNOWNED_DRAFT"],
            {"DRAFT_RESET_AUTHORIZED", "BLOCKED"},
        )
        self.assertNotIn("SAME_TASK_SKILL_DRAFT", transitions["PERSISTED_UNOWNED_DRAFT"])
        self.assertNotIn("STALE_CODEX_DRAFT_RESET", transitions["PERSISTED_UNOWNED_DRAFT"])
        self.assertIn("Never create or backfill a `WRITTEN` record", self.composer_text)

    def test_new_task_epoch_expires_prior_draft_provenance(self) -> None:
        for phrase in (
            "Every new Codex user task starts a new task epoch",
            "Discard all prior in-memory draft provenance",
            "never resumed merely because its marker, hash, body, or prior provenance is known",
            "This exception exists only for interruption recovery inside the current Codex task",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.composer_text)

    def test_stale_codex_reset_is_narrow_and_one_shot(self) -> None:
        for phrase in (
            "zero attachments",
            "zero canonical user turns",
            "legacy Codex task envelope without a fingerprint",
            "perform one `STALE_CODEX_DRAFT_RESET` action",
            "It must never clear a same-task recovery draft, arbitrary user prose",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.composer_text)

    def test_multiline_editor_contract_is_dom_representation_independent(self) -> None:
        for phrase in (
            "Replace `CRLF` with `LF`",
            "Do not trim, collapse whitespace, normalize Unicode",
            "join adjacent blocks with exactly one `LF`",
            "Reconstruct canonical ATX heading markers",
            "join every other adjacent top-level rich block with two `LF` characters",
            "ignore an editor-owned trailing sentinel",
            "Raw `innerText` and `textContent` lengths may be recorded for diagnostics only",
            "UTF-8 SHA-256",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.composer_text)

        examples = {
            "<p>alpha</p>": "alpha",
            "<p>alpha</p><p>beta</p>": "alpha\nbeta",
            '<p>alpha</p><p><br class="ProseMirror-trailingBreak"></p><p>beta</p>': "alpha\n\nbeta",
            "<p>alpha<br>beta</p>": "alpha\nbeta",
        }
        for dom, expected in examples.items():
            with self.subTest(dom=dom):
                rendered = expected.replace("\n", "\\n")
                self.assertIn(f"| `{rendered}` |", self.composer_text)

    def test_provenance_requires_write_ahead_and_zero_send_actions(self) -> None:
        for phrase in (
            "Immediately before the first semantic write",
            "state `PREPARED`",
            "promote the record to `WRITTEN` only when",
            "no send action has been issued",
            "canonical user-authored turns contain no matching",
            "Resume validation without rewriting or clearing",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.composer_text)

    def test_post_send_phantom_draft_does_not_invalidate_confirmed_send(self) -> None:
        self.assertIn("After exactly-once delivery is confirmed", self.composer_text)
        self.assertIn("does not invalidate the already confirmed message", self.composer_text)
        transitions = self.parse_transitions()
        self.assertIn("POST_SEND_PHANTOM_DRAFT", transitions["SEND_CONFIRMED"])
        self.assertNotIn("INPUT_READY", transitions["POST_SEND_PHANTOM_DRAFT"])
        self.assert_valid_trace(
            [
                "INPUT_UNREADY",
                "INPUT_READY",
                "SEND_ATTEMPTED",
                "SEND_UNKNOWN",
                "SEND_RETRY_READY",
                "FALLBACK_ATTEMPTED",
                "SEND_CONFIRMED",
                "RESPONSE_OBSERVED",
                "CONTENT_VERIFIED",
            ]
        )

    def test_transition_graph_forbids_blind_retry(self) -> None:
        transitions = self.parse_transitions()
        self.assertNotIn("SEND_ATTEMPTED", transitions["SEND_UNKNOWN"])
        self.assertIn("FALLBACK_ATTEMPTED", transitions["SEND_RETRY_READY"])

    def test_transition_graph_forbids_a_second_fallback(self) -> None:
        transitions = self.parse_transitions()
        self.assertNotIn("SEND_RETRY_READY", transitions["FALLBACK_ATTEMPTED"])
        self.assertNotIn("SEND_RETRY_READY", transitions["FALLBACK_UNKNOWN"])
        self.assertNotIn("FALLBACK_ATTEMPTED", transitions["FALLBACK_UNKNOWN"])
        self.assert_valid_trace(
            [
                "INPUT_UNREADY",
                "INPUT_READY",
                "SEND_ATTEMPTED",
                "SEND_UNKNOWN",
                "SEND_RETRY_READY",
                "FALLBACK_ATTEMPTED",
                "FALLBACK_UNKNOWN",
                "SEND_CONFIRMED",
                "RESPONSE_OBSERVED",
                "CONTENT_VERIFIED",
            ]
        )

    def test_contract_scopes_ownership_roles_and_wait_bounds(self) -> None:
        for phrase in (
            "Canonical message evidence counts only user-authored conversation turns",
            "Do not loop on tabs, clear site storage",
            "finite deadline or maximum recheck count",
            "two consecutive content reads separated by a state recheck are identical",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.workflow_text)

    def test_completion_contract_uses_structural_evidence(self) -> None:
        for phrase in (
            "assistant response exists",
            "generation has ended",
            "two consecutive content reads separated by a state recheck are identical and readable",
            "must not be the sole completion test",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.workflow_text)

    def test_report_keeps_runtime_evidence_separate(self) -> None:
        for field in (
            "Pre-input baseline",
            "Task epoch",
            "Persisted-draft handling",
            "Payload canonicalization",
            "Composer-readiness evidence",
            "Post-send composer anomaly",
            "Send evidence",
            "Ambiguous-send recovery",
            "Completion evidence",
            "Composer ownership",
            "Wait bounds",
        ):
            with self.subTest(field=field):
                self.assertIn(field, self.report_text)


if __name__ == "__main__":
    unittest.main()
