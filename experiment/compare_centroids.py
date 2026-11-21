import argparse
import csv
import json
import hashlib
import tempfile
import platform
from pathlib import Path

import numpy as np

from checks.check_hw2 import (
    X, Y, verify_archive, compute_concentration_center, euclidean_error,
)
from src.gaussian_baseline import gaussian_field, synthetic_checks

ROOT = Path(__file__).resolve().parents[1]


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_rel(path):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def _module_hashes():
    paths = ("checks/check_hw2.py", "src/gaussian_baseline.py", "experiment/compare_centroids.py")
    return {path: _sha256_file(ROOT / path) for path in paths}


def rectangle_sources(boxes, x_centers, y_centers):
    x_centers = np.asarray(x_centers, dtype=float)
    y_centers = np.asarray(y_centers, dtype=float)

    if x_centers.ndim != 1 or y_centers.ndim != 1:
        raise ValueError("x_centers and y_centers must be one-dimensional")
    if x_centers.size < 2 or y_centers.size < 2:
        raise ValueError("at least two centers are required in each direction")
    if not np.all(np.isfinite(x_centers)) or not np.all(np.isfinite(y_centers)):
        raise ValueError("centers must be finite")
    if boxes is None or len(boxes) == 0:
        raise ValueError("boxes must not be empty")

    x_step = x_centers[1] - x_centers[0]
    y_step = y_centers[1] - y_centers[0]

    if not np.isfinite(x_step) or x_step <= 0.0:
        raise ValueError("x_centers must be increasing with a positive step")
    if not np.isfinite(y_step) or y_step <= 0.0:
        raise ValueError("y_centers must be increasing with a positive step")

    x_edges = np.concatenate(
        (x_centers - 0.5 * x_step, np.array([x_centers[-1] + 0.5 * x_step]))
    )
    y_edges = np.concatenate(
        (y_centers - 0.5 * y_step, np.array([y_centers[-1] + 0.5 * y_step]))
    )

    rows = []

    for box in boxes:
        x0, x1, y0, y1 = map(float, box["bounds_m"])
        power = float(box["relative_power"])

        if not np.isfinite(power) or power <= 0.0:
            raise ValueError("relative_power must be finite and positive")
        if not all(np.isfinite(v) for v in (x0, x1, y0, y1)):
            raise ValueError("bounds must be finite")
        if x1 <= x0 or y1 <= y0:
            raise ValueError("bounds must have positive width and height")
        if x0 < x_edges[0] or x1 > x_edges[-1]:
            raise ValueError("bounds lie outside the grid in x")
        if y0 < y_edges[0] or y1 > y_edges[-1]:
            raise ValueError("bounds lie outside the grid in y")

        xs = np.unique(np.clip(x_edges, x0, x1))
        ys = np.unique(np.clip(y_edges, y0, y1))

        x_mid = 0.5 * (xs[:-1] + xs[1:])
        y_mid = 0.5 * (ys[:-1] + ys[1:])

        X, Y = np.meshgrid(x_mid, y_mid, indexing="xy")
        areas = np.outer(np.diff(ys), np.diff(xs))
        weights = areas.ravel() * power / ((x1 - x0) * (y1 - y0))

        rows.append(np.column_stack((X.ravel(), Y.ravel(), weights)))

    return np.vstack(rows)


