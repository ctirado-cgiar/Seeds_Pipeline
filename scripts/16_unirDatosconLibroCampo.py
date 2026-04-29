import pandas as pd
import numpy as np
import os
import re
import glob
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BASE  = os.getenv('RUTA')
TRIAL = os.path.basename(BASE.rstrip('/\\'))
FECHA = datetime.now().strftime('%Y%m%d')

# ==========================================
# CONFIGURACIÓN
# ==========================================

COL_ID = 'In_row'

# Cada entrada: (ruta o patrón glob, columna clave, alias legible, tipo)
# tipo: 'principal'  → usar solo imagen principal (sin sufijo numérico o _1/-1)
#       'conteo'     → sumar todas las repeticiones fotográficas del mismo in_row
#       'campo'      → libro de campo, clave ya normalizada (solo número)
FUENTES = {
    'field'      : (BASE + '/libroCampo/libroCampo.csv',                      'In_row',  'Libro de campo',  'campo'),
    'conteo'     : (BASE + '/conteo/reporte_*.csv',                           'Imagen',  'Conteo',          'conteo'),
    'color'      : (BASE + '/Colorimetria/analisis_colores.csv',              'Image',   'Colores',         'principal'),
    'morfometria': (BASE + '/Morfometria/metricasCompletas_summary.csv',      'Imagen',  'Morfometría',     'principal'),
    'formas'     : (BASE + '/formaPromedio/efa_coefficients_all_images.csv',  'image_name', 'Formas',       'principal'),
}

# ==========================================
# NORMALIZACIÓN DE CLAVES
# ==========================================

def normalizar_clave(valor):
    """
    Extrae el número base del nombre de imagen.

    Ejemplos:
      in_row=1224.jpg   → '1224'
      in_row=1234_2.jpg → '1234'   (rep fotográfica, se descarta sufijo)
      in_row=1234-2.jpg → '1234'
      1224.jpg          → '1224'
      1224              → '1224'
      G4001.jpg         → 'G4001'  (nombres alfanuméricos sin prefijo in_row=)
    """
    s = str(valor).strip()

    # Quitar prefijo in_row= o In_row= si existe
    s = re.sub(r'(?i)^in_row=', '', s)

    # Quitar extensión de imagen
    s = re.sub(r'\.(jpg|jpeg|png|tif|tiff|bmp)$', '', s, flags=re.IGNORECASE)

    # Quitar sufijo de repetición fotográfica: _1, _2, _3, -1, -2, -3, etc.
    # Solo si el cuerpo antes del sufijo es puramente numérico
    m = re.match(r'^(\d+)[_-]\d+$', s)
    if m:
        s = m.group(1)

    return s.strip()


def es_imagen_principal(valor):
    """
    Retorna True si la imagen es la principal (sin sufijo o con sufijo _1/-1).
    False si es repetición fotográfica _2, _3, etc.

    Ejemplos:
      1224.jpg      → True   (sin sufijo)
      1224_1.jpg    → True   (primera toma)
      1224-1.jpg    → True
      1224_2.jpg    → False
      1224-3.jpg    → False
    """
    s = str(valor).strip()
    s = re.sub(r'(?i)^in_row=', '', s)
    s = re.sub(r'\.(jpg|jpeg|png|tif|tiff|bmp)$', '', s, flags=re.IGNORECASE)

    m = re.match(r'^(\d+)[_-](\d+)$', s)
    if m:
        sufijo = int(m.group(2))
        return sufijo == 1  # solo _1 o -1 es principal
    return True  # sin sufijo numérico = principal


# ==========================================
# CARGA CON VALIDACIÓN
# ==========================================

dfs = {}

