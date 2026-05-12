from app.services.coreset_selection import CoresetCandidate, CoresetSelector


def test_kmeans_selection_scales_on_large_candidate_pool() -> None:
    selector = CoresetSelector(seed=42)
    candidates = [
        CoresetCandidate(question_id=index + 1, text=f"题目 {index + 1}")
        for index in range(5000)
    ]

    selections = selector.select(candidates, "kmeans", 20)

    assert len(selections) == 20
    assert len({item.question_id for item in selections}) == 20
    assert all(1 <= item.question_id <= 5000 for item in selections)


def test_full_pool_kmeans_prefers_embedding_mode() -> None:
    selector = CoresetSelector(seed=7)
    candidates = [
        CoresetCandidate(
            question_id=index + 1,
            text=f"候选题 {index + 1}",
            embedding=[1.0, 0.0, 0.0] if index < 4 else [0.0, 1.0, 0.0],
        )
        for index in range(8)
    ]

    progress_steps: list[tuple[int, int]] = []
    selections = selector.select_full_pool(
        candidates,
        "kmeans",
        2,
        progress_callback=lambda current, total: progress_steps.append((current, total)),
    )

    assert len(selections) == 2
    assert len({item.question_id for item in selections}) == 2
    assert progress_steps


def test_full_pool_hierarchical_strategies_record_cluster_summary() -> None:
    selector = CoresetSelector(seed=11)
    candidates = [
        CoresetCandidate(
            question_id=index + 1,
            text=f"cluster-a {index + 1}" if index < 6 else f"cluster-b {index + 1}",
            embedding=[1.0, 0.0, 0.0] if index < 6 else [0.0, 1.0, 0.0],
        )
        for index in range(12)
    ]

    for strategy in ("facility_location", "graph_cut", "moe"):
        progress_steps: list[tuple[int, int]] = []
        selections = selector.select_full_pool(
            candidates,
            strategy,
            3,
            progress_callback=lambda current, total: progress_steps.append((current, total)),
        )

        assert len(selections) == 3
        assert len({item.question_id for item in selections}) == 3
        assert progress_steps
        assert selector.last_summary["selection_mode"] == "hierarchical_full_pool"
        assert int(selector.last_summary["cluster_count"]) >= 3


def test_incremental_selection_uses_anchor_summary() -> None:
    selector = CoresetSelector(seed=23)
    anchors = [
        CoresetCandidate(question_id=100 + index, text=f"anchor {index}", embedding=[1.0, 0.0, 0.0])
        for index in range(4)
    ]
    candidates = [
        CoresetCandidate(
            question_id=index + 1,
            text=f"new {index + 1}",
            embedding=[0.0, 1.0, 0.0] if index < 4 else [0.0, 0.0, 1.0],
        )
        for index in range(8)
    ]

    progress_steps: list[tuple[int, int]] = []
    selections = selector.select_incremental(
        candidates,
        anchors,
        "facility_location",
        3,
        progress_callback=lambda current, total: progress_steps.append((current, total)),
    )

    assert len(selections) == 3
    assert len({item.question_id for item in selections}) == 3
    assert progress_steps
    assert selector.last_summary["selection_mode"] == "incremental_update"
    assert int(selector.last_summary["anchor_count"]) == len(anchors)
