#!/usr/bin/env python3
"""Исследовательский парный bootstrap для описательной статистики ошибок HW2.

Читает results/hw2/hw2_results.csv, вычисляет описательную статистику для
errors_cur и errors_baseline, а также парного bootstrap.
Результаты сохраняются в results/hw2/uncertainty.json и results/hw2/uncertainty.txt.

Не заменяет check_hw2.py, не подменяет критерий принятия.
"""

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "results" / "hw2" / "hw2_results.csv"
JSON_OUT = ROOT / "results" / "hw2" / "uncertainty.json"
TXT_OUT = ROOT / "results" / "hw2" / "uncertainty.txt"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def validate_csv(path: Path):
    """Возвращает list[geometry_id], list[errors_cur], list[errors_baseline]."""
    geometry_ids = []
    errors_cur = []
    errors_base = []

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            gid = int(row["geometry_id"])
            ec = float(row["errors_cur"])
            eb = float(row["errors_baseline"])
            geometry_ids.append(gid)
            errors_cur.append(ec)
            errors_base.append(eb)

    # Ровно 25 строк, все geometry_id уникальны, отсортированы 150..174
    expected = list(range(150, 175))
    if len(geometry_ids) != 25:
        print(f"[FAIL] ожидалось 25 строк, получено {len(geometry_ids)}",
              file=sys.stderr)
        sys.exit(1)
    if len(set(geometry_ids)) != 25:
        print(f"[FAIL] найдены дубли geometry_id: {len(geometry_ids)} "
              f"строк, {len(set(geometry_ids))} уникальных", file=sys.stderr)
        sys.exit(1)
    if sorted(geometry_ids) != expected:
        print(f"[FAIL] geometry_id не 150..174: {sorted(geometry_ids)}",
              file=sys.stderr)
        sys.exit(1)

    for gid, ec, eb in zip(geometry_ids, errors_cur, errors_base):
        if not np.isfinite(ec) or not np.isfinite(eb):
            print(f"[FAIL] неконечная ошибка gid={gid}", file=sys.stderr)
            sys.exit(1)
        if ec < 0 or eb < 0:
            print(f"[FAIL] отрицательная ошибка gid={gid}: cur={ec}, base={eb}",
                  file=sys.stderr)
            sys.exit(1)

    return geometry_ids, errors_cur, errors_base


# ---------------------------------------------------------------------------
# Description
# ---------------------------------------------------------------------------

