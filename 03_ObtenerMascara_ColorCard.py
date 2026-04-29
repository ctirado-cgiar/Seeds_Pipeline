'''
Librerias
'''
from plantcv import plantcv as pcv
import numpy as np
import cv2
import os
from dotenv import load_dotenv
load_dotenv()

# Check el sitio oficial de plantcv para encontar el proceso de correccion documentado : https://plantcv.readthedocs.io/en/stable/tutorials/transform_color_correction_tutorial/

print(pcv.__version__)  # 4.46

# Configurar parámetros globales
pcv.params.debug = "plot"  # Mostrar imágenes intermedias para depuración
pcv.params.dpi = 96       # Resolución de las imágenes
pcv.params.text_size = 1    # Tamaño del texto en las imágenes
pcv.params.text_thickness = 1  # Grosor del texto en las imágenes
pcv.params.sample_label = "B73"  # Asignar una etiqueta a la muestra

# Ruta de la imagen donde se ve la tarjeta de color
ruta_imagen = os.getenv('RUTA') + '/calibracionCamara/colorCard/colorCard.jpg'
#ruta_imagen = "D:/OneDrive - CGIAR/Frijol/Metodologias/Roots/Test3/aruco/out/IMG_2164.JPG"
# Leer la imagen
img, path, filename = pcv.readimage(filename=ruta_imagen)

# Mostrar la imagen original
# pcv.plot_image(img)

# Detectar la tarjeta de color en la imagen
card_mask = pcv.transform.detect_color_card(rgb_img=img, radius=6)  # Ajusta el radio según el tamaño de la tarjeta en la imagen

# Verificar si la tarjeta de color se detectó correctamente
if card_mask is None:
    raise ValueError("No se detectó la tarjeta de color. Ajusta el radio o verifica la imagen.")

# Guardar la máscara de la tarjeta de color en una ubicación conocida
ruta_mascara = os.getenv('RUTA') + '/calibracionCamara/colorCard/colorCard_mask.png'
#ruta_mascara = "D:/OneDrive - CGIAR/Frijol/Metodologias/Roots/Test3/aruco/out/IMG_2164_MASK.JPG"
directorio_mascara = os.path.dirname(ruta_mascara)

if not os.path.exists(directorio_mascara):
    os.makedirs(directorio_mascara)

# Guardar la máscara (verificamos si se guarda correctamente)
guardado_exitoso = cv2.imwrite(ruta_mascara, card_mask)
if guardado_exitoso:
    print(f"Máscara guardada en: {ruta_mascara}")
else:
    print(f"⚠️ No se pudo guardar la máscara en: {ruta_mascara}")

# Crear la matriz de colores de la tarjeta
headers, card_matrix = pcv.transform.get_color_matrix(rgb_img=img, mask=card_mask)
print(f"Matriz detectada (card_matrix): {card_matrix.shape}")

# Definir la matriz de colores estándar (usando la posición 3 para la tarjeta de color)
# ⚠️ Puedes cambiar a pos=1 o pos=2 si la tarjeta es vertical
std_color_matrix = pcv.transform.std_color_matrix(pos=3)
print(f"Matriz estándar (std_color_matrix): {std_color_matrix.shape}")

# Validar si las matrices tienen el mismo número de parches
if card_matrix.shape != std_color_matrix.shape:
    print("⚠️ Las matrices no son compatibles para corrección de color.")
    print("   - Asegúrate de que la tarjeta tenga la orientación correcta.")
    print("   - Puedes probar con otro valor en pos=1, 2 o 3 en std_color_matrix().")
    raise ValueError("Las matrices no tienen la misma forma.")

# Aplicar la corrección de color a la imagen completa
img_corregida = pcv.transform.affine_color_correction(rgb_img=img, source_matrix=card_matrix, 
                                                      target_matrix=std_color_matrix)

# Mostrar la imagen corregida
pcv.plot_image(img_corregida)

# Guardar la imagen corregida
ruta_guardado = os.getenv('RUTA') + '/calibracionCamara/colorCard/colorCard.png'
#ruta_guardado = "D:/OneDrive - CGIAR/Frijol/Metodologias/Roots/Test3/aruco/out/IMG_2164_CORRECT.JPG"
directorio_salida = os.path.dirname(ruta_guardado)

if not os.path.exists(directorio_salida):
    os.makedirs(directorio_salida)

pcv.print_image(img=img_corregida, filename=ruta_guardado)
print(f"Imagen corregida guardada en: {ruta_guardado}")
