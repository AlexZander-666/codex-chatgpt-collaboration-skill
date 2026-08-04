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
            "Visible text alone is insufficient",
            "current conversation's visible model control",
            "Do not inherit model evidence from a prior conversation",
            "Confirm that the exact payload appears once in canonical user-authored conversation turns",
            "Do not depend on a single transient status string",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill_text)

    def test_interaction_recovery_states_are_complete(self) -> None:
        required_states = {
            "INPUT_UNREADY",
            "INPUT_READY",
            "SEND_ATTEMPTED",
            "SEND_CONFIRMED",
            "SEND_UNKNOWN",
            "SEND_RETRY_READY",
            "FALLBACK_ATTEMPTED",
            "FALLBACK_UNKNOWN",
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
        self.assertIn("matching message appears more than once", self.workflow_text)

    def test_transition_graph_supports_success_and_recovery_traces(self) -> None:
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
            "Never clear, replace, or submit any other draft",
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
            "Composer-readiness evidence",
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