for nombre, (patron, col_clave, etiqueta, tipo) in FUENTES.items():

    # Resolver patrón glob (conteo usa reporte_*.csv)
    if '*' in patron:
        archivos = sorted(glob.glob(patron))
        if not archivos:
            print(f"  [AUSENTE]  {etiqueta:20s} → {patron}")
            continue
        ruta = archivos[-1]  # más reciente
        print(f"  [GLOB]     {etiqueta:20s} → {os.path.basename(ruta)}")
    else:
        ruta = patron
        if not os.path.exists(ruta):
            print(f"  [AUSENTE]  {etiqueta:20s} → {ruta}")
            continue

    df = pd.read_csv(ruta)

    # Detectar columna clave flexible (case-insensitive)
    col_encontrada = None
    for col in df.columns:
        if col.lower() == col_clave.lower():
            col_encontrada = col
            break
    if col_encontrada is None:
        # Intentar detectar automáticamente columnas candidatas
        candidatas = [c for c in df.columns if 'row' in c.lower() or 'image' in c.lower() or 'imagen' in c.lower()]
        if candidatas:
            col_encontrada = candidatas[0]
            print(f"  [AUTO-COL] {etiqueta:20s} → usando columna '{col_encontrada}' (esperada: '{col_clave}')")
        else:
            print(f"  [SIN CLAVE]{etiqueta:20s} → columna '{col_clave}' no encontrada. Saltando.")
            print(f"             Columnas disponibles: {df.columns.tolist()}")
            continue

    # ── Normalizar clave ──────────────────────────────────────────────────────
    df['_raw_key'] = df[col_encontrada].astype(str)
    df['key']      = df['_raw_key'].apply(normalizar_clave)

    if tipo == 'campo':
        # Libro de campo: la clave ya es el número, solo limpiar
        df['key'] = df[col_encontrada].astype(str).str.strip()

    elif tipo == 'conteo':
        # Sumar semillas de todas las repeticiones fotográficas del mismo in_row
        col_semillas = None
        for c in df.columns:
            if c.lower() in ('semillas','seeds','count','conteo','total'):
                col_semillas = c
                break

        if col_semillas:
            df[col_semillas] = pd.to_numeric(df[col_semillas], errors='coerce').fillna(0)
            df_conteo = (df.groupby('key', as_index=False)
                           .agg(Semillas_total=(col_semillas, 'sum'),
                                Imagenes_contadas=('_raw_key', 'count')))
            dfs[nombre] = df_conteo
            print(f"  [OK]       {etiqueta:20s} → {len(df_conteo)} entradas "
                  f"({len(df)} imágenes sumadas, col semillas: '{col_semillas}')")
            continue
        else:
            print(f"  [AVISO]    {etiqueta:20s} → columna de conteo no encontrada. "
                  f"Columnas: {df.columns.tolist()}")
            # Guardar sin agregar
            df = df[['key']].copy()

    elif tipo == 'principal':
        # Solo conservar imágenes principales (sin sufijo repetición o _1/-1)
        mascara   = df['_raw_key'].apply(es_imagen_principal)
        n_total   = len(df)
        df        = df[mascara].copy()
        n_descartadas = n_total - len(df)
        if n_descartadas > 0:
            print(f"  [FILTRO]   {etiqueta:20s} → {n_descartadas} rep. fotográficas descartadas "
                  f"(quedaron {len(df)} imágenes principales)")

    df = df.drop(columns=['_raw_key'], errors='ignore')
    df = df.drop(columns=[col_encontrada], errors='ignore') if col_encontrada != 'key' else df

    # Verificar duplicados en key
    dupes = df['key'].duplicated()
    if dupes.any():
        print(f"  [AVISO]    {etiqueta:20s} → {dupes.sum()} clave(s) duplicadas — se conserva la primera.")
        df = df.drop_duplicates(subset='key', keep='first')

    dfs[nombre] = df
    print(f"  [OK]       {etiqueta:20s} → {len(df)} filas, {len(df.columns)} columnas")

if not dfs:
    raise RuntimeError("No se cargó ningún archivo. Verifica RUTA en el .env.")

# ==========================================
# MERGE EN CADENA
# ==========================================

base_key    = 'field' if 'field' in dfs else next(iter(dfs))
df_merged   = dfs[base_key].copy()

print(f"\n  Base de merge: '{base_key}' ({len(df_merged)} filas)")

for nombre, df in dfs.items():
    if nombre == base_key:
        continue
    antes = len(df_merged)
    df_merged = pd.merge(df_merged, df, on='key', how='left',
                         suffixes=('', f'_{nombre}'))
    print(f"  Merge con '{nombre}': {antes} → {len(df_merged)} filas")

# ==========================================
# DIAGNÓSTICO
# ==========================================

keys_base = set(dfs[base_key]['key'])
print(f"\n  Claves en libro de campo: {len(keys_base)}")

for nombre, df in dfs.items():
    if nombre == base_key:
        continue
    etiqueta   = FUENTES[nombre][2]
    keys_fuente = set(df['key'])
    sin_match   = keys_fuente - keys_base
    sin_datos   = keys_base - keys_fuente
    if sin_match:
        print(f"  [AVISO] {etiqueta}: {len(sin_match)} clave(s) del pipeline sin match en libro de campo:")
        print(f"          {sorted(sin_match)[:10]}{'...' if len(sin_match)>10 else ''}")
    if sin_datos:
        print(f"  [INFO]  {etiqueta}: {len(sin_datos)} entrada(s) del libro de campo sin datos de pipeline.")

# ==========================================
# GUARDAR
# ==========================================

carpeta_out = os.path.join(BASE, 'resultadosUnidos')
os.makedirs(carpeta_out, exist_ok=True)
nombre_out  = f'metricasCompletasSemillas_Conteo-Color-Morfometria-Forma_{TRIAL}_{FECHA}.csv'
ruta_out    = os.path.join(carpeta_out, nombre_out)

df_merged = df_merged.rename(columns={'key': COL_ID})
df_merged.to_csv(ruta_out, index=False)

print(f"\n  Guardado: {ruta_out}")
print(f"  Filas: {len(df_merged)}  |  Columnas: {len(df_merged.columns)}")
