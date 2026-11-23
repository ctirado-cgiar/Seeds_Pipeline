# common.py
"""
Utilidades compartidas por los scripts de Seeds_Pipeline.

Centraliza tres cosas que antes estaban repetidas (o rotas) en cada script:

1. Ruta del ensayo (variable RUTA) y rutas de carpetas.
2. Parámetros: el orquestador los exporta como variables de entorno ORC_<NOMBRE>;
   param() las lee y, si no existen (ejecución manual), usa el valor por defecto.
   log_params() deja constancia de lo realmente usado en <RUTA>/parametros_usados.json.
3. Tabla de muestras: une color, morfometría y forma (EFA) por clave de imagen y,
   si existe, el libro de campo, para los pasos de distancias y agrupamiento.
"""
from __future__ import annotations

import glob
import json
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

SCRIPTS_DIR = Path(__file__).resolve().parent
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")

try:  # .env en scripts/ (como indica el README) o en el directorio actual
    from dotenv import load_dotenv
    load_dotenv(SCRIPTS_DIR / ".env")
    load_dotenv()
except ImportError:  # python-dotenv es opcional si RUTA ya está en el entorno
    pass


# ── Ruta y carpetas ──────────────────────────────────────────────────────────

def get_ruta() -> str:
    """Carpeta del ensayo. Termina el script con un mensaje claro si no está definida."""
    ruta = os.environ.get("RUTA")
    if not ruta:
        raise SystemExit("RUTA no está definida. Defínela en scripts/.env "
                         "(RUTA=D:/ruta/al/ensayo) o ejecuta desde el orquestador.")
    if not os.path.isdir(ruta):
        raise SystemExit(f"RUTA no existe o no es una carpeta: {ruta}")
    return ruta


def path(*parts: str) -> str:
    """Ruta dentro del ensayo: path('Morfometria', 'metricasCompletas.csv')."""
    return os.path.join(get_ruta(), *parts)


def list_images(folder: str) -> list[str]:
    """Nombres de imagen de una carpeta, ordenados (los scripts antes usaban os.listdir)."""
    return sorted(f for f in os.listdir(folder) if f.lower().endswith(IMAGE_EXTS))


def strip_ext(name: str) -> str:
    base, ext = os.path.splitext(name)
    return base if ext.lower() in IMAGE_EXTS else name


# ── Parámetros ───────────────────────────────────────────────────────────────

def param(name: str, default):
    """Valor del parámetro `name`: ORC_<name> si el orquestador lo exportó, si no `default`.
    El tipo de `default` decide la conversión (bool, int, float o texto)."""
    raw = os.environ.get(f"ORC_{name}")
    if raw is None or raw.strip() == "":
        return default
    try:
        if isinstance(default, bool):
            return raw.strip().lower() in ("1", "true", "si", "sí", "yes")
        if isinstance(default, int):
            return int(float(raw))
        if isinstance(default, float):
            return float(raw.replace(",", "."))
    except ValueError:
        print(f"[AVISO] ORC_{name}={raw!r} no es válido; se usa el valor por defecto {default!r}")
        return default
    return raw


