import numpy as np

def briggs_widths(downwind_m, min_distance_m):
    a = np.maximum(downwind_m, min_distance_m)
    return (0.16 * a / np.sqrt(1 + 0.0004 * a),
            0.14 * a / np.sqrt(1 + 0.0003 * a))


def gaussian_field(x_m, y_m, sources_xyq, pressure_gradient_xy,
                   *, source_z_m, receptor_z_m, min_distance_m):
    x_m = np.asarray(x_m, dtype=float)
    y_m = np.asarray(y_m, dtype=float)
    sq = np.asarray(sources_xyq, dtype=float)
    g = np.asarray(pressure_gradient_xy, dtype=float)

    if x_m.ndim != 1 or len(x_m) == 0:
        raise ValueError("x_m must be 1D and nonempty")
    if y_m.ndim != 1 or len(y_m) == 0:
        raise ValueError("y_m must be 1D and nonempty")
    if sq.ndim != 2 or sq.shape[1] != 3:
        raise ValueError("sources_xyq must be Nx3")
    if g.shape != (2,) or not np.isfinite(g).all():
        raise ValueError("gradient must be finite shape (2,)")
    if not np.isfinite(source_z_m) or source_z_m < 0:
        raise ValueError("source_z_m must be nonnegative finite")
    if not np.isfinite(receptor_z_m) or receptor_z_m < 0:
        raise ValueError("receptor_z_m must be nonnegative finite")
    if min_distance_m <= 0:
        raise ValueError("min_distance_m must be positive")
    if not np.isfinite(sq).all():
        raise ValueError("sources_xyq must be finite")
    if (sq[:, 2] < 0).any():
        raise ValueError("weights must be nonnegative")
    gn = np.hypot(g[0], g[1])
    if not np.isfinite(gn) or gn == 0:
        raise ValueError("gradient norm must be nonzero finite")

    t = -g / gn
    cw = np.array([-t[1], t[0]])
    result = np.zeros((len(y_m), len(x_m)), dtype=float)
    ZS, ZR = float(source_z_m), float(receptor_z_m)
    mindist = float(min_distance_m)

    X, Y = np.meshgrid(x_m, y_m, indexing="xy")
    for sx, sy, Q in sq:
        px = X - sx
        py = Y - sy
        a_true = px * t[0] + py * t[1]
        b = px * cw[0] + py * cw[1]
        mask = a_true > 0
        a = np.maximum(a_true, mindist)
        sy_f, sz_f = briggs_widths(a, mindist)
        contrib = (Q / (2 * np.pi * sy_f * sz_f)) \
                  * np.exp(-0.5 * (b / sy_f) ** 2) \
                  * (np.exp(-0.5 * ((ZR - ZS) / sz_f) ** 2)
                   + np.exp(-0.5 * ((ZR + ZS) / sz_f) ** 2))
        result += np.where(mask, contrib, 0.0)
    return result


def synthetic_checks():
    import numpy.testing as npt

    # widths test
    sy, sz = briggs_widths(100, 1)
    npt.assert_allclose(sy, 15.689290811054722, rtol=1e-6)
    npt.assert_allclose(sz, 13.794609894300104, rtol=1e-6)

    x = np.array([-10., 0., 10., 100.], dtype=float)
    y = np.array([-2., 0., 2.], dtype=float)
    src = np.array([[0., 0., 1.]], dtype=float)
    grad = np.array([-1., 0.], dtype=float)

    f = gaussian_field(x, y, src, grad,
                       source_z_m=0, receptor_z_m=0, min_distance_m=1)

    # first two columns exactly zero; last two middle cells positive
    npt.assert_allclose(f[:, :2], 0, atol=0)
    assert f[1, 2] > 0
    assert f[1, 3] > 0

    # first and last rows equal (symmetry about y=0)
    npt.assert_allclose(f[0], f[2], rtol=1e-13)

    # ground-reflection test at x=100, y=0
    npt.assert_allclose(f[1, 3],
                        1 / (np.pi * 15.689290811054722 * 13.794609894300104),
                        rtol=1e-6)

    # additivity test
    s2 = np.array([[0., 0., 1.], [1., 1., 2.]], dtype=float)
    f2 = gaussian_field(x, y, s2, grad,
                        source_z_m=0, receptor_z_m=0, min_distance_m=1)
    f1 = gaussian_field(x, y, src, grad,
                        source_z_m=0, receptor_z_m=0, min_distance_m=1)
    sq2 = np.array([[1., 1., 2.]], dtype=float)
    fs2 = gaussian_field(x, y, sq2, grad,
                         source_z_m=0, receptor_z_m=0, min_distance_m=1)
    npt.assert_allclose(f2, f1 + fs2, rtol=1e-13)

    # linearity test (weights scaled by 13)
    fw = gaussian_field(x, y, np.array([[0., 0., 13.]], dtype=float),
                        grad, source_z_m=0, receptor_z_m=0, min_distance_m=1)
    npt.assert_allclose(f.mean(), fw.mean() / 13., rtol=1e-13)

    # near-source / floor-distance test
    xn = np.array([1e-8], dtype=float)
    yn = np.array([0.], dtype=float)
    fn = gaussian_field(xn, yn, src, grad,
                        source_z_m=0, receptor_z_m=0, min_distance_m=1)
    ff = gaussian_field(np.array([1.], dtype=float), yn, src, grad,
                        source_z_m=0, receptor_z_m=0, min_distance_m=1)
    assert np.isfinite(fn) and fn > 0
    npt.assert_allclose(fn, ff, rtol=1e-13)