from __future__ import annotations

import json
import os
import re
import tempfile
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import requests
from requests.exceptions import RequestException, SSLError

from .config import load_config
from .infer import build_expo_payload, infer_image
from .utils import ensure_dir
from .visualize import save_overlay

DEFAULT_OUTPUT_COLUMNS = (
    "analysis_json",
    "segmentation_json",
    "floater_types",
    "floater_type_counts",
    "analysis_artifacts",
    "analysed_at",
)

PATH_TOKEN_PATTERN = re.compile(r"[ML]|-?\d+(?:\.\d+)?")
WRITE_MODES = ("incremental", "overwrite_all")


@dataclass(frozen=True)
class SupabaseConfig:
    project_url: str
    api_key: str
    input_table: str = "drawings"
    output_bucket: str = "analyses"
    poll_interval_s: int = 10
    canvas_width_fallback: int = 512
    canvas_height_fallback: int = 512
    analysis_json_column: str = "analysis_json"
    segmentation_json_column: str = "segmentation_json"
    floater_types_column: str = "floater_types"
    floater_type_counts_column: str = "floater_type_counts"
    analysis_artifacts_column: str = "analysis_artifacts"
    analysed_at_column: str = "analysed_at"
    write_mode: str = "incremental"
    wipe_output_bucket_on_start: bool = False
    upload_retries: int = 4
    request_retries: int = 4

    @property
    def rest_url(self) -> str:
        return self.project_url.rstrip("/") + "/rest/v1"

    @property
    def storage_url(self) -> str:
        return self.project_url.rstrip("/") + "/storage/v1"


def load_supabase_config(env_path: str | Path | None = None) -> SupabaseConfig:
    raw = _load_env_file(env_path)
    project_url = (
        os.getenv("SUPABASE_URL")
        or os.getenv("PROJECT_URL")
        or raw.get("SUPABASE_URL")
        or raw.get("PROJECT_URL")
        or raw.get("PROJECT URL")
    )
    api_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_API_KEY")
        or os.getenv("SUPABASE_KEY")
        or raw.get("SUPABASE_SERVICE_ROLE_KEY")
        or raw.get("SUPABASE_API_KEY")
        or raw.get("SUPABASE_KEY")
        or raw.get("API-KEY")
        or raw.get("API_KEY")
    )
    if not project_url or not api_key:
        raise RuntimeError(
            "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
            "or add them to floater_demo/.env."
        )

    return SupabaseConfig(
        project_url=project_url,
        api_key=api_key,
        input_table=os.getenv("SUPABASE_INPUT_TABLE", raw.get("SUPABASE_INPUT_TABLE", "drawings")),
        output_bucket=os.getenv("SUPABASE_OUTPUT_BUCKET", raw.get("SUPABASE_OUTPUT_BUCKET", "analyses")),
        poll_interval_s=int(os.getenv("SUPABASE_POLL_INTERVAL_S", raw.get("SUPABASE_POLL_INTERVAL_S", "10"))),
        canvas_width_fallback=int(
            os.getenv("SUPABASE_CANVAS_WIDTH_FALLBACK", raw.get("SUPABASE_CANVAS_WIDTH_FALLBACK", "512"))
        ),
        canvas_height_fallback=int(
            os.getenv("SUPABASE_CANVAS_HEIGHT_FALLBACK", raw.get("SUPABASE_CANVAS_HEIGHT_FALLBACK", "512"))
        ),
        analysis_json_column=os.getenv(
            "SUPABASE_ANALYSIS_JSON_COLUMN",
            raw.get("SUPABASE_ANALYSIS_JSON_COLUMN", "analysis_json"),
        ),
        segmentation_json_column=os.getenv(
            "SUPABASE_SEGMENTATION_JSON_COLUMN",
            raw.get("SUPABASE_SEGMENTATION_JSON_COLUMN", "segmentation_json"),
        ),
        floater_types_column=os.getenv(
            "SUPABASE_FLOATER_TYPES_COLUMN",
            raw.get("SUPABASE_FLOATER_TYPES_COLUMN", "floater_types"),
        ),
        floater_type_counts_column=os.getenv(
            "SUPABASE_FLOATER_TYPE_COUNTS_COLUMN",
            raw.get("SUPABASE_FLOATER_TYPE_COUNTS_COLUMN", "floater_type_counts"),
        ),
        analysis_artifacts_column=os.getenv(
            "SUPABASE_ANALYSIS_ARTIFACTS_COLUMN",
            raw.get("SUPABASE_ANALYSIS_ARTIFACTS_COLUMN", "analysis_artifacts"),
        ),
        analysed_at_column=os.getenv(
            "SUPABASE_ANALYSED_AT_COLUMN",
            raw.get("SUPABASE_ANALYSED_AT_COLUMN", "analysed_at"),
        ),
        write_mode=os.getenv(
            "SUPABASE_WRITE_MODE",
            raw.get("SUPABASE_WRITE_MODE", "incremental"),
        ),
        wipe_output_bucket_on_start=_as_bool(
            os.getenv(
                "SUPABASE_WIPE_OUTPUT_BUCKET_ON_START",
                raw.get("SUPABASE_WIPE_OUTPUT_BUCKET_ON_START", "false"),
            )
        ),
        upload_retries=int(
            os.getenv("SUPABASE_UPLOAD_RETRIES", raw.get("SUPABASE_UPLOAD_RETRIES", "4"))
        ),
        request_retries=int(
            os.getenv("SUPABASE_REQUEST_RETRIES", raw.get("SUPABASE_REQUEST_RETRIES", "4"))
        ),
    )


