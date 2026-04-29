import os
import cv2
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from tkinter import simpledialog, Tk
from dotenv import load_dotenv
load_dotenv()

def calcular_factor_escala(ruta_imagen_calibracion):
    """
    Calcula el factor de escala (mm/píxel) a partir de una imagen con una referencia conocida.
    """
    # Cargar imagen de calibración
    imagen = cv2.imread(ruta_imagen_calibracion)
    if imagen is None:
        raise FileNotFoundError(f"No se encontró la imagen en {ruta_imagen_calibracion}")

    # Configuración de la figura
    fig, ax = plt.subplots(figsize=(12, 8))
    plt.subplots_adjust(bottom=0.25)  # espacio para dos botones
    ax.imshow(cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB))
    ax.set_title("Selecciona DOS puntos y haz clic en 'Calcular'")

    puntos = []
    objetos_graficos = []  # almacena puntos, línea y texto

    def onclick(event):
        if event.inaxes != ax:
            return
        if len(puntos) < 2:
            x, y = int(event.xdata), int(event.ydata)
            puntos.append((x, y))
            punto = ax.plot(x, y, 'ro', markersize=5)[0]
            objetos_graficos.append(punto)

            if len(puntos) == 2:
                x_vals = [p[0] for p in puntos]
                y_vals = [p[1] for p in puntos]
                linea = ax.plot(x_vals, y_vals, 'r-')[0]
                objetos_graficos.append(linea)

                distancia_px = np.sqrt((x_vals[1] - x_vals[0])**2 + (y_vals[1] - y_vals[0])**2)
                texto = ax.text(np.mean(x_vals), np.mean(y_vals), f"{distancia_px:.1f} px",
                                color='yellow', ha='center', va='center')
                objetos_graficos.append(texto)

            fig.canvas.draw()

    def calcular(event):
        if len(puntos) != 2:
            print("¡Selecciona exactamente 2 puntos!")
            return
        distancia_px = np.sqrt((puntos[1][0]-puntos[0][0])**2 + (puntos[1][1]-puntos[0][1])**2)
        root = Tk()
        root.withdraw()
        distancia_mm = simpledialog.askfloat("Distancia real",
                                             f"Distancia en píxeles: {distancia_px:.1f}\nIngresa la distancia REAL en mm:",
                                             minvalue=0.01)
        root.destroy()
        if distancia_mm:
            factor = distancia_mm / distancia_px
            guardar_factor_escala(factor)
            plt.close()
            print(f"Factor de escala calculado: {distancia_px/distancia_mm} píxel/mm")
            return factor
        else:
            print("¡Valor inválido!")
            return None

    def borrar(event):
        puntos.clear()
        for obj in objetos_graficos:
            obj.remove()
        objetos_graficos.clear()
        fig.canvas.draw()

    # Botón Calcular
    ax_btn_calcular = plt.axes([0.4, 0.05, 0.2, 0.075])
    btn_calcular = Button(ax_btn_calcular, 'Calcular')
    btn_calcular.on_clicked(calcular)

    # Botón Borrar
    ax_btn_borrar = plt.axes([0.7, 0.05, 0.2, 0.075])
    btn_borrar = Button(ax_btn_borrar, 'Borrar')
    btn_borrar.on_clicked(borrar)

    fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()

def guardar_factor_escala(factor, ruta_guardado=os.getenv('RUTA') + '/calibracionCamara/factorEscala/factor_escala.json'):    
    """Guarda el factor de escala en un archivo JSON."""
    os.makedirs(os.path.dirname(ruta_guardado), exist_ok=True)
    with open(ruta_guardado, 'w') as f:
        json.dump({"factor_escala": factor}, f)
    print(f"Factor de escala guardado: {factor:.6f} mm/píxel en {ruta_guardado}")

def cargar_factor_escala(ruta=os.getenv('RUTA') + '/calibracionCamara/factorEscala/factor_escala.json'):
    """Carga el factor de escala desde el archivo JSON."""
    try:
        with open(ruta, 'r') as f:
            data = json.load(f)
            return data["factor_escala"]
    except FileNotFoundError:
        print("¡Archivo de calibración no encontrado! Usando 1.0 (píxeles).")
        return 1.0

# --- Ejecución principal ---
if __name__ == "__main__":
    # Ruta de la imagen de calibración (debe tener una regla o objeto de referencia)
    #ruta_imagen_calibracion = "D:/OneDrive - CGIAR/Frijol/Procesamiento/Seeds_Pipeline/Mexico_Diversity/Calibracion/colorCard/calibresult.jpg"
    ruta_imagen_calibracion = os.getenv('RUTA') + '/calibracionCamara/ajedrez/1.jpg'
    # Calcular y guardar el factor
    factor = calcular_factor_escala(ruta_imagen_calibracion)
    if factor is not None:
        guardar_factor_escala(factor)
