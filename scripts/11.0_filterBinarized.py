# 11.0_filterBinarized.py
import cv2
import numpy as np
import os
import glob
from dotenv import load_dotenv

load_dotenv()
import common

# ─────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────
CARPETA_ENTRADA = common.path('Binarizadas')
CARPETA_SALIDA  = common.path('binarizadasFiltradas')

# Filtros (parámetros AREA_MIN_F, ANCHO_MIN_F, ... del orquestador)
FILTROS    = common.object_filters('_F')

# Relación largo/ancho máxima. Quita semillas pegadas (dos semillas en fila dan ~2x), PERO
# también elimina semillas realmente alargadas: con 2.2 se pierde ~40 % de las semillas de
# genotipos con AR mediana ≈ 2.1-2.2. Sesga el análisis de forma hacia semillas redondas.
# 0 = sin filtro de relación. Valor histórico: 2.2.
AR_MAX_F   = common.param('AR_MAX_F', 2.2)

# ─────────────────────────────────────────────


def filtrar_imagen_binaria(ruta_entrada: str, ruta_salida: str):
    imagen = cv2.imread(ruta_entrada, cv2.IMREAD_GRAYSCALE)
    if imagen is None:
        return

    _, binaria = cv2.threshold(imagen, 127, 255, cv2.THRESH_BINARY)
    contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    salida = np.zeros_like(binaria)

    for contorno in contornos:
        area = cv2.contourArea(contorno)

        rect = cv2.minAreaRect(contorno)
        (x, y), (w, h), angulo = rect
        w, h = (h, w) if w > h else (w, h)

        if not common.passes_filters(area, w, h, FILTROS):
            continue

        if AR_MAX_F > 0 and w > 0 and h / w > AR_MAX_F:  # Relación largo/ancho
            continue

        cv2.drawContours(salida, [contorno], -1, color=255, thickness=cv2.FILLED)

    cv2.imwrite(ruta_salida, salida)


def main():
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    common.log_params('11.0_filterBinarized', dict(AR_MAX_F=AR_MAX_F, **FILTROS))

    extensiones = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tif", "*.tiff")
    archivos = []
    for ext in extensiones:
        archivos.extend(glob.glob(os.path.join(CARPETA_ENTRADA, ext)))

    for ruta in sorted(archivos):
        nombre   = os.path.basename(ruta)
        ruta_out = os.path.join(CARPETA_SALIDA, nombre)
        filtrar_imagen_binaria(ruta, ruta_out)


if __name__ == "__main__":
    main()
