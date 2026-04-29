import pandas as pd
import numpy as np
from scipy.spatial.distance import euclidean
from scipy.optimize import linear_sum_assignment
import seaborn as sns
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv
load_dotenv()

'''
Earth Mover's Distance (EMD)
https://homepages.inf.ed.ac.uk/rbf/CVonline/LOCAL_COPIES/RUBNER/emd.htm
Similar a la función colordistance en R
Etiquetas: Line_Env_Rep_InRow en lugar de solo Image/InRow
'''

BASE = os.getenv('RUTA')

# ==========================================
# ⚙️  CONFIGURACIÓN
# ==========================================

# Archivo de entrada (salida del script de selección de reps)
csv_path = BASE + '/colorDistance/coloresMorfologiaFormas_Rep-1_Env-ALL_GGR_2025_ANALISIS_20260310.csv'  # <-- ajusta

# Columnas que forman la etiqueta — edita el orden o quita las que no necesites
LABEL_COLS = ['Line', 'Env', 'REP_usada', 'In_row']   # <-- ajusta según tus datos
LABEL_SEP  = '_'   # separador entre partes

# ==========================================
# PASO 1: CARGAR Y CONSTRUIR ETIQUETAS
# ==========================================

df = pd.read_csv(csv_path)

print("Datos cargados:")
print(df.head(3))
print(f"\nForma: {df.shape}")
print(f"Columnas disponibles: {df.columns.tolist()}")

# Construir etiqueta descriptiva
# Resultado: 'MRD00306CIC_IRRIGATION_1_1561'
df['label'] = df[LABEL_COLS].astype(str).apply(
    lambda row: LABEL_SEP.join(row.values), axis=1
)

# Verificar que no hay etiquetas duplicadas
dupes = df['label'].duplicated()
if dupes.any():
    print(f"\n⚠️  Etiquetas duplicadas ({dupes.sum()}) — revisa los datos:")
    print(df[dupes]['label'].tolist())
else:
    print(f"\n✓ Etiquetas únicas: {len(df['label'])} — OK")

print("\nEjemplos de etiquetas:")
print(df['label'].head(8).tolist())

# ==========================================
# PASO 2: FUNCIONES DE DISTANCIA
# ==========================================

def parse_rgb(rgb_string):
    rgb_clean = str(rgb_string).strip('()').replace(' ', '')
    return np.array([int(x) for x in rgb_clean.split(',')])

def emd_distance(img1_data, img2_data):
    try:
        colors1 = np.array([
            parse_rgb(img1_data['RGB1']),
            parse_rgb(img1_data['RGB2'])
        ], dtype=float)

        colors2 = np.array([
            parse_rgb(img2_data['RGB1']),
            parse_rgb(img2_data['RGB2'])
        ], dtype=float)

        weights1 = np.array([float(img1_data['1%']), float(img1_data['2%'])]) / 100.0
        weights2 = np.array([float(img2_data['1%']), float(img2_data['2%'])]) / 100.0

        weights1 = weights1 / weights1.sum()
        weights2 = weights2 / weights2.sum()

        dist_matrix = np.zeros((2, 2))
        for i in range(2):
            for j in range(2):
                dist_matrix[i, j] = euclidean(colors1[i], colors2[j])

        row_ind, col_ind = linear_sum_assignment(dist_matrix)

        emd = 0
        for i, j in zip(row_ind, col_ind):
            weight = min(weights1[i], weights2[j])
            emd += weight * dist_matrix[i, j]

        return emd

    except Exception as e:
        print(f"Error: {img1_data['label']} vs {img2_data['label']} — {e}")
        return np.nan

# ==========================================
# PASO 3: CALCULAR MATRIZ DE DISTANCIAS
# ==========================================

print("\n" + "="*50)
print("Calculando matriz de distancias...")
print("="*50)

n = len(df)
distance_matrix = np.zeros((n, n))

for i in range(n):
    for j in range(i + 1, n):
        dist = emd_distance(df.iloc[i], df.iloc[j])
        distance_matrix[i, j] = dist
        distance_matrix[j, i] = dist

    if (i + 1) % 10 == 0 or i == n - 1:
        print(f"Procesadas {i+1}/{n}...")

# ==========================================
# PASO 4: DATAFRAME CON ETIQUETAS
# ==========================================

labels = df['label'].values

distance_df = pd.DataFrame(
    distance_matrix,
    index=labels,
    columns=labels
)

print("\nMatriz (preview):")
print(distance_df.iloc[:4, :4])

# Guardar
out_matrix = BASE + '/colorDistance/color_distance_Rep-1_matrix_emd.csv'
distance_df.to_csv(out_matrix)
print(f"\n✓ Matriz guardada: {out_matrix}")

# ==========================================
# PASO 5: VISUALIZACIONES
# ==========================================

print("\nGenerando visualizaciones...")

# — Heatmap —
n_labels = len(labels)
tick_size = max(3, min(8, int(120 / n_labels)))   # escala automática

fig_size  = max(10, n_labels * 0.35)
plt.figure(figsize=(fig_size, fig_size * 0.85))
sns.heatmap(
    distance_df,
    cmap='YlOrRd',
    square=True,
    cbar_kws={'label': 'EMD Distance'},
    xticklabels=True,
    yticklabels=True,
    annot=False
)
plt.title('Color Distance Matrix (EMD)', fontsize=14, pad=20)
plt.xticks(fontsize=tick_size, rotation=90)
plt.yticks(fontsize=tick_size, rotation=0)
plt.tight_layout()
out_heatmap = BASE + '/colorDistance/distance_heatmap_Rep-1.png'
plt.savefig(out_heatmap, dpi=300, bbox_inches='tight')
print(f"✓ Heatmap guardado: {out_heatmap}")
plt.show()

# — Dendrograma —
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

fig_w = max(14, n_labels * 0.4)
plt.figure(figsize=(fig_w, 6))

# squareform convierte la matriz cuadrada → vector condensado (triángulo superior)
# que es lo que linkage espera cuando los datos ya son distancias
condensed = squareform(distance_matrix)
linkage_matrix = linkage(condensed, method='average')
dendrogram(
    linkage_matrix,
    labels=labels,
    leaf_rotation=90,
    leaf_font_size=tick_size
)
plt.title('Hierarchical Clustering by Color (EMD)', fontsize=14, pad=20)
plt.xlabel('Genotipo', fontsize=12)
plt.ylabel('Distancia EMD', fontsize=12)
plt.tight_layout()
out_dendro = BASE + '/colorDistance/dendrogram_Rep-1.png'
plt.savefig(out_dendro, dpi=300, bbox_inches='tight')
print(f"✓ Dendrograma guardado: {out_dendro}")
plt.show()

# ==========================================
# PASO 6: ESTADÍSTICAS
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

# Pares
distance_long = []
for i in range(n):
    for j in range(i + 1, n):
        distance_long.append({
            'Genotipo1' : labels[i],
            'Genotipo2' : labels[j],
            'Distance'  : distance_matrix[i, j]
        })

distance_pairs = pd.DataFrame(distance_long).sort_values('Distance')

print("\n5 pares MÁS SIMILARES:")
print(distance_pairs.head(5).to_string(index=False))

print("\n5 pares MÁS DIFERENTES:")
print(distance_pairs.tail(5).to_string(index=False))

out_pairs = BASE + '/colorDistance/distances_pairwise_Rep-1.csv'
distance_pairs.to_csv(out_pairs, index=False)
print(f"\n✓ Pares guardados: {out_pairs}")

print("\n" + "="*50)
print("¡PROCESO COMPLETADO!")
print("="*50)