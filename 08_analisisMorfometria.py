'''
Script eleborado a detalle para el programa de mejoramiento de frijol
Escrito en Python 3.11.9 en un entorno de desarrollo virtual por Cristian Tirado.

Librerias
- Os instalado por defecto
- OpenCV istalado por consola en la version
- Numpy instalado por en la terminal en la version 
- Csv importado directamente
- Random importado directamente
- Matplotlib instalado por la terminal en la versión

Que hace?
- Mejora el contraste de las imagenes ingresadas basado en un Alpha y Beta definido por el usuario
- Filtra objetos en la imagen que puden ser considerados como suciedad, no se aplican operaciones morfologicas para no cambiar las areas reales.
- Toma un set de imagenes previamente binarizadas, detecta los objetos y calcula algunos 37 descriptores de la función procesar imagen
- Agrega todos los descriptores de la imagen a un archivo CSV y los exporta en la CARPETA INDICADA DE RESULTADOS
- Muestra el resultado de manera grafica sobre una imagen aleatoria.


COSAS QUE EL USUARIO DEBE TENER EN CUENTA:

- Debe contar con un set de imagenes con objetos de interes (hojas, vainas, semillas etc) habiendo seleccionado el area de interes a procesar, idelmente con un fondo de color similar que facilite el proceso de analisis.
- Debe suministrar en el MAIN la ruta de las carpetas solicitadas, tales como Origen de las Imagenes con el area de interes, las binarizadas, 
  las segmentadas y la carpeta donde se almacenaran los resultados del proceso.
  El usuario dispondra de un set de imagenes.
'''



import os
import cv2
import csv
import json
import random
import numpy as np
from scipy.spatial import distance
from skimage.feature import graycomatrix, graycoprops
from dotenv import load_dotenv
load_dotenv()

#Funcion para aumentar contraste
def mejorar_contraste(imagen, alpha=1.1, beta=0):
    return cv2.convertScaleAbs(imagen, alpha=alpha, beta=beta)

#Funcion para filtrar objetos de dimensiones n<100
def eliminar_objetos_pequenos(mask, area_minima=100):
    contornos, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask_filtrada = np.zeros_like(mask)
    for cnt in contornos:
        if cv2.contourArea(cnt) >= area_minima:
            cv2.drawContours(mask_filtrada, [cnt], -1, 255, -1)
    return mask_filtrada

#def cargar_factor_escala(ruta="D:/OneDrive - CGIAR/Frijol/Datos/Imagenes/Photoboot/Mexico_Diversity/Calibracion/factor_escala.json"):
def cargar_factor_escala(ruta=os.getenv('RUTA') + '/calibracionCamara/factorEscala/factor_escala.json'):
    """Carga el factor de escala desde el archivo JSON."""
    try:
        with open(ruta, 'r') as f:
            data = json.load(f)
            return data["factor_escala"]
    except FileNotFoundError:
        print("¡Archivo de calibración no encontrado! Usando 1.0 (píxeles).")
        return 1.0


