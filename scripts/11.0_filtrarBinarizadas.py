import cv2
import numpy as np
import os
import glob
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────
CARPETA_ENTRADA = os.getenv('RUTA') + '/Binarizadas'
CARPETA_SALIDA  = os.getenv('RUTA') + '/binarizadasFiltradas'

# Filtros (mismos criterios del proceso principal)
AREA_MIN   = 200
AREA_MAX   = 10000
ANCHO_MIN  = 5
ANCHO_MAX  = 105
LARGO_MIN  = 10
LARGO_MAX  = 190

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

        if area < AREA_MIN or area > AREA_MAX:
            continue

        rect = cv2.minAreaRect(contorno)
        (x, y), (w, h), angulo = rect
        w, h = (h, w) if w > h else (w, h)

        if w < ANCHO_MIN or w > ANCHO_MAX:
            continue

        if h < LARGO_MIN or h > LARGO_MAX:
            continue

        if h/w > 2.2:  # Relación largo/ancho
            continue

        cv2.drawContours(salida, [contorno], -1, color=255, thickness=cv2.FILLED)

    cv2.imwrite(ruta_salida, salida)


def main():
    os.makedirs(CARPETA_SALIDA, exist_ok=True)

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
