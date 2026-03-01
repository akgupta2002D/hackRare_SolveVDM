from pathlib import Path

import cv2

from floater_demo.supabase_worker import (
    SupabaseConfig,
    SupabaseWorker,
    infer_canvas_size,
    parse_svg_points,
    render_row_to_png,
)


def test_parse_svg_points_handles_move_and_line_commands() -> None:
    points = parse_svg_points("M 10 20 L 30 40 L 50 60")
    assert points == [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)]


def test_infer_canvas_size_uses_path_extents() -> None:
    width, height = infer_canvas_size(
        [{"d": "M 10 20 L 100 200"}, {"d": "M 150 250 L 175 300"}]
    )
    assert width >= 199
    assert height >= 324


def test_render_row_to_png_draws_paths(tmp_path: Path) -> None:
    row = {
        "canvas_width": 120,
        "canvas_height": 120,
        "paths": [
            {
                "d": "M 10 10 L 110 110",
                "opacity": 0.5,
                "strokeWidth": 5,
            }
        ],
    }
    output_path = render_row_to_png(row, tmp_path / "render.png")
    image = cv2.imread(str(output_path), cv2.IMREAD_GRAYSCALE)
    assert image is not None
    assert int(image.min()) < 245


def test_fetch_pending_rows_respects_incremental_mode(monkeypatch) -> None:
    config = SupabaseConfig(project_url="https://example.supabase.co", api_key="secret", write_mode="incremental")
    worker = SupabaseWorker(config, artifacts_dir=Path("/tmp/floater_demo_test"))

    captured_params = {}

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return []

    def fake_request(method: str, url: str, **kwargs):
        captured_params.update(kwargs.get("params", {}))
        return DummyResponse()

    monkeypatch.setattr(worker, "_request_with_retry", fake_request)
    worker.fetch_pending_rows(limit=5)

    assert captured_params["limit"] == "5"
    assert captured_params[config.analysed_at_column] == "is.null"


def test_fetch_pending_rows_omits_null_filter_in_overwrite_mode(monkeypatch) -> None:
    config = SupabaseConfig(project_url="https://example.supabase.co", api_key="secret", write_mode="overwrite_all")
    worker = SupabaseWorker(config, artifacts_dir=Path("/tmp/floater_demo_test"))

    captured_params = {}

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return []

    def fake_request(method: str, url: str, **kwargs):
        captured_params.update(kwargs.get("params", {}))
        return DummyResponse()

    monkeypatch.setattr(worker, "_request_with_retry", fake_request)
    worker.fetch_pending_rows(limit=5)

    assert captured_params["limit"] == "5"
    assert config.analysed_at_column not in captured_params
