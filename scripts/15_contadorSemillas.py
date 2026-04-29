import numpy as np
import cv2 as cv
from skimage.feature import peak_local_max
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# ── Rutas desde .env ──────────────────────────────────────────────────────────
RUTA = os.getenv('RUTA')
if not RUTA:
    raise EnvironmentError("La variable RUTA no está definida en el archivo .env")

INPUT_FOLDER  = os.path.join(RUTA, 'areaInteres')
OUTPUT_FOLDER = os.path.join(RUTA, 'conteo')

# ── Parámetros de detección ───────────────────────────────────────────────────
THRESHOLD_VAL  = 125   # Umbral en canal Cr (YCrCb)
MIN_DISTANCE   = 10    # Distancia mínima entre semillas (px)
PEAK_THRESHOLD = 0.20  # Fracción del máximo de la distancia transform


# ── Funciones ─────────────────────────────────────────────────────────────────

def detect_seeds(image_path):
    img = cv.imread(image_path)
    if img is None:
        raise ValueError(f"No se pudo cargar: {image_path}")

    img = cv.resize(img, (img.shape[1] // 4, img.shape[0] // 4))
    h, w = img.shape[:2]

    cr = cv.cvtColor(img, cv.COLOR_BGR2YCrCb)[:, :, 1]
    _, thresh = cv.threshold(cr, THRESHOLD_VAL, 255, cv.THRESH_BINARY)

    kernel  = np.ones((3, 3), np.uint8)
    cleaned = cv.morphologyEx(thresh, cv.MORPH_OPEN, kernel, iterations=2)

    dist   = cv.distanceTransform(cleaned, cv.DIST_L2, 5)
    coords = peak_local_max(dist,
                            min_distance=MIN_DISTANCE,
                            threshold_abs=PEAK_THRESHOLD * dist.max())

    valid  = (coords[:, 0] >= 0) & (coords[:, 0] < h) & \
             (coords[:, 1] >= 0) & (coords[:, 1] < w)
    coords = coords[valid]

    return img, coords


def save_annotated(img, coords, out_path):
    h, w = img.shape[:2]
    out  = img.copy()
    for i, (row, col) in enumerate(coords):
        row, col = int(row), int(col)
        if 0 <= row < h and 0 <= col < w:
            cv.circle(out, (col, row), 5, (0, 255, 0), 2)
            cv.putText(out, str(i + 1), (col - 5, row + 5),
                       cv.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
    cv.imwrite(out_path, out)


def process_folder():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    exts   = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
    images = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(exts)]

    if not images:
        print(f"⚠️  No se encontraron imágenes en {INPUT_FOLDER}")
        return

    print(f"🔍 Procesando {len(images)} imagen(es)\n")

    rows = []
    for i, fname in enumerate(images, 1):
        img_path = os.path.join(INPUT_FOLDER, fname)
        name     = os.path.splitext(fname)[0]
        print(f"  [{i}/{len(images)}] {fname}", end=" ... ")

        try:
            img, coords = detect_seeds(img_path)
            count       = len(coords)

            out_img = os.path.join(OUTPUT_FOLDER, f"{name}.jpg")
            save_annotated(img, coords, out_img)

            rows.append({'Imagen': fname, 'Semillas': count})
            print(f"{count} semillas")

        except Exception as e:
            print(f"ERROR → {e}")
            rows.append({'Imagen': fname, 'Semillas': -1})

    # Reporte CSV
    df  = pd.DataFrame(rows)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv = os.path.join(OUTPUT_FOLDER, f"reporte_{ts}.csv")
    df.to_csv(csv, index=False)

    print(f"\n✅ Listo! Reporte: {csv}")
    print(df.to_string(index=False))
    return df


if __name__ == "__main__":
    print("🚀 Contador de semillas\n")
    process_folder()
