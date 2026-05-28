#02_DistorcionCorrection_Ajedrez
import cv2 as cv
import numpy as np
import glob
import os
from tqdm import tqdm
from dotenv import load_dotenv
load_dotenv()


#Cargar parámetros de calibración
calib_data = np.load(os.getenv('RUTA') + '/calibracionCamara/parametrosCorreccion/calibracion_params.npz')
mtx = calib_data['mtx']  # Matriz de cámara
dist = calib_data['dist']  # Coeficientes de distorsión


#Rutas de entrada y salida
input_dir = os.getenv('RUTA') + '/all/*.jpg' 
output_dir = os.getenv('RUTA') + '/noDistorcion/'
os.makedirs(output_dir, exist_ok=True)

# Obtener la lista de imágenes a procesar
new_images = glob.glob(input_dir)
print(f"Procesando {len(new_images)} imágenes...\n")

# Procesar cada imagen con corrección de distorsión y guardarla en la carpeta de salida
for img_path in tqdm(new_images, desc="Progreso", unit="img"):
    img = cv.imread(img_path)
    h, w = img.shape[:2]
    
    # Obtener la nueva matriz de cámara y el área de interés después de la corrección
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))
    undistorted_img = cv.undistort(img, mtx, dist, None, newcameramtx)
    x, y, w, h = roi
    undistorted_img = undistorted_img[y:y+h, x:x+w]
    
    # Guardar con ruta personalizada
    filename = os.path.basename(img_path)
    output_path = os.path.join(output_dir, filename)
    cv.imwrite(output_path, undistorted_img)

print("\n✓ ¡Corrección completada para todas las imágenes!")
