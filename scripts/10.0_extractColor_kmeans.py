# 10.0_extractColor_kmeans.py
"""
Colores dominantes de las semillas (K-means en RGB, k fijo; por defecto k = 2).

Método (el mismo de FenotIT, con k fijo para poder comparar muestras con EMD en 10.1):

  1. Objetos: contornos externos de Binarizadas/.
       - Color de la foto (analisis_colores.csv): TODOS los objetos, incluidas semillas
         pegadas y cortadas por el borde.
       - Color por semilla (analisis_colores_semillas.csv): solo los que pasan los filtros
         de área, ancho y largo del paso 08 (las mismas semillas que la morfometría).
  2. Píxeles: los del objeto sin un anillo de borde, donde se mezclan semilla y fondo.
     Ancho del anillo = 1.5 % de la raíz del área, redondeado y limitado a 1-3 px
     (EDGE_TRIM = -1, automático). Objetos con menos de 20 px restantes usan todos.
     Ya no se usa el criterio "píxel >= 245 es fondo": las semillas blancas se conservan.
  3. K-means (OpenCV): inicio k-means++, 3 intentos, semilla fija 134, ajustado sobre una
     muestra de hasta 3000 píxeles y aplicado a todos; los colores se ordenan por proporción.

Salidas (carpeta Colorimetria/):
  analisis_colores.csv          una fila por foto: k colores con todas las semillas juntas
  analisis_colores_semillas.csv una fila por semilla: sus k colores
  <foto>.png                    semillas pintadas con su color K-means y paleta
"""
import os

import cv2
import numpy as np
import pandas as pd
from skimage.color import rgb2lab
import common
import matplotlib
if not common.show_plots():
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

N_COLORS    = common.param("N_COLORS", 2)       # k fijo
EDGE_TRIM   = common.param("EDGE_TRIM", -1)     # px de borde a quitar; -1 = automático (1-3 px)
SEED        = 134
SAMPLE      = 3000
FILTERS     = common.object_filters()           # los mismos del paso 08
MAX_SLOTS   = max(3, N_COLORS)


# ── Funciones de color (de FenotIT) ──────────────────────────────────────────

def luminosidad(rgb):
    """Luminancia relativa (Rec. 709) sobre valores 0-255."""
    return round(0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2], 2)


def lab_cielab(rgb):
    """RGB (0-255) → CIELAB (skimage, sRGB y D65), redondeado a 2 decimales."""
    L, a, b = rgb2lab(np.array(rgb, dtype=float).reshape(1, 1, 3) / 255.0)[0, 0]
    return round(float(L), 2), round(float(a), 2), round(float(b), 2)


def core_pixels(mask, trim):
    """Quita el borde del objeto (mezcla objeto-fondo). trim < 0: automático."""
    if trim < 0:
        trim = int(np.clip(round(0.015 * np.sqrt(np.count_nonzero(mask))), 1, 3))
    if trim == 0:
        return mask
    inner = cv2.erode(np.pad(mask, 1), np.ones((3, 3), np.uint8), iterations=trim)[1:-1, 1:-1]
    return inner if np.count_nonzero(inner) >= 20 else mask