def log_params(step: str, values: dict) -> None:
    """Imprime y guarda los parámetros realmente usados en un paso (reproducibilidad)."""
    print(f"Parámetros usados [{step}]: " + ", ".join(f"{k}={v}" for k, v in values.items()))
    file = path("parametros_usados.json")
    try:
        with open(file, encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data[step] = {"fecha": datetime.now().isoformat(timespec="seconds"), **values}
    with open(file, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, default=str)


def show_plots() -> bool:
    """False por defecto: las figuras se guardan y no bloquean el pipeline con plt.show()."""
    return param("SHOW_PLOTS", False)


def finish_figure(plt) -> None:
    """Muestra la figura solo si SHOW_PLOTS está activo; si no, la cierra."""
    if show_plots():
        plt.show()
    else:
        plt.close("all")


# ── Filtros de objetos (compartidos por 08, 10.0 y 11.0) ─────────────────────

_FILTER_DEFAULTS = {
    "":   dict(AREA_MIN=200, AREA_MAX=12000, ANCHO_MIN=5, ANCHO_MAX=105, LARGO_MIN=10, LARGO_MAX=190),
    "_F": dict(AREA_MIN=200, AREA_MAX=10000, ANCHO_MIN=5, ANCHO_MAX=105, LARGO_MIN=10, LARGO_MAX=190),
}


def object_filters(suffix: str = "") -> dict:
    """Límites de área (px²), ancho y largo (px) del rectángulo mínimo.
    suffix='' → paso 08;  suffix='_F' → paso 11.0 (parámetros AREA_MIN_F, ...)."""
    return {k: param(k + suffix, v) for k, v in _FILTER_DEFAULTS[suffix].items()}


def passes_filters(area: float, width: float, length: float, f: dict) -> bool:
    """width/length en px, con width <= length."""
    return (f["AREA_MIN"] <= area <= f["AREA_MAX"]
            and f["ANCHO_MIN"] <= width <= f["ANCHO_MAX"]
            and f["LARGO_MIN"] <= length <= f["LARGO_MAX"])


# ── Claves de imagen ─────────────────────────────────────────────────────────

def normalizar_clave(valor) -> str:
    """in_row=1224.jpg → '1224';  in_row=1234_2.jpg → '1234' (réplica fotográfica);
    G4001.jpg → 'G4001'."""
    s = str(valor).strip()
    s = re.sub(r"(?i)^in_row=", "", s)
    s = re.sub(r"\.(jpg|jpeg|png|tif|tiff|bmp)$", "", s, flags=re.IGNORECASE)
    m = re.match(r"^(\d+)[_-]\d+$", s)
    if m:
        s = m.group(1)
    return s.strip()


def es_imagen_principal(valor) -> bool:
    """False para réplicas fotográficas _2, _3, ... (solo sin sufijo o _1 es principal)."""
    s = str(valor).strip()
    s = re.sub(r"(?i)^in_row=", "", s)
    s = re.sub(r"\.(jpg|jpeg|png|tif|tiff|bmp)$", "", s, flags=re.IGNORECASE)
    m = re.match(r"^(\d+)[_-](\d+)$", s)
    return int(m.group(2)) == 1 if m else True


# ── Tabla de muestras ────────────────────────────────────────────────────────

# nombre → (archivo dentro del ensayo, columna con el nombre de imagen)
SOURCES = {
    "color":       (("Colorimetria", "analisis_colores.csv"),             "Image"),
    "morfometria": (("Morfometria", "metricasCompletas_summary.csv"),     "Imagen"),
    "formas":      (("formaPromedio", "efa_coefficients_all_images.csv"), "image_name"),
}


def load_samples(sources=("color",), field_book: bool = True) -> pd.DataFrame:
    """Una fila por foto principal con las fuentes pedidas ('color', 'morfometria', 'formas')
    unidas por clave normalizada. Si existe libroCampo/libroCampo.csv se añaden sus columnas.
    Devuelve columnas 'key' (clave normalizada) e 'image' (nombre original)."""
    merged = None
    for name in sources:
        parts, col = SOURCES[name]
        file = path(*parts)
        if not os.path.exists(file):
            raise SystemExit(f"Falta {file}. Ejecuta antes el paso que lo genera.")
        df = pd.read_csv(file)
        if col not in df.columns:
            raise SystemExit(f"{file} no tiene la columna '{col}' (tiene {list(df.columns)[:6]}...)")
        df = df[df[col].astype(str).apply(es_imagen_principal)].copy()
        df["key"] = df[col].astype(str).apply(normalizar_clave)
        df = df.drop_duplicates(subset="key", keep="first")
        df = df.rename(columns={col: "image"}) if merged is None else df.drop(columns=[col])
        merged = df if merged is None else pd.merge(merged, df, on="key", how="inner",
                                                    suffixes=("", f"_{name}"))
    if field_book:
        book = path("libroCampo", "libroCampo.csv")
        if os.path.exists(book):
            fb = pd.read_csv(book)
            id_col = next((c for c in fb.columns if c.lower() == "in_row"), None)
            if id_col:
                fb["key"] = fb[id_col].astype(str).str.strip()
                fb = fb.drop_duplicates(subset="key", keep="first")
                merged = pd.merge(merged, fb, on="key", how="left", suffixes=("", "_campo"))
    return merged.reset_index(drop=True)


def make_labels(df: pd.DataFrame, default_cols: str = "", sep: str = "_") -> list[str]:
    """Etiqueta por muestra: el nombre de imagen sin extensión (como en tu versión).
    Con el parámetro LABEL_COLS (p. ej. "Line,Env,REP_usada") se antepone esas columnas
    del libro de campo."""
    wanted = [c.strip() for c in str(param("LABEL_COLS", default_cols)).split(",") if c.strip()]
    cols = [c for c in wanted if c in df.columns and c != "In_row"]
    stem = df["image"].astype(str).apply(strip_ext)
    labels = df[cols].astype(str).agg(sep.join, axis=1) + sep + stem if cols else stem
    labels = labels.tolist()
    seen: dict[str, int] = {}
    for i, lab in enumerate(labels):          # etiquetas únicas (la matriz las usa como índice)
        seen[lab] = seen.get(lab, 0) + 1
        if seen[lab] > 1:
            labels[i] = f"{lab}{sep}dup{seen[lab]}"
    return labels
