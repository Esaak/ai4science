#!/usr/bin/env python3
"""Сравнить пять худших сцен с полной валидацией по перцентилям 30 признаков.

Метод: для каждой ячейки (сцена, признак) — перцентиль = (lo + hi) / 2 / N * 100,
где lo = searchsorted(left), hi = searchsorted(right) в отсортированном full-распределении.
Это корректно обрабатывает дубликаты.
"""

import json
import numpy as np

VAL_PATH = "data/edison_cache/val.npz"
TOP_PATH = "data/edison_cache/top_fields.npz"
OUT_JSON = "results/top5_percentiles.json"
OUT_MD = "results/top5_comparison.md"


def main():
    val = np.load(VAL_PATH)
    top = np.load(TOP_PATH)

    num_all = val["num"]          # (11632, 30)
    cols = val["cols"]            # (30,)
    idx = top["idx"]              # (5,)
    N = num_all.shape[0]

    num_top = num_all[idx]        # (5, 30)

    # Отсортированный full для searchsorted
    sorted_all = np.sort(num_all, axis=0)

    # Перцентили методом searchsorted
    percentiles = np.zeros((5, 30))
    for i in range(5):
        for j in range(30):
            val_i = num_top[i, j]
            lo = np.searchsorted(sorted_all[:, j], val_i, side='left')
            hi = np.searchsorted(sorted_all[:, j], val_i, side='right')
            percentiles[i, j] = (lo + hi) / 2.0 / N * 100.0

    # Построить JSON
    scenes_info = []
    for i in range(5):
        scene_num = int(idx[i])
        campaign = val["campaign"][scene_num]
        family = "январские" if str(campaign).startswith("2026_01") else "urban_layer"
        feats = []
        for j in range(30):
            feats.append({
                "признак": str(cols[j]),
                "значение": float(num_top[i, j]),
                "перцентиль": float(round(percentiles[i, j], 2))
            })
        scenes_info.append({
            "номер": scene_num,
            "семейство": family,
            "признаки": feats
        })

    # Топ-выделяющиеся признаки по размаху перцентилов
    p_array = percentiles
    spread = p_array.max(axis=0) - p_array.min(axis=0)
    top_features_idx = np.argsort(-spread)

    feature_extremes = []
    for fi in top_features_idx[:10]:
        fname = str(cols[fi])
        vals = num_top[:, fi]
        ps = percentiles[:, fi]
        feature_extremes.append({
            "признак": fname,
            "размах_перцентилов": float(round(spread[fi], 2)),
            "мин_перцентиль": float(round(ps.min(), 2)),
            "макс_перцентиль": float(round(ps.max(), 2)),
            "значения_пятёрки": [float(round(v, 4)) for v in vals]
        })

    result = {
        "данные": {
            "val": VAL_PATH,
            "top_fields": TOP_PATH,
            "всего_сцен": N,
            "признаков": 30,
            "колонки": [str(c) for c in cols]
        },
        "сцены": scenes_info,
        "топ_выделяющиеся_признаки": feature_extremes
    }

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Markdown-таблица
    md_lines = [
        "# Пять худших сцен: перцентили по 30 признакам",
        "",
        f"Полная валидация: {N} сцен, {num_all.shape[1]} признаков.",
        "Перцентиль = (lo + hi) / 2 / N × 100, где lo/hi — searchsorted(left/right).",
        "Корректно обрабатывает дубликаты: при одинаковых значениях — 50-й перцентиль.",
        "",
        "## Таблица перцентилов",
        "",
        "| сцена | семейство | " + " | ".join(str(cols[j]) for j in range(30)) + " |",
        "|---|---|" + "|".join("---" for _ in range(30)) + "|",
    ]
    for i in range(5):
        scene_num = int(idx[i])
        campaign = val["campaign"][scene_num]
        family = "январские" if str(campaign).startswith("2026_01") else "urban_layer"
        row = [str(scene_num), family]
        for j in range(30):
            row.append(f"{percentiles[i, j]:.1f}")
        md_lines.append("| " + " | ".join(row) + " |")

    md_lines.append("")
    md_lines.append("## Топ-10 признаков по размаху перцентилов")
    md_lines.append("")
    md_lines.append("| признак | размах | мин | макс | значения |")
    md_lines.append("|---|---|---|---|---|")
    for fe in feature_extremes[:10]:
        vals_str = ", ".join(f"{v:.4g}" for v in fe["значения_пятёрки"])
        md_lines.append(
            f"| {fe['признак']} | {fe['размах_перцентилов']:.1f} | "
            f"{fe['мин_перцентиль']:.1f} | {fe['макс_перцентиль']:.1f} | {vals_str} |"
        )

    md_lines.append("")
    md_lines.append("## Вывод")
    md_lines.append("")
    top3 = feature_extremes[:3]
    md_lines.append(
        f"Сильнее всего пятёрка худших сцен выделяется по признакам: "
        f"`{top3[0]['признак']}` (размах {top3[0]['размах_перцентилов']:.1f} п.п.), "
        f"`{top3[1]['признак']}` ({top3[1]['размах_перцентилов']:.1f}), "
        f"`{top3[2]['признак']}` ({top3[2]['размах_перцентилов']:.1f})."
    )

    with open(OUT_MD, "w") as f:
        f.write("\n".join(md_lines))

    print(f"Написано: {OUT_JSON}, {OUT_MD}")


if __name__ == "__main__":
    main()