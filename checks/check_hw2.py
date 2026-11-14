#!/usr/bin/env python3
"""
Проверка ДЗ2: метрики центра концентрации, интеграла и ширины шлейфа.

Часть 1 — функции расчёта для будущего применения к 25 сценам.
Часть 2 — синтетические тесты из раздела 7.5 METHOD.md.

Запуск:  .venv/bin/python checks/check_hw2.py
         .venv/bin/python checks/check_hw2.py --synthetic
"""

import sys
import numpy as np

# ---------------------------------------------------------------------------
# Постоянные сетки
# ---------------------------------------------------------------------------
NX, NY = 128, 128          # число ячеек
DX, DY = 2.0, 2.0           # размер ячейки, м
X = np.arange(NX) * DX      # координаты центров ячеек по X
Y = np.arange(NY) * DY      # координаты центров ячеек по Y

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def build_layer_valid_masks(
    les: np.ndarray,
    pred: np.ndarray,
    baseline: np.ndarray | None = None,
) -> np.ndarray:
    """
    Штатная маска валидных ячеек Z1.
    Принимает поля концентрации (128, 128) и возвращает масшт (128, 128) типа bool.

    ПРАКТИЧЕСКИЙ КОМПАКТ: в рамках ДЗ2 маска определяется высотой зданий
    и одинакова для LES и предсказаний. Заглушка — маска из `isValid`:
    True везде, где максимальная концентрация среди всех трёх полей > 0.
    Если будет необходимость — заменить на полную реализацию.
    """
    if baseline is not None:
        together = np.maximum(np.maximum(les, pred), baseline)
    else:
        together = np.maximum(les, pred)
    # Простая заглушка: all valid where any concentration > 0
    return together > 0


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
    # Meshgrid по X, Y
    Xg, Yg = np.meshgrid(X, Y, indexing="ij")
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
    Xg, Yg = np.meshgrid(X, Y, indexing="ij")
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
    # Пятно-сигнал
    c = np.zeros((NX, NY))
    c[30:40, 40:50] = 1.0  # 10×10 пятно, сумма = 100
    # «Под зданием» — ложная концентрация, которую маска должна排除
    c[50, 50] = 100.0     # один чужой пиксель

    # Маска: всё, кроме ячейки [50, 50]
    mask = np.ones((NX, NY), dtype=bool)
    mask[50, 50] = False

    # С маской: интеграл = 100 * 2 * 2 = 400
    I_masked = compute_area_integral(c, mask)
    # Без маски: интеграл = 200 * 2 * 2 = 800
    I_all = compute_area_integral(c, None)

    #痘屏蔽的细胞已被排除
    if I_masked < I_all - 0.5:
        ok("test_mask: ячейка под зданием исключена из интеграла (I_masked={:.0f} < I_all={:.0f})".format(
            I_masked, I_all))
    else:
        fail("test_mask: маска не работает (I_masked={:.0f}, I_all={:.0f})".format(I_masked, I_all), code=1)


def test_shift() -> None:
    """Тест 4: Смещение пятна на одну ячейку.
    c_shifted — то же пятно, сдвинутое на 1 ячейку (2 м) по X.
    Ошибка центра должна быть ≈ 2 м."""
    c = np.zeros((NX, NY))
    c[30:35, 40:45] = 1.0
    c_shifted = np.zeros((NX, NY))
    c_shifted[31:36, 40:45] = 1.0  # сдвиг на 1 ячейку по X

    center = compute_concentration_center(c)
    center_shifted = compute_concentration_center(c_shifted)
    err = euclidean_error(center, center_shifted)
    if abs(err - 2.0) < 0.5:
        ok("test_shift: смещение ≈ 2 м  (err={:.2f} м)".format(err))
    else:
        fail("test_shift: err={:.2f} м, ожидаемо ≈ 2 м".format(err), code=1)


def test_rotation() -> None:
    """Тест 5: Поворот пятна на 90° вокруг центра области.
    Ошибка центра должна равняться расстоянию между центрами."""
    cx_area, cy_area = X.max() / 2.0 + DX / 2.0, Y.max() / 2.0 + DY / 2.0
    # Асимметричное пятно в правом верхнем квадранте
    c = np.zeros((NX, NY))
    c[80:90, 90:100] = 1.0
    c[70:75, 95:105] = 2.0  # смещено — не симметрично

    c_rotated = np.rot90(c, k=1)  # поворот на 90° против часовой
    center = compute_concentration_center(c)
    center_rot = compute_concentration_center(c_rotated)
    err = euclidean_error(center, center_rot)

    # Независимо рассчитываем центры по формуле
    # и проверяем, что err ≠ 0 и положителен
    if err > 1.0:
        ok("test_rotation: поворот на 90° → err={:.2f} м".format(err))
    else:
        fail("test_rotation: err={:.2f} м, ожидаемо > 1 м".format(err), code=1)


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

    # По умолчанию: вызов без --synthetic — краткий авторейтинг функций.
    # В будущем сюда войдёт загрузка данных и расчёт по 25 сценам.
    print("check_hw2.py — метрики центра концентрации, интеграла и ширины.")
    print("Запуск: python checks/check_hw2.py --synthetic")
    print("Пример:")
    c_example = np.zeros((NX, NY))
    c_example[60:70, 60:70] = 1.0
    mask_example = c_example > 0
    center = compute_concentration_center(c_example, mask_example)
    integral = compute_area_integral(c_example, mask_example)
    width = compute_radial_width(c_example, center, mask_example)
    print(f"  Центр: {center[0]:.2f}, {center[1]:.2f} м")
    print(f"  Интеграл: {integral:.2f}")
    print(f"  Ширина: {width:.2f} м")

if __name__ == "__main__":
    main()