def procesar_imagen_binarizada(binary_img, nombre_imagen, imagen_original, escritor_csv, factor_escala=None):
    if factor_escala is None:
        # Intenta cargar el factor desde el JSON
        try:
            with open('factor_escala.json', 'r') as f:
                factor_escala = json.load(f)['factor_escala']
        except FileNotFoundError:
            print("¡Advertencia! No se encontró factor de escala. Usando píxeles.")
            factor_escala = 1.0

    contornos, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    imagen_contornos = imagen_original.copy()
    metricas_adicionales = []

    for i, contorno in enumerate(contornos):
        area = cv2.contourArea(contorno)
        if area < 200:
            #print(f"Advertencia: Área demasiado pequeña ({area}) en {nombre_imagen}. Saltando contorno.")
            continue
        if area > 12000:
            #print(f"Advertencia: Área demasiado grande ({area}) en {nombre_imagen}. Saltando contorno.")
            continue
        
        # Rectángulo mínimo
        rect = cv2.minAreaRect(contorno)
        (x, y), (w, h), angulo = rect
        w, h = (h, w) if w > h else (w, h)

        if w < 5 or w > 105:
            #print(f"Advertencia: Ancho fuera de rango ({w}px) en {nombre_imagen}. Saltando contorno.")
            continue

        if h < 10 or h > 190:
            #print(f"Advertencia: Largo fuera de rango ({h}px) en {nombre_imagen}. Saltando contorno.")
            continue

        # Cálculo del centro de masa
        M = cv2.moments(contorno)
        cx = int(M["m10"]/M["m00"]) if M["m00"] != 0 else 0
        cy = int(M["m01"]/M["m00"]) if M["m00"] != 0 else 0
        
        # Métricas básicas
        perimetro = cv2.arcLength(contorno, True)
        hull = cv2.convexHull(contorno)
        area_ch = cv2.contourArea(hull)

        # Usamos el convex hull para mayor eficiencia
        hull_points = hull[:, 0, :] if len(hull) > 1 else contorno[:, 0, :]
        caliper = max(np.linalg.norm(p1 - p2) for p1 in hull_points for p2 in hull_points)
        
        # Elipse ajustada
        if len(contorno) >= 5:
            ellipse = cv2.fitEllipse(contorno)
            (x_el, y_el), (diam_mayor, diam_menor), angle_el = ellipse
            major_axis = max(diam_mayor, diam_menor)
            minor_axis = min(diam_mayor, diam_menor)
            eccentricity = np.sqrt(1 - (minor_axis**2 / major_axis**2))
        else:
            major_axis = h
            minor_axis = w
            eccentricity = np.sqrt(1 - (w**2 / h**2))
        
        # Radios y diámetros
        radio_min = w/2 
        radio_max = h/2
        radio_mean = (radio_max + radio_min)/2
        diam_min = w
        diam_mean = (w + h)/2
        diam_max = h
        radius_ratio = radio_max/radio_min
        # Ángulo theta (orientación)
        theta = (180/np.pi)*(np.radians(angulo))
        form_factor = (4 * np.pi * area) / (perimetro**2) if perimetro > 0 else 0
        narrow_factor = caliper / h
        rectangularity = (h * w) / area if area > 0 else 0
        pd_ratio = perimetro / caliper if caliper > 0 else 0
        plw_ratio = perimetro / (h + w) if (h + w) > 0 else 0
        convexity = cv2.arcLength(hull, True) / perimetro if perimetro > 0 else 0
        solidez = area / area_ch if area_ch > 0 else 0
        circularity = (4 * np.pi * area) / (perimetro**2) if perimetro > 0 else 0
        circularity_norm = (perimetro**2) / (4 * np.pi * area) if area > 0 else 0
        # Haralick circularity (distancia media al centroide)
        distancias = [distance.euclidean((cx, cy), point[0]) for point in contorno]
        circularity_haralick = np.mean(distancias) / np.std(distancias) if np.std(distancias) > 0 else 0
        elongation = 1 - (w / h) if h > 0 else 0
        # Características de textura Haralick (requiere imagen en escala de grises)
        if len(imagen_original.shape) > 2:
            gray_img = cv2.cvtColor(imagen_original, cv2.COLOR_BGR2GRAY)
        # Crear máscara para el objeto actual
        mask = np.zeros_like(gray_img)
        cv2.drawContours(mask, [contorno], -1, 255, -1)
        #cv2.drawContours(mask, [rect], -1, 255, -1)
        # Extraer región de interés
        roi = cv2.bitwise_and(gray_img, gray_img, mask=mask)
        # Calcular GLCM y características Haralick
        glcm = graycomatrix(roi, distances=[1], angles=[0], levels=256, symmetric=True, normed=True)
        asm = graycoprops(glcm, 'ASM')[0, 0]
        con = graycoprops(glcm, 'contrast')[0, 0]
        cor = graycoprops(glcm, 'correlation')[0, 0]
        var = graycoprops(glcm, 'dissimilarity')[0, 0]
        idm = graycoprops(glcm, 'homogeneity')[0, 0]
        sav = graycoprops(glcm, 'energy')[0, 0]
        entropy = graycoprops(glcm, 'entropy')[0, 0]
    
        metricas = {
            "Imagen": nombre_imagen,
            "Total_seeds": len(contornos),
            "seed": i + 1,
            "W": w*factor_escala,
            "L": h*factor_escala,
            "P": perimetro*factor_escala,
            "A": area*(factor_escala**2),
            "AR": h/w if w > 0 else 0,
            "Circ": circularity,
            "Solid": solidez,
            "Centroid_X": cx,
            "Centroid_Y": cy,
            "Radius_min": radio_min*factor_escala,
            "Radius_mean": radio_mean*factor_escala,
            "Radius_max": radio_max*factor_escala,
            "Radius_ratio": radius_ratio,
            "Diam_min": diam_min*factor_escala,
            "Diam_mean": diam_mean*factor_escala,
            "Diam_max": diam_max*factor_escala,
            "Major_axis": major_axis*factor_escala,
            "Minor_axis": minor_axis*factor_escala,
            "Caliper": caliper*factor_escala,
            "Theta": theta,
            "Eccentricity": eccentricity,
            "Form_factor": form_factor,
            "Narrow_factor": narrow_factor,
            "Rectangularity": rectangularity,
            "PD_ratio": pd_ratio,
            "PLW_ratio": plw_ratio,
            "Area_CH": area_ch*(factor_escala**2),
            "Convexity": convexity,
            "Elongation": elongation,
            "Circ_haralick": circularity_haralick,
            "Circ_norm": circularity_norm,
            "ASM": asm,
            "Contrast": con,
            "Correlation": cor,
            "Variance": var,
            "IDM": idm,
            "Energy": sav,
            "Entropy": entropy
        }
        metricas_adicionales.append(metricas)

        # Dibujar anotaciones (código original)
        cv2.drawContours(imagen_contornos, [contorno], -1, (0,255,0), 1)
        cv2.drawMarker(imagen_contornos, (cx, cy), (255,0,0), markerType=cv2.MARKER_CROSS, markerSize=10, thickness=2)
        
        texto = [
            f"Seed {i+1}",
            f"Area: {area*(factor_escala**2):.1f}",
            f"W: {w*factor_escala:.1f}, L: {h*factor_escala:.1f}",
            #f"Centroide: ({cx}, {cy})",
            #f"Theta: {theta:.1f}",
            f"Circ: {circularity: .1f} , Rect: {rectangularity: .1f}",
            f"+ Metrics on CSV"
        ]
        
        y_texto = cy - 40
        for linea in texto:
            cv2.putText(imagen_contornos, linea, (cx-50, y_texto), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
            y_texto += 15

    # Escribir en CSV
    for metrica in metricas_adicionales:
        escritor_csv.writerow(metrica)

    return imagen_contornos

def main():
    # Configuración de directorios
    carpetas = {
        "input"     :   os.getenv('RUTA') + '/areaInteres',
        "binarized" :   os.getenv('RUTA') + '/Binarizadas',
        "segmented" :   os.getenv('RUTA') + '/Segmentadas',
        "results"   :   os.getenv('RUTA') + '/Morfometria'
    }
    # Crear todas las carpetas
    for dir in carpetas.values():
        os.makedirs(dir, exist_ok=True)

    # Cargar factor de escala desde JSON (si existe)
    try:
        #with open('D:/OneDrive - CGIAR/Frijol/Procesamiento/Seeds_Pipeline/Mexico_Diversity/Calibracion/factor_escala.json', 'r') as f:
        with open(os.getenv('RUTA') + '/calibracionCamara/factorEscala/factor_escala.json', 'r') as f:
            factor_data = json.load(f)
            factor_escala = factor_data['factor_escala']
            print(f"Factor de escala cargado: {factor_escala:.7f} mm/px")
    except FileNotFoundError:
        factor_escala = 1.0
        print("¡Advertencia! No se encontró factor_escala.json. Usando 1.0 (trabajando en píxeles)")

    # Ruta del CSV en carpeta Results
    csv_path = os.path.join(carpetas["results"], "metricasCompletas.csv")
    
    # Configuración de imágenes a guardar (solo para Segmented/ y Results/)
    #guardar_n = 10  # Número exacto de imágenes a guardar en estas carpetas
    guardar_n = len(os.listdir(carpetas["input"]))  #el número de imágenes disponibles
    imagenes_disponibles = [
        archivo for archivo in os.listdir(carpetas["input"]) 
        if archivo.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]
    imagenes_a_guardar = random.sample(imagenes_disponibles, min(guardar_n, len(imagenes_disponibles)))

    with open(csv_path, "w", newline="", encoding='utf-8') as archivo_csv:
        campos = ["Imagen", "Total_seeds", "seed", "W", "L", "P", "A", 
                "AR", "Circ", "Solid", "Centroid_X", "Centroid_Y",
                "Radius_min", "Radius_mean", "Radius_max", "Radius_ratio",
                "Diam_min", "Diam_mean", "Diam_max", "Major_axis", "Minor_axis",
                "Caliper", "Theta", "Eccentricity", "Form_factor", "Narrow_factor",
                "Rectangularity", "PD_ratio", "PLW_ratio", "Area_CH",
                "Convexity", "Elongation", "Circ_haralick", "Circ_norm",
                "ASM", "Contrast", "Correlation", "Variance", "IDM", "Energy", "Entropy"]
        
        escritor = csv.DictWriter(archivo_csv, fieldnames=campos)
        print("Hemos creado el CSV")
        escritor.writeheader()

        for archivo in os.listdir(carpetas["input"]):
            if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                img = cv2.imread(os.path.join(carpetas["input"], archivo))
                ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
                cr = mejorar_contraste(ycrcb[:,:,1], alpha=1.03, beta=1.4)
                cr = cv2.GaussianBlur(cr, (5,5), 1.9)
                _, binaria = cv2.threshold(cr, 127, 255, cv2.THRESH_BINARY)
                binaria = eliminar_objetos_pequenos(binaria, 500)
                # Operaciones morfológicas para mejorar la segmentación
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                binaria = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, kernel, iterations=3) #12
                cv2.imwrite(os.path.join(carpetas["binarized"], archivo), binaria)
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img_contornos = procesar_imagen_binarizada(binaria, archivo, img_rgb, escritor, factor_escala)
                # --- Guardar en Segmented/ y Results/ SOLO si está en la lista aleatoria ---
                if archivo in imagenes_a_guardar:
                    mascara = cv2.cvtColor(binaria, cv2.COLOR_GRAY2BGR)
                    segmentada = cv2.bitwise_and(img, mascara)
                    segmentada[mascara == 0] = 255
                    cv2.imwrite(os.path.join(carpetas["segmented"], archivo), segmentada)
                    cv2.imwrite(os.path.join(carpetas["results"], archivo), 
                              cv2.cvtColor(img_contornos, cv2.COLOR_RGB2BGR))
    # Mostrar resultado de muestra 2 segundos y cerrar solo
    if imagenes_a_guardar:
        import matplotlib.pyplot as plt
        img_name = random.choice(imagenes_a_guardar)
        fig, axs = plt.subplots(1, 3, figsize=(18, 6))
        axs[0].imshow(cv2.imread(f'{carpetas["binarized"]}/{img_name}', 0), cmap='gray')
        axs[1].imshow(cv2.cvtColor(cv2.imread(f'{carpetas["segmented"]}/{img_name}'), cv2.COLOR_BGR2RGB))
        axs[2].imshow(cv2.cvtColor(cv2.imread(f'{carpetas["results"]}/{img_name}'), cv2.COLOR_BGR2RGB))
        for ax, title in zip(axs, ['Binarized', 'Segmented', 'Results']):
            ax.set_title(title)
            ax.axis('off')
        plt.suptitle(f"Muestra: {img_name}", fontsize=11)
        plt.tight_layout()
        plt.show(block=False)
        plt.pause(2)
        plt.close('all')
        print(f"Vista previa mostrada: {img_name}")
    else:
        print("Advertencia: no se procesó ninguna imagen. Verifica la carpeta de entrada.")

if __name__ == "__main__":
    main()