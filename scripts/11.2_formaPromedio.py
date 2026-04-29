"""
formaPromedio.py
================
Análisis morfométrico de semillas por imagen.

Pipeline por imagen:
  1. Extracción de contornos desde imagen binaria
  2. Filtrado de semillas pegadas (solidity + circularidad)
  3. Normalización a N_POINTS equidistantes y centrado
  4. Alineación por GPA iterativo (Generalized Procrustes Analysis)
     sin eliminación de escala, preservando diferencias reales de tamaño
  5. Cálculo del contorno promedio convergido
  6. Descriptores EFA normalizados (Kuhl & Giardina, 1982)
     con rotación de fase para comparabilidad entre imágenes

Salidas:
  - efa_coefficients_all_images.csv  →  insumo para análisis comparativo entre muestras
  - *_pipeline.png                   →  visualización del proceso por imagen
  - *_harmonics.png                  →  reconstrucción acumulativa por armónicos
  - *_individual_seeds.png           →  semillas individuales alineadas

Dependencias: numpy, pandas, matplotlib, scikit-image, scipy, opencv-python, python-dotenv
"""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cv2
from skimage import measure
from scipy.spatial import procrustes
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# PARÁMETROS — ajustar según el conjunto de imágenes
# ─────────────────────────────────────────────────────────────────────────────

N_HARMONICS = 20      # Número de armónicos EFA. 20 es suficiente para semillas;
                      # aumentar si las formas tienen detalles muy finos.

N_POINTS    = 128     # Puntos por contorno tras normalización.
                      # Debe ser >= 2 * N_HARMONICS (regla de Nyquist).

MIN_AREA    = 100     # Área mínima en px² para considerar una región como semilla.
                      # Subir si hay ruido pequeño en las imágenes binarias.

MAX_AREA    = None    # Área máxima en px². None = sin límite superior.
                      # Útil para excluir regiones grandes no deseadas.

MIN_SOLIDITY    = 0.90  # Solidity mínima (área real / área convexa).
                        # Semillas pegadas tipo "8" tienen concavidad → valor bajo.
                        # Bajar a ~0.85 si tus semillas tienen forma naturalmente cóncava.

MIN_CIRCULARITY = 0.55  # Circularidad mínima (4π·A / P²). 1.0 = círculo perfecto.
                        # Bajar a ~0.45 si las semillas son muy alargadas (ej. arroz).

GPA_MAX_ITER = 20     # Iteraciones máximas del GPA. Converge típicamente en < 10.
GPA_TOL      = 1e-7   # Tolerancia de convergencia del GPA.


