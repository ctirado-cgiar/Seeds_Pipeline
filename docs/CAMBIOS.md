# Cambios de esta versión y qué reportar en el manuscrito

## Qué se mide con qué objetos
- **Conteo (15):** cuenta todas las semillas, también las pegadas (watershed).
- **Color de la foto (10.0):** usa todos los objetos segmentados, incluidos pegados y cortados por el borde.
- **Morfometría (08), color por semilla (10.0) y forma (11.x):** solo objetos aislados que pasan los filtros de área, ancho y largo (`AREA_*`, `ANCHO_*`, `LARGO_*`). Los pegados quedan fuera.
- **Forma (11.0):** además se descartan objetos con largo/ancho > `AR_MAX_F` (2.2). Con ese valor se pierde ~40 % de las semillas en genotipos alargados.

## Parámetros a reportar
Quedan guardados en `parametros_usados.json` de cada ensayo: umbral Cr (`THRESHOLD`=127), contraste, desenfoque, filtros de objeto, k de color (2), armónicos EFA, etc.

## Cambios de método
- Perímetro: Douglas-Peucker a 1 px (como FenotIT). Circularidad y columnas derivadas cambian (`P` -4.6 %, `Circ` +9.9 %).
- Color: K-means (k=2) por semilla con anillo de borde, método de FenotIT; ya no se descartan píxeles ≥245.
- Distancia de color: EMD exacta en RGB (antes daba 0 con la misma paleta y proporciones invertidas).

## Arreglos
- El orquestador exportaba solo el primer parámetro de cada paso; ahora exporta todos y los scripts los leen (`common.py`).
- Pasos 10.1, 12, 13 y 14 sin rutas de un ensayo fijo; se encadenan por clave de imagen y libro de campo.
- `plt.show()` ya no bloquea el pipeline (`ORC_SHOW_PLOTS=1` para verlas).

## Notas
- Se respetaron tus cambios locales (nombres de salida, `Image` sin extensión, LAB con skimage, linkage `ward`). `LINKAGE_METHOD` cambia el linkage de los pasos 10.1, 12 y 13.
- `ward` asume distancias euclídeas; con la matriz EMD es una aproximación (`average` es la opción segura).

## Pendiente (no se tocó)
Haralick sobre fondo en cero; descriptores redundantes; `Total_seeds`; área por `contourArea`; README y `requirements.txt`.
