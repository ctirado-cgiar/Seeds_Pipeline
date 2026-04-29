import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def visualizar_espacios_color(ruta_imagen):
    """
    Visualiza una imagen en diferentes espacios de color y sus canales.
    Cada fila representa un espacio de color con sus 3 canales.
    
    Args:
        ruta_imagen: Ruta al archivo de imagen
    """
    # Verificar que la imagen existe
    if not Path(ruta_imagen).exists():
        raise FileNotFoundError(f"No se encontró la imagen: {ruta_imagen}")
    
    # Leer imagen
    img = cv2.imread(ruta_imagen)
    if img is None:
        raise ValueError(f"No se pudo leer la imagen: {ruta_imagen}")
    
    # Convertir BGR a RGB para visualización correcta
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Definir espacios de color y sus conversiones
    espacios_color = [
        ('RGB', img_rgb, ['Canal R', 'Canal G', 'Canal B']),
        ('HSV', cv2.cvtColor(img, cv2.COLOR_BGR2HSV), ['Canal H', 'Canal S', 'Canal V']),
        ('HLS', cv2.cvtColor(img, cv2.COLOR_BGR2HLS), ['Canal H', 'Canal L', 'Canal S']),
        ('LAB', cv2.cvtColor(img, cv2.COLOR_BGR2LAB), ['Canal L', 'Canal A', 'Canal B']),
        ('LUV', cv2.cvtColor(img, cv2.COLOR_BGR2LUV), ['Canal L', 'Canal U', 'Canal V']),
        ('YUV', cv2.cvtColor(img, cv2.COLOR_BGR2YUV), ['Canal Y', 'Canal U', 'Canal V']),
        ('YCrCb', cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb), ['Canal Y', 'Canal Cr', 'Canal Cb']),
        ('XYZ', cv2.cvtColor(img, cv2.COLOR_BGR2XYZ), ['Canal X', 'Canal Y', 'Canal Z']),
    ]
    
    # Crear figura: 8 filas (espacios) x 4 columnas (original + 3 canales)
    fig, axes = plt.subplots(8, 4, figsize=(16, 24))
    fig.suptitle('Análisis de Espacios de Color y Canales', 
                 fontsize=18, fontweight='bold', y=0.995)
    
    # Ajustar espaciado entre subplots
    plt.subplots_adjust(left=0.05, right=0.95, top=0.99, bottom=0.02, 
                        hspace=0.15, wspace=0.1)
    
    print(f"\n{'='*80}")
    print(f"ANÁLISIS DE CONTRASTE POR ESPACIO DE COLOR")
    print(f"{'='*80}\n")
    
    # Procesar cada espacio de color (cada fila)
    for i, (nombre_espacio, img_convertida, nombres_canales) in enumerate(espacios_color):
        
        # Columna 0: Imagen original en el espacio de color
        ax = axes[i, 0]
        if nombre_espacio == 'RGB':
            ax.imshow(img_convertida)
        else:
            ax.imshow(img_convertida, cmap='gray')
        ax.set_title(f'{nombre_espacio}', fontsize=11, fontweight='bold', pad=5)
        ax.axis('off')
        
        # Imprimir estadísticas
        print(f"{nombre_espacio:8s} |", end=" ")
        
        # Columnas 1-3: Canales individuales
        for j in range(3):
            ax = axes[i, j + 1]
            canal = img_convertida[:, :, j]
            
            # Mostrar canal
            ax.imshow(canal, cmap='gray', vmin=0, vmax=255)
            ax.set_title(nombres_canales[j], fontsize=10, pad=5)
            ax.axis('off')
            
            # Calcular estadísticas
            std = np.std(canal)
            rango = np.ptp(canal)
            media = np.mean(canal)
            
            # Imprimir estadísticas
            letra_canal = nombres_canales[j].split()[-1]
            print(f"{letra_canal}(STD:{std:6.2f} Rng:{rango:3d})", end=" | ")
        
        print()
    
    print(f"\n{'='*80}")
    print("STD = Desviación Estándar (mayor valor = mayor contraste)")
    print("Rng = Rango (máx-mín, mayor valor = mayor separación)")
    print(f"{'='*80}\n")
    
    # Guardar figura
    nombre_salida = Path(ruta_imagen).stem + '_analisis_color.png'
    plt.savefig(nombre_salida, dpi=300, bbox_inches='tight')
    print(f"✓ Figura guardada como: {nombre_salida}")
    
    plt.show()


