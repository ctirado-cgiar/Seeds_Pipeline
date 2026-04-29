import cv2 as cv
import numpy as np
import glob
import os
from dotenv import load_dotenv
load_dotenv()


# 1. Cargar parámetros de calibración
#calib_data = np.load('D:/OneDrive - CGIAR/Frijol/Procesamiento/Seeds_Pipeline/Mexico_Diversity/Calibracion/parametrosCorreccion/calibracion_params.npz')
calib_data = np.load(os.getenv('RUTA') + '/calibracionCamara/parametrosCorreccion/calibracion_params.npz')
mtx = calib_data['mtx']  # Matriz de cámara
dist = calib_data['dist']  # Coeficientes de distorsión


# 2. Procesar nuevas imágenes
#input_dir = 'D:/OneDrive - CGIAR/Frijol/Experimentos/PP009BP2025_BioacumulacionCdPb/Ensayo/Preparacion/Semillas/hidrophonia/*.jpg'  # Carpeta con imágenes nuevas
input_dir = os.getenv('RUTA') + '/all/*.jpg'  # Carpeta con imágenes nuevas
output_dir = os.getenv('RUTA') + '/noDistorcion/'  # Carpeta de salida (personalizable)
#output_dir = 'D:/OneDrive - CGIAR/Frijol/Experimentos/PP009BP2025_BioacumulacionCdPb/Ensayo/Preparacion/Semillas/noDistorcion/'  # Carpeta de salida (personalizable)
os.makedirs(output_dir, exist_ok=True)

# 3. Procesar imágenes
new_images = glob.glob(input_dir)

for img_path in new_images:
    img = cv.imread(img_path)
    h, w = img.shape[:2]
    
    # Corrección con ROI
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))
    undistorted_img = cv.undistort(img, mtx, dist, None, newcameramtx)
    x, y, w, h = roi
    undistorted_img = undistorted_img[y:y+h, x:x+w]
    
    # Guardar con ruta personalizada
    filename = os.path.basename(img_path)
    output_path = os.path.join(output_dir, filename.replace('.jpg', '.jpg'))
    cv.imwrite(output_path, undistorted_img)

print(f"¡Imágenes corregidas guardadas en: {output_dir}")

for img_path in new_images:
    img = cv.imread(img_path)
    h, w = img.shape[:2]
    
    # Corrección con ROI
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))
    undistorted_img = cv.undistort(img, mtx, dist, None, newcameramtx)
    x, y, w, h = roi
    undistorted_img = undistorted_img[y:y+h, x:x+w]
    
    # Guardar
    output_path = img_path.replace('.jpg', '.jpg')
    cv.imwrite(output_path, undistorted_img)

print("¡Corrección completada para todas las imágenes!")
