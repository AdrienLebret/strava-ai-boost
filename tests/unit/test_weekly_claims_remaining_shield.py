"""Pin the 2026-08-24 production bug: 'Cette semaine : 2 courses (15,6km),
1 séance restante à faire' shipped unflagged because the remaining marker of
the SECOND claim shielded the FIRST one at sentence level. The shield is now
per-claim and forward-only: what precedes a remaining marker keeps its own
authority, what follows it describes the plan and is skipped."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambda_functions"))

from processing.coach_output_check import verify_weekly_claims  # noqa: E402

WO = {"done_this_week": {"runs": 1, "run_km": 7.8, "muscu": 0, "strength": 0, "total": 1}}


def _problems(text):
    return verify_weekly_claims({"strava_block": text}, WO, None, None)


class TestRemainingShieldPerClaim:
    def test_prod_20260824_wrong_count_before_remaining_is_flagged(self):
        # The exact production sentence: wrong done-claim, then a remaining clause.
        text = (
            "Cette semaine : 2 courses (15,6km), 1 séance restante à faire — la "
            "Sortie Longue & Active en fin de semaine pour compléter le plan."
        )
        problems = _problems(text)
        assert any("run count this week" in p for p in problems), problems
        assert any("kilometres this week" in p for p in problems), problems

    def test_pure_remaining_sentence_still_passes(self):
        # The historical trap that motivated the sentence-level gate: a count of
        # sessions still TO DO must not be compared against sessions done.
        assert _problems("Il te reste 3 courses cette semaine, accroche-toi.") == []

    def test_correct_recap_line_still_passes(self):
        assert _problems(
            "Cette semaine : 1 course (7,8 km), soit 1 séance au total."
        ) == []

    def test_remaining_clause_then_true_claim_passes(self):
        # Forward-only shield: a remaining clause silences what FOLLOWS it in the
        # segment, and a correct done-claim before it must not be flagged either.
        assert _problems(
            "Cette semaine : 1 course (7,8 km), encore 2 séances à faire au plan."
        ) == []

    def test_wrong_claim_after_remaining_clause_is_not_flagged(self):
        # Whatever follows a remaining marker describes the plan: even if its
        # figures do not match the done counts, it is not a done-claim.
        assert _problems(
            "Cette semaine il te reste 2 séances, dont 12 km de sortie longue."
        ) == []

    def test_decimal_comma_does_not_split_claims(self):
        # "15,6km" carries a decimal comma with no following space: the claim
        # boundary must not cut through it.
        problems = _problems("Cette semaine : 2 courses (15,6km) au compteur.")
        assert any("15.6" in p for p in problems), problems
