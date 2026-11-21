"""Generate the paired centroid errors and example plume fields for the paper."""

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, LogNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from checks.check_hw2 import X, Y, compute_concentration_center, euclidean_error, verify_archive
from experiment.analyze_pairs import GEOMETRY_IDS, RESULTS, read_pairs
from experiment.compare_centroids import rectangle_sources
from src.gaussian_baseline import gaussian_field

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_IDS = (168, 167)


def load_scenes(errors_dl, errors_gaussian):
    config = json.loads((ROOT / "experiment/gaussian_config.json").read_text(encoding="utf-8"))
    inputs = json.loads((ROOT / "experiment/gaussian_inputs.json").read_text(encoding="utf-8"))
    source_inputs = {(row["geometry_id"], row["scene_name"]): row for row in inputs}
    layer = config["layer_index"]
    scenes = []

    with verify_archive(ROOT / "fixtures/hw2/plumes.npz", ROOT / "fixtures/hw2/manifest.json") as archive:
        indices = {int(gid): idx for idx, gid in enumerate(archive["geometry_id"])}
        names = archive["scene_name"]
        les = archive["les"]
        current = archive["current"]
        valid = archive["valid"]
        for gid in EXAMPLE_IDS:
            idx = indices[gid]
            mask = valid[idx, layer]
            row = source_inputs[gid, str(names[idx])]
            gaussian = gaussian_field(
                X, Y,
                rectangle_sources(row["boxes"], X, Y),
                row["pressure_gradient_direction_xy"],
                source_z_m=config["source_z_m"],
                receptor_z_m=config["receptor_z_m"],
                min_distance_m=config["min_distance_m"],
            )
            fields = np.array([les[idx, layer], gaussian, current[idx, layer]], dtype=np.float64)
            centers = [compute_concentration_center(field, mask) for field in fields]
            errors = [euclidean_error(center, centers[0]) for center in centers]
            table_idx = GEOMETRY_IDS.index(gid)
            expected = [0.0, errors_gaussian[table_idx], errors_dl[table_idx]]
            if not np.allclose(errors, expected, rtol=0, atol=1e-10):
                raise ValueError(f"Centroid errors do not match paired_errors.csv for scene {gid}")
            totals = fields[:, mask].sum(axis=1)
            if not np.isfinite(totals).all() or np.any(totals <= 0):
                raise ValueError(f"Invalid total concentration in scene {gid}")
            fields[:, ~mask] = 0
            fields /= totals[:, None, None]
            scenes.append((gid, mask, fields, centers, errors))
    return scenes


def plot_differences(ax, differences):
    ordered = sorted(differences.items(), key=lambda item: item[1])
    values = np.array([value for _, value in ordered])
    ranks = np.arange(1, len(values) + 1)
    colors = np.select([values < 0, values > 0], ["#a94f1c", "#21638b"], default="#77828a")
    limit = max(54.0, float(np.abs(values).max()) + 10.0)

    ax.axvline(0, color="#77828a", linewidth=0.75, zorder=1)
    ax.hlines(ranks, 0, values, color=colors, linewidth=0.65, alpha=0.65)
    ax.scatter(values, ranks, color=colors, s=10, zorder=3)
    for rank, (gid, value) in enumerate(ordered, start=1):
        if gid in EXAMPLE_IDS:
            right = value > 0
            ax.annotate(str(gid), (value, rank), xytext=(4 if right else -4, 0),
                        textcoords="offset points", ha="left" if right else "right",
                        va="center", fontsize=7)
    ax.set(
        xlim=(-limit, limit), ylim=(0, len(values) + 1),
        xticks=[-40, -20, 0, 20, 40], yticks=[1, 13, 25],
        xlabel="Gaussian − DL error (m)", ylabel="Scene rank",
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=2.5, pad=2)
    ax.text(0.01, 1.02, "Gaussian closer", transform=ax.transAxes,
            color="#a94f1c", va="bottom", fontsize=7)
    ax.text(0.99, 1.02, "DL closer", transform=ax.transAxes,
            color="#21638b", ha="right", va="bottom", fontsize=7)


