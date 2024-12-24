import os
import exifread
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk


class ImageMetadataApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestión de Imágenes")
        self.root.geometry("1920x1080")
        self.root.resizable(True, True)

        # Carpeta inicial
        self.current_folder = "./image_folder"
        os.makedirs(self.current_folder, exist_ok=True)

        # Configuración de paginación
        self.page_size = 10
        self.current_page = 0
        self.image_list = []
        self.metadata_list = []
        self.filtered_metadata_list = []

        # Configuración del Grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=2)
        self.root.grid_rowconfigure(1, weight=1)

        # Frame superior para la selección de carpeta
        self.top_frame = tk.Frame(self.root)
        self.top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        self.top_frame.grid_columnconfigure(0, weight=1)
        self.top_frame.grid_columnconfigure(1, weight=0)

        self.folder_label = ttk.Label(self.top_frame, text="Carpeta Actual:")
        self.folder_label.grid(row=0, column=0, sticky="w", padx=5)

        self.select_folder_button = ttk.Button(self.top_frame, text="Seleccionar Carpeta", command=self.select_folder)
        self.select_folder_button.grid(row=0, column=1, sticky="e", padx=5)

        # Frame para los filtros
        self.filter_frame = tk.Frame(self.root, relief=tk.GROOVE, borderwidth=1)
        self.filter_frame.grid(row=1, column=0, sticky="ns", padx=10, pady=10)
        self.filter_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(self.filter_frame, text="Filtros de Búsqueda").grid(row=0, column=0, columnspan=2, pady=5)

        self.name_label = ttk.Label(self.filter_frame, text="Nombre:")
        self.name_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.name_entry = ttk.Entry(self.filter_frame)
        self.name_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        self.invoice_label = ttk.Label(self.filter_frame, text="Comprobante:")
        self.invoice_label.grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.invoice_entry = ttk.Entry(self.filter_frame)
        self.invoice_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        self.date_label = ttk.Label(self.filter_frame, text="Fecha (YYYY-MM-DD):")
        self.date_label.grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.start_date_entry = ttk.Entry(self.filter_frame, width=10)
        self.start_date_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        self.end_date_entry = ttk.Entry(self.filter_frame, width=10)
        self.end_date_entry.grid(row=3, column=1, sticky="e", padx=5, pady=5)

        self.search_button = ttk.Button(self.filter_frame, text="Buscar", command=self.search_images)
        self.search_button.grid(row=4, column=0, columnspan=2, pady=10)

        self.clear_search_button = ttk.Button(self.filter_frame, text="Limpiar Filtros", command=self.clear_search)
        self.clear_search_button.grid(row=5, column=0, columnspan=2, pady=10)

        # Frame principal para las imágenes y su scroll
        self.main_frame = tk.Frame(self.root)
        self.main_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

        self.canvas = tk.Canvas(self.main_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar_y = tk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.scrollbar_x = tk.Scrollbar(self.root, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.scrollbar_x.grid(row=2, column=1, sticky="ew", padx=10, pady=5)

        self.canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)

        self.list_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")

        self.image_listbox = tk.Listbox(self.list_frame, height=20, width=50)
        self.image_listbox.pack(fill=tk.BOTH, expand=True)
        self.image_listbox.bind("<<ListboxSelect>>", self.display_image)

        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Paginación
        self.pagination_frame = tk.Frame(self.root)
        self.pagination_frame.grid(row=3, column=1, pady=10)

        self.previous_button = ttk.Button(self.pagination_frame, text="Anterior", command=self.previous_page)
        self.previous_button.grid(row=0, column=0, padx=10)

        self.next_button = ttk.Button(self.pagination_frame, text="Siguiente", command=self.next_page)
        self.next_button.grid(row=0, column=1, padx=10)

        # Frame derecho para mostrar la imagen y la metadata
        self.image_frame = tk.Frame(self.root, relief=tk.GROOVE, borderwidth=1)
        self.image_frame.grid(row=1, column=2, sticky="nsew", padx=10, pady=10)
        self.root.grid_columnconfigure(2, weight=2)

        self.image_label = tk.Label(self.image_frame, cursor="hand2")
        self.image_label.pack(pady=10)
        self.image_label.bind("<Button-1>", self.show_large_image)

        self.metadata_frame = tk.Frame(self.image_frame)
        self.metadata_frame.pack(pady=10, fill=tk.X)

        self.file_name_label = ttk.Label(self.metadata_frame, text="Nombre:")
        self.file_name_label.grid(row=0, column=0, sticky="w")
        self.file_name_entry = ttk.Entry(self.metadata_frame, width=30)
        self.file_name_entry.grid(row=0, column=1, sticky="ew")

        self.reason_label = ttk.Label(self.metadata_frame, text="Razón Social:")
        self.reason_label.grid(row=1, column=0, sticky="w")
        self.reason_entry = ttk.Entry(self.metadata_frame, width=30)
        self.reason_entry.grid(row=1, column=1, sticky="ew")

        self.invoice_label = ttk.Label(self.metadata_frame, text="Número de Factura:")
        self.invoice_label.grid(row=2, column=0, sticky="w")
        self.invoice_entry = ttk.Entry(self.metadata_frame, width=30)
        self.invoice_entry.grid(row=2, column=1, sticky="ew")

        self.date_label = ttk.Label(self.metadata_frame, text="Fecha de Emisión:")
        self.date_label.grid(row=3, column=0, sticky="w")
        self.date_entry = ttk.Entry(self.metadata_frame, width=30)
        self.date_entry.grid(row=3, column=1, sticky="ew")

        self.save_button = ttk.Button(self.metadata_frame, text="Renombrar Archivo", command=self.rename_file)
        self.save_button.grid(row=4, column=1, sticky="e", pady=10)

        # Cargar imágenes iniciales
        self.load_images()

    def select_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar Carpeta")
        if folder:
            self.current_folder = folder
            self.folder_label.config(text=f"Carpeta Actual: {self.current_folder}")
            self.load_images()

    def load_images(self):
        self.image_list = [
            os.path.join(self.current_folder, file)
            for file in os.listdir(self.current_folder)
            if file.lower().endswith((".jpg", ".jpeg", ".png", ".jfif"))
        ]
        self.metadata_list = [self.extract_metadata(image) for image in self.image_list]
        self.filtered_metadata_list = self.metadata_list.copy()
        self.update_listbox()

    def update_listbox(self):
        self.image_listbox.delete(0, tk.END)
        start = self.current_page * self.page_size
        end = start + self.page_size
        for metadata in self.filtered_metadata_list[start:end]:
            self.image_listbox.insert(tk.END, metadata["file_name"])
        self.previous_button.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if end < len(self.filtered_metadata_list) else tk.DISABLED)

    def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_listbox()

    def next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.filtered_metadata_list):
            self.current_page += 1
            self.update_listbox()

    def search_images(self):
        name_query = self.name_entry.get().lower()
        invoice_query = self.invoice_entry.get().lower()
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()

        self.filtered_metadata_list = self.metadata_list

        if name_query:
            self.filtered_metadata_list = [
                md for md in self.filtered_metadata_list if name_query in md["file_name"].lower()
            ]

        if invoice_query:
            self.filtered_metadata_list = [
                md for md in self.filtered_metadata_list if md["invoice_number"] and invoice_query in md["invoice_number"].lower()
            ]

        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                self.filtered_metadata_list = [
                    md for md in self.filtered_metadata_list if md["issue_date"] and start_date <= md["issue_date"] <= end_date
                ]
            except ValueError:
                messagebox.showerror("Error", "Las fechas deben estar en formato YYYY-MM-DD.")
                return

        self.current_page = 0
        self.update_listbox()

    def clear_search(self):
        self.name_entry.delete(0, tk.END)
        self.invoice_entry.delete(0, tk.END)
        self.start_date_entry.delete(0, tk.END)
        self.end_date_entry.delete(0, tk.END)
        self.filtered_metadata_list = self.metadata_list.copy()
        self.current_page = 0
        self.update_listbox()

    def display_image(self, event):
        selection = self.image_listbox.curselection()
        if not selection:
            return
        index = selection[0] + (self.current_page * self.page_size)
        metadata = self.filtered_metadata_list[index]

        image_path = metadata["file_path"]
        image = Image.open(image_path)
        image.thumbnail((400, 400))
        image_tk = ImageTk.PhotoImage(image)
        self.image_label.configure(image=image_tk)
        self.image_label.image = image_tk
        self.image_label.image_path = image_path

        self.file_name_entry.delete(0, tk.END)
        self.file_name_entry.insert(0, metadata["file_name"])

        self.reason_entry.delete(0, tk.END)
        self.reason_entry.insert(0, metadata["reason_social"] or "")

        self.invoice_entry.delete(0, tk.END)
        self.invoice_entry.insert(0, metadata["invoice_number"] or "")

        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, metadata["issue_date"] or "")

    def rename_file(self):
        current_file_path = self.image_label.image_path
        if not current_file_path:
            messagebox.showerror("Error", "No se seleccionó ninguna imagen.")
            return

        new_name = self.file_name_entry.get()
        if not new_name:
            messagebox.showerror("Error", "El nombre no puede estar vacío.")
            return

        new_file_path = os.path.join(self.current_folder, new_name)

        try:
            os.rename(current_file_path, new_file_path)
            messagebox.showinfo("Éxito", "El archivo se renombró correctamente.")
            self.load_images()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo renombrar el archivo: {e}")

    def extract_metadata(self, image_path):
        try:
            with open(image_path, 'rb') as img_file:
                tags = exifread.process_file(img_file)
                issue_date = tags.get("EXIF DateTimeOriginal")
                invoice_number = tags.get("InvoiceNumber")
                reason_social = tags.get("ReasonSocial")

                if issue_date:
                    issue_date = datetime.strptime(issue_date.values, "%Y:%m:%d %H:%M:%S").date()

                return {
                    "file_name": os.path.basename(image_path),
                    "file_path": image_path,
                    "issue_date": issue_date,
                    "invoice_number": invoice_number.values if invoice_number else None,
                    "reason_social": reason_social.values if reason_social else None,
                }
        except Exception:
            return {
                "file_name": os.path.basename(image_path),
                "file_path": image_path,
                "issue_date": None,
                "invoice_number": None,
                "reason_social": None,
            }

    def show_large_image(self, event):
        image_path = self.image_label.image_path
        if not image_path:
            return

        try:
            top = tk.Toplevel(self.root)
            top.title("Imagen Ampliada")
            top.geometry("800x600")
            top.resizable(True, True)

            frame = tk.Frame(top)
            frame.pack(fill=tk.BOTH, expand=True)

            canvas = tk.Canvas(frame, bg="black")
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            x_scroll = tk.Scrollbar(frame, orient=tk.HORIZONTAL, command=canvas.xview)
            x_scroll.pack(side=tk.BOTTOM, fill=tk.X)

            y_scroll = tk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
            y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

            canvas.config(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)

            pil_image = Image.open(image_path)
            self.large_image = ImageTk.PhotoImage(pil_image)

            canvas.create_image(0, 0, anchor=tk.NW, image=self.large_image)
            canvas.config(scrollregion=canvas.bbox(tk.ALL))

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la imagen: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageMetadataApp(root)
    root.mainloop()
