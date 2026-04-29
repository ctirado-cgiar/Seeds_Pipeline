import cv2
import numpy as np
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import os
import pandas as pd
from matplotlib.patches import Rectangle
from dotenv import load_dotenv
load_dotenv()

# === Función para calcular luminosidad ===
def luminosidad(rgb):
    return round(0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2], 2)

# === Procesar cada imagen ===
def process_image(img_path, n_colors, erosion_iterations=3, kernel_size=7):
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Detectar fondo blanco
    lower_white = np.array([245, 245, 245])
    upper_white = np.array([255, 255, 255])
    mask = cv2.inRange(img, lower_white, upper_white)

    # Operaciones morfológicas para limpiar la máscara
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = ~mask.astype(bool)

    # === NUEVA SECCIÓN: Erosión adicional para limpiar bordes ===
    # Convertir la máscara a uint8 para operaciones morfológicas
    mask_uint8 = mask.astype(np.uint8) * 255
    
    # Crear kernel de erosión (más grande = más erosión)
    erosion_kernel = np.ones((kernel_size, kernel_size), np.uint8)
    
    # Aplicar erosión múltiples veces para limpiar bordes
    eroded_mask = cv2.erode(mask_uint8, erosion_kernel, iterations=erosion_iterations)
    
    # Convertir de vuelta a booleano
    mask = eroded_mask.astype(bool)
    # === FIN DE NUEVA SECCIÓN ===

    pixels = img[mask].reshape(-1, 3)
    if len(pixels) == 0:
        return img, img, []

    n_clusters = min(n_colors, len(np.unique(pixels, axis=0)))
    if n_clusters < 1:
        return img, img, []

    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=134)
    kmeans.fit(pixels)

    colors_data = []
    total_pixels = len(pixels)

    for cluster_id in np.unique(kmeans.labels_):
        cluster_mask = (kmeans.labels_ == cluster_id)
        cluster_size = np.sum(cluster_mask)
        cluster_color = kmeans.cluster_centers_[cluster_id].astype(int)

        if not np.all(cluster_color >= [245, 245, 245]):
            pct = round(cluster_size / total_pixels * 100, 1)
            hex_color = '#%02x%02x%02x' % tuple(cluster_color)
            lum = luminosidad(cluster_color)
            colors_data.append((tuple(cluster_color), hex_color, lum, pct))

    if not colors_data:
        return img, img, []

    colors_data.sort(key=lambda x: -x[3])  # Ordenar por porcentaje descendente

    # Crear imagen segmentada
    segmented = np.zeros_like(img) + 255  # Fondo blanco
    mask_flat = mask.reshape(-1)
    segmented_flat = segmented.reshape(-1, 3)
    segmented_flat[mask_flat] = kmeans.cluster_centers_[kmeans.labels_].astype(int)
    segmented = segmented_flat.reshape(img.shape)

    return img, segmented, colors_data

# === Carpetas ===
input_folder = os.getenv('RUTA') + '/SegmentadasCortadas'
output_folder = os.getenv('RUTA') + '/Colorimetria'
os.makedirs(output_folder, exist_ok=True)

# === DataFrame para CSV ===
csv_data = []

# === Procesamiento ===
# Ajusta estos parámetros según necesites:
# - erosion_iterations: número de veces que se aplica la erosión (más = más limpieza)
# - kernel_size: tamaño del kernel de erosión (más grande = erosión más agresiva)
EROSION_ITERATIONS = 3  # Prueba con 2, 3, 4 o 5
KERNEL_SIZE = 7  # Prueba con 5, 7, 9 o 11

for filename in os.listdir(input_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        try:
            img_path = os.path.join(input_folder, filename)
            original, processed, colors_data = process_image(
                img_path, 
                n_colors=2,
                erosion_iterations=EROSION_ITERATIONS,
                kernel_size=KERNEL_SIZE
            )

            if not colors_data:
                print(f"Saltando {filename}, sin colores detectados.")
                continue

            fig, ax = plt.subplots()
            ax.imshow(processed)
            ax.axis('off')

            # === Posición y dimensiones del cuadro ===
            box_x, box_y = 0.70, 0.97
            box_width, box_height = 0.29, 0.08 * (len(colors_data) + 1.5)

            # Fondo del cuadro
            ax.add_patch(plt.Rectangle(
                (box_x, box_y - box_height),
                box_width, box_height,
                transform=ax.transAxes,
                color='white', alpha=0.7, ec='black', lw=0.6
            ))

            # === Título con nombre de la imagen ===
            nombre_imagen = os.path.splitext(filename)[0]
            ax.text(
                box_x + 0.01, box_y - 0.02,
                f"Color Analysis of:\n{nombre_imagen}",
                transform=ax.transAxes,
                fontsize=5, fontweight='bold',
                va='top', ha='left', zorder=3
            )

            # === Datos de colores ===
            for idx, (rgb, hex_c, lum, pct) in enumerate(colors_data):
                y_pos = box_y - 0.12 - idx*0.09
                ax.add_patch(plt.Rectangle(
                    (box_x + 0.01, y_pos - 0.015),
                    0.04, 0.035,
                    transform=ax.transAxes,
                    color=hex_c, ec='white', lw=0.5
                ))
                ax.text(
                    box_x + 0.06, y_pos,
                    f"RGB: {rgb}\nHEX: {hex_c}\nLum: {lum}\n{pct}%",
                    transform=ax.transAxes,
                    fontsize=4, va='center'
                )

            # Guardar imagen
            fig.savefig(os.path.join(output_folder, filename),
                        bbox_inches='tight', dpi=300)
            plt.close(fig)

            # Guardar en CSV
            row = {"Image": filename}
            for i in range(3):
                if i < len(colors_data):
                    rgb, hex_c, lum, pct = colors_data[i]
                    row[f"RGB{i+1}"] = str(rgb)
                    row[f"Hex{i+1}"] = hex_c
                    row[f"Luminosidad{i+1}"] = lum
                    row[f"%{i+1}"] = pct
                else:
                    row[f"RGB{i+1}"] = ""
                    row[f"Hex{i+1}"] = ""
                    row[f"Luminosidad{i+1}"] = ""
                    row[f"%{i+1}"] = ""
            csv_data.append(row)

        except Exception as e:
            print(f"Error procesando {filename}: {str(e)}")

# Guardar CSV
df = pd.DataFrame(csv_data)
df.to_csv(os.path.join(output_folder, "analisis_colores.csv"), index=False)

print("Proceso completado exitosamente.")
print(f"Parámetros usados: Erosión={EROSION_ITERATIONS} iteraciones, Kernel={KERNEL_SIZE}x{KERNEL_SIZE}")