def rectangle_checks():
    x_centers = np.array([1.0, 3.0])
    y_centers = np.array([1.0, 3.0])
    boxes = [
        {
            "bounds_m": (0.5, 2.5, 1.0, 3.0),
            "relative_power": 12.0,
        }
    ]
    expected = np.array(
        [
            [1.25, 1.5, 4.5],
            [2.25, 1.5, 1.5],
            [1.25, 2.5, 4.5],
            [2.25, 2.5, 1.5],
        ]
    )

    result = rectangle_sources(boxes, x_centers, y_centers)
    np.testing.assert_allclose(result, expected)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "experiment/results")
    args = parser.parse_args()

    synthetic_checks()
    rectangle_checks()

    manifest_path = ROOT / "fixtures/hw2/manifest.json"
    config_path = ROOT / "experiment/gaussian_config.json"
    inputs_path = ROOT / "experiment/gaussian_inputs.json"
    archive_path = ROOT / "fixtures/hw2/plumes.npz"

    with open(manifest_path) as f:
        manifest = json.load(f)
    with open(config_path) as f:
        cfg = json.load(f)
    with open(inputs_path) as f:
        inputs = json.load(f)

    with verify_archive(archive_path, manifest_path) as data:
        gids = data["geometry_id"]
        names = data["scene_name"]
        les = data["les"]
        current = data["current"]
        valid = data["valid"]

        archive_index = {}
        for i in range(len(names)):
            key = (int(gids[i]), str(names[i]))
            if key in archive_index:
                raise ValueError(f"duplicate archive key {key}")
            archive_index[key] = i

        row_index = {}
        for r in inputs:
            key = (r["geometry_id"], r["scene_name"])
            if key in row_index:
                raise ValueError(f"duplicate input row {key}")
            row_index[key] = r

        if set(archive_index) != set(row_index):
            raise ValueError("archive/input key sets differ")

        for key, r in row_index.items():
            if r.get("dir_k") != cfg["dir_k"] or r.get("tracer") != cfg["tracer"]:
                raise ValueError(f"config mismatch for {key}")
            if r.get("source_npz_sha256") != manifest["scene_sha256"][key[1]]:
                raise ValueError(f"sha mismatch for {key}")

        keys = sorted(row_index)
        rows = []
        for key in keys:
            idx = archive_index[key]
            li = int(cfg["layer_index"])
            row = row_index[key]
            mask = valid[idx, li]

            sources = rectangle_sources(row["boxes"], X, Y)
            field = gaussian_field(
                X, Y, sources,
                row["pressure_gradient_direction_xy"],
                source_z_m=cfg["source_z_m"],
                receptor_z_m=cfg["receptor_z_m"],
                min_distance_m=cfg["min_distance_m"],
            )
            if not np.all(np.isfinite(field)) or np.any(field < 0):
                raise ValueError(f"bad field for {key}")
            if not np.all(np.isfinite(field[mask])):
                raise ValueError(f"nonfinite field on mask for {key}")
            total = float(np.sum(field[mask]))
            if not np.isfinite(total) or total <= 0:
                raise ValueError(f"bad field mass for {key}")

            les64 = np.asarray(les[idx, li], dtype=np.float64)
            dl64 = np.asarray(current[idx, li], dtype=np.float64)
            g64 = np.asarray(field, dtype=np.float64)

            reference = compute_concentration_center(les64, mask)
            center_dl = compute_concentration_center(dl64, mask)
            center_g = compute_concentration_center(g64, mask)

            e_dl = euclidean_error(center_dl, reference)
            e_g = euclidean_error(center_g, reference)
            d = e_g - e_dl
            if not (np.isfinite(e_dl) and np.isfinite(e_g) and np.isfinite(d)):
                raise ValueError(f"nonfinite error for {key}")

            out_row = (key[0], key[1], float(e_dl), float(e_g), float(d))
            if args.pilot:
                print(f"{out_row} mass={total!r}")
                return
            rows.append(out_row)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_name = "paired_errors.csv"
    prov_name = "provenance.json"

    with tempfile.TemporaryDirectory(dir=output_dir) as tmp:
        tmp = Path(tmp)
        stage_csv = tmp / csv_name
        stage_prov = tmp / prov_name

        with open(stage_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["geometry_id", "scene_name", "e_DL", "e_Gaussian", "d"])
            for r in rows:
                w.writerow([r[0], r[1],
                            f"{r[2]:.12f}", f"{r[3]:.12f}", f"{r[4]:.12f}"])

        provenance = {
            "csv_sha256": _sha256_file(stage_csv),
            "inputs": {
                _resolve_rel(manifest_path): _sha256_file(manifest_path),
                _resolve_rel(config_path): _sha256_file(config_path),
                _resolve_rel(inputs_path): _sha256_file(inputs_path),
                _resolve_rel(archive_path): _sha256_file(archive_path),
            },
            "modules": _module_hashes(),
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
        }
        with open(stage_prov, "w") as f:
            json.dump(provenance, f, indent=2, sort_keys=True)

        Path(stage_csv).replace(output_dir / csv_name)
        Path(stage_prov).replace(output_dir / prov_name)


if __name__ == "__main__":
    main()