class SupabaseWorker:
    def __init__(self, config: SupabaseConfig, artifacts_dir: str | Path) -> None:
        self.config = config
        if self.config.write_mode not in WRITE_MODES:
            raise ValueError(f"Unsupported write_mode={self.config.write_mode!r}. Expected one of {WRITE_MODES}.")
        self.demo_config = load_config()
        self.artifacts_dir = ensure_dir(artifacts_dir)
        self.session = requests.Session()
        self._startup_reset_completed = False
        self.session.headers.update(
            {
                "apikey": self.config.api_key,
                "Authorization": f"Bearer {self.config.api_key}",
            }
        )

    def run_forever(self) -> None:
        while True:
            processed = self.run_once()
            if not processed:
                time.sleep(self.config.poll_interval_s)

    def run_once(self) -> bool:
        self._maybe_reset_outputs()
        rows = self.fetch_pending_rows(limit=10)
        if not rows:
            return False
        for row in rows:
            self.process_row(row)
        return True

    def fetch_pending_rows(self, limit: int = 10) -> list[dict[str, Any]]:
        params = {
            "select": "id,name,paths,canvas_width,canvas_height,image_url,created_at,analysed_at",
            "order": "created_at.asc",
            "limit": str(limit),
        }
        if self.config.write_mode == "incremental":
            params[self.config.analysed_at_column] = "is.null"
        response = self._request_with_retry(
            "GET",
            f"{self.config.rest_url}/{self.config.input_table}",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError("Supabase response was not a list")
        return payload

    def _maybe_reset_outputs(self) -> None:
        if self._startup_reset_completed:
            return
        self._startup_reset_completed = True
        if self.config.write_mode != "overwrite_all":
            return
        if self.config.wipe_output_bucket_on_start and self.config.output_bucket:
            self.clear_output_bucket()

    def clear_output_bucket(self) -> int:
        deleted = 0
        page = 0
        while True:
            object_paths = self._list_storage_objects(prefix="", limit=1000, offset=page * 1000)
            if not object_paths:
                break
            response = self._request_with_retry(
                "DELETE",
                f"{self.config.storage_url}/object/{self.config.output_bucket}",
                headers={"Content-Type": "application/json"},
                json={"prefixes": object_paths},
                timeout=60,
            )
            response.raise_for_status()
            deleted += len(object_paths)
            if len(object_paths) < 1000:
                break
            page += 1
        return deleted

    def _list_storage_objects(self, prefix: str, limit: int, offset: int) -> list[str]:
        response = self._request_with_retry(
            "POST",
            f"{self.config.storage_url}/object/list/{self.config.output_bucket}",
            headers={"Content-Type": "application/json"},
            json={
                "prefix": prefix,
                "limit": limit,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"},
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []

        object_paths: list[str] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            if item.get("id") is None:
                child_prefix = f"{prefix.rstrip('/')}/{name}".strip("/")
                object_paths.extend(self._list_storage_objects(child_prefix, limit=limit, offset=0))
            else:
                object_paths.append(f"{prefix.rstrip('/')}/{name}".strip("/"))
        return object_paths

    def process_row(self, row: dict[str, Any]) -> dict[str, Any]:
        row_id = str(row["id"])
        with tempfile.TemporaryDirectory(prefix=f"floater_{row_id}_") as temp_dir:
            temp_dir_path = Path(temp_dir)
            image_path = self._prepare_input_image(row, temp_dir_path)
            result = infer_image(image_path, self.demo_config, save_debug_masks=True)
            expo_payload = build_expo_payload(result)

            row_artifacts_dir = ensure_dir(self.artifacts_dir / row_id)
            overlay_path = save_overlay(result, row_artifacts_dir)
            segmentation_path = row_artifacts_dir / "segmentation.json"
            analysis_path = row_artifacts_dir / "analysis.json"

            segmentation_payload = self._build_segmentation_payload(row, result, expo_payload)
            analysis_payload = self._build_analysis_payload(row, result, expo_payload)

            segmentation_path.write_text(json.dumps(segmentation_payload, indent=2), encoding="utf-8")
            analysis_path.write_text(json.dumps(analysis_payload, indent=2), encoding="utf-8")

            uploaded_artifacts = self._upload_artifacts(
                row_id=row_id,
                overlay_path=overlay_path,
                segmentation_path=segmentation_path,
                analysis_path=analysis_path,
            )
            self._update_row(row_id, analysis_payload, segmentation_payload, uploaded_artifacts)
            return analysis_payload

    def _prepare_input_image(self, row: dict[str, Any], temp_dir: Path) -> Path:
        image_url = row.get("image_url")
        if image_url:
            downloaded = self._download_image(str(image_url), temp_dir / "input.png")
            if downloaded is not None:
                return downloaded
        return render_row_to_png(
            row=row,
            output_path=temp_dir / "rendered.png",
            fallback_width=self.config.canvas_width_fallback,
            fallback_height=self.config.canvas_height_fallback,
        )

    def _download_image(self, image_url: str, output_path: Path) -> Path | None:
        response = requests.get(image_url, timeout=30, headers={"Connection": "close"})
        if response.status_code != 200 or not response.content:
            return None
        output_path.write_bytes(response.content)
        return output_path

    def _build_segmentation_payload(
        self,
        row: dict[str, Any],
        result: dict[str, Any],
        expo_payload: dict[str, Any],
    ) -> dict[str, Any]:
        present_types = sorted(
            label for label, count in result["summary"]["counts"].items() if int(count) > 0
        )
        return {
            "schema_version": 1,
            "drawing_id": row["id"],
            "drawing_name": row.get("name"),
            "created_at": row.get("created_at"),
            "present_types": present_types,
            "counts": result["summary"]["counts"],
            "instance_count": result["summary"]["instance_count"],
            "expo": expo_payload,
        }

    def _build_analysis_payload(
        self,
        row: dict[str, Any],
        result: dict[str, Any],
        expo_payload: dict[str, Any],
    ) -> dict[str, Any]:
        instances = []
        for instance in result["instances"]:
            instances.append(
                {
                    "id": instance["id"],
                    "label": instance["label"],
                    "confidence": instance["confidence"],
                    "bbox": instance["bbox"],
                    "bbox_normalized": instance["bbox_normalized"],
                    "contour": instance["contour"],
                    "contour_normalized": instance["contour_normalized"],
                    "features": instance["features"],
                    "explanation": instance["explanation"],
                }
            )
        present_types = sorted(
            label for label, count in result["summary"]["counts"].items() if int(count) > 0
        )
        return {
            "schema_version": 1,
            "drawing_id": row["id"],
            "drawing_name": row.get("name"),
            "analysed_at": utc_now_iso(),
            "present_types": present_types,
            "summary": result["summary"],
            "image": result["image"],
            "expo": expo_payload,
            "instances": instances,
        }

    def _upload_artifacts(
        self,
        row_id: str,
        overlay_path: Path,
        segmentation_path: Path,
        analysis_path: Path,
    ) -> dict[str, str]:
        if not self.config.output_bucket:
            return {}
        bucket = self.config.output_bucket
        prefix = f"{row_id}"
        uploads = [
            ("overlay_url", f"{prefix}/overlay.png", overlay_path, "image/png"),
            ("segmentation_url", f"{prefix}/segmentation.json", segmentation_path, "application/json"),
            ("analysis_url", f"{prefix}/analysis.json", analysis_path, "application/json"),
        ]
        artifacts: dict[str, str] = {}
        for key, object_path, local_path, content_type in uploads:
            try:
                artifacts[key] = self._upload_file(bucket, object_path, local_path, content_type)
            except requests.HTTPError as exc:
                response = exc.response
                if response is not None and response.status_code == 400 and "Bucket not found" in response.text:
                    return {}
                raise
            except RequestException:
                # Keep row analysis usable even if one artifact upload flakes.
                continue
        return artifacts

    def _upload_file(self, bucket: str, object_path: str, local_path: Path, content_type: str) -> str:
        encoded_path = urllib.parse.quote(object_path, safe="/")
        payload = local_path.read_bytes()
        headers = {
            "x-upsert": "true",
            "Content-Type": content_type,
            "Connection": "close",
        }
        response: requests.Response | None = None
        last_error: Exception | None = None
        for attempt in range(1, self.config.upload_retries + 1):
            try:
                response = self._request_with_retry(
                    "POST",
                    f"{self.config.storage_url}/object/{bucket}/{encoded_path}",
                    headers=headers,
                    data=payload,
                    timeout=60,
                    retries=self.config.upload_retries,
                )
                response.raise_for_status()
                break
            except (SSLError, RequestException) as exc:
                last_error = exc
                if attempt == self.config.upload_retries:
                    raise
                time.sleep(min(2 ** (attempt - 1), 8))
                continue
        if response is None:
            raise RuntimeError(f"Upload failed for {object_path}: {last_error}")
        return f"{self.config.project_url.rstrip('/')}/storage/v1/object/public/{bucket}/{encoded_path}"

    def _update_row(
        self,
        row_id: str,
        analysis_payload: dict[str, Any],
        segmentation_payload: dict[str, Any],
        uploaded_artifacts: dict[str, str],
    ) -> None:
        patch_payload: dict[str, Any] = {
            self.config.analysis_json_column: analysis_payload,
            self.config.segmentation_json_column: segmentation_payload,
            self.config.floater_types_column: analysis_payload["present_types"],
            self.config.floater_type_counts_column: analysis_payload["summary"]["counts"],
            self.config.analysis_artifacts_column: uploaded_artifacts,
            self.config.analysed_at_column: analysis_payload["analysed_at"],
        }
        response = self._request_with_retry(
            "PATCH",
            f"{self.config.rest_url}/{self.config.input_table}",
            params={"id": f"eq.{row_id}"},
            headers={"Content-Type": "application/json", "Prefer": "return=minimal"},
            json=patch_payload,
            timeout=30,
        )
        if response.ok:
            return

        # Fallback for schemas that do not yet have the analysis columns.
        fallback_payload = {self.config.analysed_at_column: analysis_payload["analysed_at"]}
        fallback = self._request_with_retry(
            "PATCH",
            f"{self.config.rest_url}/{self.config.input_table}",
            params={"id": f"eq.{row_id}"},
            headers={"Content-Type": "application/json", "Prefer": "return=minimal"},
            json=fallback_payload,
            timeout=30,
        )
        fallback.raise_for_status()

    def _request_with_retry(
        self,
        method: str,
        url: str,
        retries: int | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        attempt_count = retries or self.config.request_retries
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("Connection", "close")
        last_error: Exception | None = None
        for attempt in range(1, attempt_count + 1):
            try:
                response = self.session.request(method, url, headers=headers, **kwargs)
                return response
            except (SSLError, RequestException) as exc:
                last_error = exc
                if attempt == attempt_count:
                    raise
                time.sleep(min(2 ** (attempt - 1), 8))
        raise RuntimeError(f"{method} {url} failed: {last_error}")


def render_row_to_png(
    row: dict[str, Any],
    output_path: str | Path,
    fallback_width: int = 512,
    fallback_height: int = 512,
) -> Path:
    width = int(row.get("canvas_width") or 0)
    height = int(row.get("canvas_height") or 0)
    if width <= 0 or height <= 0:
        inferred_width, inferred_height = infer_canvas_size(row.get("paths") or [])
        width = inferred_width or fallback_width
        height = inferred_height or fallback_height

    canvas = np.full((height, width, 3), 255, dtype=np.uint8)
    for path_entry in row.get("paths") or []:
        draw_path(canvas, path_entry)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), canvas)
    return output


def infer_canvas_size(paths: list[dict[str, Any]]) -> tuple[int, int]:
    max_x = 0.0
    max_y = 0.0
    for path_entry in paths:
        for x, y in parse_svg_points(str(path_entry.get("d") or "")):
            max_x = max(max_x, x)
            max_y = max(max_y, y)
    if max_x <= 0 or max_y <= 0:
        return (0, 0)
    return (int(max_x) + 24, int(max_y) + 24)


def draw_path(canvas: np.ndarray, path_entry: dict[str, Any]) -> None:
    points = parse_svg_points(str(path_entry.get("d") or ""))
    if len(points) < 2:
        if len(points) == 1:
            x, y = points[0]
            cv2.circle(canvas, (int(round(x)), int(round(y))), 2, (150, 150, 150), -1)
        return

    opacity = float(path_entry.get("opacity") or 0.5)
    stroke_width = max(1, int(round(float(path_entry.get("strokeWidth") or 5))))
    stroke_gray = int(max(40, min(200, 255 - opacity * 180)))
    color = (stroke_gray, stroke_gray, stroke_gray)

    for start, end in zip(points, points[1:]):
        x1, y1 = start
        x2, y2 = end
        cv2.line(
            canvas,
            (int(round(x1)), int(round(y1))),
            (int(round(x2)), int(round(y2))),
            color,
            stroke_width,
            lineType=cv2.LINE_AA,
        )


def parse_svg_points(path_d: str) -> list[tuple[float, float]]:
    tokens = PATH_TOKEN_PATTERN.findall(path_d)
    points: list[tuple[float, float]] = []
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if token in {"M", "L"}:
            idx += 1
            continue
        if idx + 1 >= len(tokens):
            break
        x = float(tokens[idx])
        y = float(tokens[idx + 1])
        points.append((x, y))
        idx += 2
    return points


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_env_file(env_path: str | Path | None) -> dict[str, str]:
    if env_path is None:
        candidate = Path(__file__).resolve().parents[1] / ".env"
    else:
        candidate = Path(env_path)
    if not candidate.exists():
        return {}

    values: dict[str, str] = {}
    for line in candidate.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            key, value = stripped.split("=", 1)
        elif ":" in stripped:
            key, value = stripped.split(":", 1)
        else:
            continue
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _as_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}
