import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
from PIL import Image, ImageTk, ImageDraw
import glob

class AppMascara:
    def __init__(self, root):
        self.root = root
        self.root.title("EasyBean - Máscara de Color v2.0")

        self.source_folder = tk.StringVar()
        self.mask_color_mode = tk.StringVar(value="preset")
        self.preset_color = tk.StringVar(value="black")
        self.custom_color = "#000000"  # Color personalizado en formato hex
        self.mask_shape = tk.StringVar(value="rectangle")

        self.start_point = None
        self.end_point = None
        self.display_ratio = 1
        self.image = None
        self.tk_image = None
        self.rect_id = None

        self.build_ui()

    def build_ui(self):
        control_frame = tk.Frame(self.root)
        
        # Selector de carpeta
        tk.Label(control_frame, text="Carpeta de imágenes:").grid(row=0, column=0, sticky='w')
        tk.Entry(control_frame, textvariable=self.source_folder, width=50).grid(row=0, column=1, padx=5)
        tk.Button(control_frame, text="Seleccionar", command=self.select_folder).grid(row=0, column=2, padx=5)

        tk.Button(control_frame, text="Cargar imagen de ejemplo", command=self.load_image).grid(row=1, column=0, columnspan=3, pady=5)

        # Selector de forma
        shape_frame = tk.Frame(control_frame)
        tk.Label(shape_frame, text="Forma de máscara:").pack(side=tk.LEFT)
        ttk.Radiobutton(shape_frame, text="Rectangular", variable=self.mask_shape, value="rectangle").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(shape_frame, text="Cuadrado", variable=self.mask_shape, value="square").pack(side=tk.LEFT, padx=5)
        shape_frame.grid(row=2, column=0, columnspan=3, pady=5)

        # Selector de modo de color
        color_mode_frame = tk.Frame(control_frame)
        tk.Label(color_mode_frame, text="Modo de color:").pack(side=tk.LEFT)
        ttk.Radiobutton(color_mode_frame, text="Colores predefinidos", variable=self.mask_color_mode, value="preset", command=self.update_color_options).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(color_mode_frame, text="Color personalizado", variable=self.mask_color_mode, value="custom", command=self.update_color_options).pack(side=tk.LEFT, padx=5)
        color_mode_frame.grid(row=3, column=0, columnspan=3, pady=5)

        # Frame para opciones de color (se actualiza dinámicamente)
        self.color_options_frame = tk.Frame(control_frame)
        self.color_options_frame.grid(row=4, column=0, columnspan=3, pady=5)
        
        self.update_color_options()

        tk.Button(control_frame, text="Seleccionar área", command=self.enable_mask_selection).grid(row=5, column=0, columnspan=3, pady=5)
        tk.Button(control_frame, text="Aplicar máscara a todas", command=self.apply_mask_all).grid(row=6, column=0, columnspan=3, pady=5)

        control_frame.pack(pady=10)

        self.canvas = tk.Canvas(self.root, width=800, height=600, bg='white')
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def update_color_options(self):
        # Limpiar el frame de opciones de color
        for widget in self.color_options_frame.winfo_children():
            widget.destroy()

        if self.mask_color_mode.get() == "preset":
            # Mostrar colores predefinidos
            tk.Label(self.color_options_frame, text="Color de máscara:").pack(side=tk.LEFT)
            ttk.Radiobutton(self.color_options_frame, text="Negro", variable=self.preset_color, value="black").pack(side=tk.LEFT, padx=5)
            ttk.Radiobutton(self.color_options_frame, text="Blanco", variable=self.preset_color, value="white").pack(side=tk.LEFT, padx=5)
            ttk.Radiobutton(self.color_options_frame, text="Rojo", variable=self.preset_color, value="red").pack(side=tk.LEFT, padx=5)
            ttk.Radiobutton(self.color_options_frame, text="Azul", variable=self.preset_color, value="blue").pack(side=tk.LEFT, padx=5)
            ttk.Radiobutton(self.color_options_frame, text="Verde", variable=self.preset_color, value="green").pack(side=tk.LEFT, padx=5)
        else:
            # Mostrar selector de color personalizado
            tk.Label(self.color_options_frame, text="Color personalizado:").pack(side=tk.LEFT)
            self.color_button = tk.Button(self.color_options_frame, text="Seleccionar color", 
                                        command=self.choose_color, bg=self.custom_color, width=15)
            self.color_button.pack(side=tk.LEFT, padx=5)
            self.color_label = tk.Label(self.color_options_frame, text=self.custom_color)
            self.color_label.pack(side=tk.LEFT, padx=5)

    def choose_color(self):
        color = colorchooser.askcolor(color=self.custom_color, title="Seleccionar color de máscara")
        if color[1]:  # Si se seleccionó un color
            self.custom_color = color[1]
            self.color_button.config(bg=self.custom_color)
            self.color_label.config(text=self.custom_color)

    def get_selected_color_rgb(self):
        """Devuelve el color seleccionado en formato RGB"""
        if self.mask_color_mode.get() == "preset":
            color_map = {
                "black": (0, 0, 0),
                "white": (255, 255, 255),
                "red": (255, 0, 0),
                "blue": (0, 0, 255),
                "green": (0, 255, 0)
            }
            return color_map[self.preset_color.get()]
        else:
            # Convertir color hex a RGB
            hex_color = self.custom_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_folder.set(folder)

    def load_image(self):
        if not self.source_folder.get():
            messagebox.showerror("Error", "Seleccione una carpeta primero")
            return
        files = glob.glob(os.path.join(self.source_folder.get(), '*.jpg'))
        if not files:
            messagebox.showerror("Error", "No hay imágenes .jpg en la carpeta")
            return
        self.image_path = files[0]
        self.image = Image.open(self.image_path)
        self.display_image(self.image)

    def display_image(self, img):
        img_width, img_height = img.size
        canvas_width, canvas_height = 800, 600
        self.display_ratio = min(canvas_width / img_width, canvas_height / img_height)
        new_size = (int(img_width * self.display_ratio), int(img_height * self.display_ratio))
        resized = img.resize(new_size, Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

    def enable_mask_selection(self):
        self.start_point = None
        self.end_point = None
        self.rect_id = None

    def on_click(self, event):
        self.start_point = (event.x, event.y)

    def on_drag(self, event):
        if self.start_point:
            self.end_point = (event.x, event.y)
            if self.rect_id:
                self.canvas.delete(self.rect_id)

            x0, y0 = self.start_point
            x1, y1 = self.end_point

            if self.mask_shape.get() == "square":
                size = min(abs(x1 - x0), abs(y1 - y0))
                x1 = x0 + size if x1 > x0 else x0 - size
                y1 = y0 + size if y1 > y0 else y0 - size

            self.rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline="red", dash=(4, 4), width=2)

    def on_release(self, event):
        self.end_point = (event.x, event.y)

    def apply_mask_all(self):
        if not self.start_point or not self.end_point:
            messagebox.showerror("Error", "Debe seleccionar un área")
            return

        x0, y0 = self.start_point
        x1, y1 = self.end_point

        if self.mask_shape.get() == "square":
            size = min(abs(x1 - x0), abs(y1 - y0))
            x1 = x0 + size if x1 >= x0 else x0 - size
            y1 = y0 + size if y1 >= y0 else y0 - size

        left = int(min(x0, x1) / self.display_ratio)
        right = int(max(x0, x1) / self.display_ratio)
        top = int(min(y0, y1) / self.display_ratio)
        bottom = int(max(y0, y1) / self.display_ratio)

        # Obtener el color seleccionado
        color_rgb = self.get_selected_color_rgb()

        files = glob.glob(os.path.join(self.source_folder.get(), '*.jpg'))
        processed_count = 0
        
        for path in files:
            try:
                img = Image.open(path).convert("RGB")
                draw = ImageDraw.Draw(img)
                draw.rectangle([left, top, right, bottom], fill=color_rgb)
                img.save(path)
                processed_count += 1
            except Exception as e:
                print(f"Error con {path}: {e}")

        messagebox.showinfo("Completado", f"Máscara aplicada correctamente a {processed_count} imágenes.\nColor usado: RGB{color_rgb}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppMascara(root)
    root.mainloop()