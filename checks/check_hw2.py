#!/usr/bin/env python3
"""
Проверка ДЗ2: метрики центра концентрации, интеграла и ширины шлейфа.

Загружает архив из fixtures/hw2/plumes.npz (25 сцен, geometry_id 150–174),
проверяет SHA-256, схему, данные и считает:
  - евклидову ошибку центра (LES vs current, LES vs baseline)
  - медиану ошибки current
  - число сцен с ошибкой current ≤ 20 м
Вердикт: медиана ≤ 10 м И счёт ≥ 20/25 → код 0, иначе код 1.

Запуск:  .venv/bin/python checks/check_hw2.py
"""

import sys
import os
import json
import hashlib
import argparse
import numpy as np

# ---------------------------------------------------------------------------
# Постоянные сетки  (шаг 2 м, область 256×256 м)
# ---------------------------------------------------------------------------
NX, NY = 128, 128
DX, DY = 2.0, 2.0
X = (np.arange(NX) + 0.5) * DX      # x=2*j+1    метры  [1, 255]
Y = (np.arange(NY) + 0.5) * DY      # y=2*i+1    метры  [1, 255]

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def compute_concentration_center(c: np.ndarray, mask: np.ndarray | None = None):
    """
    Центр концентрации: взвешенное концентрацией среднее координат ячеек.
    Параметры
    ---------
    c : (128, 128)
    mask : (128, 128) bool, optional
    Возврат
    -------
    (x_c, y_c) : float, float
    Поднимает ValueError при Σc[mask] == 0.
    """
    if mask is None:
        mask = np.ones_like(c, dtype=bool)
    if (c * mask).sum() == 0.0:
        raise ValueError("Σc[mask]=0 — центр не определён.")
    Xg, Yg = np.meshgrid(X, Y, indexing="xy")
    total = (c * mask).sum()
    return float(((c * mask) * Xg).sum() / total), \
           float(((c * mask) * Yg).sum() / total)


def compute_area_integral(c: np.ndarray, mask: np.ndarray | None = None) -> float:
    """I = Σ c·Δx·Δy по валидным ячейкам."""
    if mask is None:
        mask = np.ones_like(c, dtype=bool)
    return float((c * mask).sum() * DX * DY)


def compute_radial_width(c: np.ndarray, center, mask: np.ndarray | None = None) -> float:
    """W = sqrt( Σ c·r² / Σ c ) — радиальная ширина."""
    if mask is None:
        mask = np.ones_like(c, dtype=bool)
    x_c, y_c = center
    Xg, Yg = np.meshgrid(X, Y, indexing="xy")
    r2 = (Xg - x_c) ** 2 + (Yg - y_c) ** 2
    total = (c * mask).sum()
    if total == 0.0:
        raise ValueError("Σc=0 при вычислении ширины.")
    return float(np.sqrt(((c * mask) * r2).sum() / total))


def euclidean_error(c1, c2) -> float:
    return float(np.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2))

# ---------------------------------------------------------------------------
# Вывод
# ---------------------------------------------------------------------------

def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def fail(msg: str, code: int = 1) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(code)

# ===========================================================================
# 1. СИНТЕТИЧЕСКИЕ ТЕСТЫ
# ===========================================================================

def test_additivity() -> None:
    c1 = np.zeros((NX, NY)); c1[30:35, 40:45] = 1.0
    c2 = np.zeros((NX, NY)); c2[60:65, 80:85] = 2.0
    Isyn = compute_area_integral(c1 + c2)
    rel = abs(Isyn - (compute_area_integral(c1) + compute_area_integral(c2))) / (Isyn + 1e-30)
    if rel < 1e-10:
        ok(f"test_additivity: rel_err={rel:.2e}")
    else:
        fail(f"test_additivity: rel_err={rel:.2e}")


def test_scale_invariance() -> None:
    c = np.zeros((NX, NY)); c[30:40, 40:50] = 1.0
    tp = euclidean_error(compute_concentration_center(c),
                         compute_concentration_center(c * 3.7))
    if tp < 1e-10:
        ok(f"test_scale_invariance: err={tp:.2e}")
    else:
        fail(f"test_scale_invariance: err={tp:.2e}")


