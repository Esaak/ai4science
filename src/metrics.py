"""Метрики качества предсказания суррогата LES (Chang & Hanna 2004)."""

import numpy as np


def metrics(obs: np.ndarray, pred: np.ndarray) -> dict:
    """Вычисляет 5 метрик качества предсказания.

    Parameters
    ----------
    obs : np.ndarray
        Наблюдаемые значения (таргет LES).
    pred : np.ndarray
        Предсказанные значения.

    Returns
    -------
    dict
        Словарь с ключами R2, FAC2, NMSE, FB, mass_ratio.
    """
    o = np.asarray(obs, dtype=np.float64).ravel()
    p = np.asarray(pred, dtype=np.float64).ravel()

    mo = o.mean()
    mp = p.mean()

    # mass_ratio = Σp / Σo
    mass_ratio = float(p.sum() / o.sum())

    # FB = 2*(ō - p̄) / (ō + p̄)
    FB = float(2.0 * (mo - mp) / (mo + mp))

    # NMSE = mean((o - p)^2) / (ō * p̄)
    NMSE = float(((o - p) ** 2).mean() / (mo * mp))

    # R2 = 1 - Σ(o - p)^2 / Σ(o - ō)^2
    R2 = float(1.0 - ((o - p) ** 2).sum() / ((o - mo) ** 2).sum())

    # FAC2 = доля ячеек с 0.5 <= p/o <= 2 среди ячеек где o > 0
    pos = o > 0
    ratio = p[pos] / o[pos]
    FAC2 = float(((ratio >= 0.5) & (ratio <= 2.0)).mean())

    return {
        "R2": R2,
        "FAC2": FAC2,
        "NMSE": NMSE,
        "FB": FB,
        "mass_ratio": mass_ratio,
    }