def kmeans_colors(pixels_rgb, k):
    """K-means++ (3 intentos, semilla fija) sobre una muestra; asigna todos los píxeles.
    Devuelve ([(rgb_int, fracción)] de mayor a menor, etiqueta de cada píxel)."""
    pixels = np.asarray(pixels_rgb)
    fit = pixels
    if len(pixels) > SAMPLE:
        fit = pixels[np.random.default_rng(SEED).choice(len(pixels), SAMPLE, replace=False)]
    packed = (fit[:, 0].astype(np.int64) << 16) | (fit[:, 1].astype(np.int64) << 8) | fit[:, 2]
    k = int(min(k, len(np.unique(packed))))
    cv2.setRNGSeed(SEED)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 300, 1e-3)
    _, _, centers = cv2.kmeans(fit.astype(np.float32), k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    px = pixels.astype(np.float32)
    best = np.full(len(pixels), np.inf, np.float32)
    labels = np.zeros(len(pixels), np.int64)
    for j, center in enumerate(centers):
        dist = ((px - center) ** 2).sum(axis=1)
        closer = dist < best
        best[closer], labels[closer] = dist[closer], j
    counts = np.bincount(labels, minlength=k)
    order = np.argsort(-counts, kind="stable")
    rank = np.empty(k, int)
    rank[order] = np.arange(k)
    colors = [(tuple(int(v) for v in centers[i]), counts[i] / counts.sum()) for i in order]
    return colors, rank[labels]


# ── Objetos de una foto ──────────────────────────────────────────────────────

def seed_objects(binary_path, apply_filters=True):
    """Máscaras (id, ventana, recorte) de los objetos; con apply_filters solo los que
    pasan los filtros del paso 08."""
    binary = cv2.imread(binary_path, cv2.IMREAD_GRAYSCALE)
    if binary is None:
        return []
    _, binary = cv2.threshold(binary, 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    objects = []
    for i, cnt in enumerate(contours, 1):
        area = cv2.contourArea(cnt)
        (_, _), (w, h), _ = cv2.minAreaRect(cnt)
        w, h = (h, w) if w > h else (w, h)
        if apply_filters and not common.passes_filters(area, w, h, FILTERS):
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        mask = np.zeros((bh, bw), np.uint8)
        cv2.drawContours(mask, [cnt - [x, y]], -1, 255, -1)
        objects.append((i, (slice(y, y + bh), slice(x, x + bw)), mask))
    return objects


def color_row(prefix_values, colors):
    """Columnas RGB/Hex/Luminosidad/%/LAB para hasta MAX_SLOTS colores."""
    row = dict(prefix_values)
    for i in range(MAX_SLOTS):
        if i < len(colors):
            rgb, frac = colors[i]
            row[f"RGB{i+1}"] = str(tuple(int(v) for v in rgb))
            row[f"Hex{i+1}"] = "#%02x%02x%02x" % rgb
            row[f"Luminosidad{i+1}"] = luminosidad(rgb)
            row[f"%{i+1}"] = round(100 * float(frac), 1)
            row[f"LAB{i+1}"] = str(lab_cielab(rgb))
        else:
            for col in ("RGB", "Hex", "Luminosidad", "%", "LAB"):
                row[f"{col}{i+1}"] = ""
    return row


def save_figure(path_png, name, rgb_img, objs_pixels, labels_all, colors):
    """Semillas pintadas con su color K-means (fondo blanco) y paleta de la foto."""
    painted = np.full_like(rgb_img, 255)
    palette = np.array([c for c, _ in colors], np.uint8)
    start = 0
    for _, window, core, pixels in objs_pixels:
        lab = labels_all[start:start + len(pixels)]
        view = painted[window]
        view[core > 0] = palette[lab]
        start += len(pixels)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(painted)
    ax.axis("off")
    ax.set_title(f"{name}  |  k = {len(colors)}", fontsize=9)
    for i, (rgb, frac) in enumerate(colors):
        ax.add_patch(plt.Rectangle((0.02 + i * 0.16, 0.02), 0.04, 0.035, transform=ax.transAxes,
                                   color="#%02x%02x%02x" % rgb, ec="black", lw=0.5))
        ax.text(0.065 + i * 0.16, 0.0375, f"{100 * frac:.0f}%", transform=ax.transAxes,
                fontsize=6, va="center", bbox=dict(fc="white", ec="none", alpha=0.7, pad=1))
    fig.savefig(path_png, bbox_inches="tight", dpi=150)
    plt.close(fig)


def main():
    in_seg, in_bin = common.path("Segmentadas"), common.path("Binarizadas")
    out = common.path("Colorimetria")
    os.makedirs(out, exist_ok=True)
    common.log_params("10.0_extractColor_kmeans", dict(N_COLORS=N_COLORS, EDGE_TRIM=EDGE_TRIM,
                      SEED=SEED, SAMPLE=SAMPLE, **FILTERS))
    rows_photo, rows_seed = [], []

    for filename in common.list_images(in_seg):
        try:
            img = cv2.cvtColor(cv2.imread(os.path.join(in_seg, filename)), cv2.COLOR_BGR2RGB)
            bin_path = os.path.join(in_bin, filename)
            kept = {oid for oid, _, _ in seed_objects(bin_path)}      # los que mide el paso 08
            objs = []                                                 # todos los objetos
            for oid, window, mask in seed_objects(bin_path, apply_filters=False):
                core = core_pixels(mask, EDGE_TRIM)
                pixels = img[window][core > 0].reshape(-1, 3)
                if len(pixels):
                    objs.append((oid, window, core, pixels))
            if not objs:
                print(f"Saltando {filename}: sin objetos.")
                continue

            all_pixels = np.concatenate([o[3] for o in objs])
            colors, labels_all = kmeans_colors(all_pixels, N_COLORS)
            name = common.strip_ext(filename)
            rows_photo.append(color_row({"Image": name, "N_objetos": len(objs),
                                         "N_objetos_filtrados": len(kept)}, colors))

            for oid, _, _, pixels in objs:
                if oid not in kept:
                    continue
                seed_colors, _ = kmeans_colors(pixels, N_COLORS)
                mean = tuple(int(v) for v in pixels.mean(axis=0))
                rows_seed.append(color_row({"Image": name, "seed": oid,
                                            "mean_RGB": str(mean), "mean_LAB": str(lab_cielab(mean))},
                                           seed_colors))
            save_figure(os.path.join(out, name + ".png"), name, img, objs, labels_all, colors)
        except Exception as exc:                      # una foto mala no detiene el lote
            print(f"Error procesando {filename}: {exc}")

    pd.DataFrame(rows_photo).to_csv(os.path.join(out, "analisis_colores.csv"), index=False)
    pd.DataFrame(rows_seed).to_csv(os.path.join(out, "analisis_colores_semillas.csv"), index=False)
    print(f"Proceso completado: {len(rows_photo)} fotos, {len(rows_seed)} semillas (k = {N_COLORS}).")


if __name__ == "__main__":
    main()
