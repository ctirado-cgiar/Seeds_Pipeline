import pandas as pd
import numpy as np
import json
from scipy.spatial.distance import squareform
from scipy.cluster.hierarchy import linkage, to_tree
import os
from dotenv import load_dotenv
load_dotenv()

BASE = os.getenv('RUTA')

'''
Exporta la linkage matrix a un JSON jerárquico compatible con D3.js
para visualización de dendrograma en el HTML Explorer.

Genera:
  dendrogram_color.json   ← desde distances pairwise de color
  dendrogram_shapes.json  ← desde distances pairwise de formas (si existe)

Formato de salida:
{
  "name": "node_12",
  "height": 45.2,
  "children": [
    { "name": "AFR298_IRRIGATION_1_1711", "height": 0, "children": [] },
    { ... }
  ]
}
'''

# ==========================================
# ⚙️  CONFIGURACIÓN
# ==========================================

FILES = {
    'color': {
        'input':  BASE + '/colorDistance/distances_pairwise_Rep-1.csv',
        'output': BASE + '/colorDistance/dendrogram_color_Rep-1.json',
        'active': False,  # cambia a True si tienes datos de color
    },
    'shapes': {
        'input':  BASE + '/formasDistance/shapes_pairwise_Rep-1.csv',   # <-- ajusta si tienes
        'output': BASE + '/formasDistance/dendrogram_shapes_Rep-1.json',
        'active': True,   # cambia a True si tienes datos de formas
    },
}

LINKAGE_METHOD = 'average'   # 'average' = UPGMA, igual al script de EMD
                              # otras opciones: 'ward', 'complete', 'single'

# ==========================================
# FUNCIONES
# ==========================================

def pairwise_to_square(df_pairs):
    """
    Convierte un DataFrame de pares (G1, G2, Distance)
    a una matriz cuadrada de distancias con etiquetas.
    """
    # Detectar columnas automáticamente
    col_map = {}
    for col in df_pairs.columns:
        cl = col.lower()
        if cl in ['genotipo1','image1','label1','g1']:   col_map['g1']   = col
        if cl in ['genotipo2','image2','label2','g2']:   col_map['g2']   = col
        if cl in ['distance','distancia','dist','emd']:  col_map['dist'] = col

    if len(col_map) < 3:
        raise ValueError(f"Columnas no reconocidas: {df_pairs.columns.tolist()}")

    g1_col   = col_map['g1']
    g2_col   = col_map['g2']
    dist_col = col_map['dist']

    # Lista de todos los genotipos únicos
    labels = sorted(set(df_pairs[g1_col].tolist() + df_pairs[g2_col].tolist()))
    n = len(labels)
    idx = {label: i for i, label in enumerate(labels)}

    # Construir matriz cuadrada
    mat = np.zeros((n, n))
    for _, row in df_pairs.iterrows():
        i = idx[row[g1_col]]
        j = idx[row[g2_col]]
        mat[i, j] = row[dist_col]
        mat[j, i] = row[dist_col]

    return mat, labels


def node_to_dict(node, labels):
    """
    Convierte recursivamente un ClusterNode de scipy
    a un diccionario anidado compatible con D3.js hierarchy.
    """
    if node.is_leaf():
        return {
            'name':     labels[node.id],
            'height':   0.0,
            'children': []
        }
    else:
        return {
            'name':     f'node_{node.id}',
            'height':   round(float(node.dist), 6),
            'children': [
                node_to_dict(node.left,  labels),
                node_to_dict(node.right, labels)
            ]
        }


def export_dendrogram(input_path, output_path, method, label):
    """
    Lee el CSV de pares, calcula linkage y exporta el JSON.
    """
    print(f"\n{'='*50}")
    print(f"Procesando: {label}")
    print(f"{'='*50}")

    # Cargar pares
    df = pd.read_csv(input_path)
    print(f"Pares cargados: {len(df)}")

    # Convertir a matriz cuadrada
    mat, labels = pairwise_to_square(df)
    print(f"Genotipos únicos: {len(labels)}")
    print(f"Ejemplos de etiquetas: {labels[:4]}")

    # Verificar que la diagonal es 0 y la matriz es simétrica
    assert np.allclose(np.diag(mat), 0), "La diagonal no es 0"
    assert np.allclose(mat, mat.T),      "La matriz no es simétrica"

    # Condensar y calcular linkage
    condensed     = squareform(mat)
    linkage_mat   = linkage(condensed, method=method)
    print(f"Linkage calculado con método: {method}")

    # Convertir a árbol
    tree, _  = to_tree(linkage_mat, rd=True)
    tree_dict = node_to_dict(tree, labels)

    # Agregar metadata al JSON
    output = {
        'meta': {
            'n_leaves':      len(labels),
            'method':        method,
            'dist_min':      round(float(mat[mat > 0].min()), 4),
            'dist_max':      round(float(mat.max()), 4),
            'dist_mean':     round(float(mat[mat > 0].mean()), 4),
            'labels':        labels,   # lista plana para búsqueda rápida en JS
        },
        'tree': tree_dict
    }

    # Guardar
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"✓ Exportado: {output_path}  ({size_kb:.1f} KB)")

    return labels, linkage_mat


# ==========================================
# EJECUTAR
# ==========================================

results = {}

for key, cfg in FILES.items():
    if not cfg['active']:
        print(f"\n[{key}] — desactivado, saltando")
        continue

    if not os.path.exists(cfg['input']):
        print(f"\n⚠️  [{key}] Archivo no encontrado: {cfg['input']}")
        continue

    try:
        labels, lmat = export_dendrogram(
            input_path  = cfg['input'],
            output_path = cfg['output'],
            method      = LINKAGE_METHOD,
            label       = key.upper()
        )
        results[key] = {'labels': labels, 'linkage': lmat}
    except Exception as e:
        print(f"\n❌ Error en [{key}]: {e}")

# ==========================================
# RESUMEN
# ==========================================

print(f"\n{'='*50}")
print("RESUMEN")
print(f"{'='*50}")
for key, cfg in FILES.items():
    if cfg['active'] and os.path.exists(cfg['output']):
        size_kb = os.path.getsize(cfg['output']) / 1024
        print(f"  ✓ {key:10s} → {cfg['output'].split('/')[-1]}  ({size_kb:.1f} KB)")
    elif not cfg['active']:
        print(f"  — {key:10s} → desactivado")
    else:
        print(f"  ✗ {key:10s} → no generado")

print(f"\nArchivos JSON listos para cargar en el HTML Explorer")
print(f"Método de linkage usado: {LINKAGE_METHOD}")
print(f"{'='*50}")