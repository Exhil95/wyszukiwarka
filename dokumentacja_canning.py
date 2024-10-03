import os
import tkinter as tk
from tkinter import messagebox, font, Label, Frame, Scrollbar, Canvas, Toplevel
import pdfplumber
import threading
import queue
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

def find_files_with_reference(directory, reference_number):
    matches = []
    pdf_files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if '$' in filename:
                continue
            file_path = os.path.join(root, filename)
            if reference_number in filename:
                matches.append((filename, file_path))
            elif filename.startswith('IP-') and filename.endswith('.pdf'):
                pdf_files.append(file_path)
    return matches, pdf_files

def search_pdf_content(pdf_files, reference_number, result_queue):
    for file_path in pdf_files:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and reference_number in text:
                        result_queue.put((os.path.basename(file_path), file_path))
                        break
        except Exception as e:
            print(f"Błąd odczytu {file_path}: {e}")
    result_queue.put(None)

def search_files_in_directory(directory):
    matches = []
    for root, _, filenames in os.walk(directory):
        if root != directory:
            continue
        for filename in filenames:
            if '$' in filename:
                continue
            file_path = os.path.join(root, filename)
            matches.append((filename, file_path))
    return matches

def update_tiles(files, gci_files=None):
    for widget in control_list_frame.winfo_children():
        widget.destroy()
    for widget in visualization_frame.winfo_children():
        widget.destroy()
    for widget in other_files_frame.winfo_children():
        widget.destroy()
    for widget in gci_frame.winfo_children():
        widget.destroy()

    for name, path in files:
        tile_text = name
        if name.startswith("CL"):
            if "op.5" in name:
                tile_text = "Lista kontrolna\nZaładunek"
                parent_frame = control_list_frame
            elif "op.20" in name or "op.30" in name:
                tile_text = "Lista kontrolna\nSpider"
                parent_frame = control_list_frame
            elif "op.110" in name:
                tile_text = "Lista kontrolna\nKontrola finalna"
                parent_frame = control_list_frame
            else:
                tile_text = "Lista kontrolna"
                parent_frame = control_list_frame
        elif name.startswith("VCL"):
            if "Identyfikacja komponentów" in name:
                tile_text = "Wizualizacja\nKomponenty"
                parent_frame = visualization_frame
            elif "pozycji" in name:
                tile_text = "Wizualizacja\nPozycja grawerki"
                parent_frame = visualization_frame
            elif "Treść" in name:
                tile_text = "Wizualizacja\nTreść grawerki"
                parent_frame = visualization_frame
            else:
                tile_text = "Wizualizacja"
                parent_frame = visualization_frame
        elif name.startswith("IP"):
            tile_text = "Instrukcja pakowania"
            parent_frame = other_files_frame
        elif name.startswith("Raport pomiarowy") or name.startswith("Raport Pomiarowy"):
            tile_text = "Raport pomiarowy"
            parent_frame = other_files_frame
        else:
            parent_frame = other_files_frame

        tile = Frame(parent_frame, bg='grey', padx=5, pady=5, relief=tk.RAISED, borderwidth=2)
        tile.pack(fill=tk.X, pady=5, padx=5)

        label = Label(tile, text=tile_text, bg='grey', fg='white', font=app_font)
        label.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)
        tile.bind("<Button-1>", lambda e, p=path: open_file(p))
        label.bind("<Button-1>", lambda e, p=path: open_file(p))
        create_tooltip(tile, name)

    if gci_files:
        for name, path in gci_files:
            tile_text = name
            parent_frame = gci_frame

            tile = Frame(parent_frame, bg='grey', padx=5, pady=5, relief=tk.RAISED, borderwidth=2)
            tile.pack(fill=tk.X, pady=5, padx=5)

            label = Label(tile, text=tile_text, bg='grey', fg='white', font=app_font)
            label.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)
            tile.bind("<Button-1>", lambda e, p=path: open_file(p))
            label.bind("<Button-1>", lambda e, p=path: open_file(p))
            create_tooltip(tile, name)

    status_label.config(text="Stan wyszukiwania: 100%")

