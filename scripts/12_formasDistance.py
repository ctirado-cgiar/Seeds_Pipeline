import pandas as pd
import numpy as np
from scipy.spatial.distance import euclidean, squareform
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.preprocessing import StandardScaler
import seaborn as sns
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv
load_dotenv()

'''
Distancia morfométrica (Forma + EFA + Haralick)
Misma estructura que el script EMD de colores.
Distancia: Euclidiana normalizada (Z-score) sobre variables seleccionadas.
Etiquetas: Line_Env_REP_usada_In_row
'''

BASE = os.getenv('RUTA')

# ==========================================
# ⚙️  CONFIGURACIÓN
# ==========================================

csv_path = BASE + '/formasDistance/coloresMorfologiaFormas_Rep-1_Env-ALL_GGR_2025_ANALISIS_20260312.csv'

# Columnas que forman la etiqueta
LABEL_COLS = ['Line', 'Env', 'REP_usada', 'In_row']
LABEL_SEP  = '_'

# Variables morfométricas a usar
# ── Morfometría clásica ──────────────────────────────────────
MORPH_COLS = [
    'W_mean', 'L_mean', 'AR_mean', 'Circ_mean',
    'Solid_mean', 'Radius_ratio_mean',
    'Major_axis_mean', 'Minor_axis_mean',
    'Eccentricity_mean', 'Form_factor_mean',
    'Elongation_mean', 'Convexity_mean',
    'Narrow_factor_mean', 'Rectangularity_mean',
    'PLW_ratio_mean',
]

# ── Textura Haralick ─────────────────────────────────────────
HARALICK_COLS = [
    'ASM_mean', 'Contrast_mean', 'Correlation_mean',
    'Variance_mean', 'IDM_mean', 'Entropy_mean',
]

# ── Coeficientes EFA (H1_A ... H10_D) ───────────────────────
# Se detectan automáticamente — cambia a [] para excluirlos
EFA_PATTERN = 'H'   # columnas que empiecen por H seguidas de dígito
USE_EFA = True

# ==========================================
# PASO 1: CARGAR Y CONSTRUIR ETIQUETAS
# ==========================================

df = pd.read_csv(csv_path)

print("Datos cargados:")
print(df.head(3))
print(f"\nForma: {df.shape}")

df['label'] = df[LABEL_COLS].astype(str).apply(
    lambda row: LABEL_SEP.join(row.values), axis=1
)

dupes = df['label'].duplicated()
if dupes.any():
    print(f"\n⚠️  Etiquetas duplicadas ({dupes.sum()}):")
    print(df[dupes]['label'].tolist())
else:
    print(f"\n✓ Etiquetas únicas: {len(df['label'])} — OK")

print("\nEjemplos de etiquetas:")
print(df['label'].head(8).tolist())

# ==========================================
# PASO 1.5: CONSTRUIR VECTOR DE FEATURES
# ==========================================

# Filtrar columnas que existen
morph_ok    = [c for c in MORPH_COLS     if c in df.columns]
haralick_ok = [c for c in HARALICK_COLS  if c in df.columns]
efa_ok      = [c for c in df.columns
               if USE_EFA and c.startswith(EFA_PATTERN)
               and len(c) > 1 and c[1].isdigit()] if USE_EFA else []

feature_cols = morph_ok + haralick_ok + efa_ok

print(f"\nFeatures seleccionados:")
print(f"  Morfometría : {len(morph_ok)} columnas")
print(f"  Haralick    : {len(haralick_ok)} columnas")
print(f"  EFA         : {len(efa_ok)} columnas")
print(f"  TOTAL       : {len(feature_cols)} columnas")

# Verificar NaNs en features
nan_mask = df[feature_cols].isna().any(axis=1)
if nan_mask.any():
    print(f"\n⚠️  {nan_mask.sum()} filas con NaN en features de forma:")
    print(df[nan_mask]['label'].tolist())

    DETENER_SI_HAY_NANS = False   # <-- cambia a True para detener
    if DETENER_SI_HAY_NANS:
        raise ValueError(f"Corrige los NaN antes de continuar.")
    else:
        df = df[~nan_mask].reset_index(drop=True)
        print(f"✓ Excluidas {nan_mask.sum()} filas — continuando con {len(df)} genotipos")
else:
    print("✓ Sin NaN en features — OK")

# ==========================================
# PASO 2: NORMALIZAR (Z-score)
# ==========================================

# Necesario para que morfometría, Haralick y EFA sean comparables
# sin que las unidades de W_mean (pixels) dominen sobre H1_A (adimensional)

features_raw = df[feature_cols].values.astype(float)

scaler = StandardScaler()
features_scaled = scaler.fit_transform(features_raw)

print(f"\n✓ Features normalizados (Z-score) — shape: {features_scaled.shape}")

# ==========================================
# PASO 3: CALCULAR MATRIZ DE DISTANCIAS
# ==========================================

