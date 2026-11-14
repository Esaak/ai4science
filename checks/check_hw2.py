#!/usr/bin/env python3
"""
Проверка ДЗ2: метрики центра концентрации, интеграла и ширины шлейфа.

Часть 1 — функции расчёта для будущего применения к 25 сценам.
Часть 2 — синтетические тесты из раздела 7.5 METHOD.md.

Запуск:  .venv/bin/python checks/check_hw2.py
         .venv/bin/python checks/check_hw2.py --synthetic
"""

import sys
import os
import numpy as np

# ---------------------------------------------------------------------------
# Постоянные сетки
# ---------------------------------------------------------------------------
NX, NY = 128, 128          # число ячеек
DX, DY = 2.0, 2.0           # размер ячейки, м
X = (np.arange(NX) + 0.5) * DX      # координаты центров ячеек по X, x=2*j+1
Y = (np.arange(NY) + 0.5) * DY      # координаты центров ячеек по Y, y=2*i+1

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Основные функции
# ---------------------------------------------------------------------------

def compute_concentration_center(c: np.ndarray, mask: np.ndarray | None = None):
    """
    Центр концентрации как взвешенное концентрацией среднее координат ячеек.

    Параметры
    ---------
    c : np.ndarray  (128, 128)
        Поле концентрации.
    mask : np.ndarray (128, 128) bool, optional
        Маска валидных ячеек. Если None — используются все ячейки.

    Возвращает
    ----------
    (x_c, y_c) : tuple(float, float)
        Координаты центра концентрации в метрах.

    Поднимает ValueError, если Σc[mask] == 0.
    """
    if mask is None:
        mask = np.ones_like(c, dtype=bool)
    if (c * mask).sum() == 0.0:
        raise ValueError(
            "Площадной интеграл концентрации равен нулю — "
            "центр не определён. "
            "Сцена не может быть исключения."
        )
    # Meshgrid по X, Y: indexing="xy" → Xg по столбцам, Yg по строкам
    Xg, Yg = np.meshgrid(X, Y, indexing="xy")
    total = (c * mask).sum()
    x_c = ((c * mask) * Xg).sum() / total
    y_c = ((c * mask) * Yg).sum() / total
    return float(x_c), float(y_c)


def compute_area_integral(c: np.ndarray, mask: np.ndarray | None = None) -> float:
    """
    Площадной интеграл концентрации I = Σ c_ij · Δx · Δy по валидным ячейкам.

    Возвращает float — интеграл.
    """
    if mask is None:
        mask = np.ones_like(c, dtype=bool)
    return float((c * mask).sum() * DX * DY)


def compute_radial_width(c: np.ndarray, center, mask: np.ndarray | None = None) -> float:
    """
    Радиальная ширина шлейфа W — взвешенное концентрацией стандартное
    отклонение расстояний ячеек от центра концентрации.

    W = sqrt( Σ c_ij · ((x_ij - x_c)² + (y_ij - y_c)²) / Σ c_ij )

    Возвращает float — ширина в метрах.
    """
    if mask is None:
        mask = np.ones_like(c, dtype=bool)
    x_c, y_c = center
    Xg, Yg = np.meshgrid(X, Y, indexing="xy")
    r2 = (Xg - x_c) ** 2 + (Yg - y_c) ** 2
    total = (c * mask).sum()
    if total == 0.0:
        raise ValueError("Интеграл = 0 при вычислении ширины.")
    return float(np.sqrt(((c * mask) * r2).sum() / total))


def euclidean_error(c1_center, c2_center) -> float:
    """Евклидова ошибка между двумя центрами концентрации."""
    return float(np.sqrt(
        (c1_center[0] - c2_center[0]) ** 2 +
        (c1_center[1] - c2_center[1]) ** 2
    ))

# ---------------------------------------------------------------------------
# Печать для человека и машины
# ---------------------------------------------------------------------------

def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def fail(msg: str, code: int = 1) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(code)