def test_mask() -> None:
    c = np.zeros((NX, NY)); c[30:40, 40:50] = 1.0; c[50, 50] = 100.0
    mask = np.ones((NX, NY), dtype=bool); mask[50, 50] = False
    I = compute_area_integral(c, mask)
    center = compute_concentration_center(c, mask)
    err = abs(I - 400.0) + euclidean_error(center, (90.0, 70.0))
    if err < 0.5:
        ok(f"test_mask: I={I:.0f} центр=({center[0]:.1f},{center[1]:.1f})")
    else:
        fail(f"test_mask: I={I:.0f} центр=({center[0]:.1f},{center[1]:.1f})")


def test_shift() -> None:
    c = np.zeros((NX, NY)); c[30:35, 40:45] = 1.0
    cs = np.zeros((NX, NY)); cs[30:35, 41:46] = 1.0
    x_err = abs(compute_concentration_center(cs)[0] - compute_concentration_center(c)[0] - 2.0)
    y_err = abs(compute_concentration_center(cs)[1] - compute_concentration_center(c)[1])
    if x_err < 1e-10 and y_err < 1e-10:
        ok(f"test_shift: dx={x_err:.2e}, dy={y_err:.2e}")
    else:
        fail(f"test_shift: dx={x_err:.2e}, dy={y_err:.2e}")


def test_rotation() -> None:
    c = np.zeros((NX, NY)); c[80:90, 90:100] = 1.0; c[70:75, 95:105] = 2.0
    center = compute_concentration_center(c)
    center_rot = compute_concentration_center(np.rot90(c, k=1))
    dx = abs(center_rot[0] - center[1])
    dy = abs(center_rot[1] - (256.0 - center[0]))
    if dx < 1e-10 and dy < 1e-10:
        ok(f"test_rotation: dx={dx:.2e} dy={dy:.2e}")
    else:
        fail(f"test_rotation: dx={dx:.2e} dy={dy:.2e}")


def test_zero_field():
    c = np.zeros((NX, NY))
    try:
        compute_concentration_center(c)
        fail("test_zero_field: нет ValueError")
    except ValueError:
        ok("test_zero_field: ValueError при Σc=0")


def test_single_cell():
    c = np.zeros((NX, NY)); c[3, 4] = 1.0
    center = compute_concentration_center(c)
    if abs(center[0] - 9.0) < 1e-10 and abs(center[1] - 7.0) < 1e-10:
        ok(f"test_single_cell: ({center[0]:.1f},{center[1]:.1f})")
    else:
        fail(f"test_single_cell: ({center[0]:.1f},{center[1]:.1f})")


def test_width_shift_invariance():
    """Width of a compact spot is invariant under shift when using own
    center. Two equal peaks at known distance 10 m, plus a shifted replica.
    """
    # Two equal single-cell peaks 20 m apart (10 cells)
    c = np.zeros((NX, NY))
    c[3, 4] = 1.0   # x=9, y=7
    c[3, 14] = 1.0  # x=29, y=7
    center = compute_concentration_center(c)
    w = compute_radial_width(c, center)
    if abs(w - 10.0) < 1e-6:
        ok(f"test_width_shift_invariance: W={w:.6f} m (exp 10.0) own center")
    else:
        fail(f"test_width_shift_invariance: W={w:.6f} != 10.0 own center")
    # Shifted external center: width changes (formula works)
    center_shifted = (24.0, 7.0)
    w_shifted = compute_radial_width(c, center_shifted)
    expected_w_shifted = np.sqrt(125.0)
    if abs(w_shifted - expected_w_shifted) < 1e-6:
        ok(f"test_width_shift_invariance: W_shifted={w_shifted:.6f} (exp {expected_w_shifted:.6f})")
    else:
        fail(f"test_width_shift_invariance: W_shifted={w_shifted:.6f} != {expected_w_shifted:.6f}")
    # Real shift: move both peaks by (+3 row, +4 col), check own center width
    c2 = np.zeros((NX, NY))
    c2[3 + 3, 4 + 4] = 1.0   # shift +3 row, +4 col -> x=17, y=13
    c2[3 + 3, 14 + 4] = 1.0  # x=37, y=13
    center2 = compute_concentration_center(c2)
    w2 = compute_radial_width(c2, center2)
    if abs(w2 - 10.0) < 1e-6:
        ok(f"test_width_shift_invariance (shifted): W2={w2:.6f} m (exp 10.0)")
    else:
        fail(f"test_width_shift_invariance: W2={w2:.6f} != 10.0 shifted", code=1)
    if abs(center2[0] - 27.0) < 1e-6 and abs(center2[1] - 13.0) < 1e-6:
        ok(f"test_width_shift_invariance: center2={center2} OK")
    else:
        fail(f"test_width_shift_invariance: center2={center2} != (27.0,13.0)", code=1)


