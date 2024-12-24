import os
from collections import defaultdict
import tkinter as tk
from tkinter import filedialog, messagebox


def move_file(old_path, new_path):
    """Mueve un archivo de old_path a new_path."""
    try:
        os.rename(old_path, new_path)
    except Exception as e:
        print(f"Error al mover {old_path} a {new_path}: {e}")


def organize_folder(folder_path):
    """Organiza los archivos en la carpeta especificada por extensión."""
    file_counts = defaultdict(int)

    # Mover archivos a la carpeta principal y eliminar subcarpetas
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for file in files:
            old_path = os.path.join(root, file)
            new_path = os.path.join(folder_path, file)
            move_file(old_path, new_path)
        for dir in dirs:
            try:
                os.rmdir(os.path.join(root, dir))
            except OSError:
                print(f"No se pudo eliminar la carpeta {dir}, puede que no esté vacía.")

    # Organizar archivos por extensión
    for file in os.listdir(folder_path):
        if os.path.isfile(os.path.join(folder_path, file)):
            file_extension = os.path.splitext(file)[1].lower()
            file_counts[file_extension] += 1

            if file_extension == ".pdf":
                extension_folder = os.path.join(folder_path, "pdf")
            elif file_extension in [".jpg", ".jpeg", ".png", ".gif"]:
                extension_folder = os.path.join(folder_path, "imagenes")
            else:
                extension_folder = os.path.join(folder_path, file_extension[1:])

            if not os.path.exists(extension_folder):
                os.makedirs(extension_folder)

            old_path = os.path.join(folder_path, file)
            new_path = os.path.join(extension_folder, file)
            move_file(old_path, new_path)

    # Crear un archivo de resumen con el conteo de cada extensión de archivo
    summary_file = os.path.join(folder_path, "summary.txt")
    with open(summary_file, "w") as f:
        f.write("Conteo de archivos por extensión:\n")
        for extension, count in file_counts.items():
            f.write(f"{extension}: {count}\n")
        total_files = sum(file_counts.values())
        f.write(f"\nTotales: {total_files} archivos\n")

    return file_counts


def select_folder():
    """Abre un cuadro de diálogo para seleccionar una carpeta y organiza su contenido."""
    folder_path = filedialog.askdirectory()
    if folder_path:
        file_counts = organize_folder(folder_path)
        result_text = "Conteo de archivos por extensión:\n"
        for extension, count in file_counts.items():
            result_text += f"{extension}: {count}\n"
        total_files = sum(file_counts.values())
        result_text += f"\nTotales: {total_files} archivos\n"
        messagebox.showinfo("Resultados", result_text)


# Crear la ventana principal
root = tk.Tk()
root.title("Organizador de Carpetas")

# Crear y colocar el botón para seleccionar la carpeta y procesar
select_button = tk.Button(
    root, text="Seleccionar Carpeta y Procesar", command=select_folder
)
select_button.pack(pady=20)

# Ejecutar la aplicación
root.mainloop()