print("\n" + "="*50)
print("Calculando matriz de distancias (Euclidiana norm.)...")
print("="*50)

n = len(df)
labels = df['label'].values

distance_matrix = np.zeros((n, n))

for i in range(n):
    for j in range(i + 1, n):
        dist = euclidean(features_scaled[i], features_scaled[j])
        distance_matrix[i, j] = dist
        distance_matrix[j, i] = dist

    if (i + 1) % 10 == 0 or i == n - 1:
        print(f"  Procesadas {i+1}/{n}...")

# ==========================================
# PASO 4: DATAFRAME CON ETIQUETAS
# ==========================================

distance_df = pd.DataFrame(distance_matrix, index=labels, columns=labels)

print("\nMatriz (preview):")
print(distance_df.iloc[:4, :4])

out_matrix = BASE + '/formasDistance/shapes_distance_Rep-1_matrix.csv'
distance_df.to_csv(out_matrix)
print(f"\n✓ Matriz guardada: {out_matrix}")

# ==========================================
# PASO 5: VISUALIZACIONES
# ==========================================

print("\nGenerando visualizaciones...")

n_labels = len(labels)
tick_size = max(3, min(8, int(120 / n_labels)))
fig_size  = max(10, n_labels * 0.35)

# — Heatmap —
plt.figure(figsize=(fig_size, fig_size * 0.85))
sns.heatmap(
    distance_df,
    cmap='YlOrRd',
    square=True,
    cbar_kws={'label': 'Euclidean Distance (normalized)'},
    xticklabels=True,
    yticklabels=True,
    annot=False
)
plt.title('Shape Distance Matrix (Euclidean norm.)', fontsize=14, pad=20)
plt.xticks(fontsize=tick_size, rotation=90)
plt.yticks(fontsize=tick_size, rotation=0)
plt.tight_layout()
out_heatmap = BASE + '/formasDistance/shapes_distance_heatmap_Rep-1.png'
plt.savefig(out_heatmap, dpi=300, bbox_inches='tight')
print(f"✓ Heatmap guardado: {out_heatmap}")
plt.show()

# — Dendrograma —
# Forzar simetría perfecta (mismo fix que EMD colores)
distance_matrix = (distance_matrix + distance_matrix.T) / 2
np.fill_diagonal(distance_matrix, 0)
print(f"✓ Simetría forzada — asimetría residual: {np.max(np.abs(distance_matrix - distance_matrix.T)):.2e}")

condensed      = squareform(distance_matrix, checks=False)
linkage_matrix = linkage(condensed, method='average')

fig_w = max(14, n_labels * 0.4)
plt.figure(figsize=(fig_w, 6))
dendrogram(
    linkage_matrix,
    labels=labels,
    leaf_rotation=90,
    leaf_font_size=tick_size
)
plt.title('Hierarchical Clustering by Shape (Euclidean norm.)', fontsize=14, pad=20)
plt.xlabel('Genotipo', fontsize=12)
plt.ylabel('Distancia', fontsize=12)
plt.tight_layout()
out_dendro = BASE + '/formasDistance/shapes_dendrogram_Rep-1.png'
plt.savefig(out_dendro, dpi=300, bbox_inches='tight')
print(f"✓ Dendrograma guardado: {out_dendro}")
plt.show()

# ==========================================
# PASO 6: ESTADÍSTICAS Y PAIRWISE
# ==========================================

upper = distance_matrix[np.triu_indices(n, k=1)]

print("\n" + "="*50)
print("Estadísticas de distancias:")
print("="*50)
print(f"Comparaciones totales : {len(upper)}")
print(f"Distancia mínima      : {upper.min():.2f}")
print(f"Distancia máxima      : {upper.max():.2f}")
print(f"Distancia promedio    : {upper.mean():.2f}")
print(f"Desviación estándar   : {upper.std():.2f}")

distance_long = []
for i in range(n):
    for j in range(i + 1, n):
        distance_long.append({
            'Genotipo1': labels[i],
            'Genotipo2': labels[j],
            'Distance':  distance_matrix[i, j]
        })

distance_pairs = pd.DataFrame(distance_long).sort_values('Distance')

print("\n5 pares MÁS SIMILARES (forma):")
print(distance_pairs.head(5).to_string(index=False))

print("\n5 pares MÁS DIFERENTES (forma):")
print(distance_pairs.tail(5).to_string(index=False))

out_pairs = BASE + '/formasDistance/shapes_pairwise_Rep-1.csv'
distance_pairs.to_csv(out_pairs, index=False)
print(f"\n✓ Pares guardados: {out_pairs}")

print("\n" + "="*50)
print("¡PROCESO COMPLETADO!")
print("="*50)
print(f"\nArchivos generados:")
print(f"  {out_matrix}")
print(f"  {out_heatmap}")
print(f"  {out_dendro}")
print(f"  {out_pairs}")
