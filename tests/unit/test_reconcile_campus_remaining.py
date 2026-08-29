"""Pin the 2026-08-29 production bug: the coach recommended the very session
the athlete had just completed, because campus_remaining was built from
DynamoDB statuses read before the parallel content branch marked the matched
session done. reconcile_campus_remaining() must remove the matched session
from the remaining view."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambda_functions"))

from processing.coach_generator import reconcile_campus_remaining  # noqa: E402


def _overview(titles, running_count=None):
    return {
        "campus_remaining": {
            "count": len(titles),
            "running_count": running_count if running_count is not None else len(titles),
            "titles": list(titles),
        }
    }


class TestReconcileCampusRemaining:
    def test_removes_matched_running_session(self):
        # The 2026-08-29 case: activity matched 'Sortie Longue & Active'
        # while the stale remaining list still contained it.
        wo = _overview(["Renforcement", "Sortie Longue & Active"], running_count=1)
        matched = {"title": "Sortie Longue & Active", "sport": "running"}
        assert reconcile_campus_remaining(wo, matched) is True
        rem = wo["campus_remaining"]
        assert rem["titles"] == ["Renforcement"]
        assert rem["count"] == 1
        assert rem["running_count"] == 0

    def test_ppg_session_does_not_touch_running_count(self):
        wo = _overview(["Renforcement", "Endurance Fondamentale"], running_count=1)
        matched = {"title": "Renforcement", "sport": "ppg"}
        assert reconcile_campus_remaining(wo, matched) is True
        rem = wo["campus_remaining"]
        assert rem["titles"] == ["Endurance Fondamentale"]
        assert rem["count"] == 1
        assert rem["running_count"] == 1

    def test_noop_when_session_already_marked_done(self):
        # Statuses were fresh: the matched session is absent, nothing changes.
        wo = _overview(["Endurance Fondamentale"])
        matched = {"title": "Sortie Longue & Active", "sport": "running"}
        assert reconcile_campus_remaining(wo, matched) is False
        assert wo["campus_remaining"]["titles"] == ["Endurance Fondamentale"]
        assert wo["campus_remaining"]["count"] == 1

    def test_noop_on_missing_overview_or_remaining(self):
        assert reconcile_campus_remaining(None, {"title": "X"}) is False
        assert reconcile_campus_remaining({}, {"title": "X"}) is False

    def test_counts_never_go_negative(self):
        wo = {"campus_remaining": {"count": 0, "running_count": 0, "titles": ["Seuil 60"]}}
        matched = {"title": "Seuil 60", "sport": "running"}
        assert reconcile_campus_remaining(wo, matched) is True
        assert wo["campus_remaining"]["count"] == 0
        assert wo["campus_remaining"]["running_count"] == 0

    def test_removes_single_occurrence_only(self):
        # Two EF sessions planned the same week: only one is closed by the match.
        wo = _overview(["Endurance Fondamentale", "Endurance Fondamentale"])
        matched = {"title": "Endurance Fondamentale", "sport": "running"}
        assert reconcile_campus_remaining(wo, matched) is True
        assert wo["campus_remaining"]["titles"] == ["Endurance Fondamentale"]
        assert wo["campus_remaining"]["count"] == 1