SYNTHETICS = [
    ("test_additivity", test_additivity),
    ("test_scale_invariance", test_scale_invariance),
    ("test_mask", test_mask),
    ("test_shift", test_shift),
    ("test_rotation", test_rotation),
    ("test_zero_field", test_zero_field),
    ("test_single_cell", test_single_cell),
    ("test_width_shift_invariance", test_width_shift_invariance),
]

# ===========================================================================
# 2. ЗАГРУЗКА АРХИВА + СХЕМА + SHA-256
# ===========================================================================

def verify_archive(archive: str, manifest_path: str):
    """Проверка SHA-256, схемы, данных."""
    # --- SHA-256 ---
    h = hashlib.sha256()
    with open(archive, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    actual_sha = h.hexdigest()

    with open(manifest_path) as f:
        mf = json.load(f)
    expected_sha = mf.get("archive_sha256", "")
    if actual_sha != expected_sha:
        fail(f"SHA-256 не совпадает: ожидаем {expected_sha[:12]}… = "
             f"{actual_sha[:12]}…", code=1)
    ok(f"archive SHA-256 OK ({actual_sha[:16]}…)")

    # --- Схема ---
    d = np.load(archive, allow_pickle=True)

    expected_keys = {"geometry_id", "scene_name", "les", "current", "baseline", "valid"}
    actual_keys = set(d.keys())
    if actual_keys != expected_keys:
        fail(f"Схема: ключи {actual_keys} != {expected_keys}", code=1)
    ok(f"схема ключей OK: {sorted(actual_keys)}")

    # geometry_id  (25,) uint16,  150–174
    if d["geometry_id"].shape != (25,):
        fail(f"geometry_id shape {d['geometry_id'].shape} != (25,)", code=1)
    if not np.array_equal(np.sort(d["geometry_id"]), np.arange(150, 175)):
        fail(f"geometry_id не 150–174", code=1)
    ok(f"geometry_id 150–174 OK")

    # scene_name   (25, str), уникальные
    names = d["scene_name"]
    if len(np.unique(names)) != 25:
        fail(f"scene_name: duplicates", code=1)
    ok(f"scene_name 25 уникальных OK")

    # les / current / baseline  (25,4,128,128) float32
    for field in ("les", "current", "baseline"):
        arr = d[field]
        if arr.shape != (25, 4, 128, 128):
            fail(f"{field} shape {arr.shape} != (25,4,128,128)", code=1)
        if not np.all(np.isfinite(arr)):
            fail(f"{field} содержит inf/nan", code=1)
        if np.any(arr < 0):
            fail(f"{field} содержит отрицательные значения", code=1)
        z1_int = arr[:, 0, :, :].sum(axis=(1, 2)) * DX * DY
        if np.any(z1_int == 0):
            fail(f"{field}: нулевой интеграл Z1, сцены "
                 f"{d['geometry_id'][z1_int == 0].tolist()}", code=1)
    ok("les/current/baseline shape, finite, non-neg, non-zero Z1 integral OK")

    # valid  (25,4,128,128) bool
    if d["valid"].shape != (25, 4, 128, 128) or d["valid"].dtype != bool:
        fail(f"valid: shape {d['valid'].shape} dtype {d['valid'].dtype}", code=1)
    ok("valid bool (25,4,128,128) OK")

    # Хотя бы одна допустимая ячейка Z1 в каждой сцене
    for i in range(25):
        n_valid = int(d["valid"][i, 0, :, :].sum())
        if n_valid == 0:
            fail(f"valid: 0 допустимых ячеек Z1, сцена {d['geometry_id'][i]}", code=1)
    ok("≥1 допустимая ячейка Z1 в каждой сцене OK")

    # Нулевые суммы по valid (проверка согласованности)
    for field in ("les", "current", "baseline"):
        arr = d[field].astype(np.float64)
        for i in range(25):
            mask = d["valid"][i, 0, :, :]
            s = (arr[i, 0, :, :] * mask).sum()
            if s == 0.0:
                fail(f"{field}: нулевая сумма по valid в Z1, сцена {d['geometry_id'][i]}", code=1)
    ok("суммы по valid > 0 во всех сценах OK")

    # Общая маска valid (25,4,128,128) применяется к полям по построению;
    # происхождение маски — метаданные экспорта.
    # SHA-256 подтверждает целостность архивa, а не истинность метаданных.

    # Не закрываем — compute_all_metrics ещё читает
    return d


# ===========================================================================
# 3. РАСЧЁТ МЕТОРИК
# ===========================================================================

def compute_all_metrics(d, out_dir: str):
    """Считает евклидову ошибку центра для 25 сцен, сохраняет таблицу."""
    N = 25
    errors_cur = np.zeros(N)
    errors_base = np.zeros(N)
    ids = d["geometry_id"]

    for i in range(N):
        mask = d["valid"][i, 0, :, :]  # Z1
        c_les = d["les"][i, 0, :, :]
        c_cur = d["current"][i, 0, :, :]
        c_base = d["baseline"][i, 0, :, :]

        try:
            center_les = compute_concentration_center(c_les, mask)
        except ValueError:
            fail(f"геометрия {ids[i]}: LES Σc=0 — нельзя", code=1)

        try:
            center_cur = compute_concentration_center(c_cur, mask)
        except ValueError:
            fail(f"геометрия {ids[i]}: current Σc=0 — нельзя", code=1)

        try:
            center_base = compute_concentration_center(c_base, mask)
        except ValueError:
            fail(f"геометрия {ids[i]}: baseline Σc=0 — нельзя", code=1)

        errors_cur[i] = euclidean_error(center_les, center_cur)
        errors_base[i] = euclidean_error(center_les, center_base)

    median_cur = float(np.median(errors_cur))
    median_base = float(np.median(errors_base))

    # Threshold score for current: error <= 20m
    count_cur = int((errors_cur <= 20.0).sum())
    count_base = int((errors_base <= 20.0).sum())

    # Wide integral and width for descriptive output
    widths_cur = np.zeros(N)
    widths_base = np.zeros(N)
    integrals_les = np.zeros(N)
    integrals_cur_out = np.zeros(N)
    integrals_base = np.zeros(N)
    for i in range(N):
        mask = d["valid"][i, 0, :, :]
        c_les = d["les"][i, 0, :, :]
        c_cur = d["current"][i, 0, :, :]
        c_base = d["baseline"][i, 0, :, :]
        try:
            center_cur = compute_concentration_center(c_cur, mask)
        except ValueError:
            center_cur = None
        try:
            center_base = compute_concentration_center(c_base, mask)
        except ValueError:
            center_base = None
        try:
            widths_cur[i] = compute_radial_width(c_cur, center_cur, mask)
        except ValueError:
            widths_cur[i] = float('nan')
        try:
            widths_base[i] = compute_radial_width(c_base, center_base, mask)
        except ValueError:
            widths_base[i] = float('nan')
        integrals_les[i] = compute_area_integral(c_les, mask)
        integrals_cur_out[i] = compute_area_integral(c_cur, mask)
        integrals_base[i] = compute_area_integral(c_base, mask)

    # --- Save ---
    os.makedirs(out_dir, exist_ok=True)

    # Table CSV
    dot = "-" * 105
    lines = [
        dot,
        f"{'geom':>5}  {'scene_name':>30}  {'err_cur[m]':>12}  {'err_base[m]':>13}"
        f"  {'I_les':>12}  {'I_cur':>12}  {'I_base':>12}"
        f"  {'W_cur[m]':>11}  {'W_base[m]':>11}",
        dot,
    ]
    for i in range(N):
        lines.append(
            f"{ids[i]:>5}  {str(d['scene_name'][i]):>30}  "
            f"{errors_cur[i]:>12.4f}  {errors_base[i]:>13.4f}  "
            f"{integrals_les[i]:>12.2f}  {integrals_cur_out[i]:>12.2f}  "
            f"{integrals_base[i]:>12.2f}  "
            f"{widths_cur[i]:>11.2f}  {widths_base[i]:>11.2f}"
        )
    lines.append(dot)

    # CSV version
    csv_lines = ["geometry_id,scene_name,errors_cur,errors_baseline,"
                 "integral_les,integral_current,integral_baseline,"
                 "width_current,width_baseline"]
    for i in range(N):
        csv_lines.append(
            f"{ids[i]},{d['scene_name'][i]},{errors_cur[i]:.6f},{errors_base[i]:.6f},"
            f"{integrals_les[i]:.6f},{integrals_cur_out[i]:.6f},{integrals_base[i]:.6f},"
            f"{widths_cur[i]:.6f},{widths_base[i]:.6f}"
        )

    # JSON summary
    summary = {
        "n": int(N),
        "median_error_current_m": float(median_cur),
        "median_error_baseline_m": float(median_base),
        "max_error_current_m": float(errors_cur.max()),
        "max_error_baseline_m": float(errors_base.max()),
        "count_error_le20_current": int(count_cur),
        "count_error_le20_baseline": int(count_base),
        "mean_error_current_m": float(errors_cur.mean()),
        "mean_error_baseline_m": float(errors_base.mean()),
    }

    with open(os.path.join(out_dir, "hw2_table.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(out_dir, "hw2_results.csv"), "w") as f:
        f.write("\n".join(csv_lines) + "\n")
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    return summary, lines, csv_lines

# ===========================================================================
# CLI парсер
# ===========================================================================

def build_parser():
    """Парсер командной строки: три взаимно исключающих режима."""
    parser = argparse.ArgumentParser(
        description="ДЗ2 verifikator: метрики центра концентрации, интеграла и ширины шлейфа.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Режимы (несовместимы): "
            "--synthetic — только синтетические тесты; "
            "--dry-run — синтетика + проверка архива без расчёта таблицы; "
            "без опций — полный расчёт и вердикт."
        ),
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--synthetic",
        action="store_true",
        help="Только синтетические тесты. Не требует архива и manifest. Код 0 при успехе.",
    )
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Синтетика + проверка архива/схемы/маски/нулевых сумм. Без расчёта таблицы, без записи результатов.",
    )
    return parser


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    parser = build_parser()
    args = parser.parse_args()

    archive   = "fixtures/hw2/plumes.npz"
    manifest  = "fixtures/hw2/manifest.json"
    out_dir   = "results/hw2"

    print("=" * 80)
    print("ДЗ2 verifikator: метрики центра концентрации")
    print("=" * 80)

    # -- 1. Синтетика (общий для всех режимов) --
    print("\n--- 1. Синтетические тесты ---")
    failed_synth = []
    for name, fn in SYNTHETICS:
        try:
            fn()
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed_synth.append(name)
    if failed_synth:
        fail(f"Синтетика: провалены {failed_synth}", code=1)
    print(f"\nВсе {len(SYNTHETICS)} синтетических тестов пройдены.\n")

    # -- --synthetic --
    if args.synthetic:
        print("Режим --synthetic: синтетика пройдена, выход.")
        sys.exit(0)

    # -- 2. Архив (общий для dry-run и полного режима) --
    print("--- 2. Проверка архива ---")
    d = verify_archive(archive, manifest)
    print()

    # -- --dry-run --
    if args.dry_run:
        print("Режим --dry-run: архив проверен, выход без расчёта таблицы.")
        sys.exit(0)

    # -- 3. Расчёт ---
    print("--- 3. Расчёт метрик ---")
    summary, txt_lines, csv_lines = compute_all_metrics(d, out_dir)

    # -- 4. Вердикт ---
    print("\n" + "=" * 80)
    print("ИТОГИ")
    print("=" * 80)
    for ln in txt_lines[-5:]:
        print(ln)

    median_cur = summary["median_error_current_m"]
    count_cur  = summary["count_error_le20_current"]

    print(f"\nМедиана ошибки current:   {median_cur:.4f} м")
    print(f"Сцен с ошибкой ≤ 20 м:   {count_cur} / 25")

    cond1 = median_cur <= 10.0
    cond2 = count_cur >= 20
    accepted = cond1 and cond2

    print(f"\nУсловие 1 (медиана ≤ 10 м):  {'ДА' if cond1 else 'НЕТ'}")
    print(f"Условие 2 (≥ 20 из 25):      {'ДА' if cond2 else 'НЕТ'}")
    print(f"Вердикт: {'✓ ПРИНЯТА' if accepted else '✗ НЕ ПРИНЯТА'} (Модель combined_family_ft_best)")

    # Таблица в файл — уже сохранена.

    # Сохраняем commit имя методики
    # (За этот скрипт отвечает git-коммит основной ветки, а не 9c3c149 — пилот ИИ-ассистента)
    print(f"\nИсточники данных: {archive}")
    print(f"Верификатор: checks/check_hw2.py")
    print("=" * 80)

    sys.exit(0 if accepted else 1)


if __name__ == "__main__":
    main()