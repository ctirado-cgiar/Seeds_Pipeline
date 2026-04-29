############################--Alineación de formas de los objetos--############################
import os
import cv2
import numpy as np
from skimage.transform import rotate
from skimage.measure import regionprops, label
import os
from dotenv import load_dotenv
load_dotenv()

# Configuración de paths

input_folder = os.getenv('RUTA') + '/binarizadasFiltradas'
output_folder = os.getenv('RUTA') + '/binarizadasAlineadas'
os.makedirs(output_folder, exist_ok=True)
#input_folder = "D:/OneDrive - CGIAR/Frijol/Metodologias/Seeds_Pipeline/AOI_Cu/Binarized"
#output_folder = "D:/OneDrive - CGIAR/Frijol/Metodologias/Seeds_Pipeline/06_FormasAnalisis/Images"

# Parámetros de la rejilla
grid_cols = 8  # Número de columnas en la rejilla
margin = 10     # Espacio entre semillas en píxeles
bg_color = 0    # Color de fondo (negro para imágenes binarias)

# Procesar todas las imágenes en la carpeta de entrada
for filename in os.listdir(input_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.bmp')):
        # Leer imagen binaria
        img_path = os.path.join(input_folder, filename)
        binary_img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        
        # Invertir si es necesario (objetos blancos en fondo negro)
        _, binary_img = cv2.threshold(binary_img, 127, 255, cv2.THRESH_BINARY)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Lista para almacenar semillas alineadas
        aligned_seeds = []
        
        for contour in contours:
            # Crear máscara para el objeto actual
            mask = np.zeros_like(binary_img)
            cv2.drawContours(mask, [contour], -1, 255, -1)
            
            # Obtener ROI del objeto
            x, y, w, h = cv2.boundingRect(contour)
            roi = mask[y:y+h, x:x+w]
            
            # Calcular orientación y alinear
            labeled = label(roi > 0)
            props = regionprops(labeled)
            if props:
                angle = props[0].orientation
                angle_deg = np.degrees(angle)
                # Rotar para alinear el eje mayor horizontalmente
                aligned = rotate(roi, -angle_deg, resize=True, order=0, preserve_range=True)
                aligned = aligned.astype(np.uint8)
                aligned_seeds.append(aligned)
        
        # Crear imagen de rejilla
        if aligned_seeds:
            # Calcular tamaño máximo para normalizar
            max_h = max([s.shape[0] for s in aligned_seeds])
            max_w = max([s.shape[1] for s in aligned_seeds])
            
            # Crear lienzo para la rejilla
            rows = (len(aligned_seeds) + grid_cols - 1) // grid_cols
            grid_h = rows * (max_h + margin) + margin
            grid_w = grid_cols * (max_w + margin) + margin
            grid = np.full((grid_h, grid_w), bg_color, dtype=np.uint8)
            
            # Colocar cada semilla en la rejilla
            for i, seed in enumerate(aligned_seeds):
                row = i // grid_cols
                col = i % grid_cols
                y = margin + row * (max_h + margin)
                x = margin + col * (max_w + margin)
                
                # Centrar la semilla en su celda
                y_offset = y + (max_h - seed.shape[0]) // 2
                x_offset = x + (max_w - seed.shape[1]) // 2
                
                grid[y_offset:y_offset+seed.shape[0], x_offset:x_offset+seed.shape[1]] = seed
            
            # Guardar imagen resultante
            output_path = os.path.join(output_folder, f"{filename}")
            cv2.imwrite(output_path, grid)

print("Procesamiento completado!")
