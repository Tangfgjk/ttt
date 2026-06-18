from types import SimpleNamespace

from app.services.active_learning_service import (
    ActiveLearningService,
    _portable_checkpoint_path,
    _resolve_checkpoint_path,
)


def _run(run_id, question_ids, *, active_learning_round=None):
    return SimpleNamespace(
        id=run_id,
        params_json=(
            {"active_learning_round": active_learning_round}
            if active_learning_round is not None
            else {}
        ),
        metrics_json={},
        recommendation_batch=SimpleNamespace(
            items=[SimpleNamespace(question_id=question_id) for question_id in question_ids]
        ),
    )


def test_round_map_for_runs_returns_mapping() -> None:
    service = ActiveLearningService.__new__(ActiveLearningService)

    round_map = service._round_map_for_runs(
        [
            _run(1, [10, 20, 30], active_learning_round=2),
            _run(2, [10, 20, 30]),
            _run(3, [40, 50]),
        ]
    )

    assert round_map == {1: 2, 2: 2, 3: 3}


def test_checkpoint_path_helpers_use_configured_artifact_root(tmp_path) -> None:
    checkpoint_root = tmp_path / "active_learning"
    checkpoint_root.mkdir()
    checkpoint = checkpoint_root / "train_202606180001_abcd.pth"
    checkpoint.write_bytes(b"checkpoint")

    missing_windows_path = (
        r"C:\Users\29694\Desktop\ttt\backend\artifacts\active_learning"
        r"\train_202606180001_abcd.pth"
    )

    resolved = _resolve_checkpoint_path(
        missing_windows_path,
        checkpoint_dir=str(checkpoint_root),
    )
    portable = _portable_checkpoint_path(
        str(checkpoint),
        checkpoint_dir=str(checkpoint_root),
    )

    assert resolved == str(checkpoint)
    assert portable == "artifacts/active_learning/train_202606180001_abcd.pth"
