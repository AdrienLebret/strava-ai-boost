"""Pin the 2026-09-03 production bug: the published block ended with
"Prochaine séance : les 5 fractions au seuil qui t'attendent cette semaine"
while campus_remaining held two EF, one Renforcement and the Sortie Longue.
The threshold session had been done the day BEFORE (data was correct, session
marked done and matched); the model recycled its own note from yesterday and
projected it into the future. Narrative-only error, so the guard must read
the OUTPUT against the remaining sessions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambda_functions"))

from processing.coach_output_check import (  # noqa: E402
    _check_next_session,
    strip_false_claims,
    verify_weekly_claims,
)

# The real W36 state on 2026-09-03 after the seuil was done and marked.
WO = {
    "done_this_week": {"runs": 2, "run_km": 15.5, "muscu": 0, "strength": 0, "total": 2},
    "campus_remaining": {
        "count": 4,
        "running_count": 3,
        "titles": [
            "Endurance Fondamentale",
            "Renforcement",
            "Endurance Fondamentale",
            "Sortie Longue & Active",
        ],
    },
}


def _problems(text, overview=WO):
    return verify_weekly_claims({"strava_block": text}, overview, None, None)


class TestNextSessionVsRemaining:
    def test_prod_20260903_seuil_recycled_from_yesterday_is_flagged(self):
        # The exact published sentence: no threshold session remains in W36.
        text = (
            "Prochaine séance : les 5 fractions au seuil qui t'attendent cette "
            "semaine."
        )
        problems = _problems(text)
        assert any("'seuil'" in p for p in problems), problems

    def test_remaining_type_recommendation_passes(self):
        assert _problems("Prochaine séance : EF 40min pour absorber la charge.") == []
        assert _problems("Prochaine séance : ta sortie longue de 80 minutes.") == []

    def test_intense_work_inside_a_remaining_session_is_waived(self):
        # Titles do not carry the interval content: the Sortie Longue & Active
        # legitimately contains tempo blocks. Naming the remaining session waives.
        assert _problems(
            "Prochaine séance : ta sortie longue avec ses blocs tempo."
        ) == []

    def test_own_strength_program_stays_out_of_scope(self):
        # Upper A is the athlete's personal program, not a Campus session.
        assert _problems("Prochaine séance : Upper A de ton programme perso.") == []

    def test_sentence_without_next_marker_is_not_examined(self):
        # A recap of the DONE threshold session must never be flagged.
        assert _problems(
            "5 fractions au seuil hier, ton cardio a répondu fort."
        ) == []

    def test_abstains_without_titles(self):
        # No plan synced (or week fully done): the coach may propose its own next
        # workout, possibly intense. Abstain.
        no_plan = {"done_this_week": {"runs": 2}, "campus_remaining": {"titles": []}}
        assert _problems("Prochaine séance : du seuil pour progresser.", no_plan) == []
        assert _problems("Prochaine séance : du seuil pour progresser.", {}) == []

    def test_abstains_on_incomplete_counts(self):
        wo = dict(WO, counts_incomplete=True)
        assert _problems(
            "Prochaine séance : les fractions au seuil de la semaine.", wo
        ) == []

    def test_strip_removes_only_the_false_recommendation(self):
        feedback = {
            "strava_block": (
                "Cette semaine : 2 courses (15,5 km), soit 2 séances au total. "
                "Ta Zone 2 tient bien malgré la coupure. "
                "Prochaine séance : les 5 fractions au seuil qui t'attendent "
                "cette semaine."
            )
        }
        cleaned, removed = strip_false_claims(feedback, WO, None, None)
        assert len(removed) == 1 and "seuil" in removed[0], removed
        assert "Zone 2" in cleaned["strava_block"]
        assert "seuil" not in cleaned["strava_block"]

    def test_longue_alone_does_not_waive(self):
        # "une longue série" is not the Sortie Longue: the waiver needs the full
        # "sortie longue" marker, so the absent seuil still flags.
        problems = _check_next_session(
            "Prochaine séance : une longue série de fractions au seuil.", WO
        )
        assert any("'seuil'" in p for p in problems), problems