# ---------------------------------------------------------------------------
# Часть 2 — синтетические тесты (раздел 7.5 METHOD.md)
# ---------------------------------------------------------------------------

def test_additivity() -> None:
    """Тест 1: Аддитивность площадного интеграла.
    c1 и c2 непересекающиеся; c_syn = c1 + c2  →  Σc_syn = Σc1 + Σc2."""
    c1 = np.zeros((NX, NY))
    c1[30:35, 40:45] = 1.0
    c2 = np.zeros((NX, NY))
    c2[60:65, 80:85] = 2.0
    c_syn = c1 + c2
    I1 = compute_area_integral(c1)
    I2 = compute_area_integral(c2)
    Isyn = compute_area_integral(c_syn)
    rel_err = abs(Isyn - (I1 + I2)) / (I1 + I2 + 1e-30)
    if rel_err < 1e-10:
        ok("test_additivity: Σc_syn = Σc1 + Σc2  (rel_err={:.2e})".format(rel_err))
    else:
        fail("test_additivity: rel_err={:.2e}".format(rel_err), code=1)


def test_single_cell() -> None:
    """Тест 7: Единичная ненулевая ячейка.
    row=3, col=4 → центр (x=9, y=7) при DX=DY=2."""
    c = np.zeros((NX, NY))
    c[3, 4] = 1.0
    center = compute_concentration_center(c)

    # (row=3, col=4) → X[4]=(4+0.5)*2=9, Y[3]=(3+0.5)*2=7
    expected = (9.0, 7.0)
    if abs(center[0] - expected[0]) < 1e-10 and \
       abs(center[1] - expected[1]) < 1e-10:
        ok("test_single_cell: row3,col4 = ({:.1f},{:.1f})".format(
            center[0], center[1]))
    else:
        fail("test_single_cell: ({:.1f},{:.1f}); ожид. {}".format(
            center[0], center[1], expected), code=1)


def test_scale_invariance() -> None:
    """Тест 2: Инвариантность центра к масштабированию.
    Центр для c и k·c должен совпадать."""
    c = np.zeros((NX, NY))
    c[30:40, 40:50] = 1.0
    k = 3.7
    c_k = c * k
    center = compute_concentration_center(c)
    center_k = compute_concentration_center(c_k)
    err = euclidean_error(center, center_k)
    if err < 1e-10:
        ok("test_scale_invariance: центры совпадают (err={:.2e})".format(err))
    else:
        fail("test_scale_invariance: err={:.2e}".format(err), code=1)


def test_mask() -> None:
    """Тест 3: Корректность маски.
    Поле с ненулевыми концентрациями под зданиями (внутри маски) —
    ячейки под зданиями исключены из расчёта центра и интеграла."""
    c = np.zeros((NX, NY))
    c[30:40, 40:50] = 1.0  # 10×10 пятно, сумма = 100
    c[50, 50] = 100.0     # один чужой пиксель под зданием

    mask = np.ones((NX, NY), dtype=bool)
    mask[50, 50] = False

    I_masked = compute_area_integral(c, mask)
    I_all = compute_area_integral(c, None)

    # Пятно: 100 ячеек × 2×2 = 400; центр пятна: rows 30..39, cols 40..49
    # X[40:50] = (40.5..49.5)*2 = [81,83,..,99] → среднее = 90
    # Y[30:40] = (30.5..39.5)*2 = [61,63,..,79] → среднее = 70
    center_masked = compute_concentration_center(c, mask)
    expected_center = (90.0, 70.0)
    if abs(I_masked - 400.0) < 0.5 and \
       euclidean_error(center_masked, expected_center) < 1e-10:
        ok("test_mask: I_masked={:.0f} (отсечён пиксель c[50,50]), "
           "центр=({:.1f},{:.1f})".format(I_masked, center_masked[0], center_masked[1]))
    else:
        fail("test_mask: I_masked={:.0f}, центр={:.1f},{:.1f}; "
             "ожид. 400, (90,70)".format(I_masked, center_masked[0], center_masked[1]),
             code=1)


