import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import fitz  # PyMuPDF
import asyncio
import threading
from pathlib import Path
import logging
import re

class ValidadorMasivoPDF(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Validador Masivo de Facturas (PDF) con Paginación, Extracción y Eliminación tras Renombrar")
        self.geometry("1200x700")

        # Lista completa de PDFs en la carpeta
        self.archivos_pdf = []
        self.directorio_actual = None

        # Paginación
        self.pdfs_per_page = 3  # Cuántos PDFs se muestran por “página”
        self.current_page = 0   # Índice de la página actual

        # Estructura para datos de cada página (miniaturas, checks, etc.)
        # Formato: [{'ruta_pdf':..., 'pdf_name':..., 'pag_index':..., 'check_var':..., 'entry_widget':...}, ...]
        self.datos_paginas = []

        # Configurar logging
        logging.basicConfig(
            filename='visor_pdf.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Construir la interfaz principal
        self.configurar_interfaz()

    def configurar_interfaz(self):
        """
        Crea los widgets principales: botones superiores, área de miniaturas con scroll y barra de paginación.
        """
        # Frame superior (botones)
        self.frame_superior = ttk.Frame(self)
        self.frame_superior.pack(fill=tk.X, padx=10, pady=5)

        # Botón: Seleccionar Carpeta
        self.boton_cargar = ttk.Button(
            self.frame_superior, 
            text="Seleccionar Carpeta de PDFs", 
            command=self.cargar_directorio
        )
        self.boton_cargar.pack(side=tk.LEFT, padx=5)

        # Botón: Guardar Validaciones (checkbox + observaciones)
        self.boton_guardar = ttk.Button(
            self.frame_superior,
            text="Guardar Validaciones",
            command=self.guardar_validaciones
        )
        self.boton_guardar.pack(side=tk.LEFT, padx=5)

        # Área con scroll para miniaturas
        self.frame_scroll = ttk.Frame(self)
        self.frame_scroll.pack(fill=tk.BOTH, expand=True)

        self.canvas_scroll = tk.Canvas(self.frame_scroll)
        self.scrollbar_y = ttk.Scrollbar(self.frame_scroll, orient=tk.VERTICAL, command=self.canvas_scroll.yview)
        self.canvas_scroll.configure(yscrollcommand=self.scrollbar_y.set)
        
        self.canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Frame contenedor interno para los PDFs y sus páginas
        self.frame_contenedor = ttk.Frame(self.canvas_scroll)
        self.canvas_scroll.create_window((0, 0), window=self.frame_contenedor, anchor=tk.NW)

        # Ajustar la región de scroll cuando cambie el tamaño
        self.frame_contenedor.bind(
            "<Configure>", 
            lambda e: self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all"))
        )

        # Frame inferior (paginación)
        self.frame_inferior = ttk.Frame(self)
        self.frame_inferior.pack(fill=tk.X, padx=10, pady=5)

        self.boton_anterior = ttk.Button(self.frame_inferior, text="<< Anterior", command=self.pag_anterior)
        self.boton_anterior.pack(side=tk.LEFT, padx=5)

        self.label_paginacion = ttk.Label(self.frame_inferior, text="Página 0 / 0")
        self.label_paginacion.pack(side=tk.LEFT, padx=10)

        self.boton_siguiente = ttk.Button(self.frame_inferior, text="Siguiente >>", command=self.pag_siguiente)
        self.boton_siguiente.pack(side=tk.LEFT, padx=5)

    # -------------------- PAGINACIÓN --------------------
    def pag_anterior(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.mostrar_pagina_actual()

    def pag_siguiente(self):
        max_page = (len(self.archivos_pdf) - 1) // self.pdfs_per_page
        if self.current_page < max_page:
            self.current_page += 1
            self.mostrar_pagina_actual()

    def mostrar_pagina_actual(self):
        """
        Limpia el contenedor y muestra sólo los PDFs de la "página" actual.
        """
        # Borrar contenido actual
        for widget in self.frame_contenedor.winfo_children():
            widget.destroy()
        self.datos_paginas.clear()

        start_index = self.current_page * self.pdfs_per_page
        end_index = start_index + self.pdfs_per_page
        pdfs_en_esta_pagina = self.archivos_pdf[start_index:end_index]

        # Actualizar etiqueta de paginación
        max_page = (len(self.archivos_pdf) - 1) // self.pdfs_per_page
        self.label_paginacion.config(text=f"Página {self.current_page+1} / {max_page+1}")

        # Cargar las miniaturas en un hilo aparte
        threading.Thread(
            target=lambda: asyncio.run(self.cargar_miniaturas_pagina(pdfs_en_esta_pagina))
        ).start()

    async def cargar_miniaturas_pagina(self, lista_pdfs):
        """
        Genera miniaturas SOLO para los PDFs en la lista.
        """
        for pdf_name in lista_pdfs:
            ruta_pdf = os.path.join(self.directorio_actual, pdf_name)
            try:
                doc = fitz.open(ruta_pdf)
            except Exception as e:
                logging.error(f"No se pudo abrir {pdf_name}: {e}")
                continue

            # LabelFrame para agrupar las páginas de este PDF
            frame_pdf_title = ttk.LabelFrame(self.frame_contenedor, text=pdf_name)
            frame_pdf_title.pack(fill=tk.X, padx=5, pady=5)

            for page_index in range(len(doc)):
                try:
                    page = doc[page_index]
                    thumb_matrix = fitz.Matrix(0.2, 0.2)  # Zoom miniatura
                    pix = page.get_pixmap(matrix=thumb_matrix)
                    img = tk.PhotoImage(data=pix.tobytes("ppm"))
                except Exception as e:
                    logging.warning(f"No se pudo generar miniatura: {pdf_name}, página {page_index+1}")
                    img = None

                frame_pagina = ttk.Frame(frame_pdf_title)
                frame_pagina.pack(fill=tk.X, padx=5, pady=5)

                var_check = tk.BooleanVar(value=False)
                chk = ttk.Checkbutton(frame_pagina, variable=var_check)
                chk.pack(side=tk.LEFT, padx=5)

                if img:
                    lbl_img = tk.Label(frame_pagina, image=img, cursor="hand2")
                    lbl_img.image = img  # Mantener referencia
                    lbl_img.pack(side=tk.LEFT, padx=5)
                    # Clic => ver vista detallada
                    lbl_img.bind(
                        "<Button-1>",
                        lambda e, rp=ruta_pdf, pi=page_index: self.abrir_vista_detallada(rp, pi)
                    )
                else:
                    # Si no hay miniatura
                    lbl_img = tk.Label(frame_pagina, text=f"[Página {page_index+1}]", fg="red", cursor="hand2")
                    lbl_img.pack(side=tk.LEFT, padx=5)
                    lbl_img.bind(
                        "<Button-1>",
                        lambda e, rp=ruta_pdf, pi=page_index: self.abrir_vista_detallada(rp, pi)
                    )

                ttk.Label(frame_pagina, text=f"Pág {page_index+1}").pack(side=tk.LEFT, padx=5)

                entry_val = ttk.Entry(frame_pagina, width=60)
                entry_val.insert(0, f"Observación pág {page_index+1}")
                entry_val.pack(side=tk.LEFT, padx=5)

                # Guardar info en datos_paginas
                self.datos_paginas.append({
                    "ruta_pdf": ruta_pdf,
                    "pdf_name": pdf_name,
                    "pag_index": page_index,
                    "check_var": var_check,
                    "entry_widget": entry_val,
                })
            doc.close()
            await asyncio.sleep(0)  # ceder el control al loop

        logging.info("Miniaturas de la página actual cargadas.")

    def cargar_directorio(self):
        """
        Solicita la carpeta con PDFs y muestra la primera página de resultados.
        """
        directorio = filedialog.askdirectory(title="Seleccionar directorio de PDFs")
        if not directorio:
            return
        
        self.directorio_actual = directorio
        self.archivos_pdf = [
            f for f in os.listdir(directorio)
            if f.lower().endswith(".pdf")
        ]
        self.archivos_pdf.sort()

        if not self.archivos_pdf:
            messagebox.showinfo("Sin PDFs", "No se encontraron PDFs en la carpeta.")
            return

        self.current_page = 0
        self.mostrar_pagina_actual()

    def abrir_vista_detallada(self, ruta_pdf, page_index):
        """
        Abre una ventana con zoom y scroll, ofreciendo renombrado y extracción de páginas.
        """
        try:
            doc = fitz.open(ruta_pdf)
            page = doc[page_index]
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la página:\n{e}")
            return

        vent_detail = tk.Toplevel(self)
        vent_detail.title(f"Vista detallada: {os.path.basename(ruta_pdf)} - Página {page_index+1}")
        vent_detail.geometry("900x700")

        frame_princ = ttk.Frame(vent_detail)
        frame_princ.pack(fill=tk.BOTH, expand=True)

        canvas_detalle = tk.Canvas(frame_princ, bg="white")
        canvas_detalle.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar_det_y = ttk.Scrollbar(frame_princ, orient=tk.VERTICAL, command=canvas_detalle.yview)
        scrollbar_det_y.pack(side=tk.RIGHT, fill=tk.Y)

        scrollbar_det_x = ttk.Scrollbar(vent_detail, orient=tk.HORIZONTAL, command=canvas_detalle.xview)
        scrollbar_det_x.pack(side=tk.BOTTOM, fill=tk.X)

        canvas_detalle.configure(
            xscrollcommand=scrollbar_det_x.set,
            yscrollcommand=scrollbar_det_y.set,
            scrollregion=(0,0,0,0)
        )

        detail_matrix = fitz.Matrix(1.5, 1.5)  # Zoom de 150%
        pix = page.get_pixmap(matrix=detail_matrix)
        img = tk.PhotoImage(data=pix.tobytes("ppm"))

        canvas_detalle.create_image(0, 0, anchor=tk.NW, image=img)
        canvas_detalle.image = img
        canvas_detalle.config(scrollregion=(0, 0, img.width(), img.height()))

        def _on_mousewheel(event):
            canvas_detalle.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas_detalle.bind_all("<MouseWheel>", _on_mousewheel)

        frame_inferior = ttk.Frame(vent_detail)
        frame_inferior.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)

        # Renombrar con fecha
        ttk.Label(frame_inferior, text="Fecha (ej. 2023-08-15):").pack(side=tk.LEFT, padx=(0,5))
        entry_fecha = ttk.Entry(frame_inferior, width=20)
        entry_fecha.pack(side=tk.LEFT, padx=5)

        def renombrar_con_fecha():
            fecha = entry_fecha.get().strip()
            if not fecha:
                messagebox.showwarning("Advertencia", "Ingrese la fecha.")
                return
            # Reemplazar caracteres no permitidos en Windows
            fecha = re.sub(r'[<>:"/\\|?*]', '_', fecha)

            doc.close()
            self.renombrar_pdf(ruta_pdf, fecha)
            vent_detail.destroy()

        ttk.Button(
            frame_inferior,
            text="Renombrar PDF con fecha",
            command=renombrar_con_fecha
        ).pack(side=tk.LEFT, padx=5)

        # Extraer páginas
        ttk.Button(
            frame_inferior,
            text="Extraer páginas",
            command=lambda: self.extraer_paginas(doc, ruta_pdf)
        ).pack(side=tk.LEFT, padx=5)

    def extraer_paginas(self, doc_original, ruta_pdf):
        """
        Abre un cuadro para ingresar el rango de páginas a extraer y genera un nuevo PDF.
        """
        vent_extract = tk.Toplevel(self)
        vent_extract.title("Extraer páginas")
        vent_extract.geometry("300x150")

        ttk.Label(vent_extract, text="Rango de páginas (ej. '1-3' o '5'):").pack(pady=5)
        entry_rango = ttk.Entry(vent_extract, width=15)
        entry_rango.pack(pady=5)

        def hacer_extraccion():
            rango_texto = entry_rango.get().strip()
            if not rango_texto:
                messagebox.showerror("Error", "Debe especificar un rango de páginas.")
                return
            try:
                if '-' in rango_texto:
                    start_str, end_str = rango_texto.split('-')
                    start_page = int(start_str) - 1
                    end_page = int(end_str) - 1
                    pages_list = list(range(start_page, end_page+1))
                else:
                    single_page = int(rango_texto) - 1
                    pages_list = [single_page]
            except ValueError:
                messagebox.showerror("Error", "Formato inválido. Use '1-3' o '5'.")
                return

            for p in pages_list:
                if p < 0 or p >= len(doc_original):
                    messagebox.showerror("Error", f"La página {p+1} está fuera de rango.")
                    return
            
            carpeta_destino = filedialog.askdirectory(title="Seleccionar carpeta de destino")
            if not carpeta_destino:
                return
            
            splitted_doc = fitz.open()
            for p in pages_list:
                splitted_doc.insert_pdf(doc_original, from_page=p, to_page=p)
            
            base_original = os.path.splitext(os.path.basename(ruta_pdf))[0]
            sub_name = f"{base_original}_pag_{rango_texto.replace('-', '_')}.pdf"
            path_final = Path(carpeta_destino) / sub_name
            c = 1
            while path_final.exists():
                path_final = Path(carpeta_destino) / f"{base_original}_pag_{rango_texto.replace('-', '_')}_{c}.pdf"
                c += 1
            
            try:
                splitted_doc.save(path_final)
                splitted_doc.close()
                messagebox.showinfo("Éxito", f"Se guardó la extracción en: {path_final.name}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar el PDF:\n{str(e)}")

            vent_extract.destroy()

        ttk.Button(vent_extract, text="Extraer", command=hacer_extraccion).pack(pady=5)

    def renombrar_pdf(self, ruta_pdf, fecha):
        """
        Renombra el PDF y luego lo quita de la lista para que no vuelva a aparecer.
        """
        dir_original = os.path.dirname(ruta_pdf)
        nombre_original = os.path.basename(ruta_pdf)
        base_name, ext = os.path.splitext(nombre_original)

        nuevo_nombre = f"{fecha}__{base_name}{ext}"

        carpeta_destino = filedialog.askdirectory(title="Seleccionar carpeta de destino para renombrar")
        if not carpeta_destino:
            return

        ruta_nueva = Path(carpeta_destino) / nuevo_nombre

        # Evitar colisiones
        contador = 1
        while ruta_nueva.exists():
            ruta_nueva = Path(carpeta_destino) / f"{fecha}__{base_name}_{contador}{ext}"
            contador += 1

        try:
            os.rename(ruta_pdf, ruta_nueva)
            messagebox.showinfo("Éxito", f"Archivo renombrado a: {ruta_nueva.name}")
            logging.info(f"Renombrado: {ruta_pdf} -> {ruta_nueva}")

            # --- Eliminar de la vista ---
            # 1) Quitar de self.archivos_pdf
            if nombre_original in self.archivos_pdf:
                self.archivos_pdf.remove(nombre_original)

            # 2) Eliminar las entradas en datos_paginas que apunten a la ruta original
            self.datos_paginas = [
                info for info in self.datos_paginas
                if info["ruta_pdf"] != ruta_pdf
            ]

            # 3) Refrescar la interfaz
            self.mostrar_pagina_actual()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo renombrar:\n{e}")

    def guardar_validaciones(self):
        """
        Guarda info de checks y observaciones en 'validaciones.txt'.
        """
        if not self.datos_paginas:
            messagebox.showinfo("Info", "No hay datos de páginas para guardar.")
            return

        with open("validaciones.txt", "w", encoding="utf-8") as f:
            for info in self.datos_paginas:
                check_str = "OK" if info["check_var"].get() else "NO"
                txt_obs = info["entry_widget"].get()
                linea = f"{info['pdf_name']} | Página {info['pag_index']+1} | Val={check_str} | Obs={txt_obs}\n"
                f.write(linea)
        
        messagebox.showinfo("Validaciones", "Se guardaron las validaciones en 'validaciones.txt'.")


if __name__ == "__main__":
    app = ValidadorMasivoPDF()
    app.mainloop()
