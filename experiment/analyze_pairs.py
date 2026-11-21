"""Summarize paired plume centroid errors and generate the paper figure."""

import argparse
import csv
import hashlib
import io
import json
import math
import platform
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

RESULTS = Path(__file__).resolve().parent / "results"
GEOMETRY_IDS = list(range(150, 175))
CSV_COLUMNS = {"geometry_id", "scene_name", "e_DL", "e_Gaussian", "d"}
RESAMPLES = 10_000
SEED = 20261121
DESCRIPTION_THRESHOLD_M = 20.0


def read_pairs(input_dir):
    csv_path = input_dir / "paired_errors.csv"
    provenance = json.loads((input_dir / "provenance.json").read_text(encoding="utf-8"))
    csv_bytes = csv_path.read_bytes()
    csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()
    if csv_sha256 != provenance["csv_sha256"]:
        raise ValueError("paired_errors.csv SHA-256 does not match provenance.json")

    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8"), newline=""), strict=True)
    if len(reader.fieldnames or []) != len(CSV_COLUMNS) or set(reader.fieldnames) != CSV_COLUMNS:
        raise ValueError("unexpected columns in paired_errors.csv")

    rows = []
    for row in reader:
        if None in row or None in row.values():
            raise ValueError(f"invalid CSV row at line {reader.line_num}")
        rows.append((
            int(row["geometry_id"]),
            row["scene_name"].strip(),
            float(row["e_DL"]),
            float(row["e_Gaussian"]),
            float(row["d"]),
        ))
    rows.sort(key=lambda row: row[0])
    if [row[0] for row in rows] != GEOMETRY_IDS:
        raise ValueError("expected exactly one pair per geometry, IDs 150–174")
    names = {row[1] for row in rows}
    if "" in names or len(names) != len(rows):
        raise ValueError("scene names must be nonempty and unique")

    dl, gaussian, saved_d = np.array([row[2:] for row in rows], dtype=np.float64).T
    if not np.isfinite([dl, gaussian]).all() or np.any(dl < 0) or np.any(gaussian < 0):
        raise ValueError("centroid errors must be finite and nonnegative")
    if not np.allclose(saved_d, gaussian - dl, rtol=0, atol=2e-12):
        raise ValueError("saved d must equal Gaussian minus DL within CSV rounding precision")
    return dl, gaussian, csv_sha256


def describe_errors(errors):
    return {
        "median_m": float(np.median(errors)),
        "count_le_20_m": int(np.count_nonzero(errors <= DESCRIPTION_THRESHOLD_M)),
    }


def summarize(dl, gaussian, csv_sha256):
    differences = gaussian - dl
    rng = np.random.Generator(np.random.PCG64(SEED))
    indices = rng.integers(0, len(differences), size=(RESAMPLES, len(differences)))
    means = differences[indices].mean(axis=1)
    return {
        "n": len(differences),
        "mean_difference_m": float(differences.mean()),
        "ci_95_m": np.percentile(means, [2.5, 97.5], method="linear").tolist(),
        "bootstrap": {
            "resamples": RESAMPLES,
            "seed": SEED,
            "generator": "PCG64",
            "method": "percentile",
            "interpolation": "linear",
        },
        "dl": describe_errors(dl),
        "gaussian": describe_errors(gaussian),
        "csv_sha256": csv_sha256,
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
        },
    }


def plot_pairs(dl, gaussian, path):
    top = max(1, math.ceil(1.05 * max(dl.max(), gaussian.max())))
    with matplotlib.rc_context({"font.size": 8, "pdf.fonttype": 42}):
        fig, ax = plt.subplots(figsize=(3.4, 3.4), layout="constrained")
        ax.set(
            xlim=(0, top), ylim=(0, top), aspect="equal",
            xlabel="Gaussian centroid error (m)", ylabel="DL centroid error (m)",
        )
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
        ax.grid(color="#e6e6e6", linewidth=0.5)
        ax.spines[["top", "right"]].set_visible(False)
        ax.plot([0, top], [0, top], "--", color="#666666", linewidth=0.9, label="Equal errors")
        ax.scatter(gaussian, dl, s=17, color="#164f72", edgecolors="white", linewidths=0.4, zorder=3)
        ax.legend(loc="upper left", frameon=False)
        fig.savefig(path, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=RESULTS)
    parser.add_argument("--output-dir", type=Path, default=RESULTS)
    args = parser.parse_args()

    try:
        dl, gaussian, csv_sha256 = read_pairs(args.input_dir)
        summary = summarize(dl, gaussian, csv_sha256)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=args.output_dir) as work:
            pdf_path = Path(work) / "paired_errors.pdf"
            json_path = Path(work) / "summary.json"
            plot_pairs(dl, gaussian, pdf_path)
            summary["pdf_sha256"] = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
            json_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            pdf_path.replace(args.output_dir / pdf_path.name)
            json_path.replace(args.output_dir / json_path.name)
    except (OSError, KeyError, ValueError, TypeError, csv.Error) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")


if __name__ == "__main__":
    main()
