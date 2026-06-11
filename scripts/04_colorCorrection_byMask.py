# 04_ColorCorrection_ByMask.py
from plantcv import plantcv as pcv
from tqdm import tqdm
import numpy as np
import cv2
import os
from dotenv import load_dotenv
load_dotenv()

# Configurar parámetros globales
pcv.params.debug = None  # Desactivar la visualización automática de PlantCV

# Definir rutas
ruta_mascara       = os.getenv('RUTA') + '/calibracionCamara/colorCard/colorCard_mask.png'
carpeta_imagenes   = os.getenv('RUTA') + '/noDistorcion/'
carpeta_corregidas = os.getenv('RUTA') + '/colorCorrejidas/'
os.makedirs(carpeta_corregidas, exist_ok=True)

# Cargar la máscara de la tarjeta de color
card_mask = cv2.imread(ruta_mascara, cv2.IMREAD_GRAYSCALE)
if card_mask is None:
    raise ValueError(f"No se pudo cargar la máscara desde: {ruta_mascara}")


pos = 3  # Posición de la tarjeta de color (1, 2 o 3) para std_color_matrix()
std_color_matrix = pcv.transform.std_color_matrix(pos=pos)

# Función para corregir el color de una imagen dada la máscara y la matriz estándar
def corregir_color_imagen(ruta_imagen, card_mask, std_color_matrix, carpeta_corregidas):
    img = cv2.imread(ruta_imagen)
    if img is None:
        print(f"Error: No se pudo cargar {ruta_imagen}")
        return None, None

    headers, card_matrix = pcv.transform.get_color_matrix(rgb_img=img, mask=card_mask)
    img_corregida = pcv.transform.affine_color_correction(
        rgb_img=img,
        source_matrix=card_matrix,
        target_matrix=std_color_matrix
    )

    nombre_archivo = os.path.basename(ruta_imagen)
    ruta_guardado  = os.path.join(carpeta_corregidas, nombre_archivo)
    cv2.imwrite(ruta_guardado, img_corregida)

    return img, img_corregida

# Procesar todas las imágenes en la carpeta
archivos_imagen = [f for f in os.listdir(carpeta_imagenes)
                   if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
print(f"Procesando {len(archivos_imagen)} imágenes...\n")

for nombre_archivo in tqdm(archivos_imagen, desc="Progreso", unit="img"):
    ruta_imagen = os.path.join(carpeta_imagenes, nombre_archivo)
    corregir_color_imagen(ruta_imagen, card_mask, std_color_matrix, carpeta_corregidas)

print("\n✓ Procesamiento completado!")
