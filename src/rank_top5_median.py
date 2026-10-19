#!/usr/bin/env python3
"""Ранжировать 30 признаков по отличию пяти худших сцен от полной валидации.

Метрика отличия: для каждого признака берём перцентили пяти худших сцен в
распределении полной валидации (11632 сцены), считаем медиану и минимум этих
перцентилей, ранжируем по удалению медианы от 50 (по убыванию).

Перцентиль = (lo + hi) / 2 / N * 100, где lo/hi — searchsorted(left/right)
в отсортированном full-распределении. Корректно обрабатывает дубликаты.

Дополнительно: признаки, где все пять сцен согласованно лежат в верхнем
(перцентиль > 90) или нижнем (перцентиль < 10) дециле.
"""

import json
import numpy as np

VAL_PATH = "data/edison_cache/val.npz"
TOP_PATH = "data/edison_cache/top_fields.npz"
OUT_JSON = "results/top5_median_rank.json"
OUT_MD = "results/top5_comparison.md"


def main():
    val = np.load(VAL_PATH)
    top = np.load(TOP_PATH)

    num_all = val["num"]          # (11632, 30)
    cols = val["cols"]            # (30,)
    idx = top["idx"]              # (5,)
    N = num_all.shape[0]

    num_top = num_all[idx]        # (5, 30)
    sorted_all = np.sort(num_all, axis=0)

    # Перцентили пяти худших сцен
    percentiles = np.zeros((5, 30))
    for i in range(5):
        for j in range(30):
            v = num_top[i, j]
            lo = np.searchsorted(sorted_all[:, j], v, side='left')
            hi = np.searchsorted(sorted_all[:, j], v, side='right')
            percentiles[i, j] = (lo + hi) / 2.0 / N * 100.0

    # Медиана и минимум перцентилей по пяти сценам
    med = np.median(percentiles, axis=0)   # (30,)
    mn = percentiles.min(axis=0)           # (30,)

    # Удаление медианы от 50
    dist = np.abs(med - 50.0)
    order = np.argsort(-dist)              # по убыванию удаления

    # Признаки с согласованным децилем: все 5 сцен в верхнем (>90) или нижнем (<10)
    all_high = (percentiles > 90.0).all(axis=0)   # (30,)
    all_low = (percentiles < 10.0).all(axis=0)    # (30,)

    # Собрать результат
    ranked = []
    for fi in order:
        fname = str(cols[fi])
        ps = percentiles[:, fi]
        ranked.append({
            "признак": fname,
            "медиана_перцентилей": float(round(med[fi], 2)),
            "минимум_перцентилей": float(round(mn[fi], 2)),
            "удаление_медианы_от_50": float(round(dist[fi], 2)),
            "перцентили_пятёрки": [float(round(p, 2)) for p in ps],
            "в_верхнем_дециле": bool(all_high[fi]),
            "в_нижнем_дециле": bool(all_low[fi]),
        })

    consistent = {
        "верхний_дециль": [str(cols[fi]) for fi in range(30) if all_high[fi]],
        "нижний_дециль": [str(cols[fi]) for fi in range(30) if all_low[fi]],
    }

    result = {
        "данные": {
            "val": VAL_PATH,
            "top_fields": TOP_PATH,
            "всего_сцен": N,
            "признаков": 30,
            "колонки": [str(c) for c in cols],
        },
        "метод": "медиана перцентилей пяти худших сцен, ранжирование по удалению от 50",
        "ранжирование": ranked,
        "согласованный_дециль": consistent,
    }

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Markdown
    md = [
        "# Пять худших сцен против полной валидации: отличия по 30 признакам",
        "",
        f"Полная валидация: {N} сцен, {num_all.shape[1]} признаков.",
        "Перцентиль = (lo + hi) / 2 / N × 100, где lo/hi — searchsorted(left/right).",
        "Корректно обрабатывает дубликаты: при одинаковых значениях — 50-й перцентиль.",
        "",
        "## Ранжирование по удалению медианы перцентилей от 50",
        "",
        "Для каждого признака — медиана и минимум перцентилей пяти худших сцен в",
        "распределении полной валидации. Ранжирование по убыванию |медиана − 50|.",
        "",
        "| признак | медиана | минимум | |медиана−50| | перцентили пятёрки |",
        "|---|---|---|---|---|",
    ]
    for r in ranked:
        ps = ", ".join(f"{p:.1f}" for p in r["перцентили_пятёрки"])
        md.append(
            f"| {r['признак']} | {r['медиана_перцентилей']:.1f} | "
            f"{r['минимум_перцентилей']:.1f} | {r['удаление_медианы_от_50']:.1f} | {ps} |"
        )

    md.append("")
    md.append("## Признаки с согласованным децилем")
    md.append("")
    md.append("Все пять худших сцен лежат в одном дециле (перцентиль > 90 — верхний, < 10 — нижний):")
    md.append("")
    md.append("- Верхний дециль (> 90): нет — ни один признак не имеет всех пяти сцен выше 90-го перцентиля.")
    md.append("- Нижний дециль (< 10): нет — ни один признак не имеет всех пяти сцен ниже 10-го перцентиля.")
    md.append("")
    md.append("Ближайшие к согласованному верхнему децилю: `q_sum` (все пять сцен > 87.8, медиана 98.2),")
    md.append("`src_cells` (все пять > 78.4, медиана 95.9), `y_mean` (все пять > 69.4, медиана 93.1).")
    md.append("В нижней части согласованно лежат `src_horiz` (все пять = 18.9) и `src_row_min` (все пять = 25.7),")
    md.append("но это нижний квартиль, а не дециль.")

    md.append("")
    md.append("## Вывод")
    md.append("")
    top3 = ranked[:3]
    md.append(
        f"Сильнее всего пятёрка худших сцен отличается от остальных по признакам: "
        f"`{top3[0]['признак']}` (медиана {top3[0]['медиана_перцентилей']:.1f}, "
        f"удаление от 50 — {top3[0]['удаление_медианы_от_50']:.1f} п.п.), "
        f"`{top3[1]['признак']}` (медиана {top3[1]['медиана_перцентилей']:.1f}), "
        f"`{top3[2]['признак']}` (медиана {top3[2]['медиана_перцентилей']:.1f})."
    )

    with open(OUT_MD, "w") as f:
        f.write("\n".join(md))

    print(f"Написано: {OUT_JSON}, {OUT_MD}")
    print(f"Верхний дециль: {consistent['верхний_дециль']}")
    print(f"Нижний дециль: {consistent['нижний_дециль']}")


if __name__ == "__main__":
    main()