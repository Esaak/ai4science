#!/usr/bin/env python3
"""Критерий готовности: метрики качества суррогата по пяти сценам.

Проверка независима от src/metrics.py: метрики здесь посчитаны своим кодом, и
результат агента сверяется с ним. Что проверяется:

  1. src/metrics.py есть и даёт правильные значения на случаях с известным ответом;
  2. целостность данных: средние по слоям в top_fields.npz совпадают со scene_table;
  3. results/metrics.json есть, в нём 16 нужных разрезов и все значения совпадают
     с независимым пересчётом;
  4. results/metrics_table.md есть и содержит обе модели и все пять метрик.

Код возврата 0 — принято, 1 — отклонено.

Запуск из корня проекта:  python3 checks/check.py
"""
import json
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:
    print("НЕТ: numpy не установлен; запускайте .venv/bin/python checks/check.py")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "edison_cache" / "top_fields.npz"
TABLE = ROOT / "data" / "edison_cache" / "val.npz"
RESULT = ROOT / "results" / "metrics.json"
MD = ROOT / "results" / "metrics_table.md"

LAYERS = ["Z1", "Z5", "Z8", "Z25", "Mean"]
MODELS = ["p_combo", "p_прежняя"]
KEYS = ["R2", "FAC2", "NMSE", "FB", "mass_ratio"]
RTOL = 1e-6

errors = []


def fail(msg):
    errors.append(msg)


def ref_metrics(o, p):
    """Независимая реализация метрик Chang & Hanna, см. AGENTS.md раздел 0."""
    o = np.asarray(o, dtype=np.float64).ravel()
    p = np.asarray(p, dtype=np.float64).ravel()
    mo, mp = o.mean(), p.mean()
    pos = o > 0
    ratio = p[pos] / o[pos]
    return {
        "mass_ratio": p.sum() / o.sum(),
        "FB": 2 * (mo - mp) / (mo + mp),
        "NMSE": ((o - p) ** 2).mean() / (mo * mp),
        "R2": 1 - ((o - p) ** 2).sum() / ((o - mo) ** 2).sum(),
        "FAC2": float(((ratio >= 0.5) & (ratio <= 2.0)).mean()),
    }


def close(a, b):
    return bool(np.isclose(a, b, rtol=RTOL, atol=1e-9))


# --- 1. Данные на месте ------------------------------------------------------
if not DATA.exists() or not TABLE.exists():
    print(f"НЕТ: нет данных {DATA} или {TABLE}")
    sys.exit(1)

z = np.load(DATA, allow_pickle=True)
v = np.load(TABLE, allow_pickle=True)
idx, t = z["idx"], z["t"].astype(np.float64)
preds = {m: z[m].astype(np.float64) for m in MODELS}

# --- 2. Целостность данных: таргет против scene_table ------------------------
got = t.mean(axis=(2, 3))
want = v["y_layer_mean"][idx]
dev = np.abs(got - want).max() / max(want.max(), 1e-9)
if dev > 1e-6:
    fail(f"данные повреждены: средние по слоям расходятся со scene_table на {dev:.2e}")

families = np.where(np.char.startswith(v["campaign"][idx], "2026_01"), "январские", "urban_layer")

# --- 3. src/metrics.py на случаях с известным ответом ------------------------
sys.path.insert(0, str(ROOT))
try:
    from src.metrics import metrics as agent_metrics
except Exception as e:  # noqa: BLE001 — любая причина импорта должна быть видна
    fail(f"src/metrics.py не импортируется: {type(e).__name__}: {e}")
    agent_metrics = None

