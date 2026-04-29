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

#------------------------------------------------------------------DETECCION------------------------------------------------------------------#
# termination criteria
criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# CORRECCIÓN: Para un tablero de 8x7 cuadros, son 7x6 esquinas interiores
# prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
objp = np.zeros((7*6,3), np.float32)  # Cambiado de 6*7 a 7*6
objp[:,:2] = np.mgrid[0:7,0:6].T.reshape(-1,2)  # Cambiado de (0:7,0:6) a (0:7,0:6) - correcto

# Arrays to store object points and image points from all the images.
objpoints = [] # 3d point in real world space.
imgpoints = [] # 2d points in image plane.

images = glob.glob(os.getenv('RUTA') + '/calibracionCamara/ajedrez/*.jpg')

# DEBUG: Verificar cuántas imágenes se encuentran
print(f"Encontré {len(images)} imágenes")

for fname in images:
    img = cv.imread(fname)
    if img is None:
        print(f"Error: No se pudo cargar la imagen {fname}")
        continue
        
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    # CORRECCIÓN: Buscar esquinas para 7x6 (esquinas interiores)
    ret, corners = cv.findChessboardCorners(gray, (7,6), None)  # (ancho, alto) en esquinas

    # If found, add object points, image points (after refining them)
    if ret == True:
        objpoints.append(objp)
        corners2 = cv.cornerSubPix(gray,corners, (11,11), (-1,-1), criteria)
        imgpoints.append(corners2)

        # Draw and display the corners
        img_corners = img.copy()
        cv.drawChessboardCorners(img_corners, (7,6), corners2, ret)
        # Guardar (controlado por flag)
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

# DEBUG: Verificar cuántas imágenes tuvieron esquinas detectadas
print(f"Imágenes con esquinas detectadas: {len(objpoints)}")

#------------------------------------------------------------------CALIBRACION------------------------------------------------------------------#
# Solo calibrar si tenemos suficientes imágenes
if len(objpoints) > 0:
    ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

    # Print the camera matrix and distortion coefficients
    print("Camera matrix:")
    print(mtx)
    print("Distortion coefficients:")
    print(dist)
    
    #------------------------------------------------------------------Sin distorsión------------------------------------------------------------------#
    #Carpetas automáticas para guardar resultados y consultar parámetros
    os.makedirs(os.getenv('RUTA') + '/calibracionCamara/colorCard', exist_ok=True)
    os.makedirs(os.getenv('RUTA') + '/calibracionCamara/parametrosCorreccion', exist_ok=True)

    img = cv.imread(os.getenv('RUTA') + '/calibracionCamara/ajedrez/0.jpg')
    if img is not None:
        h,  w = img.shape[:2]
        newcameramtx, roi = cv.getOptimalNewCameraMatrix(mtx, dist, (w,h), 1, (w,h))

        # undistort
        dst = cv.undistort(img, mtx, dist, None, newcameramtx)

        # crop the image
        x, y, w, h = roi
        dst = dst[y:y+h, x:x+w]
        cv.imwrite(os.getenv('RUTA') + '/calibracionCamara/colorCard/colorCard.jpg', dst)
        
        # Guardar los parámetros
        np.savez(os.getenv('RUTA') + '/calibracionCamara/parametrosCorreccion/calibracion_params.npz', mtx=mtx, dist=dist)
        np.savetxt(os.getenv('RUTA') + '/calibracionCamara/parametrosCorreccion/camera_matrix.txt', mtx)
        np.savetxt(os.getenv('RUTA') + '/calibracionCamara/parametrosCorreccion/dist_coeffs.txt', dist)
        print("Calibración completada y parámetros guardados")
    else:
        print("Error: No se pudo cargar la imagen para prueba de distorsión")
else:
    print("Error: No se detectaron esquinas en ninguna imagen. No se puede calibrar.")