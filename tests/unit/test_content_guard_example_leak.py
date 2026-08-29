"""Pin the 2026-08-29 production leak: the published description closed on
'Prochaine étape : la séance mix Force + Allure 42km !', copied verbatim from
the sparse-input few-shot example of the content prompt. No such session exists
in any Campus plan. The guard now flags prompt-example fingerprints so the
regeneration pass is told exactly what to rewrite."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambda_functions"))

from processing.content_guard import _check_prompt_example_leak, verify_content  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent.parent


class TestPromptExampleLeak:
    def test_prod_20260829_leak_is_flagged(self):
        content = {
            "description": (
                "Cette base longue se construit semaine après semaine. "
                "Prochaine sortie : session mix Force + Allure 42km !"
            )
        }
        problems = _check_prompt_example_leak(content)
        assert len(problems) == 1
        assert "force + allure 42" in problems[0]

    def test_leak_detection_is_case_insensitive(self):
        content = {"description": "Objectif : FORCE + ALLURE 42, on y va."}
        assert _check_prompt_example_leak(content)

    def test_clean_description_passes(self):
        content = {
            "description": (
                "Séance validée. Prochaine étape : la Sortie Longue & Active "
                "de dimanche prévue au plan."
            ),
            "title": "EF du matin",
        }
        assert _check_prompt_example_leak(content) == []
        assert verify_content(content, None, "") == []

    def test_leak_reaches_verify_content(self):
        # The check must drive the guard's regeneration, not just exist.
        content = {"description": "Fun fact : un escargot mettrait 6 jours ici."}
        problems = verify_content(content, None, "")
        assert any("prompt example leaked" in p for p in problems)

    def test_markers_are_absent_from_current_prompt_examples(self):
        # The prompt's own examples must not contain the leaking strings anymore:
        # the fingerprints exist to catch OLD deployed prompts and future leaks,
        # not to flag text the current prompt still teaches the model to write.
        prompt = (REPO_ROOT / "src" / "agents" / "embedded_prompts.py").read_text(
            encoding="utf-8"
        )
        assert "Force + Allure 42" not in prompt
