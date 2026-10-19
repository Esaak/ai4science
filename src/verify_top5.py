#!/usr/bin/env python3
"""Независимая проверка перцентилей top5 — через numpy.percentile + rank."""

import json
import numpy as np

VAL_PATH = "data/edison_cache/val.npz"
TOP_PATH = "data/edison_cache/top_fields.npz"
REF_JSON = "results/top5_percentiles.json"

TOL = 0.5  # допустимая разница в п.п.


def main():
    val = np.load(VAL_PATH)
    top = np.load(TOP_PATH)

    num_all = val["num"]
    cols = val["cols"]
    idx = top["idx"]
    num_top = num_all[idx]

    # Метод 2 (независимый): для каждой ячейки — доля full <= значения
    # Используем np.searchsorted на отсортированном массиве
    N = num_all.shape[0]
    sorted_all = np.sort(num_all, axis=0)  # (11632, 30)

    percentiles_v2 = np.zeros((5, 30))
    for i in range(5):
        for j in range(30):
            val_i = num_top[i, j]
            # searchsorted даёт индекс, куда вставить val_i в sorted_all[:, j]
            # это = количество элементов < val_i
            lo = np.searchsorted(sorted_all[:, j], val_i, side='left')
            hi = np.searchsorted(sorted_all[:, j], val_i, side='right')
            # перцентиль: (lo + hi) / 2 / N * 100
            percentiles_v2[i, j] = (lo + hi) / 2.0 / N * 100.0

    # Загружаем референс
    with open(REF_JSON) as f:
        ref = json.load(f)

    ref_p = np.zeros((5, 30))
    for i in range(5):
        for j in range(30):
            ref_p[i, j] = ref["сцены"][i]["признаки"][j]["перцентиль"]

    # Сравниваем
    diff = np.abs(percentiles_v2 - ref_p)
    max_diff = diff.max()
    mean_diff = diff.mean()
    n_over_tol = np.sum(diff > TOL)

    print(f"Метод 2 (searchsorted):")
    print(f"  Макс. расхождение: {max_diff:.4f} п.п.")
    print(f"  Среднее расхождение: {mean_diff:.4f} п.п.")
    print(f"  Ячеек с расхождением > {TOL}: {n_over_tol}")

    if n_over_tol > 0:
        print("\nЯчейки с расхождением > {}: ".format(TOL))
        for i in range(5):
            for j in range(30):
                if diff[i, j] > TOL:
                    print(f"  сцена {int(idx[i])}, {cols[j]}: ref={ref_p[i,j]:.2f}, "
                          f"v2={percentiles_v2[i,j]:.2f}, diff={diff[i,j]:.4f}")

    # Метод 3: ещё один подход — для каждой сцены считаем z-score и переводим в перцентиль
    # через CDF аппроксимацию (параметрический)
    # Но это уже параметрический, лучше сравнить с методом 1 напрямую
    # Метод 1: (rank - 0.5) / N * 100
    # Метод 2: (lo + hi) / 2 / N * 100
    # Они должны совпадать, если нет дубликатов

    # Проверим совпадение методов 1 и 2
    diff_12 = np.abs(percentiles_v2 - ref_p)
    print(f"\nСовпадение методов 1 и 2: max_diff={diff_12.max():.4f}")

    # Топ-3 признака по размаху
    spread_v2 = percentiles_v2.max(axis=0) - percentiles_v2.min(axis=0)
    spread_ref = ref_p.max(axis=0) - ref_p.min(axis=0)
    top3_v2 = np.argsort(-spread_v2)[:3]
    top3_ref = np.argsort(-spread_ref)[:3]
    print(f"\nТоп-3 по методу 2: {[str(cols[j]) for j in top3_v2]}")
    print(f"Топ-3 по референсу: {[str(cols[j]) for j in top3_ref]}")
    print(f"Совпадают: {list(top3_v2) == list(top3_ref)}")

    ok = n_over_tol == 0
    print(f"\n{'✓ Проверка пройдена' if ok else '✗ Проверка не пройдена'}")
    return ok


if __name__ == "__main__":
    ok = main()
    exit(0 if ok else 1)