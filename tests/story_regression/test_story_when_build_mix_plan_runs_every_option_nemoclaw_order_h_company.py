"""Generated story-backed regression tests.

This file is deterministic and safe to run without LLM/cloud credentials.
"""
import hashlib
from pathlib import Path
import re
import unittest

PDD_STORY_ID = "when_build_mix_plan_runs_every_option_nemoclaw_order_h_company"
PDD_STORY_HASH = "a15888d1480084e4"
STORY_PATH = Path(__file__).resolve().parent / "../../user_stories/story__when_build_mix_plan_runs_every_option_nemoclaw_order_h_company.md"
CONTRACT_PATH = Path(__file__).resolve().parent / "../../user_stories/contracts/when_build_mix_plan_runs_every_option_nemoclaw_order_h_company.contract.md"


class _StoryMark:
    """Keep PDD's AST marker without adding pytest as a project dependency."""

    @staticmethod
    def story(**_metadata):
        return lambda function: function


class _PytestCompatibility:
    mark = _StoryMark()


pytest = _PytestCompatibility()


def _story_bundle() -> str:
    story = STORY_PATH.read_text(encoding="utf-8")
    if CONTRACT_PATH is not None and CONTRACT_PATH.exists():
        return story + "\n\n" + CONTRACT_PATH.read_text(encoding="utf-8")
    return story


def _bundle_hash() -> str:
    # Mirror PDD's small canonical primitive locally so the repository's
    # stdlib-only test lane does not need PDD installed in its virtualenv.
    metadata = re.compile(
        r"<!--\s*pdd-story-(?:prompts|dev-units):.*?\s*-->",
        flags=re.IGNORECASE,
    )

    def normalized(text: str) -> str:
        without_metadata = metadata.sub("", text)
        lines = [line.rstrip() for line in without_metadata.strip().splitlines()]
        return "\n".join(line for line in lines if line.strip())

    story = normalized(STORY_PATH.read_text(encoding="utf-8"))
    if CONTRACT_PATH.exists():
        story += "\n\n" + normalized(CONTRACT_PATH.read_text(encoding="utf-8"))
    return hashlib.sha256(story.encode("utf-8")).hexdigest()[:16]


@pytest.mark.story(story_id=PDD_STORY_ID)
def test_story_when_build_mix_plan_runs_every_option_nemoclaw_order_h_company_r1_r2_r3_oracle_contract():
    assert _bundle_hash() == PDD_STORY_HASH
    expected = [
    'These details matter for pass/fail:',
    'The observable output of Build mix plan includes a previewable ordered track list before Start mix.',
    'The planned order is allowed to differ from input selection order; validation must fail if the system treats selection order as mandatory playback order.',
    'For a normal full-set plan, each selected track is present once and only once in the planned sequence.',
    'The same reorder freedom applies across the named modes in scope: NemoClaw order, H Company order, and Feel only.',
    'Planning succeeds without requiring an LLM for mix-quality ordering itself.',
    'In H Company planning-only operation, no local desktop bridge startup or dependency is triggered.'
]
    bundle = _story_bundle()
    assert expected, "story has no Oracle or Acceptance Criteria clauses"
    for clause in expected:
        assert clause in bundle


@pytest.mark.story(story_id=PDD_STORY_ID)
def test_story_when_build_mix_plan_runs_every_option_nemoclaw_order_h_company_negative_cases():
    assert _bundle_hash() == PDD_STORY_HASH
    expected = [
    'Treating the order in which tracks were selected as a required final playback order.',
    'Dropping a selected track, duplicating a selected track, or otherwise failing to include each selected track exactly once in a normal full-set plan.',
    'Producing no previewable order before Start mix.',
    'Requiring an LLM in order to perform mix-quality ordering.',
    'Starting or requiring a local desktop bridge for H Company planning-only ordering.',
    'Allowing one of the named modes to bypass reordering and simply preserve selection order by default when reordering is needed for the mix.'
]
    bundle = _story_bundle()
    for clause in expected:
        assert clause in bundle


class StoryRegressionTest(unittest.TestCase):
    """Expose PDD's deterministic story checks to the repository test lane."""

    def test_oracle_contract(self) -> None:
        test_story_when_build_mix_plan_runs_every_option_nemoclaw_order_h_company_r1_r2_r3_oracle_contract()

    def test_negative_cases(self) -> None:
        test_story_when_build_mix_plan_runs_every_option_nemoclaw_order_h_company_negative_cases()
