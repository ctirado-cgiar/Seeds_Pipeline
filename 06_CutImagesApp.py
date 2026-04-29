import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw
import glob

class ImageCropperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EasyBean - Morfologia V.1.0.0")
        
        # Variables
        self.source_folder = tk.StringVar()
        self.dest_folder = tk.StringVar()
        self.start_point = None
        self.end_point = None
        self.current_image = None
        self.tk_image = None
        self.rect_id = None
        self.crop_shape = tk.StringVar(value="rectangular")  # rectangular o square
        self.temp_rect = None
        
        # UI Elements
        self.create_widgets()
        
    def create_widgets(self):
        # Source folder selection
        tk.Label(self.root, text="Carpeta de imágenes:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        tk.Entry(self.root, textvariable=self.source_folder, width=50).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Seleccionar", command=self.select_source_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # Destination folder selection
        tk.Label(self.root, text="Carpeta de destino:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        tk.Entry(self.root, textvariable=self.dest_folder, width=50).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Seleccionar", command=self.select_dest_folder).grid(row=1, column=2, padx=5, pady=5)
        
        # Shape selection
        shape_frame = tk.Frame(self.root)
        shape_frame.grid(row=2, column=0, columnspan=3, pady=5)
        tk.Label(shape_frame, text="Forma de recorte:").pack(side=tk.LEFT)
        ttk.Radiobutton(shape_frame, text="Rectangular", variable=self.crop_shape, value="rectangular").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(shape_frame, text="Cuadrado", variable=self.crop_shape, value="square").pack(side=tk.LEFT, padx=5)
        
        # Image display canvas
        self.canvas = tk.Canvas(self.root, width=600, height=400, bg='white')
        self.canvas.grid(row=3, column=0, columnspan=3, padx=5, pady=5)
        self.canvas.bind("<ButtonPress-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.update_selection)
        self.canvas.bind("<ButtonRelease-1>", self.end_selection)
        
        # Buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=5)
        tk.Button(btn_frame, text="Cargar Imagen", command=self.load_sample_image).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Procesar Todas", command=self.process_all_images).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Limpiar Selección", command=self.clear_selection).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status = tk.Label(self.root, text="Seleccione una carpeta y cargue una imagen para seleccionar el área de recorte", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.grid(row=5, column=0, columnspan=3, sticky='we', padx=5, pady=5)
    
    def select_source_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta con imágenes")
        if folder:
            self.source_folder.set(folder)
            self.status.config(text=f"Carpeta origen seleccionada: {folder}")
    
    def select_dest_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if folder:
            self.dest_folder.set(folder)
            self.status.config(text=f"Carpeta destino seleccionada: {folder}")
    
    def load_sample_image(self):
        if not self.source_folder.get():
            messagebox.showerror("Error", "Primero seleccione una carpeta con imágenes")
            return
        
        image_files = glob.glob(os.path.join(self.source_folder.get(), '*.[jJ][pP][gG]')) + \
                     glob.glob(os.path.join(self.source_folder.get(), '*.[pP][nN][gG]')) + \
                     glob.glob(os.path.join(self.source_folder.get(), '*.[jJ][pP][eE][gG]'))
        
        if not image_files:
            messagebox.showerror("Error", "No se encontraron imágenes en la carpeta seleccionada")
            return
        
        # Load the first image
        try:
            self.current_image = Image.open(image_files[0])
            self.display_image(self.current_image)
            self.status.config(text=f"Imagen cargada: {os.path.basename(image_files[0])}. Arrastre para seleccionar el área de recorte.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la imagen: {str(e)}")
    
    def display_image(self, image):
        # Resize for display but keep original for processing
        display_width = 600
        display_height = 400
        img_width, img_height = image.size
        ratio = min(display_width/img_width, display_height/img_height)
        
        display_size = (int(img_width * ratio), int(img_height * ratio))
        display_img = image.resize(display_size, Image.Resampling.LANCZOS)
        
        self.display_ratio = ratio
        self.tk_image = ImageTk.PhotoImage(display_img)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)
    
    def start_selection(self, event):
        if not self.current_image:
            return
            
        self.start_point = (event.x, event.y)
        self.end_point = None
        self.temp_rect = None
    
    def update_selection(self, event):
        if not self.current_image or not self.start_point:
            return
            
        # Delete previous temporary rectangle
        if self.temp_rect:
            self.canvas.delete(self.temp_rect)
        
        x0, y0 = self.start_point
        x1, y1 = event.x, event.y
        
        # For square selection, adjust coordinates to maintain aspect ratio
        if self.crop_shape.get() == "square":
            width = abs(x1 - x0)
            height = abs(y1 - y0)
            size = min(width, height)
            
            if x1 < x0:
                x1 = x0 - size
            else:
                x1 = x0 + size
                
            if y1 < y0:
                y1 = y0 - size
            else:
                y1 = y0 + size
        
        # Draw temporary rectangle
        self.temp_rect = self.canvas.create_rectangle(
            x0, y0, x1, y1,
            outline='red', dash=(5,5), width=2, tag="selection"
        )
    
    def end_selection(self, event):
        if not self.current_image or not self.start_point:
            return
            
        x0, y0 = self.start_point
        x1, y1 = event.x, event.y
        
        # For square selection, adjust coordinates to maintain aspect ratio
        if self.crop_shape.get() == "square":
            width = abs(x1 - x0)
            height = abs(y1 - y0)
            size = min(width, height)
            
            if x1 < x0:
                x1 = x0 - size
            else:
                x1 = x0 + size
                
            if y1 < y0:
                y1 = y0 - size
            else:
                y1 = y0 + size
        
        self.end_point = (x1, y1)
        
        # Draw final selection rectangle
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            
        self.rect_id = self.canvas.create_rectangle(
            x0, y0, x1, y1,
            outline='blue', width=2, tag="selection"
        )
        
        self.status.config(text="Área de recorte seleccionada (azul). Puede procesar las imágenes o limpiar la selección.")
    
    def clear_selection(self):
        self.start_point = None
        self.end_point = None
        self.canvas.delete("selection")
        if self.current_image:
            self.display_image(self.current_image)
        self.status.config(text="Selección limpiada. Arrastre para seleccionar un nuevo área de recorte.")
    
    def process_all_images(self):
        if not self.source_folder.get() or not self.dest_folder.get():
            messagebox.showerror("Error", "Debe seleccionar tanto la carpeta origen como la de destino")
            return
            
        if not self.start_point or not self.end_point:
            messagebox.showerror("Error", "Debe seleccionar un área de recorte")
            return
            
        # Convert display coordinates to original image coordinates
        x0, y0 = self.start_point
        x1, y1 = self.end_point
        
        # Scale back to original image coordinates
        x0_orig = int(x0 / self.display_ratio)
        y0_orig = int(y0 / self.display_ratio)
        x1_orig = int(x1 / self.display_ratio)
        y1_orig = int(y1 / self.display_ratio)
        
        # Ensure x0,y0 is top-left and x1,y1 is bottom-right
        left = min(x0_orig, x1_orig)
        right = max(x0_orig, x1_orig)
        top = min(y0_orig, y1_orig)
        bottom = max(y0_orig, y1_orig)
        
        # Get all image files
        image_files = glob.glob(os.path.join(self.source_folder.get(), '*.[jJ][pP][gG]')) + \
                     glob.glob(os.path.join(self.source_folder.get(), '*.[pP][nN][gG]')) + \
                     glob.glob(os.path.join(self.source_folder.get(), '*.[jJ][pP][eE][gG]'))
        
        if not image_files:
            messagebox.showerror("Error", "No se encontraron imágenes en la carpeta seleccionada")
            return
        
        # Create destination folder if it doesn't exist
        os.makedirs(self.dest_folder.get(), exist_ok=True)
        
        # Process each image
        success_count = 0
        for img_path in image_files:
            try:
                img = Image.open(img_path)
                cropped = img.crop((left, top, right, bottom))
                
                # Save to destination
                dest_path = os.path.join(self.dest_folder.get(), os.path.basename(img_path))
                cropped.save(dest_path)
                success_count += 1
            except Exception as e:
                print(f"Error procesando {img_path}: {str(e)}")
        
        messagebox.showinfo("Completado", f"Procesadas {success_count} de {len(image_files)} imágenes correctamente")
        self.status.config(text=f"Proceso completado. {success_count} imágenes procesadas.")

def main():
    root = tk.Tk()
    app = ImageCropperApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()