# ─────────────────────────────────────────────────────────────────────────────
# CLASE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class SeedMorphometrics:

    def __init__(self):
        self.n_harmonics = N_HARMONICS
        self.n_points    = N_POINTS

    # ── 1. Extracción y filtrado ──────────────────────────────────────────────

    def _is_merged_seed(self, region):
        """Devuelve True si la región parece dos semillas pegadas."""
        area        = region.area
        perimeter   = region.perimeter if region.perimeter > 0 else 1e-6
        solidity    = region.solidity
        circularity = (4 * np.pi * area) / (perimeter ** 2)
        return solidity < MIN_SOLIDITY or circularity < MIN_CIRCULARITY

    def extract_contours(self, binary_image):
        """
        Detecta regiones en la imagen binaria y extrae el contorno externo
        de cada semilla válida, descartando ruido y semillas pegadas.
        """
        if binary_image.max() > 1:
            _, binary_image = cv2.threshold(binary_image, 127, 1, cv2.THRESH_BINARY)

        labeled = measure.label(binary_image, connectivity=2)
        regions = measure.regionprops(labeled)

        contours   = []
        n_rejected = 0

        for region in regions:
            if region.area < MIN_AREA:
                continue
            if MAX_AREA is not None and region.area > MAX_AREA:
                continue
            if self._is_merged_seed(region):
                n_rejected += 1
                continue

            mask  = (labeled == region.label).astype(np.uint8)
            found = measure.find_contours(mask, 0.5)
            if not found:
                continue

            contour = max(found, key=len)
            if len(contour) < 50:
                continue

            contours.append(contour)

        return contours, n_rejected

    # ── 2. Normalización ─────────────────────────────────────────────────────

    def _resample(self, contour):
        """Resamplea un contorno a N_POINTS puntos equidistantes."""
        n   = len(contour)
        idx = np.linspace(0, n - 1, self.n_points)
        out = np.zeros((self.n_points, 2))
        for i, x in enumerate(idx):
            lo = int(np.floor(x))
            hi = int(np.ceil(x)) % n
            w  = x - lo
            out[i] = (1 - w) * contour[lo] + w * contour[hi]
        return out

    def _center(self, contour):
        """Traslada el contorno para que su centroide quede en el origen."""
        return contour - contour.mean(axis=0)

    def preprocess(self, contours):
        """Resamplea y centra todos los contornos."""
        return [self._center(self._resample(c)) for c in contours]

    # ── 3. GPA iterativo ─────────────────────────────────────────────────────

    def gpa(self, contours):
        """
        Generalized Procrustes Analysis iterativo sin eliminación de escala.

        Alinea todos los contornos hacia una referencia media convergida
        aplicando solo rotación y traslación. La escala se preserva para
        mantener diferencias reales de tamaño entre semillas.
        """
        aligned = [c.copy() for c in contours]

        for _ in range(GPA_MAX_ITER):
            mean_shape = self._center(np.mean(aligned, axis=0))

            new_aligned = []
            for c in aligned:
                # Escalar la referencia al tamaño del contorno actual
                # para que Procrustes solo corrija rotación y traslación
                scale      = np.linalg.norm(c) / (np.linalg.norm(mean_shape) + 1e-10)
                ref_scaled = mean_shape * scale

                _, mtx2, _ = procrustes(ref_scaled, c)

                # Restaurar la escala original del contorno
                norm_mtx2 = np.linalg.norm(mtx2)
                if norm_mtx2 > 1e-10:
                    mtx2 = mtx2 * (np.linalg.norm(c) / norm_mtx2)

                new_aligned.append(mtx2)

            prev_mean = np.mean(aligned, axis=0)
            aligned   = new_aligned
            new_mean  = np.mean(aligned, axis=0)

            if np.linalg.norm(new_mean - prev_mean) < GPA_TOL:
                break

        average_contour = self._center(np.mean(aligned, axis=0))
        return aligned, average_contour

    # ── 4. Descriptores EFA ───────────────────────────────────────────────────

    def efa(self, contour):
        """
        Calcula descriptores de Fourier Elíptico (Kuhl & Giardina, 1982).
        Retorna array (N_HARMONICS × 4) con columnas [A, B, C, D].
        """
        dxy = np.diff(contour, axis=0)
        dxy = np.vstack([dxy, contour[0] - contour[-1]])

        dt          = np.sqrt((dxy ** 2).sum(axis=1))
        dt[dt == 0] = 1e-10
        t = np.concatenate([[0], np.cumsum(dt)])
        T = t[-1]

        coeffs = np.zeros((self.n_harmonics, 4))
        for n in range(1, self.n_harmonics + 1):
            an = bn = cn = dn = 0.0
            for i in range(len(dxy)):
                dx  = dxy[i, 1]
                dy  = dxy[i, 0]
                dti = dt[i]
                t1  = 2 * n * np.pi * t[i]     / T
                t2  = 2 * n * np.pi * t[i + 1] / T
                cd  = np.cos(t2) - np.cos(t1)
                sd  = np.sin(t2) - np.sin(t1)
                an += (dx / dti) * cd
                bn += (dx / dti) * sd
                cn += (dy / dti) * cd
                dn += (dy / dti) * sd
            f = T / (2 * n * n * np.pi * np.pi)
            coeffs[n - 1] = [an * f, bn * f, cn * f, dn * f]

        return coeffs

    def normalize_efa(self, coeffs):
        """
        Normalización estándar de Kuhl & Giardina.

        Rota los coeficientes para que sean independientes de la orientación
        inicial del contorno. Sin este paso, dos imágenes de semillas idénticas
        fotografiadas en distinta orientación producirían coeficientes distintos,
        haciendo inválida cualquier comparación entre muestras.
        """
        a1, b1, c1, d1 = coeffs[0]

        # Rotación de fase: elimina dependencia del punto de inicio del contorno
        theta = 0.5 * np.arctan2(
            2 * (a1*b1 + c1*d1),
            a1**2 - b1**2 + c1**2 - d1**2
        )
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)

        rot1 = np.zeros_like(coeffs)
        for n in range(self.n_harmonics):
            an, bn, cn, dn = coeffs[n]
            rot1[n] = [
                 an * cos_t + bn * sin_t,
                -an * sin_t + bn * cos_t,
                 cn * cos_t + dn * sin_t,
                -cn * sin_t + dn * cos_t,
            ]

        # Rotación psi: alinea el eje principal al eje X
        psi   = np.arctan2(rot1[0, 2], rot1[0, 0])
        cos_p = np.cos(psi)
        sin_p = np.sin(psi)

        final = np.zeros_like(rot1)
        for n in range(self.n_harmonics):
            an, bn, cn, dn = rot1[n]
            final[n] = [
                 an * cos_p + cn * sin_p,
                 bn * cos_p + dn * sin_p,
                -an * sin_p + cn * cos_p,
                -bn * sin_p + dn * cos_p,
            ]

        # Garantizar A1 positivo (convención de signo)
        if final[0, 0] < 0:
            final *= -1

        return final

    def reconstruct(self, coeffs, n_points=256):
        """Reconstruye un contorno desde coeficientes EFA."""
        t       = np.linspace(0, 1, n_points)
        contour = np.zeros((n_points, 2))
        for n, (an, bn, cn, dn) in enumerate(coeffs, start=1):
            theta = 2 * n * np.pi * t
            contour[:, 1] += an * np.cos(theta) + bn * np.sin(theta)
            contour[:, 0] += cn * np.cos(theta) + dn * np.sin(theta)
        return contour

    def _rotate_to_match(self, source, reference):
        """
        Rota 'source' para que su eje mayor coincida con el de 'reference'.
        Uso exclusivamente visual — no modifica los coeficientes EFA.
        """
        def major_angle(c):
            _, vecs = np.linalg.eigh(np.cov(c.T))
            ax = vecs[:, 1]          # eigenvector del valor propio mayor
            return np.arctan2(ax[0], ax[1])

        delta = major_angle(reference) - major_angle(source)
        cos_d, sin_d = np.cos(delta), np.sin(delta)
        R = np.array([[cos_d, -sin_d], [sin_d, cos_d]])
        return source @ R.T

    # ── 5. Pipeline completo por imagen ──────────────────────────────────────

    def process(self, image_path):
        """
        Ejecuta el pipeline completo para una imagen.
        Retorna dict con todos los resultados, o None si no hay semillas válidas.
        """
        name = os.path.splitext(os.path.basename(image_path))[0]

        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"No se pudo leer: {image_path}")

        raw, n_rejected = self.extract_contours(img)
        if not raw:
            return None

        preprocessed         = self.preprocess(raw)
        aligned, avg_contour = self.gpa(preprocessed)
        coeffs               = self.normalize_efa(self.efa(avg_contour))
        reconstructed        = self.reconstruct(coeffs)

        return {
            'name'            : name,
            'n_seeds'         : len(raw),
            'n_rejected'      : n_rejected,
            'preprocessed'    : preprocessed,
            'aligned'         : aligned,
            'avg_contour'     : avg_contour,
            'efa_coefficients': coeffs,
            'reconstructed'   : reconstructed,
        }

    # ── 6. Visualizaciones ────────────────────────────────────────────────────

    def plot_pipeline(self, res, output_folder):
        """
        4 paneles:
          1. Contornos normalizados sin alinear
          2. Contornos alineados por GPA
          3. Overlay estilo Momocs (alineados + promedio)
          4. Promedio directo vs reconstrucción EFA normalizada
        """
        fig, axes = plt.subplots(2, 2, figsize=(12, 12))
        avg = res['avg_contour']
        rec = res['reconstructed']

        ax = axes[0, 0]
        for c in res['preprocessed']:
            ax.plot(c[:, 1], -c[:, 0], color='gray', alpha=0.3, lw=1)
        ax.set_aspect('equal'); ax.grid(True, alpha=0.3)
        ax.set_title('1. Normalizados (sin alinear)', fontsize=12, fontweight='bold')

        ax = axes[0, 1]
        for c in res['aligned']:
            ax.plot(c[:, 1], -c[:, 0], color='steelblue', alpha=0.3, lw=1)
        ax.set_aspect('equal'); ax.grid(True, alpha=0.3)
        ax.set_title('2. Alineados (GPA)', fontsize=12, fontweight='bold')

        ax = axes[1, 0]
        for c in res['aligned']:
            ax.plot(c[:, 1], -c[:, 0], color='lightgray', alpha=0.4, lw=0.8)
        ax.plot(avg[:, 1], -avg[:, 0], color='red', lw=3, label='Promedio', zorder=10)
        ax.fill(avg[:, 1], -avg[:, 0], color='red', alpha=0.1)
        ax.set_aspect('equal'); ax.grid(True, alpha=0.3); ax.legend(fontsize=10)
        ax.set_title('3. Overlay (estilo Momocs)', fontsize=12, fontweight='bold')

        ax = axes[1, 1]
        rec_vis = self._rotate_to_match(rec, avg)   # solo visual, EFA sin cambios
        ax.plot(avg[:, 1], -avg[:, 0], color='blue', lw=2,
                label='Promedio directo', alpha=0.7)
        ax.plot(rec_vis[:, 1], -rec_vis[:, 0], color='red', lw=2, ls='--',
                label=f'EFA normalizado ({self.n_harmonics} arm.)', alpha=0.7)
        ax.set_aspect('equal'); ax.grid(True, alpha=0.3); ax.legend(fontsize=9)
        ax.set_title('4. Promedio vs EFA normalizado', fontsize=12, fontweight='bold')

        plt.suptitle(f"{res['name']}  —  n={res['n_seeds']} semillas",
                     fontsize=14, fontweight='bold', y=0.998)
        plt.tight_layout()
        plt.savefig(os.path.join(output_folder, f"{res['name']}_pipeline.png"),
                    dpi=300, bbox_inches='tight')
        plt.close()

    def plot_harmonics(self, res, output_folder):
        """Reconstrucción acumulativa armónico a armónico, orientada como el promedio GPA."""
        coeffs = res['efa_coefficients']
        avg    = res['avg_contour']
        nh     = self.n_harmonics
        ncols  = 5
        nrows  = int(np.ceil(nh / ncols))

        fig, axes = plt.subplots(nrows, ncols,
                                 figsize=(ncols * 2.5, nrows * 2.5))
        axes = axes.flatten()

        for i in range(nh):
            c     = self.reconstruct(coeffs[:i + 1])
            c_vis = self._rotate_to_match(c, avg)   # solo visual
            axes[i].fill(c_vis[:, 1], -c_vis[:, 0],
                         facecolor='lightblue', edgecolor='navy', lw=1.5, alpha=0.7)
            axes[i].set_aspect('equal'); axes[i].axis('off')
            axes[i].set_title(f'{i + 1} arm.', fontsize=10, fontweight='bold')

        for i in range(nh, len(axes)):
            axes[i].axis('off')

        plt.suptitle(f"{res['name']}  —  Contribución de armónicos EFA",
                     fontsize=14, fontweight='bold', y=0.998)
        plt.tight_layout()
        plt.savefig(os.path.join(output_folder, f"{res['name']}_harmonics.png"),
                    dpi=300, bbox_inches='tight')
        plt.close()

    def plot_individual_seeds(self, res, output_folder, max_seeds=20):
        """Panel con cada semilla alineada individualmente."""
        aligned = res['aligned']
        n       = min(len(aligned), max_seeds)
        ncols   = 5
        nrows   = int(np.ceil(n / ncols))

        fig, axes = plt.subplots(nrows, ncols,
                                 figsize=(ncols * 2, nrows * 2))
        axes = axes.flatten()

        for i in range(n):
            c = aligned[i]
            axes[i].fill(c[:, 1], -c[:, 0],
                         facecolor='lightcoral', edgecolor='darkred', lw=1, alpha=0.6)
            axes[i].set_aspect('equal'); axes[i].axis('off')
            axes[i].set_title(f'#{i + 1}', fontsize=9)

        for i in range(n, len(axes)):
            axes[i].axis('off')

        plt.suptitle(
            f"{res['name']}  —  Semillas individuales alineadas\n"
            f"(mostrando {n} de {len(aligned)})",
            fontsize=13, fontweight='bold'
        )
        plt.tight_layout()
        plt.savefig(os.path.join(output_folder, f"{res['name']}_individual_seeds.png"),
                    dpi=300, bbox_inches='tight')
        plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# GUARDADO CONSOLIDADO