def comparar_mejor_contraste(ruta_imagen):
    """
    Identifica y visualiza los 6 canales con mejor contraste.
    
    Args:
        ruta_imagen: Ruta al archivo de imagen
    """
    # Leer imagen
    img = cv2.imread(ruta_imagen)
    if img is None:
        raise ValueError(f"No se pudo leer la imagen: {ruta_imagen}")
    
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Definir espacios de color
    espacios = [
        ('RGB', img_rgb, ['R', 'G', 'B']),
        ('HSV', cv2.cvtColor(img, cv2.COLOR_BGR2HSV), ['H', 'S', 'V']),
        ('HLS', cv2.cvtColor(img, cv2.COLOR_BGR2HLS), ['H', 'L', 'S']),
        ('LAB', cv2.cvtColor(img, cv2.COLOR_BGR2LAB), ['L', 'A', 'B']),
        ('LUV', cv2.cvtColor(img, cv2.COLOR_BGR2LUV), ['L', 'U', 'V']),
        ('YUV', cv2.cvtColor(img, cv2.COLOR_BGR2YUV), ['Y', 'U', 'V']),
        ('YCrCb', cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb), ['Y', 'Cr', 'Cb']),
        ('XYZ', cv2.cvtColor(img, cv2.COLOR_BGR2XYZ), ['X', 'Y', 'Z']),
    ]
    
    # Calcular contraste para cada canal
    canales_info = []
    for nombre_espacio, img_conv, nombres_canales in espacios:
        for canal_idx, nombre_canal in enumerate(nombres_canales):
            canal = img_conv[:, :, canal_idx]
            std = np.std(canal)
            rango = np.ptp(canal)
            score = std * 0.7 + rango * 0.3  # Score combinado
            
            canales_info.append({
                'espacio': nombre_espacio,
                'canal': nombre_canal,
                'imagen': canal,
                'std': std,
                'rango': rango,
                'score': score,
                'nombre': f'{nombre_espacio}-{nombre_canal}'
            })
    
    # Ordenar por score y tomar los mejores 6
    canales_info.sort(key=lambda x: x['score'], reverse=True)
    mejores = canales_info[:6]
    
    # Crear figura 2x3
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Top 6 Canales con Mejor Contraste', 
                 fontsize=16, fontweight='bold')
    
    plt.subplots_adjust(hspace=0.3, wspace=0.2)
    
    print(f"\n{'='*70}")
    print("TOP 6 CANALES CON MEJOR CONTRASTE")
    print(f"{'='*70}")
    print(f"{'Rank':<6} {'Canal':<15} {'STD':<10} {'Rango':<10} {'Score':<10}")
    print(f"{'-'*70}")
    
    for idx, info in enumerate(mejores):
        fila = idx // 3
        col = idx % 3
        ax = axes[fila, col]
        
        ax.imshow(info['imagen'], cmap='gray')
        ax.set_title(f"#{idx+1}: {info['nombre']}\nSTD:{info['std']:.1f} Rango:{info['rango']}", 
                    fontsize=10, fontweight='bold')
        ax.axis('off')
        
        print(f"{idx+1:<6} {info['nombre']:<15} {info['std']:<10.2f} "
              f"{info['rango']:<10.0f} {info['score']:<10.2f}")
    
    print(f"{'='*70}\n")
    
    # Guardar figura
    nombre_salida = Path(ruta_imagen).stem + '_mejores_canales.png'
    plt.savefig(nombre_salida, dpi=300, bbox_inches='tight')
    print(f"✓ Figura guardada como: {nombre_salida}")
    
    plt.show()


# Ejemplo de uso
if __name__ == "__main__":
    # Cambiar por tu ruta de imagen
    RUTA_IMAGEN = r"D:/OneDrive - CGIAR/Frijol/Procesamiento/Seeds_Pipeline/Trials/Lineas_Objetivo/areaInteres/CAL 96.jpg"
    
    print("="*80)
    print("ANÁLISIS DE ESPACIOS DE COLOR PARA SEGMENTACIÓN")
    print("="*80)
    print(f"Imagen: {RUTA_IMAGEN}\n")
    
    try:
        # Visualización completa por filas
        print("Generando análisis completo de espacios de color...\n")
        visualizar_espacios_color(RUTA_IMAGEN)
        
        # Comparativa de mejores canales
        print("\nGenerando ranking de mejores canales para contraste...\n")
        comparar_mejor_contraste(RUTA_IMAGEN)
        
        print("\n" + "="*80)
        print("✓ ANÁLISIS COMPLETADO EXITOSAMENTE")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