def create_tooltip(widget, text):
    tooltip = tk.Toplevel(widget)
    tooltip.wm_overrideredirect(True)
    tooltip.withdraw()
    label = Label(tooltip, text=text, bg='white', relief=tk.SOLID, borderwidth=1, font=("times", "12", "normal"))
    label.pack(ipadx=5, ipady=5)

    def enter(event):
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + 20
        tooltip.wm_geometry(f"+{x}+{y}")
        tooltip.deiconify()

    def leave(event):
        tooltip.withdraw()

    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)

def open_file(file_to_open):
    try:
        os.startfile(file_to_open)
    except AttributeError:
        os.system(f'open "{file_to_open}"')
    except Exception as e:
        messagebox.showerror("Błąd", str(e))

def search_files():
    global files
    ref_number = entry.get()
    if not ref_number:
        messagebox.showinfo("Błąd", "Proszę wpisać numer referencyjny")
        return

    status_label.config(text="Stan wyszukiwania: 0%")

    files, pdf_files = find_files_with_reference(predefined_directory, ref_number)
    update_tiles(files)
    status_label.config(text="Stan wyszukiwania: 33%")

    if not files and not pdf_files:
        messagebox.showinfo("Wyniki", "Nie znaleziono plików z podaną referencją")
        status_label.config(text="Stan wyszukiwania: 100%")
        return

    if pdf_files:
        result_queue = queue.Queue()
        threading.Thread(target=search_pdf_content, args=(pdf_files, ref_number, result_queue)).start()
        root.after(100, check_queue, result_queue)

    status_label.config(text="Stan wyszukiwania: 67%")

def check_queue(result_queue):
    while not result_queue.empty():
        result = result_queue.get()
        if result is None:
            status_label.config(text="Stan wyszukiwania: 100%")
            return
        files.append(result)
        update_tiles(files)
    root.after(100, check_queue, result_queue)

def clear_search():
    entry.delete(0, tk.END)
    for widget in control_list_frame.winfo_children():
        widget.destroy()
    for widget in visualization_frame.winfo_children():
        widget.destroy()
    for widget in other_files_frame.winfo_children():
        widget.destroy()
    for widget in gci_frame.winfo_children():
        widget.destroy()
    status_label.config(text="Stan wyszukiwania: 0%")

def on_enter_key(event):
    search_files()

def open_directory_window(directory, title, tooltip_text):
    files = search_files_in_directory(directory)
    
    dir_window = Toplevel(root)
    dir_window.title(title)
    dir_window.configure(bg='#0033A0')
    
    canvas = Canvas(dir_window, bg='#0033A0')
    scroll_y = Scrollbar(dir_window, orient="vertical", command=canvas.yview)

    tile_frame = Frame(canvas, bg='#0033A0')

    for name, path in files:
        tile = Frame(tile_frame, bg='grey', padx=5, pady=5, relief=tk.RAISED, borderwidth=2)
        tile.pack(fill=tk.X, pady=5, padx=5)

        label = Label(tile, text=name, bg='grey', fg='white', font=app_font)
        label.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)
        tile.bind("<Button-1>", lambda e, p=path: open_file(p))
        label.bind("<Button-1>", lambda e, p=path: open_file(p))
        create_tooltip(tile, name)

    canvas.create_window((0, 0), window=tile_frame, anchor='nw')
    canvas.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox('all'), yscrollcommand=scroll_y.set)

    canvas.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
    scroll_y.pack(fill=tk.Y, side=tk.RIGHT)

    dir_window.update_idletasks()
    width = tile_frame.winfo_width() + scroll_y.winfo_width()
    height = tile_frame.winfo_height()
    dir_window.geometry(f"{width}x{height}")

predefined_directory = config.get('path', 'dir')
gci_directory = config.get('path', 'gci')
mpv_directory = config.get('path', 'mpv')
psi_directory = config.get('path', 'psi')
swi_directory = config.get('path', 'swi')
vbs_directory = config.get('path', 'vbs')

root = tk.Tk()
root.title("Canning - wyszukiwarka dokumentacji - Python edition")
root.configure(bg='#0033A0')

image_filename = tk.PhotoImage(file="tenlogo.png")

logo_label = Label(root, image=image_filename, bg='#0033A0')
logo_label.grid(row=0, column=0, columnspan=4, pady=10)

