"""Метрики качества предсказания (Chang & Hanna)."""
import numpy as np


def metrics(obs: np.ndarray, pred: np.ndarray) -> dict:
    """Посчитать 5 метрик для массивов наблюдений и предсказаний."""
    o = np.asarray(obs, dtype=np.float64).ravel()
    p = np.asarray(pred, dtype=np.float64).ravel()
    mo, mp = o.mean(), p.mean()
    pos = o > 0
    ratio = p[pos] / o[pos]
    return {
        "R2": float(1.0 - ((o - p) ** 2).sum() / ((o - mo) ** 2).sum()),
        "FAC2": float(((ratio >= 0.5) & (ratio <= 2.0)).mean()),
        "NMSE": float(((o - p) ** 2).mean() / (mo * mp)),
        "FB": float(2.0 * (mo - mp) / (mo + mp)),
        "mass_ratio": float(p.sum() / o.sum()),
    }