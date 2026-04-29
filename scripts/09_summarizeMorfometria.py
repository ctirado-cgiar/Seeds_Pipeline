import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

# ── Rutas desde .env ──────────────────────────────────────────────────────────
RUTA = os.getenv('RUTA')
if not RUTA:
    raise EnvironmentError("La variable RUTA no está definida en el archivo .env")

INPUT_CSV  = os.path.join(RUTA, 'Morfometria', 'metricasCompletas.csv')
OUTPUT_CSV = os.path.join(RUTA, 'Morfometria', 'metricasCompletas_summary.csv')

# ── Columnas métricas (excluye Imagen, Total_seeds, seed que son ID/conteo) ───
METRIC_COLS = [
    "W", "L", "P", "A", "AR", "Circ", "Solid",
    "Centroid_X", "Centroid_Y",
    "Radius_min", "Radius_mean", "Radius_max", "Radius_ratio",
    "Diam_min", "Diam_mean", "Diam_max",
    "Major_axis", "Minor_axis", "Caliper", "Theta", "Eccentricity",
    "Form_factor", "Narrow_factor", "Rectangularity",
    "PD_ratio", "PLW_ratio", "Area_CH",
    "Convexity", "Elongation", "Circ_haralick", "Circ_norm",
    "ASM", "Contrast", "Correlation", "Variance", "IDM", "Energy", "Entropy"
]

# ── Procesamiento ─────────────────────────────────────────────────────────────
print(f"📂 Leyendo: {INPUT_CSV}")
df = pd.read_csv(INPUT_CSV)

print(f"   {len(df)} filas | {df['Imagen'].nunique()} imágenes únicas")

# Agregar mean, median, std por imagen
summary = df.groupby('Imagen')[METRIC_COLS].agg(['mean', 'median', 'std'])

# Aplanar columnas: W_mean, W_median, W_std, L_mean ...
summary.columns = [f"{col}_{stat}" for col, stat in summary.columns]

# Agregar Total_seeds (es el mismo para todas las filas de una imagen)
summary.insert(0, 'Total_seeds', df.groupby('Imagen')['Total_seeds'].first())

summary.to_csv(OUTPUT_CSV, index=True)
print(f"✅ Resumen guardado: {OUTPUT_CSV}")
print(f"   {len(summary)} filas | {len(summary.columns)} columnas")
