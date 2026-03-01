from __future__ import annotations

from pathlib import Path

from floater_demo.closed_loop import run_closed_loop


def test_closed_loop_smoke(tmp_path: Path) -> None:
    payload = run_closed_loop(
        outdir=tmp_path / "closed_loop",
        rounds=1,
        seed=42,
        n_per_suite=2,
        apply_updates=False,
    )

    assert payload["rounds_completed"] == 1
    summary_path = tmp_path / "closed_loop" / "closed_loop_summary.json"
    report_path = tmp_path / "closed_loop" / "round_00" / "report.json"
    confusion_path = tmp_path / "closed_loop" / "round_00" / "confusion.csv"
    confusion_json_path = tmp_path / "closed_loop" / "round_00" / "confusion_matrix.json"
    confusion_png_path = tmp_path / "closed_loop" / "round_00" / "confusion_matrix.png"
    presentation_metrics_path = tmp_path / "closed_loop" / "round_00" / "presentation_metrics.json"

    assert summary_path.exists()
    assert report_path.exists()
    assert confusion_path.exists()
    assert confusion_json_path.exists()
    assert confusion_png_path.exists()
    assert presentation_metrics_path.exists()
