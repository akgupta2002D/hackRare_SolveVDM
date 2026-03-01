from pathlib import Path

import cv2

from floater_demo.supabase_worker import (
    SupabaseConfig,
    SupabaseWorker,
    apply_path_prior_to_instance,
    apply_vector_priors,
    build_path_priors,
    infer_canvas_size,
    parse_svg_points,
    path_bbox,
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
    assert captured_params["offset"] == "0"
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
    assert captured_params["offset"] == "0"
    assert config.analysed_at_column not in captured_params


def test_run_once_returns_processed_count_and_fetches_all_rows_in_overwrite_mode(monkeypatch, tmp_path: Path) -> None:
    config = SupabaseConfig(project_url="https://example.supabase.co", api_key="secret", write_mode="overwrite_all")
    worker = SupabaseWorker(config, artifacts_dir=tmp_path / "artifacts")

    calls: list[tuple[int, int]] = []
    rows = [{"id": str(idx)} for idx in range(1, 20)]

    def fake_fetch(limit: int = 10, offset: int = 0):
        calls.append((limit, offset))
        return rows

    processed: list[str] = []

    def fake_safe_process(row):
        processed.append(str(row["id"]))
        return True

    monkeypatch.setattr(worker, "_maybe_reset_outputs", lambda: None)
    monkeypatch.setattr(worker, "fetch_pending_rows", fake_fetch)
    monkeypatch.setattr(worker, "_safe_process_row", fake_safe_process)

    count = worker.run_once()

    assert count == 19
    assert processed == [str(idx) for idx in range(1, 20)]
    assert calls == [(1000, 0)]


def test_safe_process_row_writes_error_and_continues(tmp_path: Path) -> None:
    config = SupabaseConfig(project_url="https://example.supabase.co", api_key="secret")
    worker = SupabaseWorker(config, artifacts_dir=tmp_path / "artifacts")

    def boom(row):
        raise RuntimeError("bad row")

    worker.process_row = boom  # type: ignore[method-assign]
    ok = worker._safe_process_row({"id": "row-1", "name": "test"})

    assert ok is False
    error_path = tmp_path / "artifacts" / "_errors" / "row-1.json"
    assert error_path.exists()


def test_build_path_priors_detects_closed_and_open_paths() -> None:
    priors = build_path_priors(
        [
            {"d": "M 10 10 L 30 10 L 30 30 L 10 30 L 12 12", "strokeWidth": 5},
            {"d": "M 100 100 L 160 160", "strokeWidth": 20},
        ]
    )
    assert len(priors) == 2
    assert priors[0]["closed_like"] is True
    assert priors[1]["closed_like"] is False
    assert priors[1]["stroke_width"] == 20.0


def test_build_path_priors_treats_nearly_closed_large_loop_as_closed() -> None:
    priors = build_path_priors(
        [
            {
                "d": "M 333.5 573.5 L 332 572 L 328 566 L 328.5 562.5 L 330 559 L 332.5 556 L 335.5 553 L 339 549 L 344 545 L 350.5 541 L 357 538 L 363 536 L 370.5 534 L 379.5 532 L 387.5 531 L 395.5 531 L 404.5 531 L 413 532 L 421.5 533.5 L 429.5 536 L 437 539 L 444.5 543 L 450.5 547.5 L 453 552.5 L 454 557 L 454.5 562 L 452.5 567.5 L 449.5 572.5 L 445.5 577.5 L 440.5 581.5 L 436 585.5 L 432 589 L 428 592 L 422.5 595 L 415 597.5 L 408.5 598.5 L 403 598.5 L 397 598.5 L 392.5 598.5 L 388 597.5 L 384 597 L 379.5 595.5 L 375.5 593.5 L 371.5 591 L 368.5 588.5 L 366 586 L 364 583.5 L 361 581.5 L 357.5 578.5 L 354 575.5 L 350 572 L 345.5 568.5 L 342 566 L 339.5 564 L 338 562.5 L 337.5 560.5 L 337 559.5 L 337 558 L 337 557",
                "strokeWidth": 5,
            }
        ]
    )
    assert priors[0]["closed_like"] is True
    assert priors[0]["bbox_area"] >= 1800


def test_vector_prior_vetoes_ring_for_thick_open_stroke() -> None:
    result = {
        "image": {"width": 320, "height": 320, "path": "x"},
        "summary": {"instance_count": 1, "counts": {"dots": 0, "strands": 0, "membranes": 0, "rings": 1}},
        "expo": {"canvas": {"width": 320, "height": 320}, "instances": []},
        "instances": [
            {
                "id": 1,
                "bbox": [300, 505, 70, 75],
                "bbox_normalized": [0, 0, 0, 0],
                "contour": [],
                "contour_normalized": [],
                "area": 3500,
                "features": {},
                "label": "rings",
                "confidence": 0.85,
                "explanation": "Detected a large obvious hole inside a thin annular structure.",
            }
        ],
    }
    row = {
        "paths": [
            {
                "d": "M 307 558 L 307 559 L 303 561 L 306 553 L 310 538 L 312.5 528.5 L 313 517 L 313.5 511 L 314 510.5 L 314 511.5 L 314 522 L 314 535 L 311 553.5 L 310.5 558 L 314.5 552.5 L 321.5 534.5 L 326.5 522 L 329.5 515.5 L 329.5 518 L 327 527.5 L 322 547.5 L 318.5 559.5 L 318 569.5 L 320.5 568 L 324.5 560.5 L 332.5 543 L 340.5 523.5 L 341.5 520 L 341.5 519 L 340 524.5 L 338.5 534 L 335.5 557 L 333.5 569.5 L 334 569 L 339.5 555 L 349 534 L 353 525.5 L 355 522 L 354 526.5 L 351.5 541 L 349.5 555 L 348 568 L 351 570 L 355 566.5 L 362.5 551.5 L 367 537.5 L 369 525 L 367.5 524.5 L 365 528.5 L 362 543 L 359 560 L 357.5 566.5 L 357 568 L 360 560 L 363.5 550.5 L 368 535 L 368 534 L 366.5 537.5",
                "opacity": 0.5,
                "strokeWidth": 20,
            }
        ]
    }
    adjusted = apply_vector_priors(result, row)
    assert adjusted["instances"][0]["label"] == "membranes"
    assert adjusted["summary"]["counts"]["membranes"] == 1
    assert adjusted["summary"]["counts"]["rings"] == 0


def test_vector_prior_supports_ring_for_closed_loop_stroke() -> None:
    instance = {
        "id": 1,
        "bbox": [520, 500, 90, 80],
        "bbox_normalized": [0, 0, 0, 0],
        "contour": [],
        "contour_normalized": [],
        "area": 1200,
        "features": {},
        "label": "membranes",
        "confidence": 0.6,
        "explanation": "Large compact region matched membrane rule.",
    }
    prior = build_path_priors(
        [
            {
                "d": "M 536 572.5 L 535.5 572.5 L 521 568.5 L 514 559 L 505.5 545 L 505.5 527.5 L 512 516.5 L 529.5 505.5 L 551.5 506 L 566.5 509.5 L 585 518 L 598 528.5 L 600.5 538 L 596 556.5 L 583 570.5 L 567.5 573.5 L 556.5 574.5 L 541.5 575 L 532.5 574.5",
                "opacity": 0.5,
                "strokeWidth": 5,
            }
        ]
    )[0]
    adjusted = apply_path_prior_to_instance(instance, prior)
    assert adjusted["label"] == "rings"


def test_vector_prior_supports_dot_for_tiny_closed_stroke() -> None:
    instance = {
        "id": 1,
        "bbox": [361, 369, 23, 18],
        "bbox_normalized": [0, 0, 0, 0],
        "contour": [],
        "contour_normalized": [],
        "area": 120,
        "features": {},
        "label": "rings",
        "confidence": 0.79,
        "explanation": "Detected a large obvious hole inside a thin annular structure.",
    }
    prior = build_path_priors(
        [
            {
                "d": "M 378 381 L 378 380.5 L 377.5 378.5 L 377 378 L 377.5 377.5 L 378 377.5 L 378 377.5 L 378.5 377 L 378.5 376 L 378.5 375.5 L 378.5 375.5 L 377.5 376 L 375 378 L 371 380.5 L 367 381.5 L 365 381.5 L 365 379 L 368.5 376 L 372 374 L 373.5 373.5 L 373.5 373.5 L 371 375 L 370 376 L 371 376.5",
                "strokeWidth": 5,
            }
        ]
    )[0]
    adjusted = apply_path_prior_to_instance(instance, prior)
    assert adjusted["label"] == "dots"