def test_shift() -> None:
    """Тест 4: Смещение пятна на одну ячейку по столбцу.
    c_shifted — то же пятно, сдвинутое на 1 колонку (2 м) по X, Y без изменения."""
    c = np.zeros((NX, NY))
    c[30:35, 40:45] = 1.0
    c_shifted = np.zeros((NX, NY))
    c_shifted[30:35, 41:46] = 1.0  # сдвиг на 1 колонку по X

    center = compute_concentration_center(c)
    center_shifted = compute_concentration_center(c_shifted)

    dx = abs(center_shifted[0] - center[0] - 2.0)
    dy = abs(center_shifted[1] - center[1])
    if dx < 1e-10 and dy < 1e-10:
        ok("test_shift: X+2={:.6f}, ΔY={:.2e}".format(dx, dy))
    else:
        fail("test_shift: dx={:.2e}, dy={:.2e} (ожид. 0,0)".format(dx, dy), code=1)


def test_rotation() -> None:
    """Тест 5: Поворот пятна на 90°.
    np.rot90 → (x,y) → (y, 256-x) с допуском 1e-10."""
    # Асимметричное пятно
    c = np.zeros((NX, NY))
    c[80:90, 90:100] = 1.0
    c[70:75, 95:105] = 2.0  # смещено — не симметрично

    c_rotated = np.rot90(c, k=1)
    center = compute_concentration_center(c)
    center_rot = compute_concentration_center(c_rotated)

    x0, y0 = center
    x_expected = y0
    y_expected = 256.0 - x0
    if abs(center_rot[0] - x_expected) < 1e-10 and \
       abs(center_rot[1] - y_expected) < 1e-10:
        ok("test_rotation: (x0,y0)=({:.1f},{:.1f}) → "
           "({:.1f},{:.1f})".format(x0, y0, center_rot[0], center_rot[1]))
    else:
        fail("test_rotation: ({:.1f},{:.1f}) → ({:.1f},{:.1f}); "
             "ожид. ({:.1f},{:.1f})".format(
                 x0, y0, center_rot[0], center_rot[1], x_expected, y_expected),
             code=1)


def test_zero_field() -> None:
    """Тест 6: Нулевое поле.
    Все ячейки = 0 → compute_concentration_center поднимает ValueError."""
    c = np.zeros((NX, NY))
    try:
        compute_concentration_center(c)
        fail("test_zero_field: не поднята ошибка", code=1)
    except ValueError:
        ok("test_zero_field: ValueError при Σc = 0")

# ---------------------------------------------------------------------------
# daemon: --synthetic
# ---------------------------------------------------------------------------

def run_synthetic():
    """Запустить все синтетические тесты."""
    tests = [
        ("test_additivity",     test_additivity),
        ("test_scale_invariance", test_scale_invariance),
        ("test_mask",           test_mask),
        ("test_shift",          test_shift),
        ("test_rotation",       test_rotation),
        ("test_zero_field",     test_zero_field),
        ("test_single_cell",    test_single_cell),
    ]
    failed = []
    for name, fn in tests:
        try:
            fn()
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed.append(name)
    if failed:
        print("\nНе пройдено: {}".format(", ".join(failed)))
        sys.exit(1)
    print("\nВсе {} синтетических тестов пройдены.".format(len(tests)))
    sys.exit(0)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--synthetic":
        run_synthetic()
        return

    # Проверка локального пакета 25 сцен (geometry_id 150–174):
    archive = "data/edison_cache/val.npz"
    if not os.path.isfile(archive):
        print("нет локального пакета")
        sys.exit(1)
    try:
        data = np.load(archive)
        scenes = data["idx"].shape[0] if "idx" in data else 0
    except KeyError:
        scenes = 0

    if scenes < 25:
        print("нет локального пакета")
        sys.exit(1)

    print("Сцена: {}, геометрии 150–174.".format(scenes))

if __name__ == "__main__":
    main()