"""
Seeds Pipeline Orchestrator v2
Alliance Bioversity International and CIAT

Flujo:
  1. Pantalla de configuración inicial (SetupWizard):
     - Selección de RUTA del ensayo
     - Parámetros clave del pipeline
     - Pasos a activar/desactivar
     - Factor de escala  (usuario marca 2 puntos en imagen, se guarda factor_escala.json)
     - Recorte de área de interés (opcional, usuario arrastra rectángulo)
     - Máscara de exclusión (opcional, usuario arrastra rectángulo)
  2. OrchestratorApp corre el pipeline solo, sin más intervención humana.

Requisitos: Python 3.11.9+, tkinter, opencv-python, numpy, python-dotenv
Uso: python 00_orquestador_pipeline.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess, threading, os, sys, json, glob
from pathlib import Path
import numpy as np
import cv2
from dotenv import load_dotenv

# ── Paleta ────────────────────────────────────────────────────────────────────
C_BG    = "#1e1e2e"; C_PANEL = "#2a2a3e"; C_BORDER = "#44445a"
C_ACC   = "#7c9ef8"; C_OK    = "#52c77e"; C_WARN   = "#f0a050"
C_ERR   = "#f07070"; C_TEXT  = "#cdd6f4"; C_DIM    = "#6e7190"
C_YEL   = "#f9e04b"

S_ICON  = {"pendiente":"○","ejecutando":"▶","completado":"✓",
           "omitido":"—","error":"✗","esperando":"⏸"}
S_CLR   = {"pendiente":C_DIM,"ejecutando":C_YEL,"completado":C_OK,
           "omitido":C_DIM,"error":C_ERR,"esperando":C_WARN}

# ── Pasos ─────────────────────────────────────────────────────────────────────
STEPS = [
    {"id":"01","name":"Obtener Parámetros de Calibración",
     "script":"01_ObtenerParametros_Ajedrez.py","enabled":True,
     "params":{"GUARDAR_CHESSBOARD_CORNERS":{"label":"Guardar imágenes de esquinas","type":"bool","default":True}}},
    {"id":"02","name":"Corrección de Distorsión",
     "script":"02_DistorcionCorrection_Ajedrez.py","enabled":True,"params":{}},
    {"id":"03","name":"Obtener Máscara de Tarjeta de Color",
     "script":"03_ObtenerMascara_ColorCard.py","enabled":True,
     "params":{"RADIUS":{"label":"Radio de detección de parches","type":"int","default":6},
               "POS":{"label":"Orientación tarjeta (1,2,3)","type":"int","default":3}}},
    {"id":"04","name":"Corrección de Color por Máscara",
     "script":"04_ColorCorrection_ByMask copy.py","enabled":True,"params":{}},
    {"id":"05","name":"Calibración de Escala",
     "script":"05_ConocerEscalas.py","enabled":True,"params":{}},
    {"id":"06","name":"Recorte de Área de Interés",
     "script":"06_CutImagesApp.py","enabled":False,"params":{}},
    {"id":"07","name":"Aplicar Máscara de Exclusión",
     "script":"07_ApplyMaskApp.py","enabled":False,"params":{}},
    {"id":"08","name":"Análisis de Morfologías",
     "script":"08_analisisMorfometria.py","enabled":True,
     "params":{"THRESHOLD":{"label":"Umbral binarización Cr","type":"int","default":127},
               "AREA_MIN":{"label":"Área mínima (px²)","type":"int","default":200},
               "AREA_MAX":{"label":"Área máxima (px²)","type":"int","default":12000},
               "ANCHO_MIN":{"label":"Ancho mínimo (px)","type":"int","default":5},
               "ANCHO_MAX":{"label":"Ancho máximo (px)","type":"int","default":105},
               "LARGO_MIN":{"label":"Largo mínimo (px)","type":"int","default":10},
               "LARGO_MAX":{"label":"Largo máximo (px)","type":"int","default":190}}},
    {"id":"09","name":"Resumen de Morfometría",
     "script":"09_summarizeMorfometria.py","enabled":True,"params":{}},
    {"id":"10_0","name":"Extracción de Color por K-means",
     "script":"10.0_extraerColor_Kmeans.py","enabled":True,
     "params":{"N_COLORS":{"label":"Colores dominantes K","type":"int","default":2},
               "EROSION_ITERATIONS":{"label":"Iteraciones erosión","type":"int","default":3},
               "KERNEL_SIZE":{"label":"Kernel erosión (px)","type":"int","default":7}}},
    {"id":"10_1","name":"Distancias de Color (EMD)",
     "script":"10.1_colorDistance.py","enabled":True,"params":{}},
    {"id":"11_0","name":"Filtrar Binarizadas",
     "script":"11.0_filtrarBinarizadas.py","enabled":True,
     "params":{"AREA_MIN_F":{"label":"Área mínima (px²)","type":"int","default":200},
               "AREA_MAX_F":{"label":"Área máxima (px²)","type":"int","default":10000},
               "ANCHO_MIN_F":{"label":"Ancho mínimo (px)","type":"int","default":5},
               "ANCHO_MAX_F":{"label":"Ancho máximo (px)","type":"int","default":105},
               "LARGO_MIN_F":{"label":"Largo mínimo (px)","type":"int","default":10},
               "LARGO_MAX_F":{"label":"Largo máximo (px)","type":"int","default":190}}},
    {"id":"11_1","name":"Alinear Formas",
     "script":"11.1_alinearFormas.py","enabled":True,
     "params":{"GRID_COLS":{"label":"Columnas rejilla","type":"int","default":8}}},
    {"id":"11_2","name":"Forma Promedio EFA",
     "script":"11.2_formaPromedio.py","enabled":True,
     "params":{"N_HARMONICS":{"label":"Armónicos EFA","type":"int","default":20},
               "N_POINTS":{"label":"Puntos por contorno","type":"int","default":128},
               "MIN_SOLIDITY":{"label":"Solidez mínima","type":"float","default":0.90},
               "MIN_CIRCULARITY":{"label":"Circularidad mínima","type":"float","default":0.55}}},
    {"id":"12","name":"Distancias de Forma",
     "script":"12_formasDistance.py","enabled":True,
     "params":{"USE_EFA":{"label":"Incluir EFA en distancias","type":"bool","default":True}}},
    {"id":"13","name":"Exportar Dendrogramas a JSON",
     "script":"13_linkage2json.py","enabled":True,
     "params":{"LINKAGE_METHOD":{"label":"Método linkage","type":"str","default":"average"}}},
    {"id":"14","name":"Clusterización Integrada",
     "script":"14_clusterFormasFormayMorfometríaIntegrada.py","enabled":True,
     "params":{"MAX_CLUSTERS":{"label":"Máx. clusters","type":"int","default":6},
               "N_COMPONENTS":{"label":"Máx. componentes PCA","type":"int","default":10}}},
    {"id":"15","name":"Contador de Semillas",
     "script":"15_contadorSemillas.py","enabled":True,
     "params":{"THRESHOLD_VAL":{"label":"Umbral conteo Cr","type":"int","default":125},
               "MIN_DISTANCE":{"label":"Dist. mínima semillas (px)","type":"int","default":10},
               "PEAK_THRESHOLD":{"label":"Fracción umbral Watershed","type":"float","default":0.20}}},
    {"id":"16","name":"Unir Datos con Libro de Campo",
     "script":"16_unirDatosconLibroCampo.py","enabled":True,"params":{}},
]
INTERACTIVE_IDS = {"05","06","07"}

# ── Helpers OpenCV ────────────────────────────────────────────────────────────

def _load_scaled(path, max_dim=900):
    img = cv2.imread(path)
    if img is None:
        return None, 1.0
    h, w = img.shape[:2]
    scale = min(max_dim/w, max_dim/h, 1.0)
    if scale < 1.0:
        img = cv2.resize(img, (int(w*scale), int(h*scale)))
    return img, scale


def pick_two_points(image_path, title):
    """Abre ventana OpenCV. Usuario hace clic en 2 puntos. Retorna lista [(x,y),(x,y)] en coords originales o None."""
    img, scale = _load_scaled(image_path)
    if img is None:
        return None
    points_disp = []
    canvas = [img.copy()]

    def cb(ev, x, y, *_):
        if ev == cv2.EVENT_LBUTTONDOWN and len(points_disp) < 2:
            points_disp.append((x, y))
            cv2.circle(canvas[0], (x, y), 7, (0, 255, 100), -1)
            cv2.circle(canvas[0], (x, y), 9, (255, 255, 255), 2)
            if len(points_disp) == 2:
                cv2.line(canvas[0], points_disp[0], points_disp[1], (0,200,255), 2)
            cv2.imshow(title, canvas[0])

    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(title, cb)
    cv2.imshow(title, canvas[0])
    while True:
        n = len(points_disp)
        cv2.setWindowTitle(title,
            f"{title}  |  Puntos: {n}/2  |  ENTER=confirmar  ESC=cancelar  R=reiniciar")
        k = cv2.waitKey(20) & 0xFF
        if k == 13 and n == 2:
            cv2.destroyWindow(title)
            return [(int(p[0]/scale), int(p[1]/scale)) for p in points_disp]
        elif k == ord('r'):
            points_disp.clear(); canvas[0] = img.copy(); cv2.imshow(title, canvas[0])
        elif k == 27 or cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
            cv2.destroyWindow(title); return None


def pick_rectangle(image_path, title):
    """Abre ventana OpenCV. Usuario arrastra para seleccionar rectángulo. Retorna (x1,y1,x2,y2) en coords originales o None."""
    img, scale = _load_scaled(image_path)
    if img is None:
        return None
    state = {"start":None,"end":None,"drag":False}
    canvas = [img.copy()]

    def cb(ev, x, y, *_):
        if ev == cv2.EVENT_LBUTTONDOWN:
            state.update(start=(x,y), drag=True)
        elif ev == cv2.EVENT_MOUSEMOVE and state["drag"]:
            canvas[0] = img.copy()
            cv2.rectangle(canvas[0], state["start"], (x,y), (0,200,255), 2)
            cv2.imshow(title, canvas[0])
        elif ev == cv2.EVENT_LBUTTONUP:
            state.update(end=(x,y), drag=False)
            canvas[0] = img.copy()
            cv2.rectangle(canvas[0], state["start"], state["end"], (0,255,100), 2)
            cv2.imshow(title, canvas[0])

    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(title, cb)
    cv2.imshow(title, img)
    while True:
        cv2.setWindowTitle(title, f"{title}  |  Arrastre  |  ENTER=confirmar  R=reiniciar  ESC=cancelar")
        k = cv2.waitKey(20) & 0xFF
        if k == 13 and state["start"] and state["end"]:
            cv2.destroyWindow(title)
            s, e = state["start"], state["end"]
            return (int(min(s[0],e[0])/scale), int(min(s[1],e[1])/scale),
                    int(max(s[0],e[0])/scale), int(max(s[1],e[1])/scale))
        elif k == ord('r'):
            state.update(start=None,end=None); canvas[0]=img.copy(); cv2.imshow(title,canvas[0])
        elif k == 27 or cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
            cv2.destroyWindow(title); return None


def crop_folder(src, dst, rect):
    x1,y1,x2,y2 = rect
    os.makedirs(dst, exist_ok=True)
    files = [f for e in ("*.jpg","*.JPG","*.jpeg","*.JPEG","*.png","*.PNG")
             for f in glob.glob(os.path.join(src, e))]
    for f in files:
        img = cv2.imread(f)
        if img is not None:
            cv2.imwrite(os.path.join(dst, os.path.basename(f)), img[y1:y2, x1:x2])
    return len(files)


def mask_folder(folder, rect, color=(0,0,0)):
    x1,y1,x2,y2 = rect
    files = [f for e in ("*.jpg","*.JPG","*.jpeg","*.JPEG","*.png","*.PNG")
             for f in glob.glob(os.path.join(folder, e))]
    for f in files:
        img = cv2.imread(f)
        if img is not None:
            img[y1:y2, x1:x2] = color
            cv2.imwrite(f, img)
    return len(files)


def first_image(folder, exclude_zero=False):
    """Retorna la primera imagen del folder ordenada alfabéticamente.
    Si exclude_zero=True, omite archivos cuyo nombre sea '0.*' (reservado para tarjeta de color)."""
    for ext in ("*.jpg","*.JPG","*.jpeg","*.JPEG","*.png","*.PNG"):
        for m in sorted(glob.glob(os.path.join(folder, ext))):
            if exclude_zero and Path(m).stem == "0":
                continue
            return m
    return None

# ── Widgets comunes ───────────────────────────────────────────────────────────

def label(parent, text, fg=None, font=None, **kw):
    return tk.Label(parent, text=text, bg=C_PANEL if kw.get("in_panel") else C_BG,
                    fg=fg or C_TEXT, font=font or ("Segoe UI", 9), **{k:v for k,v in kw.items() if k!="in_panel"})

# ── Setup Wizard ──────────────────────────────────────────────────────────────

class SetupWizard(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Seeds Pipeline — Configuración inicial")
        self.configure(bg=C_BG)
        self.geometry("760x720"); self.minsize(680,580)

        self.ruta_var       = tk.StringVar()
        self.use_aoi        = tk.BooleanVar(value=False)
        self.use_mask       = tk.BooleanVar(value=False)
        self.scale_done     = False
        self.scale_factor   = None
        self.aoi_rect       = None
        self.mask_rect      = None
        self.param_values   = {}
        self.step_enabled   = {s["id"]: tk.BooleanVar(value=s["enabled"]) for s in STEPS}
        self._param_vars    = {}

        for step in STEPS:
            for k, meta in step["params"].items():
                key = meta.get("key", k)
                self.param_values[key] = meta["default"]

        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            self.ruta_var.set(os.getenv("RUTA",""))

        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        hdr = tk.Frame(self, bg=C_PANEL, height=50); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙  Seeds Pipeline — Configuración inicial", bg=C_PANEL,
                 fg=C_TEXT, font=("Segoe UI",12,"bold")).pack(side="left", padx=20)
        tk.Label(hdr, text="Alliance Bioversity International and CIAT", bg=C_PANEL,
                 fg=C_DIM, font=("Segoe UI",8)).pack(side="right", padx=20)

        outer = tk.Frame(self, bg=C_BG); outer.pack(fill="both", expand=True)
        cv = tk.Canvas(outer, bg=C_BG, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=cv.yview)
        self.body = tk.Frame(cv, bg=C_BG)
        self.body.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0,0), window=self.body, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        cv.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(int(-1*(e.delta/120)),"units"))

        self._sec("1.  Carpeta del ensayo")
        self._ruta_block()

        self._sec("2.  Parámetros clave")
        self._params_block()

        self._sec("3.  Pasos a ejecutar")
        self._steps_block()

        self._sec("4.  Factor de escala   ·  requerido")
        self._scale_block()

        self._sec("5.  Área de interés y máscara")
        self._aoi_mask_options()

        # Footer
        foot = tk.Frame(self, bg=C_PANEL, height=56); foot.pack(fill="x", side="bottom"); foot.pack_propagate(False)
        tk.Label(foot, text="Complete lo requerido y presione Iniciar para lanzar el pipeline automáticamente.",
                 bg=C_PANEL, fg=C_DIM, font=("Segoe UI",8)).pack(side="left", padx=18)
        tk.Button(foot, text="▶  Iniciar Pipeline", bg=C_ACC, fg=C_BG,
                  font=("Segoe UI",10,"bold"), relief="flat", padx=20, pady=8,
                  cursor="hand2", command=self._launch).pack(side="right", padx=16, pady=10)

    def _sec(self, title):
        tk.Frame(self.body, bg=C_BORDER, height=1).pack(fill="x", padx=20, pady=(14,0))
        tk.Label(self.body, text=title, bg=C_BG, fg=C_ACC,
                 font=("Segoe UI",9,"bold")).pack(anchor="w", padx=22, pady=(4,2))

    def _card(self):
        f = tk.Frame(self.body, bg=C_PANEL, highlightbackground=C_BORDER, highlightthickness=1)
        f.pack(fill="x", padx=20, pady=3)
        return f

    def _ruta_block(self):
        c = self._card()
        r = tk.Frame(c, bg=C_PANEL); r.pack(fill="x", padx=14, pady=10)
        e = tk.Entry(r, textvariable=self.ruta_var, bg=C_BG, fg=C_TEXT,
                     insertbackground=C_TEXT, relief="flat", font=("Consolas",9),
                     highlightbackground=C_BORDER, highlightthickness=1)
        e.pack(side="left", fill="x", expand=True, ipady=5)
        tk.Button(r, text="Examinar…", bg=C_BG, fg=C_TEXT, relief="flat",
                  font=("Segoe UI",9), padx=10, pady=4, cursor="hand2",
                  command=lambda: self.ruta_var.set(
                      filedialog.askdirectory(title="Carpeta del ensayo") or self.ruta_var.get()),
                  highlightbackground=C_BORDER, highlightthickness=1).pack(side="left", padx=(8,0))

    def _params_block(self):
        KEY_PARAMS = [
            ("THRESHOLD",    "Umbral binarización (Cr)"),
            ("AREA_MIN",     "Área mínima objeto (px²)"),
            ("AREA_MAX",     "Área máxima objeto (px²)"),
            ("N_COLORS",     "Colores dominantes K-means"),
            ("N_HARMONICS",  "Armónicos EFA"),
            ("MIN_SOLIDITY", "Solidez mínima (0–1)"),
            ("MAX_CLUSTERS", "Máx. clusters análisis integrado"),
            ("THRESHOLD_VAL","Umbral conteo semillas (Cr)"),
        ]
        c = self._card()
        g = tk.Frame(c, bg=C_PANEL); g.pack(fill="x", padx=14, pady=10)
        for i, (key, lbl) in enumerate(KEY_PARAMS):
            col = (i % 2) * 3; row = i // 2
            tk.Label(g, text=lbl, bg=C_PANEL, fg=C_TEXT,
                     font=("Segoe UI",8), anchor="w").grid(row=row, column=col, sticky="w", pady=3, padx=(0,6))
            v = tk.StringVar(value=str(self.param_values.get(key,"")))
            e = tk.Entry(g, textvariable=v, bg=C_BG, fg=C_TEXT,
                         insertbackground=C_TEXT, relief="flat", font=("Consolas",9), width=10,
                         highlightbackground=C_BORDER, highlightthickness=1)
            e.grid(row=row, column=col+1, sticky="w", pady=3, padx=(0,20))
            self._param_vars[key] = v
        g.columnconfigure(1, weight=1); g.columnconfigure(4, weight=1)

    def _steps_block(self):
        c = self._card()
        g = tk.Frame(c, bg=C_PANEL); g.pack(fill="x", padx=14, pady=8)
        non_inter = [s for s in STEPS if s["id"] not in INTERACTIVE_IDS]
        for i, step in enumerate(non_inter):
            col = (i%3)*2; row = i//3
            tk.Checkbutton(g, variable=self.step_enabled[step["id"]],
                           text=f"{step['id']}  {step['name'][:30]}",
                           bg=C_PANEL, fg=C_TEXT, selectcolor=C_BG,
                           activebackground=C_PANEL, font=("Segoe UI",8)
                           ).grid(row=row, column=col, sticky="w", pady=1, padx=(0,14))

    def _scale_block(self):
        c = self._card()
        inner = tk.Frame(c, bg=C_PANEL); inner.pack(fill="x", padx=14, pady=10)
        tk.Label(inner, text="Marque dos puntos sobre un objeto de referencia conocida e ingrese su distancia real en mm.",
                 bg=C_PANEL, fg=C_DIM, font=("Segoe UI",8), wraplength=560, justify="left").pack(anchor="w")
        row = tk.Frame(inner, bg=C_PANEL); row.pack(fill="x", pady=(8,0))
        self.scale_btn = tk.Button(row, text="🔎  Abrir imagen y marcar puntos",
                                   bg=C_ACC, fg=C_BG, relief="flat",
                                   font=("Segoe UI",9,"bold"), padx=12, pady=5,
                                   cursor="hand2", command=self._do_scale)
        self.scale_btn.pack(side="left")
        self.scale_lbl = tk.Label(row, text="⚠  Pendiente", bg=C_PANEL, fg=C_WARN, font=("Segoe UI",9))
        self.scale_lbl.pack(side="left", padx=14)

    def _aoi_mask_options(self):
        """Checkboxes simples. La selección visual ocurre después de correr 01-04."""
        c = self._card()
        inner = tk.Frame(c, bg=C_PANEL); inner.pack(fill="x", padx=14, pady=12)
        tk.Label(inner,
                 text="El pipeline pausará tras los scripts 01–04 y mostrará una imagen ya corregida para que defina estas opciones.",
                 bg=C_PANEL, fg=C_DIM, font=("Segoe UI",8), justify="left").pack(anchor="w")
        row = tk.Frame(inner, bg=C_PANEL); row.pack(fill="x", pady=(8,0))
        tk.Checkbutton(row, variable=self.use_aoi,
                       text="Activar recorte de área de interés  (se definirá sobre imagen corregida)",
                       bg=C_PANEL, fg=C_TEXT, selectcolor=C_BG,
                       activebackground=C_PANEL, font=("Segoe UI",9)).pack(anchor="w", pady=2)
        tk.Checkbutton(row, variable=self.use_mask,
                       text="Activar máscara de exclusión  (se definirá sobre imagen corregida)",
                       bg=C_PANEL, fg=C_TEXT, selectcolor=C_BG,
                       activebackground=C_PANEL, font=("Segoe UI",9)).pack(anchor="w", pady=2)

    def _ref_image(self, *subfolders, exclude_zero=False):
        ruta = self.ruta_var.get().strip()
        for sf in subfolders:
            img = first_image(os.path.join(ruta, sf), exclude_zero=exclude_zero)
            if img: return img
        return None

    def _do_scale(self):
        ruta = self.ruta_var.get().strip()
        if not ruta or not os.path.isdir(ruta):
            messagebox.showerror("Error","Configure la carpeta del ensayo primero."); return

        img_path = self._ref_image("calibracionCamara/factorEscala","calibracionCamara/ajedrez", exclude_zero=True)
        if not img_path:
            messagebox.showerror("Sin imagen",
                "No se encontró ninguna imagen en calibracionCamara/factorEscala/ ni en calibracionCamara/ajedrez/."); return

        self.scale_lbl.configure(text="Abriendo imagen…", fg=C_YEL); self.update()
        pts = pick_two_points(img_path, "Factor de escala — marque 2 puntos sobre el objeto de referencia")
        if not pts:
            self.scale_lbl.configure(text="⚠  Cancelado", fg=C_WARN); return

        # Pedir distancia real con ventana pequeña
        dlg = tk.Toplevel(self); dlg.title("Distancia real"); dlg.configure(bg=C_BG)
        dlg.grab_set(); dlg.resizable(False,False)
        dx,dy = pts[1][0]-pts[0][0], pts[1][1]-pts[0][1]
        px = (dx**2+dy**2)**0.5
        tk.Label(dlg, text=f"Distancia seleccionada: {px:.1f} px",
                 bg=C_BG, fg=C_DIM, font=("Consolas",9)).pack(padx=20, pady=(16,4))
        tk.Label(dlg, text="Distancia real en milímetros:",
                 bg=C_BG, fg=C_TEXT, font=("Segoe UI",9)).pack(padx=20)
        mm_var = tk.StringVar()
        e = tk.Entry(dlg, textvariable=mm_var, bg=C_PANEL, fg=C_TEXT,
                     insertbackground=C_TEXT, relief="flat", font=("Consolas",11),
                     width=12, highlightbackground=C_BORDER, highlightthickness=1)
        e.pack(padx=20, pady=8, ipady=6); e.focus()
        result = [None]
        def ok():
            try:
                v = float(mm_var.get().replace(",","."))
                if v <= 0: raise ValueError
                result[0] = v; dlg.destroy()
            except: messagebox.showerror("Error","Ingrese un número positivo.", parent=dlg)
        tk.Button(dlg, text="Confirmar", bg=C_ACC, fg=C_BG,
                  font=("Segoe UI",9,"bold"), relief="flat", padx=16, pady=6,
                  cursor="hand2", command=ok).pack(pady=(0,16))
        dlg.bind("<Return>", lambda _: ok())
        self.wait_window(dlg)
        if result[0] is None:
            self.scale_lbl.configure(text="⚠  Cancelado", fg=C_WARN); return

        factor = result[0] / px if px > 0 else None
        if factor is None:
            messagebox.showerror("Error","Los puntos seleccionados son idénticos."); return

        self.scale_factor = factor; self.scale_done = True
        fdir = os.path.join(ruta, "calibracionCamara","factorEscala")
        os.makedirs(fdir, exist_ok=True)
        with open(os.path.join(fdir,"factor_escala.json"),"w") as f:
            json.dump({"factor_escala": factor}, f)
        self.scale_lbl.configure(
            text=f"✓  {factor:.6f} mm/px  ({result[0]:.1f} mm / {px:.1f} px)", fg=C_OK)

    def _launch(self):
        ruta = self.ruta_var.get().strip()
        if not ruta or not os.path.isdir(ruta):
            messagebox.showerror("Error","La carpeta del ensayo no existe o no está configurada."); return

        if not self.scale_done:
            if not messagebox.askyesno("Factor de escala no configurado",
                "No configuró el factor de escala.\nLas mediciones se reportarán en píxeles.\n\n¿Continuar de todas formas?"):
                return

        # Actualizar param_values desde los Entry widgets
        for key, var in self._param_vars.items():
            old = self.param_values.get(key)
            try:
                if isinstance(old, bool):   self.param_values[key] = var.get().lower() in ("true","1")
                elif isinstance(old, int):  self.param_values[key] = int(var.get())
                elif isinstance(old, float):self.param_values[key] = float(var.get().replace(",","."))
                else:                       self.param_values[key] = var.get()
            except: pass

        # El factor de escala ya se guardó en disco; desactivar script 05
        if self.scale_done:
            self.step_enabled["05"].set(False)

        config = {
            "ruta":         ruta,
            "param_values": self.param_values,
            "step_enabled": {sid: v.get() for sid,v in self.step_enabled.items()},
            "use_aoi":      self.use_aoi.get(),
            "use_mask":     self.use_mask.get(),
        }
        self.destroy()
        OrchestratorApp(config).mainloop()


# ── Orquestador autónomo ──────────────────────────────────────────────────────

class OrchestratorApp(tk.Tk):

    def __init__(self, config):
        super().__init__()
        self.title("Seeds Pipeline — Ejecutando")
        self.configure(bg=C_BG); self.geometry("860x700"); self.minsize(720,560)
        self.ruta         = config["ruta"]
        self.param_values = config["param_values"]
        self.step_enabled = config["step_enabled"]
        self.use_aoi      = config.get("use_aoi",  False)
        self.use_mask     = config.get("use_mask", False)
        self.running = False; self.stop_flag = False
        self._slbls = {}  # step_id → Label widget
        self._build()
        self.after(600, self._auto_start)

    def _build(self):
        hdr = tk.Frame(self, bg=C_PANEL, height=50); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="▶  Seeds Pipeline — En ejecución", bg=C_PANEL,
                 fg=C_TEXT, font=("Segoe UI",12,"bold")).pack(side="left", padx=20)
        tk.Label(hdr, text=self.ruta, bg=C_PANEL, fg=C_DIM, font=("Consolas",8)).pack(side="right", padx=20)

        tk.Label(self, text="Pasos del pipeline", bg=C_BG, fg=C_DIM,
                 font=("Segoe UI",8,"bold")).pack(anchor="w", padx=22, pady=(8,2))
        outer = tk.Frame(self, bg=C_BG); outer.pack(fill="both", expand=True, padx=20)
        cv = tk.Canvas(outer, bg=C_BG, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=cv.yview)
        self.sf = tk.Frame(cv, bg=C_BG)
        self.sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0,0), window=self.sf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        cv.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(int(-1*(e.delta/120)),"units"))
        for step in STEPS:
            self._step_row(step)

        tk.Label(self, text="Registro", bg=C_BG, fg=C_DIM,
                 font=("Segoe UI",8,"bold")).pack(anchor="w", padx=22, pady=(6,2))
        self.log = scrolledtext.ScrolledText(
            self, bg="#12121e", fg=C_TEXT, insertbackground=C_TEXT,
            font=("Consolas",8), relief="flat", height=9,
            highlightbackground=C_BORDER, highlightthickness=1, state="disabled")
        self.log.pack(fill="both", padx=20, pady=(0,4))
        for tag,clr in [("ok",C_OK),("err",C_ERR),("warn",C_WARN),("step",C_ACC),("dim",C_DIM)]:
            self.log.tag_config(tag, foreground=clr)

        foot = tk.Frame(self, bg=C_PANEL, height=54); foot.pack(fill="x",side="bottom"); foot.pack_propagate(False)
        self.prog = ttk.Progressbar(foot, mode="determinate", length=260)
        self.prog.pack(side="left", padx=20, pady=16)
        self.prog_lbl = tk.Label(foot, text="Iniciando…", bg=C_PANEL, fg=C_DIM, font=("Consolas",8))
        self.prog_lbl.pack(side="left")
        self.stop_btn = tk.Button(foot, text="⏹  Detener", bg=C_ERR, fg=C_BG,
                                  font=("Segoe UI",9,"bold"), relief="flat",
                                  padx=14, pady=7, cursor="hand2", command=self._stop)
        self.stop_btn.pack(side="right", padx=16, pady=10)

    def _step_row(self, step):
        enabled = self.step_enabled.get(step["id"], step["enabled"])
        row = tk.Frame(self.sf, bg=C_PANEL, highlightbackground=C_BORDER, highlightthickness=1)
        row.pack(fill="x", pady=2, padx=2)
        tk.Label(row, text=f" {step['id']:>4} ", bg=C_BG, fg=C_DIM,
                 font=("Consolas",8), padx=4).pack(side="left")
        nf = tk.Frame(row, bg=C_PANEL); nf.pack(side="left", fill="x", expand=True)
        tk.Label(nf, text=step["name"], bg=C_PANEL, fg=C_TEXT if enabled else C_DIM,
                 font=("Segoe UI",9,"bold"), anchor="w").pack(anchor="w")
        tk.Label(nf, text=step["script"], bg=C_PANEL, fg=C_DIM,
                 font=("Consolas",8), anchor="w").pack(anchor="w")
        st = "pendiente" if enabled else "omitido"
        iv = tk.StringVar(value=S_ICON[st])
        lbl = tk.Label(row, textvariable=iv, bg=C_PANEL, fg=S_CLR[st],
                       font=("Segoe UI",11), width=2)
        lbl.pack(side="right", padx=10)
        step["_iv"] = iv; step["_lbl"] = lbl

    def _set_st(self, sid, st):
        for s in STEPS:
            if s["id"] == sid:
                s["_iv"].set(S_ICON[st]); s["_lbl"].configure(fg=S_CLR[st]); break

    def _log(self, msg, tag=""):
        self.log.configure(state="normal")
        self.log.insert("end", msg+"\n", tag)
        self.log.see("end"); self.log.configure(state="disabled")

    def _auto_start(self):
        enabled = [s for s in STEPS if self.step_enabled.get(s["id"], s["enabled"])]
        self.prog["maximum"] = max(len(enabled),1)
        self._log(f"RUTA: {self.ruta}", "dim")
        self._log(f"Pasos habilitados: {len(enabled)}", "dim")
        self._log("─"*56, "dim")
        self.running = True
        threading.Thread(target=self._run, args=(enabled,), daemon=True).start()

    def _run(self, enabled):
        total = len(enabled); pipeline_dir = str(Path(__file__).parent)
        for i, step in enumerate(enabled):
            if self.stop_flag:
                self._log("\n⏹  Detenido.", "warn"); break

            # ── Pausa tras paso 04: pedir AOI y/o máscara sobre imagen corregida ──
            if step["id"] == "05" and (self.use_aoi or self.use_mask):
                self._log("\n⏸  Pausa — definir área de interés y/o máscara sobre imagen corregida…", "warn")
                # Bloquear thread hasta que el usuario termine en el diálogo
                done_event = threading.Event()
                self.after(0, lambda ev=done_event: self._interactive_aoi_mask(ev))
                done_event.wait()
                if self.stop_flag:
                    self._log("\n⏹  Detenido.", "warn"); break
                self._log("  ✓  AOI/máscara aplicados. Continuando…", "ok")

            spath = os.path.join(pipeline_dir, step["script"])
            self._log(f"\n[{step['id']}] {step['name']}", "step")
            if not os.path.exists(spath):
                self._log("  ⚠  Script no encontrado — omitido.", "warn")
                self._set_st(step["id"],"omitido")
                self.after(0, lambda v=i+1: self._upd(v,total)); continue
            env = os.environ.copy(); env["RUTA"] = self.ruta
            for meta in step.get("params",{}).values():
                k = meta.get("key", list(step["params"].keys())[0])
                env[f"ORC_{k}"] = str(self.param_values.get(k, meta["default"]))
            self._set_st(step["id"],"ejecutando")
            self.after(0, lambda v=i+1: self._upd(v,total))
            rc = self._exec(spath, env)
            if rc is None: break
            elif rc == 0:
                self._set_st(step["id"],"completado"); self._log("  ✓  Completado.", "ok")
            else:
                self._set_st(step["id"],"error"); self._log(f"  ✗  Error (código {rc}).", "err")
                if not messagebox.askyesno("Error",
                    f"'{step['name']}' finalizó con error.\n¿Continuar con el siguiente paso?"):
                    break
            self.after(0, lambda v=i+1: self._upd(v,total))
        self._finish()

    def _exec(self, path, env):
        try:
            proc = subprocess.Popen([sys.executable, path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                env=env, cwd=str(Path(path).parent))
            for line in proc.stdout:
                if self.stop_flag: proc.terminate(); return None
                self._log("    "+line.rstrip())
            proc.wait(); return proc.returncode
        except Exception as ex:
            self._log(f"  ✗  {ex}", "err"); return 1

    def _upd(self, v, total):
        self.prog["value"] = v
        self.prog_lbl.configure(text=f"{v} / {total} pasos")

    def _stop(self): self.stop_flag = True; self._log("\n⏹  Solicitando detención…","warn")

    def _interactive_aoi_mask(self, done_event):
        """
        Llamado en el hilo principal (after) mientras el pipeline espera.
        Abre una ventana tkinter con botones para AOI y/o máscara
        usando la imagen ya corregida de colorCorrejidas/.
        Cuando el usuario confirma, aplica los cambios y libera done_event.
        """
        ruta = self.ruta

        dlg = tk.Toplevel(self)
        dlg.title("Definir área de interés y máscara — imagen corregida")
        dlg.configure(bg=C_BG)
        dlg.grab_set()
        dlg.resizable(True, True)
        dlg.geometry("620x340")

        tk.Label(dlg,
                 text="Los scripts 01–04 ya se ejecutaron.\nDefina ahora el área de interés y/o máscara sobre la imagen ya corregida.",
                 bg=C_BG, fg=C_TEXT, font=("Segoe UI",9), justify="left").pack(padx=20, pady=(16,10), anchor="w")

        # Estado
        aoi_rect  = [None]
        mask_rect = [None]

        def ref_img():
            img = first_image(os.path.join(ruta,"colorCorrejidas"), exclude_zero=False)
            if not img:
                messagebox.showerror("Sin imagen",
                    "No se encontró ninguna imagen en colorCorrejidas/.\n"
                    "Verifique que los scripts 01–04 se ejecutaron correctamente.", parent=dlg)
            return img

        # ── AOI ──────────────────────────────────────────────────────────────
        if self.use_aoi:
            aoi_card = tk.Frame(dlg, bg=C_PANEL, highlightbackground=C_BORDER, highlightthickness=1)
            aoi_card.pack(fill="x", padx=20, pady=4)
            row = tk.Frame(aoi_card, bg=C_PANEL); row.pack(fill="x", padx=14, pady=8)
            tk.Label(row, text="Recorte de área de interés", bg=C_PANEL, fg=C_TEXT,
                     font=("Segoe UI",9,"bold")).pack(side="left")
            aoi_lbl = tk.Label(row, text="⚠ Pendiente", bg=C_PANEL, fg=C_WARN,
                               font=("Segoe UI",9))
            aoi_lbl.pack(side="right")

            def do_aoi():
                img = ref_img()
                if not img: return
                dlg.withdraw()
                rect = pick_rectangle(img, "Área de interés — arrastre para seleccionar")
                dlg.deiconify()
                if rect:
                    aoi_rect[0] = rect
                    aoi_lbl.configure(
                        text=f"✓  ({rect[0]},{rect[1]}) → ({rect[2]},{rect[3]})", fg=C_OK)
                else:
                    aoi_lbl.configure(text="— Omitido", fg=C_DIM)

            tk.Button(row, text="✂  Seleccionar área", bg=C_ACC, fg=C_BG,
                      relief="flat", font=("Segoe UI",9,"bold"), padx=10, pady=4,
                      cursor="hand2", command=do_aoi).pack(side="left", padx=(10,0))

        # ── Máscara ───────────────────────────────────────────────────────────
        if self.use_mask:
            mask_card = tk.Frame(dlg, bg=C_PANEL, highlightbackground=C_BORDER, highlightthickness=1)
            mask_card.pack(fill="x", padx=20, pady=4)
            row = tk.Frame(mask_card, bg=C_PANEL); row.pack(fill="x", padx=14, pady=8)
            tk.Label(row, text="Máscara de exclusión", bg=C_PANEL, fg=C_TEXT,
                     font=("Segoe UI",9,"bold")).pack(side="left")
            mask_lbl = tk.Label(row, text="⚠ Pendiente", bg=C_PANEL, fg=C_WARN,
                                font=("Segoe UI",9))
            mask_lbl.pack(side="right")

            def do_mask():
                img = ref_img()
                if not img: return
                dlg.withdraw()
                rect = pick_rectangle(img, "Máscara de exclusión — arrastre sobre la región a ocultar")
                dlg.deiconify()
                if rect:
                    mask_rect[0] = rect
                    mask_lbl.configure(
                        text=f"✓  ({rect[0]},{rect[1]}) → ({rect[2]},{rect[3]})", fg=C_OK)
                else:
                    mask_lbl.configure(text="— Omitida", fg=C_DIM)

            tk.Button(row, text="🎭  Seleccionar región", bg=C_ACC, fg=C_BG,
                      relief="flat", font=("Segoe UI",9,"bold"), padx=10, pady=4,
                      cursor="hand2", command=do_mask).pack(side="left", padx=(10,0))

        # ── Confirmar ─────────────────────────────────────────────────────────
        def confirm():
            # Aplicar AOI
            if aoi_rect[0]:
                src = os.path.join(ruta,"colorCorrejidas")
                dst = os.path.join(ruta,"areaInteres")
                if os.path.isdir(src):
                    n = crop_folder(src, dst, aoi_rect[0])
                    self._log(f"  ✓  AOI aplicado a {n} imágenes → areaInteres/", "ok")
                self.step_enabled["06"] = False

            # Aplicar máscara
            if mask_rect[0]:
                target = os.path.join(ruta,"areaInteres")
                if not os.path.isdir(target):
                    target = os.path.join(ruta,"colorCorrejidas")
                if os.path.isdir(target):
                    n = mask_folder(target, mask_rect[0])
                    self._log(f"  ✓  Máscara aplicada a {n} imágenes.", "ok")
                self.step_enabled["07"] = False

            dlg.destroy()
            done_event.set()

        def skip():
            self._log("  — AOI/máscara omitidos por el usuario.", "warn")
            dlg.destroy()
            done_event.set()

        btn_row = tk.Frame(dlg, bg=C_BG); btn_row.pack(pady=16)
        tk.Button(btn_row, text="✓  Confirmar y continuar", bg=C_OK, fg=C_BG,
                  font=("Segoe UI",10,"bold"), relief="flat", padx=18, pady=8,
                  cursor="hand2", command=confirm).pack(side="left", padx=8)
        tk.Button(btn_row, text="Omitir y continuar", bg=C_PANEL, fg=C_TEXT,
                  font=("Segoe UI",9), relief="flat", padx=14, pady=8,
                  cursor="hand2", command=skip).pack(side="left", padx=4)

        dlg.protocol("WM_DELETE_WINDOW", skip)

    def _finish(self):
        self.running = False
        errs = sum(1 for s in STEPS if s.get("_iv") and s["_iv"].get() == S_ICON["error"])
        self._log("\n"+"─"*56,"dim")
        if self.stop_flag:
            self._log("Pipeline detenido.", "warn"); self.prog_lbl.configure(text="Detenido")
        else:
            self._log("Pipeline finalizado.", "step"); self.prog_lbl.configure(text="Completado")
            if errs == 0:
                messagebox.showinfo("¡Listo!", f"El pipeline finalizó correctamente.\n\nResultados en:\n{self.ruta}")
            else:
                messagebox.showwarning("Finalizado con errores",
                    f"El pipeline finalizó con {errs} error(es).\nRevise el registro.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    SetupWizard().mainloop()