header_label = Label(root, text="Wyszukiwarka Dokumentacji - Canning", font=('Helvetica', 20, 'bold'), bg='#0033A0', fg='#ffffff')
header_label.grid(row=1, column=0, columnspan=4, pady=10)

app_font = font.Font(size=16)

entry = tk.Entry(root, width=50, font=app_font, bg='#ffffff', fg='#000000')
entry.grid(row=2, column=0, columnspan=4, pady=20)
entry.bind('<Return>', on_enter_key)

search_button = tk.Button(root, text="Szukaj plików", command=search_files, font=app_font, bg='#646464', fg='#ffffff')
search_button.grid(row=3, column=0, pady=10, padx=5)

gci_button = tk.Button(root, text="GCI", command=lambda: open_directory_window(gci_directory, "Pliki GCI", "Instrukcje jak poprawnie mierzyć/ używać przyrządów pomiarowych"), font=app_font, bg='#646464', fg='#ffffff')
gci_button.grid(row=3, column=1, pady=10, padx=5)

mpv_button = tk.Button(root, text="MPV", command=lambda: open_directory_window(mpv_directory, "Pliki MPV", "Instrukcja weryfikacji Poka-Yoke"), font=app_font, bg='#646464', fg='#ffffff')
mpv_button.grid(row=3, column=2, pady=10, padx=5)

psi_button = tk.Button(root, text="PSI", command=lambda: open_directory_window(psi_directory, "Pliki PSI", "Instrukcja ustawienia procesu"), font=app_font, bg='#646464', fg='#ffffff')
psi_button.grid(row=3, column=3, pady=10, padx=5)

swi_button = tk.Button(root, text="SWI", command=lambda: open_directory_window(swi_directory, "Pliki SWI", "Instrukcje pracy operatora"), font=app_font, bg='#646464', fg='#ffffff')
swi_button.grid(row=4, column=0, pady=10, padx=5)

vbs_button = tk.Button(root, text="VBS", command=lambda: open_directory_window(vbs_directory, "Pliki VBS", "Katalogi wad"), font=app_font, bg='#646464', fg='#ffffff')
vbs_button.grid(row=4, column=1, pady=10, padx=5)

clear_button = tk.Button(root, text="Resetuj", command=clear_search, font=app_font, bg='#646464', fg='#ffffff')
clear_button.grid(row=4, column=2, pady=10, padx=5)

create_tooltip(gci_button, "Instrukcje jak poprawnie mierzyć/ używać przyrządów pomiarowych")
create_tooltip(mpv_button, "Instrukcja weryfikacji Poka-Yoke")
create_tooltip(psi_button, "Instrukcja ustawienia procesu")
create_tooltip(swi_button, "Instrukcje pracy operatora")
create_tooltip(vbs_button, "Katalogi wad")

status_label = Label(root, text="Stan wyszukiwania: 0%", font=('Helvetica', 12), bg='#0033A0', fg='#ffffff')
status_label.grid(row=5, column=0, columnspan=4, pady=10)

canvas = Canvas(root, bg='#0033A0')
scroll_y = Scrollbar(root, orient="vertical", command=canvas.yview)

tile_frame = Frame(canvas, bg='#0033A0')

control_list_frame = Frame(tile_frame, bg='#0033A0')
control_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

visualization_frame = Frame(tile_frame, bg='#0033A0')
visualization_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

other_files_frame = Frame(tile_frame, bg='#0033A0')
other_files_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

gci_frame = Frame(tile_frame, bg='#0033A0')
gci_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

canvas.create_window((0, 0), window=tile_frame, anchor='nw')
canvas.update_idletasks()
canvas.configure(scrollregion=canvas.bbox('all'), yscrollcommand=scroll_y.set)

canvas.grid(row=6, column=0, columnspan=4, sticky='nsew')
scroll_y.grid(row=6, column=4, sticky='ns')

footer_label = Label(root, text="Wyszukiwarka dokumentacji Canningowych © 2024 by Denis Kuczka v.1_2", font=('Helvetica', 10), bg='#0033A0', fg='#ffffff')
footer_label.grid(row=7, column=0, columnspan=4, pady=10, sticky='ew')

root.grid_rowconfigure(6, weight=1)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_columnconfigure(3, weight=1)

root.mainloop()
