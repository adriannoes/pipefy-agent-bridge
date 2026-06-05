"""Offline tests for eval/capture_scenario_baseline.py."""

from __future__ import annotations

from typing import Any

import pytest

from eval.capture_scenario_baseline import (
    CardRecord,
    build_stale_cards_baseline,
    build_summary_baseline,
    capture_scenario_baseline,
    card_record_from_node,
)


def test_card_record_from_node_maps_phase_and_assignees() -> None:
    record = card_record_from_node(
        {
            "id": "123",
            "title": "Example card",
            "done": False,
            "createdAt": "2026-01-10T12:00:00Z",
            "current_phase": {"name": "Submitted"},
            "current_phase_age": 900_000,
            "assignees": [{"name": "Alex Demo"}],
        }
    )
    assert record is not None
    assert record.card_id == "123"
    assert record.phase_name == "Submitted"
    assert record.phase_age_seconds == 900_000
    assert record.assignee_names == ("Alex Demo",)


def test_build_stale_cards_baseline_filters_by_phase_and_age() -> None:
    cards = [
        CardRecord(
            card_id="1",
            title="Fresh in phase",
            done=False,
            created_at="2026-06-01T00:00:00Z",
            phase_name="Submitted",
            phase_age_seconds=86_400,
            assignee_names=(),
        ),
        CardRecord(
            card_id="2",
            title="Stale in phase",
            done=False,
            created_at="2026-01-01T00:00:00Z",
            phase_name="Submitted",
            phase_age_seconds=900_000,
            assignee_names=(),
        ),
        CardRecord(
            card_id="3",
            title="Wrong phase",
            done=False,
            created_at="2026-01-01T00:00:00Z",
            phase_name="Done",
            phase_age_seconds=900_000,
            assignee_names=(),
        ),
    ]
    baseline = build_stale_cards_baseline(
        pipe_id="900000101",
        phase_name="Submitted",
        cards=cards,
    )
    assert baseline["stale_count"] == 1
    assert baseline["stale_cards"] == [{"id": "2", "title": "Stale in phase"}]


def test_build_summary_baseline_selects_newest_open_cards() -> None:
    cards = [
        CardRecord(
            card_id="1",
            title="Older open",
            done=False,
            created_at="2026-01-01T00:00:00Z",
            phase_name="Submitted",
            phase_age_seconds=1,
            assignee_names=(),
        ),
        CardRecord(
            card_id="2",
            title="Newest open",
            done=False,
            created_at="2026-06-01T00:00:00Z",
            phase_name="In Progress",
            phase_age_seconds=1,
            assignee_names=("Alex",),
        ),
        CardRecord(
            card_id="3",
            title="Done card",
            done=True,
            created_at="2026-06-02T00:00:00Z",
            phase_name="Done",
            phase_age_seconds=1,
            assignee_names=(),
        ),
    ]
    baseline = build_summary_baseline(pipe_id="900000101", cards=cards, max_cards=2)
    assert baseline["card_count"] == 2
    assert [row["title"] for row in baseline["cards"]] == ["Newest open", "Older open"]


def test_capture_scenario_baseline_uses_injected_graphql_runner() -> None:
    pages: list[dict[str, Any]] = [
        {
            "cards": {
                "edges": [
                    {
                        "node": {
                            "id": "10",
                            "title": "Stale card",
                            "done": False,
                            "createdAt": "2026-01-01T00:00:00Z",
                            "current_phase": {"name": "Review"},
                            "current_phase_age": 900_000,
                            "assignees": [],
                        }
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
    ]

    def fake_runner(
        query: str,
        *,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del query, variables
        return pages.pop(0)

    baseline = capture_scenario_baseline(
        "stale_cards",
        pipe_id="900000101",
        phase_name="Review",
        graphql_runner=fake_runner,
    )
    assert baseline["stale_count"] == 1
    assert baseline["stale_cards"][0]["title"] == "Stale card"


def test_capture_scenario_baseline_requires_phase_name_for_stale_cards() -> None:
    with pytest.raises(ValueError, match=r"phase_name is required"):
        capture_scenario_baseline("stale_cards", pipe_id="900000101", phase_name=None)