def plot_example_fields(fig, scenes):
    maps = fig.add_gridspec(
        2, 3, left=0.489, right=0.986, bottom=0.228, top=0.88,
        wspace=0.06, hspace=0.23,
    )
    extent = (0, 256, 0, 256)
    building_color = "#aab2bb"
    center_color = "#be4c21"
    model_color = "#172c3d"
    cmap = matplotlib.colormaps["YlGnBu"].copy()
    cmap.set_bad("#fbfcfd")
    norm = LogNorm(1e-6, max(0.01, max(fields.max() for _, _, fields, _, _ in scenes)))
    buildings_cmap = ListedColormap([building_color])

    for row_index, (gid, mask, fields, centers, errors) in enumerate(scenes):
        buildings = np.ma.masked_where(mask, np.ones(mask.shape))
        for col, (field, center, error, label) in enumerate(
            zip(fields, centers, errors, ("LES", "Gaussian", "DL"), strict=True)
        ):
            ax = fig.add_subplot(maps[row_index, col])
            normalized = np.ma.masked_less(field, norm.vmin)
            ax.imshow(normalized, norm=norm, cmap=cmap, extent=extent,
                      origin="lower", interpolation="nearest")
            ax.imshow(buildings, cmap=buildings_cmap, extent=extent,
                      origin="lower", interpolation="nearest")
            if col:
                ax.plot(*center, "o", markerfacecolor="white",
                        markeredgecolor=model_color, markersize=3.7, markeredgewidth=0.7,
                        zorder=4)
                ax.text(0.5, -0.045, f"{error:.1f} m", transform=ax.transAxes,
                        ha="center", va="top", fontsize=7)
            else:
                ax.text(-0.085, 0.5, str(gid), transform=ax.transAxes,
                        ha="right", va="center", fontsize=7)
            ax.plot(*centers[0], "x", color=center_color,
                    markersize=4, markeredgewidth=0.9, zorder=5)
            ax.set(xticks=[], yticks=[])
            for spine in ax.spines.values():
                spine.set_color("#b8c2c8")
            if row_index == 0:
                ax.set_title(label, pad=2)

    color_axis = fig.add_axes([0.527, 0.155, 0.421, 0.018])
    colorbar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap),
                            cax=color_axis, orientation="horizontal")
    colorbar.set_label("Cell fraction of field sum (log scale)", labelpad=0, fontsize=6.5)
    colorbar.ax.tick_params(length=2, pad=1, labelsize=6.5)
    colorbar.minorticks_off()
    colorbar.outline.set_edgecolor("#b8c2c8")

    handles = [
        Patch(facecolor=building_color, edgecolor="none", label="Buildings"),
        Line2D([], [], color=center_color, marker="x", linestyle="none",
               markersize=4, label="LES center"),
        Line2D([], [], color=model_color, marker="o", markerfacecolor="white",
               linestyle="none", markersize=3.5, label="Model center"),
    ]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.737, 0.002),
               ncols=3, frameon=False, fontsize=6.5, handlelength=1, columnspacing=1.3)


def render_figure(scenes, differences, output):
    with matplotlib.rc_context({"font.size": 7.5, "pdf.fonttype": 42, "axes.linewidth": 0.55}):
        fig = plt.figure(figsize=(6.75, 2.9))
        fig.text(0.022, 0.975, "(a) Paired centroid errors", va="top", weight="bold")
        fig.text(0.466, 0.975, "(b) Example plume fields at 3 m", va="top", weight="bold")

        ax = fig.add_axes([0.083, 0.19, 0.337, 0.663])
        plot_differences(ax, differences)
        mean = float(np.mean(list(differences.values())))
        fig.text(0.25, 0.035, f"Mean difference: {mean:+.1f} m", ha="center", fontsize=7)
        plot_example_fields(fig, scenes)

        fig.savefig(output, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=RESULTS / "paper_figure.pdf")
    args = parser.parse_args()

    errors_dl, errors_gaussian, _ = read_pairs(RESULTS)
    differences = dict(zip(GEOMETRY_IDS, errors_gaussian - errors_dl, strict=True))
    scenes = load_scenes(errors_dl, errors_gaussian)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    render_figure(scenes, differences, args.output)


if __name__ == "__main__":
    main()
