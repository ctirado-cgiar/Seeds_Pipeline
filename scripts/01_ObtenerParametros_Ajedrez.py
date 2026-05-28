# 01_ObtenerParametros_Ajedrez.py

import numpy as np
import cv2 as cv
import glob
import os
from dotenv import load_dotenv
load_dotenv()

GUARDAR_CHESSBOARD_CORNERS = True
output_corners_dir = os.path.join(
    os.getenv('RUTA'),
    'calibracionCamara',
    'ajedrezCorners'
)
os.makedirs(output_corners_dir, exist_ok=True)

criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

objp = np.zeros((7*6,3), np.float32)
objp[:,:2] = np.mgrid[0:7,0:6].T.reshape(-1,2)

objpoints = []
imgpoints = []

images = glob.glob(os.getenv('RUTA') + '/calibracionCamara/ajedrez/*.jpg')

print(f"Encontré {len(images)} imágenes")

for fname in images:
    img = cv.imread(fname)
    if img is None:
        print(f"Error: No se pudo cargar la imagen {fname}")
        continue
        
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    ret, corners = cv.findChessboardCorners(gray, (7,6), None)

    if ret == True:
        objpoints.append(objp)
        corners2 = cv.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)
        imgpoints.append(corners2)

        img_corners = img.copy()
        cv.drawChessboardCorners(img_corners, (7,6), corners2, ret)
        if GUARDAR_CHESSBOARD_CORNERS:
            base_name = os.path.basename(fname)
            name, ext = os.path.splitext(base_name)
            out_path = os.path.join(
                output_corners_dir,
                f"{name}_corners{ext}"
            )
            cv.imwrite(out_path, img_corners)
    else:
        print(f"No se encontraron esquinas en: {fname}")

cv.destroyAllWindows()

print(f"Esquinas detectadas en {len(objpoints)} imágenes")

if len(objpoints) > 0:
    ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

    print("Matriz de cámara:")
    print(mtx)
    print("Coeficientes de distorsión:")
    print(dist)
    
    os.makedirs(os.getenv('RUTA') + '/calibracionCamara/colorCard', exist_ok=True)
    os.makedirs(os.getenv('RUTA') + '/calibracionCamara/parametrosCorreccion', exist_ok=True)

    img = cv.imread(os.getenv('RUTA') + '/calibracionCamara/ajedrez/0.jpg')
    if img is not None:
        h, w = img.shape[:2]
        newcameramtx, roi = cv.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))
        dst = cv.undistort(img, mtx, dist, None, newcameramtx)

        x, y, w, h = roi
        dst = dst[y:y+h, x:x+w]
        cv.imwrite(os.getenv('RUTA') + '/calibracionCamara/colorCard/colorCard.jpg', dst)
        
        # Guardar parámetros de calibración para uso posterior
        np.savez(os.getenv('RUTA') + '/calibracionCamara/parametrosCorreccion/calibracion_params.npz', mtx=mtx, dist=dist)
        np.savetxt(os.getenv('RUTA') + '/calibracionCamara/parametrosCorreccion/camera_matrix.txt', mtx)
        np.savetxt(os.getenv('RUTA') + '/calibracionCamara/parametrosCorreccion/dist_coeffs.txt', dist)
        print("Calibración completada y parámetros guardados")
    else:
        print("Error: No se pudo cargar la imagen para prueba de distorsión")
else:
    print("Error: No se detectaron esquinas en ninguna imagen. No se puede calibrar.")
