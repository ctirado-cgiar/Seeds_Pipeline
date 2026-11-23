# 10.1_colorDistance.py
"""
Distancia de color entre muestras: Earth Mover's Distance (EMD) exacta en RGB.

Cada muestra (foto) es una "firma": k colores dominantes (RGB 0-255) con su proporción
(paso 10.0). La EMD (Rubner et al., 2000) es el costo mínimo de transformar la firma de una
muestra en la de otra moviendo masa de color, con la distancia euclídea en RGB como costo
unitario. Como las proporciones suman 1, la EMD queda en unidades de RGB (0-441).

A diferencia de la versión anterior (una asignación 1 a 1 con min(peso_i, peso_j)), esta
resuelve el problema de transporte completo: cuando los pesos difieren, la masa sobrante
se mueve al color más cercano disponible en vez de ignorarse.

Entrada : Colorimetria/analisis_colores.csv (+ libroCampo/libroCampo.csv si existe)
Salidas : colorDistance/color_distance_matrix_emd.csv, color_distances_pairwise.csv,
          color_distance_heatmap.png, color_dendrogram.png
"""
import os
import re

import numpy as np
import pandas as pd
import common
import matplotlib
if not common.show_plots():
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.optimize import linprog
from scipy.spatial.distance import cdist, squareform

LINKAGE_METHOD = common.param("LINKAGE_METHOD", "ward")   # como en tu versión; 'average' = UPGMA


# ── Firmas de color ──────────────────────────────────────────────────────────

def parse_rgb(text):
    """'(188, 177, 33)' → array([188, 177, 33]). Acepta también el formato antiguo
    '(np.int64(188), ...)' que escribía el 10.0 con NumPy 2."""
    nums = re.findall(r"\d+", re.sub(r"np\.\w+", "", str(text)))
    if len(nums) != 3:
        raise ValueError(f"RGB no válido: {text!r}")
    return np.array([int(n) for n in nums], dtype=float)


def signature(row):
    """(colores (n, 3), pesos (n,) que suman 1) de una fila de analisis_colores.csv."""
    colors, weights, i = [], [], 1
    while f"RGB{i}" in row.index:
        rgb = row[f"RGB{i}"]
        if isinstance(rgb, str) and rgb.strip():
            pct = row.get(f"%{i}", row.get(f"{i}%"))
            colors.append(parse_rgb(rgb))
            weights.append(float(pct))
        i += 1
    colors, weights = np.array(colors), np.array(weights)
    return colors, weights / weights.sum()


def emd(colors1, w1, colors2, w2):
    """EMD exacta entre dos firmas con masa total 1 y costo euclídeo en RGB."""
    cost = cdist(colors1, colors2)
    n, m = cost.shape
    if n == 1:                                   # toda la masa de la firma 1 va a cada color de la 2
        return float(cost[0] @ w2)
    if m == 1:
        return float(cost[:, 0] @ w1)
    if n == 2 and m == 2:                        # un solo grado de libertad: el óptimo está en un extremo
        lo, hi = max(0.0, w1[0] + w2[0] - 1.0), min(w1[0], w2[0])
        best = np.inf
        for x in (lo, hi):                       # x = masa que va del color 1a al 2a
            flow = np.array([[x, w1[0] - x], [w2[0] - x, w1[1] - w2[0] + x]])
            best = min(best, float((flow * cost).sum()))
        return best
    # caso general: programación lineal (flujos >= 0, filas suman w1, columnas suman w2)
    a_eq = np.zeros((n + m, n * m))
    for i in range(n):
        a_eq[i, i * m:(i + 1) * m] = 1
    for j in range(m):
        a_eq[n + j, j::m] = 1
    res = linprog(cost.ravel(), A_eq=a_eq, b_eq=np.concatenate([w1, w2]),
                  bounds=(0, None), method="highs")
    return float(res.fun)


# ── Programa principal ───────────────────────────────────────────────────────

def main():
    out = common.path("colorDistance")
    os.makedirs(out, exist_ok=True)

    df = common.load_samples(("color",))
    df["label"] = common.make_labels(df)
    print(f"Muestras: {len(df)}  |  ejemplos de etiqueta: {df['label'].head(4).tolist()}")
    common.log_params("10.1_colorDistance", dict(distancia="EMD exacta, euclídea en RGB 0-255",
                                                 LINKAGE_METHOD=LINKAGE_METHOD, muestras=len(df)))

    sigs = [signature(row) for _, row in df.iterrows()]
    n = len(df)
    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            dist[i, j] = dist[j, i] = emd(*sigs[i], *sigs[j])
        if (i + 1) % 25 == 0 or i == n - 1:
            print(f"  procesadas {i + 1}/{n}")

    labels = df["label"].values
    dist_df = pd.DataFrame(dist, index=labels, columns=labels)
    dist_df.to_csv(os.path.join(out, "color_distance_matrix_emd.csv"))

    tick = max(3, min(8, int(120 / n)))
    plt.figure(figsize=(max(10, n * 0.35), max(10, n * 0.35) * 0.85))
    sns.heatmap(dist_df, cmap="YlOrRd", square=True, xticklabels=True, yticklabels=True,
                cbar_kws={"label": "EMD (RGB)"})
    plt.title("Color Distance Matrix (EMD, RGB)", fontsize=14, pad=20)
    plt.xticks(fontsize=tick, rotation=90)
    plt.yticks(fontsize=tick, rotation=0)
    plt.tight_layout()
    plt.savefig(os.path.join(out, "color_distance_heatmap.png"), dpi=300, bbox_inches="tight")
    common.finish_figure(plt)

    if n > 2:
        plt.figure(figsize=(max(14, n * 0.4), 6))
        dendrogram(linkage(squareform(dist, checks=False), method=LINKAGE_METHOD),
                   labels=labels, leaf_rotation=90, leaf_font_size=tick)
        plt.title("Hierarchical Clustering by Color (EMD)", fontsize=14, pad=20)
        plt.ylabel("EMD (RGB)")
        plt.tight_layout()
        plt.savefig(os.path.join(out, "color_dendrogram.png"), dpi=300, bbox_inches="tight")
        common.finish_figure(plt)

    pairs = pd.DataFrame([{"Genotipo1": labels[i], "Genotipo2": labels[j], "Distance": dist[i, j]}
                          for i in range(n) for j in range(i + 1, n)]).sort_values("Distance")
    pairs.to_csv(os.path.join(out, "color_distances_pairwise.csv"), index=False)

    upper = dist[np.triu_indices(n, k=1)]
    print(f"Comparaciones: {len(upper)} | mín {upper.min():.2f} | máx {upper.max():.2f} | "
          f"media {upper.mean():.2f} | sd {upper.std():.2f}")
    print("Salidas en", out)


if __name__ == "__main__":
    main()
