import os
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from downloader import Downloader, DownloadOptions
from settings import SettingsStore, DEFAULT_OUTPUT


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("4K Video Converter")
        self.minsize(760, 520)
        self._set_icon()

        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()

        self._queue = queue.Queue()
        self._downloader = Downloader(progress_cb=self._on_progress, log_cb=self._on_log, status_cb=self._on_status)
        self._download_thread = None
        self._analyze_thread = None
        self._closing = False

        self._build_ui()
        self._apply_settings_to_ui()

        self.after(100, self._poll_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_icon(self):
        # Optional: if you add an .ico file in assets/app.ico it will be used.
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "app.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        style = ttk.Style(self)
        style.theme_use("clam")
        self._apply_light_theme(style)

        notebook = ttk.Notebook(self)
        notebook.grid(row=0, column=0, sticky="nsew", padx=14, pady=12)

        self.tab_download = ttk.Frame(notebook)
        self.tab_settings = ttk.Frame(notebook)

        notebook.add(self.tab_download, text="Pobieranie")
        notebook.add(self.tab_settings, text="Ustawienia")

        self._build_download_tab()
        self._build_settings_tab()

    def _apply_light_theme(self, style: ttk.Style):
        bg = "#f3f5f8"
        panel = "#ffffff"
        panel_alt = "#f1f4f8"
        fg = "#1f2328"
        muted = "#5b6673"
        accent = "#2f6feb"

        self.configure(bg=bg)

        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg, padding=(2, 2), font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=bg, foreground=fg, font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", background=bg, foreground=muted, font=("Segoe UI", 10))

        style.configure("TButton", padding=(10, 6), background=panel_alt, foreground=fg, borderwidth=0, font=("Segoe UI", 10))
        style.map("TButton", background=[("active", "#e3e7ee")])
        style.configure("Primary.TButton", background=accent, foreground="white")
        style.map("Primary.TButton", background=[("active", "#4c86f0")], foreground=[("active", "white")])

        style.configure("TEntry", fieldbackground=panel, foreground=fg, insertcolor=fg, padding=6, font=("Segoe UI", 10))
        style.configure("TCombobox", fieldbackground=panel, foreground=fg, arrowcolor=fg, padding=4, font=("Segoe UI", 10))
        style.map("TCombobox", fieldbackground=[("readonly", panel)])
        style.configure("TCheckbutton", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[("active", bg)])
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", background=panel_alt, foreground=fg, padding=(14, 8), font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", panel)], foreground=[("selected", fg)])
        style.configure("Horizontal.TProgressbar", troughcolor=panel_alt, background=accent)
        style.configure("Card.TFrame", background=panel, borderwidth=0)
        style.configure("CardAlt.TFrame", background=panel_alt, borderwidth=0)

    def _build_download_tab(self):
        frame = self.tab_download
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=0)
        frame.rowconfigure(5, weight=1)

        header = ttk.Frame(frame)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="4K Video Converter", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Analizuj link, wybierz jakosc MP4 i pobierz.", style="Sub.TLabel").grid(
            row=1, column=0, sticky="w"
        )

        card = ttk.Frame(frame, style="Card.TFrame")
        card.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 12))
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="Link YouTube:").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(card, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))

        self.analyze_btn = ttk.Button(card, text="Analizuj", command=self._start_analyze)
        self.analyze_btn.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 12))

        row = ttk.Frame(frame, style="CardAlt.TFrame")
        row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 12))
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=0)

        ttk.Label(row, text="Jakosc:").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        self.quality_var = tk.StringVar(value="auto")
        self.quality_combo = ttk.Combobox(
            row,
            textvariable=self.quality_var,
            values=["auto"],
            state="disabled",
        )
        self.quality_combo.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 12))

        self.format_var = tk.StringVar(value="mp4")

        self.download_btn = ttk.Button(row, text="Pobierz", command=self._start_download, style="Primary.TButton")
        self.download_btn.grid(row=1, column=1, sticky="e", padx=12, pady=(0, 12))
        self.download_btn.configure(state="disabled")

        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(frame, variable=self.progress_var, maximum=100)
        self.progress.grid(row=3, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))

        self.status_var = tk.StringVar(value="Gotowy.")
        self.status_label = ttk.Label(frame, textvariable=self.status_var)
        self.status_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 10))

        log_card = ttk.Frame(frame, style="Card.TFrame")
        log_card.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=6, pady=(0, 6))
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)

        ttk.Label(log_card, text="Logi:").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        self.log_text = tk.Text(log_card, height=10, wrap="word")
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.log_text.configure(state="disabled", bg="#ffffff", fg="#1f2328", insertbackground="#1f2328")
        scroll = ttk.Scrollbar(log_card, orient="vertical", command=self.log_text.yview)
        scroll.grid(row=1, column=1, sticky="ns", padx=(0, 12), pady=(0, 12))
        self.log_text.configure(yscrollcommand=scroll.set)

    def _build_settings_tab(self):
        frame = self.tab_settings
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=0)

        header = ttk.Frame(frame)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Ustawienia", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Zmien lokalizacje zapisu pobranych plikow.", style="Sub.TLabel").grid(
            row=1, column=0, sticky="w"
        )

        card = ttk.Frame(frame, style="Card.TFrame")
        card.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 12))
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="Folder zapisu:").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(card, textvariable=self.path_var)
        self.path_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        ttk.Button(card, text="Wybierz...", command=self._choose_folder).grid(row=1, column=1, sticky="e", padx=12, pady=(0, 12))

        ttk.Button(frame, text="Zapisz ustawienia", command=self._save_settings, style="Primary.TButton").grid(
            row=2, column=0, sticky="w", padx=6, pady=(0, 6)
        )

    def _apply_settings_to_ui(self):
        self.path_var.set(self.settings.output_dir)

    def _choose_folder(self):
        selected = filedialog.askdirectory(initialdir=self.path_var.get() or DEFAULT_OUTPUT)
        if selected:
            self.path_var.set(selected)

    def _save_settings(self, show_message=True):
        self.settings.output_dir = self.path_var.get().strip() or DEFAULT_OUTPUT
        self.settings_store.save(self.settings)
        if show_message:
            messagebox.showinfo("Ustawienia", "Ustawienia zapisane.")

    def _start_analyze(self):
        if self._analyze_thread and self._analyze_thread.is_alive():
            messagebox.showwarning("Analiza", "Analiza juz trwa.")
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Blad", "Wklej link do YouTube.")
            return
        self._clear_log()
        self.progress_var.set(0)
        self.download_btn.configure(state="disabled")
        self.quality_combo.configure(state="disabled")
        self.analyze_btn.configure(state="disabled")
        self.status_var.set("Analizowanie linku...")
        self._analyze_thread = threading.Thread(target=self._analyze_worker, args=(url,), daemon=True)
        self._analyze_thread.start()

    def _analyze_worker(self, url: str):
        try:
            result = self._downloader.analyze(url)
            self._queue.put(("analyze_ok", result))
        except Exception as exc:
            self._queue.put(("error", str(exc)))

    def _start_download(self):
        if self._download_thread and self._download_thread.is_alive():
            messagebox.showwarning("Pobieranie", "Pobieranie juz trwa.")
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Blad", "Wklej link do YouTube.")
            return

        self._save_settings(show_message=False)
        self.progress_var.set(0)
        self._clear_log()
        self.status_var.set("Pobieranie...")

        options = DownloadOptions(
            url=url,
            output_dir=self.settings.output_dir,
            quality=self.quality_var.get() or "auto",
            fmt=self.format_var.get(),
        )

        self._download_thread = threading.Thread(target=self._download_worker, args=(options,), daemon=True)
        self._download_thread.start()

    def _download_worker(self, options: DownloadOptions):
        try:
            self._downloader.download(options)
            self._queue.put(("done", "Gotowe."))
        except Exception as exc:
            msg = str(exc)
            if "Cancelled by user" in msg:
                self._downloader.cleanup_temp()
                self._queue.put(("error", "Anulowano"))
            else:
                self._queue.put(("error", msg))

    def _on_progress(self, percent):
        self._queue.put(("progress", percent))

    def _on_log(self, message):
        self._queue.put(("log", message))

    def _on_status(self, message):
        self._queue.put(("status", message))

    def _poll_queue(self):
        try:
            while True:
                item = self._queue.get_nowait()
                kind, value = item
                if kind == "progress":
                    self.progress_var.set(value)
                elif kind == "log":
                    self._append_log(value)
                elif kind == "status":
                    self.status_var.set(value)
                elif kind == "error":
                    self._append_log(f"Blad: {value}")
                    messagebox.showerror("Blad", value)
                    self.analyze_btn.configure(state="normal")
                    if value == "Anulowano":
                        self._reset_ui()
                elif kind == "done":
                    self._append_log(value)
                    messagebox.showinfo("Pobieranie", value)
                    self._reset_ui()
                elif kind == "analyze_ok":
                    self._handle_analyze_result(value)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _handle_analyze_result(self, result):
        available = result.get("available_qualities") or []
        if not available:
            available = ["auto"]
        else:
            if "auto" not in available:
                available = ["auto"] + available
        self.quality_combo.configure(values=available, state="readonly")
        self.quality_var.set(available[0])
        title = result.get("title") or ""
        if title:
            self._append_log(f"Tytul: {title}")
        self._append_log("Dostepne jakosci (MP4): " + ", ".join(available))
        self.download_btn.configure(state="normal")
        self.analyze_btn.configure(state="normal")
        self.status_var.set("Analiza zakonczona.")

    def _append_log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _reset_ui(self):
        self.url_var.set("")
        self.quality_combo.configure(values=["auto"], state="disabled")
        self.quality_var.set("auto")
        self.progress_var.set(0)
        self.download_btn.configure(state="disabled")
        self.analyze_btn.configure(state="normal")
        self.status_var.set("Gotowy.")

    def _on_close(self):
        if self._download_thread and self._download_thread.is_alive():
            confirm = messagebox.askyesno("Zamknac?", "Trwa pobieranie. Na pewno przerwac?")
            if not confirm:
                return
            self.status_var.set("Anulowanie pobierania...")
            self._downloader.cancel()
            self._closing = True
            self.after(200, self._wait_close)
            return
        self.destroy()

    def _wait_close(self):
        if self._download_thread and self._download_thread.is_alive():
            self.after(200, self._wait_close)
            return
        self.destroy()
