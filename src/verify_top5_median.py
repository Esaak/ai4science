#!/usr/bin/env python3
"""Независимая проверка ранжирования top5 по медиане перцентилей.

Метод 2 (независимый): перцентиль = (число элементов < v + 0.5 * число равных) / N * 100,
считается прямым перебором np.sum, а не searchsorted. Затем медиана и минимум по пяти
сценам, ранжирование по |медиана - 50| — сравнивается с results/top5_median_rank.json.
"""

import json
import numpy as np

VAL_PATH = "data/edison_cache/val.npz"
TOP_PATH = "data/edison_cache/top_fields.npz"
REF_JSON = "results/top5_median_rank.json"

TOL = 0.5  # допустимая разница в п.п.


def main():
    val = np.load(VAL_PATH)
    top = np.load(TOP_PATH)

    num_all = val["num"]
    cols = val["cols"]
    idx = top["idx"]
    num_top = num_all[idx]
    N = num_all.shape[0]

    # Метод 2: прямой перебор — доля строго меньше + половина равных
    percentiles_v2 = np.zeros((5, 30))
    for i in range(5):
        for j in range(30):
            v = num_top[i, j]
            col = num_all[:, j]
            less = np.sum(col < v)
            eq = np.sum(col == v)
            percentiles_v2[i, j] = (less + 0.5 * eq) / N * 100.0

    # Медиана и минимум, ранжирование
    med_v2 = np.median(percentiles_v2, axis=0)
    mn_v2 = percentiles_v2.min(axis=0)
    dist_v2 = np.abs(med_v2 - 50.0)
    order_v2 = np.argsort(-dist_v2)

    # Загружаем референс
    with open(REF_JSON) as f:
        ref = json.load(f)

    ref_order = [r["признак"] for r in ref["ранжирование"]]
    ref_med_by_name = {r["признак"]: r["медиана_перцентилей"] for r in ref["ранжирование"]}
    ref_med = np.array([ref_med_by_name[str(c)] for c in cols])

    # Сравнение перцентилей — сопоставление по имени признака
    ref_by_name = {r["признак"]: r["перцентили_пятёрки"] for r in ref["ранжирование"]}
    ref_p = np.zeros((5, 30))
    for j in range(30):
        name = str(cols[j])
        ref_p[:, j] = ref_by_name[name]

    diff = np.abs(percentiles_v2 - ref_p)
    max_diff = diff.max()
    n_over = np.sum(diff > TOL)

    print(f"Метод 2 (прямой перебор):")
    print(f"  Макс. расхождение перцентилей: {max_diff:.4f} п.п.")
    print(f"  Ячеек с расхождением > {TOL}: {n_over}")

    # Сравнение ранжирования
    order_v2_names = [str(cols[j]) for j in order_v2]
    match = order_v2_names == ref_order
    print(f"  Ранжирование совпадает: {match}")
    if not match:
        print(f"    Метод 2: {order_v2_names[:10]}")
        print(f"    Референс: {ref_order[:10]}")

    # Сравнение медиан
    med_diff = np.abs(med_v2 - ref_med)
    print(f"  Макс. расхождение медиан: {med_diff.max():.4f} п.п.")

    ok = n_over == 0 and match
    print(f"\n{'✓ Проверка пройдена' if ok else '✗ Проверка не пройдена'}")
    return ok


if __name__ == "__main__":
    ok = main()
    exit(0 if ok else 1)