def desc_stats(values):
    arr = np.array(values, dtype=float)
    n = len(arr)
    return {
        "n": n,
        "mean": round(float(np.mean(arr)), 6),
        "median": round(float(np.median(arr)), 6),
        "std": round(float(np.std(arr, ddof=1)), 6),
        "min": round(float(np.min(arr)), 6),
        "Q1": round(float(np.percentile(arr, 25)), 6),
        "Q3": round(float(np.percentile(arr, 75)), 6),
        "max": round(float(np.max(arr)), 6),
        "count_le20": int(np.sum(arr <= 20.0))
    }


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def bootstrap_pair(e_cur, e_base, n_reps, seed):
    """Парный percentile bootstrap [2.5%,97.5%].
    
    Квантили берутся через np.quantile(..., method='linear') — согласованное
    определение, не зависящее от n_reps.
    """
    rng = np.random.default_rng(seed)
    n = len(e_cur)
    med_out = []
    frac_out = []
    diff_out = []
    for _ in range(n_reps):
        idx = rng.integers(0, n, size=n)
        ec = e_cur[idx]
        eb = e_base[idx]
        med_out.append(float(np.median(ec)))
        frac_out.append(float(np.mean(ec <= 20.0)))
        diff_out.append(float(np.mean(eb - ec)))

    # согласованные квантили, не зависят от n_reps
    ci = []
    for arr in [med_out, frac_out, diff_out]:
        lo, hi = np.quantile(arr, [0.025, 0.975], method='linear')
        ci.append((round(float(lo), 6), round(float(hi), 6)))

    # статистика распределения mean_diff
    diff_arr = np.array(diff_out)
    diff_stats = {
        "median": round(float(np.median(diff_arr)), 6),
        "std": round(float(np.std(diff_arr, ddof=1)), 6),
        "min": round(float(np.min(diff_arr)), 6),
        "Q1": round(float(np.percentile(diff_arr, 25)), 6),
        "Q3": round(float(np.percentile(diff_arr, 75)), 6),
        "max": round(float(np.max(diff_arr)), 6),
    }

    return {"median_ci": ci[0], "frac_le20_ci": ci[1],
            "mean_diff_ci": ci[2], "diff_stats": diff_stats}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not CSV_PATH.exists():
        print(f"[FAIL] CSV not found: {CSV_PATH}", file=sys.stderr)
        sys.exit(1)

    csv_sha = sha256_file(CSV_PATH)
    _, e_cur, e_base = validate_csv(CSV_PATH)

    # Описательная статистика
    desc_cur = desc_stats(e_cur)
    desc_base = desc_stats(e_base)

    # Средняя парная разность
    diff_arr = np.array(e_base) - np.array(e_cur)
    mean_diff_all = round(float(np.mean(diff_arr)), 6)

    # Bootstrap-seeds
    seeds = [20261115, 20261116, 20261117]
    n_reps = 10000
    b_results = []

    np_cur = np.array(e_cur, dtype=float)
    np_base = np.array(e_base, dtype=float)

    for sd in seeds:
        res = bootstrap_pair(np_cur, np_base, n_reps, sd)
        b_results.append({"seed": sd,
                          "median_cur_ci": res["median_ci"],
                          "frac_le20_ci": res["frac_le20_ci"],
                          "mean_diff_ci": res["mean_diff_ci"],
                          "diff_stats": res["diff_stats"]})

    # Парная разность: статистика полных перцентилей
    diff_stats_main = {
        "median": round(float(np.median(diff_arr)), 6),
        "std": round(float(np.std(diff_arr, ddof=1)), 6),
        "min": round(float(np.min(diff_arr)), 6),
        "Q1": round(float(np.percentile(diff_arr, 25)), 6),
        "Q3": round(float(np.percentile(diff_arr, 75)), 6),
        "max": round(float(np.max(diff_arr)), 6),
    }

    # JSON
    out = {
        "model": "combined_family_ft_best",
        "description": {
            "note": "post-hoc descriptive + pairwise bootstrap, not preregistered",
            "csv_file": str(CSV_PATH.relative_to(ROOT)),
            "csv_sha256": csv_sha,
            "n_situations": 25,
            "geometry_id_range": [150, 174],
            "desc_cur": desc_cur,
            "desc_baseline": desc_base,
            "mean_diff_baseline_minus_cur": mean_diff_all,
            "diff_stats": diff_stats_main
        },
        "bootstrap": {
            "method": "quantile-based CI [2.5%,97.5%] via np.quantile(method='linear')",
            "n_resamples": n_reps,
            "sign": "mean_diff = baseline - cur, positive = cur better",
            "numpy_version": str(np.__version__),
            "seeds": seeds,
            "results": b_results
        }
    }

    JSON_OUT.parent.mkdir(exist_ok=True)
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    # TEXT TABLE
    lines = [
        "REPORT: descriptive stats + pairwise bootstrap [2.5%,97.5%]",
        f"CSV: {CSV_PATH.name} sha={csv_sha}",
        f"n=25, seeds: {seeds}",
        f"mean_diff (baseline - cur) = {mean_diff_all}",
        "",
        "--- Descriptive Stats ---",
        f"{'':<18} {'cur':>12} {'baseline':>12}",
        "-" * 46,
    ]

    metric_labels = {
        "mean": ["mean", "mean"],
        "median": ["median", "median"],
        "std": ["std", "std"],
        "min": ["min", "min"],
        "Q1": ["Q1", "Q1"],
        "Q3": ["Q3", "Q3"],
        "max": ["max", "max"],
        "count_le20": ["count_le20", "count_le20"],
    }

    for lbl, k in metric_labels.items():
        cv = desc_cur[k[0]]
        bv = desc_base[k[1]]
        lines.append(f"{lbl:<18} {cv:>12} {bv:>12}")

    lines.append("")
    lines.append("--- Bootstrap CI [2.5%,97.5%] ---")
    lines.append(f"{'seed':<14} {'median_cur':>16} {'frac_le20':>16} {'mean_diff':>16}")
    lines.append("-" * 68)
    for br in b_results:
        s = br["seed"]
        mc = br["median_cur_ci"]
        fl = br["frac_le20_ci"]
        md = br["mean_diff_ci"]
        lines.append(f"{s:<14} [{mc[0]:>8.4f}..{mc[1]:>8.4f}] "
                     f"[{fl[0]:>8.4f}..{fl[1]:>8.4f}] "
                     f"[{md[0]:>8.4f}..{md[1]:>8.4f}]")
    lines.append("")
    lines.append("--- Distribution statistics of mean_diff (baseline - cur) ---")
    dsm = diff_stats_main
    lines.append(f"{'':<18} {'median':>12} {'std':>12} {'min':>12} {'Q1':>12} {'Q3':>12} {'max':>12}")
    lines.append("-" * 80)
    lines.append(f"{'full_diff':<18} {dsm['median']:>12} {dsm['std']:>12} {dsm['min']:>12} "
                 f"{dsm['Q1']:>12} {dsm['Q3']:>12} {dsm['max']:>12}")
    lines.append("")
    for br in b_results:
        s = br["seed"]
        ds = br["diff_stats"]
        lines.append(f"seed {s}: median={ds['median']} std={ds['std']} "
                     f"min={ds['min']} Q1={ds['Q1']} Q3={ds['Q3']} max={ds['max']}")

    lines.append("")
    lines.append("--- Interpretation ---")
    lines.append("mean_diff = baseline - current. Положительное значение")
    lines.append("означает преимущество current (меньшая ошибка на scene).")
    lines.append("Интервалы bootstrap — post-hoc, при предположении обменности")
    lines.append("и репрезентативности 25 фиксированных сцен. Все 3 seed показаны")
    lines.append("без выделения «лучшего» — они проверяют устойчивость Монте-Карло.")

    lines.append("")
    lines.append("OUTPUT: " + str(JSON_OUT) + "  " + str(TXT_OUT))

    txt = "\n".join(lines) + "\n"
    TXT_OUT.parent.mkdir(exist_ok=True)
    TXT_OUT.write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()