# ─────────────────────────────────────────────────────────────────────────────

def save_efa_consolidated(all_results, output_folder):
    """
    CSV consolidado con los coeficientes EFA normalizados de todas las imágenes.
    Una fila por imagen/muestra. Columnas: image_name, n_seeds, H1_A … HN_D.
    """
    rows = []
    for res in all_results:
        row  = {'image_name': res['name'], 'n_seeds': res['n_seeds']}
        flat = res['efa_coefficients'].flatten()
        for i, val in enumerate(flat):
            row[f"H{i // 4 + 1}_{['A','B','C','D'][i % 4]}"] = val
        rows.append(row)

    path = os.path.join(output_folder, 'efa_coefficients_all_images.csv')
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# GRÁFICO COMPARATIVO — formas promedio de todas las muestras
# ─────────────────────────────────────────────────────────────────────────────

def plot_all_averages(all_results, output_folder, analyzer):
    """
    Genera dos gráficos comparativos con las formas promedio de todas las muestras:

      - all_averages_grid.png    : una forma por celda, con su nombre
      - all_averages_overlay.png : todas superpuestas en un mismo eje

    Cada forma es la reconstrucción EFA rotada para coincidir con la orientación
    del contorno promedio GPA (igual que en los gráficos individuales).
    """
    if not all_results:
        return

    n       = len(all_results)
    # Paleta de colores: un color distinto por muestra
    colors  = plt.cm.tab20.colors if n <= 20 else plt.cm.hsv(np.linspace(0, 1, n))

    # Precalcular contornos visuales (EFA rotado al promedio GPA)
    shapes = []
    for res in all_results:
        rec     = analyzer.reconstruct(res['efa_coefficients'])
        rec_vis = analyzer._rotate_to_match(rec, res['avg_contour'])
        shapes.append(rec_vis)

    # ── Grid ──────────────────────────────────────────────────────────────────
    ncols = min(5, n)                          # máximo 5 columnas
    nrows = int(np.ceil(n / ncols))
    cell  = 3                                  # tamaño de celda en pulgadas

    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(ncols * cell, nrows * cell))
    axes = np.array(axes).flatten()

    for i, (res, shape, color) in enumerate(zip(all_results, shapes, colors)):
        ax = axes[i]
        ax.fill(shape[:, 1], -shape[:, 0],
                facecolor=color, edgecolor='black',
                alpha=0.45, lw=1.2)
        ax.plot(shape[:, 1], -shape[:, 0], color='black', lw=1.2)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(res['name'], fontsize=8, fontweight='bold')

    for i in range(n, len(axes)):
        axes[i].axis('off')

    plt.suptitle('Formas promedio — todas las muestras',
                 fontsize=14, fontweight='bold', y=1.01)
    plt.tight_layout()
    grid_path = os.path.join(output_folder, 'all_averages_grid.png')
    plt.savefig(grid_path, dpi=300, bbox_inches='tight')
    plt.close()

    # ── Overlay ───────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 7))

    for res, shape, color in zip(all_results, shapes, colors):
        ax.fill(shape[:, 1], -shape[:, 0],
                facecolor=color, edgecolor=color,
                alpha=0.25, lw=0)
        ax.plot(shape[:, 1], -shape[:, 0],
                color=color, lw=1.5, label=res['name'])

    ax.set_aspect('equal')
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, loc='upper right',
              ncol=max(1, n // 15),     # dos columnas si hay muchas muestras
              framealpha=0.8)
    ax.set_title('Formas promedio — overlay de todas las muestras',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    overlay_path = os.path.join(output_folder, 'all_averages_overlay.png')
    plt.savefig(overlay_path, dpi=300, bbox_inches='tight')
    plt.close()

    return grid_path, overlay_path


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    input_folder  = os.getenv('RUTA') + '/binarizadasAlineadas'
    output_folder = os.getenv('RUTA') + '/formaPromedio'
    os.makedirs(output_folder, exist_ok=True)

    image_paths = sorted(
        p for ext in ('*.jpg', '*.png', '*.tif', '*.bmp')
        for p in glob.glob(os.path.join(input_folder, ext))
    )

    if not image_paths:
        print(f"No se encontraron imágenes en: {input_folder}")
        return

    analyzer    = SeedMorphometrics()
    all_results = []
    skipped     = []

    for idx, path in enumerate(image_paths, 1):
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            res = analyzer.process(path)
            if res is None:
                skipped.append(name)
                continue

            all_results.append(res)
            analyzer.plot_pipeline(res, output_folder)
            analyzer.plot_harmonics(res, output_folder)
            analyzer.plot_individual_seeds(res, output_folder)

            extra = f"  (descartadas: {res['n_rejected']})" if res['n_rejected'] else ""
            print(f"[{idx}/{len(image_paths)}] {name}  →  {res['n_seeds']} semillas{extra}")

        except Exception as e:
            print(f"[{idx}/{len(image_paths)}] {name}  →  ERROR: {e}")

    if not all_results:
        print("No se procesó ninguna imagen.")
        return

    efa_path = save_efa_consolidated(all_results, output_folder)
    print(f"\nEFA consolidado guardado en: {efa_path}")

    paths = plot_all_averages(all_results, output_folder, analyzer)
    if paths:
        print(f"Gráficos comparativos: {paths[0]}")
        print(f"                       {paths[1]}")

    if skipped:
        print(f"Sin semillas válidas: {', '.join(skipped)}")


if __name__ == "__main__":
    main()