if agent_metrics is not None:
    rng = np.random.default_rng(0)
    o = rng.lognormal(mean=1.0, sigma=1.0, size=(4, 32, 32))
    cases = [
        ("pred = obs", o, o, {"R2": 1.0, "FAC2": 1.0, "NMSE": 0.0, "FB": 0.0, "mass_ratio": 1.0}),
        ("pred = 2*obs", o, 2 * o, {"FB": -2 / 3, "mass_ratio": 2.0, "FAC2": 1.0}),
        ("pred = 0.5*obs", o, 0.5 * o, {"FB": 2 / 3, "mass_ratio": 0.5, "FAC2": 1.0}),
        ("pred = mean(obs)", o, np.full_like(o, o.mean()), {"R2": 0.0, "FB": 0.0, "mass_ratio": 1.0}),
    ]
    for name, obs, pred, want_vals in cases:
        try:
            got_vals = agent_metrics(obs, pred)
        except Exception as e:  # noqa: BLE001
            fail(f"metrics() падает на случае «{name}»: {type(e).__name__}: {e}")
            continue
        if not isinstance(got_vals, dict):
            fail(f"metrics() вернула {type(got_vals).__name__}, а не словарь")
            continue
        missing = [k for k in KEYS if k not in got_vals]
        if missing:
            fail(f"metrics() не вернула ключи {missing}")
            continue
        for k, w in want_vals.items():
            if not close(got_vals[k], w):
                fail(f"случай «{name}»: {k} = {got_vals[k]!r}, ожидалось {w:.6g}")
        # на любом случае значения должны совпадать с независимым пересчётом
        for k, w in ref_metrics(obs, pred).items():
            if not close(got_vals[k], w):
                fail(f"случай «{name}»: {k} = {got_vals[k]!r}, независимый пересчёт даёт {w:.6g}")

# --- 4. results/metrics.json -------------------------------------------------
if not RESULT.exists():
    fail(f"нет файла {RESULT.relative_to(ROOT)}")
else:
    try:
        res = json.loads(RESULT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"results/metrics.json не читается как JSON: {e}")
        res = None

    if res is not None:
        rows = res.get("метрики")
        if not isinstance(rows, list):
            fail("в results/metrics.json нет списка «метрики»")
        else:
            # эталонные разрезы
            want_rows = {}
            for m in MODELS:
                p = preds[m]
                want_rows[(m, "всё")] = (ref_metrics(t, p), t.size)
                for li, layer in enumerate(LAYERS):
                    want_rows[(m, f"слой {layer}")] = (ref_metrics(t[:, li], p[:, li]), t[:, li].size)
                for fam in ("январские", "urban_layer"):
                    sel = families == fam
                    want_rows[(m, f"семейство {fam}")] = (ref_metrics(t[sel], p[sel]), t[sel].size)

            seen = {}
            for r in rows:
                if not isinstance(r, dict):
                    fail("запись в «метрики» не является объектом")
                    continue
                key = (r.get("модель"), r.get("разрез"))
                if key not in want_rows:
                    fail(f"лишняя или неизвестная запись: модель={key[0]!r}, разрез={key[1]!r}")
                    continue
                if key in seen:
                    fail(f"запись повторяется: модель={key[0]!r}, разрез={key[1]!r}")
                    continue
                seen[key] = r
                want_vals, want_n = want_rows[key]
                if r.get("n") != want_n:
                    fail(f"{key[0]} / {key[1]}: n = {r.get('n')!r}, ожидалось {want_n}")
                for k, w in want_vals.items():
                    if k not in r:
                        fail(f"{key[0]} / {key[1]}: нет метрики {k}")
                    elif not isinstance(r[k], (int, float)):
                        fail(f"{key[0]} / {key[1]}: {k} не число: {r[k]!r}")
                    elif not close(r[k], w):
                        fail(f"{key[0]} / {key[1]}: {k} = {r[k]!r}, независимый пересчёт даёт {w:.6g}")

            for key in want_rows:
                if key not in seen:
                    fail(f"нет записи: модель={key[0]!r}, разрез={key[1]!r}")

# --- 5. results/metrics_table.md --------------------------------------------
if not MD.exists():
    fail(f"нет файла {MD.relative_to(ROOT)}")
else:
    text = MD.read_text(encoding="utf-8")
    for need in MODELS + KEYS:
        if need not in text:
            fail(f"в results/metrics_table.md нет упоминания «{need}»")

# --- итог --------------------------------------------------------------------
if errors:
    print(f"НЕ ПРИНЯТО: нарушений {len(errors)}")
    for e in errors[:20]:
        print(f"  - {e}")
    if len(errors) > 20:
        print(f"  … и ещё {len(errors) - 20}")
    sys.exit(1)

print("ПРИНЯТО: метрики совпадают с независимым пересчётом, все 16 разрезов на месте")
sys.exit(0)
